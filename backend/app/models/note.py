from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey

from ..database import Base


class Note(Base):
    """A free-form Markdown note, anchored to whichever calendar day it was
    created for (see routers/notes.py - the frontend lets you attach a note
    to the currently-selected calendar day, defaulting to today).

    tags: plain string labels (like WikiEntry.tags), optionally picked from
      the user's saved NoteTag registry below, but not enforced against it -
      free text is fine.
    is_favorited: surfaced via the calendar page's sidebar "Favorites" list
      (grouped by date) - see routers/notes.py's /favorite endpoint.

    user_id: notes are entirely private per account (see app/models/auth.py)."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    content = Column(Text)  # raw Markdown
    tags = Column(JSON, default=list)
    is_favorited = Column(Boolean, default=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NoteTemplate(Base):
    """A reusable Markdown skeleton, picked from a dropdown when adding a
    note from the calendar (see routers/notes.py, the standalone Notes page
    is where these get created/renamed/deleted). Purely a content prefill -
    applying one doesn't link the resulting note back to it."""

    __tablename__ = "note_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    content = Column(Text)  # raw Markdown
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NoteTag(Base):
    """A saved, reusable tag name, managed from the standalone Notes page.
    Note.tags stores plain strings and isn't a foreign key into this table -
    this is just the "create a tag" registry for autocomplete/browsing, not
    an enforced taxonomy."""

    __tablename__ = "note_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
