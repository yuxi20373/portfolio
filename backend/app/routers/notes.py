from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/notes", tags=["notes"])


class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[list[str]] = None
    date: Optional[str] = None  # "YYYY-MM-DD"; defaults to today if omitted


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None


class FavoriteUpdate(BaseModel):
    favorited: bool


class NoteTemplateCreate(BaseModel):
    name: str
    content: str = ""


class NoteTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None


class NoteTagCreate(BaseModel):
    name: str


def _note_dict(n: models.Note):
    return {
        "id": n.id,
        "title": n.title,
        "content": n.content,
        "tags": n.tags or [],
        "is_favorited": n.is_favorited,
        "created_at": n.created_at,
    }


def _get_owned_note(db: DBSession, note_id: int, user: models.User) -> models.Note:
    n = db.query(models.Note).get(note_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "not found")
    return n


@router.get("")
def list_notes(
    favorited: Optional[bool] = None,
    tag: Optional[str] = None,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """All of the user's notes, newest first - powers both the calendar
    page's sidebar "Favorites" list (favorited=true) and the standalone
    Notes page's browser (optionally filtered by tag)."""
    q = db.query(models.Note).filter(models.Note.user_id == user.id)
    if favorited:
        q = q.filter(models.Note.is_favorited.is_(True))
    notes = q.order_by(models.Note.created_at.desc()).all()
    if tag:
        notes = [n for n in notes if tag in (n.tags or [])]
    return [_note_dict(n) for n in notes]


@router.post("")
def create_note(
    payload: NoteCreate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(400, "title cannot be empty")

    if payload.date:
        # anchor the note to noon on the chosen calendar day, so it reliably
        # falls on that date regardless of timezone formatting on the frontend
        created_at = datetime.strptime(payload.date, "%Y-%m-%d").replace(hour=12)
    else:
        created_at = datetime.utcnow()

    note = models.Note(
        title=title,
        content=payload.content or "",
        tags=payload.tags or [],
        created_at=created_at,
        user_id=user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_dict(note)


@router.get("/{note_id}")
def get_note(note_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    n = _get_owned_note(db, note_id, user)
    return _note_dict(n)


@router.patch("/{note_id}")
def update_note(
    note_id: int,
    payload: NoteUpdate,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Direct manual edit of a note's title/content/tags - the note's date
    (created_at) doesn't change; delete and re-add it under a different day
    if you need to move it."""
    n = _get_owned_note(db, note_id, user)
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(400, "title cannot be empty")
        n.title = title
    if payload.content is not None:
        n.content = payload.content
    if payload.tags is not None:
        n.tags = payload.tags
    db.commit()
    db.refresh(n)
    return _note_dict(n)


@router.patch("/{note_id}/favorite")
def update_note_favorite(
    note_id: int,
    payload: FavoriteUpdate,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    n = _get_owned_note(db, note_id, user)
    n.is_favorited = payload.favorited
    db.commit()
    return {"id": n.id, "is_favorited": n.is_favorited}


@router.delete("/{note_id}")
def delete_note(note_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    n = _get_owned_note(db, note_id, user)
    db.delete(n)
    db.commit()
    return {"ok": True}


# ---------------- Templates (standalone Notes page) ----------------


@router.get("/templates")
def list_note_templates(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    templates = (
        db.query(models.NoteTemplate)
        .filter(models.NoteTemplate.user_id == user.id)
        .order_by(models.NoteTemplate.name.asc())
        .all()
    )
    return [{"id": t.id, "name": t.name, "content": t.content} for t in templates]


@router.post("/templates")
def create_note_template(
    payload: NoteTemplateCreate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name cannot be empty")
    t = models.NoteTemplate(name=name, content=payload.content, user_id=user.id)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "name": t.name, "content": t.content}


def _get_owned_template(db: DBSession, template_id: int, user: models.User) -> models.NoteTemplate:
    t = db.query(models.NoteTemplate).get(template_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "template not found")
    return t


@router.patch("/templates/{template_id}")
def update_note_template(
    template_id: int,
    payload: NoteTemplateUpdate,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    t = _get_owned_template(db, template_id, user)
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(400, "name cannot be empty")
        t.name = name
    if payload.content is not None:
        t.content = payload.content
    db.commit()
    return {"id": t.id, "name": t.name, "content": t.content}


@router.delete("/templates/{template_id}")
def delete_note_template(
    template_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    t = _get_owned_template(db, template_id, user)
    db.delete(t)
    db.commit()
    return {"ok": True}


# ---------------- Tags (standalone Notes page) ----------------


@router.get("/tags")
def list_note_tags(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    tags = (
        db.query(models.NoteTag).filter(models.NoteTag.user_id == user.id).order_by(models.NoteTag.name.asc()).all()
    )
    return [{"id": t.id, "name": t.name} for t in tags]


@router.post("/tags")
def create_note_tag(
    payload: NoteTagCreate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name cannot be empty")
    t = models.NoteTag(name=name, user_id=user.id)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "name": t.name}


@router.delete("/tags/{tag_id}")
def delete_note_tag(tag_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    t = db.query(models.NoteTag).get(tag_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "tag not found")
    db.delete(t)
    db.commit()
    return {"ok": True}
