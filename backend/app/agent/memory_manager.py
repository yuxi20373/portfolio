"""Keeps each session's LLM-visible context small by folding older turns
into a rolling summary instead of always resending the full raw history.

Raw messages are always kept in the database (needed for the calendar view,
wiki summarization, exporting, etc). This only controls what actually gets
sent to the model on each turn - it's the difference between "the whole
transcript" and "a recap + the last few turns", which is where the token
savings come from on long-running sessions.
"""

from sqlalchemy.orm import Session as DBSession

from .. import models
from ..config import settings
from ..integrations.llm_client import simple_completion
from ..prompts.chat_memory import MEMORY_UPDATE_SYSTEM_PROMPT


def get_context_messages(db: DBSession, session: models.ChatSession) -> list[dict]:
    """Build the message list to hand to the agent for this turn: an optional
    memory-summary message, followed by the recent raw messages. Call this
    BEFORE persisting the new user message, so it isn't duplicated."""
    all_messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )

    _maybe_compact(db, session, all_messages)

    cutoff_id = session.summarized_up_to_message_id or 0
    recent = [m for m in all_messages if m.id > cutoff_id]

    context = []
    if session.memory_summary:
        context.append(
            {
                "role": "system",
                "content": f"Summary of the earlier part of this conversation:\n{session.memory_summary}",
            }
        )
    context += [{"role": m.role, "content": m.content} for m in recent]
    return context


def _maybe_compact(db: DBSession, session: models.ChatSession, all_messages: list[models.ChatMessage]):
    cutoff_id = session.summarized_up_to_message_id or 0
    unsummarized = [m for m in all_messages if m.id > cutoff_id]

    if len(unsummarized) <= settings.memory_compact_trigger:
        return

    # keep the most recent N verbatim, fold everything older into the summary
    to_fold = unsummarized[: -settings.memory_recent_window] if settings.memory_recent_window > 0 else unsummarized
    if not to_fold:
        return

    transcript = "\n".join(f"{m.role}: {m.content}" for m in to_fold)
    prior_summary = session.memory_summary or "(none yet)"

    try:
        updated = simple_completion(
            messages=[
                {"role": "system", "content": MEMORY_UPDATE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Current summary:\n{prior_summary}\n\nNew messages to fold in:\n{transcript}",
                },
            ],
            temperature=0.2,
        )
    except Exception:
        return  # if compaction fails, just leave the raw history as-is for this turn

    session.memory_summary = updated.strip()
    session.summarized_up_to_message_id = to_fold[-1].id
    db.commit()
