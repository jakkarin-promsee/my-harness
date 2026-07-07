"""Context assembly: the first message is assembled, never hardcoded.

Layers (docs/notes/06 + 20 + 23): the BACKBONE from prompts/system.md —
six tagged sections (identity, loop, tools, failure, verification, style)
every role keeps unless it opts out — then the active role's body, then an
environment block (facts the model shouldn't burn a tool call asking),
AGENTS.md project memory when the working directory has one, and one line
per skill from skills/ (the model reads a skill's body only on activation).

Section markers (`<!-- section: name tier: micro -->`) carry the tier tag
2.18b's ladder reads; assembly strips them — the model never sees plumbing.
"""

import os
import platform
import re
import subprocess
import time
from pathlib import Path

from harness.core import skills as skills_lib

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

SECTION_MARK = re.compile(r"<!--\s*section:\s*([\w-]+)\s*(?:tier:\s*(\w+)\s*)?-->")


def parse_sections(text: str) -> list[tuple[str, str, str]]:
    """Backbone text -> [(name, tier, body), ...]. Text before the first
    marker (if any) is ignored - every real section is fenced. The tier tag
    defaults to 'standard' (inert until 2.18b's ladder filters on it)."""
    marks = list(SECTION_MARK.finditer(text))
    sections = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end].strip()
        if body:
            sections.append((m.group(1), m.group(2) or "standard", body))
    return sections


def load_backbone() -> str:
    """The assembled backbone: every section, markers stripped, one blank
    line between sections. (2.18b adds tier selection on top.)"""
    text = (PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    return "\n\n".join(body for _, _, body in parse_sections(text))


def _git_branch(cwd: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
        return proc.stdout.strip() or None if proc.returncode == 0 else None
    except OSError:
        return None


def build_env_block(cwd: str) -> str:
    lines = [
        f"- OS: {platform.system()} {platform.release()}",
        f"- Working directory: {cwd}",
        f"- Today's date: {time.strftime('%Y-%m-%d')}",
    ]
    branch = _git_branch(cwd)
    if branch:
        lines.append(f"- Git branch: {branch}")
    return "\n".join(lines)


def build_system_prompt(cwd: str | None = None, template: str | None = None,
                        backbone: bool = True) -> str:
    """Assemble the system prompt (note 23). `template` is the active role's
    body (note 17); since 2.18a it EXTENDS the backbone instead of replacing
    it — the backbone is exactly the part no role should lose. `backbone=
    False` restores replace semantics (the `chill` role: an "operates the
    computer" identity is nonsense in a mode where tools aren't even sent).
    replace(), not format(): an agent prompt containing {braces} must not
    crash the assembly. A template without the placeholder gets the env
    block appended, so plain prose files work unmodified."""
    cwd = cwd or os.getcwd()
    if template is None:
        prompt = load_backbone()  # the built-in `build` role IS the backbone
    elif backbone:
        prompt = load_backbone() + "\n\n# Active role\n" + template.strip()
    else:
        prompt = template
    env = build_env_block(cwd)
    if "{env_block}" in prompt:
        # Substitute the first placeholder, drop any strays: the env block
        # must appear exactly once however the role file was written.
        prompt = prompt.replace("{env_block}", env, 1).replace("{env_block}", "")
    else:
        prompt = prompt.rstrip() + "\n\nEnvironment:\n" + env
    # Project memory: the file the USER owns. Cross-tool convention: AGENTS.md.
    agents_md = Path(cwd) / "AGENTS.md"
    if agents_md.exists():
        prompt += (
            "\n\nProject notes (from AGENTS.md in the working directory):\n"
            + agents_md.read_text(encoding="utf-8")
        )
    # Skills: one name+description line each (note 20). Every role and every
    # subagent rides this same pipeline, so all of them see the library.
    block = skills_lib.skills_block(skills_lib.discover(str(Path(cwd) / "skills")))
    if block:
        prompt += "\n\n" + block
    return prompt
