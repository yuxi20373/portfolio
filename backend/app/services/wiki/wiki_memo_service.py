"""Turns a quick memo/note (see routers/memos.py's add_to_wiki flag) into a
proper wiki entry via LLM curation - same create-or-update-additively
pattern as wiki_search_service.py, but the source material is the memo's
own text instead of live web search results (no web search involved here,
so this is faster and doesn't depend on the flaky keyless DuckDuckGo
fallback).
"""

import json
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from ... import models
from ...integrations.llm_client import simple_completion
from ...prompts.wiki_memo import MEMO_MERGE_ADDITIVE_SYSTEM_PROMPT, MEMO_WRITE_SYSTEM_PROMPT
from ...utils.json_extract import extract_json_and_body
from .entry_types import ENTRY_TYPE_TEMPLATES
from .wiki_search_service import get_existing_titles_context


def absorb_memo_into_wiki(db: DBSession, user_id: int, memo_text: str) -> models.WikiEntry:
    memo_text = (memo_text or "").strip()
    if not memo_text:
        raise ValueError("Memo text is required.")

    existing = get_existing_titles_context(db, user_id)

    user_prompt = (
        f"Memo:\n{memo_text}\n\n"
        f"Existing entries (for you to judge duplicates):\n{json.dumps(existing, ensure_ascii=False)}\n\n"
        "Produce the response in the exact format instructed."
    )

    raw = simple_completion(
        messages=[
            {"role": "system", "content": MEMO_WRITE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    data, content = extract_json_and_body(raw)
    if isinstance(data, list):  # be forgiving if the model wraps it in an array anyway
        data = data[0] if data else {}

    title = (data.get("title") or memo_text[:60]).strip()
    entry_type = data.get("entry_type")
    if entry_type not in ENTRY_TYPE_TEMPLATES:
        entry_type = "general"

    existing_entry = (
        db.query(models.WikiEntry).filter(models.WikiEntry.user_id == user_id, models.WikiEntry.title == title).first()
    )
    if existing_entry:
        merged_content = simple_completion(
            messages=[
                {"role": "system", "content": MEMO_MERGE_ADDITIVE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Existing content:\n{existing_entry.content}\n\n"
                        f"New draft to integrate (from a memo):\n{content}"
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
