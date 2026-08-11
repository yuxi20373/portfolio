"""Alternative to the built-in `subagents=[...]` / `task` tool pattern
(see app/agent_factory.py): instead of a pre-registered subagent spec, 1DA
gets a `create_da2` tool that builds and runs a genuinely separate deep
agent instance on demand.

Isolation is via checkpointer + a fresh thread_id per call - DA2's message
history is checkpointed into its own thread, completely separate from
1DA's. Unlike the ephemeral `task` tool, this history isn't discarded when
the call returns - it stays queryable by thread_id (see `get_da2_thread`
below), at the cost of this service no longer being fully stateless (DA2
threads live in this process's memory - see `_da2_checkpointer`).

Sharing the virtual filesystem is NOT automatic just because a checkpointer
is used - each thread's `files` state is independent. So this still copies
`files` in before the call and back out after, exactly like the `task`
tool does internally - a checkpointer gives isolation, not sharing.
"""

import uuid

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from deepagents import create_deep_agent

from ..config import settings
from .web_search import web_search

# Shared across every DA2 run, but each run gets its own thread_id, so runs
# don't see each other's state - this is what makes checkpointer isolation
# work. In-memory only: DA2 threads are lost on process restart. Swap for
# langgraph.checkpoint.sqlite.SqliteSaver (or postgres) if DA2 threads need
# to survive restarts or be inspected from outside this process.
_da2_checkpointer = InMemorySaver()

DA2_SYSTEM_PROMPT = (
    "You are a worker agent handling one delegated task. Complete it using "
    "your tools, then report back. Write any long or reusable output to a "
    "file under /results/ and reply with only a short pointer + summary - "
    "see the delegation-output skill for details."
)


def _build_da2_model():
    if settings.agent_model_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)

    from langchain_groq import ChatGroq

    return ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key)


def _build_da2():
    from ..agent_factory import SKILLS_DIR

    return create_deep_agent(
        model=_build_da2_model(),
        tools=[web_search],
        system_prompt=DA2_SYSTEM_PROMPT,
        skills=[str(SKILLS_DIR)] if SKILLS_DIR.exists() else None,
        checkpointer=_da2_checkpointer,
    )


def _last_text(messages) -> str:
    for msg in reversed(messages):
        text = getattr(msg, "content", None)
        if isinstance(text, str) and text.strip():
            return text
    return ""


@tool
def create_da2(task_description: str, runtime: ToolRuntime) -> Command:
    """Dynamically create and run an isolated worker agent (DA2) on a task.

    Use for complex, multi-step, or tool-heavy sub-tasks, same as you would
    use a `task` delegation - the worker's own tool calls and reasoning
    stay off this conversation, only its final reply comes back. Unlike a
    static subagent, this worker's execution is checkpointed on its own
    thread and can be inspected later via get_da2_thread(thread_id).
    """
    da2 = _build_da2()
    thread_id = f"da2-{uuid.uuid4().hex[:12]}"
    parent_files = runtime.state.get("files", {})

    result = da2.invoke(
        {"messages": [HumanMessage(task_description)], "files": parent_files},
        config={"configurable": {"thread_id": thread_id}},
    )

    reply = _last_text(result.get("messages", []))
    return Command(
        update={
            "files": result.get("files", {}),
            "messages": [
                ToolMessage(
                    f"[da2 thread_id={thread_id}] {reply}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


@tool
def get_da2_thread(thread_id: str) -> str:
    """Look up a past DA2 run's full message history by the thread_id
    reported in create_da2's result (e.g. to audit or debug what a worker
    actually did, beyond its final summary)."""
    da2 = _build_da2()
    state = da2.get_state({"configurable": {"thread_id": thread_id}})
    if not state.values:
        return f"No DA2 thread found for {thread_id!r}"
    lines = []
    for msg in state.values.get("messages", []):
        role = getattr(msg, "type", msg.__class__.__name__)
        content = getattr(msg, "content", "")
        lines.append(f"[{role}] {content}")
    return "\n".join(lines)
