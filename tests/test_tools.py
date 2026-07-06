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
    }
    assert basic.NEEDS_PERMISSION <= schema_names  # gate only guards real tools
