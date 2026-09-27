"""Contracts for the documented agent-to-engine command surface."""

from __future__ import annotations

import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hollowstar.host import HSRHost


def test_documented_commands_start_save_and_project_a_run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        host = HSRHost.from_options(data_root=Path(temp) / ".local")
        started = host.handle({
            "id": "start",
            "command": "start-run",
            "mode": "DESIGN",
            "run_id": "command-surface",
            "party": ["Doran"],
            "opposition": ["Townsperson"],
            "seed": "command-surface",
        })
        assert started["ok"], started

        saved = host.handle({"id": "save", "command": "save-run", "run_id": "command-surface"})
        assert saved["ok"], saved

        inventory = host.handle({
            "id": "inventory",
            "command": "show-temporary-inventory",
            "run_id": "command-surface",
        })
        assert inventory["ok"], inventory
        assert "temporary_inventory" in inventory["result"]["readout"]


def test_capabilities_publish_documented_commands() -> None:
    host = HSRHost.from_options()
    response = host.handle({"id": "capabilities", "command": "inspect"})
    commands = response["result"]["capabilities"]["commands"]
    assert {
        "start-run",
        "observe",
        "submit-action",
        "resolve-round",
        "test-perception",
        "reveal-room-record",
        "show-temporary-inventory",
        "sanctum-check-in",
        "save-run",
        "create-forge-receipt",
    } <= set(commands)


if __name__ == "__main__":
    for name in sorted(globals()):
        if name.startswith("test_"):
            globals()[name]()
    print("agent command surface tests passed")
