// Wren's paperdoll: layered vector parts bound to the shared SkeletalRig.
//
// Same contract as doran-rig.js: every part is drawn in its bone's local frame
// (+y runs down the bone), so forward kinematics, IK and pose blending move her
// exactly as they move every other figure. Clean Cel style (2026-09-23 guide):
// one ink weight, two-tone flat fills, silhouette-first poses.
//
// Canon locks (DM041_D Appearance, DM040_0, DM041_B2, DM048_0):
//   half-elf woman, 5'6"-5'7", slim; long red hair, freckles, soft features;
//   she normally floats -- relaxed hover a little off the ground, wings
//   dismissed; white Otherworldly Wings manifest only for real flight;
//   Robe of the Archmagi in brilliant white and gold carrying six stars that
//   leave the garment when spent; a permanent crown of seven star motes;
//   Weave-sight glasses; Cloak of Protection matching Doran's; Staff of the
//   Magi in divine white wood with a black bird standing on a metal perch;
//   the Black-Bird Sigil is a black bird, wings spread, ENCLOSED in white.
//   Nothing that makes her survivable is visible: no plate, no bulk.
//
// Presentation only: this draws outcomes the host has already resolved and
// never reads or decides mechanics.

import {SkeletalRig} from './skeletal-rig.js';

const TAU = Math.PI * 2;
// Rig units per foot at the shared 5'8" puppet baseline (97 units tall).
export const RIG_UNITS_PER_FOOT = 97 / (68 / 12);
const FT = RIG_UNITS_PER_FOOT;
export const WREN_HEIGHT_UNITS = (5 + 6.5 / 12) * FT;   // 5'6.5"
export const WREN_FLOAT = 7;                             // rest hover, units (~5 in)
export const CROWN_MOTES = 7;
export const ROBE_STARS = 6;

// Slim, long-limbed half-elf frame measured to 5'6.5".
const SKELETON = Object.freeze({
  pelvis: {x: 0, y: -53}, spine: {y: -8}, torso: {y: -14.5}, neck: {y: -5}, head: {x: 0, y: -.5},
  left_shoulder: {x: -9.5, y: 1}, right_shoulder: {x: 9.5, y: 1},
  left_upper_arm: {length: 15.5, angle: .1}, right_upper_arm: {length: 15.5, angle: -.06},
  left_lower_arm: {length: 13.5, angle: -.05}, right_lower_arm: {length: 13.5, angle: -.1},
  left_hip: {x: -6.5, y: 0}, right_hip: {x: 6.5, y: 0},
  left_thigh: {length: 24, angle: .03}, right_thigh: {length: 24, angle: -.03},
  left_shin: {length: 23, angle: 0}, right_shin: {length: 23, angle: 0},
});
const SOLE = 6;           // ankle to slipper sole
const HAND_REACH = 2.2;   // wrist to the centre of a gripping hand
const HEAD_TOP = 13.5;    // neck joint to crown of the head

// Staff of the Magi along its own axis; 0 = butt, +length = the perch.
export const STAFF = Object.freeze({length: 5.2 * FT, grip: 3.05 * FT, perch: 8, bird: 7.5});

export const WREN_PAPERDOLL_LAYERS = Object.freeze({
  'ground:shadow': {slot: 'ground', className: 'char-shadow wren-hover-shadow', z: 0},
  'wing:far': {slot: 'effect', className: 'char-wings wren-wing-far', bone: 'torso', z: 4},
  'cape:back': {slot: 'clothing', className: 'char-cape wren-cloak', bone: 'torso', z: 8},
  'hair:back': {slot: 'body', className: 'char-hair wren-hair-long', bone: 'head', z: 9},
  'wing:near': {slot: 'effect', className: 'char-wings wren-wing-near', bone: 'torso', z: 12},
  'arm:left': {slot: 'body', className: 'char-arm wren-sleeve-far', bone: 'left_upper_arm', z: 30},
  'hand:left': {slot: 'body', className: 'char-hand wren-hand-far', bone: 'left_hand', z: 34},
  'body:feet': {slot: 'clothing', className: 'char-boots wren-slippers', bone: 'pelvis', z: 48},
  'body:robe': {slot: 'clothing', className: 'char-coat wren-robe-skirt', bone: 'pelvis', z: 55},
  'body:torso': {slot: 'body', className: 'char-torso wren-robe-bodice', bone: 'torso', z: 60},
  'equipment:sigil': {slot: 'equipment', className: 'char-emblem wren-black-bird-sigil', bone: 'torso', z: 63},
  'fx:crown-back': {slot: 'effect', className: 'char-fx wren-crown-back', bone: 'head', z: 65},
  'body:head': {slot: 'body', className: 'char-head wren-face', bone: 'head', z: 70},
  'hair:front': {slot: 'body', className: 'char-fringe wren-hair-front', bone: 'head', z: 72},
  'equipment:glasses': {slot: 'equipment', className: 'char-eyes wren-weave-glasses', bone: 'head', z: 74},
  'hair:lock': {slot: 'body', className: 'char-hair wren-shoulder-lock', bone: 'torso', z: 82},
  'arm:right': {slot: 'body', className: 'char-arm wren-sleeve-near', bone: 'right_upper_arm', z: 90},
  'weapon:staff': {slot: 'weapon', className: 'char-weapon staff wren-staff-of-the-magi', bone: 'right_hand', z: 100},
  'hand:right': {slot: 'body', className: 'char-hand wren-hand-near', bone: 'right_hand', z: 104},
  'fx:crown-front': {slot: 'effect', className: 'char-fx wren-crown-front', bone: 'head', z: 118},
});
export const WREN_LOADOUTS = Object.freeze(['staff']);

// ---------------------------------------------------------------------------
// Palette (Clean Cel: each material is a flat base and one shade).
const C = {
  ink: '#10131b', inkSoft: 'rgba(16,19,27,.5)',
  robe: '#f7f4ed', robeShade: '#dcd5c7', robeDeep: '#bdb4a4',
  gold: '#d8b15a', goldShade: '#a47f35', goldHi: '#f4de9a',
  hair: '#b8402e', hairShade: '#842a1f', hairHi: '#d65f45',
  skin: '#f2d5bf', skinShade: '#d9ac92', freckle: '#c27b5d', lip: '#c9837a', eye: '#3a3140',
  navy: '#1b2233', navyShade: '#10141f', navyHi: '#38445f',
  wood: '#f2ede1', woodShade: '#cfc5b0',
  perch: '#4b505d', perchShade: '#2c2f38', bird: '#111218', birdHi: '#3a3d4a',
  wing: '#ffffff', wingShade: '#dde2ec', wingDeep: '#b9c1d0',
  mote: '#ffe7a0', moteCore: '#fff8dc', lens: 'rgba(190,228,255,.28)',
};

// ---------------------------------------------------------------------------
// Poses. Channels are plain numbers so any two poses blend:
//   py pa  pelvis drop / roll            sp to hd  spine / torso / head lean (+ forward)
//   lt ls rt rs  thigh and shin offsets (far = l, near = r; + swings back)
//   nu nl  far arm upper / forearm angles (used only while lying down)
//   fx fy  far (open) hand target, units relative to the pelvis
//   eb fb  near / far elbow fold sign (chosen per pose so each elbow points outward)
//   hx hy  staff-hand target, units relative to the PELVIS (she floats, so
//          targets ride with the body rather than the floor)
//   st  staff tilt (0 upright, + tips forward)   wing  wings manifested 0..1
//   flap  wingbeat amplitude   float  hover height (units)   air  lying down
const BASE = {py: 0, pa: 0, sp: 0, to: 0, hd: .05, lt: .05, ls: .22, rt: -.02, rs: .12, nu: .12, nl: -.25,
  hx: 12, hy: -3, fx: -12.5, fy: 1, eb: -1, fb: 1, st: .04, wing: 0, flap: 0, float: WREN_FLOAT, air: 0};
const P = over => Object.freeze({...BASE, ...over});
const DOWN = P({pa: -1.5, lt: 0, ls: .05, rt: .05, rs: .1, nu: -.4, nl: -.3, hd: .3, hx: 20, hy: -2, st: 1.5, float: 0, air: 1});
export const WREN_POSES = Object.freeze({
  // Relaxed hover: toes pointed, one knee soft, staff upright at her side.
  rest: P({}),
  // Combat ready: open far hand raised for a ward, staff angled forward.
  guard: P({fb: -1, fx: -21, fy: -19, sp: .06, to: .02, hd: -.03, lt: .22, ls: .32, rt: -.08, rs: .26, nu: -1.1, nl: -.6, hx: 13, hy: -8, st: .32, float: 8}),
  // Channel: far hand high, staff lifted; the crown brightens (drawn from ch.float).
  channel: P({eb: 1, fb: -1, fx: -13, fy: -47, sp: -.06, to: -.04, hd: -.16, lt: .1, ls: .18, rt: -.08, rs: .12, nu: -2.45, nl: -.2, hx: 12, hy: -26, st: -.08, float: 10}),
  // Release: far palm and staff thrust at the target.
  release: P({fb: -1, fx: -23, fy: -25, sp: .14, to: .08, hd: .02, lt: .3, ls: .3, rt: -.2, rs: .22, nu: -1.45, nl: -.08, hx: 19, hy: -15, st: .95, float: 9}),
  hit: P({fx: -16, fy: -8, sp: -.2, to: -.1, hd: -.26, lt: -.12, ls: .38, rt: -.28, rs: .42, nu: -.4, nl: -.95, hx: 8, hy: -8, st: -.35, float: 5}),
  // Evade: knees tucked, lifted higher.
  dodge: P({fx: -16, fy: -12, sp: .22, to: .05, lt: .55, ls: .85, rt: .22, rs: .95, nu: -.6, nl: -.8, hx: 9, hy: -6, st: .2, float: 13}),
  // Glide: the everyday travel float, leaning into the direction of motion.
  glide: P({fx: -14, fy: 2, sp: .22, to: .06, hd: -.06, lt: -.18, ls: .3, rt: -.3, rs: .22, nu: .45, nl: -.15, hx: 12, hy: -6, st: .35, float: 9}),
  // Real flight: wings out, legs trailing, staff carried forward.
  fly: P({fx: -16, fy: -5, sp: .38, to: .12, hd: -.12, lt: -.32, ls: .35, rt: -.48, rs: .3, nu: .55, nl: -.2, hx: 14, hy: -10, st: 1.15, wing: 1, flap: 1, float: 16}),
  victory: P({eb: 1, fb: -1, fx: -14, fy: -48, sp: -.08, hd: -.2, nu: -2.6, nl: -.1, hx: 10, hy: -30, st: -.05, float: 12}),
  look: P({hd: -.12, to: -.03}),
  point: P({fb: -1, fx: -27, fy: -23, to: .05, nu: -1.5, nl: -.02, hd: -.04}),
  study: P({fx: -5, fy: -24, hd: .18, nu: -.9, nl: -1.6}),
  down: DOWN, ko: DOWN,
});
const FIDGETS = ['look', 'study', 'look', 'point'];
const FLIGHT_POSES = new Set(['fly', 'jump', 'fall', 'airborne', 'flight']);
const TRAVEL_POSES = new Set(['run', 'travel', 'move', 'advance', 'retreat']);

// ---------------------------------------------------------------------------
// Drawing helpers (part-local units).
function poly(ctx, pts) { ctx.beginPath(); pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath(); }
function fillStroke(ctx, fill, stroke = C.ink, width = .55) {
  ctx.fillStyle = fill; ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.lineJoin = 'round'; ctx.stroke(); }
}
// Two-tone cel ramp: base holds flat to the split, shade after it.
function cel(ctx, x0, x1, base, shade, split = .6) {
  const g = ctx.createLinearGradient(x0, 0, x1, 0);
  g.addColorStop(0, base); g.addColorStop(split, base); g.addColorStop(split, shade); g.addColorStop(1, shade); return g;
}
function line(ctx, pts, colour, width = .5) {
  ctx.beginPath(); pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
  ctx.strokeStyle = colour; ctx.lineWidth = width; ctx.lineCap = 'round'; ctx.stroke();
}
function capsule(ctx, w0, w1, y0, y1) {
  ctx.beginPath(); ctx.moveTo(-w0 / 2, y0); ctx.quadraticCurveTo(0, y0 - w0 * .45, w0 / 2, y0);
  ctx.lineTo(w1 / 2, y1); ctx.quadraticCurveTo(0, y1 + w1 * .45, -w1 / 2, y1); ctx.closePath();
}
// Four-point star (robe stars and crown motes).
function star4(ctx, x, y, r, fill, stroke = C.ink) {
  const k = r * .34;
  poly(ctx, [[x, y - r], [x + k, y - k], [x + r, y], [x + k, y + k], [x, y + r], [x - k, y + k], [x - r, y], [x - k, y - k]]);
  fillStroke(ctx, fill, stroke, .4);
}
// The Black-Bird Sigil (DM048_0 FORM LOCK): a black bird, wings spread, fully
// enclosed by a white outline. The enclosure is part of the mark.
export function blackBirdSigil(ctx, s = 1) {
  ctx.save(); ctx.scale(s, s);
  ctx.beginPath(); ctx.arc(0, 0, 3.2, 0, TAU); fillStroke(ctx, '#ffffff', C.ink, .45);
  ctx.fillStyle = C.bird; ctx.beginPath();
  ctx.moveTo(0, -1.3);
  ctx.lineTo(.5, -.9); ctx.lineTo(2.5, -1.9); ctx.lineTo(2.2, -.9); ctx.lineTo(2.7, -.6);
  ctx.lineTo(1.6, .1); ctx.lineTo(.6, .3); ctx.lineTo(.8, 1.9); ctx.lineTo(0, 1.4);
  ctx.lineTo(-.8, 1.9); ctx.lineTo(-.6, .3); ctx.lineTo(-1.6, .1); ctx.lineTo(-2.7, -.6);
  ctx.lineTo(-2.2, -.9); ctx.lineTo(-2.5, -1.9); ctx.lineTo(-.5, -.9); ctx.closePath(); ctx.fill();
  ctx.restore();
}

// ---------------------------------------------------------------------------
// Part painters. Origins: the bone the part is bound to. Facing right (+x).
const PAINT = {
  wing(ctx, {open = 1, beat = 0}) {
    // Root at the shoulder blade; the wing sweeps up and back (-x).
    ctx.save(); ctx.rotate(-.7 + beat * .55); ctx.scale(open * .85, open * .85);
    const outline = () => {
      ctx.beginPath(); ctx.moveTo(0, 0);
      ctx.bezierCurveTo(-4, -14, -12, -24, -22, -27);        // leading edge to the wrist
      ctx.quadraticCurveTo(-34, -29, -46, -24);              // hand to the tip
      const feathers = [[-43, -18], [-49, -12], [-39, -9], [-44, -2], [-33, -1], [-36, 7], [-25, 4], [-26, 12], [-15, 7], [-14, 14], [-6, 8]];
      for (const [x, y] of feathers) ctx.lineTo(x, y);
      ctx.quadraticCurveTo(-2, 6, 0, 0); ctx.closePath();
    };
    outline(); fillStroke(ctx, C.wing, null);
    ctx.save(); outline(); ctx.clip();
    ctx.fillStyle = C.wingShade; poly(ctx, [[-4, 2], [-46, -10], [-50, 20], [-2, 20]]); ctx.fill();   // one shade: the flight feathers
    for (const [x0, y0, x1, y1] of [[-10, -6, -18, 9], [-18, -12, -28, 6], [-26, -17, -38, 2], [-34, -21, -44, -9]]) line(ctx, [[x0, y0], [x1, y1]], C.wingDeep, .45);
    ctx.restore();
    outline(); ctx.strokeStyle = C.ink; ctx.lineWidth = .55; ctx.lineJoin = 'round'; ctx.stroke();
    ctx.restore();
  },
  cloak(ctx, {trail = 0, t = 0}) {
    // Cloak of Protection -- Doran wears the matching one. Short, shoulder to mid-back.
    const flare = Math.max(0, trail) * 10, wave = Math.sin(t * .0019) * .7, len = 30;
    ctx.beginPath(); ctx.moveTo(-9.5, -2.5); ctx.lineTo(8.5, -2.5);
    ctx.bezierCurveTo(10, 10, 8 - flare * .2, len * .7, 6 - flare * .4, len);
    for (let i = 1; i <= 5; i++) { const x = 6 - flare * .4 - i * (19 + flare) / 5; ctx.lineTo(x + 1.6, len + (i % 2 ? 1.6 + wave : -.2)); ctx.lineTo(x, len + (i % 2 ? .3 : 1.2 - wave)); }
    ctx.bezierCurveTo(-15 - flare, len * .7, -13 - flare * .4, 10, -9.5, -2.5); ctx.closePath();
    fillStroke(ctx, cel(ctx, -16 - flare, 9, C.navyHi, C.navy, .35));
    ctx.save(); ctx.clip(); ctx.globalAlpha = .45;
    for (const x of [-9, -3, 3]) line(ctx, [[x * .8, 4], [x - flare * .4, len]], C.navyShade, 1.1);
    ctx.restore();
  },
  // Long red hair hanging behind her. Drawn in an upright frame at the head so
  // it falls with gravity; `sway` trails it against motion.
  hairBack(ctx, {sway = 0, t = 0}) {
    const w = Math.sin(t * .0016) * .8, tx = -sway * 9;
    ctx.beginPath(); ctx.moveTo(-4.8, -12.5);
    ctx.bezierCurveTo(-8.8, -9, -8.6, 0, -9.2, 6);
    ctx.bezierCurveTo(-10 + tx * .4, 14, -11 + tx * .7, 22, -9.5 + tx + w, 30);
    ctx.lineTo(-7 + tx + w, 27.5); ctx.lineTo(-5.4 + tx * .9 + w, 31); ctx.lineTo(-3.8 + tx * .8, 26);
    ctx.bezierCurveTo(-1 + tx * .5, 18, 1.2, 10, 1.6, 4);
    ctx.lineTo(3.4, -1); ctx.bezierCurveTo(4, -8, 1, -13.5, -4.8, -12.5); ctx.closePath();
    fillStroke(ctx, cel(ctx, -11, 2, C.hair, C.hairShade, .42));
    ctx.save(); ctx.clip();
    line(ctx, [[-6.5, -4], [-7.4 + tx * .5, 14], [-7 + tx + w, 27]], C.hairShade, .5);
    line(ctx, [[-2.5, 2], [-3.4 + tx * .4, 16], [-4.6 + tx * .8, 25]], C.hairShade, .5);
    ctx.restore();
  },
  // Lock falling in front of the near shoulder (torso frame).
  hairLock(ctx, {sway = 0}) {
    const tx = -sway * 3;
    ctx.beginPath(); ctx.moveTo(1.5, -5.5); ctx.bezierCurveTo(4.8, -2, 5.4, 4, 4.6 + tx, 11);
    ctx.lineTo(3.2 + tx, 13.5); ctx.lineTo(2.6 + tx, 10); ctx.bezierCurveTo(2.8, 4, 1.4, -1, -.4, -4.4); ctx.closePath();
    fillStroke(ctx, cel(ctx, 0, 5.5, C.hair, C.hairShade, .6));
  },
  sleeveUpper(ctx) {
    capsule(ctx, 6, 6.6, 1, 15.8);
    fillStroke(ctx, cel(ctx, -3.3, 3.3, C.robe, C.robeShade, .6));
    // Mantle cap at the shoulder, gold-edged.
    ctx.beginPath(); ctx.moveTo(-5.2, 4.2); ctx.bezierCurveTo(-6, -2.4, -3, -4.8, .4, -4.6);
    ctx.bezierCurveTo(3.8, -4.4, 6, -2, 5.4, 4.4); ctx.quadraticCurveTo(0, 6.4, -5.2, 4.2); ctx.closePath();
    fillStroke(ctx, cel(ctx, -5.6, 5.6, C.robe, C.robeShade, .62));
    line(ctx, [[-5, 3.6], [0, 5.6], [5.2, 3.8]], C.gold, .9);
  },
  // Bell sleeve: flares toward the wrist, gold cuff band.
  sleeveLower(ctx) {
    ctx.beginPath(); ctx.moveTo(-3.2, .5); ctx.lineTo(3.4, .5); ctx.lineTo(5.8, 12.8);
    ctx.quadraticCurveTo(.2, 15, -5.2, 12.4); ctx.closePath();
    fillStroke(ctx, cel(ctx, -5.2, 5.8, C.robe, C.robeShade, .58));
    poly(ctx, [[-4.9, 10.6], [5.4, 10.8], [5.8, 12.8], [-5.2, 12.4]]); fillStroke(ctx, C.gold, C.ink, .4);
  },
  hand(ctx, {open = false}) {
    if (open) {             // ward palm: fingers together, spread slightly
      ctx.beginPath(); ctx.moveTo(-1.8, -.6); ctx.lineTo(1.9, -.6); ctx.lineTo(2.4, 4.2);
      ctx.lineTo(1.2, 6.8); ctx.lineTo(-.4, 6.4); ctx.lineTo(-1.6, 4.4); ctx.lineTo(-3.2, 2.6); ctx.lineTo(-2.2, 1.4); ctx.closePath();
    } else { ctx.beginPath(); ctx.roundRect(-2.3, -.4, 4.6, 4.8, 1.5); }
    fillStroke(ctx, cel(ctx, -2.4, 2.4, C.skin, C.skinShade, .62));
  },
  slipper(ctx, {point = .8}) {
    // Floating feet point down; white slipper, gold vamp line.
    ctx.save(); ctx.rotate(-point * .9);
    ctx.beginPath(); ctx.moveTo(-2, -1.4); ctx.lineTo(2, -1.4); ctx.quadraticCurveTo(2.8, 2.2, 4.4, 3.6);
    ctx.quadraticCurveTo(6.4, 4.8, 6.2, 6); ctx.lineTo(-2.6, 6); ctx.quadraticCurveTo(-3, 2.4, -2, -1.4); ctx.closePath();
    fillStroke(ctx, cel(ctx, -3, 6.4, C.robe, C.robeShade, .6));
    line(ctx, [[-1.8, 1.4], [2.6, 1.6]], C.gold, .6);
    ctx.restore();
  },
  // Robe skirt from the hips to just above the ankles, following the legs.
  skirt(ctx, {swing = 0, stars = ROBE_STARS, t = 0}) {
    const hem = 45, flare = 13, sway = Math.sin(t * .0017) * .6;
    ctx.save(); ctx.rotate(swing);
    const outline = () => {
      ctx.beginPath(); ctx.moveTo(-7, -2); ctx.lineTo(7, -2);
      ctx.bezierCurveTo(9, 14, flare - 2, 30, flare + sway, hem);
      ctx.quadraticCurveTo(0, hem + 2.6, -flare - 1 + sway, hem - .8);
      ctx.bezierCurveTo(-flare + 1, 30, -9, 14, -7, -2); ctx.closePath();
    };
    outline(); fillStroke(ctx, cel(ctx, -flare, flare, C.robe, C.robeShade, .62), null);
    ctx.save(); outline(); ctx.clip();
    // Front opening panel and the gold hem band.
    poly(ctx, [[1.4, -2], [3.6, -2], [7.4, hem + 3], [3, hem + 3]]); fillStroke(ctx, C.robeDeep, null);
    line(ctx, [[1.4, -2], [3, hem + 3]], C.gold, .9); line(ctx, [[3.6, -2], [7.4, hem + 3]], C.gold, .9);
    ctx.fillStyle = C.gold; poly(ctx, [[-flare - 3, hem - 3.4], [flare + 3, hem - 2.6], [flare + 3, hem + 3], [-flare - 3, hem + 3]]); ctx.fill();
    line(ctx, [[-flare - 3, hem - 3.4], [flare + 3, hem - 2.6]], C.goldShade, .45);
    ctx.restore();
    outline(); ctx.strokeStyle = C.ink; ctx.lineWidth = .55; ctx.lineJoin = 'round'; ctx.stroke();
    // Robe stars on the skirt: four of the six. They leave when spent.
    const spots = [[-5, 14], [5.5, 17], [-8, 29], [8.5, 32]];
    spots.slice(0, Math.max(0, stars - 2)).forEach(([x, y]) => star4(ctx, x, y, 2.3, C.gold));
    ctx.restore();
  },
  bodice(ctx, {stars = ROBE_STARS}) {
    // Slim bodice; no plate, no bulk (DM041_D: durability is unsigned).
    ctx.beginPath(); ctx.moveTo(-8.6, -2.4); ctx.quadraticCurveTo(0, -4.4, 8.6, -2.4);
    ctx.quadraticCurveTo(9.6, 6, 7.4, 12); ctx.quadraticCurveTo(6.4, 17, 6.8, 22.5);
    ctx.lineTo(-6.8, 22.5); ctx.quadraticCurveTo(-6.4, 17, -7.4, 12); ctx.quadraticCurveTo(-9.6, 6, -8.6, -2.4); ctx.closePath();
    fillStroke(ctx, cel(ctx, -9, 9, C.robe, C.robeShade, .64));
    // V neckline with gold edging.
    poly(ctx, [[-3.4, -3.4], [3.8, -3.4], [.4, 4.2]]); fillStroke(ctx, C.skin, null);
    line(ctx, [[-3.8, -3.4], [.4, 4.6], [4.2, -3.4]], C.gold, 1);
    // Gold sash at the waist.
    poly(ctx, [[-7, 17.6], [7, 17.6], [6.9, 21], [-6.9, 21]]); fillStroke(ctx, C.gold, C.ink, .45);
    poly(ctx, [[.6, 17.2], [3.2, 17.2], [3.4, 21.4], [.4, 21.4]]); fillStroke(ctx, C.goldShade, C.ink, .4);
    // The other two robe stars ride the bodice.
    [[-4.6, 10], [5, 12]].slice(0, Math.max(0, Math.min(2, stars))).forEach(([x, y]) => star4(ctx, x, y, 2, C.gold));
  },
  sigil(ctx) { ctx.save(); ctx.translate(-4.2, 3.2); blackBirdSigil(ctx, .72); ctx.restore(); },
  face(ctx) {
    // Pointed half-elf ear, back of the head.
    ctx.beginPath(); ctx.moveTo(-3.4, -8); ctx.lineTo(-7.8, -12.6); ctx.lineTo(-5.2, -5.2); ctx.quadraticCurveTo(-4, -4.4, -3.2, -5.4); ctx.closePath();
    fillStroke(ctx, cel(ctx, -7.8, -3, C.skin, C.skinShade, .45));
    // Soft oval face, three-quarter right.
    ctx.beginPath(); ctx.moveTo(-4.6, -8);
    ctx.bezierCurveTo(-5, -12.8, 4.6, -14, 5.6, -8.6);
    ctx.bezierCurveTo(6.2, -5.4, 5.6, -2.6, 3.8, -.6);
    ctx.quadraticCurveTo(1.8, 1, -.6, .4); ctx.bezierCurveTo(-3.4, -.6, -4.6, -4, -4.6, -8); ctx.closePath();
    fillStroke(ctx, cel(ctx, -4.6, 5.8, C.skin, C.skinShade, .78));
    // Eyes (calm, serene default), brows, mouth.
    for (const x of [1.2, 4.3]) { ctx.fillStyle = C.eye; ctx.beginPath(); ctx.ellipse(x, -6.6, .62, .9, 0, 0, TAU); ctx.fill(); }
    line(ctx, [[.3, -8.7], [2, -9]], C.hairShade, .45); line(ctx, [[3.6, -9], [5, -8.6]], C.hairShade, .45);
    line(ctx, [[4.6, -5.4], [5.2, -3.8], [4.5, -3.6]], C.skinShade, .4);
    line(ctx, [[2.4, -1.9], [3.8, -2]], C.lip, .5);
    // Freckles across the nose and cheeks.
    ctx.fillStyle = C.freckle;
    for (const [x, y] of [[.2, -4.6], [1, -4], [1.8, -4.8], [3.4, -4.4], [4, -5], [5, -4.4], [.8, -5.2]]) { ctx.beginPath(); ctx.arc(x, y, .22, 0, TAU); ctx.fill(); }
  },
  hairFront(ctx) {
    // Crown and side-swept fringe; the ear tip shows through.
    ctx.beginPath(); ctx.moveTo(-5.6, -6);
    ctx.bezierCurveTo(-7, -13, -1, -16, 3.6, -14.2);
    ctx.bezierCurveTo(6.6, -13, 7.2, -10.2, 6.2, -7.8);
    ctx.quadraticCurveTo(4.4, -10.8, 1.4, -10.6); ctx.quadraticCurveTo(-.4, -8.2, -2.6, -8.8);
    ctx.quadraticCurveTo(-3.8, -7.2, -3.4, -3.4); ctx.lineTo(-5.4, -2.4); ctx.closePath();
    fillStroke(ctx, cel(ctx, -7, 7, C.hairHi, C.hair, .38));
    line(ctx, [[-1.8, -13.6], [1.6, -10.8]], C.hairShade, .45);
  },
  glasses(ctx) {
    // Weave-sight glasses: thin gold rims, faint lens tint.
    for (const x of [1.2, 4.4]) {
      ctx.beginPath(); ctx.ellipse(x, -6.6, 1.35, 1.2, 0, 0, TAU); ctx.fillStyle = C.lens; ctx.fill();
      ctx.strokeStyle = C.goldShade; ctx.lineWidth = .4; ctx.stroke();
    }
    line(ctx, [[2.5, -6.8], [3.1, -6.8]], C.goldShade, .4); line(ctx, [[-.1, -6.8], [-3.2, -7.4]], C.goldShade, .4);
  },
  // Staff of the Magi. Frame origin at the grip; -y toward the perch.
  staff(ctx) {
    const {length, grip, perch, bird} = STAFF, top = -(length - grip), butt = grip;
    ctx.beginPath(); ctx.moveTo(-1.1, butt); ctx.lineTo(1.1, butt); ctx.lineTo(1.35, top + 2); ctx.lineTo(-1.35, top + 2); ctx.closePath();
    fillStroke(ctx, cel(ctx, -1.4, 1.4, C.wood, C.woodShade, .55));
    poly(ctx, [[-1.3, butt - 3], [1.3, butt - 3], [1.2, butt], [-1.2, butt]]); fillStroke(ctx, C.gold, C.ink, .4);     // ferrule
    // Metal perch: collar, short post, crossbar.
    poly(ctx, [[-1.7, top + 3.6], [1.7, top + 3.6], [1.5, top + 1.2], [-1.5, top + 1.2]]); fillStroke(ctx, C.perch, C.ink, .45);
    poly(ctx, [[-.55, top + 1.4], [.55, top + 1.4], [.55, top - perch + 1.4], [-.55, top - perch + 1.4]]); fillStroke(ctx, C.perch, C.ink, .4);
    const bar = top - perch + 1;
    ctx.beginPath(); ctx.roundRect(-4.6, bar - .7, 9.2, 1.4, .6); fillStroke(ctx, cel(ctx, -4.6, 4.6, C.perch, C.perchShade, .6), C.ink, .45);
    // The black bird standing on the perch, facing forward (+x).
    ctx.save(); ctx.translate(.4, bar - .7);
    line(ctx, [[-.6, 0], [-.4, -1.6]], C.bird, .45); line(ctx, [[.8, 0], [.6, -1.6]], C.bird, .45);
    ctx.beginPath(); ctx.moveTo(-bird * .52, -3.2);                      // tail
    ctx.lineTo(-bird * .3, -2.4); ctx.bezierCurveTo(-1.6, -1, 1.8, -1, 2.6, -3.2);
    ctx.bezierCurveTo(3.4, -4.6, 3.4, -6, 2.6, -6.6);                   // breast to throat
    ctx.lineTo(4.3, -6.3); ctx.lineTo(2.7, -7.2);                       // beak
    ctx.bezierCurveTo(1.6, -8.4, -.2, -7.8, -.4, -6.2);                 // crown to nape
    ctx.bezierCurveTo(-2.2, -5.4, -bird * .4, -4.4, -bird * .52, -3.2); ctx.closePath();
    fillStroke(ctx, C.bird, C.ink, .45);
    line(ctx, [[-.4, -5], [-2.4, -3.6]], C.birdHi, .45);                 // folded wing edge
    ctx.fillStyle = '#e9e4d6'; ctx.beginPath(); ctx.arc(2, -6.8, .3, 0, TAU); ctx.fill();
    ctx.restore();
  },
  mote(ctx, {bright = 1, t = 0}) {
    const r = 1.15 + Math.sin(t * .006) * .08;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .22 * bright;
    ctx.fillStyle = C.mote; ctx.beginPath(); ctx.arc(0, 0, r * 1.5, 0, TAU); ctx.fill(); ctx.restore();
    star4(ctx, 0, 0, r, C.mote, C.goldShade);
    ctx.fillStyle = C.moteCore; ctx.beginPath(); ctx.arc(0, 0, r * .3, 0, TAU); ctx.fill();
  },
};

// ---------------------------------------------------------------------------
// Frame helpers. Local rig space is pre-mirror and root-relative (scaled).
function frame(ctx, rig, wx, wy, angle, paint, filter = '') {
  ctx.save(); ctx.translate(wx, wy); ctx.scale(rig.facing * rig.scale, rig.scale); ctx.rotate(angle);
  if (filter) ctx.filter = filter;
  paint(ctx); ctx.restore();
}
const worldOf = (rig, lx, ly) => [rig.rootX + lx * rig.facing, rig.rootY + ly];
function frameToLocal(rig, ox, oy, angle, px, py) {
  const s = rig.scale;
  return [ox + (px * Math.cos(angle) - py * Math.sin(angle)) * s, oy + (px * Math.sin(angle) + py * Math.cos(angle)) * s];
}
const dirOf = angle => [-Math.sin(angle), Math.cos(angle)];
const FAR = 'brightness(.82) saturate(.92)';
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

function stateOf(rig) {
  if (!rig.wren) rig.wren = {ch: {...WREN_POSES.rest}, beat: '', beatAt: 0, attackAt: -1, fidget: null, fidgetAt: 0};
  return rig.wren;
}

// Which pose she is reaching for, and how fast (tau ms).
function resolveTarget(st, {pose, beat, now, reduced, alive, idleFidgets, flying}) {
  if (!alive || pose === 'down' || pose === 'ko') return {key: 'down', tau: 170};
  const cue = beat || (['windup', 'strike', 'cast', 'cast_channel', 'cast_release', 'hit', 'crit', 'impact', 'attack', 'dodge', 'miss'].includes(pose) ? pose : '');
  if (cue !== st.beat) { st.beat = cue; st.beatAt = now; }
  // Her attack is Crown of Stars: gather, then release a mote down the staff line.
  if (cue === 'windup' || cue === 'cast' || cue === 'cast_channel') return {key: 'channel', tau: 90};
  if (cue === 'strike' || cue === 'cast_release') return {key: 'release', tau: reduced ? 0 : 40, contact: true};
  if (cue === 'attack') {                       // arcade / preview loop
    const t = (now - (st.attackAt < 0 ? (st.attackAt = now) : st.attackAt)) % 1300;
    return t < 560 ? {key: 'channel', tau: 90} : {key: 'release', tau: 40, contact: t < 700};
  }
  st.attackAt = -1;
  if (['hit', 'impact', 'crit'].includes(cue)) return {key: 'hit', tau: 35};
  if (['miss', 'dodge'].includes(cue)) return {key: 'dodge', tau: 60};
  if (cue.startsWith('gesture:') && WREN_POSES[cue.slice(8)]) return {key: cue.slice(8), tau: 120};
  if (FLIGHT_POSES.has(pose)) return {key: 'fly', tau: 90};
  if (TRAVEL_POSES.has(pose) || beat === 'move') return {key: flying ? 'fly' : 'glide', tau: 90};
  if (pose === 'victory' || pose === 'cheer') return {key: 'victory', tau: 140};
  if (WREN_POSES[pose] && !['rest', 'guard', 'down', 'ko'].includes(pose)) return {key: pose, tau: 120};
  if (pose === 'guard' || pose === 'combat' || pose === 'block') return {key: flying ? 'fly' : 'guard', tau: 140};
  if (flying) return {key: 'fly', tau: 140};
  if (idleFidgets && !reduced) {
    if (!st.fidgetAt) st.fidgetAt = now + 7000 + (now % 5000);
    if (st.fidget && now > st.fidgetAt + 2800) { st.fidget = null; st.fidgetAt = now + 9000 + (now % 7000); }
    else if (!st.fidget && now > st.fidgetAt) { st.fidget = FIDGETS[Math.floor(now / 997) % FIDGETS.length]; st.fidgetAt = now; }
    if (st.fidget) return {key: st.fidget, tau: 220};
  }
  return {key: 'rest', tau: 200};
}

function targetChannels(key, {now, reduced, flying}) {
  const base = {...(WREN_POSES[key] || WREN_POSES.rest)};
  if (flying && key !== 'down') base.wing = 1;
  if (!reduced && key !== 'down') {             // the hover breathes
    base.float += Math.sin(now * .0018) * 1.2;
    base.sp += Math.sin(now * .0021) * .01;
  }
  return base;
}

// ---------------------------------------------------------------------------
// Public: draw Wren on `rig` (a SkeletalRig whose scale is already set).
//   x, y       canvas point of the FLOOR under her; facing 1 = right
//   pose       poseFor() output; beat = the combat director's live beat
//   paint      false: advance and measure only (sockets for the FX engine)
// Returns world sockets {head, chest, main_hand, off_hand, ground, weapon_main,
// weapon_tip, shield, focus}.
export function drawWren(ctx, rig, model = {}, {
  x = 0, y = 0, facing = 1, dt = 16, now = performance.now(), pose = 'idle', beat = '',
  paint = true, reducedMotion = false, shadow = true, idleFidgets = true, weapons = true, casting = null,
} = {}) {
  rig.reshape('wren', SKELETON);
  const st = stateOf(rig);
  const reduced = Boolean(reducedMotion);
  const kit = wrenPresentation(model);
  const want = resolveTarget(st, {pose, beat, now, reduced, alive: model.alive !== false, idleFidgets, flying: kit.wings});
  const target = targetChannels(want.key, {now, reduced, flying: kit.wings});
  if (casting && ['cast', 'cast_channel', 'cast_release'].includes(beat || pose) && casting.stance === 'overhead') Object.assign(target, {nu: -2.6, hy: -30});
  const ch = st.ch;
  const k = reduced || !Number.isFinite(dt) ? 1 : want.tau <= 0 ? 1 : 1 - Math.exp(-Math.max(0, dt) / want.tau);
  for (const key of Object.keys(target)) ch[key] = (ch[key] ?? target[key]) + (target[key] - (ch[key] ?? target[key])) * k;

  // --- pose the skeleton -----------------------------------------------------
  const R = rig.bones, bone = n => R.get(n), set = (n, a) => { const b = bone(n); if (b) b.localAngle = b.restAngle + a; };
  rig.resetPose(); rig.pose = want.key; rig.weapon = 'staff';
  if (want.contact && st.contactAt !== st.beatAt) st.contactAt = st.beatAt;
  bone('pelvis').localY += ch.py; bone('pelvis').localAngle = ch.pa;
  set('spine', ch.sp); set('torso', ch.to); set('head', ch.hd);
  set('left_thigh', ch.lt); set('left_shin', ch.ls); set('right_thigh', ch.rt); set('right_shin', ch.rs);
  set('left_upper_arm', ch.nu); set('left_lower_arm', ch.nl);
  rig.update(0, x, y, facing);
  const s = rig.scale;
  if (ch.air < .5) {
    // She floats: lift the body until the lower slipper hovers `float` units up.
    const sole = n => { const b = bone(n); return b.y + SOLE * s * Math.cos(b.angle * .35); };
    const lowest = Math.max(sole('left_foot'), sole('right_foot'));
    bone('pelvis').localY -= (lowest + ch.float * s) / s;
  } else {
    // Lying: settle the lowest joint onto the floor.
    let lowest = -Infinity;
    for (const b of R.values()) if (b.name !== 'root') lowest = Math.max(lowest, b.y, b.endY ?? b.y);
    bone('pelvis').localY -= (lowest + 3 * s) / s;
  }
  rig.update(0, x, y, facing);
  const pelvis = bone('pelvis');
  // Both hands reach for targets measured from the pelvis, each on its own
  // side of the body, elbows bending outward. Lying down keeps the FK arm.
  rig.reach('right', pelvis.x + ch.hx * s, pelvis.y + ch.hy * s, ch.eb >= 0 ? 1 : -1);
  if (ch.air < .5) rig.reach('left', pelvis.x + ch.fx * s, pelvis.y + ch.fy * s, ch.fb >= 0 ? 1 : -1);
  const handCentre = side => {
    const lower = bone(side + '_lower_arm'), hand = bone(side + '_hand'), [dx, dy] = dirOf(lower.angle);
    return [hand.x + dx * HAND_REACH * s, hand.y + dy * HAND_REACH * s];
  };
  const [gx, gy] = handCentre('right');
  const staffAngle = ch.st;                           // 0 = upright: local -y (the perch) points up
  const staffPoint = along => { const [dx, dy] = dirOf(staffAngle); return worldOf(rig, gx - dx * along * s, gy - dy * along * s); };

  // --- sockets --------------------------------------------------------------
  const torso = bone('torso'), head = bone('head');
  const faceAt = frameToLocal(rig, head.x, head.y, head.angle, 2, -6.5);
  const crownAt = frameToLocal(rig, head.x, head.y, head.angle * .4, .5, -HEAD_TOP - 4.5);
  const [ogx, ogy] = worldOf(rig, gx, gy);
  const off = worldOf(rig, ...handCentre('left'));
  const tipLen = STAFF.length - STAFF.grip + STAFF.perch;
  const sockets = {
    head: {x: worldOf(rig, ...faceAt)[0], y: worldOf(rig, ...faceAt)[1], rotation: head.worldAngle},
    chest: (([cx, cy]) => ({x: cx, y: cy, rotation: torso.worldAngle}))(worldOf(rig, ...frameToLocal(rig, torso.x, torso.y, torso.angle, 0, 8))),
    main_hand: {x: ogx, y: ogy, rotation: ch.st * facing},
    off_hand: {x: off[0], y: off[1], rotation: bone('left_lower_arm').worldAngle},
    ground: {x: rig.rootX, y: rig.rootY, rotation: 0},
    crown: {x: worldOf(rig, ...crownAt)[0], y: worldOf(rig, ...crownAt)[1], rotation: 0},
  };
  sockets.weapon_main = sockets.main_hand;
  sockets.shield = sockets.chest;
  sockets.weapon_tip = (([tx, ty]) => ({x: tx, y: ty, rotation: ch.st * facing}))(staffPoint(tipLen));
  // Her focus is the staff's perch; a one-handed cast comes off the open palm.
  sockets.focus = casting?.hands === 1 ? sockets.off_hand : sockets.weapon_tip;
  if (!paint) return sockets;

  const ops = [];
  const add = (z, fn) => ops.push({z, fn});
  const onBone = (name, painter, opts = {}, filter = '') => {
    const b = bone(name); return () => frame(ctx, rig, b.worldX, b.worldY, b.angle, c => PAINT[painter](c, opts), filter);
  };
  if (shadow) add(0, () => {
    // Hover shadow: smaller and fainter the higher she floats.
    const lift = clamp(ch.float / 16, 0, 1.4);
    ctx.save(); ctx.fillStyle = `rgba(0,0,0,${(.3 - lift * .1).toFixed(3)})`; ctx.beginPath();
    ctx.ellipse(rig.rootX, rig.rootY + s * .6, (15 - lift * 3) * s, 3 * s, 0, 0, TAU); ctx.fill(); ctx.restore();
  });
  // Wings: manifest only for real flight. Scale up from the shoulder blades.
  const open = clamp(ch.wing, 0, 1);
  if (open > .04) {
    const beatAmp = reduced ? 0 : ch.flap * Math.sin(now * .011);
    const root = frameToLocal(rig, torso.x, torso.y, torso.angle, -3, 3);
    const [rx, ry] = worldOf(rig, ...root);
    add(4, () => frame(ctx, rig, rx, ry, torso.angle * .5 - .12, c => PAINT.wing(c, {open, beat: beatAmp * .9 + .12}), FAR));
    add(12, () => frame(ctx, rig, rx, ry, torso.angle * .5, c => PAINT.wing(c, {open, beat: beatAmp})));
  }
  const motion = clamp(ch.sp * 1.4 + (want.key === 'fly' || want.key === 'glide' ? .4 : 0), -.3, 1);
  add(8, () => frame(ctx, rig, torso.worldX, torso.worldY, torso.angle * .6 + motion * .35, c => PAINT.cloak(c, {trail: motion, t: now})));
  add(9, () => frame(ctx, rig, head.worldX, head.worldY, head.angle * .3, c => PAINT.hairBack(c, {sway: motion, t: reduced ? 0 : now})));

  // Far (open) arm.
  const leftHand = bone('left_hand'), leftLower = bone('left_lower_arm');
  const openPalm = ['guard', 'channel', 'release', 'point', 'victory'].includes(want.key);
  add(30, onBone('left_upper_arm', 'sleeveUpper', {}, FAR));
  add(31, onBone('left_lower_arm', 'sleeveLower', {}, FAR));
  add(34, () => frame(ctx, rig, leftHand.worldX, leftHand.worldY, leftLower.angle, c => PAINT.hand(c, {open: openPalm}), FAR));

  // Slippers below the hem, then the robe over the legs.
  for (const [side, z, filter] of [['left', 47, FAR], ['right', 48, '']]) {
    const foot = bone(side + '_foot'), shin = bone(side + '_shin');
    add(z, () => frame(ctx, rig, foot.worldX, foot.worldY, shin.angle * .5, c => PAINT.slipper(c, {point: ch.air > .5 ? .1 : .85}), filter));
  }
  const legSwing = (bone('left_thigh').angle + bone('right_thigh').angle) * .5 - pelvis.angle;
  add(55, () => frame(ctx, rig, pelvis.worldX, pelvis.worldY, pelvis.angle, c => PAINT.skirt(c, {swing: legSwing * .55, stars: kit.stars, t: reduced ? 0 : now})));
  add(60, onBone('torso', 'bodice', {stars: kit.stars}));
  add(63, onBone('torso', 'sigil'));
  add(70, onBone('head', 'face'));
  add(72, onBone('head', 'hairFront'));
  add(74, onBone('head', 'glasses'));
  add(82, onBone('torso', 'hairLock', {sway: motion}));

  // Crown of stars: seven motes on a tilted ring above her head. Motes on the
  // far side of the ring paint behind the head, near-side motes in front.
  const [cx, cy] = worldOf(rig, ...crownAt);
  const glow = 1 + clamp((ch.float - WREN_FLOAT) / 8, 0, .6) + (want.key === 'channel' ? .5 : 0);
  const spin = reduced ? 0 : now * .0007;
  for (let i = 0; i < CROWN_MOTES; i++) {
    if (i >= kit.motes) continue;                     // spent motes are gone until the daily refresh
    const a = spin + i * TAU / CROWN_MOTES, mx = Math.cos(a) * 8.6 * s * facing, my = Math.sin(a) * 2.4 * s;
    add(Math.sin(a) < 0 ? 65 : 118, () => frame(ctx, rig, cx + mx, cy + my, 0, c => PAINT.mote(c, {bright: glow, t: now + i * 400})));
  }

  // Near arm, staff, then the gripping hand over the shaft.
  add(90, onBone('right_upper_arm', 'sleeveUpper'));
  add(91, onBone('right_lower_arm', 'sleeveLower'));
  if (weapons) {
    if (ch.air > .5) {
      // Fallen: the staff lies on the floor beside her.
      const [lx, ly] = worldOf(rig, pelvis.x + 6 * s, -1.5 * s);
      add(46, () => frame(ctx, rig, lx, ly, Math.PI / 2, c => PAINT.staff(c)));
    } else add(100, () => frame(ctx, rig, ogx, ogy, staffAngle, c => PAINT.staff(c)));
  }
  const rightHand = bone('right_hand'), rightLower = bone('right_lower_arm');
  add(104, () => frame(ctx, rig, rightHand.worldX, rightHand.worldY, rightLower.angle, c => PAINT.hand(c, {open: ch.air > .5})));

  ops.sort((a, b) => a.z - b.z);
  for (const op of ops) op.fn();
  return sockets;
}

// Presentation facts from public actor data. Robe stars and crown motes read
// the host's own resource counts when present; wings follow the host's flight
// state (fly_speed set by the `wings` action, or an explicit flag).
export function wrenPresentation(item = {}) {
  if (item.kit) return item.kit;                   // already resolved by dollModel()
  const res = item.resources || {};
  const count = (v, full) => { const n = Number(v); return Number.isFinite(n) ? clamp(Math.round(n), 0, full) : full; };
  return {
    motes: count(res.crown_motes, CROWN_MOTES),
    stars: count(res.robe_stars, ROBE_STARS),
    wings: Boolean(item.wings ?? item.flying ?? res.wings ?? (Number(item.fly_speed) > 0)),
  };
}
export function wrenLoadout() { return 'staff'; }

// Voice-card medallion drawn by the same rig, so the portrait never drifts.
let portrait = '';
export function wrenPortrait(size = 128) {
  if (portrait || typeof document === 'undefined') return portrait;
  try {
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d'), scale = size / 44;
    const bg = ctx.createRadialGradient(size * .42, size * .3, size * .05, size * .5, size * .5, size * .75);
    bg.addColorStop(0, '#6a5f86'); bg.addColorStop(1, '#171a2c');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, size, size);
    drawWren(ctx, new SkeletalRig({scale}), {alive: true}, {x: size * .5, y: size * .5 + 99 * scale, pose: 'rest',
      now: 0, dt: 0, reducedMotion: true, shadow: false, weapons: false, idleFidgets: false});
    portrait = canvas.toDataURL('image/png');
  } catch { portrait = ''; }
  return portrait;
}

export const WREN_RIG = Object.freeze({
  identity: 'wren', kind: 'vector-rig', heightUnits: WREN_HEIGHT_UNITS + WREN_FLOAT,
  layers: WREN_PAPERDOLL_LAYERS, poses: Object.keys(WREN_POSES), loadouts: WREN_LOADOUTS,
  draw: drawWren, loadout: wrenLoadout, presentation: wrenPresentation, portrait: wrenPortrait,
});
