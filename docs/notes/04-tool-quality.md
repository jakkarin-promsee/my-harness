# Note 04 — Stage 2.2: tool quality (the ACI lesson)

> Written 2026-07-06, before implementing. Sources studied: SWE-agent paper (arXiv 2405.15793 — the agent-computer interface matters more than model IQ), Claude Code's Edit/Grep/Glob tool descriptions, aider's edit formats saga (diffs vs whole-file vs search/replace).

## What the seniors do

- **Editing**: nobody serious rewrites whole files. Claude Code's Edit = exact `old_string -> new_string` with a uniqueness requirement; aider converged on search/replace blocks after measuring everything else failing more. The uniqueness rule is the genius bit: ambiguity becomes an *error the model can fix* (add more context) instead of a silent wrong edit.
- **Searching**: grep/glob as first-class tools, not "run grep in bash" — structured args, bounded output, predictable formatting (SWE-agent showed unbounded output wrecks agents).
- **Truncation**: keep the head AND the tail. Shell output puts the error at the END — chopping the tail (what Stage 1 did) hides exactly the part that matters.

## What we build

Three new tools in `tools/basic.py` (staying in one module until it hurts):

- `edit_file(path, old_string, new_string)` — occurrences: 0 → "not found" error; >1 → "appears N times, add surrounding context" error; exactly 1 → replace + write. Needs permission (it mutates).
- `grep(pattern, path=".")` — pure-Python regex over the tree, skipping `.git/.venv/__pycache__/node_modules/sessions` and files >1 MB; returns `path:lineno: line`, capped at 50 matches. Read-only.
- `glob(pattern, path=".")` — `Path.glob`, files only, newest first (Claude Code's ordering — recency is relevance), capped at 100. Read-only.

Loop change: truncation becomes **head + tail** (¾ head, ¼ tail, marker in the middle stating how much was dropped).

## How we know it works

New pytest cases: edit's three outcomes, grep skip-dirs + cap + bad-regex-as-error, glob ordering, head+tail truncation marker (existing truncation test updated). Live sanity check happens at the Stage 2 exit gate (grep/edit acceptance tasks).
