"""Proxies Apify's "automation-lab/airbnb-listing" actor - a third-party
Airbnb scraper, not part of this app's own scraping code. Replaces the
earlier Bright Data integration: unlike Bright Data (which rejected any
price field with a strict validation error), this actor natively supports
server-side priceMin/priceMax filtering. It has no rating/review-count
filter though, so that part is still done client-side (see HotelSearchView.js's
TOP_N sort).

Apify has no built-in result caching either (same situation Bright Data was
in) - every run burns real platform credit (PAY_PER_EVENT pricing: $0.005
per run + $0.005 per listing scraped - the $5/month free platform credit is
roughly 1000 listings' worth). So this router still owns its own cache: a
repeat search for the exact same locations/dates/adults within
settings.airbnb_search_cache_days returns the stored AirbnbSearch row
instead of triggering a fresh run.

Multi-location: the actor's `locationQueries` input takes an array directly,
so a search across several locations is still one run, not N separate
searches - simpler than Bright Data's per-input `limit_per_input` math,
though it also means there's no per-location breakdown in the raw results
(see _extract_listing's discovery_location: always None here, unlike the
Bright Data version).

Flow: POST creates (or reuses a cached) row and, if new, calls Apify's
POST /v2/acts/{actor}/runs (genuinely async - returns a run id immediately,
confirmed via direct testing: trigger responds in ~1s regardless of how
long the actual scrape takes). GET polls Apify's GET /v2/actor-runs/{runId}
and, once SUCCEEDED, fetches GET /v2/actor-runs/{runId}/dataset/items and
stores a trimmed-down version of the results (see _extract_listing - Apify's
raw fields are nested objects with currency-symbol-prefixed price strings,
very different shape from Bright Data's flat numeric fields).
"""

import json
import re
from datetime import date, datetime, timedelta
from typing import List, Optional

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..config import settings
from ..database import get_db, SessionLocal

router = APIRouter(prefix="/api/airbnb-search", tags=["airbnb-search"])

_TIMEOUT = 45
_BASE_URL = "https://api.apify.com/v2"


def _params(**extra):
    return {"token": settings.apify_api_token, **extra}


class AirbnbSearchCreate(BaseModel):
    locations: List[str]
    check_in_date: str  # "YYYY-MM-DD"
    check_out_date: str
    adults: int = 1


def _location_key(locations: List[str]) -> str:
    """排序後存成 JSON 字串當快取比對用 - 使用者輸入順序不該影響是否命中
    快取(["A","B"] 跟 ["B","A"]要視為同一次搜尋)。"""
    return json.dumps(sorted(set(locations)))


_PRICE_RE = re.compile(r"[\d,.]+")


def _parse_price(s: Optional[str]) -> Optional[float]:
    """Apify 的價格是帶符號的字串,例如 "$129"、"NT$3,450" - 不是純數字,
    要自己抓數字部分轉成 float。"""
    if not s:
        return None
    m = _PRICE_RE.search(s)
    return float(m.group().replace(",", "")) if m else None


def _extract_listing(raw: dict, nights: int) -> Optional[dict]:
    """Apify 一筆 raw record 的欄位形狀跟 Bright Data 完全不同 - title/price/
    rating 都是巢狀物件,價格要自己轉數字、算平均每晚價(actor 本身只給整段
    住宿的總價,不是每晚價)。skipDetailPages=true(見 _trigger_body)模式下
    沒有 guests/amenities/is_guest_favorite 這些要進 detail page 才有的欄位,
    固定回 None,前端本來就是 v-if 顯示,缺欄位不會壞掉。"""
    if "id" not in raw:
        return None
    price = raw.get("price") or {}
    rating = raw.get("rating") or {}
    total = _parse_price(price.get("price"))
    return {
        "property_id": raw.get("id"),
        "name": raw.get("title"),
        "image": raw.get("thumbnail"),
        "price_per_night": round(total / nights, 2) if total and nights else None,
        "total_price": total,
        "currency": "USD",
        "rating": rating.get("guestSatisfaction"),
        "review_count": rating.get("reviewsCount"),
        "guests": None,
        "is_superhost": raw.get("isSuperHost"),
        "is_guest_favorite": None,
        "url": raw.get("url"),
        "discovery_location": None,
    }


def _job_dict(row: models.AirbnbSearch) -> dict:
    results = json.loads(row.results) if row.results else []
    return {
        "id": row.id,
        "locations": json.loads(row.location),
        "check_in_date": row.check_in.isoformat(),
        "check_out_date": row.check_out.isoformat(),
        "adults": row.adults,
        "status": row.status,
        "error_message": row.error_message,
        "hotel_count": len(results) if row.status == "done" else None,
        "results": results,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _trigger_body(locations: List[str], check_in_date: str, check_out_date: str, adults: int) -> dict:
    return {
        "locationQueries": locations,
        "checkIn": check_in_date,
        "checkOut": check_out_date,
        "adults": adults,
        "currency": "USD",  # actor 的 currency enum 沒有 TWD
        "skipDetailPages": True,
        "maxListings": settings.airbnb_search_total_limit,
        "maxRequestsPerCrawl": settings.airbnb_search_max_requests,
    }


# 直接測試過 Apify 的 trigger 呼叫 - POST /runs 幾乎立刻回應(~1 秒),不像
# Bright Data 的 trigger 偶爾要等 45-60 秒以上,但還是丟 background task 做,
# 理由不變:POST /searches 本身不該卡著等一個外部服務,前端本來就是每 3 秒
# 輪詢一次,pending 狀態直接復用「還在忙」的輪詢邏輯。
def _run_trigger(row_id: int, locations: List[str], check_in_date: str, check_out_date: str, adults: int):
    db = SessionLocal()
    try:
        row = db.query(models.AirbnbSearch).get(row_id)
        if not row:
            return
        try:
            r = requests.post(
                f"{_BASE_URL}/acts/{settings.apify_airbnb_actor_id}/runs",
                params=_params(),
                json=_trigger_body(locations, check_in_date, check_out_date, adults),
                timeout=120,
            )
            r.raise_for_status()
            row.snapshot_id = r.json()["data"]["id"]  # Apify run id
            row.status = "scraping"
        except Exception as e:
            row.status = "failed"
            row.error_message = str(e)
        db.commit()
    finally:
        db.close()


@router.post("/searches", status_code=201)
def create_search(
    payload: AirbnbSearchCreate,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if not payload.locations:
        raise HTTPException(status_code=422, detail="locations must not be empty")

    check_in = date.fromisoformat(payload.check_in_date)
    check_out = date.fromisoformat(payload.check_out_date)
    location_key = _location_key(payload.locations)

    cutoff = datetime.utcnow() - timedelta(days=settings.airbnb_search_cache_days)
    cached = (
        db.query(models.AirbnbSearch)
        .filter(
            models.AirbnbSearch.location == location_key,
            models.AirbnbSearch.check_in == check_in,
            models.AirbnbSearch.check_out == check_out,
            models.AirbnbSearch.adults == payload.adults,
            models.AirbnbSearch.status == "done",
            models.AirbnbSearch.created_at >= cutoff,
        )
        .order_by(models.AirbnbSearch.created_at.desc())
        .first()
    )
    if cached:
        return _job_dict(cached)

    row = models.AirbnbSearch(
        location=location_key,
        check_in=check_in,
        check_out=check_out,
        adults=payload.adults,
        currency="USD",
        status="pending",
        user_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    background_tasks.add_task(
        _run_trigger, row.id, payload.locations, payload.check_in_date, payload.check_out_date, payload.adults
    )
    return _job_dict(row)


@router.get("/searches/{job_id}")
def get_search(
    job_id: int,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    row = db.query(models.AirbnbSearch).get(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="not found")

    if row.status != "scraping" or not row.snapshot_id:
        return _job_dict(row)

    # 前端每 3 秒就會來戳一次這支 API,單次逾時/連線失敗多半只是暫時的網路
    # 抖動 - 不要直接判定整個 job 失敗(那樣使用者要重新整個搜一次,還是要
    # 再扣一次 Apify 額度),原樣回傳讓前端下一輪再試。真的卡太久(超過
    # 10 分鐘還沒好)才視為失敗,避免永遠卡在 scraping。
    try:
        pr = requests.get(f"{_BASE_URL}/actor-runs/{row.snapshot_id}", params=_params(), timeout=_TIMEOUT)
        pr.raise_for_status()
        run = pr.json()["data"]
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return _maybe_timeout(row, db)
    except Exception as e:
        row.status = "failed"
        row.error_message = str(e)
        db.commit()
        db.refresh(row)
        return _job_dict(row)

    apify_status = run.get("status")
    if apify_status in ("FAILED", "ABORTED", "TIMED-OUT"):
        row.status = "failed"
        row.error_message = f"Apify run {apify_status}"
        db.commit()
        db.refresh(row)
        return _job_dict(row)

    if apify_status != "SUCCEEDED":
        # 還在跑(READY/RUNNING/ABORTING/TIMING-OUT 之類),原樣回傳,前端繼續輪詢。
        return _job_dict(row)

    try:
        sr = requests.get(
            f"{_BASE_URL}/actor-runs/{row.snapshot_id}/dataset/items",
            params=_params(format="json"),
            timeout=_TIMEOUT,
        )
        sr.raise_for_status()
        raw_records = sr.json()
        nights = (row.check_out - row.check_in).days
        listings = [x for x in (_extract_listing(r, nights) for r in raw_records) if x]
        row.results = json.dumps(listings)
        row.status = "done"
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return _maybe_timeout(row, db)
    except Exception as e:
        row.status = "failed"
        row.error_message = str(e)
    db.commit()
    db.refresh(row)
    return _job_dict(row)


_STUCK_AFTER_MINUTES = 10


def _maybe_timeout(row: models.AirbnbSearch, db: DBSession) -> dict:
    """暫時的網路逾時/連線失敗 - 不動 row,讓前端下一輪繼續輪詢;但如果這個
    job 已經卡超過 _STUCK_AFTER_MINUTES 分鐘都還是 scraping,就不要再讓它
    無限卡下去了,標記失敗讓使用者可以重搜。"""
    if row.created_at and datetime.utcnow() - row.created_at > timedelta(minutes=_STUCK_AFTER_MINUTES):
        row.status = "failed"
        row.error_message = "Timed out waiting for Apify"
        db.commit()
        db.refresh(row)
    return _job_dict(row)
