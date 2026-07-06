# researcher-harness

A **from-scratch agent harness** — the loop, tools, providers, and context plumbing
that sit *under* something like Claude Code — rebuilt by hand to understand how the
real ones actually work. Learning-first: **understanding beats features, every time.**

Two reasons it exists:

1. **Learn by rebuilding.** How do Claude Code, Codex CLI, opencode, and aider work
   under the hood? The fastest way to know is to build one and hit the same walls they did.
2. **"claude2 insurance."** Own an independent, provider-agnostic harness on this
   machine — so the day a single AI vendor isn't available here isn't the day work stops.

It is **not** a product, and **not** an SDK wrapper. One user: the owner. Real research
work keeps running on Claude Code as usual; this harness doesn't touch it until it earns
the trust (Stage 3).

## The three pains it's built around

1. **Signal vs. noise.** Agents drown in context they didn't need — raw file dumps,
   full command output, tool chatter. Most of it is noise; the answer is a few lines
   of signal. Paying (in tokens and latency) to bury the signal is the core waste this
   project attacks.
2. **Prompt reuse by hand.** Reusing a good prompt (plan / summarize / clean-up) means
   copy-paste-and-edit every time. The goal: templates plus small interviewers that
   collect what's missing, so a workflow is `/name args`, not a manual rewrite.
3. **Learning & independence.** Understand the machine from the inside, and own a
   working, provider-agnostic copy of it — whatever happens to any one vendor.

## What it does today

| Piece | What it is |
|---|---|
| **The loop** | One model call → run the tool calls it asks for → append results → repeat. The entire "agent" is [`src/harness/core/loop.py`](src/harness/core/loop.py). |
| **Tools** | Read / edit files, search, run commands, and a **todo** tool — an external plan the model can't forget. |
| **Subagents** | Delegate a subtask to a fresh child loop and get back just its result. |
| **Providers** | Ollama (local, free), Gemini, and Anthropic behind one adapter — swapping is a CLI argument, because all three speak OpenAI-compatible chat completions. |
| **Visible mind** | Thinking and narration stream live to the terminal (SSE), so you watch it reason and talk instead of staring at a spinner. |
| **Permissions** | [`harness.toml`](harness.toml) decides per tool: allow / ask / deny. |
| **Token meter** | Every run reports tokens. The project exists because of context economics, so the cost is always on screen. |

## Status

**Stage 2 complete (2026-07-07).** The harness runs end-to-end on both providers.

- **79 offline tests** against a FakeModel — the loop's contract, zero tokens: `uv run pytest -q`
- **Exit gate 7/7 on both providers** (`uv run python acceptance/run.py <provider>`):
  gemini-2.5-flash-lite (~1,083 output tokens) and local qwen3:4b-instruct (~1,460).

Next up is **Stage 3** — the custom layer that turns the three pains above into real
features. The full staged plan and exit criteria live in [docs/ROADMAP.md](docs/ROADMAP.md).

## Quickstart

```bash
# offline test suite — always run after a code change (sub-second, zero tokens)
uv run pytest -q

# run the harness (local model is free; -y auto-approves tools)
uv run harness ollama
uv run harness [ollama|gemini|anthropic] [-y] [--resume] [--sessions]
#   ...or the module form: uv run python -m harness <provider>

# the live-model acceptance gate
uv run python acceptance/run.py <provider>
```

Local dev runs on `qwen3:4b-instruct` via Ollama (4 GB VRAM friendly). Gemini is the
paid fallback for validating response *quality*; debug loop logic locally so a runaway
loop costs $0. Anthropic's adapter is built but stays live-untested until the key is set
deliberately.

## Layout

Code under `src/`, prose under `docs/`, frozen/experimental under `archive/`, and the
runtime config the harness reads from the working directory stays at root.

| Path | What it is |
|---|---|
| `src/harness/` | The living codebase — `core/`, `providers/`, `tools/`, `cli/`, `prompts/` (installable package) |
| `tests/` | FakeModel pytest suite (the loop's contract, offline) |
| `acceptance/` | Stage-2 live-model exit gate |
| `docs/` | [ROADMAP](docs/ROADMAP.md), design [notes/](docs/notes), [open problems](docs/problem.md) |
| `commands/` | Slash-command template library (`/name args` → `commands/name.md`) |
| `harness.toml`, `AGENTS.md` | Permissions policy and project memory — read from cwd at runtime |
| `archive/` | Frozen Stage-1 `mvp/`, throwaway `labs/`, and the real `prompt/` library (Stage-3 raw material) |

Working rules and the project's constitution are in [CLAUDE.md](CLAUDE.md).
