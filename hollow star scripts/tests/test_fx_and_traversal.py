from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


class FXAndTraversalTests(unittest.TestCase):
    def test_fx_engine_module_structure(self):
        fx_path = WEB / "fx-engine.js"
        self.assertTrue(fx_path.is_file(), "fx-engine.js must exist")
        content = fx_path.read_text(encoding="utf-8")
        self.assertIn("export const DAMAGE_PALETTES", content)
        self.assertIn("export function getPalette", content)
        self.assertIn("export class FXEngine", content)
        self.assertIn("export function createFXOverlay", content)
        self.assertIn("spawnProjectile", content)
        self.assertIn("spawnImpact", content)
        self.assertIn("setAura", content)

    def test_skeletal_rig_module_structure(self):
        rig_path = WEB / "skeletal-rig.js"
        self.assertTrue(rig_path.is_file(), "skeletal-rig.js must exist")
        content = rig_path.read_text(encoding="utf-8")
        self.assertIn("export class Bone", content)
        self.assertIn("export class SkeletalRig", content)
        self.assertIn("buildSkeleton", content)
        self.assertIn("applyPose", content)
        self.assertIn("getSocket", content)
        self.assertIn("drawSegmented", content)
        self.assertIn("drawMonolithic", content)

        # Sockets checked
        for socket in ("main_hand", "off_hand", "chest", "head", "ground"):
            self.assertIn(socket, content)

        # Kinematic poses checked
        for pose in ("idle", "run", "jump", "climb", "vault"):
            self.assertIn(f"'{pose}'", content)

    def test_traversal_controller_module_structure(self):
        trav_path = WEB / "traversal-controller.js"
        self.assertTrue(trav_path.is_file(), "traversal-controller.js must exist")
        content = trav_path.read_text(encoding="utf-8")
        self.assertIn("export class TraversalController", content)
        self.assertIn("findRelevantObstacle", content)
        self.assertIn("update", content)
        self.assertIn("'climb'", content)
        self.assertIn("'vault'", content)
        self.assertIn("'jump'", content)

    def test_arcade_canvas_integration(self):
        canvas_path = WEB / "arcade-canvas.js"
        self.assertTrue(canvas_path.is_file(), "arcade-canvas.js must exist")
        content = canvas_path.read_text(encoding="utf-8")
        self.assertIn("from './fx-engine.js'", content)
        self.assertIn("from './skeletal-rig.js'", content)
        self.assertIn("from './traversal-controller.js'", content)
        self.assertIn("new FXEngine()", content)
        self.assertIn("new TraversalController()", content)
        self.assertIn("traversal.update(", content)
        self.assertIn("drawChampion(context,rig,image", content)
        self.assertIn("drawPuppet(context, rig, model", content)

    def test_combat_director_integration(self):
        director_path = WEB / "combat-director.js"
        self.assertTrue(director_path.is_file(), "combat-director.js must exist")
        content = director_path.read_text(encoding="utf-8")
        self.assertIn("from './fx-engine.js'", content)
        self.assertIn("createFXOverlay", content)
        self.assertIn("spawnProjectile", content)
        self.assertIn("spawnImpact", content)
        self.assertIn("setAura", content)

    def test_cross_module_accessibility(self):
        # sprite-renderer.js re-exports
        sr_content = (WEB / "sprite-renderer.js").read_text(encoding="utf-8")
        self.assertIn("export {SkeletalRig, Bone} from './skeletal-rig.js'", sr_content)
        self.assertIn("export {TraversalController} from './traversal-controller.js'", sr_content)
        self.assertIn("export {FXEngine, createFXOverlay, getPalette, DAMAGE_PALETTES} from './fx-engine.js'", sr_content)

        # paperdoll.js re-exports. Sockets come from the live rig (CORE_SOCKETS
        # in skeletal-rig.js), never from static offsets on the doll model.
        pd_content = (WEB / "paperdoll.js").read_text(encoding="utf-8")
        self.assertNotIn("DOLL_SOCKET_OFFSETS", pd_content)
        self.assertIn("export const CORE_SOCKETS", (WEB / "skeletal-rig.js").read_text(encoding="utf-8"))
        self.assertIn("export {SkeletalRig, Bone} from './skeletal-rig.js'", pd_content)
        self.assertIn("export {TraversalController} from './traversal-controller.js'", pd_content)
        self.assertIn("export {FXEngine, createFXOverlay, getPalette, DAMAGE_PALETTES} from './fx-engine.js'", pd_content)

    def test_sprite_guide_documentation(self):
        guide = (WEB / "SPRITE_GUIDE.md").read_text(encoding="utf-8")
        self.assertIn("Unified Canvas FX Engine (`web/fx-engine.js`)", guide)
        self.assertIn("2D Skeletal Rig & Socket System (`web/skeletal-rig.js`)", guide)
        self.assertIn("Kinematic Traversal Subsystem (`web/traversal-controller.js`)", guide)
        self.assertIn("Cross-Module Integration", guide)

    def test_javascript_syntax_via_node(self):
        node_script = (
            "const fs = require('fs'); const vm = require('vm'); "
            "['web/fx-engine.js', 'web/skeletal-rig.js', 'web/traversal-controller.js', "
            "'web/arcade-canvas.js', 'web/combat-director.js', 'web/sprite-renderer.js', 'web/paperdoll.js'].forEach(f => { "
            "  const code = fs.readFileSync(f, 'utf8'); "
            "  new vm.SourceTextModule(code); "
            "});"
        )
        res = subprocess.run(
            ["node", "--experimental-vm-modules", "-e", node_script],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Node syntax check failed: {res.stderr}")

    def test_web_server_serves_fx_and_traversal_modules(self):
        import hollowstar_web_server as web
        for asset in (
            "/web/fx-engine.js", "/fx-engine.js",
            "/web/skeletal-rig.js", "/skeletal-rig.js",
            "/web/traversal-controller.js", "/traversal-controller.js",
            "/web/visual-armory.json", "/visual-armory.json",
        ):
            self.assertIn(asset, web.Handler.assets, f"{asset} must be in Handler.assets")
            target = web.ROOT / web.Handler.assets[asset]
            self.assertTrue(target.is_file(), f"Target file for {asset} must exist at {target}")


if __name__ == "__main__":
    unittest.main()
