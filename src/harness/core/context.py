"""Context assembly: the first message is assembled, never hardcoded.

Four layers (docs/notes/06-context-assembly.md + 20-skills.md):
identity/rules from prompts/system.md (edit behavior = edit a text file),
an environment block (facts the model shouldn't burn a tool call asking),
AGENTS.md project memory when the working directory has one, and one line
per skill from skills/ (the model reads a skill's body only on activation).
"""

import os
import platform
import subprocess
import time
from pathlib import Path

from harness.core import skills as skills_lib

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


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


def build_system_prompt(cwd: str | None = None, template: str | None = None) -> str:
    """Assemble the system prompt. `template` overrides prompts/system.md —
    that's how an agent's markdown body (note 17) rides the same pipeline.
    replace(), not format(): an agent prompt containing {braces} must not
    crash the assembly. A template without the placeholder gets the env
    block appended, so plain prose files work unmodified."""
    cwd = cwd or os.getcwd()
    if template is None:
        template = (PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    if "{env_block}" in template:
        prompt = template.replace("{env_block}", build_env_block(cwd))
    else:
        prompt = template.rstrip() + "\n\nEnvironment:\n" + build_env_block(cwd)
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
