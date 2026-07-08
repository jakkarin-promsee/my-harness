"""The acceptance runner's destructive-shell tripwire (problem.md #3) —
born from the 2026-07-08 incident: an auto-approved local agent deleted
every file in the repo root, .env included, during a core gate run."""

import sys
from pathlib import Path

# run.py resolves `from museum import ...` via its own dir on sys.path
# (true when run as a script); give the import the same courtesy here.
sys.path.insert(0, str(Path(__file__).parent.parent / "acceptance"))

from acceptance.run import DESTRUCTIVE, guarded  # noqa: E402


def test_tripwire_catches_the_incident_class():
    for cmd in ("del *", "del /f /q *.log", "rm -rf *", "erase *.py",
                "git clean -fdx", "format c:"):
        assert DESTRUCTIVE.search(cmd), cmd


def test_tripwire_lets_normal_work_through():
    for cmd in ("del fizzbuzz.py", "uv run pytest -q", "rm sessions/x.jsonl",
                "uv run python -m harness", "echo formatting done",
                "grep -r retry src"):
        assert not DESTRUCTIVE.search(cmd), cmd


def test_guarded_blocks_only_destructive_run_shell():
    gate = guarded(lambda name, args: True)  # inner gate says yes to all
    assert gate("run_shell", {"command": "del *"}) is False
    assert gate("run_shell", {"command": "del old.txt"}) is True
    assert gate("edit_file", {"path": "x.py"}) is True  # other tools untouched
