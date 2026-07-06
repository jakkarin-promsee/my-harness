# Note 17 — Stage 2.11: agents (the roles registry)

> Written 2026-07-07, before implementing. Sources studied: [opencode agents](https://opencode.ai/docs/agents/) (one md file = prompt + model + permissions; primary agents Tab-switch; same registry serves subagents; `tools` frontmatter deprecated in favor of permissions), [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) (YAML frontmatter: `name`/`description`/`tools`/`model`; body = system prompt) and its plan-approval flow (plan ends by offering the switch into an executing mode), [aider's architect/editor split](https://aider.chat/2024/09/26/architect.html) (strong model proposes, cheap model edits — per-role model assignment as the cheap intelligence hack). Full audit: ROADMAP2 §2–3.

## What the seniors do

All three converged on the same shape: **a role is a markdown file** — frontmatter carries the knobs, the body is the system prompt. opencode goes furthest (its agents *are* its modes); Claude Code keeps roles as subagents; aider proves the economics (per-role models beat one-model-fits-all on benchmarks). Claude Code's plan mode adds the handoff detail: a finished plan *offers the switch* to an executing mode rather than dead-ending.

## What we build

- **`core/agents.py`** — `AgentSpec` (name, description, model, mode, think, prompt) + `discover("agents")`: parse `agents/*.md` at cwd (runtime dir, sibling of `commands/` — the 2.7 pattern). Frontmatter is hand-parsed `key: value` lines between `---` fences (no yaml dependency; comments and blanks ignored; no frontmatter → whole file is the prompt). `think` is parsed now, applied in 2.12.
- **`build` is a code-level built-in, not a file**: its body already lives in `prompts/system.md` (one fact, one home). Three roles ship as files: `agents/plan.md` (mode `explore`; investigate, propose, never edit; *ends by offering `/agent build`* — the light plan-approval flow), `agents/chill.md` (mode `chat`; no tools, warm conversation — the "chill guy", verbatim), `agents/reviewer.md` (mode `explore`; adversarial read — the red-team seed).
- **Assembly**: agent body goes through the same pipeline as 2.4 — env block + `AGENTS.md` appended. `context.build_system_prompt` gains a `template=` parameter and swaps `.format()` for `.replace("{env_block}", …)` so arbitrary braces in agent prompts can't crash it.
- **REPL**: `--agent <name>` at launch; `/agent` bare → list, `/agent <name>` → switch. A switch replaces the system message, applies the agent's default `mode` (orthogonality: `/mode` still works afterwards — the agent only sets the *default*), rebuilds the model if the agent pins a different provider, and **continues in a new session file** (the `/compact` precedent: in-memory history carries over; the on-disk transcript stays append-only and replayable).
- **`spawn_subagent` gains `agent=`** (opencode's registry unification): a named role gives the *fresh* child that agent's system prompt. Fork keeps the parent's history untouched (a forked child inherits the parent's identity by definition). Children keep the session model and the parent's gate — per-role models apply to the *primary* agent in 2.11; wiring child models is noted as a non-goal until something needs it.
- **Budget rule holds**: shipped built-ins leave `model:` unset (session provider). Pinning `plan` to gemini is one uncommented line in `agents/plan.md` — the owner's call, not a default that silently burns credit on every local run.

## How we know it works

- **pytest** (`tests/test_agents.py` + additions): frontmatter parsing (all four keys, comments, missing frontmatter, missing dir → `{}`); `build_system_prompt(template=…)` appends env + AGENTS.md and survives braces; FakeModel spawn with `agent=` → child's system message is the role's prompt; unknown `agent=` → ERROR text, not a crash.
- **acceptance** (new task I, runs as agent `plan` on the live model): ask for a code change → zero writes hit disk (explore mode + prompt), and the final answer contains the `/agent build` handoff its prompt mandates.
