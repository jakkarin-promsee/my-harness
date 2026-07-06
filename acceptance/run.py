"""The stage exit gate (Stage 2, now growing through 2R): scripted acceptance
suite, one command, real models.

    uv run python acceptance/run.py gemini
    uv run python acceptance/run.py ollama

Each task gets a FRESH Agent + messages list (no REPL, no stdin); a verifier
checks reality (files on disk, test exit codes) or the agent's final answer.
Auto-approve is on (scripted run), but harness.toml policy still applies —
deny stays deny. Cleanups restore every fixture even on failure.

pytest (tests/, zero tokens) covers the loop's CONTRACT; this suite covers
the full stack against a live model — both must be green to exit Stage 2.
"""

import os
import subprocess
import sys

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
from harness.core.context import build_system_prompt  # noqa: E402
from harness.core.loop import Agent  # noqa: E402
from harness.core.permissions import ModeSet, load_modes  # noqa: E402
from harness.core.subagent import make_spawn_tool  # noqa: E402
from harness.tools import basic  # noqa: E402
from harness.tools.todo import make_todo_tool  # noqa: E402


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


TASKS = [
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
]


def main() -> None:
    provider_name = sys.argv[1] if len(sys.argv) > 1 else "ollama"
    provider = PROVIDERS[provider_name]
    model = make_model(provider)
    modes = load_modes()
    totals = {"in": 0, "out": 0}

    def on_usage(usage):
        totals["in"] += usage.get("prompt_tokens", 0)
        totals["out"] += usage.get("completion_tokens", 0)

    print(f"=== acceptance | provider: {provider_name} | model: {provider['model']} ===")
    results = []
    for task in TASKS:
        if task.get("setup"):
            task["setup"]()
        # Per-task mode (default build); -y semantics via the gate's
        # auto_approve — deny still denies, in every mode.
        modeset = ModeSet(modes, active=task.get("mode", "build"))
        gate = make_gate(True, modeset)
        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": task["prompt"]},
        ]
        spawn_fn, spawn_schema = make_spawn_tool(
            model=model, registry=basic.REGISTRY, schemas=basic.SCHEMAS,
            needs_permission=set(basic.REGISTRY), approve=gate, emit=print,
            get_parent_messages=lambda m=messages: m,
            system_prompt=messages[0]["content"], on_usage=on_usage,
        )
        todo_fn, todo_schema = make_todo_tool(emit=print)  # fresh list per task
        agent = Agent(
            model=model,
            registry=dict(basic.REGISTRY, spawn_subagent=spawn_fn, todo_write=todo_fn),
            schemas=basic.SCHEMAS + [spawn_schema, todo_schema],
            needs_permission=set(basic.REGISTRY) | {"spawn_subagent", "todo_write"},
            approve=gate, on_usage=on_usage,
        )
        print(f"\n--- {task['id']} ---")
        try:
            agent.run_turn(messages)
            final = next(
                (m.get("content") for m in reversed(messages)
                 if m.get("role") == "assistant" and m.get("content")),
                "",
            )
            ok, note = task["verify"](final)
        except Exception as e:  # a crashed task is a failed task, not a crashed suite
            ok, note = False, f"{type(e).__name__}: {e}"
        finally:
            if task.get("cleanup"):
                task["cleanup"]()
        results.append((task["id"], ok, note))
        print(f"--- {task['id']}: {'PASS' if ok else 'FAIL'} ({note})")

    print(f"\n=== results | provider: {provider_name} ===")
    for tid, ok, note in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {tid:<18} {note}")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"  {passed}/{len(results)} passed | tokens: {totals['in']:,} in / {totals['out']:,} out")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
