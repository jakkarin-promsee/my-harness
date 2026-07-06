"""Subagents offline: two FakeModels, parent spawns, child answers."""

import json

from harness.core.loop import Agent
from harness.core.subagent import make_spawn_tool
from tests.fakes import FakeModel, text_reply, tool_reply

SILENT = lambda line: None  # noqa: E731


class RecordingModel(FakeModel):
    """FakeModel that also snapshots messages and schemas per call."""

    def __init__(self, script):
        super().__init__(script)
        self.seen = []
        self.seen_schemas = []

    def complete(self, messages, schemas):
        self.seen.append([dict(m) for m in messages])
        self.seen_schemas.append(list(schemas))
        return super().complete(messages, schemas)


def run_parent_with_spawn(child_model, spawn_args: dict, parent_history=None):
    parent_messages = parent_history or [
        {"role": "system", "content": "PARENT SYS"},
        {"role": "user", "content": "please delegate"},
    ]
    spawn_fn, schema = make_spawn_tool(
        model=child_model,
        registry={},
        schemas=[],
        needs_permission=set(),
        approve=lambda name, args: True,
        emit=SILENT,
        get_parent_messages=lambda: parent_messages,
        system_prompt="CHILD SYS",
    )
    parent_model = FakeModel([
        tool_reply(("s1", "spawn_subagent", json.dumps(spawn_args))),
        text_reply("delegated fine"),
    ])
    Agent(
        model=parent_model,
        registry={"spawn_subagent": spawn_fn},
        schemas=[schema],
        emit=SILENT,
    ).run_turn(parent_messages)
    return parent_messages


def test_fresh_child_sees_only_system_and_prompt():
    child = RecordingModel([text_reply("child answer")])
    messages = run_parent_with_spawn(child, {"prompt": "check X", "context": "fresh"})
    first_call = child.seen[0]
    assert [m["role"] for m in first_call] == ["system", "user"]
    assert first_call[0]["content"] == "CHILD SYS"      # not the parent's system
    assert first_call[1]["content"] == "check X"
    # child's final text became the parent's tool result, verbatim
    tool_msg = next(m for m in messages if m.get("role") == "tool")
    assert tool_msg["content"] == "child answer"


def test_fork_child_gets_history_copy_and_parent_stays_clean():
    child = RecordingModel([text_reply("checked against history")])
    messages = run_parent_with_spawn(child, {"prompt": "audit", "context": "fork"})
    first_call = child.seen[0]
    contents = [m.get("content") for m in first_call]
    assert "please delegate" in contents        # parent history inherited
    assert first_call[-1]["content"] == "audit"
    # the child's own assistant reply must NOT leak into parent history
    assert all(m.get("content") != "checked against history"
               for m in messages if m.get("role") == "assistant")


def test_child_cannot_spawn_recursively():
    """Even handed the PARENT's registry (spawn included), the child must
    see neither the spawn function nor its schema."""
    from harness.core.subagent import SPAWN_SCHEMA

    child = RecordingModel([
        tool_reply(("c1", "spawn_subagent", '{"prompt": "recurse!"}')),
        text_reply("gave up"),
    ])
    spawn_fn, _ = make_spawn_tool(
        model=child,
        registry={"spawn_subagent": lambda **kw: "MUST NOT RUN", "read": lambda: "r"},
        schemas=[SPAWN_SCHEMA],
        needs_permission=set(), approve=lambda n, a: True,
        emit=SILENT, get_parent_messages=lambda: [], system_prompt="S",
    )
    result = spawn_fn("do it")
    # schema stripped from what the child model was advertised
    assert all(
        s["function"]["name"] != "spawn_subagent" for s in child.seen_schemas[0]
    )
    # and the child's attempt to call it anyway hit "unknown tool"
    assert result == "gave up"


def test_child_without_text_answer_reports_gracefully():
    child = FakeModel([tool_reply(("c1", "missing_tool", "{}"))] +
                      [tool_reply(("c2", "missing_tool", "{}")) for _ in range(9)])
    spawn_fn, _ = make_spawn_tool(
        model=child, registry={}, schemas=[], needs_permission=set(),
        approve=lambda n, a: True, emit=SILENT,
        get_parent_messages=lambda: [], system_prompt="S",
    )
    assert "without a final text answer" in spawn_fn("loop forever")


# ---- 2.11: named roles (agent=) --------------------------------------------

def make_spawn_with_roles(child, agent_prompts):
    return make_spawn_tool(
        model=child, registry={}, schemas=[], needs_permission=set(),
        approve=lambda n, a: True, emit=SILENT,
        get_parent_messages=lambda: [{"role": "system", "content": "PARENT SYS"}],
        system_prompt="CHILD SYS", agent_prompts=agent_prompts,
    )


def test_named_role_gives_fresh_child_that_prompt():
    child = RecordingModel([text_reply("planned")])
    spawn_fn, schema = make_spawn_with_roles(child, {"plan": "PLAN SYS"})
    # roles present -> the schema advertises the agent parameter
    assert "agent" in schema["function"]["parameters"]["properties"]
    result = spawn_fn("plan it", context="fresh", agent="plan")
    assert child.seen[0][0]["content"] == "PLAN SYS"   # not CHILD SYS
    assert result == "planned"


def test_no_roles_means_no_agent_param_in_schema():
    spawn_fn, schema = make_spawn_tool(
        model=FakeModel([]), registry={}, schemas=[], needs_permission=set(),
        approve=lambda n, a: True, emit=SILENT,
        get_parent_messages=lambda: [], system_prompt="S",
    )
    assert "agent" not in schema["function"]["parameters"]["properties"]


def test_unknown_role_is_error_text_not_crash():
    spawn_fn, _ = make_spawn_with_roles(FakeModel([]), {"plan": "P"})
    out = spawn_fn("x", agent="ghost")
    assert out.startswith("ERROR") and "plan" in out


def test_role_plus_fork_is_error_text():
    spawn_fn, _ = make_spawn_with_roles(FakeModel([]), {"plan": "P"})
    out = spawn_fn("x", context="fork", agent="plan")
    assert out.startswith("ERROR") and "fresh" in out
