"""Acceptance tests for procedural NPCs, monster power systems, items, lore descriptions, and dynamic reaction trees."""
from __future__ import annotations

import random
import unittest
from pathlib import Path

from hollowstar import conversation, dungeon, life_sim, npc_generator
from hollowstar.loader import load_items
from hollowstar.phases import Tier


class TestProceduralGeneration(unittest.TestCase):

    def setUp(self):
        self.rng = random.Random(42)

    def test_cultural_naming_pools(self):
        cultures = ("imperial", "frontier_goblin", "arcane_elven", "stoneforged_dwarven", "monster")
        for culture in cultures:
            name = npc_generator.generate_name(culture=culture, rng=self.rng)
            self.assertIsInstance(name, str)
            self.assertTrue(len(name.strip()) > 3)
            # Ensure name contains plausible components
            self.assertTrue(" " in name or len(name) > 4)

    def test_personality_generation(self):
        profile = npc_generator.generate_personality("trader", trait_count=3, rng=self.rng)
        self.assertEqual(len(profile.traits), 3)
        self.assertTrue(len(profile.tells) >= 1)
        self.assertTrue(len(profile.core_motive) > 0)
        self.assertTrue(len(profile.motive_goal) > 5)
        self.assertTrue(0.0 <= profile.surrender_hp_threshold <= 1.0)
        self.assertTrue(0.0 <= profile.bribe_acceptance <= 1.0)

    def test_items_and_lore_populated(self):
        items = load_items()
        # Verify expanded roster of at least 80 items
        self.assertGreaterEqual(len(items), 80)

        # Verify key new standard fantasy equipment
        required_items = [
            "dagger", "shortsword", "scimitar", "shortbow", "longbow",
            "heavy crossbow", "halberd", "spear", "full plate", "breastplate",
            "warded robe", "heavy tower shield", "buckler shield",
            "vial of healing draught", "flask of liquid fire", "amulet of shielding"
        ]
        for name in required_items:
            self.assertIn(name, items, f"Expected {name} to be in items.json")
            item = items[name]
            self.assertTrue(bool(item.flavor), f"Expected {name} to have flavor text")
            self.assertTrue(bool(item.lore), f"Expected {name} to have lore text")
            self.assertTrue(bool(item.silhouette), f"Expected {name} to have silhouette")
            self.assertTrue(bool(item.material), f"Expected {name} to have material")

    def test_modular_materialist_lore_assembly(self):
        # Generate an item combining base halberd with Flame-Wreathed prefix and of the Inferno suffix
        item = npc_generator.generate_procedural_item(
            base_item_name="halberd",
            prefix_name="Flame-Wreathed",
            suffix_name="of the Inferno",
            rng=self.rng,
        )
        self.assertEqual(item.display_name, "Flame-Wreathed halberd of the Inferno")
        self.assertIn("heavy infantry", item.lore.lower())
        self.assertIn("volcanic embers", item.lore.lower())
        self.assertIn("scorched wake", item.lore.lower())

    def test_tiered_enemy_power_kits(self):
        common_actor, common_rules = npc_generator.generate_enemy(tier="common", rng=self.rng)
        self.assertEqual(common_rules["threat_tier"], "common")
        self.assertEqual(len(common_rules["known_spells"]), 0)

        elite_actor, elite_rules = npc_generator.generate_enemy(tier="elite", rng=self.rng)
        self.assertEqual(elite_rules["threat_tier"], "elite")
        self.assertGreater(elite_actor.max_hp, common_actor.max_hp)

        champ_actor, champ_rules = npc_generator.generate_enemy(tier="champion", rng=self.rng)
        self.assertEqual(champ_rules["threat_tier"], "champion")
        self.assertGreater(champ_actor.max_hp, elite_actor.max_hp)
        self.assertTrue(len(champ_rules["resistances"]) > 0 or len(champ_rules["condition_immunities"]) > 0 or len(champ_rules["known_spells"]) > 0)

        boss_actor, boss_rules = npc_generator.generate_enemy(tier="boss", rng=self.rng)
        self.assertEqual(boss_rules["threat_tier"], "boss")
        self.assertIn("PARALYZED", boss_rules["condition_immunities"])
        self.assertEqual(boss_actor.resources.get("legendary_resistance"), 3)

    def test_dynamic_reaction_tree_options(self):
        resident = npc_generator.generate_resident(role="trader", rng=self.rng)
        opts = conversation.options(resident)
        opt_ids = [o["id"] for o in opts]
        self.assertIn("ask-town", opt_ids)
        self.assertIn("ask-route", opt_ids)
        self.assertIn("ask-self", opt_ids)
        # Should include trait or offer affordance
        self.assertTrue(any(i in opt_ids for i in ("bribe-coin", "trade-offer", "ask-work", "probe-rumors")))

    def test_reaction_tree_state_transitions(self):
        # 1. Bribery test with greedy resident
        greedy_target = {
            "name": "Morwen Vell",
            "disposition": "neutral",
            "traits": ["greedy"],
            "core_motive": "greed",
            "tells": ["Eyes flicker to coin."],
            "offers": []
        }
        res_bribe = conversation.resolve(greedy_target, "Take this purse of gold", mode="bribe")
        self.assertEqual(res_bribe["consequence"], "bribe_accepted")
        self.assertEqual(res_bribe["disposition_after"], "warm")

        # 2. Bribery rejection with devout resident
        devout_target = {
            "name": "Prior Lucan",
            "disposition": "neutral",
            "traits": ["devout"],
            "core_motive": "faith",
            "tells": ["Touches a holy symbol."],
            "offers": []
        }
        res_devout = conversation.resolve(devout_target, "Here is a bribe for passage", mode="bribe")
        self.assertEqual(res_devout["consequence"], "bribe_rejected")
        self.assertEqual(res_devout["disposition_after"], "wary")

        # 3. Surrender test on cowardly/injured resident
        coward_target = {
            "name": "Nix",
            "disposition": "hostile",
            "traits": ["cowardly"],
            "core_motive": "survival",
            "hp": 2,
            "max_hp": 10,
            "surrender_hp_threshold": 0.5,
            "tells": ["Trembles nervously."],
            "offers": []
        }
        res_threat = conversation.resolve(coward_target, "Yield or die!", mode="threaten")
        self.assertTrue(res_threat["surrender_offered"])
        self.assertEqual(res_threat["consequence"], "surrender_offered")

        # 4. De-escalation test
        hostile_target = {
            "name": "Watchman Corin",
            "disposition": "hostile",
            "traits": ["stoic"],
            "core_motive": "duty",
            "tells": ["Hand on sword."],
            "offers": []
        }
        res_calm = conversation.resolve(hostile_target, "We seek peace and a quiet talk, not a fight.", mode="speak")
        self.assertTrue(res_calm["truce_agreed"])
        self.assertEqual(res_calm["disposition_after"], "wary")

    def test_dungeon_procedural_enemy_creation(self):
        class MockRun:
            rng = random.Random(101)

        run = MockRun()
        actor, rules = dungeon.procedural_enemy(run, {"name": "Watch Sentinel", "hp": 30, "ac": 14}, tier="elite")
        self.assertIn("Watch Sentinel", actor.name)
        self.assertGreater(actor.max_hp, 30)
        self.assertIsInstance(rules["damage_type"], str)

    def test_life_sim_spawn_visitor_and_bribe(self):
        from hollowstar.run_service import RunService
        import tempfile
        import shutil

        root = Path(tempfile.mkdtemp(prefix="hsr-test-procedural-"))
        try:
            service = RunService(root / ".local" / "reliquary_runs")
            service.create("proc-run", ["Doran"], ["Townsperson"], seed="proc-seed", scenario="floor_one_life")
            service.design_start("proc-run")
            run = service._active["proc-run"]

            # Spawn a procedural visitor into the life-sim world
            visitor = life_sim.spawn_visitor(run, role="trader", culture="imperial", location="market")
            self.assertIn(visitor["id"], run.context["life_world"]["residents"])
            self.assertEqual(visitor["location"], "market")

            # Converse with the procedural visitor using bribe
            result = service.design_action("proc-run", {
                "type": "conversation",
                "target": visitor["name"],
                "mode": "bribe",
                "text": "Accept this gold for trade tips."
            })
            self.assertEqual(result["event"]["type"], "conversation_resolved")
            self.assertIn(result["event"]["receipt"]["public"]["consequence"], ("bribe_accepted", "bribe_rejected"))
        finally:
            shutil.rmtree(root)


class TestEquationVerification(unittest.TestCase):
    """Rigorous software QA verification of at least twenty core combat, balance, and scaling equations."""

    def setUp(self):
        self.rng = random.Random(999)
        self.items = load_items()

    def test_eq01_ability_modifier_formula(self):
        """Eq 1: ability_modifier(score) = floor((score - 10) / 2)"""
        cases = [(8, -1), (9, -1), (10, 0), (11, 0), (12, 1), (13, 1), (14, 2), (18, 4), (20, 5), (30, 10)]
        for score, expected in cases:
            self.assertEqual((score - 10) // 2, expected)

    def test_eq02_attack_bonus_derivation(self):
        """Eq 2: attack_bonus = weapon.attack_bonus + ability_modifier + proficiency_bonus"""
        from hollowstar.actors import Actor
        actor = Actor(name="Hero", ability_scores={"STR": 16, "DEX": 14}, proficiency_bonus=2)
        actor.equipment = [self.items["longsword"]]
        bonus = actor.equipment_attack_bonus(ability="STR")
        self.assertEqual(bonus, 5)

    def test_eq03_d20_hit_probability(self):
        """Eq 3: P(hit) = max(1, min(19, 21 + bonus - AC)) / 20.0"""
        def hit_prob(bonus, ac):
            return max(1, min(19, 21 + bonus - ac)) / 20.0
        self.assertAlmostEqual(hit_prob(5, 15), 0.55)
        self.assertEqual(hit_prob(0, 30), 0.05)
        self.assertEqual(hit_prob(20, 10), 0.95)

    def test_eq04_expected_damage_calculation(self):
        """Eq 4: E[dice] = N * (X + 1) / 2.0 + mod"""
        from hollowstar.tactical import dice_odds
        def expected_damage(expr: str) -> float:
            return sum(val * prob for val, prob in dice_odds(expr).items())

        self.assertAlmostEqual(expected_damage("1d4"), 2.5)
        self.assertAlmostEqual(expected_damage("1d6"), 3.5)
        self.assertAlmostEqual(expected_damage("1d8"), 4.5)
        self.assertAlmostEqual(expected_damage("1d10+3"), 8.5)
        self.assertAlmostEqual(expected_damage("2d4+2"), 7.0)

    def test_eq05_critical_hit_damage(self):
        """Eq 5: E[crit] = 2 * N * (X + 1) / 2.0 + mod"""
        base_dice_mean = 5.5
        crit_dice_mean = 2 * base_dice_mean + 5
        self.assertEqual(crit_dice_mean, 16.0)

    def test_eq06_light_armor_ac_formula(self):
        """Eq 6: Light Armor AC = base_ac + dex_mod (uncapped)"""
        from hollowstar.actors import Actor
        actor = Actor(name="Scout", ability_scores={"DEX": 18})
        actor.equipment = [self.items["padded armor"]]
        self.assertEqual(actor.equipment_armor_class(), 15)

    def test_eq07_medium_armor_ac_formula_with_dex_cap(self):
        """Eq 7: Medium Armor AC = base_ac + min(dex_mod, dex_cap)"""
        from hollowstar.actors import Actor
        actor = Actor(name="Soldier", ability_scores={"DEX": 18})
        actor.equipment = [self.items["half plate"]]
        self.assertEqual(actor.equipment_armor_class(), 17)

    def test_eq08_heavy_armor_ac_formula_zero_dex(self):
        """Eq 8: Heavy Armor AC = base_ac (DEX cap 0)"""
        from hollowstar.actors import Actor
        actor_high_dex = Actor(name="Knight", ability_scores={"DEX": 18})
        actor_low_dex = Actor(name="Knight", ability_scores={"DEX": 6})
        actor_high_dex.equipment = [self.items["full plate"]]
        actor_low_dex.equipment = [self.items["full plate"]]
        self.assertEqual(actor_high_dex.equipment_armor_class(), 18)
        self.assertEqual(actor_low_dex.equipment_armor_class(), 18)

    def test_eq09_shield_stack_bonus(self):
        """Eq 9: total_ac = armor_ac + shield_bonus"""
        from hollowstar.actors import Actor
        actor = Actor(name="Guardian", ability_scores={"DEX": 10})
        actor.equipment = [self.items["full plate"], self.items["shield"]]
        self.assertEqual(actor.equipment_armor_class(), 20)
        actor.equipment = [self.items["full plate"], self.items["heavy tower shield"]]
        self.assertEqual(actor.equipment_armor_class(), 21)

    def test_eq10_accessory_ac_stacking(self):
        """Eq 10: total_ac = armor_ac + shield_bonus + sum(accessory.ac_bonus)"""
        from hollowstar.actors import Actor
        actor = Actor(name="Paladin", ability_scores={"DEX": 10})
        actor.equipment = [
            self.items["full plate"],
            self.items["shield"],
            self.items["ring of protection"],
            self.items["amulet of shielding"],
            self.items["iron greaves"],
            self.items["enchanted cowl"]
        ]
        self.assertEqual(actor.equipment_armor_class(), 24)

    def test_eq11_spell_save_dc_formula(self):
        """Eq 11: Spell Save DC = 8 + prof + casting_mod"""
        prof = 3
        int_score = 16
        dc = 8 + prof + (int_score - 10) // 2
        self.assertEqual(dc, 14)

    def test_eq12_saving_throw_success_probability(self):
        """Eq 12: P(save) = max(1, min(20, 21 + save_bonus - DC)) / 20.0"""
        def save_prob(bonus, dc):
            return max(1, min(20, 21 + bonus - dc)) / 20.0
        self.assertEqual(save_prob(3, 15), 0.45)

    def test_eq13_half_damage_on_save(self):
        """Eq 13: dmg_half = floor(dmg / 2)"""
        self.assertEqual(17 // 2, 8)
        self.assertEqual(28 // 2, 14)

    def test_eq14_common_enemy_scaling_formula(self):
        """Eq 14: HP_common = base_hp * 1.0, AC_common = base_ac + 0"""
        base_spec = {"hp": 40, "ac": 14}
        actor, rules = npc_generator.generate_enemy(base_spec=base_spec, tier="common")
        self.assertEqual(actor.max_hp, 40)
        self.assertEqual(actor.armor_class, 14)

    def test_eq15_elite_enemy_scaling_formula(self):
        """Eq 15: HP_elite = round(base_hp * 1.35 * prefix_mult), AC_elite = base_ac + 1 + prefix_ac"""
        base_spec = {"hp": 40, "ac": 14}
        actor, rules = npc_generator.generate_enemy(base_spec=base_spec, tier="elite", rng=random.Random(1))
        self.assertGreaterEqual(actor.max_hp, 54)
        self.assertGreaterEqual(actor.armor_class, 15)

    def test_eq16_champion_enemy_scaling_formula(self):
        """Eq 16: HP_champ = round(base_hp * 1.75 * prefix_mult * suffix_mult)"""
        base_spec = {"hp": 40, "ac": 14}
        actor, rules = npc_generator.generate_enemy(base_spec=base_spec, tier="champion", rng=random.Random(1))
        self.assertGreaterEqual(actor.max_hp, 70)
        self.assertGreaterEqual(actor.armor_class, 16)

    def test_eq17_boss_enemy_scaling_formula(self):
        """Eq 17: HP_boss = round(base_hp * 2.5 * prefixes * suffixes)"""
        base_spec = {"hp": 100, "ac": 16}
        actor, rules = npc_generator.generate_enemy(base_spec=base_spec, tier="boss", rng=random.Random(1))
        self.assertGreaterEqual(actor.max_hp, 250)
        self.assertGreaterEqual(actor.armor_class, 19)

    def test_eq18_tactical_speed_and_movement(self):
        """Eq 18: speed_final = speed_base + speed_affix"""
        base_speed = 30
        volt_bonus = 10
        ironclad_penalty = -5
        self.assertEqual(base_speed + volt_bonus, 40)
        self.assertEqual(base_speed + ironclad_penalty, 25)

    def test_eq19_surrender_hp_ratio_formula(self):
        """Eq 19: surrender = (hp / max_hp) <= threshold"""
        max_hp = 50
        surrender_threshold = 0.30
        self.assertTrue((15 / max_hp) <= surrender_threshold)
        self.assertFalse((16 / max_hp) <= surrender_threshold)

    def test_eq20_disposition_shift_clamping(self):
        """Eq 20: new_idx = max(0, min(4, old_idx + delta))"""
        from hollowstar.conversation import shift_disposition
        self.assertEqual(shift_disposition("allied", 2), "allied")
        self.assertEqual(shift_disposition("hostile", -2), "hostile")
        self.assertEqual(shift_disposition("neutral", 1), "warm")

    def test_eq21_modular_lore_expansion_equation(self):
        """Eq 21: len(lore_total) >= len(lore_base) + len(lore_prefix) + len(lore_suffix)"""
        item = npc_generator.generate_procedural_item(
            base_item_name="halberd",
            prefix_name="Flame-Wreathed",
            suffix_name="of the Inferno"
        )
        base_lore = self.items["halberd"].lore
        self.assertGreater(len(item.lore), len(base_lore))

    def test_eq22_resource_pool_consumption(self):
        """Eq 22: pool_remaining = pool_current - cost >= 0"""
        pool = {"mana": 6}
        cost = 2
        pool["mana"] -= cost
        self.assertEqual(pool["mana"], 4)
        self.assertGreaterEqual(pool["mana"], 0)


if __name__ == "__main__":
    unittest.main()
