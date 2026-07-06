"""OpenAI-compatible provider client: one HTTP POST + dialect normalization.

Covers Ollama, Gemini, OpenRouter, vLLM — everything that speaks
/v1/chat/completions. The adapter's job is to hide the wire format from the
loop: `complete()` returns a small normalized dict, so the loop (and the
tests' FakeModel) never see raw provider JSON. providers/anthropic.py is the
native sibling behind this same interface.

Thinking dialects (docs/notes/11-visible-mind.md): qwen3 via Ollama returns
`message.reasoning`; vLLM/DeepSeek call it `message.reasoning_content`; some
chat templates embed a leading `<think>…</think>` block in content instead.
All three are normalized to a top-level `reasoning` key here — and REMOVED
from the message, because thinking is a per-turn scratchpad, not
conversation: re-sending it wastes window, persisting it bloats sessions.
"""

import re

import requests

THINK_TAG = re.compile(r"^\s*<think>(.*?)</think>\s*", re.DOTALL)


def normalize_reply(data: dict) -> dict:
    """Raw /v1/chat/completions JSON -> the normalized shape the loop speaks."""
    choice = data["choices"][0]
    msg = dict(choice["message"])  # copy: never hand raw provider JSON onward
    reasoning = msg.pop("reasoning", None)
    reasoning = msg.pop("reasoning_content", None) or reasoning
    content = msg.get("content")
    if content and not reasoning:
        m = THINK_TAG.match(content)
        if m:
            reasoning = m.group(1).strip()
            msg["content"] = content[m.end():]
    return {
        "message": msg,
        "finish_reason": choice["finish_reason"],
        "usage": data.get("usage"),
        "reasoning": reasoning or None,
    }


class OpenAICompatModel:
    def __init__(self, url: str, key: str, model: str, timeout: int = 600,
                 max_tokens: int = 2000):
        self.url = url
        self.key = key  # Ollama ignores auth, but the header must exist
        self.model = model
        # Generous timeout: a 4B model thinking hard on a 4 GB laptop GPU can
        # legitimately take minutes per call (measured in Stage 1: 300s wasn't enough).
        self.timeout = timeout
        # Per-provider, not hardcoded: thinking models spend their budget on
        # reasoning BEFORE the tool call — 2000 was measured as thinking-death
        # on qwen3 (acceptance-local.log, tasks A and G).
        self.max_tokens = max_tokens

    def complete(self, messages: list, tools: list) -> dict:
        # One retry on 5xx: cloud endpoints throw transient 503s under load
        # (measured live on Gemini flash-lite). A 4xx is OUR bug and must not
        # be retried — same request, same rejection.
        for attempt in (1, 2):
            resp = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {self.key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    # No temperature override: qwen3 + temperature 0 (greedy
                    # decoding) spirals into infinite repetition while
                    # "thinking" — measured as a 600s timeout in Stage 1.
                    # Models ship tuned defaults; trust them. max_tokens is
                    # the runaway-GENERATION guard (max_steps guards the
                    # loop) — overruns end as finish_reason "length".
                    "max_tokens": self.max_tokens,
                },
                timeout=self.timeout,
            )
            if resp.status_code >= 500 and attempt == 1:
                print(f"  [!] {resp.status_code} from provider - retrying once...")
                continue
            resp.raise_for_status()
            return normalize_reply(resp.json())
