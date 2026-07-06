"""Template commands, offline."""

from harness.core import commands


def make_dir(tmp_path, files: dict):
    d = tmp_path / "commands"
    d.mkdir()
    for name, text in files.items():
        (d / name).write_text(text, encoding="utf-8")
    return str(d)


def test_discover_finds_md_files_only(tmp_path):
    d = make_dir(tmp_path, {"a.md": "x", "b.md": "y", "junk.txt": "z"})
    assert set(commands.discover(d)) == {"a", "b"}


def test_discover_handles_missing_dir(tmp_path):
    assert commands.discover(str(tmp_path / "nope")) == {}


def test_expand_substitutes_all_placeholders(tmp_path):
    d = make_dir(tmp_path, {"greet.md": "Hello {{args}}! I said: {{args}}"})
    cmds = commands.discover(d)
    assert commands.expand("/greet world", cmds) == "Hello world! I said: world"


def test_expand_appends_args_when_no_placeholder(tmp_path):
    d = make_dir(tmp_path, {"plain.md": "Do the thing.\n"})
    cmds = commands.discover(d)
    assert commands.expand("/plain with feeling", cmds) == "Do the thing.\n\nwith feeling"
    # and empty args leaves the prompt clean
    assert commands.expand("/plain", cmds) == "Do the thing."


def test_expand_returns_none_for_unknown_or_plain_input(tmp_path):
    d = make_dir(tmp_path, {"a.md": "x"})
    cmds = commands.discover(d)
    assert commands.expand("/nope hi", cmds) is None
    assert commands.expand("just a task", cmds) is None
