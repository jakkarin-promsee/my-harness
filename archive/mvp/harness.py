"""mvp/harness.py — the smallest real harness: labs 00-02 plus a while-loop.

This file IS the project's thesis made runnable: a harness is a messages
list, a loop around /v1/chat/completions, a tool table, and bookkeeping.
Structure copied from Thorsten Ball's tutorial agent and mini-swe-agent's
DefaultAgent (see docs/notes/01-mvp.md for what was taken from where).

Run:
    uv run python mvp/harness.py             # local Ollama (free)
    uv run python mvp/harness.py gemini      # Gemini flash-lite (uses $ credit)
    uv run python mvp/harness.py -y          # auto-approve gate (scripted runs)

Type a task at the `you>` prompt. `exit` quits.
Stage-1 scope on purpose: 4 tools, y/N gate, token meter. Nothing else.
"""

import json
import os
import subprocess
import sys

import truststore

truststore.inject_into_ssl()  # this machine has TLS interception (see labs/02)

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------- providers --
# Same three-string swap as labs/02: url + key + model IS the provider layer
# at this stage. Stage 2.1 grows this dict into a real adapter.
PROVIDERS = {
    "ollama": {
        "url": "http://localhost:11434/v1/chat/completions",
        "key": "ollama",  # Ollama ignores auth, but the header must exist
        "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "model": "gemini-2.5-flash-lite",
    },
}

_args = sys.argv[1:]
AUTO_APPROVE = "-y" in _args  # scripted acceptance runs only (aider --yes, mini-swe -y)
_provider_name = next((a for a in _args if not a.startswith("-")), "ollama")
PROVIDER = PROVIDERS[_provider_name]

MAX_STEPS = 20  # a loop that cannot stop is a token furnace (mini-swe-agent lesson)
MAX_TOOL_CHARS = 2000  # crude truncation for huge output; Stage 3.1 replaces this
                       # with dump-to-file (truncation loses data, dumping doesn't)

# -------------------------------------------------------------------- tools --
# A tool = a plain local function (what actually runs) + a JSON-schema advert
# (all the model ever sees). The model cannot execute anything — it *asks* by
# replying with tool_calls; WE run the function and mail the result back.


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"wrote {len(content)} chars to {path}"


def list_dir(path: str) -> str:
    return json.dumps(sorted(os.listdir(path)))


def run_shell(command: str) -> str:
    # shell=True on Windows means cmd.exe. The timeout is load-bearing:
    # without it, one hung command hangs the whole agent turn forever.
    proc = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=60
    )
    return f"exit code: {proc.returncode}\n{proc.stdout or ''}{proc.stderr or ''}"


REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
    "list_dir": list_dir,
    "run_shell": run_shell,
}

NEEDS_PERMISSION = {"write_file", "run_shell"}  # mutating tools get the y/N gate


def _schema(name: str, desc: str, props: dict, required: list) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


# Tool descriptions matter more than they look: they are the ONLY signal the
# model has for choosing tools (the SWE-agent "ACI" lesson — Stage 2.2 topic).
TOOLS = [
    _schema(
        "read_file",
        "Read a text file and return its full contents.",
        {"path": {"type": "string", "description": "File path, relative to the working directory."}},
        ["path"],
    ),
    _schema(
        "write_file",
        "Create or overwrite a text file with the given content.",
        {
            "path": {"type": "string", "description": "File path to write."},
            "content": {"type": "string", "description": "The full file content."},
        },
        ["path", "content"],
    ),
    _schema(
        "list_dir",
        "List the names of all files and folders in a directory.",
        {"path": {"type": "string", "description": "Directory path, e.g. '.' for the current one."}},
        ["path"],
    ),
    _schema(
        "run_shell",
        "Run a shell command (Windows cmd.exe) and return its exit code and output.",
        {"command": {"type": "string", "description": "The command line to run."}},
        ["command"],
    ),
]

# ------------------------------------------------------------- system prompt --
# Organ #5. Real harnesses put thousands of tokens here; the MVP needs three
# rules and the working directory.
SYSTEM_PROMPT = f"""You are a coding agent running in a terminal on Windows.
Working directory: {os.getcwd()}

Rules:
- Use the tools to inspect and change files; never guess file contents.
- Run Python files with: uv run python <path>
- Keep answers short. When the task is done, state the result plainly."""

# --------------------------------------------------------------- token meter --
# Non-negotiable from day 1: this project exists because of token economics.
# Watch `prompt_tokens` climb call after call — that is Pain #1, measured live.
session_in = session_out = 0


def print_usage(usage: dict | None) -> None:
    global session_in, session_out
    if not usage:
        return
    p = usage.get("prompt_tokens", 0)
    c = usage.get("completion_tokens", 0)
    session_in += p
    session_out += c
    print(f"  [tokens] call: {p:,} in / {c:,} out | session: {session_in:,} in / {session_out:,} out")


# ------------------------------------------------------------ provider client --
def call_model(messages: list) -> dict:
    # One retry on 5xx: cloud endpoints throw transient 503s under load
    # (measured live on Gemini flash-lite mid-acceptance-run). A 4xx is OUR
    # bug and must not be retried — same request, same rejection.
    for attempt in range(1, 6):
        resp = requests.post(
            PROVIDER["url"],
            headers={"Authorization": f"Bearer {PROVIDER['key']}"},
            json={
                "model": PROVIDER["model"],
                "messages": messages,
                "tools": TOOLS,
                # No temperature override: qwen3 + temperature 0 (greedy
                # decoding) spirals into infinite repetition while "thinking"
                # — measured live as a 600s timeout. Models ship tuned
                # defaults; trust them. max_tokens is the runaway-GENERATION
                # guard (MAX_STEPS guards the loop; this guards one call) —
                # overruns end as finish_reason "length".
                "max_tokens": 2000,
            },
            # Generous: a 4B model thinking hard on a 4 GB laptop GPU can
            # legitimately take minutes per call (measured: 300s wasn't enough).
            timeout=600,
        )
        if resp.status_code >= 500 and attempt == 1:
            print(f"  [!] {resp.status_code} from provider - retrying once...")
            continue
        resp.raise_for_status()
        return resp.json()


# ------------------------------------------------------------ permission gate --
def approved(name: str, arguments: dict) -> bool:
    """First taste of the permission layer every serious harness has."""
    if AUTO_APPROVE:
        return True
    preview = json.dumps(arguments)
    if len(preview) > 200:
        preview = preview[:200] + "..."
    try:
        answer = input(f"  allow {name}({preview})? [y/N] ")
    except EOFError:  # stdin closed (piped input ran out) -> safest answer is no
        return False
    return answer.strip().lower() == "y"


def run_tool(name: str, arguments: dict) -> str:
    if name not in REGISTRY:
        return f"ERROR: unknown tool {name!r}"
    if name in NEEDS_PERMISSION and not approved(name, arguments):
        return "User denied permission for this call."
    try:
        return REGISTRY[name](**arguments) or "(empty output)"
    except TypeError as e:
        return f"ERROR: bad arguments: {e}"  # model invented/omitted a parameter
    except Exception as e:
        # Tool failures go back to the MODEL as text, not to the user as a
        # crash — the model can read the error and try something else.
        return f"ERROR: {type(e).__name__}: {e}"


# ------------------------------------------------------------------- the loop --
def agent_turn(messages: list) -> None:
    """One user request -> the model chains tool calls -> final text answer.

    This is lab 01's five-step dance wrapped in a bounded while-loop.
    """
    for _ in range(MAX_STEPS):
        data = call_model(messages)
        choice = data["choices"][0]
        msg = choice["message"]
        print_usage(data.get("usage"))
        # The model's move — text OR tool request — is part of the
        # conversation. Forgetting this append breaks the next call (lab 01).
        messages.append(msg)

        if choice["finish_reason"] == "length":
            # ASCII only in runtime messages: piped Windows consoles mangle non-ASCII
            print("  [!] reply was cut off by the token limit - stopping this turn")
            return

        # Presence of tool_calls, not finish_reason, is the robust signal:
        # some Ollama models say "stop" while still carrying tool calls.
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            print(f"\nagent> {msg.get('content') or '(no text)'}")
            return

        for call in tool_calls:
            name = call["function"]["name"]
            try:
                # Classic gotcha: arguments arrive as a JSON *string*.
                arguments = json.loads(call["function"]["arguments"])
                result = run_tool(name, arguments)
            except json.JSONDecodeError as e:
                result = f"ERROR: arguments were not valid JSON: {e}"
            if len(result) > MAX_TOOL_CHARS:
                result = result[:MAX_TOOL_CHARS] + f"\n[truncated {len(result) - MAX_TOOL_CHARS} chars]"
            first_line = result.splitlines()[0] if result else ""
            print(f"  [tool] {name} -> {first_line[:80]}")
            # tool_call_id echoes the model's id so results match requests.
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    print(f"  [!] hit MAX_STEPS={MAX_STEPS} - stopping this turn (runaway guard)")


# ------------------------------------------------------------------ the REPL --
def main() -> None:
    print(f"researcher-harness MVP | provider: {_provider_name} | model: {PROVIDER['model']}")
    print("type a task, 'exit' to quit")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        try:
            user = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() in {"exit", "quit"}:
            break
        if not user:
            continue
        messages.append({"role": "user", "content": user})
        try:
            agent_turn(messages)
        except requests.RequestException as e:
            print(f"  [!] API error: {e}")
    print(f"\nsession total: {session_in:,} in / {session_out:,} out tokens")


if __name__ == "__main__":
    main()
