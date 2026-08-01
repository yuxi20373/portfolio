# 用途：新對話的第一輪問答結束後，自動幫這個對話生成一個簡短標題。
# 使用位置：app/services/chat/title_service.py 的 generate_title()。

TITLE_SYSTEM_PROMPT = (
    "Write a short, concise title (max 6 words) that summarizes what this "
    "conversation is about. Respond with ONLY the title text - no quotes, "
    "no trailing punctuation, no explanation."
)
