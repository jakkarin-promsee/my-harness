# 30 — Attention anchors: don't lose the plot (2.23)

> The honest core of the owner's "RAG for its own history" (ROADMAP3 §1):
> in-session *focus*, not retrieval. The live sessions show the shape — an
> agent twenty tool calls deep answering "hi" as if nothing happened
> (`20260707-004701`), M3 runs burning 90k tokens wandering away from the
> checklist they never wrote. Claude Code's fix is the system-reminder
> pattern: small, structural, injected when attention has drifted.

## What we build (minimum viable version, red-team #14 lifecycle up front)

**The re-anchoring rule, in the loop:** after K consecutive tool steps with
no `todo_write` activity (K = `anchor_after`, default 5, per-provider
override), inject ONE compact reminder before the next model call:

    (Attention check - N tool steps without touching the plan.
    The original request: "..."
    Current plan: <todo snapshot | "no todo list written">
    If you are on track, continue; if you have drifted, return to the request.)

- **Anchors are ordinary user-role messages with `meta: "anchor"`.** The
  2.9c steering finding says user-role text steers hardest; the tag makes
  them *protocol, not signal* — the first live application of the
  distinction Stage 3.1 generalizes.
- **One live anchor at a time:** injecting a new one deletes the old from
  the in-memory list (the loop emits `[anchor]` so it's visible). The JSONL
  stays append-only — every anchor was persisted when it existed; on
  `--resume`, `session.prune_stale_anchors` keeps only the last (replay
  reconstructs the same view).
- **Adapters scrub `meta` before the wire** — all three (strict endpoints
  400 on unknown fields; today's adapters send messages near-verbatim, so
  the scrub is part of this feature).
- **`/compact` drops anchors entirely** before summarizing (protocol, not
  signal — they must not pollute the summary).
- **The todo snapshot** comes from `make_todo_tool`, which now returns
  `(fn, schema, snapshot)` — the plan state lives in one closure, one home.

## How we know it works

1. FakeModel tests: anchor appears after K quiet steps with the original
   request + plan state; `todo_write` resets the counter; a second anchor
   replaces the first (one live anchor); adapters scrub `meta`; `/compact`
   drops anchors; `prune_stale_anchors` keeps the last only.
2. **Before/after on the longest non-holdout museum task (M3-guidebook),
   N=3 on flash**: the freshest pre-2.23 sample (2.21b gate: 2/3 at
   ~105,580 in/run) is the *before*; the *after* runs under anchors.
   Completion + token burn recorded. Core gates green on the regression
   lane.

## Results (2026-07-08) — including the failure that taught the wording

**First attempt (K=5, "Attention check - N steps without touching the
plan... if you have drifted...") made M3 WORSE: 0/3** (before: 2/3). The
transcripts showed three distinct failure modes, all caused by the anchor
itself: (1) the model *replied to the reminder* instead of working ("I am
confident I am on track..." — a wasted turn); (2) an anchor mid-exploration
triggered an empty reply and the run died with no file written; (3) the
model read the anchor as a REPRIMAND — *"You are absolutely right. My
apologies."* — dropped its momentum and replanned from scratch, burning 110k
tokens. And K=5 fires during *healthy* deep exploration, which is exactly
what M3 needs.

**The fix, copied from how Claude Code's system-reminders actually read:**
ambient, not accusatory; explicitly "not user feedback, do not reply to it
or change course because of it"; K default 8. **Re-run: M3 2/3 majority-PASS
with anchors firing** — back to the pre-anchor level, with the insurance
still armed for genuinely drifting sessions. The 2.9c steering effect cuts
both ways: user-role text steers HARD, so protocol text must say what it is.

- **179 offline tests green**: anchor after K quiet steps (ask + plan in the
  text), todo_write resets the clock, one live anchor (replacement), all
  three adapters scrub/omit `meta`, `/compact` drops anchors,
  `prune_stale_anchors` keeps only the last on resume.
- **Core gates: flash-lite 14/14** (ran WITH anchors armed); local 13/14
  where the one failure was a 695s Ollama ReadTimeout on I (environmental —
  problem.md #0's wedged-server territory; I re-ran PASS immediately after).
- The `meta` tag is live: 2C creates clean context, Stage 3.1 deletes dirty
  context — the handshake exists now.
