import json

from sqlalchemy.orm import Session as DBSession

from ... import models
from ...integrations.llm_client import simple_completion
from ...prompts.chat_search import SEARCH_SYSTEM_PROMPT
from ...utils.json_extract import extract_json


def semantic_search_sessions(db: DBSession, user_id: int, query: str, limit_sessions: int = 200):
    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user_id)
        .order_by(models.ChatSession.last_message_at.desc())
        .limit(limit_sessions)
        .all()
    )
    if not sessions:
        return []

    corpus = []
    for s in sessions:
        first_messages = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.session_id == s.id)
            .order_by(models.ChatMessage.created_at.asc())
            .limit(4)
            .all()
        )
        snippet = " ".join(m.content for m in first_messages)[:300]
        corpus.append({"id": s.id, "title": s.title, "snippet": snippet})

    user_prompt = f"Query: {query}\n\nSessions:\n{json.dumps(corpus, ensure_ascii=False)}"

    raw = simple_completion(
        messages=[
            {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )

    try:
        ids = extract_json(raw)
        return [int(i) for i in ids]
    except Exception:
        return []
