"""The "test_agent" experimental mode: a sandbox for trying out fab/function
skill scoping WITHOUT redeploying code for every scenario. The user
declares which (fab, function) identities they're testing as (e.g.
[("L8A", "Cell")], or two at once for a dual-identity test), and:

- the main agent (o, see agent_factory.py) sees the skills for ALL
  declared identities (fab-shared + that identity's own function skill,
  per identity)
- o has a create_process_agent tool that takes an explicit (fab, function)
  per call - letting you watch whether it recognizes a question spans two
  different identities and spawns two separately-scoped p's instead of
  one that just answers from everything it can see

Skill folders live under ../process_agent/skills/{FAB}/{_shared,FUNCTION}/
(reusing that directory rather than duplicating it - these are the same
kind of "who can see this" skill files, just organized by organizational
identity instead of by agent role). Discovered from disk at import time
(see _discover_identities) rather than hardcoded, so dropping in a new
FAB/FUNCTION folder is enough to make it available here - no code change.

Reuses process_agent's Postgres-backed store (see ..process_agent.tools)
instead of opening a second connection pool - just a different top-level
namespace ("test_agent" vs "process_agent") so the two don't collide.

Backend note: unlike process_agent (which builds one FilesystemBackend per
role, each rooted exactly at that role's folder - see that module's
comments on why), this registers routes for EVERY discovered
fab/function pair up front in one shared CompositeBackend. A worker scoped
to one identity via skills= is still, strictly, ABLE to read_file() a path
under a different fab/function if it somehow knew the exact path - the
skills= list only controls what shows up in its skill INDEX, not a hard
filesystem permission. That's an acceptable simplification for a
throwaway testing sandbox; it would matter for a real access-control
feature.
"""

import uuid
from dataclasses import dataclass
from pathlib import Path

from langchain.tools import ToolRuntime, tool
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend

from ..agent_factory import build_chat_model
from ..process_agent.tools import _shared_store
from ..tools.web_search import web_search

_SKILLS_ROOT = Path(__file__).resolve().parent.parent / "process_agent" / "skills"


def _discover_identities() -> dict[str, list[str]]:
    """Scan disk for {FAB}/{FUNCTION} folders - fab -> sorted list of
    function names (excluding "_shared", which isn't a function, it's the
    fab-wide shared bucket). Re-scanned on every call (cheap, a handful of
    directories) so dropping in a new skill folder is visible without a
    restart during local dev - see list_available_identities, exposed to
    the frontend so it doesn't hardcode fab/function names either."""
    identities: dict[str, list[str]] = {}
    if not _SKILLS_ROOT.exists():
        return identities
    for fab_dir in sorted(p for p in _SKILLS_ROOT.iterdir() if p.is_dir() and p.name != "_shared"):
        functions = sorted(p.name for p in fab_dir.iterdir() if p.is_dir() and p.name != "_shared")
        identities[fab_dir.name] = functions
    return identities


def list_available_identities() -> list[dict]:
    """[{"fab": "L8A", "functions": ["Array", "Cell"]}, ...] - what the
    frontend's identity picker offers (see routers/chat.py)."""
    return [{"fab": fab, "functions": functions} for fab, functions in _discover_identities().items()]


@dataclass
class TestAgentContext:
    session_id: int


def _namespace_for(session_id: int) -> tuple:
    return ("test_agent", str(session_id))


_shared_store_backend = StoreBackend(store=_shared_store, namespace=lambda rt: _namespace_for(rt.context.session_id))


def _build_shared_backend() -> CompositeBackend:
    routes = {}
    for fab, functions in _discover_identities().items():
        fab_dir = _SKILLS_ROOT / fab
        for role in ["_shared", *functions]:
            role_dir = fab_dir / role
            if role_dir.exists():
                routes[f"/{fab}/{role}/"] = FilesystemBackend(root_dir=str(role_dir), virtual_mode=True)
    return CompositeBackend(default=_shared_store_backend, routes=routes)


shared_backend = _build_shared_backend()

# Separate from process_agent's own checkpointer - different sandbox,
# different thread_id namespace (prefixed "test_agent-" below), no reason
# to share.
_test_agent_checkpointer = InMemorySaver()


class _ToolCallLogger(BaseCallbackHandler):
    """Same purpose as process_agent's - ground truth for who actually did
    the work, printed straight to stdout. See that module for the full
    rationale."""

    def __init__(self, label: str):
        self.label = label

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name", "?")
        print(f"[test_agent:{self.label}] {name}({input_str})")

    def on_tool_end(self, output, **kwargs):
        preview = str(output)[:500]
        print(f"[test_agent:{self.label}]   -> {preview!r}")


def _last_text(messages) -> str:
    for msg in reversed(messages):
        text = getattr(msg, "content", None)
        if isinstance(text, str) and text.strip():
            return text
    return ""


WORKER_SYSTEM_PROMPT_TEMPLATE = (
    "You are a worker agent simulating an employee of {fab}, function "
    "{function}. Complete the delegated task using your tools and any "
    "relevant skill, then report back concisely. You can only see skills "
    "for {fab}'s shared skills and {function}'s own skills - not any other "
    "fab or function."
)

_worker_agents = {}


def _get_worker_agent(fab: str, function: str, model_name: str = None):
    """Lazily build and cache one worker agent per (fab, function, model) -
    scoped ONLY to that identity's skills (fab-shared + that one function),
    unlike o (agent_factory.get_agent) which can see every identity the
    test session declared. This is what makes the "does o split a
    multi-identity question into separately-scoped delegations" test
    meaningful - a worker literally can't see the other identity's skill
    unless o gave it a task that doesn't need to."""
    key = (model_name or "__default__", fab, function)
    if key not in _worker_agents:
        _worker_agents[key] = create_deep_agent(
            model=build_chat_model(model_name),
            tools=[web_search],
            system_prompt=WORKER_SYSTEM_PROMPT_TEMPLATE.format(fab=fab, function=function),
            skills=[f"/{fab}/_shared", f"/{fab}/{function}"],
            checkpointer=_test_agent_checkpointer,
            backend=shared_backend,
            store=_shared_store,
            context_schema=TestAgentContext,
        )
    return _worker_agents[key]


@tool
def create_process_agent(task_description: str, fab: str, function: str, runtime: ToolRuntime) -> str:
    """Delegate a task to a worker scoped to exactly one (fab, function)
    identity - it can only see that fab's shared skills and that
    function's own skills, nothing from any other identity. Use this when
    a task is specific to one of your identities; if a question spans
    MULTIPLE of your identities, call this once per identity instead of
    once for everything, so each part is handled by a worker that's
    actually scoped to the right skills.
    """
    available = _discover_identities()
    if fab not in available or function not in available[fab]:
        return f"Error: no such identity ({fab}, {function}). Available: {available}"

    worker = _get_worker_agent(fab, function)
    thread_id = f"test_agent-{fab}-{function}-{uuid.uuid4().hex[:8]}"
    session_id = runtime.context.session_id

    result = worker.invoke(
        {"messages": [HumanMessage(task_description)]},
        config={"configurable": {"thread_id": thread_id}, "callbacks": [_ToolCallLogger(f"{fab}/{function}")]},
        context=TestAgentContext(session_id=session_id),
    )
    reply = _last_text(result.get("messages", []))
    return f"[{fab}/{function} thread_id={thread_id}] {reply}"


@tool
def get_process_agent_thread(thread_id: str) -> str:
    """Look up a past worker run's full message history by the thread_id
    reported in create_process_agent's result."""
    # Any cached worker instance shares the same checkpointer, so any of
    # them can look up any thread_id - doesn't need to be the exact worker
    # that created it.
    if not _worker_agents:
        return f"No test_agent thread found for {thread_id!r}"
    worker = next(iter(_worker_agents.values()))
    state = worker.get_state({"configurable": {"thread_id": thread_id}})
    print(f"[test_agent:main] get_process_agent_thread({thread_id!r})")
    if not state.values:
        return f"No test_agent thread found for {thread_id!r}"
    lines = []
    for msg in state.values.get("messages", []):
        role = getattr(msg, "type", msg.__class__.__name__)
        content = getattr(msg, "content", "")
        lines.append(f"[{role}] {content}")
    return "\n".join(lines)
