---
name: explore
description: Understand a part of the researcher-harness before changing it. Use when starting work on an unfamiliar module (the loop, a provider, a tool, permissions, sessions, the CLI) and you need to know how it works and why — without editing anything yet.
---

# Explore a part of the harness

Goal: build an accurate mental model of **one area** before touching it, using the context hierarchy so you read the right things in the right order — not the whole repo (that waste is the project's Pain 1).

## Steps

1. **Start at the map.** Read `src/harness/CLAUDE.md` (auto-loaded when you open code) for the architecture-in-brief and the invariants you must not break.
2. **Find the folder.** Open the `README.md` in the folder you're exploring (`src/harness/core/`, `providers/`, `tools/`, or `tests/`, `acceptance/`). It's the file-by-file map of what's there now, with a link to the design note.
3. **Read the why.** Open the linked `docs/notes/NN-*.md`. Notes are written before implementing: *what the seniors do → what we built → how we know it works.*
4. **Read the code's own words.** Every module's top docstring is the spec (`loop.py`, `base.py`, `subagent.py` …). Read it before the body.
5. **Run it, for free.** Offline: `uv run pytest -q`. Live behavior on the local model costs $0: `uv run harness ollama`.

## Rules

- **Read narrowly.** The whole point of the hierarchy is that understanding one part shouldn't require the whole repo in context.
- **Don't edit in this mode.** Explore produces understanding; the `implement-feature` skill produces changes.
- **Code is the territory.** If a README or note disagrees with the code, trust the code and flag the stale doc.
