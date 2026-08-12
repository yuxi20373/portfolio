"""Builds and caches the "test_agent" main agent (o) - sees the skills for
every (fab, function) identity the test session declared (fab-shared +
that identity's own function, per identity), and can delegate a task to a
worker scoped to exactly ONE identity via create_process_agent (see
tools.py) - the point of this whole sandbox is watching whether o
recognizes a multi-identity question and splits it into separately-scoped
delegations instead of just answering from everything it can see at once.

Cached per (model_name, identities) - a different identity combination is
a genuinely different agent (different skills= list baked in at build
time), not just a different session - see get_agent below.
"""

from deepagents import create_deep_agent

from ..agent_factory import build_chat_model
from ..tools.web_search import web_search
from .tools import TestAgentContext, create_process_agent, get_process_agent_thread, shared_backend
from .tools import _shared_store  # same Postgres store process_agent uses, different namespace prefix

AGENT_INSTRUCTIONS_TEMPLATE = (
    "You are a helpful AI assistant simulating an employee with these "
    "organizational identities: {identities_desc}. For each identity, you "
    "can see that fab's shared skills and that specific function's own "
    "skills - nothing from any other fab or function.\n\n"
    "Use the web_search tool whenever the answer depends on current, "
    "fast-changing, or otherwise unfamiliar information.\n\n"
    "When a request only concerns ONE of your identities, you can answer "
    "directly. When a request spans MULTIPLE of your identities (e.g. it "
    "asks for something from each fab/function you represent), delegate "
    "each part separately via create_process_agent, passing the specific "
    "fab and function each part belongs to - don't answer a multi-identity "
    "request from a single call or from your own general knowledge; "
    "actually delegate one call per identity involved, then combine the "
    "results in your reply. Each create_process_agent call reports back a "
    "thread_id - use get_process_agent_thread(thread_id) if you need the "
    "full detail behind a delegated task's summary later."
)

_agents = {}


def get_agent(identities: tuple, model_name: str = None):
    """identities: tuple of (fab, function) pairs, e.g.
    (("L8A", "Cell"),) or (("L8A", "Cell"), ("L8B", "Cell")) for a
    dual-identity test. Lazily build and cache one agent per
    (model_name, identities) combination."""
    key = (model_name or "__default__", identities)
    if key not in _agents:
        skills = []
        for fab, function in identities:
            for path in (f"/{fab}/_shared", f"/{fab}/{function}"):
                if path not in skills:
                    skills.append(path)
        identities_desc = "、".join(f"{fab}/{function}" for fab, function in identities)
        _agents[key] = create_deep_agent(
            tools=[web_search, create_process_agent, get_process_agent_thread],
            system_prompt=AGENT_INSTRUCTIONS_TEMPLATE.format(identities_desc=identities_desc),
            model=build_chat_model(model_name),
            skills=skills or None,
            backend=shared_backend,
            store=_shared_store,
            context_schema=TestAgentContext,
        )
    return _agents[key]
