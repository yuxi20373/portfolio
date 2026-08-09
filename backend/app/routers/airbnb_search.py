"""Proxies Bright Data's "discover Airbnb by location" dataset scraper
(Dataset API, dataset_id=gd_ld7ll037kqy322v05, discover_by=location) - a
third-party service, not part of this app's own scraping code.

Unlike the AsiaYo proxy (routers/hotel_search.py), Bright Data has no
built-in result caching - every trigger call burns real quota against the
free 5K records/month tier. So this router owns its own cache: a repeat
search for the exact same locations/dates/adults within
settings.airbnb_search_cache_days returns the stored AirbnbSearch row
instead of triggering a fresh collection.

Multi-location: Bright Data's trigger body takes an `input` array, one
object per location, in a single call - so a search across several
locations at once is still one trigger/one snapshot, not N separate
searches. `limit_per_input` is literally "per input item" though, so to
keep a predictable total record budget (~settings.airbnb_search_total_limit
per search, regardless of how many locations are in it) it's divided
evenly across however many locations were requested.

Flow: POST creates (or reuses a cached) row and, if new, calls Bright
Data's /scrape endpoint (which is itself async despite the name - it
returns a snapshot_id immediately, not the data). GET polls Bright Data's
/progress endpoint and, once ready, fetches /snapshot and stores a
trimmed-down version of the results (the raw response is enormous - full
amenity lists, review text, HTML fragments - and mostly irrelevant to the
UI, see _extract_listing).
"""

import json
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
_BASE_URL = "https://api.brightdata.com/datasets/v3"


def _headers():
    return {"Authorization": f"Bearer {settings.brightdata_api_token}", "Content-Type": "application/json"}


class AirbnbSearchCreate(BaseModel):
    locations: List[str]
    check_in_date: str  # "YYYY-MM-DD"
    check_out_date: str
    adults: int = 1


def _location_key(locations: List[str]) -> str:
    """排序後存成 JSON 字串當快取比對用 - 使用者輸入順序不該影響是否命中
    快取(["A","B"] 跟 ["B","A"]要視為同一次搜尋)。"""
    return json.dumps(sorted(set(locations)))


def _extract_listing(raw: dict) -> Optional[dict]:
    """Bright Data 一個 raw record 有 40+ 個欄位(含完整 amenities/reviews/HTML
    片段),UI 用不到大部分,只挑幾個顯示會用到的存下來。有些 sub-item 爬失敗
    時整個 record 只有 error/error_code,沒有 name,直接跳過。"""
    if "name" not in raw and "listing_title" not in raw:
        return None
    pricing = raw.get("pricing_details") or {}
    images = raw.get("images") or []
    return {
        "property_id": raw.get("property_id"),
        "name": raw.get("listing_title") or raw.get("name"),
        "image": raw.get("image") or (images[0] if images else None),
        "price_per_night": pricing.get("price_per_night") or raw.get("price"),
        "total_price": raw.get("total_price"),
        "currency": raw.get("currency"),
        "rating": raw.get("ratings"),
        "review_count": raw.get("property_number_of_reviews"),
        "guests": raw.get("guests"),
        "is_superhost": raw.get("is_supperhost"),
        "is_guest_favorite": raw.get("is_guest_favorite"),
        "url": raw.get("final_url") or raw.get("url"),
        "discovery_location": (raw.get("discovery_input") or {}).get("location"),
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
    # 5K records/月的免費額度,固定抓一個 batch 就給 settings.airbnb_search_total_limit
    # 筆的預算,不管這次搜幾個地點,平均分掉(至少 1 筆/地點)。
    limit_per_input = max(1, settings.airbnb_search_total_limit // len(locations))
    return {
        "input": [
            {
                "location": loc,
                "check_in": f"{check_in_date}T00:00:00.000Z",
                "check_out": f"{check_out_date}T00:00:00.000Z",
                "num_of_adults": adults,
                "num_of_children": 0,
                "num_of_infants": "0",
                "num_of_pets": 0,
                "currency": "TWD",
                "country": "",
            }
            for loc in locations
        ],
        "limit_per_input": limit_per_input,
    }


# Bright Data 的 trigger 呼叫實測延遲落差很大 - 有時候 1 秒內就回
# snapshot_id,有時候要等 45-60 秒以上(甚至偶爾整個沒回應)。如果讓
# POST /searches 直接同步等這支呼叫,前端那個請求本身就會卡很久,Render
# 這類平台前面的 gateway 搞不好等不到那麼久就先斷線了。所以改成:先用
# status="pending" 建好 row、馬上回應前端,實際打 Bright Data 的動作丟到
# background task 做完才更新 row - 前端本來就是每 3 秒輪詢一次,pending
# 狀態直接復用「還在忙」的輪詢邏輯,不用改前端。
def _run_trigger(row_id: int, locations: List[str], check_in_date: str, check_out_date: str, adults: int):
    db = SessionLocal()
    try:
        row = db.query(models.AirbnbSearch).get(row_id)
        if not row:
            return
        try:
            r = requests.post(
                f"{_BASE_URL}/scrape",
                params={
                    "dataset_id": settings.brightdata_airbnb_dataset_id,
                    "notify": "false",
                    "include_errors": "true",
                    "type": "discover_new",
                    "discover_by": "location",
                },
                json=_trigger_body(locations, check_in_date, check_out_date, adults),
                headers=_headers(),
                timeout=120,
            )
            r.raise_for_status()
            row.snapshot_id = r.json()["snapshot_id"]
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
        currency="TWD",
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
    # 再扣一次 Bright Data 配額),原樣回傳讓前端下一輪再試。真的卡太久(超過
    # 10 分鐘還沒好)才視為失敗,避免永遠卡在 scraping。
    try:
        pr = requests.get(f"{_BASE_URL}/progress/{row.snapshot_id}", headers=_headers(), timeout=_TIMEOUT)
        pr.raise_for_status()
        progress = pr.json()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return _maybe_timeout(row, db)
    except Exception as e:
        row.status = "failed"
        row.error_message = str(e)
        db.commit()
        db.refresh(row)
        return _job_dict(row)

    bd_status = progress.get("status")
    if bd_status in ("failed", "error"):
        row.status = "failed"
        row.error_message = progress.get("message") or "Bright Data collection failed"
        db.commit()
        db.refresh(row)
        return _job_dict(row)

    if bd_status != "ready":
        # 還在跑(running/closing 之類的),原樣回傳,前端繼續輪詢。
        return _job_dict(row)

    try:
        sr = requests.get(
            f"{_BASE_URL}/snapshot/{row.snapshot_id}",
            params={"format": "json"},
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        sr.raise_for_status()
        raw_records = sr.json()
        listings = [x for x in (_extract_listing(r) for r in raw_records) if x]
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
        row.error_message = "Timed out waiting for Bright Data"
        db.commit()
        db.refresh(row)
    return _job_dict(row)
