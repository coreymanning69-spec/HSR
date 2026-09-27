import json
import tempfile
from pathlib import Path

import hsr_mcp_server
from hollowstar.cli import _parser
from hollowstar.host import HSRHost
from hollowstar.transfer import capsule


def test_cli_mcp_and_host_share_the_public_readout_contract():
    with tempfile.TemporaryDirectory(prefix="hsr-contract-") as temp:
        host = HSRHost.from_options(data_root=Path(temp) / ".local")
        assert host.handle({"id": "boot", "command": "boot", "mode": "DESIGN"})["ok"]
        created = host.handle({
            "id": "create", "command": "create_run", "run_id": "contract-run",
            "seed": "contract-seed", "party": ["divine:Doran"], "opposition": ["Townsperson"],
        })
        assert created["ok"]
        started = host.handle({"id": "start", "command": "design_start", "run_id": "contract-run"})
        assert started["ok"]
        readout = host.handle({
            "id": "read", "command": "readout", "run_id": "contract-run", "identity": "divine:Doran",
            "public_only": False,
        })
        assert readout["ok"]
        public = readout["result"]["readout"]["public_view"]
        assert public["schema"] == "hollow-star-public-view-1"
        assert {"room", "party", "opposition", "progression", "available_actions"} <= set(public)
        assert public["run_id"] == "contract-run"
        assert public["room"]["id"] == "1:1"
        assert public["room"]["resident"] == "Wellkeeper"
        compact = host.handle({
            "id": "compact", "command": "readout", "run_id": "contract-run",
            "identity": "divine:Doran", "public_only": True,
        })
        assert compact["ok"]
        compact_readout = compact["result"]["readout"]
        assert "visible_state" not in compact_readout
        assert compact_readout["public_view"] == public
        assert len(json.dumps(compact)) <= len(json.dumps(readout)) * .65
        transfer = capsule(readout, request={"id": "read", "command": "readout", "run_id": "contract-run"})
        assert transfer["view"] == public

    mcp_readout = next(tool for tool in hsr_mcp_server.TOOLS if tool["name"] == "hsr_readout")
    assert mcp_readout["command"] == "readout"
    assert "identity" in mcp_readout["inputSchema"]["properties"]
    assert "public_only" in mcp_readout["inputSchema"]["properties"]
    mcp_turn = next(tool for tool in hsr_mcp_server.TOOLS if tool["name"] == "hsr_design_turn")
    assert "public_only" in mcp_turn["inputSchema"]["properties"]

    cli_args = _parser().parse_args(["readout", "--run-id", "contract-run", "--identity", "divine:Doran"])
    assert cli_args.command == "readout"
    assert cli_args.identity == "divine:Doran"
    compact_cli = _parser().parse_args(["readout", "--run-id", "contract-run", "--public-only"])
    assert compact_cli.public_only is True
