# CLAUDE.md — researcher-harness

## What this project is

A **from-scratch agent harness**, built to learn how harnesses (Claude Code, Codex CLI, opencode, aider, ...) actually work under the hood — and to own an independent one if the day ever comes when Claude isn't available here ("claude2 insurance"). Learning-first side project: **understanding beats features, every time.**

What this project is **NOT**:

- It is NOT the owner's research project. That lives elsewhere and keeps running on Claude Code as usual. This harness never touches real research work until Stage 3 proves itself.
- It is NOT an Agent SDK wrapper. (See "Legacy context" below — an older brief in this repo says "build on the Agent SDK"; that decision belonged to a different plan and does not govern this project.)
- It is NOT a product. One user: the owner.

Read [docs/ROADMAP.md](docs/ROADMAP.md) before doing anything. It holds the full story, the staged plan, and the exit criteria for every stage.

## Current status

- **Repo restructured 2026-07-07:** code is now an installable package under `src/harness/`, prose docs under `docs/`, and the frozen/experimental dirs (`labs/`, `mvp/`, `prompt/`) under `archive/`. Runtime/config files (`harness.toml`, `AGENTS.md`, `commands/`, `README.md`, `CLAUDE.md`) stay at root. Entry point: `uv run harness <provider>` or `uv run python -m harness <provider>`.
- **Stage: 2 COMPLETE (2026-07-07) — exit gate 7/7 on BOTH providers; Stage 3 unblocked.** 79 offline tests (`uv run pytest -q`); exit gate `uv run python acceptance/run.py <provider>`: **7/7 gemini-2.5-flash-lite** (1,083 out-tokens), **7/7 local qwen3:4b-instruct** (1,460 out-tokens). 2.9 shipped 2026-07-07: visible mind (narration preambles + dim thinking display + length-nudge), SSE streaming, todo tool (notes 11–13). Local workhorse: `qwen3:4b-instruct` (non-thinking 2507 refresh, set in `.env`) with `OLLAMA_CONTEXT_LENGTH=8192` machine-wide. Model lessons: `llama3.2:3b` fabricates — unusable; thinking `qwen3:4b` burns 10× the output tokens and dies at length limits — use the instruct variant; never `temperature: 0` on qwen3; flash-lite throws 503s (retry handles) and empty replies (nudge handles). [docs/problem.md](docs/problem.md): only the deliberate Anthropic live test remains open.
- Update this line whenever a stage milestone completes. This is the first thing a fresh session should check.

## Stack & environment

| Thing | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Managed with `uv` |
| Primary dev model | Local via Ollama | RTX 3050 Ti Laptop, 4 GB VRAM → `qwen3:4b-instruct` (chosen 2026-07-07: 7/7 exit gate, non-thinking, ~1.5k out-tokens per suite). Window: `OLLAMA_CONTEXT_LENGTH=8192` machine-wide + `.env` |
| Fallback dev model | Gemini API (flash / flash-lite) | Via its OpenAI-compatible endpoint. ~$19 of credit total — guard it |
| Wire protocol | OpenAI-compatible chat completions | Both Ollama (`http://localhost:11434/v1`) and Gemini speak it → provider swap is one `base_url` change |
| Anthropic API | Adapter built (2.1), live-untested | `ANTHROPIC_API_KEY` stays **unset** until the owner sets it deliberately for a live smoke test (a stray key silently bills pay-as-you-go) — see docs/problem.md |

**Budget rule:** debug agent-loop logic on the local model (an infinite-loop bug burns $0 locally); validate response *quality* on Gemini. Never point a possibly-buggy loop at a paid endpoint.

## Repo map

Layout: **code** under `src/`, **docs** under `docs/`, **frozen/experimental** under `archive/`, **runtime/config** at root.

| Path | What it is |
|---|---|
| `docs/ROADMAP.md` | The plan. Stages 0–3, exit criteria, reference shelf |
| `docs/notes/` | Design notes — one per feature, written *before* implementing (created in Stage 0) |
| `docs/problem.md` | Open problems needing the owner — check when returning to the project |
| `docs/harness-context-v3.md` | Legacy brief (see below) |
| `src/harness/` | **The living codebase** (Stage 2+): `core/` loop, `providers/`, `tools/`, `cli/`, `prompts/`. Installable package. Run: `uv run harness [ollama\|gemini\|anthropic] [-y] [--resume] [--sessions]` (or `uv run python -m harness ...`) |
| `tests/` | FakeModel pytest suite — the loop's contract, zero tokens. Run: `uv run pytest -q` |
| `acceptance/` | Stage-2 exit gate: live-model suite. Run: `uv run python acceptance/run.py <provider>` |
| `commands/` | Slash-command template library (`/name args` reads `commands/name.md`) — read from cwd at runtime, so it stays at root |
| `harness.toml` | Permissions policy (allow/ask/deny per tool), versioned on purpose — read from cwd at runtime |
| `AGENTS.md` | Project memory injected into the harness's own system prompt — read from cwd at runtime |
| `archive/mvp/` | Stage 1 single-file harness — **frozen** as the learning artifact; `archive/mvp/ACCEPTANCE.md` + fixtures still serve as the acceptance suite |
| `archive/labs/` | Tiny throwaway experiments (raw API calls, wire-format studies) (created in Stage 0) |
| `archive/prompt/` | The owner's **real prompt library** from the research project. Read-only reference — do not edit. Raw material for Stage 3.2 (prompt middleware) |

## Working rules (the constitution)

1. **Copy first, invent later.** Every feature starts with "how do mini-swe-agent / opencode / aider / Claude Code do this?" — study 2–3 references, then implement. Custom ideas wait until Stage 3.
2. **One feature at a time.** Never two features in flight. Design note → implement → acceptance suite green → next.
3. **No line you can't explain.** If code got copied in and the owner can't explain it, it doesn't merge. The whole point is understanding.
4. **Measure tokens from day 1.** The project exists because of context economics. Every stage keeps a visible token meter.
5. **The harness must be boring.** When a result looks weird, the question must never be "or is my harness buggy?" Tests stay green; the acceptance suite runs before and after every feature.
6. **Design note before feature.** One page in `docs/notes/` — what the seniors do, what we'll build, how we'll know it works.
7. **Ask the owner** when a decision changes scope or direction; he answers fast and enjoys the questions.

## Doc conventions

- English for all project docs.
- Reports use a storytelling tone: what was the problem → what did we do → why → what happened.
- Prose + tables over ASCII-art diagrams. Short pseudocode blocks are fine.

## Legacy context

- `docs/harness-context-v3.md` — an earlier brief written for an **Agent-SDK-based** research harness. Its decisions D1–D3 (build on SDK, billing path, orchestrator design) do **not** govern this project. But its pain-point analysis (§2, the 5/95 signal ratio) and feature sketches (§4 A–E: `report_finding` schema, dump-to-file diet, fork-vs-fresh policy, checkpointing, cache TTL) are still gold — they are the **spec source for Stage 3**.
- `archive/prompt/` — eight real prompts from months of research work (plan / run-overnight / summarize / compact / clean). They document the owner's actual workflow and its pain. Stage 3.2 turns them into structured templates.
