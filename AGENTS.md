# Project notes for agents

## Map (what lives where)

- `src/harness/` — the code: `core/` (the loop + layers), `providers/`
  (model adapters), `tools/`, `cli/` (the REPL), `prompts/` (the backbone).
- `docs/` — ROADMAPs, design notes (`notes/`), open problems (`problem.md`).
- `acceptance/` — the live-model gate; `tests/` — the offline pytest suite.
- `agents/`, `commands/`, `skills/` — runtime libraries (roles, slash
  commands, model procedures) read from this directory.
- `archive/` — frozen Stage-1 artifact (`mvp/`), wire labs, prompt library.

## Rules

- Run tests: `uv run pytest -q` (offline, sub-second — always run after code changes).
- Run the harness itself: `uv run harness [ollama|gemini|anthropic] [-y]` (or `uv run python -m harness ...`).
- `archive/mvp/` is a frozen Stage-1 artifact — do not modify it.
- `archive/mvp/fixtures/stats.py` contains a bug ON PURPOSE (acceptance task C). Do not "helpfully" fix it unless the task asks.
- Never commit `.env` (API keys live there).
