---
name: evaluate-model
description: Evaluate a candidate model as the harness workhorse — pull it, configure .env, smoke-test, run the exit gate, compare token burn, record the verdict. Use when trying a new Ollama model or when the current workhorse misbehaves.
---

# Evaluate a model

This procedure has run three times (llama3.2:3b → qwen3:4b thinking → qwen3:4b-instruct won) and made the current call. Model evaluation is a core competency here — the whole "claude2 insurance" premise depends on being able to re-run this whenever the landscape shifts.

## Hard constraints

- **4 GB VRAM** (RTX 3050 Ti Laptop) — the model must fit, or it swaps and crawls.
- Prefer **instruct / non-thinking** variants: thinking variants burned ~10× the output tokens here and died at length limits.
- Evaluate on **local only.** An unproven model driving the loop is exactly the "possibly-buggy loop" the budget rule bans from paid endpoints.

## Steps

1. `ollama pull <model>`; set `OLLAMA_MODEL` in `.env`; confirm `OLLAMA_CONTEXT_LENGTH=8192` is in effect (Ollama's 4096 default silently truncates).
2. **Smoke:** `uv run harness ollama`, one simple tool-using request ("read pyproject.toml and name the deps"). Watch for the two disqualifiers: does it call tools at all, and does it fabricate?
3. **Gate:** `uv run python acceptance/run.py ollama`. Required: **7/7**. Note the out-token count — the sitting champion (qwen3:4b-instruct) does the suite in ~1,460 out-tokens (2026-07-07); a candidate burning multiples of that loses even at 7/7.
4. **Quirk sweep:** temperature behavior (never 0 on the qwen3 family), empty replies, cut-offs, tool-call JSON fidelity.
5. **Record the verdict** in the root `CLAUDE.md` status line — winner *or loser*, with the one-line reason. The losers list is as valuable as the winner.
6. If the candidate loses, revert `.env`.
