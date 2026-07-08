# 39 — The two worlds: one character, two jobs (2.30)

> Stage 2A, Tier 2 — the mind ([ROADMAP4.md](../ROADMAP4.md) §4). The
> owner's problem 3, his words: *"separate between 2 worlds that is chat bot
> and working bot… making all prompt no contray each other. Pull it 100%
> potential."*

## The problem (with the receipt)

`prompts/system.md` line 1 welds *who the agent is* to *what it is doing*:
"You are a coding agent that OPERATES this computer." Every role inherits
the worker mission — and the only escape is `chill`'s `backbone: false`,
which throws away the safety line, the honesty rules and the style sections
along with the mission (`agents/chill.md`). The all-or-nothing opt-out is
the proof the weld is in the wrong place. Live receipt: museum M9 (note 38)
— small talk at the build agent gets *"I'm ready to help with any tasks you
have for me. I'm currently waiting for your instructions"* on flash (FAIL
1/3) and a bulleted troubleshooting menu on local.

## What the seniors do

- **opencode**: primary agents — `build` and `plan` are whole *worlds*
  (prompt + model + permissions), Tab-switched; one registry.
- **Anthropic**: claude.ai and Claude Code are the *same character* in
  different harnesses — identity is constant, the job wrapper changes.
  Claude Code's own guidance has the core insight in one line: *"when the
  user is describing a problem or thinking out loud, the deliverable is
  your assessment"* — not every message is a work order.
- **2C's own ladder** (note 24): tagged sections, one file, composed at
  assembly — the exact machinery this split rides; no new concepts.

## What we build

1. **A `world:` tag on backbone sections** — third axis after tier and
   voice: `core` (default — every world keeps it), `operator`, `companion`.
   `load_backbone(tier, voice, world)` selects core + the active world's
   sections; unknown world raises loudly (the tier precedent). The section
   file stays ONE file — no forked prompts to keep honest.
2. **The content split.** Core keeps: identity-of-character (rewritten to
   carry *who* — direct, concrete, honest — plus the role-section rule),
   the safety line, the style voices. Operator keeps: the mission ("you
   OPERATE this computer…"), the working loop, tool policy, failure
   protocol, verification, the FULL-tier worked example. New `companion`
   section (micro): a conversation, not a task — direct answers, real
   opinions, think out loud, **don't turn feelings into tickets** (no
   service menus, no "what task would you like"), and when the user
   actually wants computer work, offer `/work`.
3. **The one deliberate content addition (the M9 fix), and it lands in
   CORE, not the companion** — because M9's scenario is the owner chatting
   *without switching roles*: "Not every message is a task. When the user
   is just talking — feelings, opinions, how's-it-going — just talk;
   don't solicit work." The split itself is behavior-neutral for the
   operator; this line is the measured exception, and the museum decides it.
4. **Roles gain `world:` frontmatter** (default `operator`). `chill`
   migrates: `backbone: false` → `world: companion` — it finally keeps
   safety, honesty and style. `backbone: false` survives as the escape
   hatch for exotic roles.
5. **Companion assembly stays lean:** env block yes; orientation snapshot,
   AGENTS.md rules and skills lines are operator furniture — they re-invite
   the work register a chat world exists to shed.
6. **`/chat` and `/work`** — one-word switches, pure aliases for
   `/agent chill` / `/agent build` (the existing role lifecycle does the
   rest: new session file, mode switch, prompt swap).

Non-goals: auto world-detection (ROADMAP4 §6 — a misroute is worse than a
keystroke); a third world (reviewer/plan are roles *within* the operator
world — world = register, role = job); moving 2.32's evidence-beats-
agreement rules (next cycle, one feature at a time — but the core identity
is written so 2.32 extends it naturally).

## How we know it works

- **Offline:** world selection tests (companion excludes loop/tools,
  operator excludes companion, core rides both, default = operator,
  unknown world raises); `world:` frontmatter parsing; the measured MICRO
  operator budget stays within the 8K arithmetic (note 24).
- **Live:** M9 must move on flash (baseline FAIL 1/3); the rest of the
  museum wing must hold (M5–M8 non-regression); the core gate stays green
  on the regression lane (flash-lite + local). A manual `/chat` session
  reads like a person; `/work` reads like today.

## Results (2026-07-08)

- **Offline:** 223 tests (was 218) — world selection, furniture gating,
  frontmatter, the exact section/tier/world map; the MICRO operator budget
  stayed inside its 450-token cap after the identity split (+~60 est tokens
  for the core character + just-talk line).
- **The movement check (flash, N=3): M9 rough-day 1/3 → 3/3.** The core
  "not every message is a task" line retired the work-robot register on the
  primary lane. Non-regression: M8 3/3 (unchanged), M5 2/3 (= baseline),
  M6 2/3 (baseline 3/3 — one N=3 flake, majority holds), M7 1/3 (unchanged
  — the cave is 2.32's target, deliberately untouched).
- **Operator neutrality:** flash-lite core **15/15**; local core: see below.

## The E-exact-edit regression — first position is load-bearing (the fix)

The first local core run after the split came back **14/15, E-exact-edit
0/3 on re-measure**: the agent hunted `acceptance_scratch.py` under
`acceptance/`, had glob HAND it the right root path, re-read the wrong path
anyway, and *gave up with a report instead of acting*. Root cause (isolated
by A/B on the prompt): the split had moved the mission off the opening
slot — character first, "OPERATES this computer… go get it, make it and
prove it" second — and put a "not every message is a task" conditional in
front. On a 4B at MICRO that combination measurably weakens action drive.
The 2C lesson, one layer deeper: **first-position wording is load-bearing.**

Fix, scoped by measurement: (a) **mission first in file order** — the
operator world opens action-first again, verbatim the pre-2.30 first
sentence; the companion world has no mission, so it opens with identity;
(b) **the just-talk line moves to the `standard`-tier identity** (same-name
replacement) — flash's tier, where the M9 register actually lived; MICRO
stays lean, and local M9 was already majority-passing without the line.
Result: **E 0/3 → 3/3**; the standard-tier text flash sees keeps the
just-talk line (M9's fix intact — live flash re-check queued behind the
problem.md #3 key restoration).

## The other incident: the gate agent deleted the repo root (problem.md #3)

The first post-split local core run's agent, auto-approved in the real repo
root, executed a destructive shell command mid-run: every root file deleted
— tracked ones restored from git within minutes; **`.env` (the Gemini key)
and the run logs were not restorable**. The runner's gate now wraps a
tripwire (`acceptance/run.py`: wildcard deletes, `git clean`, `format`
blocked even under auto-approve, unit-tested); the real fix — sandboxed
gate cwd or argument-level shell policy — is the owner's call, recorded
with the re-key instructions in problem.md #3. Quality-lane work (flash
museum re-checks, 2.31/2.32 baselines) is blocked until the key returns.
- **The companion, felt:** headless `--agent chill -p` on local qwen —
  *"Damn, yeah — that's rough… Or we can just talk through it like old
  friends. Your call."* versus the baseline's bulleted service menu. Three
  features stacked in one command (2.28 `-p` + 2.11 roles + 2.30 worlds).
- **Local core gate (post mission-first fix):** 13/15 single-pass, then the
  N=3 rule on both misses: **I-agent-plan 3/3** (the documented problem.md
  #2 flake, cleared) and **D-grep 0/3 → 1/1 intermittent** — diagnosed as
  *environment drift, not the split*: Tier 1's meter code added `totals`
  bait to repl.py, so a bare-`total` grep now drowns where `def total`
  still wins in one hit (watched live, identical prompt). Recorded under
  problem.md #2's flake ledger; E 3/3 in-suite confirms the operator
  neutrality that matters. Verdict: local operator neutrality holds, D
  flagged as decayed task discrimination.
