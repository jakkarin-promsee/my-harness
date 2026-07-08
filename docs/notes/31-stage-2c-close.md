# 31 — Stage 2C close: the before/after (the stage's claim, reduced to numbers)

> ROADMAP3's thesis was that the plumbing was frontier-shaped but the agent
> was still *"a chatbot that can see my computer, not one that can control
> it"* — and that the missing strength was internal: the prompt, the shape of
> tool results, the model's sense of where it is and what it was doing.
> Nine cycles later (notes 22–30, all shipped 2026-07-08), this note is the
> §5 exit gate: the museum's verdicts, the hold-out's one and only run, and
> the before/after table. Everything measured on `gemini-2.5-flash`
> (quality) / `gemini-2.5-flash-lite` + `qwen3:4b-instruct` (regression),
> N=3 majority where it decides anything.

## What the stage shipped (one line each)

1. **2.17** — the failure museum (real failed asks from `sessions/`, one
   hold-out never touched) + the wire probes + the two-lane wiring.
2. **2.18a** — the backbone: six-section system prompt; roles extend it;
   *"keep answers short"* died.
3. **2.18b** — the ladder: MICRO 264 / COMPACT 580 / STANDARD 660 / FULL 854
   tokens from one file; `/prompt`; spawn-time assembly.
4. **2.19** — voice (`explain` = Gemini default; flipped M2) & effort
   (`off` → `reasoning_effort:"none"`, proven); the derived thinking meter.
5. **2.20** — the thinking-curve lab: H1 ✓, H2 ✗ (budget never moved the
   hard task — information problem, not reasoning), H3 ✓; flash pinned
   `think: off` from measured cells.
6. **2.21a** — read_file grew eyes: framed, numbered, pageable; the paging +
   poisoned-file tasks; per-provider tool diet.
7. **2.21b** — every observation framed (no raw JSON anywhere); descriptions
   teach workflow.
8. **2.22** — the orientation map: flash's orientation task 2/3→3/3 at HALF
   the tokens.
9. **2.23** — attention anchors (with the wording lesson: an anchor that
   reads as a reprimand is worse than none).

## The exit gate (2026-07-08, logs `close-*.log`)

| Lane | Suite | Result | Tokens / $ |
|---|---|---|---|
| **flash** (STANDARD, voice=explain, think=off) | core 14 | **14/14** | 154k in / $0.056 |
| **flash** | museum N=3 | **3/3 tasks** — M1 3/3, M2 3/3, M3 2/3 | 292k in / $0.125 |
| flash-lite (STANDARD, explain) | core 14 | 13/14 — I failed (the known coin-flip, problem.md #2; K passed this round) | 265k in / $0.029 |
| local qwen3 (MICRO, normal) | core 14 | 13/14 single-run; the miss (E-exact-edit) re-ran **2/3 majority-PASS** — 4B variance, not regression | 153k in / $0 |

**§5 criterion — "the museum moves":** the 2.17 baseline failures were M2
(0/3) and M3 (0/3) on flash. At close: **both majority-pass — 2/2 = 100 %**,
against the required ≥ half. Every remaining single-run failure has a
written, honest attribution (I/K = lite model limit; E = 4B variance; M3's
one miss = the boundary case that 3.1's surgery should finish).

## The hold-out speaks once (red-team #13)

**M4-holdout-archaeology, first and only runs, flash N=3: PASS 3/3**
(~20k in / $0.0098 per run). The task no tuning loop ever saw — find the
fizzbuzz verifier, quote what it checks, explain why lowercase passes —
solved cleanly all three times. This is the stage's only unoverfittable
number, and it agrees with the tuned ones.

## Before → after

| Measure | 2.17 baseline (before) | Stage close (after) |
|---|---|---|
| Museum, flash majority | **1/3 tasks** (M1 ✓, M2 0/3, M3 0/3) | **3/3 tasks** (M1 3/3, M2 3/3, M3 2/3) + hold-out 3/3 |
| Museum, local majority | 1/3 tasks (M2 0/3 → flipped 3/3 already at 2.18a) | 2/3 tasks at 2.18a; M3 stays hard on 4B |
| Core gate | 11 tasks | **14 tasks** (+paging, poisoned-file, orientation) |
| Offline tests | 136 | **179** |
| System prompt | 14 lines, ~250 tok, one voice, "keep answers short" | 6 sections × 4 tiers × 3 voices, 264–854 tok, per-provider defaults |
| Flash hidden thinking | always on, invisible (163 tok on a 44-tok ask) | pinned `off` (measured: bought nothing); derivable in the meter |
| Tool observations | bare strings, JSON arrays, no retrieval path | framed, numbered, pageable, teaching |
| Orientation | none (blind list_dir-flail) | tier-sized map: −50 % tokens on the orientation task (flash) |
| In-session focus | none (agents answered "hi" 20 calls deep, live) | anchors after K=8 quiet steps, meta-tagged for 3.1 |

## Honest remainders

- **K + I on flash-lite**: coin-flips under N=3 on both prompt eras — model
  limit, owner's call recorded in problem.md #2 (accept known-flaky or move
  role tasks to flash).
- **M3 on flash hovers 2/3–3/3** across samples — majority holds, but it is
  the museum's boundary case; 3.1's context surgery is its likely finisher.
- **Voice/effort have no dedicated gate task**: their acceptance was the
  measured A/Bs (notes 25–26), and both knobs ride every gemini gate run as
  defaults (`voice: explain`, `think: off`). Recorded as a §5 deviation.
- The Anthropic adapter stays live-untested (problem.md #1); the Ollama tray
  still wants its reboot (problem.md #0, one stall observed today).
