from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..database import get_db

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("")
def calendar_month(year: int, month: int, db: DBSession = Depends(get_db)):
    """For the month grid: conversation counts per day, and note titles per
    day (frontend caps the note titles shown to 2 + "..."). Both by creation time."""
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

    session_rows = (
        db.query(models.ChatSession.created_at)
        .filter(models.ChatSession.created_at >= start, models.ChatSession.created_at < end)
        .all()
    )
    counts = {}
    for (dt,) in session_rows:
        d = dt.strftime("%Y-%m-%d")
        counts[d] = counts.get(d, 0) + 1

    note_rows = (
        db.query(models.Note.created_at, models.Note.title)
        .filter(models.Note.created_at >= start, models.Note.created_at < end)
        .all()
    )
    notes_by_day = {}
    for dt, title in note_rows:
        d = dt.strftime("%Y-%m-%d")
        notes_by_day.setdefault(d, []).append(title)

    return {"counts": counts, "notes": notes_by_day}


@router.get("/day")
def calendar_day(date_str: str, db: DBSession = Depends(get_db)):
    """Everything created on a given day: conversations, wiki entries, and notes."""
    day = datetime.strptime(date_str, "%Y-%m-%d")
    next_day = day + timedelta(days=1)

    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.created_at >= day, models.ChatSession.created_at < next_day)
        .order_by(models.ChatSession.created_at.asc())
        .all()
    )

    wiki_entries = (
        db.query(models.WikiEntry)
        .filter(models.WikiEntry.created_at >= day, models.WikiEntry.created_at < next_day)
        .order_by(models.WikiEntry.title.asc())
        .all()
    )

    notes = (
        db.query(models.Note)
        .filter(models.Note.created_at >= day, models.Note.created_at < next_day)
        .order_by(models.Note.created_at.asc())
        .all()
    )

    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "channel": s.channel,
                "created_at": s.created_at,
                "last_message_at": s.last_message_at,
            }
            for s in sessions
        ],
        "wiki_entries": [{"id": e.id, "title": e.title, "entry_type": e.entry_type} for e in wiki_entries],
        "notes": [{"id": n.id, "title": n.title, "created_at": n.created_at} for n in notes],
    }
