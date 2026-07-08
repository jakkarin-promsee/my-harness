"""Turn reflection — a cheap meta-model distills each finished turn and folds
the recap back into context (play-lane prototype, docs/notes/32).

Why: the thinking lane (`ollama-think`) reasons out loud for hundreds of
tokens per step, and even on the quiet workhorse the raw tool_call/tool_result
churn piles up. Instead of carrying all of it — or throwing the reasoning away
entirely, which is what the adapter does today — a fast NON-thinking model
summarizes the completed turn and REPLACES the churn with the recap. Rolling
compaction, one turn at a time, with a second model: the same architect/editor
split aider uses, applied to memory instead of code.

Relation to the baseline: core/budget.compact summarizes the WHOLE history on
demand; this summarizes ONE turn automatically, right when the agent goes idle
("ready for the next prompt"). Both are lossy summarize-and-replace — Stage 3.1's
surgical ops must still measurably beat them.

Pure by design: render_turn is a string function (tested offline for zero
tokens); summarize_turn takes an INJECTED model, so a FakeModel drives it.
"""


REFLECT_PROMPT = """You distill ONE finished turn of an AI coding agent into a compact memory note, written for the agent's own future reference. In a few terse lines keep:
- what the user asked
- what the agent did (the files, commands, and tools that mattered) and what it found
- the conclusion or answer it gave
- anything left open or worth doing next
Drop the agent's out-loud deliberation, hedging, and repetition. Do not invent anything. Output plain text only, no preamble."""


def render_turn(turn_messages: list) -> str:
    """A finished turn's messages -> a compact plain-text transcript the
    distiller reads: assistant text, the tool calls it made, and each tool
    result (head only). Protocol messages (2.23 anchors) are noise, skipped."""
    lines: list[str] = []
    for m in turn_messages:
        if m.get("meta") == "anchor":
            continue
        role = m.get("role")
        if role == "user":
            lines.append(f"user: {m.get('content', '')}")
        elif role == "assistant":
            if m.get("content"):
                lines.append(f"assistant: {m['content']}")
            for c in m.get("tool_calls") or []:
                fn = c.get("function", {})
                lines.append(f"  -> called {fn.get('name')}({fn.get('arguments')})")
        elif role == "tool":
            body = (m.get("content") or "").strip().replace("\n", " ")
            lines.append(f"  result: {body[:300]}")
    return "\n".join(lines)


def summarize_turn(model, turn_messages: list) -> str:
    """Distill a finished turn via the injected meta-model (a fast, non-thinking
    instruct model in practice). Returns plain text; never raises on empty."""
    transcript = render_turn(turn_messages)
    reply = model.complete(
        [
            {"role": "system", "content": REFLECT_PROMPT},
            {"role": "user", "content": f"Distill this turn:\n\n{transcript}"},
        ],
        [],  # the distiller gets no tools
    )
    return reply["message"].get("content") or "(empty recap)"
