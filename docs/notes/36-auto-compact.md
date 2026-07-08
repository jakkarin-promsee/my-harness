# 36 — Auto-compact: the warning grows hands (2.27)

> Stage 2A, Tier 1 — the floor ([ROADMAP4.md](../ROADMAP4.md) §4). The 80 %
> warning has been shouting into the void since 2.5; now somebody acts on it.

## The problem (with the receipt)

`budget.py` warns at 80 % (`WARN_AT`) **and does nothing** — the human is
supposed to type `/compact`. On the 8K card the wall arrives mid-turn with
nobody watching; in a scripted or overnight run there is no human to type
anything. The window fills, the wire truncates or errors, the run degrades
silently. Robustness problem 1, ROADMAP4 §2.C.

Second receipt, found while wiring: `/compact` calls `budget.compact(model,
messages)` — but `/agent` switches rebind `agent.model` only, so after a
role pins a different provider, `/compact` summarizes on the **launch**
model, not the active one. The extraction below fixes both call sites onto
`agent.model`.

## What the seniors do

- **Claude Code**: auto-compacts as the context approaches the window, with
  a visible notice and an off-switch; the trigger leaves headroom rather
  than firing at 100 %.
- **gemini-cli**: `chatCompression` — a configurable threshold fraction of
  the model's window triggers compression of older history.
- **opencode**: autocompaction at a window threshold, announced.

Convergent shape: *threshold fraction of the window → compact automatically
→ tell the human → keep going.* Nobody compacts mid-turn; the seam is
between turns.

## What we build

- **`should_compact(estimate, window, threshold)` in `budget.py`** —
  `AUTO_COMPACT_AT = 0.85` default; windowless configs (window 0) and
  `threshold 0` (the off-switch) never fire. The knowledge lives next to the
  estimator and `WARN_AT` it extends.
- **One compact path in the REPL**: the `/compact` branch's
  compact-migrate-persist block extracts into a `run_compact()` closure;
  `/compact` calls it, and the **turn boundary** (after reflection, where
  the budget line prints) checks `should_compact` and calls it too —
  announced, headless-safe by construction (no prompt anywhere in the path).
  Turn-boundary-only is deliberate: mid-turn tool batches are in flight, and
  the boundary is the same natural seam reflection (note 32) already uses.
  Both call sites now use **`agent.model`** — the active model, fixing the
  stale-`model` bug above.
- **Per-provider override**: optional `auto_compact` key in `PROVIDERS`
  (a fraction; `0` disables). No entry ships one — 0.85 is right for the 8K
  card, and the Gemini lanes' 1M window makes the trigger unreachable there
  in practice (fine: the feature exists for the small window and for the
  genuinely long session).
- Stage 3.1 note: surgical ops will replace the *mechanism* (`compact`);
  the *trigger* (`should_compact` at the boundary) carries over unchanged.

Non-goals: mid-turn compaction (in-flight batches); compacting on a
schedule or message count (the window is the only budget that matters);
prompting the human first (the 80 % warning already was the prompt).

## The live discovery: 85 % is past the point of no return on the 8K card

The first live run (a crafted session at **est 7,058 = 86 %**) fired the
trigger perfectly — and the compact call itself came back **400:
`exceed_context_size_error`, 8,862 prompt tokens vs n_ctx 8,192.** Two
lessons, both with receipts:

1. **Summarize-and-replace must re-read the whole transcript** — so past a
   real ~100 % of the window it *cannot run at all*. A threshold meant to
   save the window has to fire while the save is still affordable.
2. **chars/4 under-estimates real tokens 25–65 % on this card** (est 7,058 →
   8,862 real; a later call: est 4,905 → 8,091 real — the gap includes the
   tool-schema array (~1.1k tokens) that rides every call but is invisible
   to the estimator, plus number-heavy text tokenizing fat).

Fix: per-lane override, exactly what the config key exists for — both ollama
lanes ship **`auto_compact: 0.6`** (estimated), which keeps the summarize
call itself inside the window. The Gemini lanes stay at the 0.85 default
(1M window; the corner doesn't exist there). Manual `/compact` typed past
the corner still 400s — the REPL survives it cleanly (error printed, session
intact), and Stage 3.1's surgical ops are the real cure: deletion doesn't
re-read anything.

## How we know it works

- **Offline** (`test_budget.py`): threshold boundaries — below/at/above,
  windowless never fires, `0` disables; the existing `compact` tests keep
  covering the mechanism.
- **Live (free lane), after the 0.6 fix:** a session crafted to est 4,881
  (59.88 %) did **not** fire on turn one — the boundary is exact — then
  crossed on turn two: `[auto-compact]` notice → the summarize call fit
  (6,201 in) → context **4,973 → 97 tokens (1 %)** → continued in a new
  session file with a faithful summary. The §5 overnight rehearsal re-proves
  it under `-p` at stage close.
