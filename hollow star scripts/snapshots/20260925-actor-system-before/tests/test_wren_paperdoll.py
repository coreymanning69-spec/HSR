"""Wren's layered paperdoll: wiring into every renderer, and rig behaviour.

The behaviour checks run web/wren-rig.js in Node against a mock 2D context and
hold the canon locks from DM041_D / DM041_B2 / DM048_0: a 5'6"-5'7" frame that
normally floats a little off the ground with wings dismissed, white wings only
in real flight, seven crown motes and six robe stars that leave when spent,
and the staff hand on its grip. Presentation only; no mechanics are read or
written.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

NODE_PROBE = r"""
import fs from 'node:fs';
const data = src => 'data:text/javascript;base64,' + Buffer.from(src).toString('base64');
const magicUrl = data(fs.readFileSync('web/magic-articulation.js', 'utf8'));
const rigUrl = data(fs.readFileSync('web/skeletal-rig.js', 'utf8').replace("from './magic-articulation.js'", `from '${magicUrl}'`));
const src = fs.readFileSync('web/wren-rig.js', 'utf8').replace("from './skeletal-rig.js'", `from '${rigUrl}'`);
const W = await import(data(src));
const {SkeletalRig} = await import(rigUrl);
const noop = () => {}, grad = {addColorStop: noop};
let painted = [];
const ctx = new Proxy({}, {get: (t, k) => k in t ? t[k] : /^create(Linear|Radial)Gradient$/.test(k) ? () => grad
  : k === 'fill' ? () => painted.push(t.fillStyle) : noop, set: (t, k, v) => (t[k] = v, true)});
const run = (pose, {frames = 40, model = {alive: pose !== 'down'}, beat = '', start = 1000, dt = 16, rig = new SkeletalRig(), reducedMotion = true} = {}) => {
  let now = start, sockets;
  for (let i = 0; i < frames; i++) { now += dt; painted = []; sockets = W.drawWren(ctx, rig, model, {x: 0, y: 0, pose, beat, now, dt, idleFidgets: false, reducedMotion}); }
  return {rig, sockets, now, fills: painted.slice()};
};
const sole = rig => Math.max(...['left_foot', 'right_foot'].map(n => rig.bones.get(n).y));
const out = {ft: W.RIG_UNITS_PER_FOOT, height: W.WREN_HEIGHT_UNITS, float: W.WREN_FLOAT, staff: W.STAFF,
  layers: W.WREN_PAPERDOLL_LAYERS, poses: Object.keys(W.WREN_POSES), rigHeight: W.WREN_RIG.heightUnits,
  hover: {}, grip: {}, wings: {}, beats: {}};
for (const pose of ['rest', 'guard', 'hit', 'fly']) {
  const {rig, sockets} = run(pose);
  out.hover[pose] = sole(rig);
  out.grip[pose] = Math.hypot(sockets.main_hand.x - (rig.bones.get('pelvis').x + W.WREN_POSES[pose === 'fly' ? 'fly' : pose].hx),
    sockets.main_hand.y - (rig.bones.get('pelvis').y + W.WREN_POSES[pose === 'fly' ? 'fly' : pose].hy));
}
// Stature: crown of the head above the slipper sole at rest.
{ const {rig} = run('rest'); const head = rig.bones.get('head');
  out.stature = (sole(rig) + 6) - (head.y - 13.5); }
// Wings: absent at rest, present in flight and when the host has her flying.
// The wings' shade tone is used by no other part.
const white = fills => fills.filter(f => f === '#dde2ec').length;
out.wings.rest = white(run('rest').fills);
out.wings.fly = white(run('fly').fills);
out.wings.hostFlying = white(run('guard', {model: {alive: true, kit: W.wrenPresentation({fly_speed: 60})}}).fills);
out.flyingKey = run('guard', {model: {alive: true, kit: {motes: 7, stars: 6, wings: true}}}).rig.pose;
// Crown motes and robe stars follow the host's resource counts.
out.kit = [W.wrenPresentation({}), W.wrenPresentation({resources: {crown_motes: 3, robe_stars: 0}}), W.wrenPresentation({fly_speed: 60})];
const moteFills = kit => run('rest', {model: {alive: true, kit}}).fills.filter(f => f === '#ffe7a0').length;
out.motes = [moteFills({motes: 7, stars: 6, wings: false}), moteFills({motes: 2, stars: 6, wings: false})];
// Beats: Crown of Stars gathers then releases; release is the contact frame.
for (const beat of ['windup', 'cast_channel', 'strike', 'cast_release', 'dodge', 'crit', 'gesture:point']) out.beats[beat] = run('guard', {beat, frames: 4}).rig.pose;
{ const rig = new SkeletalRig(); run('guard', {rig, beat: 'cast_release', frames: 3}); out.contact = rig.wren.contactAt === rig.wren.beatAt; }
out.sockets = Object.keys(run('guard').sockets);
// Fallen: she lies on the floor rather than hovering.
{ const {rig} = run('down'); let lowest = -Infinity; for (const b of rig.bones.values()) if (b.name !== 'root') lowest = Math.max(lowest, b.y, b.endY ?? b.y); out.downLowest = lowest; out.downPose = rig.pose; }
console.log(JSON.stringify(out));
"""


class WrenPaperdollWiringTests(unittest.TestCase):
    def test_rig_module_exports(self):
        content = (WEB / "wren-rig.js").read_text(encoding="utf-8")
        for name in ("WREN_PAPERDOLL_LAYERS", "WREN_POSES", "WREN_RIG", "drawWren", "wrenLoadout", "wrenPortrait",
                     "wrenPresentation", "blackBirdSigil", "STAFF"):
            with self.subTest(name=name):
                self.assertRegex(content, rf"export (const|function) {name}\b")

    def test_wren_routes_through_the_rig(self):
        sprite = (WEB / "sprite-renderer.js").read_text(encoding="utf-8")
        self.assertIn("const CHAMPION_RIGS = Object.freeze({doran: DORAN_RIG, wren: WREN_RIG});", sprite)
        self.assertIn("import {WREN_RIG} from './wren-rig.js';", sprite)
        paperdoll = (WEB / "paperdoll.js").read_text(encoding="utf-8")
        self.assertIn("kit: rig.presentation(item)", paperdoll)
        dom = (WEB / "puppet-dom.js").read_text(encoding="utf-8")
        self.assertIn("(rig.doran||rig.wren)?.contactAt", dom)
        voice = (WEB / "voice-feed.js").read_text(encoding="utf-8")
        self.assertIn("wrenPortrait()", voice)

    def test_web_server_serves_the_rig_module(self):
        import hollowstar_web_server as web
        for asset in ("/wren-rig.js", "/web/wren-rig.js"):
            self.assertIn(asset, web.Handler.assets)
            self.assertTrue((web.ROOT / web.Handler.assets[asset]).is_file())

    def test_sigil_keeps_its_white_enclosure(self):
        # DM048_0 FORM LOCK: an unenclosed black bird is not this sigil.
        content = (WEB / "wren-rig.js").read_text(encoding="utf-8")
        body = content.split("export function blackBirdSigil", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("fillStroke(ctx, '#ffffff'", body)


class WrenRigBehaviourTests(unittest.TestCase):
    probe: dict = {}

    @classmethod
    def setUpClass(cls):
        res = subprocess.run(["node", "--input-type=module", "-e", NODE_PROBE], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(f"rig probe failed: {res.stderr}")
        cls.probe = json.loads(res.stdout.strip().splitlines()[-1])

    def test_canon_stature(self):
        p, ft = self.probe, self.probe["ft"]
        self.assertTrue(5.5 <= p["height"] / ft <= 7 / 12 + 5, "DM041_D: 5'6\" to 5'7\"")
        self.assertAlmostEqual(p["stature"] / ft, p["height"] / ft, delta=.12)

    def test_she_floats_by_default(self):
        # The ankle sits one sole (6 units) above the slipper; y is negative up.
        rest = self.probe["hover"]["rest"]
        self.assertAlmostEqual(rest, -(6 + self.probe["float"]), delta=1.5)
        for pose, ankle in self.probe["hover"].items():
            with self.subTest(pose=pose):
                self.assertLess(ankle, -8, "never standing on the floor while conscious")
        self.assertLess(self.probe["hover"]["fly"], rest, "real flight rides higher than the rest hover")

    def test_wings_only_for_real_flight(self):
        w = self.probe["wings"]
        self.assertEqual(w["rest"], 0, "wings are dismissed in the default float")
        self.assertGreater(w["fly"], 0)
        self.assertGreater(w["hostFlying"], 0, "host fly_speed manifests the wings")
        self.assertEqual(self.probe["flyingKey"], "fly")

    def test_crown_and_robe_stars_follow_resources(self):
        full, spent, flying = self.probe["kit"]
        self.assertEqual(full, {"motes": 7, "stars": 6, "wings": False})
        self.assertEqual(spent, {"motes": 3, "stars": 0, "wings": False})
        self.assertTrue(flying["wings"])
        seven, two = self.probe["motes"]
        self.assertGreater(seven, two)
        self.assertEqual(seven % 7, 0)

    def test_staff_hand_reaches_its_target(self):
        for pose, miss in self.probe["grip"].items():
            with self.subTest(pose=pose):
                self.assertLess(miss, 4.0)

    def test_beats_contact_and_sockets(self):
        self.assertEqual(self.probe["beats"], {"windup": "channel", "cast_channel": "channel", "strike": "release",
                                               "cast_release": "release", "dodge": "dodge", "crit": "hit",
                                               "gesture:point": "point"})
        self.assertTrue(self.probe["contact"])
        for name in ("head", "chest", "main_hand", "off_hand", "ground", "weapon_main", "weapon_tip", "shield", "focus", "crown"):
            self.assertIn(name, self.probe["sockets"])

    def test_fallen_lies_on_the_floor(self):
        self.assertEqual(self.probe["downPose"], "down")
        self.assertAlmostEqual(self.probe["downLowest"], -3, delta=1.5)

    def test_layer_catalog_paint_order(self):
        z = {key: row["z"] for key, row in self.probe["layers"].items()}
        self.assertLess(z["wing:far"], z["body:torso"])
        self.assertLess(z["wing:near"], z["body:torso"])
        self.assertLess(z["hair:back"], z["body:torso"])
        self.assertLess(z["fx:crown-back"], z["body:head"])
        self.assertLess(z["body:head"], z["fx:crown-front"])
        self.assertLess(z["weapon:staff"], z["hand:right"])
        self.assertLess(self.probe["rigHeight"] / self.probe["ft"], 6.5)


if __name__ == "__main__":
    unittest.main()
