# Note 05 — Stage 2.3: sessions (JSONL transcripts + resume)

> Written 2026-07-06, before implementing. Sources studied: Claude Code's `~/.claude/projects/**.jsonl` transcripts, mini-swe-agent's per-step trajectory JSON dump, opencode's session storage.

## What the seniors do

Everyone converged on the same idea: **the transcript IS the session**. Claude Code appends every message to a JSONL file as it happens; resume = read the file back into the messages list. mini-swe-agent rewrites a trajectory JSON every step. The invariant both protect: *persist after every message, not at exit* — a crash, a rate limit, or a sleeping laptop must never cost the conversation. (This layer is also the raw-logs-on-disk that Stage 3.4's findings channel assumes exists.)

## What we build

- `core/session.py` — `SessionStore(dir)`: `new()` (timestamp id), `append(id, message)` (one JSON line, opened-appended-closed per write so nothing buffers), `load(id)`, `latest()`, `listing()` (id + message count + first user line).
- Loop hook: `Agent` gains an optional `on_message` callback fired for EVERY message it appends (assistant + tool). The REPL points it at the store; tests point it at a list. The loop stays persistence-agnostic.
- CLI: `--resume` (latest) / `--resume <id>` rebuilds `messages` from disk and continues; `--sessions` prints the listing and exits. New session file otherwise.
- `sessions/` is runtime data → gitignored.

One deliberate Stage-2 simplification: resume replays the *full* message list. Cross-provider resume works because everything is stored in our internal (OpenAI-style) dialect — adapters re-translate on the way out.

## How we know it works

pytest: store round-trip (append N, load N, deep-equal), latest/listing, and an Agent+FakeModel turn where `on_message` captures exactly the messages appended (assistant, tool results). Manual: run a task, kill the process, `--resume`, ask "what did we just do" — at the exit gate.
