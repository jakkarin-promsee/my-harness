"""Agent roles (2.11), offline: frontmatter parsing + discovery."""

from harness.core.agents import discover, parse_agent_file

FULL = """---
description: A planner.
mode: explore
model: gemini
think: off
# a comment the parser must ignore
---
You plan things.
"""


def test_frontmatter_all_keys_and_body():
    s = parse_agent_file("plan", FULL)
    assert s.description == "A planner."
    assert s.mode == "explore"
    assert s.model == "gemini"
    assert s.think == "off"
    assert s.prompt == "You plan things."


def test_no_frontmatter_means_all_prompt():
    s = parse_agent_file("x", "Just a prompt, no fences.")
    assert s.prompt == "Just a prompt, no fences."
    assert s.mode is None and s.model is None and s.description == ""


def test_unclosed_fence_keeps_the_whole_file():
    s = parse_agent_file("x", "---\ndescription: oops\nno closing fence")
    assert s.description == ""
    assert "oops" in s.prompt  # nothing silently eaten


def test_unknown_keys_are_ignored():
    s = parse_agent_file("x", "---\ncolor: red\nmode: chat\n---\nBody")
    assert s.mode == "chat"
    assert s.prompt == "Body"


def test_discover_missing_dir_is_empty(tmp_path):
    assert discover(str(tmp_path / "nope")) == {}


def test_discover_reads_files_and_skips_readme(tmp_path):
    d = tmp_path / "agents"
    d.mkdir()
    (d / "plan.md").write_text("---\nmode: explore\n---\nP", encoding="utf-8")
    (d / "README.md").write_text("the folder map, not a role", encoding="utf-8")
    specs = discover(str(d))
    assert set(specs) == {"plan"}
    assert specs["plan"].mode == "explore"


def test_repo_agents_ship_the_roles():
    specs = discover()  # the real agents/ at repo root
    assert {"plan", "chill", "reviewer"} <= set(specs)
    assert specs["chill"].mode == "chat"
    assert specs["plan"].mode == "explore"
    # Budget rule: no shipped role pins a provider by default.
    assert all(s.model is None for s in specs.values())


def test_backbone_frontmatter_opt_out():
    # 2.18a (note 23): roles extend the backbone by default; only an explicit
    # `backbone: false` opts out - and the shipped chill role does exactly that.
    from harness.core.agents import parse_agent_file
    spec = parse_agent_file("x", "---\nbackbone: false\n---\nbody")
    assert spec.backbone is False
    spec = parse_agent_file("y", "---\ndescription: d\n---\nbody")
    assert spec.backbone is True


def test_tier_frontmatter_rides_the_spec():
    # 2.18b (note 24): a role may pin its ladder rung.
    from harness.core.agents import parse_agent_file
    spec = parse_agent_file("x", "---\ntier: full\n---\nbody")
    assert spec.tier == "full"
    assert parse_agent_file("y", "---\ndescription: d\n---\nbody").tier is None
