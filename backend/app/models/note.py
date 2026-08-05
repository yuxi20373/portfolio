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
    color: one of "peach" / "sage" / "sky" (see the NOTE_COLORS swatches in
      CalendarView.js/NotesView.js), or None - purely a display tint, no
      other meaning.
    is_favorited: surfaced via the calendar page's sidebar "Favorites" list
      (grouped by date) - see routers/notes.py's /favorite endpoint.

    user_id: notes are entirely private per account (see app/models/auth.py)."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    content = Column(Text)  # raw Markdown
    tags = Column(JSON, default=list)
    color = Column(String(20), nullable=True)
    is_favorited = Column(Boolean, default=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NoteTemplate(Base):
    """A reusable Markdown skeleton, picked from a dropdown when adding a
    note from the calendar (see routers/notes.py, the standalone Notes page
    is where these get created/renamed/deleted). Purely a content prefill -
    applying one doesn't link the resulting note back to it.

    tags: applied to the note's own tags alongside the content whenever this
    template is picked (see CalendarView.js's applyNoteTemplate)."""

    __tablename__ = "note_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    content = Column(Text)  # raw Markdown
    tags = Column(JSON, default=list)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MemoItem(Base):
    """A quick scratchpad checklist item, shown in the standalone Notes
    page's sidebar (see routers/memos.py) - separate from the full Note
    model above, this is meant for short one-line reminders you tick off,
    not Markdown content."""

    __tablename__ = "memo_items"

    id = Column(Integer, primary_key=True)
    text = Column(String(500))
    done = Column(Boolean, default=False)
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
