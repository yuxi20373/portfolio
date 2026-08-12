import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..agent.test_agent.tools import list_available_identities
from ..auth import get_current_user
from ..database import get_db
from ..agent import model_catalog
from ..schemas.chat import (
    AvailableIdentity,
    ChatRequest,
    MessageOut,
    SessionCreate,
    SessionOut,
    SessionUpdate,
    TestAgentSessionCreate,
)
from ..services.chat.chat_service import get_or_create_session, process_chat_message

router = APIRouter(prefix="/api/sessions", tags=["chat"])


class FavoriteUpdate(BaseModel):
    favorited: bool


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


# 靜態路徑要放在 /{session_id}/... 這種動態路徑之前註冊 - 這兩支都是
# /api/sessions/test-agent/... 開頭,不然會被 /{session_id} 那個 pattern
# 誤吃(FastAPI 照註冊順序比對路由)。

@router.get("/test-agent/identities", response_model=list[AvailableIdentity])
def get_test_agent_identities():
    """給前端「測試 Agent」頁面的身分選擇器用 - 從硬碟上實際存在的
    skill 資料夾掃出來的(見 app/agent/test_agent/tools.py 的
    _discover_identities),新增一個 skill 資料夾就會自動出現,不用改
    這支程式。"""
    return list_available_identities()


@router.post("/test-agent", response_model=SessionOut, status_code=201)
def create_test_agent_session(
    payload: TestAgentSessionCreate, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    """建立一個已經設定好 fab/function 身分的 test_agent session - 跟一般
    session 不同,身分是建立當下就決定的,不是聊天中用指令切換(見
    chat_service.py 的 EXPERIMENTAL_AGENT_COMMANDS 說明)。"""
    if not payload.identities:
        raise HTTPException(400, "at least one identity is required")
    available = {a["fab"]: a["functions"] for a in list_available_identities()}
    for identity in payload.identities:
        if identity.fab not in available or identity.function not in available[identity.fab]:
            raise HTTPException(400, f"unknown identity: {identity.fab}/{identity.function}")

    default_title = "、".join(f"{i.fab}/{i.function}" for i in payload.identities)
    s = models.ChatSession(
        title=payload.title or default_title,
        channel="web",
        user_id=user.id,
        experimental_agent="test_agent",
        test_agent_identities_json=json.dumps([[i.fab, i.function] for i in payload.identities]),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


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


@router.patch("/{session_id}/favorite", response_model=SessionOut)
def update_session_favorite(
    session_id: int,
    payload: FavoriteUpdate,
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    s = _get_owned_session(db, session_id, user)
    s.is_favorited = payload.favorited
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
