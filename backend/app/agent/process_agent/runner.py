"""Runs one turn of the "process_agent" experimental deep agent. Same
interface convention as ../orchestrator/runner.py (context_messages +
user_text in, (reply, usage, files) out) so chat_service.py's dispatch
doesn't need to know which experimental implementation it's calling - see
EXPERIMENTAL_AGENTS there. The `files` slot in the return tuple is always
`{}` here and safely ignored (see chat_service.py's FILES_COLUMN_BY_AGENT
being None for "process_agent") - unlike orchestrator, process_agent's
files live in a shared store namespaced by session_id, not in a `files`
dict we'd need to persist ourselves (see tools.py's module docstring).

`session_id` is required - it's how the shared store keeps different
sessions' files apart from each other (see tools.py's ProcessAgentContext /
_namespace_for). Passing None would let the store fall back to whatever
`str(None)` resolves to as a namespace, which isn't a real per-session
boundary - always pass the real session id.
"""

from .agent_factory import get_agent
from .tools import ProcessAgentContext, _ToolCallLogger
from ..runner import _aggregate_usage, _last_text


def run_turn(
    context_messages: list[dict],
    user_text: str,
    files: dict = None,
    model_name: str = None,
    session_id: int = None,
) -> tuple[str, dict, dict]:
    agent = get_agent(model_name)
    input_messages = context_messages + [{"role": "user", "content": user_text}]

    # "main" here means the top-level agent itself (as opposed to a spawned
    # process agent, which gets its own thread_id label - see tools.py's
    # create_process_agent) - lets you tell from the printed log alone
    # whether the main agent answered directly or a specific delegated
    # instance did the work.
    result = agent.invoke(
        {"messages": input_messages},
        config={"callbacks": [_ToolCallLogger("main")]},
        context=ProcessAgentContext(session_id=session_id),
    )
    all_messages = result.get("messages", [])

    reply = _last_text(all_messages)
    usage = _aggregate_usage(all_messages, len(input_messages), model_name)
    return reply, usage, {}
