# Note 08 — Stage 2.6: subagents (spawn with fresh | fork)

> Written 2026-07-06, before implementing. Sources studied: Claude Code's Agent tool (fresh context, summary returned, results not auto-trusted), opencode subsessions, the fork-vs-fresh analysis in `harness-context-v3.md` §C (the Stage 3.5 spec source).

## What the seniors do

A subagent is just *another loop over another messages list* — the parent sees only a summary message. What differs is inheritance: Claude Code's Task agents start **fresh** (clean slate, only the prompt — outside view, catches blind spots); a **fork** copies the parent's context (inside view, consistency checks). v3 §C's insight: these are different epistemic tools, so both modes must exist as first-class options.

## What we build

- `core/subagent.py` — `make_spawn_tool(...)` factory returning `(spawn_fn, schema)`:
  - `spawn_subagent(prompt, context="fresh")` — fresh: `[system] + prompt`; fork: **deep copy** of the parent's live message list + prompt (deep because the child must never mutate parent history).
  - The child is a normal `Agent` with the same model/gate/usage-meter but `max_steps=10` and — deliberately — **no spawn tool in its registry** (no recursive spawning at Stage 2).
  - Return value to the parent = the child's final assistant text (that string becomes the tool result — the parent's context receives the summary, not the child's transcript. Stage 3.4 upgrades this to structured findings).
  - Child output is emitted with a `[sub]` prefix so the human can follow.
- Simplifications (documented, deliberate): child transcript not persisted to its own session file; parent's y/N gate applies to the child's mutating tools too.

## How we know it works

pytest with two FakeModels (parent scripted to spawn, child scripted to answer): fresh child sees exactly 2 messages (no parent leakage); fork child sees the parent history *and* parent history is unchanged afterwards; child registry lacks spawn_subagent; the child's final text lands verbatim as the parent's tool result.
