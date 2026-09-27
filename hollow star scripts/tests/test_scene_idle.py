"""Tests for the shared public scene and bounded Floor One idle contract."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.host import HSRHost
from hollowstar.run_service import RunService
from hollowstar.scene import build_scene, idle_pause


def _service():
    root = Path(tempfile.mkdtemp(prefix="hsr-scene-idle-"))
    service = RunService(root / ".local" / "reliquary_runs")
    service.create("scene", ["Doran"], ["Townsperson"], seed="scene-seed", scenario="floor_one_life")
    service.design_start("scene")
    return service, root


def test_floor_one_public_view_contains_side_scroll_scene() -> None:
    service, root = _service()
    try:
        state = service.observe("scene")
        scene = build_scene(state)
        assert scene["schema"] == "hollow-star-scene-1"
        assert scene["floor_id"] == "floor-1-town"
        assert scene["phase"] == "social"
        assert scene["direction"] == "right"
        assert 0 <= scene["progress"] <= 1
    finally:
        shutil.rmtree(root)


def test_idle_pauses_before_social_choice() -> None:
    service, root = _service()
    try:
        state = service.observe("scene")
        pause = idle_pause(state)
        assert pause and pause["code"] == "social_choice"
        result = service.idle_tick("scene", max_steps=8)
        assert result["event"]["type"] == "idle_paused"
        assert result["event"]["pause"]["code"] == "social_choice"
        assert result["event"]["steps"] == 0
    finally:
        shutil.rmtree(root)


def test_host_idle_tick_returns_public_view_and_receipt() -> None:
    root = Path(tempfile.mkdtemp(prefix="hsr-host-idle-"))
    try:
        host = HSRHost.from_options(data_root=root / ".local")
        assert host.handle({"id": "boot", "command": "boot", "mode": "DESIGN"})["ok"]
        assert host.handle({"id": "create", "command": "create_run", "run_id": "idle-host",
                            "seed": "idle-seed", "party": ["divine:Doran"],
                            "opposition": ["Townsperson"], "scenario": "floor_one_life"})["ok"]
        assert host.handle({"id": "start", "command": "design_start", "run_id": "idle-host"})["ok"]
        response = host.handle({"id": "idle", "command": "idle_tick", "run_id": "idle-host", "max_steps": 2})
        assert response["ok"]
        idle = response["result"]["idle"]
        assert idle["public_view"]["scene"]["schema"] == "hollow-star-scene-1"
        assert idle["public_receipt"]["type"] == "idle_paused"
    finally:
        shutil.rmtree(root)
