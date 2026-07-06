"""The four basic tools against a temp directory — no model involved at all."""

import json

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
        "edit_file", "grep", "glob",
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
