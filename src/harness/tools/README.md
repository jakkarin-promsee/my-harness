# src/harness/tools — what the model can DO

A tool is a plain Python function (what runs) plus a JSON-schema advertisement (all the model ever sees). The model can't execute anything — it *asks* by replying with `tool_calls`; the loop runs the function and mails back the result as a string. Tool **descriptions are the only signal** the model has for choosing — they matter more than they look (note 04).

| File | Provides |
|---|---|
| `basic.py` | 7 file/shell tools: `read_file`, `write_file`, `list_dir`, `run_shell`, `edit_file`, `grep`, `glob`. `REGISTRY` maps name→fn; `SCHEMAS` are the advertisements; `NEEDS_PERMISSION` = the mutating three (`write_file`, `run_shell`, `edit_file`). |
| `todo.py` | `todo_write` — an external checklist the model can't forget. Replace-the-whole-list semantics (no patch ops for a small model to fumble). Note 13. |

`spawn_subagent` is a tool too, but it lives in `core/subagent.py` because it needs the loop itself.

**Adding a tool:** write the function (return a string, *always* — let the loop turn errors into text), add a `_schema(...)` entry, register it in `REGISTRY`, and add it to `NEEDS_PERMISSION` if it mutates. Design lessons worth keeping: bound the output (`grep` caps at 50 matches, `glob` at 100), and make ambiguity an error the model can fix (`edit_file`'s match-exactly-once rule). Test pattern: `tests/test_tools.py`.
