"""Public appearance survives creation, world modes, and save/resume."""
import copy
from pathlib import Path
import tempfile
import unittest
from hollowstar.character_builder import preview
from hollowstar.profiles import ProfileService
from hollowstar.run_service import RunService
from hollowstar.view_model import build_public_view
from hollowstar import arcade

class PuppetPresentationTests(unittest.TestCase):
    def test_creation_world_and_saved_appearance_are_identical(self):
        with tempfile.TemporaryDirectory(prefix="hsr-puppet-") as tmp:
            root=Path(tmp)/".local"
            profiles=ProfileService(root/"reliquary_profiles")
            profile=preview({"name":"Puppet","creation_seed":"puppet-test","race":"half-elf","gender":"other",
                             "character_class":"magician","appearance":{"hair_style":"braided","hair_color":"auburn"}})["profile"]
            profiles.save("puppet",profile,replace=False)
            for scenario in ("floor_one_life","dungeon"):
                runs=RunService(root/"reliquary_runs",profile_root=profiles.root)
                kwargs={"scenario":scenario} if scenario=="floor_one_life" else {}
                runs.create(scenario,["custom:puppet"],["Townsperson"],"puppet-seed",**kwargs)
                state=runs.design_start(scenario)["state"]
                actor=build_public_view(state,run_id=scenario)["party"][0]
                self.assertEqual(actor["appearance"],profile["appearance"])
                self.assertEqual((actor["race_id"],actor["gender"]),("half-elf","other"))
                self.assertEqual(actor["equipment"][0]["presentation"]["silhouette"],"staff")
                resumed=RunService(root/"reliquary_runs",profile_root=profiles.root)
                resumed.load(scenario)
                restored=build_public_view(resumed.observe(scenario),run_id=scenario)["party"][0]
                self.assertEqual(restored["appearance"],actor["appearance"])
                self.assertEqual(restored["equipment"],actor["equipment"])

    def test_public_arcade_animation_hints_do_not_mutate_state(self):
        with tempfile.TemporaryDirectory(prefix="hsr-puppet-arcade-") as tmp:
            runs=RunService(Path(tmp)/".local/reliquary_runs")
            runs.create("puppet",["Doran"],["Townsperson"],"puppet")
            runs.design_start("puppet")
            run=runs._active["puppet"]
            run.context["dungeon"]["rooms"]["1:1"]["resolved"]=True
            runs.design_action("puppet",{"type":"exit"})
            run=runs._active["puppet"]
            record=run.context["arcade"]["entities"]["p0"]
            record["status_tags"]["combo_last_frame"]=run.context["arcade"]["frame"]
            before=copy.deepcopy(run.context["arcade"])
            public=arcade.view(run)["entities"]["p0"]
            self.assertEqual(public["attack_ticks"],6)
            self.assertEqual(public["velocity"],record["velocity"])
            self.assertNotIn("status_tags",public)
            self.assertEqual(run.context["arcade"],before)

if __name__=="__main__":unittest.main()
