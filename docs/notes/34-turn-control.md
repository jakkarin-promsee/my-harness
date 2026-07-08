# 34 — Turn control: interrupt, steer, repair (2.25)

> Stage 2A, Tier 1 — the floor ([ROADMAP4.md](../ROADMAP4.md) §4). The first
> run-robustness cycle: Ctrl+C stops the *turn*, not the *harness*.

## The problem (with the receipt)

`KeyboardInterrupt` is caught in exactly one place — around `input()` at the
`you>` prompt (`repl.py`). During a turn it is caught nowhere: Ctrl+C in a
20-step tool chain propagates out of `run_turn`, out of `main()`, and kills
the process. The paid-lane runaway has no off switch short of murder, and the
murder leaves a corpse: an assistant message carrying `tool_calls` with no
`role:"tool"` answers. Strict OpenAI-style wires reject exactly that shape on
the next POST ("an assistant message with 'tool_calls' must be followed by
tool messages responding to each 'tool_call_id'") — our own loop already
documents the poisoning in its length-cut path (`loop.py`, "an unanswered
tool_call poisons strict OpenAI-style history"). So the crash-recovery path
(`--resume` — the whole point of per-message JSONL) can hand the wire a
400-ing transcript. Ability problem 1, ROADMAP4 §2.D, both rows.

## What the seniors do

- **Claude Code**: Esc interrupts the running turn; the session survives and
  the next user message steers. On the wire, every `tool_use` block must be
  answered, so an interrupted turn gets **synthesized tool results** ("Request
  interrupted by user") — the transcript stays valid without rewriting
  history. Resume of a crashed session repairs the same way.
- **aider**: Ctrl+C once interrupts the streaming reply and returns to the
  prompt ("^C again to exit"); a second within the window exits.
- **Codex CLI**: Ctrl+C interrupts the running task; the session continues;
  quitting is a separate, deliberate gesture.

The convergent design: **interrupt = steer** (stop the turn, keep the
session, let the human redirect), and **repair = synthesize, never rewrite**
(the JSONL stays append-only; the fix is an *addition*).

## What we build

1. **`repair_dangling_calls(messages)` in `core/session.py`** (sibling of
   `prune_stale_anchors` — same "transcript hygiene at the seams" family).
   Find the last assistant message carrying `tool_calls`; collect the
   `tool_call_id`s of the `role:"tool"` messages after it; for every
   unanswered id, append a synthesized result: *"(interrupted by user — this
   tool call was cancelled; it may not have run. Do not assume it did.)"*
   Pure, in-place, idempotent; returns the synthesized messages so callers
   can persist them. Conservative guard: if anything **other than** tool
   answers follows the batch, the history isn't an interrupt shape — return
   `[]` and touch nothing (repairing a foreign tail would insert results
   after a user message: invalid ordering, and not our corpse).
2. **REPL: catch at the turn boundary** (the loop stays pure — `_execute`'s
   error-to-text net catches `Exception`, and `KeyboardInterrupt` is a
   `BaseException`, so it already escapes; two new loop tests pin that
   contract). `run_turn` gains a `KeyboardInterrupt` arm next to the existing
   `RequestException` arm: close the half-printed stream line (the printer's
   `end` event — otherwise the notice lands mid-dim-text and the printer's
   mode state goes stale), repair, persist the synthesized messages, print
   `[interrupted] turn stopped — the session is intact; tell me how to
   proceed`, and skip reflection (`turn_ok = False`). Works for interrupts
   during the model call (no dangle — repair no-ops), during tool execution
   (the dangle case), and at the y/N gate prompt (input() raises there too —
   today that also kills the process).
3. **`--resume` repairs on load**, right after `prune_stale_anchors`: the
   synthesized results append to the same JSONL (append-only stays true — the
   repair is recorded, not implied), with a one-line notice.
4. **A small belt on `/compact`**: Ctrl+C during the summary call cancels the
   compact ("context unchanged") instead of killing the process.

Non-goals, recorded: aider's "^C again to exit" ladder (Ctrl+C at the `you>`
prompt keeps meaning exit — one user, existing muscle memory); mid-turn
message *queueing* (Claude Code's steer-while-running — needs threaded input,
teaches nothing about the loop); scripted CTRL_C_EVENT injection on Windows
for the live test (flaky console-group semantics — the manual check covers it).

## How we know it works

- **Offline (the primitive + the contract):** repair synthesizes exactly the
  missing ids in batch order; answered/tool-less histories return `[]`;
  foreign tails are refused; repair is idempotent; `KeyboardInterrupt` from
  the model call AND from inside a tool escapes `run_turn` (never swallowed
  into ERROR text), leaving exactly the dangle repair expects.
- **Live (free lane):** craft a session ending in a dangling batch, `--resume`
  it on ollama, watch the repair notice, and get a clean model answer on the
  next turn (the wire accepts the repaired transcript). Manual Ctrl+C on a
  long local turn: the `[interrupted]` notice, then a steering message works.
- **Stage close:** the §5 overnight rehearsal's interrupt-and-resume leg
  exercises both consumers end-to-end.
