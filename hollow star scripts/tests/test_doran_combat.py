"""Champion affordances and canonical Grand Cleave laws, using a real run fixture."""
import unittest
from unittest.mock import patch
from tests import test_gameplay as fixtures
from hollowstar import tactical as t, maneuvers
from hollowstar.view_model import public_event_summary

class DoranCombatTests(unittest.TestCase):
    setUp=fixtures.GameplayTest.setUp
    tearDown=fixtures.GameplayTest.tearDown
    runstate=fixtures.GameplayTest.runstate
    combat=fixtures.GameplayTest.combat

    def ready(self):
        r=self.combat()
        r.context['combat']['cursor']=r.context['combat']['order'].index('p0')
        r.context['combat']['positions']['p0']=[10,10,0]
        r.context['combat']['positions']['p1']=[0,10,0]
        for i,key in enumerate(k for k in t.actors(r) if k.startswith('e')):
            r.context['combat']['positions'][key]=[15+i*5,10,0]
        return r

    def test_champion_affordances_and_costs(self):
        r=self.ready()
        rows={row['id']:row for row in t.contextual_actions(r,'p0')}
        for key in ('grand_cleave','read_seam','action_surge','quick_toss','dagger_attack','cleaver_attack'):
            self.assertTrue(rows[key]['available'],key)
        self.assertEqual(rows['grand_cleave']['cost'],'whole_turn')
        self.assertEqual(rows['grand_cleave']['facings'],['east','west','north','south'])
        self.assertEqual(rows['maneuver_trip_attack']['maneuver'],'Trip Attack')
        t.economy(r,'p0')['bonus']=0
        rows={row['id']:row for row in t.contextual_actions(r,'p0')}
        self.assertFalse(rows['grand_cleave']['available'])
        self.assertFalse(rows['read_seam']['available'])
        self.assertTrue(rows['cleaver_attack']['available'])

    def test_grand_cleave_single_roll_critical_and_public_targets(self):
        r=self.ready()
        with patch.object(r.rng,'d20',return_value=20):
            event=t.apply(r,{'type':'grand_cleave','actor':'p0','facing':'east'})
        self.assertEqual(event['damage'],2*(120+sum(event['damage_rolls'])))
        self.assertTrue(event['critical'])
        self.assertTrue(t.rules(r,'p0')['planted'])
        self.assertEqual(t.economy(r,'p0')['movement'],0)
        self.assertEqual(t.economy(r,'p0')['bonus'],0)
        self.assertEqual(t.economy(r,'p0')['reaction'],1)
        public=public_event_summary(event)
        self.assertEqual(len(public['targets']),len(event['targets']))
        self.assertTrue(public['critical'])
        self.assertEqual(public['presentation']['weapon_mode'],'cleaver')
        self.assertEqual(public['presentation']['animation']['attack'],'grand_cleave')
        self.assertNotIn('before',public['targets'][0]['result'])
        self.assertTrue(all(ev['result']['parted'] for ev in public['targets']))

    def test_grand_cleave_cannot_repeat_after_action_surge(self):
        r=self.ready()
        with patch.object(r.rng,'d20',return_value=1):
            t.apply(r,{'type':'grand_cleave','actor':'p0','facing':'east'})
        t.apply(r,{'type':'action_surge','actor':'p0'})
        # Even a caller restoring other fields cannot bypass the per-turn gate.
        t.economy(r,'p0').update(bonus=1,movement=r.party[0].speed,attacks=0)
        with self.assertRaisesRegex(t.ActionError,'cannot repeat'):
            maneuvers.grand_cleave(r,'p0',{'facing':'east'})

    def test_second_wind_is_fixed_thirty_and_quick_toss_uses_bonus(self):
        r=self.ready();r.party[0].hp-=100
        before=r.party[0].hp
        t.apply(r,{'type':'second_wind','actor':'p0'})
        self.assertEqual(r.party[0].hp-before,30)

    def test_quick_toss_uses_bonus_and_superiority(self):
        r=self.ready();before=r.party[0].resources['superiority_dice']
        event=t.apply(r,{'type':'maneuver','actor':'p0','maneuver':'Quick Toss','target':'e0','mode':'dagger'})
        self.assertEqual(t.economy(r,'p0')['bonus'],0)
        self.assertEqual(r.party[0].resources['superiority_dice'],before-1)
        self.assertEqual(event['presentation']['animation']['attack'],'dagger_throw')

    def test_finishing_cleave_keeps_combat_receipt_with_reward(self):
        from hollowstar.view_model import public_event_summary
        r=self.ready()
        event=t.apply(r,{'type':'grand_cleave','actor':'p0','facing':'east'})
        receipt=public_event_summary({'combat':event,'reward':{'gold':8}})
        self.assertEqual(receipt['type'],'grand_cleave')
        self.assertTrue(receipt['targets'])
        self.assertEqual(receipt['reward']['gold'],8)

    def test_non_champions_do_not_receive_doran_actions(self):
        r=self.ready();t.rules(r,'p0')['identity']='custom'
        ids={row['id'] for row in t.contextual_actions(r,'p0')}
        self.assertNotIn('grand_cleave',ids)

if __name__=='__main__':unittest.main()
