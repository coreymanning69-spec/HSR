// Hero part painters: the art half of hero-rig.js.
//
// Every painter draws in its bone's local frame (+y runs down the bone, the
// figure faces +x in a three-quarter view) in rig units, using the Actor Look's
// palette. Light comes from the back (-x): each part holds its base colour to
// the split and takes one shade toward the front edge, matching the champion
// rigs. Clean Cel: one ink weight, two-tone flat fills, metal gets one
// posterized highlight band, detail only where it reads.

import {INK, TAU, capsule, celGradient, celRamp, dot, fillStroke, glowGradient, poly, rgba, stroke} from './actor-core.js';
import {ELEMENT_COLOUR, MATERIALS} from './actor-look.js';

const LW = .55;
const cel = (ctx, x0, x1, base, shade, split = .62) => celGradient(ctx, x0, x1, base, shade, split);
const metalRamp = (ctx, x0, x1, m) => celRamp(ctx, x0, 0, x1, 0, [[0, m.hi], [.3, m.base], [.72, m.shade], [1, m.deep]]);

// ---------------------------------------------------------------------------
// HEAD. Frame: head joint (top of the neck, just under the jaw); the skull
// rises to -13.5 at unit head scale. Painted at unit scale; the rig scales it.
export const HEAD_TOP = 13.5;

function faceOutline(ctx, shape, jaw = 1) {
  const j = jaw;
  ctx.beginPath(); ctx.moveTo(-4.9, -8.2);
  if (shape === 'round') {
    ctx.bezierCurveTo(-5.4, -13.6, 5.2, -14.8, 6.3, -8.8);
    ctx.bezierCurveTo(7, -5.4, 6.5, -2.2, 4.4, -.2 * j);
    ctx.quadraticCurveTo(2, 1.6, -.8, .9);
    ctx.bezierCurveTo(-3.9, 0, -4.9, -3.8, -4.9, -8.2);
  } else if (shape === 'narrow') {
    ctx.bezierCurveTo(-5, -13.8, 4.2, -14.9, 5.3, -9);
    ctx.bezierCurveTo(5.8, -5.6, 5.3, -2, 3.4, .2);
    ctx.quadraticCurveTo(1.6, 1.9, -.6, 1.1);
    ctx.bezierCurveTo(-3.4, -.3, -4.9, -4, -4.9, -8.2);
  } else if (shape === 'angular') {
    ctx.bezierCurveTo(-5.2, -13.4, 4.6, -14.6, 5.9, -8.8);
    ctx.lineTo(6.2, -5.2); ctx.lineTo(5.3, -2.6 * j);
    ctx.lineTo(4.3 * j, -.1); ctx.lineTo(1.6, 1.1); ctx.lineTo(-.8, .6);
    ctx.lineTo(-3.6, -.8); ctx.bezierCurveTo(-4.6, -3, -4.9, -5, -4.9, -8.2);
  } else if (shape === 'soft') {
    ctx.bezierCurveTo(-5.3, -13.4, 4.8, -14.5, 6, -8.8);
    ctx.bezierCurveTo(6.7, -5.2, 6.1, -2.1, 4.1, -.1);
    ctx.bezierCurveTo(2.8, 1.5, .2, 1.6, -1, .8);
    ctx.bezierCurveTo(-3.8, -.2, -4.9, -4, -4.9, -8.2);
  } else {
    ctx.bezierCurveTo(-5.2, -13.4, 4.6, -14.6, 5.9, -8.8);
    ctx.bezierCurveTo(6.5, -5.4, 5.9, -2.6 * j, 4.1 * j, -.4);
    ctx.quadraticCurveTo(2, 1.3, -.6, .6);
    ctx.bezierCurveTo(-3.6, -.4, -4.9, -4, -4.9, -8.2);
  }
  ctx.closePath();
}

function ear(ctx, P, look) {
  const size = look.earSize, kind = look.ears;
  ctx.save(); ctx.translate(-3.5, -7.4);
  ctx.beginPath();
  if (kind === 'standard' && size < 2.5) {
    ctx.moveTo(.3, -1.6); ctx.bezierCurveTo(-1.9, -2.4, -2.4, 1.6, -.4, 2.2); ctx.quadraticCurveTo(.4, 1.8, .6, .6);
  } else {
    // Pointed ears grow back and up with the race; swept ones run back flat.
    const len = kind === 'standard' ? size * .7 : size, up = kind === 'swept' ? .35 : 1;
    ctx.moveTo(.4, -1.4); ctx.lineTo(-1.4 - len * .9, -1.6 - len * up);
    if (kind === 'notched') { ctx.lineTo(-1.2 - len * .55, -.9 - len * up * .45); ctx.lineTo(-1.6 - len * .6, -.4 - len * up * .5); }
    ctx.quadraticCurveTo(-1.6, 1, -.3, 2.3); ctx.quadraticCurveTo(.5, 1.8, .6, .6);
  }
  ctx.closePath();
  fillStroke(ctx, cel(ctx, -2.4 - size, .6, P.skin, P.skinShade, .5), INK, LW);
  stroke(ctx, [[-.3, -.8], [-1, .2], [-.4, 1.2]], P.skinDeep, .35);
  ctx.restore();
}

function eyes(ctx, P, look, {blink = false, mood = 'alert'}) {
  // Near eye (full) sits toward the middle of the face; the far eye sits by the
  // profile edge and reads narrower.
  const rows = [[1.35, 1], [4.45, .74]];
  for (const [x, w] of rows) {
    if (blink || mood === 'fallen') { stroke(ctx, [[x - .9 * w, -6.5], [x + .9 * w, -6.4]], INK, .5); continue; }
    const squint = mood === 'pain' ? .45 : mood === 'focused' ? .8 : 1;
    ctx.beginPath(); ctx.ellipse(x, -6.55, .95 * w, .7 * squint, 0, 0, TAU); ctx.fillStyle = P.white; ctx.fill();
    ctx.save(); ctx.clip();
    dot(ctx, x + .12 * w, -6.5, .66, P.eye); dot(ctx, x + .15 * w, -6.5, .3, '#0d0f14'); dot(ctx, x - .08, -6.75, .14, '#ffffff');
    ctx.restore();
    stroke(ctx, [[x - 1.05 * w, -6.35], [x - .5 * w, -7.2 * (squint < 1 ? .98 : 1)], [x + .6 * w, -7.25], [x + 1.05 * w, -6.7]], INK, .5);
  }
}

function brows(ctx, P, look, mood) {
  const c = look.hairStyle === 'shaved' ? P.skinDeep : P.hairShade, w = .45 * look.brow;
  const tilt = mood === 'focused' || mood === 'angry' ? .5 : mood === 'strained' || mood === 'pain' ? -.45 : mood === 'cheer' ? -.2 : 0;
  stroke(ctx, [[.2, -8.45 + tilt * .2], [2.3, -8.8 - tilt * .3]], c, w + .1);
  stroke(ctx, [[3.7, -8.8 - tilt * .3], [5.2, -8.4 + tilt * .2]], c, w);
}

function mouth(ctx, P, mood) {
  if (mood === 'cheer') { ctx.beginPath(); ctx.moveTo(2.1, -2.3); ctx.quadraticCurveTo(3.1, -.7, 4.2, -2.2); ctx.closePath(); fillStroke(ctx, '#5a2a2a', INK, .35); return; }
  if (mood === 'shout' || mood === 'pain') { ctx.beginPath(); ctx.ellipse(3.1, -1.9, .75, mood === 'pain' ? .45 : .7, 0, 0, TAU); fillStroke(ctx, '#3a1c1f', INK, .35); return; }
  if (mood === 'strained') { stroke(ctx, [[2.1, -1.8], [2.8, -2.15], [3.5, -1.85], [4.1, -2.1]], P.lip, .5); return; }
  if (mood === 'fallen') { stroke(ctx, [[2.4, -1.8], [3.8, -1.9]], P.skinDeep, .45); return; }
  stroke(ctx, [[2.3, -2], [3.2, -2.1], [3.9, -2.3]], P.lip, .5);
}

function marks(ctx, P, look) {
  if (look.marks === 'freckles') {
    ctx.fillStyle = look.palette.skinDeep;
    for (const [x, y] of [[.3, -4.7], [1.1, -4.1], [1.9, -4.9], [3.5, -4.5], [4.1, -5.1], [5, -4.5], [.8, -5.3], [2.6, -4.3]]) { ctx.beginPath(); ctx.arc(x, y, .2, 0, TAU); ctx.fill(); }
  } else if (look.marks === 'cheek-scar') {
    stroke(ctx, [[3.4, -5.6], [4.6, -3.2]], '#a0473f', .5);
    for (const t of [.3, .6]) stroke(ctx, [[3.4 + 1.2 * t - .4, -5.6 + 2.4 * t + .2], [3.4 + 1.2 * t + .4, -5.6 + 2.4 * t - .2]], '#a0473f', .3);
  } else if (look.marks === 'war-paint') {
    poly(ctx, [[-.6, -7.2], [6.2, -7.4], [6.3, -5.9], [-.5, -5.6]]); ctx.fillStyle = rgba(P.accent === '#d9b56e' ? '#4f6d93' : P.accent, .78); ctx.fill();
    stroke(ctx, [[.5, -4.4], [.5, -2.6]], rgba(P.accent === '#d9b56e' ? '#4f6d93' : P.accent, .78), .6);
  } else if (look.marks === 'temple-mark') {
    poly(ctx, [[-2.2, -10.4], [-1.3, -9.4], [-2.2, -8.4], [-3.1, -9.4]]); ctx.fillStyle = rgba(P.accent, .9); ctx.fill();
    dot(ctx, -2.2, -9.4, .3, P.white);
  }
}

// Hair behind the head: long falls and braids trail on a spring (`sway`).
// Painted in an upright frame at the head joint so it hangs with gravity.
export function hairBack(ctx, P, look, {sway = 0, t = 0}) {
  const style = look.hairStyle, tx = -sway * 8, w = Math.sin(t * .0016) * .7;
  if (style === 'long') {
    ctx.beginPath(); ctx.moveTo(-4.4, -12.4);
    ctx.bezierCurveTo(-8.6, -9, -8.8, 0, -9.3, 6);
    ctx.bezierCurveTo(-10 + tx * .4, 13, -10.8 + tx * .7, 19, -9.2 + tx + w, 25);
    ctx.lineTo(-6.8 + tx + w, 22.6); ctx.lineTo(-5.2 + tx * .9 + w, 26); ctx.lineTo(-3.6 + tx * .8, 21);
    ctx.bezierCurveTo(-1 + tx * .5, 14, 1, 8, 1.4, 3); ctx.lineTo(3, -1.5);
    ctx.bezierCurveTo(3.8, -8, .8, -13.2, -4.4, -12.4); ctx.closePath();
    fillStroke(ctx, cel(ctx, -11, 2, P.hair, P.hairShade, .44));
    ctx.save(); ctx.clip();
    stroke(ctx, [[-6.4, -4], [-7.2 + tx * .5, 12], [-6.8 + tx + w, 22]], P.hairShade, .5);
    stroke(ctx, [[-2.8, 1], [-3.4 + tx * .4, 13], [-4.4 + tx * .8, 20]], P.hairShade, .5);
    ctx.restore();
  } else if (style === 'braided') {
    // A cap at the nape and a braid of overlapping lobes swinging behind.
    ctx.beginPath(); ctx.moveTo(-4.8, -11); ctx.bezierCurveTo(-7.4, -8, -7.2, -3, -5.4, -1.6); ctx.lineTo(-2, -2.4); ctx.lineTo(-1.8, -9); ctx.closePath();
    fillStroke(ctx, cel(ctx, -7.4, -1.8, P.hair, P.hairShade, .5));
    for (let i = 0; i < 7; i++) {
      const k = i / 6, x = -6 + tx * k * k + Math.sin(t * .002 + i * .5) * .25 * k, y = -1 + i * 3.3;
      ctx.beginPath(); ctx.ellipse(x, y, 1.9 - k * .6, 2.1, .3 * (i % 2 ? 1 : -1), 0, TAU);
      fillStroke(ctx, i % 2 ? P.hair : P.hairShade);
    }
    const ex = -6 + tx, ey = 22;
    poly(ctx, [[ex - 1, ey], [ex + 1, ey], [ex + .6, ey + 1.6], [ex - .6, ey + 1.6]]); fillStroke(ctx, P.accent, INK, .35);
    ctx.beginPath(); ctx.moveTo(ex - 1, ey + 1.6); ctx.lineTo(ex, ey + 5); ctx.lineTo(ex + 1, ey + 1.6); ctx.closePath(); fillStroke(ctx, P.hairShade);
  } else if (style === 'topknot') {
    ctx.beginPath(); ctx.ellipse(-2.8, -15.4, 3.2, 2.7, -.3, 0, TAU); fillStroke(ctx, cel(ctx, -6, .4, P.hair, P.hairShade, .5));
  }
}

function hairFront(ctx, P, look) {
  const style = look.hairStyle;
  if (style === 'shaved') {
    ctx.save(); faceOutline(ctx, look.face, look.body.jaw); ctx.clip();
    ctx.beginPath(); ctx.moveTo(-5.4, -7); ctx.bezierCurveTo(-6, -13.8, 3, -15.4, 6.2, -10); ctx.lineTo(4.8, -10.2); ctx.quadraticCurveTo(0, -11.4, -3.2, -8.4); ctx.closePath();
    ctx.fillStyle = rgba(P.hair, .38); ctx.fill(); ctx.restore(); return;
  }
  // Crown cap common to every grown style.
  const cap = () => {
    ctx.beginPath(); ctx.moveTo(-5.6, -5.6);
    ctx.bezierCurveTo(-7.2, -13.4, -1, -16.4, 3.8, -14.6);
    ctx.bezierCurveTo(6.8, -13.4, 7.4, -10.4, 6.3, -8.1);
  };
  if (style === 'cropped') {
    cap(); ctx.quadraticCurveTo(3.4, -11.6, .4, -11.2); ctx.quadraticCurveTo(-2.4, -10.6, -3.4, -7.6); ctx.lineTo(-3.8, -4.6); ctx.closePath();
  } else if (style === 'tousled') {
    ctx.beginPath(); ctx.moveTo(-5.8, -5.4); ctx.lineTo(-7.4, -10); ctx.lineTo(-5.6, -10.4); ctx.lineTo(-6.4, -14); ctx.lineTo(-3.4, -12.8);
    ctx.lineTo(-2.4, -16.6); ctx.lineTo(.2, -13.8); ctx.lineTo(2.6, -16.4); ctx.lineTo(3.6, -13.4); ctx.lineTo(6.8, -14.2); ctx.lineTo(5.6, -11.4);
    ctx.lineTo(7.4, -9.4); ctx.lineTo(4.6, -9.6); ctx.lineTo(3.8, -7.8); ctx.lineTo(2, -9.8); ctx.lineTo(.2, -8.2); ctx.lineTo(-1.4, -9.8);
    ctx.lineTo(-3, -7.6); ctx.lineTo(-3.6, -4.4); ctx.closePath();
  } else if (style === 'long') {
    cap(); ctx.quadraticCurveTo(4.6, -10.8, 1.6, -10.6);
    ctx.quadraticCurveTo(-.2, -8.4, -2.4, -8.9); ctx.quadraticCurveTo(-3.6, -7.2, -3.3, -3.4);
    ctx.lineTo(-4.2, 2.6); ctx.lineTo(-5.8, 1); ctx.closePath();
  } else {
    // short / braided / topknot: a clean side-swept cap with a fringe point.
    cap(); ctx.lineTo(5.2, -7.4); ctx.lineTo(4.2, -9.6); ctx.quadraticCurveTo(1.8, -10.9, -.4, -9.6);
    ctx.lineTo(-1.2, -8.2); ctx.lineTo(-2.2, -9.4); ctx.quadraticCurveTo(-3.6, -7.6, -3.4, -4.4); ctx.lineTo(-5.4, -3.6); ctx.closePath();
  }
  fillStroke(ctx, cel(ctx, -7, 7, P.hairHi, P.hair, .36));
  stroke(ctx, [[-2.4, -13.8], [1, -11.2]], P.hairShade, .45);
  if (style === 'long') stroke(ctx, [[-4.3, -6], [-4.6, 1]], P.hairShade, .45);
  if (style === 'topknot') { poly(ctx, [[-4.6, -14.1], [-1.4, -14.8], [-1.2, -13.4], [-4.3, -12.8]]); fillStroke(ctx, P.accent, INK, .35); }
}

function headgearBack(ctx, P, look) {
  if (look.headgear === 'hood') {
    ctx.beginPath(); ctx.moveTo(-7.6, 4); ctx.bezierCurveTo(-9.6, -6, -7, -15.8, .6, -16.4); ctx.bezierCurveTo(6.6, -16.2, 8.6, -11, 7.6, -7.4);
    ctx.lineTo(4, -9); ctx.lineTo(-5.4, -2); ctx.closePath();
    fillStroke(ctx, cel(ctx, -9.6, 8.6, P.clothShade, P.clothDeep, .6));
  }
}
function headgearFront(ctx, P, look, t) {
  const g = look.headgear, M = MATERIALS[look.main.material === 'gold' ? 'gold' : 'steel'];
  if (g === 'hood') {
    // Cowl rim framing the face.
    ctx.beginPath(); ctx.moveTo(-5.8, -1); ctx.bezierCurveTo(-7, -9.4, -3, -15.8, 1.6, -15.6); ctx.bezierCurveTo(6.2, -15.4, 8, -11.6, 7.3, -8.2);
    ctx.lineTo(5.6, -9.4); ctx.bezierCurveTo(5, -12.8, 1.6, -13.8, -1, -12.6); ctx.bezierCurveTo(-3.6, -11.2, -4.6, -6, -3.8, -1.2); ctx.closePath();
    fillStroke(ctx, cel(ctx, -7, 8, P.cloth, P.clothShade, .56));
    stroke(ctx, [[-3.8, -1.2], [-4.4, -7], [-1, -12.6], [5.6, -9.4]], P.accentShade, .45);
  } else if (g === 'circlet') {
    stroke(ctx, [[-5.4, -9.8], [0, -10.9], [6.1, -9.9]], INK, 1.5); stroke(ctx, [[-5.4, -9.8], [0, -10.9], [6.1, -9.9]], P.accent, .9);
    poly(ctx, [[2.6, -12.3], [3.6, -10.9], [2.6, -9.5], [1.6, -10.9]]); fillStroke(ctx, look.fx.length ? ELEMENT_COLOUR[look.fx[0]] : '#7fd0c6', INK, .35);
  } else if (g === 'half-helm') {
    ctx.beginPath(); ctx.moveTo(-5.9, -6.4); ctx.bezierCurveTo(-7.2, -13.6, -1.8, -17.2, 1.8, -17);
    ctx.bezierCurveTo(5.8, -16.6, 7.8, -13, 7, -9.4); ctx.lineTo(5.7, -9.6); ctx.lineTo(5.6, -4.6); ctx.lineTo(4.6, -4.8); ctx.lineTo(4.4, -9.4);
    ctx.quadraticCurveTo(0, -10.6, -3.4, -8.6); ctx.lineTo(-3.4, -3.2); ctx.lineTo(-5.6, -3.4); ctx.closePath();
    fillStroke(ctx, metalRamp(ctx, -7, 7.6, M));
    stroke(ctx, [[-5.6, -8.8], [0, -10.7], [6.9, -9.6]], P.accent, .8);
    stroke(ctx, [[1.6, -16.8], [1.4, -11]], M.hi, .5);
  } else if (g === 'full-helm') {
    // Enclosed helm: the face and hair are hidden; a lit visor slit and a crest.
    ctx.beginPath(); ctx.moveTo(-6.1, -1.8);
    ctx.bezierCurveTo(-7.2, -8, -6.8, -14.4, -4.2, -17); ctx.quadraticCurveTo(-1.6, -19.2, 1, -19.2);
    ctx.quadraticCurveTo(4.2, -18.9, 6.2, -16.2); ctx.bezierCurveTo(8, -13, 8.2, -7.4, 7.4, -2.2);
    ctx.lineTo(5, 1.8); ctx.quadraticCurveTo(.8, 3.4, -3.6, 1.6); ctx.closePath();
    fillStroke(ctx, metalRamp(ctx, -7, 8.2, M));
    ctx.save(); ctx.clip(); stroke(ctx, [[1, -19], [1.1, -12]], M.hi, .8); stroke(ctx, [[-6.8, -.6], [.8, 1.2], [7.6, -.8]], rgba(INK, .5), .5); ctx.restore();
    poly(ctx, [[-4.4, -11.4], [7.1, -11.4], [6.9, -9.7], [-4.2, -9.7]]); fillStroke(ctx, '#0a0c12', null);
    const glow = .55 + Math.sin(t * .004) * .1;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; poly(ctx, [[-2, -11.1], [6.6, -11.1], [6.5, -10], [-1.9, -10]]);
    ctx.fillStyle = rgba(look.fx.length ? ELEMENT_COLOUR[look.fx[0]] : '#9fd8ff', glow * .6); ctx.fill(); ctx.restore();
    for (const x of [2.8, 4, 5.2]) { dot(ctx, x, -6.4, .32, '#1a1d26'); dot(ctx, x, -5, .32, '#1a1d26'); }
    // Crest in the accent colour.
    ctx.beginPath(); ctx.moveTo(-3.6, -17.6); ctx.bezierCurveTo(-7, -21.4, -12, -20, -14.4, -15.6);
    ctx.bezierCurveTo(-11, -17, -7.6, -16.6, -4.6, -15.4); ctx.closePath(); fillStroke(ctx, cel(ctx, -14, -3, P.accent, P.accentShade, .5));
  }
}

export function head(ctx, P, look, {blink = false, mood = 'alert', t = 0}) {
  const enclosed = look.headgear === 'full-helm';
  headgearBack(ctx, P, look);
  if (!enclosed) {
    ear(ctx, P, look);
    faceOutline(ctx, look.face, look.body.jaw);
    fillStroke(ctx, cel(ctx, -4.9, 6.4, P.skin, P.skinShade, .78), INK, LW);
    // Cheek flush and the jaw shade under the front edge.
    ctx.save(); faceOutline(ctx, look.face, look.body.jaw); ctx.clip();
    ctx.fillStyle = rgba(P.blush, .35); ctx.beginPath(); ctx.ellipse(2.4, -4.1, 1.2, .7, 0, 0, TAU); ctx.fill();
    ctx.restore();
    eyes(ctx, P, look, {blink, mood});
    brows(ctx, P, look, mood);
    // Nose: a single shaded wedge; goblins grow theirs.
    const n = look.nose;
    if (n > 1.2) { poly(ctx, [[5.2, -6.4], [5.4 + 2.6 * n, -4.2], [4.6, -3.6]]); fillStroke(ctx, cel(ctx, 4.6, 5.4 + 2.6 * n, P.skin, P.skinShade, .4), INK, .45); }
    else stroke(ctx, [[5.1, -5.9], [5.8, -4], [5, -3.7]], P.skinDeep, .45);
    mouth(ctx, P, mood);
    if (look.tusks) for (const x of [2.1, 4.2]) { poly(ctx, [[x - .45, -1.7], [x + .1, -3.8], [x + .5, -1.6]]); fillStroke(ctx, '#efe4c2', INK, .35); }
    marks(ctx, P, look);
    if (look.headgear !== 'hood' && look.headgear !== 'half-helm') hairFront(ctx, P, look);
    else if (look.headgear === 'half-helm' && look.hairStyle !== 'shaved') {
      // Hair shows under the helm rim at the nape.
      ctx.beginPath(); ctx.moveTo(-5.8, -6); ctx.lineTo(-3.4, -8); ctx.lineTo(-3.2, -3.4); ctx.lineTo(-5.6, -2.8); ctx.closePath(); fillStroke(ctx, P.hairShade);
    }
  }
  headgearFront(ctx, P, look, t);
}

// ---------------------------------------------------------------------------
// NECK and TORSO. Torso frame: the shoulder line; +y runs down to the waist
// (the hip joint line) at `d.waist`.
export function neck(ctx, P, d) {
  capsule(ctx, 4.2 * d.W, 4.6 * d.W, -d.neck - 1, 1.5);
  fillStroke(ctx, cel(ctx, -2.4 * d.W, 2.4 * d.W, P.skin, P.skinShade, .5));
}

// Three-quarter torso: the front edge (+x) carries the chest profile, the back
// edge the shoulder blade; a V taper for broad frames, a waist for narrow ones.
function torsoPath(ctx, d, look, flare = 0, hem = 3.2) {
  const female = look.gender === 'female', sw = d.sx + 1.1 * d.W, wy = d.waist;
  const ww = d.hx + (female ? .9 : .5) * d.W, nip = female && !look.armored ? ww - 1.1 * d.W : ww - .2, cw = sw * (female ? .9 : .96);
  const neck = 3.2 * d.W;
  ctx.beginPath();
  ctx.moveTo(-neck, -2.8);
  ctx.quadraticCurveTo(-sw * .7, -2.2, -sw, .6);                           // trapezius to the back shoulder
  ctx.quadraticCurveTo(-sw - .6, wy * .18, -cw, wy * .36);                   // shoulder blade
  ctx.quadraticCurveTo(-nip - .4, wy * .62, -nip, wy * .72);                 // small of the back
  ctx.quadraticCurveTo(-ww - .4, wy * .9, -ww - flare - .3, wy + hem);
  ctx.quadraticCurveTo(0, wy + hem + 1.6, ww + flare + .3, wy + hem);
  ctx.quadraticCurveTo(ww + .4, wy * .9, nip, wy * .72);
  if (female && !look.armored) ctx.bezierCurveTo(nip + 1, wy * .52, cw + 1.6, wy * .44, cw + .9, wy * .28); // bust
  else ctx.quadraticCurveTo(cw + .9, wy * .5, cw + .5, wy * .26);                                         // chest
  ctx.quadraticCurveTo(sw + .5, wy * .08, sw, .6);
  ctx.quadraticCurveTo(sw * .7, -2.2, neck, -2.8);
  ctx.quadraticCurveTo(0, -1.6, -neck, -2.8);
  ctx.closePath();
  return {sw, cw, ww, wy};
}

// The seat of the trousers: bridges the waist and both thighs so the legs
// hang from the hips rather than from the belt. Pelvis frame.
export function hips(ctx, P, look, d) {
  if (look.torso === 'robe') return;
  const w = d.hx + 2.2 * d.W, h = 6.4 * d.kl;
  ctx.beginPath(); ctx.moveTo(-w, -3.2); ctx.lineTo(w, -3.2); ctx.quadraticCurveTo(w + .6, h * .45, w - 1, h);
  ctx.lineTo(1.4, h + .8); ctx.quadraticCurveTo(0, h - .6, -1.4, h + .8); ctx.lineTo(-w + 1, h);
  ctx.quadraticCurveTo(-w - .6, h * .45, -w, -3.2); ctx.closePath();
  const plate = look.torso === 'plate';
  fillStroke(ctx, plate ? metalRamp(ctx, -w, w, {hi: P.metalHi, base: P.metal, shade: P.metalShade, deep: P.metalDeep}) : cel(ctx, -w, w, P.trouser, P.trouserShade, .62));
  if (!plate) stroke(ctx, [[.8, -2], [1.2, h - .6]], P.trouserShade, .45);
}

export function torso(ctx, P, look, d, {t = 0} = {}) {
  const kind = look.torso;
  if (kind === 'plate') {
    const M = {base: P.metal, shade: P.metalShade, hi: P.metalHi, deep: P.metalDeep};
    const {sw, ww, wy} = torsoPath(ctx, d, look);
    fillStroke(ctx, metalRamp(ctx, -sw, sw, M));
    ctx.save(); ctx.clip();
    // Tabard in the owner's colours down the front, the one place cloth shows.
    poly(ctx, [[-2.6, wy * .34], [4.8, wy * .34], [ww + .2, wy + 1], [-3.6, wy + 1]]); fillStroke(ctx, cel(ctx, -3.6, ww, P.cloth, P.clothShade, .62), null);
    stroke(ctx, [[-2.6, wy * .34], [-3.6, wy + 1]], P.accent, .7); stroke(ctx, [[4.8, wy * .34], [ww + .2, wy + 1]], P.accent, .7);
    emblem(ctx, P, 1, wy * .62, .9);
    ctx.fillStyle = rgba('#ffffff', .5); ctx.beginPath(); ctx.ellipse(-sw * .45, wy * .16, 2.6, 4.4, -.2, 0, TAU); ctx.fill();
    stroke(ctx, [[-sw, wy * .3], [0, wy * .36], [2.6, wy * .34]], rgba(INK, .45), .45);
    ctx.restore();
    // Gorget.
    ctx.beginPath(); ctx.moveTo(-4.2 * d.W, -2.2); ctx.quadraticCurveTo(0, -4.6, 4.4 * d.W, -2.2); ctx.lineTo(3.8 * d.W, 1.4); ctx.quadraticCurveTo(0, 2.6, -3.6 * d.W, 1.4); ctx.closePath();
    fillStroke(ctx, metalRamp(ctx, -4.4, 4.4, M));
    return;
  }
  const base = {chain: P.mail, leather: P.leather, robe: P.cloth, travel: P.cloth, tunic: P.cloth, coat: P.cloth, vest: P.clothHi, uniform: P.cloth}[kind] || P.cloth;
  const shade = {chain: P.mailShade, leather: P.leatherShade}[kind] || P.clothShade;
  const {sw, cw, ww, wy} = torsoPath(ctx, d, look);
  fillStroke(ctx, cel(ctx, -sw, sw, base, shade, .64));
  ctx.save(); ctx.clip();
  if (EXTRA_OUTFITS.has(kind)) EXTRA_OUTFITS.get(kind)(ctx, P, look, d, {sw, cw, ww, wy});
  else if (kind === 'chain') {
    // Mail rings: staggered rows of short arcs.
    ctx.strokeStyle = rgba(INK, .32); ctx.lineWidth = .3;
    for (let y = 0, row = 0; y < wy + 2; y += 1.5, row++) {
      ctx.beginPath();
      for (let x = -sw + (row % 2) * .8; x < sw; x += 1.6) { ctx.moveTo(x - .6, y); ctx.quadraticCurveTo(x, y + .8, x + .6, y); }
      ctx.stroke();
    }
    // Surcoat panel in the owner's colours.
    poly(ctx, [[-1.8, 1], [3.6, 1], [ww, wy + 1], [-3, wy + 1]]); fillStroke(ctx, cel(ctx, -3, ww, P.cloth, P.clothShade, .6), null);
    stroke(ctx, [[-1.8, 1], [-3, wy + 1]], P.accent, .6); stroke(ctx, [[3.6, 1], [ww, wy + 1]], P.accent, .6);
    emblem(ctx, P, 1, wy * .45, .75);
  } else if (kind === 'leather') {
    stroke(ctx, [[1.2, -1], [1.6, wy]], P.leatherDeep, .5);
    ctx.setLineDash([.7, .7]); stroke(ctx, [[2.2, 0], [2.6, wy]], P.leatherHi, .35); ctx.setLineDash([]);
    for (const y of [wy * .3, wy * .55]) stroke(ctx, [[-sw, y], [cw, y + 1.2]], P.leatherDeep, .8);
    poly(ctx, [[-sw, -1], [-sw + 3.2, -1.8], [-sw + 2.6, wy * .4], [-sw, wy * .35]]); fillStroke(ctx, P.leatherShade, null);
  } else if (kind === 'robe') {
    poly(ctx, [[-2.8, -2.6], [4.2, -2.6], [.8, wy * .3]]); fillStroke(ctx, P.skin, null);
    stroke(ctx, [[-3.2, -2.6], [.8, wy * .32], [4.6, -2.6]], P.accent, .9);
    poly(ctx, [[-ww - 1, wy * .78], [ww + 1, wy * .78], [ww + 1, wy * .94], [-ww - 1, wy * .94]]); fillStroke(ctx, P.accent, INK, .4);
    stroke(ctx, [[.8, wy * .32], [.4, wy * .78]], P.clothShade, .45);
  } else if (kind === 'coat') {
    poly(ctx, [[-1.2, -2.6], [3.6, -2.6], [1.4, wy * .42]]); fillStroke(ctx, P.white, null);
    poly(ctx, [[3.6, -2.6], [cw * .8, wy * .08], [1.4, wy * .42]]); fillStroke(ctx, P.clothHi, INK, .4);
    stroke(ctx, [[1.4, wy * .42], [1.6, wy + 1]], INK, .45);
    for (const y of [wy * .52, wy * .68, wy * .84]) dot(ctx, 2.6, y, .45, P.accent);
    stroke(ctx, [[3.6, -2.6], [cw * .8, wy * .08]], P.accent, .5);
  } else if (kind === 'travel') {
    // Shirt under a leather vest.
    poly(ctx, [[-1.6, -2.6], [3.8, -2.6], [cw * .9, wy + 1], [-3.4, wy + 1]]); fillStroke(ctx, cel(ctx, -3.4, cw, P.leather, P.leatherShade, .6), INK, .45);
    poly(ctx, [[-.6, -2.6], [3, -2.6], [1.2, wy * .3]]); fillStroke(ctx, P.clothHi, null);
    stroke(ctx, [[1.6, wy * .3], [1.9, wy + 1]], P.leatherDeep, .45);
    for (const y of [wy * .4, wy * .6]) { stroke(ctx, [[.7, y], [2.8, y + .6]], P.leatherHi, .4); }
  } else if (kind === 'tunic') {
    poly(ctx, [[-1, -2.6], [3.6, -2.6], [1.4, wy * .36]]); fillStroke(ctx, P.clothShade, null);
    stroke(ctx, [[-1.4, -2.6], [1.4, wy * .38], [4, -2.6]], P.accent, .5);
  } else if (kind === 'vest') {
    // Quilted vest over a pale shirt: diamond stitching.
    ctx.strokeStyle = rgba(P.clothDeep, .6); ctx.lineWidth = .35;
    for (let k = -sw * 2; k < sw * 2; k += 3) { ctx.beginPath(); ctx.moveTo(k, -2); ctx.lineTo(k + wy, wy + 2); ctx.moveTo(k + wy, -2); ctx.lineTo(k, wy + 2); ctx.stroke(); }
    poly(ctx, [[-.4, -2.6], [3, -2.6], [1.6, wy + 1], [.2, wy + 1]]); fillStroke(ctx, P.white, INK, .4);
  } else if (kind === 'uniform') {
    poly(ctx, [[-sw, -1.4], [sw, -1.4], [sw, 1.2], [-sw, 1.2]]); fillStroke(ctx, P.accent, INK, .4);
    stroke(ctx, [[1.8, 1], [2, wy + 1]], INK, .45);
    for (const y of [wy * .25, wy * .45, wy * .65, wy * .85]) dot(ctx, 3, y, .5, P.accent);
    stroke(ctx, [[-sw * .8, wy * .3], [-1, wy * .5]], P.accent, .6);
  }
  ctx.restore();
}

// A device in the owner's colours: a ring and chevron, sized to the chest.
function emblem(ctx, P, x, y, s) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.beginPath(); ctx.arc(0, 0, 2.6, 0, TAU); fillStroke(ctx, P.accent, INK, .45);
  poly(ctx, [[-1.6, .9], [0, -1.3], [1.6, .9], [.9, .9], [0, -.2], [-.9, .9]]); fillStroke(ctx, P.clothDeep, null);
  ctx.restore();
}

// ---------------------------------------------------------------------------
// PELVIS: belt and whatever hangs from the hips. Frame: the hip joint line,
// +y down the legs. `swing` follows the thighs so skirts move with the stride.
export function belt(ctx, P, look, d) {
  const w = d.hx + 1.2 * d.W, y = -4;
  if (look.torso === 'robe') {
    poly(ctx, [[-w, y], [w, y], [w - .2, y + 2.8], [-w + .2, y + 2.8]]); fillStroke(ctx, P.accentShade, INK, .45);
    poly(ctx, [[1.2, y + 1.4], [2.6, y + 1.4], [3.4, y + 8.4], [1.8, y + 8]]); fillStroke(ctx, P.accent, INK, .4);
    return;
  }
  poly(ctx, [[-w, y], [w, y], [w - .1, y + 2.8], [-w + .1, y + 2.8]]); fillStroke(ctx, P.leatherShade, INK, .45);
  poly(ctx, [[1.2, y - .4], [3.6, y - .4], [3.6, y + 3.2], [1.2, y + 3.2]]); fillStroke(ctx, P.accent, INK, .45);
  poly(ctx, [[1.9, y + .4], [2.9, y + .4], [2.9, y + 2.4], [1.9, y + 2.4]]); fillStroke(ctx, P.leatherDeep, null);
}

export function skirt(ctx, P, look, d, {swing = 0, t = 0} = {}) {
  const kind = look.torso, w = d.hx + 1.7 * d.W;
  const len = {robe: d.thigh + d.shin + 2, coat: d.thigh + 3, tunic: d.thigh * .45, chain: d.thigh * .52, plate: d.thigh * .3}[kind];
  if (!len) return;
  const flare = kind === 'robe' ? 6 : kind === 'coat' ? 4.2 : 2.4, sway = Math.sin(t * .0017) * .5;
  ctx.save(); ctx.rotate(swing * (kind === 'robe' ? .5 : .75));
  const base = kind === 'chain' ? P.mail : kind === 'plate' ? P.metal : P.cloth, shade = kind === 'chain' ? P.mailShade : kind === 'plate' ? P.metalShade : P.clothShade;
  const outline = () => {
    ctx.beginPath(); ctx.moveTo(-w, -1); ctx.lineTo(w, -1);
    ctx.bezierCurveTo(w + 1, len * .35, w + flare * .7, len * .7, w + flare + sway, len);
    ctx.quadraticCurveTo(0, len + 1.8, -w - flare - 1 + sway, len - .6);
    ctx.bezierCurveTo(-w - flare * .6, len * .7, -w - 1, len * .35, -w, -1); ctx.closePath();
  };
  outline(); fillStroke(ctx, cel(ctx, -w - flare, w + flare, base, shade, .62), null);
  ctx.save(); outline(); ctx.clip();
  if (kind === 'chain') {
    ctx.strokeStyle = rgba(INK, .3); ctx.lineWidth = .3;
    for (let y = 0, r = 0; y < len + 2; y += 1.5, r++) { ctx.beginPath(); for (let x = -w - flare + (r % 2) * .8; x < w + flare; x += 1.6) { ctx.moveTo(x - .6, y); ctx.quadraticCurveTo(x, y + .8, x + .6, y); } ctx.stroke(); }
    poly(ctx, [[-2.6, -1], [3.6, -1], [4.4, len + 2], [-3.2, len + 2]]); fillStroke(ctx, cel(ctx, -3.2, 4.4, P.cloth, P.clothShade, .6), null);
    stroke(ctx, [[.4, 0], [.6, len + 2]], P.clothDeep, .45);
  } else if (kind === 'plate') {
    for (let y = 1.6; y < len; y += 2.6) stroke(ctx, [[-w - 2, y], [w + 2, y + .2]], rgba(INK, .45), .45);
    poly(ctx, [[-2.4, -1], [4.2, -1], [5.4, len + 6], [-3, len + 6]]); fillStroke(ctx, cel(ctx, -3, 5.4, P.cloth, P.clothShade, .6), INK, .45);
    stroke(ctx, [[-3, len + 5.4], [5.4, len + 5.4]], P.accent, .8);
  } else if (kind === 'coat') {
    stroke(ctx, [[2.2, -1], [3 + flare * .3, len + 2]], INK, .45);
    poly(ctx, [[-w - flare - 2, len - 2.2], [w + flare + 2, len - 1.8], [w + flare + 2, len + 3], [-w - flare - 2, len + 3]]); fillStroke(ctx, P.clothDeep, null);
  } else if (kind === 'robe') {
    poly(ctx, [[1.2, -1], [3.4, -1], [6.4 + flare * .3, len + 3], [2.4, len + 3]]); fillStroke(ctx, P.clothShade, null);
    stroke(ctx, [[1.2, -1], [2.4, len + 3]], P.accent, .7); stroke(ctx, [[3.4, -1], [6.4 + flare * .3, len + 3]], P.accent, .7);
    poly(ctx, [[-w - flare - 3, len - 3], [w + flare + 3, len - 2.4], [w + flare + 3, len + 3], [-w - flare - 3, len + 3]]); fillStroke(ctx, P.accent, null);
  } else if (kind === 'tunic') {
    stroke(ctx, [[-w - flare, len - 1.6], [w + flare, len - 1.2]], P.accent, .6);
  }
  ctx.restore();
  outline(); ctx.strokeStyle = INK; ctx.lineWidth = LW; ctx.lineJoin = 'round'; ctx.stroke();
  ctx.restore();
}

// ---------------------------------------------------------------------------
// LEGS. Thigh and shin frames: +y down the bone.
export function thigh(ctx, P, look, d) {
  const L = d.thigh, w0 = 8.4 * d.W, w1 = 6.2 * d.W;
  capsule(ctx, w0, w1, -1, L + .8);
  if (look.torso === 'plate') {
    fillStroke(ctx, metalRamp(ctx, -w0 / 2, w0 / 2, {hi: P.metalHi, base: P.metal, shade: P.metalShade, deep: P.metalDeep}));
    ctx.beginPath(); ctx.ellipse(0, L, w1 * .52, 2.4, 0, 0, TAU); fillStroke(ctx, P.metal);   // poleyn
  } else fillStroke(ctx, cel(ctx, -w0 / 2, w0 / 2, P.trouser, P.trouserShade, .6));
}
export function shin(ctx, P, look, d) {
  const L = d.shin, w0 = 6 * d.W, w1 = 4.6 * d.W;
  capsule(ctx, w0, w1, -.6, L + .4);
  if (look.torso === 'plate') {
    fillStroke(ctx, metalRamp(ctx, -w0 / 2, w0 / 2, {hi: P.metalHi, base: P.metal, shade: P.metalShade, deep: P.metalDeep}));
    stroke(ctx, [[.8, 1], [.6, L - 1]], P.metalHi, .5);
    return;
  }
  fillStroke(ctx, cel(ctx, -w0 / 2, w0 / 2, P.trouser, P.trouserShade, .6));
  // Boot shaft: knee-high for leather and travel wear, ankle-high otherwise.
  const top = look.boots === 'shoes' ? L - 2 : ['leather', 'travel', 'chain', 'uniform'].includes(look.torso) ? L * .28 : L * .58;
  capsule(ctx, w0 * (1 - top / L * .25) + .5, w1 + .6, top, L + .5);
  fillStroke(ctx, cel(ctx, -w0 / 2, w0 / 2, look.boots === 'shoes' ? P.clothDeep : P.leather, look.boots === 'shoes' ? '#1c1a20' : P.leatherShade, .58));
  if (look.boots !== 'shoes') stroke(ctx, [[-w0 * .52, top + 1.2], [w0 * .52, top + 1]], P.leatherHi, .5);
}
// Foot in an upright frame at the ankle: the sole sits `sole` below, toe +x.
export function foot(ctx, P, look, d, {tilt = 0} = {}) {
  const s = d.sole, L = 8.2 * d.kl + 1.2;
  ctx.save(); ctx.rotate(tilt);
  ctx.beginPath(); ctx.moveTo(-2.6 * d.W, -1.4); ctx.lineTo(2.2 * d.W, -1.4);
  ctx.quadraticCurveTo(2.8, s * .5, L * .55, s * .62); ctx.quadraticCurveTo(L + .6, s * .72, L, s);
  ctx.lineTo(-3 * d.W, s); ctx.quadraticCurveTo(-3.4 * d.W, s * .4, -2.6 * d.W, -1.4); ctx.closePath();
  if (look.boots === 'sabatons') {
    fillStroke(ctx, metalRamp(ctx, -3, L, {hi: P.metalHi, base: P.metal, shade: P.metalShade, deep: P.metalDeep}));
    for (const x of [L * .3, L * .52]) stroke(ctx, [[x, s * .45], [x - .6, s]], rgba(INK, .5), .4);
  } else if (look.boots === 'shoes') {
    fillStroke(ctx, cel(ctx, -3, L, P.clothDeep, '#1c1a20', .6));
    stroke(ctx, [[-1.4, s * .3], [2.4, s * .45]], P.accent, .5);
  } else {
    fillStroke(ctx, cel(ctx, -3, L, P.leather, P.leatherShade, .6));
    poly(ctx, [[-3 * d.W, s - 1], [L, s - .9], [L, s], [-3 * d.W, s]]); fillStroke(ctx, P.leatherDeep, null);
  }
  ctx.restore();
}

// ---------------------------------------------------------------------------
// ARMS. Upper and lower frames: +y down the bone.
export function upperArm(ctx, P, look, d, {near = true} = {}) {
  const k = look.torso, L = d.upper, w0 = (k === 'plate' ? 6.4 : k === 'robe' ? 6 : 5.2) * d.W, w1 = (k === 'plate' ? 5.8 : k === 'robe' ? 6.2 : 4.5) * d.W;
  ctx.beginPath(); ctx.moveTo(-w0 / 2, 1.6); ctx.bezierCurveTo(-w0 / 2 - .3, -2.6, w0 / 2 + .5, -2.8, w0 / 2 + .2, 1.8);
  ctx.lineTo(w1 / 2, L); ctx.quadraticCurveTo(0, L + w1 * .45, -w1 / 2, L); ctx.closePath();
  const sleeve = k === 'plate' ? null : k === 'chain' ? [P.mail, P.mailShade] : k === 'leather' ? [P.leather, P.leatherShade]
    : k === 'vest' ? [P.white, '#cfc8ba'] : k === 'travel' ? [P.clothHi, P.cloth] : [P.cloth, P.clothShade];
  if (sleeve) fillStroke(ctx, cel(ctx, -w0 / 2, w0 / 2, sleeve[0], sleeve[1], .6));
  else fillStroke(ctx, metalRamp(ctx, -w0 / 2, w0 / 2, {hi: P.metalHi, base: P.metal, shade: P.metalShade, deep: P.metalDeep}));
  if (k === 'chain') { ctx.save(); ctx.clip(); ctx.strokeStyle = rgba(INK, .3); ctx.lineWidth = .3; for (let y = 0; y < L; y += 1.5) { ctx.beginPath(); ctx.moveTo(-w0, y); ctx.lineTo(w0, y + .5); ctx.stroke(); } ctx.restore(); }
  // Shoulder: pauldron for plate, a cap for leather and uniforms, a mantle edge for robes.
  if (k === 'plate') {
    ctx.beginPath(); ctx.moveTo(-5.2 * d.W, 5.6); ctx.bezierCurveTo(-6.4 * d.W, -2.6, -3 * d.W, -5.6, .6, -5.4);
    ctx.bezierCurveTo(4.4 * d.W, -5.2, 6.6 * d.W, -2.4, 5.8 * d.W, 5.8); ctx.quadraticCurveTo(0, 8, -5.2 * d.W, 5.6); ctx.closePath();
    fillStroke(ctx, metalRamp(ctx, -6.4 * d.W, 6.6 * d.W, {hi: P.metalHi, base: P.metal, shade: P.metalShade, deep: P.metalDeep}));
    stroke(ctx, [[-5 * d.W, 4.8], [0, 6.8], [5.6 * d.W, 5]], P.accent, .8);
    stroke(ctx, [[-4.6 * d.W, 1.6], [0, 3.4], [5 * d.W, 1.8]], rgba(INK, .4), .4);
  } else if (k === 'uniform' && near) {
    poly(ctx, [[-4 * d.W, -1.6], [4.2 * d.W, -1.6], [3.6 * d.W, 1.6], [-3.4 * d.W, 1.6]]); fillStroke(ctx, P.accent, INK, .4);
    for (const x of [-2, 0, 2]) stroke(ctx, [[x * d.W, 1.6], [x * d.W, 3.2]], P.accent, .4);
  } else if (k === 'leather') {
    ctx.beginPath(); ctx.moveTo(-4.4 * d.W, 3.6); ctx.bezierCurveTo(-5 * d.W, -2, -2 * d.W, -3.8, .4, -3.6); ctx.bezierCurveTo(3 * d.W, -3.4, 5 * d.W, -1.6, 4.6 * d.W, 3.8); ctx.quadraticCurveTo(0, 5.4, -4.4 * d.W, 3.6); ctx.closePath();
    fillStroke(ctx, cel(ctx, -5 * d.W, 5 * d.W, P.leatherShade, P.leatherDeep, .6));
  }
}
export function lowerArm(ctx, P, look, d) {
  const L = d.lower, k = look.torso, w0 = (k === 'plate' ? 5.6 : 4.5) * d.W, w1 = (k === 'plate' ? 4.8 : 3.7) * d.W;
  if (k === 'robe') {
    // Bell sleeve flaring toward the wrist.
    ctx.beginPath(); ctx.moveTo(-3 * d.W, .2); ctx.lineTo(3.2 * d.W, .2); ctx.lineTo(5.6 * d.W, L - .6); ctx.quadraticCurveTo(0, L + 1.8, -5 * d.W, L - 1); ctx.closePath();
    fillStroke(ctx, cel(ctx, -5 * d.W, 5.6 * d.W, P.cloth, P.clothShade, .58));
    poly(ctx, [[-4.8 * d.W, L - 2.8], [5.3 * d.W, L - 2.4], [5.6 * d.W, L - .6], [-5 * d.W, L - 1]]); fillStroke(ctx, P.accent, INK, .4);
    return;
  }
  capsule(ctx, w0, w1, -.4, L + .4);
  if (k === 'plate') {
    fillStroke(ctx, metalRamp(ctx, -w0 / 2, w0 / 2, {hi: P.metalHi, base: P.metal, shade: P.metalShade, deep: P.metalDeep}));
    ctx.beginPath(); ctx.ellipse(0, .2, w0 * .5, 1.9, 0, 0, TAU); fillStroke(ctx, P.metal);   // couter
    return;
  }
  // Rolled sleeves show forearm for vests and travel wear.
  const bare = k === 'vest' || k === 'travel' || k === 'tunic';
  const sleeve = k === 'chain' ? [P.clothHi, P.cloth] : k === 'leather' ? [P.leather, P.leatherShade] : bare ? [P.skin, P.skinShade] : [P.cloth, P.clothShade];
  fillStroke(ctx, cel(ctx, -w0 / 2, w0 / 2, sleeve[0], sleeve[1], .58));
  if (bare) { capsule(ctx, w0 + .6, w0 + .2, -.6, 2.4); fillStroke(ctx, k === 'travel' ? P.clothHi : k === 'vest' ? P.white : P.cloth); }
  // Bracer / cuff.
  const cuff = k === 'coat' || k === 'uniform' ? P.accent : ['chain', 'leather', 'travel'].includes(k) ? P.leatherShade : null;
  if (cuff) { poly(ctx, [[-w1 * .56, L - 3.8], [w1 * .56, L - 3.8], [w1 * .6, L], [-w1 * .6, L]]); fillStroke(ctx, cuff, INK, .4); }
}

// Hands. `grip` closes around a handle across the palm; `open` spreads a ward
// or spell palm; otherwise a loose, slightly curled rest.
export function hand(ctx, P, look, d, {mode = 'rest'} = {}) {
  const plate = look.torso === 'plate', skin = plate ? P.metal : P.skin, shade = plate ? P.metalShade : P.skinShade, s = d.W * .96;
  ctx.save(); ctx.scale(s, s);
  if (mode === 'open') {
    ctx.beginPath(); ctx.moveTo(-1.9, -.6); ctx.lineTo(2, -.6); ctx.lineTo(2.5, 4.4); ctx.lineTo(1.3, 7);
    ctx.lineTo(-.3, 6.6); ctx.lineTo(-1.5, 4.6); ctx.lineTo(-3.3, 2.8); ctx.lineTo(-2.3, 1.5); ctx.closePath();
    fillStroke(ctx, cel(ctx, -3.3, 2.5, skin, shade, .6));
    stroke(ctx, [[-.2, 3.4], [.4, 6.2]], shade, .35); stroke(ctx, [[1, 3.4], [1.4, 6.2]], shade, .35);
  } else if (mode === 'grip') {
    ctx.beginPath(); ctx.roundRect(-2.2, -.5, 4.4, 4.6, 1.5); fillStroke(ctx, cel(ctx, -2.2, 2.2, skin, shade, .6));
    for (const y of [1.2, 2.5]) stroke(ctx, [[.5, y], [2.1, y]], shade, .35);
    ctx.beginPath(); ctx.ellipse(-1.4, 1.3, 1, 1.6, .4, 0, TAU); fillStroke(ctx, skin, INK, .4);  // thumb over the grip
  } else {
    ctx.beginPath(); ctx.moveTo(-1.9, -.6); ctx.lineTo(2, -.6); ctx.quadraticCurveTo(2.8, 3, 1.8, 5.4); ctx.quadraticCurveTo(0, 6.2, -1.6, 5); ctx.quadraticCurveTo(-2.6, 2.4, -1.9, -.6); ctx.closePath();
    fillStroke(ctx, cel(ctx, -2.6, 2.8, skin, shade, .6));
    stroke(ctx, [[.2, 3.6], [1.6, 4.6]], shade, .35);
  }
  ctx.restore();
}

// ---------------------------------------------------------------------------
// CLOAK. Frame: the shoulder line in an upright frame; `bend` is the spring
// angle the hem trails at, `flare` widens it with speed.
export function cloakBack(ctx, P, look, d, {bend = 0, flare = 0, t = 0} = {}) {
  const style = look.cloak; if (style === 'none') return;
  const len = style === 'shoulder-mantle' ? d.torso * .9 : style === 'long-mantle' ? d.waist + d.thigh + d.shin * .8 : d.waist + d.thigh * .95;
  const sw = d.sx + 1.8 * d.W, wave = Math.sin(t * .0021) * .8, f = Math.max(0, flare) * 10;
  const tip = x => [x - Math.sin(bend) * len * .35 - f * .5, len];
  ctx.beginPath(); ctx.moveTo(-sw, -1.6); ctx.lineTo(sw * .7, -1.6);
  ctx.bezierCurveTo(sw * 1.05, len * .3, sw * .9 - Math.sin(bend) * len * .2, len * .7, tip(sw * .8)[0], len);
  const n = 6, x0 = tip(sw * .8)[0], x1 = tip(-sw * 1.2)[0] - f;
  for (let i = 1; i <= n; i++) { const x = x0 + (x1 - x0) * i / n; ctx.lineTo(x + 1.2, len + (i % 2 ? 1.6 + wave : -.2)); ctx.lineTo(x, len + (i % 2 ? .3 : 1.2 - wave)); }
  ctx.bezierCurveTo(-sw * 1.25 - f, len * .7, -sw * 1.15, len * .3, -sw, -1.6); ctx.closePath();
  fillStroke(ctx, cel(ctx, -sw * 1.3 - f, sw, P.clothShade, P.clothDeep, .42));
  ctx.save(); ctx.clip(); ctx.globalAlpha = .45;
  for (const x of [-sw * .7, -sw * .15, sw * .4]) stroke(ctx, [[x, 3], [x - Math.sin(bend) * len * .3 - f * .4, len]], P.clothDeep, 1.1);
  ctx.globalAlpha = 1; ctx.restore();
}
export function cloakFront(ctx, P, look, d) {
  const style = look.cloak; if (style === 'none') return;
  const sw = d.sx + 1.8 * d.W;
  if (style === 'shoulder-mantle' || style === 'long-mantle') {
    ctx.beginPath(); ctx.moveTo(-sw, -1.8); ctx.quadraticCurveTo(0, -4, sw, -1.8); ctx.quadraticCurveTo(sw + 1, 4, sw * .7, 7.4);
    ctx.quadraticCurveTo(0, 9.2, -sw * .6, 7); ctx.quadraticCurveTo(-sw - 1, 4, -sw, -1.8); ctx.closePath();
    fillStroke(ctx, cel(ctx, -sw, sw, P.cloth, P.clothShade, .6));
    stroke(ctx, [[-sw * .6, 7], [0, 9], [sw * .7, 7.4]], P.accent, .6);
  } else {
    stroke(ctx, [[-sw * .9, -1.2], [2, 2.6], [sw * .75, -1]], P.clothShade, 1.4);
  }
  // Clasp.
  ctx.beginPath(); ctx.arc(2, 2.2, 1.3, 0, TAU); fillStroke(ctx, P.accent, INK, .4);
}

// ---------------------------------------------------------------------------
// TRINKETS. Torso frame.
export function trinket(ctx, P, look, d) {
  const k = look.trinket, wy = d.waist;
  if (k === 'pendant' || k === 'talisman' || k === 'medal') {
    stroke(ctx, [[-2.6, -2.4], [1.6, wy * .34], [4.6, -2.4]], k === 'talisman' ? P.leatherShade : P.accent, .45);
    if (k === 'pendant') { poly(ctx, [[1.6, wy * .3], [2.9, wy * .4], [1.6, wy * .52], [.3, wy * .4]]); fillStroke(ctx, look.fx.length ? ELEMENT_COLOUR[look.fx[0]] : '#7fd0c6', INK, .4); }
    else if (k === 'medal') { poly(ctx, [[.6, wy * .24], [2.6, wy * .24], [2.2, wy * .36], [1, wy * .36]]); fillStroke(ctx, P.cloth, INK, .35); ctx.beginPath(); ctx.arc(1.6, wy * .42, 1.4, 0, TAU); fillStroke(ctx, P.accent, INK, .4); }
    else { ctx.beginPath(); ctx.ellipse(1.6, wy * .42, 1, 1.5, .3, 0, TAU); fillStroke(ctx, '#e8dfc8', INK, .4); stroke(ctx, [[1.2, wy * .38], [2, wy * .46]], '#7d6d55', .35); }
  } else if (k === 'satchel') {
    stroke(ctx, [[-d.sx, -1], [d.sx * .7, wy]], INK, 1.8); stroke(ctx, [[-d.sx, -1], [d.sx * .7, wy]], P.leatherShade, 1.1);
  }
}
export function satchelBag(ctx, P, look, d) {
  if (look.trinket !== 'satchel') return;
  poly(ctx, [[-d.hx - 6, 1], [-d.hx + 1, 1], [-d.hx + 1, 9], [-d.hx - 6, 8.4]]); fillStroke(ctx, cel(ctx, -d.hx - 6, -d.hx + 1, P.leather, P.leatherShade, .55));
  poly(ctx, [[-d.hx - 6.2, .6], [-d.hx + 1.2, .6], [-d.hx + .8, 4.4], [-d.hx - 5.8, 4]]); fillStroke(ctx, P.leatherShade, INK, .45);
  dot(ctx, -d.hx - 2.6, 3.6, .5, P.accent);
}

// ---------------------------------------------------------------------------
// OFF-HAND ITEMS. Frame: the grip of the far hand, upright (angle = `tilt`).
export function shield(ctx, P, look, {kind = 'kite-shield'} = {}) {
  const M = MATERIALS[look.shieldMaterial] || MATERIALS.steel;
  if (kind === 'buckler') {
    ctx.beginPath(); ctx.arc(1, 0, 7.4, 0, TAU); fillStroke(ctx, metalRamp(ctx, -6.4, 8.4, M));
    ctx.beginPath(); ctx.arc(1, 0, 5.6, 0, TAU); fillStroke(ctx, cel(ctx, -4.6, 6.6, P.cloth, P.clothShade, .6), INK, .45);
    ctx.beginPath(); ctx.arc(1, 0, 2.2, 0, TAU); fillStroke(ctx, metalRamp(ctx, -1.2, 3.2, M));
    return;
  }
  const pts = [[-8.4, -12], [10.4, -12], [11.4, -1.6], [1, 17.6], [-9.4, -1.6]];
  poly(ctx, pts); fillStroke(ctx, cel(ctx, -9.4, 11.4, P.cloth, P.clothShade, .6), INK, .6);
  ctx.save(); poly(ctx, pts); ctx.clip();
  poly(ctx, [[-10, -3], [1, 6], [12, -3], [12, 1.2], [1, 10.2], [-10, 1.2]]); fillStroke(ctx, P.accent, null);   // chevron
  ctx.restore();
  poly(ctx, pts); ctx.strokeStyle = M.base; ctx.lineWidth = 1.4; ctx.lineJoin = 'round'; ctx.stroke();
  poly(ctx, pts); ctx.strokeStyle = INK; ctx.lineWidth = .5; ctx.stroke();
  ctx.beginPath(); ctx.arc(1, -4.6, 1.8, 0, TAU); fillStroke(ctx, M.base, INK, .4);
}
export function tome(ctx, P, look, {open = 0, t = 0} = {}) {
  if (open > .5) {
    poly(ctx, [[-8, -3], [0, -1.6], [8, -3], [8, 3.2], [0, 4.6], [-8, 3.2]]); fillStroke(ctx, P.clothDeep, INK, .5);
    poly(ctx, [[-7.2, -3.8], [0, -2.4], [0, 3.6], [-7.2, 2.4]]); fillStroke(ctx, '#f3ead3', INK, .4);
    poly(ctx, [[7.2, -3.8], [0, -2.4], [0, 3.6], [7.2, 2.4]]); fillStroke(ctx, '#e6dcc2', INK, .4);
    for (const y of [-1.8, -.4, 1]) { stroke(ctx, [[-6, y - .6], [-1.2, y + .4]], rgba(INK, .4), .3); stroke(ctx, [[1.2, y + .4], [6, y - .6]], rgba(INK, .4), .3); }
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = glowGradient(ctx, 9, look.fx.length ? ELEMENT_COLOUR[look.fx[0]] : '#b48cff', .35 + Math.sin(t * .006) * .08);
    ctx.beginPath(); ctx.arc(0, -2, 9, 0, TAU); ctx.fill(); ctx.restore();
    return;
  }
  poly(ctx, [[-5, -6.4], [5, -6.4], [5, 6.4], [-5, 6.4]]); fillStroke(ctx, cel(ctx, -5, 5, P.clothShade, P.clothDeep, .6), INK, .5);
  poly(ctx, [[4.2, -6.4], [5.6, -6], [5.6, 6], [4.2, 6.4]]); fillStroke(ctx, '#efe6cf', INK, .4);
  stroke(ctx, [[-3.6, -5], [-3.6, 5]], P.accent, .7); ctx.beginPath(); ctx.arc(.4, 0, 1.6, 0, TAU); fillStroke(ctx, P.accent, INK, .4);
}
export function lantern(ctx, P, look, {t = 0, swing = 0} = {}) {
  ctx.save(); ctx.rotate(swing);
  stroke(ctx, [[0, -1], [0, 3]], INK, .6);
  const flicker = .85 + Math.sin(t * .02) * .06 + Math.sin(t * .047) * .05;
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = glowGradient(ctx, 20, '#ffcf6b', .32 * flicker);
  ctx.beginPath(); ctx.arc(0, 9, 20, 0, TAU); ctx.fill(); ctx.restore();
  poly(ctx, [[-3.4, 3], [3.4, 3], [4.2, 13.6], [-4.2, 13.6]]); fillStroke(ctx, rgba('#ffd98a', .9), INK, .45);
  poly(ctx, [[-2.4, 4.6], [2.4, 4.6], [2.8, 12.2], [-2.8, 12.2]]); ctx.fillStyle = rgba('#fff3c4', .8 * flicker); ctx.fill();
  poly(ctx, [[-4, 2.2], [4, 2.2], [4.4, 3.6], [-4.4, 3.6]]); fillStroke(ctx, P.leatherDeep, INK, .4);
  poly(ctx, [[-4.6, 13.2], [4.6, 13.2], [4, 15], [-4, 15]]); fillStroke(ctx, P.leatherDeep, INK, .4);
  for (const x of [-2.9, 2.9]) stroke(ctx, [[x, 3.4], [x * 1.2, 13.4]], INK, .4);
  ctx.restore();
}

// ---------------------------------------------------------------------------
// WEAPONS. Frame: the grip centre; local -y is the business end, +y the butt.
// Returns nothing; geometry for sockets lives in WEAPON_GEOMETRY.
export const WEAPON_GEOMETRY = Object.freeze({
  sword: {tip: 33, butt: 7, grip2: 0}, sword2: {tip: 45, butt: 12, grip2: 7},
  dagger: {tip: 16, butt: 4.6, grip2: 0}, axe: {tip: 27, butt: 8, grip2: 0}, axe2: {tip: 38, butt: 16, grip2: 12},
  mace: {tip: 26, butt: 7, grip2: 0}, mace2: {tip: 34, butt: 14, grip2: 10},
  // A quarterstaff held upright stands on the floor beside its bearer, as
  // Wren's does; a spear stands a head taller than the one who carries it.
  polearm: {tip: 60, butt: 50, grip2: 26}, staff: {tip: 44, butt: 50, grip2: 20}, wand: {tip: 17, butt: 3, grip2: 0},
  bow: {tip: 0, butt: 0, grip2: 0}, none: {tip: 4, butt: 0, grip2: 0},
});
// Extension points: a new weapon silhouette or outfit is a painter plus data.
// registerWeapon(kind, painter(ctx, P, look, main, {glow, t}), {tip, butt, grip2});
// registerOutfit(id, painter(ctx, P, look, d, {sw, cw, ww, wy})) draws inside the torso outline.
const EXTRA_WEAPONS = new Map(), EXTRA_OUTFITS = new Map();
export function registerWeapon(kind, painter, geometry) { EXTRA_WEAPONS.set(kind, {painter, geometry: {tip: 20, butt: 5, grip2: 0, ...geometry}}); }
export function registerOutfit(id, painter) { EXTRA_OUTFITS.set(id, painter); }
export function weaponGeometry(main) {
  if (EXTRA_WEAPONS.has(main.kind)) return EXTRA_WEAPONS.get(main.kind).geometry;
  const heavy = main.hands === 2 && ['sword', 'axe', 'mace'].includes(main.kind);
  return WEAPON_GEOMETRY[heavy ? main.kind + '2' : main.kind] || WEAPON_GEOMETRY.none;
}

function finishMarks(ctx, P, main, x, y0, y1) {
  if (main.finish === 'runed') {
    const c = main.fx.length ? ELEMENT_COLOUR[main.fx[0]] : '#7fe0d6';
    for (let y = y0; y > y1; y -= 4.2) { poly(ctx, [[x, y - 1.3], [x + 1.1, y], [x, y + 1.3], [x - 1.1, y]]); ctx.fillStyle = c; ctx.fill(); }
  } else if (main.finish === 'weathered') {
    for (let y = y0; y > y1; y -= 6) stroke(ctx, [[x - 1.4, y], [x + .8, y - 1.6]], rgba('#3d2f28', .6), .5);
  }
}

export function weapon(ctx, P, look, main, {glow = 0, t = 0} = {}) {
  const kind = main.kind, M = MATERIALS[main.material] || MATERIALS.steel, heavy = main.hands === 2;
  const S = MATERIALS[main.material === 'wood' ? 'steel' : main.material] || MATERIALS.steel;
  const trim = main.finish === 'ceremonial' ? MATERIALS.gold : main.material === 'gold' ? MATERIALS.gold : {base: P.accent, shade: P.accentShade, hi: P.accentHi, deep: P.accentShade};
  const wide = main.finish === 'heavy' ? 1.35 : 1, dense = main.dense ? 1.15 : 1;
  const grip = (y0, y1, w = 2.4) => { poly(ctx, [[-w / 2, y0], [w / 2, y0], [w / 2, y1], [-w / 2, y1]]); fillStroke(ctx, cel(ctx, -w / 2, w / 2, P.leather, P.leatherDeep, .5)); for (let y = y0 + 1.2; y < y1; y += 1.6) stroke(ctx, [[-w / 2, y], [w / 2, y - .8]], P.leatherDeep, .35); };
  const pommel = (y, r = 1.6) => { ctx.beginPath(); ctx.arc(0, y, r, 0, TAU); fillStroke(ctx, metalRamp(ctx, -r, r, trim)); };
  const bladeGlow = (pts) => {
    if (!glow) return;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; poly(ctx, pts); ctx.strokeStyle = rgba(main.fx.length ? ELEMENT_COLOUR[main.fx[0]] : '#fff3c4', .55 * glow); ctx.lineWidth = 2.6; ctx.stroke();
    ctx.globalAlpha = .35 * glow; ctx.fillStyle = main.fx.length ? ELEMENT_COLOUR[main.fx[0]] : '#fff3c4'; ctx.fill(); ctx.restore();
  };
  ctx.save(); ctx.scale(dense, 1);
  if (EXTRA_WEAPONS.has(kind)) EXTRA_WEAPONS.get(kind).painter(ctx, P, look, main, {glow, t});
  else if (kind === 'sword') {
    const tip = heavy ? 45 : 33, w = (heavy ? 3.4 : 2.8) * wide, base = -3.2, butt = heavy ? 10 : 5;
    const pts = [[-w / 2, base], [-w / 2, -tip + 5], [0, -tip], [w / 2, -tip + 5], [w / 2, base]];
    bladeGlow(pts);
    poly(ctx, pts); fillStroke(ctx, S.base, INK, LW);
    poly(ctx, [[0, base], [0, -tip], [w / 2, -tip + 5], [w / 2, base]]); fillStroke(ctx, S.shade, null);
    stroke(ctx, [[-w * .18, base - 1], [-w * .18, -tip + 6]], S.hi, .45);
    finishMarks(ctx, P, main, 0, base - 3, -tip + 8);
    poly(ctx, pts); ctx.strokeStyle = INK; ctx.lineWidth = LW; ctx.stroke();
    const gw = (heavy ? 7.4 : 6.2) * wide;
    poly(ctx, [[-gw, base - .2], [gw, base - .2], [gw - .6, base + 1.6], [-gw + .6, base + 1.6]]); fillStroke(ctx, metalRamp(ctx, -gw, gw, trim));
    grip(base + 1.6, butt); pommel(butt + 1.3, heavy ? 2 : 1.6);
    if (main.finish === 'ceremonial') { ctx.beginPath(); ctx.arc(0, base + .7, .9, 0, TAU); fillStroke(ctx, '#c0504d', INK, .35); }
  } else if (kind === 'dagger') {
    const tip = 16, w = 2.4 * wide;
    const pts = [[-w / 2, -2.4], [-w * .4, -tip + 4], [0, -tip], [w / 2, -tip + 3], [w / 2, -2.4]];
    bladeGlow(pts);
    poly(ctx, pts); fillStroke(ctx, S.base, INK, LW); poly(ctx, [[0, -2.4], [0, -tip], [w / 2, -tip + 3], [w / 2, -2.4]]); fillStroke(ctx, S.shade, null);
    poly(ctx, pts); ctx.strokeStyle = INK; ctx.lineWidth = LW; ctx.stroke();
    poly(ctx, [[-3.6, -2.6], [3.6, -2.6], [3.2, -1.2], [-3.2, -1.2]]); fillStroke(ctx, metalRamp(ctx, -3.6, 3.6, trim));
    grip(-1.2, 3.4, 2.1); pommel(4.2, 1.2);
  } else if (kind === 'axe' || kind === 'mace') {
    const top = heavy ? 38 : 27, butt = heavy ? 16 : 8, hw = heavy ? 3 : 2.4;
    poly(ctx, [[-hw / 2, butt], [hw / 2, butt], [hw / 2, -top + 2], [-hw / 2, -top + 2]]);
    fillStroke(ctx, cel(ctx, -hw / 2, hw / 2, MATERIALS.wood.base, MATERIALS.wood.shade, .5));
    grip(-1.4, 4.2, hw + .5);
    if (kind === 'axe') {
      const s = (heavy ? 1.45 : 1) * wide, y = -top + 3;
      const pts = [[1, y], [7 * s, y - 5 * s], [11 * s, y - 2 * s], [11.6 * s, y + 4.6 * s], [8 * s, y + 9 * s], [5.2 * s, y + 6.4 * s], [1, y + 5]];
      bladeGlow(pts);
      poly(ctx, pts); fillStroke(ctx, metalRamp(ctx, 1, 11.6 * s, S));
      stroke(ctx, [[10.4 * s, y - 1.4 * s], [11 * s, y + 4.4 * s], [8 * s, y + 8 * s]], S.hi, .6);
      if (heavy) { poly(ctx, [[-1, y], [-5.4, y - 1.6], [-6, y + 4], [-1, y + 5]]); fillStroke(ctx, metalRamp(ctx, -6, -1, S)); }
      finishMarks(ctx, P, main, 6 * s, y + 3, y);
    } else {
      const s = (heavy ? 1.35 : 1) * wide, y = -top + 2;
      const pts = [[-4 * s, y + 5], [-4.6 * s, y - 2], [0, y - 6 * s], [4.6 * s, y - 2], [4 * s, y + 5], [0, y + 7]];
      bladeGlow(pts);
      poly(ctx, pts); fillStroke(ctx, metalRamp(ctx, -4.6 * s, 4.6 * s, S));
      for (const x of [-2.4, 0, 2.4]) stroke(ctx, [[x * s, y - 4], [x * s, y + 5]], rgba(INK, .5), .45);
    }
    pommel(butt + 1, 1.3);
  } else if (kind === 'polearm') {
    poly(ctx, [[-1.25, 50], [1.25, 50], [1.25, -45], [-1.25, -45]]); fillStroke(ctx, cel(ctx, -1.25, 1.25, MATERIALS.wood.base, MATERIALS.wood.shade, .5));
    for (const y of [-2, 24]) grip(y - 1.6, y + 3, 3);
    poly(ctx, [[-1.5, 47], [1.5, 47], [1.2, 50.5], [-1.2, 50.5]]); fillStroke(ctx, metalRamp(ctx, -1.5, 1.5, S));
    const pts = [[-2.6 * wide, -44], [-1.6 * wide, -52], [0, -60], [1.6 * wide, -52], [2.6 * wide, -44], [0, -42]];
    bladeGlow(pts);
    poly(ctx, pts); fillStroke(ctx, S.base, INK, LW); poly(ctx, [[0, -42], [0, -60], [1.6 * wide, -52], [2.6 * wide, -44]]); fillStroke(ctx, S.shade, null);
    poly(ctx, pts); ctx.strokeStyle = INK; ctx.lineWidth = LW; ctx.stroke();
    poly(ctx, [[-2.8, -45.4], [2.8, -45.4], [2.2, -43], [-2.2, -43]]); fillStroke(ctx, metalRamp(ctx, -2.8, 2.8, trim));
    stroke(ctx, [[-2.2, -43], [-4.6, -39.6]], P.accent, .7); stroke(ctx, [[-2, -42.6], [-3.2, -38.4]], P.accentShade, .6);   // pennant cords
    finishMarks(ctx, P, main, 0, -47, -55);
  } else if (kind === 'staff') {
    const style = main.finish;
    poly(ctx, [[-1.3, 50], [1.3, 50], [1.5, -37], [-1.5, -37]]); fillStroke(ctx, cel(ctx, -1.5, 1.5, M.base, M.shade, .5));
    poly(ctx, [[-1.5, 46.5], [1.5, 46.5], [1.3, 50.4], [-1.3, 50.4]]); fillStroke(ctx, trim.base, INK, .4);
    for (const y of [-5, 14]) stroke(ctx, [[-1.5, y], [1.5, y - .8]], M.shade, .5);
    finishMarks(ctx, P, main, 0, 16, -32);
    // Head: a caged crystal whose colour follows the staff's element.
    const c = main.fx.length ? ELEMENT_COLOUR[main.fx[0]] : '#8fd0cb', hy = -41;
    if (glow || main.fx.length) { ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = glowGradient(ctx, 10, c, .4 + glow * .3); ctx.beginPath(); ctx.arc(0, hy, 10, 0, TAU); ctx.fill(); ctx.restore(); }
    poly(ctx, [[0, hy - 5], [2.9, hy], [0, hy + 4.4], [-2.9, hy]]); fillStroke(ctx, c, INK, .5); poly(ctx, [[0, hy - 5], [0, hy + 4.4], [-2.9, hy]]); fillStroke(ctx, rgba('#ffffff', .35), null);
    stroke(ctx, [[-1.5, hy + 4.4], [-3.7, hy], [-1.2, hy - 4.2]], trim.base, .8); stroke(ctx, [[1.5, hy + 4.4], [3.7, hy], [1.2, hy - 4.2]], trim.base, .8);
    if (style === 'ceremonial') { ctx.beginPath(); ctx.arc(0, hy - 6.6, 1.3, 0, TAU); fillStroke(ctx, trim.base, INK, .4); }
  } else if (kind === 'wand') {
    poly(ctx, [[-.9, 3], [.9, 3], [.7, -13.4], [-.7, -13.4]]); fillStroke(ctx, cel(ctx, -.9, .9, M.base, M.shade, .5));
    grip(-2, 3, 1.8);
    const c = main.fx.length ? ELEMENT_COLOUR[main.fx[0]] : '#b48cff';
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = glowGradient(ctx, 6, c, .35 + glow * .3); ctx.beginPath(); ctx.arc(0, -15, 6, 0, TAU); ctx.fill(); ctx.restore();
    poly(ctx, [[0, -17.4], [1.3, -14.8], [0, -12.8], [-1.3, -14.8]]); fillStroke(ctx, c, INK, .45);
  }
  ctx.restore();
}

// Bow: held in the far hand, frame at the grip, limbs along local y; `draw`
// pulls the string back toward -x by `pull` units (to the drawing hand).
export function bow(ctx, P, look, main, {pull = 0, arrow = false} = {}) {
  const M = MATERIALS[main.material] || MATERIALS.wood, L = 26;
  const c = main.fx.length ? ELEMENT_COLOUR[main.fx[0]] : null;
  // String first so the limbs cover its ends.
  stroke(ctx, [[-1.5, -L], [-1.5 - pull, 0], [-1.5, L]], '#efe8d4', .45);
  if (arrow) {
    stroke(ctx, [[-1.5 - pull, 0], [16, 0]], '#8c6a44', .8);
    poly(ctx, [[16, -1.3], [19.6, 0], [16, 1.3]]); fillStroke(ctx, c || '#dfe5ea', INK, .35);
    poly(ctx, [[-1.5 - pull, 0], [-4.5 - pull, -1.6], [-2.5 - pull, 0], [-4.5 - pull, 1.6]]); fillStroke(ctx, look.palette.accent, INK, .3);
  }
  ctx.beginPath(); ctx.moveTo(-1.5, -L); ctx.bezierCurveTo(4, -L * .8, 5.6, -L * .45, 2.2, -2.6); ctx.lineTo(2.2, 2.6);
  ctx.bezierCurveTo(5.6, L * .45, 4, L * .8, -1.5, L);
  ctx.lineWidth = 3.4; ctx.strokeStyle = INK; ctx.lineCap = 'round'; ctx.stroke();
  ctx.lineWidth = 2.2; ctx.strokeStyle = M.base; ctx.stroke();
  if (c) { ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineWidth = 1; ctx.strokeStyle = rgba(c, .8); ctx.stroke(); ctx.restore(); }
  poly(ctx, [[.6, -3.4], [3.2, -3.4], [3.2, 3.4], [.6, 3.4]]); fillStroke(ctx, P.leatherShade, INK, .4);
}

// Scabbard for a stowed or drawn blade, frame on the far hip.
export function scabbard(ctx, P, main) {
  const len = main.kind === 'dagger' ? 15 : main.hands === 2 ? 42 : 31;
  poly(ctx, [[-1.9, 0], [1.9, 0], [1.6, len], [0, len + 2], [-1.6, len]]); fillStroke(ctx, cel(ctx, -1.9, 1.9, P.leather, P.leatherDeep, .5));
  poly(ctx, [[-2.1, -.4], [2.1, -.4], [2.1, 2.2], [-2.1, 2.2]]); fillStroke(ctx, P.accent, INK, .4);
  poly(ctx, [[-1.7, len - 2.4], [1.7, len - 2.4], [0, len + 2]]); fillStroke(ctx, P.accentShade, INK, .35);
}

// Quiver on the back for bows.
export function quiver(ctx, P) {
  poly(ctx, [[-2.8, -2], [2.8, -2], [2.4, 20], [-2.4, 20]]); fillStroke(ctx, cel(ctx, -2.8, 2.8, P.leather, P.leatherDeep, .55));
  for (const x of [-1.4, 0, 1.4]) { stroke(ctx, [[x, -2], [x - .4, -7]], '#8c6a44', .45); poly(ctx, [[x - .4, -7], [x - 1.4, -9.4], [x + .6, -9.4]]); fillStroke(ctx, P.accent, INK, .3); }
  stroke(ctx, [[-2.6, 4], [2.6, 5]], P.accent, .6);
}

export function shadow(ctx, x, y, rx, ry, alpha = .3) {
  ctx.save(); ctx.fillStyle = `rgba(0,0,0,${alpha.toFixed(3)})`; ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, TAU); ctx.fill(); ctx.restore();
}
