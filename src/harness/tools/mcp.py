"""MCP client — the infinite tool bus, round one (2.16, note 33).

Speaks the Model Context Protocol over its stdio transport: newline-delimited
JSON-RPC 2.0 on a child process's stdin/stdout. The slice is deliberately
minimal (ROADMAP2 §4): initialize handshake -> tools/list -> merge the tools
into our registry (namespaced mcp__<server>__<tool>) -> tools/call dispatch.
No resources, no prompts, no HTTP transport, no server-initiated requests.

Servers come from harness.toml ([mcp.servers.<name>]: command/args/env/
timeout/enabled — Codex CLI's TOML shape). Permissions need zero new code:
the namespaced names fall into each mode's `default` bucket (ask in build and
auto, deny in explore), fail-closed exactly as 2.8 built it.

The reader-thread design: blocking readline-with-timeout doesn't exist on
Windows pipes, so one daemon thread drains stdout into a Queue and _request()
waits on the queue for its reply id. stderr drains into a small deque, shown
only when a server fails — server logs never pollute the REPL, but the tail
is there when debug-live needs it.

Invariant 3 holds at the boundary: every failure a TOOL CALL can hit — dead
server, timeout, isError, malformed reply — returns ERROR text the model can
read and adapt to. Startup failures degrade to a warning; the harness runs on
without the server.
"""

import json
import os
import re
import shutil
import subprocess
import threading
import time
import tomllib
from collections import deque
from pathlib import Path
from queue import Empty, Queue

PROTOCOL_VERSION = "2025-06-18"  # the stable revision the 2026-07-28 RC builds on
CALL_TIMEOUT = 30       # seconds per request, like web_fetch's WEB_TIMEOUT
DESC_MAX_CHARS = 800    # a runaway description would eat the local 8K window
NAME_MAX = 64           # Gemini's (and Anthropic's) function-name ceiling


class MCPServer:
    """One child process speaking MCP over stdio. start() spawns and
    handshakes (raises RuntimeError with a readable reason); call_tool()
    never raises — failures become ERROR text (invariant 3)."""

    def __init__(self, name: str, command: str, args: list | None = None,
                 env: dict | None = None, timeout: float = CALL_TIMEOUT):
        self.name = name
        self.command = command
        self.args = list(args or ())
        self.env = env or {}
        self.timeout = timeout
        self.proc = None
        self.tool_names: list[str] = []  # filled by connect(); /mcp reads it
        self._queue: Queue = Queue()
        self._stderr_tail: deque = deque(maxlen=10)
        self._next_id = 0

    # ---- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        exe = shutil.which(self.command)
        if exe is None:
            raise RuntimeError(f"command {self.command!r} not found on PATH")
        argv = [exe, *self.args]
        # CreateProcess can't execute batch files directly — the classic
        # Windows paper cut for npx-class servers. Wrap once, here.
        if exe.lower().endswith((".cmd", ".bat")):
            argv = ["cmd", "/c", exe, *self.args]
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, **{k: str(v) for k, v in self.env.items()}},
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        threading.Thread(target=self._drain_stdout, daemon=True).start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "researcher-harness", "version": "0.1"},
        })
        self._notify("notifications/initialized")

    def stop(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            return
        try:
            self.proc.stdin.close()  # stdio servers exit on stdin EOF
        except OSError:
            pass
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def stderr_tail(self) -> str:
        return "\n".join(self._stderr_tail)

    # ---- the wire ----------------------------------------------------------

    def _drain_stdout(self) -> None:
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._queue.put(json.loads(line))
            except json.JSONDecodeError:
                continue  # startup banners on stdout happen — skip, don't die
        self._queue.put(None)  # EOF sentinel: the server went away

    def _drain_stderr(self) -> None:
        for line in self.proc.stderr:
            self._stderr_tail.append(line.rstrip())

    def _send(self, msg: dict) -> None:
        if self.proc is None or self.proc.poll() is not None:
            raise RuntimeError(f"server {self.name!r} is not running")
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})

    def _request(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        rid = self._next_id
        msg = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"{method} timed out after {self.timeout}s")
            try:
                reply = self._queue.get(timeout=remaining)
            except Empty:
                raise TimeoutError(f"{method} timed out after {self.timeout}s")
            if reply is None:
                raise RuntimeError(f"server {self.name!r} closed its stdout")
            if reply.get("id") != rid:
                # A notification, or a server-initiated request — round one
                # answers nothing and waits for its own reply.
                continue
            if "error" in reply:
                err = reply["error"]
                raise RuntimeError(f"{method} error {err.get('code')}: {err.get('message')}")
            return reply.get("result", {})

    # ---- the two protocol calls we speak ------------------------------------

    def list_tools(self) -> list[dict]:
        tools, cursor = [], None
        while True:
            result = self._request("tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                return tools

    def call_tool(self, tool: str, arguments: dict) -> str:
        """-> framed text (2.21a house style), ERROR text on any failure."""
        try:
            result = self._request("tools/call", {"name": tool, "arguments": arguments})
        except (RuntimeError, TimeoutError, OSError) as e:
            return f"ERROR: mcp:{self.name} {tool}: {e}"
        parts = []
        for item in result.get("content", []):
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
            else:
                parts.append(f"[non-text content: {item.get('type', '?')}]")
        text = "\n".join(parts).strip() or "(empty result)"
        if result.get("isError"):
            return f"ERROR: mcp:{self.name} {tool}: {text}"
        return f"[mcp:{self.name}] {tool} - {len(text)} chars\n{text}"


# ---- namespacing + schema conversion (pure — unit-testable without a proc) --

def sanitize(name: str) -> str:
    """Legal on every wire we speak: [a-zA-Z0-9_-] only."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def tool_name(server: str, tool: str) -> str:
    return f"mcp__{sanitize(server)}__{sanitize(tool)}"


def make_schema(server: str, tool: dict) -> dict | None:
    """MCP tool advertisement -> our function-call schema shape. None when
    the namespaced name would exceed the wire's 64-char ceiling (skip it —
    a warning at connect time beats a 400 from the provider)."""
    name = tool_name(server, tool.get("name", ""))
    if len(name) > NAME_MAX:
        return None
    desc = (tool.get("description") or "").strip()
    if len(desc) > DESC_MAX_CHARS:
        desc = desc[:DESC_MAX_CHARS] + "..."
    params = dict(tool.get("inputSchema") or {"type": "object", "properties": {}})
    params.pop("$schema", None)  # metadata some servers emit; providers may 400 on it
    return {
        "type": "function",
        "function": {"name": name, "description": desc, "parameters": params},
    }


def _make_caller(server: MCPServer, tool: str):
    """A closure per tool. NOT a default-arg lambda: a tool whose own
    parameter is named 'server' or 'tool' would shadow the defaults —
    here every model argument lands safely in **arguments."""
    def call(**arguments) -> str:
        return server.call_tool(tool, arguments)
    return call


# ---- config + connect --------------------------------------------------------

def load_config(path: str = "harness.toml") -> dict[str, dict]:
    """[mcp.servers.<name>] sections, minus the enabled=false ones."""
    fp = Path(path)
    if not fp.exists():
        return {}
    with open(fp, "rb") as f:
        data = tomllib.load(f)
    servers = data.get("mcp", {}).get("servers", {})
    return {name: cfg for name, cfg in servers.items() if cfg.get("enabled", True)}


def connect(config: dict[str, dict], emit=print):
    """Start every configured server; return (registry, schemas, servers).
    A server that fails to start is a warning plus its stderr tail, never a
    crash — the harness runs on without it."""
    registry: dict = {}
    schemas: list = []
    servers: list[MCPServer] = []
    for name, cfg in config.items():
        server = MCPServer(
            name,
            command=cfg.get("command", ""),
            args=cfg.get("args", []),
            env=cfg.get("env", {}),
            timeout=cfg.get("timeout", CALL_TIMEOUT),
        )
        try:
            server.start()
            tools = server.list_tools()
        except (RuntimeError, TimeoutError, OSError) as e:
            emit(f"  [!] mcp server {name!r} failed: {e}")
            tail = server.stderr_tail()
            if tail:
                emit("      " + tail.replace("\n", "\n      "))
            server.stop()
            continue
        for tool in tools:
            schema = make_schema(name, tool)
            if schema is None:
                emit(f"  [!] mcp:{name} tool {tool.get('name')!r} skipped (name too long)")
                continue
            ns_name = schema["function"]["name"]
            registry[ns_name] = _make_caller(server, tool.get("name", ""))
            schemas.append(schema)
            server.tool_names.append(ns_name)
        servers.append(server)
        emit(f"  mcp: {name} - {len(server.tool_names)} tools "
             f"({', '.join(server.tool_names)})")
    return registry, schemas, servers
