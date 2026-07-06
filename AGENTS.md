# Project notes for agents

This repo is a from-scratch agent harness (learning project). Facts an agent
working here should know:

- Run tests: `uv run pytest -q` (offline, sub-second — always run after code changes).
- Run the harness itself: `uv run harness [ollama|gemini|anthropic] [-y]` (or `uv run python -m harness ...`).
- Code lives under `src/harness/` (installable package); docs under `docs/`; frozen/experimental dirs under `archive/`.
- `archive/mvp/` is a frozen Stage-1 artifact — do not modify it.
- `archive/mvp/fixtures/stats.py` contains a bug ON PURPOSE (acceptance task C). Do not "helpfully" fix it unless the task asks.
- Never commit `.env` (API keys live there).
