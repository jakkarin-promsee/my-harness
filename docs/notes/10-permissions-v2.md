# Note 10 — Stage 2.8: permissions v2 (policy from config)

> Written 2026-07-06, before implementing. Sources studied: Claude Code's allow/deny rules in settings.json + permission modes, codex CLI's sandbox/approval policies, opencode permission config.

## What the seniors do

Everyone grows the same three-state policy per tool: **allow** (run silently), **ask** (human confirms), **deny** (refuse flatly, model gets told). Config lives in a project file so the policy is versioned with the repo. Read-only tools default to allow — the y/N fatigue on `read_file` is how users learn to blind-approve everything, which defeats the gate entirely (the real lesson of permission UX).

## What we build

- `harness.toml` (repo root, committed) — `[permissions]` table: `default = "ask"`, plus `allow` / `ask` / `deny` name lists. Ships with reads (`read_file`, `list_dir`, `grep`, `glob`) allowed, mutators asked, nothing denied.
- `core/permissions.py` — `load_policy(path)` (tomllib; missing file → safe defaults: everything asks) and `Policy.decide(tool_name)` → `"allow" | "ask" | "deny"`; unknown tools follow `default`. A tool in multiple lists: **deny wins, then ask, then allow** (fail-closed tie-break).
- CLI gate becomes policy-aware: `deny` → refusal string back to the model (it should know, not silently stall); `allow` → run; `ask` → the existing y/N prompt; `-y` upgrades *ask* to yes but **never overrides deny**.

## How we know it works

pytest: precedence (deny > ask > allow), default fallback, missing-file defaults, malformed file → clear error; gate behavior with a scripted approve. The -y-cannot-override-deny rule gets an explicit test — it's the one that matters when a future overnight run goes weird.
