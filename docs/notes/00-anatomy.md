# Note 00 — The Anatomy of a Harness

> Written during Stage 0 recon (2026-07-06). Sources: `labs/00–02` (run them, read them), mini-swe-agent's `agents/default.py`, Thorsten Ball's *How to Build an Agent*, Anthropic's *Building Effective Agents* and *Effective Context Engineering*.
>
> **Owner's exit exam is at the bottom.** Stage 0 isn't done because this file exists — it's done when you can answer the quiz without looking.

## The one-sentence version

A harness is a program that keeps a `messages` list, sends the *whole* list to a chat API in a loop, executes the tool calls the model asks for, and appends the results — plus a lot of hard-won bookkeeping around that loop.

## The six organs

| # | Organ | What it does | Where you saw it |
|---|---|---|---|
| 1 | **Provider client** | One HTTP POST to `/v1/chat/completions`; JSON in, JSON out. No hidden server state — the "conversation" lives on OUR side. | `labs/00` — the whole file |
| 2 | **Message list (the context)** | The `messages` array. Every call re-sends all of it; `usage.prompt_tokens` grows every turn. This list is the thing Pain #1 is about — and in our own harness, editing it is just Python list surgery. | `labs/00` request body; mini-swe-agent's `self.messages` |
| 3 | **Tool registry + executor** | Local functions plus their JSON-schema "advertisements". The model only ever *asks*; the harness runs the function and appends a `role:"tool"` message with the echoed `tool_call_id`. | `labs/01` steps 0–4 |
| 4 | **The loop** | `while finish_reason == "tool_calls": execute, append, call again`. That's the entire "agent" part. Everything else is decoration. | `labs/01` did one iteration by hand; mini-swe-agent's `run()` |
| 5 | **System prompt** | The first message: identity, rules, environment info. In real harnesses this is where most behavior-shaping lives (Claude Code's is thousands of tokens). | `labs/00` — the one-liner system message |
| 6 | **UI / REPL** | Whatever lets the human type and read: a terminal REPL at minimum. Also where permission gates ("run this shell command? y/n") live. | Not built yet — that's Stage 1 |

## Two schools of getting actions from the model

This split matters when reading other people's harnesses:

- **School A — native tool calling** (our labs, Claude Code, opencode): send a `tools` array; model replies with structured `tool_calls`; arguments arrive as a JSON *string* you must `json.loads`. Reliable schemas, but requires a model trained for it.
- **School B — parse the text** (mini-swe-agent): no `tools` param at all. The system prompt says "reply with one bash code block"; the harness regex-extracts and runs it. Works with *any* model — that's how a 100-line agent with zero dependencies scores >74% on SWE-bench. The cost: everything is bash, no fine-grained tools.

Our MVP uses School A (we want to learn the standard protocol), but School B is the fallback if small local models keep fumbling tool calls.

## What mini-swe-agent adds beyond the naive loop (worth stealing later)

Reading `agents/default.py`, the ~100 "extra" lines over the bare loop are all *survival bookkeeping* — a preview of Stage 2:

- **Limits**: `step_limit`, `cost_limit`, wall-clock limit — a loop that can't stop is a token furnace (this is why we debug on Ollama, where a runaway loop costs $0).
- **Format-error tolerance**: N consecutive malformed replies → give up gracefully, don't spin forever.
- **Trajectory saving**: every step, the full `messages` list is serialized to a JSON file. Crash-safe by construction — and it's literally our Stage 2.3 sessions feature.
- **Templates**: system/instance prompts are Jinja templates with variables (task, cost so far, elapsed time) rendered in.

## Field-by-field cheat sheet (the wire format)

| Field | Direction | Meaning |
|---|---|---|
| `model` | → | which model runs the request |
| `messages[].role` | → | `system` / `user` / `assistant` / `tool` |
| `tools[]` | → | JSON-schema advertisements of callable functions |
| `max_tokens`, `temperature` | → | generation cap / randomness (0 = deterministic) |
| `choices[0].message` | ← | an assistant message; append it verbatim to `messages` |
| `choices[0].finish_reason` | ← | `stop` (done) / `tool_calls` (wants a tool) / `length` (truncated!) — the loop is a switch on this |
| `message.tool_calls[].id` | ← | must be echoed back as `tool_call_id` in the result message |
| `message.tool_calls[].function.arguments` | ← | the args — a JSON **string**, not an object |
| `usage.prompt_tokens` / `completion_tokens` | ← | what we sent / what it generated. Watch prompt_tokens climb — that's Pain #1 in numbers |
| `message.reasoning` | ← | (some models, e.g. qwen3) visible chain-of-thought before the answer/tool call — observed live in lab 01; not part of the strict OpenAI schema, a reminder that "compatible" endpoints still have dialects |

## Owner's exit exam (no peeking)

1. The API server keeps no conversation state. So where does the "memory" of a chat live, and what single consequence does that have for token costs as a session grows?
2. In the tool round trip, there are **two** messages you must append between the two HTTP calls. Which two, and what breaks if you forget the first one?
3. What are the three `finish_reason` values you'll meet, and what should the loop do for each?
4. `function.arguments` has a classic gotcha — what is it?
5. Why can mini-swe-agent work with literally any model, and what does it give up for that?
6. Your session hits 500k tokens and 95% is stale tool output. In Claude Code you must `/compact` (a paid model call that rewrites everything). In YOUR harness, what is the equivalent operation and what does it cost?

*(Answers are all in this note, the labs' comments, or one run of the labs.)*
