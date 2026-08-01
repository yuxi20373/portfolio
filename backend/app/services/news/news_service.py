"""Orchestrates the news digest: scrape -> summarize -> store, plus the
read-side queries the News view calls (see app/routers/news.py).

Retention policy: only articles from the last NEWS_RETENTION_DAYS get
(re)scraped going forward; articles already stored are kept even once
they age past that window (they're just never topped up further back).
Only the title, publish time, and LLM summary are ever persisted - the
raw article text is discarded right after summarization.
"""

import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session as DBSession

from ... import models
from ...config import settings
from ...database import SessionLocal
from . import news_summary_service
from .news_sources import SOURCES

_scrape_lock = threading.Lock()
_UTC = ZoneInfo("UTC")


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.news_timezone)


def _local_now() -> datetime:
    return datetime.now(_tz())


def _ran_at_local_date(ran_at: datetime):
    # ran_at is stored naive (datetime.utcnow()) - anchor it as UTC, then convert
    return ran_at.replace(tzinfo=_UTC).astimezone(_tz()).date()


def has_run_today(db: DBSession) -> bool:
    last = db.query(models.NewsScrapeLog).order_by(models.NewsScrapeLog.ran_at.desc()).first()
    if not last:
        return False
    return _ran_at_local_date(last.ran_at) == _local_now().date()


def should_lazy_run(db: DBSession) -> bool:
    """Gate for the catch-up trigger on GET /api/news/overview: only fire
    once we're past the configured hour, and only once per local day."""
    if has_run_today(db):
        return False
    return _local_now().hour >= settings.news_digest_hour


def _ensure_source_settings(db: DBSession) -> None:
    existing = {row[0] for row in db.query(models.NewsSourceSetting.source_key).all()}
    for s in SOURCES:
        if s["key"] not in existing:
            db.add(models.NewsSourceSetting(source_key=s["key"], enabled=True))
    db.commit()


def _is_source_enabled(db: DBSession, key: str) -> bool:
    row = db.query(models.NewsSourceSetting).filter(models.NewsSourceSetting.source_key == key).first()
    return row.enabled if row else True


def set_source_enabled(db: DBSession, key: str, enabled: bool) -> None:
    _ensure_source_settings(db)
    row = db.query(models.NewsSourceSetting).filter(models.NewsSourceSetting.source_key == key).first()
    if row:
        row.enabled = enabled
        db.commit()


def set_source_pinned(db: DBSession, key: str, pinned: bool) -> None:
    _ensure_source_settings(db)
    row = db.query(models.NewsSourceSetting).filter(models.NewsSourceSetting.source_key == key).first()
    if row:
        row.pinned = pinned
        db.commit()


def run_scrape_job(force: bool = False) -> None:
    """Safe to call from APScheduler, a BackgroundTasks catch-up trigger, or
    the manual /api/news/refresh endpoint - overlapping calls are dropped
    rather than queued, and (unless force=True) a call is a no-op if
    today's run already happened. Scrapes every ENABLED source in turn (see
    the News sidebar's schedule toggle / NewsSourceSetting) - one source
    failing doesn't stop the others (see _do_scrape)."""
    if not _scrape_lock.acquire(blocking=False):
        return
    try:
        db = SessionLocal()
        try:
            if not force and has_run_today(db):
                return
            _ensure_source_settings(db)
            for source in SOURCES:
                if _is_source_enabled(db, source["key"]):
                    _do_scrape(db, source)
        finally:
            db.close()
    finally:
        _scrape_lock.release()


def _do_scrape(db: DBSession, source: dict) -> None:
    cutoff = _local_now().date() - timedelta(days=settings.news_retention_days)

    try:
        listing = source["fetch_listing"](source["listing_url"], source["listing_pages"])
    except Exception:
        db.add(models.NewsScrapeLog(source_key=source["key"], status="error", new_articles_count=0))
        db.commit()
        return

    existing_urls = {row[0] for row in db.query(models.NewsArticle.source_url).all()}
    new_count = 0

    for item in listing:
        if item["url"] in existing_urls:
            continue

        if item.get("date_str"):
            try:
                if datetime.strptime(item["date_str"], "%Y-%m-%d").date() < cutoff:
                    continue
            except ValueError:
                pass

        try:
            detail = source["fetch_article"](item["url"])
        except Exception:
            continue

        published_at = detail["published_at"] or _local_now().replace(tzinfo=None)
        if published_at.date() < cutoff or not detail["content_text"]:
            continue

        try:
            title, summary_md = news_summary_service.summarize_article(detail["title"] or item["title"], detail["content_text"])
        except Exception:
            continue

        db.add(
            models.NewsArticle(
                source_key=source["key"],
                source_name=source["name"],
                source_url=item["url"],
                title=title,
                published_at=published_at,
                summary_md=summary_md,
            )
        )
        existing_urls.add(item["url"])
        new_count += 1
        db.commit()  # incremental commit - a mid-run failure keeps what's already summarized

    db.add(models.NewsScrapeLog(source_key=source["key"], status="ok", new_articles_count=new_count))
    db.commit()


def list_sources(db: DBSession) -> list[dict]:
    _ensure_source_settings(db)
    rows = {r.source_key: r for r in db.query(models.NewsSourceSetting).all()}
    return [
        {"key": s["key"], "name": s["name"], "enabled": rows[s["key"]].enabled, "pinned": rows[s["key"]].pinned}
        for s in SOURCES
    ]


def _brief(a: models.NewsArticle) -> dict:
    return {"id": a.id, "title": a.title, "published_at": a.published_at, "source_name": a.source_name}


def _full(a: models.NewsArticle) -> dict:
    return {
        **_brief(a),
        "summary_md": a.summary_md,
        "source_url": a.source_url,
        "source_name": a.source_name,
    }


def _build_overview(articles: list[models.NewsArticle]) -> dict:
    if not articles:
        return {"featured_date": None, "featured": [], "other_days": []}

    featured_date = articles[0].published_at.date()
    # oldest -> newest within the featured day, so the carousel reads chronologically
    featured = [_full(a) for a in articles if a.published_at.date() == featured_date]
    featured.reverse()

    by_day: dict[str, list] = {}
    day_order: list[str] = []
    for a in articles:
        d = a.published_at.date()
        if d == featured_date:
            continue
        key = d.isoformat()
        if key not in by_day:
            by_day[key] = []
            day_order.append(key)
        by_day[key].append(_brief(a))

    return {
        "featured_date": featured_date.isoformat(),
        "featured": featured,
        # Timeline default window - see _build_week for browsing further back.
        "other_days": [{"date": k, "articles": by_day[k]} for k in day_order[:7]],
    }


def get_overview(db: DBSession, source_key: str) -> dict:
    articles = (
        db.query(models.NewsArticle)
        .filter(models.NewsArticle.source_key == source_key)
        .order_by(models.NewsArticle.published_at.desc())
        .all()
    )
    return _build_overview(articles)


def get_favorites_overview(db: DBSession) -> dict:
    articles = (
        db.query(models.NewsArticle)
        .filter(models.NewsArticle.is_favorited.is_(True))
        .order_by(models.NewsArticle.published_at.desc())
        .all()
    )
    return _build_overview(articles)


def _week_bounds(date_str: str):
    """Any date -> (monday, sunday) of that ISO week."""
    picked = datetime.strptime(date_str, "%Y-%m-%d").date()
    monday = picked - timedelta(days=picked.weekday())
    return monday, monday + timedelta(days=6)


def _build_week(articles: list[models.NewsArticle], monday, sunday) -> dict:
    by_day: dict[str, list] = {}
    day_order: list[str] = []
    for a in articles:
        key = a.published_at.date().isoformat()
        if key not in by_day:
            by_day[key] = []
            day_order.append(key)
        by_day[key].append(_brief(a))

    return {
        "start": monday.isoformat(),
        "end": sunday.isoformat(),
        "days": [{"date": k, "articles": by_day[k]} for k in day_order],
    }


def get_week(db: DBSession, source_key: str, date_str: str) -> dict:
    """A specific Monday-Sunday week's articles, grouped by day, for the
    News view's week-picker popover. `date_str` can be any day in the
    target week - the week is always computed as Monday-Sunday."""
    monday, sunday = _week_bounds(date_str)
    articles = (
        db.query(models.NewsArticle)
        .filter(
            models.NewsArticle.source_key == source_key,
            models.NewsArticle.published_at >= datetime.combine(monday, datetime.min.time()),
            models.NewsArticle.published_at < datetime.combine(sunday + timedelta(days=1), datetime.min.time()),
        )
        .order_by(models.NewsArticle.published_at.desc())
        .all()
    )
    return _build_week(articles, monday, sunday)


def get_favorites_week(db: DBSession, date_str: str) -> dict:
    monday, sunday = _week_bounds(date_str)
    articles = (
        db.query(models.NewsArticle)
        .filter(
            models.NewsArticle.is_favorited.is_(True),
            models.NewsArticle.published_at >= datetime.combine(monday, datetime.min.time()),
            models.NewsArticle.published_at < datetime.combine(sunday + timedelta(days=1), datetime.min.time()),
        )
        .order_by(models.NewsArticle.published_at.desc())
        .all()
    )
    return _build_week(articles, monday, sunday)


def get_article(db: DBSession, article_id: int):
    return db.query(models.NewsArticle).filter(models.NewsArticle.id == article_id).first()


def set_article_favorited(db: DBSession, article_id: int, favorited: bool):
    article = get_article(db, article_id)
    if not article:
        return None
    article.is_favorited = favorited
    db.commit()
    return article
