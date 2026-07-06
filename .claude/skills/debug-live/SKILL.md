---
name: debug-live
description: Triage a live-model failure in the researcher-harness — an acceptance task fails, the agent loops, replies come back empty or cut off. Encodes the project's triage order (verifier → harness → config → model). Use BEFORE blaming the model or editing any code.
---

# Debug a live failure — the triage ladder

Working rule 5 says the harness must be boring: when a result looks weird, "or is my harness buggy?" needs a fast, *ordered* answer. Climb this ladder rung by rung — every bug found so far lived one rung earlier than first suspected.

## 0. Reproduce for $0

Reproduce on `ollama` only. Never re-run a failure on a paid endpoint "to see if it happens again" — that's the budget rule.

## 1. Suspect the verifier first

Read what the agent *actually did* (the transcript in `sessions/*.jsonl`, or the acceptance output) against what the verifier *checks*. Precedent: task A "failed" because the check demanded `FizzBuzz` while the prompt said "fizzbuzz" — the model was right, the check was wrong (fixed 2026-07-07).

## 2. Then the harness

- `uv run pytest -q` — is the contract still green?
- Inspect the messages list around the failure: an unanswered `tool_call` poisons strict OpenAI-style history; a reply cut off at `finish_reason: length` can carry half-written tool calls (the loop is supposed to drop them — did it?).
- Console encoding: a single ✓ or emoji once killed a whole task on Windows cp1252 (now handled by UTF-8 reconfigure — but new entry points need it too).

## 3. Then the config

- `.env`: is `OLLAMA_MODEL` what you think it is? A stale value silently swaps the model under you.
- `OLLAMA_CONTEXT_LENGTH`: 8192 expected on this machine; Ollama's own default (4096) silently truncates context.
- `max_tokens` headroom: 2000 was thinking-death on qwen3 (note 11).

## 4. Only now, the model

Consult the model lessons in the root `CLAUDE.md` status line (already in your context: fabrication, thinking-burn, temperature, 503s, empty replies). A *new* pathology is a finding, not necessarily a bug.

## 5. Record what you learned

- New model lesson → the status line in root `CLAUDE.md`.
- Needs the owner's decision → `docs/problem.md`.
- Harness bug → fix it **with a FakeModel regression test** in `tests/` that replays the failure for zero tokens.
