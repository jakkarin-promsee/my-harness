"""demo-app tests (acceptance fixture - not real code)."""

from app.main import fetch_with_retries


def test_fetch():
    assert fetch_with_retries("https://example.test") == "ok"
