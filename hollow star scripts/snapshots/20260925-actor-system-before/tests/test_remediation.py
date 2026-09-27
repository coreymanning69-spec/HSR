"""Unit tests verifying all fixes and remediations across combat, voice, spells, and host."""

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent

from hollowstar.host import HSRHost
from hollowstar.run_service import RunService
from hollowstar import tactical as t
from hollowstar import dungeon
from hollowstar import spells
from hollowstar.items import Item
from hollowstar.view_model import public_event_summary, PUBLIC_EVENT_KEEP_KEYS


class RemediationTests(unittest.TestCase):
    def test_public_event_keep_keys_preserves_voice_and_commentary(self):
        self.assertIn("commentary", PUBLIC_EVENT_KEEP_KEYS)
        self.assertIn("sfx", PUBLIC_EVENT_KEEP_KEYS)
        self.assertIn("voice", PUBLIC_EVENT_KEEP_KEYS)
        raw_event = {
            "type": "attack",
            "actor": "p0",
            "damage": 5,
            "commentary": [{"speaker": "Doran", "text": "Take that!"}],
            "sfx": {"text": "CLANG"},
            "voice": "dialogue",
            "private_debug_state": {"secret": 123},
        }
        summary = public_event_summary(raw_event)
        self.assertEqual(summary["commentary"], [{"speaker": "Doran", "text": "Take that!"}])
        self.assertEqual(summary["sfx"], {"text": "CLANG"})
        self.assertEqual(summary["voice"], "dialogue")
        self.assertEqual(summary["damage"], 5)
        self.assertNotIn("private_debug_state", summary)

    def test_tactical_plural_targets_presentation(self):
        with tempfile.TemporaryDirectory(prefix="hsr-rem-") as tmp:
            runs = RunService(Path(tmp) / ".local/reliquary_runs")
            runs.create("tactical_test", ["Doran", "Wren"], ["Townsperson"], "tactical_test")
            runs.design_start("tactical_test")
            run = runs._active["tactical_test"]
            # Trigger combat
            dungeon.room(run)["resolved"] = True
            runs.design_action("tactical_test", {"type": "enter"})
            run = runs._active["tactical_test"]
            run.context["combat"]["cursor"] = run.context["combat"]["order"].index("p1")
            action = {"type": "cast", "spell": "Healing Word@5e", "actor": "p1", "targets": ["p0"]}
            result = t.apply(run, action)
            self.assertIn("presentation", result)
            self.assertEqual(result["presentation"]["target_id"], "p0")

    def test_spell_receipt_promotes_damage_and_healing(self):
        with tempfile.TemporaryDirectory(prefix="hsr-rem-") as tmp:
            runs = RunService(Path(tmp) / ".local/reliquary_runs")
            runs.create("spell_test", ["Doran", "Wren"], ["Townsperson"], "spell_test")
            runs.design_start("spell_test")
            run = runs._active["spell_test"]
            dungeon.room(run)["resolved"] = True
            runs.design_action("spell_test", {"type": "enter"})
            run = runs._active["spell_test"]
            # Reduce Doran's HP so heal actually restores HP
            t.actor(run, "p0").adjust_hp(-10)
            # Cast Healing Word on Doran
            action = {"type": "cast", "spell": "Healing Word@5e", "actor": "p1", "targets": ["p0"]}
            result = spells.cast(run, "p1", action)
            self.assertIn("healing", result)
            self.assertGreater(result["healing"], 0)
            self.assertEqual(result["target"], "p0")

    def test_metamagic_consumes_casting_energy_when_sorcery_points_zero(self):
        with tempfile.TemporaryDirectory(prefix="hsr-rem-") as tmp:
            runs = RunService(Path(tmp) / ".local/reliquary_runs")
            runs.create("meta_test", ["Doran", "Wren"], ["Townsperson"], "meta_test")
            runs.design_start("meta_test")
            run = runs._active["meta_test"]
            dungeon.room(run)["resolved"] = True
            runs.design_action("meta_test", {"type": "enter"})
            run = runs._active["meta_test"]
            # Setup custom caster on p1 with casting_energy and 0 sorcery_points
            t.rules(run, "p1")["identity"] = "custom"
            t.rules(run, "p1")["class_id"] = "magician"
            t.rules(run, "p1")["known_spells"] = ["Arcane Bolt@HSR"]
            p1_actor = t.actor(run, "p1")
            p1_actor.resources["casting_energy"] = 5
            p1_actor.resources["sorcery_points"] = 0
            # Cast with metamagic careful (cost 1)
            target = [k for k in t.actors(run) if not t.same_side(k, "p1")][0]
            action = {"type": "cast", "spell": "Arcane Bolt@HSR", "actor": "p1", "targets": [target], "metamagic": ["careful"]}
            result = spells.cast(run, "p1", action)
            self.assertEqual(result["type"], "cast")
            self.assertEqual(p1_actor.resources["casting_energy"], 4)

    def test_mid_run_gear_swapping(self):
        with tempfile.TemporaryDirectory(prefix="hsr-rem-") as tmp:
            runs = RunService(Path(tmp) / ".local/reliquary_runs")
            runs.create("gear_test", ["Doran"], ["Townsperson"], "gear_test")
            runs.design_start("gear_test")
            run = runs._active["gear_test"]
            # Acquire weapon into inventory
            runs.design_action("gear_test", {"type": "acquire_weapon", "name": "Mithral Greatsword", "base_damage": 12})
            run = runs._active["gear_test"]
            d = run.context["dungeon"]
            item_id = [k for k, v in d["inventory"].items() if v.get("name") == "Mithral Greatsword"][0]
            # Equip the weapon mid-run
            result = runs.design_action("gear_test", {"type": "equip", "item": item_id, "actor": "p0"})
            self.assertEqual(result["event"]["type"], "equip")
            run = runs._active["gear_test"]
            p0 = run.party[0]
            equipped_weapons = [eq for eq in p0.equipment if eq.slot == "hand"]
            self.assertTrue(any(eq.name == "Mithral Greatsword" for eq in equipped_weapons))

    def test_mid_run_armor_equipping_updates_ac_and_combat(self):
        with tempfile.TemporaryDirectory(prefix="hsr-rem-") as tmp:
            runs = RunService(Path(tmp) / ".local/reliquary_runs")
            runs.create("armor_test", ["Doran"], ["Townsperson"], "armor_test")
            runs.design_start("armor_test")
            run = runs._active["armor_test"]
            # Trigger combat
            dungeon.room(run)["resolved"] = True
            runs.design_action("armor_test", {"type": "enter"})
            run = runs._active["armor_test"]
            # Add plate armor into inventory
            d = run.context["dungeon"]
            item_id = f"item-{d['next_item']}"
            d['next_item'] += 1
            d['inventory'][item_id] = {
                'id': item_id, 'kind': 'permanent_gear', 'gear_type': 'armor',
                'name': 'Heavy Plate', 'slot': 'armor', 'base_ac': 18, 'dex_cap': 0,
            }
            # Equip mid-combat
            res = runs.design_action("armor_test", {"type": "equip", "item": item_id, "actor": "p0"})
            self.assertEqual(res["event"]["type"], "equip")
            run = runs._active["armor_test"]
            p0 = run.party[0]
            # 18 base AC + 0 dex cap = 18 AC
            self.assertEqual(p0.armor_class, 18)
            self.assertEqual(t.actor(run, "p0").armor_class, 18)
            self.assertEqual(run.context["combat"]["rules"]["p0"]["base_ac"], 18)

    def test_spell_attack_roll_promoted_on_miss_with_target(self):
        with tempfile.TemporaryDirectory(prefix="hsr-rem-") as tmp:
            runs = RunService(Path(tmp) / ".local/reliquary_runs")
            runs.create("spell_miss_test", ["Doran", "Wren"], ["Townsperson"], "spell_miss_test")
            runs.design_start("spell_miss_test")
            run = runs._active["spell_miss_test"]
            dungeon.room(run)["resolved"] = True
            runs.design_action("spell_miss_test", {"type": "enter"})
            run = runs._active["spell_miss_test"]
            # Set target AC very high to guarantee a miss unless natural 20
            t.actor(run, "e0").set_armor_class(99)
            action = {"type": "cast", "spell": "Arcane Bolt@HSR", "actor": "p1", "targets": ["e0"]}
            # Force non-20 roll
            t.rules(run, "p1")["identity"] = "custom"
            t.rules(run, "p1")["class_id"] = "magician"
            t.rules(run, "p1")["known_spells"] = ["Arcane Bolt@HSR"]
            result = spells.cast(run, "p1", action)
            self.assertEqual(result["type"], "cast")
            self.assertIn("roll", result)
            self.assertEqual(result["target"], "e0")
            self.assertEqual(result["events"][0]["target"], "e0")
            self.assertEqual(result["events"][0]["type"], "attack")

    def test_custom_caster_insufficient_casting_energy_message(self):
        with tempfile.TemporaryDirectory(prefix="hsr-rem-") as tmp:
            runs = RunService(Path(tmp) / ".local/reliquary_runs")
            runs.create("custom_err_test", ["Doran", "Wren"], ["Townsperson"], "custom_err_test")
            runs.design_start("custom_err_test")
            run = runs._active["custom_err_test"]
            dungeon.room(run)["resolved"] = True
            runs.design_action("custom_err_test", {"type": "enter"})
            run = runs._active["custom_err_test"]
            t.rules(run, "p1")["identity"] = "custom"
            t.rules(run, "p1")["class_id"] = "magician"
            t.rules(run, "p1")["known_spells"] = ["Arcane Bolt@HSR"]
            p1_actor = t.actor(run, "p1")
            p1_actor.resources.clear()
            p1_actor.resources["casting_energy"] = 0
            p1_actor.resources["sorcery_points"] = 0
            action = {"type": "cast", "spell": "Arcane Bolt@HSR", "actor": "p1", "targets": ["e0"], "metamagic": ["careful"]}
            with self.assertRaises(t.ActionError) as cm:
                spells.cast(run, "p1", action)
            self.assertIn("casting_energy", str(cm.exception))

    def test_host_dispatches_arcade_commands(self):
        with tempfile.TemporaryDirectory(prefix="hsr-host-") as tmp:
            host = HSRHost.from_options(WORKSPACE, data_root=Path(tmp) / ".local" / "reliquary_runs")
            boot = host.handle({"id": "1", "command": "boot", "mode": "DESIGN"})
            self.assertTrue(boot["ok"])
            create = host.handle({"id": "2", "command": "create_run", "run_id": "arcade_run", "party": ["Doran"], "opposition": ["Townsperson"]})
            self.assertTrue(create["ok"])
            start = host.handle({"id": "3", "command": "design_start", "run_id": "arcade_run"})
            self.assertTrue(start["ok"])
            run = host._runs()._active["arcade_run"]
            # Move to Room 1:2 (Arcade encounter)
            run.context["dungeon"]["rooms"]["1:1"]["resolved"] = True
            exit_reply = host.handle({"id": "4", "command": "design_action", "run_id": "arcade_run", "action": {"type": "exit"}})
            self.assertTrue(exit_reply["ok"])
            # Now in arcade room, test arcade_tick via host command dispatch
            tick_reply = host.handle({"id": "5", "command": "arcade_tick", "run_id": "arcade_run", "inputs": [{"actor": "p0", "dx": 10, "dy": 0}]})
            self.assertTrue(tick_reply["ok"])
            self.assertIn("arcade", tick_reply["result"]["state"])

    def test_host_auto_combat_player_turn_resolves_via_policy(self):
        with tempfile.TemporaryDirectory(prefix="hsr-host-") as tmp:
            host = HSRHost.from_options(WORKSPACE, data_root=Path(tmp) / ".local" / "reliquary_runs")
            host.handle({"id": "1", "command": "boot", "mode": "DESIGN"})
            host.handle({"id": "2", "command": "create_run", "run_id": "auto_run", "party": ["Doran"], "opposition": ["Townsperson"]})
            host.handle({"id": "3", "command": "design_start", "run_id": "auto_run"})
            run = host._runs()._active["auto_run"]
            # Trigger combat
            dungeon.room(run)["resolved"] = True
            host.handle({"id": "4", "command": "design_action", "run_id": "auto_run", "action": {"type": "enter"}})
            # Call design_auto_combat on player turn
            auto_reply = host.handle({"id": "5", "command": "design_auto_combat", "run_id": "auto_run"})
            self.assertTrue(auto_reply["ok"])
            self.assertNotIn("error", auto_reply)
            self.assertIn("public_view", auto_reply["result"])
            self.assertIn("public_receipt", auto_reply["result"])


if __name__ == "__main__":
    unittest.main()
