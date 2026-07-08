# agents — the harness's role library (runtime, not dev context)

Each `*.md` here is a **role** the harness's own agent can wear: frontmatter
(`description`, `mode`, `model`, `think`, `backbone`, `tier`, `voice`,
`world`) + body = the role's specialization. Since 2.18a a role **extends the
backbone** (`src/harness/prompts/system.md`) instead of replacing it; since
2.30 the backbone is split by **world** (note 39): `core` sections (identity,
safety, style) ride every role, and `world: operator` (default) or
`world: companion` picks the job wrapper — the working loop and tool policy,
or the conversational register. `backbone: false` remains the full opt-out for
exotic roles. Switch with `/agent <name>` (or the one-word `/chat` · `/work`)
or launch with `--agent <name>`; `spawn_subagent` can give a fresh child a
role via `agent=`. Read from the cwd at runtime — same pattern as `commands/`.
Design: `docs/notes/17-agents.md` + `23-backbone.md` + `39-two-worlds.md`;
parser: `src/harness/core/agents.py`.

| Role | Mode | World | What it is |
|---|---|---|---|
| `build` | build | operator | *(built-in, no file)* the working agent, the default (`/work`) |
| `plan` | explore | operator | investigate & propose, never edit; ends by offering `/agent build` |
| `chill` | chat | **companion** | no tools — a warm conversation partner that keeps the core character (`/chat`) |
| `reviewer` | explore | operator | adversarial read-only review; reports, never fixes |

Add a role: drop a `name.md` here. `model:` pins a provider (`ollama`/`gemini`)
— shipped files leave it unset so nothing silently burns credit; `mode:` names
a `harness.toml` profile and only sets the *default* (`/mode` still switches);
`world:` defaults to operator and a typo fails loudly at assembly.
