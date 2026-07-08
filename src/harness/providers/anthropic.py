"""Native Anthropic adapter — the 'claude2 insurance' officially lives here.

Anthropic's /v1/messages is NOT OpenAI-compatible; six differences are
catalogued in docs/notes/03-provider-adapter.md. All translation is done in
module-level pure functions so tests never need HTTP. The loop stays
monolingual: it sends OpenAI-style history, gets a normalized reply back.

Native (rather than a compat shim) matters later: prompt caching
(cache_control breakpoints, Stage 2.9/3) only exists on this wire format.
"""

import json

import requests

from harness.providers.base import request_with_retries

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

STOP_REASON_MAP = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "tool_use": "tool_calls",
    "max_tokens": "length",
}

# /think levels -> extended-thinking budget_tokens (docs/notes/18). The API
# requires max_tokens > budget, so complete() raises max_tokens to match.
# CAVEAT on record: thinking + tool use needs the thinking block replayed
# within the turn (Anthropic returns signed blocks) — our strip-always policy
# (2.9a) conflicts; resolve during the live smoke test (docs/problem.md).
THINK_BUDGETS = {"low": 1024, "on": 4096, "medium": 4096, "high": 16384}


def to_anthropic_tools(schemas: list) -> list:
    """OpenAI {type:function, function:{name,description,parameters}}
    -> Anthropic {name, description, input_schema}."""
    return [
        {
            "name": s["function"]["name"],
            "description": s["function"]["description"],
            "input_schema": s["function"]["parameters"],
        }
        for s in schemas
    ]


def to_anthropic_messages(messages: list) -> tuple[str, list]:
    """OpenAI-style history -> (system_string, anthropic_messages).

    Three rewrites:
      - role:"system"  -> top-level system param (Anthropic has no system role)
      - assistant with tool_calls -> content blocks (text? + tool_use*),
        arguments json.loads'd back to objects
      - role:"tool" -> user message with tool_result blocks; CONSECUTIVE tool
        results merge into ONE user turn (Anthropic requires alternating roles)
    """
    system = ""
    out: list = []
    for m in messages:
        role = m["role"]
        if role == "system":
            system = m["content"]
        elif role == "assistant" and m.get("tool_calls"):
            blocks: list = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for call in m["tool_calls"]:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["function"]["name"],
                        "input": json.loads(call["function"]["arguments"]),
                    }
                )
            out.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": m["tool_call_id"],
                "content": m["content"],
            }
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)  # merge consecutive results
            else:
                out.append({"role": "user", "content": [block]})
        else:  # plain user or plain assistant text
            out.append({"role": role, "content": m["content"]})
    return system, out


def from_anthropic_reply(data: dict) -> dict:
    """Anthropic response -> the normalized shape the loop speaks."""
    texts = [b["text"] for b in data["content"] if b["type"] == "text"]
    thinking = [b.get("thinking", "") for b in data["content"] if b["type"] == "thinking"]
    tool_calls = [
        {
            "id": b["id"],
            "type": "function",
            "function": {
                "name": b["name"],
                # Back to the OpenAI convention: arguments as a JSON *string*.
                "arguments": json.dumps(b["input"]),
            },
        }
        for b in data["content"]
        if b["type"] == "tool_use"
    ]
    message: dict = {"role": "assistant", "content": "\n".join(texts) or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    usage = data.get("usage") or {}
    return {
        "message": message,
        "finish_reason": STOP_REASON_MAP.get(data.get("stop_reason"), "stop"),
        "usage": {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        },
        "reasoning": "\n".join(t for t in thinking if t) or None,
    }


class AnthropicModel:
    def __init__(self, key: str, model: str, url: str = API_URL, timeout: int = 600,
                 max_tokens: int = 2000):
        self.key = key
        self.model = model
        self.url = url
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.think = None  # off|on|low|medium|high (docs/notes/18), None = never send

    def body(self, messages: list, tools: list) -> dict:
        """The full request payload, as a pure function of adapter state —
        split from complete() so the translation is testable without HTTP."""
        system, anthropic_messages = to_anthropic_messages(messages)
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,  # REQUIRED here (optional in OpenAI-compat)
            "messages": anthropic_messages,
            "tools": to_anthropic_tools(tools),
        }
        if system:
            payload["system"] = system
        if self.think and self.think != "off":
            budget = THINK_BUDGETS.get(self.think, 4096)
            payload["thinking"] = {"type": "enabled", "budget_tokens": budget}
            # The API rejects budget >= max_tokens; give the answer headroom.
            payload["max_tokens"] = max(self.max_tokens, budget + 1000)
        return payload

    def complete(self, messages: list, tools: list) -> dict:
        payload = self.body(messages, tools)
        # Shared retry policy (2.26, note 35) - cloud endpoint, full attempts.
        resp = request_with_retries(lambda: requests.post(
            self.url,
            headers={
                "x-api-key": self.key,  # NOT Authorization: Bearer
                "anthropic-version": API_VERSION,
            },
            json=payload,
            timeout=self.timeout,
        ))
        return from_anthropic_reply(resp.json())
