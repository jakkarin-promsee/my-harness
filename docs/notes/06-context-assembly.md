# Note 06 — Stage 2.4: system prompt & context assembly

> Written 2026-07-06, before implementing. Sources studied: how Claude Code assembles its first message (identity prompt + env block + CLAUDE.md injection), opencode's provider-specific system prompts + AGENTS.md convention, aider's repo-map-in-prompt.

## What the seniors do

The first message is never one hardcoded string; it's **assembled** from layers:

1. **Identity & rules** — a maintained prompt file (Claude Code: thousands of tokens of behavior-shaping; the single highest-leverage text in the product).
2. **Environment block** — machine facts (OS, cwd, date, git state) injected at session start so the model never wastes a tool call asking.
3. **Project memory** — a file the *user* owns, read from the working directory (CLAUDE.md / AGENTS.md / .cursorrules — same idea everywhere). The emerging cross-tool convention is `AGENTS.md`; we adopt it.

## What we build

- `harness/prompts/system.md` — the identity/rules template with `{placeholders}`. Editing behavior = editing a text file, no code change.
- `core/context.py` — `build_system_prompt(cwd)`: renders the template with an env block (OS, cwd, date, git branch if any) and appends `AGENTS.md` content when the file exists (with a header saying where it came from).
- REPL uses it; the hardcoded SYSTEM_PROMPT constant dies. An `AGENTS.md` for this repo itself (dogfooding: our harness working in this repo reads it).

## How we know it works

pytest with tmp dirs: placeholder substitution, AGENTS.md included when present / silently absent when not, env block contains cwd + today's date. Template file resolved relative to the package (works from any cwd).
