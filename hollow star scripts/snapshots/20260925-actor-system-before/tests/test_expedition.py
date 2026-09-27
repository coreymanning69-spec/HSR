"""Encounters expedition: seeded route, node resolution modes, AFK bounds."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar import expedition, tactical as t
from hollowstar.run_service import RunService, RunServiceError
from hollowstar.view_model import build_public_view


class ExpeditionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="hsr-expedition-")
        self.root = Path(self.tmp.name) / ".local" / "reliquary_runs"
        self.service = RunService(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def start(self, run_id="exp", seed="exp-seed"):
        self.service.create(run_id, ["Doran", "Wren"], ["Townsperson"], seed)
        self.service.design_start(run_id)
        self.service._active[run_id].context["dungeon"]["rooms"]["1:1"]["resolved"] = True
        return self.service.design_action(run_id, {"type": "expedition_start"})

    def test_route_is_seeded_and_connected(self):
        first = self.start("a")["state"]["expedition"]["maps"]["1"]
        second = self.start("b")["state"]["expedition"]["maps"]["1"]
        self.assertEqual(first, second)
        columns = first["columns"]
        self.assertEqual([node["type"] for node in columns[-1]], ["boss"])
        for current, following in zip(columns, columns[1:]):
            ids = {node["id"] for node in following}
            self.assertTrue(all(node["links"] and set(node["links"]) <= ids for node in current))
            linked = {link for node in current for link in node["links"]}
            self.assertEqual(linked, ids)

    def test_view_does_not_mutate_route(self):
        self.start()
        run = self.service._active["exp"]
        before = repr(run.context["dungeon"]["expedition"])
        expedition.view(run)
        self.assertEqual(before, repr(run.context["dungeon"]["expedition"]))

    def test_unreachable_node_is_refused(self):
        self.start()
        with self.assertRaises(RunServiceError):
            self.service.design_action("exp", {"type": "expedition_choose", "node": "1:7:0"})

    def test_tactical_fight_node_uses_turn_based_ladder(self):
        state = self.start()["state"]["expedition"]
        fights = [node for column in state["maps"]["1"]["columns"] for node in column
                  if node["type"] == "fight" and node["id"] in state["choices"]]
        self.assertTrue(fights, "exp-seed draws a fight in column two")
        node = fights[0]
        outcome = self.service.design_action("exp", {"type": "expedition_choose", "node": node["id"],
                                                     "mode": "tactical"})
        run = self.service._active["exp"]  # transitions commit a clone
        room = outcome["state"]["room"]
        self.assertEqual(room["encounter_mode"], "turn_based")
        self.assertIsNone(outcome["state"]["arcade"])
        self.assertEqual(len(run.opposition), node["ladder"]["arcade_enemy_count"])
        layout = outcome["state"]["combat"]["formation"]
        self.assertEqual(layout, t.formation(run))
        for key, spot in layout.items():
            self.assertEqual(spot["side"], "party" if key.startswith("p") else "enemy")
        self.assertEqual(layout["p1"]["row"], "back")  # Wren casts from the back row

    def test_arcade_mode_enters_arcade_waves(self):
        run_id = "arc"
        self.service.create(run_id, ["Doran"], ["Townsperson"], "arcade-seed")
        self.service.design_start(run_id)
        run = self.service._active[run_id]
        run.context["dungeon"]["rooms"]["1:1"]["resolved"] = True
        state = self.service.design_action(run_id, {"type": "expedition_start"})["state"]["expedition"]
        exp = self.service._active[run_id].context["dungeon"]["expedition"]
        combat_nodes = [node_id for node_id in state["choices"]
                        if expedition._node(exp, node_id)["type"] in expedition.COMBAT_NODES]
        if not combat_nodes:
            self.skipTest("seed drew no combat node in column two")
        node = expedition._node(exp, combat_nodes[0])
        outcome = self.service.design_action(run_id, {"type": "expedition_choose",
                                                      "node": node["id"], "mode": "arcade"})
        self.assertEqual(outcome["state"]["room"]["encounter_mode"], "arcade")
        self.assertEqual(outcome["state"]["arcade"]["waves"], len(node["ladder"]["waves"]))

    def test_afk_run_is_bounded_and_summarised(self):
        self.start()
        outcome = self.service.design_action("exp", {"type": "expedition_auto", "max_nodes": 3})
        summary = outcome["event"]["summary"]
        self.assertLessEqual(len(summary["nodes"]), 3)
        self.assertIn(summary["stopped"], {"budget_spent", "retreat_threshold", "run_ended",
                                           "route_complete", "action_cap"})
        self.assertEqual(outcome["state"]["expedition"]["last_auto"], summary)

    def test_retreat_threshold_pauses_before_next_node(self):
        self.start()
        run = self.service._active["exp"]
        for actor in run.party:
            actor.hp = max(1, actor.max_hp // 10)
        outcome = self.service.design_action("exp", {"type": "expedition_auto", "max_nodes": 2,
                                                     "retreat_below": 0.5})
        self.assertEqual(outcome["event"]["summary"]["stopped"], "retreat_threshold")
        self.assertEqual(outcome["event"]["summary"]["nodes"], [])

    def test_auto_bounds_are_validated(self):
        self.start()
        for bad in ({"max_nodes": 0}, {"max_nodes": 7}, {"max_nodes": True}, {"retreat_below": 1.5}):
            with self.assertRaises(RunServiceError):
                self.service.design_action("exp", {"type": "expedition_auto", **bad})

    def test_public_view_carries_expedition(self):
        state = self.start()["state"]
        view = build_public_view(state, mode="SANDBOX", run_id="exp")
        self.assertTrue(view["expedition"]["active"])
        self.assertTrue(view["expedition"]["choices"])
        reach = {node["id"]: node["reach"] for column in view["expedition"]["maps"]["1"]["columns"]
                 for node in column}
        self.assertTrue(all(reach[node_id] == "available" for node_id in view["expedition"]["choices"]))


class ExpeditionHostTest(unittest.TestCase):
    def test_host_advertises_expedition_commands(self):
        from hollowstar import host
        self.assertTrue({"expedition_start", "expedition_choose", "expedition_auto",
                         "expedition_view"} <= host.EXPEDITION_COMMANDS)

    def test_mcp_tool_maps_steps_to_design_actions(self):
        import hsr_mcp_server as server
        tool = server.TOOLS_BY_NAME["hsr_expedition"]
        fields = tool["fields"]({"run_id": "r", "step": "choose", "node": "1:2:0", "mode": "auto"})
        self.assertEqual(fields["action"], {"type": "expedition_choose", "node": "1:2:0", "mode": "auto"})


if __name__ == "__main__":
    unittest.main()
