// Stage FX: everything short-lived that a scene throws off.
//
// Ambient motes for the place (dust in a shaft, embers by a fire, mist over
// water), what a blow throws off by what it hits (blood, chips, straw, sparks,
// stone), debris when a thing breaks, footfall dust, floating numbers, and
// short flashes that feed the lighting pass. Screen px, pooled and capped.
// Presentation only.
import {clamp, lerp, TAU, rgba, mixHex, shadeHex} from './actor-core.js';
import {MATERIALS} from './stage-world.js';

const MAX = 520;
export class StageFx {
  constructor(rand = Math.random) { this.rand = rand; this.p = []; this.floats = []; this.rings = []; this.flashes = []; this.amb = []; this.ambKey = ''; this.t = 0; }
  clear() { this.p.length = 0; this.floats.length = 0; this.rings.length = 0; this.flashes.length = 0; }

  // -- ambient ---------------------------------------------------------------
  setAmbient(spec = {}, W, H, S) {
    const key = `${spec.kind}|${spec.n}|${spec.color}|${W}|${H}`;
    if (key === this.ambKey) return; this.ambKey = key; this.amb = [];
    const n = Math.round((spec.n || 0) * clamp(W * H / 520000, .5, 1.8)), r = this.rand;
    for (let i = 0; i < n; i++) this.amb.push({x: r() * W, y: r() * H, ph: r() * TAU, sp: .4 + r() * .9, sz: (.8 + r() * 1.8) * S, kind: spec.kind, color: spec.color || '#ffffff', life: r()});
    this.spec = spec;
  }
  stepAmbient(dt, W, H, S) {
    const s = dt / 1000;
    for (const a of this.amb) {
      a.ph += s * a.sp;
      switch (a.kind) {
        case 'embers': a.y -= (16 + a.sp * 16) * s * S; a.x += Math.sin(a.ph * 2) * 10 * s * S; if (a.y < H * .2) { a.y = H * (.62 + this.rand() * .34); a.x = this.rand() * W; } break;
        case 'ash': a.y += (12 + a.sp * 10) * s * S; a.x += Math.sin(a.ph) * 14 * s * S; if (a.y > H) { a.y = -4; a.x = this.rand() * W; } break;
        case 'steam': a.y -= (22 + a.sp * 20) * s * S; a.x += Math.sin(a.ph) * 8 * s * S; if (a.y < H * .3) { a.y = H * (.6 + this.rand() * .35); a.x = this.rand() * W; } break;
        case 'mist': a.x += (5 + a.sp * 6) * s * S; if (a.x > W + 80 * S) a.x = -80 * S; a.y += Math.sin(a.ph * .5) * 3 * s * S; break;
        case 'fireflies': case 'spores': a.x += Math.cos(a.ph * .9) * 16 * s * S; a.y += Math.sin(a.ph * 1.3) * 12 * s * S; if (a.x < 0) a.x = W; if (a.x > W) a.x = 0; if (a.y < H * .3) a.y = H * .8; if (a.y > H * .95) a.y = H * .4; break;
        default: a.x += Math.cos(a.ph * .6) * 6 * s * S; a.y += Math.sin(a.ph * .8) * 4 * s * S; if (a.x < 0) a.x = W; if (a.x > W) a.x = 0; if (a.y < 0) a.y = H; if (a.y > H) a.y = 0;
      }
    }
  }
  drawAmbient(ctx, S) {
    for (const a of this.amb) {
      const tw = .5 + .5 * Math.sin(a.ph * 2.2);
      ctx.save();
      switch (a.kind) {
        case 'mist': ctx.globalAlpha = .07; ctx.fillStyle = a.color; ctx.beginPath(); ctx.ellipse(a.x, a.y, 70 * S * a.sz, 16 * S * a.sz, 0, 0, TAU); ctx.fill(); break;
        case 'steam': ctx.globalAlpha = .12 * (1 - (a.y / 900) % 1) + .04; ctx.fillStyle = a.color; ctx.beginPath(); ctx.arc(a.x, a.y, a.sz * 5, 0, TAU); ctx.fill(); break;
        case 'embers': ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .35 + tw * .55; ctx.fillStyle = a.color; ctx.fillRect(a.x, a.y, a.sz * 1.3, a.sz * 1.3); break;
        case 'fireflies': case 'spores': ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .12 + tw * .6; ctx.fillStyle = a.color; ctx.beginPath(); ctx.arc(a.x, a.y, a.sz * (1.2 + tw), 0, TAU); ctx.fill(); ctx.globalAlpha *= .3; ctx.beginPath(); ctx.arc(a.x, a.y, a.sz * 4.5, 0, TAU); ctx.fill(); break;
        case 'ash': ctx.globalAlpha = .5; ctx.fillStyle = a.color; ctx.fillRect(a.x, a.y, a.sz, a.sz * .7); break;
        default: ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .1 + tw * .28; ctx.fillStyle = a.color; ctx.beginPath(); ctx.arc(a.x, a.y, a.sz, 0, TAU); ctx.fill();
      }
      ctx.restore();
    }
  }

  // -- impacts ---------------------------------------------------------------
  add(p) { if (this.p.length >= MAX) this.p.shift(); this.p.push({age: 0, rot: 0, vr: 0, g: 900, landed: false, ...p}); }
  // A blow lands on `material` at (x, y). dir: +1 = thrown right, -1 = left.
  hit(x, y, material = 'flesh', {dir = 1, power = 1, crit = false, S = 1, floorY = y + 60 * S} = {}) {
    const M = MATERIALS[material] || MATERIALS.flesh, r = this.rand, n = Math.round((10 + power * 8) * (crit ? 1.5 : 1));
    for (let i = 0; i < n; i++) {
      const a = (r() - .5) * 2.4 - (dir > 0 ? 0 : Math.PI) * 0, sp = (90 + r() * 260) * power * S, vx = dir * Math.abs(Math.cos(a)) * sp, vy = -Math.abs(Math.sin(a)) * sp * .9 - 40 * S * r();
      if (M.kind === 'blood') this.add({k: 'drop', x, y, vx, vy, size: (1.2 + r() * 2.2) * S, life: 520 + r() * 420, color: r() < .3 ? M.chunk : M.blood, floorY});
      else if (M.kind === 'spark') this.add({k: 'spark', x, y, vx: vx * 1.3, vy: vy * 1.1, size: (1 + r() * 1.4) * S, life: 260 + r() * 260, color: M.blood, g: 700});
      else if (M.kind === 'straw') this.add({k: 'straw', x, y, vx: vx * .6, vy: vy * .6, size: (2 + r() * 4) * S, life: 700 + r() * 700, color: r() < .5 ? M.blood : M.chunk, g: 260, rot: r() * TAU, vr: (r() - .5) * 9});
      else if (M.kind === 'dust') this.add({k: 'puff', x, y, vx: vx * .35, vy: vy * .3, size: (4 + r() * 6) * S, life: 520 + r() * 400, color: M.blood, g: -20});
      else this.add({k: 'chip', x, y, vx, vy, size: (1.6 + r() * 3) * S, life: 620 + r() * 500, color: r() < .5 ? M.blood : M.chunk, rot: r() * TAU, vr: (r() - .5) * 16, floorY});
    }
    this.flashes.push({x, y, r: (50 + power * 30) * S, c: M.kind === 'spark' ? '#ffe2a0' : '#ffd9a0', a: crit ? .8 : .5, age: 0, life: 150});
    this.rings.push({x, y, r: 6 * S, age: 0, life: 210, color: crit ? '#fff2c0' : '#ffffff', w: (crit ? 3 : 2) * S});
  }
  // A thing breaks: chunks by its material, tumbling and settling.
  debris(x, y, w, h, material, dir = 1, S = 1) {
    const M = MATERIALS[material] || MATERIALS.wood, r = this.rand, n = clamp(Math.round(w * h / (90 * S * S)), 10, 34);
    for (let i = 0; i < n; i++) {
      const px = x + (r() - .5) * w, py = y - r() * h;
      this.add({k: 'chunk', x: px, y: py, vx: dir * (30 + r() * 210) * S + (r() - .5) * 90 * S, vy: -(60 + r() * 260) * S, size: (2.5 + r() * 6) * S, life: 3600 + r() * 1800, color: r() < .5 ? M.blood : M.chunk,
        rot: r() * TAU, vr: (r() - .5) * 14, floorY: y + (r() - .3) * 6 * S, g: 1100, keep: true});
    }
    for (let i = 0; i < 8; i++) this.add({k: 'puff', x: x + (r() - .5) * w, y: y - r() * h * .6, vx: (r() - .5) * 60 * S, vy: -20 * r() * S, size: (7 + r() * 9) * S, life: 700 + r() * 500, color: '#b7ab99', g: -18});
    this.flashes.push({x, y: y - h * .5, r: 90 * S, c: '#ffe2b0', a: .5, age: 0, life: 220});
  }
  puff(x, y, n = 3, color = '#b7ab99', S = 1, dir = 0) {
    for (let i = 0; i < n; i++) this.add({k: 'puff', x: x + (this.rand() - .5) * 8 * S, y, vx: -dir * (10 + this.rand() * 30) * S + (this.rand() - .5) * 20 * S, vy: -(4 + this.rand() * 14) * S, size: (3 + this.rand() * 4) * S, life: 380 + this.rand() * 300, color, g: -8});
  }
  float(x, y, text, {color = '#fff2c0', crit = false, S = 1} = {}) { this.floats.push({x, y, text, color, crit, age: 0, life: crit ? 1250 : 950, S}); }
  flash(x, y, r, c, a = .6, life = 180) { this.flashes.push({x, y, r, c, a, age: 0, life}); }

  step(dt) {
    this.t += dt; const s = dt / 1000;
    for (const p of this.p) {
      p.age += dt; p.vy += p.g * s; p.x += p.vx * s; p.y += p.vy * s; p.rot += p.vr * s;
      if (p.floorY != null && p.y > p.floorY && p.vy > 0) { if (p.keep) { p.y = p.floorY; p.vy = 0; p.vx *= .4; p.vr *= .3; p.landed = true; } else { p.age = p.life; } }
      if (p.landed) { p.vx *= Math.exp(-dt / 90); p.vr *= Math.exp(-dt / 90); }
    }
    this.p = this.p.filter(p => p.age < p.life);
    for (const f of this.floats) f.age += dt;
    this.floats = this.floats.filter(f => f.age < f.life);
    for (const r of this.rings) r.age += dt; this.rings = this.rings.filter(r => r.age < r.life);
    for (const f of this.flashes) f.age += dt; this.flashes = this.flashes.filter(f => f.age < f.life);
  }
  draw(ctx, S) {
    for (const p of this.p) {
      const k = 1 - p.age / p.life, fade = p.keep ? clamp((p.life - p.age) / 700, 0, 1) : k;
      ctx.save(); ctx.globalAlpha = clamp(fade * 1.2, 0, 1);
      switch (p.k) {
        case 'drop': ctx.fillStyle = p.color; ctx.beginPath(); ctx.ellipse(p.x, p.y, p.size * .8, p.size * 1.5, Math.atan2(p.vx, -p.vy), 0, TAU); ctx.fill(); break;
        case 'spark': ctx.globalCompositeOperation = 'lighter'; ctx.strokeStyle = p.color; ctx.lineWidth = p.size; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x - p.vx * .035, p.y - p.vy * .035); ctx.stroke(); break;
        case 'straw': ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.fillStyle = p.color; ctx.fillRect(-p.size, -p.size * .12, p.size * 2, p.size * .24); break;
        case 'puff': ctx.globalAlpha *= .4; ctx.fillStyle = p.color; ctx.beginPath(); ctx.arc(p.x, p.y, p.size * (1.2 - k * .5 + .3), 0, TAU); ctx.fill(); break;
        default: ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.fillStyle = p.color; ctx.fillRect(-p.size, -p.size * .55, p.size * 2, p.size * 1.1); ctx.strokeStyle = 'rgba(10,12,20,.6)'; ctx.lineWidth = S * .8; ctx.strokeRect(-p.size, -p.size * .55, p.size * 2, p.size * 1.1);
      }
      ctx.restore();
    }
    for (const r of this.rings) { const k = r.age / r.life; ctx.save(); ctx.globalAlpha = (1 - k) * .8; ctx.strokeStyle = r.color; ctx.lineWidth = r.w * (1 - k * .7); ctx.beginPath(); ctx.ellipse(r.x, r.y, r.r + k * 34 * S, (r.r + k * 34 * S) * .55, 0, 0, TAU); ctx.stroke(); ctx.restore(); }
    for (const f of this.floats) {
      const k = f.age / f.life, up = (1 - Math.pow(1 - k, 2)) * 46 * f.S, sc = f.crit ? 1.15 + (k < .12 ? (1 - k / .12) * .5 : 0) : 1;
      ctx.save(); ctx.globalAlpha = k > .7 ? (1 - k) / .3 : 1; ctx.translate(f.x, f.y - up); ctx.scale(sc, sc);
      ctx.font = `700 ${(f.crit ? 24 : 18) * f.S}px Cinzel, Georgia, serif`; ctx.textAlign = 'center'; ctx.lineWidth = 4 * f.S; ctx.strokeStyle = 'rgba(8,10,18,.9)'; ctx.lineJoin = 'round';
      ctx.strokeText(f.text, 0, 0); ctx.fillStyle = f.color; ctx.fillText(f.text, 0, 0); ctx.restore();
    }
  }
}

// One cut on a body, in Clean Cel: an ink outline, the wound itself (blood, straw, spark or char by material),
// and a light edge on the lit side. Blood runs a little, then dries. `x, y` is its centre, `len` its length in px.
export function paintWound(c, wd, {x, y, len, S = 1, material = 'flesh', bodyRot = 0} = {}) {
  const mat = MATERIALS[material] || MATERIALS.flesh, a = wd.ang + bodyRot, dx = Math.cos(a) * len / 2, dy = Math.sin(a) * len / 2, fresh = clamp(1 - wd.age / 9000, 0, 1);
  c.save(); c.lineCap = 'round';
  const core = mat.kind === 'blood' ? '#7c1520' : mat.kind === 'straw' ? '#e6cc74' : mat.kind === 'spark' ? '#fff2c0' : '#1c1410';
  c.strokeStyle = 'rgba(12,14,22,.75)'; c.lineWidth = 5.4 * S; c.beginPath(); c.moveTo(x - dx, y - dy); c.lineTo(x + dx, y + dy); c.stroke();
  c.strokeStyle = core; c.lineWidth = 3.4 * S * (wd.kind === 'gash' ? 1.4 : 1); c.beginPath(); c.moveTo(x - dx, y - dy); c.lineTo(x + dx, y + dy); c.stroke();
  c.strokeStyle = mat.kind === 'blood' ? `rgba(255,120,110,${(.55 * fresh + .1).toFixed(3)})` : 'rgba(255,255,255,.4)'; c.lineWidth = 1.1 * S; c.beginPath(); c.moveTo(x - dx - S, y - dy - S); c.lineTo(x + dx - S, y + dy - S); c.stroke();
  if (mat.kind === 'blood' && wd.age < 14000) {
    const run = Math.min(len * .9, wd.age * .01 * S), x1 = x + dx * .6;
    c.strokeStyle = `rgba(150,24,36,${(.9 * fresh + .15).toFixed(3)})`; c.lineWidth = 2 * S; c.beginPath(); c.moveTo(x1, y + dy * .6); c.lineTo(x1 + Math.sin((wd.seed || 0) * 9) * 1.5 * S, y + dy * .6 + run); c.stroke();
  }
  c.restore();
}
