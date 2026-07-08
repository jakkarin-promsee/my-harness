"""The MCP client (2.16, note 33): protocol against a real subprocess
(tests/fake_mcp_server.py — real wire, zero network), pure functions
without one, and the loop dispatching a namespaced tool like any other.
These are the slowest tests in the suite (each server is a spawned
Python interpreter) — the module-scoped fixture keeps it to one spawn."""

import sys
from pathlib import Path

import pytest

from harness.core.loop import Agent
from harness.tools import mcp

from fakes import FakeModel, text_reply, tool_reply

FAKE_SERVER = str(Path(__file__).parent / "fake_mcp_server.py")
FAKE_CONFIG = {"command": sys.executable, "args": [FAKE_SERVER, "--banner"]}


@pytest.fixture(scope="module")
def server():
    s = mcp.MCPServer("fake", sys.executable, [FAKE_SERVER, "--banner"])
    s.start()  # succeeding despite --banner proves junk stdout lines are skipped
    yield s
    s.stop()


# ---- the wire, against a real subprocess -----------------------------------

def test_handshake_and_paginated_list(server):
    tools = server.list_tools()
    assert [t["name"] for t in tools] == ["echo", "boom", "sleepy"]  # page2 followed


def test_call_returns_framed_text(server):
    result = server.call_tool("echo", {"text": "hi"})
    lines = result.splitlines()
    assert lines[0].startswith("[mcp:fake] echo - ")
    assert lines[1] == "echo: hi"


def test_iserror_becomes_error_text(server):
    result = server.call_tool("boom", {})
    assert result.startswith("ERROR: mcp:fake boom:")
    assert "it broke" in result


def test_jsonrpc_error_raises_readably(server):
    # The fake answers unknown methods with a JSON-RPC error object; _request
    # must surface code and message (call_tool turns this into ERROR text).
    with pytest.raises(RuntimeError, match="-32601"):
        server._request("bogus/method")


def test_timeout_is_error_text():
    s = mcp.MCPServer("slow", sys.executable, [FAKE_SERVER], timeout=0.5)
    s.start()
    try:
        result = s.call_tool("sleepy", {})
        assert result.startswith("ERROR: mcp:slow sleepy:")
        assert "timed out" in result
    finally:
        s.stop()


def test_dead_command_degrades_to_warning():
    emitted = []
    registry, schemas, servers = mcp.connect(
        {"ghost": {"command": "definitely-not-a-real-command-xyz"}},
        emit=emitted.append,
    )
    assert registry == {} and schemas == [] and servers == []
    assert any("ghost" in line and "failed" in line for line in emitted)


def test_connect_merges_and_lists():
    emitted = []
    registry, schemas, servers = mcp.connect({"fake": FAKE_CONFIG}, emit=emitted.append)
    try:
        names = ["mcp__fake__echo", "mcp__fake__boom", "mcp__fake__sleepy"]
        assert list(registry) == names
        assert [s["function"]["name"] for s in schemas] == names
        assert servers[0].tool_names == names
        assert "echo: ping" in registry["mcp__fake__echo"](text="ping")
        assert any("mcp: fake - 3 tools" in line for line in emitted)
    finally:
        for s in servers:
            s.stop()


# ---- pure functions (no subprocess) -----------------------------------------

def test_namespacing_sanitizes():
    assert mcp.tool_name("duck duck!", "search") == "mcp__duck_duck___search"
    assert mcp.tool_name("fake", "fetch-content") == "mcp__fake__fetch-content"


def test_schema_conversion_caps_and_cleans():
    tool = {
        "name": "search",
        "description": "x" * 1000,
        "inputSchema": {"$schema": "http://json-schema.org/draft-07/schema#",
                        "type": "object", "properties": {"q": {"type": "string"}}},
    }
    schema = mcp.make_schema("fake", tool)
    fn = schema["function"]
    assert fn["name"] == "mcp__fake__search"
    assert len(fn["description"]) == mcp.DESC_MAX_CHARS + 3  # capped + "..."
    assert "$schema" not in fn["parameters"]
    assert fn["parameters"]["properties"] == {"q": {"type": "string"}}


def test_schema_conversion_skips_overlong_names():
    assert mcp.make_schema("s" * 40, {"name": "t" * 40}) is None


def test_schema_conversion_defaults_missing_input_schema():
    schema = mcp.make_schema("fake", {"name": "bare"})
    assert schema["function"]["parameters"] == {"type": "object", "properties": {}}


def test_load_config_skips_disabled(tmp_path):
    toml = tmp_path / "harness.toml"
    toml.write_text(
        '[mcp.servers.on]\ncommand = "uvx"\nargs = ["x"]\n'
        '[mcp.servers.off]\ncommand = "uvx"\nenabled = false\n',
        encoding="utf-8",
    )
    cfg = mcp.load_config(str(toml))
    assert list(cfg) == ["on"]
    assert cfg["on"]["args"] == ["x"]


def test_load_config_missing_file(tmp_path):
    assert mcp.load_config(str(tmp_path / "nope.toml")) == {}


# ---- the loop treats a namespaced tool like any other ------------------------

def test_loop_dispatches_mcp_tool():
    calls = []

    def fake_search(**arguments):
        calls.append(arguments)
        return "[mcp:fake] search - 9 chars\nresult: 1"

    model = FakeModel([
        tool_reply(("c1", "mcp__fake__search", '{"query": "python"}')),
        text_reply("done"),
    ])
    messages = [{"role": "user", "content": "go"}]
    agent = Agent(model, {"mcp__fake__search": fake_search},
                  schemas=[], emit=lambda _: None)
    agent.run_turn(messages)
    assert calls == [{"query": "python"}]
    tool_msg = next(m for m in messages if m.get("role") == "tool")
    assert tool_msg["content"].startswith("[mcp:fake] search")
