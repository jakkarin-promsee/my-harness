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


def test_same_second_sessions_get_distinct_ids(tmp_path):
    # Two /agent switches (or /compacts) inside one second must not share a
    # file - the second would silently append into the first (2026-07-07).
    store = SessionStore(str(tmp_path / "s"))
    ids = {store.new() for _ in range(3)}
    assert len(ids) == 3
    later = store.new()
    assert store.latest() == later  # suffixed ids still sort as newest


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


def _batch(*ids):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": i, "type": "function", "function": {"name": "t", "arguments": "{}"}}
        for i in ids]}


def test_repair_synthesizes_exactly_the_missing_results():
    # 2.25 (note 34): a turn killed mid-batch leaves unanswered tool_calls -
    # the shape strict wires 400 on. Repair fills the gaps, in batch order.
    from harness.core.session import repair_dangling_calls
    msgs = [{"role": "user", "content": "go"},
            _batch("c1", "c2", "c3"),
            {"role": "tool", "tool_call_id": "c2", "content": "done"}]
    new = repair_dangling_calls(msgs)
    assert [m["tool_call_id"] for m in new] == ["c1", "c3"]
    assert all(m["role"] == "tool" and "interrupted" in m["content"] for m in new)
    assert msgs[-2:] == new  # appended in place
    assert repair_dangling_calls(msgs) == []  # idempotent


def test_repair_leaves_healthy_histories_alone():
    from harness.core.session import repair_dangling_calls
    answered = [_batch("c1"), {"role": "tool", "tool_call_id": "c1", "content": "ok"}]
    assert repair_dangling_calls(answered) == []
    chat = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]
    assert repair_dangling_calls(chat) == []
    assert len(answered) == 2 and len(chat) == 2  # untouched


def test_repair_refuses_a_foreign_tail():
    # A non-tool message after an unanswered batch is not an interrupt shape;
    # appending results past it would be invalid ordering. Touch nothing.
    from harness.core.session import repair_dangling_calls
    msgs = [_batch("c1"), {"role": "user", "content": "steer"}]
    assert repair_dangling_calls(msgs) == []
    assert len(msgs) == 2


def test_prune_stale_anchors_keeps_only_the_last():
    # 2.23 (note 30): append-only JSONL replays every anchor that ever
    # existed; only the newest was live.
    from harness.core.session import prune_stale_anchors
    msgs = [{"role": "user", "content": "ask"},
            {"role": "user", "content": "a1", "meta": "anchor"},
            {"role": "assistant", "content": "work"},
            {"role": "user", "content": "a2", "meta": "anchor"}]
    pruned = prune_stale_anchors(msgs)
    anchors = [m for m in pruned if m.get("meta") == "anchor"]
    assert [a["content"] for a in anchors] == ["a2"]
    assert len(pruned) == 3
