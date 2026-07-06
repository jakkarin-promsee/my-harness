"""The REPL — everything human-facing lives here, and only here.

The permission gate, the token meter, argv parsing, environment loading:
all of it is CLI concern, injected into the loop as callables. The loop
itself stays pure (and therefore testable offline).

Run:
    uv run python -m harness             # local Ollama (free)
    uv run python -m harness gemini      # Gemini flash-lite (uses $ credit)
    uv run python -m harness -y          # auto-approve gate (scripted runs)
"""

import json
import os
import sys

import truststore

truststore.inject_into_ssl()  # this machine has TLS interception (see labs/02)

import requests
from dotenv import load_dotenv

from harness.core.loop import Agent
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
    },
    "gemini": {
        "kind": "openai",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "model": "gemini-2.5-flash-lite",
    },
    "anthropic": {
        "kind": "anthropic",
        "key": os.getenv("ANTHROPIC_API_KEY", ""),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
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

SYSTEM_PROMPT = f"""You are a coding agent running in a terminal on Windows.
Working directory: {os.getcwd()}

Rules:
- Use the tools to inspect and change files; never guess file contents.
- Run Python files with: uv run python <path>
- Keep answers short. When the task is done, state the result plainly."""


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


def main() -> None:
    args = sys.argv[1:]
    auto_approve = "-y" in args
    provider_name = next((a for a in args if not a.startswith("-")), "ollama")
    provider = PROVIDERS[provider_name]

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

    agent = Agent(
        model=model,
        registry=basic.REGISTRY,
        schemas=basic.SCHEMAS,
        needs_permission=basic.NEEDS_PERMISSION,
        approve=make_gate(auto_approve),
        on_usage=on_usage,
    )

    print(f"researcher-harness | provider: {provider_name} | model: {provider['model']}")
    print("type a task, 'exit' to quit")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        try:
            user = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() in {"exit", "quit"}:
            break
        if not user:
            continue
        messages.append({"role": "user", "content": user})
        try:
            agent.run_turn(messages)
        except requests.RequestException as e:
            print(f"  [!] API error: {e}")
    print(f"\nsession total: {totals['in']:,} in / {totals['out']:,} out tokens")
