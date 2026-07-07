# acceptance — the stage exit gate (Stage 2 → 2R → 2C)

The live-model suite: the full stack against a real model, in one command. Where `tests/` proves the *contract* offline, this proves the *whole thing works* end to end — **both must be green to leave a stage.**

```
uv run python acceptance/run.py ollama                        # core 11, local, free
uv run python acceptance/run.py gemini                        # regression lane
uv run python acceptance/run.py gemini-flash --suite museum --n 3   # quality lane, majority-of-3
```

## What it does

`run.py` gives each task a **fresh** Agent + messages list (no REPL, no stdin), runs it against the chosen provider, then a **verifier checks reality** — files on disk, test exit codes — not the model's words. Auto-approve is on, but `harness.toml` still applies (deny stays deny). Fixtures are restored even on failure. It prints `PASS/FAIL` per run, a majority verdict per task, tokens (including Gemini's **hidden thinking**, derived as `total − prompt − completion` — note 22 probe (b)), wall-clock, and a $ estimate from `PRICES`.

Flags since 2.17 (docs/notes/22): `--suite core|museum|all` (per-provider asymmetry is explicit — local runs core, gemini lanes run everything), `--n N` (repetition; majority decides), `--task ID` (debugging), `--include-holdout` (**stage close only**).

## The files

| File | What it is |
|---|---|
| `run.py` | the runner + the core tasks |
| `museum.py` | the failure museum (2.17): real failed tasks from live sessions, one hold-out — see docs/notes/22 |
| `museum/` | frozen exhibits (e.g. the guidebook the live agent actually produced) |

## The tasks

**Core** (every ✅ = one shipped feature): `A` create-and-run · `B` read-and-report · `C` find-fix-prove (the on-purpose bug in `archive/mvp/fixtures/stats.py`) · `D` grep · `E` exact-edit · `F` glob · `G` subagent · `H` mode-explore (2.10: a write in read-only `explore` mode must come back permission-denied — a task can set `"mode"` to run under any profile) · `I` agent-plan (2.11: a task can set `"agent"` to run under any role; the plan role must offer the handoff) · `J` web-fetch (2.13: answer from a real page — needs internet) · `K` skill-trigger (2.14: a fixture skill's house format must be read and obeyed, never guessed).

**Museum** (2.17 — proves *judgment*, not features): `M1` page-eyes (simple; use web_fetch, don't deny having it) · `M2` orient-summary (summarize the project, don't report one fixture's planted bug) · `M3` guidebook (long multi-step; the guide must document real commands) · `M4` holdout-archaeology (**the hold-out** — untouched until stage close).

**Budget rule:** debug on `ollama` (a runaway loop costs $0), validate quality on the gemini lanes. `anthropic` stays untested until `ANTHROPIC_API_KEY` is set deliberately (`docs/problem.md`). Run logs land at `acceptance-*.log` (gitignored).
