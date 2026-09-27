"""Paperdoll appearance styling: the clothing dye must reach the CSS variables.

Runs web/paperdoll.js's appearanceStyle() in Node. Presentation only; no
mechanics are read or written.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NODE_PROBE = (Path(__file__).with_name("web-probe-prelude.js").read_text(encoding="utf-8") + r"""
const {appearanceStyle} = await webModule('paperdoll.js');
const style = appearance => appearanceStyle({appearance});
console.log(JSON.stringify({
  outfitOnly: style({outfit: {hex: '#3f4a63'}}),
  dyed: style({outfit: {hex: '#3f4a63'}, cloth_color: {hex: '#e8e2d0'}}),
  asOutfit: style({outfit: {hex: '#3f4a63'}, cloth_color: {id: 'as-outfit'}}),
  badHex: style({outfit: {hex: '#3f4a63'}, cloth_color: {hex: 'red;background:url(x)'}}),
}));
""")


class PaperdollAppearanceTests(unittest.TestCase):
    probe: dict = {}

    @classmethod
    def setUpClass(cls):
        res = subprocess.run(["node", "--input-type=module", "-e", NODE_PROBE], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(f"appearance probe failed: {res.stderr}")
        cls.probe = json.loads(res.stdout.strip().splitlines()[-1])

    @staticmethod
    def _outfit(style: str) -> str:
        """The winning --outfit value: the last declaration in the attribute."""
        values = [part.split(":", 1)[1] for part in style.split(";") if part.startswith("--outfit:")]
        return values[-1]

    def test_dye_overrides_the_outfit_colour(self):
        self.assertEqual(self._outfit(self.probe["outfitOnly"]), "#3f4a63")
        self.assertEqual(self._outfit(self.probe["dyed"]), "#e8e2d0")

    def test_as_outfit_keeps_the_outfit_colour(self):
        self.assertEqual(self._outfit(self.probe["asOutfit"]), "#3f4a63")

    def test_non_hex_dye_is_dropped(self):
        self.assertEqual(self._outfit(self.probe["badHex"]), "#3f4a63")
        self.assertNotIn("url(", self.probe["badHex"])


if __name__ == "__main__":
    unittest.main()
