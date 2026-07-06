"""Context budget + the standard /compact — built to be beaten.

This is context management "the way everyone ships it": estimate, warn,
summarize-and-replace. Its two costs (the summary call itself, and lossy
summarization of signal along with noise) are exactly Pain #1 — Stage 3.1's
surgical ops (/prune, /pin, dump-to-file) must measurably beat this baseline.
You can't beat what you haven't measured, so the costs are made visible here.
"""

import json

# chars/4 is crude but provider-neutral and monotonic. We can't use the API's
# usage numbers for a live estimate: Ollama's prompt_tokens excludes
# KV-cached tokens (measured in Stage 1), so it under-reports systematically.
def estimate_tokens(messages: list) -> int:
    return sum(len(json.dumps(m, ensure_ascii=False)) for m in messages) // 4


WARN_AT = 0.80


def budget_line(estimate: int, window: int) -> str:
    if not window:
        return f"  [context] ~{estimate:,} tokens"
    pct = estimate / window
    line = f"  [context] ~{estimate:,} tokens ({pct:.0%} of {window:,})"
    if pct >= WARN_AT:
        line += "  [!] approaching the window - /compact or start fresh"
    return line


SUMMARIZER_PROMPT = """You compact agent-session transcripts. Produce a dense plain-text summary that preserves:
- the user's task(s) and current state (done / in progress / blocked)
- decisions made and why
- exact file paths and commands that were touched or matter
- unresolved questions or next steps
Drop pleasantries and tool mechanics. Do not invent anything."""


def compact(model, messages: list) -> tuple[list, dict | None]:
    """Summarize everything after the system message; REPLACE history with it.

    Note what this costs (returned usage — the model re-reads the whole
    transcript) and what it loses (summarization is lossy for signal too).
    That is the point: this is the baseline, not the goal.
    """
    transcript = json.dumps(messages[1:], ensure_ascii=False)
    reply = model.complete(
        [
            {"role": "system", "content": SUMMARIZER_PROMPT},
            {"role": "user", "content": f"Summarize this transcript:\n\n{transcript}"},
        ],
        [],  # the summarizer gets no tools
    )
    summary = reply["message"].get("content") or "(empty summary)"
    new_messages = [
        messages[0],  # the system prompt survives untouched
        {
            "role": "user",
            "content": "[Context was compacted. Summary of the conversation so far:]\n" + summary,
        },
    ]
    return new_messages, reply.get("usage")
