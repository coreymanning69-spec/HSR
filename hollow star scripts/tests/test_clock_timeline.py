"""Shared frame clock, cue timeline and status-FX registry (web/clock.js,
timeline.js, status-fx.js), run headlessly in Node with a hand-cranked rAF."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROBE = (Path(__file__).with_name("web-probe-prelude.js").read_text(encoding="utf-8") + r"""
const {createClock} = await webModule('clock.js');
const {createTimeline} = await webModule('timeline.js');
const {wantedAuras, registerStatusFx} = await webModule('status-fx.js');

function rig(opts = {}) {
  let q = null, hidden = false, n = 0;
  const clock = createClock({raf: cb => { q = cb; return ++n; }, caf: () => { q = null; }, hidden: () => hidden});
  let now = 1000;
  return {clock, step(ms = 16) { now += ms; const cb = q; q = null; if (cb) cb(now); }, get pending() { return q !== null; }, setHidden(v) { hidden = v; }};
}
const out = {};

// -- clock: one loop, priority order, dt clamp, teardown, hidden, timeScale
{
  const r = rig(), order = [], dts = [];
  const offB = r.clock.subscribe(() => order.push('b'), {priority: 5});
  const offA = r.clock.subscribe(dt => { order.push('a'); dts.push(dt); }, {priority: 1});
  r.step(); r.step(16); r.step(500);
  out.order = order.slice(0, 2); out.dts = dts.slice();
  r.setHidden(true); const before = dts.length; r.step(16); out.hiddenSkipped = dts.length === before;
  r.setHidden(false); r.step(16); out.afterHiddenDt = dts[dts.length - 1]; r.step(16); out.nextDt = dts[dts.length - 1];
  r.clock.timeScale = .5; r.step(16); out.scaled = dts[dts.length - 1];
  offA(); offB(); out.stopped = !r.pending && !r.clock.running;
}
// -- clock: a throwing subscriber does not kill the loop
{
  const r = rig(); let ok = 0; const err = console.error; console.error = () => {};
  r.clock.subscribe(() => { throw new Error('x'); }); r.clock.subscribe(() => ok++);
  r.step(); r.step(); console.error = err; out.survivedThrow = ok;
}
// -- timeline: cues fire in order on scaled time; skip, seek, pause, cancel
{
  const r = rig(), tl = createTimeline(r.clock), log = [];
  const h = tl.play([{at: 100, run: () => log.push('b')}, {at: 0, run: () => log.push('a')}, {at: 100, run: () => log.push('c')}, {at: 300, run: () => log.push('d')}]);
  out.tl0 = log.slice();
  r.step(0); r.step(64); r.step(64);
  out.tl1 = log.slice();
  h.pause(); r.step(64); r.step(64); out.pausedHeld = log.length;
  h.resume(); h.skip(); out.skipped = log.slice(); out.skipStopsClock = !r.pending;
  const log2 = []; const h2 = tl.play([{at: 50, run: () => log2.push('x')}]); h2.cancel(); r.step(); r.step(200); out.cancelled = log2.length;
  const log3 = []; const h3 = tl.play([{at: 10, run: () => log3.push(1)}, {at: 500, run: () => log3.push(2)}]); h3.seek(400); r.step(0); r.step(64); r.step(64); out.seekLog = log3.slice();
}
// -- timeline: onDone / done, and a failing cue does not stop later cues
{
  const r = rig(), tl = createTimeline(r.clock); let done = 0, later = 0; const err = console.error; console.error = () => {};
  tl.play([{at: 0, run: () => { throw new Error('boom'); }}, {at: 20, run: () => later++}], {onDone: () => done++});
  r.step(0); r.step(32); r.step(32); console.error = err; out.done = done; out.later = later;
}
// -- status-fx: priority, radius, deterministic overlap, registration
{
  const w1 = wantedAuras({conditions: ['poisoned', 'burning']}), w2 = wantedAuras({conditions: ['poisoned']}), w3 = wantedAuras({blocking: true, status_tags: {burning: true}});
  out.fx = {both: w1.body.aura, poison: w2.body.aura, blocking: wantedAuras({blocking: true}).body.aura, burnBeatsShield: w3.body.aura,
    head: wantedAuras({invulnerable: true}).head, ground: wantedAuras({conditions: ['bless']}).ground, none: Object.keys(wantedAuras({})).length};
  registerStatusFx({tags: ['frozen'], socket: 'body', aura: 'frost', priority: 5});
  out.fx.frozen = wantedAuras({conditions: ['frozen', 'burning']}).body.aura;
}
console.log(JSON.stringify(out));
""")


class ClockTimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "--input-type=module", "-e", PROBE], cwd=ROOT,
                              capture_output=True, text=True, timeout=60)
        if done.returncode:
            raise AssertionError(done.stderr[-2000:])
        cls.out = json.loads(done.stdout.strip().splitlines()[-1])

    def test_clock_orders_by_priority_and_clamps_dt(self):
        self.assertEqual(self.out["order"], ["a", "b"])
        self.assertEqual(self.out["dts"], [0, 16, 64])          # first frame 0, stall clamped

    def test_clock_hidden_tab_and_time_scale(self):
        self.assertTrue(self.out["hiddenSkipped"])
        self.assertEqual(self.out["afterHiddenDt"], 0)           # first visible frame: no jump
        self.assertEqual(self.out["nextDt"], 16)
        self.assertEqual(self.out["scaled"], 8)

    def test_clock_stops_when_idle_and_survives_a_bad_subscriber(self):
        self.assertTrue(self.out["stopped"])
        self.assertEqual(self.out["survivedThrow"], 2)

    def test_timeline_fires_in_order_on_the_clock(self):
        self.assertEqual(self.out["tl0"], ["a"])
        self.assertEqual(self.out["tl1"], ["a", "b", "c"])      # 128ms elapsed: d (300ms) not yet
        self.assertEqual(self.out["pausedHeld"], len(self.out["tl1"]))

    def test_timeline_skip_finishes_and_releases_the_clock(self):
        self.assertEqual(self.out["skipped"], ["a", "b", "c", "d"])
        self.assertTrue(self.out["skipStopsClock"])

    def test_timeline_cancel_seek_and_failure_isolation(self):
        self.assertEqual(self.out["cancelled"], 0)
        self.assertEqual(self.out["seekLog"], [2])
        self.assertEqual((self.out["done"], self.out["later"]), (1, 1))

    def test_status_fx_priority_is_deterministic(self):
        fx = self.out["fx"]
        self.assertEqual((fx["both"], fx["poison"], fx["blocking"], fx["burnBeatsShield"]), ("fire", "poison", "force", "fire"))
        self.assertEqual(fx["head"], {"aura": "radiant", "radius": 22, "priority": 0})
        self.assertEqual(fx["ground"]["aura"], "radiant")
        self.assertEqual(fx["none"], 0)
        self.assertEqual(fx["frozen"], "frost")                  # a new status is one registration


if __name__ == "__main__":
    unittest.main()
