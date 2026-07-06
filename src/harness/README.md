# src/harness

The installable package — the harness itself. This README is the **architecture overview**; for the agent-facing map and the invariants see [`CLAUDE.md`](CLAUDE.md) in this directory, and for the *why* behind each piece see [`docs/notes/`](../../docs/notes).

## The shape

Everything is one loop around a chat API. A turn flows like this:

```
repl.py                      human types a request        (cli/)
  → Agent.run_turn(messages) the heart                    (core/loop.py)
      → model.complete(...)  one HTTP call, translated     (providers/)
      → run the tool_calls   each returns a string         (tools/)
      → append results, repeat
  → final text back to the human
```

The loop knows nothing concrete: the model, the tools, the permission gate, and the output callbacks are all **injected**. Swap the model for a `FakeModel` and the same loop runs offline for zero tokens — which is why the contract is testable (`tests/`).

## The packages

| Package | Role | Start at |
|---|---|---|
| `core/` | the loop + its survival layers (context, permissions, sessions, budget/compact, commands, subagents) | `core/README.md` |
| `providers/` | make each vendor look like one internal dialect | `providers/README.md`, note 03 |
| `tools/` | the model's hands: file/shell ops + a todo plan | `tools/README.md`, notes 04 & 13 |
| `cli/` | the REPL — the only human-facing code | `cli/repl.py` docstring |
| `prompts/` | `system.md`, the harness's own system prompt | note 06 |

## Run it

`uv run harness [ollama|gemini|anthropic] [-y] [--resume] [--sessions]` (or `uv run python -m harness ...`). Local Ollama is free; guard the Gemini credit; `anthropic` needs a key set deliberately (`docs/problem.md`).
