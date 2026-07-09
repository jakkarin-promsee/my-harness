"""ask_user (2.31, note 40): asking as an action — the whole contract,
offline. The tool returns strings in every path; a question must never
hang a run (the 2.28 rule extended)."""

from harness.tools.ask import ASK_SCHEMA, make_ask_tool


def make(answer=None, eof=False):
    lines = []

    def ask_input(prompt):
        if eof:
            raise EOFError
        return answer

    fn, schema = make_ask_tool(ask_input=ask_input, emit=lines.append)
    return fn, lines


def test_verbatim_answer_returns_as_the_result():
    fn, _ = make(answer="the second one")
    assert fn("Which one?") == "The user answered: the second one"


def test_options_render_and_a_number_picks_one():
    fn, lines = make(answer="2")
    out = fn("Which lane?", options=["local", "gemini-flash"])
    assert out == "The user answered: gemini-flash"
    joined = "\n".join(lines)
    assert "[ask] Which lane?" in joined
    assert "1. local" in joined and "2. gemini-flash" in joined


def test_empty_answer_takes_the_recommended_default():
    fn, _ = make(answer="")
    assert fn("Proceed?", recommended="yes") == "The user answered: yes"


def test_eof_takes_the_default_and_says_so():
    # Headless / piped stdin: never hang, take the default, FLAG it.
    fn, _ = make(eof=True)
    out = fn("Proceed?", recommended="the 8192 window")
    assert "No user is available" in out
    assert "the 8192 window" in out


def test_eof_without_default_delegates_honestly():
    fn, _ = make(eof=True)
    out = fn("Proceed?")
    assert "best judgment" in out and "assumption" in out


def test_empty_answer_without_default_delegates_honestly():
    fn, _ = make(answer="  ")
    assert "best judgment" in fn("Which?")


def test_schema_teaches_investigate_first():
    desc = ASK_SCHEMA["function"]["description"]
    assert "AFTER" in desc and "grep" in desc  # never a substitute for looking
    assert ASK_SCHEMA["function"]["parameters"]["required"] == ["question"]
