# Problems & owner decisions

> Things an autonomous run could not finish alone, plus decisions that are
> yours to make. Updated 2026-07-07. Delete items as you resolve them.

## 1. Anthropic adapter is live-untested (deliberate)

`harness/providers/anthropic.py` is fully built and offline-tested (7 tests,
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
