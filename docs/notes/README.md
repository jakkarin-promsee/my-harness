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
| [21-local-lab](21-local-lab.md) | 2.15 lab log: FA + q8_0 KV = +13 % speed, not more context (weights overflow the card); bake-off — incumbent holds |
| [22-failure-museum](22-failure-museum.md) | 2.17: real failed tasks from `sessions/` frozen as fixtures (one hold-out); the flash wire probes — `"none"` works, thinking is derivable as `total−prompt−completion` |
| [23-backbone](23-backbone.md) | 2.18a: system prompt v2 — six tagged sections every role extends (`backbone: false` opts out); "keep answers short" dies; local museum M2 flipped 0/3→3/3 |
| [24-prompt-ladder](24-prompt-ladder.md) | 2.18b: MICRO/COMPACT/STANDARD/FULL over one file — same-name sections replace; measured 264/580/660/854; `/prompt`; spawn-time assembly |
| [25-voice-and-effort](25-voice-and-effort.md) | 2.19: `/voice quiet\|normal\|explain` (Gemini default = explain — flipped M2 on flash, ×2.3 output) + `/think off` → `reasoning_effort:"none"` (0 think proven) + the derived think meter |
| [26-thinking-curve](26-thinking-curve.md) | 2.20 lab: H1 ✓ (thinking = waste on simple), H2 ✗ (budget never moved the hard task — it's an information problem; high explored LESS), H3 ✓ early (voice). Pin: flash `think: off` for every role |
| [27-structured-observations](27-structured-observations.md) | 2.21a: read_file framed/numbered/pageable (header + how-to-get-more tail); per-provider tool diet; L-paging + M-poisoned-file tasks. Flash museum went 9/9 — the eyes were M3's bottleneck |
| [28-senses-and-descriptions](28-senses-and-descriptions.md) | 2.21b: list_dir dirs-first+sizes, grep/glob/web_fetch frames (no JSON arrays left), all 8 descriptions teach workflow. Local 13/13, lite 13/13, museum majority holds |
| [29-orientation](29-orientation.md) | 2.22: tier-sized project map in the env block + AGENTS.md map convention. A/B on flash: 2/3→3/3 with input tokens HALVED; local −22 % tokens. N-orientation task joins the gate |
| [30-attention-anchors](30-attention-anchors.md) | 2.23: re-anchor after K quiet steps (meta-tagged, adapters scrub, /compact drops, resume prunes). First wording caused apology-spirals (M3 0/3!) — ambient "not user feedback" wording + K=8 fixed it |
| [31-stage-2c-close](31-stage-2c-close.md) | **Stage 2C close report**: exit gate (flash 14/14 + museum 3/3, hold-out 3/3 first-run), the before/after table, honest remainders |
| [32-turn-reflection](32-turn-reflection.md) | 2.24: a fast meta-model distills each finished turn — rolling per-turn compaction on the ollama-think lane |
| [33-mcp-client](33-mcp-client.md) | 2.16 (un-deferred): stdio MCP client — `[mcp.servers.*]` → `mcp__server__tool` in the registry, ask-by-default; duckduckgo search is the flagship; the child-process TLS lesson (`ca_bundle.py`) |
| [34-turn-control](34-turn-control.md) | 2.25: Ctrl+C = steer, not die — the turn stops, the session survives; `repair_dangling_calls` synthesizes results for unanswered tool_calls on interrupt AND on `--resume` (the 400-poison corpse) |
| [35-wire-survival](35-wire-survival.md) | 2.26: the shared retry policy in `providers/base.py` — backoff+jitter on 429/5xx/connection errors, `Retry-After` honored (capped 60s), other 4xx never retried; cloud 5 attempts, localhost 2 |
| [36-auto-compact](36-auto-compact.md) | 2.27: the 80% warning grows hands — `should_compact` fires `/compact` at the turn boundary (85% default, **0.6 on the 8K lanes** — live 400 receipt: past ~real-100% the summarize call can't fit; chars/4 under-estimates 25–65%); also fixed /compact using the stale launch model after /agent |
| [37-headless-mode](37-headless-mode.md) | 2.28: `-p "task"` — one turn, stdout = the answer only (chrome → stderr via the `info` seam), exit 0 iff `final_answer` finds a plain assistant tail; asks EOF-deny unless `-y`; `-p --resume` chains (cron works) |
| [38-ambiguity-character-museum](38-ambiguity-character-museum.md) | 2.29: the Tier-2 museum wing (M5–M9 + sealed M10) — synthesized from the owner's descriptions, verified live; flash baseline: **cave 1/3 and robot-register 1/3 certified**, stall intermittent 2/3, M6/M8 already pass; the M9 verifier's first needle set missed the live failure — frozen verbatim as the fixture |
