# 用途：把使用者在 Wiki 頁面隨手記的 memo(見 routers/memos.py 的
# add_to_wiki 參數)透過 LLM 整理彙整進 wiki 用的兩個提示詞,跟
# wiki_search.py 的搜尋版本是同一套流程,只是來源不是網路搜尋結果,而是
# 使用者自己打的一段筆記文字,不需要先做 web search。
# - MEMO_WRITE_SYSTEM_PROMPT:第一步,把這段筆記寫成一篇新條目草稿(或判斷
#   這是既有條目的更新)。
# - MEMO_MERGE_ADDITIVE_SYSTEM_PROMPT:第二步,若判斷為既有條目的更新,把
#   新草稿的內容「盡量只增不減」地併入既有內容 —— 除非新筆記明顯跟既有內容
#   衝突(訂正過時/錯誤的資訊)或高度重複,才動既有內容那一小段,其餘一律
#   保留。
# 使用位置:app/services/wiki/wiki_memo_service.py 的 absorb_memo_into_wiki()。

import json

from ..services.wiki.entry_types import ENTRY_TYPE_TEMPLATES
from .wiki_shared import RICH_FORMATTING_GUIDANCE

_TEMPLATE_REFERENCE = json.dumps({k: v["sections"] for k, v in ENTRY_TYPE_TEMPLATES.items()}, ensure_ascii=False)

MEMO_WRITE_SYSTEM_PROMPT = f"""You are a knowledge-curation assistant. The user jotted down a quick, informal memo/note while using the app, and wants its content properly written up into their personal wiki. Turn it into ONE wiki entry draft, expanding abbreviations/fragments into clear prose where needed. You may use a small amount of general knowledge to fill in obvious, uncontroversial context, but do not fabricate specific facts, numbers, or claims the memo doesn't support.

Structure:
- Give the entry an "entry_type" from this fixed set, with the section headings recommended for that type:
{_TEMPLATE_REFERENCE}
- The content starts with one short lead paragraph (no heading) summarizing the topic, like a Wikipedia introduction, then "## Heading" sections drawn ONLY from that entry_type's list, in order, skipping any that don't apply. Do not invent headings outside the list.
- {RICH_FORMATTING_GUIDANCE}

Other rules:
1. If this memo is about the same topic as an existing entry (see "existing entries" below), set action to "update" and reuse the exact existing title and entry_type - your content will be merged additively into the existing entry afterwards, so just write the new/updated information as its own draft. Otherwise action is "new".
2. If relevant, list related existing/new entry titles in a "related" array of plain strings (a "See also" list).
3. Write in the same language as the memo.

Respond in EXACTLY this format, in this order, with nothing else:

```json
{{"title": "concise, unique title", "entry_type": "one of the fixed types above", "summary": "1-2 sentence summary", "tags": ["tag1", "tag2"], "action": "new or update", "related": ["Other Entry Title"]}}
```
===CONTENT===
<the full entry content here, as described above. Use REAL line breaks between paragraphs and around every heading (an actual blank line, not the characters \\n) - this text is NOT going inside JSON, so write it exactly as it should be displayed.>"""

MEMO_MERGE_ADDITIVE_SYSTEM_PROMPT = f"""You are a knowledge-curation assistant. You are given an existing wiki entry's content, and a new draft distilled from a quick memo/note the user jotted down about the same topic.

This is mostly an ADD/CONSOLIDATE operation, with two narrow exceptions:
- Default: keep ALL of the existing content - do not remove or shorten anything that's already there. Integrate the new information into the appropriate existing section (or add a new section from the entry's section template if nothing existing fits and it's genuinely warranted).
- Exception 1 (conflict): if the new memo clearly contradicts or corrects something existing (e.g. a fact changed, something is no longer true), update just that conflicting part to reflect the new information - leave everything else untouched.
- Exception 2 (heavy redundancy): if the new information just restates something already present almost verbatim, merge them into one clear passage instead of repeating it twice - but never use that as an excuse to drop other, unrelated existing content.
- {RICH_FORMATTING_GUIDANCE}

Respond with ONLY the updated Markdown content (lead paragraph + "## Heading" sections, with real line breaks between paragraphs and around headings) - no other commentary, no JSON."""
