"""The shared retry policy (2.26, note 35) — the wire's FakeModel.

`send` is a scripted callable and `sleep` is captured instead of slept, so
the whole policy — backoff, Retry-After, the never-retry-4xx rule — runs
offline in milliseconds. Zero tokens, zero seconds.
"""

import pytest
import requests

from harness.providers.base import RETRY_AFTER_CAP, request_with_retries


class Resp:
    def __init__(self, status, headers=None):
        self.status_code = status
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def run(script, **kwargs):
    """script: list of Resp | Exception. Returns (result_or_raise, sleeps)."""
    script = list(script)
    sleeps = []

    def send():
        item = script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    resp = request_with_retries(send, on_wait=lambda line: None,
                                sleep=sleeps.append, **kwargs)
    return resp, sleeps


def test_first_try_success_passes_through_untouched():
    resp, sleeps = run([Resp(200)])
    assert resp.status_code == 200
    assert sleeps == []


def test_503_retries_with_exponential_backoff():
    resp, sleeps = run([Resp(503), Resp(503), Resp(200)])
    assert resp.status_code == 200
    assert len(sleeps) == 2
    assert 0.75 <= sleeps[0] <= 1.25    # 1s base, ±25% jitter
    assert 1.5 <= sleeps[1] <= 2.5      # 2s base


def test_429_honors_retry_after_exactly():
    resp, sleeps = run([Resp(429, {"Retry-After": "7"}), Resp(200)])
    assert resp.status_code == 200
    assert sleeps == [7.0]  # the server's number, not our backoff


def test_absurd_retry_after_is_capped():
    _, sleeps = run([Resp(429, {"Retry-After": "600"}), Resp(200)])
    assert sleeps == [RETRY_AFTER_CAP]


def test_plain_4xx_never_retries():
    # Same request, same rejection - our bug, fail loudly on try one.
    with pytest.raises(requests.HTTPError):
        run([Resp(400)])


def test_connection_errors_retry_then_raise():
    with pytest.raises(requests.ConnectionError):
        run([requests.ConnectionError("down")] * 3, attempts=3)
    _, sleeps = run([requests.ConnectionError("blip"), Resp(200)])
    assert len(sleeps) == 1


def test_exhausted_5xx_surfaces_as_http_error():
    # The REPL's RequestException arm catches this - same failure shape as
    # before 2.26, just later and politer.
    with pytest.raises(requests.HTTPError):
        run([Resp(503)] * 2, attempts=2)
