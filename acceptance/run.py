"""The stage exit gate (Stage 2 → 2R → 2C): scripted acceptance suite, one
command, real models.

    uv run python acceptance/run.py gemini                      # core 11, once
    uv run python acceptance/run.py gemini-flash --suite museum --n 3
    uv run python acceptance/run.py ollama --suite all --task M1-page-eyes

Each task gets a FRESH Agent + messages list (no REPL, no stdin); a verifier
checks reality (files on disk, test exit codes) or the agent's final answer.
Auto-approve is on (scripted run), but harness.toml policy still applies —
deny stays deny. Cleanups restore every fixture even on failure.

Since 2.17 (docs/notes/22): `--suite core|museum|all` makes per-provider task
lists explicit; `--n` repeats each task (majority-of-3 is the deciding verdict
everywhere — red-team #12); the meter derives Gemini's HIDDEN THINKING tokens
per call (total − prompt − completion; probe (b) showed the wire has no usage
split) and estimates $ from PRICES. The museum hold-out only runs with
--include-holdout — stage close only (red-team #13).

pytest (tests/, zero tokens) covers the loop's CONTRACT; this suite covers
the full stack against a live model — both must be green to exit a stage.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

# Windows pipes default to cp1252; one ✓ from a model then kills a whole task
# with UnicodeEncodeError (measured 2026-07-07, task C). UTF-8, never crash.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# The package lives under src/; put it on sys.path so `from harness...` resolves
# even without the editable install (uv run installs it, but this keeps the
# runner self-contained). Mirrors pythonpath = ["src", "."] in pyproject.toml.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from harness.cli.repl import PROVIDERS, make_gate, make_model  # noqa: E402 (side effects wanted)
from harness.core import agents as roles  # noqa: E402
from harness.core.context import build_system_prompt  # noqa: E402
from harness.core.loop import Agent  # noqa: E402
from harness.core.permissions import ModeSet, load_modes  # noqa: E402
from harness.core.subagent import make_spawn_tool  # noqa: E402
from harness.tools import basic  # noqa: E402
from harness.tools.todo import make_todo_tool  # noqa: E402

from museum import MUSEUM_TASKS  # noqa: E402 (sibling module; the script's own dir is on sys.path)

# $ per 1M tokens (input, output) as configured 2026-07-08 — estimates, not
# invoices. Gemini bills thinking as OUTPUT, so cost uses out + thinking.
PRICES = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}


def sh(command: str) -> subprocess.CompletedProcess:
    return subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)


def rm(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


# ---- the tasks -----------------------------------------------------------
# verify(final_text) -> (ok: bool, note: str). Prefer checking REALITY
# (files, exit codes) over the agent's words wherever possible.

def verify_fizzbuzz(final: str):
    if not os.path.exists("fizzbuzz.py"):
        return False, "fizzbuzz.py was not created"
    # Case-insensitive: the prompt itself says "fizzbuzz" — qwen3:4b-instruct
    # faithfully printed lowercase and failed the old check (2026-07-07).
    out = sh("uv run python fizzbuzz.py").stdout.lower()
    ok = "fizzbuzz" in out and "fizz" in out and "buzz" in out
    return ok, "program output verified" if ok else f"bad program output: {out[:60]!r}"


def verify_deps(final: str):
    low = final.lower()
    ok = all(name in low for name in ("requests", "dotenv", "truststore"))
    return ok, "all three deps named" if ok else f"answer missed deps: {final[:100]!r}"


def verify_bugfix(final: str):
    proc = sh("uv run python archive/mvp/fixtures/test_stats.py")
    ok = proc.returncode == 0
    return ok, "test exits 0" if ok else "test still failing"


def verify_grep(final: str):
    ok = "stats.py" in final
    return ok, "found the defining file" if ok else f"wrong file: {final[:100]!r}"


def verify_edit(final: str):
    with open("acceptance_scratch.py", encoding="utf-8") as f:
        text = f.read()
    ok = 'GREETING = "world"' in text and "hello" not in text
    return ok, "exact edit landed" if ok else f"file now: {text[:80]!r}"


def verify_glob(final: str):
    ok = "loop" in final  # loop.py must be among the reported core files
    return ok, "loop.py reported" if ok else f"answer: {final[:100]!r}"


def verify_subagent(final: str):
    ok = "MVP Acceptance" in final
    return ok, "child's finding relayed" if ok else f"answer: {final[:100]!r}"


def verify_mode_explore(final: str):
    # Reality first: explore mode must have blocked every write path.
    if os.path.exists("mode_probe.txt"):
        return False, "explore mode let a write through"
    ok = bool(final.strip())
    return ok, "write blocked, agent reported it" if ok else "blocked, but agent said nothing"


def verify_agent_plan(final: str):
    # The plan role's prompt mandates the handoff line — its presence proves
    # the role's system prompt actually governed the run.
    ok = "/agent build" in final.lower()
    return ok, "plan produced, handoff offered" if ok else f"no handoff line: {final[-120:]!r}"


def verify_web_fetch(final: str):
    # example.com's h1 is "Example Domain" — IANA-reserved, maximally stable.
    ok = "example domain" in final.lower()
    return ok, "heading fetched and reported" if ok else f"answer: {final[:100]!r}"


# The fixture skill for task K: a house format the model cannot guess — it
# must notice the skill from its one description line, read the body, obey.
STAMP_SKILL = """---
name: stamp-files
description: The required house format for stamp files. The format is exact and cannot be guessed - read this skill before creating any .stamp file.
---
Every stamp file in this project MUST follow this exact format:
1. The first line is exactly: STAMP v2
2. The second line is the requested content, in UPPERCASE.
No other lines.
"""


def setup_skill_fixture():
    os.makedirs("skills/stamp-files", exist_ok=True)
    with open("skills/stamp-files/SKILL.md", "w", encoding="utf-8") as f:
        f.write(STAMP_SKILL)


def cleanup_skill_fixture():
    shutil.rmtree("skills/stamp-files", ignore_errors=True)
    rm("probe.stamp")


def verify_skill_trigger(final: str):
    # Reality: the file must match the house format the skill mandates —
    # provable only if the model read skills/stamp-files/SKILL.md and obeyed.
    if not os.path.exists("probe.stamp"):
        return False, "probe.stamp was not created"
    with open("probe.stamp", encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
    ok = len(lines) == 2 and lines[0] == "STAMP v2" and lines[1] == "BANANA"
    return ok, "house format followed" if ok else f"file was: {lines!r}"


CORE_TASKS = [
    {
        "id": "A-create-and-run",
        "prompt": "Create fizzbuzz.py that prints fizzbuzz from 1 to 15, then run it and show me the output.",
        "verify": verify_fizzbuzz,
        "cleanup": lambda: rm("fizzbuzz.py"),
    },
    {
        "id": "B-read-and-report",
        "prompt": "Read pyproject.toml and tell me what dependencies this project has.",
        "verify": verify_deps,
    },
    {
        "id": "C-find-fix-prove",
        "prompt": (
            "The test script archive/mvp/fixtures/test_stats.py is failing - run it with: "
            "uv run python archive/mvp/fixtures/test_stats.py. Find the bug in "
            "archive/mvp/fixtures/stats.py, fix it, and prove the fix by re-running that script."
        ),
        "verify": verify_bugfix,
        "cleanup": lambda: sh("git checkout -- archive/mvp/fixtures/stats.py"),
    },
    {
        "id": "D-grep",
        "prompt": "Which file in this project defines the function 'total'? Use the grep tool and answer with the file path.",
        "verify": verify_grep,
    },
    {
        "id": "E-exact-edit",
        "prompt": 'In acceptance_scratch.py, change GREETING from "hello" to "world" using edit_file.',
        "setup": lambda: open("acceptance_scratch.py", "w", encoding="utf-8").write('GREETING = "hello"\n'),
        "verify": verify_edit,
        "cleanup": lambda: rm("acceptance_scratch.py"),
    },
    {
        "id": "F-glob",
        "prompt": "Using the glob tool, list the .py files directly under src/harness/core and name them.",
        "verify": verify_glob,
    },
    {
        "id": "G-subagent",
        "prompt": "Use spawn_subagent with context='fresh' to have a subagent read archive/mvp/ACCEPTANCE.md and report the exact text of its first heading. Then repeat that heading to me.",
        "verify": verify_subagent,
    },
    {
        # 2.10: explore mode is read-only — the write must come back as a
        # permission-denied tool result and the agent must SAY so, not crash.
        "id": "H-mode-explore",
        "prompt": "Create a file named mode_probe.txt containing the single word hi. If you cannot, explain briefly why not.",
        "mode": "explore",
        "verify": verify_mode_explore,
        "cleanup": lambda: rm("mode_probe.txt"),
    },
    {
        # 2.11: the plan role investigates read-only and must end with the
        # handoff line its prompt mandates ("Run /agent build ...").
        "id": "I-agent-plan",
        "prompt": (
            "I want a new tool named current_time that returns the current time. "
            "Investigate how tools are registered in this project and produce the plan."
        ),
        "agent": "plan",
        "mode": "explore",
        "verify": verify_agent_plan,
    },
    {
        # 2.13: the web_fetch tool answers from a real page (needs internet).
        "id": "J-web-fetch",
        "prompt": (
            "Use the web_fetch tool to fetch https://example.com and tell me "
            "the exact text of the page's main heading."
        ),
        "verify": verify_web_fetch,
    },
    {
        # 2.14: the model must notice the fixture skill from its description
        # line in the system prompt, read its SKILL.md, and follow the house
        # format — the prompt never names the skill or its path.
        "id": "K-skill-trigger",
        "prompt": "Create a stamp file named probe.stamp containing the word banana.",
        "setup": setup_skill_fixture,
        "verify": verify_skill_trigger,
        "cleanup": cleanup_skill_fixture,
    },
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="acceptance")
    p.add_argument("provider", nargs="?", default="ollama", choices=PROVIDERS)
    p.add_argument("--suite", choices=("core", "museum", "all"), default="core",
                   help="which task list (per-provider asymmetry is explicit: "
                        "local runs core, gemini lanes run everything)")
    p.add_argument("--n", type=int, default=1,
                   help="runs per task; the verdict is the majority")
    p.add_argument("--task", action="append", metavar="ID",
                   help="run only this task id (repeatable)")
    p.add_argument("--include-holdout", action="store_true",
                   help="run the museum hold-out - STAGE CLOSE ONLY (red-team #13)")
    return p.parse_args()


def run_once(task: dict, model, modes, specs, on_usage) -> tuple[bool, str]:
    """One fresh Agent + messages list for one task run. The 2.17 refactor
    only extracted this from main()'s old body - the per-run machinery
    (fresh gate, spawn tool, todo list) is unchanged."""
    if task.get("setup"):
        task["setup"]()
    # Per-task mode (default build); -y semantics via the gate's
    # auto_approve - deny still denies, in every mode.
    modeset = ModeSet(modes, active=task.get("mode", "build"))
    gate = make_gate(True, modeset)
    # Per-task role (2.11): a named agent's body rides the same pipeline.
    template = specs[task["agent"]].prompt if task.get("agent") else None
    messages = [
        {"role": "system", "content": build_system_prompt(template=template)},
        {"role": "user", "content": task["prompt"]},
    ]
    spawn_fn, spawn_schema = make_spawn_tool(
        model=model, registry=basic.REGISTRY, schemas=basic.SCHEMAS,
        needs_permission=set(basic.REGISTRY), approve=gate, emit=print,
        get_parent_messages=lambda m=messages: m,
        system_prompt=messages[0]["content"], on_usage=on_usage,
    )
    todo_fn, todo_schema = make_todo_tool(emit=print)  # fresh list per run
    agent = Agent(
        model=model,
        registry=dict(basic.REGISTRY, spawn_subagent=spawn_fn, todo_write=todo_fn),
        schemas=basic.SCHEMAS + [spawn_schema, todo_schema],
        needs_permission=set(basic.REGISTRY) | {"spawn_subagent", "todo_write"},
        approve=gate, on_usage=on_usage,
    )
    try:
        agent.run_turn(messages)
        final = next(
            (m.get("content") for m in reversed(messages)
             if m.get("role") == "assistant" and m.get("content")),
            "",
        )
        return task["verify"](final)
    except Exception as e:  # a crashed run is a failed run, not a crashed suite
        return False, f"{type(e).__name__}: {e}"
    finally:
        if task.get("cleanup"):
            task["cleanup"]()


def main() -> None:
    args = parse_args()
    provider = PROVIDERS[args.provider]
    model = make_model(provider)
    modes = load_modes()
    specs = roles.discover()  # agents/*.md at the repo root

    tasks = {"core": CORE_TASKS, "museum": MUSEUM_TASKS,
             "all": CORE_TASKS + MUSEUM_TASKS}[args.suite]
    if args.task:
        tasks = [t for t in tasks if t["id"] in args.task]
        missing = set(args.task) - {t["id"] for t in tasks}
        if missing:
            sys.exit(f"unknown task id(s): {', '.join(sorted(missing))}")
    held_back = [t for t in tasks if t.get("holdout")]
    if held_back and not args.include_holdout:
        tasks = [t for t in tasks if not t.get("holdout")]
        print(f"[holdout] skipping {', '.join(t['id'] for t in held_back)} "
              "(stage close only; pass --include-holdout to run it)")
    elif held_back:
        print(f"[holdout] RUNNING {', '.join(t['id'] for t in held_back)} - "
              "this is only legitimate at stage close (red-team #13)")

    # The meter, 2.17 edition: Gemini hides thinking in total_tokens (probe
    # (b), note 22) - derive it per call; Ollama reports totals only.
    totals = {"in": 0, "out": 0, "think": 0}
    run_usage = {"in": 0, "out": 0, "think": 0}

    def on_usage(usage):
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        t = usage.get("total_tokens")
        think = max(0, t - p - c) if t else 0
        for bucket in (totals, run_usage):
            bucket["in"] += p
            bucket["out"] += c
            bucket["think"] += think

    def dollars(u: dict) -> float | None:
        if provider["model"] not in PRICES:
            return None  # local = free; unknown = don't guess
        pin, pout = PRICES[provider["model"]]
        return (u["in"] * pin + (u["out"] + u["think"]) * pout) / 1e6

    print(f"=== acceptance | provider: {args.provider} | model: {provider['model']}"
          f" | suite: {args.suite} | n={args.n} ===")
    results = []  # (task_id, [(ok, note, usage, secs), ...])
    for task in tasks:
        runs = []
        for i in range(args.n):
            run_usage.update({"in": 0, "out": 0, "think": 0})
            print(f"\n--- {task['id']} (run {i + 1}/{args.n}) ---")
            t0 = time.monotonic()
            ok, note = run_once(task, model, modes, specs, on_usage)
            secs = time.monotonic() - t0
            usage = dict(run_usage)
            runs.append((ok, note, usage, secs))
            cost = dollars(usage)
            print(f"--- {task['id']} run {i + 1}: {'PASS' if ok else 'FAIL'} ({note}) | "
                  f"{usage['in']:,} in / {usage['out']:,} out"
                  + (f" / {usage['think']:,} think" if usage["think"] else "")
                  + f" | {secs:.1f}s" + (f" | ~${cost:.4f}" if cost is not None else ""))
        results.append((task["id"], runs))

    print(f"\n=== results | provider: {args.provider} | model: {provider['model']}"
          f" | suite: {args.suite} ===")
    all_pass = True
    for tid, runs in results:
        wins = sum(1 for ok, *_ in runs if ok)
        majority = wins * 2 > len(runs)
        all_pass &= majority
        mean_in = sum(u["in"] for _, _, u, _ in runs) / len(runs)
        mean_out = sum(u["out"] + u["think"] for _, _, u, _ in runs) / len(runs)
        mean_s = sum(s for *_, s in runs) / len(runs)
        cost = dollars({"in": mean_in, "out": mean_out, "think": 0})
        notes = runs[-1][1] if len(runs) == 1 else "; ".join(
            f"r{i + 1}:{'P' if ok else 'F'}" for i, (ok, *_) in enumerate(runs))
        print(f"  {'PASS' if majority else 'FAIL'}  {tid:<24} {wins}/{len(runs)}"
              f" | ~{mean_in:,.0f} in / {mean_out:,.0f} out | {mean_s:.1f}s"
              + (f" | ~${cost:.4f}/run" if cost is not None else "") + f" | {notes}")
    passed = sum(1 for _, runs in results
                 if sum(1 for ok, *_ in runs if ok) * 2 > len(runs))
    total_cost = dollars(totals)
    print(f"  {passed}/{len(results)} tasks pass by majority | tokens:"
          f" {totals['in']:,} in / {totals['out']:,} out / {totals['think']:,} think"
          + (f" | est ${total_cost:.4f} total" if total_cost is not None else ""))
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
