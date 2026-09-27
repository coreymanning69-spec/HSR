// clock.js — the one frame clock. Everything that moves per frame subscribes
// here instead of running its own requestAnimationFrame loop, so there is one
// dt, one hidden-tab policy, one place to pause, slow down or freeze time
// (hitstop), and cut scenes and combat share the same timebase.
//
//   const off = clock.subscribe((dt, now) => {...}, {priority: 0});
//   clock.timeScale = .25;            // slow-motion, applied to every dt
//   clock.hitstop(80);                // freeze scaled time for 80 real ms
//   clock.every(100, fn);             // throttled subscriber
//
// dt is milliseconds, clamped to MAX_DT so a stalled tab cannot teleport
// anything. Lower priority runs first (simulate, then draw).

export const MAX_DT = 64;

export function createClock({
  raf = cb => requestAnimationFrame(cb),
  caf = id => cancelAnimationFrame(id),
  hidden = () => typeof document !== 'undefined' && document.hidden,
} = {}) {
  const subs = [];
  let id = 0, last = 0, freezeUntil = 0, paused = false;
  const clock = {
    timeScale: 1,
    time: 0,                                   // accumulated scaled ms
    get running() { return id !== 0; },
    get paused() { return paused; },
    pause() { paused = true; },
    resume() { paused = false; last = 0; },
    hitstop(ms) { freezeUntil = Math.max(freezeUntil, performance.now() + ms); },
    subscribe(fn, {priority = 0} = {}) {
      const sub = {fn, priority};
      subs.push(sub);
      subs.sort((a, b) => a.priority - b.priority);
      if (!id) { last = 0; id = raf(frame); }
      return () => {
        const i = subs.indexOf(sub);
        if (i >= 0) subs.splice(i, 1);
        if (!subs.length && id) { caf(id); id = 0; }
      };
    },
    every(ms, fn, opts) {
      let acc = 0;
      return clock.subscribe((dt, now) => { acc += dt; if (acc >= ms) { const step = acc; acc = 0; fn(step, now); } }, opts);
    },
  };
  function frame(now) {
    id = 0;
    if (!subs.length) return;
    id = raf(frame);
    if (hidden() || paused) { last = 0; return; }
    const real = last ? Math.min(MAX_DT, now - last) : 0;
    last = now;
    const frozen = performance.now() < freezeUntil;
    const dt = frozen ? 0 : real * clock.timeScale;
    clock.time += dt;
    for (const sub of subs.slice()) {
      try { sub.fn(dt, now); } catch (error) { console.error('clock subscriber failed', error); }
    }
  }
  return clock;
}

export const clock = createClock();
