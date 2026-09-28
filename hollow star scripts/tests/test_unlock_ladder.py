"""Doran and Wren's Story Mode unlock ladder."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as N

from hollowstar import policies
from hollowstar import tactical as t
from hollowstar.run_service import RunService
from hollowstar.unlock_ladder import (
    UnlockLadder,
    action_locked,
    apply_slot_cap,
    level_for,
    lock_reason,
    next_pick_level,
    picks_for,
)


def _ladder():
    return UnlockLadder(Path(tempfile.mkdtemp(prefix="hsr-ladder-")))


def test_levels_and_picks_scale_to_one_hundred():
    assert level_for(0) == 1 and level_for(10_000) == 100
    assert picks_for(5) == 1 and picks_for(25) == 6 and picks_for(100) == 24


def test_grand_cleave_waits_for_level_fifty_and_a_pick():
    ladder = _ladder()
    ladder.debug_set_level("doran", 49)
    try:
        ladder.pick("doran", "grand_cleave")
    except ValueError as exc:
        assert "level 50" in str(exc)
    else:
        raise AssertionError("grand cleave unlocked early")
    ladder.debug_set_level("doran", 50)
    view = ladder.pick("doran", "grand_cleave")
    assert next(e for e in view["entries"] if e["key"] == "grand_cleave")["unlocked"]


def test_level_one_hundred_unlocks_everything():
    view = _ladder().debug_set_level("wren", 100)
    assert all(e["unlocked"] for e in view["entries"]) and view["slot_cap"] == 9


def test_run_credit_is_once_per_run():
    ladder = _ladder()
    ladder.credit("doran", "r1", 10)
    assert ladder.credit("doran", "r1", 10)["xp"] == 10


def test_locks_refuse_actions_and_close_high_slots():
    locks = _ladder().run_locks("doran")
    assert action_locked(locks, {"type": "grand_cleave"}) == "grand_cleave"
    assert action_locked(locks, {"type": "maneuver", "maneuver": "Riposte"}) == "maneuver:Riposte"
    assert action_locked(locks, {"type": "attack"}) is None
    actor = N(resources={"slot_1_general": 4, "slot_5_general": 2, "slot_9_general": 1})
    assert apply_slot_cap(actor, 1) == ["slot_5_general", "slot_9_general"]
    assert actor.resources == {"slot_1_general": 4, "slot_5_general": 0, "slot_9_general": 0}


# --- Story Mode runs: the lock holds on every path, and says when it opens ---


def test_view_reports_progress_and_sorts_by_level():
    ladder = _ladder()
    ladder.credit("doran", "r1", 9)  # 2 XP a level: level 5, one XP into it
    view = ladder.view("doran")
    assert (view["level"], view["xp_into_level"], view["next_pick_level"]) == (5, 1, 10)
    levels = [e["min_level"] for e in view["entries"]]
    assert levels == sorted(levels)
    assert next_pick_level(24) == 25 and next_pick_level(100) is None


def test_lock_reason_names_the_opening_level_or_the_pick():
    rules = {"champion_level": 12, "locked_levels": {"grand_cleave": 50, "maneuver:Riposte": 10}}
    assert "level 50" in lock_reason(rules, "grand_cleave")
    assert "spend a Champion Ladder pick" in lock_reason(rules, "maneuver:Riposte")


class StoryRunLocks(unittest.TestCase):
    """A fight carrying fresh level-1 Story locks for Doran (p0) and Wren (p1),
    copied into party rules exactly as a FORGE launch copies them."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / ".local/reliquary_runs")
        self.service.create("story", ["Doran", "Wren"], ["Townsperson"], "ladder-seed")
        self.service.design_start("story")
        self.service.design_action("story", {"type": "fight"})
        self.run = self.service._active["story"]
        self.combat = self.run.context["combat"]
        ladder = UnlockLadder(Path(self.tmp.name) / "progress")
        t.rules(self.run, "p0").update(ladder.run_locks("doran"))
        t.rules(self.run, "p1").update(ladder.run_locks("wren"))

    def tearDown(self):
        self.tmp.cleanup()

    def turn(self, key):
        self.combat["cursor"] = self.combat["order"].index(key)

    def test_story_launch_copies_the_locks_into_party_rules(self):
        service = RunService(Path(self.tmp.name) / "forge/.local/reliquary_runs")
        service.create("forge", ["Doran", "Wren"], ["Townsperson"], "ladder-seed", run_mode="FORGE")
        rules = service._active["forge"].context["party_rules"]
        self.assertIn("grand_cleave", rules["p0"]["locked_actions"])
        self.assertEqual(rules["p0"]["locked_levels"]["grand_cleave"], 50)
        self.assertEqual(rules["p1"]["champion_level"], 1)
        self.assertEqual(rules["p1"]["slot_cap"], 1)

    def test_catalog_greys_out_locked_abilities_with_the_level(self):
        self.turn("p0")
        rows = {row["id"]: row for row in t.contextual_actions(self.run, "p0")}
        cleave = rows["grand_cleave"]
        self.assertFalse(cleave["available"])
        self.assertTrue(cleave["locked"])
        self.assertIn("level 50", cleave["reason"])
        self.assertFalse(rows["maneuver_trip_attack"]["available"])
        self.assertTrue(rows["attack"]["available"])
        self.assertNotIn("locked", rows["attack"])

    def test_locked_reactions_are_never_offered(self):
        self.combat["positions"]["p0"] = [20, 20, 0]
        self.combat["positions"]["e0"] = [20, 25, 0]
        self.turn("e0")
        t.move(self.run, "e0", [40, 20, 0])
        window = next(w for w in self.combat["pending"] if w["reactor"] == "p0")
        self.assertEqual(window["options"], ["opportunity"])  # no Brace yet
        self.combat["pending"].clear()
        self.combat.pop("pending_movement", None)
        # Entering Doran's reach opens no Brace-only window while it is locked.
        self.combat["positions"]["e0"] = [20, 40, 0]
        t.move(self.run, "e0", [20, 25, 0])
        self.assertFalse([w for w in self.combat["pending"] if w.get("kind") == "brace"])

    def test_reaction_paths_refuse_locked_features(self):
        doran, wren = t.rules(self.run, "p0"), t.rules(self.run, "p1")
        for rules, action in ((doran, {"type": "reaction", "defense": "brace"}),
                              (doran, {"type": "reaction", "defense": "riposte"}),
                              (wren, {"type": "domain_reaction"})):
            self.assertTrue(action_locked(rules, action), action)
        self.assertIsNone(action_locked(doran, {"type": "reaction"}))
        with self.assertRaises(t.ActionError) as caught:
            t.incoming_failed_save(self.run, "e0", "p0", {"success": False})
        self.assertIn("Champion Ladder", str(caught.exception))

    def test_refusal_says_when_it_opens(self):
        self.turn("p0")
        with self.assertRaises(t.ActionError) as caught:
            t.apply(self.run, {"type": "grand_cleave", "actor": "p0", "facing": "east"})
        self.assertIn("level 50", str(caught.exception))

    def test_auto_play_never_reaches_for_a_locked_ability(self):
        self.turn("p0")
        doran = self.run.party[0]
        doran.hp = doran.max_hp // 4  # would normally trigger Second Wind
        self.assertNotEqual(policies.combat_action(self.run).get("type"), "second_wind")
        rows = policies.candidate_actions(self.run, "p0", include_illegal=True)
        laddered = [row for row in rows if row["kind"] == "maneuver"
                    and f"maneuver:{row['action']['maneuver']}" in t.rules(self.run, "p0")["locked_actions"]]
        self.assertTrue(laddered)
        self.assertFalse(any(row["legal"] for row in laddered))
        self.assertTrue(all("Champion Ladder" in row["reason"] for row in laddered))
        self.assertFalse(policies._legal_now(self.run, "p0", {"type": "grand_cleave", "actor": "p0"}))

    def test_simulation_runs_keep_the_complete_sheets(self):
        service = RunService(Path(self.tmp.name) / "sim/.local/reliquary_runs")
        service.create("sim", ["Doran", "Wren"], ["Townsperson"], "ladder-seed")
        service.design_start("sim")
        service.design_action("sim", {"type": "fight"})
        self.assertNotIn("locked_actions", t.rules(service._active["sim"], "p0"))
