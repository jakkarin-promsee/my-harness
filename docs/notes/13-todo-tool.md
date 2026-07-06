# Note 13 — Stage 2.9c: the todo tool (an external plan the model can't forget)

> Written 2026-07-07, before implementing. Sources studied: Claude Code's TodoWrite (the model sends the *complete* list every call — replace, not patch; statuses pending / in_progress / completed; exactly one item in_progress; the harness renders it as a visible checklist), OpenHands' plan events (same idea, event-sourced), and the "externalize the plan into context" lesson from Anthropic's context-engineering post.

## What the seniors do

Claude Code's todo list looks like UX garnish but is actually a *steering device*: writing the plan puts it into context where attention can find it every turn, and updating statuses forces the model to re-read its own plan mid-task. This disproportionately helps at the small end — a 4B model loses the plot fastest, and a checklist in context is the cheapest re-anchoring there is. The design choice that matters: **replace semantics**. The model resends the whole list each time; no add/remove/update micro-ops for a small model to fumble.

## What we build

- `tools/todo.py` — `make_todo_tool(emit)` factory returning `(fn, schema)`, closure state per agent:
  - `todo_write(todos: [{content, status: pending|in_progress|completed}])` — replaces the stored list.
  - Returns a one-line summary ("Todo list updated: 1 done, 1 in progress, 1 pending") followed by the rendered checklist — the model sees canonical state as the tool result, which is the whole point.
  - Renders to the human via the injected `emit`: `[x]` done, `[>]` in progress, `[ ]` pending.
  - Bad status values → ERROR text (model-fixable, loop philosophy), state untouched.
- Wired into the **top-level** agent only (REPL and acceptance runner). Subagents don't get it — they only see advertised schemas, so they won't call it; the system-prompt rule says "if available" for exactly this reason. (Claude Code eventually gave subagents their own lists; ours can too, in Stage 3 if wanted.)
- `harness.toml`: `todo_write` → allow (it mutates nothing outside the harness).
- `prompts/system.md` rule: for tasks with three or more steps, write the plan with todo_write first, keep statuses honest, one item in_progress at a time.

## How we know it works

pytest: replace semantics (second call clobbers the first list), render glyphs, invalid status becomes ERROR without corrupting state, emit shows the human the same checklist the model saw, schema/registry names agree. Live: watch a local multi-step task plan itself in the acceptance bake-off.
