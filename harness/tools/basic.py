"""The four Stage-1 tools: implementation + JSON-schema advertisement.

A tool = a plain local function (what actually runs) + a schema (all the
model ever sees). The model cannot execute anything — it *asks* by replying
with tool_calls; the loop runs the function and mails the result back.

Tool descriptions matter more than they look: they are the ONLY signal the
model has for choosing tools (the SWE-agent "ACI" lesson — Stage 2.2 topic).
"""

import json
import os
import subprocess


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


SCHEMAS = [
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
