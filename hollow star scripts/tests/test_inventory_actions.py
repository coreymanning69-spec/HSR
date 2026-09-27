"""
Tests for inventory bookbag actions, equip/unequip mechanics, and carrying weight calculations.
"""

import tempfile
import unittest
from pathlib import Path

from hollowstar.actors import Actor
from hollowstar.items import Item
from hollowstar.run_service import RunService


class InventoryActionsTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        run_root = Path(self.temp_dir.name) / ".local" / "reliquary_runs"
        self.service = RunService(run_root, durable_saves=True)
        self.run_id = "test-inv-run"
        self.service.create(self.run_id, party=["Doran"], opposition=["Townsperson"], seed=42, run_mode="DESIGN")
        self.service.design_start(self.run_id)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_carrying_capacity_formula(self):
        run = self.service._active[self.run_id]
        hero = run.party[0]
        hero.set_ability_score("STR", 16)
        str_val = hero.ability_score("STR")
        self.assertEqual(str_val, 16)
        max_capacity = str_val * 15
        self.assertEqual(max_capacity, 240)

        starting_weight = sum(item.weight for item in hero.equipment)
        plate = Item(name="Full Plate", slot="armor", base_ac=18, weight=55.0)
        hero.equipment.append(plate)
        total_weight = sum(item.weight for item in hero.equipment)
        self.assertEqual(total_weight, starting_weight + 55.0)
        self.assertLess(total_weight, max_capacity)

    def test_equip_and_unequip_action(self):
        run = self.service._active[self.run_id]
        hero = run.party[0]
        dungeon_ctx = run.context["dungeon"]
        dungeon_ctx["inventory"]["item_warhammer"] = {
            "id": "item_warhammer",
            "name": "warhammer",
            "kind": "weapon",
            "slot": "hand",
            "base_damage": 8,
            "damage_dice": "1d8",
            "attack_ability": "STR",
            "weight": 6.0,
            "density": 1.0,
        }
        self.service.save(self.run_id)

        # Equip the warhammer
        action_equip = {"type": "equip", "item": "item_warhammer", "actor": "p0"}
        result_equip = self.service.design_action(self.run_id, action_equip)
        self.assertEqual(result_equip["event"]["type"], "equip")
        
        # Check that target_actor in run.party has warhammer equipped
        active_hero = self.service._active[self.run_id].party[0]
        equipped_names = [eq.name for eq in active_hero.equipment]
        self.assertIn("warhammer", equipped_names)

        # Check weapon profile
        profile = active_hero.weapon_profile()
        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"], "warhammer")
        self.assertEqual(profile["damage_dice"], "1d8")

        # Unequip the warhammer
        action_unequip = {"type": "unequip", "slot": "hand", "actor": "p0"}
        result_unequip = self.service.design_action(self.run_id, action_unequip)
        self.assertEqual(result_unequip["event"]["type"], "unequip")
        self.assertTrue(result_unequip["event"]["evidence"]["unequipped"])
        active_hero_after = self.service._active[self.run_id].party[0]
        self.assertFalse(any(eq.slot == "hand" for eq in active_hero_after.equipment))

    def test_public_view_serializes_inventory_and_weight(self):
        run = self.service._active[self.run_id]
        dungeon_ctx = run.context["dungeon"]
        dungeon_ctx["inventory"]["item_potion"] = {
            "id": "item_potion",
            "name": "Healing Potion",
            "kind": "potion",
            "weight": 0.5,
            "identified": True,
        }
        self.service.save(self.run_id)

        public_view = self.service.observe(self.run_id)
        self.assertIn("inventory", public_view)
        inventory_items = public_view["inventory"]
        self.assertIn("item_potion", inventory_items)
        self.assertEqual(inventory_items["item_potion"]["name"], "Healing Potion")
        self.assertEqual(inventory_items["item_potion"]["weight"], 0.5)


if __name__ == "__main__":
    unittest.main()
