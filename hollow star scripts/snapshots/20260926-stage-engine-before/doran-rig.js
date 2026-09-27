// Doran's paperdoll: layered vector parts bound to the shared SkeletalRig.
//
// Every part is drawn in its bone's local frame (+y runs down the bone), so
// the rig's forward kinematics, IK and pose blending move him exactly as they
// move every other figure. Style follows Corey's 2026-09-23 guide: clean cel
// plate, navy cloth, brown leather, charcoal gauntlets. Design locks from the
// Doran paperdoll spec: 7'0" in the enclosed helm with a lit visor slit, kite
// shield fused to the shield-arm vambrace, and the Giant Cleaver as a 6 ft x
// 3 ft white razor slab on a 3 ft handle.
//
// Presentation only: this draws outcomes the host has already resolved and
// never reads or decides mechanics.

import {SkeletalRig} from './skeletal-rig.js';
import {celRamp, farPalette} from './actor-core.js';
import {isCastingImplement} from './magic-articulation.js';

const TAU = Math.PI * 2;
// Rig units per foot at the shared 5'8" puppet baseline (97 units tall).
export const RIG_UNITS_PER_FOOT = 97 / (68 / 12);
const FT = RIG_UNITS_PER_FOOT;
export const DORAN_HEIGHT_UNITS = 7 * FT;

// Measured to the 7'0" silhouette: long legs, broad shoulders, big helm.
const SKELETON = Object.freeze({
  pelvis: {x: 0, y: -66}, spine: {y: -10}, torso: {y: -18}, neck: {y: -7.5}, head: {x: 0, y: -.5},
  left_shoulder: {x: -15.5, y: 1}, right_shoulder: {x: 15.5, y: 1},
  left_upper_arm: {length: 19.5, angle: .1}, right_upper_arm: {length: 19.5, angle: -.06},
  left_lower_arm: {length: 17.5, angle: -.05}, right_lower_arm: {length: 17.5, angle: -.1},
  left_hip: {x: -11, y: 0}, right_hip: {x: 11, y: 0},
  left_thigh: {length: 28.5, angle: .03}, right_thigh: {length: 28.5, angle: -.03},
  left_shin: {length: 27.5, angle: 0}, right_shin: {length: 27.5, angle: 0},
});
const SOLE = 10;          // ankle to sole
const FIST_REACH = 2.8;   // wrist to the centre of a gripping gauntlet

// The Giant Cleaver along its own axis, pommel end = 0 (units).
export const CLEAVER = Object.freeze({
  handle: 3 * FT, guard: 5, blade: 6 * FT, width: 1 * FT,
  spine: 4.2,             // handle axis to the flat spine
  chisel: .55,            // tip drop on the edge side, share of blade width
  grips: {reach: 6, choke: 3 * FT - 5}, support: 38,
});
const DAGGER = Object.freeze({blade: 1.45 * FT, hilt: 7.5});
const STAFF = Object.freeze({length: 6 * FT, grip: 3.3 * FT, support: 32});
const WAND = Object.freeze({length: 1.5 * FT, grip: 4});

// Layer catalog (spec section 3). z is the paint order; `bone` binds a part to
// the skeleton. Weapons and hands move between z bands with the pose: a
// forward cleaver paints over the body, a raised one hangs behind it.
export const DORAN_PAPERDOLL_LAYERS = Object.freeze({
  'ground:shadow': {slot: 'ground', className: 'char-shadow doran-shadow', z: 0},
  'cape:back': {slot: 'clothing', className: 'char-cape doran-cape-back', bone: 'torso', z: 10},
  'weapon:stowed': {slot: 'equipment', className: 'char-back-cleaver', bone: 'torso', z: 20},
  'arm:left': {slot: 'body', className: 'char-arm doran-shield-arm', bone: 'left_upper_arm', z: 30},
  'shield:kite': {slot: 'equipment', className: 'char-bracer-kite doran-gauntlet-shield', bone: 'left_lower_arm', z: 35},
  'hand:left': {slot: 'body', className: 'char-hand doran-hand-free', bone: 'left_hand', z: 40},
  'body:legs': {slot: 'clothing', className: 'char-legs doran-greaves', bone: 'pelvis', z: 50},
  'equipment:tabard': {slot: 'clothing', className: 'char-tabard doran-tabard', bone: 'pelvis', z: 55},
  'body:torso': {slot: 'body', className: 'char-torso doran-cuirass', bone: 'torso', z: 60},
  'equipment:belt': {slot: 'equipment', className: 'char-belt doran-belt', bone: 'pelvis', z: 62},
  'body:head': {slot: 'body', className: 'char-head doran-helm-enclosed', bone: 'head', z: 70},
  'fx:visor-glow': {slot: 'effect', className: 'char-eyes doran-visor-glow', bone: 'head', z: 71},
  'equipment:cape-front': {slot: 'clothing', className: 'char-cape doran-cowl', bone: 'torso', z: 80},
  'arm:right': {slot: 'body', className: 'char-arm doran-weapon-arm', bone: 'right_upper_arm', z: 90},
  'hand:right': {slot: 'body', className: 'char-hand doran-weapon-hand', bone: 'right_hand', z: 94},
  'weapon:cleaver': {slot: 'weapon', className: 'char-weapon doran-giant-cleaver', bone: 'right_hand', z: 110},
  'weapon:daggers': {slot: 'weapon', className: 'char-weapon doran-obsidian-daggers', bone: 'right_hand', z: 112},
  'weapon:staff': {slot: 'weapon', className: 'char-weapon doran-staff', bone: 'right_hand', z: 110},
  'weapon:wand': {slot: 'weapon', className: 'char-weapon doran-wand', bone: 'right_hand', z: 110},
  'fx:slash-arc': {slot: 'effect', className: 'char-fx doran-silver-arc', z: 120},
});
export const DORAN_LOADOUTS = Object.freeze(['cleaver', 'daggers', 'staff', 'wand']);

// ---------------------------------------------------------------------------
// Palette (style guide).
const NEAR_PALETTE = Object.freeze({
  ink: '#10131b', inkSoft: 'rgba(16,19,27,.55)',
  plateHi: '#ffffff', plate: '#eceae6', plateMid: '#d2d0cf', plateShade: '#a9a8ad', plateDeep: '#7f7f88',
  navyDeep: '#10141f', navy: '#1b2233', navyMid: '#252e45', navyHi: '#38445f', trim: '#56638a',
  sleeve: '#4b4039', sleeveDeep: '#2f2823', sleeveHi: '#66574c',
  leather: '#4a3529', leatherHi: '#6f513d', leatherDeep: '#2c1f18', brass: '#cdb071', brassDeep: '#8a6f3a',
  glove: '#25262c', gloveHi: '#474851', emblem: '#151a26',
  steel: '#a5afba', steelHi: '#d7dde3', steelDeep: '#6b7581', rim: '#d8c89e', rimDeep: '#9e8c62',
  blade: '#f3f5f7', bladeSpine: '#d4d9df', bladeBevel: '#c3cad4', bladeEdge: '#ffffff', bladeCold: '#aab5c3',
  obsidian: '#0c0b12', obsidianHi: '#8f80d6',
});
const FAR_PALETTE = farPalette(NEAR_PALETTE, 0.2);
// The palette parts paint from; frame() swaps in FAR_PALETTE for far parts.
let C = NEAR_PALETTE;

// ---------------------------------------------------------------------------
// Poses. Channels are plain numbers so any two poses blend:
//   py pa  pelvis drop (units) / pelvis roll    sp to hd  spine / torso / head lean (+ = forward)
//   lt ls rt rs  thigh and shin offsets (far = l, near = r; + swings back)
//   nu nl  shield-arm upper / forearm          hx hy  weapon-hand target (units, root-relative)
//   bl  blade angle (0 = point down, - = forward)   gr  grip 0 pommel .. 1 choked at the guard
//   sup  second hand on the handle             wf hf af  blade / handle / whole weapon arm in front of the body
//   sh  shield tilt   vis  visor light   cape  mantle trail
//   stow  cleaver latched on the back
//   air  skip ground contact   plant  both soles on the floor (stances; off for strides)
//   eb  weapon-elbow fold: - = outward on his own side (stances), + = tucked under (shoulder carry)
const BASE = {py: 0, pa: 0, sp: 0, to: 0, hd: 0, lt: 0, ls: 0, rt: 0, rs: 0, nu: -.05, nl: -.12,
  hx: 22, hy: -58, lx: -16, ly: -71, lc: 0, bl: .1, gr: 1, sup: 0, wf: 0, hf: 0, af: 0,
  sh: 0, vis: .45, cape: 0, stow: 0, air: 0, plant: 1, eb: -1};
const P = over => Object.freeze({...BASE, ...over});
// The fallen pose, shared by `down` and `ko`.
const DOWN = P({pa: -1.45, py: 42, lt: -.1, ls: .3, rt: .1, rs: .5, hd: .3, nu: .6, nl: .4,
  hx: -73.7, hy: -8, bl: 1.57, gr: 0, vis: .08, air: 1});
export const DORAN_POSES = Object.freeze({
  // At rest: the Cleaver held low in hands, blade resting down.
  rest: P({hx: 22, hy: -58, bl: -.15, gr: 0, sup: 0, stow: 1}),
  // Vanguard: two-handed grounded low-ready stance, cleaver pointed down-forward.
  guard: P({sp: .08, to: .03, hd: -.05, lt: .3, ls: .12, rt: -.34, rs: .4, nu: -.95, nl: -1.05,
    hx: 3.4, hy: -77.8, bl: -.25, gr: .3, sup: 1, vis: .55, cape: .04}),
  windup: P({sp: -.14, to: -.05, hd: .05, lt: .38, ls: .16, rt: -.42, rs: .52, nu: -.6, nl: -1.5,
    hx: 23.0, hy: -128.0, bl: 2.25, gr: 1, sup: 1, hf: 1, vis: .8, cape: .06}),
  strike: P({sp: .3, to: .12, hd: .06, lt: .5, ls: .38, rt: -.66, rs: .58, nu: -.4, nl: -1.2,
    hx: 14.3, hy: -69.6, bl: -1.25, gr: 1, sup: 1, wf: 1, hf: 1, vis: 1.15, cape: .16}),
  follow: P({sp: .36, to: .14, hd: .1, lt: .54, ls: .42, rt: -.72, rs: .62, nu: -.35, nl: -1.1,
    hx: 12.3, hy: -47, bl: -1.12, gr: 1, sup: 1, wf: 1, hf: 1, vis: .7, cape: .12}),
  sweepWind: P({sp: -.06, to: -.1, lt: .35, ls: .15, rt: -.35, rs: .45, nu: -.5, nl: -1.4,
    hx: 0.3, hy: -82.0, bl: 1.72, gr: .3, hf: 1, vis: .7, cape: .05}),
  sweep: P({sp: .2, to: .18, lt: .45, ls: .3, rt: -.6, rs: .5, nu: -.3, nl: -1.3,
    hx: 16.4, hy: -79.8, bl: -1.6, gr: .3, wf: 1, hf: 1, vis: .9, cape: .14}),
  sweepFollow: P({sp: .24, to: .22, lt: .48, ls: .32, rt: -.62, rs: .52, nu: -.28, nl: -1.2,
    hx: 18, hy: -70, bl: -1.95, gr: .3, wf: 1, hf: 1, vis: .6, cape: .1}),
  hit: P({sp: -.2, to: -.08, hd: -.28, lt: .12, ls: .1, rt: -.1, rs: .15, nu: -1.15, nl: -.85,
    hx: 0.3, hy: -73.7, bl: 2.5, gr: 0, vis: .3, cape: -.04}),
  brace: P({sp: .16, to: .05, hd: -.02, lt: .45, ls: .3, rt: -.55, rs: .72, nu: -1.1, nl: -.8,
    hx: 2.3, hy: -67.6, bl: -.15, gr: .4, sup: 1, vis: 1, sh: -.08}),
  low: P({sp: .38, to: .1, hd: -.12, lt: .75, ls: .95, rt: -.85, rs: 1.25, nu: -.75, nl: -.7,
    hx: 6.4, hy: -49.0, bl: 1.9, gr: 0, vis: .6, cape: .05}),
  command: P({sp: -.06, to: -.04, hd: -.12, lt: .1, ls: .05, rt: -.12, rs: .1, nu: 2.3, nl: .35, vis: 1.1}),
  staffLow: P({sp: .08, nu: -.55, nl: -.6, hx: 26, hy: -61, bl: 3.08, af: 1, hf: 1, vis: .6}),
  staffPoint: P({sp: .14, nu: -.8, nl: -.7, hx: 24, hy: -82, bl: -1.3, af: 1, hf: 1, wf: 1, vis: .95}),
  bash: P({sp: .26, to: .16, hd: .02, lt: .5, ls: .35, rt: -.7, rs: .55, nu: -1.45, nl: -.15,
    hx: 3.0, hy: -72.0, bl: 2.3, gr: 0, sh: -.22, vis: .9, cape: .12}),
  jump: P({lt: -.85, ls: 1.15, rt: -.2, rs: .95, sp: .12, nu: -1.2, nl: -.6, hx: 16.7, hy: -123.0,
    bl: 2.6, gr: 0, vis: .5, cape: -.12, air: 1}),
  land: P({sp: .3, hd: .1, lt: .7, ls: 1.1, rt: -.8, rs: 1.2, nu: -.6, nl: -.8, hx: 7.0, hy: -52.0,
    bl: 1.8, gr: 0, vis: .6, cape: .1}),
  climb: P({nu: -2.6, nl: .4, lt: -.3, ls: .8, rt: -.3, rs: .8, hx: 11.0, hy: -132.0, stow: 1, vis: .5, plant: 0}),
  down: DOWN,
  // Downtime vocabulary from the style guide; the Cleaver stays on his back.
  look: P({hd: -.1, to: -.03, nu: -.1, nl: -.2, hx: 4, hy: -112, af: 1, stow: 1, vis: .6}),
  point: P({to: .05, lt: .1, rt: -.15, rs: .1, nu: -.1, nl: -.15, hx: 40, hy: -96, af: 1, stow: 1, vis: .7}),
  cheer: P({sp: -.08, hd: -.12, nu: -.05, nl: -.1, hx: 13.0, hy: -140.0, stow: 1, vis: .9}),
  crossed: P({hd: .05, nu: -.55, nl: -1.9, hx: 6, hy: -80, af: 1, stow: 1, vis: .4}),
  scratch: P({hd: .12, to: -.03, nu: -.05, nl: -.12, hx: -4, hy: -117, af: 1, stow: 1, vis: .4}),
  tired: P({sp: .5, to: .12, hd: .3, lt: .3, ls: .45, rt: -.3, rs: .55, nu: -.35, nl: -.3,
    hx: 2, hy: -48, af: 1, stow: 1, vis: .2}),
  kneel: P({py: 28.5, sp: .08, hd: .12, lt: -.03, ls: 1.57, rt: -1.52, rs: 1.52, nu: -.6, nl: -.9,
    hx: 8, hy: -52, af: 1, stow: 1, vis: .5, air: 1}),
  // Side-view battle line. battleIdle / ready hold two-handed low ready stance;
  // ready leans in as the acting combatant. defend is the heavy two-handed brace; victory lifts
  // the slab overhead; ko is the fallen pose.
  battleIdle: P({sp: .1, to: .03, hd: -.04, lt: .32, ls: .14, rt: -.36, rs: .42, nu: -1.0, nl: -1.0,
    hx: 4.5, hy: -79.0, bl: -.28, gr: .3, sup: 1, vis: .6, cape: .05}),
  ready: P({sp: .16, to: .06, hd: -.06, lt: .4, ls: .2, rt: -.44, rs: .5, nu: -1.05, nl: -1.0,
    hx: 9.0, hy: -84.0, bl: -.35, gr: .35, sup: 1, hf: 1, vis: .9, cape: .08}),
  defend: P({sp: .2, to: .06, hd: -.02, lt: .5, ls: .36, rt: -.6, rs: .78, nu: -1.15, nl: -.75,
    hx: 2.3, hy: -66.0, bl: -.15, gr: .4, sup: 1, vis: 1, sh: -.12}),
  victory: P({sp: -.1, to: -.05, hd: -.16, lt: .12, ls: .06, rt: -.14, rs: .1, nu: -.3, nl: -.5,
    hx: 25.0, hy: -150.0, bl: 3.0, gr: .6, vis: 1.2, cape: -.06}),
  ko: DOWN,
});
// Weapon-hand targets while the obsidian daggers are out (the cleaver rides on
// his back): quick, low and close behind the forward kite.
const DAGGER_HAND = Object.freeze({
  rest: [-19.5, -61.4, .5], guard: [-4, -75.8, -1.3], windup: [-18.4, -98.3, 2.4], strike: [24.6, -79.8, -1.57],
  follow: [20.5, -69.6, -1.4], sweepWind: [-22, -86, 1.9], sweep: [24, -80, -1.7], sweepFollow: [20, -72, -1.9],
  hit: [-20.5, -73.7, 2], brace: [-12, -70, -1.2], low: [-8, -55, -1], bash: [-12, -70, -1.2],
  jump: [-14, -110, 2.2], land: [-10, -55, -.8], kneel: [-20, -42, .6], command: [-19.5, -61.4, .5],
});
// Which maneuvers colour which beats (MANEUVER_POSE in sprite-renderer.js).
const SWEEP_MANEUVERS = new Set(['Trip Attack']);
const MANEUVER_STANCE = Object.freeze({'Rally': 'low', 'Commanding Presence': 'command', 'Menacing Attack': 'guard', 'Trip Attack': 'guard'});
const FIDGETS = ['look', 'scratch', 'crossed', 'look', 'point'];
// Shoulder carry for walking (hand target, blade angle up and back).
const SHOULDER_CARRY = Object.freeze({hx: 24, hy: -82, bl: 2.2});

// ---------------------------------------------------------------------------
// Small drawing helpers (all in part-local units).
function poly(ctx, pts) { ctx.beginPath(); pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath(); }
function fillStroke(ctx, fill, stroke = C.ink, width = .55) {
  ctx.fillStyle = fill; ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.lineJoin = 'round'; ctx.stroke(); }
}
// Shading ramps are posterized into hard cel bands (the shared CLEAN CEL rule
// in puppet-renderer.js): each colour holds flat until the midpoint to the next.
// Cached per context (actor-core.js celRamp posterizes exactly as celStops does).
function hGrad(ctx, x0, x1, stops) { return celRamp(ctx, x0, 0, x1, 0, stops); }
function vGrad(ctx, y0, y1, stops) { return celRamp(ctx, 0, y0, 0, y1, stops); }
const plateGrad = (ctx, x0, x1) => hGrad(ctx, x0, x1, [[0, C.plateHi], [.35, C.plate], [.72, C.plateMid], [1, C.plateShade]]);
function line(ctx, pts, colour, width = .5) {
  ctx.beginPath(); pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
  ctx.strokeStyle = colour; ctx.lineWidth = width; ctx.lineCap = 'round'; ctx.stroke();
}
function capsule(ctx, w0, w1, y0, y1) {
  ctx.beginPath(); ctx.moveTo(-w0 / 2, y0); ctx.quadraticCurveTo(0, y0 - w0 * .45, w0 / 2, y0);
  ctx.lineTo(w1 / 2, y1); ctx.quadraticCurveTo(0, y1 + w1 * .45, -w1 / 2, y1); ctx.closePath();
}

// The heraldic raptor: wings raised, head turned, fanned tail.
function raptor(ctx, s, colour = C.emblem) {
  ctx.save(); ctx.scale(s, s); ctx.fillStyle = colour; ctx.beginPath();
  ctx.moveTo(0, -3.6);
  ctx.bezierCurveTo(.9, -3.6, 1.4, -2.8, 1.2, -2.1);          // head, beak to the right
  ctx.lineTo(2.1, -2.2); ctx.lineTo(1.3, -1.6);
  ctx.lineTo(1.6, -.9);
  ctx.lineTo(3.8, -3.2); ctx.lineTo(6.4, -4.4); ctx.lineTo(6.9, -3.2); // right wing leading edge
  ctx.lineTo(6.1, -2.4); ctx.lineTo(6.6, -1.6); ctx.lineTo(5.6, -1.2); ctx.lineTo(5.9, -.3);
  ctx.lineTo(4.6, -.2); ctx.lineTo(4.6, .6); ctx.lineTo(3.2, .4); ctx.lineTo(1.7, 1.6); // feathered trailing edge
  ctx.lineTo(1.4, 3.1); ctx.lineTo(2.6, 4.6); ctx.lineTo(1, 4.2); ctx.lineTo(0, 5.3); // tail fan
  ctx.lineTo(-1, 4.2); ctx.lineTo(-2.6, 4.6); ctx.lineTo(-1.4, 3.1);
  ctx.lineTo(-1.7, 1.6); ctx.lineTo(-3.2, .4); ctx.lineTo(-4.6, .6); ctx.lineTo(-4.6, -.2); ctx.lineTo(-5.9, -.3);
  ctx.lineTo(-5.6, -1.2); ctx.lineTo(-6.6, -1.6); ctx.lineTo(-6.1, -2.4); ctx.lineTo(-6.9, -3.2); ctx.lineTo(-6.4, -4.4);
  ctx.lineTo(-3.8, -3.2); ctx.lineTo(-1.6, -.9); ctx.lineTo(-1.1, -2.4);
  ctx.bezierCurveTo(-1, -3.3, -.5, -3.6, 0, -3.6);
  ctx.closePath(); ctx.fill(); ctx.restore();
}

// ---------------------------------------------------------------------------
// Part painters. Origins: the bone the part is bound to.
const PAINT = {
  cape(ctx, {length = 84, trail = 0, t = 0}) {
    const flare = Math.max(0, trail) * 20, wave = Math.sin(t * .0021) * .9;
    ctx.beginPath();
    ctx.moveTo(-14, -3); ctx.lineTo(14, -3);
    ctx.bezierCurveTo(18, 18, 19 - flare * .2, length * .6, 16 - flare * .35, length);
    for (let i = 1; i <= 6; i++) {
      const x = 16 - flare * .35 - i * (38 + flare) / 6;
      ctx.lineTo(x + 2.4, length + (i % 2 ? 2.2 + wave : -.4));
      ctx.lineTo(x, length + (i % 2 ? .4 : 1.8 - wave));
    }
    ctx.bezierCurveTo(-21 - flare, length * .6, -19 - flare * .4, 18, -14, -3);
    ctx.closePath();
    fillStroke(ctx, hGrad(ctx, -22 - flare, 18, [[0, C.navyHi], [.22, C.navyMid], [.7, C.navy], [1, C.navyDeep]]));
    ctx.save(); ctx.clip();
    ctx.globalAlpha = .45;
    for (const [x, bend] of [[-11, 3], [-4, -2], [5, 2.5], [11, -1.5]]) line(ctx, [[x * .8, 6], [x + bend - flare * .25, length * .55], [x - flare * .4, length]], C.navyDeep, 1.4);
    ctx.globalAlpha = .35; line(ctx, [[-15, 2], [-19 - flare * .6, length * .7]], C.trim, 1.2);
    ctx.restore();
  },
  torso(ctx) {
    // Navy under-layer shows at the arms and waist.
    poly(ctx, [[-15.5, -2.5], [15.5, -2.5], [14, 12], [12.4, 26], [-12.4, 26], [-14, 12]]);
    fillStroke(ctx, hGrad(ctx, -14, 14, [[0, C.navyMid], [1, C.navyDeep]]));
    ctx.beginPath();
    ctx.moveTo(-13.4, -2.2); ctx.quadraticCurveTo(-6.5, -4.8, 0, -4.4); ctx.quadraticCurveTo(6.5, -4.8, 13.4, -2.2);
    ctx.quadraticCurveTo(14.8, 6, 12, 12.5); ctx.quadraticCurveTo(11, 17.5, 10.1, 22);
    ctx.quadraticCurveTo(0, 23.8, -10.1, 22); ctx.quadraticCurveTo(-11, 17.5, -12, 12.5);
    ctx.quadraticCurveTo(-14.8, 6, -13.4, -2.2); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -13, 14));
    ctx.save(); ctx.clip();
    ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.beginPath(); ctx.ellipse(-5.5, 3, 4, 7, -.2, 0, TAU); ctx.fill();
    ctx.fillStyle = 'rgba(80,80,96,.16)'; ctx.fillRect(4, -5, 10, 30);
    line(ctx, [[-9.6, 17.4], [0, 18.6], [9.6, 17.4]], C.inkSoft, .45);
    ctx.restore();
    ctx.save(); ctx.translate(0, 10.4); raptor(ctx, 1.12); ctx.restore();
  },
  pelvisSkirt(ctx, {swing = 0}) {
    ctx.save(); ctx.rotate(swing);
    ctx.beginPath(); ctx.moveTo(-6.3, -1); ctx.lineTo(6.3, -1);
    ctx.lineTo(7.6, 21.6); ctx.quadraticCurveTo(0, 23.2, -7.6, 21.6); ctx.closePath();
    fillStroke(ctx, hGrad(ctx, -7, 7, [[0, C.navyHi], [.4, C.navyMid], [1, C.navyDeep]]));
    line(ctx, [[-5, 0], [-6, 20.2], [0, 21.4], [6, 20.2], [5, 0]], C.trim, .5);
    ctx.globalAlpha = .4; line(ctx, [[-1.5, 1], [-2, 19]], C.navyHi, 1.4); ctx.globalAlpha = 1;
    ctx.restore();
  },
  pelvisBelt(ctx) {
    for (const s of [-1, 1]) {           // tassets over the hips
      poly(ctx, [[s * 11.8, -1.2], [s * 6.4, -1.2], [s * 6.8, 5.8], [s * 9.4, 8.2], [s * 12.6, 6]]);
      fillStroke(ctx, plateGrad(ctx, s < 0 ? -12.6 : 6.4, s < 0 ? -6.4 : 12.6));
      line(ctx, [[s * 6.7, 3], [s * 12.3, 3.3]], C.inkSoft, .4);
    }
    ctx.beginPath(); ctx.moveTo(-11.8, -5); ctx.quadraticCurveTo(0, -5.8, 11.8, -5);
    ctx.lineTo(11.6, -.9); ctx.quadraticCurveTo(0, -.1, -11.6, -.9); ctx.closePath();
    fillStroke(ctx, vGrad(ctx, -5.6, -.4, [[0, C.leatherHi], [.5, C.leather], [1, C.leatherDeep]]));
    poly(ctx, [[-2, -5.4], [2, -5.4], [2.1, -.3], [-2.1, -.3]]);
    fillStroke(ctx, vGrad(ctx, -5.4, -.3, [[0, '#ecd79d'], [1, C.brassDeep]]), C.ink, .45);
    poly(ctx, [[-.9, -4.2], [.9, -4.2], [.9, -1.5], [-.9, -1.5]]); fillStroke(ctx, C.leatherDeep, null);
  },
  helm(ctx) {
    ctx.beginPath();
    ctx.moveTo(-6.2, -2.2);
    ctx.bezierCurveTo(-7, -8, -6.6, -13.6, -4.3, -16.6);
    ctx.quadraticCurveTo(-1.8, -19.6, .7, -19.8);
    ctx.quadraticCurveTo(3.4, -19.5, 5.7, -16.5);
    ctx.bezierCurveTo(7.8, -13.4, 8, -8, 7.3, -2.4);
    ctx.lineTo(4.9, 1.6); ctx.quadraticCurveTo(.7, 3.4, -3.6, 1.6); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -6.5, 8));
    ctx.save(); ctx.clip();
    ctx.fillStyle = 'rgba(255,255,255,.75)'; ctx.beginPath(); ctx.ellipse(-3.3, -12.5, 1.7, 4.6, .25, 0, TAU); ctx.fill();
    ctx.fillStyle = 'rgba(90,90,110,.18)'; ctx.fillRect(3.4, -21, 6, 25);
    line(ctx, [[.7, -19.6], [.8, -12]], 'rgba(255,255,255,.9)', .7);
    line(ctx, [[-6.6, -.6], [.7, 1.2], [7.4, -.8]], C.inkSoft, .5);
    ctx.restore();
    // Visor slit and breath slot. The glow is painted separately (fx layer).
    poly(ctx, [[-5, -11.4], [6.2, -11.4], [6, -9.7], [-4.8, -9.7]]); fillStroke(ctx, '#0a0c12', null);
    poly(ctx, [[.3, -9.8], [1.1, -9.8], [1, -3.8], [.4, -3.8]]); fillStroke(ctx, '#161922', null);
    for (const x of [-3.4, 4.6]) { ctx.fillStyle = '#595f6d'; ctx.beginPath(); ctx.arc(x, -5.4, .45, 0, TAU); ctx.fill(); }
  },
  visor(ctx, {glow = .5, t = 0}) {
    const flicker = 1 + Math.sin(t * .013) * .04 + Math.sin(t * .031) * .03;
    const g = Math.max(0, glow) * flicker;
    poly(ctx, [[-4.6, -11], [5.8, -11], [5.6, -10.1], [-4.4, -10.1]]);
    ctx.fillStyle = `rgba(255,${Math.round(200 + 40 * Math.min(1, g))},${Math.round(110 + 80 * Math.min(1, g))},${Math.min(1, .45 + g * .55)})`; ctx.fill();
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    ctx.translate(.6, -10.55); ctx.scale(1, .34);
    const r = 6 + g * 7;
    const halo = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
    halo.addColorStop(0, `rgba(255,246,214,${.75 * Math.min(1.2, g)})`);
    halo.addColorStop(.35, `rgba(255,205,110,${.42 * Math.min(1.2, g)})`);
    halo.addColorStop(1, 'rgba(255,180,70,0)');
    ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fill();
    if (g > .85) {                        // lens trail on a flare
      const len = 12 + (g - .85) * 60, a = Math.min(.8, (g - .85) * 1.6);
      const streak = ctx.createLinearGradient(-len, 0, len, 0);
      streak.addColorStop(0, 'rgba(255,210,120,0)'); streak.addColorStop(.5, `rgba(255,244,210,${a})`); streak.addColorStop(1, 'rgba(255,210,120,0)');
      ctx.fillStyle = streak; ctx.fillRect(-len, -1.2, len * 2, 2.4);
    }
    ctx.restore();
  },
  cowl(ctx) {
    ctx.beginPath();
    ctx.moveTo(-8.6, -6.4); ctx.quadraticCurveTo(0, -10.2, 8.6, -6.4);
    ctx.quadraticCurveTo(13.8, -4.6, 16, -1.2); ctx.quadraticCurveTo(12.4, 1.4, 7.4, 1.4);
    ctx.quadraticCurveTo(3.2, 3.4, 0, 5.4); ctx.quadraticCurveTo(-3.2, 3.4, -7.4, 1.4);
    ctx.quadraticCurveTo(-12.4, 1.4, -16, -1.2); ctx.quadraticCurveTo(-13.8, -4.6, -8.6, -6.4); ctx.closePath();
    fillStroke(ctx, vGrad(ctx, -10, 8, [[0, C.navyHi], [.45, C.navyMid], [1, C.navyDeep]]));
    ctx.globalAlpha = .6;
    line(ctx, [[-12, -2.6], [-6, .6], [0, 3.6], [6, .6], [12, -2.6]], C.navyHi, .8);
    line(ctx, [[-6.4, 1.6], [0, 4.4], [6.4, 1.6]], C.navyDeep, .7);
    ctx.globalAlpha = 1;
  },
  upperArm(ctx) {
    capsule(ctx, 6.8, 6, 3, 20.5);
    fillStroke(ctx, hGrad(ctx, -3.4, 3.4, [[0, C.sleeveHi], [.45, C.sleeve], [1, C.sleeveDeep]]));
    ctx.beginPath(); ctx.moveTo(-6.6, 5.6); ctx.quadraticCurveTo(0, 9.6, 6.8, 5.8);
    ctx.lineTo(6, 9.4); ctx.quadraticCurveTo(0, 12.2, -5.8, 9.2); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -6.6, 6.8));
    ctx.beginPath(); ctx.moveTo(-8, 5); ctx.bezierCurveTo(-9, -2.6, -4.6, -6.4, .5, -6.2);
    ctx.bezierCurveTo(5.6, -6, 9, -2.2, 8.2, 5.2); ctx.quadraticCurveTo(0, 8, -8, 5); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -8.5, 8.5));
    ctx.save(); ctx.clip(); ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.beginPath(); ctx.ellipse(-3.2, -2, 2.4, 3.4, -.5, 0, TAU); ctx.fill(); ctx.restore();
    line(ctx, [[-7.4, 3.6], [0, 6.2], [7.6, 3.8]], C.inkSoft, .45);
  },
  forearm(ctx) {
    ctx.beginPath(); ctx.moveTo(-3.5, 1.6); ctx.lineTo(3.7, 1.6); ctx.lineTo(3, 16);
    ctx.quadraticCurveTo(0, 17.3, -2.8, 16); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -3.5, 3.7));
    line(ctx, [[-3.3, 6.4], [0, 7.2], [3.5, 6.4]], C.inkSoft, .4);
    poly(ctx, [[-2.9, 15.2], [3.1, 15.2], [3, 17.8], [-2.8, 17.8]]); fillStroke(ctx, C.glove, C.ink, .4);
    ctx.beginPath(); ctx.moveTo(0, -4.2); ctx.bezierCurveTo(3.8, -3.8, 5, -.6, 3.8, 2.6);
    ctx.lineTo(0, 4.4); ctx.lineTo(-3.8, 2.6); ctx.bezierCurveTo(-5, -.6, -3.8, -3.8, 0, -4.2); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -4.8, 4.8));
    ctx.fillStyle = '#9fa0a8'; ctx.beginPath(); ctx.arc(0, .2, .55, 0, TAU); ctx.fill();
  },
  fist(ctx) {
    ctx.beginPath(); ctx.roundRect(-3.3, -.4, 6.6, 6.4, 1.9);
    fillStroke(ctx, hGrad(ctx, -3.3, 3.3, [[0, C.gloveHi], [.5, C.glove], [1, '#16161b']]));
    line(ctx, [[-2.6, 3.9], [2.6, 3.9]], 'rgba(255,255,255,.18)', .5);
    for (const x of [-1.6, 0, 1.6]) line(ctx, [[x, 4.3], [x, 5.6]], 'rgba(0,0,0,.45)', .35);
    ctx.beginPath(); ctx.ellipse(-2.6, 2, 1.2, 1.9, .3, 0, TAU); fillStroke(ctx, C.gloveHi, C.ink, .35);
  },
  openHand(ctx) {
    ctx.beginPath(); ctx.ellipse(0, 1, 3.7, 4.2, 0, 0, TAU);
    fillStroke(ctx, hGrad(ctx, -4, 4, [[0, C.gloveHi], [.6, C.glove], [1, '#17181d']]));
    for (const x of [-2.7, -1, .8, 2.5]) line(ctx, [[x, -1.6], [x * 1.2, -6.6 + Math.abs(x) * .3]], C.glove, 1.1);
    line(ctx, [[-3, 1], [-6.2, -2.1]], C.gloveHi, 1.5);
  },
  thigh(ctx) {
    capsule(ctx, 11.6, 9, -.5, 28.8);
    fillStroke(ctx, hGrad(ctx, -5.8, 5.8, [[0, C.navyMid], [1, C.navyDeep]]));
    ctx.beginPath(); ctx.moveTo(-5.2, 3); ctx.quadraticCurveTo(0, 1, 5.4, 3);
    ctx.lineTo(4.5, 23.6); ctx.quadraticCurveTo(0, 25.8, -4, 23.6); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -5.2, 5.4));
    line(ctx, [[-4.8, 12.4], [0, 13.6], [5, 12.4]], C.inkSoft, .4);
    ctx.save(); ctx.globalAlpha = .6; line(ctx, [[-2.2, 4.4], [-1.8, 21]], '#ffffff', 1.1); ctx.restore();
  },
  shin(ctx) {
    ctx.beginPath(); ctx.moveTo(-4.5, 2); ctx.quadraticCurveTo(0, .3, 4.7, 2);
    ctx.lineTo(3.6, 25.4); ctx.quadraticCurveTo(0, 26.9, -3.3, 25.4); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -4.5, 4.7));
    ctx.save(); ctx.globalAlpha = .7; line(ctx, [[-.9, 5], [-.6, 23.4]], '#ffffff', .9); ctx.restore();
    poly(ctx, [[3.4, -1.4], [6.4, 1.6], [3.6, 3.4]]); fillStroke(ctx, C.plateMid, C.ink, .45);
    ctx.beginPath(); ctx.moveTo(0, -4.8); ctx.bezierCurveTo(3.7, -4.4, 5.1, -1, 3.9, 2.9);
    ctx.lineTo(0, 5.4); ctx.lineTo(-3.9, 2.9); ctx.bezierCurveTo(-5.1, -1, -3.7, -4.4, 0, -4.8); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -5, 5));
    ctx.fillStyle = 'rgba(255,255,255,.8)'; ctx.beginPath(); ctx.ellipse(-1.5, -1.6, 1.1, 1.9, .2, 0, TAU); ctx.fill();
  },
  foot(ctx) {
    ctx.beginPath(); ctx.moveTo(-3.2, -1.4); ctx.lineTo(3.2, -1.4);
    ctx.quadraticCurveTo(4.1, 3, 5.8, 5); ctx.quadraticCurveTo(8.8, 6.4, 9, 8.6);
    ctx.lineTo(-3.6, 8.6); ctx.quadraticCurveTo(-4.4, 4, -3.2, -1.4); ctx.closePath();
    fillStroke(ctx, plateGrad(ctx, -4, 9));
    line(ctx, [[-3.3, 2.2], [3.6, 2.4]], C.inkSoft, .4); line(ctx, [[-3.4, 5], [5.8, 5.2]], C.inkSoft, .4);
    poly(ctx, [[-3.9, 8.4], [9.2, 8.4], [9, 10], [-3.8, 10]]); fillStroke(ctx, '#2a2a31', C.ink, .4);
  },
  shield(ctx) {
    const outline = () => {
      ctx.beginPath(); ctx.moveTo(-20, -23); ctx.quadraticCurveTo(0, -26.4, 20, -23); ctx.lineTo(21, -12);
      ctx.bezierCurveTo(21, 6, 12, 24, 0, 38); ctx.bezierCurveTo(-12, 24, -21, 6, -21, -12); ctx.closePath();
    };
    outline();
    ctx.fillStyle = hGrad(ctx, -21, 21, [[0, C.steelHi], [.3, C.steel], [.75, '#8893a0'], [1, C.steelDeep]]); ctx.fill();
    ctx.save(); ctx.clip();
    ctx.fillStyle = 'rgba(255,255,255,.28)'; ctx.beginPath(); ctx.ellipse(-8, -6, 6, 26, .08, 0, TAU); ctx.fill();
    ctx.translate(0, -2); raptor(ctx, 2.1, 'rgba(21,26,38,.82)');
    ctx.restore();
    outline();
    ctx.lineWidth = 2.4; ctx.strokeStyle = hGrad(ctx, -21, 21, [[0, '#f0e3bd'], [.6, C.rim], [1, C.rimDeep]]); ctx.stroke();
    ctx.lineWidth = .6; ctx.strokeStyle = C.ink; ctx.stroke();
    line(ctx, [[0, -24.2], [0, 35]], 'rgba(255,255,255,.25)', .6);
    ctx.fillStyle = '#e9dcb4';
    for (const [x, y] of [[-17, -20], [17, -20], [0, -22.8], [-16, 4], [16, 4], [0, 32]]) { ctx.beginPath(); ctx.arc(x, y, .75, 0, TAU); ctx.fill(); }
  },
  // Cleaver frame: origin at the grip, +y toward the tip; `grip` is the grip's
  // distance from the pommel end. part: 'handle' | 'blade'.
  cleaver(ctx, {grip, part}) {
    const {handle, guard, blade, width, spine, chisel} = CLEAVER;
    const at = s => s - grip;
    if (part === 'handle') {
      const y0 = at(1.6), y1 = at(handle);
      ctx.beginPath(); ctx.roundRect(-2.2, y0, 4.4, y1 - y0, 1.4);
      fillStroke(ctx, hGrad(ctx, -2.2, 2.2, [[0, '#6a4f3e'], [.45, '#3d2d24'], [1, '#1f1712']]));
      ctx.save(); ctx.clip();
      for (let s = 3; s < handle - 1; s += 2.6) line(ctx, [[-2.4, at(s)], [2.4, at(s + 1.6)]], 'rgba(18,12,9,.75)', .6);
      ctx.restore();
      poly(ctx, [[0, at(-.8)], [2.2, at(.3)], [0, at(1.4)], [-2.2, at(.3)]]);            // short diamond pommel
      fillStroke(ctx, hGrad(ctx, -2.6, 2.6, [[0, '#ffffff'], [.5, '#c4cad2'], [1, '#79828e']]));
      line(ctx, [[0, at(-.5)], [0, at(1.1)]], 'rgba(255,255,255,.7)', .4);
      const g0 = at(handle);
      ctx.beginPath(); ctx.roundRect(-width + spine - 2, g0, width + 4, guard, 1.2);  // bolster guard
      fillStroke(ctx, vGrad(ctx, g0, g0 + guard, [[0, '#d0d5dc'], [.5, '#949ca7'], [1, '#626a75']]));
      ctx.fillStyle = '#e5e9ee';
      for (const x of [-width + spine + 1.5, -width / 2 + spine, spine - 1.2, 0]) { ctx.beginPath(); ctx.arc(x, g0 + guard / 2, .65, 0, TAU); ctx.fill(); }
      return;
    }
    // Blade: flat spine on +x, keen edge on -x, angled chisel point on the spine.
    const b0 = at(handle + guard), b1 = b0 + blade, edgeX = spine - width, drop = width * chisel;
    const outline = () => {
      ctx.beginPath(); ctx.moveTo(spine, b0); ctx.lineTo(spine, b1); ctx.lineTo(edgeX, b1 - drop);
      ctx.lineTo(edgeX, b0 + 3.5); ctx.quadraticCurveTo(edgeX + 1.2, b0, edgeX + 3.2, b0); ctx.closePath();
    };
    outline();
    ctx.fillStyle = hGrad(ctx, edgeX, spine, [[0, C.bladeCold], [.02, C.bladeEdge], [.07, '#fbfcfd'], [.43, C.bladeBevel],
      [.455, '#8e98a6'], [.47, '#ffffff'], [.54, C.blade], [.9, '#e6eaef'], [.93, C.bladeSpine], [1, '#b9c0c9']]);
    ctx.fill();
    ctx.save(); ctx.clip();
    // Mirror luster: long diagonal reflections and a darker reflected horizon.
    ctx.globalAlpha = .55; ctx.fillStyle = '#ffffff';
    for (const [y, w] of [[b0 + blade * .18, 7], [b0 + blade * .58, 4], [b0 + blade * .8, 10]]) {
      ctx.beginPath(); ctx.moveTo(spine, y); ctx.lineTo(spine, y + w); ctx.lineTo(edgeX, y + w + 14); ctx.lineTo(edgeX, y + 14); ctx.closePath(); ctx.fill();
    }
    ctx.globalAlpha = .2; ctx.fillStyle = '#56647a';
    ctx.beginPath(); ctx.moveTo(spine, b0 + blade * .42); ctx.lineTo(spine, b0 + blade * .48); ctx.lineTo(edgeX, b0 + blade * .58); ctx.lineTo(edgeX, b0 + blade * .52); ctx.closePath(); ctx.fill();
    ctx.globalAlpha = 1;
    // Chisel facet.
    ctx.beginPath(); ctx.moveTo(spine, b1); ctx.lineTo(edgeX, b1 - drop); ctx.lineTo(edgeX, b1 - drop - 3.2); ctx.lineTo(spine, b1 - 3.2); ctx.closePath();
    ctx.fillStyle = 'rgba(255,255,255,.6)'; ctx.fill();
    line(ctx, [[spine, b1 - 3.2], [edgeX, b1 - drop - 3.2]], 'rgba(110,122,138,.7)', .45);
    ctx.restore();
    outline(); ctx.strokeStyle = C.ink; ctx.lineWidth = .6; ctx.stroke();
    line(ctx, [[edgeX + .5, b0 + 4], [edgeX + .5, b1 - drop - 1]], '#ffffff', .6);
  },
  dagger(ctx, {alpha = 1} = {}) {
    const {blade, hilt} = DAGGER;
    ctx.save(); ctx.globalAlpha *= alpha;
    ctx.beginPath(); ctx.roundRect(-1.1, -hilt * .45, 2.2, hilt * .8, .8); fillStroke(ctx, '#17151f', C.ink, .35);
    poly(ctx, [[-3, hilt * .35], [3, hilt * .35], [2.6, hilt * .35 + 1.4], [-2.6, hilt * .35 + 1.4]]); fillStroke(ctx, '#1c1a26', C.ink, .3);
    const b0 = hilt * .35 + 1.4;
    const edge = () => poly(ctx, [[-2.1, b0], [2.1, b0], [2.6, b0 + DAGGER.blade * .36], [0, b0 + DAGGER.blade], [-2.6, b0 + DAGGER.blade * .36]]);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.shadowColor = 'rgba(150,120,255,.85)'; ctx.shadowBlur = 6;
    edge(); ctx.fillStyle = 'rgba(70,50,140,.35)'; ctx.fill(); ctx.restore();
    edge(); fillStroke(ctx, hGrad(ctx, -2.6, 2.6, [[0, '#3a3456'], [.48, C.obsidian], [1, '#05050a']]), 'rgba(196,184,255,.95)', .5);
    line(ctx, [[0, b0 + .5], [0, b0 + blade - 1]], C.obsidianHi, .45);
    line(ctx, [[.9, b0 + 2], [1.5, b0 + blade * .3]], '#e4ddff', .35);
    ctx.restore();
  },
  staff(ctx, {grip = STAFF.grip} = {}) {
    const low = -grip, high = STAFF.length - grip;
    ctx.beginPath(); ctx.moveTo(-3.1, low + 4); ctx.lineTo(-2.6, high - 7);
    ctx.quadraticCurveTo(0, high - 5, 2.6, high - 7);
    ctx.lineTo(3.1, low + 4); ctx.quadraticCurveTo(0, low - 1, -3.1, low + 4); ctx.closePath();
    fillStroke(ctx, hGrad(ctx, -3.2, 3.2, [[0, '#34271f'], [.45, '#826449'], [1, '#241b19']]));
    line(ctx, [[-.8, low + 6], [-1.1, high - 8]], 'rgba(240,205,150,.5)', .7);
    for (const y of [low + 5, -10, 8, high - 8]) {
      ctx.beginPath(); ctx.roundRect(-3.6, y, 7.2, 2.3, .6); fillStroke(ctx, C.brass, C.brassDeep, .35);
    }
    poly(ctx, [[0, high + 7], [5, high], [3, high - 7], [-3, high - 7], [-5, high]]);
    fillStroke(ctx, hGrad(ctx, -5, 5, [[0, '#5c8b99'], [.5, '#d8f4f1'], [1, '#51778e']]));
    line(ctx, [[0, high + 5], [0, high - 5]], '#ffffff', .65);
  },
  wand(ctx, {grip = WAND.grip} = {}) {
    const low = -grip, high = WAND.length - grip;
    poly(ctx, [[-2.2, low], [2.2, low], [1.7, high - 5], [-1.7, high - 5]]);
    fillStroke(ctx, hGrad(ctx, -2.2, 2.2, [[0, '#322331'], [.5, '#76526f'], [1, '#261b2b']]));
    for (const y of [low + 3, high - 8]) {
      ctx.beginPath(); ctx.roundRect(-2.8, y, 5.6, 2, .5); fillStroke(ctx, C.brass, C.brassDeep, .3);
    }
    poly(ctx, [[0, high + 4], [3.4, high - 1], [0, high - 7], [-3.4, high - 1]]);
    fillStroke(ctx, hGrad(ctx, -3.4, 3.4, [[0, '#608aa8'], [.5, '#e3f7ff'], [1, '#6d70a6']]));
  },
};

// ---------------------------------------------------------------------------
// Frame helpers. Local rig space is pre-mirror and root-relative (scaled).
// A far part paints from the pre-darkened palette instead of setting
// ctx.filter, which forced an offscreen pass for every far limb each frame.
function frame(ctx, rig, wx, wy, angle, paint, filter = '') {
  ctx.save(); ctx.translate(wx, wy); ctx.scale(rig.facing * rig.scale, rig.scale); ctx.rotate(angle);
  const near = C; if (filter) C = FAR_PALETTE;
  try { paint(ctx); } finally { C = near; ctx.restore(); }
}
const worldOf = (rig, lx, ly) => [rig.rootX + lx * rig.facing, rig.rootY + ly];
function frameToLocal(rig, ox, oy, angle, px, py) {
  const s = rig.scale;
  return [ox + (px * Math.cos(angle) - py * Math.sin(angle)) * s, oy + (px * Math.sin(angle) + py * Math.cos(angle)) * s];
}
const dirOf = angle => [-Math.sin(angle), Math.cos(angle)];
const FAR = 'brightness(.8) saturate(.92)';

// ---------------------------------------------------------------------------
// Per-figure animation state lives on the rig so DOM figures and arcade
// entities each keep their own blend, trail and dust.
function stateOf(rig) {
  if (!rig.doran) rig.doran = {ch: {...DORAN_POSES.rest}, beat: '', beatAt: 0, attackAt: -1,
    trail: [], dust: [], rings: [], impactAt: -1, dustAt: -1, fidget: null, fidgetAt: 0};
  return rig.doran;
}

// Which pose the figure is reaching for, and how fast (tau ms; Infinity = hold).
function resolveTarget(st, {pose, beat, now, attackAnimation, maneuver, loadout, reduced, alive, idleFidgets}) {
  if (!alive || pose === 'down') return {key: 'down', tau: 160};
  const sweep = SWEEP_MANEUVERS.has(maneuver) || /sweep|cleave|spin|whirl/i.test(attackAnimation || '');
  const flare = maneuver === 'Menacing Attack' ? .35 : 0;
  const cue = beat || (['windup', 'strike', 'cast', 'cast_channel', 'cast_release', 'hit', 'crit', 'impact', 'attack', 'dodge'].includes(pose) ? pose : '');
  if (cue !== st.beat) { st.beat = cue; st.beatAt = now; }
  const age = now - st.beatAt;
  const strikeClip = t => {
    if (t < 95) return {key: sweep ? 'sweep' : 'strike', tau: reduced ? 0 : 16, flare, phase: 'snap'};
    if (t < 170) return {key: sweep ? 'sweep' : 'strike', tau: Infinity, flare, phase: 'hold'};
    return {key: sweep ? 'sweepFollow' : 'follow', tau: 110, flare, phase: 'follow'};
  };
  if (cue === 'windup') return {key: sweep ? 'sweepWind' : 'windup', tau: 70, flare};
  if (cue === 'strike') return strikeClip(age);
  if (cue === 'attack') {                       // arcade / preview loop
    const t = (now - (st.attackAt < 0 ? (st.attackAt = now) : st.attackAt)) % 1250;
    if (t < 480) return {key: sweep ? 'sweepWind' : 'windup', tau: 80, flare};
    return strikeClip(t - 480);
  }
  st.attackAt = -1;
  if (['hit', 'impact', 'crit'].includes(cue)) return {key: 'hit', tau: 30};
  if (['miss', 'dodge'].includes(cue)) return {key: 'low', tau: 55};
  if (beat === 'guard' || pose === 'block') return {key: 'brace', tau: 55};
  // Doran is no caster: a channel is the raised command, the release its thrust.
  if (cue === 'cast' || cue === 'cast_channel') return {key: 'command', tau: 80};
  if (cue === 'cast_release') return {key: 'point', tau: 40, contact: true};
  if (cue.startsWith('gesture:') && DORAN_POSES[cue.slice(8)]) return {key: cue.slice(8), tau: 120};
  if (beat === 'move' || ['run', 'travel', 'move', 'advance', 'retreat'].includes(pose)) return {key: 'run', tau: 60};
  if (['jump', 'fall', 'fly', 'airborne'].includes(pose)) return {key: 'jump', tau: 70};
  if (['climb', 'vault'].includes(pose)) return {key: 'climb', tau: 80};
  if (DORAN_POSES[pose] && !['rest', 'guard'].includes(pose)) return {key: pose, tau: 120};
  if (maneuver && MANEUVER_STANCE[maneuver]) return {key: MANEUVER_STANCE[maneuver], tau: 110, flare: .25};
  if (pose === 'guard' || pose === 'combat') return {key: 'guard', tau: 140};
  // Idle downtime: an occasional fidget from the style guide's vocabulary.
  if (idleFidgets && !reduced && loadout === 'cleaver') {
    if (!st.fidgetAt) st.fidgetAt = now + 6000 + (now % 5000);
    if (st.fidget && now > st.fidgetAt + 2600) { st.fidget = null; st.fidgetAt = now + 9000 + (now % 7000); }
    else if (!st.fidget && now > st.fidgetAt) { st.fidget = FIDGETS[Math.floor(now / 997) % FIDGETS.length]; st.fidgetAt = now; }
    if (st.fidget) return {key: st.fidget, tau: 200};
  }
  return {key: 'rest', tau: 180};
}

function runChannels(now, reduced) {
  const phase = reduced ? .8 : now * .0085, w = Math.sin(phase), c = Math.abs(Math.cos(phase));
  return {...DORAN_POSES.rest, sp: .1, to: .02, lt: .5 * w, rt: -.5 * w, ls: Math.max(0, -w) * .85 + .1,
    rs: Math.max(0, w) * .85 + .1, py: -c * 1.8, nu: -.3 - .25 * w, nl: -.5,
    // Walking with the blade out: carried casually over the shoulder like a
    // worker's shovel -- hand in front at the chest, handle on the shoulder.
    hx: SHOULDER_CARRY.hx, hy: SHOULDER_CARRY.hy + c * .8, bl: SHOULDER_CARRY.bl, gr: 0, sup: 0, wf: 0, hf: 1, af: 1, stow: 0, eb: 1,
    vis: .55, cape: .22 + .05 * Math.sin(phase * 2), plant: 0};
}

function targetChannels(key, {now, loadout, reduced}) {
  const base = key === 'run' ? runChannels(now, reduced) : {...(DORAN_POSES[key] || DORAN_POSES.rest)};
  if (loadout === 'daggers' && !base.stow) {
    const hand = DAGGER_HAND[key] || (key === 'run' ? [-12.3, -67.6, .6] : DAGGER_HAND.guard);
    // The dagger arm works in front of the body, low behind the kite.
    const front = !['rest', 'run', 'hit', 'down', 'jump'].includes(key);
    Object.assign(base, {hx: hand[0], hy: hand[1], bl: hand[2], sup: 0, wf: 0, hf: 0, af: front ? 1 : base.af});
  }
  if (loadout === 'staff' || loadout === 'wand') {
    const point = ['staffPoint', 'point', 'strike', 'follow', 'sweep', 'sweepFollow'].includes(key);
    const raised = ['windup', 'sweepWind', 'command', 'victory', 'cheer'].includes(key);
    if (key !== 'down' && key !== 'ko') Object.assign(base, {
      hx: point ? 24 : raised ? 16 : 26, hy: point ? -82 : raised ? -99 : key === 'run' ? -68 : -61,
      bl: point ? -1.3 : raised ? -2.95 : loadout === 'staff' ? 3.08 : .45,
      gr: 0, sup: 0, stow: 0, af: 1, hf: 1, wf: point ? 1 : 0, eb: -1,
    });
  }
  if (!reduced && key !== 'down') {             // breath
    base.sp += Math.sin(now * .0021) * .012; base.py += Math.sin(now * .0021) * .35;
  }
  return base;
}

// ---------------------------------------------------------------------------
// Public: draw Doran on `rig` (a SkeletalRig whose scale is already set).
//   x, y       canvas point of his ground contact; facing 1 = right
//   pose       poseFor() output; beat = the combat director's live beat
//   paint      false: advance and measure only (sockets for the FX engine)
// Returns world sockets {head, chest, main_hand, off_hand, ground, weapon_main,
// weapon_tip, shield, focus}.
export function drawDoran(ctx, rig, model = {}, {
  x = 0, y = 0, facing = 1, dt = 16, now = performance.now(), pose = 'idle', beat = '', attackAnimation = '',
  maneuver = model.maneuver || null, loadout = model.loadout || 'cleaver', paint = true, reducedMotion = false,
  shadow = true, idleFidgets = true, weapons = true, casting = null,
} = {}) {
  rig.reshape('doran', SKELETON);
  const st = stateOf(rig);
  const reduced = Boolean(reducedMotion);
  const want = resolveTarget(st, {pose, beat, now, attackAnimation, maneuver, loadout, reduced, alive: model.alive !== false, idleFidgets});
  const target = targetChannels(want.key, {now, loadout, reduced});
  const castingBeat = casting && ['cast', 'cast_channel', 'cast_release'].includes(beat || pose);
  const implementCast = castingBeat && isCastingImplement(loadout, casting);
  const handCast = castingBeat && !implementCast;
  if (castingBeat) {
    const release = (beat || pose) === 'cast_release', high = casting.stance === 'overhead';
    Object.assign(target, {sp: release ? .12 : -.06, vis: release ? 1.2 : 1.05});
    if (implementCast) {
      Object.assign(target, {
        hx: release ? 27 : high ? 10 : 18, hy: release ? -86 : high ? -112 : -79,
        bl: release ? -1.25 : high ? -2.65 : -3.05,
        stow: 0, af: 1, hf: 1, wf: release ? 1 : 0,
        sup: casting.hands === 2 && loadout === 'staff' ? 1 : 0,
        lc: casting.hands === 2 && loadout === 'wand' ? 1 : 0,
        lx: release ? 10 : -27, ly: high ? -111 : -91,
      });
    } else if (casting.hands === 2) {
      Object.assign(target, {
        hx: release ? 29 : high ? 13 : 10, hy: high ? -115 : release ? -88 : -84,
        lx: release ? 13 : high ? -27 : -24, ly: high ? -113 : release ? -86 : -97,
        lc: 1, sup: 0, stow: 1, af: 1, hf: 1, wf: 0,
      });
    } else {
      Object.assign(target, {
        lx: release ? 20 : high ? -24 : -38, ly: release ? -88 : high ? -119 : -108,
        lc: 1, sup: 0, hx: loadout === 'staff' ? 26 : 22, hy: -59,
        bl: loadout === 'staff' ? 3.08 : loadout === 'wand' ? .45 : target.bl,
        stow: loadout === 'cleaver' ? 1 : 0, af: 1, hf: 1, wf: 0,
      });
    }
  }
  target.vis += want.flare || 0;
  // Blend every channel toward the target; tau = Infinity is the hitstop.
  const ch = st.ch;
  const k = reduced || !Number.isFinite(dt) ? 1 : want.tau === Infinity ? 0 : want.tau <= 0 ? 1 : 1 - Math.exp(-Math.max(0, dt) / want.tau);
  for (const key of Object.keys(target)) ch[key] = (ch[key] ?? target[key]) + (target[key] - (ch[key] ?? target[key])) * k;

  // --- pose the skeleton -----------------------------------------------------
  const R = rig.bones, bone = n => R.get(n), set = (n, a) => { const b = bone(n); if (b) b.localAngle = b.restAngle + a; };
  rig.resetPose(); rig.pose = want.key; rig.weapon = loadout;
  // Contact: the strike's hitstop or a release. puppet-dom reports it once.
  if ((want.phase === 'hold' || want.contact) && st.contactAt !== st.beatAt) st.contactAt = st.beatAt;
  bone('pelvis').localY += ch.py; bone('pelvis').localAngle = ch.pa;
  set('spine', ch.sp); set('torso', ch.to); set('head', ch.hd);
  set('left_thigh', ch.lt); set('left_shin', ch.ls); set('right_thigh', ch.rt); set('right_shin', ch.rs);
  set('left_upper_arm', ch.nu); set('left_lower_arm', ch.nl);
  rig.update(0, x, y, facing);
  // Ground contact: drop or lift the body so the lower sole meets the floor.
  if (ch.air < .5) {
    const sole = n => { const b = bone(n); return b.y + SOLE * rig.scale * Math.cos(b.angle * .35); };
    const lowest = Math.max(sole('left_foot'), sole('right_foot'));
    bone('pelvis').localY -= lowest / rig.scale;
    rig.update(0, x, y, facing);
    // Stances keep both sabatons down: IK the lifted leg back onto the floor.
    // A target past the leg's reach slides along the floor toward the hip.
    if (ch.plant > .5) for (const side of ['left', 'right']) {
      const ankle = bone(side + '_foot'), hip = bone(side + '_hip'), floor = -SOLE * rig.scale;
      if (ankle.y >= floor - .5) continue;
      const reach = (bone(side + '_thigh').length + bone(side + '_shin').length) * rig.scale * .995;
      const span = Math.sqrt(Math.max(0, reach * reach - (floor - hip.y) ** 2));
      rig.plant(side, hip.x + Math.max(-span, Math.min(span, ankle.x - hip.x)), floor);
    }
  }
  const s = rig.scale;
  // Weapon hand: IK to the pose target (root-relative units) using near arm (right).
  const cleaverStowed = loadout === 'daggers' || loadout === 'cleaver' && ch.stow > .5;
  const cleaverHeld = loadout === 'cleaver' && !cleaverStowed;
  const focusWeapon = loadout === 'staff' || loadout === 'wand';
  const focusStowed = focusWeapon && handCast && casting.hands === 2;
  rig.reach('right', ch.hx * s, ch.hy * s, ch.eb >= 0 ? 1 : -1);
  const fistCentre = side => {
    const lower = bone(side + '_lower_arm'), hand = bone(side + '_hand'), [dx, dy] = dirOf(lower.angle);
    return [hand.x + dx * FIST_REACH * s, hand.y + dy * FIST_REACH * s];
  };
  // Second hand on the handle (choked two-handed leverage).
  const gripS = focusWeapon ? (loadout === 'staff' ? STAFF.grip : WAND.grip)
    : CLEAVER.grips.reach + (CLEAVER.grips.choke - CLEAVER.grips.reach) * Math.max(0, Math.min(1, ch.gr));
  const [gx, gy] = fistCentre('right');
  const [bdx, bdy] = dirOf(ch.bl);
  if ((cleaverHeld || focusWeapon && !focusStowed) && ch.sup > .02) {
    const along = (loadout === 'staff' ? -STAFF.support
      : (gripS >= CLEAVER.handle / 2 ? -1 : 1) * CLEAVER.support) * s;
    const tx = gx + bdx * along, ty = gy + bdy * along;
    const wrist = bone('left_hand');
    for (let i = 0; i < 2; i++) {
      const [dx, dy] = dirOf(bone('left_lower_arm').angle);
      const aimX = tx - dx * FIST_REACH * s, aimY = ty - dy * FIST_REACH * s;
      rig.reach('left', wrist.x + (aimX - wrist.x) * ch.sup, wrist.y + (aimY - wrist.y) * ch.sup, 1);
    }
  }
  if (ch.lc > .02) {
    const wrist = bone('left_hand');
    rig.reach('left', wrist.x + (ch.lx * s - wrist.x) * ch.lc,
      wrist.y + (ch.ly * s - wrist.y) * ch.lc, 1);
  }

  // --- motion FX bookkeeping ---------------------------------------------------
  const bladePoint = frac => {
    const along = (CLEAVER.handle + CLEAVER.guard + CLEAVER.blade * frac - gripS) * s;
    const across = (CLEAVER.spine - CLEAVER.width / 2) * s;
    const [ax, ay] = [bdy, -bdx];                // blade frame +x in local space
    return worldOf(rig, gx + bdx * along + ax * across, gy + bdy * along + ay * across);
  };
  if (!reduced && cleaverHeld) {
    if (want.phase === 'snap' || want.phase === 'follow' && now - st.beatAt < 360) {
      st.trail.push({t: now, a: bladePoint(.98), b: bladePoint(.45)});
    }
    if (want.phase === 'hold' && st.impactAt !== st.beatAt) {
      st.impactAt = st.beatAt;
      const [cx, cy] = bladePoint(.7);
      st.rings.push({t: now, x: cx, y: cy});
    }
    if (want.phase === 'follow' && !/sweep/i.test(want.key) && st.dustAt !== st.beatAt) {
      const [tx, ty] = bladePoint(1);
      if (ty > rig.rootY - 8 * s) {
        st.dustAt = st.beatAt;
        for (let i = 0; i < 16; i++) {
          const a = Math.PI + Math.random() * Math.PI, v = .02 + Math.random() * .06;
          st.dust.push({t: now, x: tx, y: rig.rootY, vx: Math.cos(a) * v * s * 2.2, vy: Math.sin(a) * v * s * 1.3, r: (1.4 + Math.random() * 2.4) * s, chip: i % 4 === 0});
        }
      }
    }
  }
  st.trail = st.trail.filter(p => now - p.t < 240).slice(-24);
  st.rings = st.rings.filter(r => now - r.t < 320);
  st.dust = st.dust.filter(d => now - d.t < 650);

  // --- paint --------------------------------------------------------------------
  const torso = bone('torso'), head = bone('head');
  // The kite rides the far forearm (left arm); with both hands on the Cleaver it tucks in
  // against the upper arm so it never crosses the swing (spec Mode B).
  const shieldArm = bone('left_lower_arm'), elbow = bone('left_upper_arm'), shoulder = bone('left_shoulder');
  const tuck = Math.max(0, Math.min(1, ch.sup)) * (cleaverHeld || focusWeapon && !focusStowed ? 1 : 0);
  const onArm = [elbow.endX + (shieldArm.endX - elbow.endX) * .5 - 4.5 * s, elbow.endY + (shieldArm.endY - elbow.endY) * .5 + 5 * s];
  const slung = [shoulder.x - 5 * s, shoulder.y + 27 * s];
  const shieldCentre = worldOf(rig, onArm[0] + (slung[0] - onArm[0]) * tuck, onArm[1] + (slung[1] - onArm[1]) * tuck);
  const shieldAngle = (ch.sh + shieldArm.angle * .1) * (1 - tuck) + (torso.angle * .6 + .12) * tuck;
  const [fgx, fgy] = worldOf(rig, gx, gy);
  const farFist = worldOf(rig, ...fistCentre('left'));
  const torsoHeight = -torso.y / s;
  const visorAt = frameToLocal(rig, head.x, head.y, head.angle, .6, -10.6);
  const sockets = {
    head: {x: worldOf(rig, ...visorAt)[0], y: worldOf(rig, ...visorAt)[1], rotation: head.worldAngle},
    chest: (([cx, cy]) => ({x: cx, y: cy, rotation: torso.worldAngle}))(worldOf(rig, ...frameToLocal(rig, torso.x, torso.y, torso.angle, 0, 10))),
    main_hand: {x: fgx, y: fgy, rotation: ch.bl * facing},
    off_hand: {x: shieldCentre[0], y: shieldCentre[1], rotation: shieldAngle * facing},
    ground: {x: rig.rootX, y: rig.rootY, rotation: 0},
  };
  sockets.weapon_main = sockets.main_hand;
  sockets.shield = sockets.off_hand;
  if (focusWeapon && !focusStowed) {
    const length = loadout === 'staff' ? STAFF.length : WAND.length;
    sockets.weapon_tip = (([tx, ty]) => ({x: tx, y: ty, rotation: ch.bl * facing}))(
      worldOf(rig, gx + bdx * (length - gripS) * s, gy + bdy * (length - gripS) * s));
  } else sockets.weapon_tip = cleaverHeld
    ? (([tx, ty]) => ({x: tx, y: ty, rotation: ch.bl * facing}))(bladePoint(1))
    : sockets.main_hand;
  sockets.focus = implementCast ? sockets.weapon_tip : handCast
    ? casting.hands === 1 ? {x: farFist[0], y: farFist[1]}
      : {x: (fgx + farFist[0]) / 2, y: (fgy + farFist[1]) / 2}
    : sockets.main_hand;
  if (!paint) return sockets;

  const ops = [];
  const add = (z, fn) => ops.push({z, fn});
  const onBone = (name, painter, opts = {}, filter = '') => {
    const b = bone(name); return () => frame(ctx, rig, b.worldX, b.worldY, b.angle, c => PAINT[painter](c, opts), filter);
  };
  if (shadow) add(0, () => {
    ctx.save(); ctx.fillStyle = 'rgba(0,0,0,.34)'; ctx.beginPath();
    ctx.ellipse(rig.rootX, rig.rootY + s * .6, 24 * s, 4.2 * s, 0, 0, TAU); ctx.fill(); ctx.restore();
  });
  const trail = Math.max(-.2, Math.min(.6, ch.cape));
  add(10, () => frame(ctx, rig, torso.worldX, torso.worldY, torso.angle * .6 + trail * .5,
    c => PAINT.cape(c, {length: Math.max(30, Math.min(84, torsoHeight - 4)), trail, t: now})));

  // Far arm (left arm): holds shield and secondary dagger / second hand grip.
  const castingArmFront = ch.lc > .5;
  add(castingArmFront ? 97 : 30, onBone('left_upper_arm', 'upperArm', {}, FAR));
  add(castingArmFront ? 98 : 31, onBone('left_lower_arm', 'forearm', {}, FAR));
  const leftHand = bone('left_hand'), leftLower = bone('left_lower_arm');
  const leftGrips = ch.sup > .5 && (cleaverHeld || focusWeapon && !focusStowed);
  add(leftGrips || castingArmFront ? 107 : 40, () => frame(ctx, rig, leftHand.worldX, leftHand.worldY, leftLower.angle,
    c => PAINT[handCast || implementCast && !leftGrips ? 'openHand' : 'fist'](c), leftGrips ? '' : FAR));
  if (model.showShield) {
    add(castingArmFront ? 96 : 35, () => frame(ctx, rig, shieldCentre[0], shieldCentre[1], shieldAngle, c => PAINT.shield(c), FAR));
  }

  for (const [side, z, filter] of [['left', 48, FAR], ['right', 50, '']]) {
    add(z, onBone(side + '_thigh', 'thigh', {}, filter));
    add(z + 1, onBone(side + '_shin', 'shin', {}, filter));
    const foot = bone(side + '_foot'), shin = bone(side + '_shin');
    add(z + 1.5, () => frame(ctx, rig, foot.worldX, foot.worldY, shin.angle * (ch.plant > .5 ? .06 : .35), c => PAINT.foot(c), filter));
  }
  const pelvis = bone('pelvis');
  add(55, () => frame(ctx, rig, pelvis.worldX, pelvis.worldY, pelvis.angle,
    c => PAINT.pelvisSkirt(c, {swing: -(ch.lt + ch.rt) * .22 + (bone('left_thigh').angle + bone('right_thigh').angle) * .12})));
  add(60, onBone('torso', 'torso'));
  add(62, () => frame(ctx, rig, pelvis.worldX, pelvis.worldY, pelvis.angle, c => PAINT.pelvisBelt(c)));
  add(70, onBone('head', 'helm'));
  add(71, onBone('head', 'visor', {glow: ch.vis, t: now}));
  add(80, onBone('torso', 'cowl'));

  // Near arm (right arm): primary weapon arm (cleaver / main dagger).
  const armFront = ch.af > .5;
  add(armFront ? 95 : 90, onBone('right_upper_arm', 'upperArm'));
  add(armFront ? 96 : 91, onBone('right_lower_arm', 'forearm'));
  const rightHand = bone('right_hand'), rightLower = bone('right_lower_arm');
  const rightFront = ch.hf > .5 && (cleaverHeld || focusWeapon && !focusStowed) || armFront;
  add(rightFront ? 106 : 94, () => frame(ctx, rig, rightHand.worldX, rightHand.worldY,
    focusWeapon && !focusStowed ? ch.bl : rightLower.angle,
    c => PAINT[handCast && casting.hands === 2 ? 'openHand' : 'fist'](c)));

  // Weapons.
  if (!weapons) { /* bust renders (voice cards) leave weapons out */ } else if (cleaverStowed) {
    add(20, () => frame(ctx, rig, torso.worldX, torso.worldY, torso.angle, c => {
      c.translate(9, -52); c.rotate(.42);
      PAINT.cleaver(c, {grip: CLEAVER.grips.reach, part: 'blade'}); PAINT.cleaver(c, {grip: CLEAVER.grips.reach, part: 'handle'});
    }, FAR));
  } else if (cleaverHeld) {
    add(ch.hf > .5 ? 105 : 92, () => frame(ctx, rig, fgx, fgy, ch.bl, c => PAINT.cleaver(c, {grip: gripS, part: 'handle'})));
    add(ch.wf > .5 ? 110 : 93, () => frame(ctx, rig, fgx, fgy, ch.bl, c => PAINT.cleaver(c, {grip: gripS, part: 'blade'})));
  }
  if (weapons && focusWeapon) {
    if (focusStowed) add(20, () => frame(ctx, rig, torso.worldX, torso.worldY, torso.angle, c => {
      c.translate(loadout === 'staff' ? 9 : 13, loadout === 'staff' ? -42 : -48); c.rotate(.35);
      PAINT[loadout](c, {grip: gripS});
    }, FAR));
    else add(ch.wf > .5 ? 110 : 105, () => frame(ctx, rig, fgx, fgy, ch.bl,
      c => PAINT[loadout](c, {grip: gripS})));
  }
  if (weapons && loadout === 'daggers' && ch.stow <= .5 && !(handCast && casting.hands === 2)) {
    add(ch.hf > .5 ? 105.5 : 93.5, () => frame(ctx, rig, fgx, fgy, ch.bl, c => PAINT.dagger(c)));
    add(39, () => frame(ctx, rig, farFist[0], farFist[1], shieldArm.angle - Math.PI / 2, c => PAINT.dagger(c), FAR));
  }
  // Silver crescent wake, impact ripple, ground rupture.
  if (st.trail.length > 1) add(120, () => {
    ctx.save();
    for (let i = 1; i < st.trail.length; i++) {
      const p = st.trail[i - 1], q = st.trail[i], life = 1 - (now - q.t) / 240;
      ctx.beginPath(); ctx.moveTo(...p.a); ctx.lineTo(...q.a); ctx.lineTo(...q.b); ctx.lineTo(...p.b); ctx.closePath();
      ctx.fillStyle = `rgba(236,242,255,${(.5 * life).toFixed(3)})`; ctx.fill();
      ctx.beginPath(); ctx.moveTo(...p.a); ctx.lineTo(...q.a);
      ctx.strokeStyle = `rgba(255,255,255,${(.9 * life).toFixed(3)})`; ctx.lineWidth = 1.4 * s; ctx.stroke();
    }
    ctx.restore();
  });
  if (st.rings.length || st.dust.length) add(121, () => {
    ctx.save();
    for (const r of st.rings) {
      const t = (now - r.t) / 320;
      ctx.strokeStyle = `rgba(245,248,255,${(.8 * (1 - t)).toFixed(3)})`; ctx.lineWidth = (2.4 - t * 1.8) * s;
      ctx.beginPath(); ctx.ellipse(r.x, r.y, (6 + t * 26) * s, (3 + t * 12) * s, 0, 0, TAU); ctx.stroke();
    }
    for (const d of st.dust) {
      const t = (now - d.t) / 650, age = now - d.t;
      const px = d.x + d.vx * age, py = d.y + d.vy * age + (d.chip ? .00018 * age * age * s : 0);
      if (d.chip) { ctx.fillStyle = `rgba(58,52,48,${(1 - t).toFixed(3)})`; ctx.fillRect(px, Math.min(py, d.y), 1.3 * s, 1.3 * s); }
      else { ctx.fillStyle = `rgba(196,184,166,${(.45 * (1 - t)).toFixed(3)})`; ctx.beginPath(); ctx.arc(px, py, d.r * (1 + t * 1.6), 0, TAU); ctx.fill(); }
    }
    ctx.restore();
  });
  ops.sort((a, b) => a.z - b.z);
  for (const op of ops) op.fn();
  return sockets;
}

// Loadout from public actor data: the host may name one; the cleaver is his
// field default (DM041_A: live one- or two-handed).
export function doranLoadout(item = {}, visibleWeapon = 'none') {
  const named = String(item.loadout || item.weapon_mode || '').toLowerCase();
  if (/dagger/.test(named)) return 'daggers';
  if (/staff/.test(named)) return 'staff';
  if (/wand/.test(named)) return 'wand';
  const visible = String(visibleWeapon).toLowerCase();
  return visible === 'staff' || visible === 'wand' ? visible : 'cleaver';
}

// Voice-card medallion: helm, mantle and heraldry drawn by the same rig, so
// the portrait can never drift from the figure on the stage.
let portrait = '';
export function doranPortrait(size = 128) {
  if (portrait || typeof document === 'undefined') return portrait;
  try {
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d'), scale = size / 58;
    const bg = ctx.createRadialGradient(size * .42, size * .3, size * .05, size * .5, size * .5, size * .75);
    bg.addColorStop(0, '#3a4868'); bg.addColorStop(1, '#0d1220');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, size, size);
    drawDoran(ctx, new SkeletalRig({scale}), {alive: true}, {x: size * .5, y: size * .5 + 102 * scale, pose: 'rest',
      now: 0, dt: 0, reducedMotion: true, shadow: false, weapons: false, idleFidgets: false});
    portrait = canvas.toDataURL('image/png');
  } catch { portrait = ''; }
  return portrait;
}

export const DORAN_RIG = Object.freeze({
  identity: 'doran', kind: 'vector-rig', heightUnits: DORAN_HEIGHT_UNITS,
  layers: DORAN_PAPERDOLL_LAYERS, poses: Object.keys(DORAN_POSES), loadouts: DORAN_LOADOUTS,
  draw: drawDoran, loadout: doranLoadout, portrait: doranPortrait,
});
