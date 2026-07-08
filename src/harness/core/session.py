"""Sessions: the transcript IS the session.

One JSONL file per session; every message becomes one line the moment it
exists (open-append-close per write, so a crash never loses more than
nothing). Resume = read the lines back into a list. That's the whole trick —
and it's also the raw-logs-on-disk layer Stage 3.4's findings channel needs.
"""

import json
import time
from pathlib import Path


def prune_stale_anchors(messages: list) -> list:
    """Keep only the LAST attention anchor (2.23, note 30). The JSONL is
    append-only, so a resumed transcript replays every anchor that ever
    existed; only the newest was live when the session ended - staleness is
    derivable, no mutation ever touched the disk."""
    anchor_idx = [i for i, m in enumerate(messages) if m.get("meta") == "anchor"]
    stale = set(anchor_idx[:-1])
    return [m for i, m in enumerate(messages) if i not in stale]


class SessionStore:
    def __init__(self, directory: str = "sessions"):
        self.dir = Path(directory)

    def new(self) -> str:
        self.dir.mkdir(parents=True, exist_ok=True)
        session_id = time.strftime("%Y%m%d-%H%M%S")
        # Second-resolution stamps collide (two /agent switches in one
        # second, measured 2026-07-07) — suffix rather than silently
        # appending into the earlier session's file.
        base, n = session_id, 2
        while self._path(session_id).exists():
            session_id = f"{base}-{n}"
            n += 1
        # Touch the file so `latest()` sees it even before the first message.
        self._path(session_id).touch()
        return session_id

    def append(self, session_id: str, message: dict) -> None:
        with open(self._path(session_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")

    def load(self, session_id: str) -> list:
        lines = self._path(session_id).read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def latest(self) -> str | None:
        # Sort by STEM: with the full filename, "...-2.jsonl" sorts before
        # "....jsonl" ("-" < "."), and latest() would pick the older file.
        files = sorted(self.dir.glob("*.jsonl"), key=lambda p: p.stem) if self.dir.exists() else []
        return files[-1].stem if files else None

    def listing(self) -> list[str]:
        """One human line per session: id, message count, first user words."""
        rows = []
        for fp in sorted(self.dir.glob("*.jsonl"), key=lambda p: p.stem) if self.dir.exists() else []:
            messages = self.load(fp.stem)
            first_user = next(
                (m["content"] for m in messages if m["role"] == "user"), "(empty)"
            )
            rows.append(f"{fp.stem}  {len(messages):>4} msgs  {str(first_user)[:60]}")
        return rows

    def _path(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.jsonl"
