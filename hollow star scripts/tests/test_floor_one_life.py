"""Acceptance tests for the persistent Floor One life-simulation slice."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.intent import parse_intent  # noqa: E402
from hollowstar.host import HSRHost  # noqa: E402
from hollowstar.run_service import RunService  # noqa: E402


def _service(name: str = "life") -> tuple[RunService, Path]:
    root = Path(tempfile.mkdtemp(prefix="hsr-floor-one-life-"))
    service = RunService(root / ".local" / "reliquary_runs")
    service.create(name, ["Doran"], ["Townsperson"], seed="life-seed", scenario="floor_one_life")
    service.design_start(name)
    return service, root


def test_life_world_is_seeded_persistent_and_natural_language_is_bounded() -> None:
    service, root = _service()
    try:
        state = service.observe("life")
        assert state["schema"] == "hollow-star-floor-one-public-1"
        assert len(state["npcs"]) >= 1
        assert parse_intent("go to well", state) == {"type": "move", "destination": "well"}
        service.design_action("life", {"type": "move", "destination": "well"})
        service.design_action("life", {"type": "open", "object": "sealed-chest"})
        service.save("life")
        resumed = RunService(root / ".local" / "reliquary_runs")
        resumed.load("life")
        assert resumed.observe("life")["objects"]["sealed-chest"]["open"] is True
    finally:
        shutil.rmtree(root)


def test_public_murder_creates_body_witnesses_and_civic_alarm() -> None:
    service, root = _service()
    try:
        service.design_action("life", {"type": "move", "destination": "well"})
        world = service._active["life"].context["life_world"]
        world["residents"]["marta-vell"]["hp"] = 1
        result = service.design_action("life", {"type": "attack", "target": "Marta Vell"})
        state = result["state"]
        assert result["event"]["type"] == "resident_killed"
        assert state["civic_alarm"]["active"] is True
        assert any(body["resident_id"] == "marta-vell" for body in state["bodies"])
        assert any(row["disposition"] == "hostile"
                   for row in service._active["life"].context["life_world"]["residents"].values())
    finally:
        shutil.rmtree(root)


def test_tick_is_deterministic_and_intruder_party_arrives() -> None:
    first, root1 = _service("first")
    second, root2 = _service("second")
    try:
        first.design_action("first", {"type": "world_tick", "elapsed_seconds": 3600})
        second.design_action("second", {"type": "world_tick", "elapsed_seconds": 3600})
        one = first.design_action("first", {"type": "world_tick", "elapsed_seconds": 3600})["state"]
        two = second.design_action("second", {"type": "world_tick", "elapsed_seconds": 3600})["state"]
        assert one["world_time"] == two["world_time"]
        assert one["intruder_party"] == two["intruder_party"]
        assert one["intruder_party"]["status"] == "active"
    finally:
        shutil.rmtree(root1)
        shutil.rmtree(root2)


def test_child_resident_cannot_be_directly_attacked() -> None:
    service, root = _service()
    try:
        world = service._active["life"].context["life_world"]
        assert world["residents"]["wick"]["child"] is True
        world["residents"]["wick"]["location"] = world["player"]["location"]
        try:
            service.design_action("life", {"type": "attack", "target": "Wick"})
            raised = False
        except Exception as exc:  # noqa: BLE001 -- RunServiceError wraps LifeError
            raised = "child" in str(exc)
        assert raised, "attacking a child resident must be rejected, not resolved"
        assert world["residents"]["wick"]["alive"] is True
    finally:
        shutil.rmtree(root)


def test_merged_resident_population_carries_authored_social_metadata() -> None:
    service, root = _service()
    try:
        world = service._active["life"].context["life_world"]
        assert len(world["residents"]) == 18
        marta = world["residents"]["marta-vell"]
        assert marta["species"] == "human"
        assert marta["class"] == "townsfolk"
        assert marta["tier"] == "known"
        assert marta["traits"]
        assert marta["stances"]["bandit"] < 0
        assert marta["relationships"]
        assert marta["tier_scaling"]["power_class"] in {"civilian", "skilled", "armed"}
        # disposition is now seeded from disposition_base via reaction_bands
        # rather than a hardcoded default.
        assert marta["disposition"] in {"hostile", "wary", "neutral", "warm", "helpful"}
        # possessions are resolved once at world start from authored
        # candidates, and a fresh world with the same seed resolves identically.
        assert isinstance(marta["possessions"], list)
        second, root2 = _service("life-repeat")
        try:
            other_world = second._active["life-repeat"].context["life_world"]
            assert other_world["residents"]["marta-vell"]["possessions"] == marta["possessions"]
        finally:
            shutil.rmtree(root2)
    finally:
        shutil.rmtree(root)


def test_host_design_turn_returns_public_life_view() -> None:
    root = Path(tempfile.mkdtemp(prefix="hsr-floor-one-host-"))
    try:
        host = HSRHost.from_options(data_root=root / ".local")
        assert host.handle({"id": "boot", "command": "boot", "mode": "DESIGN"})["ok"]
        assert host.handle({"id": "create", "command": "create_run", "run_id": "life-host", "seed": "host-seed",
                            "party": ["divine:Doran"], "opposition": ["Townsperson"],
                            "scenario": "floor_one_life"})["ok"]
        assert host.handle({"id": "start", "command": "design_start", "run_id": "life-host"})["ok"]
        response = host.handle({"id": "turn", "command": "design_turn", "run_id": "life-host", "intent": "go to well"})
        assert response["ok"]
        assert response["result"]["turn"]["public_view"]["room"]["id"] == "well"
    finally:
        shutil.rmtree(root)


def test_exploration_intents_survey_the_life_hub() -> None:
    service, root = _service("survey")
    try:
        state = service.observe("survey")
        for text in ("search the room", "look around", "search", "look"):
            action = parse_intent(text, state)
            assert action["type"] in {"survey", "investigate", "observe_room"}, (text, action)
            result = service.design_action("survey", action, intent=text)
            receipt = result["event"]["receipt"]["public"]
            assert result["event"]["type"] == "area_surveyed"
            assert receipt["exits"] and "hint" in receipt
        for obj in ("square", "the-square", "area", "room"):
            result = service.design_action("survey", {"type": "inspect", "object": obj})
            assert result["event"]["type"] == "area_surveyed"
        assert any(row["type"] == "survey" for row in result["state"]["available_actions"])
    finally:
        shutil.rmtree(root)


def test_unknown_life_actions_explain_what_the_hub_supports() -> None:
    service, root = _service("unknown")
    try:
        for action, needle in (({"type": "dance"}, "the town supports"),
                               ({"type": "inspect", "object": "moon-rock"}, "visible objects")):
            try:
                service.design_action("unknown", action)
            except Exception as exc:  # noqa: BLE001 - service wraps LifeError
                assert needle in str(exc)
            else:
                raise AssertionError(f"{action} should be rejected")
    finally:
        shutil.rmtree(root)
