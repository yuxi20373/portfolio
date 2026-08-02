"""Runs one turn of the deep agent given the already-compacted context
(app/agent/memory_manager.py) plus the new user message, and normalizes the
result back down to a plain reply string plus a token-usage summary for the
rest of the app. Token counts come straight from the LLM response (always
available instantly); cost is tracked separately via Langfuse
(app/integrations/langfuse_client.py), not computed here."""

from .agent_factory import get_agent, default_model_name


def run_turn(
    context_messages: list[dict], user_text: str, callbacks=None, run_id=None, model_name: str = None
) -> tuple[str, dict]:
    agent = get_agent(model_name)
    input_messages = context_messages + [{"role": "user", "content": user_text}]

    config = {}
    if callbacks:
        config["callbacks"] = callbacks
    if run_id:
        config["run_id"] = run_id

    result = agent.invoke({"messages": input_messages}, config=config)
    all_messages = result.get("messages", [])

    reply = _last_text(all_messages)
    usage = _aggregate_usage(all_messages, len(input_messages), model_name)
    return reply, usage


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


def _aggregate_usage(all_messages, input_message_count: int, model_name: str = None) -> dict:
    """Sums token usage across every model call made during this turn (a
    turn can involve more than one LLM round-trip when the agent uses
    tools) - this is the true total cost of the turn, even if some input
    tokens get counted more than once across calls, since you really are
    billed for each call's full context."""
    # Only look at messages generated during this invocation, not the
    # history we passed in (which are plain dicts with no usage_metadata
    # anyway, but be explicit about intent).
    new_messages = all_messages[input_message_count:] if len(all_messages) > input_message_count else all_messages

    total_input = 0
    total_output = 0
    reported_model = None

    for m in new_messages:
        usage = getattr(m, "usage_metadata", None)
        if usage:
            total_input += usage.get("input_tokens", 0) or 0
            total_output += usage.get("output_tokens", 0) or 0
        meta = getattr(m, "response_metadata", None) or {}
        reported_model = reported_model or meta.get("model_name") or meta.get("model")

    return {
        "model": reported_model or default_model_name(model_name),
        "input_tokens": total_input,
        "output_tokens": total_output,
    }
