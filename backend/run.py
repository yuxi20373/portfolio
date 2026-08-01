"""Development entry point. Run with: python run.py (from the backend/ directory).

Render (or any host that sets PORT) can also use this directly, though the
canonical production start command is the plain uvicorn one in render.yaml:
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    is_local_dev = "PORT" not in os.environ
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=is_local_dev)
