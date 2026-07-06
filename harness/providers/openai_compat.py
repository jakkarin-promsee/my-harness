"""OpenAI-compatible provider client: one HTTP POST + dialect normalization.

Covers Ollama, Gemini, OpenRouter, vLLM — everything that speaks
/v1/chat/completions. The adapter's job is to hide the wire format from the
loop: `complete()` returns a small normalized dict, so the loop (and the
tests' FakeModel) never see raw provider JSON. Stage 2.1 will add a native
Anthropic sibling behind this same interface.
"""

import requests


class OpenAICompatModel:
    def __init__(self, url: str, key: str, model: str, timeout: int = 600):
        self.url = url
        self.key = key  # Ollama ignores auth, but the header must exist
        self.model = model
        # Generous timeout: a 4B model thinking hard on a 4 GB laptop GPU can
        # legitimately take minutes per call (measured in Stage 1: 300s wasn't enough).
        self.timeout = timeout

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
                    "max_tokens": 2000,
                },
                timeout=self.timeout,
            )
            if resp.status_code >= 500 and attempt == 1:
                print(f"  [!] {resp.status_code} from provider - retrying once...")
                continue
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            # The normalized shape the rest of the harness speaks:
            return {
                "message": choice["message"],
                "finish_reason": choice["finish_reason"],
                "usage": data.get("usage"),
            }
