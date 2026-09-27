import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.sera_import import build_import_bundle, write_import_bundle


class SeraImportTests(unittest.TestCase):
    def _source(self) -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        data = root / "data"
        data.mkdir()
        (data / "weapons.json").write_text(json.dumps({"base_weapons": [{"name": "Test Blade", "base_damage": 3, "tags": ["PHYSICAL", "FIRE"]}]}), encoding="utf-8")
        (data / "equipment_items.json").write_text(json.dumps({"equipment_items": [{"name": "Test Helm", "slot": "Helmet", "stat_bonuses": {"AC": 1}, "damage_reduction": 1, "damage_resistance": 5, "resistances": {"fire": 10}}]}), encoding="utf-8")
        (data / "affixes.json").write_text(json.dumps({"affixes": [{"name": "Tested", "affix_type": "prefix", "flat_bonus": 2, "flat_condition": "enemy_full_hp", "multiplier": 1.0, "mult_condition": "always", "granted_tag": "DIVINE"}]}), encoding="utf-8")
        (data / "enemies.json").write_text(json.dumps({"enemy_archetypes": [{"name": "Test Fiend", "archetype": "elite", "max_hp": 10, "vulnerability": "REQUIRES_DIVINE"}]}), encoding="utf-8")
        return root

    def test_bundle_preserves_named_policies_and_counts(self):
        bundle = build_import_bundle(self._source())
        self.assertEqual(bundle["schema"], "hsr-sera-import-staging-1")
        self.assertEqual(len(bundle["weapons"]), 1)
        self.assertEqual(len(bundle["equipment"]), 1)
        self.assertEqual(len(bundle["affixes"]), 1)
        self.assertEqual(len(bundle["enemies"]), 1)
        self.assertIn("sera_fixed_pipeline_v1", bundle["policies"]["damage"])
        self.assertEqual(bundle["weapons"][0]["import_status"], "staged_fixed_damage")
        self.assertEqual(bundle["enemies"][0]["gate"], "requires_divine")

    def test_write_is_utf8_json(self):
        source = self._source()
        output_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, output_root, ignore_errors=True)
        output = output_root / "bundle.json"
        result = write_import_bundle(source, output)
        self.assertEqual(result, output)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["schema"], "hsr-sera-import-staging-1")


if __name__ == "__main__":
    unittest.main()
