"""Status registry (hollowstar/statuses.py + content/statuses.json): the derived
sets match the historical hardcoded ones, new statuses are one registration, and
refusal/lifecycle hooks dispatch."""

from __future__ import annotations

import unittest
from unittest import mock

from hollowstar import statuses, tactical


class StatusRegistryTests(unittest.TestCase):
    def test_derived_sets_match_the_historical_definitions(self):
        self.assertEqual(statuses.CONDITIONS, {
            "PRONE", "GRAPPLED", "RESTRAINED", "STUNNED", "PARALYZED", "INCAPACITATED", "BLINDED",
            "FRIGHTENED", "CHARMED", "POISONED", "DODGING", "DISENGAGED", "INVISIBLE", "HASTED", "SLOWED",
            "CONFUSED", "DOMINATED", "POSSESSED", "MENTALLY_PARALYZED", "FEEBLEMIND", "MEMORY_EDIT",
            "PETRIFIED", "SILENCED"})
        self.assertEqual(statuses.INCAPACITATING, {"STUNNED", "PARALYZED", "INCAPACITATED"})
        self.assertEqual(tactical.condition_category("CHARMED"), "mental")
        self.assertEqual(tactical.condition_category("PRONE"), "physical")
        self.assertEqual(tactical.condition_category("NOPE"), "unknown")
        self.assertIs(tactical.CONDITIONS, statuses.CONDITIONS)

    def test_decay_policy_lives_in_the_registry(self):
        self.assertFalse(statuses.decays("DODGING"))
        self.assertTrue(statuses.decays("POISONED"))
        self.assertTrue(statuses.decays("UNREGISTERED"))
        self.assertEqual(set(statuses.turn_start_cleared()), {"DODGING", "DISENGAGED"})

    def test_registering_a_status_makes_it_a_condition(self):
        name = "TEST_ONLY_WARDED"
        try:
            statuses.register(statuses.StatusDef(name, category="mental", incapacitating=True))
            self.assertIn(name, tactical.CONDITIONS)
            self.assertIn(name, tactical.MENTAL_CONDITIONS)
            self.assertIn(name, tactical.INCAPACITATING)
            self.assertEqual(tactical.condition_category(name), "mental")
        finally:
            for table in (statuses.DEFS, statuses.CONDITION_CATEGORIES):
                table.pop(name, None)
            for group in (statuses.CONDITIONS, statuses.MENTAL_CONDITIONS, statuses.INCAPACITATING):
                group.discard(name)

    def test_refusal_chain_first_hit_wins_and_hooks_fire(self):
        seen = []
        hook = statuses.hook("apply")(lambda run, key, name: seen.append((key, name)))
        try:
            # Isolate from the engine's own rules (they need a live run).
            with mock.patch.object(statuses, "_REFUSALS", []):
                miss = statuses.refusal(lambda run, key, name, mental: None)
                statuses.refusal(lambda run, key, name, mental: {"reason": "test"} if name == "HASTED" else None)
                statuses.refusal(lambda run, key, name, mental: {"reason": "late"})
                self.assertIs(statuses._REFUSALS[0], miss)
                self.assertEqual(statuses.first_refusal(None, "k", "HASTED"), {"reason": "test"})
                self.assertEqual(statuses.first_refusal(None, "k", "SLOWED"), {"reason": "late"})
            statuses.fire("apply", None, "k", "SLOWED")
            self.assertEqual(seen, [("k", "SLOWED")])
        finally:
            statuses._HOOKS["apply"].remove(hook)


if __name__ == "__main__":
    unittest.main()
