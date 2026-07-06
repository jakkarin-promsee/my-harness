# Research Harness — Context Brief (v3)

> **Read this first.** This is the context primer for any agent (human or AI) touching this project.
> This is NOT an automation pipeline. It is a hand-driven exploratory-research harness built on the **Claude Agent SDK**.
> The human orchestrates every session manually. The harness handles plumbing, never judgment.
>
> **v3 change:** D2 (billing) rewritten. The Agent SDK monthly-credit split described in v2 was announced for June 15, 2026 but **paused by Anthropic on that same day** and has not taken effect. Agent SDK / `claude -p` usage currently draws from the same subscription pool as interactive use — there is no separate credit to claim. See D2 below. Everything else in v2 is unchanged.

---

## 1. The Workflow This Must Serve

- The work is **exploratory research**. Direction is genuinely unknown at session start — sessions figure out *what the plan should be*, they don't execute a fixed plan.
- The natural loop is **"look at results, think, then decide the next direction."** Any design that forces pre-committing to a direction before seeing results is wrong for this workflow.
- Typical session shape today: one long-context planning agent → one or more execution agents (often running overnight) → one summarizing agent. Handoff between them is via markdown files. This 3-role pattern stays; the harness formalizes its communication layer.
- Human-in-the-loop is a feature, not a bug. The harness must make pausing-to-think **cheap**, not eliminate it.

## 2. The Core Problem (context economics)

Measured on a typical long session (500–900k tokens on Opus, 1M context):

- **~30k tokens (~5%)** = signal: written .md files, design decisions, conclusions.
- **~400–600k tokens (~95%)** = noise: tool-call protocol overhead, raw file dumps already summarized elsewhere, shell/test output resolved and never referenced again.

Two consequences:

1. **Cache-expiry cost spike.** Prompt cache default TTL is ~5 min from the last call. Stepping away to think (which this workflow requires) invalidates it; the next turn — even a trivial "continue" — reprocesses the full context. Single-turn spikes of 10–30% of a 5-hour usage window were observed.
2. **Compaction is too late.** It cleans noise after it entered context. The fix must prevent noise from entering the *shared* stream in the first place → restructure the inter-agent communication layer.

## 3. Decisions Already Made (do not relitigate)

**D1 — Build on the Claude Agent SDK, not raw API, not from scratch.**
~90% of a harness (agent loop, tool execution, permission gating, context assembly, compaction, subagent isolation) is already implemented and maintained by Anthropic. The actual pain point — the inter-agent communication schema — is application-layer and must be built either way. Build only that ~10%.
Research infra must be boring: when an experiment result looks weird, the question must never be "or is my harness buggy?"

**D2 — Billing path: subscription only, one shared usage pool (revised).**
Anthropic announced a split (Agent SDK usage moving to a separate monthly dollar credit, billed at standard API rates) for June 15, 2026 — but paused it on the day it was due to take effect. Per Anthropic's Help Center, the change "is not taking effect" and Agent SDK / `claude -p` / third-party Agent SDK apps continue drawing from the **same subscription usage limits as interactive use**, exactly as before. There is no separate credit, nothing to opt into, and no separate budget for SDK usage. Anthropic says it's reworking the plan and will give advance notice before anything changes — treat this as delayed, not cancelled, and re-verify before relying on it long-term.
Plan: Max 5x, $100/month (one shared usage pool for chat + interactive Claude Code + this harness's Agent SDK sessions).
Operational rules:
- **No credit to claim** — skip that step entirely.
- Because there's only one pool, overnight execution-agent runs (§1) draw down the *same* limit used for daily interactive chat/Claude Code work. Budget accordingly — a long unattended run can leave little headroom for same-window interactive use, and vice versa.
- Ensure `ANTHROPIC_API_KEY` is **unset** in the harness environment — this is still critical. If set, it silently overrides subscription auth and the SDK bills at full pay-as-you-go API rates instead of drawing from the Max plan.
- If usage volume ever outgrows what the shared pool can sustain, the documented alternative is a separate Claude Platform API key with pay-as-you-go billing (predictable but no subscription discount) — not a fallback credit.
- Re-check https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan before scaling usage; this is the exact area Anthropic has said is still in flux.

**D3 — Orchestrator reads summaries by default, raw on demand.**
(v1 diagram said the orchestrator sees "full raw context" — that recreates the bloat one level up. Corrected.)
Every agent's raw transcript/logs are persisted to disk per agent. The orchestrator's context receives only structured findings; the human drills into raw logs by opening files, not by loading them into context.

```
              ┌──────────────────────────────┐
              │         orchestrator          │  ← human, day to day,
              │    (hand-driven, not auto)    │     manual prompts
              └──────────────┬────────────────┘
                 findings only (schema below)
          ┌────────────────┼────────────────┐
          ▼                 ▼                 ▼
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ Agent A  │     │ Agent B  │     │ Agent C  │  ← own full context;
    │ (dir. 1) │     │ (dir. 2) │     │ (dir. 3) │     raw logs → disk,
    └────┬─────┘     └────┬─────┘     └────┬─────┘     never shared stream
         └── report_finding() ──┬──────────┘
                                ▼
              shared findings file (schema-controlled)
                                ▼
        orchestrator reads findings → human decides next direction
        (raw per-agent logs on disk, inspectable on demand)
```

## 4. Components to Build

### A. `report_finding` — in-process MCP tool (the only inter-agent channel)

```json
{
  "agent_id": "explore-direction-2",
  "status": "blocked | partial | complete",
  "summary": "what was concluded, not how — no raw logs",
  "key_evidence": ["1-line facts/metrics that support the conclusion"],
  "ruled_out": ["direction/approach that was tried and killed, and WHY"],
  "confidence": "low | medium | high",
  "open_question": "string or null",
  "artifact_paths": ["files carrying the full depth"]
}
```

Design notes:
- `ruled_out` is mandatory when applicable. Negative results are the highest-value output of exploration and the first thing lost in free-form summaries. Without this field, the next agent re-walks dead ends.
- Depth lives in `artifact_paths`, not in `summary`. Summary states conclusions; artifacts carry reasoning.

### B. Verbose-output diet — dump-to-file, not truncate

For known-verbose tool output (test runners, long reads, shell dumps): write the **full output to a file**, inject only `summary + file path` into context. The agent re-reads the file when it needs detail (e.g. a stack trace after a failing test).
Explicitly NOT hard truncation in a `PostToolUse` hook — the calling agent itself often needs the full output on its next turn; truncation destroys information permanently, dump-to-file defers it.

### C. Fork vs. fresh-subagent policy — explicit, not model judgment

- **Inside-view checks** (consistency with prior decisions) → `fork`, full inherited context.
- **Outside-view checks** (blind-spot detection) → fresh named subagent, given **only** the finished artifact (e.g. `design.md`). Inherited context is forbidden here — it imports the exact assumptions being audited.

### D. Session checkpointing

Incremental checkpoint files during long runs (not only end-of-session handoff), so a run killed mid-way (rate limit, crash, sleep-mode laptop) resumes from the last checkpoint instead of restarting the exploratory arc.

### E. Cache TTL for the "reading and thinking" gap — VERIFY FIRST

- The API supports extended caching: `"cache_control": {"type": "ephemeral", "ttl": "1h"}`. Pricing: 1h write = 2.0× input (vs 1.25× for 5-min), reads = 0.10×. Break-even ≈ 2 hits within the hour — trivially met by a think-then-continue loop.
- **Open question:** the Agent SDK wraps the Claude Code CLI, which assembles requests itself. Whether it exposes `cache_control` / TTL directly is unverified. Check SDK docs (docs.claude.com) before treating E as buildable. If not exposed, mitigations: keep sessions shorter via B, or cheap keep-alive pings during think gaps.

## 5. Non-Goals

- No scheduler, no unattended "run phase N" automation.
- No removing human judgment from direction decisions — orchestration stays manual.
- No replacing the SDK's built-in loop/tools/compaction — only the schema layer on top.
- (Separate hobby project, out of scope here: a from-scratch toy agent loop on cheap models, for learning only. It never touches research work.)

## 6. Prototype Plan — cheapest lever first

1. **Day 0 — billing + feasibility check (no code).** Confirm auth path (no stray `ANTHROPIC_API_KEY`, subscription auth active); confirm the shared usage pool assumption in D2 hasn't changed since; check whether cache TTL is controllable from the SDK. There is no credit-claim step (see D2). Re-measure the cost pain after this alone before building anything.
2. **Prototype 1 — schema channel.** Two agents with `report_finding`, communicating only through the shared findings file. No shared raw context.
3. **Prototype 2 — output diet.** Dump-to-file handling for one known-verbose tool type; measure actual context savings vs. baseline.
4. **Validation gate.** Manually verify the outside-view fresh subagent catches at least one thing the inside-view fork missed. If it doesn't, fix the schema (likely: artifacts too thin, or context leaking in) **before** scaling agent count.

## 7. Success Criteria

- A think-gap of 10–30 min mid-session no longer causes a full-context reprocess spike (via E). D2's separate-budget mitigation is currently unavailable (paused) — E carries this criterion alone until/unless a credit split returns.
- Shared/orchestrator context per session is dominated by findings, not transport noise (target: flip the current 5/95 signal ratio in the shared stream).
- Zero re-explored dead ends across agents within a phase (`ruled_out` doing its job).
- The human never debugs the harness during a research session.
