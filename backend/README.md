# Knowledge Chatbot - Backend

FastAPI + a LangGraph deep agent (`deepagents`), SQLite. Deploys
independently on **Render**; the frontend (Vercel) talks to this over
HTTP/CORS and is not served from here.

## Architecture

```
backend/
├── run.py                  # dev entry point: python run.py
├── render.yaml              # Render blueprint (build/start commands, env var list)
├── requirements.txt
├── .env.example
└── app/
    ├── main.py               # FastAPI app, routers, CORS, health check
    ├── config.py              # env/.env settings (pydantic-settings)
    ├── database.py            # SQLAlchemy engine/session
    ├── models/                # ORM models (chat.py, wiki.py incl. WikiFolder, note.py)
    ├── schemas/                # Pydantic request/response models
    ├── agent/                  # the deep agent (LangGraph / deepagents)
    │   ├── agent_factory.py     # builds + caches the agent, model/provider selection
    │   ├── memory_manager.py    # rolling short-term-memory compaction
    │   ├── runner.py            # runs one agent turn, normalizes the reply
    │   ├── skills/               # SKILL.md files loaded when relevant
    │   └── tools/                 # web_search, update_wiki
    ├── services/                # business logic (chat, wiki search/adjust, search, titles, weather)
    ├── routers/                 # thin FastAPI route handlers
    ├── integrations/            # groq/openai/langfuse/line clients
    └── utils/                   # small shared helpers
```

## Local dev

```bash
conda create -n knowledge-chatbot python=3.11 -y
conda activate knowledge-chatbot
pip install -r requirements.txt

cp .env.example .env
# at minimum, set GROQ_API_KEY (free: https://console.groq.com/keys)

python run.py   # -> http://localhost:8000
```

Try `curl http://localhost:8000/` - should return `{"status": "ok", ...}`.

## Deploying on Render

1. Push this repo to GitHub/GitLab.
2. Render dashboard -> **New +** -> **Blueprint** -> point it at the repo.
   Render will read `render.yaml` (root directory is already set to
   `backend` in that file). Alternatively, create a **Web Service**
   manually with root directory `backend`, build command
   `pip install -r requirements.txt`, start command
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. In the service's **Environment** tab, fill in the real values for at
   least `GROQ_API_KEY` (the blueprint marks secrets as `sync: false` so
   you enter them in the dashboard, not in git).
4. Deploy, then copy the resulting URL (e.g.
   `https://knowledge-chatbot-backend.onrender.com`) - the frontend's
   `API_BASE_URL` env var (see `frontend/README.md`) needs this.
5. Once the frontend is deployed too, come back and set
   `CORS_ALLOWED_ORIGINS` to that Vercel URL instead of `*`.

**SQLite persistence**: Render's free plan filesystem is ephemeral - your
data (`data.db`) gets wiped on every redeploy/restart. For real long-term
use, either upgrade and mount a [persistent
disk](https://render.com/docs/disks) (see the commented-out `disk:` block
in `render.yaml` and update `DATABASE_URL` to point at the mounted path),
or migrate to a managed Postgres instance.

## Environment variables

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` / `GROQ_MODEL` / `GROQ_SUMMARIZE_MODEL` | Groq (free tier) |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI (optional alternative) |
| `LLM_PROVIDER` | `groq` \| `openai` - one-shot calls (title/search/adjust/memory-compaction) |
| `AGENT_MODEL_PROVIDER` | `groq` \| `openai` - the interactive deep agent |
| `TAVILY_API_KEY` | optional, better web search; unset = key-less DuckDuckGo |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | optional; token/cost tracking per reply |
| `DATABASE_URL` | SQLite by default; see persistence note above |
| `SESSION_TIMEOUT_MINUTES` | LINE/other boundary-less channels: idle time before a new session starts |
| `MEMORY_RECENT_WINDOW` / `MEMORY_COMPACT_TRIGGER` | short-term memory compaction thresholds |
| `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot |
| `CORS_ALLOWED_ORIGINS` | comma-separated allowed origins; `*` by default |

## How it works

**Deep agent, not a plain chat loop.** `app/agent/agent_factory.py` builds
the assistant with `deepagents.create_deep_agent()` (LangGraph-based,
planning + tool use built in). `chat_service.py` never calls an LLM
directly - it builds context and calls `app/agent/runner.py`. No
LangGraph checkpointer is used for state; the SQL database is the single
source of truth for conversation history, since calendar/rename/delete
already depend on it - each turn gets a freshly-built message list.

**Tools**: `web_search` (Tavily if `TAVILY_API_KEY` is set, otherwise
key-less DuckDuckGo) and `update_wiki` (lets the agent save/update a wiki
entry mid-conversation, but only when explicitly asked - see
`app/agent/skills/wiki-management/SKILL.md`). A second skill,
`tool-calling-format`, nudges smaller/weaker models toward correctly
formed tool calls.

**Short-term memory**: `app/agent/memory_manager.py` keeps the most
recent `MEMORY_RECENT_WINDOW` messages verbatim and folds anything older
into a rolling `ChatSession.memory_summary` once `MEMORY_COMPACT_TRIGGER`
un-summarized messages pile up - keeps per-turn input tokens down without
losing earlier context. Raw messages are never deleted.

**Wiki**: entries are only created/updated on explicit action - never an
automatic background summarizer. Three LLM-assisted paths (chat's
`update_wiki` tool, the Search panel's web-search-plus-question flow, and
the Adjust drawer's propose-then-confirm natural-language edits) all write
structured content using the same `entry_type` section templates
(`app/services/wiki_templates.py`) and a shared formatting guidance block
that encourages tables/arrows/`<mark>` highlights over walls of prose.
Search is strictly additive (never removes existing content); Adjust is
the only path allowed to trim/restructure, and only via an explicit
instruction you approve before it's saved. Entries can also be edited
directly (no LLM) and organized into folders you create and move entries
into yourself - `entry_type` only affects which headings get used when
content is (re)generated, it's unrelated to folder organization.

**Calendar**: `/api/calendar` and `/api/calendar/day` group conversations,
wiki entries, and notes by creation date. `/api/weather?date=YYYY-MM-DD`
(`app/services/weather_service.py`) returns a simple rain/no-rain signal
for Taichung via [Open-Meteo](https://open-meteo.com) - free, no API key,
no config needed. It tries the regular forecast endpoint first (covers
recent past through ~16 days ahead) and falls back to the historical
archive endpoint for older dates; if neither has data it returns
`will_rain: null` rather than guessing. The frontend just needs a
boolean-ish signal to pick an animated icon, so that's all this returns -
see the function if you want more detail (temperature, etc).

**Cost tracking**: `app/integrations/langfuse_client.py` attaches a
Langfuse callback to every agent turn and best-effort polls for that
turn's cost right after (Langfuse ingests asynchronously, so this can
occasionally show "N/A" if it's not ready in time - the trace is still on
your Langfuse dashboard either way). Token counts come straight from the
LLM response, so those are always instant regardless.

**LINE Bot**: `routers/line.py` reuses the exact same
`chat_service.get_or_create_session` / `process_chat_message` as the web
UI. See the LINE section below to connect one.

## Connecting a LINE Bot

1. Create a **Messaging API** channel in the [LINE Developers
   Console](https://developers.line.biz/), grab the **Channel secret** and
   a **Channel access token (long-lived)**, and set them as env vars.
2. Set the webhook URL to `https://<your-render-url>/api/line/webhook` and
   enable "Use webhook".
3. Message the bot - it verifies the signature, resolves/creates that
   user's session (a new one starts automatically after
   `SESSION_TIMEOUT_MINUTES` of inactivity), and replies via the deep
   agent.

## Notes

- No auth on the API - fine for personal use behind an obscure URL, not
  fine for anything public. Add auth before sharing the URL around.
- `langgraph`, `deepagents`, `langchain-core`, `langchain-groq`, and
  `langchain-openai` move fast and aren't version-pinned in
  `requirements.txt`; if a `pip install` pulls a breaking change, the
  surface area this project touches (`create_deep_agent`, `@tool`,
  `ChatGroq`/`ChatOpenAI`) is small and localized to `app/agent/`.
- Groq's free tier and model names change over time; check
  https://console.groq.com if you hit a 429 or unknown-model error.
