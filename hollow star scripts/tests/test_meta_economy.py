"""Focused tests for the HSR Gold, Gems, Platinum and commentary slice."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar import dungeon
from hollowstar.progression import Progression
from hollowstar.run_service import RunService
from hollowstar.storage import atomic_json


class MetaEconomyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="hsr-meta-")
        self.root = Path(self.tmp.name) / ".local" / "reliquary_runs"

    def tearDown(self):
        self.tmp.cleanup()

    def test_schema_one_progression_migrates_to_platinum_tracks(self):
        progress = Progression(self.root.parent / "reliquary_progress")
        path = progress.path("divine:Doran")
        atomic_json(path, {
            "schema": 1, "identity": "divine:Doran", "rank_xp": 4, "rank": 2,
            "currency": 7, "upgrades": {"supplies": 2, "crafting": 1}, "runs": {},
        })
        data = progress.load("divine:Doran")
        self.assertEqual(data["schema"], 3)
        self.assertEqual(data["account_id"], "divine:Doran")
        self.assertEqual(data["account_meta"]["meta_currency"], 7)
        self.assertEqual(data["platinum"], 7)
        self.assertEqual(data["currency"], 7)
        self.assertEqual(data["upgrades"]["reserve"], 2)
        self.assertEqual(data["upgrades"]["mastery_capacity"], 1)

    def test_persistent_upgrades_apply_without_mutating_certified_snapshot(self):
        progress = Progression(self.root.parent / "reliquary_progress")
        data = progress.load("divine:Doran")
        data["platinum"] = data["currency"] = 100
        data["upgrades"].update({"precision": 1, "force": 1, "ward": 1, "reserve": 1, "mastery_capacity": 1})
        atomic_json(progress.path("divine:Doran"), data)

        service = RunService(self.root)
        service.create("meta", ["divine:Doran"], ["Townsperson"], "meta-seed")
        started = service.design_start("meta")
        run = service._active["meta"]
        self.assertIn("commentary", started["event"])
        self.assertEqual(run.context["party_rules"]["p0"]["precision_bonus"], 1)
        self.assertEqual(run.context["party_rules"]["p0"]["damage_bonus"], 1)
        self.assertEqual(run.context["dungeon"]["upgrades"]["mastery_capacity"], 1)
        self.assertEqual(run.context["dungeon"]["upgrades"]["reserve"], 1)
        self.assertGreaterEqual(len(run.context["dungeon"]["inventory"]), 1)

    def test_gem_upgrade_track_is_deterministic_and_stops_at_five(self):
        service = RunService(self.root)
        service.create("gems", ["divine:Wren"], ["Townsperson"], "gem-seed")
        service.design_start("gems")
        run = service._active["gems"]
        run.context["dungeon"]["components"] = 10
        item = dungeon.add_item(run, "imprint")
        commentary_seen = False
        for _ in range(4):
            result = service.design_action("gems", {"type": "upgrade", "item": item["id"]})
            commentary_seen = commentary_seen or "commentary" in result["event"]
        upgraded = result["event"]["item"]
        self.assertEqual(upgraded["level"], 5)
        self.assertEqual(upgraded["suffix"]["name"], "Reliquary Temper")
        self.assertEqual(upgraded["percentage_bonus"], 10)
        self.assertEqual(service._active["gems"].context["dungeon"]["components"], 0)
        self.assertTrue(commentary_seen)
        service.design_action("gems", {"type": "equip", "item": item["id"], "actor": "p0"})
        active = service._active["gems"]
        active.party[0].hp = 1
        potion = dungeon.add_item(active, "potion")
        consumed = service.design_action("gems", {"type": "consume", "item": potion["id"], "actor": "p0"})
        self.assertEqual(consumed["event"]["evidence"]["percentage_bonus"], 10)
        self.assertGreater(consumed["event"]["evidence"]["healing"], consumed["event"]["evidence"]["rolled"])

    def test_settlement_awards_platinum_once_and_keeps_run_currencies_separate(self):
        service = RunService(self.root)
        service.create("settle", ["divine:Doran"], ["Townsperson"], "settle-seed")
        service.design_start("settle")
        run = service._active["settle"]
        run.context["dungeon"]["meta_currency"] = 3
        run.context["dungeon"]["currency"] = 12
        run.context["dungeon"]["components"] = 4
        service.design_action("settle", {"type": "leave"})
        run = service._active["settle"]
        progress = Progression(self.root.parent / "reliquary_progress")
        first = progress.settle("divine:Doran", "settle", run)
        second = progress.settle("divine:Doran", "settle", run)
        self.assertEqual(first["platinum"], 3)
        self.assertEqual(first["currency"], 3)
        self.assertEqual(second["platinum"], 3)
        receipt = first["runs"]["settle"]
        self.assertEqual(receipt["retained"]["gold"], 12)
        self.assertEqual(receipt["retained"]["gems"], 4)


if __name__ == "__main__":
    unittest.main()
