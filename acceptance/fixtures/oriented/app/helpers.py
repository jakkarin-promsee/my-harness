"""demo-app helpers (acceptance fixture - not real code)."""


def backoff(attempt: int) -> float:
    return min(2.0 ** attempt, 30.0)
