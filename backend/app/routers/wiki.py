from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from datetime import datetime

from .. import models
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


@router.get("/wiki")
def list_wiki(db: DBSession = Depends(get_db)):
    entries = db.query(models.WikiEntry).order_by(models.WikiEntry.updated_at.desc()).all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "entry_type": e.entry_type,
            "summary": e.summary,
            "tags": e.tags,
            "folder_id": e.folder_id,
            "updated_at": e.updated_at,
        }
        for e in entries
    ]


@router.get("/wiki/{entry_id}")
def get_wiki_entry(entry_id: int, db: DBSession = Depends(get_db)):
    e = db.query(models.WikiEntry).get(entry_id)
    if not e:
        raise HTTPException(404, "not found")

    related = []
    for title in e.related_titles or []:
        t = db.query(models.WikiEntry).filter(models.WikiEntry.title == title).first()
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
        "updated_at": e.updated_at,
        "related": related,
    }


@router.patch("/wiki/{entry_id}")
def update_wiki_entry(entry_id: int, payload: WikiEntryUpdate, db: DBSession = Depends(get_db)):
    """Direct manual edit (title/content/tags/etc) and/or moving the entry
    into a different folder - no LLM involved at all."""
    e = db.query(models.WikiEntry).get(entry_id)
    if not e:
        raise HTTPException(404, "not found")

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
        folder = db.query(models.WikiFolder).get(payload.folder_id)
        if not folder:
            raise HTTPException(404, "folder not found")
        e.folder_id = folder.id

    e.updated_at = datetime.utcnow()
    db.commit()
    return get_wiki_entry(entry_id, db)


@router.delete("/wiki/{entry_id}")
def delete_wiki_entry(entry_id: int, db: DBSession = Depends(get_db)):
    e = db.query(models.WikiEntry).get(entry_id)
    if not e:
        raise HTTPException(404, "not found")
    db.delete(e)
    db.commit()
    return {"ok": True}


@router.post("/wiki/search")
def search_into_wiki(payload: WikiSearchRequest, db: DBSession = Depends(get_db)):
    try:
        entry = create_or_update_via_search(db, payload.keyword, payload.question)
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    return get_wiki_entry(entry.id, db)


@router.post("/wiki/{entry_id}/adjust/preview")
def preview_wiki_adjustment(entry_id: int, payload: WikiAdjustPreviewRequest, db: DBSession = Depends(get_db)):
    e = db.query(models.WikiEntry).get(entry_id)
    if not e:
        raise HTTPException(404, "not found")
    try:
        return propose_adjustment(db, e, payload.instruction, payload.base_content, payload.base_summary)
    except ValueError as ex:
        raise HTTPException(400, str(ex))


@router.post("/wiki/{entry_id}/adjust/apply")
def apply_wiki_adjustment(entry_id: int, payload: WikiAdjustApplyRequest, db: DBSession = Depends(get_db)):
    e = db.query(models.WikiEntry).get(entry_id)
    if not e:
        raise HTTPException(404, "not found")
    apply_adjustment(db, e, payload.summary, payload.content)
    return get_wiki_entry(entry_id, db)


# ---------------- Folders (user-created, manual organization only) ----------------


@router.get("/wiki-folders")
def list_wiki_folders(db: DBSession = Depends(get_db)):
    folders = db.query(models.WikiFolder).order_by(models.WikiFolder.name.asc()).all()
    return [{"id": f.id, "name": f.name} for f in folders]


@router.post("/wiki-folders")
def create_wiki_folder(payload: WikiFolderCreate, db: DBSession = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name cannot be empty")
    folder = models.WikiFolder(name=name)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "name": folder.name}


@router.patch("/wiki-folders/{folder_id}")
def rename_wiki_folder(folder_id: int, payload: WikiFolderUpdate, db: DBSession = Depends(get_db)):
    folder = db.query(models.WikiFolder).get(folder_id)
    if not folder:
        raise HTTPException(404, "not found")
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name cannot be empty")
    folder.name = name
    db.commit()
    return {"id": folder.id, "name": folder.name}


@router.delete("/wiki-folders/{folder_id}")
def delete_wiki_folder(folder_id: int, db: DBSession = Depends(get_db)):
    """Deleting a folder does not delete its entries - they just become
    Uncategorized (folder_id = None)."""
    folder = db.query(models.WikiFolder).get(folder_id)
    if not folder:
        raise HTTPException(404, "not found")
    for e in db.query(models.WikiEntry).filter(models.WikiEntry.folder_id == folder_id).all():
        e.folder_id = None
    db.delete(folder)
    db.commit()
    return {"ok": True}
