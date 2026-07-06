"""Lab 01 — one full tool-call round trip, done BY HAND. Still no loop.

This is the lab that demystifies harnesses. The model cannot run anything —
it can only *ask* us to run something, by replying with a `tool_calls` field
instead of text. WE execute it, append the result as a message, and call again.

The dance (two HTTP calls total):

    call 1: messages + tool definitions  ->  model answers "run list_dir please"
    (we run list_dir ourselves, locally)
    call 2: messages + tool result       ->  model answers in plain text

A real harness just wraps this dance in `while finish_reason == "tool_calls"`.

Run:  uv run python labs/01_tool_roundtrip.py
"""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

URL = "http://localhost:11434/v1/chat/completions"
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


# ---- STEP 0: a tool is just a local function + a JSON advertisement ---------
def list_dir(path: str) -> str:
    """The actual implementation. The model NEVER sees this code."""
    return json.dumps(sorted(os.listdir(path)))


# What the model DOES see: a JSON-schema "advertisement" of the function.
# The model chooses tools purely from name/description/parameters — which is
# why tool descriptions matter so much in real harnesses (SWE-agent's lesson).
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the names of all files and folders in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path, e.g. '.' for the current one.",
                    }
                },
                "required": ["path"],
            },
        },
    }
]

messages = [
    {"role": "user", "content": "What files are in the current directory? Use the tool."}
]

# ---- STEP 1: send the question + the tool advertisements --------------------
print("=== CALL 1: question + tools ===")
resp = requests.post(
    URL,
    json={"model": MODEL, "messages": messages, "tools": TOOLS, "temperature": 0},
    timeout=120,
)
resp.raise_for_status()
data = resp.json()
assistant_msg = data["choices"][0]["message"]
print(json.dumps(assistant_msg, indent=2))
print(f"finish_reason: {data['choices'][0]['finish_reason']}")  # -> "tool_calls"

# The assistant message now has NO (or empty) content. Instead it carries:
#   tool_calls[0].id                 : an ID we must echo back later, so the
#                                      model can match results to requests
#                                      (there can be several calls at once!)
#   tool_calls[0].function.name      : which tool it wants
#   tool_calls[0].function.arguments : the args — as a JSON *STRING*, not an
#                                      object. Classic gotcha: json.loads() it.
tool_call = assistant_msg["tool_calls"][0]
args = json.loads(tool_call["function"]["arguments"])
print(f"\nmodel wants: {tool_call['function']['name']}({args})")

# ---- STEP 2: append the assistant message itself -----------------------------
# Easy-to-miss detail: the request-to-call-a-tool is part of the conversation.
# If you don't append it, call 2 makes no sense to the model.
messages.append(assistant_msg)

# ---- STEP 3: WE run the tool. The model just waits. --------------------------
result = list_dir(**args)
print(f"tool output: {result[:120]}...")

# ---- STEP 4: append the result as a role:"tool" message ----------------------
# tool_call_id echoes the ID from step 1 — that's how results get matched up.
messages.append(
    {"role": "tool", "tool_call_id": tool_call["id"], "content": result}
)

# ---- STEP 5: call again with the grown conversation --------------------------
print("\n=== CALL 2: same messages list, now with the tool result appended ===")
resp = requests.post(
    URL,
    json={"model": MODEL, "messages": messages, "tools": TOOLS, "temperature": 0},
    timeout=120,
)
resp.raise_for_status()
data = resp.json()
final_msg = data["choices"][0]["message"]
print(f"finish_reason: {data['choices'][0]['finish_reason']}")  # -> "stop"
print(f"\nfinal answer:\n{final_msg['content']}")

# ---- WHAT YOU JUST BUILT ------------------------------------------------------
# Congratulations: steps 1-5 are the ENTIRE mechanism behind every harness.
# Claude Code, Codex CLI, opencode — all of them are this dance plus:
#   - a while-loop around steps 1-5 (so the model can chain many tools)
#   - more tools (read_file, edit, bash, ...)
#   - a permission gate before step 3 (should we actually run this?)
#   - bookkeeping around `messages` (context management, sessions, ...)
# Stage 1 (the MVP) is exactly: this file + a while-loop + 4 tools + y/n gate.
