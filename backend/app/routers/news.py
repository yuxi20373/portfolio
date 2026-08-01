from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from ..config import settings
from ..database import get_db
from ..services.news import news_service

router = APIRouter(prefix="/api/news", tags=["news"])


class SourceUpdate(BaseModel):
    enabled: Optional[bool] = None
    pinned: Optional[bool] = None


class FavoriteUpdate(BaseModel):
    favorited: bool


@router.get("/sources")
def news_sources(db: DBSession = Depends(get_db)):
    """The configured source list (key, display name, whether it's in the
    daily schedule, and whether it's pinned to the top) for the News
    sidebar - see app/services/news/news_sources.py."""
    return news_service.list_sources(db)


@router.patch("/sources/{key}")
def update_source(key: str, payload: SourceUpdate, db: DBSession = Depends(get_db)):
    """Toggles a source's daily-schedule switch and/or pinned state (see the
    sidebar's switch and pin icon). Disabling a source only stops future
    scraping - already-stored articles stay browsable."""
    if payload.enabled is not None:
        news_service.set_source_enabled(db, key, payload.enabled)
    if payload.pinned is not None:
        news_service.set_source_pinned(db, key, payload.pinned)
    return next((s for s in news_service.list_sources(db) if s["key"] == key), None)


@router.get("/week")
def news_week(source: str, date: str, db: DBSession = Depends(get_db)):
    """One Monday-Sunday week's articles for the News view's week-picker
    popover. `date` can be any day in the target week."""
    return news_service.get_week(db, source, date)


@router.get("/overview")
def news_overview(source: str, background_tasks: BackgroundTasks, db: DBSession = Depends(get_db)):
    """Today's (or the latest available day's) articles for one source's
    featured carousel, plus older days for the grid below. Also the main
    catch-up trigger: on Render's free plan the process can be asleep at
    the scheduled hour, so simply opening this view after that hour kicks
    off a background scrape (of every source) if one hasn't run yet today."""
    if news_service.should_lazy_run(db):
        background_tasks.add_task(news_service.run_scrape_job)
    return news_service.get_overview(db, source)


@router.get("/favorites")
def news_favorites(db: DBSession = Depends(get_db)):
    """Favorited articles across every source, in the same shape as
    /overview - pinned at the top of the News sidebar."""
    return news_service.get_favorites_overview(db)


@router.get("/favorites/week")
def news_favorites_week(date: str, db: DBSession = Depends(get_db)):
    return news_service.get_favorites_week(db, date)


@router.get("/articles/{article_id}")
def news_article(article_id: int, db: DBSession = Depends(get_db)):
    article = news_service.get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {
        "id": article.id,
        "title": article.title,
        "published_at": article.published_at,
        "summary_md": article.summary_md,
        "source_url": article.source_url,
        "source_name": article.source_name,
        "is_favorited": article.is_favorited,
    }


@router.patch("/articles/{article_id}/favorite")
def update_article_favorite(article_id: int, payload: FavoriteUpdate, db: DBSession = Depends(get_db)):
    article = news_service.set_article_favorited(db, article_id, payload.favorited)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"id": article.id, "is_favorited": article.is_favorited}


@router.post("/refresh")
def news_refresh(background_tasks: BackgroundTasks, x_cron_secret: str = Header(default="")):
    """Manual/external trigger (e.g. an uptime pinger or external cron
    hitting this on a schedule) - runs even if today's job already ran."""
    if settings.news_cron_secret and x_cron_secret != settings.news_cron_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Cron-Secret header")
    background_tasks.add_task(news_service.run_scrape_job, True)
    return {"status": "scheduled"}
