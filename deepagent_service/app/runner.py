"""Runs one turn of the deep agent given the full message history the
caller supplies, and normalizes the result back down to a plain reply
string + updated virtual filesystem for the caller to persist."""

from langchain_core.callbacks import BaseCallbackHandler

from .agent_factory import get_agent


class _ToolCallCollector(BaseCallbackHandler):
    """Records every tool call made during this turn - including calls made
    *inside* an isolated worker (2DA) run, since LangGraph propagates
    callbacks into nested subagent invocations automatically. Each entry is
    tagged with which agent made the call (1DA vs worker), tracked via
    whether we're currently between a `task` tool's start and its matching
    end (by run_id) - a flat list alone can't tell "1DA called write_file
    itself" apart from "write_file was called inside the delegated worker",
    since both share the same default tools.
    """

    def __init__(self):
        self.calls: list[dict] = []
        self._depth = 0
        self._names_by_run_id: dict = {}

    def on_tool_start(self, serialized, input_str, *, run_id=None, **kwargs):
        name = serialized.get("name", "?")
        self._names_by_run_id[run_id] = name
        agent = "worker" if self._depth > 0 else "1DA"
        self.calls.append({"agent": agent, "event": "call", "tool": name, "input": input_str})
        print(f"[tool:{agent}] {name}({input_str})")
        if name == "task":
            self._depth += 1

    def on_tool_end(self, output, *, run_id=None, **kwargs):
        was_task = self._names_by_run_id.pop(run_id, None) == "task"
        agent = "1DA" if was_task else ("worker" if self._depth > 0 else "1DA")
        preview = str(output)[:500]
        self.calls.append({"agent": agent, "event": "result", "output": preview})
        print(f"[tool:{agent}]   -> {preview!r}")
        if was_task:
            self._depth = max(0, self._depth - 1)


def run_turn(messages: list[dict], files: dict | None = None) -> tuple[str, dict, list[dict]]:
    """Run one turn. `messages` is the full conversation (including the new
    user message) in {"role", "content"} dict form. `files` is the deep
    agent's virtual filesystem carried over from the previous call - the
    caller owns persisting the returned files dict across calls."""
    agent = get_agent()
    collector = _ToolCallCollector()
    result = agent.invoke(
        {"messages": messages, "files": files or {}},
        config={"callbacks": [collector]},
    )
    reply = _last_text(result.get("messages", []))
    return reply, result.get("files", {}), collector.calls


def _last_text(messages) -> str:
    if not messages:
        return ""
    last = messages[-1]
    content = getattr(last, "content", last)
    if isinstance(content, list):
        # some providers return content as a list of blocks (e.g. text + tool traces)
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(part.get("text", ""))
            else:
                parts.append(str(part))
        return "".join(parts)
    return content
