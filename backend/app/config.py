from pathlib import Path

from pydantic_settings import BaseSettings

try:
    from dotenv import load_dotenv

    # backend/app/config.py -> parent = backend/app, parent.parent = backend
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


class Settings(BaseSettings):
    # Groq (free) - used for lightweight background tasks, and optionally as
    # the interactive agent's model
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    groq_summarize_model: str = "llama-3.1-8b-instant"

    # OpenAI - optional alternative provider
    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"

    # Anthropic (Claude) - optional alternative provider
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"

    # Which provider powers lightweight one-shot calls (title generation,
    # semantic search ranking, wiki summarization, memory compaction)
    llm_provider: str = "groq"  # "groq" | "openai" | "anthropic"

    # Which provider powers the interactive deep agent (the actual chat)
    agent_model_provider: str = "groq"  # "groq" | "openai" | "anthropic"

    # Web search tool used by the agent. If unset, falls back to a key-less
    # DuckDuckGo search instead of Tavily.
    tavily_api_key: str = ""

    # Langfuse (optional) - traces every chat turn and is the source of
    # truth for cost (there is no local pricing table). Leave the keys
    # blank to disable; tokens still show either way (from the LLM
    # response directly), cost just shows "N/A".
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    database_url: str = "sqlite:///./data.db"

    # For channels without an explicit session boundary (e.g. LINE), how many
    # minutes of inactivity before a new conversation session is started.
    session_timeout_minutes: int = 1440

    # Short-term memory compaction (per-session, keeps input tokens down):
    # once more than `memory_compact_trigger` un-summarized messages pile up,
    # everything except the most recent `memory_recent_window` is folded
    # into a rolling summary instead of being resent verbatim.
    memory_recent_window: int = 12
    memory_compact_trigger: int = 20

    # LINE Bot
    line_channel_secret: str = ""
    line_channel_access_token: str = ""

    # Comma-separated list of origins allowed to call this API (your deployed
    # frontend's URL, e.g. "https://your-app.vercel.app"). Defaults to "*"
    # (allow everything) so local development just works out of the box.
    cors_allowed_origins: str = "*"

    # --- News digest (multi-source scraper + LLM summary; sources
    # themselves are configured in app/services/news/news_sources.py, not
    # here - see app/services/news/news_service.py) ---
    news_retention_days: int = 14
    # Local hour (0-23, NEWS_TIMEZONE) the daily scrape job runs at.
    news_digest_hour: int = 7
    news_timezone: str = "Asia/Taipei"
    # Optional shared secret for POST /api/news/refresh's X-Cron-Secret
    # header (e.g. an external uptime pinger). Leave blank to allow anyone.
    news_cron_secret: str = ""

    # --- AsiaYo hotel-search proxy (separately-deployed external service,
    # see app/routers/hotel_search.py) - the API key is kept server-side and
    # never shipped to the frontend bundle. ---
    asiayo_api_base_url: str = "https://asiayo-scraper-api.onrender.com"
    asiayo_api_key: str = ""

    # --- Bright Data Airbnb "discover by location" scraper (Dataset API) -
    # see app/routers/airbnb_search.py. No built-in caching on their end
    # (unlike AsiaYo above), so this app caches results itself to stay
    # within the free tier. ---
    brightdata_api_token: str = ""
    brightdata_airbnb_dataset_id: str = "gd_ld7ll037kqy322v05"
    # 每次搜尋(不管搜幾個地點)總共抓幾筆,平均分給每個地點當各自的
    # limit_per_input(見 routers/airbnb_search.py 的 _trigger_body)- 免費
    # 額度 5K records/月,200 筆/次代表大概可以搜 25 次。
    airbnb_search_total_limit: int = 200
    # 同樣的地點組合+日期+人數,這麼多天內都直接吃快取(資料庫裡的舊結果),
    # 不重新觸發 Bright Data。
    airbnb_search_cache_days: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore unrelated env vars


settings = Settings()
