// Shared actor runtime: the pieces every rig uses to look alive and stay fast.
//
// Rigs (wren-rig.js, doran-rig.js, hero-rig.js) own their art and poses. This
// module owns what they have in common: cel shading that does not allocate a
// gradient per fill per frame, far-side palettes that replace ctx.filter (a
// per-part offscreen pass), springs for cloth and hair, a motion tracker that
// turns on-screen movement and knockback into lean and trail, weapon smears,
// and per-actor element particles.
//
// Presentation only. Nothing here reads or decides mechanics; rigs draw the
// outcomes the host has already resolved.

export const TAU = Math.PI * 2;
export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
export const lerp = (a, b, k) => a + (b - a) * k;
// Exponential approach factor for one frame: 1 - e^(-dt/tau). tau <= 0 snaps.
export const ease = (dt, tau) => (!(tau > 0) || !Number.isFinite(dt)) ? 1 : 1 - Math.exp(-Math.max(0, dt) / tau);
// Stable 32-bit hash for seeding per-actor variety (blinks, fidgets, NPC looks).
export function hash32(text = '') {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) { h ^= text.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

// ---------------------------------------------------------------------------
// Colour.
export const isHex = v => typeof v === 'string' && /^#[0-9a-f]{6}$/i.test(v);
const rgbOf = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
export function mixHex(a, b, k) {
  if (!isHex(a)) return a;
  if (!isHex(b)) return a;
  const x = rgbOf(a), y = rgbOf(b);
  return '#' + x.map((v, i) => Math.round(v + (y[i] - v) * k).toString(16).padStart(2, '0')).join('');
}
export const shadeHex = (hex, k = .3) => mixHex(hex, '#141826', k);
export const lightHex = (hex, k = .25) => mixHex(hex, '#ffffff', k);
export function rgba(hex, alpha) {
  if (!isHex(hex)) return hex;
  const [r, g, b] = rgbOf(hex);
  return `rgba(${r},${g},${b},${alpha})`;
}
// Relative luminance 0..1, for picking ink-on-colour and highlight strength.
export function luma(hex) {
  if (!isHex(hex)) return .5;
  const [r, g, b] = rgbOf(hex);
  return (.2126 * r + .7152 * g + .0722 * b) / 255;
}
// A far-side copy of a palette, every colour one cel step darker. This is what
// ctx.filter = 'brightness(.82)' did, without forcing an offscreen pass for
// every far limb on every frame.
export function farPalette(palette, k = .17) {
  const out = {};
  for (const [key, value] of Object.entries(palette)) out[key] = isHex(value) ? mixHex(value, '#0d1018', k) : value;
  return out;
}

// ---------------------------------------------------------------------------
// Cached cel gradients. A canvas gradient belongs to the context that made it
// and is resolved in the transform current at fill time, so one made in a
// part's local units can be reused every frame for that part. The rigs used to
// allocate ~30 of these per figure per frame.
const gradientCache = new WeakMap();
function cacheFor(ctx) {
  let cache = gradientCache.get(ctx);
  if (!cache) { cache = new Map(); gradientCache.set(ctx, cache); }
  else if (cache.size > 900) cache.clear();
  return cache;
}
// Two-tone ramp: `base` holds flat to `split`, then `shade`.
export function celGradient(ctx, x0, x1, base, shade, split = .6) {
  const cache = cacheFor(ctx), key = `c${x0}|${x1}|${base}|${shade}|${split}`;
  let g = cache.get(key);
  if (!g) {
    g = ctx.createLinearGradient(x0, 0, x1, 0);
    g.addColorStop(0, base); g.addColorStop(split, base); g.addColorStop(split, shade); g.addColorStop(1, shade);
    cache.set(key, g);
  }
  return g;
}
// Posterized multi-band ramp along any axis: each colour holds flat until the
// midpoint to the next (hard cel bands, never a soft blend).
export function celRamp(ctx, x0, y0, x1, y1, stops) {
  const cache = cacheFor(ctx);
  let key = `r${x0}|${y0}|${x1}|${y1}`;
  for (const [at, colour] of stops) key += `|${at}${colour}`;
  let g = cache.get(key);
  if (!g) {
    g = ctx.createLinearGradient(x0, y0, x1, y1);
    stops.forEach(([at, colour], i) => {
      if (i) { const mid = (stops[i - 1][0] + at) / 2; g.addColorStop(mid, stops[i - 1][1]); g.addColorStop(mid, colour); }
      else g.addColorStop(at, colour);
    });
    g.addColorStop(stops[stops.length - 1][0], stops[stops.length - 1][1]);
    cache.set(key, g);
  }
  return g;
}
// Soft radial glow (lanterns, auras, rarity light). Cached like the ramps.
export function glowGradient(ctx, r, colour, alpha = .5) {
  const cache = cacheFor(ctx), key = `g${r}|${colour}|${alpha}`;
  let g = cache.get(key);
  if (!g) {
    g = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
    g.addColorStop(0, rgba(colour, alpha)); g.addColorStop(.45, rgba(colour, alpha * .45)); g.addColorStop(1, rgba(colour, 0));
    cache.set(key, g);
  }
  return g;
}

// ---------------------------------------------------------------------------
// Path helpers in part-local units, shared so every rig inks the same way.
export const INK = '#10131b';
export function poly(ctx, pts) { ctx.beginPath(); for (let i = 0; i < pts.length; i++) i ? ctx.lineTo(pts[i][0], pts[i][1]) : ctx.moveTo(pts[i][0], pts[i][1]); ctx.closePath(); }
export function fillStroke(ctx, fill, stroke = INK, width = .55) {
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.lineJoin = 'round'; ctx.stroke(); }
}
export function stroke(ctx, pts, colour, width = .5, cap = 'round') {
  ctx.beginPath(); for (let i = 0; i < pts.length; i++) i ? ctx.lineTo(pts[i][0], pts[i][1]) : ctx.moveTo(pts[i][0], pts[i][1]);
  ctx.strokeStyle = colour; ctx.lineWidth = width; ctx.lineCap = cap; ctx.lineJoin = 'round'; ctx.stroke();
}
export function capsule(ctx, w0, w1, y0, y1) {
  ctx.beginPath(); ctx.moveTo(-w0 / 2, y0); ctx.quadraticCurveTo(0, y0 - w0 * .45, w0 / 2, y0);
  ctx.lineTo(w1 / 2, y1); ctx.quadraticCurveTo(0, y1 + w1 * .45, -w1 / 2, y1); ctx.closePath();
}
export function dot(ctx, x, y, r, colour) { ctx.fillStyle = colour; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); }

// ---------------------------------------------------------------------------
// Springs. A critically damped follower: secondary motion that trails the body
// and settles without ringing forever. dt in ms; stable at any frame rate.
export class Spring {
  constructor(value = 0, stiffness = 90, damping = null) {
    this.value = value; this.velocity = 0; this.stiffness = stiffness;
    this.damping = damping ?? 2 * Math.sqrt(stiffness) * .82;
  }
  step(target, dt) {
    let t = clamp(dt || 0, 0, 64) / 1000;
    // Sub-step long frames so a stall never launches the cloth.
    while (t > 0) {
      const h = Math.min(t, 1 / 90);
      const accel = (target - this.value) * this.stiffness - this.velocity * this.damping;
      this.velocity += accel * h; this.value += this.velocity * h; t -= h;
    }
    return this.value;
  }
  kick(velocity) { this.velocity += velocity; }
  snap(value) { this.value = value; this.velocity = 0; }
}

// Tracks how a figure is actually moving on screen (px/s) plus any knockback
// the director has applied, and exposes the smoothed lean and trail every rig
// reads for cloth, hair and body sway. The stage moves figures with CSS, so
// this is fed the figure box position, not the rig root.
export class MotionTracker {
  constructor() {
    this.x = null; this.y = null; this.vx = 0; this.vy = 0; this.ix = 0; this.iy = 0;
    this.sway = new Spring(0, 60); this.bob = new Spring(0, 140);
  }
  track(x, y, dt) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return this;
    if (this.x == null || !(dt > 0)) { this.x = x; this.y = y; return this; }
    const k = ease(dt, 90), s = 1000 / Math.max(1, dt);
    const vx = clamp((x - this.x) * s, -2400, 2400), vy = clamp((y - this.y) * s, -2400, 2400);
    this.vx += (vx - this.vx) * k; this.vy += (vy - this.vy) * k;
    this.x = x; this.y = y;
    // Knockback decays over ~a quarter second.
    const d = ease(dt, 160); this.ix -= this.ix * d; this.iy -= this.iy * d;
    return this;
  }
  // A blow or a push, in px/s. Decays on its own.
  impulse(ix, iy = 0) { this.ix += ix; this.iy += iy; this.sway.kick(-ix * .004); }
  // Facing-relative forward speed in px/s, including knockback.
  forward(facing = 1) { return (this.vx + this.ix) * facing; }
  // Smoothed lean in -1..1 (forward positive) that cloth and hair trail against.
  lean(facing, dt) { return this.sway.step(clamp(this.forward(facing) / 420, -1, 1), dt); }
  // Vertical settle after landing or a heavy hit.
  settle(dt) { return this.bob.step(clamp((this.vy + this.iy) / 900, -1, 1), dt); }
}

// ---------------------------------------------------------------------------
// Weapon smear: records the weapon's base and tip each frame while a swing is
// live and paints the swept band fading toward the tail. Coordinates are canvas
// px, so the smear stays put while the body keeps moving.
export class Trail {
  constructor(size = 12) { this.points = []; this.size = size; }
  push(now, x0, y0, x1, y1) {
    const p = this.points;
    if (p.length && now - p[p.length - 1].t < 8) { const q = p[p.length - 1]; q.x0 = x0; q.y0 = y0; q.x1 = x1; q.y1 = y1; return; }
    p.push({t: now, x0, y0, x1, y1}); if (p.length > this.size) p.shift();
  }
  clear() { this.points.length = 0; }
  draw(ctx, now, colour, life = 150, alpha = .55) {
    const p = this.points.filter(q => now - q.t < life);
    this.points = p;
    if (p.length < 3) return;
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 1; i < p.length; i++) {
      const a = p[i - 1], b = p[i], k = 1 - (now - b.t) / life;
      ctx.globalAlpha = alpha * k * k;
      ctx.fillStyle = colour; ctx.beginPath();
      // Inner edge sits a third of the way up the blade: a smear, not a wall.
      const ai = [a.x0 + (a.x1 - a.x0) * .35, a.y0 + (a.y1 - a.y0) * .35], bi = [b.x0 + (b.x1 - b.x0) * .35, b.y0 + (b.y1 - b.y0) * .35];
      ctx.moveTo(ai[0], ai[1]); ctx.lineTo(a.x1, a.y1); ctx.lineTo(b.x1, b.y1); ctx.lineTo(bi[0], bi[1]); ctx.closePath(); ctx.fill();
    }
    ctx.restore();
  }
}

// ---------------------------------------------------------------------------
// Element particles owned by one actor: embers off a fire blade, frost motes,
// radiant glints. Canvas px, pooled, capped. The FX engine owns spell bolts
// and impacts; these are the ambient tells of what the actor carries.
export const ELEMENT_LOOK = Object.freeze({
  ember: {colour: '#ff8a3d', core: '#ffe2a8', rise: -38, drift: 10, life: 700, size: 1.5, glow: true},
  frost: {colour: '#a8e6ff', core: '#ffffff', rise: 14, drift: 8, life: 900, size: 1.3, glow: true},
  tide: {colour: '#5ab4ff', core: '#d8f1ff', rise: 30, drift: 4, life: 600, size: 1.2},
  gale: {colour: '#e8f3ff', core: '#ffffff', rise: -6, drift: 42, life: 450, size: 1.1, streak: true},
  stone: {colour: '#9b8a70', core: '#d1c4a8', rise: 34, drift: 6, life: 520, size: 1.2},
  arcane: {colour: '#b48cff', core: '#f1e6ff', rise: -18, drift: 12, life: 900, size: 1.3, glow: true},
  hallow: {colour: '#ffe48a', core: '#fffbe6', rise: -22, drift: 6, life: 1000, size: 1.4, glow: true},
  radiant: {colour: '#ffd166', core: '#ffffff', rise: -26, drift: 8, life: 850, size: 1.5, glow: true},
  wither: {colour: '#6b3fa0', core: '#b99be0', rise: -14, drift: 10, life: 1100, size: 2.4, smoke: true},
  mind: {colour: '#f15bb5', core: '#ffd1ee', rise: -12, drift: 10, life: 900, size: 1.3, glow: true, ring: true},
  resonant: {colour: '#7fd6e0', core: '#ffffff', rise: 0, drift: 0, life: 700, size: 1, ring: true},
  acid: {colour: '#6fd67a', core: '#d8ffd0', rise: 40, drift: 3, life: 600, size: 1.2},
  force: {colour: '#c05bd9', core: '#f9d6ff', rise: -16, drift: 14, life: 800, size: 1.3, glow: true},
  bleed: {colour: '#b3202c', core: '#ff8a8a', rise: 46, drift: 2, life: 520, size: 1.2},
  phase: {colour: '#9fe7ff', core: '#ffffff', rise: -8, drift: 18, life: 700, size: 1.2, glow: true},
  silver: {colour: '#e6edf5', core: '#ffffff', rise: -10, drift: 8, life: 600, size: 1, glow: true},
  heal: {colour: '#55d6be', core: '#e6fff8', rise: -30, drift: 6, life: 900, size: 1.4, glow: true},
});
export const ELEMENT_OF_DAMAGE = Object.freeze({fire: 'ember', cold: 'frost', lightning: 'force', thunder: 'resonant', radiant: 'radiant',
  necrotic: 'wither', force: 'force', acid: 'acid', poison: 'acid', psychic: 'mind', heal: 'heal', water: 'tide', air: 'gale'});

export class ParticlePool {
  constructor(max = 70) { this.items = []; this.max = max; }
  emit(x, y, element, count = 1, spread = 3, speed = 1) {
    const look = ELEMENT_LOOK[element]; if (!look) return;
    for (let i = 0; i < count && this.items.length < this.max; i++) {
      const a = Math.random() * TAU;
      this.items.push({x: x + Math.cos(a) * spread * Math.random(), y: y + Math.sin(a) * spread * Math.random(),
        vx: (Math.random() - .5) * look.drift * 2 * speed, vy: look.rise * (.6 + Math.random() * .6) * speed,
        age: 0, life: look.life * (.6 + Math.random() * .6), size: look.size * (.7 + Math.random() * .7), element});
    }
  }
  burst(x, y, element, count = 14, power = 90) {
    const look = ELEMENT_LOOK[element]; if (!look) return;
    for (let i = 0; i < count && this.items.length < this.max; i++) {
      const a = Math.random() * TAU, v = power * (.35 + Math.random() * .65);
      this.items.push({x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v + look.rise * .5, age: 0,
        life: look.life * (.4 + Math.random() * .4), size: look.size * (1 + Math.random()), element});
    }
  }
  step(dt) {
    const s = clamp(dt || 0, 0, 64) / 1000, items = this.items;
    let j = 0;
    for (let i = 0; i < items.length; i++) {
      const p = items[i]; p.age += dt; if (p.age >= p.life) continue;
      p.x += p.vx * s; p.y += p.vy * s; p.vx *= .985; items[j++] = p;
    }
    items.length = j;
  }
  draw(ctx, scale = 1) {
    if (!this.items.length) return;
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (const p of this.items) {
      const look = ELEMENT_LOOK[p.element], k = 1 - p.age / p.life, r = p.size * scale * (look.smoke ? 1 + (1 - k) * 1.6 : 1);
      if (look.smoke) { ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = .35 * k; }
      else { ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .85 * k; }
      if (look.ring) { ctx.strokeStyle = look.colour; ctx.lineWidth = .6 * scale; ctx.beginPath(); ctx.arc(p.x, p.y, r * (1 + (1 - k) * 2.5), 0, TAU); ctx.stroke(); continue; }
      if (look.streak) { ctx.strokeStyle = look.colour; ctx.lineWidth = r * .7; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x - p.vx * .05, p.y - p.vy * .05); ctx.stroke(); continue; }
      ctx.fillStyle = look.colour; ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, TAU); ctx.fill();
      if (look.glow) { ctx.fillStyle = look.core; ctx.beginPath(); ctx.arc(p.x, p.y, r * .45, 0, TAU); ctx.fill(); }
    }
    ctx.restore();
  }
}

// ---------------------------------------------------------------------------
// Paint queue. Parts are collected with a z and painted in order; the array is
// reused between frames so a figure does not allocate a fresh list each tick.
export class PaintQueue {
  constructor() { this.ops = []; this.n = 0; }
  reset() { this.n = 0; return this; }
  add(z, fn) {
    const op = this.ops[this.n] || (this.ops[this.n] = {z: 0, fn: null, i: 0});
    op.z = z; op.fn = fn; op.i = this.n++; return this;
  }
  run() {
    const live = this.ops.slice(0, this.n).sort((a, b) => a.z - b.z || a.i - b.i);
    for (const op of live) op.fn();
    for (let i = 0; i < this.n; i++) this.ops[i].fn = null;
    this.n = 0;
  }
}

// ---------------------------------------------------------------------------
// Frame statistics for the Actor Lab overlay and perf checks. Rigs report the
// time they spent painting; puppet-dom reports frames.
export const actorStats = {frames: 0, paintMs: 0, paints: 0, socketQueries: 0, lastFrameMs: 0, reset() {
  this.frames = 0; this.paintMs = 0; this.paints = 0; this.socketQueries = 0; this.lastFrameMs = 0;
}};
