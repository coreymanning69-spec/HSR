"""web/combat-input.js: the pure key/click -> engine-action mapping.

Runs the module under Node when Node is installed (skipped otherwise). The
module has no imports, so it is copied to a temporary .mjs and imported.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "web" / "combat-input.js"

HARNESS = r"""
import * as I from './combat-input.mjs';
import assert from 'node:assert/strict';

assert.equal(I.combatStyle('nonsense'), 'hybrid');
assert.equal(I.styleAllows('hybrid', 'keys'), true);
assert.equal(I.styleAllows('hybrid', 'mouse'), true);
assert.equal(I.styleAllows('turn_based', 'keys'), false);
assert.equal(I.styleAllows('turn_based', 'legacy_keys'), true);
assert.equal(I.styleAllows('direct_wasd', 'mouse'), false);
assert.equal(I.styleAllows('mouse_click', 'mouse'), true);
assert.equal(I.styleAllows('mouse_click', 'dock'), true);

assert.equal(I.isTypingTarget({tagName: 'INPUT'}), true);
assert.equal(I.isTypingTarget({tagName: 'textarea'}), true);
assert.equal(I.isTypingTarget({tagName: 'DIV', isContentEditable: true}), true);
assert.equal(I.isTypingTarget({tagName: 'DIV', closest: () => null}), false);
assert.equal(I.isTypingTarget(null), false);

assert.deepEqual(I.stepDestination([20, 20, 0], 'w'), [20, 25, 0]);
assert.deepEqual(I.stepDestination([20, 20, 0], 'S'), [20, 15, 0]);
assert.deepEqual(I.stepDestination([20, 20, 0], 'a'), [15, 20, 0]);
assert.deepEqual(I.stepDestination([20, 20, 0], 'ArrowRight'), [25, 20, 0]);
assert.equal(I.stepDestination([0, 0, 0], 'a'), null);
assert.equal(I.stepDestination([120, 120, 0], 'w'), null);
assert.equal(I.stepDestination([20, 20, 0], 'x'), null);

assert.deepEqual(I.groundDestination([20, 30, 0], 0.5), [60, 30, 0]);
assert.equal(I.groundDestination([60, 30, 0], 0.5), null);
assert.deepEqual(I.flightDestination([20, 20, 5], 0.5, 0.78), [60, 0, 5]);
assert.deepEqual(I.flightDestination([20, 20, 0], 0.25, 0.16), [30, 120, 0]);
assert.equal(I.flightDestination([60, 0, 0], 0.5, 0.78), null);
assert.deepEqual(I.withinMovement([20, 20, 0], [60, 30, 0], 25), [45, 20, 0]);
assert.deepEqual(I.withinMovement([20, 20, 0], [25, 30, 0], 30), [25, 30, 0]);
assert.equal(I.withinMovement([20, 20, 0], [60, 20, 0], 0), null);

assert.deepEqual(I.avoidOccupied([20, 20, 0], [50, 20, 0], [[50, 20, 0]]), [45, 20, 0]);
assert.deepEqual(I.avoidOccupied([20, 20, 0], [30, 30, 0], [[30, 30, 0], [25, 25, 0]]), null);
assert.deepEqual(I.avoidOccupied([20, 20, 0], [40, 20, 0], [[90, 90, 0]]), [40, 20, 0]);
assert.equal(I.avoidOccupied([20, 20, 0], null, []), null);
assert.equal(I.gridDistance([0, 0, 0], [10, 5, 0]), 10);
const foes = [{id: 'e0', position: [25, 20, 0]}, {id: 'e1', position: [80, 80, 0]}];
assert.deepEqual(I.threatenedBy([20, 20, 0], [10, 20, 0], foes), ['e0']);
assert.deepEqual(I.threatenedBy([20, 20, 0], [25, 25, 0], foes), []);
assert.deepEqual(I.threatenedBy([20, 20, 0], [10, 20, 0], foes, {disengaged: true}), []);

const rows = [
  {id: 'attack', label: 'Attack', available: true, targets: ['e0', 'e1']},
  {id: 'cast', label: 'Cast a spell', available: false, reason: 'no spells', targets: []},
  {id: 'shove', label: 'Shove', available: true, targets: ['e0']},
  {id: 'trip', label: 'Trip', available: true, targets: ['e0']},
  {id: 'grapple', label: 'Grapple', available: false, reason: 'No attack remains this turn.', targets: []},
  {id: 'dodge', label: 'Dodge', available: true, targets: []},
  {id: 'dagger_attack', label: 'Obsidian dagger', available: true, targets: ['e0']},
  {id: 'maneuver_trip_attack', label: 'Trip Attack', available: true, targets: ['e0'], maneuver: 'Trip Attack'},
];
const doran = I.hotbarSlots('doran', rows);
assert.deepEqual(doran.map(s => s.id), ['attack', 'dagger_attack', 'cast', 'maneuver_trip_attack']);
assert.equal(doran[2].available, false);
const generic = I.hotbarSlots('custom', rows);
assert.deepEqual(generic.map(s => s.id), ['attack', 'shove', 'cast', 'dodge']);

const near = [{id: 'e0', position: [25, 20, 0], hp: 5}, {id: 'e1', position: [22, 30, 0], hp: 5}];
assert.deepEqual(I.spaceIntent({economy: {action: 1}, foes: near, position: [20, 20, 0]}), {kind: 'attack', target: 'e0'});
assert.deepEqual(I.spaceIntent({economy: {action: 1}, focus: 'e1', foes: near, position: [20, 20, 0], reach: 10}), {kind: 'attack', target: 'e1'});
assert.deepEqual(I.spaceIntent({economy: {action: 0, attacks: 0}, foes: near, position: [20, 20, 0]}), {kind: 'end_turn'});
assert.deepEqual(I.spaceIntent({economy: {action: 1}, foes: [{id: 'e9', position: [90, 90, 0]}], position: [20, 20, 0]}), {kind: 'end_turn'});
assert.deepEqual(I.spaceIntent({economy: {action: 0, bonus: 1}, foes: near, position: [20, 20, 0], wren: true, reach: 60}), {kind: 'attack', target: 'e0'});

const wheel = I.radialItems('e0', rows, {identity: 'doran'});
assert.deepEqual(wheel.map(i => i.id), ['attack', 'cast', 'maneuver', 'shove', 'trip', 'grapple', 'inspect']);
assert.equal(wheel.find(i => i.id === 'maneuver').action, 'maneuver_trip_attack');
assert.equal(wheel.find(i => i.id === 'grapple').available, false);
assert.equal(wheel.find(i => i.id === 'inspect').available, true);
const far = I.radialItems('e1', rows, {identity: 'doran'});
assert.equal(far.find(i => i.id === 'shove').reason, 'Out of reach for this action.');
assert.equal(I.radialItems('e0', rows, {identity: 'custom'}).some(i => i.id === 'maneuver'), false);
assert.ok(I.radialItems('e0', rows, {playerTurn: false}).filter(i => i.id !== 'inspect').every(i => !i.available));
const spots = I.radialLayout(4, 10);
assert.deepEqual(spots[0], {x: 0, y: -10});
assert.deepEqual(spots[1], {x: 10, y: 0});
console.log('combat-input ok');
"""


class CombatInputModuleTest(unittest.TestCase):
    def test_pure_mapping(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(MODULE, Path(tmp) / "combat-input.mjs")
            harness = Path(tmp) / "harness.mjs"
            harness.write_text(HARNESS, encoding="utf-8")
            done = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr or done.stdout)
        self.assertIn("combat-input ok", done.stdout)


if __name__ == "__main__":
    unittest.main()
