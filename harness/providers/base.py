"""The Model protocol — the seam between the loop and every provider.

The loop speaks exactly one dialect (OpenAI-style messages) and expects
exactly one reply shape. Every adapter's job is to make its provider look
like this, translating BOTH directions at the boundary — history gets
replayed on every call, so outgoing translation matters as much as incoming.
"""

from typing import Protocol


class Model(Protocol):
    def complete(self, messages: list, tools: list) -> dict:
        """messages/tools in OpenAI-compat shape ->
        {"message": <assistant msg>, "finish_reason": stop|tool_calls|length, "usage": dict|None}
        """
        ...
