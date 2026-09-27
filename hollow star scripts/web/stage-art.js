// Stage art: the drawing toolkit for painted sets, props and doors.
//
// Everything is canvas 2D, seeded, and drawn in Clean Cel (SPRITE_GUIDE.md):
// one ink weight, a flat base and one shade band, details as shapes. What sets
// a place apart from the paper dolls standing in it is depth: layered haze,
// perspective floors, and the lighting pass the stage lays over both.
//
// K is the kit every painter receives: {W, H, S, rand, cam, ink}. S = H / 500
// scales strokes and sizes to the scene; rand() is the set's seeded stream.
import {mixHex, shadeHex, lightHex, rgba, TAU, clamp, lerp} from './actor-core.js';

export const INK = '#0e121c';
export const kit = (W, H, rand, cam) => ({W, H, S: H / 500, rand, cam, ink: INK});
const r2 = (a, b, rand) => a + (b - a) * rand();

// ---------------------------------------------------------------------------
// Primitives.
export function vgrad(ctx, y0, y1, stops) {
  const g = ctx.createLinearGradient(0, y0, 0, y1);
  stops.forEach(([at, colour]) => g.addColorStop(at, colour)); return g;
}
export function hgrad(ctx, x0, x1, stops) {
  const g = ctx.createLinearGradient(x0, 0, x1, 0);
  stops.forEach(([at, colour]) => g.addColorStop(at, colour)); return g;
}
export function glow(ctx, x, y, r, colour, alpha = .5) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, rgba(colour, alpha)); g.addColorStop(.4, rgba(colour, alpha * .4)); g.addColorStop(1, rgba(colour, 0));
  ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
}
export function poly(ctx, pts) { ctx.beginPath(); pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath(); }
export function ink(ctx, K, width = 1.5) { ctx.strokeStyle = K.ink; ctx.lineWidth = width * K.S; ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.stroke(); }
export function inkPoly(ctx, K, pts, fill, width = 1.5) { poly(ctx, pts); if (fill) { ctx.fillStyle = fill; ctx.fill(); } if (width) ink(ctx, K, width); }
export function inkRect(ctx, K, x, y, w, h, fill, width = 1.5) { ctx.beginPath(); ctx.rect(x, y, w, h); if (fill) { ctx.fillStyle = fill; ctx.fill(); } if (width) ink(ctx, K, width); }
export function ellipse(ctx, x, y, rx, ry, fill, stroke = null, width = 1.4, K = null) {
  ctx.beginPath(); ctx.ellipse(x, y, Math.max(.01, rx), Math.max(.01, ry), 0, 0, TAU);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); } if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width * (K?.S || 1); ctx.stroke(); }
}
// A block with a cel shade band down its dark side and a light edge on top.
export function block(ctx, K, x, y, w, h, base, {shade = .3, side = 'right', lit = .18, ink: w0 = 1.5, band = .24} = {}) {
  ctx.beginPath(); ctx.rect(x, y, w, h); ctx.fillStyle = base; ctx.fill();
  ctx.fillStyle = shadeHex(base, shade);
  side === 'right' ? ctx.fillRect(x + w * (1 - band), y, w * band, h) : ctx.fillRect(x, y, w * band, h);
  ctx.fillStyle = lightHex(base, lit); ctx.fillRect(x, y, w, Math.max(1, h * .07));
  if (w0) { ctx.beginPath(); ctx.rect(x, y, w, h); ink(ctx, K, w0); }
}
export function noiseDots(ctx, K, x, y, w, h, colour, n, size = 1.2, alpha = .35) {
  ctx.save(); ctx.globalAlpha = alpha; ctx.fillStyle = colour;
  for (let i = 0; i < n; i++) { const s = size * K.S * (.5 + K.rand()); ctx.fillRect(x + K.rand() * w, y + K.rand() * h, s, s); }
  ctx.restore();
}
export function ridge(ctx, K, baseY, amp, colour, {step = 26, from = -20, to = K.W + 20, shade = null} = {}) {
  const pts = [[from, K.H + 4]]; let y = baseY;
  for (let x = from; x <= to + step; x += step * K.S) { y = clamp(y + (K.rand() - .5) * amp * K.S * 1.6, baseY - amp * K.S, baseY + amp * K.S); pts.push([x, y]); }
  pts.push([to + 20, K.H + 4]); poly(ctx, pts); ctx.fillStyle = colour; ctx.fill();
  if (shade) { ctx.save(); ctx.clip(); ctx.fillStyle = shade; ctx.fillRect(0, baseY, K.W, K.H); ctx.restore(); }
}
export function pine(ctx, K, x, base, h, colour, shade) {
  const w = h * .36;
  ctx.fillStyle = shadeHex(colour, .45); ctx.fillRect(x - w * .06, base - h * .12, w * .12, h * .14);
  for (let i = 0; i < 4; i++) {
    const y1 = base - h * (.1 + i * .22), y0 = y1 - h * .34, ww = w * (1 - i * .2);
    poly(ctx, [[x, y0], [x + ww * .5, y1], [x - ww * .5, y1]]); ctx.fillStyle = colour; ctx.fill();
    poly(ctx, [[x, y0], [x + ww * .5, y1], [x + ww * .1, y1]]); ctx.fillStyle = shade || shadeHex(colour, .35); ctx.fill();
  }
}
export function tree(ctx, K, x, base, h, colour, trunk = '#4a3626') {
  const s = K.S;
  poly(ctx, [[x - h * .04, base], [x - h * .025, base - h * .5], [x + h * .025, base - h * .5], [x + h * .045, base]]); ctx.fillStyle = trunk; ctx.fill(); ink(ctx, K, 1.2);
  for (const [dx, dy, r] of [[0, -.66, .3], [-.22, -.52, .22], [.22, -.5, .24], [.05, -.85, .2]]) {
    ellipse(ctx, x + dx * h, base + dy * h, r * h * .9, r * h * .78, colour);
  }
  ctx.save(); ctx.beginPath(); ctx.ellipse(x, base - h * .68, h * .5, h * .5, 0, 0, TAU); ctx.clip();
  ctx.fillStyle = rgba(shadeHex(colour, .4), .55); ctx.fillRect(x + h * .05, base - h * 1.2, h, h); ctx.restore();
  ctx.lineWidth = s;
}

// ---------------------------------------------------------------------------
// Sky. Gradient, an optional sun/moon with halo, stars, flat cel clouds.
export function sky(ctx, K, {top, mid, bot, y1 = K.H * .55, sun = null, stars = 0, clouds = 0, cloud = '#ffffff', cloudAlpha = .22}) {
  ctx.fillStyle = vgrad(ctx, 0, y1, [[0, top], [.55, mid], [1, bot]]); ctx.fillRect(0, 0, K.W, y1 + 2);
  for (let i = 0; i < stars; i++) { ctx.globalAlpha = .25 + K.rand() * .6; ctx.fillStyle = '#fff6dc'; const s = (.6 + K.rand() * 1.4) * K.S; ctx.fillRect(K.rand() * K.W, K.rand() * y1 * .7, s, s); }
  ctx.globalAlpha = 1;
  if (sun) {
    glow(ctx, sun.x * K.W, sun.y * K.H, sun.r * K.S * 5, sun.halo || sun.color, .5);
    ctx.fillStyle = sun.color; ctx.beginPath(); ctx.arc(sun.x * K.W, sun.y * K.H, sun.r * K.S, 0, TAU); ctx.fill();
    if (sun.crescent) { ctx.fillStyle = mid; ctx.beginPath(); ctx.arc(sun.x * K.W + sun.r * K.S * .35, sun.y * K.H - sun.r * K.S * .1, sun.r * K.S * .92, 0, TAU); ctx.fill(); }
  }
  for (let i = 0; i < clouds; i++) {
    const cx = K.rand() * K.W, cy = y1 * (.12 + K.rand() * .5), w = (90 + K.rand() * 170) * K.S;
    ctx.fillStyle = rgba(cloud, cloudAlpha);
    for (let j = 0; j < 4; j++) ellipse(ctx, cx + (j - 1.5) * w * .22, cy + Math.sin(j * 2) * 5 * K.S, w * .2, w * .07, rgba(cloud, cloudAlpha));
  }
}

// ---------------------------------------------------------------------------
// Buildings. A house is a body, a roof and windows; kind picks the walling.
export function windowPane(ctx, K, x, y, w, h, {lit = 0, frame = '#3a2c22', glass = '#1c2434', shutter = null, arch = false} = {}) {
  ctx.beginPath(); arch ? (ctx.moveTo(x, y + h), ctx.lineTo(x, y + w / 2), ctx.arc(x + w / 2, y + w / 2, w / 2, Math.PI, 0), ctx.lineTo(x + w, y + h), ctx.closePath()) : ctx.rect(x, y, w, h);
  ctx.fillStyle = lit ? mixHex(glass, '#ffd27a', lit) : glass; ctx.fill(); ink(ctx, K, 1.3);
  if (lit) { ctx.save(); ctx.clip(); ctx.fillStyle = rgba('#fff2c0', .35 * lit); ctx.fillRect(x, y, w * .45, h); ctx.restore(); }
  ctx.strokeStyle = frame; ctx.lineWidth = 1.6 * K.S; ctx.beginPath(); ctx.moveTo(x + w / 2, y + (arch ? w / 2 : 0)); ctx.lineTo(x + w / 2, y + h); ctx.moveTo(x, y + h * .5); ctx.lineTo(x + w, y + h * .5); ctx.stroke();
  if (shutter) { for (const sx of [x - w * .42, x + w * 1.02]) { inkRect(ctx, K, sx, y, w * .4, h, shutter, 1.1); ctx.strokeStyle = shadeHex(shutter, .3); ctx.lineWidth = K.S; ctx.beginPath(); for (let i = 1; i < 4; i++) { ctx.moveTo(sx, y + h * i / 4); ctx.lineTo(sx + w * .4, y + h * i / 4); } ctx.stroke(); } }
}
export function roof(ctx, K, x, y, w, h, colour, {style = 'gable', overhang = .06, rows = 5} = {}) {
  const o = w * overhang, s = K.S;
  if (style === 'gable') {
    const pts = [[x - o, y], [x + w / 2, y - h], [x + w + o, y]];
    inkPoly(ctx, K, pts, colour, 1.6);
    ctx.save(); poly(ctx, pts); ctx.clip();
    ctx.fillStyle = shadeHex(colour, .32); ctx.beginPath(); ctx.moveTo(x + w / 2, y - h); ctx.lineTo(x + w + o, y); ctx.lineTo(x + w / 2, y); ctx.fill();
    ctx.strokeStyle = rgba(INK, .32); ctx.lineWidth = s; ctx.beginPath();
    for (let i = 1; i <= rows; i++) { const yy = y - h * i / (rows + 1); ctx.moveTo(x - o, yy); ctx.lineTo(x + w + o, yy); } ctx.stroke(); ctx.restore();
  } else {
    inkRect(ctx, K, x - o, y - h, w + o * 2, h, colour, 1.6);
    ctx.fillStyle = shadeHex(colour, .3); ctx.fillRect(x - o, y - h * .3, w + o * 2, h * .3);
  }
}
export function house(ctx, K, {x, base, w, h, kind = 'timber', wall = '#b9a487', trim = '#4a3626', roofC = '#7a3f34', roofH = null, floors = 2, lit = .4, style = 'gable',
  chimney = false, shutter = '#5d4a3a', door = false, seed = 0}) {
  const s = K.S, top = base - h, rh = roofH ?? w * .3;
  if (chimney) { inkRect(ctx, K, x + w * .68, top - rh * 1.0, w * .1, rh * .9, '#6a5a52', 1.3); }
  const body = kind === 'stone' ? mixHex(wall, '#8b8f99', .5) : kind === 'brick' ? mixHex(wall, '#9a5a44', .6) : wall;
  block(ctx, K, x, top, w, h, body, {shade: .3, band: .2});
  ctx.save(); ctx.beginPath(); ctx.rect(x, top, w, h); ctx.clip();
  ctx.fillStyle = vgrad(ctx, top, base, [[0, 'rgba(255,255,255,.07)'], [1, 'rgba(0,0,0,.2)']]); ctx.fillRect(x, top, w, h);
  if (kind === 'timber') {
    ctx.fillStyle = trim; const fh = h / floors;
    for (let f = 0; f <= floors; f++) ctx.fillRect(x, top + f * fh - 2 * s, w, 4 * s);
    for (const px of [0, .5, 1]) ctx.fillRect(x + w * px - (px === 1 ? 5 * s : px === 0 ? 0 : 2.5 * s), top, 5 * s, h);
    ctx.strokeStyle = trim; ctx.lineWidth = 3 * s; ctx.beginPath();
    for (let f = 0; f < floors; f++) { ctx.moveTo(x + 4 * s, top + f * fh + 4 * s); ctx.lineTo(x + w * .5 - 3 * s, top + (f + 1) * fh - 3 * s); ctx.moveTo(x + w - 4 * s, top + f * fh + 4 * s); ctx.lineTo(x + w * .5 + 3 * s, top + (f + 1) * fh - 3 * s); }
    ctx.stroke();
  } else {
    ctx.strokeStyle = rgba(INK, .22); ctx.lineWidth = s; ctx.beginPath();
    const bh = (kind === 'brick' ? 7 : 13) * s;
    for (let yy = top + bh, i = 0; yy < base; yy += bh, i++) { ctx.moveTo(x, yy); ctx.lineTo(x + w, yy); for (let xx = x + ((i % 2) * bh * 1.4); xx < x + w; xx += bh * 2.8) { ctx.moveTo(xx, yy - bh); ctx.lineTo(xx, yy); } }
    ctx.stroke();
  }
  ctx.restore();
  const fh = h / floors;
  for (let f = 0; f < floors; f++) {
    const n = Math.max(1, Math.round(w / (58 * s)));
    for (let i = 0; i < n; i++) {
      const ww = 15 * s, cx = x + w * (i + .5) / n - ww / 2, cy = top + f * fh + fh * .26;
      if (door && f === floors - 1 && i === Math.floor(n / 2)) continue;
      windowPane(ctx, K, cx, cy, ww, ww * 1.35, {lit: K.rand() < lit ? .45 + K.rand() * .55 : 0, shutter: kind === 'timber' || kind === 'brick' ? shutter : null, frame: trim});
    }
  }
  if (door) { const dw = 20 * s, dh = 36 * s; inkRect(ctx, K, x + w * .5 - dw / 2, base - dh, dw, dh, lightHex(trim, .12), 1.4); ctx.fillStyle = '#d6b36a'; ctx.beginPath(); ctx.arc(x + w * .5 + dw * .25, base - dh * .45, 1.3 * s, 0, TAU); ctx.fill(); }
  roof(ctx, K, x, top, w, rh, roofC, {style});
}

// ---------------------------------------------------------------------------
// Stone. Ashlar courses with offset joints and a light edge on each block.
export function stoneWall(ctx, K, x0, y0, x1, y1, base, {course = 22, seed = 0, moss = 0, dark = .28, tone = .07, rows = null, joint = .3} = {}) {
  const s = K.S, ch = course * s;
  ctx.save(); ctx.beginPath(); ctx.rect(x0, y0, x1 - x0, y1 - y0); ctx.clip();
  ctx.fillStyle = base; ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  let i = 0;
  for (let y = y0; y < y1; y += ch, i++) {
    let x = x0 - (i % 2) * ch * 1.1 - K.rand() * ch;
    while (x < x1) {
      const w = ch * (1.7 + K.rand() * 1.8);
      const shade = K.rand(), c = shade < .5 ? mixHex(base, '#ffffff', tone * (.4 + shade)) : mixHex(base, '#000000', tone * (shade - .3));
      ctx.fillStyle = c; ctx.fillRect(x + s, y + s, w - 2 * s, ch - 2 * s);
      ctx.fillStyle = rgba('#ffffff', .1); ctx.fillRect(x + s, y + s, w - 2 * s, 2 * s);
      ctx.fillStyle = rgba('#000000', .16); ctx.fillRect(x + s, y + ch - 3 * s, w - 2 * s, 2 * s);
      if (moss && K.rand() < moss) { ctx.fillStyle = rgba('#4f7a3c', .45); ctx.fillRect(x + s, y + ch * .55, w - 2 * s, ch * .4); }
      x += w;
    }
    ctx.strokeStyle = rgba(INK, joint); ctx.lineWidth = s; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
  }
  ctx.fillStyle = vgrad(ctx, y0, y1, [[0, 'rgba(0,0,0,.28)'], [.5, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,.34)']]); ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  ctx.restore();
}
export function planksWall(ctx, K, x0, y0, x1, y1, base, {plank = 16, dark = .25} = {}) {
  const s = K.S; ctx.save(); ctx.beginPath(); ctx.rect(x0, y0, x1 - x0, y1 - y0); ctx.clip();
  for (let x = x0; x < x1; x += plank * s) {
    const c = mixHex(base, K.rand() < .5 ? '#000000' : '#ffffff', .05 + K.rand() * .08); ctx.fillStyle = c; ctx.fillRect(x, y0, plank * s, y1 - y0);
    ctx.fillStyle = rgba(INK, .3); ctx.fillRect(x, y0, s, y1 - y0);
    ctx.strokeStyle = rgba(INK, .16); ctx.lineWidth = s; ctx.beginPath(); const gy = y0 + K.rand() * (y1 - y0);
    ctx.moveTo(x + plank * s * .3, gy); ctx.lineTo(x + plank * s * .3, gy + 30 * s); ctx.stroke();
  }
  ctx.fillStyle = vgrad(ctx, y0, y1, [[0, 'rgba(0,0,0,.3)'], [.6, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,.3)']]); ctx.fillRect(x0, y0, x1 - x0, y1 - y0); ctx.restore();
}
export function beam(ctx, K, x0, y0, x1, y1, thick, colour) {
  const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy) || 1, nx = -dy / len * thick / 2, ny = dx / len * thick / 2;
  inkPoly(ctx, K, [[x0 + nx, y0 + ny], [x1 + nx, y1 + ny], [x1 - nx, y1 - ny], [x0 - nx, y0 - ny]], colour, 1.4);
  ctx.strokeStyle = rgba('#fff', .1); ctx.lineWidth = K.S; ctx.beginPath(); ctx.moveTo(x0 + nx * .5, y0 + ny * .5); ctx.lineTo(x1 + nx * .5, y1 + ny * .5); ctx.stroke();
}
export function arch(ctx, K, x, base, w, h, stone, {dark = '#06080d', keystone = true, inner = null} = {}) {
  const r = w / 2, p = new Path2D();
  p.moveTo(x - r, base); p.lineTo(x - r, base - h + r); p.arc(x, base - h + r, r, Math.PI, 0); p.lineTo(x + r, base);
  ctx.save(); ctx.fillStyle = inner || dark; ctx.fill(p);
  ctx.lineWidth = 7 * K.S; ctx.strokeStyle = stone; ctx.stroke(p);
  ctx.lineWidth = K.S * 1.4; ctx.strokeStyle = K.ink; ctx.stroke(p);
  ctx.restore();
  if (keystone) { inkPoly(ctx, K, [[x - r * .16, base - h - 3 * K.S], [x + r * .16, base - h - 3 * K.S], [x + r * .1, base - h + 9 * K.S], [x - r * .1, base - h + 9 * K.S]], lightHex(stone, .1), 1.2); }
}
export function pillar(ctx, K, x, base, w, h, stone, {cap = true, fluted = true} = {}) {
  const s = K.S;
  block(ctx, K, x - w / 2, base - h, w, h, stone, {band: .3, shade: .35});
  if (fluted) { ctx.strokeStyle = rgba(INK, .22); ctx.lineWidth = s; ctx.beginPath(); for (let i = 1; i < 4; i++) { ctx.moveTo(x - w / 2 + w * i / 4, base - h); ctx.lineTo(x - w / 2 + w * i / 4, base); } ctx.stroke(); }
  if (cap) { block(ctx, K, x - w * .68, base - h - 10 * s, w * 1.36, 10 * s, lightHex(stone, .06), {band: .2}); block(ctx, K, x - w * .68, base - 9 * s, w * 1.36, 9 * s, shadeHex(stone, .08), {band: .2}); }
}

// ---------------------------------------------------------------------------
// Floors. A perspective plane from `y0` (far edge) to `y1` (near edge); rows
// grow toward the viewer and columns fan out from the vanishing point.
export function floorPlane(ctx, K, y0, y1, kind, pal, {conv = .7, seed = 0, tint = null} = {}) {
  const {W} = K, s = K.S, cx = W / 2;
  ctx.save(); ctx.beginPath(); ctx.rect(0, y0, W, y1 - y0 + 2); ctx.clip();
  ctx.fillStyle = vgrad(ctx, y0, y1, [[0, shadeHex(pal.floor, .3)], [.5, pal.floor], [1, lightHex(pal.floor, .04)]]); ctx.fillRect(0, y0, W, y1 - y0 + 2);
  const rowsN = kind === 'plank' || kind === 'metal' ? 26 : 22;
  const rowAt = i => y0 + (y1 - y0) * Math.pow(i / rowsN, 1.75);
  const scaleAt = y => lerp(conv, 1, (y - y0) / (y1 - y0));
  if (kind === 'cobble' || kind === 'flag' || kind === 'tile') {
    const base = kind === 'cobble' ? 30 * s : kind === 'flag' ? 78 * s : 64 * s;
    for (let i = 0; i < rowsN; i++) {
      const ya = rowAt(i), yb = rowAt(i + 1), sa = scaleAt(ya), sb = scaleAt(yb), cw = base * sa;
      const off = (i % 2) * (kind === 'tile' ? 0 : cw * .5);
      for (let x = cx - W; x < cx + W; x += cw) {
        const xa = cx + (x - cx) + off; const xb = xa + cw;
        const jitter = (K.rand() - .5) * .12, checker = kind === 'tile' ? ((Math.round((x - cx) / cw) + i) % 2 ? .1 : -.04) : 0;
        const c = mixHex(pal.floor, jitter > 0 ? pal.floorLit : pal.floorShade, Math.max(0, Math.abs(jitter) * 2.4 + checker));
        const g = kind === 'cobble' ? 1.6 * sa * s : s;
        ctx.beginPath();
        if (kind === 'cobble') { const rx = (xb - xa) / 2 - g, ry = (yb - ya) / 2 - g * .4; ctx.ellipse((xa + xb) / 2, (ya + yb) / 2, Math.max(.5, rx * 1.02), Math.max(.5, ry * 1.1), 0, 0, TAU); }
        else ctx.rect(xa + g, ya + g * .5, xb - xa - g * 2, yb - ya - g);
        ctx.fillStyle = c; ctx.fill();
        if (kind === 'cobble') { ctx.fillStyle = rgba('#ffffff', .07); ctx.beginPath(); ctx.ellipse((xa + xb) / 2 - cw * .05, ya + (yb - ya) * .32, Math.max(.4, (xb - xa) * .28), Math.max(.4, (yb - ya) * .16), 0, 0, TAU); ctx.fill(); }
        else { ctx.fillStyle = rgba('#ffffff', .05); ctx.fillRect(xa + g, ya + g * .5, xb - xa - g * 2, Math.max(1, (yb - ya) * .16)); }
      }
    }
  } else if (kind === 'plank') {
    const n = 34;
    for (let i = -n; i <= n; i++) {
      const xa = cx + i * 46 * s * conv, xb = cx + (i + 1) * 46 * s * conv, xa2 = cx + i * 46 * s * 1.9 * (1 + conv) / 2, xb2 = cx + (i + 1) * 46 * s * 1.9 * (1 + conv) / 2;
      const c = mixHex(pal.floor, K.rand() < .5 ? '#000000' : '#ffffff', .04 + K.rand() * .08);
      poly(ctx, [[xa, y0], [xb, y0], [xb2, y1], [xa2, y1]]); ctx.fillStyle = c; ctx.fill();
      ctx.strokeStyle = rgba(INK, .35); ctx.lineWidth = s * 1.2; ctx.beginPath(); ctx.moveTo(xa, y0); ctx.lineTo(xa2, y1); ctx.stroke();
      for (let k = 0; k < 3; k++) { const t = K.rand() * .9 + .05, yy = lerp(y0, y1, Math.pow(t, 1.4)), xx = lerp(xa, xa2, Math.pow(t, 1.4)), ww = lerp(xb - xa, xb2 - xa2, Math.pow(t, 1.4)); ctx.strokeStyle = rgba(INK, .26); ctx.beginPath(); ctx.moveTo(xx, yy); ctx.lineTo(xx + ww, yy); ctx.stroke(); }
    }
  } else if (kind === 'metal') {
    for (let i = 0; i < rowsN; i++) {
      const ya = rowAt(i), yb = rowAt(i + 1);
      ctx.fillStyle = i % 2 ? rgba('#ffffff', .05) : rgba('#000000', .1); ctx.fillRect(0, ya, W, yb - ya);
      ctx.strokeStyle = rgba(INK, .55); ctx.lineWidth = s * 1.2; ctx.beginPath(); ctx.moveTo(0, ya); ctx.lineTo(W, ya); ctx.stroke();
    }
    for (let i = -14; i <= 14; i++) { ctx.strokeStyle = rgba(INK, .35); ctx.lineWidth = s; ctx.beginPath(); ctx.moveTo(cx + i * 40 * s * conv, y0); ctx.lineTo(cx + i * 40 * s * 1.7, y1); ctx.stroke(); }
  } else if (kind === 'dirt') {
    for (let i = 0; i < 260; i++) {
      const t = Math.pow(K.rand(), .8), y = lerp(y0, y1, t), sz = (2 + K.rand() * 9) * s * lerp(.4, 1.3, t);
      ctx.fillStyle = rgba(K.rand() < .5 ? pal.floorShade : pal.floorLit, .3 + K.rand() * .3); ctx.beginPath(); ctx.ellipse(K.rand() * W, y, sz * 1.5, sz * .5, 0, 0, TAU); ctx.fill();
    }
    for (let i = 0; i < 46; i++) { const t = K.rand(), y = lerp(y0, y1, t), sz = (2 + K.rand() * 4) * s * lerp(.5, 1.4, t); ellipse(ctx, K.rand() * W, y, sz, sz * .55, mixHex(pal.floor, '#8a8a88', .25), rgba(INK, .5), .9, K); }
  } else if (kind === 'water') {
    for (let i = 0; i < rowsN * 2; i++) {
      const t = i / (rowsN * 2), y = lerp(y0, y1, Math.pow(t, 1.5)), a = .04 + t * .1;
      ctx.strokeStyle = rgba(K.rand() < .5 ? pal.floorLit : '#000000', a * 2.4); ctx.lineWidth = s * (1 + t * 2); ctx.beginPath();
      for (let x = 0; x <= W; x += 24 * s) ctx.lineTo(x, y + Math.sin(x * .02 + i) * 2 * s * (1 + t)); ctx.stroke();
    }
  }
  ctx.restore();
}
// A flat pool of light or shadow on the ground, in perspective.
export function groundPool(ctx, x, y, rx, ry, colour, alpha = .3) {
  ctx.save(); ctx.translate(x, y); ctx.scale(1, ry / rx);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx); g.addColorStop(0, rgba(colour, alpha)); g.addColorStop(1, rgba(colour, 0));
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, rx, 0, TAU); ctx.fill(); ctx.restore();
}

// ---------------------------------------------------------------------------
// Props. Each draws into a box with its feet at (0,0) and extents (w, h) in
// px; `st` is {open, dmg (0..1 cut), t (seconds)}. The same painters serve
// the set's decor and the room's interactive objects.
const crack = (ctx, K, w, h, dmg, seed = 1) => {
  if (!(dmg > .04)) return;
  ctx.save(); ctx.strokeStyle = rgba(INK, .55 + dmg * .3); ctx.lineWidth = K.S * 1.1; ctx.beginPath();
  const n = Math.ceil(dmg * 5);
  for (let i = 0; i < n; i++) { const a = ((seed * 7 + i * 3.1) % 1), x = -w * .4 + a * w * .8; ctx.moveTo(x, -h * (.85 - i * .08)); ctx.lineTo(x + w * .08, -h * (.6 - i * .05)); ctx.lineTo(x - w * .05, -h * (.4 - i * .03)); }
  ctx.stroke(); ctx.restore();
};
function hoop(ctx, K, y, w, colour) { ctx.fillStyle = colour; ctx.fillRect(-w / 2, y, w, 3 * K.S); ctx.strokeStyle = K.ink; ctx.lineWidth = K.S; ctx.strokeRect(-w / 2, y, w, 3 * K.S); }
export const PROP_ART = {
  crate(ctx, K, w, h, st) {
    block(ctx, K, -w / 2, -h, w, h, '#a17a4d', {band: .22});
    ctx.strokeStyle = '#5c4229'; ctx.lineWidth = 3 * K.S; ctx.strokeRect(-w / 2 + 3 * K.S, -h + 3 * K.S, w - 6 * K.S, h - 6 * K.S);
    ctx.beginPath(); ctx.moveTo(-w / 2 + 3 * K.S, -h + 3 * K.S); ctx.lineTo(w / 2 - 3 * K.S, -3 * K.S); ctx.stroke();
    ctx.strokeStyle = K.ink; ctx.lineWidth = K.S; ctx.strokeRect(-w / 2, -h, w, h); crack(ctx, K, w, h, st.dmg);
  },
  barrel(ctx, K, w, h, st) {
    ctx.beginPath(); ctx.moveTo(-w * .42, 0); ctx.quadraticCurveTo(-w * .62, -h * .5, -w * .42, -h); ctx.lineTo(w * .42, -h); ctx.quadraticCurveTo(w * .62, -h * .5, w * .42, 0); ctx.closePath();
    ctx.fillStyle = hgrad(ctx, -w * .5, w * .5, [[0, '#a5794a'], [.7, '#8b6238'], [.7, '#684826'], [1, '#684826']]); ctx.fill(); ink(ctx, K, 1.5);
    hoop(ctx, K, -h * .82, w * .84, '#3b3f4a'); hoop(ctx, K, -h * .22, w * .84, '#3b3f4a');
    ellipse(ctx, 0, -h, w * .42, h * .07, '#b58a56', K.ink, 1.3, K); crack(ctx, K, w, h, st.dmg, 3);
  },
  chest(ctx, K, w, h, st) {
    const open = st.open || 0, s = K.S, bh = h * .62;
    block(ctx, K, -w / 2, -bh, w, bh, '#8a5f36', {band: .2});
    hoop(ctx, K, -bh * .55, w, '#3d4350'); ctx.fillStyle = '#d6b36a'; ctx.fillRect(-2.5 * s, -bh * .7, 5 * s, 7 * s);
    ctx.save(); ctx.translate(0, -bh); ctx.scale(1, 1 - open * .2);
    const lh = h * .38 * (1 - open * .55);
    ctx.beginPath(); ctx.moveTo(-w / 2, 0); ctx.quadraticCurveTo(-w / 2, -lh * 1.5 - open * h * .18, 0, -lh * 1.5 - open * h * .18); ctx.quadraticCurveTo(w / 2, -lh * 1.5 - open * h * .18, w / 2, 0); ctx.closePath();
    ctx.fillStyle = open > .3 ? '#5a3d22' : '#9a6b3e'; ctx.fill(); ink(ctx, K, 1.5); ctx.restore();
    if (open > .3) { ctx.fillStyle = rgba('#ffd97a', .5 * open); ctx.fillRect(-w * .36, -bh - 2 * s, w * .72, 3 * s); }
    crack(ctx, K, w, h, st.dmg, 5);
  },
  cabinet(ctx, K, w, h, st) {
    const open = st.open || 0, s = K.S;
    block(ctx, K, -w / 2, -h, w, h, '#6d4d34', {band: .16});
    if (open > .25) { ctx.fillStyle = '#1a1210'; ctx.fillRect(-w / 2 + 4 * s, -h + 4 * s, w - 8 * s, h - 8 * s); inkPoly(ctx, K, [[-w / 2, -h], [-w / 2 - w * .3 * open, -h + h * .05], [-w / 2 - w * .3 * open, -h * .05], [-w / 2, 0]], '#7b5a3e', 1.3); }
    else { ctx.strokeStyle = rgba(INK, .5); ctx.lineWidth = s; ctx.strokeRect(-w / 2 + 4 * s, -h + 5 * s, w / 2 - 6 * s, h - 10 * s); ctx.strokeRect(2 * s, -h + 5 * s, w / 2 - 6 * s, h - 10 * s); ctx.fillStyle = '#d6b36a'; ctx.fillRect(-3 * s, -h * .5, 2 * s, 6 * s); ctx.fillRect(1 * s, -h * .5, 2 * s, 6 * s); }
    crack(ctx, K, w, h, st.dmg);
  },
  bin(ctx, K, w, h, st) {
    const open = st.open || 0;
    poly(ctx, [[-w * .42, 0], [-w * .5, -h], [w * .5, -h], [w * .42, 0]]); ctx.fillStyle = hgrad(ctx, -w / 2, w / 2, [[0, '#6b6f78'], [.65, '#54585f'], [.65, '#3d4147'], [1, '#3d4147']]); ctx.fill(); ink(ctx, K, 1.5);
    ctx.save(); ctx.translate(-w * .48 * open, -h - open * h * .1); ctx.rotate(-open * .5); ellipse(ctx, 0, 0, w * .5, h * .07, '#7c818b', K.ink, 1.3, K); ctx.restore();
  },
  sack(ctx, K, w, h, st) {
    ctx.beginPath(); ctx.moveTo(-w * .4, 0); ctx.quadraticCurveTo(-w * .62, -h * .55, -w * .2, -h * .92); ctx.lineTo(-w * .12, -h); ctx.lineTo(w * .12, -h); ctx.lineTo(w * .2, -h * .92); ctx.quadraticCurveTo(w * .62, -h * .55, w * .4, 0); ctx.closePath();
    ctx.fillStyle = hgrad(ctx, -w / 2, w / 2, [[0, '#c9b58b'], [.65, '#b39f77'], [.65, '#8f7d5a'], [1, '#8f7d5a']]); ctx.fill(); ink(ctx, K, 1.4);
    ctx.strokeStyle = '#6b5a3c'; ctx.lineWidth = 2 * K.S; ctx.beginPath(); ctx.moveTo(-w * .16, -h * .86); ctx.lineTo(w * .16, -h * .86); ctx.stroke(); crack(ctx, K, w, h, st.dmg, 2);
  },
  table(ctx, K, w, h, st) {
    const s = K.S; ctx.fillStyle = '#5a3f2b'; for (const x of [-w * .42, w * .38]) { ctx.fillRect(x, -h * .82, 5 * s, h * .82); ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.strokeRect(x, -h * .82, 5 * s, h * .82); }
    block(ctx, K, -w / 2, -h, w, h * .2, '#8b6540', {band: .1, shade: .3}); crack(ctx, K, w, h * .5, st.dmg);
    ellipse(ctx, -w * .18, -h * 1.03, 5 * s, 2.2 * s, '#cfc7b4', K.ink, 1, K); ctx.fillStyle = '#b3202c'; ctx.fillRect(w * .12, -h * 1.1, 4 * s, 7 * s);
  },
  bench(ctx, K, w, h, st) {
    const s = K.S; ctx.fillStyle = '#5a3f2b'; for (const x of [-w * .4, w * .36]) ctx.fillRect(x, -h * .7, 5 * s, h * .7);
    block(ctx, K, -w / 2, -h, w, h * .3, '#8b6540', {band: .1}); crack(ctx, K, w, h * .5, st.dmg);
  },
  dummy(ctx, K, w, h, st) {
    const s = K.S, hit = Math.min(1, st.dmg || 0);
    ctx.fillStyle = '#5a3f2b'; ctx.fillRect(-2.5 * s, -h * .62, 5 * s, h * .62); ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.strokeRect(-2.5 * s, -h * .62, 5 * s, h * .62);
    ctx.fillRect(-w * .52, -h * .78, 5 * s, h * .14); ctx.fillRect(-w * .52 + 0, -h * .74, w * 1.04, 4 * s); ctx.strokeRect(-w * .52, -h * .74, w * 1.04, 4 * s);
    ctx.beginPath(); ctx.moveTo(-w * .34, -h * .74); ctx.quadraticCurveTo(-w * .46, -h * .4, -w * .3, -h * .3); ctx.lineTo(w * .3, -h * .3); ctx.quadraticCurveTo(w * .46, -h * .4, w * .34, -h * .74); ctx.quadraticCurveTo(0, -h * .8, -w * .34, -h * .74); ctx.closePath();
    ctx.fillStyle = hgrad(ctx, -w / 2, w / 2, [[0, '#d9c58a'], [.62, '#c7b072'], [.62, '#a18d55'], [1, '#a18d55']]); ctx.fill(); ink(ctx, K, 1.5);
    ctx.strokeStyle = '#7e6a3c'; ctx.lineWidth = 2 * s; ctx.beginPath(); ctx.moveTo(-w * .34, -h * .56); ctx.lineTo(w * .34, -h * .56); ctx.stroke();
    ellipse(ctx, 0, -h * .88, w * .2, w * .21, '#cdb98a', K.ink, 1.5, K); ctx.fillStyle = '#5a3f2b'; ctx.fillRect(-w * .12, -h * .89, w * .24, 2 * s);
    if (hit) { ctx.strokeStyle = '#d9c58a'; ctx.lineWidth = s * 1.4; ctx.beginPath(); for (let i = 0; i < Math.ceil(hit * 5); i++) { const x = -w * .3 + ((i * 37) % 60) / 60 * w * .6; ctx.moveTo(x, -h * .56); ctx.lineTo(x + 3 * s, -h * .5 + i * s); } ctx.stroke(); }
  },
  post(ctx, K, w, h, st) {
    const s = K.S; block(ctx, K, -w / 2, -h, w, h, '#7a5a3a', {band: .28}); ctx.fillStyle = '#3d4350'; ctx.fillRect(-w / 2 - s, -h * .55, w + 2 * s, 4 * s);
    ctx.strokeStyle = rgba(INK, .4); ctx.lineWidth = s; ctx.beginPath(); ctx.moveTo(-w * .1, -h * .95); ctx.lineTo(-w * .1, -h * .1); ctx.stroke(); crack(ctx, K, w * 2, h, st.dmg);
  },
  statue(ctx, K, w, h, st) {
    const s = K.S; block(ctx, K, -w * .5, -h * .16, w, h * .16, '#8d9099', {band: .3});
    poly(ctx, [[-w * .3, -h * .16], [-w * .34, -h * .62], [-w * .16, -h * .7], [w * .16, -h * .7], [w * .34, -h * .62], [w * .3, -h * .16]]); ctx.fillStyle = hgrad(ctx, -w / 2, w / 2, [[0, '#b1b4bc'], [.6, '#9a9da6'], [.6, '#767982'], [1, '#767982']]); ctx.fill(); ink(ctx, K, 1.5);
    ellipse(ctx, 0, -h * .82, w * .15, w * .17, '#aeb1b9', K.ink, 1.4, K); ctx.strokeStyle = K.ink; ctx.lineWidth = 2 * s; ctx.beginPath(); ctx.moveTo(w * .3, -h * .6); ctx.lineTo(w * .48, -h * 1.0); ctx.stroke(); crack(ctx, K, w, h, st.dmg);
  },
  pillar(ctx, K, w, h, st) { pillar(ctx, K, 0, 0, w * .8, h, '#8d8a86'); crack(ctx, K, w, h, st.dmg); },
  bell(ctx, K, w, h) {
    const s = K.S; ctx.fillStyle = '#5a3f2b'; ctx.fillRect(-w * .5, -h, w, 5 * s); ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.strokeRect(-w * .5, -h, w, 5 * s);
    ctx.beginPath(); ctx.moveTo(-w * .34, -h * .12); ctx.quadraticCurveTo(-w * .36, -h * .62, -w * .12, -h * .88); ctx.lineTo(w * .12, -h * .88); ctx.quadraticCurveTo(w * .36, -h * .62, w * .34, -h * .12); ctx.closePath();
    ctx.fillStyle = hgrad(ctx, -w / 2, w / 2, [[0, '#e0b85a'], [.6, '#c4993e'], [.6, '#8e6a25'], [1, '#8e6a25']]); ctx.fill(); ink(ctx, K, 1.4); ellipse(ctx, 0, -h * .1, w * .06, w * .06, '#6b4f1c');
  },
  altar(ctx, K, w, h, st) {
    const s = K.S; block(ctx, K, -w / 2, -h * .3, w, h * .3, '#8d8a86', {band: .25}); block(ctx, K, -w * .4, -h * .8, w * .8, h * .5, '#a3a09a', {band: .25}); block(ctx, K, -w * .48, -h * .88, w * .96, h * .1, '#b4b1aa', {band: .2});
    ellipse(ctx, 0, -h * .94, w * .18, w * .05, '#6d4d34', K.ink, 1.2, K); ctx.fillStyle = '#e8d4a0'; ctx.fillRect(-w * .3, -h * 1.04, 3 * s, 10 * s); ctx.fillRect(w * .26, -h * 1.02, 3 * s, 9 * s);
    const t = st.t || 0; for (const x of [-w * .3 + 1.5 * s, w * .26 + 1.5 * s]) { ctx.fillStyle = rgba('#ffcf6b', .9); ctx.beginPath(); ctx.ellipse(x, -h * 1.08 - Math.sin(t * 9 + x) * s, 2 * s, 4 * s, 0, 0, TAU); ctx.fill(); }
  },
  campfire(ctx, K, w, h, st) {
    const s = K.S, t = st.t || 0; ctx.fillStyle = '#4a4a50';
    for (let i = 0; i < 9; i++) { const a = i / 9 * TAU; ellipse(ctx, Math.cos(a) * w * .42, Math.sin(a) * w * .12 - 2 * s, 5 * s, 3.5 * s, i % 2 ? '#6f7078' : '#55565d', K.ink, 1, K); }
    for (const a of [-.5, .5, 0]) { ctx.save(); ctx.rotate(a * .5); beam(ctx, K, -w * .3, -3 * s, w * .3, -6 * s, 5 * s, '#5b3f28'); ctx.restore(); }
    for (let i = 0; i < 3; i++) {
      const fl = 1 + Math.sin(t * (9 + i * 3) + i) * .13, x = (i - 1) * w * .14, hh = h * (.85 - Math.abs(i - 1) * .25) * fl;
      ctx.beginPath(); ctx.moveTo(x - w * .13, -4 * s); ctx.quadraticCurveTo(x - w * .16, -hh * .55, x, -hh); ctx.quadraticCurveTo(x + w * .16, -hh * .55, x + w * .13, -4 * s); ctx.closePath();
      ctx.fillStyle = i === 1 ? '#ffb347' : '#ff7a2f'; ctx.fill();
      ctx.beginPath(); ctx.moveTo(x - w * .06, -4 * s); ctx.quadraticCurveTo(x - w * .07, -hh * .4, x, -hh * .62); ctx.quadraticCurveTo(x + w * .07, -hh * .4, x + w * .06, -4 * s); ctx.fillStyle = '#ffe9a6'; ctx.fill();
    }
  },
  rope(ctx, K, w, h) {
    const s = K.S; ctx.strokeStyle = K.ink; ctx.lineWidth = 5.5 * s; ctx.beginPath(); ctx.moveTo(0, -h); ctx.bezierCurveTo(w * .25, -h * .7, -w * .25, -h * .4, 0, 0); ctx.stroke();
    ctx.strokeStyle = '#b79c66'; ctx.lineWidth = 3.4 * s; ctx.stroke();
    ctx.strokeStyle = '#8a7346'; ctx.lineWidth = s; ctx.setLineDash([3 * s, 4 * s]); ctx.stroke(); ctx.setLineDash([]);
  },
  wheel(ctx, K, w, h, st) {
    const s = K.S, r = Math.min(w, h) / 2, a0 = (st.t || 0) * .5;
    ctx.save(); ctx.translate(0, -h / 2); ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.lineWidth = 6 * s; ctx.strokeStyle = '#5b3f28'; ctx.stroke(); ctx.lineWidth = s; ctx.strokeStyle = K.ink; ctx.stroke();
    for (let i = 0; i < 8; i++) { const a = a0 + i / 8 * TAU; beam(ctx, K, 0, 0, Math.cos(a) * r, Math.sin(a) * r, 4 * s, '#6f4c30'); inkRect(ctx, K, Math.cos(a) * r - 4 * s, Math.sin(a) * r - 6 * s, 8 * s, 12 * s, '#7a5a3a', 1); }
    ellipse(ctx, 0, 0, 6 * s, 6 * s, '#3b3f4a', K.ink, 1.2, K); ctx.restore();
  },
  boat(ctx, K, w, h) {
    const s = K.S; poly(ctx, [[-w / 2, -h * .7], [-w * .38, -h * .06], [w * .38, -h * .06], [w / 2, -h * .7], [w * .1, -h * .55], [-w * .1, -h * .55]]);
    ctx.fillStyle = hgrad(ctx, -w / 2, w / 2, [[0, '#8a6a45'], [.6, '#6f5236'], [.6, '#54402a'], [1, '#54402a']]); ctx.fill(); ink(ctx, K, 1.5);
    ctx.strokeStyle = '#3d2c1d'; ctx.lineWidth = 2 * s; ctx.beginPath(); ctx.moveTo(-w * .4, -h * .5); ctx.lineTo(w * .4, -h * .5); ctx.stroke();
  },
  lamppost(ctx, K, w, h, st) {
    const s = K.S, t = st.t || 0; ctx.fillStyle = '#2c3038'; ctx.fillRect(-2 * s, -h, 4 * s, h); ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.strokeRect(-2 * s, -h, 4 * s, h);
    inkPoly(ctx, K, [[-6 * s, -h], [6 * s, -h], [4 * s, -h - 14 * s], [-4 * s, -h - 14 * s]], '#e9c56d', 1.3); glow(ctx, 0, -h - 7 * s, 46 * s, '#ffcf6b', .55 + Math.sin(t * 6) * .05);
    ctx.fillStyle = '#2c3038'; ctx.fillRect(-7 * s, -h - 18 * s, 14 * s, 4 * s);
  },
  desk(ctx, K, w, h, st) {
    const s = K.S; block(ctx, K, -w / 2, -h, w, h, '#6b4b33', {band: .14}); block(ctx, K, -w / 2 - 3 * s, -h - 4 * s, w + 6 * s, 5 * s, '#8b6540', {band: .1});
    ctx.fillStyle = '#e8dfc6'; ctx.fillRect(-w * .3, -h - 9 * s, w * .25, 5 * s); ctx.fillStyle = '#b3202c'; ctx.fillRect(w * .1, -h - 9 * s, 5 * s, 5 * s); crack(ctx, K, w, h, st.dmg);
  },
  stall(ctx, K, w, h, st) {
    const s = K.S; ctx.fillStyle = '#5a3f2b'; for (const x of [-w * .46, w * .42]) { ctx.fillRect(x, -h, 5 * s, h); ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.strokeRect(x, -h, 5 * s, h); }
    const n = 6, aw = w * 1.08 / n;
    for (let i = 0; i < n; i++) { poly(ctx, [[-w * .54 + i * aw, -h], [-w * .54 + (i + 1) * aw, -h], [-w * .54 + (i + 1) * aw - 2 * s, -h * .78], [-w * .54 + i * aw + 2 * s, -h * .78]]); ctx.fillStyle = i % 2 ? '#e8dfc6' : '#b3403c'; ctx.fill(); ink(ctx, K, 1); }
    block(ctx, K, -w * .5, -h * .42, w, h * .42, '#7a5a3a', {band: .15});
    for (let i = 0; i < 5; i++) ellipse(ctx, -w * .38 + i * w * .19, -h * .46, 6 * s, 5 * s, ['#c0392b', '#d98a2c', '#7d9b3f', '#c0392b', '#d98a2c'][i], K.ink, 1, K);
  },
  banner(ctx, K, w, h, st) {
    const s = K.S, t = st.t || 0, sway = Math.sin(t * 1.3) * 2 * s; ctx.fillStyle = '#3d4350'; ctx.fillRect(-w * .55, -h, w * 1.1, 3 * s);
    poly(ctx, [[-w * .45, -h + 3 * s], [w * .45, -h + 3 * s], [w * .45 + sway, -h * .1], [sway, -h * .02], [-w * .45 + sway, -h * .1]]); ctx.fillStyle = '#7d1f2b'; ctx.fill(); ink(ctx, K, 1.3);
    ctx.fillStyle = '#d6b36a'; ctx.beginPath(); ctx.arc(sway * .5, -h * .58, w * .16, 0, TAU); ctx.fill();
  },
  weaponrack(ctx, K, w, h) {
    const s = K.S; block(ctx, K, -w / 2, -h * .12, w, h * .12, '#5a3f2b', {band: .1}); block(ctx, K, -w / 2, -h, 4 * s, h, '#5a3f2b'); block(ctx, K, w / 2 - 4 * s, -h, 4 * s, h, '#5a3f2b'); block(ctx, K, -w / 2, -h * .62, w, 4 * s, '#6d4d34');
    for (let i = 0; i < 5; i++) { const x = -w * .38 + i * w * .19; ctx.strokeStyle = K.ink; ctx.lineWidth = 3.4 * s; ctx.beginPath(); ctx.moveTo(x, -h * .12); ctx.lineTo(x + (i % 2 ? 2 : -2) * s, -h * (.72 + (i % 3) * .08)); ctx.stroke(); ctx.strokeStyle = i % 2 ? '#c5ccd6' : '#8a6a45'; ctx.lineWidth = 2 * s; ctx.stroke(); }
  },
  tent(ctx, K, w, h) {
    const s = K.S; poly(ctx, [[-w / 2, 0], [0, -h], [w / 2, 0]]); ctx.fillStyle = '#a89a78'; ctx.fill(); ink(ctx, K, 1.5);
    ctx.fillStyle = shadeHex('#a89a78', .3); ctx.beginPath(); ctx.moveTo(0, -h); ctx.lineTo(w / 2, 0); ctx.lineTo(w * .05, 0); ctx.closePath(); ctx.fill(); ink(ctx, K, 1.5);
    poly(ctx, [[-w * .09, 0], [0, -h * .5], [w * .09, 0]]); ctx.fillStyle = '#1a1512'; ctx.fill();
  },
  parcel(ctx, K, w, h, st) {
    block(ctx, K, -w / 2, -h, w, h, '#b6a88a', {band: .2}); ctx.strokeStyle = '#7a6a48'; ctx.lineWidth = 2 * K.S; ctx.beginPath(); ctx.moveTo(0, -h); ctx.lineTo(0, 0); ctx.moveTo(-w / 2, -h * .5); ctx.lineTo(w / 2, -h * .5); ctx.stroke(); crack(ctx, K, w, h, st.dmg);
  },
  pouch(ctx, K, w, h) {
    ctx.beginPath(); ctx.moveTo(-w * .4, 0); ctx.quadraticCurveTo(-w * .56, -h * .6, -w * .2, -h * .9); ctx.lineTo(w * .2, -h * .9); ctx.quadraticCurveTo(w * .56, -h * .6, w * .4, 0); ctx.closePath();
    ctx.fillStyle = '#7c5a3a'; ctx.fill(); ink(ctx, K, 1.3); ctx.fillStyle = '#d6b36a'; ctx.fillRect(-w * .18, -h * .92, w * .36, 3 * K.S);
  },
  hearth(ctx, K, w, h, st) {
    const s = K.S, t = st.t || 0; block(ctx, K, -w / 2, -h, w, h, '#6d6862', {band: .15}); ctx.fillStyle = '#0d0a08'; ctx.beginPath(); ctx.rect(-w * .3, -h * .62, w * .6, h * .62); ctx.fill(); ink(ctx, K, 1.4);
    for (let i = 0; i < 4; i++) { const fl = 1 + Math.sin(t * (8 + i * 2.6) + i * 1.7) * .16, x = (i - 1.5) * w * .12, hh = h * .5 * fl * (1 - Math.abs(i - 1.5) * .16); ctx.beginPath(); ctx.moveTo(x - w * .07, -3 * s); ctx.quadraticCurveTo(x - w * .09, -hh * .6, x, -hh); ctx.quadraticCurveTo(x + w * .09, -hh * .6, x + w * .07, -3 * s); ctx.fillStyle = i % 2 ? '#ffb347' : '#ff7a2f'; ctx.fill(); }
    beam(ctx, K, -w * .25, -4 * s, w * .25, -7 * s, 6 * s, '#4a3626');
  },
  bed(ctx, K, w, h) {
    const s = K.S; block(ctx, K, -w / 2, -h * .38, w, h * .38, '#6d4d34', {band: .12}); block(ctx, K, -w / 2 + 3 * s, -h * .58, w - 6 * s, h * .22, '#c9bfa8', {band: .18}); block(ctx, K, -w / 2 + 3 * s, -h * .62, w * .28, h * .1, '#e8dfc6', {band: .2});
    block(ctx, K, -w / 2, -h, 5 * s, h, '#5a3f2b'); block(ctx, K, w / 2 - 5 * s, -h * .7, 5 * s, h * .7, '#5a3f2b');
  },
  cocoon(ctx, K, w, h, st) {
    const s = K.S, t = st.t || 0, pulse = .5 + .5 * Math.sin(t * 2.2); glow(ctx, 0, -h * .55, w * 1.1, '#ffd27a', .3 + pulse * .25);
    ctx.beginPath(); ctx.ellipse(0, -h * .55, w * .34, h * .48, 0, 0, TAU); ctx.fillStyle = hgrad(ctx, -w / 2, w / 2, [[0, '#f0d9a0'], [.6, '#d4b46a'], [.6, '#9a7a3a'], [1, '#9a7a3a']]); ctx.fill(); ink(ctx, K, 1.6);
    ctx.strokeStyle = rgba('#fff2c0', .5 + pulse * .4); ctx.lineWidth = 1.6 * s; ctx.beginPath(); for (let i = -2; i <= 2; i++) { ctx.moveTo(i * w * .12, -h * (.55 + .4 * Math.cos(i * .5))); ctx.lineTo(i * w * .05, -h * (.55 - .38)); } ctx.stroke();
  },
  coffin(ctx, K, w, h) {
    const s = K.S; poly(ctx, [[-w * .3, -h], [w * .3, -h], [w * .5, -h * .7], [w * .34, 0], [-w * .34, 0], [-w * .5, -h * .7]]); ctx.fillStyle = hgrad(ctx, -w / 2, w / 2, [[0, '#8d8a86'], [.6, '#767370'], [.6, '#5a5855'], [1, '#5a5855']]); ctx.fill(); ink(ctx, K, 1.5);
    ctx.strokeStyle = rgba('#000', .35); ctx.lineWidth = 2 * s; ctx.beginPath(); ctx.moveTo(0, -h * .9); ctx.lineTo(0, -h * .2); ctx.moveTo(-w * .18, -h * .6); ctx.lineTo(w * .18, -h * .6); ctx.stroke();
  },
  brazier(ctx, K, w, h, st) {
    const s = K.S, t = st.t || 0; poly(ctx, [[-w * .5, -h * .55], [w * .5, -h * .55], [w * .3, -h * .35], [w * .08, -h * .05], [w * .3, 0], [-w * .3, 0], [-w * .08, -h * .05], [-w * .3, -h * .35]]); ctx.fillStyle = '#3b3f4a'; ctx.fill(); ink(ctx, K, 1.4);
    for (let i = 0; i < 3; i++) { const fl = 1 + Math.sin(t * (8 + i * 3) + i) * .15, x = (i - 1) * w * .2, hh = h * (.5 - Math.abs(i - 1) * .12) * fl; ctx.beginPath(); ctx.moveTo(x - w * .13, -h * .55); ctx.quadraticCurveTo(x - w * .16, -h * .55 - hh * .6, x, -h * .55 - hh); ctx.quadraticCurveTo(x + w * .16, -h * .55 - hh * .6, x + w * .13, -h * .55); ctx.fillStyle = i === 1 ? '#ffb347' : '#ff7a2f'; ctx.fill(); }
  },
};
PROP_ART.container = PROP_ART.chest; PROP_ART.wardrobe = PROP_ART.cabinet; PROP_ART.rack = PROP_ART.weaponrack;
PROP_ART.torch = (ctx, K, w, h, st) => PROP_ART.brazier(ctx, K, w * .5, h * .5, st);
export function drawProp(ctx, K, kind, w, h, st = {}) { (PROP_ART[kind] || PROP_ART.parcel)(ctx, K, w, h, st); }
export const PROP_KINDS = Object.freeze(Object.keys(PROP_ART));

// ---------------------------------------------------------------------------
// Doors. `open` runs 0..1. A hinged leaf foreshortens as it swings and the
// gap it uncovers shows what lies beyond (`beyond` is a colour pair for the
// gradient through the opening). Positions are the door's feet-centre.
export const DOOR_KINDS = Object.freeze(['wood', 'iron', 'gate', 'arch', 'path', 'curtain', 'hatch']);
export function drawDoor(ctx, K, kind, x, y, w, h, open = 0, {beyond = ['#0b0a0e', '#241a12'], wood = '#7a5232', stone = '#7d7a76', hover = 0, locked = false, t = 0, sign = ''} = {}) {
  const s = K.S, o = clamp(open, 0, 1);
  ctx.save(); ctx.translate(x, y);
  const opening = (cx0, cy0, cw, ch, round = false) => {
    ctx.beginPath(); round ? (ctx.moveTo(cx0, cy0 + ch), ctx.lineTo(cx0, cy0 + cw / 2), ctx.arc(cx0 + cw / 2, cy0 + cw / 2, cw / 2, Math.PI, 0), ctx.lineTo(cx0 + cw, cy0 + ch), ctx.closePath()) : ctx.rect(cx0, cy0, cw, ch);
    ctx.fillStyle = vgrad(ctx, cy0, cy0 + ch, [[0, beyond[0]], [1, beyond[1]]]); ctx.fill();
  };
  const rim = (path) => { if (hover > .02) { ctx.save(); ctx.strokeStyle = rgba('#f2d78c', .35 + hover * .5); ctx.lineWidth = 3.4 * s; ctx.shadowColor = '#f2d78c'; ctx.shadowBlur = 14 * s * hover; path(); ctx.stroke(); ctx.restore(); } };
  const frame = (round) => {
    ctx.beginPath(); round ? (ctx.moveTo(-w / 2, 0), ctx.lineTo(-w / 2, -h + w / 2), ctx.arc(0, -h + w / 2, w / 2, Math.PI, 0), ctx.lineTo(w / 2, 0)) : (ctx.rect(-w / 2, -h, w, h));
  };
  if (kind === 'path') {
    const pw = w * .5;
    ctx.beginPath(); ctx.moveTo(-pw, 0); ctx.lineTo(-pw, -h + pw * .9); ctx.quadraticCurveTo(-pw, -h, 0, -h); ctx.quadraticCurveTo(pw, -h, pw, -h + pw * .9); ctx.lineTo(pw, 0); ctx.closePath();
    ctx.fillStyle = vgrad(ctx, -h, 0, [[0, rgba(beyond[0], .0)], [.35, rgba(beyond[0], .62)], [1, rgba(beyond[1], .9)]]); ctx.fill();
    ctx.strokeStyle = rgba(INK, .55); ctx.lineWidth = 2 * s; ctx.beginPath(); ctx.moveTo(-pw, 0); ctx.lineTo(-pw, -h + pw * .9); ctx.moveTo(pw, 0); ctx.lineTo(pw, -h + pw * .9); ctx.stroke();
    rim(() => { ctx.beginPath(); ctx.moveTo(-pw, 0); ctx.lineTo(-pw, -h + pw * .9); ctx.quadraticCurveTo(-pw, -h, 0, -h); ctx.quadraticCurveTo(pw, -h, pw, -h + pw * .9); ctx.lineTo(pw, 0); }); ctx.restore(); return;
  }
  if (kind === 'arch') {
    opening(-w / 2, -h, w, h, true);
    arch(ctx, K, 0, 0, w + 10 * s, h + 6 * s, stone, {inner: null, keystone: true}); rim(() => frame(true));
    if (o < .5) { ctx.globalAlpha = 1 - o * 2; ctx.fillStyle = vgrad(ctx, -h, 0, [[0, rgba(beyond[0], .85)], [1, rgba(beyond[1], .85)]]); ctx.beginPath(); ctx.moveTo(-w / 2, 0); ctx.lineTo(-w / 2, -h + w / 2); ctx.arc(0, -h + w / 2, w / 2, Math.PI, 0); ctx.lineTo(w / 2, 0); ctx.fill(); ctx.globalAlpha = 1; }
    ctx.restore(); return;
  }
  if (kind === 'curtain') {
    opening(-w / 2, -h, w, h); const gap = w * .46 * o;
    for (const sd of [-1, 1]) { const x0 = sd * (w / 2), x1 = sd * gap; poly(ctx, [[x0, -h], [x1 * 1, -h], [x1 * 1 + sd * 3 * s, 0], [x0, 0]]); ctx.fillStyle = '#6b2a3a'; ctx.fill(); ink(ctx, K, 1.2); ctx.strokeStyle = rgba('#000', .3); ctx.beginPath(); for (let i = 1; i < 4; i++) { const xx = lerp(x0, x1, i / 4); ctx.moveTo(xx, -h); ctx.lineTo(xx, 0); } ctx.stroke(); }
    ctx.fillStyle = '#5a3f2b'; ctx.fillRect(-w / 2 - 4 * s, -h - 4 * s, w + 8 * s, 5 * s); rim(() => { ctx.beginPath(); ctx.rect(-w / 2, -h, w, h); }); ctx.restore(); return;
  }
  if (kind === 'hatch') {
    ctx.beginPath(); ctx.ellipse(0, 0, w / 2, h / 2, 0, 0, TAU); ctx.fillStyle = vgrad(ctx, -h / 2, h / 2, [[0, beyond[0]], [1, beyond[1]]]); ctx.fill();
    ctx.save(); ctx.translate(0, -h * .2 * o); ctx.scale(1, Math.max(.12, 1 - o * .85)); ctx.beginPath(); ctx.ellipse(0, 0, w / 2 + 3 * s, h / 2 + 3 * s, 0, 0, TAU); ctx.fillStyle = '#4b4f58'; ctx.fill(); ink(ctx, K, 1.8);
    ctx.strokeStyle = '#2f333b'; ctx.lineWidth = 3 * s; ctx.beginPath(); ctx.moveTo(-w * .4, 0); ctx.lineTo(w * .4, 0); ctx.stroke(); ctx.restore();
    rim(() => { ctx.beginPath(); ctx.ellipse(0, 0, w / 2 + 3 * s, h / 2 + 3 * s, 0, 0, TAU); }); ctx.restore(); return;
  }
  const iron = kind === 'iron', gate = kind === 'gate';
  // Frame and the dark beyond.
  const jamb = stone;
  opening(-w / 2, -h, w, h);
  const swing = Math.sin(o * 1.35);
  const leaves = gate ? [-1, 1] : [1], lw = gate ? w / 2 : w;
  for (const side of leaves) {
    const hinge = gate ? side * w / 2 : -w / 2, fore = Math.cos(o * 1.3), farH = h * (1 - .12 * o);
    const x0 = hinge, x1 = hinge + (gate ? -side : 1) * lw * fore * (gate ? 1 : 1), ya0 = -h, yb0 = 0, ya1 = -farH, yb1 = -h * .02 * o;
    poly(ctx, [[x0, ya0], [x1, ya1 + (h - farH) * .0], [x1, yb1], [x0, yb0]]);
    const c = iron ? '#4b5058' : wood; ctx.fillStyle = c; ctx.fill(); ink(ctx, K, 1.6);
    ctx.save(); poly(ctx, [[x0, ya0], [x1, ya1], [x1, yb1], [x0, yb0]]); ctx.clip();
    const pn = iron ? 7 : 5;
    ctx.strokeStyle = rgba(INK, iron ? .7 : .35); ctx.lineWidth = (iron ? 2.4 : 1.2) * s; ctx.beginPath();
    for (let i = 1; i < pn; i++) { const xx = lerp(x0, x1, i / pn); ctx.moveTo(xx, lerp(ya0, ya1, i / pn)); ctx.lineTo(xx, lerp(yb0, yb1, i / pn)); } ctx.stroke();
    ctx.fillStyle = iron ? '#2b2f36' : '#3b3f4a'; for (const f of [.22, .72]) { const yy0 = lerp(ya0, yb0, f); poly(ctx, [[x0, yy0 - 3 * s], [x1, lerp(ya1, yb1, f) - 3 * s], [x1, lerp(ya1, yb1, f) + 3 * s], [x0, yy0 + 3 * s]]); ctx.fill(); }
    ctx.fillStyle = shadeHex(c, .3); ctx.globalAlpha = .35 + o * .3; poly(ctx, [[x0, ya0], [x1, ya1], [x1, yb1], [x0, yb0]]); ctx.fill(); ctx.globalAlpha = 1;
    ctx.restore();
    if (!gate || side > 0) { ctx.fillStyle = '#d6b36a'; ctx.beginPath(); ctx.arc(lerp(x0, x1, gate ? .82 : .86), -h * .48, 2.2 * s, 0, TAU); ctx.fill(); }
  }
  ctx.strokeStyle = jamb; ctx.lineWidth = 6 * s; ctx.strokeRect(-w / 2 - 3 * s, -h - 3 * s, w + 6 * s, h + 3 * s); ctx.strokeStyle = K.ink; ctx.lineWidth = 1.4 * s; ctx.strokeRect(-w / 2 - 6 * s, -h - 6 * s, w + 12 * s, h + 6 * s);
  rim(() => { ctx.beginPath(); ctx.rect(-w / 2 - 6 * s, -h - 6 * s, w + 12 * s, h + 6 * s); });
  if (locked) { ctx.fillStyle = '#d6b36a'; ctx.fillRect(-3 * s, -h * .45, 6 * s, 6 * s); }
  if (sign) { ctx.fillStyle = '#4a3626'; ctx.fillRect(-w * .36, -h - 22 * s, w * .72, 10 * s); ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.strokeRect(-w * .36, -h - 22 * s, w * .72, 10 * s); }
  ctx.restore();
}

// ---------------------------------------------------------------------------
// Finishing: haze toward the horizon, vignette, film grain.
export function finish(ctx, K, {hazeColor = '#8a97b0', haze = .22, horizonY = K.H * .5, vignette = .45, grain = .05} = {}) {
  const {W, H} = K;
  if (haze) { ctx.fillStyle = vgrad(ctx, horizonY - H * .16, horizonY + H * .12, [[0, rgba(hazeColor, 0)], [.55, rgba(hazeColor, haze)], [1, rgba(hazeColor, 0)]]); ctx.fillRect(0, horizonY - H * .16, W, H * .28); }
  if (vignette) {
    const g = ctx.createRadialGradient(W / 2, H * .55, H * .35, W / 2, H * .55, Math.max(W, H) * .78);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(4,6,12,${vignette})`); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }
  if (grain) noiseDots(ctx, K, 0, 0, W, H, '#ffffff', Math.floor(W * H / 900), 1, grain);
}
export {r2 as range};
