# ROADMAP — Building My Own Harness

> The staged plan for building a from-scratch agent harness. Written 2026-07-06.
> Rule of the whole roadmap: **copy the seniors first, customize last.** Stages 0–2 build a boring, standard harness. Stage 3 — only after the base is trusted — bends it to the owner's real pain points.

---

## 1. Why this project exists (the three pains)

**Pain 1 — Context economics.** On a typical long research session (500–900k tokens), roughly ~30k tokens (~5%) is signal — written .md files, decisions, conclusions — and ~95% is noise: tool-call protocol overhead, raw file dumps already summarized elsewhere, shell/test output resolved and never referenced again. The only tool available today is universal `/compact`, which (a) summarizes *everything* including the signal, and (b) itself costs tokens, because a model must re-read the whole context to summarize it. The owner wants to *delete the noise* — not pay to re-summarize the signal.

**Pain 2 — Prompt reuse is manual labor.** The `prompt/` folder holds real, battle-tested prompt templates (plan phase, run overnight, summarize, clean project...). But none can be reused 1:1 — every use means hand-editing paths, phase numbers, and context, and re-reading the whole thing to check it's current. Wanted: harness-level support — a template library plus a middleware step that interviews the human for the missing context and assembles the final prompt before dispatching it to a worker. Human-in-the-loop *at the harness level*.

**Pain 3 — Learning and independence.** The owner doesn't yet know how a harness works inside. This project is the way to find out — and it doubles as insurance: if Claude ever becomes unavailable here, there is still a working, understood, provider-agnostic harness on this machine.

## 2. The secret that makes this worth building

A harness is not magic. At its core it is:

```python
messages = [system_prompt, user_task]
while True:
    reply = llm(messages, tools)          # one API call
    messages.append(reply)
    if not reply.tool_calls:
        break                             # model is done talking
    for call in reply.tool_calls:
        messages.append(execute(call))    # run tool, append result
```

Everything else — permissions, compaction, subagents, sessions, slash commands — is layers around this loop. Two consequences that pay for the whole project:

1. **`messages` is just a Python list that WE own.** Deleting a stale tool result is `del messages[i]` — zero tokens, no model call, signal untouched. The thing `/compact` can never give us is free in our own harness. (This is Stage 3.1.)
2. **Anyone can build the loop in ~300 lines.** mini-swe-agent scores >74% on SWE-bench Verified with ~100 lines of agent code. The moat is not the loop — it's the accumulated design lessons around it. Which is exactly why Stage 2 is "copy the seniors."

## 3. How the stages fit together

| Stage | Name | Question it answers | Size |
|---|---|---|---|
| 0 | Recon | What *is* a harness, exactly? | ~2–3 evenings |
| 1 | MVP | Can I build the minimal loop that does real work? | ~1–2 weekends |
| 2 | Copy the seniors | What do mature harnesses have that mine doesn't — and why? | The long middle; one feature per cycle |
| 3 | Make it mine | Now that the base is boring, how do I kill my three pains? | One pain at a time |

Each stage has **exit criteria**. Do not start stage N+1 before stage N's criteria pass. Inside Stage 2, features follow a fixed mini-cycle: *study 2–3 references → 1-page design note in `docs/notes/` → implement → acceptance suite green.*

---

## Stage 0 — Recon (no harness code)

**Goal:** be able to explain, in your own words, why a harness is "a while-loop around a chat API with function calling" — and have touched the raw wire format with your own hands.

- [x] **0.1 Read the short canon** *(owner confirmed 2026-07-06)* (order matters):
  1. Thorsten Ball — [How to Build an Agent](https://ampcode.com/notes/how-to-build-an-agent) (~1 hour; a working code-editing agent in ~315 lines, line by line)
  2. [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) — read `src/minisweagent/agents/default.py` end to end (~100 lines; note: it uses *only bash*, no tool-calling API — a deliberate design choice worth understanding)
  3. Anthropic — [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
  4. Anthropic — [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (this one is basically Pain 1 written by the seniors)
- [x] **0.2 Environment setup:** *(done 2026-07-06)* uv 0.11.18 + project init; Ollama 0.31.1 installed; pulled `llama3.2:3b` (fast, clean output) and `qwen3:4b` (smarter, emits a visible `reasoning` field) — **both** emit correct tool calls on the 4 GB GPU. Machine quirk: local TLS interception → `system-certs = true` in pyproject for uv, `truststore` for Python HTTPS. Gemini key in `.env` since 2026-07-06 (never commit it).
- [x] **0.3 Wire-format lab** (in `labs/`): *(built + run 2026-07-06 on `llama3.2:3b`; Gemini leg of 02 verified by the owner with his AI Studio key — same code, three strings changed)*
  - `00_raw_call.py` — one raw HTTP POST to Ollama's `/v1/chat/completions`, print the JSON. No SDK. See the actual shape of a request/response.
  - `01_tool_roundtrip.py` — send a `tools` array, get `tool_calls` back, execute by hand, send the `role:"tool"` result message, get the final answer. **One full round trip, no loop.** This 50-line file demystifies 80% of the project.
  - `02_provider_swap.py` — same call, `base_url` flipped to Gemini's OpenAI-compatible endpoint. Proof that provider-portability is nearly free at this layer.
- [x] **0.4 Write `docs/notes/00-anatomy.md`** *(written; owner fast-tracked the formal exam 2026-07-06 — to be spot-checked live during Stage 1 code walkthroughs)* in your own words: the six organs of a harness — provider client, message list (context), tool registry + executor, the loop, system prompt, UI/REPL — and what each reference does about each.

**Exit criteria:** the tool round-trip lab works against both providers; the anatomy note exists; you can explain every JSON field in the round trip.

---

## Stage 1 — MVP (the smallest real harness)

**Goal:** a single-file REPL agent, `mvp/harness.py`, under ~300 lines, that completes a real (tiny) task on this machine. Copy the structure of Ball's tutorial and mini-swe-agent shamelessly.

- [x] **1.1 Chat REPL:** while-loop, message list, one model call per turn. *(Streaming print dropped from Stage 1 — SSE + delta-assembled tool calls triple the parsing code and teach nothing about the loop; moved to 2.9. See docs/notes/01-mvp.md.)*
- [x] **1.2 Four tools only:** `read_file`, `write_file`, `list_dir`, `run_shell`. JSON-schema definitions + a dispatch table. No more tools — resist.
- [x] **1.3 The agent loop:** model returns `tool_calls` → execute → append results → call again; plain text ends the turn. *(Plus two runaway guards earned in battle: `MAX_STEPS` for the loop, `max_tokens` for one generation, and a single retry on 5xx.)*
- [x] **1.4 Permission gate:** y/n confirmation printed before every `write_file` and `run_shell`; `-y` auto-approves for scripted runs. (First taste of the permission layer every serious harness has.)
- [x] **1.5 Token meter:** after every model call, print per-turn and running token usage from the API response. Non-negotiable — this project exists because of token economics, so we measure from day 1.
- [x] **1.6 Acceptance tasks** *(all three PASS on `gemini-2.5-flash-lite`, B also on `qwen3:4b` — full log in `mvp/ACCEPTANCE.md`)* (write them down in `mvp/ACCEPTANCE.md`):
  - A. "Create fizzbuzz.py and run it, show me the output."
  - B. "Read pyproject.toml and tell me what dependencies this project has."
  - C. A planted buggy file + failing test: "Find the bug, fix it, prove it with the test run."

**Exit criteria:** all three acceptance tasks pass (local model, or Gemini flash when the local one is too weak — both is better); every line of the file is explainable; token meter works.

**Explicit non-goals for Stage 1:** no compaction, no subagents, no sessions/resume, no config files, no TUI, no MCP, no multi-provider abstraction. MVP means MVP.

---

## Stage 2 — Copy the seniors (standard feature set)

**Goal:** grow the MVP into a normal, trustworthy harness by systematically studying how mature harnesses solve each problem — before any custom invention. By the end, for any Claude Code feature used daily, you can name the file where your equivalent lives.

Fixed mini-cycle per feature: **study 2–3 references → design note in `docs/notes/` → implement → acceptance suite green.** Never two features in flight.

- [x] **2.0 Restructure:** *(done 2026-07-06 — `harness/` package + `tests/`; 14 FakeModel tests pass in 0.17s/zero tokens; acceptance A/B/C re-verified through `python -m harness` on Gemini, B also on local qwen3. `mvp/harness.py` frozen as the Stage 1 artifact. Design note: docs/notes/02-package-structure.md)* single file → package (`core/` loop, `providers/`, `tools/`, `cli/`); pytest with a `FakeModel` (scripted responses) so the loop is testable with zero tokens. *This makes rule 5 ("the harness must be boring") enforceable.*
- [x] **2.1 Provider adapter layer** *(done 2026-07-06; note 03)*: `Model` protocol; OpenAI-compat + native Anthropic adapter (both wire directions, pure-function translation, offline-tested; live test awaits a deliberate key — docs/problem.md #3). ← The "Claude ban insurance" officially lives here.
- [x] **2.2 Tool quality (the ACI lesson)** *(done 2026-07-06; note 04)*: `edit_file` with the uniqueness rule, bounded `grep`/`glob`, head+tail truncation (errors live at the end of output).
- [x] **2.3 Sessions** *(done 2026-07-06; note 05)*: per-message JSONL via the loop's `on_message` hook; `--resume [id]`, `--sessions`. (Doubles as the raw-logs-on-disk layer Stage 3.4 needs.)
- [x] **2.4 System prompt & context assembly** *(done 2026-07-06; note 06)*: `prompts/system.md` template + env block + `AGENTS.md` project memory.
- [x] **2.5 Context management v1 — the standard way** *(done 2026-07-06; note 07)*: chars/4 estimator, 80% warning, `/tokens`, `/compact` (summarize-and-replace, cost surfaced, continues in a new session file). The baseline Stage 3.1 must beat.
- [x] **2.6 Subagents** *(done 2026-07-06; note 08)*: `spawn_subagent(prompt, context="fresh"|"fork")`; child = plain Agent, no recursion, only final text returns to the parent.
- [x] **2.7 Slash commands + template library** *(done 2026-07-06; note 09)*: `commands/*.md` as `/name` with `{{args}}`; builtins first. (Direct ancestor of Stage 3.2.)
- [x] **2.8 Permissions v2** *(done 2026-07-06; note 10)*: `harness.toml` allow/ask/deny per tool, fail-closed precedence, `-y` never overrides deny.
- [x] **2.9 Stretch — the "feels like Claude Code" set** *(done 2026-07-07; notes 11–13; picked up after the owner set direction: interleaved narration + thinking visibility + local smartness before Stage 3)*:
  - **2.9a Visible mind** (note 11): preamble content emitted *before* tool calls run (was silently swallowed); thinking (`reasoning` / `reasoning_content` / `<think>` dialects) shown dim and stripped from history — a per-turn scratchpad, never re-sent or persisted; `finish_reason: length` gets one "act, don't think out loud" nudge (`/no_think` soft switch) instead of killing the turn; `max_tokens` is per-provider config (ollama 4096 — thinking headroom).
  - **2.9b Streaming** (note 12): SSE deltas — thinking and answer stream live token by token; tool calls assemble by `index` and only execute complete; `normalize_reply` stays the single normalization path streamed or not; subagents use a non-streaming model instance.
  - **2.9c Todo tool** (note 13): TodoWrite copied — external plan with replace semantics, `[ ]/[>]/[x]` checklist rendered for the human and returned to the model (the steering effect).
  - *Still consciously skipped:* pre/post-tool hooks; MCP client; Anthropic prompt caching (becomes relevant when the Anthropic key arrives).

**Exit criteria (the eval gate):** a scripted acceptance suite (~5–10 small tasks, grown from the Stage 1 three) runs with one command and passes on two providers. Only then does Stage 3 open.

> **Status 2026-07-07: GATE PASSED — 7/7 on both providers.** Local `qwen3:4b-instruct` (the non-thinking 2507 refresh, window raised to 8192): **7/7**, 1,460 output tokens (old thinking qwen3: 5/7 at 13,614 — 10× the cost for a worse score). What flipped it: the model swap + the 2.9a visible-mind fixes (length-nudge, thinking stripped from history) + two of our own bugs found by the bake-off (cp1252 stdout crash on a ✓ character; case-sensitive fizzbuzz verifier). `gemini-2.5-flash-lite`: 7/7 re-confirmed after 2.9. Lesson worth keeping: when a local model "fails", suspect the harness and the verifier first — both local failures on 2026-07-07 were ours.

---

## Stage 3 — Make it mine (one pain at a time)

**Goal:** now that the base is boring, kill the three pains. Spec source: `harness-context-v3.md` §4 (the feature sketches survive even though its Agent-SDK decision didn't). Order = pain order.

- [ ] **3.1 Surgical context ops** (Pain 1 — the payoff):
  - `/prune tools [N]` — delete tool results older than N turns; keep every user/assistant message untouched. Zero model calls, zero token cost — pure list surgery.
  - Auto dump-to-file for known-verbose tool output: full output → disk file; context receives summary + path; the agent re-reads the file only when it needs the detail. (v3 §B — dump, don't truncate.)
  - `/pin` to protect messages; tag messages signal-vs-protocol at creation time so pruning has metadata to work with.
  - **Measure:** signal ratio of live context before/after on a realistic session. Target: flip the 5/95.
- [ ] **3.2 Prompt middleware** (Pain 2): migrate `prompt/` into structured templates with declared slots → an intake step interviews the human for missing slots and current-phase context → assembled prompt shown for approval → dispatched to a fresh worker session. Human-in-the-loop at the harness level.
- [ ] **3.3 Checkpoint & resume for long runs** (v3 §D): periodic checkpoint files during a run; after a crash / rate limit / sleep-mode laptop, a new session boots from the last checkpoint instead of re-exploring. Retires the "previous agent got usage limit 🥺" restart prompt forever.
- [ ] **3.4 Findings channel** (v3 §A + D3): a `report_finding` tool with the fixed schema (`status`, `summary`, `key_evidence`, **`ruled_out` mandatory**, `confidence`, `open_question`, `artifact_paths`); subagents write findings to a shared file; the orchestrator context receives findings only — raw logs stay on disk (already built in 2.3).
- [ ] **3.5 Fork-vs-fresh policy as commands** (v3 §C): `/check` = fork with full context (inside-view consistency); `/audit` = fresh subagent given only the finished artifact (outside-view blind-spot detection; inherited context forbidden).

**Exit criteria:** run one real-but-small research phase end to end inside this harness; compare token spend and signal ratio against the old Claude Code workflow; write the comparison up as a storytelling report.

---

## Reference shelf

### Learning tier (read/study first)

| Resource | Why |
|---|---|
| [How to Build an Agent](https://ampcode.com/notes/how-to-build-an-agent) — Thorsten Ball | The canonical "it's just a loop" tutorial, ~315 lines |
| [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) | ~100-line agent, >74% SWE-bench Verified; bash-only design worth understanding |
| [smolagents](https://github.com/huggingface/smolagents) | HuggingFace's minimal agent library; the CodeAct idea in practice |
| [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) — Anthropic | Workflows vs agents; when NOT to add complexity |
| [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic | Pain 1, written by the seniors: context editing, memory tools, compaction trade-offs |
| [12-factor agents](https://github.com/humanlayer/12-factor-agents) | Production-agent design principles; "own your context window" is literally factor #3 |

### Production source to mine (Stage 2 study material)

| Harness | Language | Especially good for |
|---|---|---|
| [opencode](https://github.com/sst/opencode) | TypeScript | Full modern CLI harness, multi-provider, sessions |
| [crush](https://github.com/charmbracelet/crush) | Go | Same lineage as opencode, different codebase; TUI |
| [gemini-cli](https://github.com/google-gemini/gemini-cli) | TypeScript | Google's take; useful when on the Gemini backend |
| [codex](https://github.com/openai/codex) | Rust | OpenAI's open-source CLI harness; sandboxing model |
| [aider](https://github.com/Aider-AI/aider) | Python | Repo-map idea, edit formats, git integration — and it's Python |
| [OpenHands](https://github.com/All-Hands-AI/OpenHands) | Python | Full agent platform; event-stream architecture |
| [goose](https://github.com/block/goose) | Rust | Block's extensible agent; MCP-native design |

### Papers (skim, don't drown)

| Paper | Takeaway for us |
|---|---|
| ReAct (arXiv 2210.03629) | The original reason+act loop framing |
| SWE-agent (arXiv 2405.15793) | The ACI lesson: tool/interface design beats model IQ (drives 2.2) |
| CodeAct (arXiv 2402.01030) | Code-as-action alternative to JSON tool calls |
| Building Effective AI Coding Agents for the Terminal (arXiv 2603.05344) | 2026 lessons-learned paper on exactly what Stage 2 builds |
| Less Context, Better Agents (arXiv 2606.10209) | 2026: context-efficiency for long-horizon tool agents (drives 3.1) |
| Everything is Context (arXiv 2512.05470) | File-system-as-context-abstraction — the dump-to-file idea, formalized |

---

## Status tracker

| Stage | Status | Started | Finished |
|---|---|---|---|
| 0 — Recon | **done** — labs pass on Ollama + Gemini (owner-verified) | 2026-07-06 | 2026-07-06 |
| 1 — MVP | **done** — acceptance green on Gemini (B also local); walkthrough folded into Stage 2 reviews | 2026-07-06 | 2026-07-06 |
| 2 — Copy the seniors | **done** — features 2.0–2.9 complete; exit gate 7/7 on gemini-2.5-flash-lite AND local qwen3:4b-instruct | 2026-07-06 | 2026-07-07 |
| 3 — Make it mine | unblocked, not started | — | — |

*(Update this table and the "Current status" line in [CLAUDE.md](CLAUDE.md) as milestones complete.)*
