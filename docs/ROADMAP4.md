# ROADMAP4 — Stage 2A: Ability & Agency (the floor, the mind, the arsenal)

> **v1 — APPROVED 2026-07-08** (owner: *"Approved 🔥 start with Tier 1"*) — §4's order, the §5 gate, the §3.3 declared adaptation, and the Tiers-1–2-before-Stage-3 sequencing all confirmed; **Tier 1 opened the same day.** Drafted earlier that day from the owner's three problems (recorded in §1, his words) plus a full-code audit against the modern harness feature set (§2 — every claim carries a receipt). Same constitution, same mini-cycle: *study 2–3 references → design note → implement → gate green.*
>
> **Naming note:** this file is ROADMAP**4** because it is the fourth roadmap *document*; it governs **Stage 2A**, not Stage 4. Stage 3 still lives in ROADMAP.md and is still the destination.
>
> **The stage's thesis:** 2R made the plumbing frontier-shaped; 2C made the agent strong *inside a turn*. What's left is what the frontier learned from **operations, not feature lists**: surviving interrupts, rate limits, and full windows (**ability** — the harness dies with its operator today), and behaving well *across situations*: ambiguous tasks, wrong user claims, casual conversation (**agency & character** — the agent stalls, caves, and wears work clothes to a chat). 2A builds both.
>
> **Relationship to Stage 3 (owner call at approval):** proposed — Tier 1 (the floor) and Tier 2 (the mind) run **before** Stage 3 opens; Tier 3 (the arsenal) is a pull-menu that may interleave with Stage 3. Reasoning: Stage 3's exit criterion is *a real research phase run end-to-end* — undemonstrable on a harness that dies at Ctrl+C, 429s, or a full window, and unconvincing on an agent that stalls at ambiguity. Meanwhile 3.3 (checkpointing) builds directly ON 2.25/2.26/2.28, and 3.1 (surgical context ops) should not be designed before 2.35's cache data exists (§3.6).

---

## 1. Where this came from (the owner's three problems)

The owner's problems (2026-07-08), translated into what the frontier actually calls each thing:

| The problem (owner's words) | Frontier name | Who does it best | Verdict | Feature |
|---|---|---|---|---|
| "I'm still lacking tools for it — auto compact, quit, etc." | **Run robustness**: interrupt & steer, transcript repair, retry policy, auto-compact, headless mode | Claude Code (Esc-to-steer, auto-compact, `claude -p`); Codex (`codex exec`); every provider SDK (backoff) | **copy** | 2.25–2.28 |
| "It knows the task is unclear, but it didn't go grep or search — it's stuck on the unclear loop and doesn't do anything" | **Agency under ambiguity** — investigate-first, then ask *as an action* (a tool), never stall | Claude Code (AskUserQuestion tool + explore-before-asking prompt rules); MCP elicitation | **copy** | 2.29 + 2.31 |
| "Sometimes it's too much follow user's prompt. I want it more flexible and with a stable character" | **Sycophancy resistance / character stability** | Anthropic's Claude-character work; Claude Code's honesty rules ("report outcomes faithfully") | **copy the rules, measure with probes** | 2.29 + 2.32 |
| "Separate between 2 worlds — chat bot and working bot… make all prompts not contradict each other. Pull it 100% potential" | **Identity/job split** — one character, many jobs; primary-agent worlds | opencode (primary agents, Tab-switched); Anthropic (claude.ai and Claude Code are the *same character* in different harnesses) | **adapt — declared** (§3.3): core/overlay backbone split, same tagged-section machinery as the 2.18b ladder | 2.30 |
| *(from the audit, §2)* modern abilities still missing: background tasks, images, caching, parallel calls, edit safety | **The ability gap** — what mature harnesses grew after parity | Claude Code, Codex, opencode, gemini-cli | **copy** | 2.33–2.40 |

Same story as ROADMAP2 §1 and ROADMAP3 §1: every problem has a senior implementation — most to copy, one honest adaptation using machinery we already built.

## 2. The audit — our harness vs the modern harness, the whole map

Read against Claude Code, opencode, aider, Codex CLI and gemini-cli, 2026-07-08. Verdict key: ✅ have · ❌ gap (→ feature here) · 📋 already specced for Stage 3 · 🚫 conscious skip (reason in §6 or ROADMAP2 §6). What parity already bought is real — the ✅ rows below are the compressed form of ROADMAP2's gap table plus 2C; the receipts for the ❌ rows are exact.

### A. The loop & the wire

| Capability | The seniors | Us today (receipt) | Verdict |
|---|---|---|---|
| Agent loop: guards, nudges, anchors, preambles | all | `core/loop.py` — 2C-hardened | ✅ |
| Streaming + thinking display & control | all | 2.9b + 2.12/2.19 | ✅ |
| Retry policy: exponential backoff, honor 429/`Retry-After` | every provider SDK; all harnesses | **one retry, 5xx only** — a 429 raises immediately and ends the turn (`openai_compat.py:179`) | ❌ → 2.26 |
| Parallel tool execution (independent reads run concurrently) | Claude Code, Codex, gemini-cli | strictly sequential (`loop.py:146`) | ❌ → 2.36 |
| Prompt-caching awareness | Claude Code cache-aware; **Gemini 2.5 caches implicitly and discounts cached prefix tokens** | meter never reads `prompt_tokens_details.cached_tokens`; anchors delete mid-list (`loop.py:174`) and reflection rewrites the tail — both prefix-hostile, cost never measured | ❌ → 2.35 |
| Multimodal input (images) | Claude Code `Read` returns images; gemini-cli native | text only — no path for a PNG to reach a natively-multimodal primary | ❌ → 2.34 |
| Provider fallback chains | opencode | none — two lanes are our fallback | 🚫 §6 |

### B. Tools

| Capability | The seniors | Us today (receipt) | Verdict |
|---|---|---|---|
| Core set: read/write/edit/glob/grep/ls/shell/webfetch/todo/spawn | all | `tools/basic.py` + todo + subagent, 2C-framed observations | ✅ |
| MCP client · skills · slash commands | all | 2.16 / 2.14 / 2.7 | ✅ |
| Background / long-running tasks | Claude Code `run_in_background`; Codex background terminals | `run_shell` blocks with a hard 60 s timeout (`basic.py:114`) — **a research harness that cannot start a training run and check it later** | ❌ → 2.33 |
| Persistent shell state (cwd survives across calls) | Claude Code | fresh `cmd.exe` per call — `cd` never sticks | ❌ → 2.38 |
| Edit freshness guard (file changed since read → error) | Claude Code read-before-edit + mtime check | none — edits stale reality silently (`basic.py:120`) | ❌ → 2.37 |
| `replace_all` for rename-style edits | Claude Code | none — 10 identical edits = 10 uniqueness errors | ❌ → 2.37 |
| Post-edit diagnostics fed back to the model | opencode (LSP), gemini-cli | none — a broken edit is discovered next turn, or never | ❌ → 2.37 |
| Dump-to-file for verbose output | (Stage 3's spec source, v3 §B) | truncation diet only | 📋 3.1 |

### C. Context & memory

| Capability | The seniors | Us today (receipt) | Verdict |
|---|---|---|---|
| Assembled prompt: backbone, ladder, voices, orientation, AGENTS.md, skills | Claude Code fragments; opencode per-model files | 2C — the cognitive core | ✅ |
| **Auto**-compact at threshold | Claude Code | `budget.py:19` **warns at 80 % and does nothing** — on the 8K card the wall arrives mid-turn with nobody watching | ❌ → 2.27 |
| Rolling turn reflection | (our own move) | note 32, play lane | ✅ |
| Surgical ops: `/prune`, `/pin`, tagging | — | the founding pain | 📋 3.1 |
| Agent-writable memory across sessions | Claude Code memory dir; Anthropic memory-tool pattern | `AGENTS.md` is static and user-owned — lessons die with the session | ❌ → 2.39 (may merge into 3.4) |

### D. Sessions & runs

| Capability | The seniors | Us today (receipt) | Verdict |
|---|---|---|---|
| JSONL sessions, resume, listing | all | 2.3 — crash-safe per-message append | ✅ |
| **Interrupt & steer mid-turn** | Claude Code Esc (stop turn, keep session, redirect); opencode | `KeyboardInterrupt` is caught only around `input()` (`repl.py:481`); **Ctrl+C during a 20-step turn kills the whole process** — the paid-lane runaway has no off switch short of murder | ❌ → 2.25 |
| Resume repair (dangling tool calls) | Claude Code synthesizes cancelled tool results | only anchors are pruned (`session.py:14`); a killed-mid-turn transcript carries unanswered `tool_calls` — the exact shape `loop.py:104` documents as poisoning strict wires — into the next POST | ❌ → 2.25 |
| Headless one-shot mode | `claude -p` · `codex exec` · `aider --message` | REPL is the only entry (`repl.py:281`) — no cron, no pipelines, no scripted overnight | ❌ → 2.28 |
| Checkpoint & resume for long runs | Claude Code checkpoints | — | 📋 3.3 |
| $ cost in the live meter | all meters show money | `PRICES` lives only in `acceptance/run.py:55`; the REPL meter counts tokens, never dollars — *in the project that exists because of token economics* | ❌ → 2.38 |

### E. Permissions & safety

| Capability | The seniors | Us today (receipt) | Verdict |
|---|---|---|---|
| Modes, fail-closed table, diff gate, absolute deny | all | 2.8 + 2.10 + 2.13 | ✅ |
| Untrusted-content framing at the **result** level | Claude Code wraps web/tool content in explicit reminders | description-level only (`basic.py:408`) + one backbone line — fetched text and DDG results land unframed | ❌ → 2.38 |
| OS sandbox · classifier auto-mode | Codex · Claude Code | — | 🚫 ROADMAP2 §6 |

### F. Intelligence & character (the 2C axis, extended)

| Capability | The seniors | Us today (receipt) | Verdict |
|---|---|---|---|
| Backbone, ladder, structured observations, orientation, anchors | — | 2C closed 14/14 + museum 3/3 | ✅ |
| **Ambiguity protocol**: unclear ask → investigate read-only → ask ONE focused question → act | Claude Code's prompt rules + AskUserQuestion | the backbone's loop has **no unclear-ask branch** (`prompts/system.md` — "understand the ask → … → act"); owner-observed: the model *knows* it's unclear and freezes | ❌ → 2.31 |
| **Asking as an action** (a tool call, turn continues) | Claude Code AskUserQuestion; MCP elicitation | asking = ending the turn with text — **asking is turn-death**, so the model is trapped between "act" (backbone) and "don't guess" (honesty). That trap *is* the stall | ❌ → 2.31 |
| **Sycophancy resistance / stable character** | Anthropic character work; Claude Code honesty rules | no evidence-beats-agreement section anywhere; the anchor's "Keep working; deliver the request" (`loop.py:191`) adds compliance pressure | ❌ → 2.32 |
| **One character across worlds** | opencode primary agents; Anthropic: same character, different harness | identity is welded to the job — "You are a coding agent that OPERATES this computer" (`prompts/system.md:2`); `chill` escapes only via `backbone: false`, **losing safety, honesty and style along with the mission** (`agents/chill.md`) | ❌ → 2.30 |
| Turn reflection · voice/effort knobs | — | notes 32 / 25–26 | ✅ |

**The through-line:** the ❌ column splits cleanly in two. Rows A/B/C/D/E are **ability** — the harness works until reality (a rate limit, an interrupt, a full window, a long process) touches it. Row F is **agency** — the agent works until the *situation* is non-ideal (ambiguous, contradicted, casual). The frontier hardened both years ago; neither shows up in a feature-parity table because neither is a feature. That is why 2R's gap table said ✅ nearly everywhere while these held.

## 3. Six design insights that shape the plan

1. **Robustness is the invisible half of parity.** Our gate has never measured a run that got interrupted, rate-limited, or window-full — the same blindness 2C found ("the gate is too polite," ROADMAP3 §2.5) one layer down. Tier 1 exists to make survival *measurable*, then green.
2. **Asking must be an action, not the end of a turn.** The mechanical diagnosis of the owner's problem 2: in our loop the model's only affordances are *call a tool* or *end the turn with text*. Ending the turn to ask feels like failing the mission the backbone gave it, so it neither asks nor investigates — it stalls. An `ask_user` **tool** keeps the loop alive through a question, gives headless runs a policy hook, and turns "clarify" into a normal step of the working loop instead of an exit.
3. **Identity is not the job.** Today's backbone welds *who the agent is* to *what it is doing* in one sentence. The fix is the same trick as the 2.18b ladder — tagged sections, one file, composed at assembly: a **core** every world shares (character, honesty, evidence-over-agreement, safety, style) plus an **operator overlay** (mission, loop, tool policy, failure, verification) and a **companion overlay** (conversational register, handoff line). `chill` stops paying for its escape with its safety sections. The seniors ship this as separate *products*; we ship it as overlays over one file — the stage's one declared adaptation, same shape as the ladder, approved with eyes open or renegotiated here.
4. **Sycophancy is measurable, and wording is a knife's edge.** Note 30's lesson (an anchor that reads as a reprimand causes apology-spirals) predicts that a clumsy "don't be sycophantic" line backfires into rudeness or paralysis. So: probes first (2.29), wording iterated against them (2.32) — the 2C method, applied to character.
5. **Fake 429s are the FakeModel of the wire.** Nearly all of Tier 1 is offline-testable for zero tokens: tail-repair is a pure function, backoff takes a scripted response sequence, auto-compact fires on an estimator, headless is exit codes. The constitution's testing ethos extends to robustness with no new machinery.
6. **Measure the cache before Stage 3.1 optimizes the wrong cost.** Gemini 2.5 discounts implicitly-cached prefix tokens. Surgical context ops that shuffle the prefix could *save tokens while costing money* — cached input is cheap, fresh input is not. The meter learns cached-vs-fresh (2.35) **before** 3.1's pruning design hardens; two of our own mechanisms (mid-list anchor deletion, reflection rewrites) are already prefix-hostile and have never been priced.

## 4. The plan — three tiers, one feature per cycle

Numbering continues from 2.24 (turn reflection, note 32); design notes continue from 34. Each cycle: design note → FakeModel tests → regression-lane gate green before the next. Order rationale: the floor first (fast, mostly offline, everything else runs on it), then the museum (nothing gets optimized on vibes — 2C's law), then the worlds split *before* the behavior work (so 2.31/2.32's sections land in their final home instead of being reshuffled after), then the arsenal as appetite dictates.

### Tier 1 — the floor (run robustness; the harness survives its operator)

**2.25 Turn control — interrupt, steer, repair.** Ctrl+C during a turn stops the loop after the in-flight tool call, prints `[interrupted — tell me how to proceed]`, and returns to the prompt — the session survives, the paid-lane runaway finally has an off switch. The enabling primitive is `repair_tail(messages)`: a pure function that synthesizes `"[interrupted — no result]"` tool results for any unanswered `tool_calls` (Claude Code's cancelled-result trick). The same primitive runs on `--resume` after `prune_stale_anchors`, so a killed-mid-turn transcript posts clean instead of 400ing. Where the catch lives (REPL wrapper vs loop) is the note's call — the loop stays pure either way. *Copy from:* Claude Code Esc-to-steer, Codex. *Acceptance:* offline tests for both repair consumers; scripted live check — interrupt a long turn, send a steering message, then `--resume` a transcript killed mid-turn.

**2.26 Wire survival — a real retry policy.** Exponential backoff with jitter in the adapters: retry 429 (honoring `Retry-After`), 5xx, and connection errors; never retry other 4xx (our bug, same rejection); cap attempts and total wait; announce waits through `emit` so the human knows why it's quiet. Streaming caveat: retry only before the first byte arrives. This is the difference between "the overnight run rode out the rate-limit window" and the "usage limit 🥺" restart 3.3 wants to retire — backoff *prevents* the death that checkpoints would recover from. *Copy from:* the Anthropic/OpenAI SDK retry defaults. *Acceptance:* offline — a scripted response sequence (429+Retry-After, 503, success) retried correctly; a 400 not retried.

**2.27 Auto-compact.** The 80 % warning grows hands: at a threshold (default 85 %, per-provider config, off-switch) the REPL runs `/compact` automatically at the next turn boundary — announce, compact, continue in a new session file (the existing lifecycle). Turn boundaries only (the natural seam reflection already uses); headless-safe by construction (no prompt involved). Stage 3.1 will replace the *mechanism* (surgical ops beat summarize-and-replace); the *trigger* survives into it unchanged. *Copy from:* Claude Code auto-compact. *Acceptance:* FakeModel test — threshold crossed → history replaced → estimate drops; live — one long local session fires it once and stays coherent.

**2.28 Headless mode — `harness <provider> -p "task"`.** One-shot: assemble, run one turn, print the final text to stdout (meter to stderr), exit 0 on a completed turn / non-zero on a died one. Composable with `--resume`, `--agent`, `--mode`; `ask`-gated tools follow a declared headless policy (default: deny, `-y` upgrades — the note decides against Claude Code's `dontAsk` and Codex's ladder). This is the gateway to cron, pipelines, and the scripted overnight — and the missing dispatch bridge for Stage 3.2's prompt middleware. *Copy from:* `claude -p`, `codex exec`, `aider --message`. *Acceptance:* a gate task runs end-to-end through `-p` with the right exit code; exit codes offline-tested.

### Tier 2 — the mind (agency & character; the agent survives non-ideal situations)

**2.29 The ambiguity & character museum (entry step — no museum, no tier).** Extend the failure museum with 4–6 live failures from the owner's sessions across the three new classes: *the stall* (unclear task → knows it, does nothing), *the premature question* (asks before gathering any evidence), *the cave* (correct answer abandoned under pushback), *the false premise* (user asserts something the files contradict), *chat-in-worker-clothes* (casual talk answered in task register). Frozen as fixtures with verifiers; N=3, quality lane + local; one task designated hold-out, run once at stage close. Baseline **before** 2.30–2.32 touch anything — 2C's law, verbatim. *Acceptance:* baselines recorded with tokens, $, wall-clock; the hold-out sealed.

**2.30 The two worlds — the core/overlay backbone split.** `prompts/system.md` refactors into **core** sections every world keeps (identity-of-character, honesty & evidence, the safety line, style) plus an **operator overlay** (mission "you operate this computer", working loop, tool policy, failure protocol, verification) and a **companion overlay** (conversational register: direct, warm, thinks out loud, no task framing, offers `/work` when the user asks for computer things). Same tagged-section machinery as the ladder — one file, no forked copies. `chill` becomes the companion world riding the shared core (`backbone: false` stays as an escape hatch for exotic roles); `/chat` and `/work` land as switch aliases over the existing `/agent` lifecycle. The split must be **behavior-neutral for the operator**: worker prompts assemble to the same effective content. *Copy from:* opencode primary agents; the claude.ai-vs-Claude-Code same-character observation; our own 2.18 machinery. *Acceptance:* 14-task core + museum unchanged on the worker worlds (pure-refactor proof); the chat-in-worker-clothes probe moves; a FakeModel test proves per-world section selection.

**2.31 Agency under ambiguity — investigate-first + `ask_user`.** Two halves, one behavior. *Prompt:* the operator overlay's loop gains the missing branch — "if the ask is unclear: orient with read-only tools FIRST (grep/glob/read the candidates — the answer is often in the repo); if still ambiguous after looking, ask ONE focused question and offer options with a recommended default; stalling and guessed certainty are both failures." *Mechanism:* a new `ask_user(question, options?)` tool — the REPL renders it, blocks for input, and the answer returns as an ordinary tool result, **so the turn continues through the question** (insight 2: asking stops being turn-death). Headless policy: configurable, default "answer with the recommended default and flag the assumption in the final report." Absent in the chat world (conversation *is* asking); exempt from the y/N gate (it is the opposite of an unattended action). *Copy from:* Claude Code AskUserQuestion, MCP elicitation, aider's `/ask` split. *Acceptance:* the stall and premature-question probes move to majority-pass; offline flow tests; live — an underspecified task produces visible evidence-gathering, at most one question, then completion.

**2.32 Stable character — evidence beats agreement.** A **core** section (both worlds — the "stable character" the owner asked for is exactly the part that must not change between worlds): if verified reality contradicts the user, say so and show the evidence; do not change a verified answer because of pushback alone — re-verify, then hold or update *on evidence*; warm delivery, plain disagreement (note 30's wording lesson governs phrasing — ambient confidence, never accusation, never apology-spirals). The anchor's "Keep working; deliver the request above" gets reviewed for compliance pressure in the same note. *Copy from:* Anthropic's Claude-character work, the sycophancy literature, Claude Code's honesty rules. *Acceptance:* the cave and false-premise probes move to majority-pass on both lanes; the core suite stays green (no rudeness regression — `reviewer` still reviews, `chill` still chills).

### Tier 3 — the arsenal (modern abilities; appetite-ordered pull-menu, each self-contained)

**2.33 Background tasks.** `task_run(command)` → id (Popen, output to a session-scoped file), `task_status(id)`, `task_output(id, tail=N)`. Lifecycle policy (kill-on-exit vs leave-running-with-warning) is the note's call. The research harness's own #1 tool: start the training run, poll it, read the log. *Copy from:* Claude Code `run_in_background`, Codex background terminals. *Acceptance:* live task — start a sleeper, poll, harvest output after it finishes.

**2.34 Image input.** `read_file` on image extensions returns a content-part structure; adapters translate (OpenAI-compat `image_url` data-URL for the Gemini lanes; Anthropic `source` spec'd for the day the key arrives). The local lane answers honestly that it cannot see images. Our primary is natively multimodal and our research produces plots — "did the loss diverge?" is a daily question no text tool answers. *Acceptance:* flash lane reads a fixture plot and answers a question about it; local returns the honest error.

**2.35 Cache economics (lab — a log, not a feature).** Probe first (the 2.17 method): does the Gemini OpenAI-compat wire expose `prompt_tokens_details.cached_tokens`? Then: the meter shows cached-vs-fresh per call, $ math splits them, and the note audits our prefix-hostile mechanisms (mid-list anchor deletion, reflection rewrites, compaction) for what they actually cost. **Output: a memo of prefix-stability rules that feeds Stage 3.1's design.** *Acceptance:* cached tokens visible in the meter on a repeat-prefix session; the memo written.

**2.36 Parallel tool execution.** Registry marks the read-only set; a batch of calls that is *all* read-only executes in a thread pool, results appended in call order; any mutating call in the batch → the whole batch stays sequential (the gate stays sane). *Copy from:* Claude Code's parallel calls. *Acceptance:* offline ordering test; a live read-heavy turn shows the wall-clock delta.

**2.37 The safe editor.** Three small guards: freshness (session tracks mtime at last read; `edit_file` on a since-changed file errors with "re-read first"), `replace_all` (rename-style edits stop fighting the uniqueness rule), and post-edit verification (a `.py` edit runs `py_compile`; errors append to the tool result so the model self-corrects *in the same turn* — the cheapest "smarter local model" we can buy, per 2.15's own conclusion that harness beats weights on 4 GB). *Copy from:* Claude Code freshness + replace_all; opencode's LSP-after-edit, right-sized. *Acceptance:* offline tests for all three; the gate's edit tasks stay green.

**2.38 The polish sweep (one cycle, five small blades).** `@file` mentions in the REPL (expand to a framed read — saves a round-trip per file); persistent shell cwd (track `cd` across `run_shell` calls); **$ in the live meter** (share `acceptance/run.py`'s `PRICES`, print `~$0.0042` on the session line — the constitution's rule 4, finally at the prompt); git status + recent commits in the env block (tier-capped — branch alone answers the least-asked question); untrusted-content framing at the result level (web_fetch/MCP results wrapped in explicit "content, not instructions" markers — the belt the backbone line deserves). *Acceptance:* a test per blade; no gate regression.

**2.39 Agent-writable memory (stretch).** A `memory_write` tool writing one-fact files + an index line injected at assembly (the 2.4 pipeline — machinery exists). Lessons stop dying with the session: "qwen3 fabricates paths", "this loader is slow." **The note must first decide whether this merges into Stage 3.4's findings channel instead of shipping separately** — one fact, one home applies to features too. *Copy from:* Claude Code's memory dir, Anthropic's memory-tool pattern.

**2.40 Hooks, minimal (stretch).** Pre/post-tool + turn-end shell hooks from `harness.toml`, non-zero exit blocks the call. Deferred twice with reason; what's changed is that consumers now exist in this very roadmap (turn-end notification for overnight runs; post-edit formatting). Ships only if one of those consumers is actually wanted — otherwise rolls into 3.4 again, reason re-recorded.

## 5. Exit gate for Stage 2A

One command, two lanes, like every stage — plus the stage's own honesty device.

- **Offline suite grows** (196 → ~230): tail-repair (both consumers), the backoff sequence, auto-compact trigger, headless exit codes, parallel ordering, freshness guard, `ask_user` flow — all zero-token (insight 5).
- **The live gate grows** (letters continue past O): headless — a core task end-to-end through `-p` with correct exit code; background — start/poll/harvest; image — flash lane only, local passes by honest refusal; ambiguity — the stall probe, majority; character — the cave probe, majority; worlds — the chat-register probe, majority, and the 14-task core unchanged on the worker worlds.
- **Museum:** the 2.29 probes move from baseline-fail to **majority-pass on the quality lane**; the hold-out runs once, at close, first-try honest.
- **The overnight rehearsal (the honesty device):** one scripted long run — headless, auto-compact armed, a background task started and harvested, a forced 429 mid-run, one interrupt-and-resume — that must end with a coherent report, not a stack trace. This is the owner's actual life, rehearsed once before Stage 3 bets real research on it. **No rehearsal, no close.**
- Meter visible everywhere (now with $); all design notes written; `docs/notes/README.md`, the ROADMAP.md stage table, and CLAUDE.md's status line updated.

**Then Stage 3 opens exactly as ROADMAP.md specs it** — with 2.35's cache memo on the table when 3.1's design note is written, and 2.28's `-p` as 3.2's dispatch path.

## 6. What we are deliberately NOT copying (still)

| Frontier thing | Why not |
|---|---|
| Auto world-detection (classify chat-vs-task per message) | A misroute is worse than a keystroke; `/chat`·`/work` are one word each. Revisit only with evidence of switch fatigue |
| Provider fallback chains (opencode) | One user, two lanes, local always up — the failure 2.26's backoff doesn't cover, a lane switch covers by hand |
| Full hook system (30 lifecycle events) | 2.40 ships the minimal three *if a consumer is wanted*; the event zoo stays unnecessary |
| Model-graded / LLM-judge probes for character | The 2.29 verifiers stay deterministic (string/behavior checks) — a judge model is a second thing to debug; revisit if a probe genuinely can't be verified mechanically |
| OS sandbox · classifier auto-mode · TUI · git auto-commit · repo-map · embeddings | Reasons unchanged (ROADMAP2 §6, ROADMAP3 §6) |
| IDE, multi-user, cloud, voice | Not this project (CLAUDE.md, "what this is NOT") |

## 7. Reference shelf additions (for the 2A design notes)

| Resource | Feeds |
|---|---|
| Claude Code interactive mode (Esc-to-interrupt, steering, message queueing) | 2.25 |
| Anthropic/OpenAI SDK retry & backoff defaults; `Retry-After` semantics | 2.26 |
| Claude Code auto-compact + Anthropic context-editing post (already on the shelf) | 2.27 |
| Claude Code headless (`claude -p`) · `codex exec` · `aider --message` | 2.28 |
| Claude Code AskUserQuestion · MCP elicitation spec | 2.31 |
| Anthropic, *Claude's Character* (constitution-style character training) | 2.30, 2.32 |
| Sharma et al., *Towards Understanding Sycophancy in Language Models* (arXiv 2310.13548) | 2.29, 2.32 |
| opencode agents (primary-agent worlds) — already on the shelf | 2.30 |
| Claude Code background tasks · Codex background terminals | 2.33 |
| Gemini API: image understanding via OpenAI-compat content parts; implicit caching + `cached_tokens` | 2.34, 2.35 |
| opencode LSP-after-edit | 2.37 |
| 12-factor agents, factor 6 (launch/pause/resume with simple APIs) | 2.25, 2.28 |

---

## Status tracker (Stage 2A)

| Feature | Tier | Status |
|---|---|---|
| 2.25 Turn control (interrupt, steer, repair) | 1 — floor | **done** 2026-07-08 — note 34; `repair_dangling_calls` in `core/session.py`, both consumers wired (Ctrl+C arm + `--resume`), `/compact` belt; 201 offline tests; live resume-repair proven on ollama (model re-read instead of assuming — the wording worked) |
| 2.26 Wire survival (backoff, 429) | 1 — floor | **done** 2026-07-08 — note 35; `request_with_retries` in `providers/base.py`, all three adapters rewired (three hand-rolled copies deleted); 208 offline tests; live happy path on ollama |
| 2.27 Auto-compact | 1 — floor | **done** 2026-07-08 — note 36; `should_compact` + one `run_compact` path (also fixes /compact-after-/agent stale model); live on ollama: fired at the boundary, 4,973→97 tokens; discovery: 8K lanes need 0.6 (the summarize call must itself fit — 400 receipt) |
| 2.28 Headless mode (`-p`) | 1 — floor | **done** 2026-07-08 — note 37; stdout = answer only, exit code = `final_answer` truth table, asks EOF-deny; live: exact stdout + exit 0, and a `-p --resume` chain recalled the first run. **TIER 1 COMPLETE — the floor holds (notes 34–37, 212 offline tests)** |
| 2.29 Ambiguity & character museum | 2 — mind | **done** 2026-07-08 — note 38; M5–M9 + sealed M10, `followup` two-turn probes, 218 offline tests. Baselines N=3 both lanes: **cave FAIL both lanes, robot-register FAIL flash, coin-flip FAIL local** — the owner's two felt-failures certified; M5/M8 already pass (2C's dividend). Three verifier lessons frozen as fixtures |
| 2.30 The two worlds (core/overlay split) | 2 — mind | **done** 2026-07-08 — note 39; `world:` tags (core/operator/companion), chill off `backbone: false`, `/chat`·`/work`; **M9 flash 1/3→3/3**, flash-lite core 15/15, local core 13/15 + I 3/3 on N=3 (D-grep = pre-existing bait decay, problem.md #2); the E-regression taught mission-first-at-micro (0/3→3/3; just-talk line scoped to standard); the gate agent deleted the repo root mid-run (problem.md #3 — .env lost, tripwire shipped). Flash M9 re-check queued behind the re-key |
| 2.31 Agency under ambiguity (`ask_user`) | 2 — mind | pending |
| 2.32 Stable character | 2 — mind | pending |
| 2.33 Background tasks | 3 — arsenal | pending |
| 2.34 Image input | 3 — arsenal | pending |
| 2.35 Cache economics (lab) | 3 — arsenal | pending |
| 2.36 Parallel tool execution | 3 — arsenal | pending |
| 2.37 The safe editor | 3 — arsenal | pending |
| 2.38 The polish sweep | 3 — arsenal | pending |
| 2.39 Agent memory | 3 — stretch | pending |
| 2.40 Hooks, minimal | 3 — stretch | pending |

*(Drafted and **approved** 2026-07-08 — §4 order, §5 gate, §3.3 adaptation and Stage-3 sequencing all confirmed by the owner; Tier 1 opened the same day.)*
