"""Builds and caches the two-layer deep agent: a main agent ("1DA") that can
dynamically delegate complex sub-tasks to an isolated "worker" subagent
("2DA") via deepagents' built-in `task` tool.

This module has no database/session dependency by design - it's meant to be
called statelessly (see app/runner.py + app/main.py): the caller supplies
the full message history and any carried-over `files` on every call, and
gets back a reply plus the updated `files` to carry into the next call.
"""

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.middleware.subagents import SubAgent

from .config import settings
from .tools.web_search import web_search
from .tools.create_da2 import create_da2, get_da2_thread

AGENT_INSTRUCTIONS = (
    "You are a helpful AI assistant chatting with a user. Reply in the same "
    "language the user writes in, and keep answers clear and to the point. "
    "Use the web_search tool whenever the answer depends on current, "
    "fast-changing, or otherwise unfamiliar information - don't guess when "
    "you can look it up.\n\n"
    "For a complex, multi-step, or tool-heavy sub-task (e.g. gathering and "
    "synthesizing information from several sources), delegate it to the "
    "`worker` subagent via the task tool instead of doing it inline - this "
    "keeps this conversation focused on the synthesized result rather than "
    "every intermediate step. Don't delegate trivial requests (a single "
    "lookup, a short direct answer).\n\n"
    "The worker writes any long or reusable output to a file under "
    "/results/ and only reports back a short pointer + summary - so if the "
    "user later asks you to recall, compile, or reformat something from "
    "earlier, check /results/ with ls and read_file for the full content "
    "before answering, rather than relying on what's still visible in the "
    "chat history."
)

SKILLS_DIR = Path(__file__).resolve().parent / "skills"

# The "2DA": an isolated worker the main agent ("1DA") can delegate to via
# the built-in `task` tool. Its internal messages never enter the main
# conversation - only its final reply comes back - and any file it writes
# lands in the same shared virtual filesystem the main agent reads from.
# tools/model are omitted so it inherits the main agent's tools and model.
WORKER_SUBAGENT: SubAgent = {
    "name": "worker",
    "description": (
        "Handles a complex, multi-step, or tool-heavy sub-task in isolation "
        "(e.g. multi-source research, structured data gathering) so the "
        "main conversation stays uncluttered. Give it the full task context "
        "and state exactly what output you want back."
    ),
    "system_prompt": (
        "You are a worker subagent. Complete the delegated task using your "
        "tools, then report back to the calling agent. See the "
        "delegation-output skill for how to structure your output."
    ),
    "skills": [str(SKILLS_DIR)],
}

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
            tools=[web_search, create_da2, get_da2_thread],
            system_prompt=AGENT_INSTRUCTIONS,
            model=_build_chat_model(),
            subagents=[WORKER_SUBAGENT],
        )
        if SKILLS_DIR.exists():
            kwargs["skills"] = [str(SKILLS_DIR)]
        _agent = create_deep_agent(**kwargs)
    return _agent
