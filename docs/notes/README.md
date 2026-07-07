# docs/notes — the why, one note per feature

Design notes, written *before* implementing (working rule 6). Each follows the same
shape: *what the seniors do → what we built → how we know it works.* They are dated
history — if a note disagrees with the code, the code is the territory.

| Note | What it explains |
|---|---|
| [00-anatomy](00-anatomy.md) | The six organs of a harness — the mental model everything builds on |
| [01-mvp](01-mvp.md) | Stage 1: the single-file ~300-line harness (now frozen in `archive/mvp/`) |
| [02-package-structure](02-package-structure.md) | 2.0: single file → package + FakeModel tests (zero-token contract) |
| [03-provider-adapter](03-provider-adapter.md) | 2.1: the `Model` protocol; the six-way Anthropic translation table |
| [04-tool-quality](04-tool-quality.md) | 2.2: the ACI lesson — `edit_file` uniqueness, bounded `grep`/`glob` |
| [05-sessions](05-sessions.md) | 2.3: JSONL transcripts + resume |
| [06-context-assembly](06-context-assembly.md) | 2.4: system prompt = template + env block + `AGENTS.md` |
| [07-context-v1](07-context-v1.md) | 2.5: token estimator, `/tokens`, standard `/compact` — the baseline 3.1 must beat |
| [08-subagents](08-subagents.md) | 2.6: spawn with fresh \| fork; only final text returns |
| [09-commands](09-commands.md) | 2.7: slash commands as markdown files with `{{args}}` |
| [10-permissions-v2](10-permissions-v2.md) | 2.8: `harness.toml` allow/ask/deny, fail-closed |
| [11-visible-mind](11-visible-mind.md) | 2.9a: narration preambles, thinking display, the length-nudge |
| [12-streaming](12-streaming.md) | 2.9b: SSE deltas — watch it think and talk live |
| [13-todo-tool](13-todo-tool.md) | 2.9c: the external plan the model can't forget |
| [14-src-layout](14-src-layout.md) | The restructure: installable package under `src/`, `docs/` + `archive/` split |
| [15-context-hierarchy](15-context-hierarchy.md) | One fact, one home — the five doc layers and the two audiences |
| [16-permission-modes](16-permission-modes.md) | 2.10: chat/explore/build/auto profiles; the cwd scoping rule; `/mode` |
| [17-agents](17-agents.md) | 2.11: roles as markdown — per-role prompt/mode/model; `/agent`; spawn `agent=` |
| [18-reasoning-control](18-reasoning-control.md) | 2.12: `/think` knob; the native `/api/chat` dialect (v1 ignores `think`); the economics |
| [19-web-and-diff](19-web-and-diff.md) | 2.13: `web_fetch` (stdlib HTML→text, two-belt truncation) + the unified-diff `ask` prompt |
| [20-skills](20-skills.md) | 2.14: `skills/*/SKILL.md` — one description line at startup, body on `read_file` (progressive disclosure for free) |
