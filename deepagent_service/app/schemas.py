from typing import Any, Literal

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class InvokeRequest(BaseModel):
    """`messages` is the full conversation so far, including the new user
    message as the last entry - this service is stateless, it doesn't store
    or look up history itself. `files` is whatever this service returned as
    `files` on the previous call for this conversation (omit/empty on the
    first call) - pass it back unchanged each time so the deep agent's
    virtual filesystem (e.g. a worker's prior output under /results/) stays
    available across calls."""

    messages: list[Message]
    files: dict[str, Any] = {}


class InvokeResponse(BaseModel):
    reply: str
    files: dict[str, Any]
    tool_calls: list[dict[str, Any]]
