from typing import Optional

from pydantic import BaseModel


class WikiEntryUpdate(BaseModel):
    """Direct, manual edit of a wiki entry - no LLM involved. Every field is
    optional so the frontend can send only what changed (e.g. just
    folder_id when moving an entry)."""

    title: Optional[str] = None
    entry_type: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    folder_id: Optional[int] = None
    clear_folder: bool = False  # set true to explicitly move the entry to "Uncategorized"


class WikiFolderCreate(BaseModel):
    name: str


class WikiFolderUpdate(BaseModel):
    name: str
