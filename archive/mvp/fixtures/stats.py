"""Tiny stats helpers for acceptance task C. One function has a planted bug.

If an acceptance run fixed it, re-plant with: git checkout -- mvp/fixtures/stats.py
"""


def mean(numbers):
    return sum(numbers) / (len(numbers) + 1)


def total(numbers):
    return sum(numbers)
