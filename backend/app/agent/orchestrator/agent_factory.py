"""Builds and caches the "orchestrator" experimental deep agent: a two-layer
setup (a main "orchestrator" agent that can delegate complex sub-tasks to
an isolated "worker" subagent via deepagents' built-in `task` tool).

Ported in-process from the standalone deepagent_service/ prototype at the
repo root (which was never deployed) so it can be tried from the chat page
via the "/orchestrator" command without standing up a separate service - see
runner.py and app/services/chat/chat_service.py's dispatch.

Deliberately kept fully separate from ../agent_factory.py (the "original"
deep agent behind "/agent") - this module has its own agent cache and
doesn't share or mutate any of that module's state, so experimenting here
can never affect the original path. Model-provider selection IS reused from
there (build_chat_model) since that's just deployment-wide config, not
agent-specific behavior.
"""

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.middleware.subagents import SubAgent

from ..agent_factory import build_chat_model
from ..tools.web_search import web_search

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
# tool-calling-format is identical content to the "original" agent's copy -
# reuse it from there instead of duplicating; delegation-output (this
# module's own skills dir) is specific to the worker subagent below.
SHARED_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

# The isolated worker the "orchestrator" agent can delegate to via the
# built-in `task` tool. Its internal messages never enter the main
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

_agents = {}


def get_agent(model_name: str = None):
    """Lazily build and cache one orchestrator instance per model name - same
    per-model caching pattern as ../agent_factory.get_agent, but a fully
    separate cache/instance."""
    key = model_name or "__default__"
    if key not in _agents:
        kwargs = dict(
            tools=[web_search],
            system_prompt=AGENT_INSTRUCTIONS,
            model=build_chat_model(model_name),
            subagents=[WORKER_SUBAGENT],
        )
        skill_dirs = [str(d) for d in (SKILLS_DIR, SHARED_SKILLS_DIR) if d.exists()]
        if skill_dirs:
            kwargs["skills"] = skill_dirs
        _agents[key] = create_deep_agent(**kwargs)
    return _agents[key]
