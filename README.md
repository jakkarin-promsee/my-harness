# researcher-harness

A **from-scratch agent harness** — the loop, tools, providers, and context plumbing
that sit _under_ something like Claude Code — rebuilt by hand to understand how the
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

## What it does (release 1)

| Piece                    | What it is                                                                                                                                                                                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **The loop**             | One model call → run the tool calls it asks for → append results → repeat. The entire "agent" is [`src/harness/core/loop.py`](src/harness/core/loop.py) — pure, injected, testable for zero tokens.                                                          |
| **Tools**                | Read / edit files (edits show a unified diff at the prompt), search, run commands, fetch web pages, and a **todo** tool — an external plan the model can't forget. Every observation is _framed_: first line says what happened and the shape of the result. |
| **MCP client**           | Any [MCP](https://modelcontextprotocol.io) server in `harness.toml` mounts its tools as `mcp__server__tool` — one client, infinite tools. Ships with DuckDuckGo web search, no API key needed. `/mcp` lists what's connected.                                |
| **Subagents**            | Delegate a subtask to a fresh (or forked) child loop and get back just its result — optionally wearing a named role.                                                                                                                                         |
| **Providers**            | Ollama (local, free — native `/api/chat`), Gemini flash + flash-lite (OpenAI-compat), and Anthropic (native), each behind its own adapter. The loop speaks one dialect; adapters translate both directions.                                                  |
| **Visible mind**         | Thinking and narration stream live to the terminal, so you watch it reason and talk instead of staring at a spinner.                                                                                                                                         |
| **The cognitive core**   | A sectioned system-prompt backbone with a four-tier ladder (MICRO fits the 8K local card at 264 tokens), an orientation map in the first message, attention anchors for long sessions, voice & effort knobs.                                                 |
| **Modes**                | Switchable permission profiles — from "just chat" to "auto-approve writes in this folder". Deny is absolute in every mode; policy lives in versioned [`harness.toml`](harness.toml).                                                                         |
| **Agents (roles)**       | Markdown-defined personalities in [`agents/`](agents/) with their own prompt, default mode, and optionally their own model.                                                                                                                                  |
| **Skills**               | `skills/*/SKILL.md` — procedures the **model** discovers from one description line and reads on demand (the open Agent Skills standard).                                                                                                                     |
| **Reasoning control**    | `/think off…high` — the chain-of-thought budget knob, per session or per role. Off by default: measured, not assumed.                                                                                                                                        |
| **Sessions & the meter** | Every message journals to `sessions/*.jsonl` as it happens; `--resume` replays. Every call prints tokens — including Gemini's _hidden_ thinking. Experimental: per-turn reflection on the local thinking lane.                                               |

The full manual — every command, knob, and extension recipe — is
**[docs/GUIDEBOOK.md](docs/GUIDEBOOK.md)**.

## Status — release 1

**Stages 0–2 are complete** (Stage 2 core, 2R frontier parity, 2C cognitive core,
and the MCP client all closed 2026-07-08). What that means, measured:

- **196 offline tests** against a FakeModel — the loop's contract, zero tokens: `uv run pytest -q`
- **Exit gate:** a 15-task core + a 4-task _failure museum_ mined from real live
  sessions. At close: flash **14/14 core + museum 3/3 by majority** (the untuned
  baseline was 1/3), the never-tuned hold-out task passed its first-ever runs 3/3,
  local **14/14-by-majority** on a 4B model at the 264-token MICRO prompt, and the
  MCP search task passed on all three lanes.

Next: **Stage 3** — surgical context ops, prompt middleware, checkpoints; the three
pains above become features. Plans and history: [docs/ROADMAP.md](docs/ROADMAP.md) →
[docs/ROADMAP2.md](docs/ROADMAP2.md) → [docs/ROADMAP3.md](docs/ROADMAP3.md).

## Quickstart

```bash
# offline test suite — always run after a code change (sub-second, zero tokens)
uv run pytest -q

# run the harness (local model is free)
uv run harness                      # Ollama, build mode, default agent
uv run harness ollama-think         # Ollama, show thinking, slow but fun
uv run harness gemini-flash         # the quality lane (paid)
uv run harness --agent plan         # start as the read-only planning role
uv run harness --mode explore -y    # look-don't-touch, no prompts

# the live-model acceptance gate
uv run python acceptance/run.py <provider>
```

Local dev runs on `qwen3:4b-instruct` via Ollama (4 GB VRAM friendly). The Gemini
flash tier is the quality target; debug loop logic locally so a runaway loop costs $0.
Anthropic's adapter is built but stays live-untested until the key is set deliberately.

## Layout

Code under `src/`, prose under `docs/`, frozen/experimental under `archive/`, and the
runtime config the harness reads from the working directory stays at root.

| Path                        | What it is                                                                                                                                            |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/harness/`              | The living codebase — `core/`, `providers/`, `tools/`, `cli/`, `prompts/` (installable package)                                                       |
| `tests/`                    | FakeModel pytest suite (the loop's contract, offline)                                                                                                 |
| `acceptance/`               | The live-model exit gate: core tasks + the failure museum                                                                                             |
| `docs/`                     | [GUIDEBOOK](docs/GUIDEBOOK.md), [ROADMAP](docs/ROADMAP.md)s, design [notes/](docs/notes) (the why, one per feature), [open problems](docs/problem.md) |
| `commands/`                 | Slash-command template library (`/name args` → `commands/name.md`)                                                                                    |
| `agents/`                   | The role library (`/agent name` → `agents/name.md`)                                                                                                   |
| `skills/`                   | The model's own procedure library (`skills/*/SKILL.md`, description-triggered)                                                                        |
| `harness.toml`, `AGENTS.md` | Permissions policy and project memory — read from cwd at runtime                                                                                      |
| `sessions/`                 | Runtime session journals (`*.jsonl`, gitignored)                                                                                                      |
| `archive/`                  | Frozen Stage-1 `mvp/`, throwaway `labs/`, and the real `prompt/` library (Stage-3 raw material)                                                       |

Working rules and the project's constitution are in [CLAUDE.md](CLAUDE.md);
how to use and how to extend, in [docs/GUIDEBOOK.md](docs/GUIDEBOOK.md).
