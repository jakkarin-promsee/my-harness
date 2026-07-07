# 29 — Orientation: the project map (2.22)

> The honest core of the owner's "RAG for files" idea (ROADMAP3 §1): the
> model doesn't fail to *find* text — grep finds it — it fails to know
> **where it is**. §2.4's receipt: the first message carries cwd + date +
> branch + AGENTS.md, and nothing about the *shape* of the project. Every
> task starts with a blind list_dir-flail (the live M2 sessions walked into
> `archive/mvp/fixtures/` and called it the project).

## What the seniors do

- **gemini-cli** ships a directory snapshot in the first message — a bounded
  tree, not an index.
- **aider**'s repo map is the heavyweight cousin (tree-sitter symbols) —
  consciously skipped (2R §6 stands: that's monorepo-editing machinery).
- **Claude Code** is famously index-free: orientation comes from CLAUDE.md
  (a human-written map) + agentic search. Our AGENTS.md is that file's
  runtime twin.

## What we build

1. **A bounded directory snapshot in the assembled prompt**, tier-sized
   (note 24's ladder decides how generous):
   - `micro`: one line — top-level dirs + file count (~30 tokens).
   - `compact`+: one line per top-level dir with up to 8 children
     (`dir/: child/, file.py, ... (+N more)`), `SKIP_DIRS` respected
     (imported from tools — one fact, one home), ~25 lines cap
     (~150–250 tokens, counted in the whole-first-call budget).
   - Appended to the environment block at assembly: it's exactly a "fact the
     model shouldn't burn a tool call asking".
2. **The AGENTS.md convention documented**: its first section should be a
   *map of the project* — the runtime twin of note 15's CLAUDE.md-is-a-map
   rule. The harness already injects the file (2.4); the convention makes it
   load-bearing. Our own AGENTS.md gets the map section as the worked
   example.

## How we know it works — a real before/after

New gate task **N-orientation**, on a committed multi-folder fixture
(`acceptance/fixtures/oriented/`: `app/`, `config/`, `docs/`, `tests/`).
The ask: *"the retry count is configured somewhere - find it and set it
to 5"* — deliberately grep-resistant (the config key is `max_attempts`, so
grepping "retry" misses; the model must *navigate*: config/ → settings.toml).
Verifier checks the file on disk; docs/USAGE.md contains a pathless hint as
the trap a wanderer falls into.

Protocol (red-team #12): N=3 per lane, **before** the snapshot ships and
**after**, same everything else; the proxy for "tool calls to first correct
read" is mean input tokens (the runner already reports it). Museum M2 re-run
recorded (orientation's museum owner). Plus FakeModel tests for the snapshot
shape, caps, tier sizing, and SKIP_DIRS.

## Results (2026-07-08) — the before/after, N=3 per cell

| Lane | Before (no map) | After (map) | Delta |
|---|---|---|---|
| flash (standard map) | 2/3 · 32,781 in/run · 15.0s · $0.0126 | **3/3 · 16,716 in/run · 7.2s · $0.0062** | verdict flipped, tokens/wall/$ **halved** |
| local (micro one-liner) | 2/3 · 20,305 in/run · 83.8s | 2/3 · 15,865 in/run · 74.9s | score flat, −22 % tokens |

- The flash run is the cleanest possible demonstration of §3.6: the model
  never failed to *find* text — it failed to know where it was. One
  ~200-token map bought back 16k input tokens per run.
- Local's one-line micro map helps less (it names dirs, not children) —
  the right trade on an 8K window; recorded, not "fixed".
- **171 offline tests green** (snapshot shape/caps/SKIP_DIRS/tier sizing;
  operators get the map, `backbone: false` roles don't).
- **Core gates: local 14/14** (N-orientation joins the suite),
  flash-lite 12/14 (the known pair I+K, problem.md #2 — same coins,
  same flips). **Museum M2 on flash: 3/3** under the map.
- AGENTS.md now leads with its Map section — the convention documented by
  being followed (the runtime twin of note 15's CLAUDE.md-is-a-map rule).
