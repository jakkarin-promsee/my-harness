"""Turn reflection (note 32), offline and zero-token: render_turn is a pure
string function; summarize_turn drives an injected FakeModel."""

from harness.core import reflect
from tests.fakes import FakeModel, text_reply


def test_render_turn_compacts_and_skips_anchors():
    turn = [
        {"role": "user", "content": "read README"},
        {"role": "assistant", "content": "On it.",
         "tool_calls": [{"id": "1", "type": "function",
                         "function": {"name": "read_file",
                                      "arguments": '{"path":"README.md"}'}}]},
        {"role": "tool", "tool_call_id": "1", "content": "line one\nline two"},
        {"role": "user", "meta": "anchor", "content": "(automated reminder)"},
        {"role": "assistant", "content": "It's a from-scratch harness."},
    ]
    text = reflect.render_turn(turn)
    assert "user: read README" in text
    assert "called read_file" in text
    assert "result: line one line two" in text   # newlines flattened, head kept
    assert "It's a from-scratch harness." in text
    assert "automated reminder" not in text        # anchor is protocol, skipped


def test_summarize_turn_uses_injected_model():
    model = FakeModel([text_reply("Read README; it's a from-scratch harness.")])
    turn = [
        {"role": "user", "content": "what is this?"},
        {"role": "assistant", "content": "done",
         "tool_calls": [{"id": "1", "type": "function",
                         "function": {"name": "read_file", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "1", "content": "..."},
    ]
    out = reflect.summarize_turn(model, turn)
    assert out == "Read README; it's a from-scratch harness."
    assert model.calls == [2]  # the distiller sees exactly a system+user pair


def test_summarize_turn_survives_empty_reply():
    model = FakeModel([text_reply(None)])
    out = reflect.summarize_turn(model, [{"role": "user", "content": "hi"}])
    assert out == "(empty recap)"
