"""Runs one turn of the "orchestrator" experimental deep agent. Unlike
../runner.py (the "original" /agent path), this variant also carries a
virtual filesystem (`files`) across turns, since its worker subagent writes
long output to /results/ for the main agent to read back later in the same
session (see agent_factory.py's AGENT_INSTRUCTIONS). The caller
(chat_service.py) owns persisting `files` between turns - see
ChatSession.orchestrator_files.
"""

from langchain_core.callbacks import BaseCallbackHandler

from .agent_factory import get_agent
from ..runner import _aggregate_usage, _last_text


class _ToolCallCollector(BaseCallbackHandler):
    """Ground truth for whether delegation actually happened this turn - the
    model's own reply text can claim it delegated something without that
    being true, so this prints every REAL tool invocation (including ones
    made *inside* an isolated worker run, since LangGraph propagates
    callbacks into nested subagent invocations automatically) straight to
    the server console, instead of trusting the reply text. Tagged
    orchestrator vs worker via whether we're currently between a `task`
    tool's start and its matching end (by run_id) - a flat list alone can't
    tell "orchestrator called write_file itself" apart from "write_file was
    called inside the delegated worker", since both share the same default
    tools.

    Printed (not `logging`) so it's guaranteed visible in the running
    server's stdout without needing any logging config this app doesn't have."""

    def __init__(self):
        self.calls: list[dict] = []
        self._depth = 0
        self._names_by_run_id: dict = {}

    def on_tool_start(self, serialized, input_str, *, run_id=None, **kwargs):
        name = serialized.get("name", "?")
        self._names_by_run_id[run_id] = name
        agent = "worker" if self._depth > 0 else "orchestrator"
        self.calls.append({"agent": agent, "event": "call", "tool": name, "input": input_str})
        print(f"[orchestrator tool:{agent}] {name}({input_str})")
        if name == "task":
            self._depth += 1

    def on_tool_end(self, output, *, run_id=None, **kwargs):
        was_task = self._names_by_run_id.pop(run_id, None) == "task"
        agent = "orchestrator" if was_task else ("worker" if self._depth > 0 else "orchestrator")
        preview = str(output)[:500]
        self.calls.append({"agent": agent, "event": "result", "output": preview})
        print(f"[orchestrator tool:{agent}]   -> {preview!r}")
        if was_task:
            self._depth = max(0, self._depth - 1)


def run_turn(
    context_messages: list[dict],
    user_text: str,
    files: dict = None,
    model_name: str = None,
    session_id: int = None,  # unused here - orchestrator still uses the old per-invocation StateBackend/files approach, not session-namespaced sharing
) -> tuple[str, dict, dict]:
    agent = get_agent(model_name)
    input_messages = context_messages + [{"role": "user", "content": user_text}]

    collector = _ToolCallCollector()
    result = agent.invoke(
        {"messages": input_messages, "files": files or {}},
        config={"callbacks": [collector]},
    )
    all_messages = result.get("messages", [])

    reply = _last_text(all_messages)
    usage = _aggregate_usage(all_messages, len(input_messages), model_name)
    # 判斷有沒有真的委派,看的是有沒有一次呼叫 task 工具(那本身就是委派這個
    # 動作),不是看有沒有 agent=="worker" 的紀錄 - worker 被叫到之後如果它
    # 自己不需要再用任何工具(直接就能回答),就不會有任何 agent=="worker"
    # 的紀錄,但委派本身確實發生了,不能拿「worker 有沒有再用到工具」來判斷
    # 「有沒有委派」,這是兩件事。
    if any(c["event"] == "call" and c["tool"] == "task" for c in collector.calls):
        print("[orchestrator] delegated to worker via task this turn")
    elif collector.calls:
        print("[orchestrator] tools were called, but never delegated to worker via task")
    else:
        print("[orchestrator] no tool calls this turn (answered directly)")
    return reply, usage, result.get("files", {})
