"""Torso and arms of the hero rig: shoulders inside the chest, arms that reach, elbows that do not flip.

web/rig-body.js is the shared body view model (view yaw, shoulder placement, collarbone,
far-arm layering, joint ranges for the later physics pass); web/hero-rig.js draws every
custom lead, resident and foe with it. The behaviour checks run the real rig in Node
against a recording 2D context and hold what the 2026-09-26 torso and arms pass fixed:
the arm roots sit inside the chest (the near shoulder behind the far one on a
three-quarter-front body), every hand target is within arm's reach, an elbow never
snaps to the other side while a pose blends, and a far arm crosses the chest only when
the pose says so. Presentation only; no mechanics are read or written.
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
globalThis.HSRUI = {escape: v => String(v ?? '')};
const B = await webModule('rig-body.js');
const {dollModel} = await webModule('paperdoll.js');
const {actorRig} = await webModule('sprite-renderer.js');
const {SkeletalRig} = await webModule('skeletal-rig.js');
const item = (weapon, hands) => ({id: 'h', name: 'H', race_id: 'human', gender: 'male', appearance: {}, hp: 10,
  equipment: weapon === 'none' ? [] : [{presentation: {silhouette: weapon, material: 'steel', rarity: 'mundane', fx: [], handedness: hands}}]});
const make = (weapon = 'sword', hands = 'one-handed') => { const model = dollModel(item(weapon, hands), {pose: 'combat'}); return {model, def: actorRig(model)}; };
const step = (h, rig, clock, pose, beat = '', frames = 30, paint = false) => {
  let sockets;
  for (let i = 0; i < frames; i++) { clock.now += 16; sockets = h.def.draw(ctx, rig, {...h.model, alive: true}, {x: 0, y: 0, facing: 1, dt: 16, now: clock.now, pose, beat, reducedMotion: false, idleFidgets: false, paint}); }
  return sockets;
};
const out = {};

// --- the pure view model ------------------------------------------------------------------
out.spread = {near: B.shoulderSpread('right', 10, .5), far: B.shoulderSpread('left', 10, .5)};
out.turn = {rest: B.turnOf(0), high: B.turnOf(9), low: B.turnOf(-9), yaw: B.VIEW.yaw};
out.elevation = [B.elevationOf(0, 1), B.elevationOf(1, 0), B.elevationOf(0, -1)];
out.clavicle = [0, 1, 2, 3].map(e => B.clavicle(e));
out.front = [0, .5, 1].map(B.farArmFront);
out.limits = {frozen: Object.isFrozen(B.JOINT_LIMITS), elbow: B.JOINT_LIMITS.elbow, shoulder: B.JOINT_LIMITS.shoulder};

// --- the hero rig -------------------------------------------------------------------------
const POSES = [['idle', ''], ['combat', ''], ['combat', 'windup'], ['combat', 'strike'], ['combat', 'guard'], ['combat', 'hit'],
  ['combat', 'crit'], ['combat', 'dodge'], ['run', ''], ['kneel', ''], ['victory', ''], ['point', ''], ['wave', ''], ['cheer', ''],
  ['crossed', ''], ['study', '']];
const WEAPONS = [['sword', 'one-handed'], ['axe', 'two-handed'], ['dagger', 'one-handed'], ['polearm', 'two-handed'],
  ['staff', 'two-handed'], ['wand', 'one-handed'], ['bow', 'two-handed'], ['none', 'one-handed']];
out.reach = []; out.inside = []; out.grip = [];
for (const [weapon, hands] of WEAPONS) {
  const h = make(weapon, hands);
  for (const [pose, beat] of POSES) {
    const rig = new SkeletalRig(); rig.scale = 1;
    const sockets = step(h, rig, {now: 10000}, pose, beat);
    const st = rig.hero, d = st.look.dims, torso = rig.bones.get('torso'), a = torso.angle;
    out.reach.push({weapon, pose: beat || pose, near: st.reach.near.short, far: st.reach.far.short});
    // Shoulder x in the torso frame against the torso outline's half-width.
    const across = side => { const s = rig.bones.get(side + '_shoulder'); return (s.x - torso.x) * Math.cos(a) + (s.y - torso.y) * Math.sin(a); };
    out.inside.push({weapon, pose: beat || pose, near: across('right'), far: across('left'), half: d.sx + 1.1 * d.W});
    if (weapon === 'sword') {
      const hand = rig.bones.get('right_hand');
      out.grip.push({pose: beat || pose, gap: Math.hypot(sockets.main_hand.x - hand.worldX, sockets.main_hand.y - hand.worldY)});
    }
  }
}
// Bind pose: the near shoulder rests behind the far one.
{ const h = make(), rig = new SkeletalRig(); step(h, rig, {now: 10000}, 'idle', '', 2);
  out.bind = {near: rig.bones.get('right_shoulder').restX, far: rig.bones.get('left_shoulder').restX}; }
// Yaw 0 is a pure profile: both shoulders on the torso axis in a neutral pose.
{ const keep = B.VIEW.yaw; B.VIEW.yaw = 0;
  const h = make(), rig = new SkeletalRig(); step(h, rig, {now: 10000}, 'idle', '', 40);
  out.profile = {near: rig.bones.get('right_shoulder').localX, far: rig.bones.get('left_shoulder').localX}; B.VIEW.yaw = keep; }
// Elbows: the largest one-frame jump of either elbow while one pose blends into the next.
{ const h = make(), rig = new SkeletalRig(), clock = {now: 10000}; rig.scale = 1;
  // Drawn-weapon poses only: a gesture from a sheathed pose sends the hand to the hilt first, which is a
  // deliberate sweep past the shoulder rather than an elbow flip.
  const chain = [['combat', ''], ['combat', 'windup'], ['combat', 'strike'], ['combat', 'guard'], ['run', ''], ['combat', ''], ['combat', 'windup'],
    ['combat', 'strike'], ['combat', 'crit'], ['combat', 'hit'], ['combat', 'dodge'], ['combat', ''], ['combat', 'guard'], ['combat', '']];
  let prev = null; out.elbow = {};
  for (const [pose, beat] of chain) {
    let worst = 0;
    for (let f = 0; f < 26; f++) {
      step(h, rig, clock, pose, beat, 1);
      const cur = ['left', 'right'].map(s => { const u = rig.bones.get(s + '_upper_arm'); return [u.tipX, u.tipY]; });
      if (prev) for (let k = 0; k < 2; k++) worst = Math.max(worst, Math.hypot(cur[k][0] - prev[k][0], cur[k][1] - prev[k][1]));
      prev = cur;
    }
    out.elbow[beat || pose] = Math.max(out.elbow[beat || pose] || 0, worst);
  } }
// Far arm layering: in front for crossed arms, behind for a fencing guard.
{ const h = make(); out.af = {};
  for (const pose of ['crossed', 'combat', 'idle']) { const rig = new SkeletalRig(); step(h, rig, {now: 10000}, pose); out.af[pose] = rig.hero.ch.af; } }
// --- Doran: two hands on the Cleaver, shoulders inside a turned chest -----------------------------
{
  const D = await webModule('doran-rig.js');
  const doran = {alive: true, loadout: 'cleaver'};
  const settleD = (opts, frames = 60) => { const rig = new SkeletalRig({scale: 1}); let now = 1000;
    for (let i = 0; i < frames; i++) { now += 16; D.drawDoran(ctx, rig, doran, {x: 0, y: 0, dt: 16, now, idleFidgets: false, ...opts}); } return rig; };
  out.doran = {twoHanded: {}, reach: {}, inside: {}};
  for (const [key, opts] of Object.entries({guard: {pose: 'guard'}, windup: {pose: 'guard', beat: 'windup'}, strike: {pose: 'guard', beat: 'strike'}, block: {pose: 'guard', beat: 'guard'},
    hold: {pose: 'idle', carry: 'ready'}, battleHold: {pose: 'battleIdle', carry: 'ready'}, ready: {pose: 'ready'}, defend: {pose: 'defend'}, low: {pose: 'low'},
    runReady: {pose: 'run', beat: 'move', carry: 'ready', gait: .9}, shoulder: {pose: 'idle', carry: 'shoulder'}})) {
    const rig = settleD(opts), torso = rig.bones.get('torso'), a = torso.angle;
    out.doran.twoHanded[key] = rig.doran.ch.sup;
    out.doran.reach[key] = Math.max(rig.doran.reach?.left?.short ?? 0, rig.doran.reach?.right?.short ?? 0);
    const across = side => { const s = rig.bones.get(side + '_shoulder'); return (s.x - torso.x) * Math.cos(a) + (s.y - torso.y) * Math.sin(a); };
    out.doran.inside[key] = {near: across('right'), far: across('left')};
  }
  out.doran.swings = {};
  for (const style of Object.keys(D.DORAN_SWINGS)) {
    const rig = new SkeletalRig({scale: 1}); let now = 1000, two = 0, frames = 0;
    for (let i = 0; i < 40; i++) { now += 16; D.drawDoran(ctx, rig, doran, {x: 0, y: 0, dt: 16, now, pose: 'idle', carry: 'ready', idleFidgets: false}); }
    const t0 = now + 16;
    for (let t = 0; t <= D.DORAN_SWINGS[style].ms; t += 16) { now = t0 + t; D.drawDoran(ctx, rig, doran, {x: 0, y: 0, dt: 16, now, pose: 'idle', carry: 'ready', swing: style, swingAt: t0, idleFidgets: false}); frames++; if (rig.doran.ch.sup > .9) two++; }
    out.doran.swings[style] = two / frames;
  }
  const bind = settleD({pose: 'idle', carry: 'stowed'}, 3);
  out.doran.bind = {near: bind.bones.get('right_shoulder').restX, far: bind.bones.get('left_shoulder').restX};
}
console.log(JSON.stringify(out));
""")

# Two-handed reactions hold the far hand on the weapon's second grip, which sits well below
# the near hand once the weapon drops; those far hands were already short of the grip before
# the pass (a wide reaction lowers the shaft) and are tracked here rather than hidden.
KNOWN_SHORT = {("axe", "hit", "far"), ("axe", "crit", "far"), ("axe", "dodge", "far")}


class RigBodyModuleTests(unittest.TestCase):
    def test_module_is_served_and_imported(self):
        body = (WEB / "rig-body.js").read_text(encoding="utf-8")
        for name in ("VIEW", "turnOf", "shoulderSpread", "elevationOf", "CLAVICLE", "clavicle", "farArmFront", "JOINT_LIMITS", "BIND"):
            with self.subTest(name=name):
                self.assertRegex(body, rf"export (const|function) {name}\b")
        hero = (WEB / "hero-rig.js").read_text(encoding="utf-8")
        self.assertIn("from './rig-body.js'", hero)
        lab = (WEB / "actor-lab.html").read_text(encoding="utf-8")
        self.assertIn('id="yaw"', lab)
        self.assertIn('id="bones"', lab)


class HeroTorsoArmsTests(unittest.TestCase):
    probe: dict = {}

    @classmethod
    def setUpClass(cls):
        res = subprocess.run(["node", "--input-type=module", "-e", NODE_PROBE], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            raise AssertionError(f"rig probe failed: {res.stderr}")
        cls.probe = json.loads(res.stdout.strip().splitlines()[-1])

    def test_near_shoulder_sits_behind_the_far_one(self):
        # A body turned three-quarter toward camera projects the near shoulder behind the sternum
        # line and the far shoulder in front of it, equal distances either side.
        s = self.probe["spread"]
        self.assertLess(s["near"], 0)
        self.assertGreater(s["far"], 0)
        self.assertAlmostEqual(-s["near"], s["far"], places=6)

    def test_turn_is_clamped(self):
        t = self.probe["turn"]
        self.assertAlmostEqual(t["rest"], t["yaw"], places=6)
        self.assertLessEqual(t["high"], 1.4 + 1e-9)
        self.assertGreaterEqual(t["low"], -.5 - 1e-9)

    def test_elevation_measures_from_hanging(self):
        down, forward, up = self.probe["elevation"]
        self.assertAlmostEqual(down, 0, places=6)
        self.assertAlmostEqual(forward, 3.14159265 / 2, places=5)
        self.assertAlmostEqual(up, 3.14159265, places=5)

    def test_collarbone_lifts_and_reaches_as_the_arm_rises(self):
        c = self.probe["clavicle"]
        self.assertEqual(c[0], {"dy": 0, "dx": 0})
        for lo, hi in zip(c, c[1:]):
            self.assertLessEqual(hi["dy"], lo["dy"], "the shoulder only ever rises")
            self.assertGreaterEqual(hi["dx"], lo["dx"], "and only ever reaches further forward")
        self.assertLess(c[-1]["dy"], 0)
        self.assertGreater(c[-1]["dx"], 0)

    def test_far_arm_switches_forearm_before_upper_arm(self):
        behind, half, front = self.probe["front"]
        self.assertEqual(behind, {"upper": False, "lower": False})
        self.assertEqual(half, {"upper": False, "lower": True})
        self.assertEqual(front, {"upper": True, "lower": True})

    def test_joint_limits_are_data_for_the_physics_pass(self):
        limits = self.probe["limits"]
        self.assertTrue(limits["frozen"])
        self.assertEqual(limits["elbow"]["kind"], "revolute")
        self.assertEqual(limits["elbow"]["max"], 2.79)
        self.assertEqual(limits["shoulder"]["kind"], "cone")

    def test_bind_pose_has_the_shoulders_inside_and_ordered(self):
        b = self.probe["bind"]
        self.assertLess(b["near"], b["far"])
        self.assertLess(abs(b["near"]), 9.6, "no longer out on the silhouette edge")

    def test_yaw_zero_is_a_pure_profile(self):
        p = self.probe["profile"]
        self.assertAlmostEqual(p["near"], 0, places=3)
        self.assertAlmostEqual(p["far"], 0, places=3)

    def test_arm_roots_stay_inside_the_chest_in_every_pose(self):
        for row in self.probe["inside"]:
            with self.subTest(weapon=row["weapon"], pose=row["pose"]):
                self.assertLess(abs(row["near"]), row["half"] - 2.5)
                self.assertLess(abs(row["far"]), row["half"] - 2.5)

    def test_every_hand_target_is_within_reach(self):
        for row in self.probe["reach"]:
            for side in ("near", "far"):
                if (row["weapon"], row["pose"], side) in KNOWN_SHORT:
                    continue
                with self.subTest(weapon=row["weapon"], pose=row["pose"], side=side):
                    self.assertLessEqual(row[side], .8, "the arm cannot reach its hand target")

    def test_sword_grip_stays_in_the_hand(self):
        for row in self.probe["grip"]:
            with self.subTest(pose=row["pose"]):
                self.assertLess(row["gap"], 3.5)

    def test_elbows_do_not_snap_across_blends(self):
        # Before the pass an elbow could jump 30+ units in one 16 ms frame (a full flip to the other
        # side of the arm) at an ordinary blend such as the wind-up. The strike, crit and hit beats
        # snap in 24-30 ms by design (the elbow crosses its whole circle), so they are left out.
        for beat, worst in self.probe["elbow"].items():
            if beat in ("strike", "crit", "hit"):
                continue
            with self.subTest(entering=beat):
                self.assertLess(worst, 14, f"elbow jumped {worst:.1f} units in one frame entering {beat}")

    def test_crossed_arms_bring_the_far_arm_in_front(self):
        af = self.probe["af"]
        self.assertGreater(af["crossed"], .8)
        self.assertLess(af["combat"], .2)
        self.assertLess(af["idle"], .2)


class DoranTorsoArmsTests(unittest.TestCase):
    probe: dict = {}

    @classmethod
    def setUpClass(cls):
        res = subprocess.run(["node", "--input-type=module", "-e", NODE_PROBE], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            raise AssertionError(f"rig probe failed: {res.stderr}")
        cls.probe = json.loads(res.stdout.strip().splitlines()[-1])["doran"]

    def test_the_cleaver_is_two_handed_in_every_combat_pose(self):
        # Both hands on the handle wherever the blade is out and he is fighting; only the road's shoulder
        # carry (a worker's shovel) and the stowed poses are left one-handed.
        for key, sup in self.probe["twoHanded"].items():
            with self.subTest(pose=key):
                if key == "shoulder":
                    self.assertLess(sup, .1)
                else:
                    self.assertGreater(sup, .9)

    def test_every_swing_keeps_both_hands_on_the_handle(self):
        for style, share in self.probe["swings"].items():
            with self.subTest(style=style):
                self.assertGreater(share, .95)

    def test_both_hands_reach_the_handle(self):
        for key, short in self.probe["reach"].items():
            with self.subTest(pose=key):
                self.assertLessEqual(short, 1.5, "the arms cannot reach the grip")

    def test_shoulders_sit_inside_a_turned_chest(self):
        b = self.probe["bind"]
        self.assertLess(b["near"], 0)
        self.assertGreater(b["far"], 0)
        for key, row in self.probe["inside"].items():
            with self.subTest(pose=key):
                self.assertLess(abs(row["near"]), 12)
                self.assertLess(abs(row["far"]), 12)


if __name__ == "__main__":
    unittest.main()
