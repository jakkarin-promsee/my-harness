"""Museum verifiers (2.17, docs/notes/22) are pure functions — prove offline
that each one catches the REAL failure it was built from, using the frozen
live artifacts as fixtures. Zero tokens."""

from pathlib import Path

from acceptance.museum import (
    guidebook_score,
    verify_holdout_archaeology,
    verify_orient_summary,
    verify_page_eyes,
)

EXHIBIT = Path(__file__).parent.parent / "acceptance" / "museum" / "guide-book-live-20260707.md"


# --- M1: the agent must use its eyes, not deny having them ---------------

def test_page_eyes_passes_a_real_fetch():
    ok, note = verify_page_eyes("The page shows 'Example Domain' - it is a reserved demo page.")
    assert ok, note


def test_page_eyes_catches_the_live_refusal():
    # verbatim failure mode from sessions 072833/073246
    ok, note = verify_page_eyes("I can't browse websites. You'd need to use a browser.")
    assert not ok
    assert "no eyes" in note


# --- M2: a project summary must name the project, not one fixture file ----

def test_orient_summary_passes_a_real_summary():
    ok, note = verify_orient_summary(
        "This is a from-scratch agent harness: a loop around a chat API with "
        "tool calling. Providers: ollama and gemini. Main code under src/harness; "
        "run it with uv run harness. The roadmap has staged plans."
    )
    assert ok, note


def test_orient_summary_catches_the_stats_py_rabbit_hole():
    # the live failure (sessions 234230/053822): the planted bug reported as
    # "what the project is about"
    ok, note = verify_orient_summary(
        "The file archive/mvp/fixtures/stats.py contains a deliberate bug in "
        "the mean function (divides by len+1)."
    )
    assert not ok
    assert "wandered" in note


# --- M3: the frozen live guidebook must FAIL the coverage bar -------------

def test_live_guidebook_artifact_fails_the_bar():
    hits = guidebook_score(EXHIBIT.read_text(encoding="utf-8"))
    assert len(hits) < 4, f"the museum exhibit unexpectedly covers {hits}"


def test_guidebook_score_accepts_a_real_guide():
    hits = guidebook_score(
        "Launch with `uv run harness gemini`. Switch modes with /mode explore; "
        "switch roles with /agent plan; control reasoning with /think low; "
        "compress history with /compact; continue later with --resume."
    )
    assert len(hits) >= 4


# --- M4 (hold-out): verifier logic only — the TASK never runs pre-close ---

def test_holdout_verifier_wants_file_and_reason():
    ok, _ = verify_holdout_archaeology(
        "The verifier is verify_fizzbuzz in acceptance/run.py; it lowercases "
        "the program output, so case does not matter."
    )
    assert ok
    ok, note = verify_holdout_archaeology("It's somewhere in the tests.")
    assert not ok
