# 40 — Agency under ambiguity: investigate-first + ask_user (2.31)

> Stage 2A, Tier 2 — the mind ([ROADMAP4.md](../ROADMAP4.md) §4). The
> owner's problem 2, his words: *"it knows the task is unclear, but it
> didn't go grep or search. It just stuck on unclear loop and don't do
> anything."*

## The problem (with the receipts)

Two receipts, one mechanism. **Receipt 1 — the trap is real:** museum
M6-window-truth fails **0/3 on local** (note 38): asked "4096 or 8192? be
sure", the model either coin-flips or answers without evidence. M5 (the
stall) is intermittent on flash. **Receipt 2 — the mechanism (ROADMAP4
insight 2):** in this loop the model's only affordances are *call a tool*
or *end the turn with text*. Asking a question IS ending the turn — it
feels like abandoning the mission the backbone gave it, so the model
neither asks nor investigates. Asking is turn-death, and the stall is the
model frozen between "act" (mission) and "don't guess" (honesty).

## What the seniors do

- **Claude Code**: an `AskUserQuestion` **tool** — asking is an action; the
  answer comes back as a tool result and the turn continues. Its prompt
  guidance pairs it with explore-first: reserve questions for what the
  code/repo cannot answer.
- **MCP elicitation** (spec'd 2025): servers ask the human mid-call through
  a structured request — the same shape, standardized.
- **aider**: `/ask` is a *mode*, not a tool — the human opts into
  discussion. The tool-shaped version fits our loop better.

## What we build

1. **`ask_user(question, options?, recommended?)` in `tools/ask.py`** — a
   factory like todo's (`make_ask_tool(ask_input, emit)`): renders the
   question + numbered options, blocks on input, returns `"The user
   answered: …"` as an ordinary tool result — **the turn continues through
   the question**. Empty answer → the recommended default. `EOFError` (no
   human: piped stdin, headless) → the recommended default with an
   auto-answered flag, or "use your best judgment and state your
   assumption" when none was offered — the 2.28 contract extended: asks
   never hang. Ctrl+C propagates to the 2.25 steer arm like everywhere
   else. **Top-level only** (like todo): children never interrogate the
   human. Permissions: `allow` in build/explore/auto — it is literally
   asking; the gate would be asking permission to ask.
2. **The prompt branch** — *unclear or under-specified → investigate with
   read-only tools FIRST (the repo usually answers); only when evidence
   cannot settle it, ask ONE focused question with ask_user (options +
   recommended default), then continue.* Planned micro-first because M6's
   home is the 8K lane; **measured to be net-negative at micro** (see
   Results — the experiment bought the frozen-micro law) and landed at
   STANDARD only, with the tool schema carrying the lesson on the small
   lanes.
3. **The runner**: scripted runs have no human — `run_once` wires an
   `ask_input` that raises `EOFError`, so probes exercise the
   recommended-default path by construction; a task may provide
   `"answers": [...]` to script a dialogue.

Non-goals: multi-question forms (ONE focused question is the discipline);
asking in the companion world (conversation IS asking); a queue of pending
questions (the turn blocks, by design — that's what makes it an action).

## How we know it works

- **Offline:** ask-tool contract both ways (options render, empty→default,
  EOF→flagged default, EOF-no-default→best-judgment, verbatim answers);
  the loop needs no changes (a tool is a tool).
- **Live (free lane):** **M6-window-truth local 0/3 → majority** is the
  cycle's movement target; M5 local stays 3/3; E-exact-edit + core spots
  stay green after the micro prompt addition (the note-39 lesson made
  law). Flash re-checks (M5 2/3, M6 flake) queue behind the problem.md #3
  re-key.

## Results (2026-07-08, recorded at run time)

**Offline:** 234 tests (was 227) — the full ask-tool contract; MICRO
backbone measured 345 est tokens with the branch (cap 450).

**The micro experiment, and the law it bought.** With the ambiguity branch
in the MICRO loop, local N=3 read: **E-exact-edit 0/3** (the note-39
regression back from the dead — path-guess, wrong-scope glob, gave up;
never asked, so ask_user wasn't the culprit), **M5 3/3 → 1/3** (long
wandering runs, 74k in), **M6 0/3 → 1/3** (barely moved). Net negative
across the board: the micro loop is a ~60-token attention budget, and
EVERY added clause dilutes the act-verify core that carries the 4B. Second
E-breakage by a micro addition in one day → **law: the MICRO loop is
frozen. Behavior additions go to standard+ tiers or into tool schemas
(which load only when relevant — progressive disclosure was the right
mechanism all along).**

**The scoped landing:** micro loop reverted verbatim; the
investigate-first-then-ask branch rides the STANDARD loop (the Gemini
lanes); ask_user itself stays registered everywhere — its schema teaches
investigate-first at zero prompt cost. **M6-local stays an open exhibit**
(the coin-flip trap at micro has no prompt lever left — candidates: 2.32's
evidence-beats-agreement core rules, or accept as a 4B model-limit; flash
M6 already passes 3/3). Recovery runs below.

**Recovery (micro reverted, local):** **M5 3/3** — the wandering was the
branch's dilution, confirmed. **M6 1/3 tool-only** — the open exhibit at
micro stands as recorded above. **E 1/3, then 3/3 on the immediate re-run —
4/6 across six same-config runs tonight:** every miss is the identical
pre-existing trap (globs `acceptance/*.py`, baited by the filename prefix,
declares the file missing; wins whenever it globs `**/`). A coin-flip
around path-guessing — the same repo-growth family as D's `totals` bait
decay, now recorded beside it in problem.md #2. Not a 2.31 effect: E
flipped between 0/3 and 3/3 across byte-identical configs.

**Flash movement checks** (M5 2/3 baseline → target; the standard-tier
branch + tool): queued behind the problem.md #3 re-key.
