"""Runs one turn of the "test_agent" sandbox. Unlike process_agent's
runner (context_messages, user_text, files, model_name), this one also
takes `identities` - the (fab, function) pairs this session declared,
since which agent gets used depends on that (see agent_factory.get_agent).

Returns a (reply, usage, files) 3-tuple for interface consistency with
every other EXPERIMENTAL_AGENTS entry (see chat_service.py) even though
the files slot is always {} and ignored (FILES_COLUMN_BY_AGENT is None for
"test_agent" - same reasoning as process_agent, see that module)."""

from .agent_factory import get_agent
from .tools import TestAgentContext, _ToolCallLogger
from ..runner import _aggregate_usage, _last_text


def run_turn(
    context_messages: list[dict],
    user_text: str,
    files: dict = None,
    model_name: str = None,
    session_id: int = None,
    identities: tuple = (),
) -> tuple[str, dict, dict]:
    agent = get_agent(identities, model_name)
    input_messages = context_messages + [{"role": "user", "content": user_text}]

    result = agent.invoke(
        {"messages": input_messages},
        config={"callbacks": [_ToolCallLogger("main")]},
        context=TestAgentContext(session_id=session_id),
    )
    all_messages = result.get("messages", [])

    reply = _last_text(all_messages)
    usage = _aggregate_usage(all_messages, len(input_messages), model_name)
    return reply, usage, {}
