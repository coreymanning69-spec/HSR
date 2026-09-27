"""Character creation matrix, receipts, host boundary, and class mechanics."""
from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.character_builder import options, preview, preview_with_notes, randomize_build, roll_abilities
from hollowstar.host import HSRHost
from hollowstar.profiles import APPEARANCE_FIELDS, ProfileError, ProfileService, normalize_appearance
from hollowstar.run_service import RunService, RunServiceError
from hollowstar import tactical as t
from hollowstar import dungeon


class CharacterCreationTest(unittest.TestCase):
    def test_public_gender_vocabulary_and_legacy_aliases_preserve_receipt_metadata(self):
        for gender in ("male", "female", "other"):
            result = preview({"name": "Gender", "creation_seed": "gender-" + gender, "gender": gender})
            self.assertEqual(result["profile"]["gender"], gender)
            self.assertEqual(result["receipt"]["gender"], gender)
        legacy = preview({"name": "Legacy", "creation_seed": "legacy-gender", "gender": "feminine"})
        self.assertEqual(legacy["profile"]["gender"], "female")
        self.assertEqual(legacy["receipt"]["legacy_gender"], "feminine")

    def test_all_twenty_five_combinations_at_low_mid_and_high_level(self):
        choices = options()
        self.assertEqual(len(choices["races"]), 5)
        self.assertEqual(len(choices["classes"]), 5)
        for race in choices["races"]:
            for character_class in choices["classes"]:
                for level in (1, 3, 20):
                    result = preview({"name": "Matrix", "creation_seed": "matrix-seed",
                                      "race": race["id"], "character_class": character_class["id"], "background": "Veteran",
                                      "level": level})
                    profile = result["profile"]
                    self.assertEqual(profile["race_id"], race["id"])
                    self.assertEqual(profile["class_id"], character_class["id"])
                    self.assertEqual(profile["level"], level)
                    self.assertTrue(profile["equipment"])
                    self.assertEqual(len(result["build_hash"]), 64)

    def test_roll_receipts_and_single_replacement_set_are_exact(self):
        first = roll_abilities("receipt", 0)
        second = roll_abilities("receipt", 1)
        self.assertEqual(first, roll_abilities("receipt", 0))
        self.assertNotEqual(first["scores"], second["scores"])
        for row in first["rolls"] + second["rolls"]:
            self.assertEqual(row["dropped"], min(row["dice"]))
            self.assertEqual(row["total"], sum(row["dice"]) - row["dropped"])
        result = preview({"name":"Reroll", "creation_seed":"receipt", "background":"Veteran", "roll_set":1})
        self.assertEqual(len(result["receipt"]["roll_sets"]), 2)
        self.assertEqual(result["receipt"]["final_scores"], result["profile"]["ability_scores"])

    def test_race_packages_and_goblin_luck(self):
        base = dict.fromkeys(("STR", "DEX", "CON", "INT", "WIS", "CHA"), 10)
        human = preview({"name":"H", "ability_scores":base, "race":"Human", "background":"Veteran"})["profile"]
        elf = preview({"name":"E", "ability_scores":base, "race":"Elf", "background":"Veteran"})["profile"]
        half = preview({"name":"X", "ability_scores":base, "race":"Half-Elf",
                        "floating_bonuses":["STR","CON"], "background":"Veteran"})["profile"]
        orc = preview({"name":"O", "ability_scores":base, "race":"Orc", "background":"Veteran"})["profile"]
        goblin = preview({"name":"G", "ability_scores":base, "race":"Goblin", "background":"Veteran"})["profile"]
        self.assertEqual(human["ability_scores"], {"STR":12,"DEX":11,"CON":11,"INT":11,"WIS":11,"CHA":11})
        self.assertEqual((elf["ability_scores"]["DEX"], elf["ability_scores"]["INT"]), (12, 11))
        self.assertEqual((half["ability_scores"]["CHA"], half["ability_scores"]["STR"], half["ability_scores"]["CON"]), (12, 12, 11))
        self.assertEqual((orc["ability_scores"]["STR"], orc["ability_scores"]["CON"]), (13, 12))
        self.assertEqual(goblin["skill_bonuses"]["Luck"], 5)

    def test_level_three_spell_budget_is_fifteen_and_rank_limited(self):
        for class_id in ("magician", "cleric"):
            result = preview({"name":"Caster", "creation_seed":"spell-budget",
                              "character_class":class_id, "background":"Veteran", "level":3, "spell_budget":15})
            self.assertEqual(result["receipt"]["spell_points_spent"], 15)
            self.assertEqual(result["profile"]["resources"]["casting_energy"], 5)
            self.assertEqual(result["profile"]["build_rules"]["spell_rank_cap"], 2)

    def test_v1_profile_loads_with_v2_defaults(self):
        with tempfile.TemporaryDirectory(prefix="hsr-v1-profile-") as tmp:
            service = ProfileService(Path(tmp))
            body = preview({"name":"Legacy", "creation_seed":"legacy", "background":"Veteran"})["profile"]
            service.save("legacy", body, replace=False)
            path = Path(tmp) / "legacy.json"
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["schema_version"] = "hollow-star-custom-profile-1"
            for field in ("race_id", "class_id", "features", "interaction_tags",
                          "known_spells", "origin_item", "background", "heirloom_item", "creation_receipt"):
                raw.pop(field, None)
            path.write_text(json.dumps(raw), encoding="utf-8")
            loaded = service._load("legacy")
            self.assertEqual(loaded["schema_version"], "hollow-star-custom-profile-3")
            self.assertEqual(loaded["race_id"], loaded["race"].lower().replace(" ", "-"))
            self.assertEqual(loaded["features"], [])

    def test_each_ancestry_exposes_an_authored_noncombat_lane(self):
        cases = {
            "human": ("common_ground", "negotiate", "social", "human_common_ground"),
            "elf": ("old_magic", "investigate", "secret", "elf_old_magic"),
            "half-elf": ("bridge_kin", "negotiate", "social", "half_elf_bridge_kin"),
            "orc": ("force_route", "disarm", "hazard", "orc_force_route"),
            "goblin": ("scrapwise", "avoid", "hazard", "goblin_luck_hazard"),
        }
        for race, (tag, action, room_kind, hook_id) in cases.items():
            with self.subTest(race=race):
                run = SimpleNamespace(context={"party_rules":{"p0":{"interaction_tags":[tag]}}})
                hook = dungeon.ancestry_hook(run, "p0", action, {"kind":room_kind})
                self.assertEqual(hook["id"], hook_id)

    def test_origin_categories_have_five_results_and_exact_weights(self):
        registry=json.loads((Path(__file__).resolve().parents[1]/"hollowstar/content/character_creation.json").read_text(encoding="utf-8"))
        table=registry["origin_table"]
        expected={"keepsake":45,"tool":30,"heirloom":20,"oddity":5}
        for category,weight in expected.items():
            rows=[row for row in table if row["category"]==category]
            self.assertEqual(len(rows),5)
            self.assertEqual(sum(row["weight"] for row in rows),weight)

    def test_wayfinder_threshold_and_once_per_trap(self):
        class Fixed:
            def __init__(self,value): self.value=value
            def randint(self,low,high): return self.value
        for value,triggered in ((24,True),(25,True),(26,False)):
            run=SimpleNamespace(context={"party_rules":{"p0":{"origin_hook":"wayfinder_25",
                                                                 "origin_item_id":"wayfinder-amulet"}}},
                                rng=Fixed(value))
            row={}
            result=dungeon.wayfinder_check(run,"p0",row)
            self.assertEqual(result["triggered"],triggered)
            self.assertEqual(result["roll"],value)
            self.assertIsNone(dungeon.wayfinder_check(run,"p0",row))

    def test_host_requires_preview_hash_and_saves_same_sheet(self):
        with tempfile.TemporaryDirectory(prefix="hsr-builder-") as tmp:
            host = HSRHost.from_options(data_root=Path(tmp)/".local")
            self.assertTrue(host.handle({"id":"b","command":"boot","mode":"DESIGN"})["ok"])
            build={"name":"Grik","creation_seed":"grik","race":"Goblin",
                   "character_class":"Rogue","background":"Scout","level":3}
            draft=host.handle({"id":"p","command":"preview_character","build":build})
            self.assertTrue(draft["ok"])
            bad=host.handle({"id":"x","command":"build_character","profile_id":"grik",
                             "build":build,"expected_build_hash":"wrong"})
            self.assertFalse(bad["ok"])
            fingerprint=draft["result"]["character"]["build_hash"]
            saved=host.handle({"id":"s","command":"build_character","profile_id":"grik",
                               "build":build,"expected_build_hash":fingerprint})
            self.assertTrue(saved["ok"])
            self.assertEqual(saved["result"]["profile"]["identity"]["race_id"],"goblin")

    def test_forge_accepts_custom_profile_creation_for_authored_story(self):
        with tempfile.TemporaryDirectory(prefix="hsr-forge-role-") as tmp:
            host = HSRHost.from_options(data_root=Path(tmp) / ".local")
            self.assertTrue(host.handle({"id": "b", "command": "boot", "mode": "FORGE", "intent": "role test"})["ok"])
            build = {"name": "Story Custom", "creation_seed": "story-custom", "background": "scout"}
            preview = host.handle({"id": "p", "command": "preview_character", "build": build})
            reply = host.handle({
                "id": "s", "command": "build_character", "profile_id": "story-custom",
                "build": build, "expected_build_hash": preview["result"]["character"]["build_hash"],
            })
            self.assertTrue(reply["ok"], reply)
            started = host.handle({
                "id": "run", "command": "start-run", "mode": "FORGE", "run_id": "story-custom-run",
                "party": ["custom:story-custom"], "lead_selector": "custom:story-custom",
                "opposition": ["Townsperson"], "scenario": "reliquary_city",
                "module_id": "reliquary-template", "seed": "story-custom-seed",
            })
            self.assertTrue(started["ok"], started)
            self.assertEqual(started["result"]["run"]["context"]["host_mode"], "FORGE")
            view = host.handle({"id": "read", "command": "readout", "run_id": "story-custom-run"})
            self.assertTrue(view["ok"], view)
            player = view["result"]["readout"]["public_view"]["party"][0]
            self.assertEqual(player["name"], "Story Custom")
            self.assertEqual(player.get("ability_options", []), [])
            self.assertNotIn(player["name"].lower(), {"doran", "wren"})

    def test_build_notes_are_deterministic_and_outside_the_build_hash(self):
        choices = options()
        self.assertEqual(set(choices["class_ratings"]), {row["id"] for row in choices["classes"]})
        for race in choices["races"]:
            for character_class in choices["classes"]:
                build = {"name": "Notes", "creation_seed": "notes-seed", "race": race["id"],
                         "character_class": character_class["id"], "background": "scholar"}
                first, second = preview_with_notes(build), preview_with_notes(build)
                self.assertEqual(first["notes"], second["notes"])
                self.assertEqual(first["build_hash"], preview(build)["build_hash"])
                notes = first["notes"]
                self.assertTrue(notes["archetype"] and notes["strengths"] and notes["watchouts"] and notes["tip"])
                self.assertTrue(all(1 <= value <= 5 for value in notes["ratings"].values()))
        untrained = preview_with_notes({"name": "Elf", "creation_seed": "pp", "race": "elf",
                                        "character_class": "warrior", "background": "veteran",
                                        "skills": ["Athletics", "Intimidation"]})
        wis = (untrained["profile"]["ability_scores"]["WIS"] - 10) // 2
        self.assertEqual(untrained["notes"]["derived"]["passive_perception"], 10 + wis + 2)

    def test_randomize_build_is_seed_deterministic_and_previewable(self):
        self.assertEqual(randomize_build("00042"), randomize_build("00042"))
        seen = set()
        for number in range(1, 40):
            build = randomize_build(f"{number:05d}")
            seen.add((build["race"], build["character_class"]))
            self.assertTrue(preview_with_notes({**build, "name": "Random"})["build_hash"])
        self.assertGreater(len(seen), 8)

    def test_creation_seed_counter_pads_peeks_freely_and_advances_on_confirm(self):
        with tempfile.TemporaryDirectory(prefix="hsr-seed-") as tmp:
            host = HSRHost.from_options(data_root=Path(tmp) / ".local")
            self.assertTrue(host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})["ok"])
            peek = lambda: host.handle({"id": "k", "command": "peek_creation_seed"})["result"]["seed"]["creation_seed"]
            self.assertEqual(peek(), "00001")
            self.assertEqual(peek(), "00001")
            rolled = host.handle({"id": "r", "command": "randomize_build", "creation_seed": "00001", "name": "Rand"})
            self.assertTrue(rolled["ok"])
            build = rolled["result"]["build"]; build["name"] = "Rand"
            fingerprint = rolled["result"]["character"]["build_hash"]
            saved = host.handle({"id": "s", "command": "build_character", "profile_id": "web-00001",
                                 "build": build, "expected_build_hash": fingerprint})
            self.assertTrue(saved["ok"], saved)
            self.assertTrue(saved["result"]["created"])
            self.assertEqual(saved["result"]["seed_commit"]["next"], 2)
            self.assertEqual(peek(), "00002")
            retried = host.handle({"id": "s-retry", "command": "build_character", "profile_id": "web-00001",
                                   "build": build, "expected_build_hash": fingerprint})
            self.assertTrue(retried["ok"], retried)
            self.assertFalse(retried["result"]["created"])
            self.assertIsNone(retried["result"]["seed_commit"])
            self.assertEqual(peek(), "00002")
            changed = {**build, "name": "Different"}
            changed_preview = host.handle({"id": "p-changed", "command": "preview_character", "build": changed})
            conflict = host.handle({"id": "s-conflict", "command": "build_character", "profile_id": "web-00001",
                                    "build": changed,
                                    "expected_build_hash": changed_preview["result"]["character"]["build_hash"]})
            self.assertFalse(conflict["ok"])
            self.assertIn("already exists", conflict["error"]["message"])
            # A hand-typed seed saves normally and leaves the counter alone.
            custom = {"name": "Hand", "creation_seed": "my-seed", "background": "scout"}
            draft = host.handle({"id": "p", "command": "preview_character", "build": custom})
            self.assertTrue(host.handle({"id": "t", "command": "build_character", "profile_id": "web-my-seed", "build": custom,
                                         "expected_build_hash": draft["result"]["character"]["build_hash"]})["ok"])
            self.assertEqual(peek(), "00002")
            counter = Path(tmp) / ".local" / "creation_seed_counter.json"
            counter.write_text("{not json", encoding="utf-8")
            self.assertEqual(peek(), "00002")  # corrupt counter: falls back and skips saved numbers

    def test_explicit_all_eighteen_sheet_is_refused(self):
        with self.assertRaises(Exception) as caught:
            preview({"name": "Impossible", "creation_seed": "impossible",
                     "ability_scores": {ability: 18 for ability in ("STR", "DEX", "CON", "INT", "WIS", "CHA")},
                     "background": "Veteran"})
        self.assertIn("all six abilities", str(caught.exception))

    def test_class_actions_use_frozen_profile_rules(self):
        with tempfile.TemporaryDirectory(prefix="hsr-classes-") as tmp:
            root=Path(tmp)/".local"; profiles=ProfileService(root/"reliquary_profiles")
            for class_id in ("warrior","magician","archer","rogue","cleric"):
                built=preview({"name":class_id.title(),"creation_seed":class_id,
                               "character_class":class_id,"background":"Veteran","level":3})["profile"]
                profiles.save(class_id,built,replace=False)
            for class_id in ("warrior","magician","archer","rogue","cleric"):
                runs=RunService(root/"reliquary_runs",profile_root=profiles.root)
                run_id=f"run-{class_id}";runs.create(run_id,[f"custom:{class_id}"],["Townsperson"],class_id)
                runs.design_start(run_id);runs.design_action(run_id,{"type":"fight"})
                run=runs._active[run_id]
                run.context["combat"]["cursor"]=run.context["combat"]["order"].index("p0")
                if class_id == "warrior":
                    run.party[0].hp-=5
                    event=runs.design_action(run_id,{"type":"second_wind","actor":"p0"})["event"]
                    self.assertEqual(event["type"],"healing")
                elif class_id == "magician":
                    spell=next(row for row in run.context["combat"]["rules"]["p0"]["known_spells"] if row=="Arcane Bolt@HSR")
                    event=runs.design_action(run_id,{"type":"cast","actor":"p0","spell":spell,"targets":["e0"]})["event"]
                    self.assertEqual(event["spell"],spell)
                elif class_id == "archer":
                    event=runs.design_action(run_id,{"type":"aim","actor":"p0"})["event"]
                    self.assertEqual(event["attack_bonus"],2)
                elif class_id == "rogue":
                    event=runs.design_action(run_id,{"type":"dash","actor":"p0"})["event"]
                    self.assertTrue(event["cunning_action"])
                else:
                    run.party[0].hp-=5
                    event=runs.design_action(run_id,{"type":"channel_grace","actor":"p0","target":"p0"})["event"]
                    self.assertEqual(event["type"],"channel_grace")

    def test_backgrounds_cover_each_ability_and_receipts_are_deterministic(self):
        choices = options()
        self.assertEqual({row["ability"] for row in choices["backgrounds"]}, {"STR","DEX","CON","INT","WIS","CHA"})
        first = preview({"name":"Background","creation_seed":"background","background":"Envoy"})
        second = preview({"name":"Background","creation_seed":"background","background":"Envoy"})
        self.assertEqual(first["receipt"]["background"], second["receipt"]["background"])
        self.assertEqual(first["receipt"]["background"]["gold"]["total"], first["profile"]["background"]["starting_gold"])
        self.assertLessEqual(first["profile"]["ability_scores"]["CHA"], 20)
        heirloom = first["receipt"]["heirloom_roll"]
        self.assertEqual(heirloom["triggered"], heirloom["roll"] <= heirloom["threshold"])
        self.assertNotEqual(heirloom["item_id"], first["receipt"]["origin_roll"]["item_id"])

    def test_lead_background_owns_starting_treasury_and_survives_resume(self):
        with tempfile.TemporaryDirectory(prefix="hsr-launch-") as tmp:
            root = Path(tmp) / ".local"
            profiles = ProfileService(root / "reliquary_profiles")
            lead = preview({"name":"Lead","creation_seed":"lead","background":"Envoy"})["profile"]
            companion = preview({"name":"Companion","creation_seed":"companion","background":"Veteran"})["profile"]
            profiles.save("lead", lead, replace=False); profiles.save("companion", companion, replace=False)
            runs = RunService(root / "reliquary_runs", profile_root=profiles.root)
            summary = runs.create("lead-run", ["custom:lead", "custom:companion"], ["Townsperson"], "launch", lead_selector="custom:lead")
            self.assertEqual(summary.context["run_launch"]["lead_selector"], "custom:lead")
            self.assertEqual(summary.context["run_launch"]["starting_gold"], lead["background"]["starting_gold"])
            started = runs.design_start("lead-run")
            self.assertEqual(started["state"]["currency"], lead["background"]["starting_gold"])
            resumed = RunService(root / "reliquary_runs", profile_root=profiles.root)
            self.assertEqual(resumed.load("lead-run").context["run_launch"], summary.context["run_launch"])
            with self.assertRaises(RunServiceError):
                runs.create("bad-lead", ["custom:lead"], ["Townsperson"], "launch", lead_selector="custom:missing")
            with self.assertRaises(RunServiceError):
                runs.create("dupe-party", ["custom:lead", "custom:lead"], ["Townsperson"], "launch")


class AppearanceTest(unittest.TestCase):
    """Cosmetic appearance is player-facing and must never touch mechanics."""

    def test_defaults_fill_in_when_no_appearance_is_supplied(self):
        profile = preview({"name": "Plain", "creation_seed": "plain", "race": "human"})["profile"]
        appearance = profile["appearance"]
        self.assertEqual(set(appearance), set(APPEARANCE_FIELDS))
        # The fallbacks reproduce the current stylesheet so sheets saved before
        # appearance existed keep rendering exactly as they did.
        self.assertEqual(appearance["skin_tone"]["hex"], "#ecd2bd")
        self.assertEqual(appearance["hair_color"]["hex"], "#ddd6d1")
        self.assertEqual(appearance["eye_color"]["hex"], "#777096")

    def test_explicit_selection_round_trips_with_display_values(self):
        picked = {"skin_tone": "deep", "hair_style": "braided", "hair_color": "auburn",
                  "eye_color": "amber", "body_type": "broad", "outfit": "robe"}
        profile = preview({"name": "Picked", "creation_seed": "picked", "race": "human",
                           "appearance": picked})["profile"]
        for field, chosen in picked.items():
            self.assertEqual(profile["appearance"][field]["id"], chosen)
        self.assertEqual(profile["appearance"]["hair_color"]["hex"], "#7d3b2e")
        self.assertEqual(profile["appearance"]["body_type"]["scale"], 1.08)

    def test_distinct_paperdoll_choices_and_public_presentation_contract(self):
        picked = {
            "face_shape": "angular", "facial_marks": "temple-mark", "ear_shape": "swept",
            "cloak_style": "hooded-cloak", "headgear_style": "full-helm",
            "weapon_style": "heavy", "offhand_style": "kite-shield", "trinket_style": "medal",
        }
        profile = preview({"name": "Paperdoll", "creation_seed": "paperdoll", "race": "human",
                           "character_class": "warrior", "appearance": picked})["profile"]
        for field, chosen in picked.items():
            self.assertEqual(profile["appearance"][field]["id"], chosen)
        presentation = profile["build_rules"]["presentation"]
        self.assertEqual(presentation["schema"], "hsr-paperdoll-presentation-1")
        self.assertEqual(presentation["appearance"]["headgear_style"]["visual"]["layer_ids"], ["item:full-helm"])

    def test_unknown_field_or_option_is_rejected(self):
        for bad in ({"nose_shape": "aquiline"}, {"eye_color": "chartreuse"}):
            with self.assertRaises(ProfileError):
                preview({"name": "Bad", "creation_seed": "bad", "race": "human", "appearance": bad})

    def test_skin_tones_are_gated_by_race(self):
        orc = preview({"name": "Grok", "creation_seed": "grok", "race": "orc"})["profile"]
        self.assertEqual(orc["appearance"]["skin_tone"]["id"], "ash-green")
        # A human tone is not offered to an orc, and vice versa.
        with self.assertRaises(ProfileError):
            preview({"name": "Grok", "creation_seed": "grok", "race": "orc",
                     "appearance": {"skin_tone": "fair"}})
        with self.assertRaises(ProfileError):
            preview({"name": "Ann", "creation_seed": "ann", "race": "human",
                     "appearance": {"skin_tone": "moss"}})

    def test_appearance_is_mechanically_inert(self):
        """Two sheets differing only in looks must roll and stat identically."""
        def build(hair):
            return preview({"name": "Twin", "creation_seed": "twin-seed", "race": "human",
                            "character_class": "warrior", "appearance": {"hair_color": hair}})

        gold, black = build("gold"), build("black")
        for field in ("ability_scores", "armor_class", "max_hp", "initiative_bonus",
                      "speed", "proficiency_bonus", "skill_bonuses", "equipment"):
            self.assertEqual(gold["profile"][field], black["profile"][field], field)
        self.assertEqual(gold["receipt"], black["receipt"])
        self.assertNotEqual(gold["profile"]["appearance"], black["profile"]["appearance"])

    def test_normalize_accepts_a_resolved_entry_so_saves_round_trip(self):
        """Saving a built sheet re-normalizes it; that must be idempotent."""
        catalog = json.loads(
            (Path(__file__).resolve().parents[1]
             / "hollowstar" / "content" / "character_creation.json").read_text(encoding="utf-8")
        )["appearance"]
        once = normalize_appearance({"hair_color": "gold"}, catalog, "human")
        twice = normalize_appearance(once, catalog, "human")
        self.assertEqual(once, twice)

    def test_a_sheet_saved_before_appearance_existed_still_loads(self):
        built = preview({"name": "Legacy", "creation_seed": "legacy-appearance",
                         "race": "human", "character_class": "warrior"})["profile"]
        built.pop("appearance")
        built.pop("build_rules", None)
        built.pop("creation_receipt", None)
        with tempfile.TemporaryDirectory() as tmp:
            service = ProfileService(Path(tmp))
            saved = service.save("legacy", built, replace=False)
            self.assertEqual(set(saved["appearance"]), set(APPEARANCE_FIELDS))
            self.assertEqual(saved["appearance"]["hair_color"]["hex"], "#ddd6d1")


if __name__ == "__main__":
    unittest.main()
