"""Forecasts, previews and planning agree with the resolver they predict."""
import copy
import itertools
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hollowstar.run_service import RunService
from hollowstar.rng import RunRNG
from hollowstar import tactical as t
from hollowstar import spells
from hollowstar import policies
from hollowstar import monsters


def forced_d20(value):
    return patch.object(RunRNG, "d20", lambda self: value)


def brute(expression, *, critical=False, maximize=False):
    count, sides, modifier = t.dice_terms(expression)
    if not sides:
        return {modifier: 1.0}
    count *= 2 if critical else 1
    if maximize:
        return {count * sides + modifier: 1.0}
    out = {}
    faces = list(itertools.product(range(1, sides + 1), repeat=count))
    for roll in faces:
        key = max(0, sum(roll) + modifier)
        out[key] = out.get(key, 0.0) + 1 / len(faces)
    return out


class OddsTest(unittest.TestCase):
    def assertOdds(self, first, second):
        self.assertEqual(set(k for k, v in first.items() if v > 1e-12), set(k for k, v in second.items() if v > 1e-12))
        for key in first:
            self.assertAlmostEqual(first[key], second.get(key, 0.0), places=9)

    def test_d20_odds_match_enumeration(self):
        for adv, dis in ((False, False), (True, False), (False, True), (True, True)):
            odds = t.d20_odds(adv, dis)
            counts = [0] * 21
            pairs = list(itertools.product(range(1, 21), repeat=2))
            for a, b in pairs:
                natural = max(a, b) if adv and not dis else min(a, b) if dis and not adv else a
                counts[natural] += 1
            for n in range(1, 21):
                self.assertAlmostEqual(odds[n], counts[n] / len(pairs))

    def test_attack_and_check_odds_match_enumeration(self):
        for bonus, ac, threshold in ((5, 15, 20), (16, 17, 20), (-2, 25, 19), (30, 10, 16), (0, 40, 20)):
            odds = t.attack_odds(bonus, ac, threshold=threshold)
            hits = [n for n in range(1, 21) if n != 1 and (n >= threshold or n + bonus >= ac)]
            self.assertAlmostEqual(odds["hit"], len(hits) / 20)
            self.assertAlmostEqual(odds["crit"], len([n for n in range(2, 21) if n >= threshold]) / 20)
            self.assertAlmostEqual(t.check_odds(bonus, ac), len([n for n in range(1, 21) if n + bonus >= ac]) / 20)

    def test_contest_odds_match_enumeration(self):
        for a, b in ((0, 0), (5, 2), (-1, 7)):
            wins = sum(1 for x in range(1, 21) for y in range(1, 21) if x + a > y + b)
            self.assertAlmostEqual(t.contest_odds(a, b), wins / 400)

    def test_dice_odds_match_enumeration(self):
        for expression in ("2d6+1", "3d4", "1d8-3", "1d20", "7", 12):
            self.assertOdds(t.dice_odds(expression), brute(expression))
        self.assertOdds(t.dice_odds("1d8+2", critical=True), brute("1d8+2", critical=True))
        self.assertOdds(t.dice_odds("2d6", maximize=True), {12: 1.0})
        self.assertOdds(t.dice_odds("1d4", critical=True, maximize=True), {8: 1.0})

    def test_combinators(self):
        self.assertOdds(t.add_odds(t.dice_odds("1d4"), t.dice_odds("1d6")), _sum(brute("1d4"), brute("1d6")))
        doubled = t.map_odds(t.dice_odds("1d6"), lambda v: v * 2)
        self.assertOdds(doubled, {v * 2: 1 / 6 for v in range(1, 7)})
        self.assertAlmostEqual(t.mean_odds(t.dice_odds("2d6")), 7.0)
        self.assertAlmostEqual(t.odds_at_least(t.dice_odds("1d20"), 15), 6 / 20)


def _sum(first, second):
    out = {}
    for a, p in first.items():
        for b, q in second.items():
            out[a + b] = out.get(a + b, 0.0) + p * q
    return out


class CombatFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / ".local/reliquary_runs")
        self.service.create("trial", ["Doran", "Wren"], ["Townsperson"], "gameplay-seed")
        self.service.design_start("trial")
        self.service.design_action("trial", {"type": "fight"})
        self.run = self.service._active["trial"]
        # p0 Doran, p1 Wren, e0/e1 town watch. No reactions to muddy one roll.
        for key in t.actors(self.run):
            t.economy(self.run, key)["reaction"] = 0
        self.run.context["combat"]["terrain"]["daylight"] = False

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self):
        return copy.deepcopy(self.run.context), self.run.rng.getstate(), self.run.rng.calls, \
            [(a.hp, dict(a.resources), dict(a.statuses)) for a in t.actors(self.run).values()]


class ForecastAttackTest(CombatFixture):
    def test_forecast_matches_every_forced_d20(self):
        for mode in ("weapon", "dagger"):
            forecast = t.forecast_attack(self.run, "p0", "e0", mode)
            self.assertTrue(forecast["legal"])
            hits = crits = 0
            for natural in range(1, 21):
                trial = copy.deepcopy(self.run)
                with forced_d20(natural):
                    event = t.weapon_attack(trial, "p0", "e0", mode)
                hits += event["roll"]["success"]
                crits += event["roll"]["success"] and event["critical"]
                if event["roll"]["success"]:
                    lo, hi = forecast["damage_range"]
                    self.assertTrue(lo <= event["result"]["damage"] <= hi)
            self.assertAlmostEqual(forecast["hit"], hits / 20)
            self.assertAlmostEqual(forecast["crit"], crits / 20)

    def test_forecast_leaves_the_run_untouched(self):
        before = self.snapshot()
        t.forecast_attack(self.run, "p0", "e0")
        t.forecast_attack(self.run, "p1", "e0", bonus=True)
        policies.candidate_actions(self.run, "p1")
        spells.preview_cast(self.run, "p1", {"spell": "Fireball@5e", "center": [40, 10, 0]})
        self.assertEqual(self.snapshot(), before)

    def test_precision_die_is_one_shot(self):
        r = t.rules(self.run, "p0")
        permanent = r.get("precision_bonus", 0)
        r["precision_die"] = 5
        with forced_d20(10):
            event = t.weapon_attack(self.run, "p0", "e0")
        self.assertEqual(event["evidence"]["precision_die"], 5)
        self.assertNotIn("precision_die", r)
        self.assertEqual(r.get("precision_bonus", 0), permanent)

    def test_mitigate_matches_damage(self):
        t.rules(self.run, "e0")["resistances"] = ["FIRE"]
        t.rules(self.run, "e1")["vulnerabilities"] = ["ICE"]
        for target, kind in (("e0", "FIRE"), ("e1", "ICE"), ("e0", "PIERCING")):
            profile = t.mitigation(self.run, "p1", target, kind)
            for amount in (0, 1, 7, 20):
                trial = copy.deepcopy(self.run)
                hp = t.actor(trial, target).hp
                event = t.damage(trial, "p1", target, amount, kind)
                self.assertEqual(event["damage"], min(hp, t.mitigate(amount, profile)))

    def test_party_forecasts_are_uninformed_until_seen(self):
        t.rules(self.run, "e0")["resistances"] = ["PIERCING"]
        informed = t.forecast_attack(self.run, "p0", "e0", "dagger", informed=True)
        blind = t.forecast_attack(self.run, "p0", "e0", "dagger", informed=False)
        # Doran's non-Cleaver attacks bypass resistance, so use the Cleaver-free
        # dagger only when bypass is off; otherwise compare a plain resisted type.
        if informed["expected_damage"] == blind["expected_damage"]:
            t.rules(self.run, "e0")["resistances"] = ["RADIANT"]
            informed = t.forecast_attack(self.run, "p1", "e0", bonus=True, informed=True)
            blind = t.forecast_attack(self.run, "p1", "e0", bonus=True, informed=False)
            kind, source = "RADIANT", "p1"
        else:
            kind, source = "PIERCING", "p0"
        self.assertLess(informed["expected_damage"], blind["expected_damage"] + 1e-9)
        self.assertTrue(policies.informed(self.run, "e0"))
        self.assertFalse(policies.informed(self.run, "p0"))
        t.damage(self.run, source, "e0", 10, kind)
        seen = t.knowledge(self.run, "p")["creatures"][t.actor(self.run, "e0").name]["damage"][kind]
        self.assertIn(seen["outcome"], {"resisted", "normal"})
        again = t.forecast_attack(self.run, source, "e0", "dagger" if source == "p0" else None,
                                  bonus=source == "p1", informed=False)
        informed = t.forecast_attack(self.run, source, "e0", "dagger" if source == "p0" else None,
                                     bonus=source == "p1", informed=True)
        self.assertAlmostEqual(again["expected_damage"], informed["expected_damage"])


class SpellTest(CombatFixture):
    def bolt(self, **extra):
        return spells.cast(self.run, "p1", {"spell": "Arcane Bolt@HSR", "target": "e0", **extra})

    def test_healing_word_accepts_target(self):
        self.run.party[0].hp = 100
        receipt = spells.cast(self.run, "p1", {"spell": "Healing Word@5e", "target": "p0"})
        self.assertEqual(receipt["targets"], ["p0"])
        self.assertGreater(receipt["healing"], 0)
        heal = receipt["events"][0]
        self.assertIn("rolled", heal["evidence"])

    def test_default_wren_policy_heal_is_accepted_by_the_engine(self):
        state = self.run.context["combat"]
        state["cursor"] = state["order"].index("p1")
        self.run.party[0].hp = 100
        action = policies.combat_action(self.run)
        self.assertEqual(action["spell"], "Healing Word@5e")
        result = t.apply(self.run, action)
        self.assertGreater(self.run.party[0].hp, 100, result)

    def test_spell_attack_reads_cover(self):
        self.run.context["combat"]["terrain"]["cover"]["e0"] = "half"
        with forced_d20(10):
            event = self.bolt()["events"][0]
        self.assertEqual(event["evidence"]["target_ac"], t.actor(self.run, "e0").armor_class + 2)
        self.assertEqual(event["evidence"]["cover"], "half")

    def test_spell_attack_reads_prone_at_range(self):
        t.actor(self.run, "e0").statuses["PRONE"] = 1
        with forced_d20(10):
            event = self.bolt()["events"][0]
        self.assertIn("target prone", event["evidence"]["attack_reasons"]["disadvantage"])
        self.assertTrue(event["evidence"]["disadvantage"])

    def test_spell_attack_consumes_help(self):
        t.rules(self.run, "p1")["help_advantage"] = {"target": "e0", "helper": "p0"}
        with forced_d20(10):
            event = self.bolt()["events"][0]
        self.assertIn("helped", event["evidence"]["attack_reasons"]["advantage"])
        self.assertNotIn("help_advantage", t.rules(self.run, "p1"))

    def test_spell_hit_pops_distraction(self):
        t.rules(self.run, "e0")["distracted_by"] = "p0"
        with forced_d20(19):
            event = self.bolt()["events"][0]
        self.assertTrue(event["attack"]["success"])
        self.assertNotIn("distracted_by", t.rules(self.run, "e0"))

    def test_maximize_and_empower_survive_a_crit(self):
        with forced_d20(20):
            receipt = self.bolt(metamagic=["maximize", "empower"])
        event = receipt["events"][0]
        self.assertTrue(event["critical"])
        self.assertTrue(receipt["critical"])
        part = event["evidence"]["damage_parts"][0]
        self.assertEqual(part["total"], 20)  # 1d10 crit, maximized: 2 x 10
        self.assertTrue(part["maximized"])
        self.assertEqual(event["evidence"]["damage_steps"], [{"label": "empower ×1.5", "amount": 30}])
        self.assertEqual(event["result"]["raw"], 30)

    def test_a_miss_rolls_no_damage(self):
        calls = self.run.rng.calls
        with forced_d20(1):
            event = self.bolt()["events"][0]
        self.assertIsNone(event["result"])
        self.assertEqual(self.run.rng.calls, calls)

    def test_save_evidence_carries_half(self):
        self.run.context["combat"]["positions"]["e0"] = [40, 40, 0]
        with patch("hollowstar.spells.saving_throw", return_value={"success": True, "dc": 22}):
            receipt = spells.cast(self.run, "p1", {"spell": "Fireball@5e", "center": [40, 40, 0]})
        event = next(ev for ev in receipt["events"] if ev["target"] == "e0")
        self.assertEqual(event["evidence"]["damage_steps"][-1]["label"], "saved: half")

    def test_contained_target_does_not_crash_a_save_spell(self):
        t.rules(self.run, "e0")["contained_by"] = "forcecage-test"
        receipt = spells.cast(self.run, "p1", {"spell": "Sacred Flame@5e", "target": "e0"})
        self.assertEqual(receipt["events"][0]["reason"], "target is contained")

    def test_preview_legality_equals_cast(self):
        wren = self.run.party[1]
        cases = [
            {"spell": "Arcane Bolt@HSR", "target": "e0"},
            {"spell": "Arcane Bolt@HSR", "targets": ["e0", "e1"]},
            {"spell": "Arcane Bolt@HSR", "target": "p0"},
            {"spell": "Healing Word@5e", "target": "p0"},
            {"spell": "Healing Word@5e"},
            {"spell": "Fireball@5e", "center": [40, 10, 0]},
            {"spell": "Fireball@5e", "center": [7, 10, 0]},
            {"spell": "Fireball@5e", "target": "e0"},
            {"spell": "Magic Missile@5e", "target": "e1", "metamagic": ["twin"]},
            {"spell": "Scorching Ray@5e", "target": "e0", "metamagic": ["quicken", "empower"]},
            {"spell": "Scorching Ray@5e", "target": "e0", "metamagic": ["bogus"]},
            {"spell": "Imprisonment@5e", "target": "e0"},
            {"spell": "Nope@5e", "target": "e0"},
            {"spell": "Hold Monster@5e", "target": "e0"},
            {"spell": "Sacred Flame@5e", "target": "e1"},
        ]
        states = [lambda: None,
                  lambda: wren.statuses.__setitem__("SILENCED", 1),
                  lambda: t.economy(self.run, "p1").update(action=0),
                  lambda: [wren.resources.__setitem__(k, 0) for k in list(wren.resources) if k.startswith("slot_")]]
        for setup in states:
            setup()
            for action in cases:
                preview = spells.preview_cast(self.run, "p1", action)
                trial = copy.deepcopy(self.run)
                try:
                    spells.cast(trial, "p1", copy.deepcopy(action))
                    ok, reason = True, None
                except t.ActionError as exc:
                    ok, reason = False, str(exc)
                self.assertEqual(preview["legal"], ok, (action, preview["reason"], reason))
                if not ok:
                    self.assertEqual(preview["reason"], reason)

    def test_preview_prices_a_heal(self):
        self.run.party[0].hp = 10
        preview = spells.preview_cast(self.run, "p1", {"spell": "Healing Word@5e", "target": "p0"})
        # Doran's healing is maximized: 1d4+5 is always 9.
        self.assertAlmostEqual(preview["expected_healing"], 9.0)
        self.assertEqual(preview["cost"], {"economy": {"bonus": 1}, "resources": {"slot_1_general": 1}})


class PlanningTest(CombatFixture):
    def test_candidates_are_legal_canonical_actions(self):
        rows = policies.candidate_actions(self.run, "p1")
        self.assertTrue(rows)
        for row in rows[:12]:
            self.assertTrue(row["legal"])
            trial = copy.deepcopy(self.run)
            state = trial.context["combat"]
            state["cursor"] = state["order"].index("p1")
            t.apply(trial, copy.deepcopy(row["action"]))

    def test_plan_goals(self):
        self.run.party[0].hp = 300
        heal = policies.plan_action(self.run, "p1", "heal")
        self.assertEqual(heal["target"], "p0")
        damage = policies.plan_action(self.run, "p1", "damage")
        self.assertEqual(damage["actor"], "p1")
        cheap = policies.plan_action(self.run, "p1", "damage", spend=False)
        self.assertTrue(cheap is None or cheap.get("spell") in {None, "Arcane Bolt@HSR", "Sacred Flame@5e"})
        self.run.opposition[1].hp = 3
        self.assertEqual(policies._macro_target(self.run, "p1", "killable_enemy"), "e1")
        kill = policies.plan_action(self.run, "p1", "kill")
        self.assertIsNotNone(kill)

    def test_gambit_plan_and_forecast_conditions(self):
        state = self.run.context["combat"]
        state["cursor"] = state["order"].index("p0")
        certain = [{"id": "sure", "priority": 1, "when": {"hit_chance_gte": 101},
                    "then": {"type": "attack", "target": "nearest_enemy"}},
                   {"id": "plan", "priority": 2, "then": {"type": "plan", "goal": "damage"}}]
        action = policies.macro_action(self.run, "p0", certain)
        self.assertEqual(action["type"], "attack")
        self.assertIn("mode", action)  # came from the planner, not the first gambit
        likely = [{"id": "likely", "when": {"hit_chance_gte": 50, "expected_damage_gte": 1},
                   "then": {"type": "attack", "target": "likeliest_hit_enemy"}}]
        self.assertEqual(policies.macro_action(self.run, "p0", likely)["type"], "attack")

    def test_spell_ready_and_concentration_conditions(self):
        wren = self.run.party[1]
        gambit = [{"id": "fire", "when": {"spell_ready": "Fireball@5e", "self_concentrating": False},
                   "then": {"type": "cast", "spell": "Fireball@5e", "center": "most_damage_enemy"}}]
        state = self.run.context["combat"]
        state["cursor"] = state["order"].index("p1")
        action = policies.macro_action(self.run, "p1", gambit)
        self.assertEqual(action["center"], list(t.position(self.run, action_target(self.run, action))))
        wren.resources["slot_3_general"] = 0
        self.assertIsNone(policies.macro_action(self.run, "p1", gambit))

    def test_illegal_gambit_falls_through(self):
        state = self.run.context["combat"]
        state["cursor"] = state["order"].index("p1")
        self.run.context["combat"]["positions"]["e0"] = [118, 118, 0]
        gambits = [{"id": "far", "then": {"type": "cast", "spell": "Inflict Wounds@5e", "target": "e0"}},
                   {"id": "near", "then": {"type": "cast", "spell": "Arcane Bolt@HSR", "target": "e1"}}]
        self.assertEqual(policies.macro_action(self.run, "p1", gambits)["target"], "e1")


def action_target(run, action):
    return next(k for k in t.actors(run) if list(t.position(run, k)) == action["center"])


class MonsterAttackTest(CombatFixture):
    def test_tarrasque_attack_reads_cover_and_glare(self):
        key = monsters.spawn_tarrasque(self.run)["actor"]
        self.run.context["combat"]["positions"][key] = list(self.run.context["combat"]["positions"]["p0"])
        self.run.context["combat"]["positions"][key][0] += 10
        self.run.context["combat"]["terrain"]["cover"]["p0"] = "half"
        self.run.context["combat"]["terrain"]["daylight"] = True
        with forced_d20(15):
            result = monsters.attack(self.run, key, "p0", "claw")
        self.assertEqual(result["evidence"]["target_ac"], t.actor(self.run, "p0").armor_class + 2)
        self.assertIsNotNone(result["evidence"]["glare"])
        if result["roll"]["success"]:
            self.assertEqual(result["evidence"]["damage_parts"][0]["label"], "claw")


if __name__ == "__main__":
    unittest.main()
