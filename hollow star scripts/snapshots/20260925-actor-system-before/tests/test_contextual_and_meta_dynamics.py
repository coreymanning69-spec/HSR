"""Meta Shop capacity, the Attunement Matrix, the Immunity Lattice, D&D saves,
Turn 0, contextual actions, Gambits, intent grammar, and replay determinism.

Acceptance suite for docs/foundational-contextual-actions-and-meta-dynamics.md
sections 8 and 9 (Phases 1-3 foundation, contextual actions, Gambit additions).
Outcomes that depend on dice are forced through skill and save bonuses, never
by patching the RNG, so every assertion exercises the real resolver.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hollowstar import attunement, dungeon, lattice, policies
from hollowstar import tactical as t
from hollowstar.affix_runtime import attack_adjustment, damage_resistances, effects, materialize
from hollowstar.intent import IntentError, parse_intent
from hollowstar.progression import Progression, UPGRADES, shop_catalog
from hollowstar.run_service import RunService, RunServiceError
from hollowstar.storage import atomic_json
from hollowstar.view_model import build_public_view


def rune(ident, *, prefix=None, suffix=None, rarity="uncommon", identified=True):
    return {"id": ident, "kind": "imprint", "name": ident, "true_name": ident, "identified": identified,
            "rarity": rarity, "slot": "ring_1", "level": 1, "modifiers": [], "temporary": True, "value": 5,
            "prefix": materialize(prefix, "prefix") if prefix else None,
            "suffix": materialize(suffix, "suffix") if suffix else None}


def relic(ident, name, modifier):
    return {"id": ident, "kind": "relic", "relic": True, "name": name, "identified": True, "rarity": "rare",
            "slot": None, "level": 1, "modifiers": [modifier], "temporary": True, "value": 25,
            "prefix": None, "suffix": None}


LATTICE = {row["id"]: row["lattice"] for row in attunement.legendary_catalog().values()}


class Harness(unittest.TestCase):
    seed = "dynamics-seed"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / ".local/reliquary_runs")
        self.service.create("trial", ["Doran", "Wren"], ["Townsperson"], self.seed)
        self.service.design_start("trial")

    def tearDown(self):
        self.tmp.cleanup()

    @property
    def live(self):
        return self.service._active["trial"]

    def act(self, action):
        return self.service.design_action("trial", action)["event"]

    def give(self, item):
        self.live.context["dungeon"]["inventory"][item["id"]] = item
        return item["id"]

    def fight(self):
        self.act({"type": "fight"})
        return self.live

    @staticmethod
    def turn(run, key):
        state = run.context["combat"]
        state["cursor"] = state["order"].index(key)
        state["pending"] = []

    @staticmethod
    def adjacent(run, key="e0", to="p0"):
        x, y, z = run.context["combat"]["positions"][to]
        run.context["combat"]["positions"][key] = [x + 5, y, z]


class MetaShopTest(unittest.TestCase):
    def test_capacity_tracks_cost_clamp_and_serialize_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Progression(Path(tmp))
            identity = "divine:Doran"
            data = progress.load(identity)
            for track in ("prefix_capacity", "suffix_capacity", "legendary_capacity"):
                self.assertEqual(data["upgrades"][track], 0)
                self.assertEqual(UPGRADES[track]["cap"], 5)
            data["platinum"] = data["currency"] = 100
            atomic_json(progress.path(identity), data)
            spent = []
            for _ in range(5):
                before = progress.load(identity)["platinum"]
                spent.append(before - progress.purchase(identity, "prefix_capacity")["platinum"])
            self.assertEqual(spent, [3, 6, 9, 12, 15])
            with self.assertRaisesRegex(ValueError, "capped"):
                progress.purchase(identity, "prefix_capacity")
            legendary = progress.purchase(identity, "legendary_capacity")
            self.assertEqual(legendary["platinum"], 100 - 45 - 4)
            on_disk = json.loads(progress.path(identity).read_text(encoding="utf-8"))
            self.assertEqual(on_disk["upgrades"]["prefix_capacity"], 5)
            self.assertEqual(on_disk["upgrades"]["legendary_capacity"], 1)
            self.assertEqual(on_disk["platinum"], legendary["platinum"])
            rows = {row["key"]: row for row in shop_catalog(on_disk["upgrades"])}
            self.assertTrue(rows["prefix_capacity"]["capped"])
            self.assertIsNone(rows["prefix_capacity"]["next_cost"])
            self.assertEqual(rows["legendary_capacity"]["next_cost"], 8)

    def test_insufficient_platinum_spends_nothing_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Progression(Path(tmp))
            with self.assertRaisesRegex(ValueError, "insufficient Platinum"):
                progress.purchase("divine:Wren", "suffix_capacity")
            self.assertFalse(progress.path("divine:Wren").exists())

    def test_older_saves_without_capacity_tracks_load_at_tier_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Progression(Path(tmp))
            legacy = progress.load("divine:Doran")
            for track in ("prefix_capacity", "suffix_capacity", "legendary_capacity"):
                legacy["upgrades"].pop(track)
            atomic_json(progress.path("divine:Doran"), legacy)
            self.assertEqual(progress.load("divine:Doran")["upgrades"]["suffix_capacity"], 0)


class AttunementTest(Harness):
    def test_launch_freezes_account_capacity_into_the_run(self):
        self.service.create("frozen", ["Doran", "Wren"], ["Townsperson"], "frozen-seed")
        run = self.service._active["frozen"]
        run.context["earned_progress"] = {"Doran": {"upgrades": {"suffix_capacity": 2, "legendary_capacity": 1}}}
        self.service.design_start("frozen")
        self.assertEqual(attunement.capacity(self.service._active["frozen"]),
                         {"prefix": 1, "suffix": 3, "legendary": 2})

    def test_decant_destroys_item_unequips_it_and_attunes_its_suffix(self):
        item = self.give(rune("item-900", suffix="of Frostbite"))
        self.live.context["dungeon"]["imprints"]["p0"] = {"ring_1": item}
        event = self.act({"type": "decant", "item": item, "actor": "p0"})
        self.assertEqual(event["type"], "item_decanted")
        self.assertEqual(event["extracted"], {"suffix": "of Frostbite"})
        self.assertEqual(event["slots_used"]["suffix"], 1)
        d = self.live.context["dungeon"]
        self.assertNotIn(item, d["inventory"])
        self.assertNotIn("ring_1", d["imprints"]["p0"])
        self.assertTrue(event["evidence"]["item_destroyed"])
        sources = [source for _effect, source in effects(self.live, "p0")]
        self.assertTrue(any(source.get("attuned") and source.get("lane") == "suffix" for source in sources))

    def test_full_lane_refuses_without_destroying_then_replaces_by_name(self):
        self.act({"type": "decant", "item": self.give(rune("item-901", suffix="of Frostbite")), "actor": "p0"})
        second = self.give(rune("item-902", suffix="of Silence"))
        with self.assertRaisesRegex((RunServiceError, t.ActionError), r"suffix slots are full \(1/1\)"):
            self.act({"type": "decant", "item": second, "actor": "p0"})
        self.assertIn(second, self.live.context["dungeon"]["inventory"])
        event = self.act({"type": "decant", "item": second, "actor": "p0", "replace": "of Frostbite"})
        self.assertEqual(event["replaced"], {"suffix": "of Frostbite"})
        names = [row["name"] for row in attunement.matrix(self.live, "p0")["suffix"]]
        self.assertEqual(names, ["of Silence"])

    def test_meta_capacity_opens_more_slots_and_duplicates_are_refused(self):
        self.live.context["dungeon"]["upgrades"]["suffix_capacity"] = 1
        self.act({"type": "decant", "item": self.give(rune("item-903", suffix="of Frostbite")), "actor": "p0"})
        self.act({"type": "decant", "item": self.give(rune("item-904", suffix="of Silence")), "actor": "p0"})
        self.assertEqual(len(attunement.matrix(self.live, "p0")["suffix"]), 2)
        self.live.context["dungeon"]["upgrades"]["suffix_capacity"] = 2
        with self.assertRaisesRegex((RunServiceError, t.ActionError), "already attuned"):
            self.act({"type": "decant", "item": self.give(rune("item-905", suffix="of Silence")), "actor": "p0"})

    def test_relic_fills_the_legendary_lane_and_its_modifier_goes_live(self):
        self.assertNotIn("PIERCING", damage_resistances(self.live, "p0"))
        item = self.give(relic("item-906", "Relay Heart", {"effect": "resistance", "value": "PIERCING"}))
        event = self.act({"type": "decant", "item": item, "actor": "p0"})
        self.assertEqual(event["extracted"], {"legendary": "Relay Heart"})
        self.assertIn("PIERCING", damage_resistances(self.live, "p0"))

    def test_ineligible_items_fail_closed(self):
        cases = [(rune("item-907", suffix="of Frostbite", identified=False), "identify"),
                 ({**rune("item-908"), "kind": "potion", "rarity": "common"}, "only Imprints"),
                 (rune("item-909", prefix="Vital"), "no active Prefix")]
        for item, message in cases:
            ident = self.give(item)
            with self.assertRaisesRegex((RunServiceError, t.ActionError), message):
                self.act({"type": "decant", "item": ident, "actor": "p0"})
            self.assertIn(ident, self.live.context["dungeon"]["inventory"])

    def test_decanting_requires_a_safe_pause(self):
        item = self.give(rune("item-910", suffix="of Frostbite"))
        self.fight()
        with self.assertRaisesRegex((RunServiceError, t.ActionError), "safe pause"):
            self.act({"type": "decant", "item": item, "actor": "p0"})

    def test_release_empties_a_slot(self):
        self.act({"type": "decant", "item": self.give(rune("item-911", suffix="of Frostbite")), "actor": "p0"})
        event = self.act({"type": "release_attunement", "actor": "p0", "lane": "suffix", "name": "of Frostbite"})
        self.assertEqual(event["slots_used"]["suffix"], 0)

    def test_checkpoint_resume_rolls_attunement_back_with_the_item(self):
        item = self.give(rune("item-912", suffix="of Frostbite"))
        run = self.live
        run.context["dungeon"]["checkpoint"]["banked"] = dungeon._checkpoint_snapshot(run, "checkpoint:test")
        attunement.decant(run, item, "p0")
        dungeon.resume_checkpoint(run)
        self.assertIn(item, run.context["dungeon"]["inventory"])
        self.assertEqual(attunement.matrix(run, "p0")["suffix"], [])

    def test_design_grant_places_a_legendary_and_public_view_reports_the_matrix(self):
        event = self.act({"type": "grant_legendary", "legendary": "voidborne-shroud"})
        item = event["item"]["id"]
        self.act({"type": "decant", "item": item, "actor": "p0"})
        view = build_public_view(self.service.observe("trial"))
        self.assertEqual(view["attunement"]["capacity"]["legendary"], 1)
        lane = view["attunement"]["actors"]["p0"]["lanes"]["legendary"]
        self.assertEqual(lane[0]["name"], "Voidborne Shroud")
        self.assertEqual(lane[0]["lattice"], ["damage_immunity"])


class ImmunityLatticeTest(Harness):
    def test_slashing_converted_to_arcane_against_arcane_immunity_deals_exactly_zero(self):
        self.live.context["dungeon"]["upgrades"]["legendary_capacity"] = 1
        for legendary in ("prismatic-prism", "voidborne-shroud"):
            item = self.act({"type": "grant_legendary", "legendary": legendary})["item"]["id"]
            self.act({"type": "decant", "item": item, "actor": "p0"})
        run = self.fight()
        hp = t.actor(run, "p0").hp
        event = t.damage(run, "e0", "p0", 30, "SLASHING")
        self.assertEqual(event["damage"], 0)
        self.assertEqual(t.actor(run, "p0").hp, hp)
        self.assertEqual(event["damage_type"], "ARCANE")
        self.assertEqual(event["evidence"]["printed_damage_type"], "SLASHING")
        self.assertEqual(event["evidence"]["conversions"][0]["to"], "ARCANE")
        self.assertEqual(event["evidence"]["lattice_immunity"]["tier"], "ARTIFACT")
        self.assertTrue(event["tell"])
        self.assertIn("physical_invulnerable", lattice.audit(run, "p0")["flags"])

    def test_conversion_alone_changes_what_the_damage_is(self):
        run = self.fight()
        baseline = t.damage(run, "e0", "p0", 32, "SLASHING")["damage"]  # divine plate: 3/8 of slashing
        t.rules(run, "p0")["lattice"] = [lattice.validate(row) for row in LATTICE["prismatic-prism"]]
        converted = t.damage(run, "e0", "p0", 32, "SLASHING")
        self.assertEqual(baseline, 12)
        self.assertEqual(converted["damage_type"], "ARCANE")
        self.assertEqual(converted["damage"], 32)  # plate does not treat arcane

    def test_higher_source_authority_pierces_the_immunity(self):
        run = self.fight()
        t.rules(run, "p0")["lattice"] = [lattice.validate(row) for row in LATTICE["voidborne-shroud"]]
        self.assertEqual(t.damage(run, "e0", "p0", 10, "ARCANE")["damage"], 0)
        t.rules(run, "e0")["authority_tier"] = "BLESSED"
        self.assertEqual(t.damage(run, "e0", "p0", 10, "ARCANE")["damage"], 10)

    def test_consequence_denial_refuses_conditions_from_any_source(self):
        run = self.fight()
        t.rules(run, "p0")["lattice"] = [lattice.validate(row) for row in LATTICE["unyielding-stance"]]
        refused = t.condition(run, "p0", "STUNNED", 1)
        self.assertFalse(refused["applied"])
        self.assertEqual(refused["reason"], "consequence denied")
        self.assertNotIn("STUNNED", t.actor(run, "p0").statuses)

    def test_lattice_rows_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "tell"):
            lattice.validate({"kind": "damage_immunity", "tags": ["FIRE"]})
        with self.assertRaisesRegex(ValueError, "unknown damage tags"):
            lattice.validate({"kind": "damage_immunity", "tags": ["PLASMA"], "tell": "x"})
        run = self.fight()
        with self.assertRaisesRegex(t.ActionError, "Immunity Lattice"):
            t.begin(run, {"p0": {"identity": "doran", "lattice": [{"kind": "nonsense", "tell": "x"}]}})


class SavingThrowTest(Harness):
    def test_con_save_dc15_negates_a_poison_rider_and_a_failed_save_applies_it(self):
        run = self.fight()
        rider = {"name": "POISONED", "duration": 2, "save": {"ability": "CON", "dc": 15}}
        t.rules(run, "e0")["saves"]["CON"] = 50
        saved = t.apply_rider(run, "p0", "e0", rider)
        self.assertFalse(saved["applied"])
        self.assertEqual(saved["reason"], "saving throw")
        t.rules(run, "e0")["saves"]["CON"] = -50
        failed = t.apply_rider(run, "p0", "e0", rider)
        self.assertTrue(failed["applied"])
        self.assertFalse(failed["save"]["success"])
        self.assertIn("POISONED", t.actor(run, "e0").statuses)

    def test_wis_save_dc15_negates_a_fear_rider(self):
        run = self.fight()
        t.rules(run, "e0")["saves"]["WIS"] = 50
        result = t.apply_rider(run, "p0", "e0", {"name": "FRIGHTENED", "duration": 1, "mental": True,
                                                 "save": {"ability": "WIS", "dc": 15}})
        self.assertFalse(result["applied"])
        self.assertNotIn("FRIGHTENED", t.actor(run, "e0").statuses)

    def test_ability_threshold_refuses_mundane_riders_but_not_magical_ones(self):
        run = self.fight()  # Doran: CON 18
        mundane = t.apply_rider(run, "e0", "p0", {"name": "POISONED", "duration": 1})
        self.assertEqual(mundane["reason"], "ability threshold immunity")
        self.assertEqual(mundane["threshold"]["ability"], "CON")
        magical = t.apply_rider(run, "e0", "p0", {"name": "POISONED", "duration": 1, "magical": True})
        self.assertTrue(magical["applied"])

    def test_affix_rider_saves_flow_from_content_to_the_attack_rider(self):
        from hollowstar.loader import _effect
        parsed = _effect({"name": "x", "phase": "CONSEQUENCE", "direction": "GRANT",
                          "inflicts_status": "POISONED", "save_ability": "con", "save_dc": 15})
        self.assertEqual((parsed.save_ability, parsed.save_dc), ("CON", 15))
        self.act({"type": "decant", "item": self.give(rune("item-913", suffix="of Frostbite")), "actor": "p0"})
        attuned = attunement.matrix(self.live, "p0")["suffix"][0]
        rider_effect = next(e for e in attuned["effects"] if e["phase"] == "CONSEQUENCE")
        rider_effect.update({"save_ability": "CON", "save_dc": 15})
        run = self.fight()
        _amount, _applied, riders = attack_adjustment(run, "p0", "e0", 10)
        self.assertEqual(riders[0]["save"], {"ability": "CON", "dc": 15})

    def test_silenced_rider_applies_instead_of_crashing_and_blocks_verbal_casting(self):
        from hollowstar.spells import cast
        run = self.fight()
        result = t.apply_rider(run, "p0", "p1", {"name": "SILENCED", "duration": 2})
        self.assertTrue(result["applied"])
        with self.assertRaisesRegex(t.ActionError, "silenced"):
            cast(run, "p1", {"spell": "Healing Word@5e", "targets": ["p0"]})
        try:
            cast(run, "p1", {"spell": "Healing Word@5e", "targets": ["p0"], "metamagic": ["silent"]})
        except t.ActionError as exc:
            self.assertNotIn("silenced", str(exc))


class TurnZeroTest(Harness):
    def decant_legendary(self, legendary, actor="p0"):
        item = self.act({"type": "grant_legendary", "legendary": legendary})["item"]["id"]
        return self.act({"type": "decant", "item": item, "actor": actor})

    def test_wards_then_auras_resolve_before_round_one_initiative(self):
        self.live.context["dungeon"]["upgrades"]["legendary_capacity"] = 1
        self.decant_legendary("aegis-of-first-light")
        self.decant_legendary("heralds-haste")
        run = self.fight()
        turn_zero = run.context["combat"]["turn_zero"]
        self.assertEqual([row["type"] for row in turn_zero], ["turn_zero_ward", "turn_zero_condition"])
        self.assertEqual(turn_zero[0]["ward_after"], t.actor(run, "p0").max_hp // 2)
        self.assertEqual(t.actor(run, "p0").resources["ward"], t.actor(run, "p0").max_hp // 2)
        self.assertIn("HASTED", t.actor(run, "p0").statuses)
        self.assertEqual(run.round_number, 1)

    def test_a_pre_emptive_strike_can_end_the_fight_before_initiative(self):
        self.decant_legendary("royal-arrogance")
        strike = attunement.matrix(self.live, "p0")["legendary"][0]["lattice"][0]
        strike.update({"dice": "200", "save": None})
        event = self.act({"type": "fight"})
        run = self.live
        self.assertTrue(run.context["combat"]["complete"])
        self.assertTrue(event.get("turn_zero_resolution"))
        self.assertIn("reward", event)
        strike_event = run.context["combat"]["turn_zero"][0]
        self.assertEqual(strike_event["type"], "turn_zero_strike")
        self.assertEqual(strike_event["defeated"], ["e0"])

    def test_encounters_without_turn_zero_rows_are_unchanged(self):
        run = self.fight()
        self.assertEqual(run.context["combat"]["turn_zero"], [])
        self.assertFalse(run.context["combat"]["complete"])


class ContextualActionTest(Harness):
    def setUp(self):
        super().setUp()
        self.combat = self.fight()
        self.turn(self.combat, "p0")
        self.adjacent(self.combat)

    def test_shove_pushes_five_feet_and_replaces_one_attack(self):
        run = self.combat
        t.actor(run, "e0").skill_bonuses.update({"Athletics": -50, "Acrobatics": -50})
        event = t.apply(run, {"type": "shove", "actor": "p0", "target": "e0"})
        self.assertEqual(event["outcome"], "pushed")
        self.assertEqual(t.position(run, "e0"), [20, 10, 0])
        economy = t.economy(run, "p0")
        self.assertEqual((economy["action"], economy["attacks"]), (0, 3))
        attack = t.apply(run, {"type": "attack", "actor": "p0", "target": "e0"})
        self.assertEqual(attack["type"], "attack")

    def test_trip_knocks_prone_and_a_lost_contest_changes_nothing(self):
        run = self.combat
        t.actor(run, "e0").skill_bonuses.update({"Athletics": 100})
        lost = t.apply(run, {"type": "trip", "actor": "p0", "target": "e0"})
        self.assertEqual(lost["outcome"], "resisted")
        self.assertNotIn("PRONE", t.actor(run, "e0").statuses)
        t.actor(run, "e0").skill_bonuses.update({"Athletics": -50, "Acrobatics": -50})
        won = t.apply(run, {"type": "trip", "actor": "p0", "target": "e0"})
        self.assertEqual(won["outcome"], "prone")
        self.assertIn("PRONE", t.actor(run, "e0").statuses)

    def test_strength_threshold_refuses_a_mundane_knockdown(self):
        run = self.combat
        self.turn(run, "e0")
        t.actor(run, "e0").skill_bonuses.update({"Athletics": 100})
        event = t.apply(run, {"type": "trip", "actor": "e0", "target": "p0"})
        self.assertEqual(event["outcome"], "refused")
        self.assertEqual(event["threshold"]["ability"], "STR")
        self.assertNotIn("PRONE", t.actor(run, "p0").statuses)

    def test_grapple_zeroes_speed_until_the_target_breaks_free(self):
        run = self.combat
        t.actor(run, "e0").skill_bonuses.update({"Athletics": -50, "Acrobatics": -50})
        event = t.apply(run, {"type": "grapple", "actor": "p0", "target": "e0"})
        self.assertEqual(event["outcome"], "grappled")
        self.assertIsNone(t.move_cost(run, "e0", [45, 10, 0]))
        self.turn(run, "e0")
        t.actor(run, "e0").skill_bonuses.update({"Athletics": 100})
        escape = t.apply(run, {"type": "escape_grapple", "actor": "e0"})
        self.assertEqual(escape["outcome"], "escaped")
        self.assertNotIn("GRAPPLED", t.actor(run, "e0").statuses)
        self.assertNotIn("grappling", t.rules(run, "p0"))

    def test_size_limit_is_enforced(self):
        run = self.combat
        t.rules(run, "e0")["size"] = "huge"
        with self.assertRaisesRegex(t.ActionError, "more than one size larger"):
            t.apply(run, {"type": "shove", "actor": "p0", "target": "e0"})

    def test_help_grants_advantage_on_the_allys_next_attack_only(self):
        run = self.combat
        run.context["combat"]["positions"]["p1"] = [15, 15, 0]
        self.turn(run, "p1")
        helped = t.apply(run, {"type": "help", "actor": "p1", "target": "e0", "ally": "p0"})
        self.assertEqual(helped["ally"], "p0")
        self.turn(run, "p0")
        attack = t.apply(run, {"type": "attack", "actor": "p0", "target": "e0"})
        self.assertTrue(attack["evidence"]["advantage"])
        self.assertEqual(attack["evidence"]["help"]["from"], "p1")
        self.assertNotIn("help_advantage", t.rules(run, "p0"))

    def test_catalog_lists_legal_targets_and_the_public_view_carries_help_text(self):
        rows = {row["id"]: row for row in t.contextual_actions(self.combat, "p0")}
        self.assertTrue(rows["shove"]["available"])
        self.assertEqual(rows["shove"]["targets"], ["e0"])
        self.assertIn("Replaces one attack", rows["shove"]["help"])
        self.assertFalse(rows["cast"]["available"])  # Doran has no implemented spellcasting
        view = build_public_view(self.service.observe("trial"))
        actions = {row["id"]: row for row in view["available_actions"]}
        self.assertIn("shove", actions)
        self.assertEqual(actions["shove"]["category"], "tactical")
        self.assertTrue(view["combat"]["contextual_actions"])


class GambitTest(Harness):
    def setUp(self):
        super().setUp()
        self.combat = self.fight()
        self.turn(self.combat, "p0")

    def test_priority_order_with_new_conditions_and_selectors(self):
        run = self.combat
        self.adjacent(run)
        macros = [{"priority": 1, "when": {"round_number_gte": 5}, "then": {"type": "attack", "target": "nearest_enemy"}},
                  {"priority": 2, "when": {"enemy_adjacent": True},
                   "then": {"type": "shove", "target": "adjacent_enemy", "mode": "prone"}},
                  {"priority": 3, "then": {"type": "attack", "target": "highest_hp_enemy"}}]
        self.assertEqual(policies.macro_action(run, "p0", macros),
                         {"type": "shove", "target": "e0", "mode": "prone", "actor": "p0"})

    def test_unknown_conditions_fail_closed(self):
        macros = [{"priority": 1, "when": {"moon_phase": "full"}, "then": {"type": "dodge"}},
                  {"priority": 2, "then": {"type": "attack", "target": "nearest_enemy"}}]
        self.assertEqual(policies.macro_action(self.combat, "p0", macros)["type"], "attack")

    def test_cocoon_clock_threshold_triggers(self):
        run = self.combat
        d = run.context["dungeon"]
        d["rooms"][f"{d['floor']}:{d['room']}"]["cocoon"] = {"rounds": 20, "opened": False}
        macros = [{"priority": 1, "when": {"cocoon_rounds_gte": 15}, "then": {"type": "dodge"}},
                  {"priority": 2, "then": {"type": "end_turn"}}]
        run.round_number = 14
        self.assertEqual(policies.macro_action(run, "p0", macros)["type"], "end_turn")
        run.round_number = 15
        self.assertEqual(policies.macro_action(run, "p0", macros)["type"], "dodge")

    def test_resource_gated_gambit_spends_the_resource_then_falls_through(self):
        run = self.combat
        doran = t.actor(run, "p0")
        doran.hp = doran.max_hp // 4
        doran.resources["second_wind"] = 1
        macros = [{"priority": 1, "when": {"self_hp_below": 50, "has_resource": "second_wind"},
                   "then": {"type": "second_wind"}},
                  {"priority": 2, "then": {"type": "dodge"}}]
        action = policies.macro_action(run, "p0", macros)
        self.assertEqual(action["type"], "second_wind")
        t.apply(run, action)
        self.assertEqual(doran.resources["second_wind"], 0)
        self.assertEqual(policies.macro_action(run, "p0", macros)["type"], "dodge")

    def test_an_illegal_gambit_is_skipped_on_the_actors_turn(self):
        macros = [{"priority": 1, "then": {"type": "grapple", "target": "nearest_enemy"}},
                  {"priority": 2, "then": {"type": "attack", "target": "nearest_enemy"}}]
        # e0 is 30 ft away: grapple is not legal, so the processor moves on.
        self.assertEqual(policies.macro_action(self.combat, "p0", macros)["type"], "attack")


class IntentGrammarTest(unittest.TestCase):
    def test_contextual_phrases(self):
        cases = {
            "dodge": {"type": "dodge", "actor": "p0"},
            "Doran shoves e0 prone": {"type": "shove", "actor": "p0", "target": "e0", "mode": "prone"},
            "trip e0": {"type": "trip", "actor": "p0", "target": "e0"},
            "grab e0": {"type": "grapple", "actor": "p0", "target": "e0"},
            "break free": {"type": "escape_grapple", "actor": "p0"},
            "escape the grapple": {"type": "escape_grapple", "actor": "p0"},
            "help wren against e0": {"type": "help", "actor": "p0", "ally": "p1", "target": "e0"},
            "decant item-3 for wren replacing of Frostbite":
                {"type": "decant", "actor": "p1", "item": "item-3", "replace": "of Frostbite"},
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_intent(text), expected)

    def test_bare_help_is_a_clear_error(self):
        with self.assertRaisesRegex(IntentError, "help needs a foe"):
            parse_intent("help")


class ReplayDeterminismTest(unittest.TestCase):
    def transcript(self, root):
        service = RunService(Path(root) / ".local/reliquary_runs")
        service.create("replay", ["Doran", "Wren"], ["Townsperson"], "replay-seed")
        service.design_start("replay")
        run = service._active["replay"]
        run.context["dungeon"]["inventory"]["item-950"] = rune("item-950", suffix="of Frostbite")
        service.design_action("replay", {"type": "decant", "item": "item-950", "actor": "p0"})
        granted = service.design_action("replay", {"type": "grant_legendary", "legendary": "aegis-of-first-light"})
        service.design_action("replay", {"type": "decant", "item": granted["event"]["item"]["id"], "actor": "p0"})
        service.design_action("replay", {"type": "configure_macros", "macros": {"p0": [
            {"priority": 1, "when": {"enemy_adjacent": True}, "then": {"type": "trip", "target": "adjacent_enemy"}},
            {"priority": 2, "then": {"type": "attack", "target": "nearest_enemy"}}]}})
        service.design_action("replay", {"type": "fight"})
        for _ in range(60):
            run = service._active["replay"]
            if run.context["combat"]["complete"]:
                break
            service.design_action("replay", policies.combat_action(run))
        run = service._active["replay"]
        return json.dumps({"combat": run.context["combat"]["events"], "dungeon": run.context["dungeon"]["events"],
                           "rng": run.rng.calls}, sort_keys=True, default=str)

    def test_identical_seeds_reproduce_identical_transcripts(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            transcript = self.transcript(first)
            self.assertEqual(transcript, self.transcript(second))
        # Not vacuous: the build, the Gambits, and real combat all ran.
        self.assertIn("item_decanted", transcript)
        self.assertIn("macros_configured", transcript)
        self.assertIn('"type": "attack"', transcript)


class SurfaceTest(unittest.TestCase):
    def test_host_advertises_and_serves_the_meta_shop(self):
        from hollowstar.host import HSRHost
        workspace = Path(__file__).resolve().parents[2]  # the Court root, as tests/test_host.py uses
        host = HSRHost.from_options(workspace)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        commands = host.handle({"id": "c", "command": "inspect", "target": "capabilities"})["result"]["capabilities"]["commands"]
        for command in ("decant", "release_attunement", "meta_shop", "meta_shop_purchase"):
            self.assertIn(command, commands)
        reply = host.handle({"id": "m", "command": "meta_shop", "identity": "hsr:MetaShopProbe"})
        self.assertTrue(reply["ok"])
        rows = {row["key"]: row for row in reply["result"]["meta_shop"]}
        self.assertEqual(rows["prefix_capacity"]["next_cost"], 3)
        self.assertEqual(rows["legendary_capacity"]["next_cost"], 4)

    def test_mcp_exposes_first_class_tools(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import hsr_mcp_server as mcp
        names = {tool["name"] for tool in mcp.TOOLS}
        for name in ("hsr_meta_shop", "hsr_meta_shop_purchase", "hsr_decant_item",
                     "hsr_contextual_action", "hsr_configure_gambits"):
            self.assertIn(name, names)
        tool = mcp.TOOLS_BY_NAME["hsr_contextual_action"]
        fields = tool["fields"]({"run_id": "r", "action": {"type": "shove", "target": "e0"}})
        self.assertEqual((tool["command"], fields["intent"]), ("design_turn", "shove"))


if __name__ == "__main__":
    unittest.main()
