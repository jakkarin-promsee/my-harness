"""Permissions v2, offline."""

import pytest

from harness.core.permissions import Policy, load_policy


def test_precedence_is_deny_then_ask_then_allow():
    p = Policy(allow={"t"}, ask={"t"}, deny={"t"})
    assert p.decide("t") == "deny"
    p = Policy(allow={"t"}, ask={"t"})
    assert p.decide("t") == "ask"
    p = Policy(allow={"t"})
    assert p.decide("t") == "allow"


def test_unknown_tool_follows_default():
    assert Policy(default="deny").decide("mystery") == "deny"
    assert Policy().decide("mystery") == "ask"


def test_invalid_default_is_rejected():
    with pytest.raises(ValueError):
        Policy(default="yolo")


def test_missing_file_gives_safe_defaults(tmp_path):
    p = load_policy(str(tmp_path / "nope.toml"))
    assert p.decide("anything") == "ask"


def test_load_from_toml(tmp_path):
    fp = tmp_path / "harness.toml"
    fp.write_text(
        '[permissions]\ndefault = "ask"\nallow = ["grep"]\ndeny = ["run_shell"]\n',
        encoding="utf-8",
    )
    p = load_policy(str(fp))
    assert p.decide("grep") == "allow"
    assert p.decide("run_shell") == "deny"
    assert p.decide("write_file") == "ask"


def test_repo_config_is_loadable_and_sane():
    p = load_policy()  # the real harness.toml at repo root
    assert p.decide("read_file") == "allow"
    assert p.decide("run_shell") == "ask"
