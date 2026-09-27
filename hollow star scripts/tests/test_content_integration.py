"""Focused tests for the source-linked Divine Mythos HSR slice."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar import dungeon
from hollowstar import tactical as t
from hollowstar.content_registry import (
    ContentRegistryClarification,
    audit_sources,
    load_registry,
)
from hollowstar.intent import IntentClarification, IntentError, parse_intent
from hollowstar.progression import Progression
from hollowstar.run_service import RunService, RunServiceError
from hollowstar.host import HSRHost


class ContentIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="hsr-content-")
        self.root = Path(self.tmp.name) / ".local" / "reliquary_runs"
        self.service = RunService(self.root)
        self.service.create("content", ["Doran", "Wren"], ["Townsperson"], "content-seed")
        self.service.design_start("content")
        # These tests hand-drive every actor's turn, enemies included.
        self.service._active["content"].context["manual_opposition"] = True

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def runstate(self):
        return self.service._active["content"]

    def _fight(self, run_id: str = "content"):
        self.service.design_action(run_id, {"type": "fight"})
        return self.service._active[run_id]

    def _until_turn(self, actor: str, run_id: str = "content"):
        run = self.service._active[run_id]
        for _ in range(20):
            if t.current(run) == actor:
                return run
            self.service.design_action(run_id, {"type": "end_turn", "actor": t.current(run)})
            run = self.service._active[run_id]
        self.fail(f"initiative did not reach {actor}")

    def _mark_authored_checkpoint(self, run_id: str = "content"):
        run = self.service._active[run_id]
        row = run.context["dungeon"]["rooms"]["1:1"]
        row.update({"resolved": True, "checkpoint": True, "safe_room": True})
        return run

    def test_registry_sources_and_deferred_rows_are_explicit(self):
        registry = load_registry()
        audit = audit_sources(registry)
        self.assertGreaterEqual(len(registry["entries"]), 50)
        self.assertEqual(audit["missing"], [])
        self.assertIn(
            "divine mythos set/DM041_A_T_REF_doran-machine-readable-combat-mechanics.md",
            audit["checked_files"],
        )
        self.assertIn(
            "divine mythos set/DM041_B_T_REF_wren-machine-readable-combat-and-casting-mechanics.md",
            audit["checked_files"],
        )
        deferred = {entry["id"]: entry for entry in registry["entries"] if entry["execution"]["status"] == "deferred"}
        self.assertEqual(set(deferred), {"wren.portal_slash"})
        self.assertTrue(all(entry["action"] is None and entry["execution"]["deferred"] for entry in deferred.values()))
        imprisonment = next(entry for entry in registry["entries"] if entry["id"] == "wren.imprisonment")
        self.assertEqual(imprisonment["execution"]["status"], "implemented")
        self.assertEqual(imprisonment["execution"]["resolver"], "cast")

    def test_canonical_alias_and_ambiguous_content_invocations(self):
        visible = self.service.observe("content")
        self.assertEqual(
            parse_intent("Doran draws the daggers", visible),
            {"type": "content", "actor": "p0", "content_id": "doran.obsidian_daggers"},
        )
        self.assertEqual(
            parse_intent("Wren opens the portal", visible),
            {"type": "content", "actor": "p1", "content_id": "wren.portal_gate"},
        )
        self.assertEqual(
            parse_intent("use the Staff to absorb the spell"),
            {"type": "content", "actor": "p1", "content_id": "wren.staff_magi", "parameters": {"mode": "absorb"}},
        )
        ambiguous = {"content": [
            {"id": "one", "name": "shared relic", "aliases": ["relic"]},
            {"id": "two", "name": "other relic", "aliases": ["relic"]},
        ]}
        with self.assertRaises(IntentClarification):
            parse_intent("use the relic", ambiguous)
        with self.assertRaises(IntentError):
            parse_intent("use a hidden relic", {"content": []})

    def test_host_design_turn_uses_the_visible_content_catalog(self):
        with tempfile.TemporaryDirectory(prefix="hsr-host-content-") as temp:
            data_root = Path(temp) / ".local" / "reliquary_runs"
            host = HSRHost.from_options(Path(__file__).resolve().parents[2], data_root=data_root)
            self.assertTrue(host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})["ok"])
            self.assertTrue(host.handle({
                "id": "c", "command": "create_run", "run_id": "host-content",
                "party": ["Doran", "Wren"], "opposition": ["Townsperson"], "seed": "host-content-seed",
            })["ok"])
            self.assertTrue(host.handle({"id": "s", "command": "design_start", "run_id": "host-content"})["ok"])
            catalog = host.handle({"id": "k", "command": "content_catalog", "run_id": "host-content"})
            self.assertTrue(catalog["ok"])
            self.assertIn("doran.obsidian_daggers", {row["id"] for row in catalog["result"]["content"]["entries"]})
            turn = host.handle({
                "id": "t", "command": "design_turn", "run_id": "host-content",
                "intent": "Doran draws the daggers",
            })
            self.assertTrue(turn["ok"])
            self.assertEqual(turn["result"]["turn"]["action"]["content_id"], "doran.obsidian_daggers")
            self.assertEqual(turn["result"]["turn"]["outcome"]["content"]["id"], "doran.obsidian_daggers")

    def test_equipment_content_carries_into_combat_and_keeps_provenance(self):
        result = self.service.design_action(
            "content",
            parse_intent("Doran draws the daggers", self.service.observe("content")),
            intent="Doran draws the daggers",
        )
        self.assertEqual(result["event"]["type"], "content_equipped")
        self.assertEqual(result["event"]["content"]["id"], "doran.obsidian_daggers")
        self.assertEqual(
            result["event"]["content"]["source"]["owner_file"],
            "divine mythos set/DM041_A_T_REF_doran-machine-readable-combat-mechanics.md",
        )
        run = self._fight()
        self.assertEqual(t.rules(run, "p0")["loadout"], "daggers")
        with self.assertRaises(RunServiceError):
            self.service.design_action("content", {"type": "content", "actor": "p0", "content_id": "wren.portal_slash"})

    def test_content_spell_enforces_target_range_and_resource(self):
        run = self._fight()
        self._until_turn("p1")
        run = self.runstate()
        before_resource = run.party[1].resources["portal_shear"]
        with self.assertRaises(RunServiceError):
            self.service.design_action("content", {
                "type": "content", "actor": "p1", "content_id": "wren.portal_shear", "targets": ["p0"],
            })
        self.assertEqual(self.runstate().party[1].resources["portal_shear"], before_resource)
        run.context["combat"]["positions"]["e0"] = [120, 120, 0]
        with self.assertRaises(RunServiceError):
            self.service.design_action("content", {
                "type": "content", "actor": "p1", "content_id": "wren.portal_shear", "targets": ["e0"],
            })
        self.assertEqual(self.runstate().party[1].resources["portal_shear"], before_resource)

        run.context["combat"]["positions"]["e0"] = [40, 10, 0]
        result = self.service.design_action("content", {
            "type": "content", "actor": "p1", "content_id": "wren.portal_shear", "targets": ["e0"],
        })
        self.assertEqual(result["event"]["content"]["id"], "wren.portal_shear")
        self.assertEqual(self.service._active["content"].party[1].resources["portal_shear"], before_resource - 1)

    def test_staff_content_resolves_an_authored_reaction_window(self):
        run = self._fight()
        run.party[1].resources["staff_charges"] = 40
        t.incoming_spell(run, "e0", "p1", 5)
        result = self.service.design_action("content", {
            "type": "content", "actor": "p1", "content_id": "wren.staff_magi", "parameters": {"mode": "absorb"},
        })
        self.assertEqual(result["event"]["type"], "staff_absorb")
        self.assertEqual(result["event"]["content"]["source"]["owner_file"],
                         "divine mythos set/DM041_B_T_REF_wren-machine-readable-combat-and-casting-mechanics.md")
        self.assertEqual(self.service._active["content"].party[1].resources["staff_charges"], 45)
        self.assertEqual(self.service._active["content"].context["combat"]["pending"], [])

    def test_authored_prose_and_objects_obey_the_observation_boundary(self):
        initial = self.service.observe("content")
        initial_text = json.dumps(initial, ensure_ascii=False)
        self.assertTrue(initial["room"]["prose_available"])
        self.assertNotIn("atmosphere", initial["room"])
        self.assertNotIn("The market keeps its voice low", initial_text)
        self.assertNotIn("old_waterwheel", initial_text)
        self.assertTrue(all("text" not in tell for tell in initial["room"]["tells"]))

        revealed = self.service.design_action("content", {"type": "reveal_room_record"})
        self.assertIn("old_waterwheel", json.dumps(revealed["event"]["sealed_record"]))
        self.assertTrue(revealed["event"]["evidence"]["explicit_fetch"])
        still_hidden = self.service.observe("content")
        self.assertNotIn("atmosphere", still_hidden["room"])

        observed = self.service.design_action("content", {"type": "observe_room"})
        self.assertTrue(observed["event"]["evidence"]["physical_observation"])
        self.assertIn("The market keeps its voice low", observed["event"]["atmosphere"])
        self.assertIn("atmosphere", observed["state"]["room"])
        self.assertNotIn("old_waterwheel", json.dumps(observed["state"]["room"]))

        inspected = self.service.design_action("content", {
            "type": "inspect_object", "actor": "p1", "object_id": "1:1:old_waterwheel",
        })
        consequence = inspected["event"]["consequence"]
        self.assertIn("town-route", inspected["event"]["evidence"]["authored_hooks"])
        self.assertEqual(consequence["temporary_reward"]["name"], "Well-route imprint")
        self.assertIn("hidden route", consequence["text"])
        again = self.service.design_action("content", {
            "type": "inspect_object", "actor": "p1", "object_id": "1:1:old_waterwheel",
        })
        self.assertNotIn("consequence", again["event"])

    def test_checkpoint_is_atomic_exact_and_unbanked_loot_is_lost_on_defeat(self):
        run = self._mark_authored_checkpoint()
        banked_item = dungeon.add_item(run, "potion")
        result = self.service.design_action("content", {"type": "bank_checkpoint"})
        self.assertTrue(result["event"]["evidence"]["atomic_persistence"])
        checkpoint = result["event"]["checkpoint"]
        self.assertIn(banked_item["id"], checkpoint["banked_items"])
        saved_rng = self.service._active["content"].rng.getstate()
        dungeon.add_item(self.service._active["content"], "potion")

        ended = self.service.design_action("content", {"type": "retreat"})
        receipt = ended["event"]["terminal_receipt"]
        self.assertEqual(receipt["status"], "ejected")
        # Forced ejection is a public `dead` outcome, not `completed`.
        self.assertEqual(receipt["outcome"], "dead")
        self.assertIn(banked_item["id"], {item["id"] for item in receipt["retained"]["items"]})
        self.assertEqual(len(receipt["lost_unbanked_items"]), 1)
        self.assertFalse(receipt["future_rooms_exposed"])
        self.assertNotIn("The Machine Works", json.dumps(receipt))

        progress = Progression(self.root.parent / "reliquary_progress")
        settled = progress.settle("divine:Doran", "content", self.service._active["content"])
        self.assertEqual(settled["runs"]["content"]["checkpoint_id"], checkpoint["checkpoint_id"])
        self.assertEqual(len(settled["runs"]["content"]["lost_unbanked_items"]), 1)
        self.assertEqual(self.service._active["content"].context["dungeon"]["run_capsule"]["retention"], "temporary")

        # A terminal run is closed for good: checkpoints reconnect an active
        # run, they never rewind a death or undo a completion. Retrying is an
        # account-level action that creates a new run, not a resume of this one.
        fresh = RunService(self.root)
        fresh.load("content")
        with self.assertRaises(RunServiceError):
            fresh.design_action("content", {"type": "resume_checkpoint"})
        self.assertEqual(fresh._active["content"].rng.getstate(), saved_rng)
        self.assertEqual(fresh._active["content"].context["dungeon"]["status"], "ejected")

    def test_victory_retains_current_temporary_rewards_and_reset_keeps_receipt(self):
        self._mark_authored_checkpoint()
        self.service.design_action("content", {"type": "bank_checkpoint"})
        run = self.service._active["content"]
        banked = dungeon.add_item(run, "potion")

        won = self.service._transition("content", lambda candidate: dungeon.end(candidate, "cleared"), action_label="victory")
        receipt = won["event"]["terminal_receipt"]
        retained_ids = {item["id"] for item in receipt["retained"]["items"]}
        self.assertIn(banked["id"], retained_ids)
        self.assertEqual(receipt["lost_unbanked_items"], [])

        reset = self.service.design_action("content", {"type": "reset"})
        self.assertEqual(reset["event"]["reset"]["previous"]["terminal_receipt"]["status"], "cleared")
        self.assertEqual(self.service.observe("content")["status"], "active")
        self.assertEqual(self.service.observe("content")["reset_history"][-1]["terminal_receipt"]["completion_kind"], "cleared")


if __name__ == "__main__":
    unittest.main()
