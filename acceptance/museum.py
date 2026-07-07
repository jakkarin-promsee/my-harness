"""The failure museum (2.17, docs/notes/22): real tasks that failed in the
owner's live sessions, frozen as fixtures with verifiers.

Where run.py's core tasks each prove one FEATURE, these prove (or disprove)
the agent's judgment on the messy asks the features were built for. Mined
from sessions/ — each task's docstring-comment names its source transcripts
and the debug-live triage verdict (suspect the harness before the model).

The hold-out (M4) is sacred: excluded from every tuning loop and every
per-feature acceptance, run exactly once at stage close (ROADMAP3 §5,
red-team #13). run.py skips it unless --include-holdout is passed.
"""

import os


def rm(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


# M2: a real project summary names most of these; the live failures (an agent
# reporting one fixture file's planted bug as "what the project is") hit 0-1.
ORIENT_FACTS = {
    "harness": ("harness",),
    "loop": ("loop",),
    "providers": ("provider", "ollama", "gemini", "anthropic"),
    "tools": ("tool",),
    "plan": ("stage", "roadmap", "learning"),
}

# M3: the commands a real guidebook for THIS harness cannot miss. The frozen
# live artifact (museum/guide-book-live-20260707.md) scores 1/7 — the whole
# point: generic filler must FAIL this check.
GUIDEBOOK_FACTS = (
    ("uv run harness", "python -m harness"),  # how to launch
    ("/mode",),
    ("/agent",),
    ("/think",),
    ("/compact",),
    ("--resume",),
    ("explore",),  # at least one mode named
)


def verify_page_eyes(final: str):
    # The agent has eyes (web_fetch, 2.13) — it must use them, not deny them.
    low = final.lower()
    if "example domain" in low:
        return True, "page fetched and reported"
    refused = any(p in low for p in ("can't browse", "cannot browse",
                                     "can't access", "cannot access",
                                     "cannot view", "can't view"))
    return False, "claimed it has no eyes" if refused else f"answer: {final[:100]!r}"


def verify_orient_summary(final: str):
    low = final.lower()
    hit = [name for name, needles in ORIENT_FACTS.items()
           if any(n in low for n in needles)]
    ok = len(hit) >= 4
    return ok, (f"named {len(hit)}/5 fact groups ({', '.join(hit)})" if ok
                else f"only {len(hit)}/5 fact groups ({', '.join(hit) or 'none'}) - wandered?")


def guidebook_score(text: str) -> list[str]:
    """Which real-commands groups a guidebook text covers (pure - testable
    against the frozen live artifact)."""
    low = text.lower()
    return [alts[0] for alts in GUIDEBOOK_FACTS if any(a in low for a in alts)]


def verify_guidebook(final: str):
    if not os.path.exists("docs/guide-book.md"):
        return False, "docs/guide-book.md was not created"
    with open("docs/guide-book.md", encoding="utf-8") as f:
        hit = guidebook_score(f.read())
    ok = len(hit) >= 4
    return ok, (f"covers {len(hit)}/7 real commands" if ok
                else f"only {len(hit)}/7 real commands ({', '.join(hit) or 'none'}) - generic filler?")


def verify_holdout_archaeology(final: str):
    low = final.lower()
    named_file = "run.py" in low
    named_why = "lower" in low or "case" in low
    ok = named_file and named_why
    note = []
    if not named_file:
        note.append("verifier file not named")
    if not named_why:
        note.append("case-insensitivity not explained")
    return ok, "found file + explained lowercase pass" if ok else "; ".join(note)


MUSEUM_TASKS = [
    {
        # sessions 072833/073246/073530: "I can't browse websites" — with
        # web_fetch shipped. Simple task; the failure is not knowing its senses.
        "id": "M1-page-eyes",
        "prompt": "Can you see this page? https://example.com - tell me what it says.",
        "verify": verify_page_eyes,
    },
    {
        # sessions 234230/053822/073917: agent wandered into
        # archive/mvp/fixtures/stats.py and reported the planted bug as the
        # project. Orientation failure (2.22) + bare list_dir (2.21b).
        "id": "M2-orient-summary",
        "prompt": ("Explore this project and tell me what it is about: what it does, "
                   "how I run it, and where the main code lives."),
        "verify": verify_orient_summary,
    },
    {
        # sessions 144442/144739/145030: two dead attempts, then generic filler
        # (frozen: acceptance/museum/guide-book-live-20260707.md, 1/7 commands).
        "id": "M3-guidebook",
        "prompt": ("Write docs/guide-book.md: a guide for using this agent on the "
                   "terminal. Explore the project first - the guide must document "
                   "the real commands: how to launch it, the slash commands, and "
                   "the permission modes."),
        "setup": lambda: rm("docs/guide-book.md"),
        "verify": verify_guidebook,
        "cleanup": lambda: rm("docs/guide-book.md"),
    },
    {
        # THE HOLD-OUT (red-team #13). No baseline run, no tuning contact.
        # First and only runs happen at stage close (ROADMAP3 §5).
        "id": "M4-holdout-archaeology",
        "prompt": ("The acceptance suite has a fizzbuzz task. Find which file "
                   "defines its verifier, quote what the verifier checks, and "
                   "explain why a program that prints lowercase 'fizzbuzz' passes."),
        "verify": verify_holdout_archaeology,
        "holdout": True,
    },
]
