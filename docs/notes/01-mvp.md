# Note 01 — Stage 1 MVP design (`mvp/harness.py`)

> Written 2026-07-06, before implementation (working rule 6). Sources studied: Thorsten Ball's *How to Build an Agent* (~315-line tutorial agent), mini-swe-agent `agents/default.py` (run/step loop, limits), aider (`--yes` flag precedent).

## What the seniors do

| Concern | Ball's tutorial | mini-swe-agent | We copy |
|---|---|---|---|
| Core shape | REPL → loop → tools → append | `run()` → `step()` → `execute_actions()` | Ball's shape (REPL-first) |
| Actions | native tool calling (School A) | bash-only text parsing (School B) | School A — we're here to learn the standard protocol |
| Runaway protection | none (tutorial) | step / cost / time limits | `MAX_STEPS = 20` (cost limit = free, we're on Ollama) |
| Tool errors | returned to the model as text | returned to the model as text | same — the model can read an error and adapt |
| Auto-approve | n/a | `-y` | `-y` flag, for scripted acceptance runs only |

## What we build

One file, `mvp/harness.py`, target < 300 lines. The six organs from [00-anatomy.md](00-anatomy.md) map to code directly:

1. **Provider client** — `call_model()`: one `requests.post`, provider picked from the labs/02 dict (`ollama` default, `gemini` by argv).
2. **Message list** — `messages`, born with one system prompt, grows forever (Stage 1 does nothing about that — that's the point of measuring it).
3. **Tool registry** — 4 functions + 4 JSON-schema adverts + a `REGISTRY` dispatch dict: `read_file`, `write_file`, `list_dir`, `run_shell`. No more. Resist.
4. **The loop** — `agent_turn()`: call → append reply → if `tool_calls`, execute + append results → repeat. Bounded by `MAX_STEPS`.
5. **System prompt** — a short f-string: identity, cwd, "run Python with `uv run python`", keep answers short.
6. **UI/REPL** — `input("you> ")`, plus the **permission gate**: y/N confirmation before `write_file` and `run_shell` (reads auto-approved).

Plus the non-negotiable **token meter**: after every API call, print per-call and session-running `prompt_tokens` / `completion_tokens`. Watching `prompt_tokens` climb per call is Pain #1 measured live.

## Decisions & deviations

- **No streaming** (deviation from ROADMAP 1.1's original wording): SSE parsing + delta-assembled tool calls roughly triples the parsing code and teaches nothing about the loop. Deferred to Stage 2.9; ROADMAP updated.
- **Tool output truncated at 2,000 chars** — a 3B model on Ollama has a small default context window; also plants the seed for Stage 3.1's dump-to-file (truncation is the bad version we'll replace).
- **`shell=True` on Windows** (cmd.exe), 60 s timeout so one hung command can't wedge a turn.
- **We check `msg.tool_calls` presence, not `finish_reason == "tool_calls"`** — some Ollama models report `stop` while still carrying tool calls; presence is the robust signal (dialects again).
- **No `temperature` override + `max_tokens: 2000`** (learned the hard way during acceptance): qwen3 with `temperature: 0` (greedy decoding) spirals into infinite repetition while thinking — measured as back-to-back 300s/600s timeouts. Each model ships a tuned sampling default; trust it. And `max_tokens` is the second runaway guard: `MAX_STEPS` bounds the *loop*, `max_tokens` bounds a *single generation* (overruns surface as `finish_reason: "length"`, which the loop already handles).
- **Ollama `usage` dialect:** `prompt_tokens` counts only non-KV-cached tokens, so it can *drop* between calls (measured 443 → 180). The session meter is therefore "tokens actually processed", not "context size" — fine for Stage 1, worth remembering for Stage 2.5's budget math.

## How we know it works

[`mvp/ACCEPTANCE.md`](../../mvp/ACCEPTANCE.md): three tasks (fizzbuzz create+run, dependency read, planted-bug fix with test proof), each with the exact command and pass signal, plus a results log per model. Exit criteria: all three pass on some model (local preferred, Gemini allowed), token meter visible, every line explainable.
