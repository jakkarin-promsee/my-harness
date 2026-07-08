"""A minimal MCP server for the offline suite (not a test).

Speaks the real wire — newline-delimited JSON-RPC 2.0 over stdio — so
test_mcp.py can drive harness.tools.mcp against a genuine subprocess with
zero network and zero tokens. Three tools: echo (happy path), boom
(isError), sleepy (blocks — the timeout path). `--banner` prints a junk
line to stdout first, proving the client skips non-JSON lines. Pagination
is real too: tools/list returns two pages joined by nextCursor.
"""

import json
import sys
import time

TOOLS = [
    {
        "name": "echo",
        "description": "Echo the text back.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "boom",
        "description": "Always fails.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sleepy",
        "description": "Sleeps past any short timeout.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def reply(rid, result):
    print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}), flush=True)


def main():
    if "--banner" in sys.argv:
        print("fake-mcp-server starting up...", flush=True)  # junk line on stdout
    print("log: fake server alive", file=sys.stderr, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        if "id" not in msg:
            continue  # a notification (notifications/initialized) — no reply
        method = msg.get("method")
        if method == "initialize":
            reply(msg["id"], {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake", "version": "0"},
            })
        elif method == "tools/list":
            if msg.get("params", {}).get("cursor") == "page2":
                reply(msg["id"], {"tools": [TOOLS[2]]})
            else:
                reply(msg["id"], {"tools": TOOLS[:2], "nextCursor": "page2"})
        elif method == "tools/call":
            name = msg["params"]["name"]
            if name == "echo":
                text = "echo: " + msg["params"]["arguments"]["text"]
                reply(msg["id"], {"content": [{"type": "text", "text": text}]})
            elif name == "boom":
                reply(msg["id"], {
                    "content": [{"type": "text", "text": "it broke"}],
                    "isError": True,
                })
            elif name == "sleepy":
                time.sleep(2)
                reply(msg["id"], {"content": [{"type": "text", "text": "woke up"}]})
        else:
            print(json.dumps({
                "jsonrpc": "2.0", "id": msg["id"],
                "error": {"code": -32601, "message": f"unknown method {method!r}"},
            }), flush=True)


if __name__ == "__main__":
    main()
