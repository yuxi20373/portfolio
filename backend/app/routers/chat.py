from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db
from ..agent import model_catalog
from ..schemas.chat import SessionCreate, SessionUpdate, SessionOut, MessageOut, ChatRequest
from ..services.chat.chat_service import get_or_create_session, process_chat_message

router = APIRouter(prefix="/api/sessions", tags=["chat"])


@router.post("", response_model=SessionOut)
def create_session(
    payload: SessionCreate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    s = models.ChatSession(title=payload.title or "New Conversation", channel="web", user_id=user.id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("", response_model=list[SessionOut])
def list_sessions(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.last_message_at.desc())
        .all()
    )


def _get_owned_session(db: DBSession, session_id: int, user: models.User) -> models.ChatSession:
    s = db.query(models.ChatSession).get(session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "session not found")
    return s


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def get_messages(
    session_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _get_owned_session(db, session_id, user)
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: int,
    payload: SessionUpdate,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    s = _get_owned_session(db, session_id, user)

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(400, "title cannot be empty")
        s.title = title

    if payload.model is not None:
        if not model_catalog.is_valid_model(payload.model):
            raise HTTPException(400, "unknown model")
        s.model_name = payload.model

    db.commit()
    db.refresh(s)
    return s


@router.delete("/{session_id}")
def delete_session(
    session_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    s = _get_owned_session(db, session_id, user)
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/chat", response_model=MessageOut)
def chat(
    session_id: int,
    payload: ChatRequest,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    try:
        session = get_or_create_session(db, channel="web", session_id=session_id, user_id=user.id)
    except ValueError:
        raise HTTPException(404, "session not found")
    process_chat_message(db, session, payload.message)
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.created_at.desc())
        .first()
    )
