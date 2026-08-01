---
name: tool-calling-format
description: Correct format for invoking any tool (e.g. web_search). Load this whenever you are about to call a tool, to make sure the call is well-formed and won't be rejected by the provider.
---

# Calling tools correctly

When you need to use a tool, you MUST use your model's native tool-calling
mechanism (the structured `tool_calls` field of your response), never write
the call out as plain text in the message content.

**Correct**: emit a tool call where the tool name and its arguments are two
separate, properly structured fields - e.g. calling `web_search` with the
argument `query` set to `"Taipei weather forecast"`.

**Never do this** - do not hand-write the tool name and arguments together
as a single string or fake syntax inside your text response, such as:

- `web_search={"query": "Taipei weather forecast"}`
- `<function=web_search={"query": "..."}></function>`
- `[web_search("Taipei weather forecast")]`
- any other pseudo-syntax that looks like a function call

If you're not confident a tool call will come out correctly, it is better
to just answer directly in plain text (saying you're not certain, if
that's the case) than to guess at malformed call syntax - a broken tool
call fails the entire turn for the user, while a plain-text answer does
not.
