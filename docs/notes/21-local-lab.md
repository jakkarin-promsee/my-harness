# Note 21 — Stage 2.15: the local lab (faster and smarter on the same 4 GB)

> Lab log, 2026-07-07. Not a code feature — an experiment with numbers. Sources: [K/V context quantisation in Ollama](https://smcleod.net/2024/12/bringing-k/v-context-quantisation-to-ollama/) (q8_0 halves KV memory, perplexity delta 0.002–0.05 — undetectable; flash attention is a prerequisite), [Ollama FAQ](https://docs.ollama.com/faq), the 4–8 GB surveys (ROADMAP2 §7). Honesty rule up front: on 4 GB, "smarter" comes mostly from the harness — measure, don't hope.

## The question

The card is an RTX 3050 Ti Laptop, 4 GB. The workhorse (`qwen3:4b-instruct`, Q4_K_M) has a 4.1 GB footprint at ctx 8192 — it **doesn't fit**: baseline shows a 45 %/55 % CPU/GPU split, and generation pays for it. Two free knobs we've never turned (`OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`) shrink the KV cache; the questions, in order:

1. Does the tuned config speed up generation and/or move more layers onto the GPU?
2. Under quantized KV, how far can the context window grow (8,192 → 12,288 → 16,384) before the gate breaks or speed collapses?
3. Bake-off on the grown 11-task suite: does the incumbent still beat the current 4 GB tier (phi4-mini, gemma3:4b)?

## Method

- Speed: 3× a fixed probe (same ~360-token prompt, ~150-word answer, `num_predict` 300) against native `/api/chat`; report **median gen tok/s** and prompt tok/s from Ollama's own `eval_count`/`eval_duration`. Warm model (run 1 discarded when cache-cold).
- Memory: `nvidia-smi` (VRAM used) + `ollama ps` (footprint, CPU/GPU split).
- Quality: the full acceptance gate (11 tasks, free) must stay 11/11 per config.
- Server control: kill the tray app, run `ollama serve` with the experiment's env; the machine-wide config (`setx`) is applied once at the end, for the WINNING config only. Revert path: remove the vars, restart the tray app.

## Results

### Step 1 — baseline (FA off, KV f16, ctx 8192)

| Metric | Value |
|---|---|
| gen | **11.3 tok/s** (11.2–11.6) |
| prompt | ~3,900 tok/s warm (731 cold) |
| footprint | 4.1 GB, **45 %/55 % CPU/GPU** |
| VRAM used | 2,651 / 4,096 MiB |

### Step 2 — flash attention + q8_0 KV (ctx 8192)

Server startup config verified in the log: `OLLAMA_FLASH_ATTENTION:true OLLAMA_KV_CACHE_TYPE:q8_0`.

| Metric | baseline → tuned |
|---|---|
| gen | 11.3 → **12.8–13.2 tok/s** (**+13 %**) |
| prompt (warm) | ~3,900 → ~3,900 tok/s (unchanged) |
| footprint | 4.1 GB → **3.6 GB** |
| split | 45 %/55 % → **36 %/64 % CPU/GPU** |

The mechanism is visible: the halved KV cache doesn't buy *context* here — it buys **GPU residency**. More layers fit on the card, so generation speeds up. Free speed, quality untouched (same weights, KV delta immeasurable per the source).

### Step 3 — the context sweep: 8,192 is the ceiling

**12,288 does not load.** Twice, reproducibly: the warmup run thrashes (weights already overflow VRAM; +306 MiB of KV deepens the CPU spill) until Ollama's own `OLLAMA_LOAD_TIMEOUT` (5 m) kills it — `msg="Load failed"` after 5m10s, HTTP 500. At 8,192 the same load takes **10.8 s**. 16,384 skipped: strictly more memory, same failure mode, 5 minutes of system thrash per attempt.

The honest correction to the plan's hope: *q8_0 converts to extra context only when the weights fit with room to spare.* On a card where the model itself overflows, the savings are consumed by layer placement — the ceiling stays 8,192, it just runs faster there. (A 10,240 intermediate point would refine the boundary but changes no decision; skipped.)

### Step 4 — the bake-off (grown 11-task suite, tuned config)

Per the **evaluate-model** skill: smoke first (does it call tools? does it fabricate?), gate only if the smoke survives.

| Model | Size | Verdict |
|---|---|---|
| `qwen3:4b-instruct` (incumbent) | 2.5 GB | **11/11 on the tuned config** (2,649 out-tokens) — retains the crown |
| `phi4-mini` | 2.5 GB | **disqualified at smoke**: printed the tool call as *text* (a JSON blob in `content`) with a fabricated `result` field — an invented poetry-style pyproject.toml. Both disqualifiers at once, the llama3.2:3b disease. The survey's "structured-output surprise" may hold for JSON-mode, but tool-calling through Ollama's template it cannot do |
| `gemma3:4b` | 3.3 GB | **disqualified at smoke**: Ollama itself refuses — `"registry.ollama.ai/library/gemma3:4b does not support tools"` (no tools in the official template). Can't drive a tool-calling harness at all |

Both losers stay pulled (llama3.2:3b precedent — the losers list is evidence; ~5.8 GB disk, owner may prune).

## Verdict & applied config

- **Applied machine-wide** (2026-07-07, `setx`, user scope): `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_CONTEXT_LENGTH=8192` (unchanged). Tray app restarted with the env; verified live. **Revert path:** delete the two new vars (`reg delete` or System → Environment Variables), restart the Ollama app.
- Net effect on the same 4 GB: **+13 % generation speed** (11.3 → ~12.8 tok/s), footprint 4.1 → 3.6 GB, GPU share 55 → 64 %, quality unchanged (gate 11/11), context ceiling **stays 8,192** — the quant dividend goes to layer placement, not window size, because the weights themselves overflow the card.
- Workhorse unchanged: `qwen3:4b-instruct`. The honesty rule held: the harness (modes, roles, skills, ACI) is where "smarter" comes from on this hardware; the lab bought "faster" only.
- **Casualty of the lab:** the Ollama tray app got wedged by the kill/restart cycles — it starts but its API-server child dies silently (empty `server.log`). A detached `ollama serve` (tuned env) carries the machine until the next reboot; full story and the revert path in `docs/problem.md` #0. Final config re-verified on it: **12.9 tok/s**.
