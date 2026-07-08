# The Guidebook

The complete manual for the harness, in two parts: **Part I — driving it** (every
flag, command, and knob a user meets) and **Part II — extending it** (how to add a
tool, a provider, a role, a skill, an MCP server — and how to know it works).

This document is a *map with routes*: each section gives you the working knowledge
and then points at the one place the full detail lives (a folder `README.md` for
what's-there, a `docs/notes/` entry for the why, a docstring for the how). One fact,
one home — the hierarchy is [note 15](notes/15-context-hierarchy.md).

---

# Part I — driving the harness

Everything here happens inside `uv run harness [provider]`. Type a task at the
`you>` prompt; slash commands control the harness itself.

## Providers — which model answers

```bash
uv run harness                # ollama (default) — local, free
uv run harness gemini-flash   # the quality lane
```

| Provider | What it is | When to use it |
|---|---|---|
| `ollama` | `qwen3:4b-instruct` local via Ollama's native API — free, runs the MICRO prompt tier on the 8K window | the workhorse for loop debugging: a runaway loop costs $0 |
| `ollama-think` | the *thinking* sibling of the same model — reasoning streams dim to the terminal; the experimental turn-reflection recap runs here (note 32) | the fun/study lane: watching a small model reason |
| `gemini` | `gemini-2.5-flash-lite` via the OpenAI-compat endpoint | the cheap regression lane (know its limit: it coin-flips role constraints — `docs/problem.md` #2) |
| `gemini-flash` | `gemini-2.5-flash` — the primary quality target since 2026-07-08 | validating response *quality*; museum baselines |
| `anthropic` | native `/v1/messages` adapter, fully built, **live-untested** | only after `ANTHROPIC_API_KEY` is set deliberately (`docs/problem.md` #1) |

**The budget rule** (constitution §4): debug agent-loop *logic* locally, validate
*quality* on the paid lanes. Never point a possibly-buggy loop at a paid endpoint.

## Launch flags

| Flag | What it does |
|---|---|
| `<provider>` | pick from the table above (default: `ollama`) |
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
| `/prompt` · `/prompt TIER` | show the prompt-ladder tiers with measured token costs / switch (`micro` `compact` `standard` `full`) — local defaults to `micro`, Gemini to `standard` |
| `/voice` · `/voice NAME` | how much the agent talks: `quiet` (scripted runs) · `normal` (local default) · `explain` (Gemini default — narrates the plan, teaches as it goes, closes with a verified summary) |
| `/mcp` | list connected MCP servers and the tools they mounted |
| `/tokens` | context size vs. the model's window |
| `/compact` | summarize-and-replace the conversation (costs one model call; continues in a new session file). Also fires **automatically** at a per-provider window threshold (85 % default, 60 % on the 8K local lanes — note 36); `auto_compact: 0` in a provider entry disables |
| `/NAME args` | anything else runs `commands/NAME.md` with `{{args}}` substituted |

## Modes — how much can it touch?

A mode is a named permission profile in [`harness.toml`](../harness.toml). Two laws
hold everywhere: the **deny list is absolute** (even `-y` can't cross it), and an
auto-approved write only counts **inside the working directory** — outside, it asks
anyway.

| Mode | Feels like | What runs without asking |
|---|---|---|
| `chat` | the plain website chat | nothing — tools aren't even offered |
| `explore` | look, don't touch | reads (`read_file`, `grep`, `glob`, `list_dir`); everything else is refused |
| `build` | the default | reads run; writes/edits/shell ask y/N |
| `auto` | trusted coding flow | reads + writes/edits inside this folder; shell still asks |

When a tool is refused, the model is *told* — it reads the denial as a tool result
and adapts (usually by explaining what it would have done). Design:
[note 16](notes/16-permission-modes.md).

## Agents — who is it?

A role is a markdown file in [`agents/`](../agents/): frontmatter (description,
default `mode`, optional pinned `model`, optional `think` level) + body = its
specialization, layered onto the shared backbone prompt. Ships with:

| Role | Mode | Use it for |
|---|---|---|
| `build` | build | the default working agent (*is* the backbone — `src/harness/prompts/system.md`) |
| `plan` | explore | "figure out how, don't do it" — every plan ends by offering `/agent build` to execute |
| `chill` | chat | thinking out loud with no tools in reach |
| `reviewer` | explore | adversarial read-only review — reports problems, fixes nothing |

The flow that earns its keep: `/agent plan` → discuss until the plan is right →
`/agent build` → "execute the plan above". History carries over; each switch
continues in a fresh session file so `--resume` stays truthful. Subagents can wear
roles too: the model can call `spawn_subagent(agent="reviewer", ...)`. Design:
[note 17](notes/17-agents.md) + [note 23](notes/23-backbone.md).

## Reasoning — pay for thinking only when it helps

`/think on` makes a capable model reason in a **separated trace**: streamed dim to
your terminal, then *stripped from history* so it never bills a later call.
`/think off` suppresses it — on Gemini this really is an off-switch
(`reasoning_effort: "none"`), which matters because **flash thinks by default and
bills it invisibly**: the meter's `N think` count (derived as
`total − prompt − completion`) is how you see it. `low/medium/high` set effort on
models with levels.

Why the default is off, in two measured lines: thinking qwen3 burned **10× the
tokens for a worse score** (13,614 vs 1,460; 5/7 vs 7/7), and flash's hidden default
thinking bought nothing at our task grain (A/B'd in the 2.20 lab — note 26). Mind
the fine print: this knob needs Ollama's *native* API (the OpenAI-compat endpoint
silently ignores it), and fixed-mode models ignore it entirely. Economics + probes:
[note 18](notes/18-reasoning-control.md).

## Skills — procedures the model discovers

A skill is `skills/<name>/SKILL.md` ([the open Agent Skills standard](https://agentskills.io/specification)):
at startup only each skill's **name + description line** enters the system prompt;
when a task matches, the model reads the full body with `read_file` — progressive
disclosure, so a big library costs almost nothing until used. See
[`skills/README.md`](../skills/README.md) and [note 20](notes/20-skills.md).

## MCP servers — the infinite tool bus

The harness speaks [MCP](https://modelcontextprotocol.io) as a stdio client: any
server declared in `harness.toml` is spawned at startup and its tools mount into
the registry as `mcp__<server>__<tool>`, gated like every other tool (they fall
into each mode's `default` bucket — **ask** in `build`/`auto`, **deny** in
`explore`). `/mcp` shows what's connected.

```toml
[mcp.servers.duckduckgo]
command = "uvx"
args = ["--system-certs", "--from", "duckduckgo-mcp-server[browser]", "duckduckgo-mcp-server"]
env = { SSL_CERT_FILE = "C:/Users/BTCOM/.harness/ca-bundle.pem" }  # the TLS note below
# enabled = true      # flip off without deleting
# timeout = 30        # seconds per call
```

The shipped flagship is DuckDuckGo web search — no API key, so the free lanes stay
free. Two operational notes, both learned the hard way (note 33):

- **Child-process TLS:** this machine's TLS interception breaks Python inside MCP
  *child* processes (the harness's own truststore fix can't reach them). The cure
  is `python -m harness.tools.ca_bundle`, which writes certifi + the Windows cert
  stores to `~/.harness/ca-bundle.pem`; hand it to servers via the `env` key.
  Regenerate when certs rotate.
- **Economics:** every mounted server's schemas ride *every* call. Two tools are
  trivial; keep servers few and deliberate, and let the meter have the final word.

## Sessions, tokens, and the meter

Every message lands in `sessions/<id>.jsonl` the moment it exists — a crash never
loses more than nothing. `--resume` replays the latest (or a named) session;
`/compact` and `/agent` switches continue in a new file so old transcripts stay
intact.

After every call the meter prints `call: X in / Y out | session: totals`, and after
each turn the context line shows how full the window is. When Gemini reports more
`total` tokens than `in + out`, the difference is *hidden thinking* — the meter is
how you catch it.

On the `ollama-think` lane only, an experimental **turn reflection** runs: when a
turn finishes, a fast non-thinking sibling model distills it into a few terse lines
and the turn's tool churn is replaced by that recap — rolling compaction that makes
the context line go *down*. Honest limits (it's lossy; resume replays the full
turn) in [note 32](notes/32-turn-reflection.md).

## Permissions — the fine print

[`harness.toml`](../harness.toml) is versioned on purpose: the policy is auditable
and travels with the repo. Per tool: `allow` (silent), `ask` (y/N), `deny` (refused
flatly). Precedence is fail-closed — deny > ask > allow — and `-y` upgrades *ask*
only. The `[modes.*]` sections are the profiles `/mode` switches between; the plain
`[permissions]` table *is* `build`. Design: [note 10](notes/10-permissions-v2.md) +
[note 16](notes/16-permission-modes.md).

---

# Part II — extending the harness

## The architecture in one page

A harness is a `while` loop around a chat API with tool-calling. One turn:

```
cli/repl.py                    human types a request
  → Agent.run_turn(messages)   the heart               (core/loop.py)
      → model.complete(...)    one HTTP call            (providers/)
      → run the tool_calls     each returns a string    (tools/)
      → append results, repeat
  → final text back to the human
```

The loop knows nothing concrete — model, tools, permission gate, and output
callbacks are all **injected**, which is why the same loop runs offline against a
`FakeModel` for zero tokens. The five packages and where to start reading:
[`src/harness/README.md`](../src/harness/README.md). The anatomy of harnesses in
general: [note 00](notes/00-anatomy.md).

**The invariants** (from [`src/harness/CLAUDE.md`](../src/harness/CLAUDE.md)) —
every recipe below lives inside them:

1. The loop is pure and injected — no HTTP, no `input()`, no printing it wasn't handed.
2. Adapters translate **both** directions (history is replayed every call).
3. Tools return a string, **always** — errors become ERROR text the model can read.
4. `messages` is ours — a plain Python list; editing it is free.
5. Two audiences — this code is *edited* by a coding agent but *run* by the
   harness's own agents; `AGENTS.md`, `commands/`, `agents/`, `skills/` at the repo
   root belong to the runtime.

## The workflow — how every change ships

The constitution ([CLAUDE.md](../CLAUDE.md)) in one line each:

1. **Design note first** — one page in `docs/notes/`: what the seniors
   (Claude Code / Codex CLI / opencode / aider / mini-swe-agent) do, what we build,
   how we'll know it works. Copy first, invent later.
2. **One feature at a time**, and no line you can't explain.
3. **Offline tests green** — `uv run pytest -q` drives the change against the
   FakeModel (sub-second, zero tokens).
4. **Live gate before and after** — `uv run python acceptance/run.py <provider>`;
   debug on `ollama` first, then the gemini lanes. The verifier checks *reality*
   (files on disk, exit codes), never the model's words.

The step-by-step procedure a coding agent should follow is the
**implement-feature** skill in `.claude/skills/`.

## Recipes

Ordered from config-only (no code) to core surgery.

### Add a slash command — no code

Drop `commands/<name>.md` with `{{args}}` where the user's text should land;
`/name args` is live immediately (templates are read from the cwd per keystroke).
Detail: [`commands/README.md`](../commands/README.md), [note 09](notes/09-commands.md).

### Add a role — no code

Drop `agents/<name>.md`: frontmatter (`description`, `mode`, optional `model`,
`think`, `backbone`) + body = the role's specialization on top of the backbone.
Pin `model: gemini-flash` to give one role the smart paid model while everything
else stays local — the strong-planner/cheap-executor split is aider's
benchmark-winning trick. Verify with `/agent <name>`.
Detail: [`agents/README.md`](../agents/README.md), [notes 17](notes/17-agents.md) + [23](notes/23-backbone.md).

### Add a skill — no code

Make `skills/<name>/SKILL.md` with a `description:` that says what it does **and
when to use it** — that line is the only trigger the model gets, and a description
that *invites guessing* gets guessed (measured on the 4B workhorse — note 20). If
the body holds a rule the model can't invent, say so: "the format is exact — read
this skill first". Restart (or `/agent`) to re-assemble the prompt.
Detail: [`skills/README.md`](../skills/README.md).

### Mount an MCP server — config only

Add a `[mcp.servers.<name>]` block to `harness.toml` (shape in Part I above),
restart, check `/mcp`. Permissions need zero new work — `mcp__*` names fall into
each mode's `default` bucket. If the server is Python-based and dies on TLS,
it needs the ca-bundle `env` fix (Part I). Keep servers few: their schemas ride
every call. Detail: [note 33](notes/33-mcp-client.md), client code `src/harness/tools/mcp.py`.

### Add a tool

In `src/harness/tools/`: write the function (return a string, **always** — let
errors become text), add a `_schema(...)` advertisement, register both in
`REGISTRY`/`SCHEMAS`, and add the name to `NEEDS_PERMISSION` if it mutates or
touches the network. House rules that took a stage to learn: **frame the
observation** (first line = what happened + the shape of the result — note 27),
**bound the output** (`grep` caps at 50 matches; unbounded output eats the 8K
window), and make ambiguity an error the model can fix (`edit_file`'s
match-exactly-once). The description teaches *workflow*, not just parameters —
it's the only signal the model has (note 04). Test pattern: `tests/test_tools.py`.
Detail: [`src/harness/tools/README.md`](../src/harness/tools/README.md).

### Add a provider

If it speaks OpenAI-compat: it's just a new entry in `cli/repl.py`'s `PROVIDERS`
dict (URL + key + model + per-lane defaults) — no new adapter. If it has its own
dialect: write pure `to_*` / `from_*` translation functions with a thin HTTP
`complete()` shell, like `providers/anthropic.py`, and remember translation goes
**both directions**. Test offline against a monkeypatched `requests.post`
(see `tests/test_anthropic.py`).
Detail: [`src/harness/providers/README.md`](../src/harness/providers/README.md), [note 03](notes/03-provider-adapter.md).

### Add or alter a permission mode

Add a `[modes.<name>]` table in `harness.toml` (each tool: `allow`/`ask`/`deny`,
plus a `default`). Remember the two laws: deny is absolute, and cwd-scoping guards
writes. `/mode <name>` switches live. Detail: [note 16](notes/16-permission-modes.md),
code `src/harness/core/permissions.py`.

### Change the system prompt

The backbone is `src/harness/prompts/system.md` — six tagged sections (identity,
loop, tools, failure, verification, style) that the ladder trims per tier; roles
extend it, `backbone: false` opts out. Measure any change: `/prompt` shows the
per-tier token cost, and prompt wording is empirically fragile — the accusatory
anchor cost a museum task until reworded ambient (note 30). Detail:
[notes 23](notes/23-backbone.md) + [24](notes/24-prompt-ladder.md).

### Add an acceptance task

Core tasks live in `acceptance/run.py`, museum exhibits in `acceptance/museum.py`.
A task = a prompt + a **verifier that checks reality** (files on disk, exit codes,
transcript facts — never the model's words) + optional `mode`/`agent`/`mcp` keys.
Per-provider task lists keep lane asymmetry explicit; `--n 3` majority is the rule
for anything flaky (single-run green has burned us — `docs/problem.md` #2).
Detail: [`acceptance/README.md`](../acceptance/README.md), [note 22](notes/22-failure-museum.md).

## Testing — the three rings

| Ring | Command | Costs | Proves |
|---|---|---|---|
| offline | `uv run pytest -q` | 0 tokens, sub-second | the loop's contract (FakeModel drives every path) |
| local live | `uv run python acceptance/run.py ollama` | $0, minutes | the whole stack end-to-end |
| paid live | `acceptance/run.py gemini` → `gemini-flash [--suite museum --n 3]` | cents | response *quality*; museum = judgment |

Both offline and live must be green to close a stage; the hold-out museum task is
touched **only** at stage close. When a live task fails, follow the triage order in
the **debug-live** skill: verifier → harness → config → model, in that order —
the harness must stay boring (constitution §5).

## Where to write things down

| You produced… | It goes in |
|---|---|
| the why of a new feature | `docs/notes/NN-name.md`, written *before* the code |
| a new file in a folder | that folder's `README.md` gets a row |
| a status change / milestone | the status line in [CLAUDE.md](../CLAUDE.md) |
| a decision only the owner can make | [`docs/problem.md`](problem.md) |
| a procedure a coding agent will repeat | `.claude/skills/` |
| a procedure the harness's own model should follow | `skills/` (runtime) |
