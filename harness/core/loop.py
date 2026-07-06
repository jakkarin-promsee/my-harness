"""The agent loop — the heart of the harness, and nothing but the heart.

Everything this class touches is INJECTED: the model, the tool registry, the
permission gate, the output/usage callbacks. It performs no HTTP, no input(),
no printing it wasn't handed. Consequence: the loop cannot tell a real
provider from tests/test_loop.py's FakeModel — which is exactly what makes
it testable for zero tokens (working rule 5: the harness must be boring).

The loop's contract is what it does to `messages` (the list is mutated in
place; it is the conversation):

    text reply            -> appended, turn ends
    tool_calls reply      -> assistant msg appended, every call executed,
                             one role:"tool" msg per call (tool_call_id echoed),
                             then call the model again
    finish_reason length  -> turn ends immediately (generation was cut off)
    MAX_STEPS exhausted   -> hard stop (runaway guard)

Tool problems — unknown tool, denied permission, bad-JSON arguments, a raised
exception — become ERROR/denial *text sent back to the model*, never a crash:
the model can read what went wrong and adapt.
"""

import json
from typing import Callable


class Agent:
    def __init__(
        self,
        model,
        registry: dict[str, Callable],
        schemas: list[dict],
        needs_permission: set[str] = frozenset(),
        approve: Callable[[str, dict], bool] = lambda name, args: True,
        emit: Callable[[str], None] = print,
        on_usage: Callable[[dict], None] | None = None,
        max_steps: int = 20,
        max_tool_chars: int = 2000,
    ):
        self.model = model                      # anything with .complete(messages, schemas)
        self.registry = registry                # tool name -> python function
        self.schemas = schemas                  # what the model sees
        self.needs_permission = needs_permission
        self.approve = approve                  # the permission gate, as a callable
        self.emit = emit                        # user-facing lines go through here
        self.on_usage = on_usage                # token meter hook (CLI accumulates)
        self.max_steps = max_steps              # runaway-LOOP guard
        self.max_tool_chars = max_tool_chars    # crude output diet; Stage 3.1 replaces

    def run_turn(self, messages: list) -> None:
        """One user request -> the model chains tool calls -> final text."""
        for _ in range(self.max_steps):
            reply = self.model.complete(messages, self.schemas)
            msg = reply["message"]
            if self.on_usage and reply.get("usage"):
                self.on_usage(reply["usage"])
            # The model's move — text OR tool request — is part of the
            # conversation. Forgetting this append breaks the next call.
            messages.append(msg)

            if reply["finish_reason"] == "length":
                self.emit("  [!] reply was cut off by the token limit - stopping this turn")
                return

            # Presence of tool_calls, not finish_reason, is the robust signal:
            # some Ollama models say "stop" while still carrying tool calls.
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                self.emit(f"\nagent> {msg.get('content') or '(no text)'}")
                return

            for call in tool_calls:
                result = self._execute(call)
                if len(result) > self.max_tool_chars:
                    result = result[: self.max_tool_chars] + (
                        f"\n[truncated {len(result) - self.max_tool_chars} chars]"
                    )
                first_line = result.splitlines()[0] if result else ""
                self.emit(f"  [tool] {call['function']['name']} -> {first_line[:80]}")
                # tool_call_id echoes the model's id so results match requests.
                messages.append(
                    {"role": "tool", "tool_call_id": call["id"], "content": result}
                )

        self.emit(f"  [!] hit MAX_STEPS={self.max_steps} - stopping this turn (runaway guard)")

    def _execute(self, call: dict) -> str:
        name = call["function"]["name"]
        try:
            # Classic gotcha: arguments arrive as a JSON *string*.
            arguments = json.loads(call["function"]["arguments"])
        except json.JSONDecodeError as e:
            return f"ERROR: arguments were not valid JSON: {e}"
        if name not in self.registry:
            return f"ERROR: unknown tool {name!r}"
        if name in self.needs_permission and not self.approve(name, arguments):
            return "User denied permission for this call."
        try:
            return self.registry[name](**arguments) or "(empty output)"
        except TypeError as e:
            return f"ERROR: bad arguments: {e}"  # model invented/omitted a parameter
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"
