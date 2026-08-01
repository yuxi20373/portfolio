"""Builds and caches the LangGraph deep agent (via the `deepagents` package)
used for chat turns. Tool wiring and model/provider selection live here so
the rest of the app doesn't need to know about LangGraph/deepagents
internals - `app/services/chat_service.py` just calls `app.agent.runner`.

We deliberately do NOT use LangGraph's checkpointer for cross-turn state:
the SQL database (ChatMessage / ChatSession.memory_summary) is the single
source of truth for conversation history, since the rest of the app
(calendar view, wiki summarizer, session rename/delete, etc.) already reads
from it. Each turn is invoked with a freshly-built message list instead.
"""

from pathlib import Path

from deepagents import create_deep_agent

from ..config import settings
from ..prompts.chat_agent import AGENT_INSTRUCTIONS
from .tools.web_search import web_search
from .tools.wiki_manage import update_wiki

# Skills give the agent extra, only-loaded-when-relevant instructions (the
# same Anthropic SKILL.md pattern used elsewhere) - e.g.
# skills/tool-calling-format teaches it the correct way to invoke a tool,
# which helps (though doesn't 100% guarantee) smaller/weaker models from
# hallucinating malformed tool-call syntax.
SKILLS_DIR = Path(__file__).resolve().parent / "skills"

_agent = None


def _build_chat_model():
    if settings.agent_model_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)

    from langchain_groq import ChatGroq

    return ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key)


def get_agent():
    """Lazily build and cache the deep agent instance (model init happens
    once, on first use, not at import time)."""
    global _agent
    if _agent is None:
        kwargs = dict(
            tools=[web_search, update_wiki],
            system_prompt=AGENT_INSTRUCTIONS,
            model=_build_chat_model(),
        )
        if SKILLS_DIR.exists():
            kwargs["skills"] = [str(SKILLS_DIR)]
        _agent = create_deep_agent(**kwargs)
    return _agent


def default_model_name() -> str:
    """The model name to attribute a turn's usage/cost to when the provider
    doesn't report a model name back on the message itself."""
    if settings.agent_model_provider == "openai":
        return settings.openai_model
    return settings.groq_model
