# Problems & owner decisions

> Things the autonomous Stage-2 run could not finish alone, plus decisions
> that are yours to make. Written 2026-07-06. Delete items as you resolve them.

## 1. The local model can't pass the full acceptance suite

**What happened:** `gemini-2.5-flash-lite` passes 7/7 (`uv run python acceptance/run.py gemini`). The local leg (`qwen3:4b`, run 2026-07-06 with Stardew sharing the GPU) scored **5/7** — honestly better than feared: it passed find-fix-prove, grep, exact-edit, glob, and read-report. The two fails: **A** (create-and-run — its known thinking-death on write-from-scratch tasks; burned the token budget reasoning, never created the file) and **G** (subagent — returned an empty final answer). It also spent 13.6k output tokens vs Gemini's 0.75k for the same suite: thinking is expensive. Full log: `acceptance-local.log`.

**Your options (pick one, tell me, I'll do the rest):**
- **(a) Raise Ollama's context window** — see item 2; cheap, might help, won't fix slow thinking.
- **(b) Try a different small model** — e.g. `qwen2.5-coder:3b` (coder-tuned, no thinking mode, ~2 GB) as the local workhorse: `ollama pull qwen2.5-coder:3b`, then `$env:OLLAMA_MODEL='qwen2.5-coder:3b'`.
- **(c) Accept Gemini as the primary acceptance provider** and demote the local leg to "smoke test" (task B only) until better hardware/models. ROADMAP's "two providers" exit criterion would be amended honestly.

## 2. Ollama's context window is 4,096 tokens (config, needs you)

Our system prompt + 8 tool schemas + AGENTS.md already eat a chunk of that; long tasks will silently truncate (that's the "not remember all conversation" you noticed). Fix (one-time, admin-free):

```powershell
setx OLLAMA_CONTEXT_LENGTH 8192
```

then **quit and restart the Ollama tray app**. Verify with `ollama ps` (CONTEXT column) after your next request. Costs VRAM — with the game running, 8192 is the sensible ceiling for the 4 GB card.

## 3. Anthropic adapter is live-untested (deliberate)

`harness/providers/anthropic.py` is fully built and offline-tested (7 tests, mocked HTTP), but per the constitution `ANTHROPIC_API_KEY` stays unset until you set it on purpose. When that day comes: put the key in `.env`, then `uv run python -m harness anthropic` and run acceptance task B as a smoke test. Until then, treat the adapter as "compiles, untested against the real wire".

## 4. README.md is a placeholder

Your `README.md` stub ("Project Name", b-tcom links) got committed. Say the word and I'll write a real one (what the project is, quickstart, repo map) — or replace it yourself.
