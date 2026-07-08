"""The loop's full contract, tested offline in milliseconds for zero tokens.

FakeModel is the trick (copied in spirit from mini-swe-agent's test suite):
the Agent only ever calls `.complete(messages, schemas)`, so a scripted list
of replies is indistinguishable from Gemini. Every guard and failure path the
loop grew during Stage 1 acceptance gets pinned down here — this is what
makes working rule 5 ("the harness must be boring") enforceable.
"""

import pytest

from harness.core.loop import Agent
from tests.fakes import FakeModel, text_reply, tool_reply


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


def test_length_finish_nudges_without_tool_execution():
    # A truncated reply's tool calls are garbage: never executed, and STRIPPED
    # from history (an unanswered tool_call poisons the next POST). The loop
    # nudges once instead of dying (docs/notes/11-visible-mind.md).
    boom = lambda: pytest.fail("tool must not run on a truncated reply")  # noqa: E731
    truncated = tool_reply(("i", "t", "{}"))
    truncated["finish_reason"] = "length"
    model = FakeModel([truncated, text_reply("recovered")])
    messages = [{"role": "user", "content": "go"}]
    make_agent(model, {"t": boom}).run_turn(messages)
    assert "tool_calls" not in messages[1]          # truncated calls dropped
    assert "cut off" in messages[2]["content"]      # the nudge message
    assert messages[3]["content"] == "recovered"


def test_two_length_replies_end_the_turn_without_looping():
    model = FakeModel([text_reply("half a tho", finish="length"),
                       text_reply("ught agai", finish="length")])
    messages = [{"role": "user", "content": "go"}]
    make_agent(model).run_turn(messages)
    assert len(model.calls) == 2                    # exactly one nudge, no spiral


def test_preamble_content_is_emitted_before_the_tool_runs():
    order = []
    model = FakeModel([
        tool_reply(("i", "t", "{}"), content="let me check the file first"),
        text_reply("done"),
    ])
    agent = Agent(
        model=model,
        registry={"t": lambda: order.append("tool ran") or "ok"},
        schemas=[],
        emit=lambda line: order.append(line),
    )
    agent.run_turn([{"role": "user", "content": "go"}])
    preamble = next(i for i, x in enumerate(order) if "let me check" in x)
    ran = order.index("tool ran")
    assert preamble < ran                           # narration BEFORE action


def test_reasoning_reaches_emit_thinking_but_not_history():
    thoughts = []
    model = FakeModel([text_reply("answer", reasoning="hmm, let me think")])
    messages = [{"role": "user", "content": "go"}]
    make_agent(model, emit_thinking=thoughts.append).run_turn(messages)
    assert thoughts == ["hmm, let me think"]
    assert all("reasoning" not in m for m in messages)  # scratchpad, not context


def test_denied_permission_reports_without_executing():
    model = FakeModel([tool_reply(("i", "t", "{}")), text_reply("ok")])
    messages = [{"role": "user", "content": "go"}]
    make_agent(
        model,
        {"t": lambda: pytest.fail("denied tool must not run")},
        needs_permission={"t"},
        approve=lambda name, args: False,
    ).run_turn(messages)
    assert messages[2]["content"] == "Permission denied for this call."


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


def test_huge_tool_output_keeps_head_and_tail():
    # The error is usually at the END of shell output — the tail must survive.
    payload = "HEAD" + "x" * 5000 + "TAIL"
    model = FakeModel([tool_reply(("i", "t", "{}")), text_reply("ok")])
    messages = [{"role": "user", "content": "go"}]
    make_agent(model, {"t": lambda: payload}, max_tool_chars=100).run_turn(messages)
    content = messages[2]["content"]
    assert content.startswith("HEAD")
    assert content.endswith("TAIL")
    assert "chars truncated" in content
    assert len(content) < 200


def test_empty_reply_gets_one_nudge_then_recovery():
    model = FakeModel([text_reply(""), text_reply("recovered")])
    messages = [{"role": "user", "content": "hi"}]
    make_agent(model).run_turn(messages)
    assert len(model.calls) == 2                       # nudge triggered a retry
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert "empty" in messages[2]["content"]           # the nudge message
    assert messages[3]["content"] == "recovered"


def test_two_empty_replies_end_the_turn_without_looping():
    model = FakeModel([text_reply(""), text_reply("")])
    messages = [{"role": "user", "content": "hi"}]
    make_agent(model).run_turn(messages)
    assert len(model.calls) == 2                       # exactly one nudge, no spiral


def test_usage_reaches_the_meter_hook():
    reply = text_reply("hi")
    reply["usage"] = {"prompt_tokens": 7, "completion_tokens": 3}
    seen = []
    model = FakeModel([reply])
    make_agent(model, on_usage=seen.append).run_turn([{"role": "user", "content": "hi"}])
    assert seen == [{"prompt_tokens": 7, "completion_tokens": 3}]


# ---- attention anchors (2.23, note 30) --------------------------------------

def _tool_step(i):
    return tool_reply((f"id{i}", "read_file", '{"path": "x.txt"}'))


def test_anchor_appears_after_quiet_steps_and_carries_the_ask():
    replies = [_tool_step(i) for i in range(3)] + [text_reply("done")]
    model = FakeModel(replies)
    agent = Agent(model=model, registry={"read_file": lambda path: "data"},
                  schemas=[], anchor_after=2, get_plan=lambda: "[>] step one")
    messages = [{"role": "system", "content": "s"},
                {"role": "user", "content": "find the treasure"}]
    agent.run_turn(messages)
    anchors = [m for m in messages if m.get("meta") == "anchor"]
    assert len(anchors) == 1
    assert "find the treasure" in anchors[0]["content"]
    assert "[>] step one" in anchors[0]["content"]


def test_second_anchor_replaces_the_first():
    replies = [_tool_step(i) for i in range(4)] + [text_reply("done")]
    model = FakeModel(replies)
    agent = Agent(model=model, registry={"read_file": lambda path: "data"},
                  schemas=[], anchor_after=2)
    messages = [{"role": "system", "content": "s"},
                {"role": "user", "content": "task"}]
    agent.run_turn(messages)
    anchors = [m for m in messages if m.get("meta") == "anchor"]
    assert len(anchors) == 1  # one LIVE anchor at a time
    assert "not user feedback" in anchors[0]["content"]


def test_todo_write_resets_the_anchor_clock():
    replies = [_tool_step(0),
               tool_reply(("t1", "todo_write", '{"todos": []}')),
               _tool_step(2),
               text_reply("done")]
    model = FakeModel(replies)
    agent = Agent(model=model,
                  registry={"read_file": lambda path: "data",
                            "todo_write": lambda todos: "ok"},
                  schemas=[], anchor_after=2)
    messages = [{"role": "system", "content": "s"},
                {"role": "user", "content": "task"}]
    agent.run_turn(messages)
    assert not [m for m in messages if m.get("meta") == "anchor"]


def test_keyboard_interrupt_escapes_from_the_model_call():
    """Ctrl+C must reach the REPL's steer arm (2.25, note 34): the loop's
    error-to-text net catches Exception, and KeyboardInterrupt is a
    BaseException - never swallowed. From the model call there's no dangle:
    the reply was never appended."""
    class InterruptingModel:
        def complete(self, messages, schemas):
            raise KeyboardInterrupt

    messages = [{"role": "user", "content": "go"}]
    with pytest.raises(KeyboardInterrupt):
        make_agent(InterruptingModel()).run_turn(messages)
    assert messages == [{"role": "user", "content": "go"}]


def test_keyboard_interrupt_from_a_tool_leaves_the_repairable_dangle():
    """From inside a tool the assistant batch IS already appended - exactly
    the corpse repair_dangling_calls exists to close."""
    from harness.core.session import repair_dangling_calls

    def boom():
        raise KeyboardInterrupt

    model = FakeModel([tool_reply(("c1", "boom", "{}"))])
    messages = [{"role": "user", "content": "go"}]
    with pytest.raises(KeyboardInterrupt):
        make_agent(model, {"boom": boom}).run_turn(messages)
    assert messages[-1].get("tool_calls")  # the dangle
    assert [m["tool_call_id"] for m in repair_dangling_calls(messages)] == ["c1"]
