"""Stage world: bodies, movement, reach, damage and swing timing (web/stage-world.js).

The world is pure logic, so it runs headlessly under Node. The probe copies the
web modules into a throwaway ES-module directory (tests/web-probe-prelude.js)
and drives the world through the situations the main display relies on: a figure
that turns before it walks, walks around a blocker, swings and lands a blow, and
whose body size sets its hit box and reach.
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

PROBE = (Path(__file__).with_name("web-probe-prelude.js").read_text(encoding="utf-8") + r"""
const W = await webModule('stage-world.js');
const R = await webModule('doran-rig.js');
const out = {};
const near = (a, b, e = 1e-6) => Math.abs(a - b) <= e;

// ---- bodies -----------------------------------------------------------------
const B = (item, weapon) => W.bodyOf(item, weapon);
const doran = B({identity: 'doran'}, 'cleaver'), human = B({}, 'sword'), gob = B({size: 'small'}, 'dagger'), ogre = B({name: 'Ogre'}, 'mace'),
  giant = B({size: 'huge'}, 'polearm'), titan = B({size: 'gargantuan'}, 'polearm');
out.bodies = {doranMult: doran.mult, doranHeight: doran.height, doranVis: doran.vis, doranReach: doran.reach, humanHeight: human.height,
  ogreClass: ogre.sizeClass, giantHeight: giant.height, giantVis: giant.vis, giantReach: giant.reach, humanReach: human.reach,
  ladder: [gob, human, ogre, giant, titan].map(b => [b.height, b.reach, b.foot.rx, b.width]), castellan: W.sizeClassOf({name: 'Brass Castellan'}), child: W.sizeClassOf({age: 'child'}),
  hostSize: W.sizeClassOf({size: 'Large'}), champion: B({identity: 'doran', size: 'huge'}, 'cleaver').vis};

// ---- turn first, then walk ------------------------------------------------------
{
  const w = W.createWorld({width: 44, depth: 10});
  const e = w.add({id: 'a', item: {name: 'A'}, weapon: 'sword', x: 20, d: .5, face: 1});
  w.walkTo('a', 8, .5);
  let faceAtMove = null, maxSpeed = 0, arrivedAt = -1, t = 0, turnSeen = false, gaitSeen = 0;
  for (let i = 0; i < 400; i++) {
    const ev = w.step(16); t += 16;
    if (e.turn) turnSeen = true;
    if (faceAtMove === null && Math.abs(e.x - 20) > .5) faceAtMove = e.face;
    maxSpeed = Math.max(maxSpeed, Math.hypot(e.vx, e.vd * 10)); gaitSeen = Math.max(gaitSeen, e.gait);
    if (ev.some(x => x.type === 'arrive')) { arrivedAt = t; break; }
  }
  out.walk = {faceAtMove, turnSeen, maxSpeed, walkLimit: e.body.walk, arrivedAt, x: e.x, gaitSeen};
  const r = W.createWorld({width: 44, depth: 10}), f = r.add({id: 'r', item: {}, weapon: 'none', x: 5, d: .5});
  r.walkTo('r', 35, .5, {run: true}); let runMax = 0;
  for (let i = 0; i < 400; i++) { r.step(16); runMax = Math.max(runMax, Math.hypot(f.vx, f.vd * 10)); }
  out.run = {runMax, runLimit: f.body.run, walkLimit: f.body.walk};
}

// ---- routing around a blocker -------------------------------------------------------
{
  const w = W.createWorld({width: 44, depth: 10});
  const crate = w.add(W.makeProp('crate', {id: 'crate', x: 14, d: .5}));
  const e = w.add({id: 'a', item: {}, weapon: 'none', x: 6, d: .5});
  w.walkTo('a', 22, .5);
  let minNorm = 9, maxDev = 0;
  for (let i = 0; i < 500; i++) {
    w.step(16);
    const rx = crate.body.foot.rx + e.body.foot.rx * .6, rd = (crate.body.foot.rd + e.body.foot.rd) * 1.1;
    minNorm = Math.min(minNorm, Math.hypot((e.x - crate.x) / rx, (e.d - crate.d) * 10 / rd));
    maxDev = Math.max(maxDev, Math.abs(e.d - .5));
  }
  out.route = {minNorm, maxDev, endX: e.x};
}

// ---- swings and damage --------------------------------------------------------------
const rig = (id, x, d, extra = {}) => ({id, item: {identity: 'doran'}, weapon: 'cleaver', team: 'party', x, d, face: 1, ...extra});
function fight(style, setup) {
  const w = W.createWorld({width: 44, depth: 10, seed: 'fight'});
  const doran = w.add(rig('doran', 10, .5)), targets = setup(w);
  w.beginSwing('doran', style); const events = [];
  for (let i = 0; i < 120; i++) events.push(...w.step(16));
  return {w, doran, targets, events, hits: events.filter(e => e.type === 'hit')};
}
{
  const a = fight('chop', w => [w.add(W.makeProp('dummy', {id: 'front', x: 16, d: .5})), w.add(W.makeProp('dummy', {id: 'behind', x: 3, d: .5})),
    w.add(W.makeProp('dummy', {id: 'lane', x: 16, d: .95})), w.add(W.makeProp('dummy', {id: 'far', x: 30, d: .5}))]);
  out.chop = {hit: a.hits.map(h => h.target), hpFront: a.targets[0].hp, maxFront: a.targets[0].max, wounds: a.targets[0].wounds.length, types: a.events.map(e => e.type),
    dmg: a.hits.map(h => h.damage), swinging: Boolean(a.doran.swing), stepped: a.doran.x - 10};
  const s = fight('sweep', w => [w.add(W.makeProp('dummy', {id: 'front', x: 16, d: .5})), w.add(W.makeProp('dummy', {id: 'behind', x: 5, d: .5}))]);
  out.sweep = {hit: s.hits.map(h => h.target).sort()};
  const c = fight('cleave', w => [w.add(W.makeProp('dummy', {id: 'front', x: 16, d: .5}))]);
  out.cleave = {hit: c.hits.map(h => h.target), y: c.hits.map(h => h.y)};
}
{
  // A prop dies and breaks; a broken prop is no longer a target. Actors keep to their side.
  const w = W.createWorld({width: 44, depth: 10, seed: 'kill'});
  const d = w.add(rig('doran', 10, .5)), crate = w.add(W.makeProp('crate', {id: 'crate', x: 15, d: .5, hp: 6}));
  const friend = w.add({id: 'friend', item: {}, weapon: 'none', team: 'party', x: 14, d: .5});
  const foe = w.add({id: 'foe', item: {}, weapon: 'none', team: 'foe', x: 16, d: .5, hp: 4, cuttable: true});
  w.beginSwing('doran', 'chop'); const ev = [];
  for (let i = 0; i < 120; i++) ev.push(...w.step(16));
  out.kill = {types: ev.map(e => e.type), crateBroken: crate.broken, crateHp: crate.hp, foeAlive: foe.alive, friendHp: friend.hp, friendMax: friend.max,
    targetsAfter: w.swingTargets(d, 'chop').map(x => x.t.id)};
}
{
  // Size sets how far a swing reaches and how far a blow throws.
  const reach = id => { const w = W.createWorld({width: 44, depth: 10}); return w.add({id, item: {size: id}, weapon: 'polearm'}).body.reach; };
  const knock = size => {
    const w = W.createWorld({width: 44, depth: 10, seed: 'k'}); const a = w.add(rig('doran', 10, .5)), t = w.add({id: 't', item: {size}, weapon: 'none', team: 'foe', x: 14, d: .5, hp: 500, max: 500});
    w.hit('doran', 't', 'chop'); return t.knock;
  };
  out.size = {smallReach: reach('small'), hugeReach: reach('huge'), knockSmall: knock('small'), knockHuge: knock('huge')};
}

// ---- the rig and the world agree on timing ----------------------------------------------
out.timing = Object.keys(W.SWING_STYLES).map(style => {
  const base = W.SWING_STYLES[style], rigT = R.DORAN_SWINGS[style], t = W.swingTiming(style, 'cleaver');
  return {style, sameContact: near(base.contact, rigT.contact), msMatches: t.ms === rigT.ms + R.DORAN_HITSTOP, contactMs: t.contactMs, rigContactMs: Math.round(rigT.ms * rigT.contact)};
});

// ---- residents keep to their leash -------------------------------------------------------
{
  const w = W.createWorld({width: 44, depth: 10, seed: 'ambient'});
  const home = {x: 30, d: .5}, walker = w.add({id: 'w', item: {}, weapon: 'none', x: 30, d: .5, ambient: {type: 'wander', home, leash: 3}}),
    guard = w.add({id: 'g', item: {}, weapon: 'polearm', x: 12, d: .4, face: 1, ambient: {type: 'guard', home: {x: 12, d: .4}, leash: 0, face: -1}});
  let far = 0, turns = 0, last = walker.face, moved = 0, px = walker.x;
  for (let i = 0; i < 3000; i++) { w.step(32); far = Math.max(far, Math.abs(walker.x - home.x)); if (walker.face !== last) { turns++; last = walker.face; } moved += Math.abs(walker.x - px); px = walker.x; }
  out.ambient = {far, turns, moved, guardX: guard.x, guardFace: guard.face};
}

// ---- bodies never stand inside each other ------------------------------------------------
{
  const w = W.createWorld({width: 44, depth: 10});
  const a = w.add({id: 'a', item: {}, weapon: 'none', x: 20, d: .5}), b = w.add({id: 'b', item: {size: 'huge'}, weapon: 'none', x: 20.1, d: .5});
  for (let i = 0; i < 60; i++) w.step(16);
  out.separate = {gap: Math.abs(a.x - b.x), need: (a.body.foot.rx + b.body.foot.rx) * .82 * .9, giantMoved: Math.abs(b.x - 20.1), smallMoved: Math.abs(a.x - 20)};
}

// ---- depth-dependent walkable span ---------------------------------------------------------
{
  const w = W.createWorld({width: 44, depth: 10}); w.setBounds({rangeAt: d => [5 + 10 * d, 40 - 10 * d]});
  const e = w.add({id: 'e', item: {}, weapon: 'none', x: 22, d: .1});
  w.walkTo('e', 100, .9); for (let i = 0; i < 700; i++) w.step(16);
  out.span = {x: e.x, expect: 40 - 9};
}
console.log(JSON.stringify(out));
""")


class StageWorldTests(unittest.TestCase):
    probe: dict = {}

    @classmethod
    def setUpClass(cls):
        res = subprocess.run(["node", "--input-type=module", "-e", PROBE], cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            raise AssertionError(f"stage-world probe failed: {res.stderr}")
        cls.probe = json.loads(res.stdout.strip().splitlines()[-1])

    def test_doran_is_one_and_a_quarter_times_a_person_and_giants_are_bigger(self):
        b = self.probe["bodies"]
        self.assertAlmostEqual(b["doranMult"], 1.25)
        self.assertAlmostEqual(b["doranHeight"] / b["humanHeight"], 1.25, places=3)
        self.assertEqual(b["doranVis"], 1)                       # his rig already draws him 7'0"; the box does not grow twice
        self.assertGreater(b["doranReach"], 9)                   # a nine-foot blade reaches
        self.assertEqual(b["ogreClass"], "large")
        self.assertGreater(b["giantHeight"], 2 * b["humanHeight"])
        self.assertGreater(b["giantVis"], 2)
        self.assertGreater(b["giantReach"], b["humanReach"] * 1.5)
        self.assertEqual(b["castellan"], "large")
        self.assertEqual(b["child"], "small")
        self.assertEqual(b["hostSize"], "large")                 # the host's own size word wins
        self.assertEqual(b["champion"], 1)                       # a champion's box never scales by a size class

    def test_every_size_class_step_grows_height_reach_and_footprint(self):
        ladder = self.probe["bodies"]["ladder"]
        for lower, upper in zip(ladder, ladder[1:]):
            for a, c in zip(lower, upper):
                self.assertGreater(c, a)

    def test_a_figure_turns_before_it_walks(self):
        w = self.probe["walk"]
        self.assertTrue(w["turnSeen"])
        self.assertEqual(w["faceAtMove"], -1)                    # already facing the way it goes when it moves off
        self.assertLessEqual(w["maxSpeed"], w["walkLimit"] * 1.05)
        self.assertGreater(w["gaitSeen"], 0.3)                   # stride cycles per second reach the rig
        self.assertGreater(w["arrivedAt"], 0)
        self.assertLess(abs(w["x"] - 8), 0.6)
        r = self.probe["run"]
        self.assertGreater(r["runMax"], r["walkLimit"] * 1.2)
        self.assertLessEqual(r["runMax"], r["runLimit"] * 1.05)

    def test_a_blocker_is_walked_around(self):
        r = self.probe["route"]
        self.assertGreater(r["minNorm"], 0.85)                   # never inside the crate's footprint
        self.assertGreater(r["maxDev"], 0.03)                    # it went around, not through
        self.assertLess(abs(r["endX"] - 22), 0.7)

    def test_a_chop_hits_what_is_in_reach_and_lane_and_front(self):
        c = self.probe["chop"]
        self.assertEqual(c["hit"], ["front"])                    # not behind, not another lane, not out of reach
        self.assertLess(c["hpFront"], c["maxFront"])
        self.assertEqual(c["wounds"], 1)
        self.assertEqual(c["types"][0], "swing")
        self.assertIn("contact", c["types"])
        self.assertLess(c["types"].index("contact"), c["types"].index("hit"))
        self.assertEqual(c["types"][-1], "swing_end")
        self.assertFalse(c["swinging"])
        self.assertGreater(c["stepped"], 0.5)                    # he drives into the blow
        self.assertTrue(all(6 <= d <= 30 for d in c["dmg"]))     # 2d6+5 training damage

    def test_a_sweep_reaches_behind_and_a_cleave_lands_at_torso_height(self):
        self.assertEqual(self.probe["sweep"]["hit"], ["behind", "front"])
        cleave = self.probe["cleave"]
        self.assertEqual(cleave["hit"], ["front"])
        self.assertTrue(all(2 < y < 5.5 for y in cleave["y"]))

    def test_props_break_and_stay_broken_and_allies_are_spared(self):
        k = self.probe["kill"]
        self.assertIn("death", k["types"])
        self.assertIn("break", k["types"])
        self.assertTrue(k["crateBroken"])
        self.assertEqual(k["crateHp"], 0)
        self.assertFalse(k["foeAlive"])
        self.assertEqual(k["friendHp"], k["friendMax"])          # same team: never hit
        self.assertNotIn("crate", k["targetsAfter"])

    def test_bigger_bodies_reach_further_and_are_thrown_less(self):
        s = self.probe["size"]
        self.assertGreater(s["hugeReach"], s["smallReach"] * 2)
        self.assertGreater(s["knockSmall"], s["knockHuge"] * 1.5)

    def test_world_and_rig_swing_clocks_match(self):
        for row in self.probe["timing"]:
            with self.subTest(style=row["style"]):
                self.assertTrue(row["sameContact"])
                self.assertTrue(row["msMatches"])                # the world's clock includes the rig's hitstop
                self.assertLessEqual(abs(row["contactMs"] - row["rigContactMs"]), 1)

    def test_residents_keep_to_their_leash_and_guards_hold_their_post(self):
        a = self.probe["ambient"]
        self.assertLessEqual(a["far"], 3 + 1.2)
        self.assertGreaterEqual(a["turns"], 1)
        self.assertGreater(a["moved"], 3)                        # it did wander
        self.assertEqual(a["guardX"], 12)
        self.assertEqual(a["guardFace"], -1)

    def test_bodies_do_not_stack_and_the_lighter_one_gives_way(self):
        s = self.probe["separate"]
        self.assertGreaterEqual(s["gap"], s["need"])
        self.assertGreater(s["smallMoved"], s["giantMoved"])

    def test_walkable_span_follows_depth(self):
        self.assertLessEqual(self.probe["span"]["x"], self.probe["span"]["expect"] + 0.6)


class StageModuleContractTests(unittest.TestCase):
    """Static contracts for the wiring the browser depends on."""

    def test_stage_files_are_wired_into_the_page_and_app(self):
        index = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("stage-scene.css", index)
        app = (WEB / "app.js").read_text(encoding="utf-8")
        for needle in ("createStage", "createToolbox", "keepWorldStage", "data-world-slot", "menu:toolbox", "worldTimeOfDay"):
            self.assertIn(needle, app)
        dom = (WEB / "puppet-dom.js").read_text(encoding="utf-8")
        for needle in ("node.dataset.facing", "node.dataset.carry", "node.dataset.gait", "node.dataset.swing"):
            self.assertIn(needle, dom)

    def test_no_stage_module_reads_host_state_it_should_not(self):
        for name in ("stage-world.js", "stage-set.js", "stage-fx.js", "stage-art.js"):
            text = (WEB / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\bfetch\(|/api/host|localStorage")   # presentation only


if __name__ == "__main__":
    unittest.main()
