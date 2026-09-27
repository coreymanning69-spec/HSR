"""Doran's layered paperdoll: wiring into every renderer, and rig behaviour.

The behaviour checks run web/doran-rig.js in Node against a mock 2D context:
the rig must keep his sabatons on the floor, his hand on the Cleaver's grip,
his 7'0" frame and the design-locked Cleaver (6 ft x 1 ft blade, 3 ft handle),
and it must play a strike as snap, hitstop, follow-through. Presentation only;
no mechanics are read or written.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

# tests/web-probe-prelude.js supplies webModule() and a recording 2D ctx.
NODE_PROBE = (Path(__file__).with_name("web-probe-prelude.js").read_text(encoding="utf-8") + r"""
const D = await webModule('doran-rig.js');
const PAPER = await webModule('paperdoll.js');
const {SkeletalRig} = await webModule('skeletal-rig.js');
const run = (pose, {frames = 40, loadout = 'cleaver', beat = '', casting = null, start = 1000, dt = 16, rig = new SkeletalRig()} = {}) => {
  let now = start, sockets;
  for (let i = 0; i < frames; i++) { now += dt; sockets = D.drawDoran(ctx, rig, {alive: pose !== 'down'}, {x: 0, y: 0, pose, beat, loadout, casting, now, dt, idleFidgets: false}); }
  return {rig, sockets, now};
};
const out = {ft: D.RIG_UNITS_PER_FOOT, height: D.DORAN_HEIGHT_UNITS, cleaver: D.CLEAVER, layers: D.DORAN_PAPERDOLL_LAYERS,
  poses: Object.keys(D.DORAN_POSES), loadouts: [D.doranLoadout({}), D.doranLoadout({loadout: 'daggers'}), D.doranLoadout({weapon_mode: 'dagger'})],
  feet: {}, grip: {}, strike: []};
for (const pose of ['rest', 'guard', 'brace', 'low', 'windup', 'land']) {
  const {rig} = run(pose);
  const ankle = n => rig.bones.get(n).worldY;
  out.feet[pose] = [ankle('left_foot'), ankle('right_foot')];
}
for (const pose of ['rest', 'guard', 'hit']) {
  const {sockets} = run(pose);
  const p = D.DORAN_POSES[pose];
  out.grip[pose] = Math.hypot(sockets.main_hand.x - p.hx, sockets.main_hand.y - p.hy);
}
// Strike beat: sample the rig's pose key and the weapon hand over time.
const rig = new SkeletalRig();
let now = 5000;
run('guard', {rig, start: now - 1000, frames: 60});
for (const t of [0, 16, 48, 96, 112, 128, 144, 160, 176, 240, 400]) {
  const sockets = D.drawDoran(ctx, rig, {alive: true}, {x: 0, y: 0, pose: 'guard', beat: 'strike', now: now + t, dt: 16, idleFidgets: false});
  out.strike.push([t, rig.pose, Math.round(sockets.main_hand.x * 100) / 100, Math.round(sockets.main_hand.y * 100) / 100]);
}
out.contact = rig.doran.contactAt === rig.doran.beatAt;
const dag = run('guard', {loadout: 'daggers'});
out.daggerHand = [dag.sockets.main_hand.x, dag.sockets.main_hand.y];
out.daggerWeapon = dag.rig.weapon;
out.sockets = Object.keys(run('guard').sockets);
out.beats = Object.fromEntries(['cast_channel', 'cast_release', 'dodge', 'crit', 'gesture:point', 'gesture:cheer']
  .map(beat => [beat, run('guard', {beat, frames: 4}).rig.pose]));
const reduced = new SkeletalRig();
D.drawDoran(ctx, reduced, {alive: true}, {pose: 'guard', now: 1, dt: 16, reducedMotion: true});
out.reducedSnaps = Math.abs(reduced.doran.ch.nu - D.DORAN_POSES.guard.nu) < 1e-9;
const low = run('staffLow', {loadout: 'staff'}), pointed = run('staffPoint', {loadout: 'staff'});
const wand = run('staffPoint', {loadout: 'wand'});
const oneHand = run('guard', {loadout: 'staff', beat: 'cast_channel', casting: {stance: 'aim', hands: 1, source: 'hands'}});
const twoHands = run('guard', {loadout: 'staff', beat: 'cast_channel', casting: {stance: 'overhead', hands: 2, source: 'hands'}});
const implement = run('guard', {loadout: 'staff', beat: 'cast_release', casting: {stance: 'aim', hands: 2, source: 'implement'}});
const point = r => ({hand: r.sockets.main_hand, tip: r.sockets.weapon_tip, focus: r.sockets.focus,
  leftFist: [r.rig.bones.get('left_hand').worldX, r.rig.bones.get('left_hand').worldY],
  rightFist: [r.rig.bones.get('right_hand').worldX, r.rig.bones.get('right_hand').worldY],
  leftElbow: r.rig.bones.get('left_upper_arm').tipX, leftShoulder: r.rig.bones.get('left_shoulder').worldX});
out.newStances = {low: point(low), pointed: point(pointed), wand: point(wand), oneHand: point(oneHand), twoHands: point(twoHands), implement: point(implement)};
out.newLoadouts = [D.doranLoadout({loadout: 'staff'}), D.doranLoadout({weapon_mode: 'wand'}),
  D.doranLoadout({}, 'staff'), D.doranLoadout({}, 'wand')];
out.publicModels = ['staff', 'wand'].map(silhouette => {
  const model = PAPER.dollModel({identity: 'doran', name: 'Doran', equipment: [{presentation: {silhouette}}]}, {pose: 'staffPoint'});
  return [model.loadout, model.weapon, model.pose];
});
const command = run('guard', {beat: 'cast_channel'});
out.commandArm = [command.rig.bones.get('left_upper_arm').tipX, command.rig.bones.get('left_shoulder').worldX];
console.log(JSON.stringify(out));
""")


class DoranPaperdollWiringTests(unittest.TestCase):
    def test_rig_module_exports_the_spec_layers(self):
        content = (WEB / "doran-rig.js").read_text(encoding="utf-8")
        for name in ("DORAN_PAPERDOLL_LAYERS", "DORAN_POSES", "DORAN_RIG", "drawDoran", "doranLoadout", "doranPortrait", "CLEAVER"):
            with self.subTest(name=name):
                self.assertRegex(content, rf"export (const|function) {name}\b")

    def test_doran_routes_through_the_rig_not_frame_art(self):
        sprite = (WEB / "sprite-renderer.js").read_text(encoding="utf-8")
        self.assertRegex(sprite, r"const CHAMPION_RIGS = Object\.freeze\(\{doran: DORAN_RIG[,}]")
        self.assertIn("const CHAMPION_POSE_ART = Object.freeze({});", sprite)
        self.assertIn("export function championRig", sprite)
        paperdoll = (WEB / "paperdoll.js").read_text(encoding="utf-8")
        self.assertIn("base = {type: 'rig'", paperdoll)
        self.assertIn("doll-rig champion-rig", paperdoll)
        self.assertIn("data-beat-tempo", paperdoll)
        self.assertIn("export {DORAN_PAPERDOLL_LAYERS", paperdoll)
        # Every figure resolves its rig through the registry: a champion's own
        # (championRig inside actorRig), everyone else the hero rig.
        self.assertRegex(sprite, r"export function actorRig\(model = \{\}\) \{[^}]*return championRig\(model\.identity\) \|\| HERO_RIG;")
        dom = (WEB / "puppet-dom.js").read_text(encoding="utf-8")
        self.assertIn("rec.def=actorRig(model)", dom)
        self.assertIn("rigged.draw(ctx,rig,model", dom)
        arcade = (WEB / "arcade-canvas.js").read_text(encoding="utf-8")
        self.assertIn("const rigged = actorRig(model);", arcade)
        self.assertIn("rigged.draw(context, rig, model", arcade)
        director = (WEB / "combat-director.js").read_text(encoding="utf-8")
        self.assertIn("const TEMPO = {heavy:", director)
        voice = (WEB / "voice-feed.js").read_text(encoding="utf-8")
        self.assertIn("doranPortrait()", voice)
        self.assertNotIn("doran-guard.png", voice)
        css = (WEB / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".scene-character.doll-rig .puppet-canvas", css)

    def test_web_server_serves_the_rig_module(self):
        import hollowstar_web_server as web
        for asset in ("/doran-rig.js", "/web/doran-rig.js"):
            self.assertIn(asset, web.Handler.assets)
            self.assertTrue((web.ROOT / web.Handler.assets[asset]).is_file())


class DoranRigBehaviourTests(unittest.TestCase):
    probe: dict = {}

    @classmethod
    def setUpClass(cls):
        res = subprocess.run(["node", "--input-type=module", "-e", NODE_PROBE], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(f"rig probe failed: {res.stderr}")
        cls.probe = json.loads(res.stdout.strip().splitlines()[-1])

    def test_design_locked_proportions(self):
        p, ft = self.probe, self.probe["ft"]
        self.assertAlmostEqual(p["height"] / ft, 7.0, places=6)          # 7'0" in the helm
        self.assertAlmostEqual(p["cleaver"]["blade"] / ft, 6.0, places=6)  # 6 ft blade
        self.assertAlmostEqual(p["cleaver"]["width"] / ft, 1.0, places=6)  # ~1 ft wide (Corey 2026-09-25: a third of the 3 ft slab)
        self.assertAlmostEqual(p["cleaver"]["handle"] / ft, 3.0, places=6)  # 3 ft handle

    def test_layer_catalog_paint_order(self):
        z = {key: row["z"] for key, row in self.probe["layers"].items()}
        for key in ("ground:shadow", "cape:back", "weapon:stowed", "body:legs", "body:torso", "body:head",
                    "fx:visor-glow", "shield:kite", "arm:right", "hand:right", "arm:left", "weapon:cleaver",
                    "weapon:daggers", "fx:slash-arc"):
            self.assertIn(key, z)
        self.assertLess(z["cape:back"], z["body:torso"])
        self.assertLess(z["arm:left"], z["body:torso"])            # shield arm is the far arm
        self.assertLess(z["shield:kite"], z["body:torso"])         # the kite rides the far forearm
        self.assertLess(z["body:torso"], z["arm:right"])           # weapon arm is the near arm
        self.assertLess(z["arm:right"], z["weapon:cleaver"])       # a forward blade paints over all
        self.assertEqual(self.probe["layers"]["shield:kite"]["bone"], "left_lower_arm")

    def test_sabatons_stay_on_the_floor_in_stances(self):
        # The ankle sits one sole (10 units) above the ground; y is negative up.
        for pose, (left, right) in self.probe["feet"].items():
            with self.subTest(pose=pose):
                self.assertAlmostEqual(max(left, right), -10, delta=1.2)
                self.assertAlmostEqual(min(left, right), -10, delta=2.5)

    def test_weapon_hand_reaches_its_grip(self):
        for pose, miss in self.probe["grip"].items():
            with self.subTest(pose=pose):
                self.assertLess(miss, 4.0)

    def test_strike_is_snap_hitstop_follow(self):
        rows = self.probe["strike"]
        keys = [row[1] for row in rows]
        self.assertEqual(keys[1], "strike")
        self.assertEqual(keys[-1], "follow")
        held = [row for row in rows if 112 <= row[0] <= 160]
        self.assertTrue(held and all(row[2:] == held[0][2:] for row in held), f"hitstop must freeze the hand: {held}")
        self.assertNotEqual(rows[-1][2:], held[0][2:], "follow-through moves on after the hold")
        self.assertTrue(self.probe["contact"], "the hitstop hold marks the contact frame")

    def test_casting_gestures_and_sockets(self):
        self.assertEqual(self.probe["beats"], {"cast_channel": "command", "cast_release": "point", "dodge": "low",
                                               "crit": "hit", "gesture:point": "point", "gesture:cheer": "cheer"})
        for name in ("head", "chest", "main_hand", "off_hand", "ground", "weapon_main", "weapon_tip", "shield", "focus"):
            self.assertIn(name, self.probe["sockets"])
        self.assertEqual(self.probe["daggerWeapon"], "daggers")

    def test_loadouts_and_reduced_motion(self):
        self.assertEqual(self.probe["loadouts"], ["cleaver", "daggers", "daggers"])
        hand = self.probe["daggerHand"]
        self.assertTrue(all(isinstance(v, (int, float)) for v in hand))
        self.assertTrue(self.probe["reducedSnaps"])
        for pose in ("rest", "guard", "windup", "strike", "follow", "sweep", "hit", "brace", "low", "run",
                     "jump", "climb", "down", "kneel", "look", "point"):
            if pose != "run":
                self.assertIn(pose, self.probe["poses"])

    def test_focus_loadouts_and_host_casting_profile(self):
        p = self.probe["newStances"]
        self.assertEqual(self.probe["newLoadouts"], ["staff", "wand", "staff", "wand"])
        self.assertEqual(self.probe["publicModels"], [["staff", "staff", "staffPoint"], ["wand", "wand", "staffPoint"]])
        self.assertLess(*self.probe["commandArm"], "unarmed command raises the shield arm outward")
        self.assertLess(p["low"]["tip"]["y"], p["low"]["hand"]["y"] - 25)
        self.assertGreater(p["pointed"]["tip"]["x"], p["pointed"]["hand"]["x"] + 25)
        self.assertGreater(p["wand"]["tip"]["x"], p["wand"]["hand"]["x"] + 10)
        self.assertLess(p["wand"]["tip"]["x"] - p["wand"]["hand"]["x"],
                        p["pointed"]["tip"]["x"] - p["pointed"]["hand"]["x"])
        # A hand cast uses the actual casting hand, while the held staff stays lowered.
        self.assertLess(p["oneHand"]["leftElbow"], p["oneHand"]["leftShoulder"])
        self.assertNotEqual(p["oneHand"]["focus"], p["oneHand"]["tip"])
        self.assertLess(p["oneHand"]["tip"]["y"], p["oneHand"]["hand"]["y"])
        # Both hands make the spell focus; the staff is carried off the hands.
        self.assertEqual(p["twoHands"]["tip"], p["twoHands"]["hand"])
        self.assertNotEqual(p["twoHands"]["focus"], p["twoHands"]["hand"])
        self.assertNotEqual(p["twoHands"]["focus"], p["twoHands"]["tip"])
        # An implement cast puts the focus at the staff tip, including release.
        self.assertEqual(p["implement"]["focus"], p["implement"]["tip"])


if __name__ == "__main__":
    unittest.main()
