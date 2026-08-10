from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(tags=["profile"])


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[str] = None


def _profile_dict(u: models.User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name,
        "avatar": u.avatar,
        "status": u.status,
    }


@router.get("/api/profile")
def get_profile(user: models.User = Depends(get_current_user)):
    return _profile_dict(user)


@router.patch("/api/profile")
def update_profile(
    payload: ProfileUpdate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    if payload.display_name is not None:
        name = payload.display_name.strip()
        user.display_name = name or None
    if payload.avatar is not None:
        user.avatar = payload.avatar or None
    if payload.status is not None:
        user.status = payload.status.strip() or None
    db.commit()
    db.refresh(user)
    return _profile_dict(user)


@router.get("/api/users/lookup")
def lookup_user(
    username: str = Query(...), db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    """給筆記分享功能用 - 輸入使用者帳號查對方的公開資料(顯示名稱/頭貼),
    不會回傳密碼相關的任何欄位。要登入才能查,但查誰都可以(這是內部小型
    多帳號共用系統,不是公開的使用者搜尋)。"""
    target = db.query(models.User).filter(models.User.username == username.strip()).first()
    if not target:
        raise HTTPException(404, "user not found")
    return _profile_dict(target)
