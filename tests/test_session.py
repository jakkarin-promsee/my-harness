"""Sessions: the transcript IS the session. All offline, all fast."""

from harness.core.loop import Agent
from harness.core.session import SessionStore

from tests.fakes import FakeModel, text_reply, tool_reply


def test_append_then_load_roundtrips(tmp_path):
    store = SessionStore(str(tmp_path / "s"))
    sid = store.new()
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "yo", "tool_calls": None},
    ]
    for m in msgs:
        store.append(sid, m)
    assert store.load(sid) == msgs


def test_latest_and_listing(tmp_path):
    store = SessionStore(str(tmp_path / "s"))
    assert store.latest() is None
    a = store.new()
    store.append(a, {"role": "user", "content": "first session task"})
    assert store.latest() == a
    rows = store.listing()
    assert len(rows) == 1
    assert "first session task" in rows[0]


def test_loop_reports_every_appended_message(tmp_path):
    """The on_message hook must see the assistant msg AND the tool result —
    the moment they exist, not at end of turn (crash-safety)."""
    seen = []
    model = FakeModel([tool_reply(("c1", "t", "{}")), text_reply("done")])
    messages = [{"role": "user", "content": "go"}]
    Agent(
        model=model,
        registry={"t": lambda: "result"},
        schemas=[],
        emit=lambda line: None,
        on_message=seen.append,
    ).run_turn(messages)
    assert [m.get("role") for m in seen] == ["assistant", "tool", "assistant"]
    # and what the hook saw is exactly what landed in the conversation
    assert messages[1:] == seen


def test_resume_reproduces_the_conversation(tmp_path):
    store = SessionStore(str(tmp_path / "s"))
    sid = store.new()
    model = FakeModel([text_reply("hello")])
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
    for m in messages:
        store.append(sid, m)
    Agent(
        model=model, registry={}, schemas=[],
        emit=lambda line: None, on_message=lambda m: store.append(sid, m),
    ).run_turn(messages)
    assert store.load(sid) == messages  # disk == memory, always
