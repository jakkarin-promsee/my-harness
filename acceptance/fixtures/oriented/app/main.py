"""demo-app entry point (acceptance fixture - not real code)."""

import tomllib
from pathlib import Path


def load_settings() -> dict:
    cfg = Path(__file__).parent.parent / "config" / "settings.toml"
    return tomllib.loads(cfg.read_text())


def fetch_with_retries(url: str) -> str:
    settings = load_settings()
    for attempt in range(settings["network"]["max_attempts"]):
        pass  # (fixture: no real network)
    return "ok"
