# 37 — Headless mode: `-p` and the harness becomes infrastructure (2.28)

> Stage 2A, Tier 1 — the floor ([ROADMAP4.md](../ROADMAP4.md) §4). The last
> floor cycle: the REPL stops being the only door.

## The problem (with the receipt)

`parse_args` offers provider / `-y` / `--mode` / `--agent` / `--resume` /
`--sessions` — every entry point assumes a human at a prompt (`repl.py`).
No cron job, no pipeline, no "run this phase overnight and log it", no
calling the harness *from* a script — and Stage 3.2's prompt middleware has
no dispatch path. The acceptance runner works around it by importing the
Agent directly; everything else can't.

## What the seniors do

- **Claude Code `claude -p "task"`** — print mode: run non-interactively,
  print the result, exit. stdout is the *answer*; logs and chrome go
  elsewhere. In headless, a permission `ask` is **auto-denied** — never
  hang waiting for a human who isn't there; pre-approval flags exist.
- **Codex `codex exec "task"`** — same shape; the exit code reflects
  success, which is what makes `&&`-chains and CI possible.
- **aider `--message "..."`** — one-shot: apply, report, exit.

Convergent contract: **stdout = deliverable, stderr = chrome, exit code =
verdict, asks never block.**

## What we build

`harness <provider> -p "task"`:

- **One turn, then exit.** Same assembly as interactive — roles, modes,
  tiers, sessions all compose (`-p` + `--agent plan`, `-p` + `--resume` for
  cron *chains* — each run persists its session like any other, so the next
  `-p --resume` continues it).
- **Clean stdout.** The final assistant text is the only thing printed to
  stdout; banner, meter, tool lines, thinking, repair notices all route to
  stderr via one `info()` seam (headless flips it, interactive keeps
  `print`). The permission gate's chrome joins stderr through a new `out`
  param on `make_gate`. No streaming in headless (`on_delta=None`) — nobody
  is watching deltas; the answer prints once, whole.
- **Exit code:** `0` iff the turn ended in a plain assistant text (the
  deliverable), else `1` — API death after retries, MAX_STEPS runaway,
  interrupt, empty answer. The pick is a pure function, `final_answer
  (messages)`: last message must be an assistant message with content and
  no tool_calls.
- **Asks:** already safe by construction — piped/absent stdin makes the
  gate's `input()` raise `EOFError`, which it treats as *no* (2.8). `-y`
  upgrades asks exactly as interactive; `deny` stays deny. Documented, now
  deliberate.
- **No auto-compact, no reflection in headless:** both act at the turn
  boundary *for the next turn's benefit* — there is no next turn; the next
  `--resume` (interactive or `-p`) inherits the boundary work instead.

Non-goals, recorded: `--output-format json` / stream-json (a consumer shows
up in Stage 3.4's findings channel — schema work belongs there); reading the
task from stdin (`-p -`) — compose with shell substitution instead; a
separate `dontAsk` mode (EOF-deny + `-y` + `deny` already span the ladder).

## How we know it works

- **Offline:** `parse_args` accepts `-p` (and its absence keeps interactive
  defaults); `final_answer` picks a plain assistant tail, refuses tool-call
  tails / tool tails / empty content (the exit code's whole truth table).
- **Live (free lane):** `uv run harness ollama -p "reply with exactly:
  HEADLESS OK"` → stdout contains exactly the reply, exit code 0, chrome on
  stderr only; the session file exists and is resumable. The §5 overnight
  rehearsal runs *entirely* through `-p` at stage close.
