"""Streaming, tested offline: SSE parsing and delta assembly are pure
functions; the streamed complete() runs against a mocked requests.post whose
body is a canned SSE wire (docs/notes/12-streaming.md).

The contract under test: deltas for humans (on_delta events, in order),
complete objects for the loop (the assembled reply is indistinguishable from
its non-streaming twin, plus `streamed: True`).
"""

import json

from harness.providers import openai_compat
from harness.providers.openai_compat import (
    OpenAICompatModel,
    assemble_chunks,
    parse_sse,
)


def sse(obj) -> bytes:
    return b"data: " + json.dumps(obj).encode()


def delta_chunk(delta, finish=None):
    return {"choices": [{"delta": delta, "finish_reason": finish}]}


def test_parse_sse_strips_prefix_skips_noise_and_stops_at_done():
    lines = [
        b"",                                    # keep-alive blank
        sse(delta_chunk({"content": "hi"})),
        b": comment line",                      # SSE comment, not data
        b"data: [DONE]",
        sse(delta_chunk({"content": "NEVER"})),  # after DONE -> ignored
    ]
    chunks = parse_sse(lines)
    assert len(chunks) == 1
    assert chunks[0]["choices"][0]["delta"]["content"] == "hi"


def test_content_fragments_concatenate():
    body = assemble_chunks([
        delta_chunk({"role": "assistant", "content": "Hel"}),
        delta_chunk({"content": "lo"}),
        delta_chunk({}, finish="stop"),
    ])
    msg = body["choices"][0]["message"]
    assert msg["content"] == "Hello"
    assert body["choices"][0]["finish_reason"] == "stop"


def test_reasoning_fragments_land_in_the_message_for_normalize_reply():
    body = assemble_chunks([
        delta_chunk({"reasoning": "let me "}),
        delta_chunk({"reasoning_content": "think"}),   # dialect mix, same bucket
        delta_chunk({"content": "4"}, finish="stop"),
    ])
    msg = body["choices"][0]["message"]
    assert msg["reasoning"] == "let me think"          # popped later by normalize_reply
    assert msg["content"] == "4"


def test_tool_call_arguments_accumulate_by_index():
    body = assemble_chunks([
        delta_chunk({"tool_calls": [
            {"index": 0, "id": "a", "function": {"name": "grep", "arguments": '{"pat'}},
        ]}),
        delta_chunk({"tool_calls": [
            {"index": 0, "function": {"arguments": 'tern": "x"}'}},
            {"index": 1, "id": "b", "function": {"name": "glob", "arguments": "{}"}},
        ]}, finish="tool_calls"),
    ])
    calls = body["choices"][0]["message"]["tool_calls"]
    assert [c["id"] for c in calls] == ["a", "b"]      # index order preserved
    assert json.loads(calls[0]["function"]["arguments"]) == {"pattern": "x"}
    assert calls[1]["function"]["name"] == "glob"


def test_usage_is_adopted_from_the_trailing_chunk():
    body = assemble_chunks([
        delta_chunk({"content": "ok"}, finish="stop"),
        {"choices": [], "usage": {"prompt_tokens": 9, "completion_tokens": 2}},
    ])
    assert body["usage"] == {"prompt_tokens": 9, "completion_tokens": 2}


def test_streamed_complete_emits_deltas_in_order_and_normalizes(monkeypatch):
    wire = [
        sse(delta_chunk({"role": "assistant", "reasoning": "hmm "})),
        sse(delta_chunk({"reasoning": "ok"})),
        sse(delta_chunk({"content": "an"})),
        sse(delta_chunk({"content": "swer"}, finish="stop")),
        sse({"choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 4}}),
        b"data: [DONE]",
    ]
    captured = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def iter_lines(self):
            return iter(wire)

    def fake_post(url, headers=None, json=None, timeout=None, stream=False):
        captured.update(payload=json, stream=stream)
        return FakeResp()

    monkeypatch.setattr(openai_compat.requests, "post", fake_post)
    events = []
    model = OpenAICompatModel("http://x", "k", "m",
                              on_delta=lambda kind, text: events.append((kind, text)))
    reply = model.complete([{"role": "user", "content": "q"}], [])

    assert captured["payload"]["stream"] is True
    assert captured["payload"]["stream_options"] == {"include_usage": True}
    assert captured["stream"] is True                   # requests must not buffer
    assert events == [("reasoning", "hmm "), ("reasoning", "ok"),
                      ("content", "an"), ("content", "swer"), ("end", "")]
    # the loop sees the same normalized shape as non-streaming...
    assert reply["message"] == {"role": "assistant", "content": "answer"}
    assert reply["reasoning"] == "hmm ok"               # stripped from the message
    assert reply["usage"]["completion_tokens"] == 4
    # ...plus the marker that says "already shown, don't re-print"
    assert reply["streamed"] is True


def test_no_on_delta_means_no_stream_flag(monkeypatch):
    captured = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"role": "assistant", "content": "hi"},
                                 "finish_reason": "stop"}]}

    def fake_post(url, headers=None, json=None, timeout=None, stream=False):
        captured.update(payload=json, stream=stream)
        return FakeResp()

    monkeypatch.setattr(openai_compat.requests, "post", fake_post)
    reply = OpenAICompatModel("http://x", "k", "m").complete([], [])
    assert "stream" not in captured["payload"]          # classic one-shot request
    assert captured["stream"] is False
    assert "streamed" not in reply
