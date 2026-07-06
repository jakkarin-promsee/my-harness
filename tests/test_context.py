"""Context assembly, offline: template + env block + optional AGENTS.md."""

import time

from harness.core import context


def test_env_block_has_cwd_and_todays_date(tmp_path):
    block = context.build_env_block(str(tmp_path))
    assert str(tmp_path) in block
    assert time.strftime("%Y-%m-%d") in block


def test_prompt_renders_template_with_env(tmp_path):
    prompt = context.build_system_prompt(str(tmp_path))
    assert "coding agent" in prompt
    assert str(tmp_path) in prompt
    assert "{env_block}" not in prompt  # placeholder actually substituted


def test_agents_md_is_included_when_present(tmp_path):
    (tmp_path / "AGENTS.md").write_text("- always be excellent", encoding="utf-8")
    prompt = context.build_system_prompt(str(tmp_path))
    assert "always be excellent" in prompt
    assert "AGENTS.md" in prompt  # provenance header


def test_missing_agents_md_is_silently_fine(tmp_path):
    prompt = context.build_system_prompt(str(tmp_path))
    assert "Project notes" not in prompt


def test_template_override_appends_env_and_survives_braces(tmp_path):
    # 2.11: an agent body with {braces} must not crash the assembly, and a
    # template without the placeholder still gets the environment appended.
    prompt = context.build_system_prompt(str(tmp_path), template="I am a {weird} role")
    assert prompt.startswith("I am a {weird} role")
    assert "Environment:" in prompt
    assert str(tmp_path) in prompt


def test_template_with_placeholder_is_substituted(tmp_path):
    prompt = context.build_system_prompt(str(tmp_path), template="X\nEnvironment:\n{env_block}")
    assert "{env_block}" not in prompt
    assert str(tmp_path) in prompt
