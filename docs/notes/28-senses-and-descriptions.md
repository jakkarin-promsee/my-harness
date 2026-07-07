# 28 — Structured observations, part two: the rest of the senses (2.21b)

> §2.3's second receipt: `list_dir` returns a JSON array of bare names — no
> dir-vs-file marks, no sizes, no hint where to descend. The live M2 failures
> (an agent wandering into `archive/mvp/fixtures/` and reporting the planted
> bug as the project) started exactly there. And tool descriptions still
> describe *parameters*, not *workflow* — they are the only tool-choice
> signal the model has (note 04); teaching them IS the sane version of the
> owner's "RAG for tool choice" (ROADMAP3 §1).

## What the seniors do

- **Claude Code's shipped descriptions** (Piebald corpus): every description
  teaches the next step — Grep's says when to use Glob instead, Read's
  mentions the window, Bash's warns about interactive commands.
- **Anthropic's tool-writing guidance**: descriptions should carry usage
  policy, not just signatures; outputs should suggest the follow-up.
- **gemini-cli / opencode `ls`**: dirs marked, counts shown — orientation
  starts at the directory listing.

## What we build

**`list_dir` structured** (the 2.21a frame convention applied):

    [list_dir] src/harness - 7 entries (5 dirs, 2 files)
    cli/
    core/
    ...
    __init__.py (0 B)
    py.typed (12 B)

Dirs first (marked `/`), then files with sizes; capped at 200 entries with a
count of the rest — a map, not a dump. Errors teach: a missing dir points at
glob; a file path points at read_file.

**`glob` and `grep` get the same frame** — first line reports what happened
and the shape (`[grep] 12 matches for 'pattern' under src/` /
`[glob] 8 files matching '**/*.py' (newest first)`), then the payload lines
(no more raw JSON arrays anywhere in observations). `web_fetch` gains its
one-line frame (`[web_fetch] {url} - {n} chars`) above the Title line.

**Descriptions rewritten to teach workflow** (the whole 8-tool set):
grep points to read_file for context; glob names the newest-first ordering
and points to grep for content search; list_dir says "orient before
descending"; write_file defers to edit_file for small changes; run_shell
warns about interactive commands; web_fetch says when (URL known / docs
lookup). read_file's already teaches (2.21a).

## How we know it works

1. FakeModel-free snapshot tests (pure functions): the three new frames,
   dir/file ordering + sizes, the entry cap, the teaching errors. Existing
   JSON-shape tests updated deliberately.
2. Gate green on the regression lane (13 tasks — D-grep and F-glob verify the
   agent can still *use* the reframed outputs); museum re-run recorded for
   the before/after table.

## Results (2026-07-08)

- **167 offline tests green** (six shape-tests updated deliberately — no more
  raw JSON arrays anywhere in observations; new snapshots: dirs-first with
  sizes, the entry cap, grep/glob/web_fetch frames, teaching errors).
- **Local core 13/13. Flash-lite core 13/13** — even the known-flaky pair
  (K, I) landed well this round; problem.md #2 stands (coin-flips stay
  coin-flips until N says otherwise).
- **Flash museum 3/3 tasks by majority** (M1 3/3, M2 3/3, M3 2/3 this
  sample — M3 hovers between 2/3 and 3/3 across samples; the wandering that
  remains is attention, 2.23's territory, and where-am-I, 2.22's).
- The `json` import left `basic.py` with the last JSON array — observations
  now speak one dialect: frame line, then payload lines.
