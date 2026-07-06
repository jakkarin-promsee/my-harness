---
name: close-stage
description: Close a stage or numbered milestone (2.x, 3.x) in the researcher-harness — verify exit criteria, tick the ROADMAP, rewrite the status line, sweep problem.md, commit in the project's docs style. Use when exit criteria pass or a numbered feature ships.
---

# Close a stage / milestone — the bookkeeping ritual

The ritual that keeps a fresh session able to orient from one status line. It has run twice already (`docs: Stage 2 wrap`, `docs: Stage 2 CLOSED` in git log) — same shape every time.

## Steps

1. **Prove it first.** Run whatever the exit criteria in `docs/ROADMAP.md` demand — `uv run pytest -q` at minimum; the live gate on the required provider(s) if the stage says so. No green, no close.
2. **Tick the ROADMAP.** Check the boxes with date + evidence ("7/7 gemini, 1,083 out-tokens") in the same style as the Stage 0–2 entries.
3. **Rewrite the status line** in root `CLAUDE.md`. It is *the first thing a fresh session checks*: what shipped, the date, what's now unblocked. Keep the accumulated model lessons — they're load-bearing.
4. **Sweep `docs/problem.md`** — close what got resolved, add anything new that needs the owner.
5. **Refresh the root `README.md`** if the stage changed what the harness does or its numbers — its Status section hard-codes test counts and gate results and will otherwise silently lie to GitHub readers.
6. **Tell it as a story** (doc conventions): what was the problem → what did we do → why → what happened. Usually this lives in the design note's closing section and the commit message — not a separate report file.
7. **Commit** as `docs: Stage N CLOSED — <one-line evidence>` (match the precedent in `git log`).
