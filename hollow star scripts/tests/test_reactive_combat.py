"""Reactive combat: NPC reactions resolve themselves, the host drains NPC
turns in one call, and maneuvers and contests join the planning catalog."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hollowstar.host import HSRHost
from hollowstar.run_service import RunService, DRAIN_NPC_LIMIT
from hollowstar import tactical as t
from hollowstar import policies
from hollowstar import maneuvers
from hollowstar import monsters


class Fixture(unittest.TestCase):
    """p0 Doran, p1 Wren (player-controlled), e0 a town watch (NPC)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / ".local/reliquary_runs")
        self.service.create("trial", ["Doran", "Wren"], ["Townsperson"], "reactive-seed")
        self.service.design_start("trial")
        self.service.design_action("trial", {"type": "fight"})
        self.run = self.service._active["trial"]
        self.combat = self.run.context["combat"]

    def tearDown(self):
        self.tmp.cleanup()

    def turn(self, key):
        self.combat["cursor"] = self.combat["order"].index(key)

    def adjacent(self, mover="p0", foe="e0"):
        self.combat["positions"][mover] = [20, 20, 0]
        self.combat["positions"][foe] = [20, 25, 0]


class ReactionPolicyTest(Fixture):
    def test_npc_opportunity_window_is_taken(self):
        self.turn("p0")
        self.adjacent()
        pending = t.move(self.run, "p0", [40, 20, 0])
        self.assertEqual(pending["type"], "movement_pending")
        window = self.combat["pending"][0]
        self.assertEqual(window["reactor"], "e0")
        self.assertEqual(policies.combat_action(self.run), {"type": "reaction", "actor": "e0"})

    def test_settle_resolves_npc_windows_and_commits_the_move(self):
        self.turn("p0")
        self.adjacent()
        t.move(self.run, "p0", [40, 20, 0])
        settled = t.settle_npc_reactions(self.run)
        self.assertEqual(len(settled), 1)
        self.assertEqual(settled[0]["type"], "reaction_and_movement")
        # A miss may open Doran's own Deft Answer: that one is the player's.
        self.assertFalse([w for w in self.combat["pending"] if t.ai_controlled(self.run, w["reactor"])])
        self.assertEqual(t.economy(self.run, "e0")["reaction"], 0)
        if self.run.party[0].alive:
            self.assertEqual(self.combat["positions"]["p0"], [40, 20, 0])

    def test_player_windows_are_left_for_the_player(self):
        self.turn("e0")
        self.adjacent("e0", "p0")
        t.economy(self.run, "p1")["reaction"] = 0
        t.move(self.run, "e0", [20, 45, 0])
        reactors = {w["reactor"] for w in self.combat["pending"]}
        self.assertEqual(reactors, {"p0"})
        self.assertEqual(t.settle_npc_reactions(self.run), [])
        self.assertEqual({w["reactor"] for w in self.combat["pending"]}, {"p0"})

    def test_opt_in_move_resolves_the_opportunity_attack_in_one_step(self):
        self.turn("p0")
        self.adjacent()
        self.run.context["auto_npc_reactions"] = True
        result = t.apply(self.run, {"type": "move", "actor": "p0", "destination": [40, 20, 0]})
        self.assertEqual(result["type"], "reaction_and_movement")
        self.assertEqual(len(result["auto_reactions"]), 1)
        self.assertEqual(result["evidence"]["auto_resolved_reactions"], 1)
        self.assertFalse([w for w in self.combat["pending"] if t.ai_controlled(self.run, w["reactor"])])

    def test_default_move_still_opens_the_window(self):
        # Without the opt-in, tactical.move keeps its historical contract.
        self.turn("p0")
        self.adjacent()
        result = t.apply(self.run, {"type": "move", "actor": "p0", "destination": [40, 20, 0]})
        self.assertEqual(result["type"], "movement_pending")

    def test_hit_window_uses_shield_or_parry_when_worth_it(self):
        wren, doran = self.run.party[1], self.run.party[0]
        shield = {"kind": "hit", "reactor": "p1", "target": "e0", "amount": 4, "options": ["shield"]}
        self.assertEqual(policies.reaction_action(self.run, shield)["defense"], "shield")
        wren.resources["slot_1_general"] = 0
        self.assertEqual(policies.reaction_action(self.run, shield)["type"], "decline_reaction")
        parry = {"kind": "hit", "reactor": "p0", "target": "e0", "amount": 20, "options": ["parry"]}
        self.assertEqual(policies.reaction_action(self.run, parry)["defense"], "parry")
        small = dict(parry, amount=3)
        self.assertEqual(policies.reaction_action(self.run, small)["type"], "decline_reaction")
        doran.hp = 2
        self.assertEqual(policies.reaction_action(self.run, small)["defense"], "parry")
        doran.resources["superiority_dice"] = 0
        self.assertEqual(policies.reaction_action(self.run, parry)["type"], "decline_reaction")

    def test_unknown_or_unpayable_windows_decline(self):
        self.assertEqual(policies.reaction_action(self.run, {"kind": "mystery", "reactor": "e0"})["type"],
                         "decline_reaction")
        self.assertEqual(policies.reaction_action(self.run, {"kind": "save", "reactor": "p1"})["type"],
                         "decline_reaction")
        self.run.party[0].resources["superiority_dice"] = 0
        brace = {"kind": "brace", "reactor": "p0", "target": "e0", "options": ["brace"]}
        self.assertEqual(policies.reaction_action(self.run, brace)["type"], "decline_reaction")


class MonsterAggressionTest(Fixture):
    def tarrasque(self):
        key = monsters.spawn_tarrasque(self.run)["actor"]
        self.combat["positions"][key] = [20, 30, 0]
        self.combat["positions"]["p0"] = [20, 20, 0]
        self.combat["positions"]["p1"] = [100, 100, 0]
        return key

    def test_legendary_window_spends_a_point_on_a_claw(self):
        key = self.tarrasque()
        window = {"kind": "legendary", "reactor": key, "target": "p0"}
        choice = policies.reaction_action(self.run, window)
        self.assertEqual(choice, {"type": "legendary", "actor": key, "mode": "claw", "target": "p0"})
        self.combat["pending"].append(window)
        before = t.actor(self.run, key).resources["legendary_actions"]
        t.settle_npc_reactions(self.run)
        self.assertEqual(t.actor(self.run, key).resources["legendary_actions"], before - 1)
        self.assertEqual(self.combat["pending"], [])

    def test_legendary_window_declines_with_nothing_in_reach(self):
        key = self.tarrasque()
        self.combat["positions"][key] = [100, 10, 0]
        choice = policies.reaction_action(self.run, {"kind": "legendary", "reactor": key, "target": "p0"})
        self.assertEqual(choice["type"], "decline_reaction")

    def test_tarrasque_runs_its_routine_then_ends_the_turn(self):
        key = self.tarrasque()
        self.turn(key)
        modes = []
        for _ in range(12):
            if self.combat["complete"] or t.current(self.run) != key:
                break
            action = policies.combat_action(self.run)
            if self.combat["pending"]:
                t.settle_npc_reactions(self.run)
                continue
            if action["type"] == "monster":
                modes.append(action["mode"])
            t.apply(self.run, action)
            t.settle_npc_reactions(self.run)
            while self.combat["pending"]:
                window = self.combat["pending"][0]
                t.apply(self.run, {"type": "decline_reaction", "actor": window["reactor"]})
            if action["type"] == "end_turn":
                break
        self.assertTrue(modes)
        self.assertLessEqual(len(modes), 5)
        self.assertTrue(set(modes) <= {"bite", "swallow", "claw", "horns", "tail"})

    def test_multiattack_keeps_swinging_until_the_attacks_are_spent(self):
        self.turn("e0")
        self.adjacent("e0", "p0")
        for key in t.actors(self.run):
            t.economy(self.run, key)["reaction"] = 0
        swings = 0
        for _ in range(8):
            action = policies.combat_action(self.run)
            if action["type"] != "attack":
                break
            t.apply(self.run, action)
            swings += 1
            if self.combat["complete"]:
                break
        # Every attack of the Attack action, plus a declared bonus-pool press.
        attacks = t.rules(self.run, "e0").get("attacks", self.run.opposition[0].attacks_per_action)
        self.assertGreaterEqual(swings, max(1, attacks))
        self.assertEqual(policies.combat_action(self.run)["type"], "end_turn")


class DrainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="hsr-drain-")
        self.host = HSRHost.from_options(data_root=Path(self.tmp.name) / ".local")
        self.assertTrue(self.host.handle({"id": "boot", "command": "boot", "mode": "DESIGN"})["ok"])
        created = self.host.handle({"id": "c", "command": "create_run", "run_id": "drain",
                                    "party": ["Doran", "Wren"], "opposition": ["Townsperson"],
                                    "seed": "drain-seed", "scenario": "reliquary"})
        self.assertTrue(created["ok"], created)
        self.assertTrue(self.host.handle({"id": "s", "command": "design_start", "run_id": "drain"})["ok"])

    @property
    def live(self):
        # Every transition commits a fresh clone, so always read the live one.
        return self.host._runs()._active["drain"]

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, command, **fields):
        return self.host.handle({"id": command, "command": command, "run_id": "drain", **fields})

    def enter_combat(self):
        for _ in range(40):
            combat = self.live.context.get("combat") or {}
            if combat.get("order") and not combat.get("complete"):
                return combat
            view = self.call("readout", public_only=True)["result"]["readout"]["public_view"]
            offered = [row["id"] for row in view.get("available_actions", [])]
            pick = next((p for p in ("fight", "rest", "exit", "disarm") if p in offered), None)
            self.assertIsNotNone(pick, offered)
            self.assertTrue(self.call("design_action", action={"type": pick, "actor": "p0"})["ok"])
        self.fail("never reached a fight")

    def decider(self):
        combat = self.live.context["combat"]
        return combat["pending"][0]["reactor"] if combat["pending"] else t.current(self.live)

    def test_drain_is_a_no_op_on_a_player_turn(self):
        combat = self.enter_combat()
        while t.ai_controlled(self.live, self.decider()) and not combat["complete"]:
            self.assertTrue(self.call("design_auto_combat")["ok"])
            combat = self.live.context["combat"]
        reply = self.call("design_drain_npc")
        self.assertTrue(reply["ok"], reply)
        self.assertEqual(reply["result"]["drain"]["steps"], 0)
        self.assertIn(reply["result"]["drain"]["stopped"], {"player_turn", "player_reaction"})

    def test_drain_plays_consecutive_npc_turns_and_stops_for_the_player(self):
        self.enter_combat()
        run = self.host._runs()._active["drain"]
        run.context["manual_opposition"] = True
        combat = run.context["combat"]
        # Every player turn ends at once, so only NPC steps are left to drain.
        for _ in range(30):
            if combat["complete"]:
                break
            reply = self.call("design_drain_npc")
            self.assertTrue(reply["ok"], reply)
            drain = reply["result"]["drain"]
            self.assertLessEqual(drain["steps"], DRAIN_NPC_LIMIT)
            self.assertEqual(len(reply["result"]["receipts"]), drain["steps"])
            run = self.host._runs()._active["drain"]
            combat = run.context["combat"]
            if combat["complete"]:
                self.assertIn(drain["stopped"], {"combat_complete", "run_ended"})
                break
            decider = combat["pending"][0]["reactor"] if combat["pending"] else t.current(run)
            if drain["stopped"] != "step_limit":
                self.assertFalse(t.ai_controlled(run, decider), drain)
                self.assertEqual(drain["next_actor"], decider)
            if not t.ai_controlled(run, decider):
                if combat["pending"]:
                    self.call("design_action", action={"type": "decline_reaction", "actor": decider})
                else:
                    self.call("design_action", action={"type": "end_turn", "actor": decider})
                run = self.host._runs()._active["drain"]
                combat = run.context["combat"]

    def test_drain_outside_combat_is_refused(self):
        reply = self.call("design_drain_npc")
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["code"], "NOT_IN_COMBAT")

    def test_player_action_returns_the_opposition_receipts(self):
        combat = self.enter_combat()
        run = self.host._runs()._active["drain"]
        while t.ai_controlled(run, self.decider()) and not combat["complete"]:
            self.call("design_auto_combat")
            run = self.live
            combat = run.context["combat"]
        if combat["complete"]:
            self.skipTest("the fight ended before a player turn")
        reply = self.call("design_action", action={"type": "end_turn", "actor": self.decider()})
        self.assertTrue(reply["ok"], reply)
        run = self.host._runs()._active["drain"]
        combat = run.context["combat"]
        if not combat["complete"]:
            decider = combat["pending"][0]["reactor"] if combat["pending"] else t.current(run)
            self.assertFalse(t.ai_controlled(run, decider))
        event = reply["result"]["event"]
        played = len(event.get("opposition_turns") or []) + len(event.get("auto_reactions") or [])
        self.assertEqual(len(reply["result"].get("receipts") or []), played)


class CandidateSourceTest(Fixture):
    def snapshot(self):
        return copy.deepcopy(self.run.context), self.run.rng.getstate(), \
            [(a.hp, dict(a.resources), dict(a.statuses)) for a in t.actors(self.run).values()]

    def test_maneuver_and_contest_rows_join_the_catalog(self):
        self.turn("p0")
        self.adjacent()
        rows = policies.candidate_actions(self.run, "p0")
        kinds = {row["kind"] for row in rows}
        self.assertTrue({"attack", "maneuver", "shove", "grapple", "dodge", "disengage", "dash"} <= kinds, kinds)
        self.assertEqual(len({row["id"] for row in rows}), len(rows), "candidate ids must be unique")
        trip = next(row for row in rows if row["id"] == "maneuver:Trip Attack/dagger::e0")
        plain = max(row["expected_damage"] for row in rows if row["kind"] == "attack" and row["target"] == "e0"
                    and row["action"].get("mode") == "dagger" and not row["action"].get("bonus"))
        self.assertGreater(trip["expected_damage"], plain)
        self.assertEqual(trip["forecast"]["effect"], "PRONE")
        self.assertGreater(trip["control"], 0)
        self.assertEqual(trip["cost"]["resources"], {"superiority_dice": 1})
        shove = next(row for row in rows if row["id"] == "shove:push::e0")
        self.assertIsNone(shove["hit"])
        self.assertEqual(shove["expected_damage"], 0.0)

    def test_forecasts_are_read_only(self):
        self.turn("p0")
        self.adjacent()
        before = self.snapshot()
        policies.candidate_actions(self.run, "p0", include_illegal=True)
        maneuvers.forecast_maneuver(self.run, "p0", {"maneuver": "Precision Attack", "target": "e0"})
        t.forecast_contest(self.run, "p0", {"type": "grapple", "target": "e0"})
        self.assertEqual(self.snapshot(), before)

    def test_forecast_legality_matches_the_resolver(self):
        self.turn("p0")
        self.adjacent()
        for row in policies.candidate_actions(self.run, "p0", include_illegal=True):
            if row["source"] not in {"maneuver", "contest"}:
                continue
            trial = copy.deepcopy(self.run)
            try:
                t.apply(trial, copy.deepcopy(row["action"]))
                ok, reason = True, None
            except t.ActionError as exc:
                ok, reason = False, str(exc)
            self.assertEqual(row["legal"], ok, (row["id"], row["reason"], reason))

    def test_no_superiority_dice_means_no_maneuver_rows(self):
        self.run.party[0].resources["superiority_dice"] = 0
        rows = policies.candidate_actions(self.run, "p0", include_illegal=True)
        self.assertFalse([row for row in rows if row["kind"] == "maneuver"])
        forecast = maneuvers.forecast_maneuver(self.run, "p0", {"maneuver": "Trip Attack", "target": "e0"})
        self.assertFalse(forecast["legal"])
        self.assertEqual(forecast["reason"], "no superiority dice")

    def test_precision_raises_the_hit_chance(self):
        self.turn("p0")
        self.adjacent()
        self.run.opposition[0].armor_class = 30
        plain = t.forecast_attack(self.run, "p0", "e0", "dagger")
        precise = maneuvers.forecast_maneuver(self.run, "p0", {"maneuver": "Precision Attack", "target": "e0"})
        self.assertGreater(precise["hit"], plain["hit"])

    def test_control_and_defend_goals_plan_executable_actions(self):
        self.turn("p0")
        self.adjacent()
        control = policies.plan_action(self.run, "p0", "control")
        self.assertIsNotNone(control)
        self.assertIn(control["type"], {"maneuver", "shove", "grapple"})
        t.apply(copy.deepcopy(self.run), control)
        defend = policies.plan_action(self.run, "p0", "defend")
        self.assertEqual(defend["type"], "dodge")
        t.apply(copy.deepcopy(self.run), defend)
        self.combat["positions"]["e0"] = [100, 100, 0]
        self.assertIsNone(policies.plan_action(self.run, "p0", "defend"))

    def test_gambit_can_plan_a_control_action(self):
        self.turn("p0")
        self.adjacent()
        action = policies.macro_action(self.run, "p0", [{"id": "lock", "then": {"type": "plan", "goal": "control"}}])
        self.assertIsNotNone(action)
        self.assertIsNotNone(policies.forecast_action(self.run, "p0", action))


if __name__ == "__main__":
    unittest.main()
