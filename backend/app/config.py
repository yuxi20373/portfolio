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

    # --- Apify "automation-lab/airbnb-listing" actor (取代原本的 Bright
    # Data)- 見 app/routers/airbnb_search.py。跟 Bright Data 不同,Apify 這支
    # actor 原生支援 priceMin/priceMax(server-side 篩選,不用整批抓回來自己
    # 篩),但沒有評價/評論數篩選欄位,那塊還是前端 client-side 排序/取前
    # TOP_N(見 HotelSearchView.js)。Apify 沒有內建快取,所以跟原本一樣自己
    # 存 cache。 ---
    apify_api_token: str = ""
    apify_airbnb_actor_id: str = "automation-lab~airbnb-listing"
    # 單次搜尋最多收幾筆(對應 actor 的 maxListings)- 免費方案每月 $5 平台額度,
    # 200 筆/次大概可以搜 30-40 次(依實際用量而定)。
    airbnb_search_total_limit: int = 200
    # 對應 actor 的 maxRequestsPerCrawl - 避免爬蟲卡在分頁/價格區間二分搜尋
    # 燒過多 request 額度,跟 airbnb_search_total_limit 是各自獨立的上限。
    airbnb_search_max_requests: int = 100
    # 同樣的地點組合+日期+人數,這麼多天內都直接吃快取(資料庫裡的舊結果),
    # 不重新觸發 Apify。
    airbnb_search_cache_days: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore unrelated env vars


settings = Settings()
