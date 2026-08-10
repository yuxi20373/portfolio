from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/notes", tags=["notes"])


class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[list[str]] = None
    color: Optional[str] = None
    date: Optional[str] = None  # "YYYY-MM-DD"; defaults to today if omitted


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    color: Optional[str] = None


class FavoriteUpdate(BaseModel):
    favorited: bool


class NoteTemplateCreate(BaseModel):
    name: str
    content: str = ""
    tags: Optional[list[str]] = None


class NoteTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None


class NoteTagCreate(BaseModel):
    name: str


class NoteTagUpdate(BaseModel):
    name: str


class ShareCreate(BaseModel):
    username: str


def _note_dict(n: models.Note, shared_with: Optional[list] = None):
    d = {
        "id": n.id,
        "title": n.title,
        "content": n.content,
        "tags": n.tags or [],
        "color": n.color,
        "is_favorited": n.is_favorited,
        "created_at": n.created_at,
    }
    if shared_with is not None:
        d["shared_with"] = shared_with
    return d


def _user_dict(u: models.User) -> dict:
    return {"username": u.username, "display_name": u.display_name, "avatar": u.avatar}


def _shares_by_note(db: DBSession, note_ids: list[int]) -> dict:
    """note_id -> [user_dict, ...] - 一次查完一批筆記的分享對象,不要每則筆記
    各查一次(N+1)。概念是「共享的文章」,不只收件人看得到,筆記本人自己
    的列表/詳情頁也要能看到這篇被分享給誰(見 list_notes/get_note)。"""
    if not note_ids:
        return {}
    rows = (
        db.query(models.NoteShare, models.User)
        .join(models.User, models.NoteShare.shared_with_user_id == models.User.id)
        .filter(models.NoteShare.note_id.in_(note_ids))
        .all()
    )
    result = {}
    for share, u in rows:
        result.setdefault(share.note_id, []).append(_user_dict(u))
    return result


def _get_owned_note(db: DBSession, note_id: int, user: models.User) -> models.Note:
    n = db.query(models.Note).get(note_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "not found")
    return n


def _get_viewable_note(db: DBSession, note_id: int, user: models.User) -> models.Note:
    """給讀取用(GET)- 除了自己的筆記,別人分享給你的筆記也看得到(唯讀)。
    編輯/刪除/收藏一律還是走 _get_owned_note,分享出去的筆記不能被對方改。"""
    n = db.query(models.Note).get(note_id)
    if not n:
        raise HTTPException(404, "not found")
    if n.user_id == user.id:
        return n
    shared = (
        db.query(models.NoteShare)
        .filter(models.NoteShare.note_id == note_id, models.NoteShare.shared_with_user_id == user.id)
        .first()
    )
    if not shared:
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
    shares = _shares_by_note(db, [n.id for n in notes])
    return [_note_dict(n, shares.get(n.id, [])) for n in notes]


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
        color=payload.color,
        created_at=created_at,
        user_id=user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_dict(note)


# ---------------- Templates (standalone Notes page) ----------------
#
# These, and the Tags routes further down, are registered before the
# generic /{note_id} routes below on purpose - FastAPI/Starlette matches
# routes in registration order, and /{note_id} matches any single path
# segment (including the literal strings "templates"/"tags"), so if it came
# first, GET /api/notes/templates and /tags would be swallowed by get_note()
# and fail trying to int()-parse "templates"/"tags" as a note id.


@router.get("/templates")
def list_note_templates(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    templates = (
        db.query(models.NoteTemplate)
        .filter(models.NoteTemplate.user_id == user.id)
        .order_by(models.NoteTemplate.name.asc())
        .all()
    )
    return [{"id": t.id, "name": t.name, "content": t.content, "tags": t.tags or []} for t in templates]


@router.post("/templates")
def create_note_template(
    payload: NoteTemplateCreate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name cannot be empty")
    t = models.NoteTemplate(name=name, content=payload.content, tags=payload.tags or [], user_id=user.id)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "name": t.name, "content": t.content, "tags": t.tags or []}


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
    if payload.tags is not None:
        t.tags = payload.tags
    db.commit()
    return {"id": t.id, "name": t.name, "content": t.content, "tags": t.tags or []}


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


@router.patch("/tags/{tag_id}")
def update_note_tag(
    tag_id: int, payload: NoteTagUpdate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    t = db.query(models.NoteTag).get(tag_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "tag not found")
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name cannot be empty")
    t.name = name
    db.commit()
    return {"id": t.id, "name": t.name}


@router.delete("/tags/{tag_id}")
def delete_note_tag(tag_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    t = db.query(models.NoteTag).get(tag_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "tag not found")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ---------------- Sharing ----------------
#
# Same registration-order reasoning as Templates/Tags above - /shared and
# /shared/recent-targets are static paths that must come before /{note_id}.


@router.get("/shared")
def list_shared_notes(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    """別人分享給我的筆記,唯讀 - 見 NotesView.js 底下的「Shared with me」區塊。"""
    rows = (
        db.query(models.Note, models.User)
        .join(models.NoteShare, models.NoteShare.note_id == models.Note.id)
        .join(models.User, models.Note.user_id == models.User.id)
        .filter(models.NoteShare.shared_with_user_id == user.id)
        .order_by(models.NoteShare.created_at.desc())
        .all()
    )
    result = []
    for n, owner in rows:
        d = _note_dict(n)
        d["shared_by"] = _user_dict(owner)
        result.append(d)
    return result


@router.get("/shared/recent-targets")
def recent_share_targets(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    """我最近分享出去(不是分享給我)的對象,依最後分享時間排序取前 2 個,
    給分享面板當快速選項用(見 NotesView.js)。"""
    rows = (
        db.query(models.User, func.max(models.NoteShare.created_at).label("last_shared"))
        .join(models.NoteShare, models.NoteShare.shared_with_user_id == models.User.id)
        .join(models.Note, models.NoteShare.note_id == models.Note.id)
        .filter(models.Note.user_id == user.id)
        .group_by(models.User.id)
        .order_by(func.max(models.NoteShare.created_at).desc())
        .limit(2)
        .all()
    )
    return [_user_dict(u) for u, _last_shared in rows]


# ---------------- Single note by id ----------------
#
# Registered last - see the comment above the Templates section for why
# these generic /{note_id} routes have to come after every static-path route.


@router.get("/{note_id}")
def get_note(note_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    n = _get_viewable_note(db, note_id, user)
    is_owner = n.user_id == user.id
    d = _note_dict(n, _shares_by_note(db, [n.id]).get(n.id, []) if is_owner else None)
    d["is_owner"] = is_owner
    if not is_owner:
        owner = db.query(models.User).get(n.user_id)
        d["shared_by"] = _user_dict(owner)
    return d


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
    if payload.color is not None:
        n.color = payload.color
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


@router.post("/{note_id}/share")
def share_note(
    note_id: int,
    payload: ShareCreate,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """只有筆記本人能分享(_get_owned_note),分享出去的一方唯讀 - 見
    _get_viewable_note。同一個人重複分享同一則筆記是 no-op,不會出錯也不會
    重複建立紀錄(note_shares 有 unique constraint)。"""
    n = _get_owned_note(db, note_id, user)
    target_username = payload.username.strip()
    if not target_username:
        raise HTTPException(400, "username cannot be empty")
    target = db.query(models.User).filter(models.User.username == target_username).first()
    if not target:
        raise HTTPException(404, "user not found")
    if target.id == user.id:
        raise HTTPException(400, "cannot share a note with yourself")

    existing = (
        db.query(models.NoteShare)
        .filter(models.NoteShare.note_id == n.id, models.NoteShare.shared_with_user_id == target.id)
        .first()
    )
    if not existing:
        db.add(models.NoteShare(note_id=n.id, shared_with_user_id=target.id))
        db.commit()
    return {"ok": True, "shared_with": _user_dict(target)}
