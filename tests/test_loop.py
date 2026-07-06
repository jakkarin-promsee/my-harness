"""The loop's full contract, tested offline in milliseconds for zero tokens.

FakeModel is the trick (copied in spirit from mini-swe-agent's test suite):
the Agent only ever calls `.complete(messages, schemas)`, so a scripted list
of replies is indistinguishable from Gemini. Every guard and failure path the
loop grew during Stage 1 acceptance gets pinned down here — this is what
makes working rule 5 ("the harness must be boring") enforceable.
"""

import pytest

from harness.core.loop import Agent


class FakeModel:
    """Returns scripted replies; records the messages list at each call."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []  # snapshot of len(messages) per call

    def complete(self, messages, schemas):
        self.calls.append(len(messages))
        return self.script.pop(0)


def text_reply(content, finish="stop"):
    return {"message": {"role": "assistant", "content": content}, "finish_reason": finish, "usage": None}


def tool_reply(*calls):
    return {
        "message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": cid, "type": "function", "function": {"name": name, "arguments": args}}
                for cid, name, args in calls
            ],
        },
        "finish_reason": "tool_calls",
        "usage": None,
    }


def make_agent(model, registry=None, **kwargs):
    kwargs.setdefault("emit", lambda line: None)  # silence output in tests
    return Agent(model=model, registry=registry or {}, schemas=[], **kwargs)


def test_text_reply_is_appended_and_ends_turn():
    model = FakeModel([text_reply("hello")])
    messages = [{"role": "user", "content": "hi"}]
    make_agent(model).run_turn(messages)
    assert len(messages) == 2
    assert messages[1]["content"] == "hello"
    assert model.calls == [1]  # exactly one model call


def test_tool_call_executes_and_mails_result_back():
    seen = {}

    def greet(name):
        seen["name"] = name
        return f"hello {name}"

    model = FakeModel([tool_reply(("id-1", "greet", '{"name": "night"}')), text_reply("done")])
    messages = [{"role": "user", "content": "greet night"}]
    make_agent(model, {"greet": greet}).run_turn(messages)

    assert seen["name"] == "night"          # arguments JSON-parsed and passed
    tool_msg = messages[2]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "id-1"  # id echoed back
    assert tool_msg["content"] == "hello night"
    assert messages[3]["content"] == "done"    # loop called the model again


def test_parallel_tool_calls_all_execute_in_order():
    log = []
    model = FakeModel([
        tool_reply(("a", "t", '{"x": 1}'), ("b", "t", '{"x": 2}')),
        text_reply("done"),
    ])
    messages = [{"role": "user", "content": "go"}]
    make_agent(model, {"t": lambda x: log.append(x) or f"got {x}"}).run_turn(messages)
    assert log == [1, 2]
    assert [m["tool_call_id"] for m in messages if m.get("role") == "tool"] == ["a", "b"]


def test_max_steps_stops_a_runaway_loop():
    model = FakeModel([tool_reply(("i", "t", "{}")) for _ in range(99)])
    messages = [{"role": "user", "content": "go"}]
    make_agent(model, {"t": lambda: "again"}, max_steps=5).run_turn(messages)
    assert len(model.calls) == 5  # hard stop, not 99


def test_length_finish_ends_turn_without_tool_execution():
    boom = lambda: pytest.fail("tool must not run on a truncated reply")  # noqa: E731
    truncated = tool_reply(("i", "t", "{}"))
    truncated["finish_reason"] = "length"
    model = FakeModel([truncated])
    messages = [{"role": "user", "content": "go"}]
    make_agent(model, {"t": boom}).run_turn(messages)
    assert len(messages) == 2  # assistant msg appended, then stop


def test_denied_permission_reports_without_executing():
    model = FakeModel([tool_reply(("i", "t", "{}")), text_reply("ok")])
    messages = [{"role": "user", "content": "go"}]
    make_agent(
        model,
        {"t": lambda: pytest.fail("denied tool must not run")},
        needs_permission={"t"},
        approve=lambda name, args: False,
    ).run_turn(messages)
    assert messages[2]["content"] == "User denied permission for this call."


def test_tool_failures_become_error_text_not_crashes():
    def broken():
        raise RuntimeError("kaput")

    model = FakeModel([
        tool_reply(
            ("a", "nope", "{}"),            # unknown tool
            ("b", "t", "{not json"),        # unparseable arguments
            ("c", "t", '{"wrong": true}'),  # invented parameter
            ("d", "broken", "{}"),          # tool raises
        ),
        text_reply("ok"),
    ])
    messages = [{"role": "user", "content": "go"}]
    make_agent(model, {"t": lambda: "fine", "broken": broken}).run_turn(messages)
    contents = [m["content"] for m in messages if m.get("role") == "tool"]
    assert "unknown tool" in contents[0]
    assert "not valid JSON" in contents[1]
    assert "bad arguments" in contents[2]
    assert "RuntimeError" in contents[3]


def test_huge_tool_output_is_truncated():
    model = FakeModel([tool_reply(("i", "t", "{}")), text_reply("ok")])
    messages = [{"role": "user", "content": "go"}]
    make_agent(model, {"t": lambda: "x" * 5000}, max_tool_chars=100).run_turn(messages)
    tool_msg = messages[2]
    assert "[truncated 4900 chars]" in tool_msg["content"]
    assert len(tool_msg["content"]) < 200


def test_usage_reaches_the_meter_hook():
    reply = text_reply("hi")
    reply["usage"] = {"prompt_tokens": 7, "completion_tokens": 3}
    seen = []
    model = FakeModel([reply])
    make_agent(model, on_usage=seen.append).run_turn([{"role": "user", "content": "hi"}])
    assert seen == [{"prompt_tokens": 7, "completion_tokens": 3}]
