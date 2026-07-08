# Note 33 — Stage 2.16: MCP client (the infinite tool bus)

> Written 2026-07-08, before implementing. Sources studied: the [MCP specification (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) + the [2026-07-28 release-candidate post](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) (stateless core, exactly two transports), Claude Code's MCP config/naming (observed daily: `mcp__<server>__<tool>`), Codex CLI's `[mcp_servers.<name>]` TOML shape, opencode's `mcp` config block with `enabled` toggles. Deferred from ROADMAP2 (owner, 2026-07-08: "the problem now is its core") — un-deferred by the owner today, with a **search engine** as the flagship: external context for the agent.

## Why now, and why search first

Stage 2C fixed the core: the agent orients, pages, plans, and survives its own attention. What it still cannot do is *know anything the repo doesn't contain* — `web_fetch` needs a URL already in hand. A search MCP server closes that: query → URLs + snippets → `web_fetch`/fetch follow-up. And MCP is the frontier's answer to "adding more tools" — not writing them, but speaking a protocol so any server's tools mount into the registry. One client, infinite tools; the last ❌ in ROADMAP2's gap table.

## What the seniors do

| | config | tool naming | permissions | transport |
|---|---|---|---|---|
| **Claude Code** | `.mcp.json` (`mcpServers: {name: {command, args, env}}`) | `mcp__<server>__<tool>` | MCP tools ask by default | stdio + HTTP |
| **Codex CLI** | `[mcp_servers.<name>]` in `config.toml` — `command`, `args`, `env` | namespaced | approval policy applies | stdio |
| **opencode** | `"mcp": {name: {type: "local", command: [...], enabled: true}}` | namespaced | per-agent permissions | stdio ("local") + HTTP ("remote") |

All three: spawn the subprocess at startup, `initialize` handshake, `tools/list`, merge namespaced, gate through the existing permission system. The 2026-07-28 RC helps us: the protocol core is now **stateless** with exactly two transports, so a minimal stdio client is a genuinely small project.

The wire (verified against the spec): newline-delimited JSON-RPC 2.0 over stdin/stdout, UTF-8, no embedded newlines. `initialize` (request) → response → `notifications/initialized` (notification) → then `tools/list` / `tools/call`. Tool results arrive as `content: [{type: "text", text: ...}, ...]` plus an `isError` flag.

## What we build (round one, exactly ROADMAP2 §4's slice)

**`src/harness/tools/mcp.py`** — a tool *source*, so it lives with the tools:

- `MCPServer`: `Popen` the command, one **reader thread** draining stdout into a `queue.Queue` (blocking `readline` with timeout is not a thing on Windows pipes; a thread + queue is the standard answer). `_request()` writes one JSON line, waits for the matching `id` (skipping notifications and non-JSON lines), times out to ERROR text. stderr is drained by a second thread into a small deque — shown only when startup fails, so server logs never pollute the REPL but are there when debug-live needs them.
- Handshake: `initialize` (protocolVersion `2025-06-18`, our clientInfo) → `notifications/initialized`. Then `tools/list`, following `nextCursor` pagination.
- **Namespacing:** `mcp__<server>__<tool>` — Claude Code's convention, and legal on every wire we speak (Gemini allows `[a-zA-Z0-9_.-]`, ≤64 chars; Anthropic similar). Names are sanitized to `[a-zA-Z0-9_-]`; anything still over 64 chars is skipped with a warning.
- **Schema conversion:** MCP's `inputSchema` *is* JSON Schema — it drops straight into our `{"type": "function", "function": {...}}` shape. Descriptions pass through (they are the server author teaching the model — note 04) but are capped at 800 chars: a runaway description would eat the local 8K window, and bounds are house style.
- **Result framing (2.21a house style):** first line `[mcp:<server>] <tool> - <n> chars`, then the joined text parts; non-text content becomes a `[non-text content: <type>]` placeholder. `isError` → `ERROR: ...` text. Every failure — dead server, timeout, malformed reply — is ERROR text to the model, never a raised exception (invariant 3).
- `connect(config, emit)`: start every configured server, return `(registry, schemas, servers)`. A server that fails to start is a warning + its stderr tail, not a crash — the harness runs on without it.

**Config — `harness.toml`, Codex's TOML shape** (our config file is already TOML; one fact, one home):

```toml
[mcp.servers.duckduckgo]
command = "uvx"
args = ["duckduckgo-mcp-server"]
# enabled = true      # opencode's toggle — flip off without deleting
# timeout = 30        # seconds per call (default 30)
# env = { KEY = "v" } # extra environment for the server
```

Windows detail: `command` is resolved with `shutil.which` (finds `.exe`/`.cmd`); a `.cmd`/`.bat` (npx-class servers) is wrapped in `cmd /c`, because `CreateProcess` can't execute batch files directly — the classic Windows MCP paper cut, handled once here.

**Permissions: zero new code.** The gate already receives every registry name and the mode policy decides; `mcp__*` names simply fall into each mode's `default` bucket — **ask** in `build`/`auto`, **deny** in `explore`, and `chat` sends no tools at all. Fail-closed exactly as 2.8 built it. The owner can allowlist a specific tool (e.g. `mcp__duckduckgo__search`) per mode in `harness.toml` like any other tool.

**REPL wiring:** connect after config load, merge into `registry`/`schemas` (subagents get MCP tools too — search is exactly what a research child needs; `todo_write` stays top-level-only), print one line per server at startup (`mcp: duckduckgo - 2 tools`), `/mcp` builtin lists servers + tools, servers are stopped on exit. Acceptance's `run_once` merges MCP only for tasks tagged `"mcp": True`, so the other tasks' token baselines don't move.

**The flagship server:** [nickclyde/duckduckgo-mcp-server](https://github.com/nickclyde/duckduckgo-mcp-server) — Python, MIT, `uvx duckduckgo-mcp-server`, **no API key** (the reason it wins: `.env` stays clean, the regression lane stays $0-adjacent). Ships `search` + `fetch_content`; ~30 searches/min rate limit is far above our grain. uvx caches the package after the first run.

**Not in round one** (consciously, per ROADMAP2): HTTP transport, resources, prompts, sampling, roots, server-initiated requests (we answer nothing; unmatched server requests are ignored), hot reload. Hooks still wait for Stage 3.4.

**Economics note:** every mounted server's schemas ride every call — that's the real cost of the "infinite tool bus" on an 8K local card. Two tools ≈ trivial; the meter, as always, gets the final word. Keep servers few and deliberate.

## How we know it works

- **pytest (offline, zero tokens):** `tests/fake_mcp_server.py` — a ~60-line stdio server speaking real JSON-RPC (echo tool, isError tool, a slow tool, a junk-line prelude for robustness). `tests/test_mcp.py` drives `MCPServer` against it as a genuine subprocess: handshake + list, call framing, isError → ERROR text, timeout → ERROR text, non-JSON lines skipped, dead command degrades to warning; pure-function tests for namespacing/sanitizing and schema conversion; TOML config parsing; one FakeModel loop test proving a namespaced tool dispatches like any other.
- **live, free then cheap (budget rule):** smoke on `ollama` first — a protocol bug loops at $0. Then the gemini lanes. Acceptance grows task **O-mcp-search** (tagged `mcp`): "search the web for X and answer" — the verifier checks *reality*, not words: an `mcp__*` tool call must appear in the transcript AND the answer must be right. Skips with a note when no MCP server is configured.

## What happened (2026-07-08, after implementing)

Shipped as designed; all 14 new pytest cases passed first run (196 offline total). The protocol was the easy part — **the day's real lesson was child-process TLS**:

1. First live connect died in uvx itself: this machine's TLS interception broke the PyPI fetch (`invalid peer certificate: UnknownIssuer`). The stderr-tail mechanism paid for itself immediately — the reason was right there in the warning. Fix: uvx `--system-certs`.
2. Search then returned "no results"; `fetch_content` on example.com surfaced the true cause: `CERTIFICATE_VERIFY_FAILED` inside the *server*. Our own process cures interception with truststore injection — a **child process can't**, but it honors `SSL_CERT_FILE`. New utility `tools/ca_bundle.py` writes certifi + the Windows ROOT/CA stores to `~/.harness/ca-bundle.pem`; `harness.toml` hands it to the server via the `env` key built for exactly this. (The `[browser]` extra for DDG's TLS-fingerprint detection went in along the way — the server itself recommended it.)
3. With the bundle: search + fetch both work, **zero model tokens spent on debugging** — the whole TLS hunt ran through a scratch script against the client directly.

Gate results, all three lanes: **O-mcp-search local PASS** (qwen3:4b-instruct discovered the namespaced tool from its schema alone — 5,704 in / 54 out, 23 s), **lite 3/3** (~$0.0007/run), **flash 3/3** (~$0.0025/run). Full-core regression on lite: 13/15 single-run, with K recovering 3/3 on majority and I-agent-plan confirmed as the pre-existing problem.md #2 lite coin-flip (1/3 lite, but 3/3 on flash where 2C closed) — mechanically untouchable by this feature, since only mcp-tagged tasks mount the schemas. Local full core: see the run log. The two-tool schema cost measured ~600–900 input tokens/call on the O task — the "keep servers few" economics note stands.
