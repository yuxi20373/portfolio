import secrets
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from ..database import Base


def _generate_token() -> str:
    return secrets.token_hex(32)


class User(Base):
    """A login account. Each account's chat sessions / wiki entries / notes
    are entirely private to that account (see the user_id column on those
    models). There is no self-serve signup - accounts are created directly
    against the database, see backend/scripts/create_user.py."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(60), nullable=False)  # bcrypt hash - always 60 chars
    created_at = Column(DateTime, default=datetime.utcnow)

    tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")


class AuthToken(Base):
    """A logged-in session's bearer token. Deliberately has no expiry/TTL -
    per product decision there's no auto-logout, so a token stays valid
    until the user explicitly logs out (DELETE /api/auth/logout), which
    just deletes this row. See app/auth.py."""

    __tablename__ = "auth_tokens"

    token = Column(String(64), primary_key=True, default=_generate_token)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="tokens")
