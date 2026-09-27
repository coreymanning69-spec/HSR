"""Resolved spell transport must retain targets without exposing private ruling data."""
import copy
import unittest
from hollowstar.view_model import public_event_summary

class MagicPresentationTests(unittest.TestCase):
    def test_area_outcomes_and_private_data(self):
        source = {"type":"cast", "actor":"p0", "target":"e0", "damage":15,
                  "ruling":{"radius":20,"damage_type":"FIRE","private":"secret"},
                  "events":[{"target":"e0","save":{"success":False},
                             "result":{"damage":10,"damage_type":"FIRE","resources":{"secret":4}}},
                            {"target":"e1","save":{"success":True},"result":{"damage":5}}]}
        before=copy.deepcopy(source)
        public=public_event_summary(source)
        self.assertEqual(source,before)
        self.assertEqual(public["presentation"]["casting"],{"stance":"overhead","hands":2,"source":"hands","element":"fire"})
        self.assertEqual([e["target"] for e in public["events"]],["e0","e1"])
        self.assertEqual(public["events"][1]["result"]["damage"],5)
        self.assertNotIn("ruling",public)
        self.assertNotIn("resources",public["events"][0]["result"])

    def test_heal_and_missed_attack(self):
        heal=public_event_summary({"type":"cast","actor":"p0","ruling":{"operation":"heal"},
                                   "events":[{"target":"p0","healing":7}]})
        self.assertEqual(heal["presentation"]["casting"]["element"],"heal")
        self.assertEqual(heal["events"][0]["healing"],7)
        miss=public_event_summary({"type":"cast","actor":"p0","events":[
            {"target":"e0","attack":{"success":False,"natural":1},"result":None}]})
        self.assertFalse(miss["events"][0]["attack"]["success"])
        self.assertNotIn("damage",miss["events"][0])

    def test_condition_immunity_is_preserved(self):
        public=public_event_summary({"type":"cast","events":[{"target":"e0",
             "result":{"condition":"STUNNED","applied":False,"reason":"private"}}]})
        self.assertFalse(public["events"][0]["result"]["applied"])
        self.assertNotIn("reason",public["events"][0]["result"])

    def test_cast_source_defaults_and_authored_overrides(self):
        normal = public_event_summary({"type": "cast"})["presentation"]["casting"]
        staff = public_event_summary({"type": "staff_cast"})["presentation"]["casting"]
        self.assertEqual(normal["source"], "hands")
        self.assertEqual(staff["source"], "implement")
        authored = {"type": "cast", "ruling": {"presentation": {"casting": {
            "source": "implement", "stance": "aim", "hands": 1, "private": "secret"}}}}
        presented = public_event_summary(authored)["presentation"]["casting"]
        self.assertEqual(presented, {"source": "implement", "stance": "aim", "hands": 1, "element": "force"})
        authored["presentation"] = {"casting": {"source": "hands", "stance": "ward", "hands": 2}}
        presented = public_event_summary(authored)["presentation"]["casting"]
        self.assertEqual((presented["source"], presented["stance"], presented["hands"]), ("hands", "ward", 2))

    def test_invalid_cast_choreography_falls_back_without_private_fields(self):
        public = public_event_summary({"type": "cast", "presentation": {"casting": {
            "source": "secret-focus", "stance": "unknown", "hands": True, "private": "secret"}}})
        self.assertEqual(public["presentation"]["casting"], {
            "source": "hands", "stance": "gather", "hands": 2, "element": "force"})
        malformed = public_event_summary({"type": "cast", "presentation": {"casting": {
            "source": ["hands"], "stance": {"private": "unknown"}, "hands": [1, 2]}}})
        self.assertEqual(malformed["presentation"]["casting"], public["presentation"]["casting"])
        auto = public_event_summary({"type": "cast", "presentation": {"casting": {"source": "auto"}}})
        self.assertEqual(auto["presentation"]["casting"]["source"], "auto")

    def test_wand_public_item_is_a_one_handed_wooden_implement(self):
        from hollowstar.items import Item, item_presentation, public_item
        item = Item(name="Short casting implement", slot="hand", silhouette="wand")
        visual = item_presentation(item)
        self.assertEqual((visual["silhouette"], visual["item_type"], visual["handedness"],
                          visual["material"], visual["animation_profile"]),
                         ("wand", "weapon", "one-handed", "wood", "wand"))
        self.assertEqual(public_item(item)["presentation"], visual)

    def test_real_host_spell_receipt_and_asset_routes(self):
        import tempfile
        from pathlib import Path
        from hollowstar.run_service import RunService
        from hollowstar.spells import cast
        import hollowstar_web_server as web
        with tempfile.TemporaryDirectory() as temp:
            service=RunService(Path(temp)/".local/reliquary_runs")
            service.create("magic",["Doran","Wren"],["Townsperson"],"magic-articulation")
            service.design_start("magic")
            service.design_action("magic",{"type":"fight"})
            run=service._active["magic"]
            run.context["combat"]["positions"]["e0"]=[60,0,0]
            receipt=cast(run,"p1",{"spell":"Fireball@5e","center":[60,0,0]})
            public=public_event_summary(receipt)
            self.assertEqual(public["presentation"]["casting"]["stance"],"overhead")
            self.assertEqual(public["events"][0]["target"],"e0")
            self.assertEqual(public["events"][0]["result"]["damage"],receipt["events"][0]["result"]["damage"])
        for route in ("/magic-articulation.js","/web/magic-articulation.js"):
            self.assertTrue((web.ROOT/web.Handler.assets[route]).is_file())
