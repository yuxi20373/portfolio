from anthropic import Anthropic

from ..config import settings


def chat_completion(messages: list, model: str = None) -> str:
    """One-shot completion via Anthropic (Claude). Used for lightweight
    background tasks (title generation, search ranking, wiki summarization,
    memory compaction) when LLM_PROVIDER=anthropic - not used by the
    interactive deep agent, which talks to the model through
    langchain-anthropic instead (see app/agent/).

    Claude has no "system" role inside `messages` - any leading system-role
    dicts (this app always builds messages as [system?, user, ...]) are
    pulled out into the top-level `system` param instead. Effort is kept low
    (rather than disabling thinking outright, which on Claude Opus 5 can
    leak stray tool-call text or <thinking> tags into the reply) since these
    are quick, non-agentic one-shot calls."""
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. Set it in backend/.env, "
            'or switch LLM_PROVIDER/AGENT_MODEL_PROVIDER back to "groq" or "openai".'
        )

    client = Anthropic(api_key=settings.anthropic_api_key)

    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    conversation = [m for m in messages if m["role"] != "system"]

    kwargs = dict(
        model=model or settings.anthropic_model,
        max_tokens=2048,
        output_config={"effort": "low"},
        messages=conversation,
    )
    if system_parts:
        kwargs["system"] = "\n\n".join(system_parts)

    response = client.messages.create(**kwargs)

    return "".join(block.text for block in response.content if block.type == "text")
