from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from ..database import Base


class CustomEmoji(Base):
    """A user-uploaded :shortcode: emoji (see routers/emoji.py), resized down
    to a small square PNG server-side on upload and stored directly in the
    database as base64 - Render's free tier has no persistent disk, so a
    plain uploads/ folder on the filesystem would vanish on every deploy/
    restart. The images are tiny post-resize, so storing them as a DB
    column instead of wiring up external object storage (S3 etc.) is the
    simplest thing that actually survives deploys.

    shortcode is not globally unique - each user has their own namespace,
    and a re-upload of the same shortcode replaces the existing one (see
    upload_emoji)."""

    __tablename__ = "custom_emoji"

    id = Column(Integer, primary_key=True)
    shortcode = Column(String(50), nullable=False, index=True)
    image_data = Column(Text, nullable=False)  # base64-encoded PNG
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
