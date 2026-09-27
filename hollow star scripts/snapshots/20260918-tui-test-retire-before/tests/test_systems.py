"""Cross-adapter state, world identity, and explicit dice regression tests."""
from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.actors import Actor
from hollowstar.host import HSRHost
from hollowstar.items import Item
from hollowstar.phases import Phase
from hollowstar.profiles import ProfileError, ProfileService
from hollowstar.resolution import resolve_attack
from hollowstar.rng import RunRNG
from hollowstar.combat import Encounter
from hollowstar.run_service import RunService
from hollowstar.run_state import resume_run, save_run
from hollowstar.session_screen import SessionScreen
from hollowstar.world import world_context


def profile():
    return {"name": "Ash", "race": "Human", "character_class": "Fighter",
            "specialization": "Unselected", "ability_scores": dict.fromkeys(("STR", "DEX", "CON", "INT", "WIS", "CHA"), 12),
            "max_hp": 24, "armor_class": 15, "resources": {"potions": 2},
            "equipment": [{"name": "Sword", "damage_dice": "1d8", "damage_modifier": 1, "attack_bonus": 3}]}


class Rolls:
    def __init__(self, *values):
        self.values = iter(values)

    def d20(self):
        return self.randint(1, 20)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


class SystemsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="hsr-systems-")
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / ".local"
        self.profiles = ProfileService(self.data / "reliquary_profiles")
        self.runs = RunService(self.data / "reliquary_runs", profile_root=self.profiles.root)
        self.profiles.save("ash", profile(), replace=False)

    def make_run(self):
        self.runs.create("trial", ["custom:ash", "divine:Wren"], ["Townsperson"], "seed")

    def test_weighted_choice_is_seeded_and_validated(self):
        left = RunRNG("weighted").weighted_choice(["common", "rare"], [9, 1])
        right = RunRNG("weighted").weighted_choice(["common", "rare"], [9, 1])
        self.assertEqual(left, right)
        with self.assertRaises(ValueError):
            RunRNG("weighted").weighted_choice(["common"], [0])

    def test_encounter_turn_pipeline_processes_periodic_effects_and_expiry(self):
        actor = Actor(name="Ash", max_hp=10, hp=5, statuses={"POISONED": 1})
        enemy = Actor(name="Rat", max_hp=2, hp=2)
        encounter = Encounter([actor], [enemy], RunRNG("turn"), context={
            "periodic_effects": {"Ash": [{"status": "POISONED", "damage": 2}]}
        })
        encounter.start_turn(actor)
        self.assertEqual(actor.hp, 3)
        encounter.end_turn(actor)
        self.assertNotIn("POISONED", actor.statuses)

    def test_mixed_save_and_frozen_profiles(self):
        self.make_run()
        changed = profile()
        changed["ability_scores"]["STR"] = 20
        changed["name"] = "Later Ash"
        self.profiles.save("ash", changed, replace=True)
        self.runs.save("trial")
        service = RunService(self.runs.run_root, profile_root=self.profiles.root)
        service.load("trial")
        sheets = service.sheets("trial")
        self.assertEqual(sheets[0]["name"], "Ash")
        self.assertEqual(sheets[0]["stats"]["abilities"]["STR"]["score"], 12)
        self.assertEqual(sheets[0]["resources"], {"potions": 2})
        self.assertEqual(sheets[0]["identity"]["level"], 2)
        self.assertEqual(sheets[0]["identity"]["hsr_rank"], 1)
        self.assertFalse(sheets[0]["editable"])
        sheets[0]["stats"]["abilities"]["STR"]["score"] = 1
        self.assertEqual(service.sheets("trial")[0]["stats"]["abilities"]["STR"]["score"], 12)

    def test_world_identity_round_trip_and_no_aliasing(self):
        self.make_run()
        summary = self.runs.load("trial").as_dict()
        world = summary["context"]["world"]
        self.assertEqual(world["creator"], "Soliera")
        self.assertEqual(world["conceived_by"], ["Ember", "Sera"])
        self.assertIn("Letha", world["social_context"]["interested_adventurers"])
        world["creator"] = "wrong"
        self.assertEqual(self.runs.inspect("trial").context["world"]["creator"], "Soliera")
        self.assertEqual(world_context()["creator"], "Soliera")

    def test_terminal_and_new_host_see_same_saved_state(self):
        host = HSRHost.from_options(data_root=self.data)
        ui = SessionScreen(host, io.StringIO(), io.StringIO())
        ui.request("boot", mode="DESIGN")
        self.assertIn("Soliera", ui.execute("world"))
        self.assertIn("Ash", ui.execute("create shared seed custom:ash divine:Wren"))
        self.assertIn("Saved shared", ui.execute("save"))
        second = SessionScreen(HSRHost.from_options(data_root=self.data), io.StringIO(), io.StringIO())
        second.request("boot", mode="REVIEW")
        self.assertEqual(ui.execute("status"), second.execute("load shared"))
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_OPERATION"):
            second.execute("attack")
        self.assertEqual(second.request("inspect_run", run_id="shared")["run"]["round_number"], 0)

    def test_guided_profile_and_quit(self):
        answers = "new-profile ember_guest\nGuest\n" + "\n" * 9 + "quit\n"
        output = io.StringIO()
        ui = SessionScreen(HSRHost.from_options(data_root=self.data), io.StringIO(answers), output)
        self.assertEqual(ui.run(), 0)
        self.assertIn("Saved deterministic local custom profile", output.getvalue())
        self.assertEqual(self.profiles.inspect("ember_guest")["name"], "Guest")

    def test_old_save_additive_migration(self):
        self.make_run()
        path = self.runs.run_root / "trial.json"
        raw = json.loads(path.read_text())
        raw["encounter"].pop("context")
        def strip(value):
            if isinstance(value, list):
                for child in value:
                    strip(child)
            elif isinstance(value, dict):
                if value.get("__dataclass__") == "Item":
                    value["fields"].pop("damage_dice")
                    value["fields"].pop("damage_modifier")
                for child in value.values():
                    strip(child)
        strip(raw)
        path.write_text(json.dumps(raw), encoding="utf-8")
        loaded = resume_run(path)
        self.assertEqual(loaded.context["world"]["creator"], "Soliera")
        self.assertEqual(loaded.party[0].weapon().damage_dice, "")

    def test_invalid_profile_numbers_fail_without_writes(self):
        for field, value in [("level", True), ("hsr_rank", 11), ("resources", {"potions": -1})]:
            data = profile()
            data[field] = value
            with self.assertRaises(ProfileError):
                self.profiles.save("bad", data, replace=False)
            self.assertFalse((self.profiles.root / "bad.json").exists())
        for value in [float("nan"), float("inf")]:
            data = profile()
            data["equipment"][0]["density"] = value
            with self.assertRaises(ProfileError):
                self.profiles.save("bad", data, replace=False)

    def fighters(self):
        attacker = self.profiles.actor("ash")
        defender = Actor("Target", hp=40, max_hp=40, armor_class=15)
        return attacker, defender

    def test_hit_damage_and_bounded_hp(self):
        attacker, defender = self.fighters()
        result = resolve_attack(attacker, defender, rng=Rolls(12, 8))
        self.assertEqual(result.damage, 9)
        self.assertEqual(defender.hp, 31)
        defender.hp = 1
        resolve_attack(attacker, defender, rng=Rolls(12, 8))
        self.assertEqual(defender.hp, 0)

    def test_natural_one_misses_even_with_large_bonus(self):
        attacker, defender = self.fighters()
        attacker.weapon().attack_bonus = 100
        result = resolve_attack(attacker, defender, rng=Rolls(1))
        self.assertEqual(result.stopped_at, Phase.DELIVERY)
        self.assertEqual(defender.hp, 40)
        self.assertIn("natural 1", result.log())

    def test_critical_doubles_dice_only_and_ignores_ac(self):
        attacker, defender = self.fighters()
        defender.armor_class = 100
        result = resolve_attack(attacker, defender, rng=Rolls(20, 3, 7))
        self.assertEqual(result.damage, 11)
        self.assertIn("natural 20", result.log())

    def test_advantage_disadvantage_and_cancellation(self):
        attacker, defender = self.fighters()
        self.assertTrue(resolve_attack(attacker, defender, rng=Rolls(1, 12, 4), advantage=True).succeeded)
        self.assertFalse(resolve_attack(attacker, defender, rng=Rolls(20, 1), disadvantage=True).succeeded)
        self.assertTrue(resolve_attack(attacker, defender, rng=Rolls(12, 4), advantage=True, disadvantage=True).succeeded)

    def test_missing_weapon_dice_refused_before_mutation(self):
        attacker, defender = self.fighters()
        attacker.weapon().damage_dice = ""
        with self.assertRaisesRegex(ValueError, "deferred"):
            resolve_attack(attacker, defender, rng=Rolls())
        self.assertEqual(defender.hp, 40)

    def test_rng_continuation_and_transcript(self):
        self.make_run()
        path = self.runs.run_root / "trial.json"
        encounter = resume_run(path)
        encounter.opposition[0].hp = encounter.opposition[0].max_hp = 200
        encounter.transcript.append(resolve_attack(encounter.party[0], encounter.opposition[0], rng=encounter.rng))
        save_run(encounter, "trial", path)
        loaded = resume_run(path)
        a = resolve_attack(encounter.party[0], encounter.opposition[0], rng=encounter.rng)
        b = resolve_attack(loaded.party[0], loaded.opposition[0], rng=loaded.rng)
        self.assertEqual(a.log(), b.log())
        self.assertEqual(encounter.rng.calls, loaded.rng.calls)
        self.assertEqual(encounter.opposition[0].hp, loaded.opposition[0].hp)
        self.assertEqual(loaded.transcript[0].log(), encounter.transcript[0].log())


if __name__ == "__main__":
    unittest.main(verbosity=2)
