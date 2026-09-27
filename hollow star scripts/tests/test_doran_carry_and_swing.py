"""Doran's Cleaver: where it rides (back, shoulder, out in front) and how it swings.

The stage sets `carry` (stowed in a friendly place, over the shoulder on the road
in a hostile one, held out in front in a fight) and drives keyframed swings
(chop, cleave, sweep, rise) with a hitstop at contact. This probes the rig
directly: sockets say where the blade is, the rig's own clock says when it lands.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROBE = (Path(__file__).with_name("web-probe-prelude.js").read_text(encoding="utf-8") + r"""
const D = await webModule('doran-rig.js');
const {SkeletalRig} = await webModule('skeletal-rig.js');
const model = {alive: true, loadout: 'cleaver'};
const out = {};
function frames(rig, n, opts, start = 1000, dt = 16) {
  let now = start, sockets = null;
  for (let i = 0; i < n; i++) { now += dt; sockets = D.drawDoran(ctx, rig, model, {x: 0, y: 0, dt, now, idleFidgets: false, ...opts}); }
  return {sockets, now};
}
const shape = (rig, s) => ({stow: rig.doran.ch.stow, hand: s.main_hand, tip: s.weapon_tip, dx: s.weapon_tip.x - s.main_hand.x, dy: s.weapon_tip.y - s.main_hand.y, pose: rig.pose});

// ---- the three carries, still and on the move -----------------------------------------
for (const carry of ['stowed', 'shoulder', 'ready']) {
  let rig = new SkeletalRig({scale: 1.7});
  out[carry] = shape(rig, frames(rig, 80, {pose: 'idle', carry}).sockets);
  rig = new SkeletalRig({scale: 1.7});
  out[carry + 'Walk'] = shape(rig, frames(rig, 80, {pose: 'run', beat: 'move', carry, gait: .9}).sockets);
}
// Legacy callers (no carry) keep the old behaviour: idle stowed, road walk on the shoulder.
{ let rig = new SkeletalRig({scale: 1.7}); out.legacyIdle = shape(rig, frames(rig, 80, {pose: 'idle'}).sockets);
  rig = new SkeletalRig({scale: 1.7}); out.legacyRun = shape(rig, frames(rig, 80, {pose: 'run', beat: 'move'}).sockets); }
// A fight's idle on the battle stage is the same easy hold once carry is 'ready'.
{ const rig = new SkeletalRig({scale: 1.7}); out.battleHold = shape(rig, frames(rig, 80, {pose: 'battleIdle', carry: 'ready'}).sockets);
  const legacy = new SkeletalRig({scale: 1.7}); out.battleLow = shape(legacy, frames(legacy, 80, {pose: 'battleIdle'}).sockets); }

// ---- the stride follows the gait ------------------------------------------------------------
{
  const cycles = gait => {
    const rig = new SkeletalRig({scale: 1.7}); let now = 1000, last = null, crossings = 0;
    for (let i = 0; i < 250; i++) {
      now += 16; D.drawDoran(ctx, rig, model, {x: 0, y: 0, dt: 16, now, pose: 'run', beat: 'move', carry: 'stowed', gait, idleFidgets: false});
      const foot = rig.bones.get('right_foot').x - rig.bones.get('right_hip').x; if (last !== null && last < 0 && foot >= 0) crossings++; last = foot;
    }
    return crossings;
  };
  out.gait = {slow: cycles(.5), fast: cycles(1.4)};
}

// ---- drawing the blade: he reaches over the shoulder first ------------------------------------
{
  const rig = new SkeletalRig({scale: 1.7}); let now = 1000; const poses = new Set(), stows = [];
  for (let i = 0; i < 60; i++) { now += 16; D.drawDoran(ctx, rig, model, {x: 0, y: 0, dt: 16, now, pose: 'idle', carry: 'stowed', idleFidgets: false}); }
  for (let i = 0; i < 70; i++) { now += 16; D.drawDoran(ctx, rig, model, {x: 0, y: 0, dt: 16, now, pose: 'idle', carry: 'ready', idleFidgets: false}); poses.add(rig.pose); stows.push(+rig.doran.ch.stow.toFixed(2)); }
  out.draw = {poses: [...poses], stowStart: stows[0], stowEnd: stows[stows.length - 1], reachedBack: poses.has('reachBack'), flips: stows.findIndex(v => v < .5)};
}

// ---- swings -------------------------------------------------------------------------------------
out.swings = {};
for (const style of Object.keys(D.DORAN_SWINGS)) {
  const T = D.DORAN_SWINGS[style], rig = new SkeletalRig({scale: 1.7}); let now = 1000;
  for (let i = 0; i < 60; i++) { now += 16; D.drawDoran(ctx, rig, model, {x: 0, y: 0, dt: 16, now, pose: 'idle', carry: 'ready', idleFidgets: false}); }
  const at = now + 32; let contactAt = null, minBl = 9, maxBl = -9, trailMax = 0, sparks = 0, heldFrames = 0, prevHx = null, ended = null, lastPose = '', tipMinY = 9e9;
  for (let i = 0; i < Math.ceil((T.ms + D.DORAN_HITSTOP + 500) / 16); i++) {
    now += 16;
    const s = D.drawDoran(ctx, rig, model, {x: 0, y: 0, dt: 16, now, pose: 'idle', carry: 'ready', swing: style, swingAt: at, idleFidgets: false});
    const st = rig.doran; minBl = Math.min(minBl, st.ch.bl); maxBl = Math.max(maxBl, st.ch.bl); trailMax = Math.max(trailMax, st.trail.length); sparks = Math.max(sparks, st.dust.filter(d => d.spark).length);
    tipMinY = Math.min(tipMinY, s.weapon_tip.y);
    if (st.contactAt === at && contactAt === null) contactAt = now - at;
    if (contactAt !== null && prevHx !== null && Math.abs(st.ch.hx - prevHx) < .001 && now - at < contactAt + D.DORAN_HITSTOP + 20) heldFrames++;
    prevHx = st.ch.hx; lastPose = rig.pose;
    if (ended === null && now - at > T.ms + D.DORAN_HITSTOP + 40) ended = {pose: rig.pose, bl: st.ch.bl};
  }
  out.swings[style] = {contactAt, expectContact: T.ms * T.contact, arc: maxBl - minBl, trailMax, sparks, heldFrames, ended, tipMinY, ms: T.ms};
}
// A swing asked for on any other loadout is ignored (the daggers keep their own beats).
{ const rig = new SkeletalRig({scale: 1.7}); let now = 1000;
  for (let i = 0; i < 30; i++) { now += 16; D.drawDoran(ctx, rig, {alive: true, loadout: 'daggers'}, {x: 0, y: 0, dt: 16, now, pose: 'idle', swing: 'chop', swingAt: 1100, idleFidgets: false, loadout: 'daggers'}); }
  out.daggerSwing = rig.pose; }
console.log(JSON.stringify(out));
""")


class DoranCarryAndSwingTests(unittest.TestCase):
    probe: dict = {}

    @classmethod
    def setUpClass(cls):
        res = subprocess.run(["node", "--input-type=module", "-e", PROBE], cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            raise AssertionError(f"carry/swing probe failed: {res.stderr}")
        cls.probe = json.loads(res.stdout.strip().splitlines()[-1])

    def test_stowed_puts_the_blade_on_his_back(self):
        p = self.probe
        self.assertGreater(p["stowed"]["stow"], .9)
        self.assertGreater(p["stowedWalk"]["stow"], .9)           # walking through town he does not draw it

    def test_shoulder_carry_rests_the_blade_up_and_back(self):
        for key in ("shoulder", "shoulderWalk"):
            s = self.probe[key]
            self.assertLess(s["stow"], .1)
            self.assertLess(s["dy"], -60)                         # tip well above the hand
            self.assertLess(s["dx"], 0)                           # and behind it: biangular over the shoulder

    def test_ready_holds_the_blade_out_in_front(self):
        for key in ("ready", "readyWalk", "battleHold"):
            s = self.probe[key]
            self.assertLess(s["stow"], .1)
            self.assertGreater(s["dx"], 60)                       # tip out in front
            self.assertLess(abs(s["dy"]), 90)                     # held about level, not dragging or overhead
        self.assertLess(self.probe["battleLow"]["dx"], self.probe["battleHold"]["dx"] - 30)   # the old low ready pointed down-forward

    def test_old_callers_keep_their_old_behaviour(self):
        self.assertGreater(self.probe["legacyIdle"]["stow"], .9)
        self.assertLess(self.probe["legacyRun"]["stow"], .1)
        self.assertLess(self.probe["legacyRun"]["dy"], -60)

    def test_the_stride_keeps_pace_with_the_gait(self):
        g = self.probe["gait"]
        self.assertGreater(g["fast"], g["slow"] * 1.6)
        self.assertGreaterEqual(g["slow"], 1)

    def test_drawing_reaches_back_first_then_the_blade_comes_off_the_back(self):
        d = self.probe["draw"]
        self.assertTrue(d["reachedBack"])
        self.assertGreater(d["stowStart"], .5)
        self.assertLess(d["stowEnd"], .1)
        self.assertGreater(d["flips"], 4)                         # not instantly: the hand gets there first

    def test_every_swing_lands_on_its_clock_holds_and_recovers(self):
        for style, row in self.probe["swings"].items():
            with self.subTest(style=style):
                self.assertIsNotNone(row["contactAt"])
                self.assertLess(abs(row["contactAt"] - row["expectContact"]), 40)     # the rig says "now" when the world does
                self.assertGreater(row["arc"], 3.2)                                   # a real arc, not a jab
                self.assertGreater(row["trailMax"], 4)                                # a smear follows the edge
                self.assertGreater(row["sparks"], 4)                                  # sparks at contact
                self.assertGreaterEqual(row["heldFrames"], 2)                         # hitstop holds the contact frame
                self.assertEqual(row["ended"]["pose"], "hold")                        # and he settles back to the easy hold

    def test_other_loadouts_ignore_swing_requests(self):
        self.assertNotEqual(self.probe["daggerSwing"], "swing")


if __name__ == "__main__":
    unittest.main()
