"""ask_user: asking the human is an ACTION, not the end of the turn.

The mechanism behind the owner's "stuck on unclear loop" (2.31, note 40):
the model's only affordances were *call a tool* or *end the turn with
text* — asking meant ending the turn, so at an ambiguous task it neither
asked nor investigated. This tool makes the question a tool call: the
answer returns as an ordinary result and the turn continues.

Factory like todo's (note 13): the REPL injects real input(); headless and
scripted runs inject an EOF-raiser, so a question never hangs a run — the
2.28 contract extended. Top-level only: children never interrogate the
human. Permission: allow in every operator mode (the gate would be asking
permission to ask).
"""


def _render(question: str, options, recommended, emit) -> None:
    emit(f"\n  [ask] {question}")
    for i, opt in enumerate(options or [], 1):
        emit(f"    {i}. {opt}")
    if recommended:
        emit(f"    (recommended: {recommended})")


def make_ask_tool(ask_input=input, emit=print):
    def ask_user(question: str, options: list | None = None,
                 recommended: str | None = None) -> str:
        _render(question, options, recommended, emit)
        prompt = ("  your answer (enter = recommended): " if recommended
                  else "  your answer: ")
        try:
            answer = ask_input(prompt)
        except EOFError:
            # No human on stdin (headless, piped, scripted). Never hang:
            # take the offered default and SAY so, or delegate honestly.
            if recommended:
                return ("(No user is available right now - proceeding with "
                        f"the recommended default.) The answer is: {recommended}")
            return ("(No user is available right now - use your best "
                    "judgment and state the assumption you made in your "
                    "final answer.)")
        answer = (answer or "").strip()
        if not answer and recommended:
            answer = recommended
        if not answer:
            return ("(The user gave an empty answer - use your best "
                    "judgment and say what you assumed.)")
        if options and answer.isdigit() and 1 <= int(answer) <= len(options):
            answer = options[int(answer) - 1]  # a number picks its option
        return f"The user answered: {answer}"

    return ask_user, ASK_SCHEMA


ASK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "ask_user",
        "description": (
            "Ask the HUMAN one focused question when the task is still "
            "genuinely ambiguous AFTER you investigated with the read-only "
            "tools. Never a substitute for looking - grep/read first; the "
            "repo usually answers. Offer short options when they exist and "
            "always give your recommended default. The reply arrives as "
            "this tool's result and you continue working with it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The ONE focused question, concrete and answerable in a line.",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Short answer choices, when the possibilities are enumerable.",
                },
                "recommended": {
                    "type": "string",
                    "description": "Your recommended default - used automatically when no user is available.",
                },
            },
            "required": ["question"],
        },
    },
}
