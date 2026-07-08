"""Ollama NATIVE /api/chat adapter — because /v1 ignores `think`.

Probed 2026-07-07 (docs/notes/18-reasoning-control.md): Ollama's OpenAI-compat
endpoint silently drops the `think` parameter, so honest reasoning control
means speaking the native dialect. And it IS a dialect — translated BOTH
directions at this boundary (the providers/base.py invariant):

    outgoing   tool_calls arguments: JSON string -> object
               tool results: tool_call_id -> tool_name (recovered from the
               preceding assistant message's call ids)
    incoming   message.thinking -> the normalized `reasoning` key
               arguments object -> JSON string; done_reason -> finish_reason
               prompt_eval_count/eval_count -> usage
    streaming  NDJSON lines (not SSE), same on_delta protocol as 2.9b

think mapping: off -> false, on -> true, low/medium/high -> level string
(booleans for qwen3/deepseek-class models, levels for gpt-oss-class).
"""

import json

import requests

THINK_MAP = {"off": False, "on": True}  # low/medium/high pass through as strings


def translate_out(messages: list) -> list:
    """OpenAI-shape history -> native shape. History is replayed every call,
    so this runs on every message, every time."""
    id_to_name = {}  # tool_call_id -> tool name, for the results that follow
    out = []
    for m in messages:
        m = dict(m)
        m.pop("meta", None)  # our protocol tag (2.23 anchors), not the wire's
        for call in m.get("tool_calls") or []:
            id_to_name[call.get("id")] = call["function"]["name"]
        if m.get("role") == "assistant" and m.get("tool_calls"):
            m["tool_calls"] = [_call_out(c) for c in m["tool_calls"]]
        elif m.get("role") == "tool":
            name = id_to_name.get(m.pop("tool_call_id", None))
            if name:
                m["tool_name"] = name
        out.append(m)
    return out


def _call_out(call: dict) -> dict:
    args = call["function"]["arguments"]
    if isinstance(args, str):  # the OpenAI wire's JSON string -> native object
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}
    return {"id": call.get("id", ""),
            "function": {"name": call["function"]["name"], "arguments": args}}


def normalize_native(data: dict) -> dict:
    """Native /api/chat JSON -> the normalized shape the loop speaks."""
    msg = dict(data.get("message") or {})
    reasoning = msg.pop("thinking", None)
    calls = []
    for i, call in enumerate(msg.get("tool_calls") or []):
        fn = call.get("function") or {}
        args = fn.get("arguments", {})
        calls.append({
            # The loop echoes ids back as tool_call_id; synthesize when absent.
            "id": call.get("id") or f"call_{i}",
            "type": "function",
            "function": {"name": fn.get("name", ""),
                         "arguments": args if isinstance(args, str) else json.dumps(args)},
        })
    if calls:
        msg["tool_calls"] = calls
    usage = None
    if "eval_count" in data or "prompt_eval_count" in data:
        p = data.get("prompt_eval_count", 0)
        c = data.get("eval_count", 0)
        usage = {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}
    return {
        "message": msg,
        "finish_reason": data.get("done_reason") or "stop",
        "usage": usage,
        "reasoning": reasoning or None,
    }


class OllamaNativeModel:
    def __init__(self, url: str, model: str, timeout: int = 600,
                 max_tokens: int = 4096, on_delta=None):
        self.url = url                # http://localhost:11434/api/chat
        self.model = model
        self.timeout = timeout        # same rationale as the compat adapter
        self.max_tokens = max_tokens  # native name: options.num_predict
        self.on_delta = on_delta
        self.think = None             # off|on|low|medium|high, set by /think or an agent

    def body(self, messages: list, tools: list) -> dict:
        """The request payload as a pure function of adapter state — split
        from complete() so translation tests skip HTTP."""
        body = {
            "model": self.model,
            "messages": translate_out(messages),
            "tools": tools,           # schemas are identical on both wires
            "stream": bool(self.on_delta),
            # No temperature override, same reason as the compat adapter.
            "options": {"num_predict": self.max_tokens},
        }
        if self.think is not None:
            body["think"] = THINK_MAP.get(self.think, self.think)
        return body

    def complete(self, messages: list, tools: list) -> dict:
        body = self.body(messages, tools)
        for attempt in (1, 2):  # one retry on 5xx, 4xx is our bug (see compat)
            resp = requests.post(self.url, json=body, timeout=self.timeout,
                                 stream=bool(self.on_delta))
            if resp.status_code >= 500 and attempt == 1:
                print(f"  [!] {resp.status_code} from provider - retrying once...")
                continue
            resp.raise_for_status()
            if not self.on_delta:
                return normalize_native(resp.json())
            return self._stream(resp)

    def _stream(self, resp) -> dict:
        """NDJSON: one JSON object per line; fragments live in
        message.thinking / message.content; the done:true line carries
        done_reason and the token counts."""
        thinking: list[str] = []
        content: list[str] = []
        calls: list[dict] = []
        final: dict = {}
        emitted = False
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            msg = chunk.get("message") or {}
            if msg.get("thinking"):
                thinking.append(msg["thinking"])
                self.on_delta("reasoning", msg["thinking"])
                emitted = True
            if msg.get("content"):
                content.append(msg["content"])
                self.on_delta("content", msg["content"])
                emitted = True
            # Native streams deliver each tool call whole in one chunk —
            # no index-merging needed (unlike SSE, note 12).
            calls.extend(msg.get("tool_calls") or [])
            if chunk.get("done"):
                final = chunk
        if emitted:
            self.on_delta("end", "")
        message: dict = {"role": "assistant", "content": "".join(content) or None}
        if thinking:
            message["thinking"] = "".join(thinking)
        if calls:
            message["tool_calls"] = calls
        reply = normalize_native({**final, "message": message})
        reply["streamed"] = True
        return reply
