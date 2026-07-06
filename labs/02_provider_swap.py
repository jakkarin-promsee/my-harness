"""Lab 02 — the same call, different provider. Provider-portability is ~free.

Ollama, Gemini, OpenRouter, vLLM... all speak the same OpenAI-compatible
wire format that labs 00/01 used. So "support another provider" at this layer
means changing exactly three things: base URL, API key, model name.
This is the germ of Stage 2.1's provider adapter — and the "Claude got banned"
insurance in its smallest possible form.

Run:  uv run python labs/02_provider_swap.py            (local Ollama, free)
      uv run python labs/02_provider_swap.py gemini     (Gemini, uses $ credit!)

Gemini needs GEMINI_API_KEY in .env (copy .env.example -> .env, paste key).
"""

import json
import os
import sys

# This machine sits behind TLS inspection (antivirus/ISP) — the default
# certifi bundle rejects it. truststore makes Python use the Windows cert
# store instead, same fix as `system-certs = true` in pyproject.toml for uv.
import truststore

truststore.inject_into_ssl()

import requests
from dotenv import load_dotenv

load_dotenv()

# The entire difference between providers, in one dict:
PROVIDERS = {
    "ollama": {
        "url": "http://localhost:11434/v1/chat/completions",
        "key": "ollama",  # Ollama ignores auth, but the header must exist
        "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY", ""),
        # flash-lite is the cheapest; plenty for a hello-world.
        "model": "gemini-2.5-flash-lite",
    },
}

choice = sys.argv[1] if len(sys.argv) > 1 else "ollama"
provider = PROVIDERS[choice]

if choice == "gemini" and provider["key"] in ("", "paste-your-key-here"):
    sys.exit("No GEMINI_API_KEY in .env — copy .env.example to .env and paste your key.")

print(f"=== provider: {choice} | model: {provider['model']} ===")

resp = requests.post(
    provider["url"],
    # The Authorization header is the standard OpenAI-style auth. Note that
    # NOTHING else below changes between a local 3B model and Google's cloud.
    headers={"Authorization": f"Bearer {provider['key']}"},
    json={
        "model": provider["model"],
        "messages": [
            {"role": "user", "content": "Reply with exactly: harness says hello"}
        ],
        "max_tokens": 4000,
        "temperature": 0,
    },
    timeout=120,
)
resp.raise_for_status()
data = resp.json()

print(f"reply : {data['choices'][0]['message']['content']!r}")
print(f"usage : {json.dumps(data.get('usage'))}")
# ^ Compare `usage` across providers: same request, same accounting concepts.
#   Token counts differ slightly because each model family tokenizes text
#   differently — tokens are a property of the model, not of the text.
