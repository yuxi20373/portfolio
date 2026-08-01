from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..database import get_db
from ..schemas.chat import SessionCreate, SessionUpdate, SessionOut, MessageOut, ChatRequest
from ..services.chat.chat_service import get_or_create_session, process_chat_message

router = APIRouter(prefix="/api/sessions", tags=["chat"])


@router.post("", response_model=SessionOut)
def create_session(payload: SessionCreate, db: DBSession = Depends(get_db)):
    s = models.ChatSession(title=payload.title or "New Conversation", channel="web")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("", response_model=list[SessionOut])
def list_sessions(db: DBSession = Depends(get_db)):
    return db.query(models.ChatSession).order_by(models.ChatSession.last_message_at.desc()).all()


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def get_messages(session_id: int, db: DBSession = Depends(get_db)):
    s = db.query(models.ChatSession).get(session_id)
    if not s:
        raise HTTPException(404, "session not found")
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )


@router.patch("/{session_id}", response_model=SessionOut)
def rename_session(session_id: int, payload: SessionUpdate, db: DBSession = Depends(get_db)):
    s = db.query(models.ChatSession).get(session_id)
    if not s:
        raise HTTPException(404, "session not found")
    title = payload.title.strip()
    if not title:
        raise HTTPException(400, "title cannot be empty")
    s.title = title
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{session_id}")
def delete_session(session_id: int, db: DBSession = Depends(get_db)):
    s = db.query(models.ChatSession).get(session_id)
    if not s:
        raise HTTPException(404, "session not found")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/chat", response_model=MessageOut)
def chat(session_id: int, payload: ChatRequest, db: DBSession = Depends(get_db)):
    session = get_or_create_session(db, channel="web", session_id=session_id)
    process_chat_message(db, session, payload.message)
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.created_at.desc())
        .first()
    )
