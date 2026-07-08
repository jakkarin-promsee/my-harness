"""The Model protocol — the seam between the loop and every provider —
plus the wire plumbing every adapter shares (the retry policy).

The loop speaks exactly one dialect (OpenAI-style messages) and expects
exactly one reply shape. Every adapter's job is to make its provider look
like this, translating BOTH directions at the boundary — history gets
replayed on every call, so outgoing translation matters as much as incoming.
"""

import random
import time
from typing import Callable, Protocol

import requests


class Model(Protocol):
    def complete(self, messages: list, tools: list) -> dict:
        """messages/tools in OpenAI-compat shape ->
        {"message": <assistant msg>, "finish_reason": stop|tool_calls|length, "usage": dict|None}
        """
        ...


# A server asking us to wait ten minutes gets our cap, not our obedience.
RETRY_AFTER_CAP = 60


def _delay(attempt: int, resp) -> float:
    """Retry-After when the server names a wait (429s usually do), else
    exponential 1-2-4-8s with ±25% jitter (the SDKs' converged default —
    jitter keeps N clients from re-stampeding in sync)."""
    if resp is not None:
        try:
            return min(float(resp.headers.get("Retry-After")), RETRY_AFTER_CAP)
        except (TypeError, ValueError):
            pass  # absent or HTTP-date form -> backoff
    base = 2 ** (attempt - 1)
    return base * random.uniform(0.75, 1.25)


def request_with_retries(send: Callable[[], requests.Response], attempts: int = 5,
                         on_wait: Callable[[str], None] = print,
                         sleep: Callable[[float], None] = time.sleep) -> requests.Response:
    """The retry policy all three adapters share (2.26, note 35).

    `send` is a zero-arg callable doing the actual POST (each adapter keeps
    its own URL/headers/stream kwargs). Retried: connection errors and
    timeouts (nothing consumed yet), 429 (rate limit — the overnight killer)
    and 5xx. Never retried: other 4xx — same request, same rejection, our
    bug. Streaming is safe by construction: with stream=True the status check
    happens before any body is consumed, so every retry predates the first
    byte. On the last attempt the failure surfaces as it always did —
    raise_for_status / the requests exception — so the REPL's
    RequestException arm needs no changes.
    """
    for attempt in range(1, attempts + 1):
        try:
            resp = send()
        except (requests.ConnectionError, requests.Timeout):
            if attempt == attempts:
                raise
            wait = _delay(attempt, None)
            on_wait(f"  [!] connection error - waiting {wait:.0f}s (attempt {attempt}/{attempts})...")
            sleep(wait)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == attempts:
                resp.raise_for_status()
            wait = _delay(attempt, resp)
            on_wait(f"  [!] {resp.status_code} from provider - waiting {wait:.0f}s (attempt {attempt}/{attempts})...")
            sleep(wait)
            continue
        resp.raise_for_status()  # a non-retryable 4xx: fail loudly, immediately
        return resp
