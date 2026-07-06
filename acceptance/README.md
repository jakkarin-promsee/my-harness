# acceptance — the Stage-2 exit gate

The live-model suite: the full stack against a real model, in one command. Where `tests/` proves the *contract* offline, this proves the *whole thing works* end to end — **both must be green to leave Stage 2.**

```
uv run python acceptance/run.py ollama     # local, free — run this first
uv run python acceptance/run.py gemini     # spends Gemini credit — quality check
```

## What it does

`run.py` gives each task a **fresh** Agent + messages list (no REPL, no stdin), runs it against the chosen provider, then a **verifier checks reality** — files on disk, test exit codes — not the model's words. Auto-approve is on, but `harness.toml` still applies (deny stays deny). Fixtures are restored even on failure. It prints `PASS/FAIL` per task and a token meter.

## The seven tasks

`A` create-and-run · `B` read-and-report · `C` find-fix-prove (the on-purpose bug in `archive/mvp/fixtures/stats.py`) · `D` grep · `E` exact-edit · `F` glob · `G` subagent. **7/7 = gate green.**

**Budget rule:** debug on `ollama` (a runaway loop costs $0), validate quality on `gemini`. `anthropic` stays untested until `ANTHROPIC_API_KEY` is set deliberately (`docs/problem.md`). Run logs land at `acceptance-*.log` (gitignored).
