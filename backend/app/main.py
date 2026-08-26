import atexit

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (import registers models with Base.metadata)
from .config import settings
from .routers import auth, chat, wiki, calendar, search, notes, memos, weather, line, news, emoji, events, hotel_search, airbnb_search, profile, models as models_router, test_agent_skills, bash_reference
from .services.news import news_service

# Schema is owned entirely by Alembic now (backend/alembic/) - there is no
# create_all()/ad-hoc ALTER TABLE fallback here anymore, since mixing the
# two is exactly how schema drift happens. Run `alembic upgrade head`
# (locally, and via Render's Pre-Deploy Command in production - see
# render.yaml) before starting the app whenever models change.

app = FastAPI(title="Knowledge Chatbot API")

# CORS_ALLOWED_ORIGINS in .env is a comma-separated list (e.g.
# "https://your-app.vercel.app,http://localhost:5500"). Defaults to "*" so
# local development just works; tighten this once you know your deployed
# frontend's URL.
_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(wiki.router)
app.include_router(calendar.router)
app.include_router(search.router)
app.include_router(notes.router)
app.include_router(memos.router)
app.include_router(weather.router)
app.include_router(line.router)
app.include_router(news.router)
app.include_router(emoji.router)
app.include_router(events.router)
app.include_router(hotel_search.router)
app.include_router(airbnb_search.router)
app.include_router(profile.router)
app.include_router(models_router.router)
app.include_router(test_agent_skills.router)
app.include_router(bash_reference.router)

# NOTE: Wiki entries are only ever created/updated on explicit user action -
# via chat (the update_wiki agent tool), the Search panel, or the Adjust
# panel in the Knowledge base view. See
# app/services/wiki/wiki_search_service.py and
# app/services/wiki/wiki_adjust_service.py.
#
# The one exception is the news digest: a daily background scrape+summarize
# job (see app/services/news/news_service.py). NEWS_DIGEST_HOUR/NEWS_TIMEZONE in
# .env control when it fires; GET /api/news/overview also triggers a
# catch-up run if the scheduled hour has passed and today's job hasn't run
# yet (needed on hosts like Render's free tier where the process can be
# asleep at the scheduled time).
_news_scheduler = BackgroundScheduler(timezone=settings.news_timezone)
_news_scheduler.add_job(
    news_service.run_scrape_job,
    CronTrigger(hour=settings.news_digest_hour, minute=0),
    id="news_daily_digest",
)
_news_scheduler.start()
atexit.register(lambda: _news_scheduler.shutdown(wait=False))

# The frontend is deployed separately (e.g. on Vercel) and talks to this API
# over HTTP/CORS - this backend no longer serves any static files itself.
# This root route just gives Render (or any host) something to health-check.


@app.get("/")
def health_check():
    return {"status": "ok", "service": "knowledge-chatbot-backend"}
