"""Creates or updates a single wiki entry from web search results, driven
entirely by the user: a keyword (the terms they'd type into a search
engine) and a question describing what they actually want to know and keep
in the wiki. This is now the primary way entries get added - there is no
more automatic whole-conversation summarization. The user always gives at
least a rough topic; this writes it up properly using the entry_type
section templates.

This is strictly an ADD/CONSOLIDATE operation: when updating an existing
entry, none of its existing content is ever removed or shortened here -
new information is merged in. Trimming/removing content is only done by
wiki_adjust_service.py, and only on an explicit user instruction.
"""

import json
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from ... import models
from ...integrations.llm_client import simple_completion
from ...prompts.wiki_search import MERGE_ADDITIVE_SYSTEM_PROMPT, SEARCH_WRITE_SYSTEM_PROMPT
from ...utils.json_extract import extract_json_and_body
from ...agent.tools.web_search import web_search as web_search_tool
from .entry_types import ENTRY_TYPE_TEMPLATES


def get_existing_titles_context(db: DBSession, user_id: int, limit: int = 300):
    entries = (
        db.query(models.WikiEntry)
        .filter(models.WikiEntry.user_id == user_id)
        .order_by(models.WikiEntry.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [{"title": e.title, "entry_type": e.entry_type, "summary": e.summary} for e in entries]


def create_or_update_via_search(db: DBSession, user_id: int, keyword: str, question: str) -> models.WikiEntry:
    keyword = (keyword or "").strip()
    question = (question or "").strip()
    if not keyword or not question:
        raise ValueError("Both a keyword and a question are required.")

    search_results = web_search_tool.invoke({"query": keyword})
    existing = get_existing_titles_context(db, user_id)

    user_prompt = (
        f"Search keyword used: {keyword}\n"
        f"User's question: {question}\n\n"
        f"Existing entries (for you to judge duplicates):\n{json.dumps(existing, ensure_ascii=False)}\n\n"
        f"Web search results:\n{search_results}\n\n"
        "Produce the response in the exact format instructed."
    )

    raw = simple_completion(
        messages=[
            {"role": "system", "content": SEARCH_WRITE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    data, content = extract_json_and_body(raw)
    if isinstance(data, list):  # be forgiving if the model wraps it in an array anyway
        data = data[0] if data else {}

    title = (data.get("title") or question[:60]).strip()
    entry_type = data.get("entry_type")
    if entry_type not in ENTRY_TYPE_TEMPLATES:
        entry_type = "general"

    existing_entry = (
        db.query(models.WikiEntry).filter(models.WikiEntry.user_id == user_id, models.WikiEntry.title == title).first()
    )
    if existing_entry:
        merged_content = simple_completion(
            messages=[
                {"role": "system", "content": MERGE_ADDITIVE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Existing content:\n{existing_entry.content}\n\n"
                        f"New draft to integrate (from a web search answering: {question}):\n{content}"
                    ),
                },
            ],
            temperature=0.3,
        )
        existing_entry.entry_type = entry_type
        existing_entry.summary = data.get("summary", existing_entry.summary)
        existing_entry.content = merged_content.strip()
        existing_entry.tags = list(set(existing_entry.tags or []) | set(data.get("tags", [])))
        existing_entry.related_titles = list(set(existing_entry.related_titles or []) | set(data.get("related", [])))
        existing_entry.updated_at = datetime.utcnow()
        entry = existing_entry
    else:
        entry = models.WikiEntry(
            title=title,
            entry_type=entry_type,
            summary=data.get("summary", ""),
            content=content,
            tags=data.get("tags", []),
            related_titles=data.get("related", []),
            user_id=user_id,
        )
        db.add(entry)

    db.commit()
    db.refresh(entry)
    return entry
