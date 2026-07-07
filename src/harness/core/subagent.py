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

# Added to the schema only when roles exist (note 17): the registry that
# serves /agent serves subagents too — opencode's unification.
AGENT_PARAM_DESC = (
    "Optional role for a fresh child: {names}. The child gets that agent's "
    "system prompt instead of yours."
)


def make_spawn_tool(
    model,
    registry: dict,
    schemas: list,
    needs_permission: set,
    approve,
    emit,
    get_parent_messages,  # callable -> the LIVE parent list (it gets rebound on /compact)
    system_prompt,        # str, or a callable -> str assembled at SPAWN time (note 24)
    on_usage=None,
    agent_prompts: dict | None = None,  # {role name: prompt-or-callable} (notes 17, 24)
):
    # The child gets the same tools MINUS spawn itself: no recursion at Stage 2.
    # Actively stripped (not just "don't pass it") so the invariant can't be
    # broken by whichever registry the caller hands us.
    child_registry = {k: v for k, v in registry.items() if k != "spawn_subagent"}
    child_schemas = [s for s in schemas if s["function"]["name"] != "spawn_subagent"]

    schema = copy.deepcopy(SPAWN_SCHEMA)
    if agent_prompts:
        schema["function"]["parameters"]["properties"]["agent"] = {
            "type": "string",
            "description": AGENT_PARAM_DESC.format(names=", ".join(sorted(agent_prompts))),
        }

    def spawn_subagent(prompt: str, context: str = "fresh", agent: str = "") -> str:
        if agent and context == "fork":
            # Ambiguity is an error the model can fix (the edit_file lesson):
            # a fork inherits this conversation's identity by definition.
            return "ERROR: agent= only works with context='fresh' - a fork inherits this conversation as-is."
        if agent and agent not in (agent_prompts or {}):
            return f"ERROR: unknown agent {agent!r} (available: {', '.join(sorted(agent_prompts or {}))})"
        if context == "fork":
            # Deep copy: the child must never mutate parent history.
            child_messages = copy.deepcopy(get_parent_messages())
        else:
            # Callables resolve NOW, not at construction (note 24): a child
            # spawned after /prompt or /agent switched must feel the change.
            child_prompt = agent_prompts[agent] if agent else system_prompt
            if callable(child_prompt):
                child_prompt = child_prompt()
            child_messages = [{"role": "system", "content": child_prompt}]
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

    return spawn_subagent, schema
