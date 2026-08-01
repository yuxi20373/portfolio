from datetime import datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from ... import models
from ...config import settings
from ...agent import memory_manager
from ...agent import runner as agent_runner
from ...integrations import langfuse_client
from .title_service import generate_title


def get_or_create_session(
    db: DBSession,
    channel: str,
    external_user_id: str = None,
    session_id: int = None,
) -> models.ChatSession:
    """
    Resolve which session (= scope of short-term memory) this message belongs to.

    - web: if a session_id is given, use it directly; otherwise start a new one.
    - line (or any channel without an explicit session boundary): reuse the
      user's most recent session if they spoke recently (within
      SESSION_TIMEOUT_MINUTES); otherwise start a new session, so context
      doesn't grow forever.
    """
    if session_id is not None:
        s = db.query(models.ChatSession).get(session_id)
        if s:
            return s

    if external_user_id:
        cutoff = datetime.utcnow() - timedelta(minutes=settings.session_timeout_minutes)
        s = (
            db.query(models.ChatSession)
            .filter(
                models.ChatSession.channel == channel,
                models.ChatSession.external_user_id == external_user_id,
                models.ChatSession.is_open == True,  # noqa: E712
                models.ChatSession.last_message_at >= cutoff,
            )
            .order_by(models.ChatSession.last_message_at.desc())
            .first()
        )
        if s:
            return s

    s = models.ChatSession(title="New Conversation", channel=channel, external_user_id=external_user_id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def process_chat_message(db: DBSession, session: models.ChatSession, user_text: str) -> str:
    """Run one chat turn: build compacted context, persist the user message,
    call the deep agent, persist the reply, and auto-title on the first
    exchange. Sessions are fully isolated from each other via session_id."""
    is_first_message = (
        db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session.id).count() == 0
    )

    # Build context from EXISTING history first, so the new user message
    # below isn't double-counted when the agent is called.
    context_messages = memory_manager.get_context_messages(db, session)

    user_msg = models.ChatMessage(session_id=session.id, role="user", content=user_text)
    db.add(user_msg)
    db.commit()

    handler, run_id = langfuse_client.new_handler_and_run_id()
    reply_text, usage = agent_runner.run_turn(
        context_messages, user_text, callbacks=[handler] if handler else None, run_id=run_id
    )

    model_name = usage.get("model")
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    # Cost comes from Langfuse (not computed locally) - best-effort, may stay
    # None if Langfuse isn't configured or the trace isn't ready yet.
    cost_usd = None
    if run_id:
        lf_usage = langfuse_client.fetch_usage(str(run_id))
        if lf_usage:
            cost_usd = lf_usage.get("cost_usd")
            input_tokens = lf_usage.get("input_tokens") or input_tokens
            output_tokens = lf_usage.get("output_tokens") or output_tokens
            model_name = lf_usage.get("model") or model_name

    assistant_msg = models.ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply_text,
        model=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )
    db.add(assistant_msg)

    if is_first_message and session.title in (None, "", "New Conversation"):
        session.title = generate_title(user_text, reply_text)

    session.last_message_at = datetime.utcnow()
    db.commit()

    return reply_text
