"""Focused parity checks for the static Floor One city and gauntlet boundary."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hollowstar.intent import parse_intent
from hollowstar.run_service import RunService
from hollowstar.character_builder import preview
from hollowstar.profiles import ProfileService


def _service(tmp_path: str) -> RunService:
    service = RunService(run_root=tmp_path)
    service.create("city-gauntlet", seed="city-seed", scenario="reliquary_city",
                   party=["Doran"], opposition=["Townsperson"])
    return service


def test_city_conversation_is_local_and_clocked() -> None:
    with tempfile.TemporaryDirectory(dir=".local/reliquary_runs") as tmp_path:
        service = _service(tmp_path)
        started = service.design_start("city-gauntlet")
        state = started["state"]
        resident_id = next(iter(state["npcs"]))
        before = state["event_clock"]["tick"]
        result = service.design_action("city-gauntlet", {
            "type": "talk", "target": resident_id, "mode": "ask",
            "text": "ask what is happening",
        })
        assert result["event"]["type"] == "conversation_resolved"
        assert result["event"]["receipt"]["public"]["reply"]
        assert result["state"]["event_clock"]["tick"] > before
        assert result["state"]["conversation"][-1]["text"] == result["event"]["receipt"]["public"]["reply"]


def test_story_champion_path_opens_village_with_public_abilities_and_dialogue() -> None:
    for champion in ("Doran", "Wren"):
        with tempfile.TemporaryDirectory(dir=".local/reliquary_runs") as tmp_path:
            service = RunService(run_root=tmp_path)
            run_id = f"story-{champion.lower()}"
            service.create(run_id, party=[champion], opposition=["Townsperson"],
                           seed="story-village-seed", scenario="reliquary_city",
                           run_mode="FORGE")
            state = service.design_start(run_id)["state"]
            assert state["schema"] == "hollow-star-floor-one-public-1"
            assert state["player"]["name"] == champion
            assert state["player"]["ability_options"]
            resident = next(iter(state["npcs"].values()))
            assert resident["dialogue"]
            assert resident["state"]["disposition"]
            resolved = service.design_action(run_id, {
                "type": "talk", "target": resident["id"],
                "mode": resident["dialogue"][0]["mode"],
                "text": resident["dialogue"][0]["text"],
            })
            assert resolved["event"]["type"] == "conversation_resolved"
            assert resolved["state"]["conversation"][-1]["text"]


def test_city_routes_to_seeded_gauntlet_without_new_engine() -> None:
    with tempfile.TemporaryDirectory(dir=".local/reliquary_runs") as tmp_path:
        service = _service(tmp_path)
        service.design_start("city-gauntlet")
        service.design_action("city-gauntlet", {"type": "move", "destination": "well"})
        result = service.design_action("city-gauntlet", {"type": "descend"})
        assert result["event"]["type"] == "entered"
        assert result["state"]["floor"] == 1
        assert result["state"]["event_clock"]["rooms_entered"] == 1
        assert result["state"]["events"][-1]["descent"]["type"] == "descent_started"


def test_city_text_adapter_exposes_conversation_and_descent() -> None:
    context = {"schema": "hollow-star-floor-one-public-1", "npcs": {"wellkeeper": {"name": "Wellkeeper"}}}
    assert parse_intent("ask the Wellkeeper what is happening", context)["type"] == "talk"
    assert parse_intent("climb down", context) == {"type": "descend"}


def test_auto_travel_carries_custom_profile_to_descent_with_public_travel_pose() -> None:
    with tempfile.TemporaryDirectory(dir=".local/reliquary_runs") as tmp_path:
        root = Path(tmp_path)
        profiles = ProfileService(root / "profiles")
        profile = preview({"name": "Wayfarer", "creation_seed": "wayfarer",
                           "race": "Human", "gender": "female",
                           "background": "Veteran"})["profile"]
        profiles.save("wayfarer", profile, replace=False)
        service = RunService(run_root=root / "runs", profile_root=root / "profiles")
        service.create("custom-city", seed="custom-city-seed", scenario="reliquary_city",
                       party=["custom:wayfarer"], opposition=["Townsperson"],
                       lead_selector="custom:wayfarer")
        started = service.design_start("custom-city")
        travel = service.auto_travel("custom-city", destination="well", max_steps=4)
        assert travel["event"]["type"] == "auto_travel_advanced"
        assert travel["event"]["reached"] is True
        assert travel["state"]["player"]["location"] == "well"
        assert travel["state"]["travel"]["animation"] == "travel"
        assert travel["state"]["player"]["sprite_id"] == started["state"]["player"]["sprite_id"]
        descended = service.design_action("custom-city", {"type": "descend"})
        assert descended["event"]["type"] == "entered"
        assert descended["state"]["floor"] == 1


def test_auto_travel_uses_the_same_doran_host_path() -> None:
    with tempfile.TemporaryDirectory(dir=".local/reliquary_runs") as tmp_path:
        service = RunService(run_root=tmp_path)
        service.create("doran-city", seed="doran-city-seed", scenario="reliquary_city",
                       party=["Doran"], opposition=["Townsperson"])
        service.design_start("doran-city")
        travel = service.auto_travel("doran-city", destination="well", max_steps=4)
        assert travel["state"]["player"]["name"] == "Doran"
        assert travel["state"]["travel"]["mode"] == "auto"
        descended = service.design_action("doran-city", {"type": "descend"})
        assert descended["event"]["type"] == "entered"


def test_starting_location_well_permits_immediate_descent() -> None:
    with tempfile.TemporaryDirectory(dir=".local/reliquary_runs") as tmp_path:
        service = RunService(run_root=tmp_path)
        service.create("well-start", seed="well-seed", scenario="reliquary_city",
                       party=["Doran"], opposition=["Townsperson"],
                       starting_location="well")
        started = service.design_start("well-start")
        assert started["state"]["player"]["location"] == "well"
        # Since the player is already at the well, descend action is immediately valid without prior movement
        descended = service.design_action("well-start", {"type": "descend"})
        assert descended["event"]["type"] == "entered"
        assert descended["state"]["floor"] == 1
        assert descended["state"]["events"][-1]["descent"]["type"] == "descent_started"

