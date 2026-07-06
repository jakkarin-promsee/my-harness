# commands — the harness's slash-command library

> **Audience note (note 15):** this folder is read by the **harness's own agents at runtime**, not by Claude Code. It's a feature of the harness, not developer context. Don't confuse it with `.claude/skills/`, which is the coding-agent equivalent.

A slash command is just a markdown file. At runtime, `/name args` reads `commands/name.md`, substitutes `{{args}}` (or appends the args if there's no placeholder), and the result becomes the user message. No plugin API — the prompt library *is* a folder (`src/harness/core/commands.py`, note 09).

| File | Command |
|---|---|
| `explain.md` | `/explain …` |
| `note.md` | `/note …` |
| `test.md` | `/test …` |

**Adding one:** drop a `name.md` here and it's live immediately. Put `{{args}}` where the user's text should land. Stage 3.2 builds the intake-interview middleware on top of exactly this mechanism.
