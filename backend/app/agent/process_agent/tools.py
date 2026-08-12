"""The "process_agent" tool: an alternative to the `subagents=[...]` /
`task` tool delegation pattern used by ../orchestrator/ - instead of a
pre-registered static subagent, the calling agent gets a
`create_process_agent` tool that builds and runs a genuinely separate deep
agent instance on demand.

Files are GENUINELY SHARED between the caller (o) and every spawned
process agent (p) - both are built with the same `StoreBackend`, backed by
the same Postgres-backed store (same Neon DB as the rest of the app, its
own `store` table - see _build_shared_store below), namespaced per chat
session (see ProcessAgentContext/_namespace_for below). Whatever either
side writes, the other can read immediately via ls/read_file - there's no
more copying a `files` dict in and merging a result back out (that was the
old per-invocation `StateBackend` approach; StoreBackend doesn't tie files
to one invoke() call's state at all, so nothing needs to be shuttled
around by hand anymore). Being Postgres-backed also means this survives
process restarts - unlike the checkpointer below, which doesn't need to
(this experimental feature only needs its written files to stick around,
not full replayable thread history).

The namespace MUST include session_id - otherwise every session (every
user, every conversation) would read and write the exact same shared
filesystem, which would be a real cross-account data leak, not just messy
isolation.

Message-history isolation for each spawned process agent is a SEPARATE
mechanism from the above - that's the LangGraph checkpointer
(_process_agent_checkpointer), keyed by each call's own fresh thread_id,
queryable later via get_process_agent_thread. This ONE stays an
InMemorySaver on purpose (lost on process restart) - deliberately not
upgraded alongside the store above.

Ported in-process from the standalone deepagent_service/ prototype (see
that directory) - fixed there being placed at the wrong import path
(it needed to be under app/tools/, which made that service fail to start)
and reuses this app's own build_chat_model instead of duplicating
provider-selection logic.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from langchain.tools import ToolRuntime, tool
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.postgres.base import PoolConfig
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend

from ...config import settings
from ..agent_factory import build_chat_model
from ..tools.web_search import web_search

# Skills are split by who should see them - fab/function style: "_shared"
# is visible to every role in process_agent (fab-level), "main"/"worker"
# are each visible only to that one role (function-level).
#
# These are real local SKILL.md files (repo-versioned static content), so
# they're served from their own FilesystemBackend(s) rather than living in
# the Postgres store with everything else - but that backend still has to
# be reachable through the SAME `backend=` the agent's normal read_file/ls
# tools use, or skills show up in the system-prompt index (that part comes
# straight from SkillsMiddleware) but 404 the moment the agent tries to
# read_file() one (that part goes through the agent's own file tools,
# which don't know about a second backend on their own). CompositeBackend
# is what reconciles this: one backend, routed by path prefix - anything
# under /_shared, /main, /worker goes to the matching filesystem backend,
# everything else (session files, the thread log) goes to Postgres. See
# shared_backend below - this only works because create_deep_agent's
# skills= param and its normal file tools both resolve through the exact
# same backend.
#
# One FilesystemBackend PER route, each rooted exactly at that role's own
# subfolder - not one shared backend rooted at the parent "skills/" dir.
# CompositeBackend strips the matched route prefix before delegating (per
# its own docs: "/memories/note.txt" -> backend sees "/note.txt", because
# the target backend's root IS the memories area, not a parent containing
# it) - so a single backend rooted at "skills/" would have every "/_shared/
# xxx" request arrive as "/xxx" and 404, since "xxx" only actually exists
# one level down, inside "skills/_shared/".
_SKILLS_ROOT = Path(__file__).resolve().parent / "skills"


def _skills_fs_backend(role_dir: str) -> FilesystemBackend:
    # virtual_mode=True: paths resolve relative to root_dir (a virtual
    # root), not as real absolute OS paths from "/" (virtual_mode=False -
    # the deprecated implicit default - treats them as real absolute
    # paths, which 404s every time since none of these exist at actual
    # filesystem root).
    return FilesystemBackend(root_dir=str(_SKILLS_ROOT / role_dir), virtual_mode=True)


def _build_shared_store() -> PostgresStore:
    """psycopg (v3, what PostgresStore needs - NOT the psycopg2-binary the
    rest of the app uses via SQLAlchemy) doesn't understand the
    `channel_binding` query param Neon's connection string includes -
    `sslmode=require` alone is enough, so it's stripped here rather than
    changed globally in settings.database_url (SQLAlchemy/psycopg2 handles
    the original string fine - no reason to touch that).

    Opened once at import time and kept open for the process's lifetime
    (same pattern as app/database.py's module-level `engine`) - .__enter__()
    is called without a matching __exit__ on purpose; there's no app
    shutdown hook to pair it with, and the OS reclaims the connection pool
    when the process exits either way.

    IMPORTANT: from_conn_string() is a generator-based context manager - if
    nothing keeps a reference to the context-manager object itself (only to
    what __enter__() returns), Python is free to garbage-collect it at any
    point, which resumes the generator past its `yield` and runs the
    connection pool's shutdown code - the store then fails on the very next
    query with "the pool is already closed". _shared_store_cm below exists
    solely to keep that reference alive for the process's lifetime."""
    url = re.sub(r"[?&]channel_binding=require", "", settings.database_url)
    cm = PostgresStore.from_conn_string(url, pool_config=PoolConfig(min_size=1, max_size=5))
    store = cm.__enter__()
    store.setup()  # creates the `store` table on first run; no-ops after
    return cm, store


_shared_store_cm, _shared_store = _build_shared_store()


@dataclass
class ProcessAgentContext:
    """The one piece of per-invoke context both o's agent (see
    ../agent_factory.py) and every spawned p share - used purely to
    namespace the shared store (see _namespace_for). Both sides must be
    built with context_schema=ProcessAgentContext and invoked with a
    ProcessAgentContext(session_id=...) matching the same session for
    sharing to actually line up."""

    session_id: int


def _namespace_for(session_id: int) -> tuple:
    return ("process_agent", str(session_id))


# _shared_store (built above) is shared across every session - namespaced
# apart per-session via this backend's `namespace=`, which is what makes o
# and p see the same files without us copying anything by hand.
_shared_store_backend = StoreBackend(store=_shared_store, namespace=lambda rt: _namespace_for(rt.context.session_id))

# The single backend both o and every p are actually built with (see
# ../agent_factory.py's get_agent and _get_process_agent below) - routes
# skill paths to the local filesystem, everything else to the session's
# namespaced Postgres store. See the module docstring for why this has to
# be one composite backend rather than two separate ones.
shared_backend = CompositeBackend(
    default=_shared_store_backend,
    routes={
        "/_shared/": _skills_fs_backend("_shared"),
        "/main/": _skills_fs_backend("main"),
        "/worker/": _skills_fs_backend("worker"),
    },
)


class _ToolCallLogger(BaseCallbackHandler):
    """Prints every tool call/result made during one invoke() call, tagged
    with `label` - lets you see concretely WHICH agent instance actually
    did the work (the main agent, or a specific spawned process agent by
    its thread_id), instead of trusting a reply's self-description. Each
    process agent gets its own fresh thread_id and its own invoke() call,
    so a plain per-call label is enough here - no need for orchestrator's
    depth-tracking (that's only needed because it shares ONE invoke() call
    with its worker via the `task` tool)."""

    def __init__(self, label: str):
        self.label = label

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name", "?")
        print(f"[process_agent:{self.label}] {name}({input_str})")

    def on_tool_end(self, output, **kwargs):
        preview = str(output)[:500]
        print(f"[process_agent:{self.label}]   -> {preview!r}")


# Shared across every process agent run, but each run gets its own
# thread_id, so runs don't see each other's message history - this is what
# makes checkpointer isolation work. Unrelated to the shared store above -
# see the module docstring for why these are two separate mechanisms.
_process_agent_checkpointer = InMemorySaver()

PROCESS_AGENT_SYSTEM_PROMPT = (
    "You are a worker agent handling one delegated task. Complete it using "
    "your tools, then report back. Write any long or reusable output to a "
    "file under /results/ and reply with only a short pointer + summary - "
    "see the delegation-output skill for details."
)

_compiled_process_agent = None


def _get_process_agent():
    """Lazily build and cache the process agent's graph definition itself
    (not a per-thread instance - threads are just different checkpointer
    keys on this same compiled graph)."""
    global _compiled_process_agent
    if _compiled_process_agent is None:
        _compiled_process_agent = create_deep_agent(
            model=build_chat_model(),
            tools=[web_search],
            system_prompt=PROCESS_AGENT_SYSTEM_PROMPT,
            skills=["/_shared", "/worker"],
            checkpointer=_process_agent_checkpointer,
            backend=shared_backend,
            store=_shared_store,
            context_schema=ProcessAgentContext,
        )
    return _compiled_process_agent


def _last_text(messages) -> str:
    for msg in reversed(messages):
        text = getattr(msg, "content", None)
        if isinstance(text, str) and text.strip():
            return text
    return ""


# 一個純粹的「索引」檔案,不是內容本體 - 每次 create_process_agent 都會用程式
# 碼(不是靠模型自己記得講)在這裡加一行 thread_id + 任務描述。目的是讓 o
# 不用依賴自己前幾輪回覆有沒有提過 thread_id、也不受記憶壓縮影響,隨時能翻
# 這個索引找到過去委派過的 thread_id,再自己決定要不要用
# get_process_agent_thread 把完整內容抓進來 - 平常不會主動被讀,只有需要時
# 才會被翻,不會每輪都佔用 context。直接用 store.get/put(不透過
# StoreBackend 的高階 write/edit,因為那兩個是「檔案不存在才能寫」/「取代
# 舊字串」的語意,不適合累加式的 log),namespace 用跟 o/p 共用的同一套。
THREAD_LOG_PATH = "/results/_process_agent_log.md"


def _append_thread_log(store, namespace: tuple, thread_id: str, task_description: str) -> None:
    existing = store.get(namespace, THREAD_LOG_PATH)
    prior_content = existing.value.get("content", "") if existing else ""
    now = datetime.now(timezone.utc).isoformat()
    summary = task_description.strip().replace("\n", " ")[:120]
    line = f"- {thread_id} ({now}): {summary}\n"
    store.put(
        namespace,
        THREAD_LOG_PATH,
        {
            "content": prior_content + line,
            "encoding": "utf-8",
            "created_at": existing.value.get("created_at", now) if existing else now,
            "modified_at": now,
        },
    )


@tool
def create_process_agent(task_description: str, runtime: ToolRuntime) -> str:
    """Dynamically create and run an isolated worker agent (a "process
    agent") on a task.

    Use for complex, multi-step, or tool-heavy sub-tasks, same as you would
    use a `task` delegation - the worker's own tool calls and reasoning
    stay off this conversation, only its final reply comes back. It shares
    your virtual filesystem directly (whatever either of you writes, the
    other can read via ls/read_file - no copying involved), and its
    execution is checkpointed on its own thread, inspectable later via
    get_process_agent_thread(thread_id).
    """
    process_agent = _get_process_agent()
    thread_id = f"process_agent-{uuid.uuid4().hex[:12]}"
    session_id = runtime.context.session_id

    result = process_agent.invoke(
        {"messages": [HumanMessage(task_description)]},
        config={"configurable": {"thread_id": thread_id}, "callbacks": [_ToolCallLogger(thread_id)]},
        context=ProcessAgentContext(session_id=session_id),
    )

    reply = _last_text(result.get("messages", []))
    _append_thread_log(runtime.store, _namespace_for(session_id), thread_id, task_description)

    return f"[process_agent thread_id={thread_id}] {reply}"


@tool
def get_process_agent_thread(thread_id: str) -> str:
    """Look up a past process agent run's full message history by the
    thread_id reported in create_process_agent's result (e.g. to audit or
    debug what a worker actually did, beyond its final summary)."""
    process_agent = _get_process_agent()
    state = process_agent.get_state({"configurable": {"thread_id": thread_id}})
    print(f"[process_agent:main] get_process_agent_thread({thread_id!r})")
    if not state.values:
        return f"No process agent thread found for {thread_id!r}"
    lines = []
    for msg in state.values.get("messages", []):
        role = getattr(msg, "type", msg.__class__.__name__)
        content = getattr(msg, "content", "")
        lines.append(f"[{role}] {content}")
    return "\n".join(lines)
