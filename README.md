# Researcher Harness 🚀

This is a from-scratch project to build and learn about **agent harnesses**. Think of it as a workbench for creating and experimenting with AI "agents" – smart helpers that can understand and interact with your code and files.

## What's the Big Idea? 🤔

The main goal is to understand how these agent systems work under the hood. It's a learning project focused on the fundamentals. The current focus is on building a solid, standard harness first, with future plans to customize it for specific needs.

## Key Pains This Project Addresses:

1.  **Context Overload:** AI agents often get too much information (like raw file dumps or command outputs) that isn't essential, making it expensive and slow to find the actual important bits (the "signal"). This project aims to help agents focus on the signal and ignore the noise.
2.  **Manual Prompting:** Reusing prompts for common tasks (like planning, summarizing, or cleaning code) usually involves a lot of manual editing. This harness wants to make prompt reuse easier with templates and smart interviewers that gather the needed info.
3.  **Learning & Independence:** Understanding how a harness works inside — and owning a working, provider-agnostic one on this machine, whatever happens to any single AI vendor.

## Project Stages:

The project follows a phased approach:

- **Stage 0-2:** Build a standard, reliable harness by "copying the seniors" (learning from existing systems). This involves setting up core features for agents to run, communicate, and manage tasks.
- **Stage 3:** Customize the harness to address the specific pain points mentioned above, making it uniquely yours.

## How It Works:

- **The loop:** one model call, execute the tool calls it asks for, append results, repeat (`harness/core/loop.py` — the whole "agent" part).
- **Agents:** can read/edit files, search, run commands, keep a visible todo plan, and delegate to subagents. Thinking and narration stream live to the terminal.
- **Providers:** Ollama (local, free), Gemini, and Anthropic behind one adapter interface — swapping is a CLI argument.
- **Configuration:** `harness.toml` controls what tools may run (allow/ask/deny), ensuring safety and control.

## Getting Started:

- **Run Tests:** Keep everything working by running `uv run pytest -q` (offline, zero tokens).
- **Run the Harness:** Launch the system with `uv run python -m harness [ollama|gemini|anthropic] [-y] [--resume] [--sessions]`.
- **Run the exit gate:** `uv run python acceptance/run.py <provider>` — the live-model acceptance suite.

The full story, staged plan, and exit criteria live in [ROADMAP.md](ROADMAP.md); working rules in [CLAUDE.md](CLAUDE.md).
