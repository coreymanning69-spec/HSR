// Stage set: the painted places a scene can be.
//
// A theme is a place (the market at dusk, the tavern, the drowned pier, the
// palace hall...): a camera (where the floor sits and how fast it shrinks with
// depth), a painter that bakes the static art once per room, the animated bits
// drawn every frame (fire, water, steam, wheels), lights for the lighting
// pass, ambient motes, and the depth-sorted props that stand in it.
//
// The floor is a plane: d = 0 at the near edge (y = cam.front) and d = 1 at
// the back wall (y = cam.back). Everything that stands on it scales with
// lerp(1, cam.farScale, d), which is what makes a walk into the distance read.
import {clamp, lerp, hash32, mixHex, shadeHex, lightHex, rgba, TAU} from './actor-core.js';
import {rng} from './stage-world.js';
import {kit, INK, ink, vgrad, hgrad, glow, poly, inkPoly, inkRect, ellipse, block, ridge, pine, tree, sky, house, stoneWall, planksWall, beam, arch, pillar,
  floorPlane, groundPool, drawProp, drawDoor, finish, noiseDots, windowPane, roof} from './stage-art.js';

// ---------------------------------------------------------------------------
// Time of day for the outdoors.
export const TOD = Object.freeze({
  morning: {top: '#5f7fb5', mid: '#e0b58a', bot: '#f6dcaa', sun: {x: .16, y: .36, r: 22, color: '#fff0c4', halo: '#ffc98a'}, ambient: '#d9cfc1', haze: '#f2d9b4', lamps: 0, stars: 0, clouds: 4, cloud: '#fff1dc', far: '#7a8fae'},
  day: {top: '#5a8ccf', mid: '#9cc3e6', bot: '#e8dcc0', sun: {x: .72, y: .18, r: 26, color: '#fff6d0', halo: '#fff0b0'}, ambient: '#eeebe2', haze: '#d5e4f2', lamps: 0, stars: 0, clouds: 5, cloud: '#ffffff', far: '#7f9bbb'},
  evening: {top: '#26325f', mid: '#b1655d', bot: '#f0a869', sun: {x: .82, y: .4, r: 24, color: '#ffe3a8', halo: '#ff9a5a'}, ambient: '#b4a2b0', haze: '#e0906a', lamps: 1, stars: 14, clouds: 3, cloud: '#ffb18a', far: '#524a72'},
  night: {top: '#060919', mid: '#111a36', bot: '#26335a', sun: {x: .78, y: .2, r: 19, color: '#eef3ff', halo: '#9fb4e6', crescent: true}, ambient: '#5b6a95', haze: '#3b4a77', lamps: 1, stars: 90, clouds: 2, cloud: '#5a6a9a', far: '#1b2340'},
});
export const todOf = value => TOD[String(value || '').toLowerCase()] ? String(value).toLowerCase() : 'evening';

// ---------------------------------------------------------------------------
// Shared builders for the painters below.
const S = K => K.S;
const Yb = K => K.cam.back * K.H;
// A row of building fronts along the back line, one behind each door bay,
// with open lanes where a bay is a path or an arch and fillers between.
function facadeRow(ctx, K, {base, pals, tallness = [120, 210], lit = .5, bayW = 190, kinds = ['timber', 'timber', 'stone', 'brick'], door = true, chimney = .5, roofs = ['#7a3f34', '#5d4a3a', '#6b4a3a', '#4f5a68']}) {
  const s = K.S, W = K.W, r = K.rand, spans = [];
  const bays = [...K.bays].sort((a, b) => a.x - b.x);
  for (const b of bays) {
    const cx = b.x * W, open = b.kind === 'path' || b.kind === 'arch' || b.kind === 'hatch';
    spans.push({x0: cx - (open ? 62 : bayW * .5) * s, x1: cx + (open ? 62 : bayW * .5) * s, open, bay: b});
  }
  const draw = (x, w, bay) => {
    const h = (tallness[0] + r() * (tallness[1] - tallness[0])) * s, kind = kinds[Math.floor(r() * kinds.length)];
    house(ctx, K, {x, base, w, h, kind, wall: pals[Math.floor(r() * pals.length)], trim: '#4a3626', roofC: roofs[Math.floor(r() * roofs.length)], floors: h > 150 * s ? 3 : 2,
      lit: lit, chimney: r() < chimney, door: false, shutter: ['#5d4a3a', '#3f5a4a', '#6a3f3a'][Math.floor(r() * 3)]});
  };
  let x = -30 * s;
  const list = spans.sort((a, b) => a.x0 - b.x0);
  const lane = sp => { const w = sp.x1 - sp.x0; ctx.fillStyle = vgrad(ctx, base - 90 * s, base, [[0, 'rgba(8,10,18,0)'], [1, 'rgba(8,10,18,.55)']]); ctx.fillRect(sp.x0, base - 90 * s, w, 90 * s); house(ctx, K, {x: sp.x0 + w * .3, base: base - 2 * s, w: w * .4, h: 56 * s, kind: 'stone', wall: mixHex(K.tod.far, '#000000', .5), roofC: mixHex(K.tod.far, '#000000', .6), floors: 1, lit: .8}); };
  for (const sp of list) {
    while (x < sp.x0 - 40 * s) { const w = (110 + r() * 100) * s; draw(x, Math.min(w, sp.x0 - x + 4 * s), null); x += w - 2 * s; }
    if (sp.open) lane(sp); else draw(sp.x0, sp.x1 - sp.x0, sp.bay);
    x = sp.x1 - 2 * s;
  }
  while (x < W + 30 * s) { const w = (110 + r() * 100) * s; draw(x, w, null); x += w - 2 * s; }
}
const farTown = (ctx, K, y, color, n = 16) => {
  const s = K.S; ctx.fillStyle = color; let x = -10;
  while (x < K.W + 10) { const w = (26 + K.rand() * 44) * s, h = (24 + K.rand() * 50) * s; ctx.fillRect(x, y - h, w, h + 2); if (K.rand() < .6) { poly(ctx, [[x - 2 * s, y - h], [x + w / 2, y - h - (10 + K.rand() * 16) * s], [x + w + 2 * s, y - h]]); ctx.fill(); } x += w - 2 * s; }
};
// The back wall of an interior, with a ceiling band and beams.
function interior(ctx, K, {wall = 'stone', base, ceil = .12, beams = '#3b2c20', course = 22, moss = 0, inset = true, sideTone = null, shade = .0, plank = 16}) {
  const {W, H, S: s} = K, back = Yb(K), top = ceil * H;
  if (wall === 'stone') stoneWall(ctx, K, 0, top, W, back, base, {course, moss}); else if (wall === 'plank') planksWall(ctx, K, 0, top, W, back, base, {plank});
  else if (wall === 'plaster') { ctx.fillStyle = base; ctx.fillRect(0, top, W, back - top); noiseDots(ctx, K, 0, top, W, back - top, '#000000', 500, 1.6, .05); ctx.fillStyle = vgrad(ctx, top, back, [[0, 'rgba(0,0,0,.3)'], [.5, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,.28)']]); ctx.fillRect(0, top, W, back - top); }
  else if (wall === 'metal') { ctx.fillStyle = base; ctx.fillRect(0, top, W, back - top); for (let x = 0; x < W; x += 90 * s) { ctx.fillStyle = rgba('#000', .16); ctx.fillRect(x, top, 4 * s, back - top); ctx.fillStyle = rgba('#fff', .05); ctx.fillRect(x + 4 * s, top, 3 * s, back - top); for (let y = top + 20 * s; y < back; y += 40 * s) { ctx.fillStyle = rgba('#000', .3); ctx.beginPath(); ctx.arc(x + 12 * s, y, 1.6 * s, 0, TAU); ctx.fill(); } } ctx.fillStyle = vgrad(ctx, top, back, [[0, 'rgba(0,0,0,.35)'], [.5, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,.3)']]); ctx.fillRect(0, top, W, back - top); }
  else if (wall === 'marble') { ctx.fillStyle = vgrad(ctx, top, back, [[0, mixHex(base, '#000000', .18)], [1, base]]); ctx.fillRect(0, top, W, back - top); ctx.strokeStyle = rgba('#8a7a55', .35); ctx.lineWidth = s; for (let x = 0; x < W; x += 120 * s) { ctx.strokeRect(x + 6 * s, top + 24 * s, 108 * s, back - top - 48 * s); } }
  // Ceiling band with beam ends.
  ctx.fillStyle = vgrad(ctx, 0, top + 6 * s, [[0, '#06070c'], [1, shadeHex(base, .55)]]); ctx.fillRect(0, 0, W, top + 6 * s);
  if (beams) for (let x = -10 * s; x < W; x += 150 * s) beam(ctx, K, x, 0, x + 14 * s, top + 4 * s, 16 * s, beams);
  beam(ctx, K, 0, top + 2 * s, W, top + 2 * s, 12 * s, beams || '#3b2c20');
  if (inset) {                                   // side walls closing the room toward the back
    const ins = W * (1 - K.cam.farScale) * .5 * .55;
    for (const sd of [-1, 1]) { const x0 = sd < 0 ? 0 : W, x1 = sd < 0 ? ins : W - ins; poly(ctx, [[x0, 0], [x1, top], [x1, back], [x0, K.H]]); ctx.fillStyle = sideTone || shadeHex(base, .45); ctx.fill(); ctx.save(); poly(ctx, [[x0, 0], [x1, top], [x1, back], [x0, K.H]]); ctx.clip(); ctx.fillStyle = hgrad(ctx, x0, x1, [[0, 'rgba(0,0,0,.55)'], [1, 'rgba(0,0,0,.1)']]); ctx.fillRect(Math.min(x0, x1), 0, Math.abs(x1 - x0), K.H); ctx.restore(); ctx.strokeStyle = rgba(INK, .8); ctx.lineWidth = 1.6 * s; ctx.beginPath(); ctx.moveTo(x1, top); ctx.lineTo(x1, back); ctx.stroke(); }
  }
}
const skirting = (ctx, K, color = '#3a2c22') => { const back = Yb(K), s = K.S; ctx.fillStyle = color; ctx.fillRect(0, back - 7 * s, K.W, 7 * s); ctx.fillStyle = rgba('#fff', .08); ctx.fillRect(0, back - 7 * s, K.W, s); ctx.strokeStyle = K.ink; ctx.lineWidth = s * 1.2; ctx.beginPath(); ctx.moveTo(0, back - 7 * s); ctx.lineTo(K.W, back - 7 * s); ctx.stroke(); };
const stoop = (ctx, K, bay, color = '#8a8680') => { const s = K.S, x = bay.x * K.W, back = Yb(K), w = bay.w * K.cam.farScale * K.ppf; block(ctx, K, x - w * .62, back - 5 * s, w * 1.24, 6 * s, color, {band: .2}); };
const puddle = (ctx, K, x, y, rx, color) => { color = mixHex(mixHex(color, '#7f93b8', .7), '#20283c', .25); ctx.save(); ctx.globalAlpha = .55; ellipse(ctx, x, y, rx, rx * .16, color); ctx.globalAlpha = .5; ellipse(ctx, x - rx * .2, y - rx * .02, rx * .35, rx * .04, '#ffffff'); ctx.restore(); };
const string = (ctx, K, x0, y0, x1, y1, sag, colors) => { const s = K.S; ctx.strokeStyle = rgba(INK, .8); ctx.lineWidth = s; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.quadraticCurveTo((x0 + x1) / 2, (y0 + y1) / 2 + sag * s, x1, y1); ctx.stroke(); const n = 9; for (let i = 1; i < n; i++) { const t = i / n, x = lerp(x0, x1, t), y = (1 - t) * (1 - t) * y0 + 2 * (1 - t) * t * ((y0 + y1) / 2 + sag * s) + t * t * y1; poly(ctx, [[x - 4 * s, y], [x + 4 * s, y], [x, y + 9 * s]]); ctx.fillStyle = colors[i % colors.length]; ctx.fill(); } };
const wallTorch = (ctx, K, x, y, color = '#3b3f4a') => { const s = K.S; inkRect(ctx, K, x - 2 * s, y, 4 * s, 22 * s, color, 1.2); ellipse(ctx, x, y, 6 * s, 3 * s, color, K.ink, 1.1, K); };

// ---------------------------------------------------------------------------
// The themes. Coordinates in a painter are pixels; K.cam gives the floor.
export const THEMES = {};
const def = (id, spec) => { THEMES[id] = {id, indoor: false, door: 'wood', beyond: ['#0b0a0e', '#241a12'], particles: {kind: 'dust', n: 26, color: '#ffe6b0'}, world: {width: 44, depth: 10}, decor: [], live: [], lights: () => [], ...spec}; };

// The widest clear stretch of back wall between doors (as a fraction of the width): where a
// centrepiece such as the town well can stand without a door drawn across it.
export function clearSpot(bays = [], margin = .05) {
  const xs = [0, ...bays.map(b => b.x).sort((a, b) => a - b), 1];
  let best = .5, gap = -1;
  for (let i = 1; i < xs.length; i++) if (xs[i] - xs[i - 1] > gap) { gap = xs[i] - xs[i - 1]; best = (xs[i] + xs[i - 1]) / 2; }
  return Math.max(margin, Math.min(1 - margin, best));
}

// ---- Town, Floor One -----------------------------------------------------
def('market', {
  name: 'Market Square', cam: {horizon: .42, back: .60, front: .91, farScale: .66}, beyond: ['#101018', '#3a2a1c'],
  floor: {kind: 'cobble', floor: '#7d7a78', floorShade: '#57555a', floorLit: '#a09b94'},
  decor: [{prop: 'barrel', x: 5, d: .28, blocking: true}, {prop: 'crate', x: 7.6, d: .25, blocking: true}, {prop: 'barrel', x: 39, d: .3, blocking: true}, {prop: 'sack', x: 41.6, d: .27}],
  particles: {kind: 'dust', n: 22, color: '#ffe0a0'},
  lights: K => [K.tod.sun && {x: K.tod.sun.x, y: .25, r: .9, c: K.tod.sun.halo, a: .16}, ...(K.tod.lamps ? [{x: .2, y: .48, r: .3, c: '#ffbe6a', a: .6, flick: .12, hz: 5}, {x: .8, y: .48, r: .3, c: '#ffbe6a', a: .6, flick: .12, hz: 6}, {x: .5, y: .5, r: .24, c: '#ffcf8a', a: .35, flick: .1, hz: 4}] : [])].filter(Boolean),
  paint(ctx, K) {
    const {W, H, S: s} = K, T = K.tod, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: T.bot, y1: hz + 40 * s, sun: T.sun, stars: T.stars, clouds: T.clouds, cloud: T.cloud});
    ridge(ctx, K, hz - 18 * s, 22, mixHex(T.far, '#000000', .1), {step: 30}); ridge(ctx, K, hz + 4 * s, 12, mixHex(T.far, '#000000', .3), {step: 22});
    farTown(ctx, K, hz + 34 * s, mixHex(T.far, '#000000', .42));
    ctx.fillStyle = mixHex(T.far, '#000000', .5); ctx.fillRect(0, hz + 30 * s, W, back - hz);
    facadeRow(ctx, K, {base: back, pals: ['#c9b79a', '#bfa98a', '#a9adb8', '#c69a78', '#b9c2b0'], lit: T.lamps ? .7 : .25, tallness: [120, 215]});
    for (const b of K.bays) if (b.kind !== 'path' && b.kind !== 'arch') stoop(ctx, K, b, '#8b867e');
    floorPlane(ctx, K, back, H, 'cobble', K.floor, {conv: K.cam.farScale});
    if (K.rand() < 1) { string(ctx, K, W * .04, back - 150 * s, W * .5, back - 168 * s, 20, ['#b3403c', '#e8dfc6', '#3f6a8a']); string(ctx, K, W * .5, back - 168 * s, W * .96, back - 146 * s, 20, ['#3f6a8a', '#d6b36a', '#b3403c']); }
    puddle(ctx, K, W * .3, back + (H - back) * .45, 60 * s, T.mid); puddle(ctx, K, W * .72, back + (H - back) * .75, 90 * s, T.mid);
    finish(ctx, K, {hazeColor: T.haze, haze: .2, horizonY: back - 20 * s});
  },
});
def('well', {
  name: 'The Old Well', cam: {horizon: .42, back: .60, front: .91, farScale: .68}, beyond: ['#0a0b12', '#2a2f3a'],
  floor: {kind: 'cobble', floor: '#78777a', floorShade: '#50505a', floorLit: '#9a97a0'},
  decor: [{prop: 'barrel', x: 4, d: .2, blocking: true}, {prop: 'post', x: 40, d: .22, blocking: true}],
  particles: {kind: 'dust', n: 18, color: '#cfe0ff'},
  lights: K => [{x: .5, y: .52, r: .34, c: '#8fc4ff', a: .3, flick: .06, hz: 2}, ...(K.tod.lamps ? [{x: .16, y: .5, r: .26, c: '#ffbe6a', a: .55, flick: .1, hz: 5}, {x: .86, y: .5, r: .26, c: '#ffbe6a', a: .5, flick: .1, hz: 6}] : [])],
  paint(ctx, K) {
    const {W, H, S: s} = K, T = K.tod, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: T.bot, y1: hz + 40 * s, sun: T.sun, stars: T.stars, clouds: T.clouds, cloud: T.cloud});
    ridge(ctx, K, hz - 10 * s, 24, mixHex(T.far, '#000000', .16), {step: 28}); farTown(ctx, K, hz + 34 * s, mixHex(T.far, '#000000', .45));
    ctx.fillStyle = mixHex(T.far, '#000000', .5); ctx.fillRect(0, hz + 30 * s, W, back - hz);
    facadeRow(ctx, K, {base: back, pals: ['#bfa98a', '#a9adb8', '#c9b79a'], lit: T.lamps ? .7 : .2, tallness: [100, 190]});
    floorPlane(ctx, K, back, H, 'cobble', K.floor, {conv: K.cam.farScale});
    // The well: a stone drum under a small roof, with the platform it drops.
    const cx = W * clearSpot(K.bays), base = back + (H - back) * .16, ww = 122 * s;
    ellipse(ctx, cx, base, ww * .74, ww * .13, '#3c3a3e', K.ink, 1.4, K);
    inkPoly(ctx, K, [[cx - ww * .5, base - 40 * s], [cx + ww * .5, base - 40 * s], [cx + ww * .52, base], [cx - ww * .52, base]], '#8d8983', 1.5);
    ctx.save(); poly(ctx, [[cx - ww * .5, base - 40 * s], [cx + ww * .5, base - 40 * s], [cx + ww * .52, base], [cx - ww * .52, base]]); ctx.clip(); ctx.fillStyle = shadeHex('#8d8983', .32); ctx.fillRect(cx + ww * .16, base - 40 * s, ww, 44 * s); ctx.strokeStyle = rgba(INK, .3); ctx.lineWidth = s; for (let i = 1; i < 4; i++) { ctx.beginPath(); ctx.moveTo(cx - ww * .5, base - 40 * s + i * 10 * s); ctx.lineTo(cx + ww * .5, base - 40 * s + i * 10 * s); ctx.stroke(); } ctx.restore();
    ellipse(ctx, cx, base - 40 * s, ww * .5, ww * .09, '#0b1220', K.ink, 1.4, K); ellipse(ctx, cx, base - 41 * s, ww * .4, ww * .06, '#1c2f4a');
    beam(ctx, K, cx - ww * .46, base - 40 * s, cx - ww * .46, base - 118 * s, 6 * s, '#5a3f2b'); beam(ctx, K, cx + ww * .46, base - 40 * s, cx + ww * .46, base - 118 * s, 6 * s, '#5a3f2b'); beam(ctx, K, cx, base - 118 * s, cx, base - 96 * s, 5 * s, '#5a3f2b');
    roof(ctx, K, cx - ww * .6, base - 118 * s, ww * 1.2, 28 * s, '#6b4a3a', {style: 'gable', rows: 3});
    ctx.strokeStyle = '#b79c66'; ctx.lineWidth = 3 * s; ctx.beginPath(); ctx.moveTo(cx, base - 105 * s); ctx.lineTo(cx, base - 62 * s); ctx.stroke(); inkRect(ctx, K, cx - 6 * s, base - 62 * s, 12 * s, 10 * s, '#7a5a3a', 1.2);
    puddle(ctx, K, cx, base + 14 * s, 130 * s, T.mid);
    finish(ctx, K, {hazeColor: T.haze, haze: .2, horizonY: back - 20 * s});
  },
});
def('waterwheel', {
  name: 'Waterwheel Yard', cam: {horizon: .40, back: .58, front: .91, farScale: .66}, beyond: ['#080a10', '#1c2530'],
  floor: {kind: 'plank', floor: '#5b4a3c', floorShade: '#3a2f27', floorLit: '#7a6552'}, door: 'gate',
  decor: [{prop: 'crate', x: 4.6, d: .22, blocking: true}, {prop: 'barrel', x: 39.5, d: .3, blocking: true}, {prop: 'crate', x: 37, d: .2, blocking: true}],
  particles: {kind: 'mist', n: 16, color: '#b8d0e8'},
  lights: K => [{x: .3, y: .5, r: .34, c: '#8fc4ff', a: .25, flick: .05, hz: 2}, ...(K.tod.lamps ? [{x: .82, y: .5, r: .3, c: '#ffbe6a', a: .55, flick: .1, hz: 5}] : [])],
  live: [{prop: 'wheel', xn: .34, yn: .0, wn: .2, hn: .25, back: true}],
  paint(ctx, K) {
    const {W, H, S: s} = K, T = K.tod, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: T.bot, y1: hz + 40 * s, sun: T.sun, stars: T.stars, clouds: T.clouds, cloud: T.cloud});
    ridge(ctx, K, hz - 6 * s, 20, mixHex(T.far, '#000000', .2)); farTown(ctx, K, hz + 30 * s, mixHex(T.far, '#000000', .45));
    // The mill: a long timber wall the wheel turns against, and a channel of water below it.
    const mill = back - 5 * s; block(ctx, K, W * .12, mill - 190 * s, W * .5, 190 * s, '#7a6a58', {band: .18}); planksWall(ctx, K, W * .12, mill - 190 * s, W * .62, mill, '#7a6a58', {plank: 20});
    roof(ctx, K, W * .1, mill - 190 * s, W * .54, 60 * s, '#5a4438', {style: 'gable'});
    facadeRow(ctx, K, {base: back, pals: ['#8a7a68', '#6f7480'], lit: T.lamps ? .6 : .15, tallness: [90, 150], kinds: ['stone', 'timber']});
    ctx.fillStyle = vgrad(ctx, back - 26 * s, back + 30 * s, [[0, '#101a2a'], [1, '#26405c']]); ctx.fillRect(0, back - 6 * s, W, 36 * s);
    ctx.strokeStyle = rgba('#bfe0ff', .35); ctx.lineWidth = s; for (let i = 0; i < 14; i++) { const y = back + 2 * s + K.rand() * 22 * s, x = K.rand() * W; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 60 * s, y); ctx.stroke(); }
    floorPlane(ctx, K, back + 24 * s, H, 'plank', K.floor, {conv: K.cam.farScale});
    beam(ctx, K, 0, back + 24 * s, W, back + 24 * s, 9 * s, '#4a3626');
    puddle(ctx, K, W * .55, back + (H - back) * .5, 120 * s, '#8fb4d8'); puddle(ctx, K, W * .2, back + (H - back) * .8, 70 * s, '#8fb4d8');
    finish(ctx, K, {hazeColor: T.haze, haze: .24, horizonY: back - 10 * s});
  },
});
def('tavern', {
  name: 'The Crooked Crown', indoor: true, cam: {horizon: .12, back: .62, front: .91, farScale: .74}, beyond: ['#0a0908', '#2a1d12'],
  floor: {kind: 'plank', floor: '#5a4030', floorShade: '#382719', floorLit: '#7f5b40'}, ambient: '#a58a72',
  decor: [{prop: 'table', x: 12.5, d: .5, scale: 1.1, blocking: true}, {prop: 'bench', x: 12.5, d: .38}, {prop: 'table', x: 30, d: .42, scale: 1.1, blocking: true}, {prop: 'bench', x: 30, d: .3}, {prop: 'barrel', x: 4, d: .2, blocking: true}, {prop: 'barrel', x: 6.3, d: .17, blocking: true}],
  particles: {kind: 'embers', n: 12, color: '#ffb060'},
  lights: () => [{x: .78, y: .64, r: .5, c: '#ff9a4a', a: .85, flick: .2, hz: 8}, {x: .3, y: .2, r: .3, c: '#ffc27a', a: .55, flick: .1, hz: 5}, {x: .55, y: .2, r: .3, c: '#ffc27a', a: .55, flick: .1, hz: 6}, {x: .1, y: .55, r: .26, c: '#ffc27a', a: .4, flick: .08, hz: 4}],
  live: [{prop: 'hearth', xn: .78, yn: 0, wn: .2, hn: .3, back: true}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    interior(ctx, K, {wall: 'plaster', base: '#b8977a', ceil: .13, beams: '#3b2a1e'});
    // Timber framing and the bar shelves.
    ctx.fillStyle = '#3b2a1e'; for (let x = W * .06; x < W; x += W * .19) ctx.fillRect(x, H * .13, 9 * s, back - H * .13);
    block(ctx, K, W * .04, back - 120 * s, W * .26, 12 * s, '#6d4d34', {band: .1}); block(ctx, K, W * .04, back - 186 * s, W * .26, 12 * s, '#6d4d34', {band: .1});
    for (let i = 0; i < 11; i++) { const x = W * .05 + i * W * .022, h = (22 + K.rand() * 14) * s, y = i < 6 ? back - 120 * s : back - 186 * s; block(ctx, K, x, y - h, 10 * s, h, ['#3f6a4a', '#8a4a2a', '#5a7a9a', '#7a3a3a'][i % 4], {band: .3, ink: 1}); }
    block(ctx, K, W * .02, back - 46 * s, W * .34, 46 * s, '#6d4d34', {band: .1}); block(ctx, K, W * .015, back - 52 * s, W * .35, 8 * s, '#8b6540', {band: .1});
    for (const x of [.4, .58]) { const cx = W * x; ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.beginPath(); ctx.moveTo(cx, H * .13); ctx.lineTo(cx, H * .2); ctx.stroke(); inkPoly(ctx, K, [[cx - 8 * s, H * .2], [cx + 8 * s, H * .2], [cx + 5 * s, H * .2 + 12 * s], [cx - 5 * s, H * .2 + 12 * s]], '#e9c56d', 1.2); }
    skirting(ctx, K, '#3a2a1c'); floorPlane(ctx, K, back, H, 'plank', K.floor, {conv: K.cam.farScale});
    groundPool(ctx, W * .78, back + (H - back) * .3, 230 * s, 60 * s, '#ff9a4a', .3);
    finish(ctx, K, {hazeColor: '#3b2a1e', haze: .1, horizonY: back, vignette: .55});
  },
});
def('rooms', {
  name: 'Tavern Rooms', indoor: true, cam: {horizon: .12, back: .60, front: .91, farScale: .72}, beyond: ['#060506', '#1a1410'], door: 'wood',
  floor: {kind: 'plank', floor: '#4f3a2c', floorShade: '#33261c', floorLit: '#72523a'}, ambient: '#8a7866',
  decor: [{prop: 'bench', x: 5, d: .2}, {prop: 'barrel', x: 40.6, d: .22, blocking: true}],
  particles: {kind: 'dust', n: 14, color: '#ffd9a0'},
  lights: () => [{x: .3, y: .38, r: .3, c: '#ffbe6a', a: .6, flick: .1, hz: 5}, {x: .7, y: .38, r: .3, c: '#ffbe6a', a: .55, flick: .1, hz: 6}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    interior(ctx, K, {wall: 'plaster', base: '#a48a70', ceil: .12, beams: '#33251b'});
    // Wainscot and the stair going up on the right.
    planksWall(ctx, K, 0, back - 84 * s, W, back, '#5a4232', {plank: 14}); ctx.fillStyle = '#33251b'; ctx.fillRect(0, back - 88 * s, W, 6 * s);
    for (let i = 0; i < 7; i++) block(ctx, K, W * .84 + i * 14 * s, back - (i + 1) * 15 * s, W * .16 - i * 14 * s + 40 * s, 15 * s, '#6d4d34', {band: .12});
    beam(ctx, K, W * .84, back - 105 * s, W, back - 210 * s, 6 * s, '#4a3626');
    for (const x of [.3, .7]) { const cx = W * x; ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.beginPath(); ctx.moveTo(cx, back - 140 * s); ctx.lineTo(cx, back - 118 * s); ctx.stroke(); inkPoly(ctx, K, [[cx - 7 * s, back - 118 * s], [cx + 7 * s, back - 118 * s], [cx + 5 * s, back - 102 * s], [cx - 5 * s, back - 102 * s]], '#e9c56d', 1.2); }
    skirting(ctx, K, '#2d2118'); floorPlane(ctx, K, back, H, 'plank', K.floor, {conv: K.cam.farScale});
    poly(ctx, [[W * .5 - 46 * s, back], [W * .5 + 46 * s, back], [W * .5 + 150 * s, H], [W * .5 - 150 * s, H]]); ctx.fillStyle = rgba('#6d1119', .82); ctx.fill(); ctx.strokeStyle = rgba('#d6b36a', .5); ctx.lineWidth = 2 * s; ctx.stroke();
    finish(ctx, K, {hazeColor: '#2a1d14', haze: .1, horizonY: back, vignette: .55});
  },
});
def('guardhouse', {
  name: 'Guardhouse', indoor: true, cam: {horizon: .12, back: .62, front: .91, farScale: .74}, beyond: ['#08090c', '#242a34'], door: 'iron',
  floor: {kind: 'flag', floor: '#666870', floorShade: '#454852', floorLit: '#868a94'}, ambient: '#8b93a6',
  decor: [{prop: 'desk', x: 7.4, d: .38, scale: 1.2, blocking: true}, {prop: 'rack', x: 36, d: .3, scale: 1.1, blocking: true}, {prop: 'bell', x: 22, d: .9, scale: 1.4, blocking: false}, {prop: 'dummy', x: 29, d: .34, blocking: true}],
  particles: {kind: 'dust', n: 12, color: '#dfe8ff'},
  lights: () => [{x: .2, y: .38, r: .3, c: '#ffbe6a', a: .6, flick: .14, hz: 6}, {x: .8, y: .38, r: .3, c: '#ffbe6a', a: .6, flick: .14, hz: 7}, {x: .5, y: .2, r: .4, c: '#b8c8ff', a: .16}],
  live: [{prop: 'torch', xn: .2, yn: -.2, wn: .05, hn: .1, back: true}, {prop: 'torch', xn: .8, yn: -.2, wn: .05, hn: .1, back: true}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    interior(ctx, K, {wall: 'stone', base: '#7a7f8c', ceil: .12, beams: '#2c2620', course: 26});
    // The public charge board and the alarm bell rope.
    inkRect(ctx, K, W * .06, back - 150 * s, 92 * s, 96 * s, '#5a3f2b', 1.6); for (let i = 0; i < 6; i++) { ctx.fillStyle = '#e8dfc6'; ctx.fillRect(W * .06 + (8 + (i % 3) * 28) * s, back - 142 * s + Math.floor(i / 3) * 42 * s, 22 * s, 32 * s); }
    ctx.strokeStyle = '#7a4a2a'; ctx.lineWidth = 4 * s; ctx.beginPath(); ctx.moveTo(W * .5, H * .16); ctx.lineTo(W * .5, back - 30 * s); ctx.stroke();
    for (const x of [.2, .8]) wallTorch(ctx, K, W * x, back - 150 * s);
    skirting(ctx, K, '#3a3c44'); floorPlane(ctx, K, back, H, 'flag', K.floor, {conv: K.cam.farScale});
    finish(ctx, K, {hazeColor: '#2b3040', haze: .1, horizonY: back, vignette: .55});
  },
});
def('alley', {
  name: 'Cinder Alley', cam: {horizon: .36, back: .58, front: .91, farScale: .58}, beyond: ['#08080c', '#1e1a20'], door: 'wood',
  floor: {kind: 'cobble', floor: '#575660', floorShade: '#37363f', floorLit: '#787682'}, ambient: '#5c6790',
  decor: [{prop: 'bin', x: 5.4, d: .3, blocking: true}, {prop: 'crate', x: 38.6, d: .24, blocking: true}, {prop: 'barrel', x: 40.9, d: .3, blocking: true}],
  particles: {kind: 'ash', n: 22, color: '#d8c0a0'},
  lights: K => [{x: .84, y: .4, r: .3, c: '#ffbe6a', a: .6, flick: .16, hz: 7}, {x: .2, y: .3, r: .26, c: '#8aa0ff', a: .3}, {x: .5, y: .46, r: .4, c: '#ff9a5a', a: .2, flick: .1, hz: 3}],
  paint(ctx, K) {
    const {W, H, S: s} = K, T = TOD.night, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: T.bot, y1: back, sun: T.sun, stars: 60, clouds: 2, cloud: T.cloud});
    farTown(ctx, K, back - 20 * s, '#10142a');
    // Two tall brick faces closing in toward the far mouth of the alley.
    const ins = W * .2;
    for (const sd of [-1, 1]) {
      const x0 = sd < 0 ? 0 : W, x1 = sd < 0 ? ins : W - ins;
      poly(ctx, [[x0, 0], [x1, hz * .5], [x1, back], [x0, H]]); ctx.fillStyle = '#4a3f44'; ctx.fill(); ctx.save(); poly(ctx, [[x0, 0], [x1, hz * .5], [x1, back], [x0, H]]); ctx.clip();
      ctx.strokeStyle = rgba(INK, .3); ctx.lineWidth = s; for (let y = 0; y < H; y += 14 * s) { ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, lerp(y * .5, y, .5) * (back / H) + 4); ctx.stroke(); }
      ctx.fillStyle = hgrad(ctx, x0, x1, [[0, 'rgba(0,0,0,.6)'], [1, 'rgba(0,0,0,.1)']]); ctx.fillRect(Math.min(x0, x1), 0, Math.abs(x1 - x0), H);
      for (let i = 0; i < 4; i++) { const t = .18 + i * .2, xx = lerp(x0, x1, t), yy = lerp(H * .16, hz * .6, t) + i * 8 * s, ww = lerp(26, 11, t) * s; windowPane(ctx, K, xx - ww / 2, yy, ww, ww * 1.5, {lit: (i + (sd > 0 ? 1 : 0)) % 3 === 0 ? .8 : 0, frame: '#2a1f22'}); }
      ctx.restore();
    }
    ctx.fillStyle = vgrad(ctx, back - 130 * s, back, [[0, rgba('#c98a5a', 0)], [1, rgba('#c98a5a', .35)]]); ctx.fillRect(ins, back - 130 * s, W - ins * 2, 130 * s);
    // Laundry line across the gap.
    ctx.strokeStyle = rgba(INK, .8); ctx.lineWidth = s; ctx.beginPath(); ctx.moveTo(ins * .9, H * .26); ctx.quadraticCurveTo(W / 2, H * .3, W - ins * .9, H * .24); ctx.stroke();
    for (let i = 0; i < 4; i++) { const t = .24 + i * .16, x = lerp(ins * .9, W - ins * .9, t), y = H * .27 + Math.sin(t * 3) * 2 * s; poly(ctx, [[x, y], [x + 22 * s, y], [x + 20 * s, y + 30 * s], [x + 2 * s, y + 28 * s]]); ctx.fillStyle = ['#c8c1b0', '#8a5a5a', '#5a6a8a', '#b8b0a0'][i]; ctx.fill(); ink(ctx, K, 1); }
    floorPlane(ctx, K, back, H, 'cobble', K.floor, {conv: K.cam.farScale}); puddle(ctx, K, W * .5, back + (H - back) * .5, 150 * s, '#8aa0ff');
    ctx.fillStyle = vgrad(ctx, back, H, [[0, 'rgba(4,6,14,.0)'], [1, 'rgba(4,6,14,.25)']]); ctx.fillRect(0, back, W, H - back);
    finish(ctx, K, {hazeColor: '#5b4a5a', haze: .22, horizonY: back - 30 * s, vignette: .6});
  },
});
def('warehouse', {
  name: 'North Warehouse', indoor: true, cam: {horizon: .1, back: .62, front: .91, farScale: .7}, beyond: ['#070708', '#1c1a18'], door: 'gate',
  floor: {kind: 'plank', floor: '#4d3f34', floorShade: '#30271f', floorLit: '#6f5a48'}, ambient: '#7c7468',
  decor: [{prop: 'crate', x: 5, d: .26, scale: 1.2, blocking: true}, {prop: 'crate', x: 7.6, d: .24, blocking: true}, {prop: 'sack', x: 38, d: .3}, {prop: 'sack', x: 39.6, d: .26}, {prop: 'barrel', x: 22, d: .14, blocking: true}],
  particles: {kind: 'dust', n: 30, color: '#ffe6b0'},
  lights: () => [{x: .3, y: .1, r: .7, c: '#ffe6b0', a: .3, kind: 'shaft'}, {x: .72, y: .1, r: .7, c: '#ffe6b0', a: .24, kind: 'shaft'}, {x: .5, y: .5, r: .3, c: '#ffbe6a', a: .3, flick: .1, hz: 5}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    interior(ctx, K, {wall: 'plank', base: '#6d5a48', ceil: .1, beams: '#33251b', plank: 22});
    // Rafters and the loft with its rope.
    for (let i = 0; i < 6; i++) beam(ctx, K, W * (.05 + i * .18), H * .1, W * (.05 + i * .18), back - 20 * s, 9 * s, '#3f2f22');
    block(ctx, K, W * .05, back - 205 * s, W * .34, 10 * s, '#5a4432', {band: .1}); for (let i = 0; i < 5; i++) block(ctx, K, W * .07 + i * 50 * s, back - 245 * s, 40 * s, 40 * s, '#8a6a45', {band: .2});
    ctx.strokeStyle = '#b79c66'; ctx.lineWidth = 3 * s; ctx.beginPath(); ctx.moveTo(W * .42, H * .1); ctx.lineTo(W * .42, back - 60 * s); ctx.stroke();
    for (let x = W * .5; x < W * .95; x += 26 * s) for (let y = 0; y < 2; y++) block(ctx, K, x, back - 46 * s - y * 34 * s, 24 * s, 32 * s, y ? '#c9b58b' : '#b9a57b', {band: .2, ink: 1});
    skirting(ctx, K, '#2c2118'); floorPlane(ctx, K, back, H, 'plank', K.floor, {conv: K.cam.farScale});
    finish(ctx, K, {hazeColor: '#2c2118', haze: .1, horizonY: back, vignette: .58});
  },
});
def('shrine', {
  name: 'Roadside Shrine', cam: {horizon: .44, back: .62, front: .91, farScale: .66}, beyond: ['#080a10', '#1a2030'], door: 'path',
  floor: {kind: 'dirt', floor: '#5b5647', floorShade: '#3d3a32', floorLit: '#7d7660'},
  decor: [{prop: 'altar', x: 22, d: .78, scale: 1.4, blocking: true}, {prop: 'pouch', x: 9, d: .3}, {prop: 'statue', x: 36, d: .55, scale: .9, blocking: true}],
  particles: {kind: 'fireflies', n: 24, color: '#ffe89a'},
  lights: () => [{x: .5, y: .56, r: .36, c: '#ffcf6b', a: .7, flick: .1, hz: 6}, {x: .78, y: .18, r: .8, c: '#9fb4e6', a: .16}],
  paint(ctx, K) {
    const {W, H, S: s} = K, T = TOD.night, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: '#33406a', y1: hz + 60 * s, sun: T.sun, stars: 110, clouds: 3, cloud: T.cloud});
    ridge(ctx, K, hz - 20 * s, 28, '#131a33'); ridge(ctx, K, hz + 6 * s, 16, '#0f1528');
    ctx.fillStyle = '#0c1020'; ctx.fillRect(0, hz + 20 * s, W, back - hz);
    for (let i = 0; i < 16; i++) { const x = W * (i / 15) + (K.rand() - .5) * 40 * s, h = (70 + K.rand() * 70) * s; pine(ctx, K, x, hz + 44 * s + K.rand() * 10 * s, h, '#16233a', '#0e1626'); }
    for (const b of K.bays) { ctx.fillStyle = vgrad(ctx, back - 170 * s, back, [[0, rgba('#8aa0ff', 0)], [1, rgba('#0a0c14', .95)]]); ctx.fillRect(b.x * W - 70 * s, back - 170 * s, 140 * s, 170 * s); }
    floorPlane(ctx, K, back, H, 'dirt', K.floor, {conv: K.cam.farScale});
    // Stone steps and a lantern-lit shrine roof at the back.
    const cx = W * .5; for (let i = 0; i < 3; i++) block(ctx, K, cx - (120 - i * 16) * s, back - 6 * s - i * 9 * s + 30 * s, (240 - i * 32) * s, 10 * s, '#7d7a74', {band: .18});
    house(ctx, K, {x: cx - 84 * s, base: back + 6 * s, w: 168 * s, h: 82 * s, kind: 'stone', wall: '#7d7a74', roofC: '#3d3a4a', roofH: 46 * s, floors: 1, lit: 0});
    inkPoly(ctx, K, [[cx - 24 * s, back + 6 * s], [cx - 24 * s, back - 56 * s], [cx + 24 * s, back - 56 * s], [cx + 24 * s, back + 6 * s]], '#0a0b12', 1.4);
    for (const x of [-1, 1]) { ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.beginPath(); ctx.moveTo(cx + x * 96 * s, back - 80 * s); ctx.lineTo(cx + x * 96 * s, back - 60 * s); ctx.stroke(); inkPoly(ctx, K, [[cx + x * 96 * s - 6 * s, back - 60 * s], [cx + x * 96 * s + 6 * s, back - 60 * s], [cx + x * 96 * s + 4 * s, back - 44 * s], [cx + x * 96 * s - 4 * s, back - 44 * s]], '#e9c56d', 1.2); }
    finish(ctx, K, {hazeColor: '#33406a', haze: .2, horizonY: hz + 40 * s, vignette: .55});
  },
});
def('homes', {
  name: "Workers' Homes", cam: {horizon: .42, back: .61, front: .91, farScale: .66}, beyond: ['#0c0d12', '#2a2620'], door: 'wood',
  floor: {kind: 'dirt', floor: '#6b6250', floorShade: '#463f33', floorLit: '#8b8066'},
  decor: [{prop: 'barrel', x: 4.4, d: .26, blocking: true}, {prop: 'sack', x: 38, d: .3}, {prop: 'crate', x: 40.5, d: .25, blocking: true}],
  particles: {kind: 'dust', n: 18, color: '#ffe6b0'},
  lights: K => [K.tod.sun && {x: K.tod.sun.x, y: .2, r: .9, c: K.tod.sun.halo, a: .16}, ...(K.tod.lamps ? [{x: .3, y: .5, r: .26, c: '#ffbe6a', a: .55, flick: .1, hz: 5}, {x: .72, y: .5, r: .26, c: '#ffbe6a', a: .5, flick: .1, hz: 6}] : [])].filter(Boolean),
  paint(ctx, K) {
    const {W, H, S: s} = K, T = K.tod, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: T.bot, y1: hz + 40 * s, sun: T.sun, stars: T.stars, clouds: T.clouds, cloud: T.cloud});
    ridge(ctx, K, hz - 14 * s, 22, mixHex(T.far, '#000000', .15)); farTown(ctx, K, hz + 34 * s, mixHex(T.far, '#000000', .45)); ctx.fillStyle = mixHex(T.far, '#000000', .5); ctx.fillRect(0, hz + 30 * s, W, back - hz);
    facadeRow(ctx, K, {base: back, pals: ['#b8a687', '#a99a7c', '#9aa39a', '#c0a488'], lit: T.lamps ? .6 : .2, tallness: [80, 140], kinds: ['timber', 'timber', 'brick'], bayW: 150});
    floorPlane(ctx, K, back, H, 'dirt', K.floor, {conv: K.cam.farScale});
    // Vegetable plots along the near edge and a wash line between two poles.
    for (const [x0, x1] of [[.03, .2], [.8, .97]]) for (let r = 0; r < 3; r++) { const y = back + (H - back) * (.5 + r * .12); ctx.fillStyle = shadeHex('#4a3a2c', .2); ctx.fillRect(W * x0, y, W * (x1 - x0), 5 * s); for (let i = 0; i < 9; i++) ellipse(ctx, W * x0 + i * W * (x1 - x0) / 9 + 8 * s, y - 2 * s, 5 * s, 7 * s, ['#5f8a3c', '#7d9b3f', '#4f7a3c'][i % 3], K.ink, 1, K); }
    for (const x of [.33, .68]) beam(ctx, K, W * x, back - 120 * s, W * x, back + 14 * s, 6 * s, '#5a3f2b');
    ctx.strokeStyle = rgba(INK, .8); ctx.lineWidth = s; ctx.beginPath(); ctx.moveTo(W * .33, back - 108 * s); ctx.quadraticCurveTo(W * .5, back - 92 * s, W * .68, back - 108 * s); ctx.stroke();
    for (let i = 0; i < 5; i++) { const t = .16 + i * .16, x = lerp(W * .33, W * .68, t), y = back - 104 * s + Math.sin(t * Math.PI) * 10 * s; poly(ctx, [[x, y], [x + 24 * s, y], [x + 22 * s, y + 34 * s], [x + 2 * s, y + 32 * s]]); ctx.fillStyle = ['#e8dfc6', '#a86a5a', '#6a8aa8', '#d8cfae', '#8a9a6a'][i]; ctx.fill(); ink(ctx, K, 1); }
    finish(ctx, K, {hazeColor: T.haze, haze: .2, horizonY: back - 20 * s});
  },
});
def('docks', {
  name: 'Canal Docks', cam: {horizon: .40, back: .60, front: .91, farScale: .64}, beyond: ['#080a10', '#1a2028'], door: 'gate',
  floor: {kind: 'plank', floor: '#5b4a3c', floorShade: '#3a2f27', floorLit: '#7a6552'}, ambient: '#6b7ea0',
  decor: [{prop: 'crate', x: 4.4, d: .24, blocking: true}, {prop: 'crate', x: 6.8, d: .2, blocking: true}, {prop: 'barrel', x: 38.8, d: .28, blocking: true}, {prop: 'lamppost', x: 33, d: .16, scale: 1.1, blocking: false}],
  particles: {kind: 'mist', n: 22, color: '#a8c0d8'},
  lights: () => [{x: .75, y: .5, r: .3, c: '#ffbe6a', a: .6, flick: .1, hz: 5}, {x: .5, y: .3, r: .8, c: '#8aa0ff', a: .2}],
  live: [{prop: 'boat', xn: .3, yn: 0, wn: .22, hn: .1, back: true, water: true}],
  paint(ctx, K) {
    const {W, H, S: s} = K, T = K.tod === TOD.day || K.tod === TOD.morning ? K.tod : TOD.night, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: T.bot, y1: hz + 20 * s, sun: T.sun, stars: T.stars, clouds: T.clouds, cloud: T.cloud});
    ridge(ctx, K, hz - 6 * s, 16, mixHex(T.far, '#000000', .3)); farTown(ctx, K, hz + 6 * s, mixHex(T.far, '#000000', .5));
    // Warehouse fronts across the water, then the water itself in bands.
    for (let x = -20; x < W; x += 130 * s) house(ctx, K, {x, base: hz + 30 * s, w: 120 * s, h: (50 + K.rand() * 40) * s, kind: 'stone', wall: '#4a5064', roofC: '#2d3244', floors: 1, lit: .5});
    floorPlane(ctx, K, hz + 28 * s, back + 18 * s, 'water', {floor: '#16283e', floorLit: '#5a86b8', floorShade: '#0b1626'}, {conv: 1});
    ctx.fillStyle = rgba('#ffcf6b', .16); for (let i = 0; i < 6; i++) ctx.fillRect(W * .72 + (K.rand() - .5) * 30 * s, hz + 40 * s + i * 14 * s, 8 * s + K.rand() * 20 * s, 3 * s);
    // The pier the party stands on, with mooring posts along its edge.
    floorPlane(ctx, K, back + 12 * s, H, 'plank', K.floor, {conv: K.cam.farScale});
    beam(ctx, K, 0, back + 12 * s, W, back + 12 * s, 10 * s, '#4a3626');
    for (let x = W * .05; x < W; x += W * .13) { block(ctx, K, x, back - 16 * s, 10 * s, 34 * s, '#5a4432', {band: .3}); ellipse(ctx, x + 5 * s, back - 16 * s, 6 * s, 3 * s, '#7a6048', K.ink, 1, K); }
    finish(ctx, K, {hazeColor: '#7a90b0', haze: .3, horizonY: hz + 30 * s, vignette: .55});
  },
});
def('camp', {
  name: 'Bandit Camp', cam: {horizon: .40, back: .60, front: .91, farScale: .66}, beyond: ['#06080c', '#141a14'], door: 'path',
  floor: {kind: 'dirt', floor: '#4a4234', floorShade: '#2f2a21', floorLit: '#6b5f48'}, ambient: '#5f6d88',
  decor: [{prop: 'crate', x: 5, d: .3, blocking: true}, {prop: 'barrel', x: 38, d: .32, blocking: true}, {prop: 'dummy', x: 33, d: .4, blocking: true}],
  particles: {kind: 'embers', n: 26, color: '#ffa050'},
  lights: () => [{x: .5, y: .68, r: .55, c: '#ff8a3d', a: .95, flick: .22, hz: 9}, {x: .8, y: .1, r: .8, c: '#9fb4e6', a: .16}],
  live: [{prop: 'campfire', xn: .5, yn: .17, wn: .12, hn: .16, front: true}],
  paint(ctx, K) {
    const {W, H, S: s} = K, T = TOD.night, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: '#2c3a60', y1: hz + 60 * s, sun: T.sun, stars: 100, clouds: 2, cloud: T.cloud});
    ridge(ctx, K, hz - 14 * s, 26, '#111830'); ctx.fillStyle = '#0c1020'; ctx.fillRect(0, hz + 30 * s, W, back - hz);
    for (let i = 0; i < 20; i++) pine(ctx, K, W * (i / 19) + (K.rand() - .5) * 30 * s, hz + 46 * s + K.rand() * 14 * s, (80 + K.rand() * 80) * s, '#132038', '#0c1526');
    // A palisade with a watch platform behind the camp.
    for (let x = -10 * s; x < W; x += 15 * s) { const h = (58 + K.rand() * 14) * s; poly(ctx, [[x, back], [x, back - h], [x + 7.5 * s, back - h - 12 * s], [x + 15 * s, back - h], [x + 15 * s, back]]); ctx.fillStyle = shadeHex('#6b5a44', .15 + K.rand() * .1); ctx.fill(); ink(ctx, K, 1); }
    block(ctx, K, W * .12, back - 130 * s, 70 * s, 12 * s, '#4a3626', {band: .2}); beam(ctx, K, W * .14, back - 118 * s, W * .14, back - 20 * s, 6 * s, '#3f2f22'); beam(ctx, K, W * .12 + 62 * s, back - 118 * s, W * .12 + 62 * s, back - 20 * s, 6 * s, '#3f2f22');
    for (const b of K.bays) { ctx.fillStyle = '#05070c'; ctx.fillRect(b.x * W - 34 * s, back - 96 * s, 68 * s, 96 * s); beam(ctx, K, b.x * W - 38 * s, back - 100 * s, b.x * W - 38 * s, back, 8 * s, '#4a3626'); beam(ctx, K, b.x * W + 38 * s, back - 100 * s, b.x * W + 38 * s, back, 8 * s, '#4a3626'); beam(ctx, K, b.x * W - 42 * s, back - 100 * s, b.x * W + 42 * s, back - 100 * s, 8 * s, '#4a3626'); }
    floorPlane(ctx, K, back, H, 'dirt', K.floor, {conv: K.cam.farScale});
    groundPool(ctx, W * .5, back + (H - back) * .45, 320 * s, 90 * s, '#ff8a3d', .3);
    finish(ctx, K, {hazeColor: '#2c3a60', haze: .16, horizonY: hz + 40 * s, vignette: .6});
  },
});

// ---- The descent -------------------------------------------------------------
def('foundry', {
  name: 'The Machine Works', indoor: true, cam: {horizon: .1, back: .62, front: .91, farScale: .7}, beyond: ['#05060a', '#2a1a10'], door: 'hatch',
  floor: {kind: 'metal', floor: '#41464f', floorShade: '#272b32', floorLit: '#5f6672'}, ambient: '#8a7c78',
  decor: [{prop: 'crate', x: 4.6, d: .26, blocking: true}, {prop: 'barrel', x: 39, d: .3, blocking: true}, {prop: 'pillar', x: 14, d: .82, scale: .7, blocking: true}, {prop: 'pillar', x: 30, d: .82, scale: .7, blocking: true}],
  particles: {kind: 'steam', n: 22, color: '#d8dee8'},
  lights: () => [{x: .5, y: .62, r: .5, c: '#ff7a2a', a: .8, flick: .2, hz: 3}, {x: .15, y: .3, r: .3, c: '#ff9a4a', a: .4, flick: .1, hz: 2}, {x: .86, y: .3, r: .3, c: '#5ad8ff', a: .35, flick: .05, hz: 4}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    interior(ctx, K, {wall: 'metal', base: '#4c525c', ceil: .12, beams: '#2a2e36'});
    // Gantries, pipes, and a furnace mouth glowing at the back.
    for (const y of [.3, .46]) { beam(ctx, K, 0, H * y, W, H * y, 8 * s, '#2f333c'); for (let x = 0; x < W; x += 60 * s) beam(ctx, K, x, H * y, x + 30 * s, H * (y + .05), 3 * s, '#2f333c'); }
    for (const [x, c] of [[.08, '#6a6f7a'], [.14, '#5a4038'], [.9, '#6a6f7a']]) { ctx.fillStyle = hgrad(ctx, W * x - 12 * s, W * x + 12 * s, [[0, lightHex(c, .16)], [.6, c], [.6, shadeHex(c, .35)], [1, shadeHex(c, .35)]]); ctx.fillRect(W * x - 12 * s, 0, 24 * s, back); ctx.strokeStyle = K.ink; ctx.lineWidth = s; ctx.strokeRect(W * x - 12 * s, 0, 24 * s, back); }
    ctx.fillStyle = vgrad(ctx, back - 140 * s, back, [[0, '#2a1208'], [1, '#ff7a2a']]); ctx.beginPath(); ctx.moveTo(W * .36, back); ctx.lineTo(W * .36, back - 100 * s); ctx.quadraticCurveTo(W * .5, back - 160 * s, W * .64, back - 100 * s); ctx.lineTo(W * .64, back); ctx.fill(); ink(ctx, K, 1.6);
    skirting(ctx, K, '#1f2228'); floorPlane(ctx, K, back, H, 'metal', K.floor, {conv: K.cam.farScale});
    // Conveyor lanes running toward the viewer.
    for (const x of [.24, .76]) { poly(ctx, [[W * x - 26 * s * K.cam.farScale, back], [W * x + 26 * s * K.cam.farScale, back], [W * x + 60 * s, H], [W * x - 60 * s, H]]); ctx.fillStyle = '#20232a'; ctx.fill(); ink(ctx, K, 1.4); }
    groundPool(ctx, W * .5, back + 14 * s, 300 * s, 46 * s, '#ff7a2a', .35);
    finish(ctx, K, {hazeColor: '#3a2a26', haze: .14, horizonY: back, vignette: .6});
  },
});
def('lair', {
  name: 'The Three Dragons', indoor: true, cam: {horizon: .1, back: .62, front: .91, farScale: .68}, beyond: ['#050507', '#1c1418'], door: 'arch',
  floor: {kind: 'flag', floor: '#5a5560', floorShade: '#37333f', floorLit: '#7d7784'}, ambient: '#766c7e',
  decor: [{prop: 'pillar', x: 8, d: .6, scale: 1, blocking: true}, {prop: 'pillar', x: 36, d: .6, scale: 1, blocking: true}, {prop: 'crate', x: 22, d: .3, blocking: true}, {prop: 'brazier', x: 14, d: .82, blocking: true}, {prop: 'brazier', x: 22, d: .84, blocking: true}, {prop: 'brazier', x: 30, d: .82, blocking: true}],
  particles: {kind: 'embers', n: 20, color: '#ffb070'},
  lights: () => [{x: .32, y: .58, r: .3, c: '#e8f0ff', a: .5, flick: .12, hz: 5}, {x: .5, y: .58, r: .3, c: '#ff5a3a', a: .6, flick: .14, hz: 6}, {x: .68, y: .58, r: .3, c: '#8a6aff', a: .5, flick: .12, hz: 5}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    interior(ctx, K, {wall: 'stone', base: '#4d4a58', ceil: .12, beams: null, course: 34, moss: .05, inset: true});
    // Three territories: white, red, black banners over a gallery of hoard.
    for (const [x, c] of [[.16, '#d8e0ee'], [.5, '#a02c2c'], [.84, '#241f30']]) { poly(ctx, [[W * x - 34 * s, H * .18], [W * x + 34 * s, H * .18], [W * x + 30 * s, H * .5], [W * x, H * .56], [W * x - 30 * s, H * .5]]); ctx.fillStyle = c; ctx.fill(); ink(ctx, K, 1.5); ctx.fillStyle = rgba('#000', .28); ctx.beginPath(); ctx.moveTo(W * x, H * .18); ctx.lineTo(W * x + 34 * s, H * .18); ctx.lineTo(W * x + 30 * s, H * .5); ctx.lineTo(W * x, H * .56); ctx.fill(); }
    for (let i = 0; i < 50; i++) { const x = W * (.3 + K.rand() * .4), y = back - K.rand() * 26 * s; ellipse(ctx, x, y, 5 * s, 3 * s, K.rand() < .6 ? '#d9b04a' : '#f0d27a', K.ink, .8, K); }
    skirting(ctx, K, '#2c2a34'); floorPlane(ctx, K, back, H, 'flag', K.floor, {conv: K.cam.farScale});
    finish(ctx, K, {hazeColor: '#3a2f45', haze: .14, horizonY: back, vignette: .62});
  },
});
def('drowned', {
  name: 'The Sunless Sea', cam: {horizon: .34, back: .58, front: .91, farScale: .62}, beyond: ['#04070c', '#0e2030'], door: 'path',
  floor: {kind: 'plank', floor: '#3f4a48', floorShade: '#253030', floorLit: '#5c6f6a'}, ambient: '#4a6a80',
  decor: [{prop: 'barrel', x: 5, d: .28, blocking: true}, {prop: 'crate', x: 38, d: .3, blocking: true}, {prop: 'lamppost', x: 12, d: .4, scale: 1.1, blocking: false}, {prop: 'bell', x: 31, d: .75, scale: 1.3, blocking: false}],
  particles: {kind: 'mist', n: 30, color: '#8fc0c8'},
  lights: () => [{x: .24, y: .5, r: .3, c: '#8fffd8', a: .5, flick: .1, hz: 3}, {x: .74, y: .5, r: .3, c: '#8fffd8', a: .45, flick: .1, hz: 4}, {x: .5, y: .2, r: .8, c: '#4a90b0', a: .14}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K), hz = K.cam.horizon * H;
    ctx.fillStyle = vgrad(ctx, 0, back, [[0, '#02060c'], [.6, '#0a1a2a'], [1, '#17364a']]); ctx.fillRect(0, 0, W, back);
    // Broken ship ribs against a cave dark, and the black water between decks.
    for (let i = 0; i < 9; i++) { const x = W * (.05 + i * .11), h = (120 + K.rand() * 90) * s; ctx.strokeStyle = '#1b2a2e'; ctx.lineWidth = 7 * s; ctx.beginPath(); ctx.moveTo(x, hz + 40 * s); ctx.quadraticCurveTo(x + 30 * s * (i % 2 ? 1 : -1), hz - h * .5, x + 8 * s, hz + 40 * s - h); ctx.stroke(); ctx.strokeStyle = K.ink; ctx.lineWidth = 1.2 * s; ctx.stroke(); }
    for (let i = 0; i < 40; i++) { const x = K.rand() * W, y = K.rand() * hz * .8; ctx.fillStyle = rgba('#8fffd8', .1 + K.rand() * .2); ctx.fillRect(x, y, 1.6 * s, 1.6 * s); }
    floorPlane(ctx, K, hz + 34 * s, back + 30 * s, 'water', {floor: '#0d1d2c', floorLit: '#3a7a9a', floorShade: '#050d16'}, {conv: 1});
    floorPlane(ctx, K, back + 10 * s, H, 'plank', K.floor, {conv: K.cam.farScale});
    beam(ctx, K, 0, back + 10 * s, W, back + 10 * s, 10 * s, '#2c3634');
    for (let x = W * .06; x < W; x += W * .12) { block(ctx, K, x, back - 20 * s, 10 * s, 38 * s, '#3a4642', {band: .3}); }
    finish(ctx, K, {hazeColor: '#3a7a8a', haze: .3, horizonY: hz + 30 * s, vignette: .62});
  },
});
def('palace', {
  name: 'The Opulent Palace', indoor: true, cam: {horizon: .1, back: .62, front: .91, farScale: .7}, beyond: ['#0a0810', '#2a2030'], door: 'wood',
  floor: {kind: 'tile', floor: '#b9b0a0', floorShade: '#7d7565', floorLit: '#e2dac8'}, ambient: '#b0a496',
  decor: [{prop: 'pillar', x: 9, d: .7, scale: 1.15, blocking: true}, {prop: 'pillar', x: 35, d: .7, scale: 1.15, blocking: true}, {prop: 'statue', x: 4, d: .3, scale: .9, blocking: true}, {prop: 'statue', x: 40, d: .3, scale: .9, blocking: true}],
  particles: {kind: 'dust', n: 26, color: '#ffe9b0'},
  lights: () => [{x: .5, y: .55, r: .5, c: '#ffd27a', a: .7, flick: .06, hz: 2}, {x: .5, y: .1, r: .5, c: '#ffe9b0', a: .5, flick: .04, hz: 3}],
  live: [{prop: 'cocoon', xn: .5, yn: .0, wn: .2, hn: .4, back: true}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    interior(ctx, K, {wall: 'marble', base: '#cfc5b0', ceil: .12, beams: '#8a7440', inset: true, sideTone: '#8a8070'});
    // Gilded columns down both sides of the hall and balconies above.
    for (const x of [.08, .22, .78, .92]) pillar(ctx, K, W * x, back, 26 * s, back - H * .16, '#e0d6bf');
    for (const sd of [-1, 1]) { block(ctx, K, sd < 0 ? 0 : W * .7, H * .28, W * .3, 10 * s, '#a88a4a', {band: .2}); for (let i = 0; i < 9; i++) { ctx.fillStyle = '#8a7440'; ctx.fillRect((sd < 0 ? 0 : W * .7) + i * W * .034, H * .28 + 10 * s, 4 * s, 32 * s); } }
    ctx.fillStyle = '#8a7440'; ctx.fillRect(0, back - 6 * s, W, 6 * s);
    skirting(ctx, K, '#8a7440'); floorPlane(ctx, K, back, H, 'tile', K.floor, {conv: K.cam.farScale});
    ctx.fillStyle = vgrad(ctx, back, H, [[0, 'rgba(255,240,200,.22)'], [1, 'rgba(255,240,200,0)']]); ctx.fillRect(0, back, W, H - back);
    finish(ctx, K, {hazeColor: '#e0d0a0', haze: .12, horizonY: back, vignette: .5});
  },
});
def('crypt', {
  name: 'The Crypt', indoor: true, cam: {horizon: .1, back: .62, front: .91, farScale: .7}, beyond: ['#04050a', '#101828'], door: 'arch',
  floor: {kind: 'flag', floor: '#4d5260', floorShade: '#2d313c', floorLit: '#6d7382'}, ambient: '#5a6a8a',
  decor: [{prop: 'coffin', x: 8, d: .5, scale: 1.1, blocking: true}, {prop: 'coffin', x: 36, d: .5, scale: 1.1, blocking: true}, {prop: 'pillar', x: 15, d: .8, scale: .9, blocking: true}, {prop: 'pillar', x: 29, d: .8, scale: .9, blocking: true}, {prop: 'brazier', x: 22, d: .3, blocking: true}],
  particles: {kind: 'mist', n: 22, color: '#8aa8d0'},
  lights: () => [{x: .5, y: .7, r: .4, c: '#6ab0ff', a: .5, flick: .1, hz: 3}, {x: .15, y: .4, r: .3, c: '#7a9aff', a: .3, flick: .08, hz: 4}, {x: .85, y: .4, r: .3, c: '#7a9aff', a: .3, flick: .08, hz: 5}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    interior(ctx, K, {wall: 'stone', base: '#4a5060', ceil: .12, beams: null, course: 24, moss: .12});
    for (let i = 0; i < 5; i++) { const x = W * (.1 + i * .2); arch(ctx, K, x, back - 16 * s, 58 * s, 118 * s, '#5a6070', {dark: '#04060c', keystone: false}); block(ctx, K, x - 24 * s, back - 60 * s, 48 * s, 26 * s, '#6a7080', {band: .25}); }
    skirting(ctx, K, '#2d313c'); floorPlane(ctx, K, back, H, 'flag', K.floor, {conv: K.cam.farScale});
    finish(ctx, K, {hazeColor: '#28304a', haze: .2, horizonY: back, vignette: .68});
  },
});
def('dungeon', {
  name: 'The Lower Hall', indoor: true, cam: {horizon: .1, back: .62, front: .91, farScale: .7}, beyond: ['#040508', '#141820'], door: 'iron',
  floor: {kind: 'flag', floor: '#5a5d66', floorShade: '#353840', floorLit: '#7b7f8a'}, ambient: '#74788a',
  decor: [{prop: 'pillar', x: 10, d: .7, blocking: true}, {prop: 'pillar', x: 34, d: .7, blocking: true}, {prop: 'crate', x: 4.6, d: .26, blocking: true}, {prop: 'barrel', x: 39, d: .3, blocking: true}],
  particles: {kind: 'dust', n: 14, color: '#c8d4ff'},
  lights: () => [{x: .2, y: .38, r: .32, c: '#ffbe6a', a: .65, flick: .16, hz: 6}, {x: .8, y: .38, r: .32, c: '#ffbe6a', a: .65, flick: .16, hz: 7}],
  live: [{prop: 'torch', xn: .2, yn: -.2, wn: .05, hn: .1, back: true}, {prop: 'torch', xn: .8, yn: -.2, wn: .05, hn: .1, back: true}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    interior(ctx, K, {wall: 'stone', base: '#565a68', ceil: .12, beams: '#2a2620', course: 26, moss: .06});
    for (const x of [.2, .8]) wallTorch(ctx, K, W * x, back - 150 * s);
    skirting(ctx, K, '#30333c'); floorPlane(ctx, K, back, H, 'flag', K.floor, {conv: K.cam.farScale});
    finish(ctx, K, {hazeColor: '#232838', haze: .14, horizonY: back, vignette: .62});
  },
});
def('cave', {
  name: 'The Deep Cavern', indoor: true, cam: {horizon: .1, back: .62, front: .91, farScale: .68}, beyond: ['#030407', '#0c1418'], door: 'path',
  floor: {kind: 'dirt', floor: '#4a4a52', floorShade: '#2c2c34', floorLit: '#6a6a74'}, ambient: '#586080',
  decor: [{prop: 'barrel', x: 5, d: .3, blocking: true}, {prop: 'crate', x: 38.6, d: .3, blocking: true}],
  particles: {kind: 'spores', n: 30, color: '#8fffd0'},
  lights: () => [{x: .25, y: .5, r: .3, c: '#6affc0', a: .55, flick: .1, hz: 2}, {x: .7, y: .45, r: .34, c: '#6ab0ff', a: .45, flick: .1, hz: 3}],
  paint(ctx, K) {
    const {W, H, S: s} = K, back = Yb(K);
    ctx.fillStyle = vgrad(ctx, 0, back, [[0, '#05060b'], [1, '#22252f']]); ctx.fillRect(0, 0, W, back);
    ridge(ctx, K, back - 120 * s, 40, '#1a1c25', {step: 34}); ridge(ctx, K, back - 40 * s, 24, '#262932', {step: 26});
    for (let i = 0; i < 18; i++) { const x = W * (i / 17) + (K.rand() - .5) * 30 * s, h = (30 + K.rand() * 90) * s, w = (10 + K.rand() * 18) * s; poly(ctx, [[x - w, 0], [x + w, 0], [x, h]]); ctx.fillStyle = shadeHex('#2b2e38', K.rand() * .3); ctx.fill(); ink(ctx, K, 1.2); }
    for (let i = 0; i < 9; i++) { const x = W * (.05 + i * .11) + K.rand() * 30 * s, h = (16 + K.rand() * 30) * s, w = (8 + K.rand() * 12) * s; poly(ctx, [[x - w, back], [x, back - h], [x + w, back]]); ctx.fillStyle = '#31343e'; ctx.fill(); ink(ctx, K, 1.2); }
    for (let i = 0; i < 9; i++) { const x = W * (.1 + K.rand() * .8), y = back - K.rand() * 20 * s; ellipse(ctx, x, y, 4 * s, 6 * s, i % 2 ? '#6affc0' : '#6ab0ff'); glow(ctx, x, y, 26 * s, i % 2 ? '#6affc0' : '#6ab0ff', .3); }
    floorPlane(ctx, K, back, H, 'dirt', K.floor, {conv: K.cam.farScale});
    finish(ctx, K, {hazeColor: '#2a3448', haze: .2, horizonY: back, vignette: .68});
  },
});
def('forest', {
  name: 'Forest Road', cam: {horizon: .42, back: .60, front: .91, farScale: .66}, beyond: ['#080c0a', '#1a2418'], door: 'path',
  floor: {kind: 'dirt', floor: '#5b5040', floorShade: '#3a3328', floorLit: '#7b6d55'},
  decor: [{prop: 'barrel', x: 5, d: .3, blocking: true}],
  particles: {kind: 'fireflies', n: 18, color: '#ffe89a'},
  lights: K => [K.tod.sun && {x: K.tod.sun.x, y: .2, r: .9, c: K.tod.sun.halo, a: .18}].filter(Boolean),
  paint(ctx, K) {
    const {W, H, S: s} = K, T = K.tod, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: T.bot, y1: hz + 40 * s, sun: T.sun, stars: T.stars, clouds: T.clouds, cloud: T.cloud});
    ridge(ctx, K, hz - 20 * s, 26, mixHex(T.far, '#000000', .1)); ridge(ctx, K, hz + 4 * s, 18, mixHex(T.far, '#000000', .3));
    ctx.fillStyle = mixHex(T.far, '#000000', .5); ctx.fillRect(0, hz + 24 * s, W, back - hz);
    for (let i = 0; i < 14; i++) tree(ctx, K, W * (i / 13) + (K.rand() - .5) * 40 * s, hz + 50 * s + K.rand() * 20 * s, (110 + K.rand() * 70) * s, mixHex('#3f6a3a', T.far, .5));
    for (const b of K.bays) { ctx.fillStyle = vgrad(ctx, back - 160 * s, back, [[0, rgba(T.bot, .0)], [1, rgba('#0a0e0a', .9)]]); ctx.fillRect(b.x * W - 60 * s, back - 160 * s, 120 * s, 160 * s); }
    floorPlane(ctx, K, back, H, 'dirt', K.floor, {conv: K.cam.farScale});
    for (const x of [.04, .96]) tree(ctx, K, W * x, H * .96, 330 * s, mixHex('#2f5a30', '#000000', .2));
    finish(ctx, K, {hazeColor: T.haze, haze: .2, horizonY: back - 20 * s});
  },
});
def('arena', {
  name: 'Training Yard', cam: {horizon: .40, back: .60, front: .91, farScale: .68}, beyond: ['#0a0c12', '#20252f'], door: 'gate',
  floor: {kind: 'dirt', floor: '#7d6f56', floorShade: '#54493a', floorLit: '#a09070'},
  decor: [{prop: 'dummy', x: 26, d: .42, blocking: true}, {prop: 'dummy', x: 33, d: .55, blocking: true}, {prop: 'post', x: 19, d: .6, blocking: true}, {prop: 'rack', x: 40, d: .82, scale: 1.1}],
  particles: {kind: 'dust', n: 20, color: '#ffe6b0'},
  lights: K => [K.tod.sun && {x: K.tod.sun.x, y: .2, r: .9, c: K.tod.sun.halo, a: .2}, ...(K.tod.lamps ? [{x: .2, y: .5, r: .3, c: '#ffbe6a', a: .5, flick: .1, hz: 5}, {x: .8, y: .5, r: .3, c: '#ffbe6a', a: .5, flick: .1, hz: 6}] : [])].filter(Boolean),
  paint(ctx, K) {
    const {W, H, S: s} = K, T = K.tod, back = Yb(K), hz = K.cam.horizon * H;
    sky(ctx, K, {top: T.top, mid: T.mid, bot: T.bot, y1: hz + 40 * s, sun: T.sun, stars: T.stars, clouds: T.clouds, cloud: T.cloud});
    ridge(ctx, K, hz - 16 * s, 22, mixHex(T.far, '#000000', .15));
    // A stone yard wall with a timber gallery.
    stoneWall(ctx, K, 0, back - 130 * s, W, back, '#8a8478', {course: 24, moss: .03});
    for (let x = 0; x < W; x += 60 * s) block(ctx, K, x, back - 138 * s, 40 * s, 12 * s, '#9a9488', {band: .2});
    floorPlane(ctx, K, back, H, 'dirt', K.floor, {conv: K.cam.farScale});
    ctx.strokeStyle = rgba('#e8dfc6', .3); ctx.lineWidth = 2 * s; ctx.beginPath(); ctx.ellipse(W / 2, back + (H - back) * .5, W * .36, (H - back) * .34, 0, 0, TAU); ctx.stroke();
    finish(ctx, K, {hazeColor: T.haze, haze: .14, horizonY: back - 20 * s});
  },
});

// ---------------------------------------------------------------------------
// Which theme a room gets. Town locations by id; descent floors by the words
// the host gives their terrain and name; anything else by a stable hash.
const TOWN = {market: 'market', well: 'well', waterwheel: 'waterwheel', tavern: 'tavern', rooms: 'rooms', guardhouse: 'guardhouse', alley: 'alley', warehouse: 'warehouse',
  shrine: 'shrine', homes: 'homes', docks: 'docks', camp: 'camp'};
export function themeFor(room = {}, scene = {}) {
  const id = String(room.id || room.room_id || '').toLowerCase();
  if (TOWN[id]) return TOWN[id];
  const words = `${room.name || ''} ${room.terrain || ''} ${room.apparent_function || ''} ${scene.location || ''} ${id}`.toLowerCase();
  if (/machine|conveyor|steam|gantry|foundry|works/.test(words)) return 'foundry';
  if (/dragon|hoard|gallery|lair|territor/.test(words)) return 'lair';
  if (/sunless|drown|pier|deck|ferry|sea\b|dark water/.test(words)) return 'drowned';
  if (/palace|cocoon|opulent|balcon|polished/.test(words)) return 'palace';
  if (/crypt|tomb|grave|ossuary|coffin/.test(words)) return 'crypt';
  if (/cave|cavern|grotto|fungus/.test(words)) return 'cave';
  if (/forest|wood|road|trail|glade/.test(words)) return 'forest';
  if (/town|market|lane|well|stall/.test(words)) return 'market';
  const pool = ['dungeon', 'crypt', 'cave', 'dungeon'];
  return pool[hash32(id || 'room') % pool.length];
}
export const THEME_IDS = Object.freeze(Object.keys(THEMES));

// ---------------------------------------------------------------------------
// Doors: which exit gets which kind, and where along the back wall.
const DEST_DOOR = {tavern: 'wood', guardhouse: 'iron', rooms: 'wood', warehouse: 'gate', docks: 'gate', waterwheel: 'gate', alley: 'arch', well: 'path', market: 'path', shrine: 'path', homes: 'wood', camp: 'path', hatch: 'hatch'};
export function layoutExits(theme, exits = []) {
  const n = exits.length; if (!n) return [];
  return exits.map(([key, dest], i) => {
    const id = String(dest?.id || dest?.to || dest?.destination || dest);
    const x = n === 1 ? .5 : .11 + i * (.78 / (n - 1));
    let kind = DEST_DOOR[id] || theme.door;
    if (theme.indoor && kind === 'path') kind = 'arch';
    const open = kind === 'path';
    return {key, id, name: dest?.name || id.replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), x, kind, locked: Boolean(dest?.locked), w: open ? 5.4 : kind === 'gate' ? 6 : 4, h: open ? 8.4 : kind === 'gate' ? 8.4 : 7.6};
  });
}

// ---------------------------------------------------------------------------
// Baking and per-frame drawing.
export const PPF = .0575;                                   // px per foot at d = 0, as a fraction of scene height
export function camOf(theme) { return {...theme.cam}; }
export function bakeSet(themeId, W, H, {seed = 'set', tod = 'evening', bays = [], dpr = Math.min(2, globalThis.devicePixelRatio || 1)} = {}) {
  const theme = THEMES[themeId] || THEMES.market;
  const canvas = globalThis.document ? document.createElement('canvas') : {getContext: () => null};
  canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
  const ctx = canvas.getContext('2d'); if (!ctx) return canvas;
  ctx.scale(dpr, dpr);
  const K = kit(W, H, rng(`${themeId}:${seed}`), theme.cam);
  Object.assign(K, {tod: TOD[todOf(tod)], bays, floor: theme.floor, ppf: PPF * H, theme});
  theme.paint(ctx, K);
  return canvas;
}
// The animated back layer: doors, live props, water shimmer. `state` is
// {t (s), doors: Map(key -> {open, hover}), objects: hover ids}.
export function drawLive(ctx, theme, W, H, {t = 0, bays = [], doors = new Map(), tod = 'evening'} = {}) {
  const K = kit(W, H, Math.random, theme.cam); K.tod = TOD[todOf(tod)]; K.ppf = PPF * H;
  const back = theme.cam.back * H, fs = theme.cam.farScale;
  for (const item of theme.live) {
    const w = item.wn * W, h = item.hn * H, x = item.xn * W, y = item.front ? (theme.cam.back + (theme.cam.front - theme.cam.back) * (item.yn ?? .2)) * H : back + (item.yn || 0) * H;
    ctx.save(); ctx.translate(x, y);
    if (item.prop === 'wheel') { ctx.translate(0, -h * .05); drawProp(ctx, K, 'wheel', w, h * 1.4, {t}); }
    else if (item.prop === 'boat') { ctx.translate(0, Math.sin(t * 1.4) * 2 * K.S); drawProp(ctx, K, 'boat', w, h * 2.4, {t}); }
    else drawProp(ctx, K, item.prop, w, h, {t, open: 0});
    ctx.restore();
  }
  for (const b of bays) {
    const st = doors.get(b.key) || {open: 0, hover: 0};
    const s = K.ppf * fs;
    drawDoor(ctx, K, b.kind, b.x * W, back + 2 * K.S, b.w * s, b.h * s, st.open, {beyond: theme.beyond, hover: st.hover, locked: b.locked, t});
  }
}
export function tint(themeId, tod = 'evening') { const t = THEMES[themeId]; return t.indoor ? t.ambient || '#8a8fa0' : (t.ambient && (t.id === 'alley' || t.id === 'docks' || t.id === 'camp' || t.id === 'shrine') ? t.ambient : TOD[todOf(tod)].ambient); }
export {PPF as PX_PER_FOOT};
