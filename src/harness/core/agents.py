"""Agents: a role is a markdown file. Frontmatter = the knobs, body = the prompt.

The shape every senior converged on (docs/notes/17-agents.md): opencode
agents, Claude Code subagents, aider's architect/editor. An agent bundles
*behavior* (its system prompt), a default permission *mode* (2.10 profile),
and optionally a pinned *model* (provider name) — aider proved per-role
models are the cheap intelligence hack.

`build` is a code-level built-in, not a file: its body already lives in
prompts/system.md (one fact, one home). Everything else is agents/*.md at
the cwd — the same runtime-dir pattern as commands/ (2.7).

Frontmatter is hand-parsed `key: value` lines between --- fences. No yaml
dependency for four flat keys; comments (#) and blanks are ignored; a file
without frontmatter is all prompt.
"""

from pathlib import Path

# The knobs an agent file may set. `think` is parsed now, applied in 2.12.
KNOWN_KEYS = {"description", "model", "mode", "think", "backbone", "tier"}


class AgentSpec:
    def __init__(self, name: str, prompt: str, description: str = "",
                 model: str | None = None, mode: str | None = None,
                 think: str | None = None, backbone: bool = True,
                 tier: str | None = None):
        self.name = name
        self.prompt = prompt          # the system prompt body (env appended at assembly)
        self.description = description
        self.model = model            # provider name to pin, or None = session default
        self.mode = mode              # default permission profile, or None = leave as-is
        self.think = think            # default reasoning level (2.12), or None
        # Roles EXTEND the backbone by default (note 23); `backbone: false`
        # opts out - for roles where an operator identity is nonsense (chill).
        self.backbone = backbone
        self.tier = tier              # ladder override (note 24), or None = session default


def parse_agent_file(name: str, text: str) -> AgentSpec:
    meta, body = split_frontmatter(text, KNOWN_KEYS)
    return AgentSpec(
        name=name,
        prompt=body.strip(),
        description=meta.get("description", ""),
        model=meta.get("model"),
        mode=meta.get("mode"),
        think=meta.get("think"),
        backbone=meta.get("backbone", "").lower() not in {"false", "no", "off"},
        tier=meta.get("tier"),
    )


def split_frontmatter(text: str, known_keys: set) -> tuple[dict, str]:
    """'---\\nkey: value\\n---\\nbody' -> ({key: value}, body).
    No opening fence -> no frontmatter, the whole file is body.
    Shared with skills.py (note 20) — one parser, one home."""
    if not text.startswith("---"):
        return {}, text
    first_newline = text.find("\n")
    end = text.find("\n---", first_newline)
    if end == -1:
        return {}, text  # unclosed fence: treat as body, don't eat the file
    meta = {}
    for line in text[first_newline + 1:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key in known_keys and value:
            meta[key] = value
    body = text[end + len("\n---"):]
    return meta, body


def discover(directory: str = "agents") -> dict[str, AgentSpec]:
    """agents/*.md at the cwd -> {name: spec}. Missing dir -> {} (build
    always exists; the caller adds it — see cli/repl.py)."""
    d = Path(directory)
    if not d.is_dir():
        return {}
    specs = {}
    for fp in sorted(d.glob("*.md")):
        if fp.stem == "README":  # the folder map is for humans, not a role
            continue
        specs[fp.stem] = parse_agent_file(fp.stem, fp.read_text(encoding="utf-8"))
    return specs
