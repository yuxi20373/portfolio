from ...integrations.llm_client import simple_completion
from ...prompts.chat_title import TITLE_SYSTEM_PROMPT


def generate_title(user_message: str, assistant_reply: str) -> str:
    """Best-effort short title generation. Falls back to a truncated user message on failure."""
    try:
        raw = simple_completion(
            messages=[
                {"role": "system", "content": TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": f"User: {user_message}\nAssistant: {assistant_reply}"},
            ],
            temperature=0.3,
        )
        title = raw.strip().strip('"').strip()
        return title[:60] if title else user_message[:40]
    except Exception:
        return user_message[:40]
