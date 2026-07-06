"""Permissions v2: three-state policy (allow | ask | deny) from harness.toml.

Read-only tools default to allow because y/N fatigue is how users learn to
blind-approve everything — a gate that fires constantly protects nothing.
Tie-break is fail-closed: deny beats ask beats allow. And -y (auto-approve)
upgrades *ask* only; deny is deny, even overnight. Especially overnight.
"""

import tomllib
from pathlib import Path

VALID = {"allow", "ask", "deny"}


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


def load_policy(path: str = "harness.toml") -> Policy:
    fp = Path(path)
    if not fp.exists():
        return Policy()  # no config -> everything asks (safe default)
    with open(fp, "rb") as f:
        data = tomllib.load(f)
    section = data.get("permissions", {})
    return Policy(
        default=section.get("default", "ask"),
        allow=set(section.get("allow", [])),
        ask=set(section.get("ask", [])),
        deny=set(section.get("deny", [])),
    )
