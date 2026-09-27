// Hero rig: the full-detail figure for every actor without a champion rig.
//
// Custom leads, townsfolk, rehearsal foes and roster NPCs all draw here. The
// figure is built from the Actor Look (actor-look.js): proportions from race,
// gender and build; colour slots from the creator's choices; garments,
// headgear, shields and weapons from the equipped items' presentation. It
// keeps the champion contract (wren-rig.js, doran-rig.js): parts paint in
// their bone's local frame on the shared SkeletalRig, poses are plain numbers
// that blend, hands reach by IK, and draw() returns the world sockets the FX
// engine and combat director aim at. Feet are planted by IK too, so a figure
// never slides or hovers while it fights.
//
// Body: shoulder placement, chest twist, the collarbone and far-arm layering come from
// rig-body.js (a three-quarter-front view: the arm roots sit inside the chest, not on
// its edges). Hand targets and elbow sides are pose data; the sheet tool is
// tools/rig-sheet.cjs.
//
// Presentation only: this draws outcomes the host has already resolved.

import {SkeletalRig} from './skeletal-rig.js';
import {ELEMENT_OF_DAMAGE, MotionTracker, PaintQueue, ParticlePool, Spring, Trail, clamp, ease, farPalette, glowGradient, lerp} from './actor-core.js';
import {ELEMENT_COLOUR, actorLook} from './actor-look.js';
import {VIEW, clavicle, elevationOf, farArmFront, shoulderSpread, turnOf} from './rig-body.js';
import * as PART from './hero-parts.js';

const SOLE = 6, HAND_REACH = 2.3;

// ---------------------------------------------------------------------------
// Proportions. The baseline is the shared 5'8" (97-unit) puppet: sole 6,
// thigh 23.3, shin 23 (hips at 54% of stature), spine 10.7, torso 15, neck 5,
// head 13.5. Race, gender
// and build reshape it; the head keeps its own scale so goblins read by it.
function dimsOf(look) {
  const b = look.body, kh = b.head, headTop = PART.HEAD_TOP * kh;
  const below = b.heightUnits - headTop, k = below / 83.5;
  const legShare = 52.3 * b.leg, kl = k * b.leg, kt = k * (83.5 - legShare) / 31.2;
  const W = b.width, d = {k, kl, kt, kh, W, headTop,
    sole: SOLE * kl, thigh: 23.3 * kl, shin: 23 * kl, spine: 10.7 * kt, torso: 15 * kt, neck: 5 * kt,
    upper: 17 * k, lower: 15 * k, sx: 9.6 * W * b.shoulders, hx: 5.8 * W * b.hips,
    ws: .45 + .55 * Math.min(1.15, k)};
  d.waist = d.spine + d.torso;
  d.spec = {
    pelvis: {x: 0, y: -(d.sole + d.thigh + d.shin)}, spine: {y: -d.spine}, torso: {y: -d.torso}, neck: {y: -d.neck}, head: {x: 0, y: -.5},
    left_shoulder: {x: -d.sx, y: 1}, right_shoulder: {x: d.sx, y: 1},
    left_upper_arm: {length: d.upper, angle: .1}, right_upper_arm: {length: d.upper, angle: -.06},
    left_lower_arm: {length: d.lower, angle: -.05}, right_lower_arm: {length: d.lower, angle: -.1},
    left_hip: {x: -d.hx, y: 0}, right_hip: {x: d.hx, y: 0},
    left_thigh: {length: d.thigh, angle: .03}, right_thigh: {length: d.thigh, angle: -.03},
    left_shin: {length: d.shin, angle: 0}, right_shin: {length: d.shin, angle: 0},
  };
  return d;
}

// ---------------------------------------------------------------------------
// Poses. Channels are plain numbers so any two poses blend:
//   py px pa   pelvis drop / forward shift (units) / roll (lying)
//   sp to hd   spine / torso / head lean (+ forward)
//   lf rf      far / near foot x from the pelvis, planted on the floor by IK
//   ll rl      far / near foot lift (units)
//   hx hy      near (weapon) hand target, measured from its own shoulder at the
//   ox oy      bind pose (rig-body.js), and the far hand likewise; both in arm
//              units (arm = 32). Hands blend on an arc about the shoulder.
//   eb ob      near / far elbow side (+1 elbow below the shoulder-to-hand line, -1
//              above it; for a hand held forward that is down/back vs up/out). The
//              arm blends through straight between the two, so it never flips
//   tw         chest twist added to the view's yaw (rig-body.js): + opens the chest
//              toward the camera (wind-up, cheer), - turns it into the target (strike)
//   af         far arm in front of the torso (0..1): crossed arms, a raised guard
//   wa         weapon angle: 0 points up, + tips it forward, pi points down
//   oa         off-hand item tilt   two  far hand on the weapon (0..1)
//   open       far palm open (wards, spells)   draw  bowstring drawn (0..1)
//   sheath     weapon stowed (0..1): the hand fetches it from the hilt
//   lt ls rt rs nu nl fu fl   limb angles used only while lying (air)
//   air        lying on the floor
const BASE = {py: 0, px: 0, pa: 0, sp: .03, to: 0, hd: 0, lf: -5, rf: 5.5, ll: 0, rl: 0,
  hx: 1.5, hy: 30, ox: 0, oy: 30, eb: 1, ob: 1, tw: 0, af: 0, wa: 2.9, oa: 0, two: 0, open: 0, draw: 0, sheath: 0,
  lt: 0, ls: 0, rt: 0, rs: 0, nu: 0, nl: 0, fu: 0, fl: 0, air: 0};
const CHANNELS = Object.keys(BASE);

// The far arm hangs behind the torso in this three-quarter view, so a far hand
// reads only when it is held forward past the chest (ox >= ~8), back behind the
// body (ox <= ~-14), or brought across the chest with `af`. Nothing else parks
// it where the chest would hide it. Twist (`tw`): a reaching near arm wants the
// chest turned into the target (-), a reaching far arm wants it opened (+).
const COMMON = {
  rest: {sheath: 1, ox: -3, oy: 30},
  look: {sheath: 1, hd: -.16, to: -.03, ox: -3, oy: 30},
  point: {sheath: 1, ox: 30, oy: 1, hd: -.05, to: .04, tw: .15},
  wave: {sheath: 1, hx: 15, hy: -22, eb: 1, ox: -3, oy: 30, tw: -.4},
  cheer: {sheath: 1, hx: 2.6, hy: -23, ox: 7.4, oy: -23, eb: -1, ob: -1, sp: -.08, hd: -.18, tw: .2},
  crossed: {sheath: 1, hx: 13, hy: 9, eb: 1, ox: -9, oy: 11, ob: -1, af: 1, hd: .04},
  salute: {sheath: 1, hx: 23.2, hy: -12, eb: -1, hd: -.04, ox: -3, oy: 30, tw: -.3},
  study: {sheath: 1, hx: 23.2, hy: -1, eb: 1, hd: .16, sp: .06, ox: 8.8, oy: 12, tw: -.2},
  jump: {ll: 11, rl: 15, lf: -4, rf: 6, sp: .12, hx: 26.2, hy: 6, ox: -18, oy: 4, ob: -1, tw: -.3},
  climb: {sheath: 1, hx: 20.2, hy: -26, ox: -11.2, oy: -22, eb: -1, ob: -1, ll: 8, rl: 2, lf: -2, rf: 4},
  down: {air: 1, pa: -1.48, lt: -.1, ls: .35, rt: .15, rs: .5, nu: .25, nl: .1, fu: .35, fl: .1, hd: .25, wa: 1.6},
  kneel: {py: 17, lf: -13, rf: 9, sp: .3, hd: .22, hx: 24, hy: 27, wa: 3.05, ox: -1, oy: 25, tw: -.6},
  victory: {hx: 27.2, hy: -21, eb: -1, wa: -.08, ox: -13, oy: 12, sp: -.1, hd: -.2, tw: -.3},
};
// Per weapon family. `guard` is the fighting stance every reaction layers on.
const FAMILY = {
  blade: {
    guard: {py: 2.4, lf: -8, rf: 7, sp: .1, to: .03, hd: -.05, hx: 25, hy: 10, wa: .55, ox: -19, oy: 3, ob: -1, tw: -.4},
    windup: {py: 3.2, lf: -9, rf: 6.5, sp: -.14, to: -.12, hd: .04, hx: 6, hy: -22, eb: -1, wa: -1.3, ox: 8.8, oy: 9, ob: 1, tw: .4},
    strike: {py: 5, lf: -11, rf: 13, sp: .34, to: .12, hd: .06, hx: 37.5, hy: 17, wa: 1.95, ox: -12, oy: 14, tw: -1},
    follow: {py: 5.4, lf: -11, rf: 13, sp: .4, to: .14, hd: .08, hx: 31.2, hy: 27, wa: 2.75, ox: -13, oy: 12, tw: -.9},
    block: {py: 3, lf: -9, rf: 6.5, sp: .12, hx: 30, hy: 6, wa: -.18, ox: 7.8, oy: 9, ob: 1, tw: -.3},
  },
  heavy: {
    guard: {py: 3.5, lf: -8, rf: 7, sp: .12, hx: 27.2, hy: 18, wa: .42, two: 1, tw: 0},
    windup: {py: 3, lf: -8, rf: 6.5, sp: -.16, to: -.08, hd: .02, hx: 18.2, hy: -12, eb: -1, wa: -.95, two: 1, tw: 0},
    strike: {py: 6, lf: -11, rf: 13, sp: .38, to: .14, hx: 30, hy: 22, wa: 2.15, two: 1, tw: -1},
    follow: {py: 6.5, lf: -11, rf: 13, sp: .44, to: .16, hx: 25, hy: 30, wa: 2.85, two: 1, tw: -.9},
    block: {py: 4, lf: -8, rf: 6.5, sp: .1, hx: 26.2, hy: 4, eb: -1, wa: -1.35, two: 1, tw: 0},
    victory: {hx: 27.2, hy: -22, eb: -1, wa: -.05, two: 1, sp: -.1, hd: -.2},
  },
  dagger: {
    guard: {py: 3, lf: -8, rf: 8, sp: .14, hx: 26.2, hy: 16, wa: 1.2, ox: 7.8, oy: 9, tw: -.3},
    windup: {py: 3.6, lf: -8, rf: 8, sp: .02, hx: 15.2, hy: 16, wa: 1.45, ox: 9.8, oy: 7, tw: .1},
    strike: {py: 5, lf: -11, rf: 14, sp: .36, to: .1, hx: 37, hy: 10, wa: 1.57, ox: -12, oy: 14, tw: -1},
    follow: {py: 5, lf: -11, rf: 14, sp: .32, hx: 32, hy: 14, wa: 1.75, ox: -13, oy: 13, tw: -.9},
    block: {py: 4, lf: -9, rf: 6.5, sp: .1, hx: 26.2, hy: 2, eb: -1, wa: -.5, ox: 7.8, oy: 8, tw: -.2},
  },
  polearm: {
    rest: {sheath: 0, hx: 19, hy: 25, wa: .03, ox: -3, oy: 30},
    look: {sheath: 0, hx: 19, hy: 25, wa: .03, hd: -.16, ox: -3, oy: 30},
    staffLow: {sheath: 0, hx: 15, hy: 27, wa: 2.75, ox: -3, oy: 30, tw: -.2},
    staffPoint: {sheath: 0, hx: 29, hy: 13, wa: 1.3, two: 1, ox: -3, oy: 30, tw: -.3},
    guard: {py: 3.5, lf: -9, rf: 8, sp: .14, hx: 23.2, hy: 17, wa: 1.18, two: 1, tw: 0},
    windup: {py: 3.6, lf: -9, rf: 7, sp: 0, hx: 11.2, hy: 17, wa: 1.33, two: 1, tw: 0},
    strike: {py: 6, lf: -11, rf: 14, sp: .38, to: .1, hx: 33, hy: 12, wa: 1.5, two: 1, tw: -1},
    follow: {py: 6, lf: -11, rf: 14, sp: .34, hx: 29, hy: 15, wa: 1.55, two: 1, tw: -.9},
    block: {py: 4, lf: -8, rf: 6.5, hx: 19, hy: 4, wa: -.2, two: 1, tw: .2},
    victory: {hx: 21.2, hy: -14, eb: -1, wa: .02, ox: -21.2, oy: 17, sp: -.1, hd: -.2},
    kneel: {py: 17, lf: -13, rf: 9, sp: .3, hd: .22, hx: 26.2, hy: 10, wa: .1, ox: -1, oy: 25},
  },
  staff: {
    rest: {sheath: 0, hx: 19, hy: 25, wa: .03, ox: -3, oy: 30},
    look: {sheath: 0, hx: 19, hy: 25, wa: .03, hd: -.16, ox: -3, oy: 30},
    staffLow: {sheath: 0, hx: 15, hy: 27, wa: 2.75, ox: -3, oy: 30, tw: -.2},
    staffPoint: {sheath: 0, hx: 29, hy: 13, wa: 1.3, two: 1, ox: 8.8, oy: 9, open: 1, tw: -.3},
    guard: {py: 3, lf: -8, rf: 7, sp: .08, hx: 27.2, hy: 13, wa: .38, ox: 8.8, oy: 9, open: 1, tw: -.1},
    windup: {py: 3, lf: -8, rf: 6.5, sp: -.14, hx: 16.2, hy: -8, eb: -1, wa: -1.1, two: .9, tw: 0},
    strike: {py: 5, lf: -11, rf: 12, sp: .34, hx: 31, hy: 20, wa: 2.1, two: .9, tw: -1},
    follow: {py: 5.4, lf: -11, rf: 12, sp: .4, hx: 26, hy: 28, wa: 2.7, two: .9, tw: -.9},
    block: {py: 3.6, lf: -8, rf: 6.5, hx: 19, hy: 4, eb: -1, wa: -1.4, two: 1, tw: .2},
    victory: {hx: 27.2, hy: -21, eb: -1, wa: .02, ox: -21.2, oy: 17, sp: -.1, hd: -.2},
    kneel: {py: 17, lf: -13, rf: 9, sp: .3, hd: .22, hx: 24.2, hy: 6, wa: .05, ox: -1, oy: 24},
  },
  wand: {
    staffLow: {sheath: 0, hx: 15, hy: 27, wa: 2.55, ox: -3, oy: 30},
    staffPoint: {sheath: 0, hx: 30, hy: 8, wa: 1.4, ox: 8.8, oy: 9, open: 1, tw: -.3},
    guard: {py: 2.5, lf: -8, rf: 7, sp: .08, hx: 29.2, hy: 12, wa: .95, ox: 7.8, oy: 13, open: 1, tw: -.3},
    windup: {py: 2.8, lf: -8, rf: 6.5, hx: 20.2, hy: 2, eb: -1, wa: -.3, sp: -.06, ox: 7.8, oy: 13, tw: .1},
    strike: {py: 4, lf: -9, rf: 11, sp: .26, hx: 36, hy: 6, wa: 1.45, ox: -12, oy: 14, tw: -1},
    follow: {py: 4, lf: -9, rf: 11, sp: .24, hx: 32, hy: 9, wa: 1.6, ox: -13, oy: 13, tw: -.9},
    block: {py: 3, lf: -8, rf: 6.5, hx: 27.2, hy: 6, wa: .4, ox: 10.8, oy: 3, open: 1, tw: -.2},
  },
  bow: {
    guard: {py: 3, lf: -9, rf: 8, sp: .04, to: -.02, ox: 7.8, oy: 11, oa: .06, hx: 26.2, hy: 14},
    windup: {py: 3.6, lf: -10, rf: 8, sp: -.02, to: -.05, hd: -.02, ox: 13.8, oy: 3, oa: .02, hx: 11.2, hy: -1, eb: -1, draw: 1, tw: .25},
    strike: {py: 3.6, lf: -10, rf: 8, sp: -.02, ox: 13.8, oy: 3, oa: .02, hx: 5.2, hy: 3, eb: -1, tw: .2},
    follow: {py: 3.4, lf: -10, rf: 8, ox: 12.8, oy: 5, oa: .04, hx: 8.2, hy: 9, tw: .15},
    block: {py: 3.5, lf: -8, rf: 6.5, ox: 7.8, oy: 4, oa: -.3, hx: 24.2, hy: 12},
    victory: {ox: -8.2, oy: -22, ob: -1, oa: .1, hx: 18.2, hy: 22, sp: -.1, hd: -.2},
  },
  unarmed: {
    guard: {py: 3, lf: -8, rf: 7, sp: .12, hx: 26.2, hy: 8, eb: -1, ox: 8.8, oy: 7, tw: -.3},
    windup: {py: 3, lf: -8, rf: 7, hx: 17.2, hy: 12, sp: -.06, ox: 9.8, oy: 6, tw: .2},
    strike: {py: 4.5, lf: -9, rf: 12, sp: .3, hx: 36, hy: 3, ox: -12, oy: 12, tw: -1},
    follow: {py: 4.5, lf: -9, rf: 12, sp: .26, hx: 32, hy: 8, ox: -13, oy: 12, tw: -.9},
    block: {py: 3.5, lf: -8, rf: 6.5, hx: 27.2, hy: 2, eb: -1, ox: 8.8, oy: 1, ob: -1, tw: -.2},
  },
};
// A held shield or tome sits forward on the far arm, past the chest.
const OFFHAND = {
  'kite-shield': {guard: {ox: 7.8, oy: 9, ob: 1}, windup: {ox: 8.8, oy: 9, ob: 1}, strike: {ox: 2.8, oy: 14, ob: 1}, follow: {ox: 2.8, oy: 14, ob: 1}, block: {ox: 10.8, oy: 2, oa: -.1, ob: 1}},
  buckler: {guard: {ox: 7.8, oy: 10, ob: 1}, windup: {ox: 8.8, oy: 9, ob: 1}, block: {ox: 11.8, oy: 3, ob: 1}},
  tome: {guard: {ox: 7.8, oy: 13, ob: 1}},
  lantern: {guard: {ox: 7.8, oy: 16, ob: 1}, rest: {ox: -3, oy: 29}},
};
// Gestures while a staff or spear stays upright in the near hand: the far
// hand waves, and celebrations lift the weapon.
const CARRIED_GESTURES = {
  wave: {ox: -2.2, oy: -20, ob: -1},
  cheer: {hx: 23, hy: -21, eb: -1, wa: .02, ox: -5.2, oy: -23, ob: -1},
  climb: {ox: -11.2, oy: -22, ob: -1},
  jump: {hx: 26.2, hy: 12, wa: .35},
  salute: {ox: 8.8, oy: -6, ob: -1},
  point: {tw: .1},
};
// Reactions layer onto the current stance as offsets.
const REACT = {
  hit: {sp: -.28, to: -.1, hd: -.34, px: -3.5, py: 1.5, lf: -3, hx: -4, hy: 3, oy: 6, wa: .25},
  crit: {sp: -.46, to: -.14, hd: -.46, px: -7, py: 6, lf: -6, hx: -9, hy: 6, oy: 8, wa: .45},
  dodge: {sp: -.34, hd: -.12, px: -10, py: 7, lf: -8, rf: -4, hx: -4},
};
// Casting stances (magic-articulation.js castingProfile): far-hand and
// near-hand targets for the channel and the release.
const CAST = {
  aim: {channel: {ox: 8.8, oy: 6, open: 1, ob: 1, sp: .06, hd: -.02}, release: {ox: 14.8, oy: 2, open: 1, ob: 1, sp: .16, rf: 11}},
  gather: {channel: {hx: 31.2, hy: 12, ox: 10.8, oy: 11, open: 1, ob: 1, sp: -.02}, release: {hx: 42.2, hy: 7, ox: 15.8, oy: 5, open: 1, ob: 1, sp: .18, rf: 11}},
  overhead: {channel: {hx: 27.2, hy: -21, ox: -2.2, oy: -22, eb: -1, ob: -1, open: 1, sp: -.12, hd: -.2}, release: {hx: 36.2, hy: -8, ox: 8.8, oy: -10, eb: -1, ob: -1, open: 1, sp: .2}},
  ward: {channel: {ox: 9.8, oy: 0, open: 1, ob: 1, sp: .04}, release: {ox: 13.8, oy: -2, open: 1, ob: 1, sp: .12, rf: 10}},
  mend: {channel: {hx: 31.2, hy: 21, ox: 9.8, oy: 20, open: 1, ob: 1, sp: .12, hd: .12}, release: {hx: 33.2, hy: 12, ox: 10.8, oy: 10, open: 1, ob: 1, sp: .04, hd: -.08}},
};
const IMPLEMENT = {
  staff: {channel: {hx: 26.2, hy: 0, wa: .22, eb: 1}, release: {hx: 33, hy: 6, wa: 1.0}},
  wand: {channel: {hx: 28.2, hy: 8, wa: .6}, release: {hx: 34, hy: 5, wa: 1.45}},
};

// Extension points. A new weapon family, cast stance or gesture is data: add
// it here (or register it from another module) and every hero figure can use
// it. See web/ACTOR_SYSTEM.md for recipes.
export const HERO_POSES = Object.freeze({COMMON, FAMILY, OFFHAND, CARRIED_GESTURES, REACT, CAST, IMPLEMENT});
export function registerPoseFamily(name, poses) { FAMILY[name] = {...(FAMILY[name] || {}), ...poses}; tables.clear(); }
export function registerGesture(name, pose) { COMMON[name] = {...pose}; tables.clear(); }
export function registerCastStance(name, {channel, release}) { CAST[name] = {channel: {...channel}, release: {...release}}; tables.clear(); }

const tables = new Map();
function poseTable(look) {
  const key = `${look.main.profile}|${look.offStowed ? 'none' : look.offhand}`;
  let table = tables.get(key);
  if (table) return table;
  const family = FAMILY[look.main.profile] || FAMILY.unarmed, off = look.offStowed ? {} : (OFFHAND[look.offhand] || {});
  // Carried weapons keep their own grip and angle through common gestures.
  const carried = family.rest && family.rest.sheath === 0 ? family.rest : null;
  table = {};
  for (const name of new Set([...Object.keys(COMMON), ...Object.keys(family), 'guard', 'ready'])) {
    let src = family[name] || COMMON[name] || family.guard;
    if (carried && !family[name] && COMMON[name] && name !== 'down') {
      src = {...src, sheath: 0, hx: carried.hx, hy: carried.hy, wa: carried.wa, eb: 1, ...(CARRIED_GESTURES[name] || {})};
    }
    table[name] = Object.freeze({...BASE, ...src, ...(off[name] || (name === 'ready' ? off.guard : {}) || {})});
  }
  table.ready = Object.freeze({...table.guard, sp: table.guard.sp + .06, py: table.guard.py + .6, hx: table.guard.hx + 1.5});
  table.hit = Object.freeze(offset(table.guard, REACT.hit));
  table.crit = Object.freeze(offset(table.guard, REACT.crit));
  table.dodge = Object.freeze(offset(table.guard, REACT.dodge));
  tables.set(key, table);
  return table;
}
// A hand travels on an arc about its shoulder, not a straight line through the body: each
// hand target blends as (angle, reach), the shorter way round, so a swing from overhead to
// the front sweeps down the arm's side instead of cutting past the shoulder.
const ARM_PAIRS = [['hx', 'hy'], ['ox', 'oy']], ARM_KEYS = new Set(ARM_PAIRS.flat());
function blendHand(ch, target, kx, ky, k) {
  const r0 = Math.hypot(ch[kx], ch[ky]), r1 = Math.hypot(target[kx], target[ky]);
  if (r0 < 4 || r1 < 4 || k >= 1) { ch[kx] += (target[kx] - ch[kx]) * k; ch[ky] += (target[ky] - ch[ky]) * k; return; }
  const a0 = Math.atan2(ch[kx], ch[ky]);
  let da = Math.atan2(target[kx], target[ky]) - a0; da -= Math.round(da / (Math.PI * 2)) * Math.PI * 2;
  const a = a0 + da * k, r = r0 + (r1 - r0) * k;
  ch[kx] = Math.sin(a) * r; ch[ky] = Math.cos(a) * r;
}
function offset(base, delta) { const out = {...base}; for (const [k, v] of Object.entries(delta)) out[k] = (out[k] || 0) + v; return out; }

// ---------------------------------------------------------------------------
// State kept on the rig between frames.
function stateOf(rig) {
  if (!rig.hero) rig.hero = {ch: {...BASE, sheath: 1}, beat: '', beatAt: 0, contactAt: -1, lastContact: -1, pose: '', poseAt: 0,
    fidget: null, fidgetAt: 0, blinkAt: 0, blinkUntil: 0, look: null, lookFor: null, loco: 0,
    cloak: new Spring(0, 55), hair: new Spring(0, 70), lantern: new Spring(0, 40), trail: new Trail(14), particles: new ParticlePool(80),
    queue: new PaintQueue(), emit: 0};
  if (!rig.motion) rig.motion = new MotionTracker();
  return rig.hero;
}
function lookOf(st, model) {
  if (st.lookFor !== model) {
    st.look = actorLook(model); st.lookFor = model;
    st.look.dims = dimsOf(st.look); st.look.far = farPalette(st.look.palette);
  }
  return st.look;
}

// Poses that are themselves one-shot actions. 'guard' is NOT one: poseFor()
// names the resting combat stance 'guard'; only the director's guard BEAT is a block.
const ACTION_CUES = new Set(['windup', 'strike', 'cast', 'cast_channel', 'cast_release', 'hit', 'crit', 'impact', 'attack', 'dodge', 'miss']);
const LOCOMOTION = new Set(['run', 'move', 'advance', 'retreat']);
const AIR = new Set(['jump', 'fall', 'airborne', 'fly', 'flight']);
const FIDGETS = ['look', 'crossed', 'study', 'look', 'point'];

// Which pose the figure reaches for this frame, and how fast (tau, ms).
function resolveTarget(st, look, {pose, beat, now, reduced, alive, idleFidgets}) {
  if (!alive || pose === 'down' || pose === 'ko') return {key: 'down', tau: 190};
  if (pose !== st.pose) { st.pose = pose; st.poseAt = now; }
  if (pose === 'death') {
    const age = now - st.poseAt;
    return age < 200 ? {key: 'crit', tau: 30} : age < 430 ? {key: 'kneel', tau: 80} : {key: 'down', tau: 150};
  }
  const cue = beat || (ACTION_CUES.has(pose) ? pose : '');
  if (cue !== st.beat) { st.beat = cue; st.beatAt = now; }
  const age = now - st.beatAt;
  if (cue === 'windup') return {key: 'windup', tau: 70};
  if (cue === 'strike') return age < 110 ? {key: 'strike', tau: reduced ? 0 : 24, contact: age >= 40, swing: true} : {key: 'follow', tau: 90, contact: true, swing: age < 240};
  if (cue === 'attack') {                          // preview and arcade loop
    const t = age % 1300;
    return t < 380 ? {key: 'windup', tau: 80} : t < 520 ? {key: 'strike', tau: 24, swing: true} : t < 900 ? {key: 'follow', tau: 90, swing: t < 640} : {key: 'guard', tau: 160};
  }
  if (cue === 'cast' && !beat) {                   // creator preview loop: gather, then loose
    const t = age % 1500;
    return t < 700 ? {key: 'channel', tau: 90} : t < 1000 ? {key: 'release', tau: 40} : {key: 'guard', tau: 180};
  }
  if (cue === 'cast' || cue === 'cast_channel') return {key: 'channel', tau: 90};
  if (cue === 'cast_release') return {key: 'release', tau: reduced ? 0 : 40, contact: true};
  if (cue === 'hit' || cue === 'impact') return {key: 'hit', tau: 30};
  if (cue === 'crit') return {key: 'crit', tau: 26};
  if (cue === 'dodge' || cue === 'miss') return {key: 'dodge', tau: 50};
  if (beat === 'guard' || beat === 'block' || pose === 'defend' || pose === 'block') return {key: 'block', tau: 60};
  if (cue === 'move' || LOCOMOTION.has(pose)) return {key: 'run', tau: 110};
  if (pose === 'travel') return {key: 'walk', tau: 140};
  if (cue.startsWith('gesture:') && COMMON[cue.slice(8)]) return {key: cue.slice(8), tau: 120};
  if (AIR.has(pose)) return {key: 'jump', tau: 90};
  if (pose === 'climb' || pose === 'vault') return {key: 'climb', tau: 110};
  if (pose === 'victory' || pose === 'cheer') return {key: pose, tau: 140};
  if (pose === 'kneel') return {key: 'kneel', tau: 180};
  if (pose === 'ready') return {key: 'ready', tau: 140};
  if (['staffLow', 'staffPoint'].includes(pose) && FAMILY[look.main.profile]?.[pose]) return {key: pose, tau: 120};
  if (['combat', 'guard', 'battleIdle'].includes(pose)) return {key: 'guard', tau: 150};
  if (COMMON[pose] && pose !== 'rest') return {key: pose, tau: 130};
  if (idleFidgets && !reduced) {
    if (!st.fidgetAt) st.fidgetAt = now + 6000 + (look.seed % 6000);
    if (st.fidget && now > st.fidgetAt + 2600) { st.fidget = null; st.fidgetAt = now + 8000 + ((look.seed >>> 4) % 7000); }
    else if (!st.fidget && now > st.fidgetAt) { st.fidget = FIDGETS[(look.seed + Math.floor(now / 997)) % FIDGETS.length]; st.fidgetAt = now; }
    if (st.fidget) return {key: st.fidget, tau: 220};
  }
  return {key: 'rest', tau: 200};
}

function targetFor(key, look, table, {now, reduced, casting}) {
  let t;
  if (key === 'channel' || key === 'release') {
    const stance = CAST[casting?.stance] ? casting.stance : 'aim', hands = casting?.hands === 2 ? 2 : 1;
    const implement = ['staff', 'wand'].includes(look.main.kind) && casting?.source !== 'hands';
    t = {...table.guard, ...CAST[stance][key]};
    if (implement) Object.assign(t, IMPLEMENT[look.main.kind][key], hands === 2 && look.main.kind === 'staff' ? {} : {});
    else if (look.main.kind !== 'none' && look.main.kind !== 'bow') {
      // A drawn blade stays lowered while the free hand casts; a two-handed
      // cast puts it away.
      if (hands === 2) t.sheath = 1;
      else Object.assign(t, {hx: 6, hy: 24, wa: 2.5, eb: 1});
    }
    if (look.main.kind === 'bow') Object.assign(t, {sheath: 1});
  } else if (key === 'run' || key === 'walk') {
    t = {...(key === 'walk' ? table.rest : table.guard)};
    if (key === 'run' && !t.two) Object.assign(t, {ox: -2, oy: 17, ob: 1, af: 0, open: 0});
  } else t = {...(table[key] || table.rest)};
  if (!reduced && t.air < .5) {                    // breath
    t.py += Math.sin(now * .0019) * .35; t.sp += Math.sin(now * .0019) * .008;
  }
  return t;
}

// Procedural stride laid over the lower body while moving.
function stride(ch, st, now, key, blend) {
  if (blend <= .001) return;
  const run = key === 'run', ph = st.phase ?? now * (run ? .0132 : .0082), s = Math.sin(ph), c = Math.cos(ph), a = (run ? 1 : .7) * blend;
  ch.lf = lerp(ch.lf, -1.5 + s * 10 * a / blend * (run ? 1 : .8), blend);
  ch.rf = lerp(ch.rf, 1.5 - s * 10 * a / blend * (run ? 1 : .8), blend);
  ch.ll = lerp(ch.ll, Math.max(0, c) * (run ? 7 : 4), blend);
  ch.rl = lerp(ch.rl, Math.max(0, -c) * (run ? 7 : 4), blend);
  ch.py += (run ? 2.4 : .8) * blend;
  ch.sp += (run ? .16 : .05) * blend;
  if (ch.sheath > .5 || key === 'walk') { ch.hx += -s * 6 * a; ch.ox += s * 6 * a; }
}

// ---------------------------------------------------------------------------
// Frame helpers (shared shape with the champion rigs).
function frame(ctx, rig, wx, wy, angle, paint, scale = 1) {
  ctx.save(); ctx.translate(wx, wy); ctx.scale(rig.facing * rig.scale * scale, rig.scale * scale); ctx.rotate(angle);
  paint(ctx); ctx.restore();
}
const worldOf = (rig, lx, ly) => [rig.rootX + lx * rig.facing, rig.rootY + ly];
function toLocal(rig, ox, oy, angle, px, py) {
  const s = rig.scale;
  return [ox + (px * Math.cos(angle) - py * Math.sin(angle)) * s, oy + (px * Math.sin(angle) + py * Math.cos(angle)) * s];
}
const dirOf = angle => [-Math.sin(angle), Math.cos(angle)];
// Weapon axis in the pre-mirror frame: local -y is the business end.
const tipDir = angle => [Math.sin(angle), -Math.cos(angle)];

function moodOf(key, look) {
  if (key === 'hit' || key === 'crit') return 'pain';
  if (key === 'strike' || key === 'release') return 'shout';
  if (key === 'windup' || key === 'channel' || key === 'guard' || key === 'block' || key === 'ready' || key === 'follow') return 'focused';
  if (key === 'victory' || key === 'cheer') return 'cheer';
  if (key === 'down') return 'fallen';
  return look.expression === 'strained' ? 'strained' : look.expression === 'fallen' ? 'fallen' : 'alert';
}

// ---------------------------------------------------------------------------
// Public: draw a hero on `rig` (a SkeletalRig whose scale is already set).
//   x, y        canvas point of the FLOOR under the figure; facing 1 = right
//   pose, beat  poseFor() output and the combat director's live beat
//   paint       false: pose and measure only (sockets for the FX engine)
//   screenX/Y   where the figure box sits on screen (px), for motion and cloth
//   screenFacing  facing as the viewer sees it (a CSS-mirrored figure flips it)
// Returns world sockets {head, chest, main_hand, off_hand, ground, weapon_main,
// weapon_tip, shield, focus, crown}.
export function drawHero(ctx, rig, model = {}, {
  x = 0, y = 0, facing = 1, dt = 16, now = performance.now(), pose = 'idle', beat = '', paint = true,
  reducedMotion = false, shadow = true, idleFidgets = true, weapons = true, casting = null, screenX = null, screenY = null, screenFacing = null, gait = 0,
  turnProgress = 0,
} = {}) {
  const st = stateOf(rig), look = lookOf(st, model), d = look.dims, reduced = Boolean(reducedMotion);
  rig.reshape(look.key, d.spec);
  const table = poseTable(look);
  const want = resolveTarget(st, look, {pose, beat, now, reduced, alive: model.alive !== false, idleFidgets});
  const target = targetFor(want.key, look, table, {now, reduced, casting});
  // State advances on any real frame; socket measurement passes dt 0.
  const ch = st.ch, live = dt > 0;
  // Hitstop: a crit, a hit, or the frame a strike lands freezes the pose
  // briefly so the blow reads; then the blend resumes where it was.
  if (live && want.key !== st.lastKey) {
    const hold = want.key === 'crit' ? 90 : want.key === 'hit' ? 45 : 0;
    if (hold && !reduced) st.holdUntil = now + hold;
    st.lastKey = want.key;
  }
  if (live && want.contact && st.contactAt !== st.beatAt && !reduced && want.key === 'strike') st.holdUntil = now + 55;
  const holding = now < (st.holdUntil || 0);
  const k = reduced || !Number.isFinite(dt) ? 1 : holding ? 0 : ease(dt, want.tau);
  for (const key of CHANNELS) if (!ARM_KEYS.has(key)) ch[key] += (target[key] - ch[key]) * k;
  for (const [kx, ky] of ARM_PAIRS) blendHand(ch, target, kx, ky, k);
  // Sheathing reads better unhurried; drawing a weapon for a fight is quick.
  if (!reduced) ch.sheath += (target.sheath - ch.sheath) * (ease(dt, target.sheath > ch.sheath ? 200 : 90) - k);
  const moving = want.key === 'run' || want.key === 'walk';
  if (live) st.loco += ((moving ? 1 : 0) - st.loco) * ease(dt, 120);
  const loco = reduced ? 0 : (live ? st.loco : moving ? 1 : 0);
  // The stride clock runs on distance, not time: gait is stride cycles per second.
  if (st.phase == null) st.phase = 0;
  if (dt > 0) st.phase += (gait > 0 ? Math.PI * 2 * gait / 1000 : want.key === 'walk' ? .0082 : .0132) * dt;
  const pose2 = {...ch}; stride(pose2, st, now, want.key === 'walk' || (gait > 0 && gait < .95) ? 'walk' : 'run', loco);   // a slow cadence reads as a walk
  if (want.contact && st.contactAt !== st.beatAt) st.contactAt = st.beatAt;
  if (live && Number.isFinite(screenX)) rig.motion.track(screenX, screenY, dt);
  // On-screen facing: an opponent mirrored by CSS walks forward to the left.
  const lean = reduced ? 0 : (live ? rig.motion.lean(screenFacing ?? facing, dt) : rig.motion.sway.value);

  // --- pose the skeleton ------------------------------------------------------
  const R = rig.bones, bone = n => R.get(n), set = (n, a) => { const b = bone(n); b.localAngle = b.restAngle + a; };
  const c = pose2;
  // Bind pose: the shoulders sit inside the chest for the view's yaw (rig-body.js);
  // this pose's chest twist then slides them (near shoulder back, far forward, as it opens).
  const theta = turnOf(c.tw);
  for (const side of ['left', 'right']) bone(side + '_shoulder').restX = shoulderSpread(side, d.sx, VIEW.yaw);
  // 'hero' keeps SkeletalRig.update() out of its built-in staff and bow grip
  // IK; this rig places both hands itself.
  rig.resetPose(); rig.pose = want.key; rig.weapon = 'hero';
  for (const side of ['left', 'right']) bone(side + '_shoulder').localX = shoulderSpread(side, d.sx, theta);
  const s = rig.scale;
  bone('pelvis').localAngle = c.pa;
  set('spine', c.sp + lean * .1); set('torso', c.to); set('head', c.hd - lean * .05);
  bone('pelvis').localX += c.px;
  const standing = c.air < .5;
  if (standing) {
    bone('pelvis').localY += .5 + c.py * .75;
    rig.update(0, x, y, facing);
    // Drop the pelvis until both planted feet are reachable, then plant them.
    const L = (d.thigh + d.shin) * s * .994, pel = bone('pelvis');
    const feet = [['left', pel.x + c.lf * d.kl * s, -(d.sole + c.ll * d.kl) * s], ['right', pel.x + c.rf * d.kl * s, -(d.sole + c.rl * d.kl) * s]];
    let drop = 0;
    for (const [side, tx, ty] of feet) {
      const hip = bone(side + '_hip'), dx = tx - hip.x, reach = Math.sqrt(Math.max(0, L * L - dx * dx));
      drop = Math.max(drop, (ty - reach) - hip.y);
    }
    if (drop > 0) { bone('pelvis').localY += drop / s; rig.update(0, x, y, facing); }
    for (const [side, tx, ty] of feet) rig.plant(side, tx, ty, -1);
  } else {
    set('left_thigh', c.lt); set('left_shin', c.ls); set('right_thigh', c.rt); set('right_shin', c.rs);
    set('left_upper_arm', c.fu); set('left_lower_arm', c.fl); set('right_upper_arm', c.nu); set('right_lower_arm', c.nl);
    rig.update(0, x, y, facing);
    let lowest = -Infinity;
    for (const b of R.values()) if (b.name !== 'root' && !/weapon|shield|cape|hair|jaw|thumb|fingers|toe/.test(b.name)) lowest = Math.max(lowest, b.y, b.endY ?? b.y);
    bone('pelvis').localY -= (lowest + 2.2 * s) / s;
    rig.update(0, x, y, facing);
  }
  const pelvis = bone('pelvis'), torso = bone('torso'), headB = bone('head');
  // A staff or spear is sized to its bearer; blades keep a readable minimum.
  const main = look.main, ws = ['staff', 'polearm'].includes(main.kind) ? d.k : d.ws, geo = PART.weaponGeometry(main);
  const freeBothHands = casting?.source === 'hands' && casting.hands === 2 && ['channel', 'release'].includes(want.key);
  if (!['staff', 'polearm'].includes(main.kind)) st.focusStow = false;
  else if (freeBothHands) st.focusStow = true;
  else if (c.sheath < .02) st.focusStow = false;
  const handCentre = side => {
    const lower = bone(side + '_lower_arm'), hand = bone(side + '_hand'), [dx, dy] = dirOf(lower.angle);
    return [hand.x + dx * HAND_REACH * s * d.W, hand.y + dy * HAND_REACH * s * d.W];
  };
  // Where the stowed weapon's grip sits and which way it points.
  const stow = (() => {
    if (main.kind === 'none') return null;
    if (['staff', 'polearm'].includes(main.kind)) {
      if (!st.focusStow) return null;
      const [gx, gy] = toLocal(rig, torso.x, torso.y, torso.angle, -d.sx * .6, -5);
      return {x: gx, y: gy, angle: torso.angle + .35, back: true};
    }
    if (main.kind === 'bow' || main.profile === 'heavy') {   // across the back
      // Hilt up behind the back shoulder, blade diagonal behind the body.
      if (main.kind === 'bow') { const [gx, gy] = toLocal(rig, torso.x, torso.y, torso.angle, -2, d.waist * .4); return {x: gx, y: gy, angle: torso.angle + .35, back: true}; }
      const [gx, gy] = toLocal(rig, torso.x, torso.y, torso.angle, -d.sx * .6, -5);
      return {x: gx, y: gy, angle: torso.angle + 2.62, back: true};
    }
    if (main.kind === 'wand') { const [gx, gy] = toLocal(rig, pelvis.x, pelvis.y, pelvis.angle, d.hx * .8, 1); return {x: gx, y: gy, angle: pelvis.angle + 2.7}; }
    // Far-hip scabbard: blade points down and back, grip above the mouth.
    const sa = pelvis.angle + .28, [mx, my] = toLocal(rig, pelvis.x, pelvis.y, pelvis.angle, -d.hx - .6, -.6), [ax, ay] = dirOf(sa);
    return {x: mx - ax * 3.4 * ws * s, y: my - ay * 3.4 * ws * s, angle: sa + Math.PI, mouth: [mx, my], sa};
  })();
  const sheath = weapons && stow ? clamp(c.sheath, 0, 1) : 0;
  const fetch = 1 - Math.abs(2 * sheath - 1);           // 1 when the hand is at the hilt
  const ka = d.k * s;
  // Hand targets are measured from each shoulder's bind position (the view's yaw, no
  // twist). A twist or a lifting collarbone moves the arm root, never the hand.
  const anchorN = toLocal(rig, torso.x, torso.y, torso.angle, shoulderSpread('right', d.sx, VIEW.yaw), 1);
  const anchorF = toLocal(rig, torso.x, torso.y, torso.angle, shoulderSpread('left', d.sx, VIEW.yaw), 1);
  // One arm: the collarbone lifts and reaches with the arm, then the two-bone solve puts
  // the hand on its target. `bend` is continuous (-1..1), so a change of elbow side
  // passes through a straight arm instead of snapping to the other side.
  const reachArm = (side, tx, ty, bend) => {
    const sh = bone(side + '_shoulder'), lift = clavicle(elevationOf(tx - sh.x, ty - sh.y));
    sh.localX += lift.dx; sh.localY += lift.dy;
    sh.compute(torso.endX, torso.endY, torso.angle, 1, s); rig.refresh([sh]);
    rig.reach(side, tx, ty, bend);
    const upper = bone(side + '_upper_arm'), lower = bone(side + '_lower_arm'), hand = bone(side + '_hand');
    if (!st.reach) st.reach = {};
    st.reach[side === 'right' ? 'near' : 'far'] = {
      bend: +bend.toFixed(2), at: [+((tx - sh.endX) / s).toFixed(1), +((ty - sh.endY) / s).toFixed(1)],
      short: +Math.max(0, (Math.hypot(tx - sh.endX, ty - sh.endY) - (upper.length + lower.length) * s) / s).toFixed(1),
      err: +(Math.hypot(hand.x - tx, hand.y - ty) / s).toFixed(1)};
  };
  if (standing) {
    let hx = anchorN[0] + c.hx * ka, hy = anchorN[1] + c.hy * ka;
    if (stow && fetch > .02 && !stow.back) { hx = lerp(hx, stow.x, fetch); hy = lerp(hy, stow.y, fetch); }
    reachArm('right', hx, hy, c.eb);
  }
  const [gx, gy] = handCentre('right');
  const held = sheath < .5 || !stow;
  const wAngle = held ? (stow && !stow.back ? lerp(c.wa, stow.angle - 2 * Math.PI * Math.round((stow.angle - c.wa) / (2 * Math.PI)), fetch * .9) : c.wa) : stow.angle;
  const grip = held ? [gx, gy] : [stow.x, stow.y];
  if (standing) {
    let ox = anchorF[0] + c.ox * ka, oy = anchorF[1] + c.oy * ka;
    const two = held && main.kind !== 'bow' ? clamp(c.two, 0, 1) : 0;
    if (two > .01) {
      const [ux, uy] = tipDir(wAngle), g2 = geo.grip2 * ws * s;
      ox = lerp(ox, grip[0] - ux * g2, two); oy = lerp(oy, grip[1] - uy * g2, two);
    }
    reachArm('left', ox, oy, c.ob);
  }
  const [fx, fy] = handCentre('left');

  // --- sockets ----------------------------------------------------------------
  const tipAt = (() => {
    if (main.kind === 'bow') return [fx + 18 * ws * s, fy];
    const [ux, uy] = tipDir(wAngle); return [grip[0] + ux * geo.tip * ws * s, grip[1] + uy * geo.tip * ws * s];
  })();
  const faceAt = toLocal(rig, headB.x, headB.y, headB.angle, 2 * d.kh, -6.5 * d.kh);
  const crownAt = toLocal(rig, headB.x, headB.y, headB.angle * .4, .5 * d.kh, -d.headTop - 2);
  const chestAt = toLocal(rig, torso.x, torso.y, torso.angle, 0, d.waist * .35);
  const W = (lx, ly, rotation = 0) => { const [wx, wy] = worldOf(rig, lx, ly); return {x: wx, y: wy, rotation}; };
  const offItem = !look.offStowed && ['kite-shield', 'buckler', 'tome', 'lantern'].includes(look.offhand);
  const sockets = {
    head: W(...faceAt, headB.worldAngle), chest: W(...chestAt, torso.worldAngle),
    main_hand: W(gx, gy, wAngle * facing), off_hand: W(fx, fy, bone('left_lower_arm').worldAngle),
    ground: {x: rig.rootX, y: rig.rootY, rotation: 0}, crown: W(...crownAt),
  };
  sockets.weapon_main = main.kind === 'bow' ? sockets.off_hand : sockets.main_hand;
  sockets.weapon_tip = W(...tipAt, wAngle * facing);
  sockets.shield = offItem && ['kite-shield', 'buckler'].includes(look.offhand) ? sockets.off_hand : sockets.chest;
  // Spell focus: a staff or wand's head, the point between two casting
  // hands, or the open far palm.
  const implement = ['staff', 'wand'].includes(main.kind) && casting?.source !== 'hands';
  sockets.focus = implement ? sockets.weapon_tip : casting?.hands === 2 ? W((gx + fx) / 2, (gy + fy) / 2) : sockets.off_hand;
  if (!paint) return sockets;

  // --- secondary motion --------------------------------------------------------
  if (live) {
    const trailing = clamp(lean * .9 + c.sp * .5 + (moving ? .35 * loco : 0), -.3, 1.2);
    st.cloak.step(trailing, dt); st.hair.step(clamp(lean * .8 + c.sp * .6 + (moving ? .3 : 0), -.4, 1.1), dt);
    st.lantern.step(clamp(-lean * .6, -.6, .6), dt);
    if (now > st.blinkAt) { st.blinkUntil = now + 110; st.blinkAt = now + 2400 + ((look.seed >>> 3) % 2600) + Math.random() * 1400; }
  }
  const t = reduced ? 0 : now;
  const P = look.palette, F = look.far, Q = st.queue.reset();
  const onBone = (name, painter) => { const b = bone(name); return () => frame(ctx, rig, b.worldX, b.worldY, b.angle, painter); };

  if (shadow) Q.add(0, () => {
    const lift = standing ? clamp(Math.max(c.ll, c.rl) / 20, 0, .6) : 0;
    PART.shadow(ctx, rig.rootX + pelvis.x * facing * .4, rig.rootY + s * .6, (standing ? 15 + Math.abs(c.lf - c.rf) * .45 : 34) * s * d.W * (1 - lift * .3), 3.2 * s, .3 - lift * .1);
  });
  // An aura (a drowned foe's tide, a spirit's phase) glows behind the body
  // and sheds motes; it is presentation of what the look carries, nothing more.
  if (look.aura && !reduced) {
    const [ax, ay] = worldOf(rig, ...chestAt), colour = ELEMENT_COLOUR[look.aura], r = 30 * s * d.k;
    Q.add(1, () => { ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.translate(ax, ay); ctx.fillStyle = glowGradient(ctx, 30, colour, .26 + Math.sin(t * .003) * .06);
      ctx.scale(r / 30, r / 30 * 1.6); ctx.beginPath(); ctx.arc(0, 0, 30, 0, Math.PI * 2); ctx.fill(); ctx.restore(); });
    if (live && Math.random() < dt / 160) st.particles.emit(ax + (Math.random() - .5) * 20 * s, ay + (Math.random() - .3) * 40 * s, look.aura, 1, 2 * s, .8);
  }
  // Cloak and long hair behind everything.
  if (look.cloak !== 'none') Q.add(2, () => frame(ctx, rig, torso.worldX, torso.worldY, torso.angle * .5 + st.cloak.value * .32, cx => PART.cloakBack(cx, P, look, d, {bend: st.cloak.value, flare: loco * .6 + Math.max(0, lean) * .8, t})));
  if (['long', 'braided', 'topknot'].includes(look.hairStyle) && look.headgear !== 'full-helm' && look.headgear !== 'hood')
    Q.add(4, () => frame(ctx, rig, headB.worldX, headB.worldY, headB.angle * .3, cx => { cx.scale(d.kh, d.kh); PART.hairBack(cx, P, look, {sway: st.hair.value, t}); }));
  // Weapon or quiver across the back.
  if (weapons && main.kind === 'bow') Q.add(3, () => { const [qx, qy] = worldOf(rig, ...toLocal(rig, torso.x, torso.y, torso.angle, -d.sx * .3, d.waist * .2)); frame(ctx, rig, qx, qy, torso.angle - .5, cx => PART.quiver(cx, F), d.ws); });

  // Far leg.
  // Thigh over shin: its rounded end reads as the knee, with no seam.
  Q.add(6.1, onBone('left_thigh', cx => PART.thigh(cx, F, look, d)));
  Q.add(6, onBone('left_shin', cx => PART.shin(cx, F, look, d)));
  // Planted feet stay flat; a lifted foot points its toe down.
  const footOf = (side, pal, z, lift) => { const f = bone(side + '_foot'); Q.add(z, () => frame(ctx, rig, f.worldX, f.worldY, standing ? clamp(lift, 0, 14) * .035 : bone(side + '_shin').angle * .6, cx => PART.foot(cx, pal, look, d))); };
  footOf('left', F, 6.2, c.ll);

  // Far arm and whatever it holds.
  const farHandMode = main.kind === 'bow' ? 'grip' : (c.two > .5 && held) ? 'grip' : c.open > .5 ? 'open' : offItem ? 'grip' : 'rest';
  const leftUpper = bone('left_upper_arm'), leftLower = bone('left_lower_arm');
  const leftFlex = leftLower && leftUpper ? (leftLower.angle - leftUpper.angle) : 0;
  // The far arm hangs behind the torso unless the pose brings it across the chest (`af`):
  // then the forearm and hand come in front first, the upper arm after, still behind the
  // head and the near arm. Anything the far hand holds follows its forearm.
  const farFront = farArmFront(c.af), farItemZ = farFront.lower ? 48.3 : 9;
  Q.add(farFront.upper ? 48 : 8, onBone('left_upper_arm', cx => PART.upperArm(cx, F, look, d, {near: false})));
  Q.add(farFront.lower ? 48.1 : 8.1, onBone('left_lower_arm', cx => PART.lowerArm(cx, F, look, d, {flexion: leftFlex, near: false})));
  const leftHand = bone('left_hand');
  const farHandZ = c.two > .5 && held ? 64 : farFront.lower ? 48.2 : 8.2;
  Q.add(farHandZ, () => frame(ctx, rig, leftHand.worldX, leftHand.worldY, leftLower.angle, cx => PART.hand(cx, F, look, d, {mode: farHandMode, side: 'left'})));
  if (offItem) {
    const [ix, iy] = worldOf(rig, fx, fy);
    if (look.offhand === 'lantern') Q.add(farItemZ, () => frame(ctx, rig, ix, iy, 0, cx => PART.lantern(cx, P, look, {t, swing: st.lantern.value}), d.ws));
    else if (look.offhand === 'tome') Q.add(farItemZ, () => frame(ctx, rig, ix, iy, c.oa + (want.key === 'channel' || want.key === 'release' ? -.2 : .3), cx => PART.tome(cx, P, look, {open: want.key === 'channel' || want.key === 'release' ? 1 : 0, t}), d.ws));
    else Q.add(farItemZ, () => frame(ctx, rig, ix, iy, standing ? c.oa : c.pa + 1.57, cx => PART.shield(cx, F, look, {kind: look.offhand}), d.ws * (look.offhand === 'buckler' ? .9 : 1)));
  } else if (look.second && !look.offStowed && main.kind !== 'bow' && sheath < .5) {
    const [ix, iy] = worldOf(rig, fx, fy);
    Q.add(farItemZ, () => frame(ctx, rig, ix, iy, c.wa * .8 + .3, cx => PART.weapon(cx, F, look, {...main, ...look.second, hands: 1, fx: look.second.fx}, {}), d.ws));
  }
  // The bow lives in the far hand; the string runs to the drawing hand.
  if (weapons && main.kind === 'bow') {
    if (held) {
      const [bx, by] = worldOf(rig, fx, fy), pull = clamp((fx - gx) / (s * ws) - 2, 0, 24) * clamp(c.draw * 1.2, 0, 1);
      Q.add(10, () => frame(ctx, rig, bx, by, standing ? c.oa : c.pa + 1.57, cx => PART.bow(cx, P, look, main, {pull, arrow: c.draw > .3}), ws));
    } else { const [bx, by] = worldOf(rig, stow.x, stow.y); Q.add(3.1, () => frame(ctx, rig, bx, by, stow.angle, cx => PART.bow(cx, F, look, main, {}), ws)); }
  }

  // Hip gear: scabbard (always there for blades) and a stowed weapon in it.
  if (weapons && stow && !stow.back && main.kind !== 'wand') {
    const [mx, my] = worldOf(rig, ...stow.mouth);
    Q.add(12, () => frame(ctx, rig, mx, my, stow.sa, cx => PART.scabbard(cx, F, main), ws));
  }
  if (weapons && stow && !held && main.kind !== 'bow') {
    const [sx, sy] = worldOf(rig, stow.x, stow.y);
    // Sheathed: the scabbard (z 12) covers the blade, leaving the hilt.
    Q.add(stow.back ? 3.2 : 11.9, () => frame(ctx, rig, sx, sy, stow.angle, cx => PART.weapon(cx, F, look, main, {t}), ws));
  }
  if (look.trinket === 'satchel') Q.add(14, onBone('pelvis', cx => PART.satchelBag(cx, F, look, d)));

  // Near leg, then the garments over both legs.
  Q.add(20.1, onBone('right_thigh', cx => PART.thigh(cx, P, look, d)));
  Q.add(20, onBone('right_shin', cx => PART.shin(cx, P, look, d)));
  footOf('right', P, 20.2, c.rl);
  Q.add(22, onBone('pelvis', cx => PART.hips(cx, P, look, d)));
  const legSwing = (bone('left_thigh').angle + bone('right_thigh').angle) * .5 - pelvis.angle;
  Q.add(30, () => frame(ctx, rig, pelvis.worldX, pelvis.worldY, pelvis.angle, cx => PART.skirt(cx, P, look, d, {swing: legSwing, t})));
  Q.add(41, onBone('pelvis', cx => PART.belt(cx, P, look, d)));
  Q.add(39, onBone('neck', cx => PART.neck(cx, P, d)));
  Q.add(40, onBone('torso', cx => PART.torso(cx, P, look, d, {t})));
  if (look.trinket !== 'none') Q.add(42, onBone('torso', cx => PART.trinket(cx, P, look, d)));
  if (look.cloak !== 'none') Q.add(46, onBone('torso', cx => PART.cloakFront(cx, P, look, d)));
  const mood = moodOf(want.key, look), blink = !reduced && now < st.blinkUntil;
  const headYawLean = turnProgress > 0 && turnProgress < 1 ? (turnProgress < 0.5 ? 0.16 : -0.16) : 0;
  Q.add(50, () => frame(ctx, rig, headB.worldX, headB.worldY, headB.angle + headYawLean, cx => { cx.scale(d.kh, d.kh); PART.head(cx, P, look, {blink, mood, t}); }));

  // Near arm, the held weapon, then the gripping hand over the handle.
  const rightUpper = bone('right_upper_arm'), rightLower = bone('right_lower_arm');
  const rightFlex = rightLower && rightUpper ? (rightLower.angle - rightUpper.angle) : 0;
  Q.add(56, onBone('right_upper_arm', cx => PART.upperArm(cx, P, look, d, {near: true})));
  Q.add(58, onBone('right_lower_arm', cx => PART.lowerArm(cx, P, look, d, {flexion: rightFlex, near: true})));
  const glowing = main.glow || ['artifact', 'blessed'].includes(main.rarity);
  const glow = glowing ? .6 + Math.sin(t * .004) * .25 : main.fx.length && (want.key === 'strike' || want.key === 'follow' || want.key === 'release') ? .8 : 0;
  if (weapons && held && main.kind !== 'bow' && main.kind !== 'none') {
    // A blade cocked back over the shoulder hangs behind the body, as
    // Doran's raised Cleaver does; forward it paints over everything.
    const behind = tipDir(wAngle)[0] < -.3 && main.profile !== 'polearm';
    const [wx, wy] = worldOf(rig, grip[0], grip[1]);
    Q.add(behind ? 7.5 : 60, () => frame(ctx, rig, wx, wy, wAngle, cx => PART.weapon(cx, behind ? F : P, look, main, {glow, t}), ws));
  }
  const rightHand = bone('right_hand');
  const nearMode = (held && main.kind !== 'none' && main.kind !== 'bow') || (main.kind === 'bow' && c.draw > .3) ? 'grip' : want.key === 'strike' || want.key === 'follow' ? 'grip' : 'rest';
  Q.add(62, () => frame(ctx, rig, rightHand.worldX, rightHand.worldY, rightLower.angle, cx => PART.hand(cx, P, look, d, {mode: nearMode, side: 'right'})));

  // Weapon smear through the swing, and the element the weapon carries.
  const [tipX, tipY] = [sockets.weapon_tip.x, sockets.weapon_tip.y];
  if (live && want.swing && held && main.kind !== 'bow') {
    const [bx, by] = worldOf(rig, ...grip);
    st.trail.push(now, bx, by, tipX, tipY);
  }
  const element = main.fx[0];
  if (!reduced && weapons) {
    Q.add(70, () => st.trail.draw(ctx, now, element ? ELEMENT_COLOUR[element] : '#f4f7ff', 150, element ? .6 : .38));
    if (live && element && held && main.kind !== 'none') {
      st.emit += dt * (want.swing ? .06 : .018);
      const [bx, by] = worldOf(rig, ...grip);
      while (st.emit >= 1) { st.emit -= 1; const u = Math.random(); st.particles.emit(bx + (tipX - bx) * u, by + (tipY - by) * u, element, 1, 1.5 * s, 1); }
    }
    if (live) st.particles.step(dt);
    Q.add(71, () => st.particles.draw(ctx, s));
  }
  // A phase-touched figure is not entirely here.
  const spectral = look.aura === 'phase';
  if (spectral) { ctx.save(); ctx.globalAlpha *= .72 + (reduced ? 0 : Math.sin(t * .0023) * .08); }
  Q.run();
  if (spectral) ctx.restore();
  return sockets;
}

// Element burst on the figure, for impacts the director plays (a fire bolt
// landing throws embers off the target, not just an overlay ring).
export function heroBurst(rig, element, x, y) {
  const st = rig?.hero; if (!st) return;
  const token = ELEMENT_COLOUR[element] ? element : ELEMENT_OF_DAMAGE[element];
  if (token) st.particles.burst(x, y, token, 16, 110);
}

export function heroPresentation(model = {}) { return actorLook(model); }

// Voice-card medallion drawn by the same rig, so portraits never drift from
// the figure. Cached per look.
const portraits = new Map();
export function heroPortrait(model = {}, size = 128) {
  if (typeof document === 'undefined') return '';
  const look = actorLook(model), key = `${look.key}|${look.palette.hair}|${look.palette.skin}|${look.hairStyle}|${look.headgear}|${look.face}|${look.marks}|${size}`;
  if (portraits.has(key)) return portraits.get(key);
  let url = '';
  try {
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d'), scale = size / 30;
    const bg = ctx.createRadialGradient(size * .42, size * .3, size * .05, size * .5, size * .5, size * .75);
    bg.addColorStop(0, '#4f5a78'); bg.addColorStop(1, '#141828'); ctx.fillStyle = bg; ctx.fillRect(0, 0, size, size);
    const rig = new SkeletalRig({scale});
    drawHero(ctx, rig, model, {x: size * .5, y: size * .5 + (look.body.heightUnits - 8) * scale, pose: 'rest', now: 0, dt: 0,
      reducedMotion: true, shadow: false, weapons: false, idleFidgets: false});
    url = canvas.toDataURL('image/png');
  } catch { url = ''; }
  portraits.set(key, url);
  return url;
}

export const HERO_RIG = Object.freeze({
  identity: 'hero', kind: 'vector-rig', heightUnits: 97,
  layers: Object.freeze({}), poses: Object.freeze(['rest', 'guard', 'ready', 'windup', 'strike', 'follow', 'block', 'hit', 'crit', 'dodge',
    'channel', 'release', 'run', 'walk', 'jump', 'climb', 'kneel', 'victory', 'down', ...Object.keys(COMMON)]),
  loadouts: Object.freeze(['blade', 'heavy', 'dagger', 'polearm', 'staff', 'wand', 'bow', 'unarmed']),
  draw: drawHero, presentation: heroPresentation, portrait: heroPortrait,
  loadout: model => actorLook(model).main.profile,
});
