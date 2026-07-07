# src/harness/core — the loop and its survival layers

The heart of the harness plus the bookkeeping that keeps it alive. Each module's **top docstring is its spec** — read that first; this README is the map, and `docs/notes/` holds the why.

| File | What it does | Why (note) |
|---|---|---|
| `loop.py` | **The agent loop.** One model call → run the tool calls → append results → repeat. Pure and injected (no HTTP, no I/O it wasn't handed). Handles the empty-reply and cut-off (`length`) nudges. | 00, 11 |
| `context.py` | Assembles the first (system) message: the **backbone** (six tagged sections in `prompts/system.md`; roles extend it, `backbone: false` opts out) + the active role's body + an env block + `AGENTS.md` from the cwd + the skills block. | 06, 07, 20, 23 |
| `permissions.py` | Three-state policy (allow / ask / deny) from `harness.toml` + named **modes** (chat / explore / build / auto) switchable at runtime. Fail-closed: deny > ask > allow; `-y` upgrades *ask* only, never deny; an allow on `write_file`/`edit_file` counts inside cwd only. | 10, 16 |
| `session.py` | One JSONL file per session, one line per message the moment it exists. Resume = replay the lines. | 05 |
| `budget.py` | Token estimate + the standard `/compact` (summarize-and-replace). Built as the baseline Stage 3.1's surgical ops must measurably beat. | ROADMAP 3.1 |
| `commands.py` | Slash commands = markdown files: `/name args` → `commands/name.md` with `{{args}}` substituted. | 09 |
| `agents.py` | Roles = markdown files: `agents/*.md` frontmatter (description/model/mode/think/backbone) + body = the role section appended to the backbone (2.18a). `build` is the code-level built-in. Also home of the shared `split_frontmatter`. | 17, 23 |
| `skills.py` | The MODEL's procedure library: `skills/*/SKILL.md` at the cwd → one name+description line each in the system prompt; the model reads a body on activation (progressive disclosure = `read_file`). | 20 |
| `subagent.py` | Spawn a child loop (`fresh` clean slate \| `fork` copy of parent). Only the child's **final text** returns to the parent — its transcript never enters the parent window. | 08 |

**Changing the loop?** It's the boring core — keep it pure and injected, and drive every path from `tests/test_loop.py` (zero tokens). The invariants you must not break are in [`../CLAUDE.md`](../CLAUDE.md).
