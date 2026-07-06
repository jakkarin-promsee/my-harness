"""Slash commands: a command is a markdown file. That's it.

Claude Code's design, copied because it's beautifully dumb: `/name args`
reads commands/name.md, substitutes {{args}}, and the result becomes the
user message. The prompt library IS a folder — no plugin API. Stage 3.2
builds the intake-interview middleware on top of exactly this mechanism.
"""

from pathlib import Path

PLACEHOLDER = "{{args}}"


def discover(directory: str = "commands") -> dict[str, Path]:
    d = Path(directory)
    if not d.is_dir():
        return {}
    return {fp.stem: fp for fp in sorted(d.glob("*.md"))}


def render(path: Path, args: str) -> str:
    text = path.read_text(encoding="utf-8")
    if PLACEHOLDER in text:
        return text.replace(PLACEHOLDER, args)
    # No placeholder: append args, so any plain prompt file works unmodified.
    return f"{text.rstrip()}\n\n{args}".rstrip()


def expand(user_input: str, commands: dict[str, Path]) -> str | None:
    """'/name the args' -> rendered prompt, or None if not a template command."""
    if not user_input.startswith("/"):
        return None
    name, _, args = user_input[1:].partition(" ")
    if name not in commands:
        return None
    return render(commands[name], args.strip())
