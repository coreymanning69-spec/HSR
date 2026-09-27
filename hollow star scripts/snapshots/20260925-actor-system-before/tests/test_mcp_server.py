"""HSR MCP server framing tests; runnable without pytest.

These exercise the JSON-RPC/MCP framing (initialize, tools/list, tools/call,
error paths) by spawning hsr_mcp_server.py as a real subprocess -- the same
way an MCP client would talk to it. They do not, and cannot, prove the
location gate passes: that only happens once this runs natively on the real
desktop path (see hsr_mcp_server.py's own docstring). Run from this
surface, `local_location.approved` is expected to be False; these tests
assert framing correctness, not gate approval.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import hsr_mcp_server as mcp

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "hsr_mcp_server.py"


def _roundtrip(messages: list[dict]) -> list[dict]:
    input_text = "\n".join(json.dumps(m) for m in messages) + "\n"
    proc = subprocess.run(
        [sys.executable, str(SERVER)],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=20,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, f"server exited {proc.returncode}; stderr={proc.stderr!r}"
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def _tool_payload(rpc_result: dict) -> dict:
    text = rpc_result["result"]["content"][0]["text"]
    return json.loads(text)


def test_initialize_handshake() -> None:
    responses = _roundtrip([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    ])
    assert len(responses) == 1
    result = responses[0]["result"]
    assert result["serverInfo"]["name"] == "hollow-star-reliquary"
    assert result["protocolVersion"] == "2024-11-05"
    assert "tools" in result["capabilities"]


def test_tools_list_covers_the_documented_surface() -> None:
    responses = _roundtrip([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])
    names = {t["name"] for t in responses[0]["result"]["tools"]}
    expected = {
        "hsr_health", "hsr_boot", "hsr_validate", "hsr_design_turn", "hsr_readout",
        "hsr_validation_start", "hsr_validation_status", "hsr_validation_result",
        "hsr_command",
    }
    assert expected.issubset(names)

    design_turn = next(tool for tool in mcp.TOOLS if tool["name"] == "hsr_design_turn")
    assert design_turn["inputSchema"]["required"] == ["run_id", "intent"]
    assert design_turn["inputSchema"]["properties"]["public_only"]["type"] == "boolean"
    readout = next(tool for tool in mcp.TOOLS if tool["name"] == "hsr_readout")
    assert "identity" in readout["inputSchema"]["properties"]
    assert readout["inputSchema"]["properties"]["public_only"]["type"] == "boolean"
    for tool in responses[0]["result"]["tools"]:
        assert "inputSchema" in tool and tool["inputSchema"]["type"] == "object"


def test_hsr_health_always_answers_ok() -> None:
    responses = _roundtrip([
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "hsr_health", "arguments": {}}},
    ])
    payload = _tool_payload(responses[0])
    assert payload["ok"] is True
    assert "local_location" in payload["result"]
    assert not responses[0]["result"]["isError"]


def test_hsr_command_passthrough_reaches_inspect() -> None:
    responses = _roundtrip([
        {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "hsr_command", "arguments": {"command": "inspect", "params": {"target": "capabilities"}}},
        },
    ])
    payload = _tool_payload(responses[0])
    assert payload["ok"] is True
    assert "health" in payload["result"]["capabilities"]["commands"]


def test_unknown_tool_is_a_json_rpc_invalid_params_error() -> None:
    responses = _roundtrip([
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "not_a_real_tool", "arguments": {}}},
    ])
    assert responses[0]["error"]["code"] == -32602


def test_malformed_line_does_not_kill_the_process() -> None:
    input_text = "not json at all\n" + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
    proc = subprocess.run(
        [sys.executable, str(SERVER)], input=input_text, capture_output=True, text=True, timeout=20, cwd=str(ROOT),
    )
    assert proc.returncode == 0
    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert lines == [{"jsonrpc": "2.0", "id": 1, "result": {}}]


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    main()
