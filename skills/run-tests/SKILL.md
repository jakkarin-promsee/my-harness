---
name: run-tests
description: How to run this project's test suites and read the results. Use when asked to test, verify, or check the harness after a change.
---

# Running the researcher-harness test suites

1. Always start with the offline suite — it is sub-second and costs zero tokens:

       uv run pytest -q

   All tests passing prints only dots and a count. Any `F` or error output means
   the change broke the loop's contract — read `tests/README.md` before touching
   anything else.

2. Only if asked to prove the FULL stack against a live model, run the
   acceptance gate — it spends real tokens, so prefer the free local provider:

       uv run python acceptance/run.py ollama

   Details and the budget rule are in `acceptance/README.md`. Never run the
   `gemini` provider unless the request explicitly says so (it spends credit).

3. Report the counts exactly as printed (e.g. "129 passed", "10/10 passed"),
   never a paraphrase.
