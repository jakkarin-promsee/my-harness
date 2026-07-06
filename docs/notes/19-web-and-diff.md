# Note 19 — Stage 2.13: web_fetch + the diff gate

> Written 2026-07-07, before implementing. Sources studied: [opencode `webfetch.ts`](https://github.com/sst/opencode/blob/dev/packages/opencode/src/tool/webfetch.ts) (fetched raw — constants quoted below), [aider `scrape.py`](https://github.com/Aider-AI/aider/blob/main/aider/scrape.py), Claude Code's WebFetch + diff-preview behavior (observed daily). Full audit: ROADMAP2 §2.

## Why these two together

Both are "the last missing member" features. `web_fetch` completes the frontier core tool set (read/write/edit/glob/grep/ls/shell/todo/task/**webfetch** — every senior ships it). The diff gate completes 2.9's "see what it's doing" thread: the `ask` prompt today prints raw JSON args — for an `edit_file` that's an unreadable blob with `\n` escapes, which trains the user to blind-approve. Every senior renders a diff at this moment.

## What the seniors do

| | web fetch | diff at the gate |
|---|---|---|
| **opencode** | `url` + optional `format` (text/markdown/html) + `timeout`; **30 s default timeout, 5 MB response cap** (checked at header and body); http/https only; text mode parses HTML skipping `script/style/iframe`; Chrome UA with a plain-UA retry on Cloudflare 403 | TUI shows the diff before permission |
| **aider** | `/web`: playwright if present, else httpx; bs4 `slimdown_html` strips svg/images/data-URIs, pandoc → markdown | every edit is shown as a diff (its whole output format) |
| **Claude Code** | WebFetch takes url + a *prompt*, converts to markdown, runs a **second model** over it, 15-min cache | edit approval renders a colored unified diff — the canonical UX we copy |

## What we build

**`web_fetch(url)`** — the 8th core tool in `tools/basic.py` (stateless like its siblings; `todo.py` stays the only factory). Living in `basic.py` means `REGISTRY`/`SCHEMAS` carry it everywhere for free — REPL, acceptance, and subagents (children get it, same as Claude Code's).

- `requests.get` (already a dependency; `truststore` is injected at app level by the REPL, not by the tool) with **timeout 30 s** (opencode's default), a browser-ish UA (the requests default UA gets 403'd widely — opencode ships a Chrome string), redirects followed (requests default).
- **http/https only** — `file://` etc. refused as ERROR text. No private-IP blocking: single user, and the owner legitimately fetches `localhost` (Ollama's own API). The gate is the guard.
- **Download cap 2 MB** (opencode: 5 MB; right-sized down — we feed an 8 K window), streamed in chunks so a giant file never fully lands in memory.
- Content handling: HTML (by content-type or a `<html`/`<!doctype` sniff) → **stdlib `html.parser`** extractor: skip `script/style/noscript/template/iframe/head`, newline at block tags, collapse runs of whitespace. `<title>` is prepended (`Title: ...`) — opencode returns it too; it orients the model. Non-HTML text (json, plain, xml) passes through raw. Binary content types → ERROR text. No markdown conversion — that needs a converter dependency for prettier output the 2 K diet would mostly discard anyway; text is the right size for us (and the roadmap's spec).
- **Head+tail truncation at 8,000 chars in-tool** (same ¾ head + ¼ tail split as the loop's `_truncate`) — bounds the tool itself; the loop's 2,000-char diet still applies on top. Two belts, deliberately: the tool bound holds even where the loop diet is configured away.
- Every failure — bad scheme, HTTP ≥ 400, timeout, connection refused, binary type — returns `ERROR: ...` text (invariant 3), never raises.
- **Permission: `ask` in every mode's table** (`harness.toml`: build + explore + auto; chat sends no tools). Fetching is read-only for the *machine* but it's network egress — it asks. Added to `NEEDS_PERMISSION` too.
- Web *search* stays parked: it needs an API-key provider; noted, not built (roadmap).

**Diff at the gate** — presentation, so it lives in `cli/repl.py` next to `make_gate` (the loop stays pure; nothing in `core/` changes).

- `render_diff(name, arguments) -> str | None`: for `edit_file`, unified-diff `old_string` → `new_string`; for `write_file`, diff the target's current content (missing/unreadable file → empty, i.e. all-`+` lines) → `content`. `difflib.unified_diff` — stdlib, like every Python senior. Any other tool, or an empty diff → `None`, and the gate falls back to today's JSON preview.
- Capped at 40 diff lines + `... (N more diff lines)` — an unbounded render is the same disease as unbounded tool output.
- The gate colors it line-by-line (`+` green, `-` red, `@@` cyan — the VT trick from 2.9a is already applied) and prompts `allow edit_file on <path>? [y/N]`. Color lives in the printing, **not** in `render_diff`'s return — keeps the function snapshot-testable.
- Subagents inherit it free: the child gate is the same `approve` callable.

## How we know it works

- **pytest** (offline): `test_tools.py` grows web_fetch cases with a monkeypatched `requests.get` — tag stripping (script dropped), whitespace collapse, title line, scheme refusal, HTTP-error text, binary-type refusal, the 8 K head+tail marker; registry/schema agreement updated to 8 names. New `test_repl.py`: `render_diff` snapshots — edit_file exact render, write_file new-file (all `+`), write_file against an existing file, non-edit tool → `None`, the 40-line cap.
- **live, free then cheap**: acceptance grows task **J-web-fetch** — fetch `https://example.com` (IANA-reserved, maximally stable) and report its first heading; verifier: `"example domain"` in the final answer. Gate on ollama first, then gemini (budget rule). The diff gate is proven by the pytest snapshots — the acceptance suite runs auto-approved, so it never prompts.

## What happened (2026-07-07, after implementing)

Shipped as designed, one addition found in review: `iter_content` can raise `RequestException` *mid-stream* (connection drop while reading the body), so the catch wraps the whole read, not just the `get`. Results: **129 pytest** (was 116); gate **10/10 ollama** (64,353 in / 2,270 out — task J: the model picked web_fetch unprompted, quoted "Example Domain" exactly) and **10/10 gemini** (117,935 in / 4,319 out — the in-token jump vs 2.12's 40,696 is task-level variance: task I ran long and ate one length-nudge, meaning one extra full-history call; zero 503s, 33 tool calls across 10 tasks). Live smoke also confirmed both error paths read cleanly (`ERROR: only http(s)...`, `ERROR: fetch failed: ...Max retries exceeded`).
