# 25 — Voice & effort: the two knobs (2.19)

> The owner's complaint "Gemini speaks too less" is a **voice** problem; his
> "may need even max effort" instinct is an **effort** setting. GPT-5 ships
> them as two separate API params (`verbosity` vs `reasoning_effort`) — the
> proof they're different axes (ROADMAP3 §3.3). We build both, orthogonal.

## What the seniors do

- **GPT-5**: `verbosity` (how much to say) and `reasoning_effort` (how hard to
  think) as distinct API parameters.
- **Claude Code**: output styles — prompt-level modes ("Explanatory" narrates
  and teaches) — plus `/effort` for the thinking budget. Voice lives in the
  prompt; effort lives on the wire.
- **opencode `gemini.txt`**: the counter-example — *"fewer than 3 lines of
  text output per response"*. Gemini is terse by nature AND by nurture; we
  choose the opposite nurture.
- On Gemini's wire, effort has a native param (`reasoning_effort` — note 22's
  probe (a) confirmed `"none"` disables flash's default thinking); voice has
  none — it must be a prompt section. The portable path.

## What we build

**Voice** — the ladder's style section becomes swappable. Marker names carry
the variant (`style-quiet` / `style-normal` / `style-explain`, all `tier:
micro`); assembly collapses them into the one `style` slot matching the
active voice. Same one-file, zero-duplication rule as the tiers.

- `quiet`: scripted-run terseness — but the 2.9a narration floor stands
  (one line before each tool call was a hard-won fix; `quiet` cannot drop it).
- `normal`: 2.18a's style text (outcome-first, concrete, no filler).
- `explain` — **the Gemini default**, the owner's actual wish: narrate the
  plan before acting, say what each significant result changed, teach as you
  go (name the files and why they matter), close with what was done / how it
  was verified / what's left open.
- Selection mirrors the ladder exactly: per-provider default (`gemini* →
  explain`, `ollama → normal` — narration costs window on 8K), per-agent
  `voice:` frontmatter, `/voice` at runtime (new session file, the `/agent`
  precedent). The acceptance runner grows `--voice` (and `--think`, which
  2.20's grid needs anyway).

**Effort** — smaller than it looks (red-team #16): the compat adapter already
passes `low/medium/high` through and maps `on → "medium"`. New: **`off` →
`reasoning_effort: "none"`** — the missing off-switch for flash's default
thinking, gated on probe (a) which CONFIRMED the wire honors it (note 22).
Native `verbosity` params (GPT-5) noted as a future mapping; not built.

**The meter learns thinking accounting** — probe (b) found no usage split,
but the split is derivable exactly: `thinking = total − prompt − completion`.
The REPL meter now prints `/ N think` when nonzero (the runner already does);
Ollama reports totals only, honestly labeled (nothing to derive, `eval_count`
lumps everything).

## How we know it works

1. Adapter test: `think="off"` → `reasoning_effort: "none"` in the body;
   `None` still sends nothing (flash-lite must not pay for a param it
   doesn't need).
2. Context tests: exactly one style section per assembled prompt; `explain`
   text only at `voice=explain`; unknown voice raises loudly.
3. Live A/B (the acceptance ROADMAP3 names): M2-orient-summary on
   `gemini-flash` at `quiet` vs `explain`, N=3 — the narration delta and its
   $ price, recorded below. And `/think off` on flash zeroes the derived
   thinking count through OUR adapter (the probe proved the wire; this
   proves the plumbing).

## Results (2026-07-08)

- **161 offline tests green** (the 2.12 off-sends-nothing contract updated
  deliberately: `off` → `"none"` is the point of the feature).
- **`/think off` zeroes flash's hidden thinking through OUR adapter**:
  M1 on `gemini-flash` × N=3 with `--think off` = **0 think tokens** in all
  runs (same task at defaults: 32–144); still 3/3 PASS. The probe proved the
  wire; this proves the plumbing.
- **The voice A/B (M2-orient-summary, flash, N=3 per arm):**

| Voice | Verdict | Mean out/run | $/run | Wall |
|---|---|---|---|---|
| quiet | FAIL 1/3 | 385 | ~$0.0033 | 5.7s |
| **explain** | **PASS 2/3** | 903 (×2.3) | ~$0.0058 (+75 %) | 10.5s |

  The narration voice doesn't just *feel* better — it **flips the museum
  verdict**: narrating the plan makes flash actually explore, and naming
  files as it goes puts the facts in the final summary. H3 from the 2.20
  hypothesis list just got its first evidence early: part of the "felt
  dumbness" was the terse voice hiding (and skipping) the work. Price of
  generosity: ~2.3× output tokens — still under a cent a run.
- Meter: the REPL now prints `/ N think` per call and per session (derived);
  Ollama shows totals only, honestly.
- **Regression gates:** local core 10/11 — C-find-fix-prove failed once, then
  re-ran **3/3** at N=3 (local's assembled prompt is byte-identical to
  2.18b's; verdict: 4B variance, core effectively green). Flash-lite core 10/11 — I lost the
  handoff line under `explain` ("close with a summary" fights "MUST end with
  exactly this line"), so `plan` pins `voice: normal` in frontmatter; even
  then I stays a ~50 % coin-flip on lite across re-runs while the PRIMARY is
  clean (flash: I 3/3, 10k in, 8s). K+I are now jointly recorded as
  lite-fragile in problem.md #2 — the two-lane policy's real lesson: the
  regression lane catches OUR breakage; role-constraint reliability belongs
  to the quality lane.
