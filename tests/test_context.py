"""Context assembly, offline: backbone + role + env block + optional AGENTS.md."""

import time

from harness.core import context


def test_env_block_has_cwd_and_todays_date(tmp_path):
    block = context.build_env_block(str(tmp_path))
    assert str(tmp_path) in block
    assert time.strftime("%Y-%m-%d") in block


# --- the backbone (2.18a, note 23) ----------------------------------------

def test_backbone_has_the_six_sections_in_order():
    names = [n for n, _, _ in context.parse_sections(
        (context.PROMPTS_DIR / "system.md").read_text(encoding="utf-8"))]
    assert names == ["identity", "loop", "tools", "failure", "verification", "style"]


def test_markers_never_leak_into_the_prompt(tmp_path):
    prompt = context.build_system_prompt(str(tmp_path))
    assert "<!--" not in prompt and "section:" not in prompt


def test_role_extends_the_backbone(tmp_path):
    # 2.18a flips 2.11's replace semantics: the backbone comes first, the
    # role body after, under the "# Active role" header.
    prompt = context.build_system_prompt(str(tmp_path), template="I am the ROLE BODY")
    assert "OPERATES this computer" in prompt          # backbone identity kept
    assert "# Active role" in prompt
    assert prompt.index("OPERATES") < prompt.index("ROLE BODY")


def test_backbone_false_restores_replace_semantics(tmp_path):
    prompt = context.build_system_prompt(str(tmp_path), template="Just a chat body",
                                         backbone=False)
    assert prompt.startswith("Just a chat body")
    assert "OPERATES this computer" not in prompt


def test_env_block_appears_exactly_once_even_with_placeholder(tmp_path):
    # a legacy role file still carrying {env_block} must not double the env
    prompt = context.build_system_prompt(
        str(tmp_path), template="Body\nEnvironment:\n{env_block}")
    assert prompt.count(f"Working directory: {tmp_path}") == 1
    assert "{env_block}" not in prompt


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


def test_skills_block_is_included_when_skills_exist(tmp_path):
    # 2.14: a skill's name+description line rides the assembly; the body doesn't.
    d = tmp_path / "skills" / "stamp-files"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\ndescription: House format for stamp files.\n---\nSECRET BODY",
        encoding="utf-8",
    )
    prompt = context.build_system_prompt(str(tmp_path))
    assert "stamp-files" in prompt and "House format" in prompt
    assert "SECRET BODY" not in prompt  # progressive disclosure: body loads on read


def test_missing_skills_dir_adds_nothing(tmp_path):
    assert "Skills (" not in context.build_system_prompt(str(tmp_path))


def test_template_override_appends_env_and_survives_braces(tmp_path):
    # 2.11 (updated for 2.18a): an agent body with {braces} must not crash
    # the assembly, and a body without the placeholder still gets the
    # environment appended after the backbone.
    prompt = context.build_system_prompt(str(tmp_path), template="I am a {weird} role")
    assert "I am a {weird} role" in prompt
    assert "Environment:" in prompt
    assert str(tmp_path) in prompt


def test_template_with_placeholder_is_substituted(tmp_path):
    prompt = context.build_system_prompt(str(tmp_path), template="X\nEnvironment:\n{env_block}")
    assert "{env_block}" not in prompt
    assert str(tmp_path) in prompt
