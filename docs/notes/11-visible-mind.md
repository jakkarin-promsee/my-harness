# Note 11 — Stage 2.9a: the visible mind (narration, thinking, surviving the token limit)

> Written 2026-07-07, before implementing. Sources studied: Claude Code's transcript behavior (preamble text printed *before* each tool runs; thinking shown dimmed, never re-sent to the model), Anthropic's extended-thinking API docs (thinking blocks from prior turns are stripped server-side — thinking is a per-turn scratchpad, not conversation), Ollama/qwen3 dialect observed in `labs/01` (`message.reasoning`; some templates embed `<think>…</think>` in content instead), and our own `acceptance-local.log` (both local failures = `finish_reason: length` thinking-death).

## The problem, in one paragraph

The harness runs tool → tool → tool in silence and only speaks at the end. Three causes found by reading our own code: (1) `loop.py` never emits assistant `content` that arrives *alongside* tool_calls — the model may already be narrating and we swallow it; (2) qwen3's `reasoning` field is never displayed, and worse, it is appended into history and session files, polluting a 4k/8k local window with dead thinking; (3) nothing in `prompts/system.md` ever *asks* the model to narrate — Claude Code's interleaved voice is mostly prompted, not architectural. Bonus discovery: both local acceptance failures were `finish_reason: "length"` — qwen3 burned the hardcoded `max_tokens: 2000` on thinking, and the loop treats `length` as fatal.

## What the seniors do

- **Claude Code** prints the assistant's preamble text before running the tools in the same reply, and renders thinking in a dimmed style. Thinking from *previous* turns is never re-sent (the Anthropic API strips it server-side). The narration style itself is system-prompt choreography.
- **mini-swe-agent** survives malformed/limit replies by *messaging the model about the problem* instead of crashing — the same philosophy as our empty-reply nudge.
- **Everyone** makes `max_tokens` configuration, not a constant: thinking models need generation headroom that non-thinking cloud models don't.

## What we build

1. **Adapter normalizes thinking out of the message** (`providers/openai_compat.py`, new pure function `normalize_reply(data)` in the anthropic.py style): pop `message.reasoning` / `message.reasoning_content`, or extract a leading `<think>…</think>` block from content (three dialects, one normalized shape). The reply dict grows an optional top-level `"reasoning"` key; the message appended to history is *clean* — thinking never re-enters context, never lands in session JSONL, never inflates the chars/4 estimate.
2. **Loop emits the mind** (`core/loop.py`):
   - reasoning present → `emit_thinking(text)` (injected; default formats through `emit`, the REPL overrides with ANSI-dim so it *looks* like inner voice).
   - tool_calls with non-empty `content` → emit the preamble before executing (`agent> …`).
3. **Length-nudge** — the empty-reply nudge's twin: on `finish_reason == "length"`, instead of killing the turn, append one user nudge — *"cut off; do not think out loud; call the tool now or answer briefly"*, ending in `/no_think` (qwen3's documented soft switch that disables thinking for the next turn; inert text for every other model). One nudge per turn; a second `length` stops as before. Truncated tool_calls are still never executed.
4. **Per-provider `max_tokens`** — constructor parameter on both adapters, value in the `PROVIDERS` table: ollama 4096 (thinking headroom, free tokens), gemini/anthropic stay 2000. Ollama's `context_window` now reads `OLLAMA_CONTEXT_LENGTH` (set to 8192 on this machine, 2026-07-07 — problem.md #2 resolved).
5. **Narration rules in `prompts/system.md`**: one line before every tool call saying what and why; after a surprising result, say what was learned. Short — every rule costs local context.

## How we know it works

pytest, zero tokens: preamble content is emitted before tool execution; `reasoning` in a reply reaches `emit_thinking` and is *absent* from the appended message (FakeModel replies carry the normalized shape); one `length` reply → nudge appended → next reply consumed; two `length` replies → turn ends after exactly two calls; truncated tool calls still never execute. New `tests/test_openai_compat.py` pins `normalize_reply` for all three thinking dialects plus the plain pass-through. Then live: acceptance suite re-run on local + Gemini (task 5's bake-off).
