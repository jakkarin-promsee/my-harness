"""The core tools against a temp directory — no model involved at all.
web_fetch runs against a fake requests.get — no network either."""

import json

import requests

from harness.tools import basic


def test_write_then_read_roundtrip(tmp_path):
    target = str(tmp_path / "sub" / "note.txt")  # parent dir gets created
    result = basic.write_file(target, "hello harness")
    assert "13 chars" in result
    assert basic.read_file(target) == "hello harness"


def test_list_dir_is_sorted_json(tmp_path):
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    assert json.loads(basic.list_dir(str(tmp_path))) == ["a.txt", "b.txt"]


def test_run_shell_captures_exit_code_and_output():
    result = basic.run_shell("echo hello")
    assert result.startswith("exit code: 0")
    assert "hello" in result


def test_run_shell_reports_failure_exit_code():
    result = basic.run_shell("exit 3")
    assert result.startswith("exit code: 3")


def test_registry_and_schemas_agree():
    schema_names = {s["function"]["name"] for s in basic.SCHEMAS}
    assert schema_names == set(basic.REGISTRY) == {
        "read_file", "write_file", "list_dir", "run_shell",
        "edit_file", "grep", "glob", "web_fetch",
    }
    assert basic.NEEDS_PERMISSION <= schema_names  # gate only guards real tools


def test_edit_replaces_a_unique_match(tmp_path):
    fp = str(tmp_path / "f.py")
    basic.write_file(fp, "a = 1\nb = 2\n")
    assert "1 replacement" in basic.edit_file(fp, "b = 2", "b = 99")
    assert basic.read_file(fp) == "a = 1\nb = 99\n"


def test_edit_refuses_missing_and_ambiguous_matches(tmp_path):
    fp = str(tmp_path / "f.py")
    basic.write_file(fp, "x = 1\nx = 1\n")
    assert "not found" in basic.edit_file(fp, "y = 3", "z")
    assert "appears 2 times" in basic.edit_file(fp, "x = 1", "z")
    assert basic.read_file(fp) == "x = 1\nx = 1\n"  # nothing was touched


def test_grep_finds_matches_and_skips_junk_dirs(tmp_path):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "hidden.py").write_text("needle")
    (tmp_path / "real.py").write_text("hay\nneedle here\n")
    out = basic.grep("needle", str(tmp_path))
    assert "real.py:2: needle here" in out
    assert ".venv" not in out


def test_grep_reports_bad_regex_as_error():
    assert basic.grep("[unclosed").startswith("ERROR: bad regex")


def test_grep_caps_at_50_matches(tmp_path):
    (tmp_path / "big.txt").write_text("hit\n" * 80)
    out = basic.grep("hit", str(tmp_path))
    assert "[stopped at 50 matches]" in out


# ---- web_fetch (note 19): fake requests.get, zero network ----------------

class FakeResponse:
    def __init__(self, body=b"", status=200, ctype="text/html; charset=utf-8",
                 reason="OK", encoding="utf-8"):
        self.status_code = status
        self.reason = reason
        self.headers = {"content-type": ctype}
        self.encoding = encoding
        self._body = body

    def iter_content(self, chunk_size=65536):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def close(self):
        pass


def _serve(monkeypatch, response):
    monkeypatch.setattr(basic.requests, "get", lambda url, **kw: response)


def test_web_fetch_strips_html_and_prepends_title(monkeypatch):
    html = (b"<html><head><title>My   Page</title>"
            b"<script>var secret = 1;</script><style>.x{}</style></head>"
            b"<body><h1>Heading</h1><p>Some    text\t\there.</p></body></html>")
    _serve(monkeypatch, FakeResponse(html))
    out = basic.web_fetch("https://example.test/")
    assert out.startswith("Title: My Page")
    assert "Heading" in out and "Some text here." in out
    assert "secret" not in out and ".x{}" not in out  # script/style dropped


def test_web_fetch_refuses_non_http_schemes():
    assert basic.web_fetch("file:///etc/passwd").startswith("ERROR: only http(s)")


def test_web_fetch_reports_http_errors_as_text(monkeypatch):
    _serve(monkeypatch, FakeResponse(status=404, reason="Not Found"))
    assert basic.web_fetch("https://example.test/gone").startswith("ERROR: HTTP 404 Not Found")


def test_web_fetch_refuses_binary_content(monkeypatch):
    _serve(monkeypatch, FakeResponse(ctype="image/png"))
    assert "unsupported content type" in basic.web_fetch("https://example.test/a.png")


def test_web_fetch_passes_plain_text_through(monkeypatch):
    _serve(monkeypatch, FakeResponse(b'{"answer": 42}', ctype="application/json"))
    assert basic.web_fetch("https://example.test/api") == '{"answer": 42}'


def test_web_fetch_truncates_head_and_tail(monkeypatch):
    body = b"S" + b"x" * (basic.WEB_MAX_CHARS * 2) + b"E"
    _serve(monkeypatch, FakeResponse(body, ctype="text/plain"))
    out = basic.web_fetch("https://example.test/big")
    assert "chars truncated" in out
    assert out.startswith("S") and out.endswith("E")  # head AND tail survive
    assert len(out) < basic.WEB_MAX_CHARS + 100


def test_web_fetch_turns_connection_errors_into_text(monkeypatch):
    def boom(url, **kw):
        raise requests.ConnectionError("refused")
    monkeypatch.setattr(basic.requests, "get", boom)
    assert basic.web_fetch("https://example.test/").startswith("ERROR: fetch failed")


def test_glob_returns_newest_first(tmp_path):
    import os
    import time

    old = tmp_path / "old.py"
    new = tmp_path / "new.py"
    old.write_text("1")
    new.write_text("2")
    now = time.time()
    os.utime(old, (now - 100, now - 100))
    os.utime(new, (now, now))
    assert json.loads(basic.glob("*.py", str(tmp_path))) == [str(new), str(old)]
