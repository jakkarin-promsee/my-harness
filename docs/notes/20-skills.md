# Note 20 — Stage 2.14: skills, the model's own procedure library

> Written 2026-07-07, before implementing. Sources studied: the [Agent Skills specification](https://agentskills.io/specification) (fetched live — constraints quoted below), [Anthropic: equipping agents for the real world](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), Claude Code's skill loading (observed: one line per skill at startup, full body on trigger). Full audit: ROADMAP2 §2.

## The distinction that earns this a feature

`commands/` (2.7) is the **human's** library — user-invoked, `{{args}}`-substituted. `skills/` is the **model's** library — model-invoked, description-triggered. Every 2026 harness ships both; the SKILL.md shape is an open standard adopted by 26+ tools. And it's the on-ramp to Stage 3.2: the owner's `archive/prompt/` templates want to become exactly this shape.

## What the spec says (the parts we keep)

- A skill = a **directory** with a `SKILL.md`: YAML frontmatter + markdown body; optional `scripts/`, `references/`, `assets/` alongside.
- Frontmatter: `name` (required, 1–64 chars, lowercase/digits/hyphens, **must match the directory name**) and `description` (required, 1–1024 chars, "what it does AND when to use it" — the trigger text). Optional fields we ignore: `license`, `compatibility`, `metadata`, `allowed-tools` (experimental).
- **Progressive disclosure**, three levels: metadata (~100 tokens) loads at startup for *all* skills; the body (< 5 K tokens recommended) loads **when the agent activates the skill**; bundled files load only as needed.

## What we build

The roadmap's whole insight: our architecture gets progressive disclosure nearly free, because "read the full skill when relevant" is just `read_file`. So:

- **`core/skills.py`** — mirrors `commands.py`/`agents.py`: `discover(directory="skills")` walks `skills/*/SKILL.md` at the cwd (runtime dir, sibling of `commands/` and `agents/`), takes the **directory name as the skill name** (same rule as command/agent file stems; the spec requires the frontmatter name to match anyway), reads `description` from frontmatter. A folder without `SKILL.md`, or a `SKILL.md` without a description, is skipped — the description IS the trigger; a skill without one is invisible by design, not an error. `skills_block(skills)` renders the injection: a header instructing "when a task matches, FIRST read the skill's file, then follow it", then one line per skill — `- name (skills/name/SKILL.md): description`.
- **Frontmatter parsing is shared, not copied**: `agents._split_frontmatter` is promoted to public `split_frontmatter(text, known_keys)` in `agents.py` (its docstring already reads like a spec); `skills.py` imports it with `{"name", "description"}`. One fact, one home. Flat `key: value` lines only — multiline YAML descriptions are a documented non-goal, same as agents.
- **`context.build_system_prompt` appends the block** after the AGENTS.md section when `skills/` exists at the cwd — the 2.4 pipeline, so every role and every subagent sees the same library automatically. No skills dir → nothing appended (the AGENTS.md pattern).
- **No new tools, no execution machinery, no allowed-tools**: activation is the model calling `read_file` on a path it was told about. The permission table already governs everything that follows.
- Ships with `skills/README.md` (the folder map, runtime-audience note like `commands/README.md`) and one real skill, `run-tests` — pointer-style (read `tests/README.md` / `acceptance/README.md`, pytest first, budget rule) so the procedure keeps its one home.

## How we know it works

- **pytest** (offline): `tests/test_skills.py` — discovery (name from dir, description from frontmatter), skip rules (no SKILL.md / no description / a stray file at top level), `skills_block` rendering, empty-dir → `""`; plus `test_context.py` grows: a tmp cwd with a skill → block present, without → absent.
- **live**: acceptance task **K-skill-trigger** — setup drops a fixture skill `stamp-files` ("stamp files have a required house format...") whose body mandates an unguessable format (first line `STAMP v2`, content uppercased); the prompt asks for a stamp file *without naming the skill or its path*. Verifier checks the file on disk matches the house format — provable only if the model noticed the skill from its description line, read it, and obeyed. Cleanup removes the fixture. Gate on ollama first, then gemini.

## What happened (2026-07-07, after implementing): the trigger war

The loader worked first try; making a 4B model *obey* it took an evening of ablation. The record, because this is the ACI lesson of the feature:

| Variant (cumulative unless noted) | K on qwen3:4b-instruct |
|---|---|
| v1 — polite header before the list ("when a task matches, FIRST read…") | **FAIL**: the model narrated *"this follows the stamp file format rules"* — it saw the line, guessed the format, never read the file |
| v2 — "you MUST call read_file" header before the list | 1/2 — coin flip |
| v3 — imperative moved AFTER the list (recency hypothesis) + "stamp file" in the prompt | **0/3 — worse** (hypothesis falsified) |
| v4 — rule added to `prompts/system.md`'s Rules section (where the todo rule already works, note 13) | 1/2 with the old description — the rule alone is not enough |
| v4 + description says *"the format is exact and cannot be guessed — read this skill first"* | **5/5** |

Two findings worth keeping. **(1) The Rules section is this model's high-compliance zone** — instructions there outperform the same words anywhere else in the prompt; the block-position experiment (v3) actively hurt. **(2) The description is not a label, it's a defense**: a description that *invites guessing* ("the required house format") gets guessed; one that *forbids* it ("cannot be guessed — read first") gets read. That authoring rule now lives in `skills/README.md`. Final: **136 pytest**; gate **11/11 ollama** (68,338 in / 2,261 out — the new Rules line regressed nothing) and **11/11 gemini** (83,210 in / 2,522 out — flash-lite read the skill without any of the local model's coaxing; the trigger war was a 4B problem, the design survives it anyway).
