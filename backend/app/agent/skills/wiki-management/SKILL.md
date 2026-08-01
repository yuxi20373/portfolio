---
name: wiki-management
description: How and when to save or update an entry in the long-term wiki knowledge base using the update_wiki tool. Load this whenever the user asks to save, add, record, remember long-term, or update something in the wiki / knowledge base.
---

# Managing the wiki knowledge base

The user can explicitly ask you to save or update something in the
long-term wiki, separate from the automatic background summarizer. Do this
ONLY when they explicitly ask for it - phrases like "把 OOO 加入 wiki",
"更新 wiki 的 OOO", "記到知識庫", "add OOO to the wiki", "update the wiki
entry for OOO", "remember this in the wiki". Do not call the tool just
because an interesting topic came up in conversation - only on explicit
request.

When this happens, call the `update_wiki` tool yourself with a properly
structured entry - do not just describe what you would do, and do not ask
the user to do it themselves.

## Choosing entry_type and sections

Pick the closest-fitting entry_type from this fixed set, and only use
section headings from that type's list (skip ones that don't apply to this
specific topic; never invent new headings outside the list):

- **concept** (academic/technical terms, e.g. "Natural Language
  Processing"): Definition, History, Uses, Tasks and Limitations,
  Practical Issues, Trends
- **technology** (tools/software/products/techniques, e.g. "Docker"):
  Overview, How It Works, History, Use Cases, Limitations, Related
  Technologies
- **organism** (animals/plants, e.g. "Betta fish"): Overview, Behavior and
  Ecology, Habitat, Care and Keeping, Varieties and Classification
- **person**: Overview, Biography, Major Works or Contributions, Legacy
- **event**: Overview, Background, Timeline, Impact
- **place**: Overview, Geography, History, Culture and Attractions
- **general** (fallback, anything else): Overview, Key Points, Related
  Information

## Content format

`content` must start with one short lead paragraph (no heading), like a
Wikipedia introduction, followed by "## Heading" sections in the order
listed above. Write in the same language the user is using. Base the
content on what's actually been discussed in the conversation, plus your
own general knowledge to fill reasonable gaps - don't fabricate specifics
you're not confident about.

Use whatever presentation fits the content best within each section -
don't default to plain paragraphs for everything:
- Markdown tables (`| Column | Column |`) for comparisons, specs, or any
  naturally tabular information.
- Arrow notation (→) for processes, pipelines, or step-by-step flows, e.g.
  "Input → Preprocessing → Model → Output".
- Bullet or numbered lists for enumerable items instead of run-on
  sentences.
- Wrap a handful of the most important terms, conclusions, or numbers per
  section in `<mark>...</mark>` tags to highlight them. Use this sparingly
  (a few per section, not every sentence) so it stays meaningful.

If the topic is likely an update to an entry that already exists, still
just call `update_wiki` with the same title - the tool merges into the
existing entry automatically, you don't need to check first.

## After calling the tool

Briefly confirm to the user, in their language, what was saved or updated
- don't call the tool silently without acknowledging it.
