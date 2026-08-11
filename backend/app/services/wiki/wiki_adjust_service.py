"""Lets the user tweak an existing wiki entry's headings/content via a
conversational, propose-then-confirm flow:

- propose_adjustment() runs a web search for the entry's topic + the user's
  instruction, then drafts a revision (informed by those results) WITHOUT
  saving it, optionally starting from a not-yet-saved draft from an earlier
  round in the same session (so the user can keep refining before
  committing anything).
- apply_adjustment() commits an already-approved draft to the database.

Like wiki_search_service.py, this now defaults to additive edits - existing
content should be kept and supplemented rather than removed. Unlike that
service, this one CAN still remove/shorten content, but only when the
user's instruction explicitly asks for it; anything else (expand, add
detail, refresh with current info, reorganize) must not drop existing
material. See ADJUST_SYSTEM_PROMPT for the exact policy given to the model.
"""

from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from ... import models
from ...integrations.llm_client import simple_completion
from ...prompts.wiki_adjust import ADJUST_SYSTEM_PROMPT
from ...utils.json_extract import extract_json_and_body
from ...agent.tools.web_search import web_search as web_search_tool


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

    # 用條目標題+使用者指令當搜尋詞,補充最新/更詳細的資訊給模型參考 - 模型
    # 不是照單全收,只在跟指令相關時才會拿來用(見 ADJUST_SYSTEM_PROMPT)。
    # 沒設 TAVILY_API_KEY 時走的是免 key 的 DuckDuckGo 備援,偶爾會逾時/被
    # 限流拋例外 - 不能讓搜尋失敗整個搞垮 adjust(之前就是這樣:整支 500,
    # 前端沒有錯誤處理,使用者打的字就跟著憑空消失,看起來像抽屜被收起來)。
    try:
        search_results = web_search_tool.invoke({"query": f"{entry.title} {instruction}"})
    except Exception:
        search_results = "(web search unavailable right now - proceeding without it)"

    user_prompt = (
        f"Entry title: {entry.title}\n"
        f"Entry type: {entry.entry_type}\n"
        f"Current content:\n{content}\n\n"
        f"User's instruction:\n{instruction}\n\n"
        f"Web search results (for background/supplementary info - only use what's actually relevant to the instruction):\n{search_results}"
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
