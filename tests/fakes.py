"""Shared test doubles: the FakeModel and reply builders used across suites."""


class FakeModel:
    """Returns scripted replies; records the messages-list length per call."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def complete(self, messages, schemas):
        self.calls.append(len(messages))
        return self.script.pop(0)


def text_reply(content, finish="stop", reasoning=None):
    return {
        "message": {"role": "assistant", "content": content},
        "finish_reason": finish,
        "usage": None,
        "reasoning": reasoning,
    }


def tool_reply(*calls, content=None, reasoning=None):
    return {
        "message": {
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {"id": cid, "type": "function", "function": {"name": name, "arguments": args}}
                for cid, name, args in calls
            ],
        },
        "finish_reason": "tool_calls",
        "usage": None,
        "reasoning": reasoning,
    }
