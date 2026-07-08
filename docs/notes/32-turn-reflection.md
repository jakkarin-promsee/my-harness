# Note 32 — turn reflection (a meta-model distills each turn into context)

*Play-lane prototype, 2026-07-08. Status: experimental, scoped to `ollama-think`.*

## The problem

Watching `qwen3:4b` (the thinking lane, note added same day) is fun, but it
reasons out loud for **hundreds of tokens per step** — 269 tokens to answer
"Hi". Most of that is the model litigating its own system prompt (*"but wait,
the instructions say…"*). Two things pile up in a session:

1. The **reasoning** is thrown away entirely — the adapter strips `thinking`
   before the message enters context (note 11 / 03). So the *what/where/why*
   the owner wanted to persist (his very first instinct this session) is lost.
2. The **tool churn** that *does* persist — `assistant(tool_calls)` +
   `tool` results, turn after turn — is verbose and rarely re-read in full.

## What the seniors do

Summarize-and-replace is how everyone ships context management: Claude Code's
auto-compaction, MemGPT's recursive summary, aider's chat-history summarizer.
The twist here is **who** does it: aider splits work across a strong *architect*
model and a cheap *editor* model. We apply the same split to **memory** — the
verbose thinker acts; a fast, non-thinking *distiller* remembers.

## What we built

At the moment the agent goes idle ("ready for the next prompt"), if the turn
used any tools, a second model — `qwen3:4b-instruct`, fast and silent —
distills the finished turn into a few terse lines and we **replace the turn's
churn with that recap**, keeping the user's message. Rolling compaction, one
turn at a time.

- `core/reflect.py` — `render_turn` (pure: messages → transcript) and
  `summarize_turn` (injected model → recap text). No loop changes; the loop
  stays pure (invariant 1). Orchestration lives in the REPL, after `run_turn`.
- `cli/repl.py` — a `reflect` provider key names the distiller; only
  `ollama-think` sets it, so the workhorse and flash are untouched. The recap
  is an `assistant` message tagged `meta:"recap"` (adapters scrub the tag;
  unlike anchors it *survives* resume — it is real memory, not protocol).

## How we know it works

- Offline: `tests/test_reflect.py` pins `render_turn` (skips anchors, flattens
  results) and `summarize_turn` (drives a FakeModel, zero tokens).
- Live: the `[reflect] … context ~X -> ~Y tok` line shows the shrink, and the
  `[context]` budget line after it drops turn over turn instead of climbing.

## Honest limits (why it's a prototype, not a stage)

- **Lossy** — same disease as `budget.compact`: a bad recap silently drops
  signal. Not yet measured against a task suite (Stage 3.1's job).
- **Disk divergence** — the JSONL is append-only, so `--resume` replays the
  *full* (uncompacted) turn; only the live, in-memory context is compacted.
- **The final answer** to the user leaves context (the recap carries its gist;
  the user already saw it live). Fine for grounding, wrong if a later turn
  needs the verbatim answer.

This is Stage-3-flavored and, if it graduates, earns a real design note +
acceptance run. For now: a toy that makes the token meter go *down*. 😄
