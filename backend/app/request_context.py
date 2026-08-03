"""Ambient per-request context that plain function-signature dependency
injection can't reach - specifically, the deep agent's tools (see
app/agent/tools/wiki_manage.py) are shared, stateless LangChain @tool
objects with a fixed signature the LLM calls, so there's no way to pass
"which logged-in account is this turn for" through a normal argument. A
contextvar is the standard way to thread that in ambiently: set once per
request (see app/services/chat/chat_service.py:process_chat_message), read
inside the tool while it's running in that same request's call stack."""

from contextvars import ContextVar

current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)
