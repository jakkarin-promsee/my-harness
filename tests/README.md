# tests — the loop's contract, for zero tokens

The offline pytest suite. It proves the harness behaves correctly **without a model**: a `FakeModel` returns scripted replies, so the loop runs deterministically for zero tokens. This is working rule 5 made executable — *the harness must be boring.*

Run: `uv run pytest -q` (sub-second). Keep it green before and after every change.

## How it works

`fakes.py` is a stand-in `Model`: hand it a list of replies and it returns them one per `complete()` call, in the exact shape a real adapter produces. The loop can't tell it from Ollama — that's the payoff of the injected design (`src/harness/core/loop.py`).

## The files (one per unit)

| File | Covers |
|---|---|
| `fakes.py` | the `FakeModel` + helpers (not a test) |
| `test_loop.py` | the loop's contract: tool chaining, appends, empty/length nudges, runaway guard |
| `test_tools.py` | the 7 basic file/shell tools |
| `test_todo.py` | todo replace-semantics + status validation |
| `test_subagent.py` | fresh vs fork, child-tools-minus-spawn, only-final-text-returns |
| `test_openai_compat.py` / `test_streaming.py` | the OpenAI adapter + SSE deltas; think→reasoning_effort (2.12) |
| `test_ollama_native.py` | the native /api/chat dialect: both directions, think mapping, NDJSON streams (2.12) |
| `test_anthropic.py` | the six-way translation round-trip; think→budgets (2.12) |
| `test_permissions.py` | allow/ask/deny + deny > ask > allow; modes + the cwd scoping rule (2.10) |
| `test_agents.py` | role frontmatter parsing + discovery (2.11) |
| `test_session.py` | JSONL append / load / resume |
| `test_context.py` | system-prompt assembly |
| `test_budget.py` | token estimate + `/compact` |

**Adding a test:** mirror the module name (`test_<module>.py`), script a `FakeModel` for whatever loop path you need, and assert on what happens to `messages`. No network, ever. The live end-to-end checks live in `acceptance/`, not here.
