"""The todo tool: an external plan the model can't forget.

Looks like UX garnish, is actually steering (docs/notes/13-todo-tool.md):
writing the plan puts it INTO CONTEXT where attention finds it every turn,
and updating statuses forces the model to re-read its own plan mid-task.
Replace semantics on purpose — the model resends the whole list, no patch
micro-ops for a small model to fumble. Copied from Claude Code's TodoWrite.
"""

VALID_STATUS = ("pending", "in_progress", "completed")
GLYPH = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}

TODO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "todo_write",
        "description": (
            "Maintain your task checklist. Send the COMPLETE list every time - "
            "it replaces the previous one. For tasks with 3+ steps: write the "
            "plan first, then update statuses as you work. Keep exactly one "
            "item 'in_progress' at a time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "The full checklist, in execution order.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "The step, imperative and short."},
                            "status": {"type": "string", "enum": list(VALID_STATUS)},
                        },
                        "required": ["content", "status"],
                    },
                }
            },
            "required": ["todos"],
        },
    },
}


def make_todo_tool(emit=print):
    """Returns (todo_write, TODO_SCHEMA); the checklist lives in this closure,
    so each agent that gets its own factory call gets its own plan."""
    state: list[dict] = []

    def todo_write(todos: list) -> str:
        for item in todos:
            if not isinstance(item, dict) or "content" not in item:
                return "ERROR: every todo needs a 'content' field."
            if item.get("status") not in VALID_STATUS:
                return (f"ERROR: bad status {item.get('status')!r} - "
                        f"use one of {', '.join(VALID_STATUS)}. List unchanged.")
        state[:] = todos
        rendered = "\n".join(f"{GLYPH[t['status']]} {t['content']}" for t in state)
        counts = {s: sum(1 for t in state if t["status"] == s) for s in VALID_STATUS}
        summary = (f"Todo list updated: {counts['completed']} done, "
                   f"{counts['in_progress']} in progress, {counts['pending']} pending")
        if rendered:
            emit("  [todo]\n" + "\n".join(f"   {line}" for line in rendered.splitlines()))
        # The model gets the canonical list back as the tool result — seeing
        # its own plan again every update is the steering effect we want.
        return summary + ("\n" + rendered if rendered else "")

    return todo_write, TODO_SCHEMA
