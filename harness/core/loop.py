"""The agent loop — the heart of the harness, and nothing but the heart.

Everything this class touches is INJECTED: the model, the tool registry, the
permission gate, the output/usage callbacks. It performs no HTTP, no input(),
no printing it wasn't handed. Consequence: the loop cannot tell a real
provider from tests/test_loop.py's FakeModel — which is exactly what makes
it testable for zero tokens (working rule 5: the harness must be boring).

The loop's contract is what it does to `messages` (the list is mutated in
place; it is the conversation):

    text reply            -> appended, turn ends
    tool_calls reply      -> preamble content emitted first (the model
                             narrating before it acts), every call executed,
                             one role:"tool" msg per call (tool_call_id echoed),
                             then call the model again
    reasoning in reply    -> shown via emit_thinking; NOT in the message, so
                             it never re-enters context (adapter strips it)
    finish_reason length  -> one nudge ("stop thinking, act"), second -> stop
    MAX_STEPS exhausted   -> hard stop (runaway guard)

Tool problems — unknown tool, denied permission, bad-JSON arguments, a raised
exception — become ERROR/denial *text sent back to the model*, never a crash:
the model can read what went wrong and adapt.
"""

import json
from typing import Callable

# The cut-off nudge (docs/notes/11-visible-mind.md): thinking models burn the
# whole generation budget reasoning and die at finish_reason "length" —
# measured on qwen3:4b (acceptance-local.log, tasks A and G). "/no_think" is
# qwen3's documented soft switch disabling thinking for the next turn; to
# every other model it is inert text.
LENGTH_NUDGE = (
    "(Your previous reply was cut off by the token limit. Do not think out "
    "loud. Call the tool you need now, or give the final answer in a few "
    "short sentences. /no_think)"
)


class Agent:
    def __init__(
        self,
        model,
        registry: dict[str, Callable],
        schemas: list[dict],
        needs_permission: set[str] = frozenset(),
        approve: Callable[[str, dict], bool] = lambda name, args: True,
        emit: Callable[[str], None] = print,
        emit_thinking: Callable[[str], None] | None = None,
        on_usage: Callable[[dict], None] | None = None,
        on_message: Callable[[dict], None] | None = None,
        max_steps: int = 20,
        max_tool_chars: int = 2000,
    ):
        self.model = model                      # anything with .complete(messages, schemas)
        self.registry = registry                # tool name -> python function
        self.schemas = schemas                  # what the model sees
        self.needs_permission = needs_permission
        self.approve = approve                  # the permission gate, as a callable
        self.emit = emit                        # user-facing lines go through here
        # Thinking is presentation too: injectable so the REPL can dim it.
        # The default routes through emit — visible everywhere, styled nowhere.
        self.emit_thinking = emit_thinking or (
            lambda text: self.emit(f"  [thinking] {text}")
        )
        self.on_usage = on_usage                # token meter hook (CLI accumulates)
        self.on_message = on_message            # persistence hook (sessions write here)
        self.max_steps = max_steps              # runaway-LOOP guard
        self.max_tool_chars = max_tool_chars    # crude output diet; Stage 3.1 replaces

    def run_turn(self, messages: list) -> None:
        """One user request -> the model chains tool calls -> final text."""
        nudged = False          # one empty-reply nudge per turn
        length_nudged = False   # one cut-off nudge per turn
        for _ in range(self.max_steps):
            reply = self.model.complete(messages, self.schemas)
            msg = reply["message"]
            if self.on_usage and reply.get("usage"):
                self.on_usage(reply["usage"])
            if reply.get("reasoning"):
                # Shown to the human, absent from msg: the adapter already
                # stripped it, so it costs zero context from here on.
                self.emit_thinking(reply["reasoning"])

            if reply["finish_reason"] == "length":
                # A cut-off reply can carry half-written tool calls. They are
                # garbage — and an unanswered tool_call poisons strict
                # OpenAI-style history on the next POST. Drop them, keep the
                # (possibly partial) text, then nudge the model to act.
                msg.pop("tool_calls", None)
                self._append(messages, msg)
                if not length_nudged:
                    length_nudged = True
                    self.emit("  [!] reply cut off by the token limit - nudging once...")
                    self._append(messages, {"role": "user", "content": LENGTH_NUDGE})
                    continue
                self.emit("  [!] cut off by the token limit again - stopping this turn")
                return

            # The model's move — text OR tool request — is part of the
            # conversation. Forgetting this append breaks the next call.
            self._append(messages, msg)

            # Presence of tool_calls, not finish_reason, is the robust signal:
            # some Ollama models say "stop" while still carrying tool calls.
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                content = msg.get("content")
                if not content and not nudged:
                    # Fully empty reply (no text, no tool calls) — measured
                    # live on gemini flash-lite right after a tool result.
                    # One nudge, then accept whatever comes back.
                    nudged = True
                    self.emit("  [!] empty reply - nudging once...")
                    self._append(messages, {
                        "role": "user",
                        "content": "(Your previous reply was empty. Answer the request or call a tool.)",
                    })
                    continue
                self.emit(f"\nagent> {content or '(no text)'}")
                return

            # Preamble: text riding along WITH tool calls is the model
            # narrating before it acts ("let me read X first"). Claude Code
            # prints it; swallowing it was why turns felt like silent
            # tool->tool->tool (docs/notes/11-visible-mind.md).
            if msg.get("content"):
                self.emit(f"\nagent> {msg['content']}")

            for call in tool_calls:
                result = self._truncate(self._execute(call))
                first_line = result.splitlines()[0] if result else ""
                self.emit(f"  [tool] {call['function']['name']} -> {first_line[:80]}")
                # tool_call_id echoes the model's id so results match requests.
                self._append(
                    messages,
                    {"role": "tool", "tool_call_id": call["id"], "content": result},
                )

        self.emit(f"  [!] hit MAX_STEPS={self.max_steps} - stopping this turn (runaway guard)")

    def _append(self, messages: list, msg: dict) -> None:
        """Every append flows through here so persistence sees every message
        the moment it exists — crash-safety is a property of the loop, not
        a courtesy of the caller."""
        messages.append(msg)
        if self.on_message:
            self.on_message(msg)

    def _truncate(self, result: str) -> str:
        """Head + tail, never just head: shell output puts the error at the
        END — chopping the tail hides exactly the part that matters."""
        if len(result) <= self.max_tool_chars:
            return result
        head = self.max_tool_chars * 3 // 4
        tail = self.max_tool_chars - head
        dropped = len(result) - head - tail
        return (
            result[:head]
            + f"\n[... {dropped} chars truncated ...]\n"
            + result[-tail:]
        )

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
            return "Permission denied for this call."
        try:
            return self.registry[name](**arguments) or "(empty output)"
        except TypeError as e:
            return f"ERROR: bad arguments: {e}"  # model invented/omitted a parameter
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"
