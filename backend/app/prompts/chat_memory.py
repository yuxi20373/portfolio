# 用途：把一段對話中比較舊的訊息，濃縮成一段「記憶摘要」，取代原始訊息餵給
# LLM，藉此壓低長對話每輪的 token 用量。原始訊息本身仍完整保留在資料庫中，
# 這個摘要只影響「餵給模型看的內容」。
# 使用位置：app/agent/memory_manager.py 的 _maybe_compact()。

MEMORY_UPDATE_SYSTEM_PROMPT = """You maintain a running memory summary of an ongoing conversation, so the AI assistant doesn't need to re-read the entire chat history every turn.
You will be given the current memory summary (may be empty) and a batch of new messages that happened after it. Produce an updated summary that:
- preserves any facts, decisions, preferences, or context the assistant will need to keep answering well later in the conversation
- stays compact (a few short paragraphs at most)
- drops small talk / pleasantries that carry no lasting information
Respond with ONLY the updated summary text, no preamble."""
