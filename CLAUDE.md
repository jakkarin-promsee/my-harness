# CLAUDE.md — researcher-harness

> This file is a **map**, not a container (note 15). It holds pointers, status, and rules — not implementation detail. The *why* lives in `docs/notes/`; the *what's-in-each-folder* in that folder's `README.md`; the *how-this-works* in each module's docstring. One fact, one home.

## What this project is

A **from-scratch agent harness**, built to learn how harnesses (Claude Code, Codex CLI, opencode, aider, ...) actually work under the hood — and to own an independent one if the day ever comes when Claude isn't available here ("claude2 insurance"). Learning-first side project: **understanding beats features, every time.**

What this project is **NOT**:

- It is NOT the owner's research project. That lives elsewhere and keeps running on Claude Code as usual. This harness never touches real research work until Stage 3 proves itself.
- It is NOT an Agent SDK wrapper. (See "Legacy context" below — an older brief in this repo says "build on the Agent SDK"; that decision belonged to a different plan and does not govern this project.)
- It is NOT a product. One user: the owner.

Read [docs/ROADMAP.md](docs/ROADMAP.md) before doing anything. It holds the full story, the staged plan, and the exit criteria for every stage.

## Current status

- **Release 1 packaged 2026-07-08:** root run-logs cleaned (`*.log` gitignored now; the five tracked `close-*.log` untracked — retrievable from git history), README rewritten as the front page, **[docs/GUIDEBOOK.md](docs/GUIDEBOOK.md)** added — the full manual, Part I driving / Part II extending — and version bumped to 1.0.0.
- **Repo restructured 2026-07-07:** code is an installable package under `src/harness/`, prose docs under `docs/`, and the frozen/experimental dirs (`labs/`, `mvp/`, `prompt/`) under `archive/`. Runtime/config files (`harness.toml`, `AGENTS.md`, `commands/`, `README.md`, `CLAUDE.md`) stay at root. Entry point: `uv run harness <provider>` or `uv run python -m harness <provider>`.
- **Context hierarchy added 2026-07-07 (note 15):** `CLAUDE.md` files are maps; folder `README.md`s are the containers; `docs/notes/` are the why; `.claude/skills/` are how-to-task procedures. See the router below.
- **Stage: 2C CLOSED 2026-07-08 — [docs/ROADMAP3.md](docs/ROADMAP3.md) done, all nine cycles in one day** (notes 22–31): failure museum + probes, backbone, prompt ladder (MICRO 264 tok carries the local gate), voice+effort knobs, thinking lab, framed observations, orientation map, attention anchors. **Exit gate: flash core 14/14 + museum 3/3 by majority (baseline 1/3); the HOLD-OUT passed its first-ever runs 3/3; local 14/14-by-majority at MICRO; 179 offline tests.** 2R closed same day (11/11 both providers). **2.16 MCP un-deferred and SHIPPED 2026-07-08 evening (note 33):** stdio MCP client, `[mcp.servers.*]` in `harness.toml` → `mcp__server__tool` in the registry (ask-by-default, `/mcp` lists), duckduckgo web search live with no API key — gate task O passes on all three lanes; 196 offline tests; child-process TLS lesson → `tools/ca_bundle.py` (regenerate `~/.harness/ca-bundle.pem` when certs rotate). **Primary = Gemini flash tier, two lanes** (quality `gemini-flash`, regression `gemini`+local); local stays the free debug rig. **Stage 3 (surgical context ops) is UNBLOCKED.** **[docs/ROADMAP4.md](docs/ROADMAP4.md) APPROVED 2026-07-08 (Stage 2A — ability & agency): Tiers 1–2 run before Stage 3. **TIER 1 (the floor) COMPLETE 2026-07-08, all four cycles same day (notes 34–37, 212 offline tests):** 2.25 turn control (Ctrl+C steers instead of kills; dangling tool calls repaired on interrupt AND resume), 2.26 wire survival (429/5xx/connection retried with backoff+jitter, Retry-After honored — the overnight killer retired), 2.27 auto-compact (turn-boundary trigger; **0.6 on the 8K lanes** — the summarize call must itself fit, live 400 receipt in note 36; chars/4 under-estimates 25–65%), 2.28 headless `-p` (stdout = answer only, exit 0/1, asks EOF-deny, `-p --resume` chains — cron works). **Tier 2 (the mind) OPEN — 2.29 museum + 2.30 two worlds SHIPPED (notes 38–39, 227 offline tests).** 2.29: M5–M9 probes + sealed M10; baselines certified the owner's felt-failures (cave FAILS both lanes, robot-register FAILS flash, coin-flip FAILS local; three verifier lessons frozen as fixtures). 2.30: `world:` tags split the backbone (core character / operator job / companion conversation), chill rides the core now, `/chat`·`/work` — **M9 flash 1/3→3/3, flash-lite core 15/15, local 13/15 + I 3/3 at N=3 (D = bait decay, problem.md #2)**; lessons: mission stays FIRST at micro (E 0/3→3/3), the just-talk line is standard-tier only. **⚠ INCIDENT (problem.md #3): the gate's auto-approved agent deleted the repo root mid-run — tracked files restored from git, `.env` LOST (re-paste GEMINI_API_KEY from AI Studio); destructive-shell tripwire now in acceptance/run.py.** **2.31 ask_user SHIPPED (note 40, 234 offline tests):** asking = a tool call (the turn continues — asking was turn-death, the stall's mechanism), EOF → flagged recommended default so headless never hangs; **the micro experiment bought a law — the MICRO loop is FROZEN** (any addition dilutes the 4B's action drive: E 0/3, M5 3/3→1/3; the ambiguity branch rides STANDARD only, tool schemas teach at micro). E-exact-edit joined D in the path-bait flake ledger (problem.md #2). **2.32 stable character SHIPPED, local leg (note 41, 235 offline tests):** core `honesty` section at STANDARD both worlds (evidence beats agreement, re-check once, premise-checking); the micro variant measured — the rule FIRES on the 4B then the re-check drowns (M7-local = counting limit in character clothes, model-limit like M6) → **the frozen-micro law is total: the MICRO backbone is the frozen 2C artifact; Stage 2A's mind work lives at standard+ tiers and tool schemas.** **TIER 2 CLOSE = flash re-checks (M7 movement, M5/M9 holds) + the sealed M10 hold-out — ALL BLOCKED on the problem.md #3 re-key. Re-create `.env` first.** Gate: `uv run python acceptance/run.py <provider> [--suite museum --n 3]`. Local workhorse: `qwen3:4b-instruct` (non-thinking 2507, `.env`) with `OLLAMA_CONTEXT_LENGTH=8192` machine-wide. Model lessons: `llama3.2:3b` fabricates — unusable; thinking `qwen3:4b` burns 10× tokens for a worse score — instruct variant; never `temperature: 0` on qwen3; flash-lite throws 503s/empty replies (handled) and coin-flips role constraints (problem.md #2 — owner call); **flash thinks by default, bills it invisibly (only in `total_tokens`), bought nothing at our task grain — pinned `off` (note 26)**; anchor wording must be ambient, not accusatory (note 30). [docs/problem.md](docs/problem.md): Anthropic live test + Ollama tray reboot + the lite-lane call remain open.
- Update this line whenever a stage milestone completes. This is the first thing a fresh session should check.

## Stack & environment

| Thing | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Managed with `uv` |
| **Primary target model** | Gemini flash tier (1M context) | **Flipped 2026-07-08 (owner decision, ROADMAP3 §0).** Two lanes: quality = `gemini-2.5-flash` (museum baselines, labs, flash-facing acceptance); regression = `gemini-2.5-flash-lite` + local. Budget relaxed 2026-07-08 (owner: "use my all gemini as you want") — the meter still records $/run, and loop-logic bugs still get debugged locally at $0 |
| Debug/fun model | Local via Ollama | RTX 3050 Ti Laptop, 4 GB VRAM → `qwen3:4b-instruct` (re-crowned 2026-07-07 vs phi4-mini/gemma3:4b — both fail tool-calling; note 21). Tuned machine-wide (2.15): `OLLAMA_FLASH_ATTENTION=1` + `OLLAMA_KV_CACHE_TYPE=q8_0` = +13 % gen speed; window `OLLAMA_CONTEXT_LENGTH=8192` is the hard ceiling on this card. *"Optimize my local for fun, not for real work"* |
| Wire protocol | Loop speaks OpenAI-style; adapters translate | Gemini via its OpenAI-compat endpoint; **Ollama via its native `/api/chat` since 2.12** (the only wire where `think` works — note 18); Anthropic native. Three adapters in `src/harness/providers/` |
| Anthropic API | Adapter built (2.1), live-untested | `ANTHROPIC_API_KEY` stays **unset** until the owner sets it deliberately for a live smoke test (a stray key silently bills pay-as-you-go) — see docs/problem.md |

**Budget rule:** debug agent-loop logic on the local model (an infinite-loop bug burns $0 locally); validate response *quality* on Gemini. Never point a possibly-buggy loop at a paid endpoint.

## Repo map

Layout: **code** under `src/`, **docs** under `docs/`, **frozen/experimental** under `archive/`, **runtime/config** at root.

| Path | What it is |
|---|---|
| `docs/ROADMAP.md` | The plan. Stages 0–3, exit criteria, reference shelf |
| `docs/ROADMAP2.md` | Stage 2R — frontier parity (closed 2026-07-08). Modes → agents → reasoning → web_fetch+diff → skills → local lab; MCP deferred |
| `docs/ROADMAP3.md` | Stage 2C — the cognitive core (closed 2026-07-08). Museum → backbone → ladder → voice+effort → thinking lab → observations → orientation → anchors |
| `docs/ROADMAP4.md` | Stage 2A — ability & agency (approved 2026-07-08, in flight). The full us-vs-modern-harness audit + three tiers: the floor (run robustness) → the mind (ambiguity, character, two worlds) → the arsenal |
| `docs/GUIDEBOOK.md` | **The manual** (release 1): Part I — driving the harness (flags, commands, knobs), Part II — extending it (recipes + the three testing rings). Routes to folder READMEs and notes; doesn't duplicate them |
| `docs/notes/` | Design notes — one per feature, written *before* implementing. The **why** |
| `docs/problem.md` | Open problems needing the owner — check when returning to the project |
| `docs/harness-context-v3.md` | Legacy brief (see below) |
| `src/harness/` | **The living codebase.** `core/` loop, `providers/`, `tools/`, `cli/`, `prompts/`. Its `CLAUDE.md` is the code map (auto-loaded when editing under `src/`); the multi-file subpackages (`core/`, `providers/`, `tools/`) each have a `README.md` — the local, file-by-file map (`cli/` and `prompts/` route to `repl.py`'s docstring and note 06 instead) |
| `tests/` | FakeModel pytest suite — the loop's contract, zero tokens (see `tests/README.md`). Run: `uv run pytest -q` |
| `acceptance/` | Stage-2 exit gate: live-model suite (see `acceptance/README.md`). Run: `uv run python acceptance/run.py <provider>` |
| `.claude/skills/` | Task procedures for **coding agents**: `explore`, `implement-feature`, `run-tests`, `debug-live`, `close-stage`, `evaluate-model`, `commit-progress`. (Distinct from `commands/`, which is the harness's own runtime feature.) |
| `commands/` | The harness's runtime slash-command library (`/name args` → `commands/name.md`) — read from cwd by the harness, **not** dev context. See `commands/README.md` |
| `agents/` | The harness's runtime **role library** (`/agent name` → `agents/name.md`: prompt + mode + model) — runtime, like `commands/`. See `agents/README.md` |
| `skills/` | The harness's runtime **skill library** (`skills/*/SKILL.md` — the model's own procedures, description-triggered) — runtime, like `commands/`. See `skills/README.md` |
| `harness.toml` | Permissions policy (allow/ask/deny per tool), versioned on purpose — read from cwd at runtime |
| `AGENTS.md` | Project memory injected into the harness's **own** system prompt — read from cwd at runtime |
| `archive/mvp/` | Stage 1 single-file harness — **frozen** as the learning artifact; `archive/mvp/ACCEPTANCE.md` + fixtures still serve acceptance |
| `archive/labs/` | Tiny throwaway experiments (raw API calls, wire-format studies) |
| `archive/prompt/` | The owner's **real prompt library** from the research project. Read-only reference — raw material for Stage 3.2 (prompt middleware) |

## Where to read (the router)

Don't load the whole repo. To work on one area, open only its column:

| If you're… | Open |
|---|---|
| new here | this file → [docs/GUIDEBOOK.md](docs/GUIDEBOOK.md) → [docs/ROADMAP.md](docs/ROADMAP.md) → [docs/notes/00-anatomy.md](docs/notes/00-anatomy.md) |
| touching any code | `src/harness/CLAUDE.md` (auto-loads) → the folder's `README.md` |
| changing the loop | `src/harness/core/README.md` + note 00 + `loop.py`'s docstring |
| adding/altering a provider | `src/harness/providers/README.md` + note 03 |
| adding/altering a tool | `src/harness/tools/README.md` + notes 04 & 13 |
| changing permissions / sessions / compaction | `src/harness/core/README.md` + notes 10 / 05 / (ROADMAP 3.1) |
| running or reading tests | `tests/README.md`, `acceptance/README.md` |
| doing a feature end-to-end | skill: **implement-feature** |
| understanding before you change | skill: **explore** |
| a live task fails / agent acts weird | skill: **debug-live** |
| exit criteria passed, milestone done | skill: **close-stage** |
| trying a new model as workhorse | skill: **evaluate-model** |
| session done, tree has changes | skill: **commit-progress** |

## Working rules (the constitution)

1. **Copy first, invent later.** Every feature starts with "how do mini-swe-agent / opencode / aider / Claude Code do this?" — study 2–3 references, then implement. Custom ideas wait until Stage 3.
2. **One feature at a time.** Never two features in flight. Design note → implement → acceptance suite green → next.
3. **No line you can't explain.** If code got copied in and the owner can't explain it, it doesn't merge. The whole point is understanding.
4. **Measure tokens from day 1.** The project exists because of context economics. Every stage keeps a visible token meter.
5. **The harness must be boring.** When a result looks weird, the question must never be "or is my harness buggy?" Tests stay green; the acceptance suite runs before and after every feature.
6. **Design note before feature.** One page in `docs/notes/` — what the seniors do, what we'll build, how we'll know it works.
7. **Ask the owner** when a decision changes scope or direction; he answers fast and enjoys the questions.

## Doc conventions

- English for all project docs.
- Reports use a storytelling tone: what was the problem → what did we do → why → what happened.
- Prose + tables over ASCII-art diagrams. Short pseudocode blocks are fine.
- **Context hierarchy (note 15):** `CLAUDE.md` = map, `README.md` = what's-in-this-folder, `docs/notes/` = why, `.claude/skills/` = how-to-task. One fact, one home — cross-link, never copy. When you add or remove a file in a folder, update that folder's `README.md`.

## Legacy context

- `docs/harness-context-v3.md` — an earlier brief written for an **Agent-SDK-based** research harness. Its decisions D1–D3 (build on SDK, billing path, orchestrator design) do **not** govern this project. But its pain-point analysis (§2, the 5/95 signal ratio) and feature sketches (§4 A–E: `report_finding` schema, dump-to-file diet, fork-vs-fresh policy, checkpointing, cache TTL) are still gold — they are the **spec source for Stage 3**.
- `archive/prompt/` — eight real prompts from months of research work (plan / run-overnight / summarize / compact / clean). They document the owner's actual workflow and its pain. Stage 3.2 turns them into structured templates.
