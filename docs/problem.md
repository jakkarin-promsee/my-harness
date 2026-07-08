# Problems & owner decisions

> Things an autonomous run could not finish alone, plus decisions that are
> yours to make. Updated 2026-07-08. Delete items as you resolve them.

## 2. Tasks K and I are fragile on flash-lite — the lite model coin-flips role behavior (2026-07-08)

Found while gating 2.18a/2.19: on `gemini-2.5-flash-lite`, `K-skill-trigger`
is majority-FAIL at N=3 under BOTH the old prompt (1/3) and the new backbone
(0–1/3; loop-step fix and a harder skills header didn't move it), and
`I-agent-plan` oscillates around 50 % (2/3 → 1/3 across re-runs; hardening
the role body helped from ~25 %, pinning `voice: normal` didn't finish the
job). The 2R-era "11/11 both providers" was single-run luck — exactly the
red-team #12 problem the N=3 rule now catches. On the lanes that matter both
are SOLID: `gemini-2.5-flash` K 3/3 and I 3/3 (fast and cheap), local qwen3
passes both. Verdict: a "lite"-class model can't reliably hold role
constraints (skill procedure, read-only plan + mandated closing line) —
a MODEL limit, not harness breakage; we refuse to overfit prompts to the
cheapest model (that's tuning on the test set). **Your call at stage close:**
accept "core 9–11/11 with K+I known-flaky" as flash-lite's green bar, or move
the regression lane's role tasks to flash (per-provider task lists exist
since 2.17).

## 0. Ollama tray app needs a reboot (2026-07-07, from the 2.15 lab; still true 2026-07-08)

*(2026-07-08 update: one 695s ReadTimeout stall observed during the Stage 2C
close runs — the detached server recovered by itself, but reboot when you
can.)*

During the lab the tray app got wedged: it starts, but its API server child
dies instantly (`app.log`: "ollama server not ready after retries";
`server.log` empty). Likely collateral of force-killing processes between
config changes. **Right now everything works** — a detached `ollama serve`
with the tuned env is running (started by the lab session; survives until
shutdown). **Fix: just reboot.** The tray app auto-starts at login and reads
the machine-wide env (`setx`: `OLLAMA_FLASH_ATTENTION=1`,
`OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_CONTEXT_LENGTH=8192`). Verify after:
`ollama ps` after one request should show ~3.6 GB / more-GPU split. If the
tray still fails: run `ollama serve` in any terminal — the env vars are
machine-wide now, no prefix needed. Revert path for the whole lab config:
delete the two new vars in System → Environment Variables, restart Ollama.

## 1. Anthropic adapter is live-untested (deliberate)

`src/harness/providers/anthropic.py` is fully built and offline-tested (7 tests,
mocked HTTP), but per the constitution `ANTHROPIC_API_KEY` stays unset until
you set it on purpose. When that day comes: put the key in `.env`, then
`uv run python -m harness anthropic` and run acceptance task B as a smoke
test. Until then, treat the adapter as "compiles, untested against the real
wire". (Note: the adapter does not stream — docs/notes/12-streaming.md — and
prompt caching, ROADMAP 2.9's last skipped item, becomes worth building the
same day the key arrives.)

---

**Resolved 2026-07-07** (kept one line each for the record; details in git
history and ROADMAP's Stage-2 status):

- ~~Local model can't pass the suite~~ → `qwen3:4b-instruct` (non-thinking
  2507) passes **7/7** with ~1.5k output tokens; the two remaining "failures"
  were a cp1252 stdout crash and a case-sensitive verifier — our bugs, fixed.
- ~~Ollama context window 4,096~~ → `OLLAMA_CONTEXT_LENGTH=8192` set
  machine-wide (`setx`) + in `.env`; verified live via `ollama ps` (CONTEXT
  8192). Survives reboot; the tray app reads the user env var.
- ~~README is a placeholder~~ → real README written and committed.
