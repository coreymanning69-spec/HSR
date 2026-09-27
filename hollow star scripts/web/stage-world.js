import {DORAN_SWINGS, DORAN_DAGGER_TEMPO} from './doran-combat.js';
// Stage world: the rules of a scene, with no DOM in it.
//
// Bodies (size class, hurt box, footprint, weapon reach), movement on a depth
// plane (turn first, then walk; accelerate, brake, keep out of each other's
// footprints, route around blockers), ambient life for residents, and a small
// damage model (materials, wounds, stagger, breaking). The room scene and the
// Actor Toolbox both run this same world, and it is testable in Node.
//
// Presentation only. In a real run the host decides outcomes; this world moves
// figures, resolves swings against local targets (training dummies, props, the
// Toolbox's actors) and reports what to draw. Host-resolved combat keeps its
// own director and only borrows the wound and debris layer.
import {hash32, clamp, lerp} from './actor-core.js';

export const BASE_HEIGHT_FT = 5.667;          // the 5'8" the hero rig draws at unit scale
export const DORAN_SCALE = 1.25;              // Doran stands 1.25x a normal figure
export const SIZE_CLASSES = Object.freeze({tiny: .5, small: .82, medium: 1, large: 1.55, huge: 2.3, gargantuan: 3.1});

// Seeded, so a resident wanders the same way every visit to the same room.
export function rng(seed) {
  let a = typeof seed === 'number' ? seed >>> 0 : hash32(String(seed));
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// ---------------------------------------------------------------------------
// Bodies.
export function sizeClassOf(item = {}) {
  const raw = String(item.size || item.size_class || item.rules?.size || '').toLowerCase();
  if (SIZE_CLASSES[raw]) return raw;
  const text = `${item.identity || ''} ${item.name || ''} ${item.role || ''} ${item.race_id || ''} ${(item.tags || []).join(' ')}`;
  if (/titan|colossus|behemoth|tarrasque/i.test(text)) return 'gargantuan';
  if (/\bgiant\b|hill giant|stone giant|frost giant/i.test(text)) return 'huge';
  if (/ogre|troll|golem|castellan|hulk|juggernaut/i.test(text)) return 'large';
  if (/goblin|kobold|imp\b|gnome|halfling|sprite/i.test(text)) return 'small';
  if (item.age === 'child' || item.child === true) return 'small';
  return 'medium';
}
// Weapon length in feet: the whole implement, pommel to point.
export const WEAPON_LENGTH = Object.freeze({none: 0, cleaver: 9, sword: 3.4, dagger: 1.4, axe: 2.9, mace: 2.6, polearm: 7, staff: 6, wand: 1.5, bow: 4.2, daggers: 1.4});
// Presentation-only training damage. Not canon; a real run never reads it.
export const WEAPON_DAMAGE = Object.freeze({cleaver: {n: 2, d: 6, b: 5, type: 'slashing'}, sword: {n: 1, d: 8, b: 3, type: 'slashing'},
  dagger: {n: 1, d: 4, b: 3, type: 'piercing'}, daggers: {n: 1, d: 4, b: 3, type: 'piercing'}, axe: {n: 1, d: 12, b: 3, type: 'slashing'},
  mace: {n: 1, d: 6, b: 3, type: 'bludgeoning'}, polearm: {n: 1, d: 10, b: 3, type: 'piercing'}, staff: {n: 1, d: 6, b: 2, type: 'bludgeoning'},
  wand: {n: 1, d: 4, b: 0, type: 'force'}, bow: {n: 1, d: 8, b: 2, type: 'piercing'}, none: {n: 1, d: 4, b: 1, type: 'bludgeoning'}});

// One body for one item. `vis` scales the drawn figure box (a hero rig has no
// giant art, so size classes grow the box); `mult` is the physical scale that
// hurt boxes, footprints and reach use. Doran's rig already draws him 7'0", so
// he keeps vis 1 but a physical 1.25.
export function bodyOf(item = {}, weapon = item.weapon || 'none') {
  const identity = String(item.identity || '').toLowerCase();
  const cls = sizeClassOf(item);
  const vis = Number(item.scale) > 0 ? Number(item.scale) : identity === 'doran' ? 1 : SIZE_CLASSES[cls];
  const build = clamp(Number(item.appearance?.body_type?.scale) || 1, .8, 1.25);
  const mult = vis * (identity === 'doran' ? DORAN_SCALE : 1) * (identity === 'doran' ? 1 : build);
  const height = BASE_HEIGHT_FT * mult;
  // A goblin's spear is smaller than a person's, a giant's larger. Doran's Cleaver is nine feet whatever the body says.
  const length = (WEAPON_LENGTH[weapon] ?? 3) * (identity === 'doran' ? 1 : mult > 1 ? mult * .78 : mult);
  return {
    sizeClass: identity === 'doran' ? 'medium' : cls, vis, mult, height,
    width: 1.7 * mult,                                     // shoulder-to-shoulder hurt box
    foot: {rx: .78 * mult, rd: .34 * mult},                 // ft; footprint half-axes (depth is squashed)
    weapon, weaponLength: length,
    reach: .35 * height + length * .8,                      // body centre to the far tip of a swing
    walk: 4.2 * Math.sqrt(mult), run: 7.4 * Math.sqrt(mult),
    mass: 1 + (mult - 1) * 1.6,
  };
}

// ---------------------------------------------------------------------------
// Damage.
export const MATERIALS = Object.freeze({
  flesh: {blood: '#b3202c', chunk: '#6d1119', hard: .25, kind: 'blood'},
  undead: {blood: '#cfc8ae', chunk: '#8a846f', hard: .35, kind: 'dust'},
  wood: {blood: '#d6a163', chunk: '#8a5a34', hard: .5, kind: 'chip'},
  straw: {blood: '#e6cc74', chunk: '#b89a3e', hard: .12, kind: 'straw'},
  stone: {blood: '#c9c3b4', chunk: '#7c766a', hard: .9, kind: 'chip'},
  metal: {blood: '#ffe2a0', chunk: '#a8b0bc', hard: 1, kind: 'spark'},
  cloth: {blood: '#c8c1b5', chunk: '#8d8577', hard: .1, kind: 'dust'},
});
export function rollDamage(weapon, {crit = false, random = Math.random} = {}) {
  const w = WEAPON_DAMAGE[weapon] || WEAPON_DAMAGE.none;
  let total = w.b;
  for (let i = 0; i < w.n * (crit ? 2 : 1); i++) total += 1 + Math.floor(random() * w.d);
  return {amount: total, type: w.type};
}

// ---------------------------------------------------------------------------
// Swings. Contact is the fraction of the clip where the blade meets its
// target; the rig's own timing table (doran-rig.js) must match `ms`/`contact`.
// arc: degrees swept; step: ft the swinger drives forward; span: the band of
// the swinger's height the blade crosses (1 = overhead, 0 = the floor).
export const SWING_STYLES = Object.freeze({
  chop: {ms: 1150, contact: .56, arc: 54, step: 1.7, span: [.95, .25], label: 'Overhead chop', kind: 'slash'},
  cleave: {ms: 1020, contact: .52, arc: 112, step: 1.3, span: [.78, .42], label: 'Diagonal cleave', kind: 'slash'},
  sweep: {ms: 1260, contact: .55, arc: 220, step: .9, span: [.62, .3], label: 'Wide sweep', kind: 'slash'},
  rise: {ms: 960, contact: .5, arc: 76, step: 1.1, span: [.15, .8], label: 'Rising cut', kind: 'slash'},
});
export const SWING_ORDER = ['chop', 'cleave', 'sweep', 'rise'];
// A lighter weapon swings faster; the cleaver's 208 lb is the slowest.
const WEAPON_TEMPO = {cleaver: .5, polearm: .8, axe: .62, mace: .55, sword: .5, staff: .5, dagger: .34, daggers: .34, none: .4, wand: .4, bow: .5};
export function swingTiming(style, weapon = 'sword') {
  const base = SWING_STYLES[style] || SWING_STYLES.chop, k = WEAPON_TEMPO[weapon] ?? .5;
  const doran = weapon === 'cleaver' ? DORAN_SWINGS[style] : null;
  if (doran) return {...base, ms: doran.ms + doran.hitstop, contactMs: Math.round(doran.ms*doran.contact)};
  const tempo = weapon === 'daggers' ? DORAN_DAGGER_TEMPO : k;
  return {...base, ms: Math.round(base.ms*tempo), contactMs: Math.round(base.ms*tempo*base.contact)};
}

// ---------------------------------------------------------------------------
export function makeEntity(spec = {}) {
  const item = spec.item || {};
  const weapon = spec.weapon || item.weapon || 'none';
  const body = spec.body || bodyOf(item, weapon);
  const kind = spec.kind || 'actor';
  const hp = Number.isFinite(Number(spec.hp)) ? Number(spec.hp) : Number.isFinite(Number(item.hp)) ? Number(item.hp) : (kind === 'prop' ? 20 : 30);
  return {
    id: String(spec.id || item.id || `e${Math.random().toString(36).slice(2, 7)}`), kind, team: spec.team || 'npc',
    prop: spec.prop || null, name: spec.name || item.name || '', item, body, weapon,
    x: spec.x ?? 10, d: spec.d ?? .3, z: spec.z || 0, face: spec.face || 1, turn: null,
    vx: 0, vd: 0, goal: null, look: null, route: [], moving: false, run: false, gait: 0, stuck: 0,
    hp, max: Number.isFinite(Number(spec.max)) ? Number(spec.max) : Number.isFinite(Number(item.max_hp)) ? Number(item.max_hp) : hp,
    material: spec.material || (kind === 'prop' ? 'wood' : 'flesh'), armor: spec.armor || 0,
    alive: hp > 0, broken: false, wounds: [], flash: 0, stagger: 0, knock: 0, hurtAt: -1e9,
    ambient: spec.ambient || null, swing: null, queued: null, blocking: spec.blocking ?? kind === 'prop',
    cuttable: spec.cuttable ?? true, mode: spec.mode || null, spawnedAt: 0,
  };
}

export function createWorld({width = 44, depth = 12, seed = 'world', bounds = {x0: 1.5, x1: null, d0: .04, d1: .96}} = {}) {
  const ents = new Map(), events = [], random = rng(seed);
  let time = 0;
  const W = () => width, DEPTH = () => depth;
  const bound = {x0: bounds.x0 ?? 1.5, x1: bounds.x1 ?? width - 1.5, d0: bounds.d0 ?? .04, d1: bounds.d1 ?? .96};
  const list = () => [...ents.values()];
  const actors = () => list().filter(e => e.kind === 'actor' && !e.broken);
  const get = id => ents.get(String(id)) || null;
  // Feet between two entities, on the floor plane (depth is in its own units).
  const dist = (a, b) => Math.hypot(a.x - b.x, (a.d - b.d) * depth);
  const emit = ev => { events.push({t: time, ...ev}); };

  function add(spec) {
    const e = spec && spec.body && spec.id && spec.hp !== undefined && spec.wounds ? spec : makeEntity(spec);
    e.spawnedAt = time; ents.set(e.id, e); return e;
  }
  function remove(id) { ents.delete(String(id)); }
  // Where a walker may stand at depth d: a fixed span, or whatever the view
  // says is on screen there (the far floor is narrower than the near one).
  const spanAt = d => bound.rangeAt ? bound.rangeAt(d) : [bound.x0, bound.x1];
  function clampToBounds(e) {
    const m = e.body.foot.rx * .5, [lo, hi] = spanAt(e.d);
    e.x = clamp(e.x, lo + m, hi - m);
    e.d = clamp(e.d, bound.d0, bound.d1);
  }

  // Turn to face `dir` (+1 right, -1 left): 2.5D volumetric yaw turn. The figure
  // rotates through depth with head anticipation and a subtle vertical pivot bob.
  function faceDir(e, dir, quick = false) {
    if (!dir || dir === e.face || e.turn?.to === dir) return;
    e.turn = {from: e.face, to: dir, t: 0, dur: (quick ? 100 : 160) * Math.sqrt(e.body.mult), swapped: false};
  }
  function faceEntity(e, target) {
    const t = typeof target === 'object' ? target : get(target);
    if (t && Math.abs(t.x - e.x) > .25) faceDir(e, t.x > e.x ? 1 : -1);
  }
  // Volumetric 2.5D foreshortened width (body retains side-profile depth ~0.38 at the edge):
  const flipOf = e => {
    if (!e.turn) return 1;
    const p = clamp(e.turn.t / e.turn.dur, 0, 1);
    const phi = Math.PI * p;
    return Math.sqrt(Math.cos(phi) ** 2 + 0.14 * Math.sin(phi) ** 2);
  };
  const turnProgress = e => e.turn ? clamp(e.turn.t / e.turn.dur, 0, 1) : 0;
  const turnBob = e => 0;

  // Blocking props steer travel: a straight walk through one becomes a walk
  // around it, along whichever side has more room.
  function blockersFor(e, ignore = []) {
    return list().filter(o => o !== e && o.blocking && !o.broken && !ignore.includes(o.id) && (o.kind === 'prop' || o.body.mass > 0));
  }
  function routeAround(e, tx, td, ignore = []) {
    const fx = e.x, fd = e.d * depth;
    const path = [];
    let x = fx, d = fd;
    for (let guard = 0; guard < 4; guard++) {
      const dx = tx - x, dd = td * depth - d, len = Math.hypot(dx, dd) || 1;
      let hit = null, best = 1e9;
      for (const o of blockersFor(e, ignore)) {
        if (o.kind === 'actor') continue;                                  // people are dodged softly, not routed
        const rx = o.body.foot.rx + e.body.foot.rx * .6, rd = (o.body.foot.rd + e.body.foot.rd) * 1.4;
        const ox = (o.x - x) / rx, od = (o.d * depth - d) / rd, ux = dx / rx, ud = dd / rd;
        const ul = Math.hypot(ux, ud) || 1, proj = (ox * ux + od * ud) / ul, perp = Math.abs(ox * ud - od * ux) / ul;
        if (proj > 0 && proj < ul && perp < 1 && proj < best) { best = proj; hit = {o, rx, rd, side: (ox * ud - od * ux) > 0 ? -1 : 1}; }
      }
      if (!hit) break;
      const roomBelow = (hit.o.d * depth) - bound.d0 * depth, roomAbove = bound.d1 * depth - (hit.o.d * depth);
      const side = roomBelow > roomAbove ? -1 : 1;
      const wx = hit.o.x + (tx > fx ? hit.rx * .2 : -hit.rx * .2), wd = clamp(hit.o.d * depth + side * (hit.rd + .55), bound.d0 * depth, bound.d1 * depth);
      path.push({x: wx, d: wd / depth}); x = wx; d = wd;
      if (path.length >= 2) break;
    }
    return path;
  }

  // Walk to a spot. `arrive` is how close counts (ft); `run` picks the run
  // speed; `then` fires once on arrival. Replaces any earlier goal.
  function walkTo(id, x, d, {arrive = .35, run = false, then = null, faceAfter = 0, ignore = []} = {}) {
    const e = get(id); if (!e || !e.alive || e.swing) return false;
    const td = clamp(d ?? e.d, bound.d0, bound.d1), [lo, hi] = spanAt(td), tx = clamp(x, lo, hi);
    e.goal = {x: tx, d: td, arrive, run, then, faceAfter, ignore};
    e.route = routeAround(e, tx, td, ignore);
    e.run = run; e.look = null;
    return true;
  }
  // Walk up to another entity and stop at conversation range, on the side the
  // walker is coming from.
  function approach(id, targetId, {gap = 1.1, run = false, then = null} = {}) {
    const e = get(id), t = get(targetId); if (!e || !t) return false;
    const side = e.x <= t.x ? -1 : 1, want = e.body.foot.rx + t.body.foot.rx + gap;
    return walkTo(id, t.x + side * want, t.d, {arrive: .3, run, faceAfter: -side, ignore: [t.id], then});
  }
  function stop(id) { const e = get(id); if (e) { e.goal = null; e.route = []; } }
  function lookAt(id, target) { const e = get(id); if (e) e.look = target; }

  function steer(e, dtMs) {
    const dt = dtMs / 1000;
    const wp = e.route.length ? e.route[0] : e.goal;
    let wantX = 0, wantD = 0, speed = 0;
    if (wp && e.alive && !e.swing && e.stagger <= 0) {
      const dx = wp.x - e.x, dd = (wp.d - e.d) * depth, dist2 = Math.hypot(dx, dd);
      const arrive = e.route.length ? .45 : e.goal.arrive;
      if (dist2 <= arrive) {
        if (e.route.length) e.route.shift();
        else { const g = e.goal; e.goal = null; emit({type: 'arrive', id: e.id, x: e.x, d: e.d}); if (g.faceAfter) faceDir(e, g.faceAfter); g.then?.(e); }
      } else {
        const vmax = e.run || e.goal?.run ? e.body.run : e.body.walk;
        // Slow into the goal: v^2 / 2a is the braking distance.
        const accel = 9 * e.body.walk / Math.max(1, e.body.mass ** .5);
        const cur = Math.hypot(e.vx, e.vd * depth), brake = cur * cur / (2 * accel) + .2;
        speed = dist2 < brake ? Math.max(.6, vmax * dist2 / Math.max(brake, .01)) : vmax;
        if (e.route.length === 0 && dist2 < 1.4) speed = Math.min(speed, vmax * .55 + .5);
        wantX = dx / dist2 * speed; wantD = dd / dist2 * speed / depth;
        // Pivot first: the body faces the way it is about to travel, then goes.
        if (Math.abs(dx) > .35) faceDir(e, dx > 0 ? 1 : -1);
        if (e.turn && e.turn.t < e.turn.dur * .85 && cur < .8) { wantX = 0; wantD = 0; speed = 0; }
      }
    }
    // Accelerate toward the wanted velocity (ft/s, depth in units/s).
    const accel = 11 * e.body.walk / Math.max(1, e.body.mass ** .5), a = accel * dt;
    const ddx = wantX - e.vx, ddd = (wantD - e.vd) * depth, dl = Math.hypot(ddx, ddd);
    if (dl > a) { e.vx += ddx / dl * a; e.vd += ddd / dl * a / depth; } else { e.vx = wantX; e.vd = wantD; }
    // Knockback carries on top and decays.
    const push = e.knock; if (Math.abs(push) > .02) { e.x += push * dt; e.knock *= Math.exp(-dtMs / 170); } else e.knock = 0;
    e.x += e.vx * dt; e.d += e.vd * dt;
    const spd = Math.hypot(e.vx, e.vd * depth);
    e.moving = spd > .35; e.gait = spd / (.83 * e.body.height);      // stride cycles per second
  }

  // Soft separation: two bodies never stand inside each other; the lighter
  // one gives way, and a giant does not move for a townsperson.
  function separate(dtMs) {
    const a = actors().filter(e => e.alive || e.wounds.length);
    for (let i = 0; i < a.length; i++) for (let j = i + 1; j < a.length; j++) {
      const p = a[i], q = a[j];
      if (!p.alive || !q.alive) continue;
      const dx = q.x - p.x, dd = (q.d - p.d) * depth;
      const rx = (p.body.foot.rx + q.body.foot.rx) * .82, rd = (p.body.foot.rd + q.body.foot.rd) * 1.05;
      const nx = dx / rx, nd = dd / rd, n2 = nx * nx + nd * nd;
      if (n2 >= 1) continue;
      const n = Math.sqrt(n2) || .0001, over = (1 - n), ux = n2 ? nx / n : 1, ud = n2 ? nd / n : 0;
      const wp = q.body.mass / (p.body.mass + q.body.mass), wq = 1 - wp, k = Math.min(1, dtMs / 90);
      p.x -= ux * rx * over * .5 * wp * 2 * k; q.x += ux * rx * over * .5 * wq * 2 * k;
      p.d -= ud * rd * over * .5 * wp * 2 * k / depth; q.d += ud * rd * over * .5 * wq * 2 * k / depth;
    }
    for (const e of ents.values()) {
      if (e.kind !== 'actor') continue;
      for (const o of ents.values()) {
        if (o.kind !== 'prop' || !o.blocking || o.broken) continue;
        const rx = o.body.foot.rx + e.body.foot.rx * .6, rd = (o.body.foot.rd + e.body.foot.rd) * 1.1;
        const nx = (e.x - o.x) / rx, nd = ((e.d - o.d) * depth) / rd, n2 = nx * nx + nd * nd;
        if (n2 >= 1) continue;
        const n = Math.sqrt(n2) || .0001, over = 1 - n;
        e.x += (nx / n || 1) * rx * over * .6; e.d += ((nd / n) * rd * over * .6) / depth;
      }
      clampToBounds(e);
    }
  }

  // ---- ambient life ----------------------------------------------------------
  // A resident keeps to a leash around home: pause, look about, drift to
  // another spot, and turn to whoever the party is when they come close.
  function ambientStep(e, dtMs, leadId) {
    const A = e.ambient; if (!A || !e.alive || e.swing || e.stagger > 0) return;
    A.until ??= time + 800 + random() * 3000;
    const lead = leadId ? get(leadId) : null;
    if (lead && lead !== e) {
      const near = dist(e, lead) < 6.5 + e.body.foot.rx;
      if (near && !A.noticed && A.type !== 'still') { A.noticed = true; A.lookUntil = time + 2600 + random() * 2500; }
      if (!near) A.noticed = false;
      if (A.lookUntil && time < A.lookUntil) { if (!e.goal) faceEntity(e, lead); return; }
    }
    if (e.goal || time < A.until) return;
    A.until = time + 2500 + random() * 6500;
    if (A.type === 'guard' || A.type === 'still') { if (A.face) faceDir(e, A.face); return; }
    if (A.type === 'talk' && A.partner) {
      const p = get(A.partner);
      if (p) { faceEntity(e, p); if (random() < .3) A.until = time + 3000 + random() * 3000; return; }
    }
    // Wander: usually a short shuffle, sometimes just a glance the other way.
    if (random() < .35) { faceDir(e, e.face * -1); return; }
    const h = A.home || {x: e.x, d: e.d}, leash = A.leash ?? 4;
    walkTo(e.id, clamp(h.x + (random() * 2 - 1) * leash, bound.x0, bound.x1), clamp(h.d + (random() * 2 - 1) * leash * .35 / depth * 3, bound.d0, bound.d1), {arrive: .4});
  }

  // ---- swings and damage -----------------------------------------------------
  // Height (ft above the floor) at which a blade crosses a target, from the
  // swing's band of the swinger's own height clipped to the target's body.
  function contactHeight(att, tgt, style) {
    const span = (SWING_STYLES[style] || SWING_STYLES.chop).span;
    const lo = Math.min(...span) * att.body.height, hi = Math.max(...span) * att.body.height;
    const from = Math.max(lo, 0), to = Math.min(hi, tgt.body.height);
    if (to < from) return null;                                             // the blade passes over or under
    return (from + to) / 2;
  }
  // Who a swing reaches: inside the arc, inside reach (to the near edge of the
  // target's body), in the same lane, and at a height the blade crosses.
  function swingTargets(att, style, at = att) {
    const S = SWING_STYLES[style] || SWING_STYLES.chop, half = S.arc / 2 * Math.PI / 180, out = [];
    for (const t of list()) {
      if (t === att || t.broken || (!t.alive && t.kind === 'actor') || t.cuttable === false) continue;
      if (att.team && t.team === att.team && att.team !== 'neutral' && !att.hostileToAll) continue;
      const dx = t.x - at.x, dd = (t.d - at.d) * depth;
      const lane = att.body.foot.rd + t.body.foot.rd + .9 * att.body.mult;
      if (Math.abs(dd) > lane) continue;
      const edge = Math.max(0, Math.abs(dx) - t.body.width / 2);
      if (edge > att.body.reach) continue;
      const ang = Math.atan2(Math.abs(dd) * .4, Math.max(.001, Math.abs(dx)));
      if (Math.sign(dx || att.face) !== att.face && S.arc < 180 && Math.abs(dx) > t.body.width / 2) continue;
      if (S.arc >= 180 || ang <= half + .35 || Math.abs(dx) < t.body.width) {
        const y = contactHeight(att, t, style); if (y == null) continue;
        out.push({t, y, edge, dx, dd});
      }
    }
    return out.sort((p, q) => Math.abs(p.dx) - Math.abs(q.dx));
  }

  function beginSwing(id, style = 'chop') {
    const e = get(id); if (!e || !e.alive || e.broken) return null;
    if (e.swing) {                                                          // chain a follow-up in the last stretch of a swing
      const s = e.swing;
      if (time - s.at > s.ms * .45 && !e.queued) { e.queued = style; return {queued: style}; }
      return null;
    }
    const T = swingTiming(style, e.weapon);
    e.goal = null; e.route = [];
    e.swing = {style, at: time, ms: T.ms, contactAt: time + T.contactMs, contacted: false, step: T.step * Math.min(1.6, e.body.mult), x0: e.x, hits: [], id: `${e.id}:${time}`};
    emit({type: 'swing', id: e.id, style, ms: T.ms, contactMs: T.contactMs});
    return e.swing;
  }

  function applyHit(att, t, style, y, {crit = false} = {}) {
    const dmg = rollDamage(att?.weapon || 'none', {crit, random});
    const mat = MATERIALS[t.material] || MATERIALS.flesh;
    const heavy = att && att.body.mult > t.body.mult * 1.3 ? 1.4 : 1;
    const dealt = Math.max(1, Math.round((dmg.amount - t.armor) * (1 - mat.hard * .25) * heavy));
    const before = t.hp; t.hp = Math.max(0, t.hp - dealt);
    const dir = att ? (t.x >= att.x ? 1 : -1) : 1;
    // Wound lands where the blade crossed, as a fraction of the target's body.
    const v = clamp(1 - y / Math.max(.5, t.body.height), .04, .96);
    const sweepy = style === 'sweep' || style === 'cleave';
    const ang = style === 'chop' ? 1.35 * -dir : style === 'rise' ? -1.1 * -dir : sweepy ? .5 * dir : .9 * dir;
    const wound = {u: clamp(.5 + (random() - .5) * .34, .2, .8), v, ang, len: clamp(.1 + dealt / Math.max(18, t.max) * .3, .1, .34) * (style === 'sweep' ? 1.25 : 1),
      kind: style === 'rise' ? 'gash' : 'slash', age: 0, seed: random()};
    t.wounds.push(wound); if (t.wounds.length > 9) t.wounds.shift();
    t.flash = 160; t.hurtAt = time;
    const killed = before > 0 && t.hp <= 0;
    const push = (crit ? 7.5 : 4.2) * dir * (att ? Math.min(2.2, att.body.mass / Math.max(.6, t.body.mass) ** .8) : 1) * (t.kind === 'prop' ? .35 : 1);
    t.knock += push / (1 + t.body.mass * .35);
    t.stagger = t.kind === 'prop' ? 0 : Math.min(620, 160 + dealt * 22) / (1 + (t.body.mult - 1) * .5);
    if (t.kind === 'actor' && att) faceDir(t, dir * -1);
    if (killed) { t.alive = false; t.goal = null; t.route = []; t.swing = null; emit({type: 'death', id: t.id, by: att?.id, dir, kind: t.kind}); if (t.kind === 'prop') { t.broken = true; emit({type: 'break', id: t.id, dir}); } }
    const ev = {type: 'hit', attacker: att?.id, target: t.id, damage: dealt, hp: t.hp, max: t.max, crit, killed, style, y, v, dir, material: t.material, weaponType: dmg.type, wound};
    emit(ev); return ev;
  }
  function hit(attackerId, targetId, style = 'chop', {crit = false} = {}) {
    const att = get(attackerId), t = get(targetId); if (!t) return null;
    return applyHit(att, t, style, contactHeight(att, t, style) ?? t.body.height * .6, {crit});
  }
  function contact(e) {
    const s = e.swing; s.contacted = true;
    const targets = swingTargets(e, s.style);
    emit({type: 'contact', id: e.id, style: s.style, targets: targets.map(x => x.t.id)});
    const crit = random() < .12;
    for (const {t, y} of targets.slice(0, s.style === 'sweep' ? 6 : s.style === 'cleave' ? 3 : 2)) s.hits.push(applyHit(e, t, s.style, y, {crit}));
  }

  function heal(id, amount = null) {
    const e = get(id); if (!e) return;
    e.hp = amount == null ? e.max : Math.min(e.max, e.hp + amount); e.alive = e.hp > 0; e.broken = false; e.wounds = amount == null ? [] : e.wounds;
    e.stagger = 0; e.flash = 0; e.knock = 0;
  }

  function step(dtMs, {lead = null} = {}) {
    dtMs = clamp(dtMs || 0, 0, 64); time += dtMs;
    for (const e of ents.values()) {
      if (e.turn) {
        e.turn.t += dtMs;
        if (!e.turn.swapped && e.turn.t >= e.turn.dur / 2) { e.face = e.turn.to; e.turn.swapped = true; }
        if (e.turn.t >= e.turn.dur) e.turn = null;
      }
      e.flash = Math.max(0, e.flash - dtMs); e.stagger = Math.max(0, e.stagger - dtMs);
      for (const w of e.wounds) w.age += dtMs;
      if (e.kind !== 'actor') { if (Math.abs(e.knock) > .02) { e.x += e.knock * dtMs / 1000; e.knock *= Math.exp(-dtMs / 170); clampToBounds(e); } continue; }
      if (e.swing) {
        const s = e.swing, t = time - s.at, k = clamp(t / s.ms, 0, 1), c = s.contactAt - s.at;
        // Drive forward into the blow, ease back a little on the recover.
        const drive = t < c ? Math.sin(clamp(t / c, 0, 1) * Math.PI / 2) : lerp(1, .55, clamp((t - c) / (s.ms - c), 0, 1));
        const nx = s.x0 + e.face * s.step * drive; e.vx = 0; e.vd = 0; e.x += (nx - e.x) * Math.min(1, dtMs / 55);
        if (!s.contacted && time >= s.contactAt) contact(e);
        if (k >= 1) { const q = e.queued; e.swing = null; e.queued = null; emit({type: 'swing_end', id: e.id, style: s.style}); if (q && e.alive) beginSwing(e.id, q); }
        e.moving = false; e.gait = 0;
      } else steer(e, dtMs);
      if (e.look && !e.goal) faceEntity(e, e.look);
      ambientStep(e, dtMs, lead);
    }
    separate(dtMs);
    return events.splice(0);
  }
  function setBounds(next) { Object.assign(bound, next); }
  function setSize(w, d = depth) { width = w; depth = d; bound.x1 = w - 1.5; }
  return {add, remove, get, list, actors, dist, walkTo, approach, stop, lookAt, faceDir, faceEntity, flipOf, turnProgress, turnBob, beginSwing, swingTargets, hit, heal, step,
    setBounds, setSize, get time() { return time; }, width: W, depth: DEPTH, bound, random, emit};
}

// ---------------------------------------------------------------------------
// Props that can stand in the world and take a blow. `w`/`h` are ft; `hp` is
// how much cutting they take; `blocking` props steer walkers around them.
export const PROP_TYPES = Object.freeze({
  crate: {w: 2.3, h: 2.1, hp: 26, material: 'wood', mass: 1.4, name: 'Crate'},
  barrel: {w: 1.9, h: 2.7, hp: 20, material: 'wood', mass: 1.2, name: 'Barrel'},
  dummy: {w: 1.9, h: 5.7, hp: 70, material: 'straw', mass: 2.4, name: 'Training dummy'},
  post: {w: 1.1, h: 6.2, hp: 90, material: 'wood', mass: 3, name: 'Practice post'},
  table: {w: 4.2, h: 2.6, hp: 40, material: 'wood', mass: 2, name: 'Table'},
  sack: {w: 1.7, h: 2.1, hp: 12, material: 'cloth', mass: .8, name: 'Grain sack'},
  statue: {w: 2.4, h: 7.4, hp: 220, material: 'stone', mass: 6, name: 'Statue'},
  banner: {w: 1.2, h: 7, hp: 16, material: 'cloth', mass: .4, name: 'Banner', blocking: false},
  pillar: {w: 2.4, h: 9, hp: 400, material: 'stone', mass: 9, name: 'Pillar'},
  bench: {w: 4.4, h: 1.7, hp: 30, material: 'wood', mass: 1.5, name: 'Bench', blocking: false},
  desk: {w: 4.2, h: 2.6, hp: 40, material: 'wood', mass: 2, name: 'Desk'},
  rack: {w: 4.6, h: 4.6, hp: 30, material: 'wood', mass: 2, name: 'Weapon rack', blocking: false},
  bell: {w: 1.5, h: 3.6, hp: 60, material: 'metal', mass: 2, name: 'Bell', blocking: false},
  altar: {w: 3.4, h: 3.2, hp: 200, material: 'stone', mass: 5, name: 'Altar'},
  brazier: {w: 1.7, h: 3.1, hp: 60, material: 'metal', mass: 1.5, name: 'Brazier'},
  lamppost: {w: 1, h: 8.5, hp: 50, material: 'metal', mass: 2, name: 'Lamp post', blocking: false},
  coffin: {w: 2.8, h: 4.2, hp: 90, material: 'stone', mass: 4, name: 'Sarcophagus'},
  pouch: {w: 1.1, h: .9, hp: 4, material: 'cloth', mass: .2, name: 'Pouch', blocking: false},
  bin: {w: 1.9, h: 3, hp: 26, material: 'metal', mass: 1.2, name: 'Bin'},
  chest: {w: 2.8, h: 2.4, hp: 40, material: 'wood', mass: 1.6, name: 'Chest'},
  cabinet: {w: 2.8, h: 6, hp: 45, material: 'wood', mass: 2, name: 'Cabinet'},
  parcel: {w: 1.8, h: 1.6, hp: 10, material: 'cloth', mass: .6, name: 'Parcel', blocking: false},
  rope: {w: 1.4, h: 6, hp: 8, material: 'cloth', mass: .3, name: 'Rope', blocking: false},
  wheel: {w: 5, h: 5, hp: 120, material: 'wood', mass: 4, name: 'Wheel', blocking: false},
  boat: {w: 8, h: 3.2, hp: 90, material: 'wood', mass: 5, name: 'Skiff'},
  campfire: {w: 3.2, h: 2.8, hp: 999, material: 'stone', mass: 2, name: 'Campfire', blocking: true},
  stall: {w: 6.4, h: 7.2, hp: 60, material: 'wood', mass: 3, name: 'Market stall', blocking: false},
  bed: {w: 4.6, h: 3.6, hp: 50, material: 'wood', mass: 3, name: 'Bed'},
  tent: {w: 7, h: 6.4, hp: 80, material: 'cloth', mass: 3, name: 'Tent'},
});
// Things that are part of the place, not for cutting (the Toolbox can override).
export const FIXTURES = new Set(['pillar', 'statue', 'altar', 'bell', 'lamppost', 'campfire', 'wheel', 'coffin', 'brazier', 'rope', 'banner', 'tent', 'boat']);
export function propBody(type = 'crate', scale = 1) {
  const P = PROP_TYPES[type] || PROP_TYPES.crate;
  return {sizeClass: 'prop', vis: scale, mult: scale, height: P.h * scale, width: P.w * scale, foot: {rx: P.w * scale * .5, rd: Math.min(.9, P.w * scale * .22)},
    weapon: 'none', weaponLength: 0, reach: 0, walk: 0, run: 0, mass: P.mass * scale};
}
export function makeProp(type, {id, x, d, scale = 1, hp, blocking, cuttable} = {}) {
  const P = PROP_TYPES[type] || PROP_TYPES.crate;
  return makeEntity({id: id || `${type}-${Math.random().toString(36).slice(2, 6)}`, kind: 'prop', prop: type, name: P.name, x, d, body: propBody(type, scale),
    hp: hp ?? P.hp * scale, material: P.material, team: 'neutral', blocking: blocking ?? P.blocking ?? true, cuttable: cuttable ?? !FIXTURES.has(type)});
}
