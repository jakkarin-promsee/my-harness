# MVP Acceptance Suite

Three tasks, run from the **repo root**. Stage 1 exits only when all three pass on
some model (local preferred; Gemini allowed when the local model is too weak),
the token meter prints on every call, and every line of `harness.py` is explainable.

Budget rule applies: prove the loop is non-buggy on Ollama **before** any Gemini run.

## How to run

Interactive: `uv run python mvp/harness.py` and type the task text.
Scripted (what the results below used): pipe the task + `exit` in, with `-y`
auto-approving the gate — in PowerShell:

```powershell
@("<task text>", "exit") | uv run python mvp/harness.py -y
```

Model select: `$env:OLLAMA_MODEL = 'qwen3:4b'` (default `llama3.2:3b`), or `gemini` as argv.

## Task A — create and run

> Create fizzbuzz.py that prints fizzbuzz from 1 to 15, then run it and show me the output.

**Pass:** file exists after the run; agent's final answer contains the real program
output (1, 2, Fizz, 4, Buzz, ... FizzBuzz). Cleanup: delete `fizzbuzz.py` after.

## Task B — read and report

> Read pyproject.toml and tell me what dependencies this project has.

**Pass:** final answer names requests, python-dotenv, truststore (no gate prompt
should appear — reads are auto-approved).

## Task C — find the planted bug, fix it, prove it

> The test mvp/fixtures/test_stats.py is failing. Find the bug in mvp/fixtures/stats.py, fix it, and prove the fix by running the test.

**Pass:** agent runs the test (sees FAIL), fixes `mean` (the `+ 1` in the divisor),
re-runs the test, final answer reports all PASS. Reset the planted bug afterwards:
`git checkout -- mvp/fixtures/stats.py`.

## Results log

| Date | Model | A | B | C | Notes |
|---|---|---|---|---|---|
| 2026-07-06 | llama3.2:3b | — | FAIL | — | Ignores "read the file": ran global `pip freeze`, then fabricated a poetry config. Tool-calls fine mechanically; too weak to trust. |
| 2026-07-06 | qwen3:4b | FAIL | PASS | — | B clean (read_file → exact 3 deps). A: burned the whole 2,000-token budget *thinking*, never reached the tool call (GPU 33% CPU-offloaded next to a game). Guard caught it as `length`. |
| 2026-07-06 | gemini-2.5-flash-lite | PASS | PASS | PASS | A: full write→run→report, correct output; survived two 503s via the retry. B: read_file → exact 3 deps, 35 tokens out. C: read → fixed `mean` → test exit 0 (independently re-verified). One quirk seen: an occasional fully-empty reply (0 tokens) after a tool result — rerun clears it. |

> **Since Stage 2:** this suite grew into the scripted exit gate at `acceptance/run.py`
> (7 tasks incl. grep/edit/glob/subagent, one command per provider). 2026-07-06:
> **7/7 PASS on gemini-2.5-flash-lite** (empty-reply nudge + 5xx retry both fired
> mid-suite and saved their tasks); **5/7 on local qwen3:4b** (fails A + G;
> 13.6k thinking-heavy output tokens vs Gemini's 0.75k). docs/problem.md #1.
