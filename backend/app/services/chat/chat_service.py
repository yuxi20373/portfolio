import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from ... import models
from ...config import settings
from ...agent import memory_manager
from ...agent import runner as agent_runner
from ...agent import simple_chat
from ...agent.orchestrator import runner as orchestrator_runner
from ...agent.process_agent import runner as process_agent_runner
from ...agent.test_agent import runner as test_agent_runner
from ...integrations import langfuse_client
from ...request_context import current_user_id
from .title_service import generate_title

# 使用者在對話中打這兩個指令切換該 session 的模式（見 process_chat_message
# 開頭的判斷）。/agent 開啟 deep agent（完整歷史記憶 + 工具）；/normal 切回
# 一般模式（單輪快速回覆、無工具，但仍保留同 session 的短期記憶）。
AGENT_MODE_COMMAND = "/agent"
NORMAL_MODE_COMMAND = "/normal"

# 實驗性的 deep agent 實作 - 跟上面的 agent_mode 是分開獨立的一條路,不影響
# /agent 原本的行為。之後要多試別種實作,就在這三個字典各多加一個 key(+ 一個
# run_turn(context_messages, user_text, files, model_name) -> (reply, usage,
# files) 的函式),不用改這裡以外的東西。如果新實作也需要跨輪保留自己的
# files 狀態,ChatSession 要多加一欄,並在 FILES_COLUMN_BY_AGENT 註冊對應的
# 欄位名稱(不需要就不用加,留 None)。
#
# 目前有三種,前兩種是從獨立專案 deepagent_service/ 移植進來的:
# - orchestrator:主 agent 委派給預先註冊好的靜態 worker subagent(用
#   deepagents 內建的 task 工具),見 app/agent/orchestrator/。
# - process_agent:主 agent 有個 create_process_agent 工具,可以動態建立
#   獨立的 agent 實例(用 LangGraph checkpointer + 各自的 thread_id 隔離,
#   執行紀錄可以事後用 get_process_agent_thread 查回來),見
#   app/agent/process_agent/。
# - test_agent:fab/function 身分測試沙盒,不透過指令切換(session 建立時就
#   帶好 identities,見 routers/chat.py 的 create_test_agent_session),見
#   app/agent/test_agent/。不在 EXPERIMENTAL_AGENT_COMMANDS 裡,但 dispatch
#   還是走同一套 EXPERIMENTAL_AGENTS 機制。
EXPERIMENTAL_AGENT_COMMANDS = {
    "/test-subagent": "orchestrator",
    "/test-pa": "process_agent",
}
EXPERIMENTAL_AGENTS = {
    "orchestrator": orchestrator_runner.run_turn,
    "process_agent": process_agent_runner.run_turn,
    "test_agent": test_agent_runner.run_turn,
}
EXPERIMENTAL_AGENT_DESCRIPTIONS = {
    "orchestrator": "主 agent 委派給預先註冊的靜態 worker subagent（deepagents 的 task 工具）",
    "process_agent": "主 agent 可動態建立獨立 agent 實例（checkpointer + thread 隔離，可事後查詢）",
    "test_agent": "fab/function 身分測試沙盒",
}
FILES_COLUMN_BY_AGENT = {
    "orchestrator": "orchestrator_files",
    # process_agent/test_agent don't persist a files dict here - their
    # agents share one live store instead (namespaced by session_id), so
    # there's nothing for us to copy in/out or persist per turn - see
    # app/agent/process_agent/tools.py's module docstring.
    "process_agent": None,
    "test_agent": None,
}


def get_or_create_session(
    db: DBSession,
    channel: str,
    external_user_id: str = None,
    session_id: int = None,
    user_id: int = None,
) -> models.ChatSession:
    """
    Resolve which session (= scope of short-term memory) this message belongs to.

    - web: if a session_id is given, use it directly; otherwise start a new one.
    - line (or any channel without an explicit session boundary): reuse the
      user's most recent session if they spoke recently (within
      SESSION_TIMEOUT_MINUTES); otherwise start a new session, so context
      doesn't grow forever.

    user_id: the logged-in account (web channel only - see
    app/auth.py:get_current_user). When given, a session_id that doesn't
    exist or belongs to a different account raises ValueError instead of
    silently starting a new session or handing back someone else's
    conversation - routers/chat.py turns that into a 404.
    """
    if session_id is not None:
        s = db.query(models.ChatSession).get(session_id)
        if s:
            if user_id is not None and s.user_id != user_id:
                raise ValueError("session not found")
            return s
        if user_id is not None:
            raise ValueError("session not found")

    if external_user_id:
        cutoff = datetime.utcnow() - timedelta(minutes=settings.session_timeout_minutes)
        s = (
            db.query(models.ChatSession)
            .filter(
                models.ChatSession.channel == channel,
                models.ChatSession.external_user_id == external_user_id,
                models.ChatSession.is_open == True,  # noqa: E712
                models.ChatSession.last_message_at >= cutoff,
            )
            .order_by(models.ChatSession.last_message_at.desc())
            .first()
        )
        if s:
            return s

    s = models.ChatSession(title="New Conversation", channel=channel, external_user_id=external_user_id, user_id=user_id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _switch_mode(db: DBSession, session: models.ChatSession, user_text: str, agent_mode: bool, reply_text: str) -> str:
    session.agent_mode = agent_mode
    session.experimental_agent = None  # 跟實驗性模式互斥,切回 /agent 或 /normal 一律離開實驗模式
    db.add(models.ChatMessage(session_id=session.id, role="user", content=user_text))
    db.add(models.ChatMessage(session_id=session.id, role="assistant", content=reply_text))
    session.last_message_at = datetime.utcnow()
    db.commit()
    return reply_text


def _switch_experimental_agent(
    db: DBSession, session: models.ChatSession, user_text: str, agent_key: str, reply_text: str
) -> str:
    session.experimental_agent = agent_key
    session.agent_mode = False  # 跟 /agent 互斥,一次只有一種深度 agent 在跑
    db.add(models.ChatMessage(session_id=session.id, role="user", content=user_text))
    db.add(models.ChatMessage(session_id=session.id, role="assistant", content=reply_text))
    session.last_message_at = datetime.utcnow()
    db.commit()
    return reply_text


def process_chat_message(db: DBSession, session: models.ChatSession, user_text: str) -> str:
    """Run one chat turn and persist both sides of it. Sessions are fully
    isolated from each other via session_id.

    Both modes get this session's short-term memory (memory_manager.get_
    context_messages - rolling summary + recent raw messages, with its own
    compaction once the history gets long). Default: session.agent_mode is
    False, so turns are a single, tool-less call to the chat model
    (simple_chat.run_turn). Sending "/agent" flips it to True, and turns
    instead go through the deep agent (agent_runner.run_turn), which
    additionally gets tools (web search, wiki writes). "/normal" flips it
    back."""
    # Wiki writes from the deep agent's update_wiki tool need to know which
    # account's wiki to write into, but tool calls happen deep inside the
    # LangGraph loop with no access to this function's arguments - stash it
    # in a contextvar for the tool to read (see app/request_context.py).
    current_user_id.set(session.user_id)

    command = user_text.strip().lower()
    if command == AGENT_MODE_COMMAND:
        return _switch_mode(
            db,
            session,
            user_text,
            True,
            "已切換為 Deep Agent 模式，之後的對話會啟用工具（網路搜尋、寫入知識庫）。打 /normal 可以切回一般模式。",
        )
    if command == NORMAL_MODE_COMMAND:
        return _switch_mode(
            db,
            session,
            user_text,
            False,
            "已切換回一般模式，之後的對話是不使用工具的單輪快速回覆（仍保留這個對話的短期記憶）。打 /agent 可以再切回 Deep Agent 模式。",
        )
    if command in EXPERIMENTAL_AGENT_COMMANDS:
        agent_key = EXPERIMENTAL_AGENT_COMMANDS[command]
        description = EXPERIMENTAL_AGENT_DESCRIPTIONS.get(agent_key, "")
        return _switch_experimental_agent(
            db,
            session,
            user_text,
            agent_key,
            f"已切換為實驗性的 {agent_key} 模式（{description}）。打 /normal 可以切回一般模式。",
        )

    # Build context from EXISTING history first, so the new user message
    # below isn't double-counted when the model is called.
    context_messages = memory_manager.get_context_messages(db, session)
    db.add(models.ChatMessage(session_id=session.id, role="user", content=user_text))
    db.commit()

    # session.model_name is None unless the user picked a specific model in
    # the UI - every path below falls back to the deployment default in that case.
    run_id = None
    if session.experimental_agent in EXPERIMENTAL_AGENTS:
        run_experimental_turn = EXPERIMENTAL_AGENTS[session.experimental_agent]
        files_column = FILES_COLUMN_BY_AGENT.get(session.experimental_agent)
        stored_files = getattr(session, files_column, None) if files_column else None
        files = json.loads(stored_files) if stored_files else {}
        extra_kwargs = {}
        if session.experimental_agent == "test_agent":
            # tuple of (fab, function) pairs - matches
            # test_agent.agent_factory.get_agent's cache key shape.
            extra_kwargs["identities"] = tuple(
                (d["fab"], d["function"]) for d in session.test_agent_identities
            )
        reply_text, usage, files = run_experimental_turn(
            context_messages,
            user_text,
            files=files,
            model_name=session.model_name,
            session_id=session.id,
            **extra_kwargs,
        )
        if files_column:
            setattr(session, files_column, json.dumps(files))
    elif session.agent_mode:
        handler, run_id = langfuse_client.new_handler_and_run_id()
        reply_text, usage = agent_runner.run_turn(
            context_messages,
            user_text,
            callbacks=[handler] if handler else None,
            run_id=run_id,
            model_name=session.model_name,
        )
    else:
        reply_text, usage = simple_chat.run_turn(context_messages, user_text, model_name=session.model_name)

    model_name = usage.get("model")
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    # Cost comes from Langfuse (not computed locally) - best-effort, may stay
    # None if Langfuse isn't configured or the trace isn't ready yet.
    cost_usd = None
    if run_id:
        lf_usage = langfuse_client.fetch_usage(str(run_id))
        if lf_usage:
            cost_usd = lf_usage.get("cost_usd")
            input_tokens = lf_usage.get("input_tokens") or input_tokens
            output_tokens = lf_usage.get("output_tokens") or output_tokens
            model_name = lf_usage.get("model") or model_name

    assistant_msg = models.ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply_text,
        model=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
    )
    db.add(assistant_msg)

    if session.title in (None, "", "New Conversation"):
        session.title = generate_title(user_text, reply_text)

    session.last_message_at = datetime.utcnow()
    db.commit()

    return reply_text
