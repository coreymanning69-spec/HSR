// Body view model shared by every rig (hero-rig.js now; doran-rig.js and wren-rig.js next).
//
// Pure functions and data, no canvas. Presentation only: this places joints and
// orders limbs, it never reads or decides mechanics.
//
// The figures face +x in a three-quarter-front view: the chest is turned `yaw`
// radians toward the camera (0 = pure profile, pi/2 = square to the camera). With
// S the half-width of the shoulder line seen from the front, the near (right)
// shoulder then projects S*sin(theta) BEHIND the sternum line and the far (left)
// shoulder the same distance in front of it. Both sit inside the silhouette, never
// on its edge. Attacks twist the chest (`tw`): a wind-up opens it toward the
// camera, a strike turns it into the target so the near shoulder leads.

export const VIEW = {yaw: .5};

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

// Chest turn for a pose: the standing view plus that pose's twist.
export const turnOf = (tw = 0, yaw = VIEW.yaw) => clamp(yaw + tw, -.5, 1.4);

// Horizontal offset of a shoulder from the torso axis (the +x side is the front).
export const shoulderSpread = (side, S, theta) => (side === 'right' ? -1 : 1) * S * Math.sin(theta);

// Elevation of an arm from hanging straight down: 0 hanging, pi/2 horizontal,
// pi overhead, for a direction (dx, dy) with +y down.
export const elevationOf = (dx, dy) => Math.acos(clamp(dy / (Math.hypot(dx, dy) || 1), -1, 1));

// The collarbone: as an arm rises the shoulder lifts and reaches forward instead
// of staying pinned to the ribs. Ranges come from the shoulder girdle's real
// travel (up about 30 deg, forward about 45 deg) scaled to rig units.
export const CLAVICLE = Object.freeze({lift: 2.5, reach: 2, liftFrom: .9, liftTo: 2.4, reachFrom: .5, reachTo: 1.6});
export function clavicle(elevation, size = 1) {
  return {dy: -CLAVICLE.lift * size * smooth(CLAVICLE.liftFrom, CLAVICLE.liftTo, elevation),
    dx: CLAVICLE.reach * size * smooth(CLAVICLE.reachFrom, CLAVICLE.reachTo, elevation)};
}

// A body part with a front-view half-width `a` and a side half-depth `b`, turned `theta`
// from profile (the same angle as the shoulders). Its silhouette is an ellipse's shadow;
// the front-centre line (sternum, buckle, tabard) is carried forward by b*cos(theta), and
// anything drawn across the part (an emblem) is foreshortened by sin(theta).
export const halfWidth = (a, b, theta) => Math.hypot(b * Math.cos(theta), a * Math.sin(theta));
export const frontOffset = (b, theta) => b * Math.cos(theta);
export const lateralScale = theta => Math.sin(theta);

// Which far-arm segments are drawn in front of the torso for a blended `af`
// (0 behind, 1 in front). The forearm and hand switch first, so an arm can pass
// behind the chest at the shoulder and come round in front of it.
export const farArmFront = af => ({upper: af > .8, lower: af > .35});

// Joint ranges for the physics pass (radians, rig convention: negative swings a
// limb forward or up, positive back). Data only: nothing here drives the rig yet.
// A physics rig is defined in the bind pose, so `BIND` is the rest pose to use.
export const JOINT_LIMITS = Object.freeze({
  shoulder: Object.freeze({forward: -3.1, back: .9, kind: 'cone'}),
  elbow: Object.freeze({min: 0, max: 2.79, kind: 'revolute'}),
  waist: Object.freeze({min: -.5, max: .5, kind: 'revolute'}),
  neck: Object.freeze({min: -.4, max: .4, kind: 'revolute'}),
  clavicle: Object.freeze({up: CLAVICLE.lift, forward: CLAVICLE.reach, kind: 'translate'}),
});
export const BIND = Object.freeze({yaw: .5, tw: 0, eb: 1});
