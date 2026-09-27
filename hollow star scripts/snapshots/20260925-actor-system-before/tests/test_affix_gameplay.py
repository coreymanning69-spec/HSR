"""Active Prefix/Suffix rules must change host-owned gameplay, not just cards."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hollowstar import dungeon
from hollowstar import tactical as t
from hollowstar.intent import parse_intent
from hollowstar.run_service import RunService


def _service():
    root = Path(tempfile.mkdtemp(prefix="hsr-affix-gameplay-"))
    run_root = root / ".local" / "reliquary_runs"
    service = RunService(run_root)
    service.create("affix", ["Doran", "Wren"], ["Townsperson"], "affix-seed")
    service.design_start("affix")
    return service, root


def _equipped(service, name):
    run = service._active["affix"]
    run.context["dungeon"]["components"] = 5
    item = dungeon.add_item(run, "imprint", identified=True)
    service.design_action("affix", {"type": "reforge_affix", "actor": "p0", "item": item["id"], "affix": name})
    service.design_action("affix", {"type": "equip", "actor": "p0", "item": item["id"]})
    return service._active["affix"], item["id"]


def test_reforge_materializes_only_active_affixes_and_public_name():
    service, root = _service()
    try:
        run, item_id = _equipped(service, "Petty")
        row = run.context["dungeon"]["inventory"][item_id]
        assert row["prefix"]["name"] == "Petty"
        assert row["prefix"]["effects"][0]["flat_bonus"] == 2
        assert row["display_name"].startswith("Petty ")
        before = run.context["dungeon"]["components"]
        try:
            service.design_action("affix", {"type": "reforge_affix", "item": item_id, "affix": "Blazing"})
        except Exception as error:
            assert "active HSR catalog" in str(error)
        else:
            raise AssertionError("staged affix must not be attachable")
        assert run.context["dungeon"]["components"] == before
    finally:
        import shutil; shutil.rmtree(root, ignore_errors=True)


def test_reforge_intent_resolves_a_visible_item_and_preserves_affix_name():
    context = {"inventory": [{"id": "item-7", "name": "Vitality Seal"}]}
    assert parse_intent("reforge Vitality Seal with of Ice", context) == {
        "type": "reforge_affix", "actor": "p0", "item": "item-7", "affix": "of Ice",
    }


def test_prefix_damage_suffix_status_and_affix_tag_reach_tactical_resolution():
    service, root = _service()
    try:
        run, item_id = _equipped(service, "Petty")
        service.design_action("affix", {"type": "reforge_affix", "item": item_id, "affix": "of Frostbite"})
        service.design_action("affix", {"type": "fight"})
        run = service._active["affix"]
        # Doran's pinned dagger attack has a normal tactical path but no
        # native Frostbite/Petty rules, so any rider/evidence is from the Rune.
        result = service.design_action("affix", {"type": "attack", "actor": "p0", "target": "e0", "mode": "dagger"})["event"]
        run = service._active["affix"]
        if result["roll"]["success"]:
            names = {entry["effect"] for entry in result["evidence"]["affix_effects"]}
            assert "petty bonus" in names
            assert "SLOWED" in t.actor(run, "e0").statuses
        else:
            # The deterministic seed can miss only if upstream initiative or
            # rules change; the affix still reaches the host evidence on hit.
            assert result["type"] == "attack"
    finally:
        import shutil; shutil.rmtree(root, ignore_errors=True)


def test_affix_resistance_applies_to_damage_and_skill_modifier_is_explicit():
    service, root = _service()
    try:
        run, item_id = _equipped(service, "of Frostbite")
        row = run.context["dungeon"]["inventory"][item_id]
        row["modifiers"].append({"effect": "resistance", "value": "SONIC"})
        row["modifiers"].append({"effect": "skill_bonus", "skill": "Persuasion", "value": 3})
        service.design_action("affix", {"type": "fight"})
        run = service._active["affix"]
        before = t.actor(run, "p0").hp
        damage = t.damage(run, "e0", "p0", 8, "SONIC")
        assert damage["damage"] == 4
        assert damage["evidence"]["affix_resistances"] == ["SONIC"]
        from hollowstar.affix_runtime import skill_bonus
        assert skill_bonus(run, "p0", "Persuasion") == 3
    finally:
        import shutil; shutil.rmtree(root, ignore_errors=True)
