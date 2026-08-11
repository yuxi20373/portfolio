"""Builds and caches the "process_agent" experimental deep agent: a main
agent that, instead of a pre-registered static subagent (see
../orchestrator/), gets a `create_process_agent` tool letting it
dynamically spin up an isolated, independently checkpointed worker agent
per delegated task (see tools.py).

Deliberately kept fully separate from ../agent_factory.py (the "original"
deep agent behind "/agent") and from ../orchestrator/agent_factory.py -
its own agent cache, doesn't share or mutate either's state.
Model-provider selection IS reused from ../agent_factory.py
(build_chat_model) since that's just deployment-wide config, not
agent-specific behavior.
"""

from deepagents import create_deep_agent

from ..agent_factory import build_chat_model
from ..tools.web_search import web_search
from .tools import SKILLS_DIR, create_process_agent, get_process_agent_thread

AGENT_INSTRUCTIONS = (
    "You are a helpful AI assistant chatting with a user. Reply in the same "
    "language the user writes in, and keep answers clear and to the point. "
    "Use the web_search tool whenever the answer depends on current, "
    "fast-changing, or otherwise unfamiliar information - don't guess when "
    "you can look it up.\n\n"
    "For a complex, multi-step, or tool-heavy sub-task (e.g. gathering and "
    "synthesizing information from several sources), delegate it to an "
    "isolated worker via the create_process_agent tool instead of doing it "
    "inline - this keeps this conversation focused on the synthesized "
    "result rather than every intermediate step. Don't delegate trivial "
    "requests (a single lookup, a short direct answer). Each "
    "create_process_agent call reports back a thread_id - if you or the "
    "user later need the full detail behind a delegated task's summary, "
    "use get_process_agent_thread(thread_id) to look it up.\n\n"
    "A worker writes any long or reusable output to a file under /results/ "
    "and only reports back a short pointer + summary - so if the user "
    "later asks you to recall, compile, or reformat something from "
    "earlier, check /results/ with ls and read_file for the full content "
    "before answering, rather than relying on what's still visible in the "
    "chat history."
)

_agents = {}


def get_agent(model_name: str = None):
    """Lazily build and cache one process_agent instance per model name -
    same per-model caching pattern as ../agent_factory.get_agent, but a
    fully separate cache/instance."""
    key = model_name or "__default__"
    if key not in _agents:
        kwargs = dict(
            tools=[web_search, create_process_agent, get_process_agent_thread],
            system_prompt=AGENT_INSTRUCTIONS,
            model=build_chat_model(model_name),
        )
        if SKILLS_DIR.exists():
            kwargs["skills"] = [str(SKILLS_DIR)]
        _agents[key] = create_deep_agent(**kwargs)
    return _agents[key]
