"""Langfuse integration: attaches a LangChain callback handler to every
deep-agent turn for tracing, and best-effort fetches that turn's
Langfuse-calculated cost back right after the call.

This is intentionally best-effort, not guaranteed: Langfuse ingests traces
asynchronously (batched in the background), so even after flush() there
can be a short delay before a trace's cost is queryable via the API. We
retry a few times with a short sleep and give up gracefully rather than
hanging the chat response - if it doesn't show up in time, cost displays
as "N/A" in the UI (tokens still show either way, since those come
straight from the LLM response, not from Langfuse).

Also note: Langfuse can only calculate a dollar cost for a model it has
pricing data for. Common providers (OpenAI, Anthropic, etc.) are built in;
Groq models may need a custom model definition added in your Langfuse
project settings (Settings -> Models) with matching usage-unit keys,
otherwise cost will stay "N/A" even though tracing itself works fine.

The exact shape of the trace object returned by the Langfuse API client is
treated defensively here (this SDK area moves fast) - if field names have
changed since this was written, fetch_usage() just returns None instead of
raising, so the rest of the app is unaffected either way.
"""

import logging
import os
import time
import uuid

from ..config import settings

logger = logging.getLogger("langfuse_client")

_enabled = bool(settings.langfuse_public_key and settings.langfuse_secret_key)
_client = None

if _enabled:
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
    try:
        from langfuse import get_client

        _client = get_client()
    except Exception:
        logger.exception("Failed to initialize Langfuse - continuing without tracing")
        _enabled = False


def is_enabled() -> bool:
    return _enabled


def new_handler_and_run_id():
    """One handler + run_id per chat turn. Passing a predefined run_id into
    the LangChain invoke config makes it the trace_id in Langfuse, so we
    know what to look up afterward. Returns (None, None) if Langfuse isn't
    configured."""
    if not _enabled:
        return None, None
    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler(), uuid.uuid4()
    except Exception:
        logger.exception("Failed to create Langfuse callback handler")
        return None, None


def fetch_usage(trace_id: str, attempts: int = 3, delay_seconds: float = 0.5):
    """Best-effort: flush pending traces, then poll briefly for this trace's
    calculated cost/usage. Returns a dict {cost_usd, input_tokens,
    output_tokens, model} or None if unavailable."""
    if not _enabled or not trace_id or not _client:
        return None

    try:
        _client.flush()
    except Exception:
        logger.exception("Langfuse flush failed")
        return None

    for _ in range(attempts):
        try:
            trace = _client.api.trace.get(trace_id)
        except Exception:
            trace = None

        cost = _get(trace, "total_cost", "totalCost")
        if cost is not None:
            input_tokens = 0
            output_tokens = 0
            model_name = None
            for obs in _get(trace, "observations") or []:
                usage = _get(obs, "usage") or {}
                input_tokens += _get(usage, "input", "promptTokens") or 0
                output_tokens += _get(usage, "output", "completionTokens") or 0
                model_name = model_name or _get(obs, "model")
            return {
                "cost_usd": cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model": model_name,
            }
        time.sleep(delay_seconds)

    return None


def _get(obj, *names):
    """Attribute/key lookup that works whether the SDK gives us an object or a dict."""
    if obj is None:
        return None
    for name in names:
        if isinstance(obj, dict):
            if name in obj:
                return obj[name]
        elif hasattr(obj, name):
            return getattr(obj, name)
    return None
