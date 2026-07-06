---
name: implement-feature
description: Add or change a feature in the researcher-harness following the project constitution (design note → implement → tests → acceptance). Use for any non-trivial change to code under src/harness/.
---

# Implement a feature (the constitution's mini-cycle)

The working rules in the root `CLAUDE.md` are law. This skill is those rules, as steps.

## Before code

1. **One feature at a time.** If something else is in flight, stop (rule 2).
2. **Study 2–3 seniors** — mini-swe-agent, opencode, aider, Claude Code — for how they do this thing. Copy first, invent later; custom ideas wait for Stage 3 (rule 1).
3. **Write the design note** `docs/notes/NN-name.md` (next number): one page — what the seniors do → what we'll build → how we'll know it works. No note, no code (rule 6).

## Code

4. Implement under `src/harness/`. Match the surrounding style and comment density. **No line you can't explain** (rule 3).
5. Respect the invariants in `src/harness/CLAUDE.md`: the loop stays pure/injected; adapters translate both directions; tools return strings; errors become text, never crashes.
6. Add a **FakeModel** test in `tests/` (see `tests/README.md`) — the loop's contract, zero tokens.

## Prove it

7. `uv run pytest -q` — must stay green (rule 5).
8. Debug loop logic on **ollama** (a runaway loop costs $0); validate quality on **gemini**. Never point a possibly-buggy loop at a paid endpoint (the budget rule).
9. If the change touches the full stack, run the exit gate: `uv run python acceptance/run.py <provider>` (see `acceptance/README.md`).

## Finish

10. **Update the folder's `README.md`** if you added, removed, or renamed a file — the README is that folder's live map, and this step is how the hierarchy stays un-rotten (note 15).
11. Update the **status line** in the root `CLAUDE.md` if a stage milestone completed.
12. **Ask the owner** when a decision changes scope or direction (rule 7).
