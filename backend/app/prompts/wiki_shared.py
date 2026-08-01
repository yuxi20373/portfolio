# 用途：所有「撰寫/編輯 wiki 內容」的提示詞共用的排版指引片段（表格、箭頭
# 流程、條列、<mark> 重點標記），確保產生的條目看起來像正式的參考資料，
# 而不是一整塊純文字段落。被其他 prompt 用 f-string 內嵌進去使用。
# 使用位置：prompts/wiki_search.py、prompts/wiki_adjust.py，
# 以及 app/agent/skills/wiki-management/SKILL.md（聊天中觸發的 wiki 更新）。

RICH_FORMATTING_GUIDANCE = """Use whatever presentation fits the content best within each section - don't default to plain paragraphs for everything:
- Markdown tables (| Column | Column |) for comparisons, specs, or any naturally tabular information.
- Arrow notation (→) for processes, pipelines, or step-by-step flows, e.g. "Input → Preprocessing → Model → Output".
- Bullet or numbered lists for enumerable items instead of run-on sentences.
- Wrap a handful of the most important terms, conclusions, or numbers per section in <mark>...</mark> tags to highlight them. Use this sparingly (a few per section, not every sentence) so it stays meaningful - it's for genuinely key points, not decoration."""
