"""Budget estimation + the /compact baseline, offline."""

from harness.core import budget
from tests.fakes import FakeModel, text_reply


def test_estimate_is_positive_and_monotonic():
    a = [{"role": "user", "content": "hi"}]
    b = a + [{"role": "assistant", "content": "x" * 400}]
    assert 0 < budget.estimate_tokens(a) < budget.estimate_tokens(b)
    assert budget.estimate_tokens(b) >= 100  # 400 chars ≈ ≥100 tokens


def test_budget_line_warns_at_80_percent():
    calm = budget.budget_line(79, 100)
    loud = budget.budget_line(80, 100)
    assert "[!]" not in calm
    assert "[!]" in loud and "/compact" in loud


def test_budget_line_without_window_just_reports():
    line = budget.budget_line(1234, 0)
    assert "1,234" in line and "%" not in line


def test_compact_replaces_history_and_surfaces_cost():
    reply = text_reply("- task: build harness (in progress)")
    reply["usage"] = {"prompt_tokens": 500, "completion_tokens": 40}
    model = FakeModel([reply])
    messages = [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "do things"},
        {"role": "assistant", "content": "did things"},
    ]
    new_messages, usage = budget.compact(model, messages)
    assert new_messages[0] == {"role": "system", "content": "SYS"}  # survives
    assert len(new_messages) == 2
    assert new_messages[1]["role"] == "user"
    assert "build harness" in new_messages[1]["content"]
    assert "compacted" in new_messages[1]["content"].lower()
    assert usage == {"prompt_tokens": 500, "completion_tokens": 40}  # cost visible
    assert messages[0]["content"] == "SYS"  # original list untouched (caller decides)
