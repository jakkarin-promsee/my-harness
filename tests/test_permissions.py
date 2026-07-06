"""Permissions v2 + modes (2.10), offline."""

import pytest

from harness.core.permissions import Mode, ModeSet, Policy, load_modes, load_policy


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


# ---- 2.10: the scoping rule (decide_call) ---------------------------------

def test_scoped_allow_holds_inside_cwd():
    p = Policy(allow={"write_file"})
    assert p.decide_call("write_file", {"path": "notes.md"}) == "allow"
    assert p.decide_call("write_file", {"path": "sub/dir/notes.md"}) == "allow"


def test_scoped_allow_degrades_to_ask_outside_cwd():
    p = Policy(allow={"write_file", "edit_file"})
    assert p.decide_call("write_file", {"path": "../escape.txt"}) == "ask"
    assert p.decide_call("edit_file", {"path": "C:/Windows/oops.txt"}) == "ask"
    # No path argument at all -> can't prove it's inside -> fail closed.
    assert p.decide_call("write_file", {}) == "ask"


def test_scoping_never_touches_deny_or_unscoped_tools():
    p = Policy(allow={"read_file"}, deny={"write_file"})
    assert p.decide_call("write_file", {"path": "notes.md"}) == "deny"
    assert p.decide_call("read_file", {"path": "../outside.txt"}) == "allow"


# ---- 2.10: modes -----------------------------------------------------------

def test_load_modes_build_is_the_permissions_table(tmp_path):
    fp = tmp_path / "harness.toml"
    fp.write_text(
        '[permissions]\nallow = ["grep"]\n\n'
        '[modes.chat]\ntools = false\ndefault = "deny"\n\n'
        '[modes.explore]\ndefault = "deny"\nallow = ["read_file"]\n',
        encoding="utf-8",
    )
    modes = load_modes(str(fp))
    assert set(modes) == {"build", "chat", "explore"}
    assert modes["build"].policy.decide("grep") == "allow"
    assert modes["build"].send_tools is True
    assert modes["chat"].send_tools is False
    assert modes["explore"].policy.decide("write_file") == "deny"


def test_load_modes_missing_file_gives_build_only(tmp_path):
    modes = load_modes(str(tmp_path / "nope.toml"))
    assert set(modes) == {"build"}
    assert modes["build"].policy.decide("anything") == "ask"


def test_modeset_switch_and_active_policy():
    ms = ModeSet({
        "build": Mode(Policy(allow={"write_file"})),
        "explore": Mode(Policy(default="deny")),
    })
    assert ms.active == "build"
    assert ms.policy.decide("write_file") == "allow"
    ms.switch("explore")
    assert ms.policy.decide("write_file") == "deny"
    assert ms.send_tools is True


def test_modeset_rejects_unknown_mode():
    ms = ModeSet({"build": Mode(Policy())})
    with pytest.raises(ValueError):
        ms.switch("yolo")
    with pytest.raises(ValueError):
        ModeSet({"build": Mode(Policy())}, active="yolo")


def test_repo_modes_ship_the_ladder():
    modes = load_modes()  # the real harness.toml at repo root
    assert {"chat", "explore", "build", "auto"} <= set(modes)
    # chat: pure conversation - tools aren't even offered
    assert modes["chat"].send_tools is False
    # explore: reads run, writes refuse - even with -y (deny is absolute)
    assert modes["explore"].policy.decide("read_file") == "allow"
    assert modes["explore"].policy.decide("write_file") == "deny"
    assert modes["explore"].policy.decide("run_shell") == "deny"
    # auto: writes allowed inside cwd only; shell still asks
    assert modes["auto"].policy.decide_call("write_file", {"path": "x.txt"}) == "allow"
    assert modes["auto"].policy.decide_call("write_file", {"path": "../x.txt"}) == "ask"
    assert modes["auto"].policy.decide("run_shell") == "ask"
