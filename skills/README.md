# skills — the harness's model-invoked procedure library

> **Audience note (note 15):** this folder is read by the **harness's own agents at runtime**, not by Claude Code. It's a feature of the harness — the runtime sibling of `commands/` (user-invoked) and `agents/` (roles). The coding-agent equivalent lives in `.claude/skills/`.

A skill is a directory with a `SKILL.md` ([the open standard](https://agentskills.io/specification)): frontmatter `name` + `description`, body = the procedure. At startup only the **name + description line** enters the system prompt; the model reads the full body with `read_file` when a task matches — progressive disclosure via `src/harness/core/skills.py` (note 20).

| Skill | Triggers on |
|---|---|
| `run-tests/` | being asked to test, verify, or check the harness |

**Adding one:** make `skills/<name>/SKILL.md` with a `description:` that says what it does **and when to use it** — that line is the only trigger the model gets. If the body holds a rule the model can't guess, say so in the description ("the format is exact — read this skill first"): measured on the 4B workhorse, a description that *invites guessing* gets guessed (note 20). No description → not advertised. Restart (or `/agent`) to re-assemble the prompt. Stage 3.2 will grow this library from `archive/prompt/`.
