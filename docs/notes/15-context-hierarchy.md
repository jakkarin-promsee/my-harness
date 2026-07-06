# Note 15 — the context hierarchy: one fact, one home

> Written 2026-07-07, right after the src/ layout landed (note 14). Sources studied: how Claude Code loads `CLAUDE.md` (root always in context; a nested one pulled in when you touch that subtree), the cross-tool `AGENTS.md` convention, and how mature repos split `README.md` (human-facing, on-demand) from agent-instruction files. No single external reference for the exact split — it's designed around this repo's unusual property: **two audiences.**

## What was the problem

After Stage 2 all project context lived in one place: a single root `CLAUDE.md` carrying identity, status, the stack table, the repo map, the constitution, and hard-won model lessons — and it grew every stage. Two failure modes were coming:

- **Cost.** An agent doing focused work (say, editing one provider) pays for the entire `CLAUDE.md` every turn. That is the exact context waste this whole project exists to fight (Pain 1). Practising what we preach means context should load by locality, not all-at-once.
- **Drift.** When there is one big file, it becomes the place every new fact gets dumped — and dumped facts fall out of sync with the code they describe.

Meanwhile the *real* content already existed and was good: `docs/notes/` hold the **why**, and the module docstrings hold the **how** (`loop.py`'s docstring is a spec, `base.py` explains the adapter seam). The gap was never content. It was **navigation** — nothing told an agent "to work on X, read Y."

## The two audiences (the wall we must not cross)

This repo is both a codebase *and* an agent harness, so "context" means two different things:

- **Coding agents** — Claude Code and its subagents, working *on* the harness. They read `CLAUDE.md`, the skills, and the folder READMEs.
- **The harness's own agents** — at runtime, working on whatever repo they're pointed at. `core/context.py` assembles their context from exactly three sources: `prompts/system.md`, an env block, and `AGENTS.md` from the cwd. It **never** reads nested READMEs or `CLAUDE.md`.

Confirmed in `context.py`: docs we add for coding agents are invisible to the harness runtime. So `AGENTS.md`, `commands/`, and `prompts/system.md` belong to the harness — keep them out of the dev-facing hierarchy, and don't repurpose them for dev notes.

## What we built — five layers, each owning one kind of fact

| Layer | File(s) | Loads when | Owns (the one thing) |
|---|---|---|---|
| 1 Project map | `CLAUDE.md` (root) | always | map · status · constitution · router |
| 2 Code map | `src/harness/CLAUDE.md` | auto, editing under `src/` | architecture-in-brief · invariants · commands |
| 3 Folder docs | `*/README.md` | on demand (agent opens it / GitHub) | what's in THIS folder, now |
| 4 Skills | `.claude/skills/<name>/SKILL.md` | name always, body on invoke | how to DO a recurring task |
| 5 Design notes | `docs/notes/NN-*.md` | on demand | the WHY + history (already written) |

The rule that keeps it from rotting: **one fact, one home.**

> notes = *why* · README = *what-now* · skill = *how-to-task* · docstring = *how-it-works* · CLAUDE.md = *map + rules*

A README that re-explains the loop is a bug — it links to `loop.py`'s docstring instead. And (owner's rule, 2026-07-07) **`CLAUDE.md` is a map, not a container**: it appears only at file/context-dense positions (root, `src/harness/`) and holds pointers, never data.

## How we know it works

- **No duplication:** each fact has one home (spot-check — the six-way Anthropic table lives only in note 03; `providers/README.md` links to it, never copies it).
- **Routable:** an agent handed only the root `CLAUDE.md` can reach any work area from the map alone.
- **Inert to the runtime:** the harness's own suites stay green because nested docs aren't read by `context.py`. `uv run pytest -q` → 79 passed; no code changed by this note's work.
