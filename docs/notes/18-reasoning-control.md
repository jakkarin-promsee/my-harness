# Note 18 — Stage 2.12: reasoning control (the real CoT feature)

> Written 2026-07-07, before implementing — after a probe session against the local Ollama (see "what the probes found"). Sources studied: [Ollama thinking docs](https://docs.ollama.com/capabilities/thinking) (`think`: booleans on qwen3/deepseek-class, `"low"/"medium"/"high"` on gpt-oss-class; trace in `message.thinking`), [aider `--reasoning-effort`](https://aider.chat/docs/config/reasoning.html), [Anthropic extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) (budget_tokens; max_tokens must exceed it). Full audit: ROADMAP2 §2.

## Why a knob and not a display

Display shipped in 2.9a. What's missing is *control* — and our own Stage-2 data is the whole argument:

| Model (same suite) | Score | Output tokens |
|---|---|---|
| qwen3:4b-instruct (non-thinking) | 7/7 | 1,460 |
| qwen3:4b (thinking) | 5/7 | 13,614 |

**10× the tokens for a worse score.** The frontier default is thinking OFF locally, escalate on demand. `/think` is that escalation path.

## What the probes found (2026-07-07, Ollama 0.31.1)

1. **The OpenAI-compat `/v1` endpoint silently ignores `think`.** `think=false` on the thinking model still burned its whole budget reasoning; `think=true` on the instruct model didn't even error. Honest reasoning control on Ollama means speaking the **native `/api/chat`** dialect. (This is why 2.12 ships a new adapter, not a new body field.)
2. **The native dialect really is a dialect**: `tool_calls[].function.arguments` is an **object** (the OpenAI wire uses a JSON *string*); tool results are `{role:"tool", content, tool_name}` (not `tool_call_id`); the trace is `message.thinking`; streaming is NDJSON lines (not SSE); `done_reason`/`prompt_eval_count`/`eval_count` replace `finish_reason`/usage. Round trip verified by hand before any adapter code.
3. **This machine's models bound what the knob can do locally.** The 2507 refreshes are fixed-mode: the instruct workhorse *never* thinks (`think=true` ignored), and `qwen3:4b` (thinking-2507) *can't stop* — with `think=false`, 0.31.1 merely stops separating the trace, so it reasons into `content` (worse than on). On this hardware, "which variant" is the real local knob (the evaluate-model skill); `/think` earns its keep on capable models (deepseek-r1, gpt-oss, hybrid qwen3) and on the cloud legs.

## What we build

- **The vocabulary**: `/think off|on|low|medium|high` at runtime (bare `/think` shows the current value); `think:` default per agent (parsed since 2.11, applied now); a fresh `/agent` switch applies the agent's default, `/think` afterwards overrides. The value lives as a `.think` attribute on the model adapter — same pattern as `max_tokens`.
- **`providers/ollama_native.py`** — the native `/api/chat` adapter, translating BOTH directions (the invariant): outgoing, history's argument *strings* become objects and each tool result gains `tool_name` recovered from the preceding assistant message's call ids; incoming, `thinking` → the normalized `reasoning` key, arguments objects → strings, `done_reason` → `finish_reason`, eval counts → usage. NDJSON streaming feeds the same `on_delta` protocol as 2.9b. Think mapping: off→`false`, on→`true`, low/medium/high→level string. **The `ollama` provider switches to this adapter** — the `/v1` compat adapter remains for Gemini/any-OpenAI-endpoint (and its `<think>` scraper stays, per 2.9a).
- **OpenAI-compat adapter**: `.think` maps to `reasoning_effort` (low/medium/high; on→medium; off→omitted — our Gemini model, flash-lite, defaults to thinking-off, so omit==off today; noted as a caveat for thinking-default models).
- **Anthropic adapter**: `.think` maps to `thinking: {type: "enabled", budget_tokens}` — low 1,024 / on+medium 4,096 / high 16,384, and `max_tokens` is raised to `budget + 1,000` when needed (the API requires max_tokens > budget). Offline-tested only until the key arrives (problem.md).
- **Policy unchanged**: thinking never re-enters history (2.9a); the within-turn-preserve variant (DeepSeek-style) stays a documented non-goal.

## Lab results (2026-07-07, after implementing)

Same question ("17 × 23?"), `qwen3:4b` (thinking-2507) through the native adapter in the streaming REPL:

| Knob | Out-tokens | Trace | Context after the turn |
|---|---|---|---|
| `/think on` | 247 | separated, streamed dim, **stripped from history** | ~462 tokens |
| `/think off` | 270 | 0.31.1 half-suppression: reasoning leaks into *content* — and **content persists in history** | ~671 tokens |

That last column is the whole feature in one number: a separated trace costs the turn but not the future; leaked reasoning bills every later call. And the cloud leg: Gemini flash-lite accepted `reasoning_effort: "low"` (compat mapping) — reply was 3 completion tokens but **186 total**, i.e. ~169 hidden thinking tokens, visible only because the meter reports totals.

## How we know it works

- **pytest**: `test_ollama_native.py` — outgoing translation (string→object args, tool_name recovery, think mapping, num_predict), incoming normalization (thinking→reasoning, object→string args, done_reason, usage), NDJSON stream assembly + on_delta order. Plus think-mapping tests in the compat and Anthropic suites.
- **live, free**: the whole local gate now rides the native adapter — 9/9 proves the dialect end to end. The think lab (this note, above) records off/on reality on both local variants.
- **live, cheap**: one tiny `reasoning_effort` probe against Gemini flash-lite confirms the compat mapping is accepted (and the full gemini gate re-runs at the end of 2.10–2.12).
