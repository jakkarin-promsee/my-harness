"""Skill discovery + the system-prompt injection block (note 20) — offline,
against temp directories; no model, no filesystem beyond tmp_path."""

from harness.core import skills


def make_skill(root, name, frontmatter):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(frontmatter, encoding="utf-8")


def test_discover_reads_name_from_dir_and_description_from_frontmatter(tmp_path):
    make_skill(tmp_path, "pdf-magic",
               "---\nname: pdf-magic\ndescription: Handles PDFs. Use for PDF tasks.\n---\nSteps...")
    found = skills.discover(str(tmp_path))
    assert len(found) == 1
    assert found[0].name == "pdf-magic"
    assert found[0].description == "Handles PDFs. Use for PDF tasks."
    assert found[0].path.endswith("pdf-magic/SKILL.md")  # forward slashes, model-readable


def test_discover_is_sorted_and_skips_the_invisible(tmp_path):
    make_skill(tmp_path, "zeta", "---\ndescription: Z procedure.\n---\n")
    make_skill(tmp_path, "alpha", "---\ndescription: A procedure.\n---\n")
    make_skill(tmp_path, "no-description", "---\nname: no-description\n---\nBody only.")
    (tmp_path / "not-a-skill").mkdir()          # folder without SKILL.md
    (tmp_path / "README.md").write_text("map")  # stray top-level file
    found = skills.discover(str(tmp_path))
    assert [s.name for s in found] == ["alpha", "zeta"]


def test_discover_missing_dir_is_empty(tmp_path):
    assert skills.discover(str(tmp_path / "nope")) == []


def test_skills_block_renders_header_and_one_line_each(tmp_path):
    make_skill(tmp_path, "stamp", "---\ndescription: Stamp files. Use for stamps.\n---\n")
    block = skills.skills_block(skills.discover(str(tmp_path)))
    assert block.startswith("Skills (project procedures)")
    assert "- stamp (" in block and "SKILL.md): Stamp files. Use for stamps." in block
    # The imperative closes the block — last words before generation (note 20).
    assert block.splitlines()[-1].startswith("If the task matches a skill above")


def test_skills_block_of_nothing_is_empty_string():
    assert skills.skills_block([]) == ""
