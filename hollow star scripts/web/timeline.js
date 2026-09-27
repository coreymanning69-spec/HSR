// timeline.js — sequenced cues on the shared clock: the cut-scene primitive.
//
//   const tl = timeline.play([
//     {at: 0,   run: () => camera.pan(...)},
//     {at: 400, run: () => actor.say('...')},
//     {at: 900, run: ctx => ctx.wait(300).then(...)},   // ctx.t is elapsed ms
//   ], {onDone});
//   tl.pause(); tl.resume(); tl.seek(500); tl.skip(); tl.cancel();
//   await tl.done;                     // resolves on finish OR skip, never on cancel
//
// Time is the clock's scaled time, so slow-motion, hitstop, pause and hidden
// tabs affect a timeline exactly as they affect the stage. skip() fires every
// remaining cue immediately, in order, so a skipped scene still ends in the
// right state. Cue errors are logged and do not stop the sequence.

import {clock as sharedClock} from './clock.js';

export function createTimeline(clock = sharedClock) {
  function play(cues, {onDone, speed = 1} = {}) {
    const list = cues.map((cue, order) => ({...cue, order})).sort((a, b) => (a.at - b.at) || (a.order - b.order));
    const end = list.reduce((m, c) => Math.max(m, c.at + (c.duration || 0)), 0);
    let t = 0, next = 0, off = null, live = true, resolve;
    const done = new Promise(r => { resolve = r; });
    const ctx = {get t() { return t; }, wait: ms => after(ms)};
    function fire(cue) {
      try { cue.run?.(ctx); } catch (error) { console.error('timeline cue failed', error); }
    }
    function finish() {
      if (!live) return;
      live = false; off?.(); off = null;
      onDone?.(); resolve();
    }
    function advance() {
      while (next < list.length && list[next].at <= t) fire(list[next++]);
      if (next >= list.length && t >= end) finish();
    }
    const handle = {
      done,
      get time() { return t; },
      pause() { off?.(); off = null; },
      resume() { if (live && !off) off = clock.subscribe(dt => { t += dt * speed; advance(); }, {priority: -10}); },
      seek(ms) { t = ms; next = list.findIndex(c => c.at > ms); if (next < 0) next = list.length; },
      skip() { if (!live) return; while (next < list.length) fire(list[next++]); finish(); },
      cancel() { live = false; off?.(); off = null; },
    };
    handle.resume();
    advance();
    return handle;
  }
  // Clock-driven setTimeout: honours pause, slow-motion and hitstop.
  function after(ms) {
    return new Promise(resolve => { play([{at: ms, run: resolve}]); });
  }
  return {play, after};
}

export const timeline = createTimeline();
