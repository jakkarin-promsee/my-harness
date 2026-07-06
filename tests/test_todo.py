"""The todo tool: replace semantics, honest rendering, model-fixable errors
(docs/notes/13-todo-tool.md)."""

from harness.tools.todo import TODO_SCHEMA, make_todo_tool


def quiet():
    lines = []
    fn, schema = make_todo_tool(emit=lines.append)
    return fn, lines


def test_write_returns_summary_plus_rendered_checklist():
    fn, _ = quiet()
    result = fn(todos=[
        {"content": "read the file", "status": "completed"},
        {"content": "fix the bug", "status": "in_progress"},
        {"content": "run the test", "status": "pending"},
    ])
    assert result.startswith("Todo list updated: 1 done, 1 in progress, 1 pending")
    assert "[x] read the file" in result
    assert "[>] fix the bug" in result
    assert "[ ] run the test" in result


def test_replace_semantics_second_call_clobbers_the_first():
    fn, _ = quiet()
    fn(todos=[{"content": "old plan", "status": "pending"}])
    result = fn(todos=[{"content": "new plan", "status": "in_progress"}])
    assert "old plan" not in result
    assert "[>] new plan" in result


def test_bad_status_is_a_model_fixable_error_and_state_survives():
    fn, _ = quiet()
    fn(todos=[{"content": "good", "status": "pending"}])
    err = fn(todos=[{"content": "bad", "status": "done"}])  # not a valid status
    assert err.startswith("ERROR")
    assert "in_progress" in err                    # tells the model the fix
    assert "[ ] good" in fn(todos=[{"content": "good", "status": "pending"}])


def test_missing_content_is_an_error():
    fn, _ = quiet()
    assert fn(todos=[{"status": "pending"}]).startswith("ERROR")


def test_the_human_sees_the_same_checklist():
    fn, lines = quiet()
    fn(todos=[{"content": "step one", "status": "in_progress"}])
    assert len(lines) == 1
    assert "[>] step one" in lines[0]


def test_schema_and_registry_name_agree():
    fn, schema = make_todo_tool(emit=lambda _: None)
    assert schema is TODO_SCHEMA
    assert schema["function"]["name"] == "todo_write"
    statuses = schema["function"]["parameters"]["properties"]["todos"]["items"][
        "properties"]["status"]["enum"]
    assert statuses == ["pending", "in_progress", "completed"]
