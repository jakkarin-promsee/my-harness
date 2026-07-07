# 26 — The thinking curve (2.20, a lab log like 2.15 — not a code feature)

> The owner's mystery: *"the more it think, the more it dump."* The
> overthinking literature says accuracy peaks at a modest trace length and
> then DECLINES; our own note-18 data agrees locally (thinking-qwen3: 10×
> tokens, worse score). This lab measures the curve on flash — then PINS
> defaults instead of leaving thinking to the model's appetite.

## Hypotheses — on record BEFORE the runs (red-team method)

- **H1** — flash's default hidden thinking doesn't help the *simple* task:
  M1 already passes 3/3 at every effort; the measurable harm is pure waste
  (32–144 hidden tokens/run at default for the same verdict). Curve expected
  flat in score, rising in cost.
- **H2** — the *hard* task (M3-guidebook, majority-FAIL 0–1/3 at default)
  genuinely benefits from `medium`+: more planning budget → the checklist of
  real commands survives to the end. (Weak prior from the note-22 probe
  anecdote: the trick question flipped right-with-thinking.)
- **H3** — part of the felt dumbness was never thinking at all but the terse
  voice — **already half-proven early**: 2.19's `explain` A/B flipped M2
  before any thinking knob moved.

## The grid (rescoped by red-team #3)

On **flash only** (the local workhorse cannot think; thinking-qwen3's
economics are already measured in note 18 — no local grid):

`--think off|low|medium|high` × {M1-page-eyes (simple), M3-guidebook (hard,
non-holdout)} × **N=3**, via `acceptance/run.py gemini-flash --suite museum
--task … --think …` (the runner grew `--think` in 2.19). The **default**
(nothing sent = flash's own appetite) column comes from the 2.17/2.18a
baselines already on file — no re-run.

**Cost estimate before running:** M3 dominates: 12 runs × ~60k in ≈ 720k in
(~$0.22) + ~12 × 4k out+think (~$0.12); M1's 12 runs ≈ 50k in total (~$0.02).
Estimate **≈ $0.40–0.60** for the grid. (Budget relaxed by the owner
2026-07-08 — recorded, not gating.) `high` carries a 24K thinking *budget*
per call; flash spends what it wants up to it, so the estimate assumes
observed spend, not budget ceilings.

## Results (2026-07-08) — the curve, N=3 per cell, `gemini-2.5-flash`

| Cell | M1 simple (score / out) | M3 hard (score / $/run / wall) | think tokens (total) |
|---|---|---|---|
| default (baseline runs) | 3/3 / ~80 | 0–1/3 / ~$0.024 / 46–65s | 32–144 per M1 run |
| **off** | 3/3 / 88 | **1/3** / $0.0189 / 22.7s | **0** |
| low | 3/3 / 125 | 0/3 / $0.0207 / 41.2s | 3,969 |
| medium | 3/3 / 130 | 0/3 / $0.0164 / 25.5s | 2,365 |
| high | 3/3 / 95 | 0/3 / $0.0123 / 41.8s | 2,024 |

Plan-shaped cell (I-agent-plan, flash, N=3 per arm): **off 3/3, $0.0053/run,
7.6s** vs medium 3/3, $0.0132/run, 18.6s — same score, 2.5× the price.

**Hypotheses, judged:**

- **H1 CONFIRMED** — the simple task is flat 3/3 at every effort; flash's
  default hidden thinking on it was pure waste.
- **H2 REFUTED** — the hard task does NOT benefit from budget at any level.
  Its failure is an *information* problem (the model doesn't know the
  commands it must document exist — 2.21/2.22's job), not a reasoning one.
  Best exhibit: at `high`, flash explored LESS (25k vs 42k input tokens) —
  thinking displaced acting, the overthinking literature's core finding live
  on our wire. The owner's instinct "may need even max effort" is answered
  with data: no, and it's slower and blinder.
- **H3 CONFIRMED EARLY** (2.19's A/B) — the *felt* dumbness was substantially
  voice: `explain` flipped M2 with zero thinking involved.

## Pinned defaults (measured, not guessed)

- **`gemini-flash` → `think: "off"`** in PROVIDERS — for every role: even
  planning passes 3/3 at off, 2.5× cheaper than medium. Flash's
  default-on thinking is an invisible tax the wire lets us decline.
  *Caveat recorded:* measured at today's task difficulty; if a future
  planning task fails at off and passes at medium, the plan role gets a
  frontmatter pin then (the mechanism exists).
- **`gemini` (flash-lite)** — no pin: the model doesn't think unless asked
  (probe, note 22); sending `none` would be a param for nothing.
- **ollama** — no pin: the workhorse can't think (note 18 owns the local
  economics: the thinking variant was 10× tokens for a worse score).
- Precedence wired: role frontmatter > provider pin > nothing; `/think` and
  `--think` override everything at runtime.
- CLAUDE.md's model-lessons line gains: flash thinks by default and it buys
  nothing at our task grain — pinned off, meter watches the derived count.

**Confirm run under the pins** (flash museum, N=3, think=off + explain voice):
**3/3 tasks majority-PASS — the first full-museum pass on any lane** (M1 3/3,
M2 2/3, M3 2/3; 0 think tokens total, $0.082). Honesty note: the off grid
cell scored M3 1/3 forty minutes earlier — M3 sits ON the majority boundary
(~33–67 % per N=3 sample), so the pin + voice get it to borderline, and
2.21/2.22 own making it robust. The museum baseline (1/3 tasks) → 3/3 under
the full 2.18–2.20 stack is the stage's story so far, told by the meter.
