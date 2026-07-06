---
name: run-tests
description: Run and interpret the researcher-harness test suites. Use to verify a change, to check before/after a feature, or to decide whether to spend budget on the live acceptance gate.
---

# Run the tests

Two suites, two purposes.

## Offline — always, after every change

```
uv run pytest -q
```

- Zero tokens. Tests the loop's **contract** via a `FakeModel` (`tests/README.md`).
- Sub-second. If it's red, stop and fix before anything else (rule 5).

## Live — the Stage-2 exit gate, spends real budget

```
uv run python acceptance/run.py ollama     # local, free — use this first
uv run python acceptance/run.py gemini     # ~$ credit — quality check
```

- 7 tasks (A–G) against a real model; verifiers check reality (files, exit codes). See `acceptance/README.md`.
- **Budget rule:** debug on `ollama` (a bug burns $0), validate quality on `gemini`. Never point a possibly-buggy loop at a paid endpoint.
- `anthropic` stays untested until `ANTHROPIC_API_KEY` is set deliberately (`docs/problem.md`).

## Reading results

- **pytest:** a plain pass/fail count.
- **acceptance:** `PASS/FAIL <task>` per task, then a token meter (`N in / M out`). 7/7 = gate green.
