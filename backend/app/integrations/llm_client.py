"""Thin dispatcher for one-shot ("simple") completions used by background
services - title generation, semantic search ranking, wiki summarization,
and short-term memory compaction. This is deliberately separate from the
interactive deep agent (app/agent/), which needs tool use and richer
reasoning and is invoked through LangGraph instead.

Picks the provider based on settings.llm_provider so services don't need to
know or care which backend is configured.
"""

from ..config import settings
from . import groq_client, openai_client


def simple_completion(messages: list, temperature: float = 0.3) -> str:
    if settings.llm_provider == "openai":
        return openai_client.chat_completion(messages, model=settings.openai_model)
    return groq_client.chat_completion(messages, model=settings.groq_summarize_model, temperature=temperature)
