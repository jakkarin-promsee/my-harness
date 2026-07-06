# Note 07 — Stage 2.5: context management v1 (the standard way)

> Written 2026-07-06, before implementing. Sources studied: Claude Code's /compact + auto-compact threshold, Anthropic's *Effective Context Engineering* (compaction trade-offs section), mini-swe-agent (which simply... doesn't — task runs are short by design).

## What the seniors do

Three-part standard: (1) **know the budget** — model context window is config, live usage is estimated; (2) **warn early** — Claude Code auto-compacts near the limit, others warn; (3) **compact = model call** — send the transcript to the model, get a summary back, REPLACE the history with it. Everyone ships this. Everyone also documents the same two costs — the summary call itself is expensive, and summarization is lossy for *everything*, signal included. **We build it anyway**: it's the baseline Stage 3.1's surgical ops must measurably beat, and you can't beat what you haven't measured.

## What we build

- `core/budget.py`:
  - `estimate_tokens(messages)` — `len(json.dumps)/4` heuristic. Crude but provider-neutral and monotonic (we can't use `usage` for this: Ollama's prompt_tokens excludes KV-cached tokens).
  - `budget_line(estimate, window)` — the meter string, flips to a warning at 80%.
  - `compact(model, messages)` — summarizer call (transcript as JSON text, no tools), returns `([system, summary-as-user-msg], usage)`. The usage is *shown* — the cost of compaction must be visible, that's the whole point of measuring the baseline.
- CLI: `context_window` per provider (ollama 4096 — Ollama's default num_ctx; gemini 1,048,576; anthropic 200,000); budget line printed after every turn; `/tokens` and `/compact` slash commands (first slash handling in the REPL — 2.7 generalizes it).
- Compaction starts a **new session file** (old transcript stays intact on disk; resume of the old id resurrects the full pre-compact history — that's a feature).

## How we know it works

pytest: estimator sane + monotonic; budget line warns at exactly ≥80%; compact with FakeModel returns the two-message shape, preserves system message, surfaces usage. Live: at the exit gate, /tokens + /compact exercised on Gemini.
