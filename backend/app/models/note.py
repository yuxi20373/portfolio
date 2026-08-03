from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from ..database import Base


class Note(Base):
    """A free-form Markdown note, anchored to whichever calendar day it was
    created for (see routers/notes.py - the frontend lets you attach a note
    to the currently-selected calendar day, defaulting to today).

    user_id: notes are entirely private per account (see app/models/auth.py)."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    content = Column(Text)  # raw Markdown
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
