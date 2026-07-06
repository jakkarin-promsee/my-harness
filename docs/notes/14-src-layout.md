# Note 14 — src/ layout: the harness becomes an installable package

> Written 2026-07-07, after Stage 2 closed. Sources studied: the Python Packaging User Guide's "src layout vs flat layout", hatchling's `[tool.hatch.build.targets.wheel] packages`, and how mature CLIs ship an entry point (`[project.scripts]`) instead of relying on `python -m` from the repo root.

## What was the problem

After Stage 2 the root had grown cluttered: the `harness/` package, `tests/`, `acceptance/`, three prose docs, and three "keep but don't touch" dirs (`labs/`, `mvp/`, `prompt/`) all sat side by side. Worse, the package only imported because the **current working directory** happened to be the repo root — `python -m harness` and pytest's `pythonpath = ["."]` both leaned on that. That's the exact "or is my harness buggy?" fragility rule 5 warns against: a stray `cd`, or running from another folder, and imports silently resolve to the wrong thing (or not at all).

## What the seniors do

Real projects use a **src layout**: the importable package lives under `src/`, and the project is *installed* (editable) so `import harness` resolves through the installed distribution, never through "it's in my cwd". The src dir cannot be imported by accident — you're forced to test the same package your users get. Docs live under `docs/`, tests stay at the repo root (pytest convention, not under `src/`), and a console entry point (`[project.scripts]`) replaces the `python -m` cwd trick.

## What we did

- `harness/` → `src/harness/` (via `git mv`, history preserved). Every import is absolute (`from harness.xxx`), so **not one import line changed**. The one package-internal data file, `prompts/system.md`, is found via `Path(__file__).parent.parent`, so it travelled with the package for free.
- Prose docs → `docs/`: `ROADMAP.md`, `harness-context-v3.md` (joining `notes/` and `problem.md`).
- Frozen/experimental dirs → `archive/`: `labs/` (throwaway experiments), `mvp/` (frozen Stage-1 artifact), `prompt/` (read-only reference for Stage 3.2).
- **Made it a real package**: added `[build-system]` (hatchling) + `[tool.hatch.build.targets.wheel] packages = ["src/harness"]` + `[project.scripts] harness = "harness.cli.repl:main"`. `uv run` now editable-installs it, so both `uv run harness <provider>` and `uv run python -m harness <provider>` resolve the installed package.
- pytest `pythonpath = ["src", "."]` (src for `harness`, root for `tests.fakes`) — belt-and-suspenders so the suite runs even before a sync.
- `acceptance/run.py`: its `sys.path` insert now points at `src/`, and its hardcoded task paths (`mvp/fixtures/...`, `harness/core`, `mvp/ACCEPTANCE.md`) were repointed to the new locations — these are *operational*, the live gate runs them.

## What stays at root, and why

Not everything could move — some root files are **runtime config the code reads from the cwd**, and the harness is run from the repo root:

| File/dir | Loaded by | Why it stays |
|---|---|---|
| `harness.toml` | `load_policy("harness.toml")` | cwd-relative permission policy |
| `AGENTS.md` | `Path(cwd)/"AGENTS.md"` | cwd-relative project memory |
| `commands/` | `discover("commands")` | cwd-relative slash-command library |
| `CLAUDE.md` | Claude Code auto-loads it from the project root | move it and the tool stops reading it |
| `README.md` | GitHub convention | — |
| `pyproject.toml`, `uv.lock`, `.env*`, `.gitignore` | tooling | — |

So "root = only docs" wasn't reachable; "root = docs conventions + runtime config, everything else filed away" was.

## How we knew it worked

`uv run pytest -q` → **79 passed** (unchanged). Both entry points (`uv run harness --sessions`, `uv run python -m harness --sessions`) list sessions and exit — token-free proof the editable install resolves. `acceptance/run.py` imports its full harness chain through `src/` (7 tasks, 3 providers) without a model call. The live exit gate itself was **not** re-run here (it costs tokens/budget) — worth a single confirmation pass next time a provider is up.
