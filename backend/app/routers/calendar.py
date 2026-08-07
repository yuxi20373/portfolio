from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


def _event_dict(e: models.CalendarEvent, now: datetime) -> dict:
    expired = e.kind == "reminder" and e.remind_at is not None and e.remind_at < now
    return {
        "id": e.id,
        "title": e.title,
        "kind": e.kind,
        "remind_at": e.remind_at,
        "expired": expired,
    }


@router.get("")
def calendar_month(
    year: int, month: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    """For the month grid: note titles per day (frontend caps the note
    titles shown to 2 + "..."), plus non-expired events/reminders per day -
    an expired reminder drops out of this month-grid preview entirely (it's
    only meant to nag you before its moment passes), but still shows up in
    calendar_day() below."""
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

    note_rows = (
        db.query(models.Note.created_at, models.Note.title)
        .filter(
            models.Note.user_id == user.id,
            models.Note.created_at >= start,
            models.Note.created_at < end,
        )
        .all()
    )
    notes_by_day = {}
    for dt, title in note_rows:
        d = dt.strftime("%Y-%m-%d")
        notes_by_day.setdefault(d, []).append(title)

    now = datetime.utcnow()
    event_rows = (
        db.query(models.CalendarEvent)
        .filter(
            models.CalendarEvent.user_id == user.id,
            models.CalendarEvent.event_date >= start.date(),
            models.CalendarEvent.event_date < end.date(),
        )
        .all()
    )
    events_by_day = {}
    for e in event_rows:
        if e.kind == "reminder" and e.remind_at is not None and e.remind_at < now:
            continue  # 過期的 reminder 不進月曆小格子的預覽,只有點進當天才看得到
        d = e.event_date.strftime("%Y-%m-%d")
        events_by_day.setdefault(d, []).append({"title": e.title, "kind": e.kind})

    return {"notes": notes_by_day, "events": events_by_day}


@router.get("/day")
def calendar_day(date_str: str, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Everything filed under a given day: notes, and events/reminders
    (including already-expired reminders - the frontend still lists those,
    just grayed out and sorted last; see _event_dict)."""
    day = datetime.strptime(date_str, "%Y-%m-%d")
    next_day = day + timedelta(days=1)

    notes = (
        db.query(models.Note)
        .filter(
            models.Note.user_id == user.id,
            models.Note.created_at >= day,
            models.Note.created_at < next_day,
        )
        .order_by(models.Note.created_at.asc())
        .all()
    )

    events = (
        db.query(models.CalendarEvent)
        .filter(
            models.CalendarEvent.user_id == user.id,
            models.CalendarEvent.event_date == day.date(),
        )
        .order_by(models.CalendarEvent.created_at.asc())
        .all()
    )
    now = datetime.utcnow()

    return {
        "notes": [{"id": n.id, "title": n.title, "created_at": n.created_at, "color": n.color} for n in notes],
        "events": [_event_dict(e, now) for e in events],
    }
