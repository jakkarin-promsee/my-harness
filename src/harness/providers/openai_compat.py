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

import json
import re

import requests

from harness.providers.base import request_with_retries

THINK_TAG = re.compile(r"^\s*<think>(.*?)</think>\s*", re.DOTALL)


def parse_sse(lines) -> list[dict]:
    """SSE body -> parsed chunk dicts (docs/notes/12-streaming.md).

    Wire format: every event is a line 'data: {json}'; blank lines are
    keep-alive separators; 'data: [DONE]' terminates the stream."""
    chunks = []
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload.strip() == "[DONE]":
            break
        chunks.append(json.loads(payload))
    return chunks


def assemble_chunks(chunks: list) -> dict:
    """Streamed fragments -> ONE body shaped like a non-streaming response,
    so normalize_reply() stays the single normalization path.

    Deltas for humans, complete objects for the loop: content/reasoning
    concatenate; tool calls merge by `index` (id and name arrive once,
    `arguments` accumulates piece by piece and is only valid JSON at the
    end — which is exactly why a tool call must never execute mid-stream)."""
    content: list[str] = []
    reasoning: list[str] = []
    calls: dict[int, dict] = {}
    finish, usage = None, None
    for chunk in chunks:
        if chunk.get("usage"):
            usage = chunk["usage"]  # the stream_options include_usage chunk
        for choice in chunk.get("choices", []):
            if choice.get("finish_reason"):
                finish = choice["finish_reason"]
            delta = choice.get("delta") or {}
            if delta.get("content"):
                content.append(delta["content"])
            frag = delta.get("reasoning") or delta.get("reasoning_content")
            if frag:
                reasoning.append(frag)
            for tc in delta.get("tool_calls") or []:
                # OpenAI/Ollama tag every fragment with `index`; Gemini's
                # OpenAI-compat stream omits it entirely (KeyError crash on
                # the first tool call). Synthesize one: a call BEGINS when a
                # fragment carries an id or a function name; an arguments-only
                # fragment continues the call already in progress.
                idx = tc.get("index")
                if idx is None:
                    fn = tc.get("function") or {}
                    if tc.get("id") or fn.get("name") or not calls:
                        idx = len(calls)          # a new tool call
                    else:
                        idx = max(calls)          # more args for the latest
                slot = calls.setdefault(idx, {
                    "id": None, "type": "function",
                    "function": {"name": "", "arguments": ""},
                })
                if tc.get("id"):
                    slot["id"] = tc["id"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    slot["function"]["name"] = fn["name"]
                if fn.get("arguments"):
                    slot["function"]["arguments"] += fn["arguments"]
    message: dict = {"role": "assistant", "content": "".join(content) or None}
    if reasoning:
        message["reasoning"] = "".join(reasoning)  # normalize_reply pops it
    if calls:
        message["tool_calls"] = [calls[i] for i in sorted(calls)]
    return {
        "choices": [{"message": message, "finish_reason": finish or "stop"}],
        "usage": usage,
    }


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
                 max_tokens: int = 2000, on_delta=None):
        self.url = url
        self.key = key  # Ollama ignores auth, but the header must exist
        self.model = model
        # Generous timeout: a 4B model thinking hard on a 4 GB laptop GPU can
        # legitimately take minutes per call (measured in Stage 1: 300s wasn't enough).
        # (With streaming, requests applies it between chunks — even better.)
        self.timeout = timeout
        # Per-provider, not hardcoded: thinking models spend their budget on
        # reasoning BEFORE the tool call — 2000 was measured as thinking-death
        # on qwen3 (acceptance-local.log, tasks A and G).
        self.max_tokens = max_tokens
        # on_delta(kind, text) makes this a STREAMING client: "reasoning" and
        # "content" fragments as they arrive, one "end" when the stream closes.
        # None = the classic one-shot request; behavior is identical.
        self.on_delta = on_delta
        # /think knob (docs/notes/18 + 25): off|on|low|medium|high, or None =
        # never send anything. Maps to reasoning_effort on this wire. Since
        # 2.19, "off" sends "none" — the off-switch for thinking-DEFAULT
        # models (gemini flash); probe (a) in note 22 confirmed the wire
        # honors it. None stays "send nothing": flash-lite shouldn't pay
        # for a param it doesn't need.
        self.think = None

    def body(self, messages: list, tools: list) -> dict:
        """The request payload as a pure function of adapter state — split
        from complete() so translation (think mapping) tests skip HTTP."""
        body = {
            "model": self.model,
            # meta is OUR protocol (2.23 anchors) - strict endpoints 400 on
            # unknown fields, so it never crosses the wire.
            "messages": [{k: v for k, v in m.items() if k != "meta"} for m in messages],
            "tools": tools,
            # No temperature override: qwen3 + temperature 0 (greedy
            # decoding) spirals into infinite repetition while
            # "thinking" — measured as a 600s timeout in Stage 1.
            # Models ship tuned defaults; trust them. max_tokens is
            # the runaway-GENERATION guard (max_steps guards the
            # loop) — overruns end as finish_reason "length".
            "max_tokens": self.max_tokens,
        }
        if self.think:
            body["reasoning_effort"] = {"on": "medium", "off": "none"}.get(
                self.think, self.think)
        if self.on_delta:
            body["stream"] = True
            # Without this the stream carries no token counts at all.
            body["stream_options"] = {"include_usage": True}
        return body

    def complete(self, messages: list, tools: list) -> dict:
        body = self.body(messages, tools)
        # The shared retry policy (2.26, note 35): backoff+jitter on 429/5xx/
        # connection errors, Retry-After honored. Cloud endpoint -> the full
        # 5 attempts (flash-lite's 503 bursts are measured reality).
        resp = request_with_retries(lambda: requests.post(
            self.url,
            headers={"Authorization": f"Bearer {self.key}"},
            json=body,
            timeout=self.timeout,
            stream=bool(self.on_delta),
        ))
        if not self.on_delta:
            return normalize_reply(resp.json())
        return self._stream(resp)

    def _stream(self, resp) -> dict:
        """Read the SSE wire: fragments to on_delta as they arrive, the
        assembled whole to the loop at the end. `streamed: True` tells the
        loop not to re-print what the human already watched."""
        chunks: list[dict] = []
        emitted = False
        for line in resp.iter_lines():  # skips keep-alive blanks itself
            for chunk in parse_sse([line]):
                chunks.append(chunk)
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta") or {}
                    frag = delta.get("reasoning") or delta.get("reasoning_content")
                    if frag:
                        self.on_delta("reasoning", frag)
                        emitted = True
                    if delta.get("content"):
                        self.on_delta("content", delta["content"])
                        emitted = True
        if emitted:
            self.on_delta("end", "")
        reply = normalize_reply(assemble_chunks(chunks))
        reply["streamed"] = True
        return reply
