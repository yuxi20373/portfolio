"""Login/auth primitives: bcrypt password hashing, and opaque bearer tokens
with no expiry (see app/models/auth.py:AuthToken - product decision was no
auto-logout, so a token is valid until the user explicitly logs out).

get_current_user is the FastAPI dependency every user-data router (chat,
wiki, notes, calendar, search) uses to identify who's asking and scope
their queries to that account. There's no self-serve signup - accounts are
created directly against the database, see backend/scripts/create_user.py -
so there's no register endpoint here, only login/logout/me
(app/routers/auth.py)."""

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as DBSession

from . import models
from .database import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(db: DBSession, user: models.User) -> str:
    auth_token = models.AuthToken(user_id=user.id)
    db.add(auth_token)
    db.commit()
    db.refresh(auth_token)
    return auth_token.token


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: DBSession = Depends(get_db),
) -> models.User:
    if not credentials:
        raise HTTPException(401, "not authenticated")
    auth_token = db.query(models.AuthToken).get(credentials.credentials)
    if not auth_token:
        raise HTTPException(401, "invalid or expired token")
    return auth_token.user
