"""Standalone deep agent service: a single stateless endpoint that runs one
turn of the two-layer (1DA + worker) deep agent and returns the reply plus
the updated virtual filesystem. No database, no session management, no
frontend - the caller (your own backend) owns persisting conversation
history and the `files` dict between calls; see README.md."""

from fastapi import FastAPI

from .runner import run_turn
from .schemas import InvokeRequest, InvokeResponse

app = FastAPI(title="Deep Agent Service")


@app.post("/invoke", response_model=InvokeResponse)
def invoke(payload: InvokeRequest):
    reply, files, tool_calls = run_turn(
        [m.model_dump() for m in payload.messages],
        payload.files,
    )
    return InvokeResponse(reply=reply, files=files, tool_calls=tool_calls)


@app.get("/health")
def health():
    return {"ok": True}
