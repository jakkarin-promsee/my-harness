"""Context assembly: the first message is assembled, never hardcoded.

Three layers (docs/notes/06-context-assembly.md):
identity/rules from prompts/system.md (edit behavior = edit a text file),
an environment block (facts the model shouldn't burn a tool call asking),
and AGENTS.md project memory when the working directory has one.
"""

import os
import platform
import subprocess
import time
from pathlib import Path

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


def build_system_prompt(cwd: str | None = None) -> str:
    cwd = cwd or os.getcwd()
    template = (PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    prompt = template.format(env_block=build_env_block(cwd))
    # Project memory: the file the USER owns. Cross-tool convention: AGENTS.md.
    agents_md = Path(cwd) / "AGENTS.md"
    if agents_md.exists():
        prompt += (
            "\n\nProject notes (from AGENTS.md in the working directory):\n"
            + agents_md.read_text(encoding="utf-8")
        )
    return prompt
