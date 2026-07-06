# researcher-harness

A **from-scratch agent harness** — the loop, tools, providers, and context plumbing
that sit *under* something like Claude Code — rebuilt by hand to understand how the
real ones actually work. Learning-first: **understanding beats features, every time.**

Two reasons it exists:

1. **Learn by rebuilding.** How do Claude Code, Codex CLI, opencode, and aider work
   under the hood? The fastest way to know is to build one and hit the same walls they did.
2. **"claude2 insurance."** Own an independent, provider-agnostic harness on this
   machine — so the day a single AI vendor isn't available here isn't the day work stops.

It is **not** a product, and **not** an SDK wrapper. One user: the owner. Real research
work keeps running on Claude Code as usual; this harness doesn't touch it until it earns
the trust (Stage 3).

## The three pains it's built around

1. **Signal vs. noise.** Agents drown in context they didn't need — raw file dumps,
   full command output, tool chatter. Most of it is noise; the answer is a few lines
   of signal. Paying (in tokens and latency) to bury the signal is the core waste this
   project attacks.
2. **Prompt reuse by hand.** Reusing a good prompt (plan / summarize / clean-up) means
   copy-paste-and-edit every time. The goal: templates plus small interviewers that
   collect what's missing, so a workflow is `/name args`, not a manual rewrite.
3. **Learning & independence.** Understand the machine from the inside, and own a
   working, provider-agnostic copy of it — whatever happens to any one vendor.

## What it does today

| Piece | What it is |
|---|---|
| **The loop** | One model call → run the tool calls it asks for → append results → repeat. The entire "agent" is [`src/harness/core/loop.py`](src/harness/core/loop.py). |
| **Tools** | Read / edit files, search, run commands, fetch web pages (`web_fetch`), and a **todo** tool — an external plan the model can't forget. Edits show a unified diff at the approval prompt. |
| **Subagents** | Delegate a subtask to a fresh (or forked) child loop and get back just its result — optionally wearing a named role. |
| **Providers** | Ollama (local, free — via its **native** `/api/chat`), Gemini (OpenAI-compat), and Anthropic (native), each behind its own adapter. The loop speaks one dialect; adapters translate both directions. |
| **Visible mind** | Thinking and narration stream live to the terminal, so you watch it reason and talk instead of staring at a spinner. |
| **Modes** | Switchable permission profiles — from "just chat" to "auto-approve writes in this folder" (see the guidebook below). |
| **Agents (roles)** | Markdown-defined personalities with their own prompt, default mode, and optionally their own model. |
| **Reasoning control** | `/think off…high` — the chain-of-thought budget knob, per session or per role. |
| **Permissions** | [`harness.toml`](harness.toml) decides per tool: allow / ask / deny. Deny is absolute in every mode. |
| **Token meter** | Every call reports tokens. The project exists because of context economics, so the cost is always on screen. |

## Status

**Stage 2R (frontier parity) in progress — 2.10–2.13 shipped 2026-07-07.** The harness
runs end-to-end on both providers with modes, roles, reasoning control, and web fetch.

- **129 offline tests** against a FakeModel — the loop's contract, zero tokens: `uv run pytest -q`
- **Exit gate 10/10 on both providers** (`uv run python acceptance/run.py <provider>`):
  local qwen3:4b-instruct and gemini-2.5-flash-lite — including "explore mode blocks a
  write", "the plan role proposes without touching anything", and "answer from a fetched page".

Remaining in 2R: skills (2.14), the local speed lab (2.15), MCP as a stretch (2.16) —
then **Stage 3** turns the three pains above into real features.
Plans: [docs/ROADMAP.md](docs/ROADMAP.md) → [docs/ROADMAP2.md](docs/ROADMAP2.md).

## Quickstart

```bash
# offline test suite — always run after a code change (sub-second, zero tokens)
uv run pytest -q

# run the harness (local model is free)
uv run harness                      # Ollama, build mode, default agent
uv run harness gemini               # paid fallback — quality validation
uv run harness --agent plan         # start as the read-only planning role
uv run harness --mode explore -y    # look-don't-touch, no prompts

# the live-model acceptance gate
uv run python acceptance/run.py <provider>
```

Local dev runs on `qwen3:4b-instruct` via Ollama (4 GB VRAM friendly). Gemini is the
paid fallback for validating response *quality*; debug loop logic locally so a runaway
loop costs $0. Anthropic's adapter is built but stays live-untested until the key is set
deliberately.

---

# The guidebook — driving the harness

Everything below happens inside `uv run harness [provider]`. Type a task at the
`you>` prompt; slash commands control the harness itself.

## Launch flags

| Flag | What it does |
|---|---|
| `ollama` \| `gemini` \| `anthropic` | pick the provider (default: `ollama`, free) |
| `--mode NAME` | start in a permission mode (`chat`/`explore`/`build`/`auto`); beats the agent's default |
| `--agent NAME` | start as a role from `agents/*.md` (default: `build`) |
| `-y` / `--yes` | auto-approve every *ask* — **never** overrides a deny |
| `--resume [ID]` | continue a saved session (latest if no ID) |
| `--sessions` | list saved sessions and exit |

## Built-in slash commands

| Command | What it does |
|---|---|
| `/help` | list builtins + the template commands found in `commands/` |
| `/mode` · `/mode NAME` | show / switch the permission profile, mid-session |
| `/agent` · `/agent NAME` | list roles / switch role (prompt + default mode + pinned model) |
| `/think` · `/think VALUE` | show / set reasoning: `off` `on` `low` `medium` `high` |
| `/tokens` | context size vs. the model's window |
| `/compact` | summarize-and-replace the conversation (costs one model call; continues in a new session file) |
| `/NAME args` | anything else runs `commands/NAME.md` with `{{args}}` substituted |

## Modes — how much can it touch?

A mode is a named permission profile in [`harness.toml`](harness.toml). Two laws hold
everywhere: the **deny list is absolute** (even `-y` can't cross it), and an auto-approved
write only counts **inside the working directory** — outside, it asks anyway.

| Mode | Feels like | What runs without asking |
|---|---|---|
| `chat` | the plain website chat | nothing — tools aren't even offered |
| `explore` | look, don't touch | reads (`read_file`, `grep`, `glob`, `list_dir`); everything else is refused |
| `build` | the default | reads run; writes/edits/shell ask y/N |
| `auto` | trusted coding flow | reads + writes/edits inside this folder; shell still asks |

When a tool is refused, the model is *told* — it reads the denial as a tool result and
adapts (usually by explaining what it would have done). Design: [note 16](docs/notes/16-permission-modes.md).

## Agents — who is it?

A role is a markdown file in [`agents/`](agents/): frontmatter (description, default
`mode`, optional pinned `model`, optional `think` level) + body = its system prompt.
Ships with:

| Role | Mode | Use it for |
|---|---|---|
| `build` | build | the default working agent (its prompt is `src/harness/prompts/system.md`) |
| `plan` | explore | "figure out how, don't do it" — every plan ends by offering `/agent build` to execute |
| `chill` | chat | thinking out loud with no tools in reach |
| `reviewer` | explore | adversarial read-only review — reports problems, fixes nothing |

The flow that earns its keep: `/agent plan` → discuss until the plan is right →
`/agent build` → "execute the plan above". History carries over; each switch continues
in a fresh session file so `--resume` stays truthful.

**Add a role:** drop `agents/myrole.md` with a `description:` line and a prompt. Pin
`model: gemini` to give one role the smarter paid model while everything else stays
local — that split (strong planner, cheap executor) is aider's benchmark-winning trick.
Subagents can wear roles too: the model can call `spawn_subagent(agent="reviewer", ...)`.
Design: [note 17](docs/notes/17-agents.md).

## Reasoning — pay for thinking only when it helps

`/think on` makes a capable model reason in a **separated trace**: streamed dim to your
terminal, then *stripped from history* so it never bills a later call. `/think off`
suppresses it; `low/medium/high` set effort on models with levels (gpt-oss-class,
Gemini, Anthropic budgets).

Why the default is off locally, in one measured line: thinking qwen3 burned **10× the
tokens for a worse score** (13,614 vs 1,460; 5/7 vs 7/7). And mind the fine print: this
knob needs Ollama's *native* API (the OpenAI-compat endpoint silently ignores it — we
probed), and fixed-mode models ignore it entirely: the 2507 `-instruct` never thinks,
the 2507 thinking variant can't stop. Economics + probes: [note 18](docs/notes/18-reasoning-control.md).

## Sessions, tokens, and the meter

Every message lands in `sessions/<id>.jsonl` the moment it exists — a crash never loses
more than nothing. `--resume` replays the latest (or a named) session; `/compact` and
`/agent` switches continue in a new file so old transcripts stay intact.

After every call the meter prints `call: X in / Y out | session: totals`, and after each
turn the context line shows how full the window is. When Gemini reports more `total`
tokens than `in + out`, the difference is *hidden thinking* — the meter is how you
catch it.

## Permissions — the fine print

[`harness.toml`](harness.toml) is versioned on purpose: the policy is auditable and
travels with the repo. Per tool: `allow` (silent), `ask` (y/N), `deny` (refused flatly).
Precedence is fail-closed — deny > ask > allow — and `-y` upgrades *ask* only. The
`[modes.*]` sections are the profiles `/mode` switches between; the plain
`[permissions]` table *is* `build`. Design: [note 10](docs/notes/10-permissions-v2.md) + [16](docs/notes/16-permission-modes.md).

---

## Layout

Code under `src/`, prose under `docs/`, frozen/experimental under `archive/`, and the
runtime config the harness reads from the working directory stays at root.

| Path | What it is |
|---|---|
| `src/harness/` | The living codebase — `core/`, `providers/`, `tools/`, `cli/`, `prompts/` (installable package) |
| `tests/` | FakeModel pytest suite (the loop's contract, offline) |
| `acceptance/` | The live-model exit gate (Stage 2, growing through 2R) |
| `docs/` | [ROADMAP](docs/ROADMAP.md), [ROADMAP2](docs/ROADMAP2.md), design [notes/](docs/notes), [open problems](docs/problem.md) |
| `commands/` | Slash-command template library (`/name args` → `commands/name.md`) |
| `agents/` | The role library (`/agent name` → `agents/name.md`) |
| `harness.toml`, `AGENTS.md` | Permissions policy and project memory — read from cwd at runtime |
| `archive/` | Frozen Stage-1 `mvp/`, throwaway `labs/`, and the real `prompt/` library (Stage-3 raw material) |

Working rules and the project's constitution are in [CLAUDE.md](CLAUDE.md).
