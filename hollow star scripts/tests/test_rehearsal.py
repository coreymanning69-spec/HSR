"""Hardening pass: movement affordability, replay, reaction timing, final floor.

These are the checks that stand between a run loop that reaches the end and a
run loop whose result means anything. Run with: python3 tests/test_rehearsal.py
"""

import copy
import json
import sys
import tempfile
import timeit
import unittest
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.run_service import RunService, RunServiceError
from hollowstar import policies, tactical as t, dungeon


def rehearse(root, seed, limit=4000):
    """Drive one automated five-floor run to its end. Returns the run and a log."""
    # Phase 5 measures gameplay and attrition. Save/resume correctness is
    # covered separately; disabling per-action disk checkpoints here keeps
    # the long rehearsal focused on engine cost rather than filesystem I/O.
    service = RunService(root, durable_saves=False)
    service.create('r', ['Doran', 'Wren'], ['Townsperson'], seed)
    service.design_start('r')
    events, steps = [], 0
    while steps < limit:
        run = service._active['r']
        if run.context['dungeon']['status'] != 'active':
            break
        action = policies.exploration_action(run)
        if action.get('type') == 'move':
            budget = t.economy(run, action['actor'])['movement']
            cost = t.move_cost(run, action['actor'], action['destination'])
            assert cost is not None and cost <= budget, (
                f'chooser proposed an unaffordable move: cost {cost} of {budget}')
        events.append(service.design_action('r', action)['event'])
        steps += 1
    return service, events, steps


def rehearse_job(job):
    return rehearse(*job)


class FixtureOppositionCarriesItsSystems(unittest.TestCase):
    """The DESIGN residents must reach the rules the engine actually runs.

    Until 2026-09-05 `dungeon.enemy()` set hp/ac/attack/dice and nothing else,
    so every resident had default 10s, saves worth +0, one attack and no pool.
    These guard the wiring, not the balance numbers, which content/dungeon.json
    is explicitly allowed to change.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / '.local/reliquary_runs')
        self.service.create('r', ['Doran', 'Wren'], ['Townsperson'], 'fixture-seed')
        self.service.design_start('r')
        self.service.design_action('r', {'type': 'fight'})
        self.run = self.service._active['r']

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_resident_carries_band_abilities_multiattack_and_a_pool(self):
        resident = self.run.opposition[0]
        self.assertGreater(int(resident.band), 10)
        self.assertNotEqual(set(resident.ability_scores.values()), {10})
        self.assertGreaterEqual(resident.attacks_per_action, 2)
        self.assertTrue(resident.resources)

    def test_resident_saves_are_sourced_rather_than_defaulted(self):
        rules = t.rules(self.run, 'e0')
        self.assertTrue(rules['saves'])
        self.assertNotEqual(set(rules['saves'].values()), {0})

    def test_a_bonus_attack_spends_the_declared_pool_and_refuses_without_one(self):
        pool = t.rules(self.run, 'e0')['bonus_attack_resource']
        before = self.run.opposition[0].resources[pool]
        self.run.context['combat']['positions']['e0'] = list(t.position(self.run, 'p0'))
        t.weapon_attack(self.run, 'e0', 'p0', bonus=True)
        self.assertEqual(self.run.opposition[0].resources[pool], before - 1)
        self.run.opposition[0].resources[pool] = 0
        self.run.context['combat']['economy']['e0']['bonus'] = 1
        with self.assertRaises(t.ActionError):
            t.weapon_attack(self.run, 'e0', 'p0', bonus=True)

    def test_an_actor_with_no_declared_pool_still_has_no_bonus_attack(self):
        t.rules(self.run, 'e0').pop('bonus_attack_resource', None)
        self.run.context['combat']['positions']['e0'] = list(t.position(self.run, 'p0'))
        with self.assertRaises(t.ActionError):
            t.weapon_attack(self.run, 'e0', 'p0', bonus=True)


class MovementAffordability(unittest.TestCase):
    """The floor-2 wedge: a chooser that assumed five feet per square."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / '.local/reliquary_runs'
        self.service = RunService(self.root)
        self.service.create('trial', ['Doran', 'Wren'], ['Townsperson'], 'movement-seed')
        self.service.design_start('trial')
        self.service.design_action('trial', {'type': 'fight'})
        self.run = self.service._active['trial']

    def tearDown(self):
        self.tmp.cleanup()

    def test_move_cost_prices_difficult_terrain_and_prone(self):
        run = self.run
        run.context['combat']['positions']['p0'] = [10, 10, 0]
        self.assertEqual(t.move_cost(run, 'p0', [20, 10, 0]), 10)
        run.context['combat']['terrain']['difficult'] = [[15, 10, 0]]
        self.assertEqual(t.move_cost(run, 'p0', [20, 10, 0]), 15)
        t.actor(run, 'p0').statuses['PRONE'] = 1
        self.assertEqual(t.move_cost(run, 'p0', [20, 10, 0]), 30)

    def test_move_cost_reports_none_rather_than_raising(self):
        run = self.run
        run.context['combat']['terrain']['blocked'] = [[15, 10, 0]]
        run.context['combat']['positions']['p0'] = [10, 10, 0]
        self.assertIsNone(t.move_cost(run, 'p0', [20, 10, 0]))
        self.assertIsNone(t.move_cost(run, 'p0', [23, 10, 0]))
        self.assertIsNone(t.move_cost(run, 'p0', 'over there'))

    def test_move_charges_exactly_what_move_cost_quoted(self):
        run = self.run
        run.context['combat']['positions']['p0'] = [10, 10, 0]
        run.context['combat']['terrain']['difficult'] = [[15, 10, 0]]
        run.context['combat']['positions']['e0'] = [100, 100, 0]
        quoted = t.move_cost(run, 'p0', [20, 10, 0])
        before = t.economy(run, 'p0')['movement']
        t.move(run, 'p0', [20, 10, 0])
        self.assertEqual(before - t.economy(run, 'p0')['movement'], quoted)

    def test_a_difficult_column_does_not_wedge_the_chooser(self):
        """The exact floor-2 shape: difficult ground between chooser and target."""
        run = self.run
        combat = run.context['combat']
        combat['terrain']['difficult'] = [[25, y, 0] for y in range(0, 120, 5)]
        combat['positions']['e0'] = [20, 20, 0]
        combat['positions']['p0'] = [60, 20, 0]
        combat['positions']['p1'] = [60, 30, 0]
        combat['cursor'] = combat['order'].index('e0')
        t.economy(run, 'e0')['movement'] = 10
        action = policies.combat_action(run)
        if action['type'] == 'move':
            cost = t.move_cost(run, 'e0', action['destination'])
            self.assertIsNotNone(cost)
            self.assertLessEqual(cost, 10)
        else:
            self.assertEqual(action['type'], 'end_turn')

    def test_approach_returns_none_instead_of_an_unpayable_step(self):
        run = self.run
        combat = run.context['combat']
        combat['terrain']['difficult'] = [[x, 20, 0] for x in range(0, 120, 5)]
        combat['positions']['e0'] = [20, 20, 0]
        combat['positions']['p0'] = [90, 20, 0]
        t.economy(run, 'e0')['movement'] = 5
        self.assertIsNone(policies.approach(run, 'e0', 'p0', 5))
        t.economy(run, 'e0')['movement'] = 10
        destination = policies.approach(run, 'e0', 'p0', 5)
        self.assertEqual(t.move_cost(run, 'e0', destination), 10)


class FullRunReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_five_floor_rehearsals_terminate(self):
        seeds = ('rehearse-1', 'rehearse-2', 'rehearse-3')
        roots = {seed: self.root / seed / '.local/reliquary_runs' for seed in seeds}
        jobs = [(roots[seed], seed) for seed in seeds]
        with ProcessPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(rehearse_job, jobs))
        rehearsals = dict(zip(seeds, results))
        for seed in seeds:
            with self.subTest(seed=seed):
                service, events, steps = rehearsals[seed]
                dungeon = service._active['r'].context['dungeon']
                self.assertIn(dungeon['status'], {'cleared', 'defeated', 'ejected'})
                self.assertLess(steps, 4000, 'run did not reach an ending')

    def test_one_seed_replays_to_an_identical_event_stream(self):
        first = rehearse(self.root / 'a' / '.local/reliquary_runs', 'replay-seed')[1]
        second = rehearse(self.root / 'b' / '.local/reliquary_runs', 'replay-seed')[1]
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_a_reload_mid_run_continues_the_same_stream(self):
        service = RunService(self.root / 'c' / '.local/reliquary_runs')
        service.create('r', ['Doran', 'Wren'], ['Townsperson'], 'reload-seed')
        service.design_start('r')
        for _ in range(40):
            run = service._active['r']
            if run.context['dungeon']['status'] != 'active':
                break
            service.design_action('r', policies.exploration_action(run))
        reloaded = RunService(self.root / 'c' / '.local/reliquary_runs')
        reloaded.load('r')
        self.assertEqual(service._active['r'].rng.getstate(), reloaded._active['r'].rng.getstate())
        for _ in range(25):
            live, other = service._active['r'], reloaded._active['r']
            if live.context['dungeon']['status'] != 'active':
                break
            action = policies.exploration_action(live)
            self.assertEqual(action, policies.exploration_action(other))
            self.assertEqual(service.design_action('r', action), reloaded.design_action('r', action))


class TransitionClone(unittest.TestCase):
    """The transactional clone is fast without weakening the read boundary."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / '.local/reliquary_runs', durable_saves=False)
        self.service.create('trial', ['Doran', 'Wren'], ['Townsperson'], 'clone-seed')
        self.service.design_start('trial')
        self.run = self.service._active['trial']
        for _ in range(8):
            self.service.design_action('trial', {'type': 'observe_room', 'actor': 'p0'})

    def tearDown(self):
        self.tmp.cleanup()

    def test_clone_isolates_runtime_and_shares_static_configuration(self):
        candidate = dungeon.clone_for_transition(self.run)
        self.assertIs(candidate.context['dungeon']['config'], self.run.context['dungeon']['config'])
        candidate.context['dungeon']['events'].append({'type': 'candidate-only'})
        candidate.party[0].hp -= 1
        self.assertNotIn({'type': 'candidate-only'}, self.run.context['dungeon']['events'])
        self.assertNotEqual(candidate.party[0].hp, self.run.party[0].hp)

    def test_returned_state_and_sheets_cannot_mutate_live_state(self):
        state = self.service.observe('trial')
        sheets = self.service.sheets('trial')
        state['events'].clear()
        state['room']['tells'].clear()
        sheets[0]['name'] = 'caller mutation'
        sheets[0].setdefault('resources', {})['invented'] = 99
        self.assertTrue(self.run.context['dungeon']['events'])
        self.assertTrue(self.service.observe('trial')['room']['tells'])
        self.assertNotEqual(self.run.party[0].name, 'caller mutation')
        self.assertNotIn('invented', self.run.party[0].resources)

    def test_clone_owns_history_containers_and_event_records(self):
        self.run.context['dungeon']['events'].append({'type': 'history', 'evidence': {'value': 1}})
        original_first = copy.deepcopy(self.run.context['dungeon']['events'][0])
        candidate = dungeon.clone_for_transition(self.run)
        candidate.context['dungeon']['events'].append({'type': 'candidate-only'})
        candidate.context['dungeon']['events'][0]['type'] = 'candidate-edit'
        self.assertEqual(len(candidate.context['dungeon']['events']),
                         len(self.run.context['dungeon']['events']) + 1)
        self.assertEqual(self.run.context['dungeon']['events'][0], original_first)
        self.assertNotEqual(candidate.context['dungeon']['events'][0],
                            self.run.context['dungeon']['events'][0])

    def test_clone_beats_full_deepcopy_by_a_measurable_margin(self):
        full = timeit.timeit(lambda: copy.deepcopy(self.run), number=8)
        optimized = timeit.timeit(lambda: dungeon.clone_for_transition(self.run), number=8)
        self.assertLess(optimized, full * 0.8, f'optimized={optimized:.4f}s full={full:.4f}s')


class PolicyBoundaries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / '.local/reliquary_runs', durable_saves=False)
        self.service.create('trial', ['Doran', 'Wren'], ['Townsperson'], 'policy-boundary-seed')
        self.service.design_start('trial')
        self.service.design_action('trial', {'type': 'fight'}, include_state=False)
        self.run = self.service._active['trial']

    def tearDown(self):
        self.tmp.cleanup()

    def test_recovery_is_not_proposed_at_exactly_half_hp(self):
        combat = self.run.context['combat']
        combat['cursor'] = combat['order'].index('p1')
        combat['economy']['p1']['bonus'] = 1
        wren = t.actor(self.run, 'p1')
        wren.hp = wren.max_hp // 2
        action = policies.combat_action(self.run)
        self.assertNotEqual(action['type'], 'unearthly_recovery')


class ReactionTiming(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / '.local/reliquary_runs')
        self.service.create('trial', ['Doran', 'Wren'], ['Townsperson'], 'reaction-seed')
        self.service.design_start('trial')
        self.service.design_action('trial', {'type': 'fight'})
        self.run = self.service._active['trial']
        combat = self.run.context['combat']
        combat['cursor'] = combat['order'].index('p0')
        combat['positions']['p0'] = [20, 20, 0]
        combat['positions']['e0'] = [20, 25, 0]

    def tearDown(self):
        self.tmp.cleanup()

    def test_leaving_a_reach_opens_a_window_that_blocks_ordinary_actions(self):
        pending = t.move(self.run, 'p0', [40, 20, 0])
        self.assertEqual(pending['type'], 'movement_pending')
        self.assertEqual(self.run.context['combat']['positions']['p0'], [20, 20, 0])
        with self.assertRaisesRegex(t.ActionError, 'pending reactions'):
            t.apply(self.run, {'type': 'end_turn'})

    def test_taking_the_reaction_spends_it_and_clears_that_window(self):
        t.move(self.run, 'p0', [40, 20, 0])
        t.apply(self.run, {'type': 'reaction', 'actor': 'e0'})
        pending = self.run.context['combat']['pending']
        self.assertNotIn('opportunity', [w['kind'] for w in pending])
        self.assertEqual(t.economy(self.run, 'e0')['reaction'], 0)
        self.assertEqual(self.run.context['combat']['positions']['p0'], [40, 20, 0])
        with self.assertRaisesRegex(t.ActionError, 'no eligible reaction window'):
            t.apply(self.run, {'type': 'reaction', 'actor': 'e0'})

    def test_doran_deft_answer_is_a_free_dagger_attack(self):
        t.begin(self.run)
        doran = t.actor(self.run, 'p0')
        before = doran.resources.get('superiority_dice', 0)
        self.run.context['combat']['pending'].append({
            'kind': 'deft_answer', 'reactor': 'p0', 'target': 'e0', 'options': ['deft_answer']})
        event = t.apply(self.run, {'type': 'reaction', 'actor': 'p0', 'defense': 'deft_answer'})
        self.assertEqual(event['feature'], 'Deft Answer')
        self.assertEqual(doran.resources.get('superiority_dice', 0), before)
        self.assertEqual(t.economy(self.run, 'p0')['reaction'], 0)

    def test_declining_suppresses_the_repeat_offer_for_that_turn(self):
        t.move(self.run, 'p0', [40, 20, 0])
        t.apply(self.run, {'type': 'decline_reaction', 'actor': 'e0'})
        self.assertIn('p0', t.rules(self.run, 'e0')['declined_targets'])
        moved = t.move(self.run, 'p0', [40, 20, 0])
        self.assertEqual(moved['type'], 'movement')
        self.assertEqual(self.run.context['combat']['positions']['p0'], [40, 20, 0])

    def test_lethal_reaction_cancels_pending_movement(self):
        self.run.party[0].hp=1
        self.run.opposition[0].equipment[0].damage_modifier=100
        t.move(self.run, 'p0', [40, 20, 0])
        result=t.apply(self.run, {'type':'reaction','actor':'e0'})
        self.assertFalse(self.run.party[0].alive)
        self.assertEqual(result['movement']['cancelled'],'actor defeated')
        self.assertEqual(self.run.context['combat']['positions']['p0'], [20, 20, 0])


class FinalFloor(unittest.TestCase):
    """Authoritative round-20 cocoon, endings, and final-floor receipts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / '.local/reliquary_runs')
        self.service.create('trial', ['Doran', 'Wren'], ['Townsperson'], 'cocoon-seed')
        self.service.design_start('trial')

    def tearDown(self):
        self.tmp.cleanup()

    def reach_the_cocoon(self, ruling=None):
        run = self.service._active['trial']
        run.context['manual_opposition'] = True
        dungeon = run.context['dungeon']
        dungeon['floor'], dungeon['room'] = 5, 6
        dungeon['rooms']['5:6'] = {'resolved': True}
        if ruling:
            run.context['design_rulings'] = {'tarrasque_cocoon': ruling}
        self.service.design_action('trial', {'type': 'enter'})
        run = self.service._active['trial']
        self.rivals = len(run.opposition)
        run.round_number = run.context['dungeon']['rooms']['5:7']['cocoon']['rounds'] + 5
        return self.service.design_action('trial', {'type': 'end_turn'})

    def test_round_thirty_opens_the_regular_tarrasque_without_a_ruling(self):
        result = self.reach_the_cocoon()
        crisis = result['event']['crisis']
        self.assertEqual(crisis['type'], 'cocoon_opened')
        self.assertEqual(crisis['emerges_at_round'], 30)
        # It rises for five rounds, then launches two rounds later at everyone.
        opened_at = self.service._active['trial'].round_number
        self.assertEqual(crisis['rising_until'], opened_at + 5)
        self.assertEqual(crisis['launches_at'], opened_at + 7)
        self.assertEqual(crisis['rules_version'], 'regular 2014 Tarrasque')
        run = self.service._active['trial']
        self.assertIn('tarrasque', [t.rules(run, k).get('identity') for k in t.actors(run)])

    def test_an_explicit_ruling_is_not_required_or_canon_binding(self):
        result = self.reach_the_cocoon(ruling='Corey DESIGN ruling, 2026-09-05 test')
        crisis = result['event']['crisis']
        self.assertEqual(crisis['type'], 'cocoon_opened')
        self.assertEqual(crisis['rules_version'], 'regular 2014 Tarrasque')
        self.assertNotIn('authority', crisis)
        self.assertEqual(crisis['certification'], 'Step 6 final-floor fixture')
        run = self.service._active['trial']
        self.assertIn('tarrasque', [t.rules(run, k).get('identity') for k in t.actors(run)])

    def test_tarrasque_kill_upgrades_a_pre_resolved_boss_room(self):
        self.reach_the_cocoon(ruling='Corey DESIGN ruling, 2026-09-05 test')
        run = self.service._active['trial']
        dungeon.state(run)['final_floor'] = 'boss_victory_only'
        dungeon.room(run)['resolved'] = True
        dungeon.room(run)['reward_claimed'] = True
        for key in t.actors(run):
            if t.rules(run, key).get('identity') == 'tarrasque':
                t.actor(run, key).hp = 0
        result = self.service.design_action('trial', {'type': 'end_turn'})['event']
        self.assertEqual(result['final_floor_completion'], 'actual_final_floor_complete')
        self.assertEqual(self.service.observe('trial')['final_floor'], 'actual_final_floor_complete')

    def test_a_boss_kill_before_the_clock_is_not_a_measured_final_floor(self):
        run = self.service._active['trial']
        dungeon = run.context['dungeon']
        dungeon['floor'], dungeon['room'] = 5, 6
        dungeon['rooms']['5:6'] = {'resolved': True}
        self.service.design_action('trial', {'type': 'enter'})
        self.assertNotEqual(self.service.observe('trial')['final_floor'], 'actual_final_floor_complete')

    def test_cocoon_cracks_two_rounds_before_boundary(self):
        run = self.service._active['trial']
        dungeon = run.context['dungeon']
        dungeon['floor'], dungeon['room'] = 5, 6
        dungeon['rooms']['5:6'] = {'resolved': True}
        self.service.design_action('trial', {'type': 'enter'})
        run = self.service._active['trial']
        clock = run.context['dungeon']['rooms']['5:7']['cocoon']['rounds']
        run.round_number = clock - 2
        result = self.service.design_action('trial', {'type': 'end_turn'})['event']['crisis']
        self.assertEqual(result['type'], 'cocoon_cracked')
        self.assertEqual(result['round'], clock - 2)
        self.assertEqual(result['emerges_at_round'], clock)
        self.assertEqual(self.service.observe('trial')['final_floor_clock']['cracked'], True)


class RunLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = RunService(Path(self.tmp.name) / '.local/reliquary_runs')
        self.service.create('trial', ['Doran', 'Wren'], ['Townsperson'], 'reset-seed')
        self.service.design_start('trial')

    def tearDown(self):
        self.tmp.cleanup()

    def test_retreat_is_durable_and_reset_retains_receipt(self):
        ended = self.service.design_action('trial', {'type': 'retreat'})['event']
        self.assertEqual(ended['status'], 'ejected')
        reset = self.service.design_action('trial', {'type': 'reset'})['event']
        self.assertEqual(reset['reset']['reset_count'], 1)
        self.assertEqual(reset['reset']['permanent_gear_carried'], [])
        self.assertEqual(self.service.observe('trial')['status'], 'active')
        self.assertEqual(self.service._active['trial'].context['reset_history'][0]['status'], 'ejected')
        self.assertEqual(len(self.service.observe('trial')['dungeon_history']), 1)
        self.assertEqual(len(self.service.observe('trial')['reset_history']), 1)

    def test_final_floor_escape_preserves_route_and_cocoon_state(self):
        run=self.service._active['trial']; d=run.context['dungeon']
        d['floor'],d['room']=5,6; d['rooms']['5:6']={'resolved':True}
        self.service.design_action('trial',{'type':'enter'})
        event=self.service.design_action('trial',{'type':'escape','route':'balconies'})['event']
        self.assertEqual(event['status'],'escaped')
        self.assertEqual(event['completion_kind'],'escaped')
        self.assertEqual(event['escape_route'],'balconies')
        self.assertIn('lower route',event['escape_routes'])

    def test_permanent_gear_has_a_distinct_run_ledger(self):
        item=dungeon.add_item(self.service._active['trial'],'permanent_gear')
        state=self.service.observe('trial')
        self.assertFalse(item['temporary'])
        self.assertIn(item['id'],state['permanent_gear'])
        terminal=self.service.design_action('trial', {'type':'retreat'})['event']
        self.assertEqual(terminal['carry_out'][0]['id'],item['id'])
        ended=self.service.observe('trial')
        self.assertIn(item['id'],ended['permanent_gear'])
        self.service.design_action('trial', {'type':'reset'})
        reset_state=self.service.observe('trial')
        self.assertIn(item['id'],reset_state['permanent_gear'])

    def test_explicit_exit_returns_the_next_room_and_transition_evidence(self):
        run=self.service._active['trial']; run.context['dungeon']['rooms']['1:1']['resolved']=True
        event=self.service.design_action('trial',{'type':'exit'})['event']
        self.assertEqual(event['type'],'exited')
        self.assertEqual(event['evidence']['from_room'],'1:1')
        self.assertEqual(event['next']['type'],'entered')


if __name__ == '__main__':
    unittest.main(verbosity=2)
