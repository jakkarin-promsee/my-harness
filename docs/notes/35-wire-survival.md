# 35 — Wire survival: a real retry policy (2.26)

> Stage 2A, Tier 1 — the floor ([ROADMAP4.md](../ROADMAP4.md) §4). The cycle
> that turns "usage limit 🥺 restart" into a wait.

## The problem (with the receipt)

All three adapters ship the same hand-rolled policy: **one retry, 5xx only**
(`openai_compat.py`, `ollama_native.py`, `anthropic.py` — the identical
`for attempt in (1, 2)` loop, three copies). A **429 rate limit is a 4xx**,
so it raises immediately: the turn dies, and under `-y` the whole overnight
run dies — the exact death ROADMAP 3.3's checkpoints would *recover from*,
which 2.26 simply *prevents*. No backoff either: two instant retries against
an overloaded endpoint is spam, not resilience. flash-lite's 503 bursts are
already in the model-lessons line; we've been surviving them on one coin-flip
retry.

## What the seniors do

- **Anthropic & OpenAI SDKs** (the converged default): retry connection
  errors, 408/429/5xx; exponential backoff **with jitter**; honor the
  `Retry-After` header when the server sends one; a small bounded attempt
  count. Other 4xx are never retried — same request, same rejection.
- **aider** (via litellm): the same policy, with the wait surfaced to the
  human so a quiet terminal isn't a mystery.
- The streaming rule everywhere: **retry only before the first byte** — a
  half-consumed stream can't be replayed.

## What we build

**`request_with_retries(send, attempts, on_wait, sleep)` in
`providers/base.py`** — the seam module grows shared wire plumbing next to
the protocol it serves. `send` is a zero-arg callable returning a
`requests.Response` (each adapter keeps its own URL/headers/stream kwargs);
the helper owns only the policy:

- retry `requests.ConnectionError`/`Timeout` (nothing consumed yet) and
  status 429 + 5xx; every other status returns/raises immediately —
  `raise_for_status` stays the adapter-visible failure, so the REPL's
  `RequestException` arm keeps working unchanged;
- delay = `Retry-After` when present (integer seconds, capped at 60 — a
  server asking for ten minutes gets our cap, not our obedience), else
  exponential 1·2·4·8s with ±25 % jitter;
- every wait announced through `on_wait` (default `print`, the adapters'
  existing style) — a rate-limited overnight run must *look* alive;
- `sleep` injected for tests (zero-second offline suite, the FakeModel ethos
  applied to the wire — ROADMAP4 insight 5).

Adapters: `openai_compat` and `anthropic` call it with **attempts=5**
(cloud endpoints, transient by nature); `ollama_native` with **attempts=2**
— localhost is either up or hard-down (the tray problem, problem.md #0), and
15 s of backoff before "is Ollama running?" would be worse than the failure.
The streaming caveat is satisfied structurally: with `stream=True` the status
check happens before any body is consumed, so every retry predates the first
byte; a mid-stream drop still propagates to the REPL arm, un-retried.

Non-goals, recorded: retrying mid-stream (can't replay a half-consumed
generation); provider fallback chains (ROADMAP4 §6 — a lane switch by hand);
circuit breakers and retry budgets (fleet problems, one user).

## How we know it works

- **Offline** (`tests/test_retry.py`, injected sleep): success passes
  through untouched; 503→200 retries with an exponential delay; 429 honors
  `Retry-After: 7` exactly; an absurd `Retry-After: 600` caps at 60; a 400
  raises immediately with zero sleeps and zero retries; persistent
  connection errors raise after exactly `attempts` tries; three adapters'
  `complete()` still normalize a first-try success (existing suites stay
  green — the refactor is behavior-preserving on the happy path).
- **Live:** nothing to stage — flash-lite's 503 bursts are the standing
  natural experiment, and the §5 overnight rehearsal forces a 429 at stage
  close.
