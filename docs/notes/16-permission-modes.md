# Note 16 — Stage 2.10: permission modes (the wish-4 ladder)

> Written 2026-07-07, before implementing. Sources studied: [Claude Code's six permission modes](https://code.claude.com/docs/en/permission-modes) (the acceptEdits scoping rule, the Shift+Tab cycle), [Codex approval_policy × sandbox_mode](https://developers.openai.com/codex/agent-approvals-security) (read-only / workspace-write / full), [opencode permissions](https://opencode.ai/docs/permissions/) (per-agent profiles). Full audit: ROADMAP2 §2.

## What the seniors do

Every harness grew from *one* permission table to *switchable profiles over* the table. Claude Code cycles six modes with Shift+Tab (`default` ask-everything → `acceptEdits` → `plan` read-only…); Codex picks one of three sandbox rungs; opencode attaches a profile per agent. Two design details worth copying exactly:

1. **The scoping rule** (Claude Code `acceptEdits`): auto-approval of writes applies **only inside the working directory** — a path outside cwd still prompts, in every mode. Auto never means "anywhere".
2. **Deny survives every mode** (all three seniors): a mode changes *defaults*, never the absolute deny list. Claude Code's `bypassPermissions` is the lone exception — and the one mode we refuse to build.

What we *don't* copy: Claude Code's new `auto` runs a second classifier model per action — wrong size for one user on a 4 GB card (ROADMAP2 §6). Our `auto` stays dumb: scoped auto-approve + absolute deny.

## What we build

- **A mode = a named `Policy` + one flag** (`tools = true|false`). `core/permissions.py` gains `Mode`, `load_modes(path)`, and `ModeSet` (the loaded profiles + which is active; `switch(name)` validates). The existing `Policy` and its fail-closed tie-break (note 10) are untouched — a mode is just *which table is active*.
- **`build` = the existing `[permissions]` table.** One fact, one home: no duplicate table. New `[modes.chat]`, `[modes.explore]`, `[modes.auto]` sections in `harness.toml`:

| Mode | Table | Meaning |
|---|---|---|
| `chat` | `tools = false` | tools array not even sent — pure conversation ("ask only, like the websites") |
| `explore` | `default = "deny"`, reads + `todo_write` allowed | can see, can't touch ("ask but can see my computer") |
| `build` | the `[permissions]` table | today's behavior — reads allowed, mutators ask |
| `auto` | reads + `write_file`/`edit_file` allowed, shell/spawn ask | "coding" — writes auto-approved **inside cwd only** |

- **The scoping rule**, as one general law in `Policy.decide_call(name, args)`: an `allow` verdict for `write_file`/`edit_file` holds only if the target path resolves inside cwd; outside, it degrades to `ask`. Applies in every mode (in `build` it's invisible — writes ask anyway), fail-closed like everything else in this file.
- **CLI**: `--mode <name>` at launch, `/mode` builtin at runtime (bare → show current + available; with name → switch). The gate consults `modeset.policy` *per call*, so a switch takes effect mid-session. `chat` swaps the agent's schemas to `[]`; leaving it swaps them back.
- Missing `harness.toml` → only `build` exists with the note-10 safe default (everything asks). Unknown `--mode`/`/mode` → error naming the available modes. `-y` still upgrades ask only — deny is deny in every mode.

Subagents inherit the *current* mode automatically: they share the same gate.

## How we know it works

- **pytest** (`tests/test_permissions.py`): `load_modes` parses all four (build from `[permissions]`); missing file → build only; `ModeSet.switch` rejects unknown names; `decide_call` — write allowed inside cwd stays allow, `../escape.txt` and absolute-outside degrade to ask, deny still beats everything; explore's default-deny denies `write_file` even with `-y` semantics.
- **acceptance** (new task H, runs in `explore`): "create a file" → the write comes back *permission-denied as tool-result text*, the agent reports it can't (instead of crashing), and the file provably does not exist on disk.
