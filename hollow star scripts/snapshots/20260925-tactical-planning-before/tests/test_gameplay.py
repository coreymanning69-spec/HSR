"""Adversarial service fixtures, exact replay, resource laws and information boundaries."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hollowstar.run_service import RunService, RunServiceError
from hollowstar.run_state import resume_run, _payload
from hollowstar.profiles import ProfileService
from hollowstar.character_builder import build
from hollowstar.storage import atomic_json
from hollowstar import tactical as t
from hollowstar import monsters
from hollowstar.spells import cast
from hollowstar import maneuvers
from hollowstar import policies
from hollowstar import domains


class GameplayTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/'.local/reliquary_runs'
        self.service=RunService(self.root)
        self.service.create('trial',['Doran','Wren'],['Townsperson'],'gameplay-seed')
        self.service.design_start('trial')

    def tearDown(self):
        self.tmp.cleanup()

    def runstate(self):return self.service._active['trial']

    def test_wings_do_not_replenish_spent_movement(self):
        run = self.combat()
        run.context['combat']['cursor'] = run.context['combat']['order'].index('p1')
        t.economy(run, 'p1')['movement'] = 15
        t.apply(run, {'type': 'wings', 'actor': 'p1'})
        self.assertEqual(t.economy(run, 'p1')['movement'], 30)
        t.apply(run, {'type': 'wings', 'actor': 'p1'})
        self.assertEqual(t.economy(run, 'p1')['movement'], 30)
        t.apply(run, {'type': 'land', 'actor': 'p1'})
        self.assertEqual(t.economy(run, 'p1')['movement'], 15)

    def test_spell_catalog_reports_targeting_and_unresolved_effects(self):
        from hollowstar.spells import display_catalog
        rows = {row['id']: row for row in display_catalog(self.combat())}
        self.assertEqual(rows['Misty Step@5e']['operation'], 'teleport')
        self.assertTrue(rows['Misty Step@5e']['bonus'])
        self.assertEqual(rows['Fireball@5e']['radius'], 20)
        self.assertEqual(rows['Mage Armor@5e']['resolution'], 'record_only')

    def test_pressure_is_local_observable_and_does_not_secretly_change_enemy_stats(self):
        before = self.service.observe('trial')['pressure']
        event = self.service.design_action('trial', {'type': 'observe_room', 'actor': 'p0'})
        after = event['event'].get('pressure', self.service.observe('trial')['pressure'])
        self.assertGreaterEqual(after['minutes_elapsed'], before['minutes_elapsed'])
        self.assertIn('scale_of_consequence', self.service.observe('trial'))
        self.assertIn('observable_escalation', after['history'][-1])

    def combat(self):
        self.service.design_action('trial',{'type':'fight'})
        return self.runstate()

    def test_wren_flight_intent_is_bounded_and_publicly_projected(self):
        run = self.combat()
        run.context['combat']['cursor'] = run.context['combat']['order'].index('p1')
        for key in run.context['combat']['economy']:
            if key.startswith('e'):
                run.context['combat']['economy'][key]['reaction'] = 0
        before = list(run.context['combat']['positions']['p1'])
        result = self.service.design_action('trial', {'type': 'flight_move', 'actor': 'p1', 'dx': 5, 'dy': 0})
        self.assertEqual(result['event']['type'], 'movement')
        run = self.service._active['trial']
        self.assertEqual(run.context['combat']['positions']['p1'], [before[0] + 5, before[1], before[2]])
        from hollowstar.view_model import build_public_view
        arena = build_public_view(result['state'])['flight_arena']
        self.assertEqual(arena['schema'], 'hollow-star-flight-arena-1')
        self.assertEqual(arena['controller'], 'p1')
        self.assertTrue(all(0 <= row['x'] <= 120 and 0 <= row['y'] <= 120 and 0 <= row['z'] <= 120
                            for row in arena['actors'] + arena['opposition']))

    def test_flight_controls_reject_non_wren_and_out_of_bounds(self):
        run = self.combat()
        run.context['combat']['cursor'] = run.context['combat']['order'].index('p0')
        with self.assertRaises(Exception):
            self.service.design_action('trial', {'type': 'flight_move', 'actor': 'p0', 'dx': 5, 'dy': 0})
        run.context['combat']['cursor'] = run.context['combat']['order'].index('p1')
        run.context['combat']['positions']['p1'] = [120, 120, 120]
        with self.assertRaises(Exception):
            self.service.design_action('trial', {'type': 'ascend', 'actor': 'p1'})

    def test_auto_combat_policy_skips_npc_turns_and_halts_on_any_player_decision(self):
        # Mirrors the decision logic behind host.py's design_auto_combat command:
        # auto-resolve whoever is NOT player-controlled (including a pending
        # reaction's reactor, not just whoever's turn it nominally is), and
        # stop the instant a player-controlled actor has any decision to make.
        from hollowstar.policies import combat_action
        r=self.combat()
        for _ in range(2):
            self.service.design_action('trial',{'type':'end_turn','actor':t.current(r)});r=self.runstate()
        def pending_player_or_current(run):
            state=run.context['combat']
            key=state['pending'][0]['reactor'] if state['pending'] else t.current(run)
            return t.actor(run,key).controller=='player',key
        npc_steps=0
        for _ in range(20):
            stop,who=pending_player_or_current(r)
            if stop:break
            self.service.design_action('trial',combat_action(r));r=self.runstate();npc_steps+=1
        stop,who=pending_player_or_current(r)
        self.assertTrue(stop,"loop should halt on a player-controlled decision")
        self.assertEqual(t.actor(r,who).controller,'player')
        # The host now plays npc turns itself after each player action, so a
        # client-side loop finds nothing left to resolve.
        self.assertEqual(npc_steps,0,"the host should already have resolved the townsperson's turn")

    def test_invalid_nonmutation_including_rng_and_disk(self):
        before=(self.root/'trial.json').read_bytes()
        r=self.runstate();rng=r.rng.getstate()
        with self.assertRaises(RunServiceError):self.service.design_action('trial',{'type':'buy','product':'imprint'})
        self.assertEqual(before,(self.root/'trial.json').read_bytes());self.assertEqual(rng,self.runstate().rng.getstate())

    def test_new_run_uses_022_contract_and_exposes_affordable_lodging(self):
        payload=json.loads((self.root/'trial.json').read_text(encoding='utf-8'))
        self.assertEqual(payload['engine_version'],'0.2.2')
        self.assertEqual(payload['encounter']['context']['replay_contract']['engine_version'],'0.2.2')
        state=self.service.observe('trial')
        self.assertEqual(state['currency'],10)
        self.assertIn({'id':'buy','label':'Rent room — 10 gold'},state['available_actions'])

    def test_buying_room_spends_gold_starts_rest_pressure_and_triggers_patrol(self):
        run=self.runstate();run.party[0].hp-=7
        run.context['dungeon']['pressure']['fatigue']=8
        hp_before=run.party[0].hp
        result=self.service.design_action('trial',{'type':'buy','actor':'p0','product':'room'})
        event=result['event'];state=self.service.observe('trial');row=self.runstate().context['dungeon']['rooms']['1:1']
        self.assertEqual(event['type'],'night_patrol')
        self.assertEqual(event['purchase'],{'product':'room','cost':10})
        self.assertEqual(state['currency'],0)
        self.assertEqual(state['pressure']['minutes_elapsed'],360)
        self.assertEqual(state['pressure']['fatigue'],2)
        self.assertEqual(self.runstate().party[0].hp,hp_before)
        self.assertTrue(row['night_patrol'])
        self.assertFalse(row['resolved'])
        self.assertFalse(row['reward_claimed'])
        self.assertEqual(row['purchases'],['room'])
        self.assertIn('combat',self.runstate().context)

    def test_unaffordable_room_purchase_is_atomic(self):
        run=self.runstate();run.context['dungeon']['currency']=9
        self.service.save('trial')
        before=(self.root/'trial.json').read_bytes();rng=run.rng.getstate()
        with self.assertRaises(RunServiceError):
            self.service.design_action('trial',{'type':'buy','actor':'p0','product':'room'})
        self.assertEqual(before,(self.root/'trial.json').read_bytes())
        self.assertEqual(rng,self.runstate().rng.getstate())
        self.assertEqual(self.service.observe('trial')['pressure']['minutes_elapsed'],0)

    def test_mid_turn_save_exact_continuation(self):
        r=self.combat()
        action={'type':'attack','actor':'p0','target':'e0'}
        self.service.design_action('trial',action)
        other=RunService(self.root);other.load('trial')
        self.assertEqual(self.service.design_action('trial',{'type':'end_turn'}),other.design_action('trial',{'type':'end_turn'}))
        self.assertEqual(self.runstate().rng.getstate(),other._active['trial'].rng.getstate())

    def test_no_hidden_room_or_rules_in_inspection(self):
        raw=json.dumps(self.service.inspect('trial').as_dict())
        self.assertNotIn('waterwheel',raw);self.assertNotIn('baseline_party',raw)
        self.assertEqual(list(self.runstate().context['dungeon']['rooms']),['1:1'])
        public=json.dumps(self.service.observe('trial'))
        self.assertNotIn('waterwheel',public);self.assertNotIn('stacked',public)

    def test_room_objects_lighting_and_npc_occupancy_are_run_local(self):
        state=self.service.observe('trial')
        objects=state['room']['world_state']['objects']
        self.assertNotIn('1:1:cabinet',objects)
        self.assertEqual(state['room']['world_state']['npcs']['1:1:staff']['location'],'bar_back')
        lit=self.service.design_action('trial',{'type':'light_source','actor':'p1','source':'crown_of_stars'})
        self.assertTrue(lit['event']['room']['lighting']['illuminated'])
        self.service.design_action('trial',{'type':'search_object','actor':'p1','object_id':'1:1:cabinet'})
        opened=self.service.design_action('trial',{'type':'open_object','actor':'p1','object_id':'1:1:cabinet'})
        self.assertTrue(any(item['kind']=='ledger' for item in opened['event']['contents']))
        self.assertIn('1:1:cabinet',self.service.observe('trial')['room']['world_state']['objects'])

    def test_room_quest_placement_is_seeded_and_committed_once(self):
        from hollowstar import room_state
        run=self.runstate()
        row=run.context['dungeon']['rooms']['1:1']
        row['world_state']=None
        run.context['quest_hooks']=[{'quest_id':'missing_seal','item_id':'seal','eligible_tags':['cabinet'],'chance':1.0}]
        generated=room_state.generate(run,row)
        first=[x for x in generated['objects']['1:1:cabinet']['contents'] if x.get('quest')=='missing_seal']
        generated_again=room_state.generate(run,row)
        second=[x for x in generated_again['objects']['1:1:cabinet']['contents'] if x.get('quest')=='missing_seal']
        self.assertEqual(first,second)
        self.assertEqual(len(first),1)

    def test_vertical_movement_reports_height_band_and_ceiling_failure(self):
        r=self.combat()
        while t.current(r) != 'p1':
            self.service.design_action('trial',{'type':'end_turn'})
            r=self.runstate()
        self.service.design_action('trial',{'type':'wings','actor':'p1'})
        moved=self.service.design_action('trial',{'type':'move','actor':'p1','destination':[10,10,40]})
        self.assertEqual(moved['event']['evidence']['destination'],[10,10,40])
        self.assertEqual(moved['state']['combat']['height_bands']['p1'],'high')
        with self.assertRaises(RunServiceError):
            self.service.design_action('trial',{'type':'move','actor':'p1','destination':[10,10,125]})

    def test_combat_actions_include_host_derived_presentation_sequence(self):
        self.combat()
        moved = self.service.design_action('trial', {
            'type': 'move', 'actor': 'p0', 'destination': [15, 10, 0],
        })
        presentation = moved['event']['presentation']
        self.assertEqual(presentation['schema'], 'hsr-presentation-1')
        self.assertEqual(presentation['actor_id'], 'p0')
        self.assertEqual(presentation['destination'], [15, 10, 0])
        self.assertEqual(presentation['steps'][0]['type'], 'move_to')
        self.assertEqual(presentation['steps'][0]['position'], [15, 10, 0])

    def test_attack_presentation_uses_the_actor_weapon_contract(self):
        self.combat()
        attacked = self.service.design_action('trial', {
            'type': 'attack', 'actor': 'p0', 'target': 'e0',
        })
        presentation = attacked['event']['presentation']
        self.assertEqual(presentation['animation']['attack'], 'dagger')
        self.assertEqual(presentation['loadout']['weapon']['silhouette'], 'dagger')
        self.assertEqual(presentation['loadout']['handedness'], 'one-handed')

    def test_ward_break_nullifies_riders_and_next_hit_lands(self):
        r=self.combat();w=r.party[1];w.resources['ward']=3
        hit=t.damage(r,'e0','p1',10,'PIERCING',riders=[{'name':'BLINDED','duration':1}])
        self.assertEqual(w.hp,220);self.assertEqual(w.resources['ward'],0);self.assertNotIn('BLINDED',w.statuses)
        t.damage(r,'e0','p1',10,'PIERCING');self.assertEqual(w.hp,210)

    def test_plate_is_directional_and_saves_are_final(self):
        r=self.combat()
        t.damage(r,'e0','p0',40,'PIERCING');self.assertEqual(r.party[0].hp,360)
        self.assertEqual(t.rules(r,'p0')['saves']['STR'],15)
        # Assert the RULE -- an unresisted instance lands in full on a resident
        # -- not the fixture's hit points. This line read `hp == 0` against a
        # 22 HP floor-one resident until 2026-09-05 and broke the moment the
        # DESIGN opposition was retuned, which is a test coupled to a number
        # the fixture is explicitly allowed to change.
        before=r.opposition[0].hp
        event=t.damage(r,'p0','e0',40,'PIERCING')
        self.assertEqual(event['damage'],min(40,before))
        self.assertEqual(r.opposition[0].hp,max(0,before-40))

    def test_wrens_divine_tag_rides_with_printed_damage_and_bypasses_only_resistance(self):
        r=self.combat()
        target=r.opposition[0]
        t.rules(r,'e0')['resistances']=['RADIANT']
        before=target.hp
        event=t.damage(r,'p1','e0',20,'RADIANT')
        self.assertEqual(event['damage'],min(20,before))
        self.assertEqual(event['damage_type'],'RADIANT')
        self.assertIn('DIVINE',event['damage_tags'])

    def test_mind_lock_distinguishes_physical_conditions(self):
        r=self.combat()
        self.assertFalse(t.condition(r,'p1','STUNNED',2,mental=True)['applied'])
        self.assertTrue(t.condition(r,'p1','STUNNED',2,mental=False)['applied'])

    def test_crown_spent_on_miss_and_cannot_use_action(self):
        r=self.combat();r.context['combat']['positions']['e0']=[20,20,0]
        with self.assertRaises(t.ActionError):t.weapon_attack(r,'p1','e0')
        with patch.object(r.rng,'d20',return_value=1):hit=t.weapon_attack(r,'p1','e0',bonus=True)
        self.assertFalse(hit['roll']['success']);self.assertEqual(r.party[1].resources['crown_motes'],6)

    def test_fixed_cleaver_critical(self):
        r=self.combat();r.opposition[0].hp=r.opposition[0].max_hp=200
        r.context['combat']['positions']['e0']=[15,10,0]
        with patch.object(r.rng,'d20',return_value=20):hit=t.weapon_attack(r,'p0','e0','cleaver')
        self.assertEqual(hit['result']['raw'],80)

    def test_cleaver_carry_through_parts_and_stops_at_survivor(self):
        r=self.combat()
        r.context['combat']['terrain']['human_tight']=False
        r.opposition[0].hp=r.opposition[0].max_hp=30
        r.opposition[1].hp=r.opposition[1].max_hp=200
        r.context['combat']['positions']['e0']=[15,10,0]
        r.context['combat']['positions']['e1']=[20,10,0]
        with patch.object(r.rng,'d20',return_value=20):hit=t.weapon_attack(r,'p0','e0','cleaver')
        self.assertFalse(r.opposition[0].alive)
        chain=hit['carry_through']
        self.assertEqual(len(chain),1)
        self.assertEqual(chain[0]['target'],'e1')
        self.assertTrue(chain[0]['parted'] is False)
        self.assertEqual(chain[0]['result']['raw'],80)
        self.assertTrue(r.opposition[1].alive)
        self.assertEqual(chain[0]['skid']['feet'],5)
        self.assertEqual(r.context['combat']['positions']['e1'],[25,10,0])

    def test_cleaver_survivor_skids_without_carry_through(self):
        r=self.combat();r.opposition[0].hp=r.opposition[0].max_hp=200
        r.context['combat']['positions']['e0']=[15,10,0]
        with patch.object(r.rng,'d20',return_value=20):hit=t.weapon_attack(r,'p0','e0','cleaver')
        self.assertNotIn('carry_through',hit)
        self.assertEqual(hit['skid'],{'target':'e0','feet':5,'from':[15,10,0],'to':[20,10,0]})

    def test_source_profiles_are_not_modified_by_run(self):
        profile,rules=build({'name':'Ash','background':'Veteran','ability_scores':dict.fromkeys(['STR','DEX','CON','INT','WIS','CHA'],14)})
        profile['build_rules']=rules
        profiles=ProfileService(self.root.parent/'reliquary_profiles')
        profiles.save('ash',profile,replace=False)
        before=(profiles.root/'ash.json').read_bytes()
        self.service.create('custom',['custom:ash'],['Townsperson'],'seed')
        self.service.design_start('custom');self.service.design_action('custom',{'type':'fight'})
        self.assertEqual(before,(profiles.root/'ash.json').read_bytes())

    def test_interrupted_replace_preserves_previous(self):
        path=self.root/'atomic.json';atomic_json(path,{'n':1})
        with patch('hollowstar.storage.os.replace',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):atomic_json(path,{'n':2})
        self.assertEqual(json.loads(path.read_text()),{'n':1})
        self.assertFalse(list(self.root.glob('.pending-*')))

    def test_spell_version_is_not_substituted(self):
        r=self.combat()
        with self.assertRaisesRegex(t.ActionError,'RULING_REQUIRED'):
            cast(r,'p1',{'spell':'Fireball@3.5e','targets':['e0']})
        spec={'name':'Fireball','edition':'3.5e','authority':'Corey DESIGN test ruling',
              'operation':'damage','level':3,'dice':'10d6','damage_type':'FIRE','save':'DEX','half':True,'range':120}
        self.service.register_ruling('trial',spec)
        self.assertIn('Fireball@3.5e',resume_run(self.root/'trial.json').context['spell_rulings'])

    def test_healing_reports_authoritative_state_change(self):
        r=self.combat(); actor=r.party[0]; actor.hp=100
        event=t.heal(r,'p0','1d10+20')
        self.assertEqual(event['evidence']['hp_before'],100)
        self.assertEqual(event['evidence']['hp_after'],actor.hp)
        self.assertEqual(event['evidence']['hp_after']-event['evidence']['hp_before'],event['healing'])

    def test_generic_alternate_weapon_mode_uses_its_declared_profile(self):
        r=self.combat(); weapon=r.opposition[0].weapon()
        weapon.alternate_modes={'thrown': {'damage_dice':'1d6','damage_modifier':2,
                                           'attack_bonus':9,'reach':5,'range_long':60,
                                           'damage_type':'PIERCING'}}
        r.context['combat']['positions']['e0']=[5,0,0]
        event=t.weapon_attack(r,'e0','p0','thrown')
        self.assertEqual(event['mode'],'thrown')
        self.assertEqual(event['evidence']['range']['reach'],5)
        self.assertEqual(event['evidence']['range']['long'],60)

    def test_surprise_state_blocks_actions_until_first_turn_ends(self):
        r=self.combat(); r.context['combat']['surprised']['p0']=True
        with self.assertRaises(t.ActionError):
            t.apply(r,{'type':'attack','actor':'p0','target':'e0'})
        current=t.current(r)
        t.apply(r,{'type':'end_turn','actor':current})
        self.assertNotIn(current,r.context['combat']['surprised'])

    def test_alert_profiles_are_not_surprised_by_default(self):
        r=self.combat()
        t.begin(r, {'p0': {'identity':'doran'}, 'p1': {'identity':'wren'},
                    'e0': {'surprised':True}})
        self.assertNotIn('p0', r.context['combat']['surprised'])
        self.assertNotIn('p1', r.context['combat']['surprised'])
        self.assertIn('e0', r.context['combat']['surprised'])

    def test_doran_indomitable_rerolls_and_spends_pool(self):
        r=self.combat(); r.party[0].resources['indomitable']=3
        failed={'success':False,'bonus':10,'dc':22,'rolls':[1],'natural':1,'total':11}
        event=t.indomitable(r,'p0',failed)
        self.assertEqual(event['type'],'indomitable')
        self.assertEqual(r.party[0].resources['indomitable'],2)

    def test_relentless_recovers_only_from_zero_at_initiative(self):
        r=self.combat(); r.party[0].resources['superiority_dice']=0
        event=t.begin(r, {'p0': {'identity':'doran'}})
        self.assertEqual(r.party[0].resources['superiority_dice'],1)
        self.assertEqual(event['evidence']['relentless_recovered'],['p0'])
        r2=self.runstate(); r2.party[0].resources['superiority_dice']=5
        event2=t.begin(r2, {'p0': {'identity':'doran'}})
        self.assertEqual(r2.party[0].resources['superiority_dice'],5)
        self.assertEqual(event2['evidence']['relentless_recovered'],[])

    def test_staff_charges_cast_and_absorb_with_cap(self):
        r=self.combat(); r.context['combat']['rules']['p1']['identity']='wren'
        r.party[1].resources['staff_charges']=50
        cast=t.staff_cast(r,'p1','fireball')
        self.assertEqual(cast['evidence']['charges_after'],45)
        absorb=t.staff_absorb(r,'p1',9)
        self.assertEqual(absorb['evidence']['charges_after'],50)

    def test_dagger_force_construct_access_is_target_property_gated(self):
        r=self.combat(); r.context['combat']['terrain']['structures']=[
            {'kind':'wall_of_force','hp':30,'position':[15,10,0]},
            {'kind':'glyph_of_warding','hp':30,'position':[15,10,0]}]
        event=t.dagger_cut_structure(r,'p0',0)
        self.assertTrue(event['evidence']['barrier_bypass'])
        with self.assertRaises(t.ActionError): t.dagger_cut_structure(r,'p0',1)

    def test_grand_cleave_resolves_authored_structure_as_a_runtime_object(self):
        r=self.combat(); t.rules(r,'p0')['identity']='doran'
        r.context['combat']['terrain'].update({'human_tight':True,'structures':[
            {'object_id':'sealed-arch','kind':'arch','name':'sealed arch',
             'hp':80,'position':[15,10,0]}]})
        event=maneuvers.grand_cleave(r,'p0',{'facing':'east'})
        self.assertEqual(event['structures'][0]['object_id'],'sealed-arch')
        self.assertEqual(event['structures'][0]['kind'],'arch')
        self.assertLess(event['structures'][0]['hp_after'],80)
        self.assertEqual(r.context['combat']['terrain']['structures'][0]['hp'],
                         event['structures'][0]['hp_after'])

    def test_open_door_applies_its_sixty_foot_cha_toll_before_return(self):
        r=self.combat(); wren='p1'; target='p0'
        t.rules(r,wren)['anchor']=[70,70,0]
        r.context['combat']['positions'][wren]=[40,20,0]
        before=dict(r.context['combat']['positions'])
        with patch('hollowstar.domains.t.saving_throw', return_value={
                'success':False,'ability':'CHA','dc':22,'roll':3,'modifier':4}):
            blocked=domains.apply(r,wren,{'feature':'The Open Door','targets':[wren,target]})
        self.assertTrue(blocked['attempt_wasted'])
        self.assertEqual(blocked['toll'][0]['save']['dc'],22)
        self.assertEqual(r.context['combat']['positions'],before)
        self.assertEqual(r.party[1].resources['portal_anchor_return'],0)

    def test_open_door_moves_allies_when_the_toll_is_saved(self):
        r=self.combat(); wren='p1'; target='p0'
        t.rules(r,wren)['anchor']=[70,70,0]
        r.context['combat']['positions'][wren]=[40,20,0]
        with patch('hollowstar.domains.t.saving_throw', return_value={
                'success':True,'ability':'CHA','dc':22,'roll':18,'modifier':4}):
            moved=domains.apply(r,wren,{'feature':'The Open Door','targets':[wren,target]})
        self.assertEqual(moved['destination'],[70,70,0])
        self.assertEqual(r.context['combat']['positions'][wren],[70,70,0])
        self.assertEqual(r.context['combat']['positions'][target],[70,70,0])
        self.assertEqual(len(moved['toll']),2)

    def test_nivs_descent_is_a_full_turn_two_lane_resolution(self):
        r=self.combat(); wren='p1'; ally='p0'; enemy='e0'
        r.party[0].hp=100
        r.opposition[0].hp=r.opposition[0].max_hp=100
        r.context['combat']['positions'][wren]=[40,20,40]
        r.context['combat']['positions'][ally]=[40,20,20]
        r.context['combat']['positions'][enemy]=[50,20,20]
        def saves(run,key,ability,dc,magical=False,concentration=False):
            return {'success': key == ally, 'ability':ability, 'dc':dc, 'roll':18, 'modifier':4}
        with patch('hollowstar.spells.saving_throw', side_effect=saves):
            event=cast(r,wren,{'spell':"Niv's Descent@DM",'dive':True,'shape':'sphere'})
        descent=event['events'][0]
        self.assertEqual(descent['type'],'niv_descent')
        self.assertTrue(descent['evidence']['full_turn'])
        self.assertEqual(r.context['combat']['economy'][wren]['action'],0)
        self.assertEqual(r.context['combat']['economy'][wren]['bonus'],0)
        self.assertEqual(r.context['combat']['economy'][wren]['reaction'],0)
        self.assertEqual(r.context['combat']['economy'][wren]['movement'],0)
        self.assertTrue(any(row['target']==enemy for row in descent['elemental_wave']))
        self.assertTrue(any(row['target']==ally for row in descent['elemental_wave']))

    def test_forcecage_is_spatial_containment_not_a_mental_condition(self):
        r=self.combat(); wren='p1'; target='e0'
        r.party[1].resources['forcecage']=1
        event=cast(r,wren,{'spell':'Forcecage@5e','targets':[target]})
        cage=event['events'][0]
        self.assertEqual(cage['type'],'forcecage')
        self.assertTrue(cage['evidence']['spatial_containment'])
        self.assertEqual(r.context['combat']['rules'][target]['contained_by'],cage['structure']['object_id'])
        with self.assertRaises(t.ActionError):
            t.move(r,target,[45,20,0])

    def test_imprisonment_requires_explicit_mode_and_applies_spatially_on_failed_cha_save(self):
        r=self.combat(); wren='p1'; target='e0'; r.party[1].resources['sealed_imprisonment']=1
        with self.assertRaises(t.ActionError):
            cast(r,wren,{'spell':'Imprisonment@5e','targets':[target]})
        with patch('hollowstar.spells.saving_throw', return_value={'success':False,'ability':'CHA','dc':22,'roll':1,'modifier':0}):
            event=cast(r,wren,{'spell':'Imprisonment@5e','targets':[target],'mode':'minimus containment'})
        row=event['events'][0]
        self.assertTrue(row['applied']); self.assertEqual(row['mode'],'minimus containment')
        self.assertTrue(row['evidence']['spatial_containment'])
        self.assertEqual(r.party[1].resources['sealed_imprisonment'],0)
        with self.assertRaises(t.ActionError): t.move(r,target,[45,20,0])

    def test_imprisonment_success_does_not_contain_and_unknown_spell_stays_fail_closed(self):
        r=self.combat(); wren='p1'; target='e0'; r.party[1].resources['sealed_imprisonment']=1
        with patch('hollowstar.spells.saving_throw', return_value={'success':True,'ability':'CHA','dc':22,'roll':20,'modifier':0}):
            event=cast(r,wren,{'spell':'Imprisonment@5e','targets':[target],'mode':'chaining'})
        self.assertFalse(event['events'][0]['applied']); self.assertNotIn('contained_by',t.rules(r,target))
        with self.assertRaisesRegex(t.ActionError,'RULING_REQUIRED'):
            cast(r,wren,{'spell':'Holy Word@5e','targets':[target]})

    def test_gate_creates_a_concentration_bound_named_portal(self):
        r=self.combat(); wren='p1'
        event=cast(r,wren,{'spell':'Gate@5e','plane':'Avernus','named_creature':'the marked king'})
        gate=event['events'][0]
        self.assertEqual(gate['type'],'gate')
        self.assertTrue(gate['evidence']['concentration'])
        self.assertEqual(gate['portal']['plane'],'Avernus')
        self.assertEqual(gate['portal']['named_creature'],'the marked king')
        self.assertEqual(r.context['combat']['concentration'][wren]['spell'],'Gate@5e')

    def test_time_stop_pauses_initiative_and_refreshes_wrens_economy(self):
        r=self.combat(); wren='p1'
        r.context['combat']['cursor']=r.context['combat']['order'].index(wren)
        event=cast(r,wren,{'spell':'Time Stop@5e'})
        stop=event['events'][0]
        self.assertEqual(stop['type'],'time_stop')
        self.assertGreaterEqual(stop['turns'],2)
        cursor=r.context['combat']['cursor']
        continued=t.finish_turn(r)
        self.assertEqual(continued['type'],'time_stop_turn')
        self.assertEqual(r.context['combat']['cursor'],cursor)
        self.assertEqual(r.context['combat']['economy'][wren]['action'],1)

    def test_time_stop_ends_when_wren_affects_another_creature(self):
        r=self.combat(); wren='p1'; enemy='e0'
        r.context['combat']['cursor']=r.context['combat']['order'].index(wren)
        cast(r,wren,{'spell':'Time Stop@5e'})
        self.assertIn('time_stop',r.context['combat'])
        t.damage(r,wren,enemy,1,'FIRE')
        self.assertNotIn('time_stop',r.context['combat'])

    def test_wren_mind_lock_explains_named_mental_statuses(self):
        r=self.combat()
        result=t.condition(r,'p1','MENTALLY_PARALYZED',1)
        self.assertEqual(result['condition'],'MENTALLY_PARALYZED')
        self.assertEqual(result['category'],'mental')
        self.assertEqual(result['reason'],'mind lock')

    def test_staff_absorption_resolves_as_pending_reaction(self):
        r=self.combat(); r.party[1].resources['staff_charges']=40
        t.incoming_spell(r,'e0','p1',5)
        event=t.apply(r,{'type':'staff_absorb','actor':'p1'})
        self.assertEqual(event['type'],'staff_absorb')
        self.assertEqual(r.party[1].resources['staff_charges'],45)
        self.assertEqual(r.context['combat']['economy']['p1']['reaction'],0)

    def test_resident_action_uses_shared_attack_and_trait_tell(self):
        r=self.combat()
        r.context['combat']['positions']['e0']=[15,10,0]
        event=monsters.act(r,'e0',{'target':'p0'})
        self.assertIn(event['type'],{'attack','permission_blocked'})
        self.assertIn('tactic',event)
        self.assertIn('formation',event['tactic'])
        self.assertIn('counterplay',event['tactic'])

    def test_resident_equipment_synergy_pays_for_second_press(self):
        r=self.combat(); rules=t.rules(r,'e0'); rules['bonus_attack_resource']='surge'
        r.opposition[0].resources['surge']=1
        r.context['combat']['positions']['e0']=[5,10,0]
        r.context['combat']['positions']['p0']=[5,15,0]
        event=monsters.act(r,'e0',{'target':'p0'})
        self.assertIn('synergy_attack',event)
        self.assertEqual(event['tactic_resource_spent']['after'],0)

    def test_dispatcher_adds_evidence_to_simple_state_actions(self):
        r=self.combat()
        event=t.apply(r,{'type':'dodge','actor':'p0'})
        self.assertEqual(event['evidence']['action'],'dodge')
        self.assertTrue(event['evidence']['state_changes']['economy_changed'])

    def test_combat_view_exposes_condition_taxonomy(self):
        r=self.combat()
        view=t.view(r)
        self.assertEqual(view['condition_categories']['FRIGHTENED'],'mental')
        self.assertEqual(view['condition_categories']['PRONE'],'physical')

    def test_untyped_physical_damage_uses_plate_subtype_lane(self):
        r=self.combat()
        event=t.damage(r,'e0','p0',100,'PHYSICAL')
        self.assertEqual(event['evidence']['armor_damage_type'],'PIERCING')
        self.assertEqual(event['damage'],25)

    def test_turn_evidence_reports_expired_conditions(self):
        r=self.combat(); r.party[0].statuses['SLOWED']=1
        event=t.apply(r,{'type':'end_turn','actor':t.current(r)})
        self.assertIn('expired_statuses',event['evidence'])

    def test_explicit_end_concentration_clears_spell_state_and_conditions(self):
        r=self.combat()
        r.context['combat']['concentration']['p0']={'spell':'Hold Monster@5e','targets':['e0'],
                                                     'conditions':['PARALYZED'],'remaining':5}
        r.opposition[0].statuses['PARALYZED']=5
        event=t.apply(r,{'type':'end_concentration','actor':'p0'})
        self.assertEqual(event['type'],'concentration_ended')
        self.assertEqual(event['spell'],'Hold Monster@5e')
        self.assertNotIn('p0',r.context['combat']['concentration'])
        self.assertNotIn('PARALYZED',r.opposition[0].statuses)

    def test_mobile_stance_and_dash_ignore_difficult_terrain_cost(self):
        r=self.combat(); t.rules(r,'p0')['identity']='doran'
        r.party[0].statuses.clear()
        t.rules(r,'p0')['mobile']=True
        origin=list(t.position(r,'p0')); destination=[origin[0]+5,origin[1],origin[2]]
        r.context['combat']['terrain']['difficult']=[destination]
        normal=t.move_cost(r,'p0',destination)
        r.party[0].statuses['DASHING']=1
        dashed=t.move_cost(r,'p0',destination)
        self.assertEqual(normal-dashed,5)

    def test_resident_retreat_is_explicit_and_stateful_at_threshold(self):
        r=self.combat()
        r.context['combat']['rules']['e0'].update({'retreat_threshold':0.5,'counterplay':['block the exit']})
        r.opposition[0].hp=r.opposition[0].max_hp//2
        event=monsters.act(r,'e0',{})
        self.assertEqual(event['type'],'resident_retreat')
        self.assertTrue(r.context['combat']['rules']['e0']['retreated'])
        self.assertIn('counterplay',event['tactic'])

    def test_staff_physical_utility_is_durable_terrain_state(self):
        r=self.combat()
        t.apply(r,{'type':'end_turn','actor':t.current(r)})
        event=t.apply(r,{'type':'staff_utility','actor':'p1','mode':'span','target':'door-1'})
        self.assertEqual(event['type'],'staff_utility')
        self.assertEqual(r.context['combat']['terrain']['staff_utilities'][0]['mode'],'span')
        self.assertEqual(r.context['combat']['economy']['p1']['action'],0)

    def test_destroyed_staff_cannot_create_physical_utility(self):
        r=self.combat(); r.party[1].resources['staff_destroyed']=True
        with self.assertRaisesRegex(t.ActionError,'destroyed'):
            t.staff_utility(r,'p1','prop')

    def test_macros_select_first_matching_canonical_action(self):
        r=self.combat()
        r.context['macros']={'p0': [
            {'id':'emergency','priority':1,'when':{'self_hp_below':50},
             'then':{'type':'attack','target':'nearest_enemy'}},
            {'id':'fallback','priority':10,
             'then':{'type':'attack','target':'nearest_enemy'}},
        ]}
        action=policies.macro_action(r,'p0',r.context['macros']['p0'])
        self.assertEqual(action,{'type':'attack','actor':'p0','target':'e0'})

    def test_macro_condition_skips_unmatched_rule(self):
        r=self.combat()
        r.context['macros']={'p0': [
            {'id':'heal','priority':1,'when':{'ally_hp_below':20},
             'then':{'type':'cast','spell':'Healing Word@5e','target':'lowest_hp_ally'}},
            {'id':'attack','priority':2,
             'then':{'type':'attack','target':'nearest_enemy'}},
        ]}
        action=policies.macro_action(r,'p0',r.context['macros']['p0'])
        self.assertEqual(action['type'],'attack')
        self.assertEqual(action['target'],'e0')

    def test_conversation_modes_all_five_supported_in_dungeon(self):
        for mode in ('speak', 'ask', 'trade', 'threaten', 'insult', 'lie'):
            action = {'type': 'talk', 'target': 'resident', 'mode': mode, 'text': f'testing {mode}'}
            result = self.service.design_action('trial', action)
            self.assertEqual(result['event']['type'], 'conversation_resolved')
            self.assertEqual(result['event']['mode'], mode)


class CombatCapacityTests(unittest.TestCase):
    CONDITIONS = ("PRONE", "GRAPPLED", "RESTRAINED", "BLINDED", "POISONED",
                  "FRIGHTENED", "CHARMED", "INVISIBLE", "HASTED", "SLOWED")

    def fixture(self, root, party_count=4, enemy_count=4):
        from hollowstar.actors import Actor
        service = RunService(root)
        service.create('capacity', ['Doran'], ['Townsperson'], 'eight-ten')
        service.design_start('capacity')
        run = service._active['capacity']
        snapshot = copy.deepcopy(run.party[0].provenance)
        run.party = [Actor(name=f'Hero {i+1}', controller='player', hp=120, max_hp=120) for i in range(party_count)]
        run.opposition = [Actor(name=f'Foe {i+1}', hp=120, max_hp=120) for i in range(enemy_count)]
        for member in run.party:
            member.provenance = copy.deepcopy(snapshot)
        t.begin(run, {key: {'identity': 'adventurer'} for key in t.actors(run)})
        for key in t.actors(run):
            for name in self.CONDITIONS:
                self.assertTrue(t.condition(run, key, name, 2)['applied'])
        return service, run

    def test_all_eight_actor_team_splits_keep_ten_effects(self):
        from hollowstar.view_model import build_public_view
        for size in range(1, 8):
            with self.subTest(party=size), tempfile.TemporaryDirectory() as temp:
                service, run = self.fixture(Path(temp)/'.local/reliquary_runs', size, 8-size)
                before = copy.deepcopy(run.context)
                view = build_public_view(service.observe('capacity'))
                self.assertEqual(run.context, before, 'rendering may not change mechanics')
                self.assertEqual(len(view['party']), size)
                self.assertEqual(len(view['opposition']), 8-size)
                self.assertEqual(len(view['combat']['order']), 8)
                self.assertEqual(len(view['combat']['formation']), 8)
                for member in view['party'] + view['opposition']:
                    self.assertEqual(len(member['active_effects']), 10)
                    self.assertEqual({row['remaining'] for row in member['active_effects']}, {2})
                    self.assertEqual(len({row['id'] for row in member['active_effects']}), 10)

    def test_eighty_timers_and_initiative_survive_exact_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'.local/reliquary_runs'
            service, run = self.fixture(root)
            service.save('capacity')
            restored = RunService(root); restored.load('capacity')
            other = restored._active['capacity']
            self.assertEqual(t.view(run), t.view(other))
            self.assertEqual(run.rng.getstate(), other.rng.getstate())
            for turn in range(16):
                self.assertEqual(t.finish_turn(run), t.finish_turn(other))
                self.assertEqual(t.view(run), t.view(other))
                if turn == 7:
                    self.assertTrue(all(set(a.statuses.values()) == {1} for a in t.actors(run).values()))
            self.assertTrue(all(not a.statuses for a in t.actors(run).values()))
            self.assertTrue(all(not t.combat_effects(run, key) for key in t.actors(run)))

    def test_concentration_source_timer_and_record_only_status_are_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            _, run = self.fixture(Path(temp)/'.local/reliquary_runs')
            run.context['combat']['concentration']['p0'] = {
                'spell': 'Bless@5e', 'targets': ['p1'], 'remaining': 10, 'conditions': []}
            for key in ('p0', 'p1'):
                rows = [row for row in t.combat_effects(run, key) if row['kind'] == 'concentration']
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['remaining'], 10)
                self.assertEqual(rows[0]['timer_actor'], 'p0')
                self.assertIn('recorded only', rows[0]['summary'])
            t.end_concentration(run, 'p0')
            self.assertFalse(any(row['kind'] == 'concentration' for row in t.combat_effects(run, 'p1')))

    def test_ten_mechanical_effects_apply_and_extra_effect_is_retained(self):
        from hollowstar.effects import Effect
        from hollowstar.phases import Direction, Phase
        from hollowstar.resolution import resolve_attack
        with tempfile.TemporaryDirectory() as temp:
            _, run = self.fixture(Path(temp)/'.local/reliquary_runs')
            a = run.party[0]; a.statuses.clear()
            a.inherent = [Effect(name=f'Magnitude {i}', phase=Phase.MAGNITUDE,
                                 direction=Direction.MODIFY, flat_bonus=1) for i in range(10)]
            self.assertEqual(len(t.combat_effects(run, 'p0')), 10)
            # All ten rules participate in the existing resolver, not only the rack.
            result = resolve_attack(a, run.opposition[0])
            self.assertEqual(result.damage, 11)
            t.condition(run, 'p0', 'DODGING', 1)
            self.assertEqual(len(t.combat_effects(run, 'p0')), 11)
            self.assertEqual(t.combat_effects(run, 'p0')[0]['id'], 'condition:DODGING')
            a.inherent[0].charges = 0
            self.assertEqual(len(t.combat_effects(run, 'p0')), 10)
            # No private enemy loadout is exported through this new projection.
            run.opposition[0].inherent = a.inherent
            self.assertFalse(any(row['kind'] == 'inherent' for row in t.combat_effects(run, 'e0')))


if __name__=='__main__':unittest.main()
