"""The Anthropic adapter, tested offline — translation is pure functions.

No ANTHROPIC_API_KEY exists on this machine (by constitutional order until
the owner sets one deliberately), so complete() is exercised against a
monkeypatched requests.post. Live validation is tracked in docs/problem.md.
"""

import json

from harness.providers import anthropic


def test_tools_translate_to_input_schema():
    openai_schema = [{
        "type": "function",
        "function": {"name": "t", "description": "d", "parameters": {"type": "object", "properties": {}}},
    }]
    assert anthropic.to_anthropic_tools(openai_schema) == [
        {"name": "t", "description": "d", "input_schema": {"type": "object", "properties": {}}}
    ]


def test_system_message_becomes_top_level_param():
    system, msgs = anthropic.to_anthropic_messages(
        [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}]
    )
    assert system == "be brief"
    assert msgs == [{"role": "user", "content": "hi"}]


def test_assistant_tool_calls_become_tool_use_blocks():
    _, msgs = anthropic.to_anthropic_messages([
        {"role": "user", "content": "go"},
        {
            "role": "assistant",
            "content": "on it",
            "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "t", "arguments": '{"x": 1}'}}
            ],
        },
    ])
    blocks = msgs[1]["content"]
    assert blocks[0] == {"type": "text", "text": "on it"}
    # arguments string -> input OBJECT
    assert blocks[1] == {"type": "tool_use", "id": "c1", "name": "t", "input": {"x": 1}}


def test_consecutive_tool_results_merge_into_one_user_turn():
    _, msgs = anthropic.to_anthropic_messages([
        {"role": "user", "content": "go"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "a", "type": "function", "function": {"name": "t", "arguments": "{}"}},
                {"id": "b", "type": "function", "function": {"name": "t", "arguments": "{}"}},
            ],
        },
        {"role": "tool", "tool_call_id": "a", "content": "r1"},
        {"role": "tool", "tool_call_id": "b", "content": "r2"},
    ])
    # roles must alternate: both results live in ONE user message
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    result_blocks = msgs[2]["content"]
    assert [b["tool_use_id"] for b in result_blocks] == ["a", "b"]


def test_reply_normalizes_blocks_stop_reason_and_usage():
    reply = anthropic.from_anthropic_reply({
        "content": [
            {"type": "text", "text": "let me check"},
            {"type": "tool_use", "id": "c9", "name": "t", "input": {"x": 2}},
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 11, "output_tokens": 5},
    })
    assert reply["finish_reason"] == "tool_calls"
    assert reply["usage"] == {"prompt_tokens": 11, "completion_tokens": 5}
    call = reply["message"]["tool_calls"][0]
    assert call["id"] == "c9"
    assert json.loads(call["function"]["arguments"]) == {"x": 2}  # object -> string


def test_stop_reason_map_covers_the_length_case():
    reply = anthropic.from_anthropic_reply(
        {"content": [{"type": "text", "text": "..."}], "stop_reason": "max_tokens", "usage": {}}
    )
    assert reply["finish_reason"] == "length"


def test_complete_roundtrip_with_mocked_http(monkeypatch):
    captured = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "content": [{"type": "text", "text": "hello"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 3, "output_tokens": 2},
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, payload=json)
        return FakeResp()

    monkeypatch.setattr(anthropic.requests, "post", fake_post)
    model = anthropic.AnthropicModel(key="k", model="claude-test")
    reply = model.complete(
        [{"role": "system", "content": "s"}, {"role": "user", "content": "hi"}], []
    )
    assert reply["message"]["content"] == "hello"
    assert captured["headers"]["x-api-key"] == "k"          # not Authorization
    assert captured["headers"]["anthropic-version"]          # version header present
    assert captured["payload"]["system"] == "s"              # system lifted out
    assert captured["payload"]["max_tokens"] == 2000         # required field


# ---- 2.12: think -> extended-thinking budgets (docs/notes/18) ---------------

def test_think_maps_to_budget_and_raises_max_tokens():
    m = anthropic.AnthropicModel("k", "model", max_tokens=2000)
    assert "thinking" not in m.body([], [])           # None -> never sent
    m.think = "off"
    assert "thinking" not in m.body([], [])
    m.think = "low"
    body = m.body([], [])
    assert body["thinking"] == {"type": "enabled", "budget_tokens": 1024}
    assert body["max_tokens"] == 2024                  # budget+1000 > original 2000
    m.think = "high"
    body = m.body([], [])
    assert body["thinking"]["budget_tokens"] == 16384
    assert body["max_tokens"] == 17384                 # raised past the budget


def test_thinking_blocks_normalize_to_reasoning():
    reply = anthropic.from_anthropic_reply({
        "content": [
            {"type": "thinking", "thinking": "let me reason", "signature": "sig"},
            {"type": "text", "text": "answer"},
        ],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    })
    assert reply["reasoning"] == "let me reason"
    assert reply["message"]["content"] == "answer"
