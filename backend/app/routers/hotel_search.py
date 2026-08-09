"""Proxies the AsiaYo hotel-search microservice - a separately deployed
external service (https://asiayo-scraper-api.onrender.com), not part of
this app's own database/schema.

Proxied instead of called directly from the frontend for two reasons:
1. Its X-API-Key would otherwise have to ship inside the public frontend
   bundle (this app has no build-time secret injection beyond the
   non-secret API_BASE_URL - see frontend/build.js), which anyone could
   read out of the page source and reuse.
2. It sidesteps whatever CORS policy (or lack of one) that service has -
   the browser only ever talks to this backend's own domain.

These endpoints sit behind this app's own login (get_current_user), same
as the rest of the API, so the proxied external key can't be hit by
anonymous callers either.
"""

from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .. import models
from ..auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/api/hotel-search", tags=["hotel-search"])

_TIMEOUT = 20  # 爬蟲觸發的 job 建立本身很快(非同步),但保守一點抓長一點的 timeout


def _api_key_headers():
    return {"X-API-Key": settings.asiayo_api_key}


def _forward_error(r: requests.Response):
    raise HTTPException(status_code=r.status_code, detail=r.text)


class SearchCreate(BaseModel):
    city_slug: str
    check_in_date: str  # "YYYY-MM-DD"
    check_out_date: str  # "YYYY-MM-DD"


@router.get("/cities")
def list_cities(user: models.User = Depends(get_current_user)):
    """不需要 API key,但一樣掛在登入後面,跟其他 API 一致。"""
    r = requests.get(f"{settings.asiayo_api_base_url}/cities", timeout=_TIMEOUT)
    if r.status_code >= 400:
        _forward_error(r)
    return r.json()


@router.post("/searches", status_code=201)
def create_search(payload: SearchCreate, user: models.User = Depends(get_current_user)):
    r = requests.post(
        f"{settings.asiayo_api_base_url}/searches",
        json=payload.model_dump(),
        headers=_api_key_headers(),
        timeout=_TIMEOUT,
    )
    if r.status_code >= 400:
        _forward_error(r)
    return r.json()


@router.get("/searches/{job_id}")
def get_search(
    job_id: str,
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    amenities: Optional[str] = Query(None),
    user: models.User = Depends(get_current_user),
):
    params = {}
    if min_price is not None:
        params["min_price"] = min_price
    if max_price is not None:
        params["max_price"] = max_price
    if amenities:
        params["amenities"] = amenities
    r = requests.get(
        f"{settings.asiayo_api_base_url}/searches/{job_id}",
        params=params,
        headers=_api_key_headers(),
        timeout=_TIMEOUT,
    )
    if r.status_code >= 400:
        _forward_error(r)
    return r.json()
