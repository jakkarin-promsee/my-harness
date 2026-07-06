# Note 09 — Stage 2.7: slash commands + prompt template library

> Written 2026-07-06, before implementing. Sources studied: Claude Code's `.claude/commands/*.md` (`$ARGUMENTS` substitution), opencode custom commands, the owner's real `archive/prompt/` library (the Pain-2 evidence — read-only).

## What the seniors do

Claude Code's design is beautifully dumb: a command is **a markdown file**; `/name args` = read `commands/name.md`, substitute the args token, send the result as the user message. No plugin API, no code — the prompt library IS a folder. That's exactly the mechanism the owner's `archive/prompt/` folder wants (today those templates are hand-edited per use — Pain 2).

## What we build

- `core/commands.py`:
  - `discover(dir="commands")` → `{name: path}` from `commands/*.md`.
  - `render(path, args)` → file text with `{{args}}` replaced (all occurrences; absent placeholder = args appended as a final line, so plain prompt files work unmodified).
  - `expand(user_input, commands)` → the rendered prompt, or `None` if not a template command.
- REPL: input starting `/` checks **builtins first** (`/tokens`, `/compact`, `/help` — new, lists everything), then template commands; the rendered text becomes the user message and runs through the normal agent turn.
- `commands/` starter library (committed): `explain.md` (explain code at a path), `test.md` (run tests + report), `note.md` (append a dated note to NOTES.md). Deliberately tiny — the real migration of `archive/prompt/` is Stage 3.2, where the interview/intake middleware gets built on top of this exact mechanism.

## How we know it works

pytest with tmp dirs: discovery finds `.md` files only; `{{args}}` substitution (multiple occurrences, empty args); files without the placeholder get args appended; non-command input returns None; unknown command distinguishable from known. REPL wiring exercised at the exit gate.
