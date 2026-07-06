# Note 12 — Stage 2.9b: streaming (watch it think, watch it talk)

> Written 2026-07-07, before implementing. Sources studied: the OpenAI SSE chunk format (`data: {json}` lines, `choices[0].delta` fragments, `data: [DONE]` terminator, `stream_options: {"include_usage": true}` for the usage-bearing final chunk), opencode's streaming pipeline (UI consumes text deltas; tool calls are *assembled* from indexed fragments and only executed complete), and Claude Code's UX (text and thinking render live; tools never partially execute).

## Why now

On the 4 GB GPU a single turn legitimately takes minutes. Non-streaming means minutes of dead silence and then a wall of text — the single biggest "this doesn't feel like Claude Code" gap after note 11's fixes. Streaming turns the wait into watching the model think (dim) and narrate (normal), token by token. This was Stage 1's consciously deferred 2.9 item; the deferral reason ("SSE + delta-assembled tool calls triple the parsing code") is now the lesson to learn, not the cost to dodge.

## What the seniors do

Everyone splits the same way: **deltas for humans, complete objects for the loop.** Text/thinking fragments go straight to the UI as they arrive; tool-call fragments (`delta.tool_calls[].function.arguments` arrives in pieces, correlated by `index`) accumulate in a buffer and only the finished call is executed. The agent loop itself never changes: it still receives one complete reply per model call.

## What we build

- `providers/openai_compat.py` grows two pure functions (same offline-testable style as `normalize_reply`):
  - `parse_sse(lines) -> list[chunk]` — strip `data: ` prefixes, drop keep-alives, stop at `[DONE]`, `json.loads` each event.
  - `assemble_chunks(chunks) -> raw-reply dict` — concatenate `delta.content` / `delta.reasoning` / `delta.reasoning_content`; merge `delta.tool_calls` by `index` (id + name arrive once, `arguments` accumulates); take the last non-null `finish_reason`; adopt `usage` from whichever chunk carries it. Output has the *same shape as a non-streaming response body*, so it feeds straight into `normalize_reply` — one normalization path, streamed or not.
- `OpenAICompatModel(..., on_delta=None)`: when unset, behavior is byte-identical to today (tests, acceptance, subagents). When set, the POST adds `stream` + `stream_options` and `complete()` emits `on_delta(kind, text)` events while reading the wire: `"reasoning"` and `"content"` fragments as they arrive, one final `"end"` when the stream closes (so the printer can finish its line). The returned reply gains `"streamed": True`.
- `core/loop.py`: when `reply["streamed"]`, skip re-emitting what the human already watched — the thinking block, the preamble, the final `agent>` text. Everything else (append, execute, nudge) is untouched: streaming is presentation, the contract is the contract.
- `cli/repl.py`: a small `StreamPrinter` state machine — dim while `reasoning` flows, `agent> ` prefix when `content` starts, newline on `end`. Wired only into the **top-level** agent's model; the subagent gets its own non-streaming model instance so `[sub]`-prefixed lines don't interleave with a half-printed stream (documented simplification).
- Anthropic adapter: stays non-streaming (it's the insurance adapter; its SSE dialect is different work for a later day).

## How we know it works

Offline: `parse_sse` handles prefixes/keep-alives/`[DONE]`; `assemble_chunks` reassembles content split across chunks, reasoning deltas, tool-call arguments split across chunks, two parallel calls by index, usage from the trailing chunk; a mocked-HTTP `complete()` (test_anthropic.py style, fake `iter_lines`) verifies the on_delta event order (`reasoning*, content*, end`) and that the normalized reply matches its non-streaming twin. Live: REPL run on ollama + one Gemini turn — same answers as before, now visible while they happen.
