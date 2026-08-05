from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/memos", tags=["memos"])


class MemoCreate(BaseModel):
    text: str


class MemoUpdate(BaseModel):
    text: Optional[str] = None
    done: Optional[bool] = None


def _memo_dict(m: models.MemoItem):
    return {"id": m.id, "text": m.text, "done": m.done}


def _get_owned_memo(db: DBSession, memo_id: int, user: models.User) -> models.MemoItem:
    m = db.query(models.MemoItem).get(memo_id)
    if not m or m.user_id != user.id:
        raise HTTPException(404, "not found")
    return m


@router.get("")
def list_memos(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    items = (
        db.query(models.MemoItem)
        .filter(models.MemoItem.user_id == user.id)
        .order_by(models.MemoItem.created_at.asc())
        .all()
    )
    return [_memo_dict(m) for m in items]


@router.post("")
def create_memo(payload: MemoCreate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(400, "text cannot be empty")
    m = models.MemoItem(text=text, user_id=user.id)
    db.add(m)
    db.commit()
    db.refresh(m)
    return _memo_dict(m)


@router.patch("/{memo_id}")
def update_memo(
    memo_id: int, payload: MemoUpdate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    m = _get_owned_memo(db, memo_id, user)
    if payload.text is not None:
        text = payload.text.strip()
        if not text:
            raise HTTPException(400, "text cannot be empty")
        m.text = text
    if payload.done is not None:
        m.done = payload.done
    db.commit()
    return _memo_dict(m)


@router.delete("/{memo_id}")
def delete_memo(memo_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    m = _get_owned_memo(db, memo_id, user)
    db.delete(m)
    db.commit()
    return {"ok": True}
