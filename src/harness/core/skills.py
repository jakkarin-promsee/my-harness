"""Skills: the MODEL's procedure library (the SKILL.md open standard).

The complement of commands/ (2.7): a command is user-invoked and rendered
into a user message; a skill is model-invoked — only its name + description
line is injected into the system prompt (docs/notes/20-skills.md), and the
model activates it by calling read_file on the SKILL.md when a task matches.
That's the standard's "progressive disclosure" (~100 tokens at startup, the
body only on activation) — and it costs us zero new machinery, because
reading files on demand is what the model already does.

A skill = a directory under skills/ at the cwd holding a SKILL.md:
frontmatter carries `description` (the trigger text — what it does AND when
to use it); the body is the procedure; sibling files may be referenced from
it. The directory name IS the skill name (the spec requires the frontmatter
name to match it anyway — same stem rule as commands/ and agents/). A folder
without SKILL.md, or a SKILL.md without a description, is skipped: the
description is the only signal the model gets, so a skill without one is
invisible by design, not an error.
"""

from pathlib import Path

from harness.core.agents import split_frontmatter

SKILL_KEYS = {"name", "description"}


class SkillInfo:
    def __init__(self, name: str, description: str, path: str):
        self.name = name
        self.description = description
        self.path = path  # cwd-relative, forward slashes — what the model reads


def discover(directory: str = "skills") -> list[SkillInfo]:
    """skills/*/SKILL.md at the cwd -> [SkillInfo], sorted by name.
    Missing dir -> [] (same silent pattern as commands/ and agents/)."""
    d = Path(directory)
    if not d.is_dir():
        return []
    found = []
    for fp in sorted(d.glob("*/SKILL.md")):
        meta, _ = split_frontmatter(fp.read_text(encoding="utf-8"), SKILL_KEYS)
        description = meta.get("description", "").strip()
        if not description:
            continue  # no trigger text -> not advertised
        # The model's read_file resolves against the PROCESS cwd — advertise
        # a path that works there: relative when inside it, absolute if not.
        path = fp
        try:
            path = fp.resolve().relative_to(Path.cwd().resolve())
        except ValueError:
            pass
        found.append(SkillInfo(
            name=fp.parent.name,
            description=description,
            path=Path(path).as_posix(),
        ))
    return found


def skills_block(skills: list[SkillInfo]) -> str:
    """The system-prompt injection: an instruction header + one line per
    skill. Empty list -> "" (the caller appends nothing)."""
    if not skills:
        return ""
    lines = ["Skills (project procedures) available in this project:"]
    for s in skills:
        lines.append(f"- {s.name} ({s.path}): {s.description}")
    # The imperative goes AFTER the list: the block ends the system prompt,
    # and small models obey the instruction closest to generation. Measured
    # on qwen3:4b (task K, note 20) — a soft header got narrated compliance
    # with a guessed format.
    lines.append(
        "If the task matches a skill above, your FIRST action MUST be "
        "read_file on that skill's file; then follow its steps exactly. "
        "The description line is not the procedure - the file is."
    )
    return "\n".join(lines)
