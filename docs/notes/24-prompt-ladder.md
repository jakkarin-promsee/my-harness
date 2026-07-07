# 24 — The ladder: four power levels over one backbone (2.18b)

> The stage's one declared adaptation (ROADMAP3 §3.1, red-team #8): nobody
> ships a token-budget ladder — opencode forks per-model *files*, Claude Code
> assembles *conditional fragments*. Our constraint is one they don't have:
> one prompt serving a 1M window (Gemini) and an 8K window (this card).
> Approved by the owner 2026-07-08 as part of the ROADMAP3 approval.

## What we copy vs what we synthesize

Copied mechanisms: *tagged sections assembled conditionally* (Claude Code's
fragment assembly) + *per-model variation* (opencode's per-model prompts).
The synthesis: the condition is a **tier budget**, not a feature flag or a
model family. Compose at assembly time; never fork four files — a forked
prompt is four prompts to keep honest (§3.1's design consequence).

## The tiers

| Tier | Sections | Budget (whole-first-call, red-team #10) | Default for |
|---|---|---|---|
| `MICRO` | identity + **brief** loop + safety + style | ≤ ~2,000 total → backbone slice ≤ ~400 | ollama (8K card) |
| `COMPACT` | + tools, failure, verification (brief loop) | backbone ≤ ~1,200 | (subagents later, small models with room) |
| `STANDARD` | + the **full** loop protocol | backbone ≤ ~4,000 | gemini lanes — the primary's default |
| `FULL` | + worked example | unbounded | Gemini at max scaffolding, on demand |

The 8K arithmetic that forces MICRO (from ROADMAP3 2.18b, re-measured at
2.18a): 8,192 − 4,096 `num_predict` reserve ≈ 4,100 inbound; fixed overhead
(schemas ~750 + spawn/todo ~180 + AGENTS.md ~175 + skills lines) ≈ ~1,200
before the backbone says a word. A 636-token STANDARD backbone leaves ~2,000
for the user and history — MICRO at ≤ ~400 buys the difference back.

**Mechanics** (in `context.py`): tier tags already ride the section markers
(2.18a wrote them; today they're read). Selection: a section is included when
its tag ≤ the active tier. **Same-name sections replace**: `loop` exists at
`micro` (one line, *including the Skills-list check* — local runs MICRO and
must keep passing task K) and at `standard` (the full protocol); the highest
applicable wins. That keeps every tier's text in ONE file with zero
duplication and no forked copies.

## Selection & lifecycle (red-team #14)

- **Per-provider default** in the registry: `ollama → micro`, gemini lanes →
  `standard` (anthropic `standard`, untested as ever).
- **Per-agent override**: `tier:` frontmatter key (an agent that needs FULL
  scaffolding can pin it).
- **Runtime**: `/prompt` shows the active tier + each tier's measured backbone
  cost; `/prompt <tier>` switches — following the `/agent` precedent: swap
  `messages[0]`, continue in a NEW session file so `--resume` stays truthful.
- **Subagents assemble at SPAWN time**: `make_spawn_tool` learns to accept
  callables for `system_prompt`/`agent_prompts` values (strings still work —
  the tests' API survives); the REPL passes closures over the live tier, so a
  child spawned after `/prompt micro` feels it. `/compact`'s summary rides
  whatever tier is active — nothing to build, that's just what assembly does.

## How we know it works

1. FakeModel tests: tier selection per tier (micro excludes tools/failure/
   verification; standard's full loop **replaces** micro's brief one; only
   full includes the example); micro backbone ≤ 450 est tokens (the budget as
   a regression test); `tier:` frontmatter parsed; spawn-time assembly proven
   by swapping the callable's result between construction and spawn.
2. Gate: core 11 green on **local at MICRO** (the tier actually shipping
   there) and **flash-lite at STANDARD** (regression lane; K's known
   flakiness stands recorded — problem.md #2).
3. Each tier's measured backbone + assembled sizes recorded below; `/prompt`
   shows them live.

## Results (2026-07-08)

Measured with `estimate_tokens` (also live behind `/prompt`):

| Tier | Backbone | `build` assembled (env+AGENTS+skills) | Budget | Verdict |
|---|---|---|---|---|
| micro | **264** | 599 | slice ≤ ~400 | ✓ — whole-first-call ≈ 1.5k on the 8K card |
| compact | 580 | 914 | ≤ ~1,200 | ✓ |
| standard | 660 | 994 | ≤ ~4,000 | ✓ |
| full | 854 | 1,189 | unbounded | worked example costs ~194 |

- 156 offline tests green — tier selection, same-name replacement (standard's
  loop replaces micro's one-liner), FULL-only example, the micro budget as a
  regression test, `tier:` frontmatter, spawn-time assembly (a child spawned
  after a switch sees the new prompt).
- **Gate: local core 11/11 at MICRO** — the 264-token backbone carries the
  whole suite, including K's skill trigger (the micro loop one-liner keeps
  the Skills-check step on purpose). **Flash-lite at STANDARD: 9/11 → 10/11
  after one fix.** K stays known-fragile (problem.md #2, unchanged). I-agent-
  plan regressed to 1/3 (the backbone's operator identity overpowered the
  slim role body — flash-lite tried to WRITE the tool it was asked to plan,
  burning 49.8k tokens/run wandering); hardening the role body (prohibition
  + deliverable as numbered rules at the top, "calling write_file is failing
  the task") flipped it to 2/3 majority-PASS at half the tokens (23.5k), and
  local still passes it. Lesson for the dialect notes: on small models, a
  role that *contradicts* the backbone must shout, not whisper.
