"""Builds and caches the LangGraph deep agent (via the `deepagents` package)
used for chat turns. Tool wiring and model/provider selection live here so
the rest of the app doesn't need to know about LangGraph/deepagents
internals - `app/services/chat_service.py` just calls `app.agent.runner`.

We deliberately do NOT use LangGraph's checkpointer for cross-turn state:
the SQL database (ChatMessage / ChatSession.memory_summary) is the single
source of truth for conversation history, since the rest of the app
(calendar view, wiki summarizer, session rename/delete, etc.) already reads
from it. Each turn is invoked with a freshly-built message list instead.

Each chat session can override which OpenAI model it uses (see
app/agent/model_catalog.py and ChatSession.model_name) - so both the agent
and the chat model itself are cached per model name instead of as a single
global singleton.
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

_agents = {}


def build_chat_model(model_name: str = None):
    """Build the plain LangChain chat model for AGENT_MODEL_PROVIDER. Shared
    by the deep agent (below) and by the default, non-agent chat path
    (app/agent/simple_chat.py), so both talk to the same configured model.
    `model_name` overrides settings.openai_model (ignored for groq/anthropic,
    which aren't part of the user-facing model catalog/switcher - that's
    OpenAI-only, see app/agent/model_catalog.py)."""
    if settings.agent_model_provider == "openai":
        from langchain_openai import ChatOpenAI

        resolved_model = model_name or settings.openai_model
        kwargs = dict(model=resolved_model, api_key=settings.openai_api_key)
        if resolved_model.startswith("gpt-5"):
            # gpt-5.x 是推理模型 - 搭配 function tools 用時,OpenAI 的
            # /v1/chat/completions 端點會直接 400("Function tools with
            # reasoning_effort are not supported")。明確關掉/調低推理就能
            # 正常用工具,不用整個換成非推理模型 - 對日常對話/工具呼叫這種
            # 場景,推理調低的影響通常很小,差別主要在複雜數學/多步驟邏輯
            # 這類需要刻意逐步思考的題目。
            #
            # 不同 gpt-5 世代支援的有效值不一樣,不是每個都吃 "none":
            # gpt-5.6-luna 實測必須是 "none"(其他值一樣會撞 tools+reasoning
            # 的 400);gpt-5-mini 實測 "none" 直接被拒(錯誤訊息列出的合法值
            # 是 minimal/low/medium/high),用 "minimal" 通過。之後如果再遇到
            # 新的 gpt-5.x 世代炸掉,先看錯誤訊息列出的合法值,不要照抄這裡。
            kwargs["reasoning_effort"] = "none" if resolved_model.startswith("gpt-5.6") else "minimal"
        return ChatOpenAI(**kwargs)

    if settings.agent_model_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_model, api_key=settings.anthropic_api_key, max_tokens=8192
        )

    from langchain_groq import ChatGroq

    return ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key)


def get_agent(model_name: str = None):
    """Lazily build and cache one deep agent instance per model name (model
    init happens once per model, on first use, not at import time)."""
    key = model_name or "__default__"
    if key not in _agents:
        kwargs = dict(
            tools=[web_search, update_wiki],
            system_prompt=AGENT_INSTRUCTIONS,
            model=build_chat_model(model_name),
        )
        if SKILLS_DIR.exists():
            kwargs["skills"] = [str(SKILLS_DIR)]
        _agents[key] = create_deep_agent(**kwargs)
    return _agents[key]


def default_model_name(model_name: str = None) -> str:
    """The model name to attribute a turn's usage/cost to when the provider
    doesn't report a model name back on the message itself."""
    if settings.agent_model_provider == "openai":
        return model_name or settings.openai_model
    if settings.agent_model_provider == "anthropic":
        return settings.anthropic_model
    return settings.groq_model
