"""預設聊天路徑（非 deep agent）：呼叫聊天模型時不掛任何工具，也不會觸發
deepagents 的規劃/工具迴圈 - 但仍會帶入這個 session 的短期記憶（context_
messages，來自 app/agent/memory_manager.py，跟 deep agent 共用同一套歷史
/摘要壓縮機制)。這是每個 session 一開始的預設行為；使用者在該 session 打
過 /agent 指令切換成 agent_mode 後，才會改走 app/agent/runner.py 的 deep
agent（額外多了工具）；打 /normal 可以切回來。見
app/services/chat/chat_service.py:process_chat_message。"""

from .agent_factory import build_chat_model, default_model_name
from ..prompts.chat_agent import SIMPLE_CHAT_INSTRUCTIONS

_models = {}


def _get_model(model_name: str = None):
    key = model_name or "__default__"
    if key not in _models:
        _models[key] = build_chat_model(model_name)
    return _models[key]


def run_turn(context_messages: list[dict], user_text: str, model_name: str = None) -> tuple[str, dict]:
    messages = (
        [{"role": "system", "content": SIMPLE_CHAT_INSTRUCTIONS}]
        + context_messages
        + [{"role": "user", "content": user_text}]
    )
    result = _get_model(model_name).invoke(messages)

    content = result.content
    if isinstance(content, list):
        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)

    usage = getattr(result, "usage_metadata", None) or {}
    meta = getattr(result, "response_metadata", None) or {}

    return content, {
        "model": meta.get("model_name") or meta.get("model") or default_model_name(model_name),
        "input_tokens": usage.get("input_tokens", 0) or 0,
        "output_tokens": usage.get("output_tokens", 0) or 0,
    }
