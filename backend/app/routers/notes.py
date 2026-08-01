from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..database import get_db

router = APIRouter(prefix="/api/notes", tags=["notes"])


class NoteCreate(BaseModel):
    title: str
    content: str
    date: Optional[str] = None  # "YYYY-MM-DD"; defaults to today if omitted


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


def _note_dict(n: models.Note):
    return {"id": n.id, "title": n.title, "content": n.content, "created_at": n.created_at}


@router.post("")
def create_note(payload: NoteCreate, db: DBSession = Depends(get_db)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(400, "title cannot be empty")

    if payload.date:
        # anchor the note to noon on the chosen calendar day, so it reliably
        # falls on that date regardless of timezone formatting on the frontend
        created_at = datetime.strptime(payload.date, "%Y-%m-%d").replace(hour=12)
    else:
        created_at = datetime.utcnow()

    note = models.Note(title=title, content=payload.content or "", created_at=created_at)
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_dict(note)


@router.get("/{note_id}")
def get_note(note_id: int, db: DBSession = Depends(get_db)):
    n = db.query(models.Note).get(note_id)
    if not n:
        raise HTTPException(404, "not found")
    return _note_dict(n)


@router.patch("/{note_id}")
def update_note(note_id: int, payload: NoteUpdate, db: DBSession = Depends(get_db)):
    """Direct manual edit of a note's title/content - the note's date
    (created_at) doesn't change; delete and re-add it under a different day
    if you need to move it."""
    n = db.query(models.Note).get(note_id)
    if not n:
        raise HTTPException(404, "not found")
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(400, "title cannot be empty")
        n.title = title
    if payload.content is not None:
        n.content = payload.content
    db.commit()
    db.refresh(n)
    return _note_dict(n)


@router.delete("/{note_id}")
def delete_note(note_id: int, db: DBSession = Depends(get_db)):
    n = db.query(models.Note).get(note_id)
    if not n:
        raise HTTPException(404, "not found")
    db.delete(n)
    db.commit()
    return {"ok": True}
