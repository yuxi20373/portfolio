"""Runs one turn of the "da_subagent" experimental deep agent. Unlike
../runner.py (the "original" /agent path), this variant also carries a
virtual filesystem (`files`) across turns, since its worker subagent writes
long output to /results/ for the main agent to read back later in the same
session (see agent_factory.py's AGENT_INSTRUCTIONS). The caller
(chat_service.py) owns persisting `files` between turns - see
ChatSession.da_subagent_files.
"""

from .agent_factory import get_agent
from ..runner import _aggregate_usage, _last_text


def run_turn(
    context_messages: list[dict], user_text: str, files: dict = None, model_name: str = None
) -> tuple[str, dict, dict]:
    agent = get_agent(model_name)
    input_messages = context_messages + [{"role": "user", "content": user_text}]

    result = agent.invoke({"messages": input_messages, "files": files or {}})
    all_messages = result.get("messages", [])

    reply = _last_text(all_messages)
    usage = _aggregate_usage(all_messages, len(input_messages), model_name)
    return reply, usage, result.get("files", {})
