from openai import OpenAI

from ..config import settings


def chat_completion(messages: list, model: str = None) -> str:
    """One-shot completion via OpenAI. Used for lightweight background tasks
    (title generation, search ranking, wiki summarization, memory compaction)
    when LLM_PROVIDER=openai - not used by the interactive deep agent, which
    talks to the model through langchain-openai instead (see app/agent/)."""
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. Set it in backend/.env, "
            'or switch LLM_PROVIDER/AGENT_MODEL_PROVIDER back to "groq".'
        )

    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model=model or settings.openai_model,
        messages=list(messages),
        max_completion_tokens=2048,
        reasoning_effort="low",
    )

    return response.choices[0].message.content
