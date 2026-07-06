# CLAUDE.md — researcher-harness

## What this project is

A **from-scratch agent harness**, built to learn how harnesses (Claude Code, Codex CLI, opencode, aider, ...) actually work under the hood — and to own an independent one if the day ever comes when Claude isn't available here ("claude2 insurance"). Learning-first side project: **understanding beats features, every time.**

What this project is **NOT**:

- It is NOT the owner's research project. That lives elsewhere and keeps running on Claude Code as usual. This harness never touches real research work until Stage 3 proves itself.
- It is NOT an Agent SDK wrapper. (See "Legacy context" below — an older brief in this repo says "build on the Agent SDK"; that decision belonged to a different plan and does not govern this project.)
- It is NOT a product. One user: the owner.

Read [ROADMAP.md](ROADMAP.md) before doing anything. It holds the full story, the staged plan, and the exit criteria for every stage.

## Current status

- **Stage: 2 (Copy the seniors) — features 2.0–2.8 ALL done (2026-07-06); 2.9 stretch skipped.** 56 offline tests (`uv run pytest -q`); exit-gate suite `uv run python acceptance/run.py <provider>`: **7/7 on gemini-2.5-flash-lite**, local qwen3:4b leg pending. **Read [docs/problem.md](docs/problem.md)** — owner decisions block the formal Stage-2 exit (local-model choice) and Anthropic live test. Model lessons: `llama3.2:3b` fabricates — unusable; `qwen3:4b` never gets `temperature: 0`; flash-lite throws 503s (retry handles) and occasional empty replies (nudge handles).
- Update this line whenever a stage milestone completes. This is the first thing a fresh session should check.

## Stack & environment

| Thing | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Managed with `uv` |
| Primary dev model | Local via Ollama | RTX 3050 Ti Laptop, 4 GB VRAM → 3–4B tool-calling models (candidates: `qwen3:4b`, small Gemma; Stage 0 tests which one actually tool-calls reliably) |
| Fallback dev model | Gemini API (flash / flash-lite) | Via its OpenAI-compatible endpoint. ~$19 of credit total — guard it |
| Wire protocol | OpenAI-compatible chat completions | Both Ollama (`http://localhost:11434/v1`) and Gemini speak it → provider swap is one `base_url` change |
| Anthropic API | Not yet | `ANTHROPIC_API_KEY` must stay **unset** until Stage 2.1 adds a native adapter intentionally (a stray key silently bills pay-as-you-go) |

**Budget rule:** debug agent-loop logic on the local model (an infinite-loop bug burns $0 locally); validate response *quality* on Gemini. Never point a possibly-buggy loop at a paid endpoint.

## Repo map

| Path | What it is |
|---|---|
| `ROADMAP.md` | The plan. Stages 0–3, exit criteria, reference shelf |
| `docs/notes/` | Design notes — one per feature, written *before* implementing (created in Stage 0) |
| `labs/` | Tiny throwaway experiments (raw API calls, wire-format studies) (created in Stage 0) |
| `harness/` | **The living codebase** (Stage 2+): `core/` loop, `providers/`, `tools/`, `cli/`, `prompts/`. Run: `uv run python -m harness [ollama\|gemini\|anthropic] [-y] [--resume] [--sessions]` |
| `tests/` | FakeModel pytest suite — the loop's contract, zero tokens. Run: `uv run pytest -q` |
| `acceptance/` | Stage-2 exit gate: live-model suite. Run: `uv run python acceptance/run.py <provider>` |
| `commands/` | Slash-command template library (`/name args` reads `commands/name.md`) |
| `harness.toml` | Permissions policy (allow/ask/deny per tool), versioned on purpose |
| `AGENTS.md` | Project memory injected into the harness's own system prompt |
| `docs/problem.md` | Open problems needing the owner — check when returning to the project |
| `mvp/` | Stage 1 single-file harness — **frozen** as the learning artifact; `mvp/ACCEPTANCE.md` + fixtures still serve as the acceptance suite |
| `prompt/` | The owner's **real prompt library** from the research project. Read-only reference — do not edit. Raw material for Stage 3.2 (prompt middleware) |
| `harness-context-v3.md` | Legacy brief (see below) |

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

- `harness-context-v3.md` — an earlier brief written for an **Agent-SDK-based** research harness. Its decisions D1–D3 (build on SDK, billing path, orchestrator design) do **not** govern this project. But its pain-point analysis (§2, the 5/95 signal ratio) and feature sketches (§4 A–E: `report_finding` schema, dump-to-file diet, fork-vs-fresh policy, checkpointing, cache TTL) are still gold — they are the **spec source for Stage 3**.
- `prompt/` — eight real prompts from months of research work (plan / run-overnight / summarize / compact / clean). They document the owner's actual workflow and its pain. Stage 3.2 turns them into structured templates.
