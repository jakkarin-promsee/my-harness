"""The gate's diff preview (note 19) — pure-function snapshots, no model,
no stdin. render_diff returns PLAIN text (color is the printer's job), so
these are exact-string tests."""

from harness.cli import repl
from harness.core.permissions import Mode, ModeSet, Policy


def test_edit_file_renders_a_unified_diff():
    out = repl.render_diff(
        "edit_file", {"path": "f.py", "old_string": "a = 1", "new_string": "a = 2"}
    )
    assert out == "--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n-a = 1\n+a = 2"


def test_write_file_to_new_path_is_all_additions(tmp_path):
    target = str(tmp_path / "new.txt")
    out = repl.render_diff("write_file", {"path": target, "content": "one\ntwo"})
    lines = out.splitlines()
    assert lines[2] == "@@ -0,0 +1,2 @@"
    assert lines[3:] == ["+one", "+two"]


def test_write_file_diffs_against_existing_content(tmp_path):
    target = tmp_path / "old.txt"
    target.write_text("keep\ndrop\n", encoding="utf-8")
    out = repl.render_diff("write_file", {"path": str(target), "content": "keep\nadd\n"})
    assert "-drop" in out and "+add" in out
    assert "-keep" not in out  # unchanged line is context, not a removal


def test_other_tools_and_empty_diffs_fall_back_to_none(tmp_path):
    assert repl.render_diff("read_file", {"path": "f.py"}) is None
    same = tmp_path / "same.txt"
    same.write_text("x\n", encoding="utf-8")
    # Rewriting identical content: nothing to show -> JSON preview path.
    assert repl.render_diff("write_file", {"path": str(same), "content": "x\n"}) is None


def test_diff_render_is_capped(tmp_path):
    target = str(tmp_path / "big.txt")
    content = "\n".join(f"line {i}" for i in range(200))
    out = repl.render_diff("write_file", {"path": target, "content": content})
    lines = out.splitlines()
    assert len(lines) == repl.MAX_DIFF_LINES + 1
    assert lines[-1].startswith("... (") and "more diff lines" in lines[-1]


def test_parse_args_headless_flag():
    # 2.28 (note 37): -p carries the task; absence keeps interactive defaults.
    args = repl.parse_args(["ollama", "-p", "do the thing"])
    assert args.prompt == "do the thing"
    assert repl.parse_args(["ollama"]).prompt is None


def test_final_answer_truth_table():
    """The headless exit code's whole logic (2.28): only a plain assistant
    text tail counts as a deliverable."""
    ok = [{"role": "user", "content": "q"}, {"role": "assistant", "content": " hi "}]
    assert repl.final_answer(ok) == "hi"
    runaway = [{"role": "assistant", "content": None, "tool_calls": [{"id": "c1"}]}]
    assert repl.final_answer(runaway) == ""       # MAX_STEPS tail
    interrupted = [{"role": "tool", "tool_call_id": "c1", "content": "x"}]
    assert repl.final_answer(interrupted) == ""   # tool-result tail
    assert repl.final_answer([{"role": "assistant", "content": None}]) == ""
    assert repl.final_answer([]) == ""


def test_gate_shows_diff_and_asks_on_path(monkeypatch, capsys):
    modeset = ModeSet({"build": Mode(Policy(default="ask"))})
    gate = repl.make_gate(False, modeset)
    prompts = []

    def fake_input(prompt):
        prompts.append(prompt)
        return "y"

    monkeypatch.setattr("builtins.input", fake_input)
    ok = gate("edit_file", {"path": "f.py", "old_string": "a = 1", "new_string": "a = 2"})
    assert ok is True
    assert "allow edit_file on f.py?" in prompts[0]
    printed = capsys.readouterr().out
    assert "-a = 1" in printed and "+a = 2" in printed  # the diff was shown
