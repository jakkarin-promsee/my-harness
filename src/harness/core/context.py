"""Context assembly: the first message is assembled, never hardcoded.

Layers (docs/notes/06 + 20 + 23): the BACKBONE from prompts/system.md —
six tagged sections (identity, loop, tools, failure, verification, style)
every role keeps unless it opts out — then the active role's body, then an
environment block (facts the model shouldn't burn a tool call asking),
AGENTS.md project memory when the working directory has one, and one line
per skill from skills/ (the model reads a skill's body only on activation).

Section markers (`<!-- section: name tier: micro -->`) carry the tier tag the
ladder (note 24) filters on; assembly strips them — the model never sees
plumbing. Tiers nest (micro ⊂ compact ⊂ standard ⊂ full) and a same-name
section at a higher applicable tier REPLACES the lower one — every tier's
text lives in ONE file, zero duplication, no forked copies to keep honest.
"""

import os
import platform
import re
import subprocess
import time
from pathlib import Path

from harness.core import skills as skills_lib
from harness.tools.basic import SKIP_DIRS  # one fact, one home (note 29)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# The orientation snapshot (2.22, note 29): a map, not a dump. Two levels,
# capped, tier-sized - its token cost rides the whole-first-call budget.
SNAPSHOT_DIR_CAP = 20    # top-level dirs shown
SNAPSHOT_CHILD_CAP = 8   # children named per dir


def _visible(p: Path) -> bool:
    return p.name not in SKIP_DIRS and not p.name.startswith(".")


def build_snapshot(cwd: str, tier: str = "standard") -> str:
    """The project's shape, so no task starts with a blind list_dir-flail:
    micro = one line (top-level dirs + file count); compact+ = one line per
    top-level dir naming up to 8 children. Empty string on any OS trouble -
    orientation is a courtesy, never a crash."""
    root = Path(cwd)
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return ""
    dirs = [p for p in entries if p.is_dir() and _visible(p)]
    files = [p for p in entries if p.is_file() and _visible(p)]
    if not dirs and not files:
        return ""
    if tier == "micro":
        names = ", ".join(f"{d.name}/" for d in dirs[:SNAPSHOT_DIR_CAP])
        return f"Project map: {names} + {len(files)} top-level files"
    lines = []
    for d in dirs[:SNAPSHOT_DIR_CAP]:
        try:
            children = sorted((c for c in d.iterdir() if _visible(c)),
                              key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            continue
        shown = ", ".join(c.name + ("/" if c.is_dir() else "") for c in children[:SNAPSHOT_CHILD_CAP])
        more = f", +{len(children) - SNAPSHOT_CHILD_CAP} more" if len(children) > SNAPSHOT_CHILD_CAP else ""
        lines.append(f"  {d.name}/: {shown}{more}")
    if files:
        shown = ", ".join(f.name for f in files[:SNAPSHOT_CHILD_CAP])
        more = f", +{len(files) - SNAPSHOT_CHILD_CAP} more" if len(files) > SNAPSHOT_CHILD_CAP else ""
        lines.append(f"  ./: {shown}{more}")
    return ("Project map (top-level dirs and their children; dirs end with /):\n"
            + "\n".join(lines))

SECTION_MARK = re.compile(
    r"<!--\s*section:\s*([\w-]+)\s*(?:tier:\s*(\w+)\s*)?(?:world:\s*(\w+)\s*)?-->")

# The ladder (note 24): a section is included when its tag <= the active tier.
TIERS = ("micro", "compact", "standard", "full")

# The voice knob (note 25): `style-<voice>` sections collapse into ONE style
# slot; the active voice picks which. Effort is the OTHER knob - it lives on
# the wire (providers), not in the prompt. Two axes, orthogonal by design.
VOICES = ("quiet", "normal", "explain")

# The worlds (2.30, note 39) - the third axis: `core` sections ride every
# world (identity-of-character, safety, style); a world tag picks the job
# wrapper. operator = works the computer; companion = conversation. One
# character, two jobs, one file.
WORLDS = ("operator", "companion")


def parse_sections(text: str) -> list[tuple[str, str, str, str]]:
    """Backbone text -> [(name, tier, world, body), ...]. Text before the
    first marker (if any) is ignored - every real section is fenced. The
    tier tag defaults to 'standard'; the world tag defaults to 'core'
    (rides every world)."""
    marks = list(SECTION_MARK.finditer(text))
    sections = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end].strip()
        if body:
            sections.append((m.group(1), m.group(2) or "standard",
                             m.group(3) or "core", body))
    return sections


def load_backbone(tier: str = "standard", voice: str = "normal",
                  world: str = "operator") -> str:
    """The assembled backbone at a tier, voice and world: sections whose
    tier tag <= tier AND whose world tag is `core` or the active world,
    markers stripped, one blank line between sections. Same-name sections
    replace — the highest applicable tier wins, at the position of first
    appearance (so `loop` shows its one-liner at micro and the full protocol
    at standard+, from the same file). `style-<x>` sections collapse into the
    one `style` slot matching the active voice (note 25). Unknown
    tier/voice/world -> ValueError, loudly: a typo silently degrading the
    prompt would be a debugging pit."""
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r} (choose from {', '.join(TIERS)})")
    if voice not in VOICES:
        raise ValueError(f"unknown voice {voice!r} (choose from {', '.join(VOICES)})")
    if world not in WORLDS:
        raise ValueError(f"unknown world {world!r} (choose from {', '.join(WORLDS)})")
    active = TIERS.index(tier)
    text = (PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    order: list[str] = []
    chosen: dict[str, tuple[int, str]] = {}  # name -> (rank, body)
    for name, tag, sec_world, body in parse_sections(text):
        if sec_world not in ("core", world):
            continue  # another world's job wrapper
        if name.startswith("style-"):
            if name != f"style-{voice}":
                continue
            name = "style"  # every voice competes for the same slot
        rank = TIERS.index(tag) if tag in TIERS else TIERS.index("standard")
        if rank > active:
            continue
        if name not in chosen:
            order.append(name)
            chosen[name] = (rank, body)
        elif rank >= chosen[name][0]:
            chosen[name] = (rank, body)
    return "\n\n".join(chosen[name][1] for name in order)


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
                        backbone: bool = True, tier: str = "standard",
                        voice: str = "normal", world: str = "operator") -> str:
    """Assemble the system prompt (notes 23 + 24 + 25 + 39). `template` is
    the active role's body (note 17); since 2.18a it EXTENDS the backbone
    instead of replacing it — the backbone is exactly the part no role
    should lose. `backbone=False` restores replace semantics (the escape
    hatch for exotic roles). `tier` picks the ladder rung (note 24): micro
    for the 8K card, standard for the Gemini lanes, full for max
    scaffolding. `voice` picks the style section (note 25): explain is the
    Gemini default — the anti-terseness the owner asked for. `world` picks
    the job wrapper (2.30, note 39): operator works the computer, companion
    converses; the core character rides both.
    replace(), not format(): an agent prompt containing {braces} must not
    crash the assembly. A template without the placeholder gets the env
    block appended, so plain prose files work unmodified."""
    cwd = cwd or os.getcwd()
    if template is None:
        prompt = load_backbone(tier, voice, world)  # the built-in `build` role IS the backbone
    elif backbone:
        prompt = load_backbone(tier, voice, world) + "\n\n# Active role\n" + template.strip()
    else:
        prompt = template
    env = build_env_block(cwd)
    if "{env_block}" in prompt:
        # Substitute the first placeholder, drop any strays: the env block
        # must appear exactly once however the role file was written.
        prompt = prompt.replace("{env_block}", env, 1).replace("{env_block}", "")
    else:
        prompt = prompt.rstrip() + "\n\nEnvironment:\n" + env
    # Operator furniture (2.30, note 39): the project map, AGENTS.md rules
    # and skills lines exist to serve work - in the companion world (or with
    # the backbone opted out) they'd only re-invite the register the world
    # exists to shed.
    if not (backbone and world == "operator"):
        return prompt
    # Orientation (2.22, note 29): operators get the map.
    snap = build_snapshot(cwd, tier)
    if snap:
        prompt += "\n\n" + snap
    # Project memory: the file the USER owns. Cross-tool convention: AGENTS.md.
    agents_md = Path(cwd) / "AGENTS.md"
    if agents_md.exists():
        prompt += (
            "\n\nProject notes (from AGENTS.md in the working directory):\n"
            + agents_md.read_text(encoding="utf-8")
        )
    # Skills: one name+description line each (note 20). Every operator role
    # and subagent rides this same pipeline, so all of them see the library.
    block = skills_lib.skills_block(skills_lib.discover(str(Path(cwd) / "skills")))
    if block:
        prompt += "\n\n" + block
    return prompt
