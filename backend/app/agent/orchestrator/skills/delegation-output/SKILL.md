---
name: delegation-output
description: How to report results back to the calling agent when running as a delegated worker subagent. Load this whenever you were invoked via the task tool to complete a sub-task for another agent.
---

# Reporting results as a worker subagent

The calling agent only ever sees your final reply, not your intermediate
tool calls or reasoning. Keep that final reply short - but don't lose
information to get there.

## Write full output to a file, then point to it

If your result is long, structured, or something the calling agent (or the
user, later in the conversation) might need to see again in full - research
findings, a compiled list, a draft document, anything more than a few
sentences - write it with `write_file` to a path under `/results/`, using a
short descriptive slug, e.g. `/results/renewable-energy-comparison.md`.

Then your final reply to the calling agent must be ONLY:

- the file path you wrote to
- a 1-3 sentence summary of what's in it

Do not also paste the full content into your final reply - that defeats the
purpose, since it would end up duplicated in both the file and the
conversation history.

## When not to write a file

For a short, self-contained answer (a single fact, a brief direct answer),
just reply directly - don't create a file for something that's already
short enough to say once.
