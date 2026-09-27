"""Saved world time and public ambient speech, including legacy and resume paths."""
import copy
import tempfile
from pathlib import Path

from hollowstar.clock import daylight
from hollowstar.scene import build_scene
from hollowstar.run_service import RunService


def test_daylight_boundaries_and_legacy_projection():
    for hour, phase in [(5, 'dawn'), (7, 'day'), (17, 'dusk'), (19, 'night')]:
        elapsed = ((hour - 8) % 24) * 3600
        assert daylight(elapsed)['lighting_phase'] == phase
        assert daylight(elapsed)['minute_of_day'] == hour * 60
    assert daylight(16 * 3600) == {'day': 2, 'minute_of_day': 0.0, 'lighting_phase': 'night'}
    assert build_scene({'room': {'id': 'market'}})['time'] == daylight(0)
    assert build_scene({'event_clock': {'seconds': 60}, 'daylight_offset_seconds': 300})['time'] == daylight(360)


def test_ambient_public_events_are_clocked_bounded_and_resume_stable():
    with tempfile.TemporaryDirectory() as temp:
        service = RunService(Path(temp) / '.local/reliquary_runs')
        service.create('qol', ['Doran'], ['Townsperson'], seed='qol', scenario='reliquary_city')
        service.design_start('qol')
        run = service._active['qol']
        world = run.context['life_world']
        # A populated public area, with schedules pinned for this time-only fixture.
        for resident in world['residents'].values():
            resident['location'] = world['player']['location']
            resident['schedule'] = []
        first = service.design_action('qol', {'type': 'world_tick', 'elapsed_seconds': 30})['state']
        events = first['ambient_events']
        assert events and len(events[-1]['lines']) == 2
        visible = first['npcs']
        assert all(line['speaker_id'] in visible for line in events[-1]['lines'])
        assert all(set(line) == {'speaker_id', 'speaker', 'text'} for line in events[-1]['lines'])
        stable = copy.deepcopy(service.observe('qol'))
        assert service.observe('qol') == stable
        assert RunService(Path(temp) / '.local/reliquary_runs').observe('qol') == stable
        later = service.design_action('qol', {'type': 'world_tick', 'elapsed_seconds': 1})['state']
        assert later['ambient_events'] == events
        advanced = service.design_action('qol', {'type': 'world_tick', 'elapsed_seconds': 30})['state']
        assert advanced['ambient_events'][-1]['id'] != events[-1]['id']
        assert build_scene(advanced)['time']['minute_of_day'] > build_scene(first)['time']['minute_of_day']


def test_ambient_uses_only_current_visible_residents():
    from hollowstar.life_sim import _ambient_exchange
    world = {'player': {'location': 'market'}, 'status': 'active', 'event_clock': {'seconds': 30},
             'residents': {'a': {'id': 'a', 'name': 'A', 'alive': True, 'location': 'market'},
                           'b': {'id': 'b', 'name': 'B', 'alive': True, 'location': 'elsewhere'}}}
    _ambient_exchange(world, 'test:1')
    assert not world.get('ambient_events')
    world['residents']['b']['location'] = 'market'
    _ambient_exchange(world, 'test:2')
    assert [line['speaker_id'] for line in world['ambient_events'][0]['lines']] == ['a', 'b']
    assert 'elsewhere' not in str(world['ambient_events'])
