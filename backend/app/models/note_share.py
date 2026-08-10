from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint

from ..database import Base


class NoteShare(Base):
    """One user sharing a Note with another (see routers/notes.py's
    /{note_id}/share, /shared, /shared/recent-targets). Read-only for the
    recipient - sharing a note doesn't let them edit/delete it, only view it
    (see _get_viewable_note vs _get_owned_note in the router). The note's
    owner is Note.user_id, not stored again here.

    Unique on (note_id, shared_with_user_id) - re-sharing the same note with
    the same person is a no-op (upserted, not duplicated) rather than an
    error, since the frontend's "share" action doesn't distinguish
    first-time vs repeat shares."""

    __tablename__ = "note_shares"
    __table_args__ = (UniqueConstraint("note_id", "shared_with_user_id", name="uq_note_share_target"),)

    id = Column(Integer, primary_key=True)
    # ondelete=CASCADE - deleting a note must also drop its shares, or the
    # delete fails with a ForeignKeyViolation the moment a shared note gets
    # deleted (this bit a live account the day this was shipped).
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
