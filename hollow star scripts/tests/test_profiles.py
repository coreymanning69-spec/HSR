"""Custom profile and selectable-party boundary tests."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.profiles import ProfileError, ProfileService  # noqa: E402
from hollowstar.loader import load_roster
from hollowstar.run_service import RunService  # noqa: E402


def _payload(name: str = "Ash") -> dict:
    return {
        "name": name, "race": "Human", "character_class": "Fighter",
        "specialization": "Vanguard",
        "ability_scores": {"STR": 16, "DEX": 12, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        "max_hp": 24, "armor_class": 17, "initiative_bonus": 1, "speed": 30,
        "proficiency_bonus": 2, "skill_bonuses": {"athletics": 5},
        "equipment": [
            {"name": "chain mail", "slot": "armor", "base_ac": 16},
            {"name": "longsword", "slot": "hand", "base_damage": 8, "attack_bonus": 5},
        ],
    }


def _roots() -> tuple[Path, Path, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="hsr-profile-"))
    return tmp, tmp / ".local" / "reliquary_profiles", tmp / ".local" / "reliquary_runs"


def test_create_update_and_visible_sheet() -> None:
    tmp, profiles, _ = _roots()
    try:
        service = ProfileService(profiles)
        sheet = service.save("ash", _payload(), replace=False)
        assert sheet["selector"] == "custom:ash"
        assert sheet["editable"] is True
        assert sheet["stats"]["abilities"]["STR"] == {"score": 16, "modifier": 3}
        assert sheet["stacking"]["armor_class"]["equipment_components"] == [{"item": "chain mail", "base_ac": 16}]
        changed = _payload("Ash Updated")
        changed["armor_class"] = 18
        assert service.save("ash", changed, replace=True)["stats"]["armor_class"] == 18
    finally:
        shutil.rmtree(tmp)


def test_divine_imports_are_read_only_and_explicitly_selected() -> None:
    tmp, profiles, _ = _roots()
    try:
        roster = ProfileService(profiles).roster()
        divine = {row["name"]: row for row in roster if row["kind"] == "divine_mythos"}
        assert set(divine) == {"Doran", "Wren"}
        assert divine["Doran"]["editable"] is False
        assert divine["Doran"]["provenance"]["read_only"] is True
        assert divine["Doran"]["selector"] == "divine:Doran"
    finally:
        shutil.rmtree(tmp)


def test_major_npc_roster_is_source_linked_and_selectable() -> None:
    roster = load_roster()
    expected = {"Cassian Ward", "Veyren", "Kiyuru", "Korin", "Letha"}
    assert expected <= set(roster)
    assert all(roster[name].controller == "player" for name in expected)
    assert all(roster[name].provenance.owner_file for name in expected)
    assert roster["Kiyuru"].reactions == 5
    assert roster["Kiyuru"].attacks_per_action == 5
    assert roster["Letha"].equipment[0].name == "Sunset"
    assert roster["Letha"].equipment[1].range_normal == 600


def test_major_npc_selectors_round_trip_and_preserve_deferred_rules() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="hsr-major-npc-"))
    try:
        profiles = ProfileService(tmp / "profiles")
        rows = profiles.roster()
        selectors = {row["name"]: row["selector"] for row in rows if row["kind"] == "hsr_npc"}
        assert set(selectors) == {"Cassian Ward", "Veyren", "Kiyuru", "Korin", "Letha"}
        service = RunService(tmp / ".local" / "reliquary_runs")
        summary = service.create("letha-run", [selectors["Letha"]], ["Townsperson"], "npc-seed")
        assert summary.party[0]["name"] == "Letha"
        sheet = service.sheets("letha-run")[0]
        assert sheet["selector"] == "hsr:Letha"
        assert "Sunset triple-cast resolver" in sheet["provenance"]["deferred"]
        service.load("letha-run")
        assert service.sheets("letha-run")[0]["name"] == "Letha"
    finally:
        shutil.rmtree(tmp)


def test_unresolved_and_controlled_npcs_are_catalogued_outside_party_roster() -> None:
    import json
    path = Path(__file__).resolve().parents[1] / "hollowstar" / "content" / "major_npc_roster.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    by_name = {row["name"]: row for row in catalog["entries"]}
    assert by_name["Velin"]["status"] == "author_gate"
    assert by_name["Gable"]["status"] == "author_gate"
    assert by_name["Sera"]["status"] == "controlled_only"
    assert by_name["Ember"]["status"] == "controlled_only"


def test_selectable_mixed_party_persists_without_mutating_sources() -> None:
    tmp, profiles, runs = _roots()
    try:
        ProfileService(profiles).save("ash", _payload(), replace=False)
        summary = RunService(runs, profile_root=profiles).create(
            "mixed", ["custom:ash", "divine:Wren"], ["Townsperson"], "seed"
        )
        assert [row["name"] for row in summary.party] == ["Ash", "Wren"]
        assert (runs / "mixed.json").exists()
        assert ProfileService(profiles).inspect("ash")["stats"]["hp"] == 24
    finally:
        shutil.rmtree(tmp)


def test_profile_validation_fails_closed() -> None:
    tmp, profiles, _ = _roots()
    try:
        bad = _payload()
        bad["ability_scores"].pop("CHA")
        try:
            ProfileService(profiles).save("bad", bad, replace=False)
        except ProfileError:
            pass
        else:
            raise AssertionError("incomplete ability scores must be refused")
        assert not (profiles / "bad.json").exists()
    finally:
        shutil.rmtree(tmp)


def test_sheet_exposes_generic_armor_formula() -> None:
    tmp, profiles, _ = _roots()
    try:
        payload = _payload()
        payload["equipment"][0]["dex_cap"] = 2
        service = ProfileService(profiles)
        sheet = service.save("armor", payload, replace=False)
        formula = sheet["stacking"]["armor_class"]["formula"]
        assert formula["base_ac"] == 16
        assert formula["dex_cap"] == 2
        assert formula["total"] == 17
    finally:
        shutil.rmtree(tmp)


def test_malformed_alternate_modes_fail_closed() -> None:
    tmp, profiles, _ = _roots()
    try:
        payload = _payload()
        payload["equipment"][1]["alternate_modes"] = {"thrown": "not-an-object"}
        try:
            ProfileService(profiles).save("bad-modes", payload, replace=False)
        except ProfileError:
            pass
        else:
            raise AssertionError("malformed alternate modes must be refused")
        assert not (profiles / "bad-modes.json").exists()
    finally:
        shutil.rmtree(tmp)


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} profile tests passed")


if __name__ == "__main__":
    main()
