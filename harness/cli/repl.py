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

import truststore

truststore.inject_into_ssl()  # this machine has TLS interception (see labs/02)

import requests
from dotenv import load_dotenv

from harness.core import budget
from harness.core.context import build_system_prompt
from harness.core.loop import Agent
from harness.core.session import SessionStore
from harness.core.subagent import make_spawn_tool
from harness.providers.anthropic import AnthropicModel
from harness.providers.openai_compat import OpenAICompatModel
from harness.tools import basic

load_dotenv()

# The provider registry. Two adapters cover everything we can reach:
# "openai" (Ollama, Gemini, OpenRouter, vLLM — one wire format) and
# "anthropic" (its own dialect; see providers/anthropic.py).
PROVIDERS = {
    "ollama": {
        "kind": "openai",
        "url": "http://localhost:11434/v1/chat/completions",
        "key": "ollama",
        "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        "context_window": 4096,  # Ollama's default num_ctx (see docs/problem.md)
    },
    "gemini": {
        "kind": "openai",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "model": "gemini-2.5-flash-lite",
        "context_window": 1_048_576,
    },
    "anthropic": {
        "kind": "anthropic",
        "key": os.getenv("ANTHROPIC_API_KEY", ""),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        "context_window": 200_000,
    },
}


def make_model(cfg: dict):
    if cfg["kind"] == "anthropic":
        if not cfg["key"]:
            sys.exit(
                "No ANTHROPIC_API_KEY set. That's intentional (see CLAUDE.md):\n"
                "a stray key silently bills pay-as-you-go. Set it in .env only\n"
                "when you deliberately want live Anthropic calls."
            )
        return AnthropicModel(cfg["key"], cfg["model"])
    return OpenAICompatModel(cfg["url"], cfg["key"], cfg["model"])

# The system prompt is ASSEMBLED, not hardcoded — see core/context.py:
# identity template + environment block + AGENTS.md project memory.


def make_gate(auto_approve: bool):
    """First taste of the permission layer every serious harness has."""

    def approve(name: str, arguments: dict) -> bool:
        if auto_approve:
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

    model = make_model(provider)

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

    gate = make_gate(auto_approve)

    # The spawn tool closes over the LIVE messages list (rebound on /compact),
    # hence the lambda instead of the list itself.
    spawn_fn, spawn_schema = make_spawn_tool(
        model=model,
        registry=basic.REGISTRY,
        schemas=basic.SCHEMAS,
        needs_permission=basic.NEEDS_PERMISSION,
        approve=gate,
        emit=print,
        get_parent_messages=lambda: messages,
        system_prompt=build_system_prompt(),
        on_usage=on_usage,
    )
    registry = dict(basic.REGISTRY, spawn_subagent=spawn_fn)
    schemas = basic.SCHEMAS + [spawn_schema]

    agent = Agent(
        model=model,
        registry=registry,
        schemas=schemas,
        needs_permission=basic.NEEDS_PERMISSION,
        approve=gate,
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

        # ---- slash commands (2.7 generalizes this to template commands) ----
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
            print(f"  unknown command {user} (try /tokens or /compact)")
            continue

        messages.append({"role": "user", "content": user})
        persist(messages[-1])
        try:
            agent.run_turn(messages)
        except requests.RequestException as e:
            print(f"  [!] API error: {e}")
        print(budget.budget_line(budget.estimate_tokens(messages), window))
    print(f"\nsession total: {totals['in']:,} in / {totals['out']:,} out tokens")
