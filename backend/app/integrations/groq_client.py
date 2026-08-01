import requests

from ..config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def chat_completion(messages, model: str = None, temperature: float = 0.7, timeout: int = 60) -> str:
    """Call Groq's OpenAI-compatible chat completions endpoint. Returns the reply text."""
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. "
            "Get a free key at https://console.groq.com and put it in backend/.env"
        )

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or settings.groq_model,
        "messages": messages,
        "temperature": temperature,
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
