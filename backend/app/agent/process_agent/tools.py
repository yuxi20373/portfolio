"""The "process_agent" tool: an alternative to the `subagents=[...]` /
`task` tool delegation pattern used by ../orchestrator/ - instead of a
pre-registered static subagent, the calling agent gets a
`create_process_agent` tool that builds and runs a genuinely separate deep
agent instance on demand.

Isolation is via a LangGraph checkpointer + a fresh thread_id per call - a
process agent's message history is checkpointed into its own thread,
completely separate from the calling agent's. Unlike the ephemeral `task`
tool, this history isn't discarded when the call returns - it stays
queryable by thread_id (see get_process_agent_thread below), at the cost
of no longer being fully stateless (process agent threads live in this
process's memory - see _process_agent_checkpointer, an InMemorySaver: lost
on process restart, and not shared across multiple backend worker
processes if you ever run more than one - swap for a
langgraph.checkpoint.sqlite/postgres saver if that ever matters).

Sharing the virtual filesystem is NOT automatic just because a checkpointer
is used - each thread's `files` state is independent. So this still copies
`files` in before the call and back out after, exactly like the `task`
tool does internally - a checkpointer gives isolation, not sharing.

Ported in-process from the standalone deepagent_service/ prototype (see
that directory) - fixed there being placed at the wrong import path
(it needed to be under app/tools/, which made that service fail to start)
and reuses this app's own build_chat_model instead of duplicating
provider-selection logic.
"""

import uuid
from pathlib import Path

from langchain.tools import ToolRuntime, tool
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from deepagents import create_deep_agent

from ..agent_factory import build_chat_model
from ..tools.web_search import web_search

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


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
# thread_id, so runs don't see each other's state - this is what makes
# checkpointer isolation work.
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
            skills=[str(SKILLS_DIR)] if SKILLS_DIR.exists() else None,
            checkpointer=_process_agent_checkpointer,
        )
    return _compiled_process_agent


def _last_text(messages) -> str:
    for msg in reversed(messages):
        text = getattr(msg, "content", None)
        if isinstance(text, str) and text.strip():
            return text
    return ""


@tool
def create_process_agent(task_description: str, runtime: ToolRuntime) -> Command:
    """Dynamically create and run an isolated worker agent (a "process
    agent") on a task.

    Use for complex, multi-step, or tool-heavy sub-tasks, same as you would
    use a `task` delegation - the worker's own tool calls and reasoning
    stay off this conversation, only its final reply comes back. Unlike a
    static subagent, this worker's execution is checkpointed on its own
    thread and can be inspected later via get_process_agent_thread(thread_id).
    """
    process_agent = _get_process_agent()
    thread_id = f"process_agent-{uuid.uuid4().hex[:12]}"
    parent_files = runtime.state.get("files", {})

    result = process_agent.invoke(
        {"messages": [HumanMessage(task_description)], "files": parent_files},
        config={"configurable": {"thread_id": thread_id}, "callbacks": [_ToolCallLogger(thread_id)]},
    )

    reply = _last_text(result.get("messages", []))
    return Command(
        update={
            "files": result.get("files", {}),
            "messages": [
                ToolMessage(
                    f"[process_agent thread_id={thread_id}] {reply}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


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
