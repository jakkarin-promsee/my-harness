"""Lab 03 — the two wire probes 2.17 demands (ROADMAP3, red-team #4).

Before 2.19 (voice & effort) and 2.20 (thinking-curve lab) can depend on the
docs' claims, the wire has to confirm them:

  (a) does `reasoning_effort: "none"` actually DISABLE gemini-2.5-flash's
      default thinking on the OpenAI-compat endpoint?
  (b) does the usage payload expose a thinking-token split
      (`completion_tokens_details.reasoning_tokens`)? And what does Ollama's
      native /api/chat report? (expected: eval_count lumps everything)

Method: one small-but-not-trivial prompt (forces some thinking budget when
thinking is on), four Gemini variants + one Ollama call, print raw usage.
Findings land in docs/notes/22-failure-museum.md and drive 2.19's accounting.

Run:  uv run python archive/labs/03_reasoning_effort_probe.py     (uses $ credit — one deliberate run)
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import truststore

truststore.inject_into_ssl()

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"

# Small but reasoning-shaped: a model with thinking ON will spend budget here.
PROMPT = ("A farmer has 17 sheep. All but 9 run away. The next day he buys twice "
          "as many sheep as he has left. How many sheep does he have now? "
          "Answer with just the number.")


def gemini(model: str, effort: str | None) -> None:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 4096,
    }
    if effort is not None:
        body["reasoning_effort"] = effort
    label = f"{model} | reasoning_effort={effort!r}"
    resp = requests.post(
        GEMINI_URL,
        headers={"Authorization": f"Bearer {os.environ['GEMINI_API_KEY']}"},
        json=body, timeout=120,
    )
    if resp.status_code != 200:
        print(f"--- {label}\n    HTTP {resp.status_code}: {resp.text[:300]}")
        return
    data = resp.json()
    msg = data["choices"][0]["message"]
    print(f"--- {label}")
    print(f"    answer : {(msg.get('content') or '')[:80]!r}")
    print(f"    usage  : {json.dumps(data.get('usage'), indent=None)}")


def ollama() -> None:
    body = {
        "model": os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct"),
        "messages": [{"role": "user", "content": PROMPT}],
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=body, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    print(f"--- ollama native | {body['model']}")
    print(f"    answer : {(data.get('message', {}).get('content') or '')[:80]!r}")
    keys = {k: v for k, v in data.items() if "count" in k or "duration" in k}
    print(f"    usage-ish fields: {json.dumps(keys)}")


if __name__ == "__main__":
    print("=== probe (a)+(b): gemini-2.5-flash across efforts ===")
    gemini("gemini-2.5-flash", None)      # default: thinks by default per docs
    gemini("gemini-2.5-flash", "none")    # the off-switch under test
    gemini("gemini-2.5-flash", "low")
    print("\n=== control: flash-lite (docs say: does not think unless asked) ===")
    gemini("gemini-2.5-flash-lite", None)
    print("\n=== probe (b) local: what does Ollama's wire report? ===")
    ollama()
