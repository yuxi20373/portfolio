from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/events", tags=["events"])


class EventCreate(BaseModel):
    title: str
    kind: str  # "event" | "reminder"
    event_date: str  # "YYYY-MM-DD"
    remind_at: Optional[str] = None  # "YYYY-MM-DDTHH:MM" - required when kind == "reminder"


def _get_owned_event(db: DBSession, event_id: int, user: models.User) -> models.CalendarEvent:
    e = db.query(models.CalendarEvent).get(event_id)
    if not e or e.user_id != user.id:
        raise HTTPException(404, "not found")
    return e


@router.post("")
def create_event(
    payload: EventCreate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(400, "title cannot be empty")
    if payload.kind not in ("event", "reminder"):
        raise HTTPException(400, 'kind must be "event" or "reminder"')

    try:
        event_date = date.fromisoformat(payload.event_date)
    except ValueError:
        raise HTTPException(400, "event_date must be YYYY-MM-DD")

    remind_at = None
    if payload.kind == "reminder":
        if not payload.remind_at:
            raise HTTPException(400, "remind_at is required for a reminder")
        try:
            remind_at = datetime.fromisoformat(payload.remind_at)
        except ValueError:
            raise HTTPException(400, "remind_at must be an ISO date-time")

    e = models.CalendarEvent(
        title=title, kind=payload.kind, event_date=event_date, remind_at=remind_at, user_id=user.id
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"id": e.id, "title": e.title, "kind": e.kind, "event_date": e.event_date, "remind_at": e.remind_at}


@router.delete("/{event_id}")
def delete_event(event_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    e = _get_owned_event(db, event_id, user)
    db.delete(e)
    db.commit()
    return {"ok": True}
