from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from datetime import datetime

from .. import models
from ..auth import get_current_user
from ..database import get_db
from ..services.wiki.wiki_search_service import create_or_update_via_search
from ..services.wiki.wiki_adjust_service import propose_adjustment, apply_adjustment
from ..schemas.wiki import WikiEntryUpdate, WikiFolderCreate, WikiFolderUpdate

router = APIRouter(prefix="/api", tags=["wiki"])


class WikiSearchRequest(BaseModel):
    keyword: str
    question: str


class WikiAdjustPreviewRequest(BaseModel):
    instruction: str
    base_content: Optional[str] = None
    base_summary: Optional[str] = None


class WikiAdjustApplyRequest(BaseModel):
    content: str
    summary: Optional[str] = None


class FavoriteUpdate(BaseModel):
    favorited: bool


def _get_owned_entry(db: DBSession, entry_id: int, user: models.User) -> models.WikiEntry:
    e = db.query(models.WikiEntry).get(entry_id)
    if not e or e.user_id != user.id:
        raise HTTPException(404, "not found")
    return e


def _get_owned_folder(db: DBSession, folder_id: int, user: models.User) -> models.WikiFolder:
    f = db.query(models.WikiFolder).get(folder_id)
    if not f or f.user_id != user.id:
        raise HTTPException(404, "folder not found")
    return f


@router.get("/wiki")
def list_wiki(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    entries = (
        db.query(models.WikiEntry)
        .filter(models.WikiEntry.user_id == user.id)
        .order_by(models.WikiEntry.updated_at.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "title": e.title,
            "entry_type": e.entry_type,
            "summary": e.summary,
            "tags": e.tags,
            "folder_id": e.folder_id,
            "is_favorited": e.is_favorited,
            "updated_at": e.updated_at,
        }
        for e in entries
    ]


def _wiki_entry_detail(db: DBSession, e: models.WikiEntry, user: models.User):
    related = []
    for title in e.related_titles or []:
        t = db.query(models.WikiEntry).filter(models.WikiEntry.user_id == user.id, models.WikiEntry.title == title).first()
        if t:
            related.append({"id": t.id, "title": t.title})

    return {
        "id": e.id,
        "title": e.title,
        "entry_type": e.entry_type,
        "summary": e.summary,
        "content": e.content,
        "tags": e.tags,
        "folder_id": e.folder_id,
        "is_favorited": e.is_favorited,
        "updated_at": e.updated_at,
        "related": related,
    }


@router.get("/wiki/{entry_id}")
def get_wiki_entry(entry_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    e = _get_owned_entry(db, entry_id, user)
    return _wiki_entry_detail(db, e, user)


@router.patch("/wiki/{entry_id}")
def update_wiki_entry(
    entry_id: int,
    payload: WikiEntryUpdate,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Direct manual edit (title/content/tags/etc) and/or moving the entry
    into a different folder - no LLM involved at all."""
    e = _get_owned_entry(db, entry_id, user)

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(400, "title cannot be empty")
        e.title = title
    if payload.entry_type is not None:
        e.entry_type = payload.entry_type
    if payload.summary is not None:
        e.summary = payload.summary
    if payload.content is not None:
        e.content = payload.content
    if payload.tags is not None:
        e.tags = payload.tags
    if payload.clear_folder:
        e.folder_id = None
    elif payload.folder_id is not None:
        folder = _get_owned_folder(db, payload.folder_id, user)
        e.folder_id = folder.id

    e.updated_at = datetime.utcnow()
    db.commit()
    return _wiki_entry_detail(db, e, user)


@router.patch("/wiki/{entry_id}/favorite")
def update_wiki_favorite(
    entry_id: int,
    payload: FavoriteUpdate,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    e = _get_owned_entry(db, entry_id, user)
    e.is_favorited = payload.favorited
    db.commit()
    return {"id": e.id, "is_favorited": e.is_favorited}


@router.delete("/wiki/{entry_id}")
def delete_wiki_entry(entry_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    e = _get_owned_entry(db, entry_id, user)
    db.delete(e)
    db.commit()
    return {"ok": True}


@router.post("/wiki/search")
def search_into_wiki(
    payload: WikiSearchRequest, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    try:
        entry = create_or_update_via_search(db, user.id, payload.keyword, payload.question)
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    return _wiki_entry_detail(db, entry, user)


@router.post("/wiki/{entry_id}/adjust/preview")
def preview_wiki_adjustment(
    entry_id: int,
    payload: WikiAdjustPreviewRequest,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    e = _get_owned_entry(db, entry_id, user)
    try:
        return propose_adjustment(db, e, payload.instruction, payload.base_content, payload.base_summary)
    except ValueError as ex:
        raise HTTPException(400, str(ex))


@router.post("/wiki/{entry_id}/adjust/apply")
def apply_wiki_adjustment(
    entry_id: int,
    payload: WikiAdjustApplyRequest,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    e = _get_owned_entry(db, entry_id, user)
    apply_adjustment(db, e, payload.summary, payload.content)
    return _wiki_entry_detail(db, e, user)


# ---------------- Folders (user-created, manual organization only) ----------------


@router.get("/wiki-folders")
def list_wiki_folders(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    folders = (
        db.query(models.WikiFolder)
        .filter(models.WikiFolder.user_id == user.id)
        .order_by(models.WikiFolder.name.asc())
        .all()
    )
    return [{"id": f.id, "name": f.name} for f in folders]


@router.post("/wiki-folders")
def create_wiki_folder(
    payload: WikiFolderCreate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name cannot be empty")
    folder = models.WikiFolder(name=name, user_id=user.id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "name": folder.name}


@router.patch("/wiki-folders/{folder_id}")
def rename_wiki_folder(
    folder_id: int,
    payload: WikiFolderUpdate,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    folder = _get_owned_folder(db, folder_id, user)
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name cannot be empty")
    folder.name = name
    db.commit()
    return {"id": folder.id, "name": folder.name}


@router.delete("/wiki-folders/{folder_id}")
def delete_wiki_folder(
    folder_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    """Deleting a folder does not delete its entries - they just become
    Uncategorized (folder_id = None)."""
    folder = _get_owned_folder(db, folder_id, user)
    for e in db.query(models.WikiEntry).filter(models.WikiEntry.folder_id == folder_id).all():
        e.folder_id = None
    db.delete(folder)
    db.commit()
    return {"ok": True}
