"""Sessions: the transcript IS the session.

One JSONL file per session; every message becomes one line the moment it
exists (open-append-close per write, so a crash never loses more than
nothing). Resume = read the lines back into a list. That's the whole trick —
and it's also the raw-logs-on-disk layer Stage 3.4's findings channel needs.
"""

import json
import time
from pathlib import Path


class SessionStore:
    def __init__(self, directory: str = "sessions"):
        self.dir = Path(directory)

    def new(self) -> str:
        self.dir.mkdir(parents=True, exist_ok=True)
        session_id = time.strftime("%Y%m%d-%H%M%S")
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
        files = sorted(self.dir.glob("*.jsonl")) if self.dir.exists() else []
        return files[-1].stem if files else None

    def listing(self) -> list[str]:
        """One human line per session: id, message count, first user words."""
        rows = []
        for fp in sorted(self.dir.glob("*.jsonl")) if self.dir.exists() else []:
            messages = self.load(fp.stem)
            first_user = next(
                (m["content"] for m in messages if m["role"] == "user"), "(empty)"
            )
            rows.append(f"{fp.stem}  {len(messages):>4} msgs  {str(first_user)[:60]}")
        return rows

    def _path(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.jsonl"
