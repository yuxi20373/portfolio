from pathlib import Path

from pydantic_settings import BaseSettings

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


class Settings(BaseSettings):
    # Which provider powers the interactive deep agent (1DA + worker)
    agent_model_provider: str = "groq"  # "groq" | "openai"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"

    # Web search tool. If unset, falls back to key-less DuckDuckGo search.
    tavily_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
