"""Subagents: another loop over another messages list, summary back to parent.

Two context modes, two epistemic tools (harness-context-v3 §C, Stage 3.5):
  fresh — clean slate, only the prompt. Outside view: catches blind spots
          precisely because it can't see how the parent got here.
  fork  — deep copy of the parent's conversation. Inside view: can check
          consistency against everything already established.

The parent's context receives ONLY the child's final text (as the spawn
tool's result) — the child's transcript never enters the parent's window.
That asymmetry is the whole point of subagents for context economics.
"""

import copy

from harness.core.loop import Agent

SPAWN_SCHEMA = {
    "type": "function",
    "function": {
        "name": "spawn_subagent",
        "description": (
            "Delegate a task to a subagent and get its final answer back. "
            "context='fresh' gives it a clean slate (it sees ONLY your prompt - "
            "good for unbiased checks); context='fork' gives it a copy of this "
            "whole conversation (good for work that needs everything so far)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The task for the subagent."},
                "context": {"type": "string", "enum": ["fresh", "fork"],
                            "description": "Inheritance mode, default 'fresh'."},
            },
            "required": ["prompt"],
        },
    },
}


def make_spawn_tool(
    model,
    registry: dict,
    schemas: list,
    needs_permission: set,
    approve,
    emit,
    get_parent_messages,  # callable -> the LIVE parent list (it gets rebound on /compact)
    system_prompt: str,
    on_usage=None,
):
    # The child gets the same tools MINUS spawn itself: no recursion at Stage 2.
    # Actively stripped (not just "don't pass it") so the invariant can't be
    # broken by whichever registry the caller hands us.
    child_registry = {k: v for k, v in registry.items() if k != "spawn_subagent"}
    child_schemas = [s for s in schemas if s["function"]["name"] != "spawn_subagent"]

    def spawn_subagent(prompt: str, context: str = "fresh") -> str:
        if context == "fork":
            # Deep copy: the child must never mutate parent history.
            child_messages = copy.deepcopy(get_parent_messages())
        else:
            child_messages = [{"role": "system", "content": system_prompt}]
        child_messages.append({"role": "user", "content": prompt})

        child = Agent(
            model=model,
            registry=child_registry,
            schemas=child_schemas,
            needs_permission=needs_permission,
            approve=approve,               # parent's gate guards the child too
            emit=lambda line: emit(f"  [sub]{line}"),
            on_usage=on_usage,             # child tokens count in the session meter
            max_steps=10,
        )
        child.run_turn(child_messages)

        final = next(
            (
                m.get("content")
                for m in reversed(child_messages)
                if m.get("role") == "assistant" and m.get("content")
            ),
            None,
        )
        return final or "(subagent finished without a final text answer)"

    return spawn_subagent, SPAWN_SCHEMA
