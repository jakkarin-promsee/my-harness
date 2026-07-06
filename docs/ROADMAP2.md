# ROADMAP2 — Stage 2R: Copy the seniors, round two (frontier parity)

> **v2 — approved 2026-07-07.** First drafted after a research pass over Claude Code, opencode, aider, Codex CLI and the local-model landscape; revised the same day after a second, source-verified pass (live docs fetched — §2's claims carry their receipts in §7). Slots **between** ROADMAP.md's Stage 2 (closed, gate 7/7) and Stage 3 (untouched — still the destination). Same constitution, same mini-cycle: *study 2–3 references → design note → implement → gate green.* This file governs Stage 2R; ROADMAP.md and CLAUDE.md point here.

---

## 1. Where this came from

The owner's wish list (2026-07-07), translated into what the frontier actually calls each thing:

| The wish (owner's words) | Frontier name | Who does it best | Feature |
|---|---|---|---|
| "chain of thought feature" | **Reasoning control** — a thinking *budget knob*, not a display (display shipped in 2.9a) | Ollama `think` param; Anthropic extended thinking; aider `--reasoning-effort` | 2.12 |
| "many ai roles — chill guy, red team, working agent, planning agent" | **Agents** — markdown-defined roles: own prompt + model + permission mode | opencode agents; Claude Code subagents | 2.11 |
| "modes — ask only / ask but can see / coding" | **Permission modes** — switchable profiles over the permission table | Claude Code's six modes; Codex approval × sandbox | 2.10 |
| "local ai more fast and smart" | **Runtime tuning + model refresh** — flash attention, KV-cache quant, context sweep, bake-off | Ollama env knobs; the evaluate-model skill we already have | 2.15 |
| "adding more tools" | **Close the core-tool gap** (web_fetch), then **skills**, then **MCP** — the frontier's infinite tool bus | every harness; SKILL.md and MCP are open standards | 2.13 / 2.14 / 2.16 |
| "see it think or call the tool" | **Already shipped** (2.9a/b, notes 11–12) — narration preambles + dim thinking + streaming. Remaining polish: show the *diff* before approving an edit | Claude Code's diff preview | 2.13 |

The instinct was right on every line — each "vibe idea" has a senior implementation to copy. That is exactly what Stage 2R is.

## 2. What the research found (the frontier audit, verified)

**Claude Code** now runs [**six** permission modes](https://code.claude.com/docs/en/permission-modes) — `default` (labeled *Manual*: ask for everything mutating), `acceptEdits`, `plan` (read-only), `auto` (new: a separate **classifier model** reviews each action in the background — research preview), `dontAsk` (auto-deny anything not pre-approved; CI mode), `bypassPermissions` — with Shift+Tab cycling `default → acceptEdits → plan`. Two details worth copying exactly: `acceptEdits` auto-approves not just file edits but *scoped filesystem shell commands* (`mkdir`, `touch`, `mv`, `cp`, `rm`…) **only inside the working directory**; and plan mode ends in an **approval flow** — the plan is presented, and approving it switches the session into an executing mode. Roles live as [subagents](https://code.claude.com/docs/en/sub-agents): markdown files with YAML frontmatter (`name`, `description`, `tools`, `model`), body = system prompt.

**opencode** made the move that shapes this whole roadmap: it **merged modes into agents**. An [opencode agent](https://opencode.ai/docs/agents/) is one markdown file carrying prompt + model + permissions; `build` and `plan` are just the two built-in primary agents, Tab-switched, and subagents come from the same registry, invokable by @-mention or by the model itself. Fresh detail: opencode has **deprecated the `tools` frontmatter field in favor of per-agent `permission`** — the field the frontier keeps is permissions, which confirms our design of agents *referencing named permission profiles* instead of raw tool lists.

**aider** contributes two ideas. Its [chat modes](https://aider.chat/docs/usage/modes.html) (`/ask`, `/code`, `/architect`) are per-message role switches. And its [architect/editor split](https://aider.chat/2024/09/26/architect.html) — a strong model proposes, a cheap model edits — produced SOTA editing benchmarks and remains the cleanest proof that **per-role model assignment is the cheap intelligence hack**: exactly the owner's "making optimize ai intelligence more easy".

**Codex CLI** frames the territory as two orthogonal knobs: [`approval_policy`](https://developers.openai.com/codex/agent-approvals-security) (`untrusted` / `on-request` / `never`) × `sandbox_mode` (`read-only` / `workspace-write` / `danger-full-access`); `--full-auto` = on-request + workspace-write. The OS sandbox itself we skip (§6), but the ladder matches the owner's wished-for modes almost word for word.

**Skills — the miss in this file's first draft.** A [SKILL.md](https://agentskills.io) is a folder with a markdown file: YAML frontmatter (`name`, `description`), body = instructions, optional bundled files. Anthropic opened it as a standard 2025-12-18; it's now adopted by **26+ tools** including Codex CLI, Gemini CLI, Copilot and Cursor. The mechanism is **progressive disclosure**: only name + description load at startup; the model reads the full body *when the task matches*. Crucially, skills are **model-invoked** — the complement of our slash commands (2.7), which are *user*-invoked. This is also the missing bridge to Stage 3.2: the owner's `archive/prompt/` templates want to become exactly this shape.

**Reasoning, on the wire.** Ollama has a [first-class `think` parameter](https://docs.ollama.com/capabilities/thinking) — boolean on qwen3/deepseek-class models, `"low"/"medium"/"high"` levels on gpt-oss-class — and returns the trace in a separate `message.thinking` field instead of `<think>` tags scraped out of content. Providers differ on whether reasoning is re-sent within a turn (Anthropic strips server-side); our 2.9a decision (never re-send) matches Anthropic and stays the default.

**Local runtime.** Two env knobs we have never turned: `OLLAMA_FLASH_ATTENTION=1` and [`OLLAMA_KV_CACHE_TYPE=q8_0`](https://smcleod.net/2024/12/bringing-k/v-context-quantisation-to-ollama/) (flash attention is a *prerequisite* for KV quant). Verified: q8_0 **halves KV-cache memory** with measured perplexity deltas of 0.002–0.05 — undetectable — which on a fixed 4 GB card converts directly into context: our 8,192 window could become 16,384 in the same VRAM. The 4 GB tier picks ([2026 surveys](https://www.mayhemcode.com/2026/06/best-local-llms-for-4gb-6gb-and-8gb.html)): qwen3-class has the most stable tool calling; phi-4-mini is the structured-output surprise. We don't chase releases — we re-run the bake-off when there's a reason.

**MCP** just got easier to speak: the [2026-07-28 release candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) drops protocol-level sessions for a **stateless core**, with exactly two standard transports (stdio, streamable HTTP). A minimal stdio client is a smaller project than it was a year ago.

**And the meta-finding: convergence.** Every 2026 comparison says the same thing — skills, hooks, subagents, permission modes and MCP are now *everywhere*; the top harnesses converged and the gap between them narrowed sharply. The target we're copying has **stopped moving**. Parity is a finite list, and this roadmap is that list.

### The gap table

| Capability | Claude Code | opencode | aider | Codex | **Us today** |
|---|---|---|---|---|---|
| Permission modes (switchable) | 6 modes, Shift+Tab | per-agent perms | n/a (git is the undo) | policy × sandbox | ❌ one static table |
| Roles / agents | subagents (md) | agents (md) — primary + sub | architect/editor | profiles | ❌ one hardcoded prompt |
| Per-role model | ✅ | ✅ | ✅ (the SOTA trick) | ✅ | ❌ one model per session |
| Reasoning control | thinking budgets | per-agent | `--reasoning-effort` | `model_reasoning_effort` | ❌ display only (2.9a) |
| Skills (model-invoked procedures) | ✅ (originated it) | ✅ | — | ✅ | ❌ (commands are user-invoked) |
| Web fetch tool | ✅ | ✅ | `/web` | ✅ | ❌ |
| Diff preview at the gate | ✅ | ✅ | ✅ | ✅ | ❌ (gate prints args) |
| Streaming, narration, thinking display | ✅ | ✅ | ✅ | ✅ | ✅ 2.9 |
| Todo/plan tool | ✅ | ✅ | — | ✅ | ✅ 2.9c |
| Subagents | ✅ | ✅ | — | ✅ | ✅ 2.6 (roles missing) |
| Sessions/resume, compaction, slash cmds | ✅ | ✅ | ✅ | ✅ | ✅ 2.3/2.5/2.7 |
| MCP client | ✅ | ✅ | — | ✅ | ❌ (consciously) |
| Hooks | ✅ (30 lifecycle events) | ✅ | — | — | ❌ (consciously) |

Read the ✅ column bottom-up and Stage 2 did its job: the loop, tools, sessions, permissions, streaming and todo are all standard. The gap is concentrated in exactly the owner's wishes. Good instincts.

## 3. Four design insights that shape the plan

1. **Modes and roles converged.** opencode's agents *are* its modes — one markdown file bundles prompt, model, permissions. We keep the two concepts orthogonal (a mode = a named permission profile; an agent = behavior + model + default mode) because permissions must stay fail-closed and auditable in `harness.toml`, but we build modes **first** so agents have profiles to reference.
2. **Per-role models are the cheap intelligence hack.** aider's architect/editor split beats single-model setups. For us: `plan` role on gemini-flash (smart, rare, cheap), `build` role on local qwen3 (free, frequent). The budget rule already says this — roles make it structural instead of manual.
3. **Chain-of-thought at the frontier is a budget knob, not a feature.** Display: shipped. What's missing is *control* — on/off/level per call — and our own Stage-2 data says why it matters: thinking qwen3 burned **10× the tokens for a worse score** (13,614 vs 1,460; 5/7 vs 7/7). The frontier default is thinking OFF locally, escalate on demand.
4. **Procedures became a portable standard.** Skills are how every 2026 harness packages "how to do task X" for the *model* to find on its own — and our architecture gets progressive disclosure nearly free, because "read the full skill when relevant" is just `read_file`. One small feature buys both frontier parity and the on-ramp to Stage 3.2.

## 4. The plan — one feature per cycle, in this order

Each feature = design note in `docs/notes/` first, FakeModel tests, acceptance green before the next. Numbering continues from 2.9; Stage 2's closed gate stays closed — 2R has its own.

### 2.10 Permission modes (the wish-4 ladder)

Named permission profiles in `harness.toml`, switched at runtime with `/mode <name>` and at launch with `--mode`:

| Mode | Owner's words | What it is |
|---|---|---|
| `chat` | "ask only, like the websites" | **no tools offered at all** — the tools array isn't even sent; pure conversation |
| `explore` | "ask but can see my computer" | read-only tools allowed (`read_file`, `list_dir`, `grep`, `glob`); everything else denied — Claude Code's plan mode, Codex's read-only |
| `build` | today's behavior | current table: reads allowed, writes/shell ask |
| `auto` | "coding, all tools" | `write_file`/`edit_file` auto-approved **inside cwd only** (paths outside still ask — the acceptEdits scoping rule); `run_shell` still asks unless allowlisted; `deny` list absolute; `-y` semantics folded in |

Copy from: Claude Code's mode ladder (its `dontAsk` ≈ our `-y` + allowlist; its classifier-checked `auto` consciously skipped — §6), Codex's presets. Builds directly on 2.8's fail-closed precedence — a mode is just *which table is active*. `chat`/`explore` are also the guard rail the constitution wants: point the harness at anything with zero risk. **Acceptance:** a task per mode proving enforcement (e.g. in `explore`, a write attempt comes back as a permission-denied tool result, and the agent says so instead of crashing).

### 2.11 Agents — the roles registry (the big one)

Markdown-defined roles in `agents/*.md` (runtime dir at cwd, sibling of `commands/` — same pattern as 2.7): frontmatter carries `description`, `model`, `mode` (default permission profile from 2.10), `think` (default reasoning level for 2.12); body = the system prompt, assembled with the same env/AGENTS.md pipeline as 2.4. Switch with `/agent <name>`; ships with built-ins:

- `build` — today's harness identity (the default)
- `plan` — `explore` mode, prompt says *investigate and propose, never edit*; its final plan **ends by offering the switch** ("run `/agent build` to execute") — the light version of Claude Code's plan-approval flow → the "planning agent"
- `chill` — `chat` mode, no tools, a warm conversational prompt → the "chill guy", verbatim
- `reviewer` — `explore` mode, adversarial prompt → the "red team" seed

`spawn_subagent` gains an `agent=` parameter so subagents draw from the same registry (opencode's primary/subagent unification). Per-role `model` is insight #2 made real: `plan` can pin gemini while `build` stays local. Agents reference permission *profiles*, never raw tool lists — the direction opencode's deprecation confirms. Copy from: opencode agents, Claude Code subagent frontmatter. **Acceptance:** switch to `plan`, ask for a change → plan produced, zero writes, switch offered; spawn a subagent with a named role.

### 2.12 Reasoning control (the real CoT feature)

The knob on top of 2.9a's display:

- `/think off|on|low|medium|high` at runtime; `think` default per agent (2.11) and per provider config.
- Ollama adapter uses the native `think` parameter — boolean for qwen3/deepseek-class, level string for gpt-oss-class — and reads `message.thinking`, replacing the `<think>`-scraping dialect where supported (the scraper stays as fallback; `normalize_reply` remains the single path).
- Anthropic adapter maps levels to extended-thinking budgets — spec'd now, live-tested when the key arrives (problem.md #1).
- Policy stays: thinking never re-enters history (2.9a). Note the within-turn-preserve variant (DeepSeek-style) as a documented non-goal until a model we run needs it.
- The design note must carry the economics table: instruct vs thinking qwen3, tokens vs score — the reason the default is `off` locally.

Copy from: Ollama thinking docs, aider `--reasoning-effort`, Anthropic extended thinking. **Acceptance:** same task run at `off` and `on` shows the token delta in the meter; `off` on a thinking model actually suppresses the trace.

### 2.13 Tool gap, round one — web_fetch + the diff gate

- **`web_fetch(url)`** — HTTP GET → readable text (strip tags, collapse whitespace), head+tail truncation like 2.2, `ask` in every mode's table by default. This is the last missing member of the frontier core set (read/write/edit/glob/grep/ls/shell/todo/task/**webfetch**). Web *search* needs an API key/provider — parked, noted, not built.
- **Diff preview at the permission gate** — the remaining "see what it's doing" polish: `edit_file`/`write_file` approval prompts render a unified diff (old→new) instead of raw JSON args. `difflib` is stdlib; every senior does this; it makes `ask` mode *pleasant* instead of blind.

**Acceptance:** a task that fetches a real URL and answers from it; gate snapshot test showing a diff render.

### 2.14 Skills — the model's own procedure library

`skills/` dir at cwd (runtime, sibling of `commands/`): each skill = a folder with `SKILL.md` — YAML frontmatter (`name`, `description`), body = the procedure, optional bundled reference files. The loader injects **one line per skill** (name + description) into the system prompt at assembly time (the 2.4 pipeline); the model activates a skill by calling `read_file` on its `SKILL.md` when the task matches. That's the whole feature — progressive disclosure with zero new machinery, because reading files on demand is what the model already does. No plugin packaging, no allowed-tools frontmatter, no auto-execution: the standard's core only.

The distinction that earns it a separate feature: `commands/` (2.7) is the **human's** library — user-invoked, `{{args}}`-substituted. `skills/` is the **model's** library — model-invoked, description-triggered. Stage 3.2 (prompt middleware over `archive/prompt/`) will build directly on this loader.

Copy from: [agentskills.io/specification](https://agentskills.io/specification), Claude Code skills, the Anthropic engineering post. **Acceptance:** a task whose correct solution requires the model to notice a skill from its one-line description, read it, and follow the procedure inside (e.g. a house-style rule it couldn't guess).

### 2.15 Local lab — faster and smarter on the same 4 GB

An experiment with a lab log (`docs/notes/`), not a code feature:

1. Set `OLLAMA_FLASH_ATTENTION=1` + `OLLAMA_KV_CACHE_TYPE=q8_0`; measure tok/s and VRAM before/after (`ollama ps`).
2. Sweep context: 8,192 → 12,288 → 16,384 under quantized KV; find the ceiling where the gate still passes and speed holds.
3. Re-run the model bake-off via the **evaluate-model** skill against the *grown* acceptance suite: incumbent `qwen3:4b-instruct` vs the current 4 GB tier (phi-4-mini for structured output, latest qwen/gemma smalls). No chasing releases — the skill's verdict decides.
4. Honesty rule for the note: on 4 GB, "smarter" comes mostly from the harness (ACI, todo, roles, modes, skills), not the weights. Measure, don't hope.

Runs **last of the code-adjacent features** so the bake-off scores models against the final, grown suite. **Acceptance:** the exit-gate suite on the tuned config, same-or-better score, tokens and tok/s recorded.

### 2.16 MCP client (stretch — the infinite tool bus)

The frontier's answer to "adding more tools" is not writing more tools — it's speaking MCP so any server's tools mount into the registry. The 2026-07-28 spec RC makes the minimal slice smaller than it used to be: stdio transport only, `tools/list` → merge into our registry (namespaced, `ask` by default), `tools/call` → dispatch. No resources, no prompts, no HTTP transport in round one. This is still the heaviest feature here — it ships **only if 2.10–2.15 land clean and the appetite is there**; otherwise it rolls into a future round with hooks.

## 5. Exit gate for Stage 2R

One command, two providers, like Stage 2:

- Acceptance suite grown to **~11–13 tasks**: the existing 7 + mode enforcement (explore blocks a write), role switch (plan produces no edits, offers the handoff), reasoning toggle (token delta visible), web_fetch task, skill-trigger task.
- Gate passes on **gemini-2.5-flash-lite AND the local workhorse** (whichever model 2.15 crowns).
- The §2 gap table re-scored: every ❌ in the "Us today" column either ✅ or consciously-skipped-with-reason.
- Token meter still visible everywhere; all design notes written; `docs/notes/README.md` and the CLAUDE.md status line updated.

**Then Stage 3 opens exactly as ROADMAP.md specs it** — surgical context ops first. Nothing in 2R touches the three pains directly; 2R exists so that when Stage 3 bends the harness, it bends a frontier-shaped one.

## 6. What we are deliberately NOT copying

| Frontier thing | Why not |
|---|---|
| Auto-mode's classifier (Claude Code) | The most interesting new thing on the frontier — a second model reviews every action — but it *requires* a second model per action, and its threat model (prompt injection at scale, org policy) isn't ours. Our `auto` stays dumb: scoped auto-approve + absolute deny list |
| OS-level sandbox (Codex) | Windows, one user, learning project — modes + fail-closed permissions are the right-sized guard |
| Hooks (30 lifecycle events in Claude Code) | No consumer until Stage 3.4's findings channel; revisit then |
| TUI framework (crush, opencode) | The plain REPL is understood line-by-line; a TUI teaches nothing about harnesses |
| Git auto-commit (aider) | The owner drives git; the commit-progress skill covers it on the dev side |
| Repo-map (aider) | Built for big-codebase editing; our Stage 3 target is research sessions, not monorepos |
| Checkpointing / rewind | Now standard in the frontier (Claude Code checkpoints, Cline rollback) — but already spec'd as Stage 3.3; it belongs to the pain-killing stage, not parity |
| Anthropic prompt caching | The day the key arrives (problem.md #1) |
| IDE integration, multi-user, cloud anything | Not this project (see CLAUDE.md "what this is NOT") |

## 7. Reference shelf additions (for the 2R design notes)

| Resource | Feeds |
|---|---|
| [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes) (six modes; acceptEdits scoping; plan-approval flow) | 2.10, 2.11 |
| [Codex approvals & security](https://developers.openai.com/codex/agent-approvals-security) + [sandboxing](https://developers.openai.com/codex/concepts/sandboxing) | 2.10 |
| [opencode agents](https://opencode.ai/docs/agents/) + [permissions](https://opencode.ai/docs/permissions/) | 2.10, 2.11 |
| [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) | 2.11 |
| [aider: separating code reasoning and editing](https://aider.chat/2024/09/26/architect.html) | 2.11, 2.12 |
| [Ollama thinking docs](https://docs.ollama.com/capabilities/thinking) | 2.12 |
| [Agent Skills specification](https://agentskills.io/specification) + [Anthropic: equipping agents for the real world](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | 2.14 |
| [K/V context quantisation in Ollama](https://smcleod.net/2024/12/bringing-k/v-context-quantisation-to-ollama/) + [Ollama FAQ](https://docs.ollama.com/faq) | 2.15 |
| [4–8 GB VRAM model surveys, 2026](https://www.mayhemcode.com/2026/06/best-local-llms-for-4gb-6gb-and-8gb.html) | 2.15 |
| [MCP 2026-07-28 release candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) + [spec](https://modelcontextprotocol.io) | 2.16 |

---

## Status tracker (Stage 2R)

| Feature | Status |
|---|---|
| 2.10 Permission modes | **done** 2026-07-07 — note 16; gate 8/8 local qwen3 (new task H: explore blocks the write, agent reports it) |
| 2.11 Agents (roles) | **done** 2026-07-07 — note 17; gate 9/9 local (new task I: plan role investigates read-only, offers the `/agent build` handoff) |
| 2.12 Reasoning control | **done** 2026-07-07 — note 18; new native `/api/chat` adapter (v1 provably ignores `think`); gate 9/9 on BOTH providers; think-lab economics recorded |
| 2.13 web_fetch + diff gate | **done** 2026-07-07 — note 19; gate 10/10 on BOTH providers (new task J: fetch example.com, report the heading); diff gate proven by pytest snapshots (`tests/test_repl.py`) |
| 2.14 Skills | not started |
| 2.15 Local lab | not started |
| 2.16 MCP client (stretch) | not started |

*(Approved 2026-07-07 — pointers live in ROADMAP.md's stage tables and CLAUDE.md's status line + repo map. Update this tracker and the CLAUDE.md status line as features land.)*
