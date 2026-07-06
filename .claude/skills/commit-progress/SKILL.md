---
name: commit-progress
description: Commit the current working-tree progress in the researcher-harness commit style — verify tests, review every change, group by concern, write a `type: summary — detail` message. Use at the end of a work session or when a coherent chunk of work is ready to be recorded.
---

# Commit progress — the end-of-session ritual

Turn the working tree into clean history. Written to be followable by any model:
when in doubt at any step, stop and ask the owner instead of guessing.

## 1. Prove green first

`uv run pytest -q` — must pass (rule 5). Never commit red. Docs-only change?
Run it anyway; it's sub-second and catches accidental code edits.

## 2. Read what you're committing

- `git status` then `git diff` (and `git diff --stat` for the shape). Read every
  hunk — never commit blind, never `git add -A` without having read the status list.
- **Must not enter history:** `.env` (keys), `sessions/`, `acceptance-*.log`,
  scratch files. If something like that shows up, it belongs in `.gitignore`, not the commit.
- If a file was added/removed in a folder with a `README.md`, that README must
  already reflect it (note 15). If not, fix it now — same commit.

## 3. Group by concern

One commit = one concern (mirrors rule 2: one feature at a time). Unrelated
changes in the tree → stage and commit them separately (`git add <paths>`, never all-at-once).

## 4. Write the message like the log

Match the precedent — check `git log --oneline -5`. The house format:

```
type: short summary — key detail or evidence
```

- `type` ∈ feat / fix / docs / refactor / test / chore.
- Evidence beats adjectives: "7/7 on both providers" not "works great".
- Non-trivial change → a short body telling the story (what was the problem →
  what did we do → why), per doc conventions.

## 5. Boundaries

- Commit on the current branch; **never push** unless the owner asked.
- Never amend, rebase, or force — history here is append-only.
- A stage/milestone completion is **not** this skill's job — that bookkeeping
  (ROADMAP, status line, README, problem.md) is the **close-stage** skill; run it first, then commit.
