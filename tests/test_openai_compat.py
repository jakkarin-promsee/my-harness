"""normalize_reply: three thinking dialects in, one normalized shape out.

Pure-function tests in the style of test_anthropic.py — no HTTP, no mocks,
just raw provider JSON shapes as Python dicts (docs/notes/11-visible-mind.md).
"""

from harness.providers.openai_compat import normalize_reply


def raw(message, finish="stop", usage=None):
    return {"choices": [{"message": message, "finish_reason": finish}], "usage": usage}


def test_plain_reply_passes_through_with_no_reasoning():
    reply = normalize_reply(raw({"role": "assistant", "content": "hi"},
                                usage={"prompt_tokens": 5, "completion_tokens": 1}))
    assert reply["message"] == {"role": "assistant", "content": "hi"}
    assert reply["finish_reason"] == "stop"
    assert reply["usage"] == {"prompt_tokens": 5, "completion_tokens": 1}
    assert reply["reasoning"] is None


def test_reasoning_field_is_popped_out_of_the_message():
    # qwen3 via Ollama's /v1 endpoint (observed live in labs/01)
    reply = normalize_reply(raw({"role": "assistant", "content": "4",
                                 "reasoning": "2+2 is 4"}))
    assert reply["reasoning"] == "2+2 is 4"
    assert "reasoning" not in reply["message"]      # never re-sent, never persisted
    assert reply["message"]["content"] == "4"


def test_reasoning_content_dialect_is_also_popped():
    # vLLM / DeepSeek name the same thing reasoning_content
    reply = normalize_reply(raw({"role": "assistant", "content": "4",
                                 "reasoning_content": "thinking..."}))
    assert reply["reasoning"] == "thinking..."
    assert "reasoning_content" not in reply["message"]


def test_leading_think_tag_is_extracted_from_content():
    # some chat templates inline the scratchpad instead of using a field
    reply = normalize_reply(raw({"role": "assistant",
                                 "content": "<think>\nhmm ok\n</think>\nThe answer is 4."}))
    assert reply["reasoning"] == "hmm ok"
    assert reply["message"]["content"] == "The answer is 4."


def test_reasoning_field_wins_over_think_tags_in_content():
    # if a field exists, content is left alone — no double parsing
    reply = normalize_reply(raw({"role": "assistant",
                                 "content": "<think>not me</think> hi",
                                 "reasoning": "field"}))
    assert reply["reasoning"] == "field"
    assert "<think>" in reply["message"]["content"]


def test_tool_calls_survive_normalization_untouched():
    calls = [{"id": "i1", "type": "function",
              "function": {"name": "grep", "arguments": '{"pattern": "x"}'}}]
    reply = normalize_reply(raw({"role": "assistant", "content": None,
                                 "tool_calls": calls, "reasoning": "which tool?"},
                                finish="tool_calls"))
    assert reply["message"]["tool_calls"] == calls
    assert reply["reasoning"] == "which tool?"
    assert reply["finish_reason"] == "tool_calls"
