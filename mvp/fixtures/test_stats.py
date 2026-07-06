"""Test for acceptance task C. Run: uv run python mvp/fixtures/test_stats.py

Prints PASS/FAIL per check; exit code 0 only if all pass. No pytest on
purpose — Stage 1 has zero test dependencies.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats import mean, total  # noqa: E402

checks = [
    ("mean of [2, 4, 6] is 4", mean([2, 4, 6]) == 4),
    ("mean of [10] is 10", mean([10]) == 10),
    ("total of [1, 2, 3] is 6", total([1, 2, 3]) == 6),
]

failed = False
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), "-", name)
    failed = failed or not ok

sys.exit(1 if failed else 0)
