// Combat input router: one place that turns a key, a click or a right-click
// into the canonical engine action the command dock would have sent.
//
// Pure helpers only -- no DOM, no host calls. app.js owns the listeners and
// posts whatever these return through the same submit path as the buttons,
// so the host still validates range, economy, terrain and every roll.
//
// Styles (Options > Combat presentation > Combat controls):
//   turn_based   the command dock and pickers only (keys: legacy A/E hotkeys)
//   direct_wasd  W/A/S/D steps 5 ft, Space attacks or ends the turn, 1-4 hotbar
//   mouse_click  left-click ground moves, left-click enemy focuses, right-click
//                an enemy opens the action wheel, right-click ground clears
//   hybrid       all of the above at once (default)

export const COMBAT_STYLES = Object.freeze(['hybrid', 'turn_based', 'direct_wasd', 'mouse_click']);
export const DEFAULT_COMBAT_STYLE = 'hybrid';

export function combatStyle(value) {
  return COMBAT_STYLES.includes(value) ? value : DEFAULT_COMBAT_STYLE;
}
// Which input channels a style turns on. The dock is always on: it is the
// fallback every other style can reach.
export function styleAllows(style, channel) {
  const s = combatStyle(style);
  if (channel === 'dock') return true;
  if (channel === 'keys') return s === 'hybrid' || s === 'direct_wasd';
  if (channel === 'mouse') return s === 'hybrid' || s === 'mouse_click';
  if (channel === 'legacy_keys') return s === 'turn_based' || s === 'mouse_click';
  return false;
}

// Typing in chat, the console or a dialog field never moves a hero.
export function isTypingTarget(target) {
  if (!target || typeof target !== 'object') return false;
  if (target.isContentEditable) return true;
  const tag = String(target.tagName || '').toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  return Boolean(target.closest?.('input,textarea,select,[contenteditable],[contenteditable="true"]'));
}

// The host grid: 5-foot squares, 0..120 on each axis, +y is north.
export const GRID_STEP = 5;
export const GRID_MAX = 120;
export const KEY_DIRECTIONS = Object.freeze({
  w: [0, GRID_STEP], s: [0, -GRID_STEP], a: [-GRID_STEP, 0], d: [GRID_STEP, 0],
  arrowup: [0, GRID_STEP], arrowdown: [0, -GRID_STEP], arrowleft: [-GRID_STEP, 0], arrowright: [GRID_STEP, 0],
});
const clampFeet = value => Math.max(0, Math.min(GRID_MAX, Math.round(Number(value || 0) / GRID_STEP) * GRID_STEP));

// The square one step from `position` in the key's direction, or null when
// the key is not a direction or the step would leave the grid.
export function stepDestination(position, key) {
  const delta = KEY_DIRECTIONS[String(key || '').toLowerCase()];
  if (!delta || !Array.isArray(position)) return null;
  const [x, y, z] = [0, 1, 2].map(i => clampFeet(position[i]));
  const next = [clampFeet(x + delta[0]), clampFeet(y + delta[1]), z];
  return next[0] === x && next[1] === y ? null : next;
}

// A click at `fraction` (0..1) across the side-view stage, as a grid square
// on the actor's own row. The ground stage draws x = feet / 120, so this is
// the inverse of that projection; depth (y) and height (z) are kept.
export function groundDestination(position, fraction) {
  if (!Array.isArray(position) || !Number.isFinite(Number(fraction))) return null;
  const f = Math.max(0, Math.min(1, Number(fraction)));
  const next = [clampFeet(f * GRID_MAX), clampFeet(position[1]), clampFeet(position[2])];
  return next[0] === clampFeet(position[0]) ? null : next;
}

// A click on the flight arena, which draws x = feet / 120 across and
// y from 78% (0 ft) up to 16% (120 ft) of its height (app.js flightActor):
// both axes map back to the grid; height (z) is kept.
export function flightDestination(position, fx, fy) {
  if (!Array.isArray(position) || !Number.isFinite(Number(fx)) || !Number.isFinite(Number(fy))) return null;
  const x = clampFeet(Math.max(0, Math.min(1, Number(fx))) * GRID_MAX);
  const y = clampFeet((0.78 - Math.max(0, Math.min(1, Number(fy)))) / 0.62 * GRID_MAX);
  const next = [x, y, clampFeet(position[2])];
  return next[0] === clampFeet(position[0]) && next[1] === clampFeet(position[1]) ? null : next;
}

// Cap a destination to the movement the actor has left, walking from
// `position` toward it along x then y in whole squares.
export function withinMovement(position, destination, movement) {
  if (!Array.isArray(position) || !Array.isArray(destination)) return null;
  let budget = Math.max(0, Math.floor(Number(movement || 0) / GRID_STEP)) * GRID_STEP;
  const out = [clampFeet(position[0]), clampFeet(position[1]), clampFeet(position[2])];
  for (const axis of [0, 1]) {
    const gap = clampFeet(destination[axis]) - out[axis];
    const step = Math.sign(gap) * Math.min(Math.abs(gap), budget);
    out[axis] += step; budget -= Math.abs(step);
  }
  return out[0] === clampFeet(position[0]) && out[1] === clampFeet(position[1]) ? null : out;
}

// Back a destination off, one square at a time toward `origin`, until no
// other combatant stands on it. (The host's move does not check occupancy
// yet; 5e lets you pass through an ally but not end in its square.)
export function avoidOccupied(origin, destination, occupied = []) {
  if (!Array.isArray(origin) || !Array.isArray(destination)) return null;
  const taken = new Set(occupied.filter(Array.isArray).map(p => `${clampFeet(p[0])},${clampFeet(p[1])}`));
  let [x, y] = [clampFeet(destination[0]), clampFeet(destination[1])];
  const [ox, oy] = [clampFeet(origin[0]), clampFeet(origin[1])];
  while (taken.has(`${x},${y}`) && (x !== ox || y !== oy)) {
    x += Math.sign(ox - x) * GRID_STEP;
    y += Math.sign(oy - y) * GRID_STEP;
  }
  return x === ox && y === oy ? null : [x, y, clampFeet(destination[2])];
}

// Chebyshev distance in feet, the host's own measure (tactical.distance).
export function gridDistance(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b)) return Infinity;
  return Math.max(...[0, 1, 2].map(i => Math.abs(Number(a[i] || 0) - Number(b[i] || 0))));
}

// Foes a step would leave within reach of (5 ft), i.e. who may take an
// opportunity attack. Disengage and a mobile stance suppress it host-side;
// this is only a warning ring, never a rule.
export function threatenedBy(position, destination, foes = [], {disengaged = false} = {}) {
  if (disengaged || !Array.isArray(position) || !Array.isArray(destination)) return [];
  return foes.filter(foe => foe && Array.isArray(foe.position)
    && gridDistance(position, foe.position) <= GRID_STEP && gridDistance(destination, foe.position) > GRID_STEP)
    .map(foe => foe.id);
}

// The 1-4 hotbar: which contextual action each slot fires for this actor.
// `rows` is combat.contextual_actions (id, available, targets, ...).
export function hotbarSlots(identity, rows = []) {
  const byId = new Map((rows || []).map(row => [row.id, row]));
  const pick = (...ids) => ids.map(id => byId.get(id)).find(row => row && row.available) || ids.map(id => byId.get(id)).find(Boolean) || null;
  const who = String(identity || '').toLowerCase();
  const slots = who === 'doran'
    ? [pick('attack'), pick('dagger_attack', 'cleaver_attack'), pick('quick_toss', 'cast'), pick('maneuver_trip_attack', 'maneuver_precision_attack', 'read_seam')]
    : who === 'wren'
      ? [pick('attack'), pick('dodge'), pick('cast'), pick('second_wind', 'dash')]
      : [pick('attack'), pick('shove', 'trip'), pick('cast'), pick('dodge', 'dash')];
  return slots.map((row, index) => ({slot: index + 1, id: row?.id || null, label: row?.label || '—',
    available: Boolean(row?.available), reason: row?.reason || (row ? null : 'Nothing bound to this slot.'),
    targets: row?.targets || []}));
}

// Space: attack the focused (or nearest living) foe in reach while an attack
// remains, otherwise end the turn. Returns {kind: 'attack', target} |
// {kind: 'end_turn'} | null (nothing sensible).
export function spaceIntent({economy = {}, focus = null, foes = [], position = null, reach = 5, wren = false} = {}) {
  const canAttack = wren ? Boolean(economy.bonus) : Boolean(economy.action || economy.attacks);
  if (canAttack) {
    const living = foes.filter(foe => foe && foe.alive !== false && Number(foe.hp ?? 1) > 0);
    const inReach = living.filter(foe => !position || !Array.isArray(foe.position) || gridDistance(position, foe.position) <= reach);
    const chosen = inReach.find(foe => foe.id === focus)
      || inReach.slice().sort((a, b) => gridDistance(position, a.position) - gridDistance(position, b.position) || String(a.id).localeCompare(String(b.id)))[0];
    if (chosen) return {kind: 'attack', target: chosen.id};
  }
  return {kind: 'end_turn'};
}

// The right-click action wheel for one foe, from the host's own contextual
// rows. Each item carries the engine action id the dock would send.
const WHEEL = [
  {id: 'attack', label: 'Weapon attack', icon: '⚔'},
  {id: 'cast', label: 'Cast a spell', icon: '✧'},
  {id: 'maneuver', label: 'Maneuver', icon: '⚡'},
  {id: 'shove', label: 'Shove', icon: '⇥'},
  {id: 'trip', label: 'Trip', icon: '⤓'},
  {id: 'grapple', label: 'Grapple', icon: '✊'},
  {id: 'inspect', label: 'Inspect defenses', icon: '🔍'},
];
export function radialItems(targetId, rows = [], {identity = '', playerTurn = true} = {}) {
  const byId = new Map((rows || []).map(row => [row.id, row]));
  const maneuver = String(identity).toLowerCase() === 'doran'
    ? ['maneuver_trip_attack', 'maneuver_precision_attack', 'maneuver_pushing_attack'].map(id => byId.get(id)).find(row => row?.available) || byId.get('maneuver_trip_attack')
    : null;
  return WHEEL.filter(item => item.id !== 'maneuver' || maneuver).map(item => {
    if (item.id === 'inspect') return {...item, action: 'inspect', available: true, reason: null};
    const row = item.id === 'maneuver' ? maneuver : byId.get(item.id);
    let reason = !playerTurn ? 'Not your turn.' : !row ? 'Not available to this combatant.' : row.available ? null : row.reason;
    if (!reason && row?.targets?.length && !row.targets.includes(targetId)) reason = 'Out of reach for this action.';
    return {...item, action: row?.id || item.id, label: item.id === 'maneuver' && row ? row.label : item.label,
      available: !reason, reason};
  });
}
// Evenly spaced points on a circle, first at twelve o'clock, as px offsets.
export function radialLayout(count, radius = 76) {
  return Array.from({length: Math.max(0, count)}, (_, i) => {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(1, count);
    return {x: Math.round(Math.cos(angle) * radius), y: Math.round(Math.sin(angle) * radius)};
  });
}
