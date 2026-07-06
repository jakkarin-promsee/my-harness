# agents — the harness's role library (runtime, not dev context)

Each `*.md` here is a **role** the harness's own agent can wear: frontmatter
(`description`, `mode`, `model`, `think`) + body = system prompt. Switch with
`/agent <name>` or launch with `--agent <name>`; `spawn_subagent` can give a
fresh child a role via `agent=`. Read from the cwd at runtime — same pattern
as `commands/`. Design: `docs/notes/17-agents.md`; parser: `src/harness/core/agents.py`.

| Role | Mode | What it is |
|---|---|---|
| `build` | build | *(built-in, no file — its body is `src/harness/prompts/system.md`)* today's working agent, the default |
| `plan` | explore | investigate & propose, never edit; ends by offering `/agent build` |
| `chill` | chat | no tools at all — a conversation partner |
| `reviewer` | explore | adversarial read-only review; reports, never fixes |

Add a role: drop a `name.md` here. `model:` pins a provider (`ollama`/`gemini`)
— shipped files leave it unset so nothing silently burns credit; `mode:` names
a `harness.toml` profile and only sets the *default* (`/mode` still switches).
