"""Focused coverage for the playable server-authoritative arcade slice."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar import arcade, spatial, tactical as t
from hollowstar.run_service import RunService, RunServiceError


class ArcadeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="hsr-arcade-")
        self.root = Path(self.tmp.name) / ".local" / "reliquary_runs"
        self.service = RunService(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def start_room(self, run_id="arcade", party=None):
        party = party or ["Doran"]
        self.service.create(run_id, party, ["Townsperson"], "arcade-seed")
        self.service.design_start(run_id)
        run = self.service._active[run_id]
        run.context["dungeon"]["rooms"]["1:1"]["resolved"] = True
        entered = self.service.design_action(run_id, {"type": "exit"})
        return run_id, entered

    def test_real_floor_combat_enters_arcade_and_round_trips(self):
        run_id, entered = self.start_room()
        state = entered["state"]
        self.assertEqual(state["room"]["encounter_mode"], "arcade")
        self.assertEqual(state["arcade"]["schema"], "hollow-star-arcade-public-1")
        self.assertEqual(state["arcade"]["waves"], 1)
        self.assertEqual(state["arcade"]["obstacles"][0]["required_mode"], ["fly", "jump"])
        saved = json.loads((self.root / f"{run_id}.json").read_text(encoding="utf-8"))
        arcade_state = saved["encounter"]["context"]["arcade"]
        self.assertIsInstance(arcade_state["entities"]["p0"]["position"], list)
        resumed = RunService(self.root)
        resumed.load(run_id)
        self.assertEqual(resumed.observe(run_id)["arcade"]["frame"], 0)

    def test_spatial_overlap_is_frame_gated_and_excludes_friendly_fire(self):
        entities = {
            "p0": spatial.SpatialEntity("p0", "p0", (10, 10, 0), team="party"),
            "p1": spatial.SpatialEntity("p1", "p1", (12, 10, 0), team="party"),
            "e0": spatial.SpatialEntity("e0", "e0", (12, 10, 0), team="opposition"),
        }
        hitbox = spatial.Hitbox("p0", (0, 0, 10, 10), 2, 2, "PIERCING", "1")
        self.assertEqual(spatial.resolve_hitbox_overlap(entities, [hitbox], 1), [])
        hits = spatial.resolve_hitbox_overlap(entities, [hitbox], 2)
        self.assertEqual([row["target_id"] for row in hits], ["e0"])

    def test_obstacle_requires_jump_and_dungeon_act_routes_mode(self):
        run_id, entered = self.start_room()
        run = self.service._active[run_id]
        blocked = self.service.design_action(run_id, {
            "type": "arcade_tick", "inputs": [{"actor": "p0", "dx": 50, "dy": 0}],
        })
        self.assertEqual(blocked["event"]["events"][0]["type"], "movement_blocked")
        changed = self.service.design_action(run_id, {
            "type": "arcade_set_movement_mode", "actor": "p0", "mode": "jump",
        })
        self.assertEqual(changed["event"]["movement_mode"], "jump")
        moved = self.service.design_action(run_id, {
            "type": "arcade_tick", "inputs": [{"actor": "p0", "dx": 50, "dy": 0}],
        })
        self.assertEqual(moved["event"]["events"][0]["type"], "arcade_move")
        self.assertEqual(self.service.observe(run_id)["arcade"]["entities"]["p0"]["position"][0], 60)

    def test_wren_flight_requires_tactical_wings_and_is_wren_only(self):
        doran_id, _ = self.start_room("doran-flight")
        with self.assertRaises(RunServiceError):
            self.service.design_action(doran_id, {
                "type": "arcade_toggle_flight", "actor": "p0", "on": True,
            })

        wren_id, _ = self.start_room("wren-flight", ["Wren"])
        wren = self.service._active[wren_id]
        with self.assertRaises(arcade.ArcadeError):
            arcade.toggle_flight(wren, "p0", True)
        self.assertEqual(t.current(wren), "p0")
        t.apply(wren, {"type": "wings", "actor": "p0"})
        flight = arcade.toggle_flight(wren, "p0", True)
        self.assertEqual(flight["movement_mode"], "fly")
        self.assertEqual(arcade.view(wren)["entities"]["p0"]["movement_mode"], "fly")

    def test_arcade_tick_uses_tactical_damage_and_clears_room_gate(self):
        run_id, _ = self.start_room()
        run = self.service._active[run_id]
        run.context["arcade"]["entities"]["p0"]["position"] = [80, 10, 0]
        run.opposition[0].hp = 1
        result = self.service.design_action(run_id, {
            "type": "arcade_tick", "inputs": [{"actor": "p0", "attack": True}],
        })
        event = result["event"]
        self.assertTrue(event["arcade"]["complete"])
        damage = next(row for row in event["arcade"]["events"] if row["type"] == "damage")
        self.assertEqual(damage["target"], "e0")
        self.assertEqual(event["reward"]["type"], "room_resolved")
        self.assertTrue(result["state"]["room"]["resolved"])
        self.assertIsNone(result["state"]["arcade"])
        self.assertNotIn("arcade", self.service._active[run_id].context)

    def test_untagged_combat_room_remains_turn_based(self):
        run_id = "normal"
        self.service.create(run_id, ["Doran"], ["Townsperson"], "normal-seed")
        self.service.design_start(run_id)
        run = self.service._active[run_id]
        run.context["dungeon"]["rooms"]["1:1"]["resolved"] = True
        run.context["dungeon"]["config"]["floors"][0].pop("room_overrides", None)
        entered = self.service.design_action(run_id, {"type": "exit"})
        self.assertIsNone(entered["state"]["room"].get("encounter_mode"))
        self.assertIsNone(entered["state"].get("arcade"))
        self.assertIsNotNone(entered["state"].get("combat"))

    def test_bridge_marks_arcade_actions_as_non_turn_updates(self):
        from hsr_bridge_watch import _is_arcade_action

        self.assertTrue(_is_arcade_action({"action": {"type": "arcade_tick"}}))
        self.assertTrue(_is_arcade_action({"action": {"type": "arcade_set_movement_mode"}}))
        self.assertFalse(_is_arcade_action({"action": {"type": "end_turn"}}))

    def test_jump_rises_then_lands_back_to_run(self):
        run_id, _ = self.start_room()
        self.service.design_action(run_id, {
            "type": "arcade_set_movement_mode", "actor": "p0", "mode": "jump",
        })
        heights = []
        for _ in range(12):
            result = self.service.design_action(run_id, {"type": "arcade_tick", "inputs": []})
            heights.append(result["event"]["arcade_view"]["entities"]["p0"]["position"][2])
        self.assertGreater(max(heights), 0)
        self.assertEqual(heights[-1], 0)
        self.assertEqual(self.service.observe(run_id)["arcade"]["entities"]["p0"]["movement_mode"], "run")

    def test_block_reduction_only_applies_to_a_front_hit(self):
        entities = {
            "p0": spatial.SpatialEntity("p0", "p0", (50, 10, 0), facing=1, team="party",
                                         status_tags={"blocking": True}),
            "e0": spatial.SpatialEntity("e0", "e0", (55, 10, 0), team="opposition"),
        }
        self.assertEqual(arcade._block_reduction("e0", "p0", entities), arcade.BLOCK_REDUCTION_FRONT)
        entities["e0"].position = (40, 10, 0)  # behind p0, who still faces right
        self.assertEqual(arcade._block_reduction("e0", "p0", entities), 0.0)
        entities["p0"].status_tags["blocking"] = False
        entities["e0"].position = (55, 10, 0)
        self.assertEqual(arcade._block_reduction("e0", "p0", entities), 0.0)

    def test_spawn_hit_applies_block_reduction_before_damage(self):
        run_id, _ = self.start_room()
        run = self.service._active[run_id]
        hitbox = spatial.Hitbox("e0", (0, 0, 10, 10), 1, 1, "SLASHING", "10")
        event = arcade.spawn_hit(run, "e0", "p0", hitbox, reduction=0.5)
        self.assertTrue(event["blocked"])
        self.assertEqual(event["raw"], 5)

    def test_dodge_grants_i_frames_then_a_cooldown(self):
        run_id, _ = self.start_room()
        run = self.service._active[run_id]
        run.context["arcade"]["entities"]["p0"]["position"] = [50, 10, 0]
        run.context["arcade"]["entities"]["e0"]["position"] = [55, 10, 0]
        first = self.service.design_action(run_id, {
            "type": "arcade_tick", "inputs": [{"actor": "p0", "dodge": True}],
        })
        first_events = first["event"]["events"]
        # The dash itself may be stopped by the room's own obstacle (covered
        # by test_obstacle_requires_jump_and_dungeon_act_routes_mode); the
        # i-frames apply either way, which is what this test is about.
        dodge_event = next(row for row in first_events if row["type"] in ("arcade_dodge", "arcade_dodge_blocked"))
        self.assertGreater(dodge_event["invulnerable_until_frame"], 0)
        self.assertFalse(any(row["type"] == "damage" and row.get("target") == "p0" for row in first_events))
        second = self.service.design_action(run_id, {
            "type": "arcade_tick", "inputs": [{"actor": "p0", "dodge": True}],
        })
        second_events = second["event"]["events"]
        self.assertTrue(any(row["type"] == "arcade_dodge_on_cooldown" for row in second_events))

    def test_combo_tier_escalates_across_chained_attacks(self):
        run_id, _ = self.start_room()
        run = self.service._active[run_id]
        run.opposition[0].hp = 1000
        run.context["arcade"]["entities"]["p0"]["position"] = [80, 10, 0]
        tiers = []
        for _ in range(3):
            result = self.service.design_action(run_id, {
                "type": "arcade_tick", "inputs": [{"actor": "p0", "attack": True}],
            })
            tiers.append(result["event"]["arcade_view"]["entities"]["p0"]["combo_tier"])
        self.assertEqual(tiers, [0, 1, 2])

    def test_ranged_projectile_travels_and_hits_then_clears(self):
        run_id, _ = self.start_room()
        run = self.service._active[run_id]
        run.opposition[0].hp = 1000
        run.context["arcade"]["entities"]["p0"]["position"] = [10, 10, 0]
        run.context["arcade"]["entities"]["e0"]["position"] = [90, 10, 0]
        spawn = self.service.design_action(run_id, {
            "type": "arcade_tick", "inputs": [{"actor": "p0", "ranged": True}],
        })
        self.assertTrue(any(row["type"] == "arcade_ranged_spawn" for row in spawn["event"]["events"]))
        hit_result = None
        for _ in range(10):
            result = self.service.design_action(run_id, {"type": "arcade_tick", "inputs": []})
            if any(row["type"] == "arcade_projectile_hit" for row in result["event"]["events"]):
                hit_result = result
                break
        self.assertIsNotNone(hit_result)
        self.assertEqual(hit_result["event"]["arcade_view"]["projectiles"], [])

    def test_advance_projectiles_excludes_friendly_fire(self):
        run_id, _ = self.start_room()
        run = self.service._active[run_id]
        run.context["arcade"]["projectiles"] = [{
            "projectile_id": "pr-test", "owner": "p0", "team": "party",
            "position": [10, 10, 0], "velocity": [10, 0], "shape": list(arcade.PROJECTILE_SHAPE),
            "damage_type": "FORCE", "damage_expression": "10", "bypass_resistance": False,
            "expires_frame": 100,
        }]
        entity_objects = {
            "p0": spatial.SpatialEntity("p0", "p0", (10, 10, 0), team="party"),
            "p1": spatial.SpatialEntity("p1", "p1", (20, 10, 0), team="party"),
        }
        events = arcade._advance_projectiles(run, 1, entity_objects, set())
        self.assertFalse(any(row["type"] == "arcade_projectile_hit" for row in events))
        self.assertEqual(len(run.context["arcade"]["projectiles"]), 1)

    def test_advance_projectiles_expires_at_lifetime(self):
        run_id, _ = self.start_room()
        run = self.service._active[run_id]
        run.context["arcade"]["projectiles"] = [{
            "projectile_id": "pr-test", "owner": "p0", "team": "party",
            "position": [10, 10, 0], "velocity": [10, 0], "shape": list(arcade.PROJECTILE_SHAPE),
            "damage_type": "FORCE", "damage_expression": "10", "bypass_resistance": False,
            "expires_frame": 1,
        }]
        entity_objects = {
            "p0": spatial.SpatialEntity("p0", "p0", (10, 10, 0), team="party"),
            "e0": spatial.SpatialEntity("e0", "e0", (500, 10, 0), team="opposition"),
        }
        events = arcade._advance_projectiles(run, 1, entity_objects, {"e0"})
        self.assertEqual(run.context["arcade"]["projectiles"], [])
        self.assertTrue(any(row["type"] == "arcade_projectile_expired" for row in events))

    def test_enemy_auto_attacks_a_party_member_in_range(self):
        run_id, _ = self.start_room()
        run = self.service._active[run_id]
        run.context["arcade"]["entities"]["p0"]["position"] = [50, 10, 0]
        run.context["arcade"]["entities"]["e0"]["position"] = [55, 10, 0]
        result = self.service.design_action(run_id, {"type": "arcade_tick", "inputs": []})
        events = result["event"]["events"]
        damage = next(row for row in events if row["type"] == "damage" and row["target"] == "p0")
        self.assertEqual(damage["source"], "e0")

    def test_free_text_flight_routes_to_shared_arcade_toggle(self):
        from hollowstar.intent import parse_intent

        run_id, _ = self.start_room("intent-flight")
        context = self.service.observe(run_id)
        self.assertEqual(parse_intent("fly", context), {
            "type": "arcade_toggle_flight", "actor": "p0", "on": True,
        })
        self.assertEqual(parse_intent("land", context), {
            "type": "arcade_toggle_flight", "actor": "p0", "on": False,
        })


if __name__ == "__main__":
    unittest.main()
