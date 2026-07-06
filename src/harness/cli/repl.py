"""The REPL — everything human-facing lives here, and only here.

The permission gate, the token meter, argv parsing, environment loading:
all of it is CLI concern, injected into the loop as callables. The loop
itself stays pure (and therefore testable offline).

Run:
    uv run python -m harness             # local Ollama (free)
    uv run python -m harness gemini      # Gemini flash-lite (uses $ credit)
    uv run python -m harness -y          # auto-approve gate (scripted runs)
"""

import argparse
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

from harness.core import budget, commands
from harness.core.context import build_system_prompt
from harness.core.loop import Agent
from harness.core.permissions import load_policy
from harness.core.session import SessionStore
from harness.core.subagent import make_spawn_tool
from harness.providers.anthropic import AnthropicModel
from harness.providers.openai_compat import OpenAICompatModel
from harness.tools import basic
from harness.tools.todo import make_todo_tool

load_dotenv()

# The provider registry. Two adapters cover everything we can reach:
# "openai" (Ollama, Gemini, OpenRouter, vLLM — one wire format) and
# "anthropic" (its own dialect; see providers/anthropic.py).
PROVIDERS = {
    "ollama": {
        "kind": "openai",
        "url": "http://localhost:11434/v1/chat/completions",
        "key": "ollama",
        "model": os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct"),
        # Ollama's window is set machine-wide by this env var (8192 on this
        # machine since 2026-07-07); 4096 is Ollama's own default.
        "context_window": int(os.getenv("OLLAMA_CONTEXT_LENGTH", "4096")),
        # Local tokens are free and thinking models spend heavily BEFORE the
        # tool call — give generation headroom (2000 was thinking-death,
        # see docs/notes/11-visible-mind.md).
        "max_tokens": 4096,
    },
    "gemini": {
        "kind": "openai",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "model": "gemini-2.5-flash-lite",
        "context_window": 1_048_576,
        "max_tokens": 2000,
    },
    "anthropic": {
        "kind": "anthropic",
        "key": os.getenv("ANTHROPIC_API_KEY", ""),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        "context_window": 200_000,
        "max_tokens": 2000,
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


def make_gate(auto_approve: bool, policy):
    """The permission gate, policy-aware (docs/notes/10-permissions-v2.md):
    deny -> refuse flatly (-y can NEVER override it);
    allow -> run silently; ask -> y/N prompt (-y upgrades to yes)."""

    def approve(name: str, arguments: dict) -> bool:
        decision = policy.decide(name)
        if decision == "deny":
            print(f"  [policy] {name} is denied by harness.toml")
            return False
        if decision == "allow" or auto_approve:
            return True
        preview = json.dumps(arguments)
        if len(preview) > 200:
            preview = preview[:200] + "..."
        try:
            answer = input(f"  allow {name}({preview})? [y/N] ")
        except EOFError:  # stdin closed (piped input ran out) -> safest is no
            return False
        return answer.strip().lower() == "y"

    return approve


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("provider", nargs="?", default="ollama", choices=PROVIDERS)
    parser.add_argument("-y", "--yes", action="store_true", help="auto-approve the permission gate")
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
    # a half-printed delta stream.
    model = make_model(provider, on_delta=StreamPrinter())
    child_model = make_model(provider)

    # The token meter: non-negotiable from day 1 — this project exists
    # because of token economics. Watch prompt_tokens climb call after call.
    # (Ollama dialect: it excludes KV-cached tokens, so it can also drop.)
    totals = {"in": 0, "out": 0}

    def on_usage(usage: dict) -> None:
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        totals["in"] += p
        totals["out"] += c
        print(
            f"  [tokens] call: {p:,} in / {c:,} out"
            f" | session: {totals['in']:,} in / {totals['out']:,} out"
        )

    def persist(message: dict) -> None:
        store.append(session_id, message)

    policy = load_policy()
    gate = make_gate(auto_approve, policy)

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
        system_prompt=build_system_prompt(),
        on_usage=on_usage,
    )
    # The todo list is top-level only: children never see its schema, so they
    # never call it (docs/notes/13-todo-tool.md).
    todo_fn, todo_schema = make_todo_tool(emit=print)
    registry = dict(basic.REGISTRY, spawn_subagent=spawn_fn, todo_write=todo_fn)
    schemas = basic.SCHEMAS + [spawn_schema, todo_schema]

    agent = Agent(
        model=model,
        registry=registry,
        schemas=schemas,
        # Every tool goes through the gate; the POLICY decides who runs
        # silently (allow), who prompts (ask), who never runs (deny).
        needs_permission=set(registry),
        approve=gate,
        emit_thinking=print_thinking,
        on_usage=on_usage,
        on_message=persist,
    )

    window = provider.get("context_window", 0)
    print(f"researcher-harness | provider: {provider_name} | model: {provider['model']}")
    print(f"session: {session_id} | type a task, 'exit' to quit")
    if not messages:  # fresh session gets the system prompt as message zero
        messages = [{"role": "system", "content": build_system_prompt()}]
        persist(messages[0])
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
            print("  builtins: /tokens /compact /help | templates (commands/*.md): " + templates)
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
