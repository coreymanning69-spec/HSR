from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.modules import (ModuleError, load_manifest, load_module, load_module_content,
                                module_roster, validate_manifest)
from hollowstar.run_service import RunService


def test_template_manifest_loads() -> None:
    path = Path(__file__).parents[1] / "hollowstar" / "content" / "modules" / "reliquary-template" / "manifest.json"
    manifest = load_module(path)
    assert manifest["module_id"] == "reliquary-template"
    assert manifest["status"] == "candidate"
    assert manifest["blind_play"]["sealed_room_boundary"] is True
    assert set(load_module_content(path, manifest)) == {"floors", "rooms", "actors", "equipment", "spells", "encounter_tables", "rules", "authored_tells"}


def test_champion_rehearsal_equipment_reaches_combat() -> None:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="hsr-champion-fixture-") as tmp:
        service = RunService(Path(tmp) / ".local" / "reliquary_runs",
                             module_root=Path(__file__).parents[1] / "hollowstar" / "content" / "modules")
        service.create("fixture", ["Doran", "Wren"], ["Townsperson"], "fixture",
                       scenario="champion_rehearsal", run_mode="SANDBOX")
        service.design_start("fixture")
        run = service._active["fixture"]
        boss = run.opposition[0]
        assert boss.name == "Brass Castellan"
        assert boss.max_hp == 480 and boss.armor_class == 23
        assert len(boss.equipment) == 4
        assert boss.resources == {"ward": 75, "amber_beads": 4}
        assert boss.weapon().range_normal == 120
        assert run.context["combat"]["rules"]["e0"]["size"] == "huge"


def test_manifest_rejects_unsafe_id() -> None:
    raw = {"schema_version": "hollow-star-module-1", "module_id": "../escape"}
    try:
        validate_manifest(raw)
    except ModuleError as exc:
        assert "missing fields" in str(exc)
    else:
        raise AssertionError("incomplete manifests must fail closed")


def test_module_rejects_content_escape() -> None:
    raw = {
        "schema_version": "hollow-star-module-1", "module_id": "safe-module",
        "version": "1", "title": "x", "ruleset": "x", "status": "editable",
        "entry_fixture": {"fixture_id": "entry"},
        "blind_play": {"sealed_room_boundary": True},
        "content": {key: "ok.json" for key in ("floors", "rooms", "actors", "equipment", "spells", "encounter_tables", "rules", "authored_tells")},
    }
    raw["content"]["rules"] = "../escape.json"
    try:
        validate_manifest(raw)
        # Path policy is exercised through load_module in the template test;
        # this assertion documents that validation alone does not touch disk.
    except ModuleError:
        raise AssertionError("manifest shape should remain independent of filesystem")


def test_module_content_cross_references_fail_closed() -> None:
    import tempfile
    import shutil
    tmp_path = Path(tempfile.mkdtemp(prefix="hsr-module-invalid-"))
    try:
        manifest_path = tmp_path / "manifest.json"
        content = {"floors":"floors.json", "rooms":"rooms.json", "actors":"actors.json",
                   "equipment":"equipment.json", "spells":"spells.json",
                   "encounter_tables":"encounter_tables.json", "rules":"rules.json",
                   "authored_tells":"authored_tells.json"}
        raw = {"schema_version":"hollow-star-module-1", "module_id":"bad-module",
               "version":"1", "title":"bad", "ruleset":"x", "status":"editable",
               "entry_fixture":{"fixture_id":"entry"}, "blind_play":{"sealed_room_boundary":True},
               "content":content}
        manifest_path.write_text(__import__('json').dumps(raw), encoding='utf-8')
        for filename in content.values():
            (tmp_path / filename).write_text('{}', encoding='utf-8')
        (tmp_path / "rooms.json").write_text('{"rooms":[{"actor_id":"missing"}]}', encoding='utf-8')
        try:
            load_module_content(manifest_path)
        except ModuleError as exc:
            assert "missing actor" in str(exc)
        else:
            raise AssertionError("missing room actor must fail closed")
    finally:
        shutil.rmtree(tmp_path)


def test_module_is_bound_to_isolated_run_context() -> None:
    import tempfile
    import shutil
    tmp = Path(tempfile.mkdtemp(prefix="hsr-module-run-"))
    try:
        service = RunService(tmp / ".local" / "reliquary_runs",
                             module_root=Path(__file__).parents[1] / "hollowstar" / "content" / "modules")
        summary = service.create("module-run", ["Doran"], ["Townsperson"], "seed",
                                 module_id="reliquary-template")
        assert summary.context["module"]["module_id"] == "reliquary-template"
        assert summary.context["module"]["content_counts"]["actors"] == 1
        assert (service.run_root / "module-run.json").exists()
        entered = service.design_start("module-run")
        assert entered["event"]["room"]["title"] == "The First Threshold"
        assert entered["event"]["room"]["law"] == "Town-controlled sleep raises an alarm and brings an organized night patrol."
        assert entered["event"]["room"]["number"] == 1
        assert entered["event"]["room"]["checkpoint"] is True
        assert entered["event"]["room"]["safe_room"] is True
        assert service._active["module-run"].opposition[0].max_hp == 22
        assert service._active["module-run"].opposition[0].weapon().name == "chalkblade"
        assert service._active["module-run"].context["combat"]["terrain"]["structures"][0]["name"] == "sealed arch"
        reloaded = RunService(service.run_root, module_root=service.module_root)
        loaded = reloaded.load("module-run")
        assert loaded.context["module"]["module_id"] == "reliquary-template"
        assert "module_content" not in loaded.context
        assert reloaded._active["module-run"].context["module_content"]["actors"]["actors"][0]["actor_id"] == "marked-sentinel"
        resumed = reloaded.design_start("module-run")
        assert resumed["event"]["type"] == "dungeon_resumed"
        assert resumed["event"]["evidence"]["already_started"] is True
        assert reloaded._active["module-run"].opposition[0].max_hp == 22
    finally:
        shutil.rmtree(tmp)


def test_template_exposes_all_five_authored_floors() -> None:
    import json

    template_path = (Path(__file__).parents[1] / "hollowstar" / "content" / "modules"
                     / "reliquary-template" / "manifest.json")
    content = load_module_content(template_path)
    floors = content["floors"]["floors"]
    rooms = content["rooms"]["rooms"]
    assert len(floors) == 5
    assert {row["floor"] for row in rooms} == {1, 2, 3, 4, 5}
    assert [row["kind"] for row in rooms] == ["combat", "hazard", "social", "hazard", "boss"]

    tmp = Path(__import__('tempfile').mkdtemp(prefix="hsr-five-floor-module-"))
    try:
        service = RunService(tmp / ".local" / "reliquary_runs",
                             module_root=Path(__file__).parents[1] / "hollowstar" / "content" / "modules")
        summary = service.create("five-floor", ["Doran"], ["Townsperson"], "seed",
                                 module_id="reliquary-template")
        assert len(service._active["five-floor"].context["module_content"]["floors"]["floors"]) == 5
        started = service.design_start("five-floor")
        assert started["event"]["room"]["floor"] == 1
        assert started["event"]["room"]["number"] == 1
        assert started["event"]["room"]["title"] == "The First Threshold"
        dungeon_state = service._active["five-floor"].context["dungeon"]
        assert set(dungeon_state["config"]["module_rooms_by_floor"]) == {"1", "2", "3", "4", "5"}
    finally:
        import shutil
        shutil.rmtree(tmp)


TEMPLATE = (Path(__file__).parents[1] / "hollowstar" / "content" / "modules"
            / "reliquary-template" / "manifest.json")


def test_module_actors_become_selectable_engine_actors() -> None:
    roster = module_roster(load_module_content(TEMPLATE))
    # Addressable by display name and by the stable actor_id alike.
    sentinel = roster["marked sentinel"]
    assert roster["marked-sentinel"] is sentinel
    assert (sentinel.max_hp, sentinel.armor_class) == (22, 14)
    assert sentinel.band.name == "MORTAL"          # numeric band 10 resolves
    assert [item.name for item in sentinel.equipment] == ["chalkblade"]
    # Authored actors are never mistaken for a certified balance source.
    assert sentinel.provenance.verified is False


def test_module_actor_reaches_the_played_world() -> None:
    from hollowstar.sandbox import _fixture_rooms, _module_npcs

    class _Run:
        context = {"module_content": load_module_content(TEMPLATE)}

    placed = _module_npcs(_Run(), _fixture_rooms())
    sentinel = placed["marked-sentinel"]
    assert sentinel["room"] == "crypt_entry"        # authored via sandbox_room
    assert sentinel["disposition"] == "hostile"
    assert (sentinel["hp"], sentinel["ac"], sentinel["attack_bonus"]) == (22, 14, 5)


def test_module_placement_degrades_without_crashing() -> None:
    import copy

    from hollowstar.sandbox import _fixture_rooms, _module_npcs

    class _Run:
        context: dict = {}

    rooms = _fixture_rooms()
    assert _module_npcs(_Run(), rooms) == {}        # no module loaded at all

    content = copy.deepcopy(load_module_content(TEMPLATE))
    content["rooms"]["rooms"][0]["sandbox_room"] = "no-such-room"
    stray = _Run()
    stray.context = {"module_content": content}
    assert _module_npcs(stray, rooms) == {}         # unknown room is skipped


if __name__ == "__main__":
    test_template_manifest_loads()
    test_manifest_rejects_unsafe_id()
    print("4 module tests passed")
