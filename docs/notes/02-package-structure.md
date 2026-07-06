# Note 02 — Stage 2.0: from single file to package (+ FakeModel tests)

> Written 2026-07-06, before implementing. Sources studied: mini-swe-agent's package layout (`agents/`, `models/`, `environments/`, `run/`), opencode (session/tool/provider separation), aider (`coders/` + `models.py`).

## What the seniors do

Every mature harness separates the same four concerns, whatever it names them:

| Concern | mini-swe-agent | opencode | ours |
|---|---|---|---|
| The loop | `agents/default.py` | `session/` | `src/harness/core/loop.py` |
| Talking to a provider | `models/` | `provider/` | `src/harness/providers/openai_compat.py` |
| Tools | `environments/` (bash only) | `tool/` | `src/harness/tools/basic.py` |
| Entry point / UI | `run/` | `cli/` | `src/harness/cli/repl.py` |

And the key testing idea, straight from mini-swe-agent's own test suite: **a deterministic fake model with scripted replies**. The loop never knows whether replies come from Gemini or from a list — so every loop behavior (tool dispatch, guards, denial, truncation) is testable in milliseconds for zero tokens.

## What we build

```
harness/
  core/loop.py        Agent class: run_turn(messages) — the while-loop, guards, dispatch
  providers/openai_compat.py
                      OpenAICompatModel: HTTP + 5xx retry + dialect normalization.
                      complete(messages, tools) -> {"message", "finish_reason", "usage"}
  tools/basic.py      the 4 tool functions + schemas + NEEDS_PERMISSION
  cli/repl.py         argv parsing, provider dict, y/N gate, token meter, REPL
  __main__.py         `uv run python -m harness [gemini] [-y]`
tests/
  test_loop.py        FakeModel-driven: the loop's full contract
  test_tools.py       the 4 tools against tmp_path
archive/mvp/harness.py        FROZEN — the Stage 1 artifact stays as the learning record
```

**The load-bearing design move:** the loop's only dependencies are *injected* — a `model` with `.complete()`, a tool `registry`, an `approve(name, args)` callable, an `on_usage` callback. The CLI injects the real HTTP model and the `input()` gate; tests inject `FakeModel` and lambdas. The loop cannot tell the difference. (This seam is also where Stage 2.1's provider adapter will plug in.)

**The loop's contract is what it does to `messages`** — tests assert on the list, not on stdout:
- text reply → appended, turn ends
- tool_calls reply → assistant msg appended, every call executed, one `role:"tool"` msg per call with echoed `tool_call_id`, loop continues
- `finish_reason: "length"` → turn ends immediately
- MAX_STEPS → hard stop; denial / unknown tool / bad-JSON args / oversized output → ERROR-or-denial text goes back to the model, never an exception

## How we know it works

1. `uv run pytest -q` green — zero tokens, sub-second.
2. Behavior-identical check: the Stage 1 acceptance tasks rerun through `python -m harness` — B on local qwen3:4b first (budget rule: never point restructured code at a paid endpoint before a local pass), then A/B/C on gemini-2.5-flash-lite.
