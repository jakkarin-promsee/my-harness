# Project notes for agents

This repo is a from-scratch agent harness (learning project). Facts an agent
working here should know:

- Run tests: `uv run pytest -q` (offline, sub-second — always run after code changes).
- Run the harness itself: `uv run python -m harness [ollama|gemini|anthropic] [-y]`.
- `mvp/` is a frozen Stage-1 artifact — do not modify it.
- `mvp/fixtures/stats.py` contains a bug ON PURPOSE (acceptance task C). Do not "helpfully" fix it unless the task asks.
- Never commit `.env` (API keys live there).
