from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime

from ..database import Base


class NewsArticle(Base):
    """One scraped+summarized article. Deliberately does NOT keep the
    original article text - only enough to render the digest UI (title,
    publish time, source link) plus the LLM-generated summary_md (Markdown:
    bullet points, **bold** highlights, and a table where the article has
    comparable/structured data). See app/services/news/news_service.py."""

    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    source_key = Column(String(50), index=True)  # e.g. "qbitai" - see app/services/news/news_sources.py
    source_name = Column(String(100))  # display label, e.g. "量子位"
    source_url = Column(String(500), unique=True, index=True)
    title = Column(String(500))
    published_at = Column(DateTime, index=True)  # from the article's own byline
    summary_md = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    is_favorited = Column(Boolean, default=False, index=True)


class NewsScrapeLog(Base):
    """Bookkeeping for the daily job - lets routers/news.py tell whether
    today's scrape already ran without re-hitting the source site on every
    request (see get_db/ensure_daily_scrape)."""

    __tablename__ = "news_scrape_log"

    id = Column(Integer, primary_key=True)
    source_key = Column(String(50), index=True)
    ran_at = Column(DateTime, default=datetime.utcnow)
    new_articles_count = Column(Integer, default=0)
    status = Column(String(20), default="ok")  # "ok" | "error"


class NewsSourceSetting(Base):
    """Per-source settings: whether it's included in the daily scheduled
    scrape (the sidebar's toggle switch), and whether it's pinned to the top
    of the sidebar's source list (the pin icon). Missing row = enabled,
    unpinned (see news_service.list_sources / _is_source_enabled)."""

    __tablename__ = "news_source_settings"

    source_key = Column(String(50), primary_key=True)
    enabled = Column(Boolean, default=True)
    pinned = Column(Boolean, default=False)
