# agents — the harness's role library (runtime, not dev context)

Each `*.md` here is a **role** the harness's own agent can wear: frontmatter
(`description`, `mode`, `model`, `think`, `backbone`) + body = the role's
specialization. Since 2.18a a role **extends the backbone** (the six sections
in `src/harness/prompts/system.md`: identity, loop, tools, failure,
verification, style) instead of replacing it; `backbone: false` opts out, for
roles where an operator identity makes no sense. Switch with `/agent <name>`
or launch with `--agent <name>`; `spawn_subagent` can give a fresh child a
role via `agent=`. Read from the cwd at runtime — same pattern as `commands/`.
Design: `docs/notes/17-agents.md` + `23-backbone.md`; parser: `src/harness/core/agents.py`.

| Role | Mode | Backbone | What it is |
|---|---|---|---|
| `build` | build | *is* the backbone | *(built-in, no file)* today's working agent, the default |
| `plan` | explore | extends | investigate & propose, never edit; ends by offering `/agent build` |
| `chill` | chat | **opts out** | no tools at all — a conversation partner |
| `reviewer` | explore | extends | adversarial read-only review; reports, never fixes |

Add a role: drop a `name.md` here. `model:` pins a provider (`ollama`/`gemini`)
— shipped files leave it unset so nothing silently burns credit; `mode:` names
a `harness.toml` profile and only sets the *default* (`/mode` still switches).
