"""The native /api/chat dialect (2.12), offline: both translation directions,
think mapping, NDJSON stream assembly. Wire shapes verified by live probe
2026-07-07 (docs/notes/18-reasoning-control.md)."""

import json

from harness.providers.ollama_native import (
    OllamaNativeModel,
    normalize_native,
    translate_out,
)

HISTORY = [
    {"role": "system", "content": "sys"},
    {"role": "user", "content": "weather?"},
    {"role": "assistant", "content": None, "tool_calls": [
        {"id": "abc", "type": "function",
         "function": {"name": "get_weather", "arguments": '{"city": "Paris"}'}},
    ]},
    {"role": "tool", "tool_call_id": "abc", "content": '{"temp": 21}'},
]


# ---- outgoing -------------------------------------------------------------

def test_outgoing_arguments_string_becomes_object():
    native = translate_out(HISTORY)
    call = native[2]["tool_calls"][0]
    assert call["function"]["arguments"] == {"city": "Paris"}  # object, not str


def test_outgoing_tool_result_gains_tool_name():
    native = translate_out(HISTORY)
    assert native[3]["tool_name"] == "get_weather"   # recovered via call id
    assert "tool_call_id" not in native[3]           # not a native field


def test_outgoing_plain_messages_pass_through_untouched():
    native = translate_out(HISTORY)
    assert native[0] == {"role": "system", "content": "sys"}
    assert native[1] == {"role": "user", "content": "weather?"}
    assert HISTORY[3].get("tool_call_id") == "abc"   # source list never mutated


def test_outgoing_bad_argument_json_fails_soft():
    msgs = [{"role": "assistant", "tool_calls": [
        {"id": "x", "function": {"name": "t", "arguments": "not json"}}]}]
    assert translate_out(msgs)[0]["tool_calls"][0]["function"]["arguments"] == {}


# ---- think mapping ---------------------------------------------------------

def test_think_mapping_in_body():
    m = OllamaNativeModel("http://x/api/chat", "m")
    assert "think" not in m.body([], [])             # None -> never sent
    m.think = "off"
    assert m.body([], [])["think"] is False
    m.think = "on"
    assert m.body([], [])["think"] is True
    m.think = "high"
    assert m.body([], [])["think"] == "high"         # gpt-oss-class level


def test_body_carries_num_predict():
    m = OllamaNativeModel("http://x/api/chat", "m", max_tokens=1234)
    assert m.body([], [])["options"]["num_predict"] == 1234


# ---- incoming ---------------------------------------------------------------

def test_incoming_thinking_becomes_reasoning_and_leaves_message():
    reply = normalize_native({
        "message": {"role": "assistant", "content": "42", "thinking": "let me see"},
        "done_reason": "stop", "prompt_eval_count": 10, "eval_count": 5,
    })
    assert reply["reasoning"] == "let me see"
    assert "thinking" not in reply["message"]
    assert reply["message"]["content"] == "42"


def test_incoming_arguments_object_becomes_string():
    reply = normalize_native({
        "message": {"role": "assistant", "content": "", "tool_calls": [
            {"id": "abc", "function": {"index": 0, "name": "get_weather",
                                       "arguments": {"city": "Paris"}}}]},
        "done_reason": "stop",
    })
    call = reply["message"]["tool_calls"][0]
    assert call["type"] == "function"
    assert json.loads(call["function"]["arguments"]) == {"city": "Paris"}
    assert call["id"] == "abc"


def test_incoming_missing_call_id_is_synthesized():
    reply = normalize_native({
        "message": {"role": "assistant", "tool_calls": [
            {"function": {"name": "t", "arguments": {}}}]},
        "done_reason": "stop",
    })
    assert reply["message"]["tool_calls"][0]["id"]  # loop echoes ids back


def test_incoming_counts_become_usage_and_done_reason_maps():
    reply = normalize_native({
        "message": {"role": "assistant", "content": "x"},
        "done_reason": "length", "prompt_eval_count": 100, "eval_count": 50,
    })
    assert reply["finish_reason"] == "length"
    assert reply["usage"] == {"prompt_tokens": 100, "completion_tokens": 50,
                              "total_tokens": 150}


# ---- streaming ---------------------------------------------------------------

class FakeResp:
    def __init__(self, chunks):
        self._lines = [json.dumps(c).encode() for c in chunks]

    def iter_lines(self):
        return iter(self._lines)


def test_stream_assembles_and_emits_in_order():
    events = []
    m = OllamaNativeModel("http://x/api/chat", "m",
                          on_delta=lambda kind, text: events.append((kind, text)))
    reply = m._stream(FakeResp([
        {"message": {"role": "assistant", "content": "", "thinking": "hmm "}, "done": False},
        {"message": {"role": "assistant", "content": "", "thinking": "ok"}, "done": False},
        {"message": {"role": "assistant", "content": "an"}, "done": False},
        {"message": {"role": "assistant", "content": "swer"}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True,
         "done_reason": "stop", "prompt_eval_count": 7, "eval_count": 3},
    ]))
    assert events == [("reasoning", "hmm "), ("reasoning", "ok"),
                      ("content", "an"), ("content", "swer"), ("end", "")]
    assert reply["message"]["content"] == "answer"
    assert reply["reasoning"] == "hmm ok"
    assert reply["finish_reason"] == "stop"
    assert reply["usage"]["completion_tokens"] == 3
    assert reply["streamed"] is True


def test_stream_tool_calls_arrive_whole():
    m = OllamaNativeModel("http://x/api/chat", "m", on_delta=lambda k, t: None)
    reply = m._stream(FakeResp([
        {"message": {"role": "assistant", "content": "", "tool_calls": [
            {"id": "a", "function": {"name": "grep", "arguments": {"pattern": "x"}}}]},
         "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True,
         "done_reason": "stop"},
    ]))
    call = reply["message"]["tool_calls"][0]
    assert call["function"]["name"] == "grep"
    assert json.loads(call["function"]["arguments"]) == {"pattern": "x"}
