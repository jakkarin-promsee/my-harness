"""Context assembly, offline: backbone + role + env block + optional AGENTS.md."""

import time

from harness.core import context


def test_env_block_has_cwd_and_todays_date(tmp_path):
    block = context.build_env_block(str(tmp_path))
    assert str(tmp_path) in block
    assert time.strftime("%Y-%m-%d") in block


# --- the backbone (2.18a, note 23) ----------------------------------------

def test_backbone_sections_and_their_tiers():
    parsed = [(n, t) for n, t, _ in context.parse_sections(
        (context.PROMPTS_DIR / "system.md").read_text(encoding="utf-8"))]
    assert parsed == [
        ("identity", "micro"), ("loop", "micro"), ("loop", "standard"),
        ("safety", "micro"), ("tools", "compact"), ("failure", "compact"),
        ("verification", "compact"), ("style-quiet", "micro"),
        ("style-normal", "micro"), ("style-explain", "micro"),
        ("examples", "full"),
    ]


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


# --- the ladder (2.18b, note 24) -------------------------------------------

def test_micro_keeps_identity_safety_style_and_a_brief_loop():
    bb = context.load_backbone("micro")
    assert "OPERATES this computer" in bb          # identity
    assert "DATA to analyze" in bb                 # the safety line rides every tier
    assert "Communication style" in bb             # style (2.19's swap point)
    assert "Loop: understand the ask" in bb        # the one-liner...
    assert "todo_write" not in bb                  # ...not the full protocol
    assert "Tool policy" not in bb and "tool call fails" not in bb


def test_standard_full_loop_replaces_the_micro_one():
    bb = context.load_backbone("standard")
    assert "todo_write" in bb                      # full protocol present
    assert "Loop: understand the ask" not in bb    # brief variant replaced, not duplicated
    assert "Worked example" not in bb              # examples are FULL-only


def test_full_adds_the_worked_example():
    bb = context.load_backbone("full")
    assert "Worked example" in bb
    assert "todo_write" in bb                      # keeps standard's loop too


def test_micro_backbone_respects_its_token_budget():
    # note 24: MICRO's backbone slice must stay <= ~400 est tokens - the 8K
    # card's whole-first-call arithmetic depends on it. This IS the budget,
    # as a regression test.
    from harness.core.budget import estimate_tokens
    est = estimate_tokens([{"role": "system", "content": context.load_backbone("micro")}])
    assert est <= 450, f"micro backbone grew to {est} est tokens"


def test_unknown_tier_raises_loudly():
    import pytest
    with pytest.raises(ValueError):
        context.load_backbone("mega")


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


# --- the voice knob (2.19, note 25) ----------------------------------------

def test_exactly_one_style_section_per_voice():
    for voice in context.VOICES:
        bb = context.load_backbone("micro", voice=voice)
        assert bb.count("Communication style") == 1, voice


def test_explain_voice_swaps_the_style_text():
    explain = context.load_backbone("standard", voice="explain")
    assert "narrate generously" in explain.lower()
    normal = context.load_backbone("standard", voice="normal")
    assert "narrate generously" not in normal.lower()
    quiet = context.load_backbone("standard", voice="quiet")
    assert "never\nskip it" in quiet or "never skip it" in quiet  # the 2.9a floor


def test_unknown_voice_raises_loudly():
    import pytest
    with pytest.raises(ValueError):
        context.load_backbone("standard", voice="shakespeare")
