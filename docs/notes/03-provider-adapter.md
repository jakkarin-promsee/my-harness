# Note 03 — Stage 2.1: the provider adapter layer

> Written 2026-07-06, before implementing. Sources studied: opencode `provider/` (per-provider transform registry), aider `models.py` (+litellm as the "someone else's adapter" option), mini-swe-agent `models/` (litellm wrapper), Anthropic Messages API docs.

## What the seniors do

Two schools: **outsource the dialect problem** (aider/mini-swe → litellm, one dependency that speaks everything) or **own a thin adapter per provider** (opencode, Claude Code). We own it — the whole point is learning what litellm hides. The universal shape underneath: the loop speaks ONE internal message format; each adapter translates at the boundary, both directions.

## What we build

- `providers/base.py` — the `Model` protocol: `complete(messages, tools) -> {"message", "finish_reason", "usage"}`. Our internal dialect = OpenAI-style (the loop already speaks it; two of three providers are native in it).
- `providers/anthropic.py` — the interesting one. Anthropic's `/v1/messages` differs from chat/completions in SIX ways, and the adapter must translate BOTH directions because history gets replayed every call:

| Concept | OpenAI-compat | Anthropic native | Direction |
|---|---|---|---|
| System prompt | `role:"system"` message | top-level `system` param | out |
| Tool schema | `{type:"function", function:{...,parameters}}` | `{name, description, input_schema}` | out |
| Tool result | `role:"tool"` + `tool_call_id` | `user` msg with `tool_result` blocks (consecutive results merge into ONE user turn — roles must alternate) | out |
| Assistant reply | `content` string + `tool_calls[]` | list of `text` / `tool_use` blocks | in + out |
| Tool arguments | JSON **string** | JSON **object** (`input`) | both |
| Finish/usage | `stop/tool_calls/length`, `prompt_/completion_tokens` | `end_turn/tool_use/max_tokens`, `input_/output_tokens` | in |

- Translation lives in module-level pure functions (`to_anthropic_*`, `from_anthropic_reply`) so tests need no HTTP; `complete()` is a thin shell around them (x-api-key + anthropic-version headers, required `max_tokens`).
- CLI: `anthropic` provider entry (key from `ANTHROPIC_API_KEY`, model from `ANTHROPIC_MODEL`, default `claude-haiku-4-5-20251001`); missing key exits with a friendly pointer to the constitution.

## How we know it works

`tests/test_anthropic.py`: round-trip translation of a full tool conversation (system, tool call, parallel results merging, replay of a normalized assistant msg), stop_reason/usage mapping, plus one `complete()` call against a monkeypatched `requests.post`. **Live call NOT possible:** `ANTHROPIC_API_KEY` stays unset by constitutional order until the owner sets it deliberately — logged in `docs/problem.md`.
