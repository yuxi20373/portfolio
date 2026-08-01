# Knowledge Chatbot

A chatbot with a LangGraph deep agent (tool use + short-term memory
compaction), a user-driven wiki knowledge base, and a calendar of
conversations/wiki entries/Markdown notes.

The frontend (Vue 3 via CDN, no build tooling) and backend (FastAPI) are
independently deployable - frontend on **Vercel**, backend on **Render** -
but live in this one repo as sibling folders.

```
knowledge-chatbot/
├── backend/    FastAPI + LangGraph deep agent + SQLite  -> deploy on Render
│   └── README.md   full setup, architecture, and Render deployment guide
└── frontend/   Vue 3 (CDN) SPA, no build step required   -> deploy on Vercel
    └── README.md   local dev and Vercel deployment guide
```

## Quick local dev

```bash
# backend
cd backend
conda create -n knowledge-chatbot python=3.11 -y && conda activate knowledge-chatbot
pip install -r requirements.txt
cp .env.example .env   # at minimum set GROQ_API_KEY
python run.py          # -> http://localhost:8000

# frontend (separate terminal) - any static file server works
cd frontend
python -m http.server 5500   # -> http://localhost:5500
```

By default the frontend talks to whatever origin it's served from
(`window.API_BASE_URL` is empty). For local dev with the frontend on a
different port than the backend, either serve them from the same origin,
or set `window.API_BASE_URL = "http://localhost:8000"` directly in
`frontend/assets/js/config.js` for testing.

## Deploying for real (Vercel + Render)

1. **Backend first** - see `backend/README.md`. Deploy to Render (root
   directory `backend`), set your API keys as env vars there, and note the
   resulting URL (e.g. `https://your-backend.onrender.com`).
2. **Frontend** - see `frontend/README.md`. Deploy to Vercel (root
   directory `frontend`), and set the `API_BASE_URL` environment variable
   to the Render URL from step 1.
3. Back in Render, set `CORS_ALLOWED_ORIGINS` to your Vercel URL (tighter
   than the "allow everything" default).

Each README has the exact dashboard steps.

## Feature highlights

- **Home page** - a themed landing view with a hero image and floating
  clickable images (drop your own transparent PNGs into
  `frontend/assets/images/` - falls back to plain icons until you do) that
  link to Wiki/Calendar and toggle light/dark mode.
- **Deep agent, not a plain chat loop** - `deepagents` (LangGraph) with a
  `web_search` tool and an `update_wiki` tool the agent can call when you
  explicitly ask it to save something.
- **Short-term memory compaction** - older turns get folded into a rolling
  summary instead of resending full history every time, to keep input
  tokens down.
- **User-driven wiki, not automatic** - entries are only created/updated
  via chat, the Search panel (web search + your question), the Adjust
  drawer (propose-then-confirm natural-language edits), or direct manual
  editing. Organize entries into folders you create yourself and move
  between manually.
- **Calendar** - month grid + day detail for conversations, wiki entries,
  and Markdown notes (with their own editor/preview and edit/delete), plus
  a Taichung rain/no-rain weather icon in the corner for whichever day is
  selected.
- **Token/cost tracking via Langfuse**, shown in the corner of each reply.
- **LINE Bot ready** - the same agent/session logic powers a LINE webhook.

Full details, env var reference, and troubleshooting notes live in
`backend/README.md`.
