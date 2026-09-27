"""Wren's explicitly sourced domain and concentration-lane actions."""
import copy
from hollowstar import tactical as t


def apply(run,key,action):
    a,r=t.actor(run,key),t.rules(run,key)
    if r.get('identity')!='wren':raise t.ActionError("this domain belongs to Wren")
    feature=action.get('feature')
    if feature=='Indomitable Spirit':
        t.use(run,key,'action');t.spend(a,'channel_divinity')
        targets=[k for k,v in t.actors(run).items() if k[0]==key[0] and t.distance(run,key,k)<=30]
        for target in targets:
            who=t.actor(run,target)
            for status in {'CHARMED','FRIGHTENED','PARALYZED','RESTRAINED','STUNNED','GRAPPLED','INCAPACITATED','PETRIFIED'}:
                who.statuses.pop(status,None)
            t.rules(run,target)['spirit_until']=run.round_number+10
        return {'type':'domain','feature':feature,'targets':targets,'duration_rounds':10}
    if feature=='Aura of the Unbound':
        target=action.get('target'); failed=action.get('failed_save')
        if target is None or target == key or not t.same_side(key,target):
            raise t.ActionError('save conversion requires a willing ally')
        t.check_target(run,key,target,30,enemy=False)
        if not isinstance(failed,dict) or failed.get('success') is not False:
            raise t.ActionError('save conversion requires a failed save')
        t.use(run,key,'reaction');t.spend(a,'unbound_save_conversion')
        return {'type':'domain','feature':feature,'target':target,'converted':True,
                'evidence':{'failed_save':dict(failed),'success':True,
                            'resources_remaining':a.resources.get('unbound_save_conversion',0)}}
    if feature in {'Dimensional Shift','The Open Door'}:
        targets=action.get('targets',[key])
        if not isinstance(targets,list) or len(targets)!=len(set(targets)) or key not in targets:
            raise t.ActionError('teleport targets must be distinct, willing allies including Wren')
        if feature=='Dimensional Shift' and len(targets)>7:raise t.ActionError('Dimensional Shift permits Wren plus six')
        for target in targets:t.check_target(run,key,target,30,enemy=False)
        if feature=='The Open Door':
            if not r.get('anchor'):raise t.ActionError('no long-rest anchor')
            t.use(run,key,'reaction');t.spend(a,'portal_anchor_return');destination=r['anchor']
        else:
            t.use(run,key,'action');t.spend(a,'channel_divinity');destination=action.get('destination')
        if not isinstance(destination,list) or len(destination)!=3 or any(type(x)is not int or x<0 or x>120 or x%5 for x in destination):
            raise t.ActionError('this room supports grid destinations only; use extract for a run exit')
        toll=[]
        exemptions=set(action.get('toll_exemptions',[]))
        for target in targets:
            enters=max(abs(destination[i]-t.position(run,key)[i]) for i in range(3)) <= 60
            leaves=t.distance(run,key,target) <= 60
            if (enters or leaves) and target not in exemptions:
                save=t.saving_throw(run,target,'CHA',22,magical=True)
                toll.append({'target':target,'save':save})
                if not save['success']:
                    return {'type':'domain','feature':feature,'targets':targets,
                            'destination':destination,'toll':toll,'attempt_wasted':True,
                            'unbarred':True}
        for index,target in enumerate(targets):
            run.context['combat']['positions'][target]=list(destination)
            for status in {'GRAPPLED','RESTRAINED'}:t.actor(run,target).statuses.pop(status,None)
        return {'type':'domain','feature':feature,'targets':targets,'destination':destination,
                'toll':toll,'unbarred':True}
    if feature=='free_misty_step':
        t.use(run,key,'bonus');t.spend(a,'misty_step_free')
        destination=action.get('destination')
        if not isinstance(destination,list) or len(destination)!=3 or any(type(x)is not int or x<0 or x>120 or x%5 for x in destination):
            raise t.ActionError('invalid teleport destination')
        if max(abs(t.position(run,key)[i]-destination[i]) for i in range(3))>30:raise t.ActionError('Misty Step range is 30 feet')
        run.context['combat']['positions'][key]=destination
        return {'type':'teleport','feature':feature,'destination':destination}
    if feature=='simulacrum':
        e=t.economy(run,key)
        if not e['action'] or not e['bonus'] or not e['reaction'] or e['movement']!=r.get('fly_speed',a.speed):
            raise t.ActionError('Simulacrum requires an entire turn')
        copies=[k for k in t.actors(run) if t.rules(run,k).get('simulacrum')]
        if len(copies)>=4 or r.get('child') is not None:raise t.ActionError('simulacrum ceiling or personal child limit reached')
        t.spend(a,'simulacrum_cast');t.spend(a,'slot_7_general')
        e.update(action=0,bonus=0,reaction=0,movement=0,attacks=0)
        child=copy.deepcopy(a);child.max_hp=a.max_hp//2;child.hp=child.max_hp
        for resource in list(child.resources):
            if resource.startswith('slot_') or resource=='sorcery_points':child.resources[resource]//=2
        child.resources['spell_slots_total']=sum(v for k,v in child.resources.items() if k.startswith('slot_'))
        child.resources['simulacrum_cast']=1
        child.name=f"Wren simulacrum G{r.get('generation',0)+1}"
        new=f'p{len(run.party)}';run.party.append(child)
        cr=copy.deepcopy(r);cr.update(simulacrum=True,generation=r.get('generation',0)+1,parent=key,child=None)
        cr['baseline_resources']=copy.deepcopy(child.resources)
        state=run.context['combat'];state['rules'][new]=cr
        state['positions'][new]=list(t.position(run,key));state['economy'][new]={'action':1,'bonus':1,'reaction':1,'movement':child.speed,'attacks':0}
        rolled=run.rng.d20()+child.initiative_bonus;state['initiative_rolls'][new]=rolled
        # Insert relative to initiative while retaining the current actor's cursor.
        active=t.current(run);state['order'].append(new)
        state['order'].sort(key=lambda k:(-state['initiative_rolls'][k],k));state['cursor']=state['order'].index(active)
        r['child']=new
        return {'type':'simulacrum','actor':new,'parent':key,'hp':child.hp,'slots':child.resources['spell_slots_total'],'sp':child.resources['sorcery_points'],'initiative':rolled}
    raise t.ActionError(f'RULING_REQUIRED: domain feature {feature}')
