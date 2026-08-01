"""Lets the user tweak an existing wiki entry's headings/content via a
conversational, propose-then-confirm flow:

- propose_adjustment() drafts a revision based on a natural-language
  instruction WITHOUT saving it, optionally starting from a not-yet-saved
  draft from an earlier round in the same session (so the user can keep
  refining before committing anything).
- apply_adjustment() commits an already-approved draft to the database.

Kept separate from wiki_search_service.py, which is strictly additive -
this is the only path allowed to remove or restructure existing content,
and only because the user explicitly asked for it.
"""

from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from ... import models
from ...integrations.llm_client import simple_completion
from ...prompts.wiki_adjust import ADJUST_SYSTEM_PROMPT
from ...utils.json_extract import extract_json_and_body


def propose_adjustment(
    db: DBSession,
    entry: models.WikiEntry,
    instruction: str,
    base_content: str = None,
    base_summary: str = None,
) -> dict:
    """Draft a revision without saving it, so the frontend can show a
    preview the user approves, discards, or keeps refining."""
    instruction = (instruction or "").strip()
    if not instruction:
        raise ValueError("An instruction describing the desired change is required.")

    content = base_content if base_content is not None else entry.content
    summary = base_summary if base_summary is not None else entry.summary

    user_prompt = (
        f"Entry title: {entry.title}\n"
        f"Entry type: {entry.entry_type}\n"
        f"Current content:\n{content}\n\n"
        f"User's instruction:\n{instruction}"
    )

    raw = simple_completion(
        messages=[
            {"role": "system", "content": ADJUST_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    data, new_content = extract_json_and_body(raw)
    return {
        "summary": (data.get("summary") or summary or "").strip(),
        "content": (new_content or content).strip(),
    }


def apply_adjustment(db: DBSession, entry: models.WikiEntry, summary: str, content: str) -> models.WikiEntry:
    """Commit an already-approved draft (from propose_adjustment) to the entry."""
    entry.content = content
    if summary:
        entry.summary = summary
    entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return entry
