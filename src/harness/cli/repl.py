"""The REPL — everything human-facing lives here, and only here.

The permission gate, the token meter, argv parsing, environment loading:
all of it is CLI concern, injected into the loop as callables. The loop
itself stays pure (and therefore testable offline).

Run:
    uv run python -m harness             # local Ollama (free)
    uv run python -m harness gemini      # Gemini flash-lite (uses $ credit)
    uv run python -m harness -y          # auto-approve gate (scripted runs)
    uv run python -m harness --mode explore   # read-only profile (note 16)
    uv run python -m harness --agent plan     # role from agents/*.md (note 17)
"""

import argparse
import difflib
import json
import os
import sys

# Windows pipes/legacy consoles default to cp1252; a single ✓ or emoji from a
# model then crashes print() with UnicodeEncodeError. UTF-8, never crash.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import truststore

truststore.inject_into_ssl()  # this machine has TLS interception (see archive/labs/02)

import requests
from dotenv import load_dotenv

from harness.core import agents as roles
from harness.core import budget, commands
from harness.core.context import TIERS, VOICES, build_system_prompt, load_backbone
from harness.core.loop import Agent
from harness.core.permissions import ModeSet, load_modes
from harness.core.session import SessionStore
from harness.core.subagent import make_spawn_tool
from harness.providers.anthropic import AnthropicModel
from harness.providers.ollama_native import OllamaNativeModel
from harness.providers.openai_compat import OpenAICompatModel
from harness.tools import basic
from harness.tools.todo import make_todo_tool

load_dotenv()

# The provider registry. Three adapters cover everything we can reach:
# "ollama-native" (/api/chat — the only wire where `think` works, note 18),
# "openai" (Gemini, OpenRouter, vLLM — one compat format) and
# "anthropic" (its own dialect; see providers/anthropic.py).
PROVIDERS = {
    "ollama": {
        "kind": "ollama-native",
        "url": "http://localhost:11434/api/chat",
        "key": "ollama",
        "model": os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct"),
        # Ollama's window is set machine-wide by this env var (8192 on this
        # machine since 2026-07-07); 4096 is Ollama's own default.
        "context_window": int(os.getenv("OLLAMA_CONTEXT_LENGTH", "4096")),
        # Local tokens are free and thinking models spend heavily BEFORE the
        # tool call — give generation headroom (2000 was thinking-death,
        # see docs/notes/11-visible-mind.md).
        "max_tokens": 4096,
        # The ladder tier (note 24): the 8K card runs the ~200-token MICRO
        # backbone; the whole-first-call budget is the reason the ladder exists.
        "tier": "micro",
        # Narration costs window on 8K (note 25) - normal, not explain.
        "voice": "normal",
    },
    # Two Gemini lanes since 2.17 (ROADMAP3 §4): "gemini" = flash-lite, the
    # cheap REGRESSION lane (before/after-every-feature runs); "gemini-flash"
    # = the QUALITY lane (museum baselines, labs, flash-facing acceptance).
    "gemini": {
        "kind": "openai",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "model": "gemini-2.5-flash-lite",
        "context_window": 1_048_576,
        "max_tokens": 2000,
        "tier": "standard",
        # The owner's wish (note 25): Gemini narrates and teaches by default.
        "voice": "explain",
    },
    "gemini-flash": {
        "kind": "openai",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "model": "gemini-2.5-flash",
        "context_window": 1_048_576,
        # Flash THINKS BY DEFAULT and its thinking bills as completion tokens
        # (note 22's probe); 2000 would be thinking-death — the note-11
        # lesson, paid edition. 2.19 wires the off-switch.
        "max_tokens": 8192,
        "tier": "standard",
        "voice": "explain",
    },
    "anthropic": {
        "kind": "anthropic",
        "key": os.getenv("ANTHROPIC_API_KEY", ""),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        "context_window": 200_000,
        "max_tokens": 2000,
        "tier": "standard",
    },
}


def make_model(cfg: dict, on_delta=None):
    max_tokens = cfg.get("max_tokens", 2000)
    if cfg["kind"] == "anthropic":
        if not cfg["key"]:
            sys.exit(
                "No ANTHROPIC_API_KEY set. That's intentional (see CLAUDE.md):\n"
                "a stray key silently bills pay-as-you-go. Set it in .env only\n"
                "when you deliberately want live Anthropic calls."
            )
        # The insurance adapter doesn't stream (docs/notes/12-streaming.md).
        return AnthropicModel(cfg["key"], cfg["model"], max_tokens=max_tokens)
    if cfg["kind"] == "ollama-native":
        return OllamaNativeModel(cfg["url"], cfg["model"],
                                 max_tokens=max_tokens, on_delta=on_delta)
    return OpenAICompatModel(cfg["url"], cfg["key"], cfg["model"],
                             max_tokens=max_tokens, on_delta=on_delta)


# Thinking is rendered dim (ANSI SGR 2) so the inner voice reads as inner
# voice. os.system("") is the documented trick that flips the legacy Windows
# console into VT mode; it's a no-op everywhere else.
os.system("")
DIM, RESET = "\033[2m", "\033[0m"


def print_thinking(text: str) -> None:
    print(f"{DIM}  [thinking] {text}{RESET}")


class StreamPrinter:
    """Live deltas -> terminal (docs/notes/12-streaming.md): dim while the
    model thinks, an `agent> ` line when it talks, newline when the stream
    ends. One instance per REPL; state is just which voice is speaking."""

    def __init__(self):
        self.mode = None  # None | "reasoning" | "content"

    def __call__(self, kind: str, text: str) -> None:
        if kind == "end":
            if self.mode == "reasoning":
                print(RESET, end="")
            if self.mode:
                print(flush=True)
            self.mode = None
            return
        if kind != self.mode:
            if self.mode == "reasoning":
                print(RESET, end="")
            print(f"\n{DIM}  [thinking] " if kind == "reasoning" else "\nagent> ",
                  end="")
            self.mode = kind
        print(text, end="", flush=True)

# The system prompt is ASSEMBLED, not hardcoded — see core/context.py:
# identity template + environment block + AGENTS.md project memory.


MAX_DIFF_LINES = 40  # an unbounded render is the same disease as unbounded tool output

GREEN, RED, CYAN = "\033[32m", "\033[31m", "\033[36m"


def render_diff(name: str, arguments: dict) -> str | None:
    """Unified-diff preview for the gate (note 19): edit_file diffs
    old_string -> new_string; write_file diffs the target's current content
    (missing file -> all additions) -> content. Returns None for any other
    tool or an empty diff — the gate falls back to the JSON preview then.
    Plain text on purpose: color is the printer's job, this stays testable."""
    if name == "edit_file":
        old = str(arguments.get("old_string", ""))
        new = str(arguments.get("new_string", ""))
    elif name == "write_file":
        new = str(arguments.get("content", ""))
        try:
            with open(str(arguments.get("path", "")), encoding="utf-8", errors="replace") as f:
                old = f.read()
        except OSError:  # new or unreadable file -> everything is an addition
            old = ""
    else:
        return None
    path = arguments.get("path", "?")
    lines = list(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="",
    ))
    if not lines:
        return None
    if len(lines) > MAX_DIFF_LINES:
        lines = lines[:MAX_DIFF_LINES] + [f"... ({len(lines) - MAX_DIFF_LINES} more diff lines)"]
    return "\n".join(lines)


def _color_diff_line(line: str) -> str:
    if line.startswith("+") and not line.startswith("+++"):
        return f"{GREEN}{line}{RESET}"
    if line.startswith("-") and not line.startswith("---"):
        return f"{RED}{line}{RESET}"
    if line.startswith("@@"):
        return f"{CYAN}{line}{RESET}"
    return line


def make_gate(auto_approve: bool, modeset: ModeSet):
    """The permission gate, mode-aware (docs/notes/10 + 16):
    deny -> refuse flatly (-y can NEVER override it);
    allow -> run silently (writes: only inside cwd — decide_call's scoping
    rule); ask -> y/N prompt (-y upgrades to yes). Reads the ACTIVE mode's
    policy per call, so /mode switches apply mid-session. Edits/writes render
    a unified diff at the prompt instead of raw JSON args (note 19)."""

    def approve(name: str, arguments: dict) -> bool:
        decision = modeset.policy.decide_call(name, arguments)
        if decision == "deny":
            print(f"  [policy] {name} is denied in mode '{modeset.active}'")
            return False
        if decision == "allow" or auto_approve:
            return True
        diff = render_diff(name, arguments)
        if diff is not None:
            for line in diff.splitlines():
                print(f"  {_color_diff_line(line)}")
            prompt = f"  allow {name} on {arguments.get('path', '?')}? [y/N] "
        else:
            preview = json.dumps(arguments)
            if len(preview) > 200:
                preview = preview[:200] + "..."
            prompt = f"  allow {name}({preview})? [y/N] "
        try:
            answer = input(prompt)
        except EOFError:  # stdin closed (piped input ran out) -> safest is no
            return False
        return answer.strip().lower() == "y"

    return approve


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("provider", nargs="?", default="ollama", choices=PROVIDERS)
    parser.add_argument("-y", "--yes", action="store_true", help="auto-approve the permission gate")
    parser.add_argument(
        "--mode", default=None, metavar="NAME",
        help="permission mode to start in (chat/explore/build/auto; see harness.toml). "
             "Explicit --mode beats the agent's default",
    )
    parser.add_argument(
        "--agent", default=None, metavar="NAME",
        help="role to start as (build + agents/*.md at the cwd; see docs/notes/17)",
    )
    parser.add_argument(
        "--resume", nargs="?", const="latest", default=None, metavar="ID",
        help="continue a saved session (latest if no ID given)",
    )
    parser.add_argument("--sessions", action="store_true", help="list saved sessions and exit")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    auto_approve = args.yes
    provider_name = args.provider
    provider = PROVIDERS[provider_name]

    # Roles (note 17): the code-level `build` built-in + agents/*.md at cwd.
    # build has no file — its body IS prompts/system.md (one fact, one home).
    agent_specs = {"build": roles.AgentSpec(
        "build", prompt="", description="the default working agent", mode="build")}
    agent_specs.update(roles.discover())
    active_agent = args.agent or "build"
    if active_agent not in agent_specs:
        sys.exit(f"unknown agent {active_agent!r} - available: {', '.join(sorted(agent_specs))}")

    def assemble(spec: roles.AgentSpec) -> str:
        # Same 2.4 pipeline for every role; since 2.18a a role EXTENDS the
        # backbone unless its frontmatter says `backbone: false` (note 23).
        # `tier` is read LIVE from the enclosing scope, so /prompt switches
        # and spawn-time children (note 24) both see the current rung.
        return build_system_prompt(template=spec.prompt or None,
                                   backbone=spec.backbone, tier=tier,
                                   voice=voice)

    store = SessionStore()
    if args.sessions:
        print("\n".join(store.listing()) or "no sessions yet")
        return

    if args.resume:
        session_id = store.latest() if args.resume == "latest" else args.resume
        if session_id is None:
            sys.exit("nothing to resume - no sessions yet")
        messages = store.load(session_id)
        print(f"resumed session {session_id} ({len(messages)} messages)")
    else:
        session_id = store.new()
        messages = []

    # Top-level agent streams (watch it think); the subagent below gets its
    # own NON-streaming model so [sub]-prefixed lines never interleave with
    # a half-printed delta stream. A role may pin its own provider (aider's
    # architect/editor economics) — primary only; children keep the session's.
    primary_cfg = provider
    if agent_specs[active_agent].model in PROVIDERS:
        primary_cfg = PROVIDERS[agent_specs[active_agent].model]
    elif agent_specs[active_agent].model:
        print(f"  [!] agent {active_agent!r} pins unknown provider "
              f"{agent_specs[active_agent].model!r} - using {provider_name}")
    # The ladder rung (note 24): agent frontmatter beats the provider default.
    tier = agent_specs[active_agent].tier or primary_cfg.get("tier", "standard")
    if tier not in TIERS:
        sys.exit(f"unknown tier {tier!r} - available: {', '.join(TIERS)}")
    # The voice knob (note 25): agent frontmatter beats the provider default.
    voice = agent_specs[active_agent].voice or primary_cfg.get("voice", "normal")
    if voice not in VOICES:
        sys.exit(f"unknown voice {voice!r} - available: {', '.join(VOICES)}")
    model = make_model(primary_cfg, on_delta=StreamPrinter())
    model.think = agent_specs[active_agent].think  # role default; /think overrides
    child_model = make_model(provider)

    # The token meter: non-negotiable from day 1 — this project exists
    # because of token economics. Watch prompt_tokens climb call after call.
    # (Ollama dialect: it excludes KV-cached tokens, so it can also drop.)
    totals = {"in": 0, "out": 0}

    def on_usage(usage: dict) -> None:
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        # Gemini hides thinking in total_tokens (note 22, probe b): derive it.
        # Ollama's wire reports totals only - think stays 0 there, honestly.
        t = usage.get("total_tokens")
        think = max(0, t - p - c) if t else 0
        totals["in"] += p
        totals["out"] += c
        totals["think"] = totals.get("think", 0) + think
        line = f"  [tokens] call: {p:,} in / {c:,} out"
        if think:
            line += f" / {think:,} think"
        line += f" | session: {totals['in']:,} in / {totals['out']:,} out"
        if totals.get("think"):
            line += f" / {totals['think']:,} think"
        print(line)

    def persist(message: dict) -> None:
        store.append(session_id, message)

    modes = load_modes()
    # Explicit --mode wins; else the agent's default; else build (note 17 —
    # an agent only sets the DEFAULT, /mode still switches freely after).
    mode_name = args.mode or agent_specs[active_agent].mode or "build"
    if mode_name not in modes:
        sys.exit(f"unknown mode {mode_name!r} - available: {', '.join(sorted(modes))}")
    modeset = ModeSet(modes, active=mode_name)
    gate = make_gate(auto_approve, modeset)

    # The spawn tool closes over the LIVE messages list (rebound on /compact),
    # hence the lambda instead of the list itself.
    spawn_fn, spawn_schema = make_spawn_tool(
        model=child_model,
        registry=basic.REGISTRY,
        schemas=basic.SCHEMAS,
        needs_permission=set(basic.REGISTRY),  # child: gate decides via policy
        approve=gate,
        emit=print,
        get_parent_messages=lambda: messages,
        # Callables, not strings: children assemble at SPAWN time (note 24),
        # so /prompt and /agent switches reach them.
        system_prompt=lambda: assemble(agent_specs[active_agent]),
        on_usage=on_usage,
        # The registry that serves /agent serves fresh children too (note 17).
        agent_prompts={n: (lambda s=s: assemble(s)) for n, s in agent_specs.items()},
    )
    # The todo list is top-level only: children never see its schema, so they
    # never call it (docs/notes/13-todo-tool.md).
    todo_fn, todo_schema = make_todo_tool(emit=print)
    registry = dict(basic.REGISTRY, spawn_subagent=spawn_fn, todo_write=todo_fn)
    schemas = basic.SCHEMAS + [spawn_schema, todo_schema]

    agent = Agent(
        model=model,
        registry=registry,
        # chat mode doesn't even offer the tools array (note 16); every other
        # mode advertises everything and lets the policy sort it out.
        schemas=schemas if modeset.send_tools else [],
        # Every tool goes through the gate; the ACTIVE MODE's policy decides
        # who runs silently (allow), who prompts (ask), who never runs (deny).
        needs_permission=set(registry),
        approve=gate,
        emit_thinking=print_thinking,
        on_usage=on_usage,
        on_message=persist,
    )

    window = primary_cfg.get("context_window", 0)
    print(f"researcher-harness | provider: {provider_name} | model: {primary_cfg['model']}"
          f" | mode: {modeset.active} | agent: {active_agent} | prompt: {tier} | voice: {voice}")
    print(f"session: {session_id} | type a task, 'exit' to quit")
    if not messages:  # fresh session gets the system prompt as message zero
        messages = [{"role": "system", "content": assemble(agent_specs[active_agent])}]
        persist(messages[0])
    elif args.agent:
        # --agent on a resumed session = an immediate role switch: swap the
        # system message and migrate to a new file, so a later --resume
        # replays the prompt that actually governed this run.
        messages[0] = {"role": "system", "content": assemble(agent_specs[active_agent])}
        session_id = store.new()
        for m in messages:
            persist(m)
        print(f"  agent: {active_agent} | continued in session {session_id}")
    while True:
        try:
            user = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() in {"exit", "quit"}:
            break
        if not user:
            continue

        # ---- slash commands: builtins first, then template commands ----
        if user == "/help":
            templates = ", ".join(f"/{n}" for n in commands.discover()) or "(none)"
            print("  builtins: /tokens /compact /mode /agent /think /prompt /voice /help | templates (commands/*.md): " + templates)
            continue
        if user == "/prompt" or user.startswith("/prompt "):
            value = user.removeprefix("/prompt").strip()
            if not value:
                # The ladder menu with measured costs (note 24): the meter,
                # not the docs, gets the final word on what a tier costs.
                for t in TIERS:
                    est = budget.estimate_tokens(
                        [{"role": "system", "content": load_backbone(t)}])
                    mark = "*" if t == tier else " "
                    print(f"  {mark} {t:<9} backbone ~{est:,} tokens")
                continue
            if value not in TIERS:
                print(f"  invalid tier {value!r} (choose from {', '.join(TIERS)})")
                continue
            tier = value
            # /agent precedent (note 24): swap the system message, continue
            # in a NEW session file so --resume replays what actually ran.
            messages[0] = {"role": "system", "content": assemble(agent_specs[active_agent])}
            session_id = store.new()
            for m in messages:
                persist(m)
            print(f"  prompt tier: {tier} | session: {session_id}")
            continue
        if user == "/voice" or user.startswith("/voice "):
            value = user.removeprefix("/voice").strip()
            if not value:
                print(f"  voice: {voice} (available: {', '.join(VOICES)})")
                continue
            if value not in VOICES:
                print(f"  invalid voice {value!r} (choose from {', '.join(VOICES)})")
                continue
            voice = value
            # Same lifecycle as /prompt and /agent: swap the system message,
            # continue in a NEW session file (note 25).
            messages[0] = {"role": "system", "content": assemble(agent_specs[active_agent])}
            session_id = store.new()
            for m in messages:
                persist(m)
            print(f"  voice: {voice} | session: {session_id}")
            continue
        if user == "/think" or user.startswith("/think "):
            value = user.removeprefix("/think").strip()
            if not value:
                print(f"  think: {agent.model.think or 'off'} (off|on|low|medium|high)")
                continue
            if value not in {"off", "on", "low", "medium", "high"}:
                print(f"  invalid value {value!r} (off|on|low|medium|high)")
                continue
            # A session knob: the primary AND the subagent model follow it.
            agent.model.think = value
            child_model.think = value
            print(f"  think: {value}")
            continue
        if user == "/agent" or user.startswith("/agent "):
            name = user.removeprefix("/agent").strip()
            if not name:
                for n, s in sorted(agent_specs.items()):
                    mark = "*" if n == active_agent else " "
                    print(f"  {mark} {n:<10} {s.description}")
                continue
            if name not in agent_specs:
                print(f"  unknown agent {name!r} (available: {', '.join(sorted(agent_specs))})")
                continue
            sw = agent_specs[name]
            if sw.tier in TIERS:
                tier = sw.tier  # the role's ladder override (note 24)
            elif sw.tier:
                print(f"  [!] agent {name!r} names unknown tier {sw.tier!r} - keeping {tier}")
            if sw.voice in VOICES:
                voice = sw.voice  # the role's voice override (note 25)
            elif sw.voice:
                print(f"  [!] agent {name!r} names unknown voice {sw.voice!r} - keeping {voice}")
            messages[0] = {"role": "system", "content": assemble(sw)}
            if sw.mode and sw.mode in modeset.modes:
                modeset.switch(sw.mode)
                agent.schemas = schemas if modeset.send_tools else []
            elif sw.mode:
                print(f"  [!] agent {name!r} names unknown mode {sw.mode!r} - keeping {modeset.active}")
            cfg = PROVIDERS.get(sw.model, provider) if sw.model else provider
            if sw.model and sw.model not in PROVIDERS:
                print(f"  [!] agent {name!r} pins unknown provider {sw.model!r} - keeping {provider_name}")
            agent.model = make_model(cfg, on_delta=StreamPrinter())
            agent.model.think = sw.think  # the role's default; /think overrides
            window = cfg.get("context_window", 0)
            active_agent = name
            # /compact precedent: memory carries the history over; the on-disk
            # transcript stays append-only, so continue in a NEW session file.
            session_id = store.new()
            for m in messages:
                persist(m)
            print(f"  agent: {name} | mode: {modeset.active} | model: {cfg['model']} | session: {session_id}")
            continue
        if user == "/mode" or user.startswith("/mode "):
            name = user.removeprefix("/mode").strip()
            if not name:
                print(f"  mode: {modeset.active} | available: {', '.join(sorted(modeset.modes))}")
                continue
            try:
                modeset.switch(name)
            except ValueError as e:
                print(f"  {e}")
                continue
            # The gate reads the active policy per call; only the tools array
            # needs rewiring (chat offers none).
            agent.schemas = schemas if modeset.send_tools else []
            print(f"  mode: {modeset.active}")
            continue
        if user == "/tokens":
            print(budget.budget_line(budget.estimate_tokens(messages), window))
            continue
        if user == "/compact":
            print("  compacting (this costs a model call - watch the meter)...")
            try:
                messages, usage = budget.compact(model, messages)
            except requests.RequestException as e:
                print(f"  [!] API error: {e}")
                continue
            if usage:
                on_usage(usage)
            # Old transcript stays intact on disk; compacted context lives on
            # in a NEW session file (resuming the old id = full history back).
            session_id = store.new()
            for m in messages:
                persist(m)
            print(budget.budget_line(budget.estimate_tokens(messages), window))
            print(f"  continued in session {session_id}")
            continue
        if user.startswith("/"):
            expanded = commands.expand(user, commands.discover())
            if expanded is None:
                print(f"  unknown command {user} (try /help)")
                continue
            user = expanded  # the rendered template becomes the user message

        messages.append({"role": "user", "content": user})
        persist(messages[-1])
        try:
            agent.run_turn(messages)
        except requests.RequestException as e:
            print(f"  [!] API error: {e}")
        print(budget.budget_line(budget.estimate_tokens(messages), window))
    print(f"\nsession total: {totals['in']:,} in / {totals['out']:,} out tokens")
