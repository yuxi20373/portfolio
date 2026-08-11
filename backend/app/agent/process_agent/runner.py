"""Runs one turn of the "process_agent" experimental deep agent. Same
interface convention as ../orchestrator/runner.py (context_messages +
user_text in, (reply, usage, files) out) so chat_service.py's dispatch
doesn't need to know which experimental implementation it's calling - see
EXPERIMENTAL_AGENTS there.

`files` here is the top-level agent's own virtual filesystem (carried
across turns via ChatSession.process_agent_files) - separate from each
individual process agent worker thread's checkpointed state (see tools.py's
_process_agent_checkpointer), which persists in this process's memory
independently of anything this app stores in its own database.
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
