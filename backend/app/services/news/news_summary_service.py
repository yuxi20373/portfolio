"""Turns a scraped article's plain text into the Markdown digest shown in
the News view, and translates the title to Traditional Chinese (source
sites may publish in Simplified Chinese or other languages). Reuses the
same one-shot LLM dispatcher as the rest of the app's background services
(title generation, wiki summarization, etc.) - see
app/integrations/llm_client.py."""

from ...integrations.llm_client import simple_completion
from ...prompts.news_summary import SUMMARY_SYSTEM_PROMPT
from ...utils.json_extract import extract_json_and_body


def summarize_article(title: str, content_text: str) -> tuple[str, str]:
    """Returns (traditional_chinese_title, summary_md)."""
    content_text = (content_text or "")[:8000]  # keep the prompt bounded; article bodies rarely exceed this
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"標題：{title}\n\n內文：\n{content_text}",
        },
    ]
    raw = simple_completion(messages, temperature=0.3)
    data, summary_md = extract_json_and_body(raw)
    summary_md = summary_md.strip()
    if not summary_md:
        raise ValueError("model response was missing the summary body")
    translated_title = (data.get("title") or title).strip()
    return translated_title, summary_md
