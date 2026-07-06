"""Permissions v2: three-state policy (allow | ask | deny) from harness.toml.
Plus modes (2.10): named policy profiles, switchable at runtime.

Read-only tools default to allow because y/N fatigue is how users learn to
blind-approve everything — a gate that fires constantly protects nothing.
Tie-break is fail-closed: deny beats ask beats allow. And -y (auto-approve)
upgrades *ask* only; deny is deny, even overnight. Especially overnight.

A mode is just WHICH table is active (docs/notes/16-permission-modes.md):
`build` is the plain [permissions] table; [modes.<name>] sections add the
others (chat / explore / auto ship in harness.toml). Two laws hold in every
mode: the deny list is absolute, and an `allow` on a path-writing tool only
counts inside the working directory (Claude Code's acceptEdits scoping rule)
— outside, it degrades to ask.
"""

import tomllib
from pathlib import Path

VALID = {"allow", "ask", "deny"}

# Tools whose `allow` is scoped to cwd: auto-approving a write is fine for
# ./notes.md and very much not fine for C:/Windows/anything.
SCOPED_TOOLS = {"write_file", "edit_file"}


class Policy:
    def __init__(self, default: str = "ask", allow: set | None = None,
                 ask: set | None = None, deny: set | None = None):
        if default not in VALID:
            raise ValueError(f"default must be one of {VALID}, got {default!r}")
        self.default = default
        self.allow = set(allow or ())
        self.ask = set(ask or ())
        self.deny = set(deny or ())

    def decide(self, tool_name: str) -> str:
        # deny > ask > allow: a tool listed twice fails closed.
        if tool_name in self.deny:
            return "deny"
        if tool_name in self.ask:
            return "ask"
        if tool_name in self.allow:
            return "allow"
        return self.default

    def decide_call(self, tool_name: str, arguments: dict) -> str:
        """decide(), plus the scoping rule: an allow on a path-writing tool
        holds only inside cwd — outside it degrades to ask (fail-closed)."""
        decision = self.decide(tool_name)
        if decision == "allow" and tool_name in SCOPED_TOOLS:
            if not _inside_cwd(str(arguments.get("path", ""))):
                return "ask"
        return decision


def _inside_cwd(path: str) -> bool:
    # resolve() flattens ../ tricks and symlinks before the containment test;
    # a path that can't resolve (illegal chars) fails closed too. So does a
    # MISSING path: Path("") resolves to cwd itself and would fail open.
    if not path:
        return False
    try:
        return Path(path).resolve().is_relative_to(Path.cwd().resolve())
    except (OSError, ValueError):
        return False


class Mode:
    """A named profile: a Policy plus whether tools are offered at all.
    `send_tools=False` is chat mode — the tools array isn't even sent."""

    def __init__(self, policy: Policy, send_tools: bool = True):
        self.policy = policy
        self.send_tools = send_tools


class ModeSet:
    """The loaded profiles + which one is active. The gate reads `.policy`
    per call, so /mode switches take effect mid-session."""

    def __init__(self, modes: dict[str, Mode], active: str = "build"):
        if active not in modes:
            raise ValueError(f"unknown mode {active!r} (available: {sorted(modes)})")
        self.modes = modes
        self.active = active

    def switch(self, name: str) -> None:
        if name not in self.modes:
            raise ValueError(f"unknown mode {name!r} (available: {sorted(self.modes)})")
        self.active = name

    @property
    def policy(self) -> Policy:
        return self.modes[self.active].policy

    @property
    def send_tools(self) -> bool:
        return self.modes[self.active].send_tools


def _parse_policy(section: dict) -> Policy:
    return Policy(
        default=section.get("default", "ask"),
        allow=set(section.get("allow", [])),
        ask=set(section.get("ask", [])),
        deny=set(section.get("deny", [])),
    )


def load_policy(path: str = "harness.toml") -> Policy:
    fp = Path(path)
    if not fp.exists():
        return Policy()  # no config -> everything asks (safe default)
    with open(fp, "rb") as f:
        data = tomllib.load(f)
    return _parse_policy(data.get("permissions", {}))


def load_modes(path: str = "harness.toml") -> dict[str, Mode]:
    """`build` = the plain [permissions] table (one fact, one home);
    [modes.<name>] sections define the rest. Missing file -> build only,
    with note 10's safe default (everything asks)."""
    fp = Path(path)
    data = {}
    if fp.exists():
        with open(fp, "rb") as f:
            data = tomllib.load(f)
    modes = {"build": Mode(_parse_policy(data.get("permissions", {})))}
    for name, section in data.get("modes", {}).items():
        modes[name] = Mode(
            policy=_parse_policy(section),
            send_tools=section.get("tools", True),
        )
    return modes
