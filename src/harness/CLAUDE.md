# src/harness — code map for agents

> Auto-loaded when you work under `src/`. This is a **map**: where things live and the rules you can't break. *How it works* is in each module's docstring; *why* in `docs/notes/`; *what's in each folder* in that folder's `README.md`.

## The one idea

A harness is a `while` loop around a chat API with tool-calling. The loop is the heart; everything else is layers wrapped around it. Full anatomy: [docs/notes/00-anatomy.md](../../docs/notes/00-anatomy.md).

## The packages (open the folder's README for detail)

| Folder | What lives there |
|---|---|
| `core/` | the loop + everything wrapped around it: `loop`, `context`, `permissions`, `session`, `budget`, `commands`, `subagent` |
| `providers/` | the `Model` adapters: `base` (protocol), `openai_compat` (Ollama/Gemini), `anthropic` |
| `tools/` | what the model can DO: `basic` (8 file/shell/web tools), `todo`, `mcp` (external tool servers) |
| `cli/` | `repl.py` — the only human-facing code: provider registry, token meter, permission gate, streaming display |
| `prompts/` | `system.md` — the identity/rules the harness gives its **own** agents |

## Invariants — don't break these

1. **The loop is pure and injected.** `core/loop.py` does no HTTP, no `input()`, no printing it wasn't handed. That's exactly why it tests for zero tokens against a FakeModel. Keep it that way.
2. **Adapters translate BOTH directions.** History is replayed on every call, so outgoing translation matters as much as incoming (`providers/base.py`, note 03).
3. **Tools return a string, always.** A tool never raises into the loop; unknown tool / bad-JSON args / exception all become ERROR *text* the model can read and adapt to.
4. **`messages` is ours.** It's a plain Python list we own — editing it is free, no model call. That freedom is the whole thesis of Stage 3.1.
5. **Two audiences.** This code is *edited* by Claude Code but *run* by the harness's own agents. `AGENTS.md`, `commands/`, `prompts/system.md` belong to the runtime — don't repurpose them for dev context (note 15).

## Commands

- Tests (offline, zero tokens): `uv run pytest -q`
- Run it (local, free): `uv run harness ollama`
- Exit gate (live): `uv run python acceptance/run.py <provider>`
- Add a feature end-to-end: follow the **implement-feature** skill.
