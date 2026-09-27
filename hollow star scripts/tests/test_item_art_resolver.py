"""Tests for item art assets and the frontend tiered SVG resolver.

Asserts:
1. Every sprite referenced in character_creation.json and items.json exists on disk.
2. Headless Node verification of web/ui-components.js:
   - Vaelith's equipment (mace, scale mail, shield, holy focus, signet ring) resolves to valid SVGs.
   - Mundane tableware and props (fork, plate, spoon, tankard, torch, rations, etc.) resolve to valid SVGs.
   - Uncataloged/unknown items fall back gracefully to silhouette/slot archetype SVGs.
   - The string 'Art pending' or class 'art-fallback' is NEVER produced.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
CONTENT = ROOT / "hollowstar" / "content"
ITEMS_SPRITE_DIR = WEB / "assets" / "sprites" / "items"


class ItemArtAssetDiskTests(unittest.TestCase):
    def test_all_class_starting_equipment_sprites_exist_on_disk(self):
        data = json.loads((CONTENT / "character_creation.json").read_text(encoding="utf-8"))
        for class_id, class_data in data.get("classes", {}).items():
            for item in class_data.get("equipment", []):
                sprite_id = item.get("sprite_id")
                self.assertTrue(sprite_id, f"Item {item.get('name')} in class {class_id} missing sprite_id")
                svg_path = ITEMS_SPRITE_DIR / f"{sprite_id}.svg"
                self.assertTrue(svg_path.is_file(), f"SVG sprite file not found on disk: {svg_path}")

    def test_all_origin_table_sprites_exist_on_disk(self):
        data = json.loads((CONTENT / "character_creation.json").read_text(encoding="utf-8"))
        for item in data.get("origin_table", []):
            sprite_id = item.get("sprite_id")
            if sprite_id:
                svg_path = ITEMS_SPRITE_DIR / f"{sprite_id}.svg"
                self.assertTrue(svg_path.is_file(), f"Origin SVG sprite file not found on disk: {svg_path}")

    def test_all_background_gear_sprites_exist_on_disk(self):
        data = json.loads((CONTENT / "character_creation.json").read_text(encoding="utf-8"))
        for bg_id, bg_data in data.get("backgrounds", {}).items():
            for item in bg_data.get("gear", []):
                sprite_id = item.get("sprite_id")
                if sprite_id:
                    svg_path = ITEMS_SPRITE_DIR / f"{sprite_id}.svg"
                    self.assertTrue(svg_path.is_file(), f"Background gear SVG not found: {svg_path}")

    def test_core_items_json_sprites_exist_on_disk(self):
        data = json.loads((CONTENT / "items.json").read_text(encoding="utf-8"))
        for item in data.get("items", []):
            sprite_id = item.get("sprite_id")
            if sprite_id:
                svg_path = ITEMS_SPRITE_DIR / f"{sprite_id}.svg"
                self.assertTrue(svg_path.is_file(), f"items.json sprite file not found on disk: {svg_path}")


class NodeUiResolverTests(unittest.TestCase):
    def test_headless_ui_components_resolver(self):
        script = r"""
const fs = await import('node:fs');
const path = await import('node:path');

// Load script directly in node environment
const uiCode = fs.readFileSync('web/ui-components.js', 'utf-8');
const runInContext = new Function(uiCode);
runInContext();

const HSRUI = globalThis.HSRUI;
if (!HSRUI || typeof HSRUI.card !== 'function') {
  throw new Error('HSRUI.card not exported on globalThis');
}

const testItems = [
  { name: 'mace', slot: 'hand', tier: 'mundane' },
  { name: 'scale mail', slot: 'armor', tier: 'mundane' },
  { name: 'shield', slot: 'hand', tier: 'mundane' },
  { name: 'holy focus', slot: 'neck', tier: 'mundane' },
  { name: 'signet ring', slot: 'ring', tier: 'mundane' },
  { name: 'cloak', slot: 'cloak', tier: 'mundane' },
  { name: 'dining fork', slot: 'utility', category: 'tableware' },
  { name: 'pewter plate', slot: 'utility', category: 'tableware' },
  { name: 'carved spoon', slot: 'utility', category: 'tableware' },
  { name: 'table knife', slot: 'utility', category: 'tableware' },
  { name: 'ale tankard', slot: 'utility', category: 'tableware' },
  { name: 'torch', slot: 'utility', category: 'adventuring_gear' },
  { name: 'trail rations', slot: 'utility', category: 'consumable' },
  { name: 'canvas backpack', slot: 'utility', category: 'container' },
  { name: 'wool bedroll', slot: 'utility', category: 'adventuring_gear' },
  { name: 'completely unknown artifact', slot: 'hand' },
  { name: 'unknown oddity', slot: 'utility' }
];

for (const item of testItems) {
  const cardHtml = HSRUI.card(item, 'gear', 0, 'assets/');
  if (cardHtml.includes('Art pending') || cardHtml.includes('art-fallback')) {
    throw new Error(`Item ${item.name} rendered with Art pending placeholder!`);
  }
  if (!cardHtml.includes('<img class="item-art" src="assets/sprites/items/')) {
    throw new Error(`Item ${item.name} failed to render valid SVG item-art img tag! HTML: ${cardHtml}`);
  }
}

console.log(JSON.stringify({ success: true, count: testItems.length }));
"""
        res = subprocess.run(["node", "--input-type=module", "-e", script],
                             cwd=str(ROOT), capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Node resolver probe failed: {res.stderr}\n{res.stdout}")
        payload = json.loads(res.stdout.strip().splitlines()[-1])
        self.assertTrue(payload.get("success"))
        self.assertGreaterEqual(payload.get("count", 0), 15)


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(ItemArtAssetDiskTests))
    suite.addTests(loader.loadTestsFromTestCase(NodeUiResolverTests))
    return suite
