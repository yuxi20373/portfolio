"""Lets the deep agent create or update a wiki entry directly from the
conversation, when the user explicitly asks to save/update something in
the knowledge base (see the paired skill:
app/agent/skills/wiki-management/SKILL.md for when/how this should be
used).

This intentionally does NOT make its own LLM call - the agent invoking it
is already looking at the conversation, so it writes the structured entry
itself (following the section-template rules taught in the skill) and this
tool just persists it, merging into an existing entry with the same title
if one exists. That keeps this fast (no extra round-trip) and consistent
with how wiki_search_service.py structures entries.

Runs its own short-lived DB session (rather than reusing a request-scoped
one) since tool calls happen inside the LangGraph agent loop, outside of
any FastAPI request/response cycle.
"""

from datetime import datetime
from typing import Optional

from langchain_core.tools import tool

from ...database import SessionLocal
from ... import models
from ...services.wiki.entry_types import ENTRY_TYPE_TEMPLATES


@tool
def update_wiki(title: str, entry_type: str, summary: str, content: str, tags: Optional[list[str]] = None) -> str:
    """Create a new wiki entry, or update an existing one with the same
    title, in the long-term knowledge base. Use this ONLY when the user
    explicitly asks to save, add, record, or update something in the wiki
    / knowledge base. Do not call this just because an interesting topic
    came up in conversation - only on explicit request.

    Args:
        title: concise, unique entry title.
        entry_type: one of "concept", "technology", "organism", "person",
            "event", "place", "general" - pick the closest match.
        summary: a 1-2 sentence summary of the entry.
        content: the full entry content in Markdown - a short lead
            paragraph with no heading, followed by "## Heading" sections
            drawn only from that entry_type's recommended section list.
        tags: a short list of keyword tags.
    """
    if entry_type not in ENTRY_TYPE_TEMPLATES:
        entry_type = "general"

    title = title.strip()
    if not title:
        return "Could not save: no title was given."

    db = SessionLocal()
    try:
        existing = db.query(models.WikiEntry).filter(models.WikiEntry.title == title).first()
        if existing:
            existing.entry_type = entry_type
            existing.summary = summary
            existing.content = content
            existing.tags = list(set(existing.tags or []) | set(tags or []))
            existing.updated_at = datetime.utcnow()
            db.commit()
            return f'Updated the existing wiki entry "{title}".'

        entry = models.WikiEntry(
            title=title,
            entry_type=entry_type,
            summary=summary,
            content=content,
            tags=tags or [],
            related_titles=[],
        )
        db.add(entry)
        db.commit()
        return f'Created a new wiki entry "{title}".'
    finally:
        db.close()
