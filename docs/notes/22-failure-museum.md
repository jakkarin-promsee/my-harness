# 22 — The failure museum + the wiring baseline (2.17)

> Stage 2C's entry step (ROADMAP3 §4). The gate says 11/11 while the owner's live
> sessions say "a chatbot that can see my computer, not one that can control it."
> When the benchmark and the experience disagree, the benchmark is too small.
> This feature makes the disagreement measurable — **no museum, no stage.**

## What the seniors do

Every mature harness turns field failures into fixtures: SWE-bench froze real
GitHub issues; Claude Code's eval suites grew from bug reports; our own
`archive/mvp/ACCEPTANCE.md` was born the same way (Stage 1's three tasks were
that day's real asks). The pattern to copy is *regression tests mined from
reality, with a hold-out nobody tunes against* (standard ML hygiene, red-team #13).

## The museum — mined from `sessions/` (47 transcripts, 2026-07-06 → 07-07)

Triage order per the **debug-live** skill: verifier → harness → config → model.
Each exhibit records who was actually at fault before blaming the model.

| ID | From sessions | What happened live | Triage verdict |
|---|---|---|---|
| `M1-page-eyes` (simple) | `072833`, `073246`, `073530` | "Can you see this page? \<url\>" → *"I can't browse websites"* — even though `web_fetch` shipped in 2.13. In `073530` the model called web_fetch once, then still claimed it couldn't access pages | Shared: pre-2.13 sessions genuinely had no tool (ours); post-2.13 the model doesn't know its own senses — tool descriptions don't teach (2.21b), backbone doesn't say "you operate" (2.18a) |
| `M2-orient-summary` | `234230`, `053822`, `073917` | "Explore the project and tell me what it's about" → agent walks 3–4 dirs, lands in `archive/mvp/fixtures/stats.py`, and reports *the planted bug* as what the project is | Mostly harness: no orientation map (2.22), `list_dir` gives bare names with no hint where to descend (2.21b); the model wanders into the basement and reports the furnace |
| `M3-guidebook` (long, multi-step) | `144442`, `144739`, `145030` | "Write docs/guide-book.md with all detail how to use this agent on the terminal" → produced generic filler: not one slash command, no modes, no `--resume`; two earlier attempts died producing nothing | Model + prompt: it never verified its claims against the code (`no verification rule` — 2.18a), and "keep answers short" (system.md line 11) actively pushes toward thin output (2.19). The live artifact is frozen as `acceptance/museum/guide-book-live-20260707.md` |
| `M4-holdout-archaeology` (**HOLD-OUT**) | pattern from `C`/`D`-style asks | Investigation task: "The acceptance suite has a fizzbuzz task. Find which file defines its verifier, quote what it checks, and explain why lowercase output passes." | **Never run until stage close** (red-team #13). No baseline, no tuning contact, no per-feature acceptance. Runs N=3 exactly once, at §5, reported whatever it says |

Curation rules honored: one *simple* task (M1 — where overthinking/refusal hurts),
one *long multi-step* (M3 — where the agent wanders), one hold-out (M4).
Also mined but **not** frozen: "search the web for X" (`072833`) — there is no
search tool by design (parked in 2.13; MCP deferred), so it would be an unfair
fixture; and the `17*23` thinking-leak (`042330`) — already diagnosed in note 18,
belongs to the 2.20 lab, not the museum.

## The wiring (red-team #1: pin the model before measuring anything)

- **`gemini-flash` provider entry** (`gemini-2.5-flash`, quality lane) joins the
  registry; `gemini` stays `gemini-2.5-flash-lite` (regression lane). Every
  number in Stage 2C records which lane it came from. `max_tokens` 8192 on
  flash: its *default hidden thinking bills as completion tokens* — 2000 would
  be thinking-death (the note-11 lesson, paid edition).
- **Probes** (red-team #4), in `archive/labs/03_reasoning_effort_probe.py`
  (one deliberate cheap run, results recorded below and consumed by 2.19):
  - (a) does `reasoning_effort: "none"` disable flash's default thinking on the
    OpenAI-compat wire?
  - (b) does usage expose a thinking split (`completion_tokens_details`)?
    What does Ollama's native wire report?

## The runner grows three flags (`acceptance/run.py`)

- `--suite core|museum|all` — per-provider task lists become explicit (§5's
  asymmetry: local runs core, gemini lanes run everything).
- `--n N` — repetition; every verdict that decides anything is majority-of-3
  (red-team #12), variance recorded.
- `--task ID` — one task, for debugging.
- Per-run stats: pass/fail, tokens in/out, wall-clock, **$ estimate** from a
  `PRICES` table (flash $0.30/$2.50 per M in/out, flash-lite $0.10/$0.40 —
  as configured 2026-07-08; the meter labels them estimates). Museum tasks
  live in `acceptance/museum.py`; the hold-out is skipped unless
  `--include-holdout` is passed (it prints a warning when it is).

## How we know it works

1. 136 offline tests stay green; new offline tests cover the museum verifiers
   (pure functions — e.g. the frozen live guidebook artifact must FAIL
   `verify_guidebook`, proving the verifier catches the real failure).
2. Probe results recorded in this note (below), feeding 2.19's design.
3. Baseline table (below): M1–M3, N=3, quality lane + local, with $/run.
   M4 stays untouched — its first run is at stage close.

## Probe results (2026-07-08, live wire — `archive/labs/03_reasoning_effort_probe.py`)

| Call | completion | prompt | total | hidden thinking |
|---|---|---|---|---|
| flash, no effort sent | 2 | 44 | **209** | **163** |
| flash, `reasoning_effort: "none"` | 2 | 44 | 46 | **0** |
| flash, `reasoning_effort: "low"` | 2 | 44 | 195 | 149 |
| flash-lite, no effort sent | 2 | 44 | 46 | 0 |

- **(a) CONFIRMED:** `"none"` disables flash's default thinking on the
  OpenAI-compat wire. Flash *does* think by default (163 hidden tokens on a
  44-token prompt); flash-lite doesn't. Both Google-docs claims hold on our wire.
- **(b) NO usage split** — no `completion_tokens_details` on this wire. But the
  split is **derivable exactly**: `thinking = total − prompt − completion`
  (thinking tokens appear *only* in `total_tokens`). Better than expected:
  2.19's meter can show a per-call number labeled *derived*, not estimated.
  Ollama native reports `prompt_eval_count`/`eval_count` only — totals, no
  split, honestly labeled (as predicted).
- **Billing consequence:** thinking bills as output, so $ math must price
  `out + thinking` at the output rate — the runner's `dollars()` does.
- Anecdote for 2.20 (N=1, not data): the trick question was answered right
  with thinking on (27), wrong with `"none"` (26), wrong by lite (18) —
  the first live hint of H2 (hard tasks genuinely benefit from budget).

## Baseline (2026-07-08) — the numbers 2C must move

N=3 per task, majority verdict; hold-out M4 untouched (zero runs, as designed).
Quality lane = `gemini-2.5-flash`; local = `qwen3:4b-instruct` (every number's
model ID recorded per red-team #1). Logs: `acceptance-*-museum-baseline.log`.

| Task | flash (majority) | flash mean tok (in / out+think) | flash $/run | local (majority) | local mean tok / wall |
|---|---|---|---|---|---|
| M1-page-eyes | **PASS 3/3** | 3,058 / 80 | ~$0.0011 | **PASS 3/3** | 3,630 / 102 · 12.6s |
| M2-orient-summary | **FAIL 0/3** — 3/5 fact groups every run | 7,351 / 558 | ~$0.0036 | **FAIL 0/3** — 2–3/5 groups | 1,784 / 194 · 16.0s |
| M3-guidebook | **FAIL 0/3** — 2–3/7 real commands | 55,048 / 2,784 | ~$0.0235 | **FAIL 1/3** — 1–2/7, one lucky 4/7 | 18,952 / 924 · 120.8s |
| M4-holdout | — no runs until stage close — | | | — | |

Reading the failures (debug-live triage before blaming the model):

- **M1 passes on flash AND local today** — the live "I can't browse" failures
  were mostly *pre-2.13* (no tool existed). With eyes installed, both models
  use them. Kept in the museum as a cheap canary: it re-fails if descriptions
  or the backbone regress.
- **M2 fails in the opposite direction from the live sessions**: local wandered
  into the `stats.py` basement; flash *skims* — it read `README.md`, called that
  "exploring", and compressed the loop/tools out of its summary. Both are
  orientation failures; `keep answers short` (system.md) is an accomplice.
  Feature owners: 2.22 (a map invites real exploration), 2.18a (verification:
  "explore" ≠ one file), 2.19 (voice).
- **M3 reproduces the live failure exactly**: 2–3 of 7 real commands, every
  run — the same generic filler as the frozen exhibit (which scores 1/7).
  Run 3 burned 92k input tokens wandering and still missed. Feature owners:
  2.18a (verify against the code before writing), 2.22 (know where repl.py
  lives), 2.23 (don't lose the checklist mid-flight).
- **$-per-museum-run on the quality lane: ~$0.03** for the three tasks
  (~$0.085 for the N=3 baseline). At these prices the two-lane discipline is
  about habit, not survival — the owner relaxed the budget 2026-07-08, and
  the meter keeps the receipts anyway.
- **Local mirrors the shape, cheaper and slower**: M2's mean input of 1,784
  tokens says the 4B model barely explored at all before "summarizing"; M3's
  one lucky pass (r3: 4/7) out of three is exactly why single-run verdicts
  were banned (red-team #12) — N=1 would have called this task solved.
