"""Lab 00 — one raw HTTP call to a chat-completion API. No SDK, no loop.

Goal: see with your own eyes that "talking to an LLM" is one HTTP POST
with a JSON body, and one JSON response back. That's the whole secret.

Run:  uv run python labs/00_raw_call.py
Needs: Ollama running locally with the model from OLLAMA_MODEL pulled.
"""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()  # reads .env so OLLAMA_MODEL can be configured without editing code

# Ollama exposes an *OpenAI-compatible* endpoint at /v1. This exact URL shape
# (/v1/chat/completions) is spoken by OpenAI, Ollama, Gemini, OpenRouter, vLLM...
# — which is why swapping providers later is almost free (see lab 02).
URL = "http://localhost:11434/v1/chat/completions"
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# ---- THE REQUEST ------------------------------------------------------------
# This dict is *everything* the model receives. There is no hidden state on the
# server between calls: the "conversation" only exists because WE keep this
# `messages` list and send the whole thing every time. Remember this — it is
# the reason context management (our Pain #1) is even a thing.
request_body = {
    # Which model to run. For Ollama this is the local model tag.
    "model": MODEL,
    # The conversation so far, oldest first. Each message has:
    #   role:    "system" (instructions), "user" (human), "assistant" (model),
    #            or "tool" (a tool result — see lab 01)
    #   content: the text
    "messages": [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "In one sentence: what is an agent harness?"},
    ],
    # Cap on how many tokens the model may *generate* (not the input size).
    "max_tokens": 200,
    # 0 = as deterministic as possible. Nice for reproducible labs.
    "temperature": 0,
}

print("=== REQUEST BODY (what we send) ===")
print(json.dumps(request_body, indent=2))

resp = requests.post(URL, json=request_body, timeout=120)
resp.raise_for_status()
data = resp.json()

print("\n=== RESPONSE BODY (what comes back) ===")
print(json.dumps(data, indent=2))

# ---- THE RESPONSE, FIELD BY FIELD -------------------------------------------
# choices        : list of alternative completions; in practice always length 1.
# choices[0].message
#                : an assistant message — SAME SHAPE as the ones we sent.
#                  A harness appends this dict to `messages` and calls again.
# choices[0].finish_reason
#                : WHY generation stopped. The three you'll meet:
#                    "stop"       = model finished talking (turn is over)
#                    "length"     = hit max_tokens (answer is cut off!)
#                    "tool_calls" = model wants to run a tool (lab 01 →)
#                  The agent loop is literally a switch on this field.
# usage          : token accounting for THIS call.
#                    prompt_tokens     = size of everything we sent
#                    completion_tokens = size of what the model generated
#                  Watch prompt_tokens grow call after call — that growth IS
#                  the context-economics problem this whole project is about.
msg = data["choices"][0]["message"]
print("\n=== THE PARTS A HARNESS ACTUALLY USES ===")
print(f"finish_reason : {data['choices'][0]['finish_reason']}")
print(f"assistant says: {msg['content']}")
print(f"usage         : {data.get('usage')}")
