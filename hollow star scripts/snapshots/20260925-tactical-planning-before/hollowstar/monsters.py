"""Regular 2014 SRD Tarrasque DESIGN stat block, with persistent crisis state.

Source: https://www.dndbeyond.com/sources/dnd/basic-rules-2014/monster-stat-blocks-t
Room-scale movement uses HSR's declared 5-foot grid. This is not certification.
"""
from hollowstar.actors import Actor, Provenance
from hollowstar.items import Item
from hollowstar import tactical as t


ATTACKS={'bite':('4d12+10','PIERCING',10),'claw':('4d8+10','SLASHING',15),
         'horns':('4d10+10','PIERCING',10),'tail':('4d6+10','BLUDGEONING',20)}


def spawn_tarrasque(run):
    state=run.context['combat'];key=f'e{len(run.opposition)}'
    beast=Actor(name='Tarrasque',max_hp=676,hp=676,
        armor_class=25,speed=40,attacks_per_action=5,
        ability_scores={'STR':30,'DEX':11,'CON':30,'INT':3,'WIS':11,'CHA':11},
        equipment=[Item(name='claw',damage_dice='4d8',damage_modifier=10,attack_bonus=19)],
        resources={'legendary_resistance':3,'legendary_actions':3},
        provenance=Provenance(owner_file='2014 SRD Tarrasque',snapshot_version='hsr-tarrasque-2014-1',
            verified=True,fidelity='complete',note='Regular 2014 Tarrasque stat block; DESIGN-only encounter ruling.'))
    run.opposition.append(beast)
    state['rules'][key]={'identity':'tarrasque','size':'gargantuan','base_ac':25,
        'saves':{'STR':10,'DEX':0,'CON':10,'INT':5,'WIS':9,'CHA':9},
        'immunities':['FIRE','POISON'],'condition_immunities':['CHARMED','FRIGHTENED','PARALYZED','POISONED'],
        'swallowed':[],'bite_target':None,'fright_immune':[],'inside_damage':{},'routine':[]}
    state['positions'][key]=[60,60,0]
    state['economy'][key]={'action':1,'bonus':1,'reaction':1,'movement':40,'attacks':0}
    state['initiative_rolls'][key]=run.rng.d20()
    active=t.current(run);state['order'].append(key)
    state['order'].sort(key=lambda k:(-state['initiative_rolls'][k],k));state['cursor']=state['order'].index(active)
    return {'type':'cocoon_opened','actor':key,'rules_version':'regular 2014 Tarrasque','initiative':state['initiative_rolls'][key]}


def attack(run,key,target,mode):
    a,r=t.actor(run,key),t.rules(run,key)
    if mode=='swallow':
        if r['bite_target']!=target or t.rules(run,target).get('size','medium') in {'huge','gargantuan'}:
            raise t.ActionError('Swallow needs a grappled Large-or-smaller target')
        signature='bite'
    else:signature=mode
    if signature not in ATTACKS:raise t.ActionError('unsupported monster attack')
    expression,kind,reach=ATTACKS[signature]
    if target==key or not t.actor(run,target).alive or t.distance(run,key,target)>reach:
        raise t.ActionError('invalid monster target or range')
    if signature=='bite' and r['bite_target'] not in {None,target}:
        raise t.ActionError('bite is holding another creature')
    roll=t.roll_check(run,19,t.actor(run,target).armor_class)
    roll['success']=roll['natural']!=1 and (roll['natural']==20 or roll['success'])
    counterplay={
        'bite': {'tell':'The Tarrasque commits its jaws to one target.','counter':'Keep distance or break the grapple before swallow.'},
        'swallow': {'tell':'The Tarrasque is trying to swallow its grappled target.','counter':'Damage the Tarrasque from outside or force regurgitation.'},
        'tail': {'tell':'The tail sweep threatens forced movement and a knockdown.','counter':'Brace against forced movement or pass the STR save.'},
        'claw': {'tell':'A direct claw attack is incoming.','counter':'Use AC, cover, or a reaction defense.'},
        'horns': {'tell':'The horns line up a piercing charge.','counter':'Break line or improve AC.'}}
    result={'type':'monster_attack','mode':mode,'source':key,'target':target,'roll':roll,
            'counterplay':counterplay.get(mode,counterplay.get(signature))}
    if roll['success']:
        amount,values=t.dice(run,expression,critical=roll['natural']==20)
        result['damage']=t.damage(run,key,target,amount,kind);result['dice']=values
        if result['damage']['ward_before']:
            return result
        if mode=='swallow':
            r['swallowed'].append(target);r['bite_target']=None
            t.actor(run,target).statuses.pop('GRAPPLED',None)
            t.rules(run,target)['swallowed_by']=key
            # External targeting is blocked independently from damage defenses.
            run.context['combat']['terrain']['cover'][target]='total'
            t.condition(run,target,'BLINDED',10000)
            t.condition(run,target,'RESTRAINED',10000)
        elif mode=='bite':
            applied=t.condition(run,target,'GRAPPLED',10000)
            if applied['applied']:
                r['bite_target']=target;t.condition(run,target,'RESTRAINED',10000)
        elif mode=='tail':
            save=t.saving_throw(run,target,'STR',20);result['save']=save
            if not save['success']:result['prone']=t.condition(run,target,'PRONE',10000)
    return result


def force_regurgitation(run, source, target):
    """DESIGN counterplay action: an outside actor forces the swallowed party out."""
    if t.rules(run,target).get('identity') != 'tarrasque':
        raise t.ActionError('force regurgitation requires a Tarrasque target')
    beast_rules=t.rules(run,target)
    swallowed=[k for k in beast_rules.get('swallowed',[]) if t.actor(run,k).alive]
    if not swallowed:
        raise t.ActionError('Tarrasque has no living swallowed target')
    if t.distance(run,source,target)>30:
        raise t.ActionError('force regurgitation requires a target within 30 feet')
    t.use(run,source,'action')
    for victim in swallowed:
        who=t.actor(run,victim);who.statuses.pop('BLINDED',None);who.statuses.pop('RESTRAINED',None)
        t.rules(run,victim).pop('swallowed_by',None)
        run.context['combat']['terrain']['cover'].pop(victim,None)
        run.context['combat']['positions'][victim]=list(t.position(run,target))
        t.condition(run,victim,'PRONE',10000)
    beast_rules['swallowed']=[k for k in beast_rules.get('swallowed',[]) if k not in swallowed]
    return {'type':'force_regurgitation','actor':source,'target':target,'released':swallowed,
            'evidence':{'counter':'force regurgitation','state_change':'swallowed targets released',
                        'released':swallowed,'distance':t.distance(run,source,target)}}


def act(run,key,action,legendary=False):
    a,r=t.actor(run,key),t.rules(run,key)
    if r.get('identity')!='tarrasque':
        if legendary: raise t.ActionError('legendary actions require a Tarrasque')
        if r.get('retreated'):
            return {'type':'resident_withdrawn','source':key,'actor':a.name,
                    'tactic':{'policy':'already-retreated','tell':'The resident is no longer pressing the fight.',
                              'counterplay':list(r.get('counterplay',[]))},
                    'evidence':{'actor':a.name,'state_change':'no action; resident remains retreated'}}
        threshold=r.get('retreat_threshold')
        if threshold is not None and a.max_hp and a.hp/a.max_hp <= threshold and not r.get('retreated'):
            r['retreated']=True
            return {'type':'resident_retreat','source':key,'actor':a.name,
                    'tactic':{'policy':'retreat_at_threshold','threshold':threshold,
                              'tell':'The resident breaks formation and looks for an exit.',
                              'counterplay':list(r.get('counterplay',[])),
                              'motive':r.get('motive','')},
                    'evidence':{'actor':a.name,'hp':a.hp,'max_hp':a.max_hp,
                                'threshold':threshold,'state_change':'resident marked retreated'}}
        target=action.get('target')
        if target is None:
            candidates=[k for k,v in t.actors(run).items() if k!=key and v.alive and not t.same_side(key,k)]
            if not candidates: raise t.ActionError('no living enemy target')
            target=min(candidates,key=lambda k:(t.distance(run,key,k),k))
        result=t.weapon_attack(run,key,target,action.get('mode','weapon'),bonus=action.get('bonus',False))
        pool=r.get('bonus_attack_resource')
        if not action.get('bonus') and pool and t.economy(run,key).get('bonus') and a.resources.get(pool):
            before=a.resources[pool]
            result['synergy_attack']=t.weapon_attack(run,key,target,action.get('mode','weapon'),bonus=True)
            result['tactic_resource_spent']={'resource':pool,'before':before,'after':a.resources.get(pool,0)}
        result['tactic']={'trait':r.get('trait',''),
                          'tell':r.get('trait','Declared resident trait; inspect the room for its tell.'),
                          'formation':r.get('formation','unknown'),
                          'motive':r.get('motive',''),
                          'counterplay':list(r.get('counterplay',[]))}
        return result
    mode=action.get('mode');target=action.get('target')
    if target is None:
        candidates=[k for k,v in t.actors(run).items() if k!=key and v.alive and not t.same_side(key,k)]
        if not candidates:raise t.ActionError('no living enemy target')
        target=min(candidates,key=lambda k:(t.distance(run,key,k),k))
        action=dict(action,target=target)
    if mode is None and not legendary:
        available=r.get('routine') or ['bite','claw','claw','horns','tail']
        mode='swallow' if r.get('bite_target') == target else available[0]
    if legendary:
        if mode not in {'claw','tail','bite','swallow','move'}:raise t.ActionError('invalid legendary action')
        t.spend(a,'legendary_actions',2 if mode in {'bite','swallow'} else 1)
        if mode=='move':
            old=t.economy(run,key)['movement'];t.economy(run,key)['movement']=20
            result=t.move(run,key,action.get('destination'));t.economy(run,key)['movement']=old
            return result
        return attack(run,key,target,mode)
    e=t.economy(run,key)
    if not r['routine']:
        t.use(run,key,'action');r['routine']=['bite','claw','claw','horns','tail']
        fear=[]
        for other,who in t.actors(run).items():
            if other==key or not who.alive or other in r['fright_immune'] or t.distance(run,key,other)>120:continue
            check=t.saving_throw(run,other,'WIS',17)
            if check['success']:r['fright_immune'].append(other)
            else:
                result=t.condition(run,other,'FRIGHTENED',10,mental=True)
                if result['applied']:t.rules(run,other)['fright_source']=key
            fear.append({'target':other,'save':check})
    else:fear=[]
    actual='bite' if mode=='swallow' else mode
    if actual not in r['routine']:raise t.ActionError('attack already used in the five-attack routine')
    r['routine'].remove(actual)
    result=attack(run,key,target,mode);result['frightful_presence']=fear
    result['tactic']={'policy':'nearest-living-target','tell':'The Tarrasque commits toward the nearest living target.'}
    result['frightful_presence_counter']='Pass the WIS save, remain beyond 120 ft, or use fear immunity.'
    return result


def start_turn(run,key):
    r=t.rules(run,key);a=t.actor(run,key)
    if r.get('identity')!='tarrasque':return []
    a.resources['legendary_actions']=3;r['routine']=[]
    out=[]
    for swallowed in list(r['swallowed']):
        if t.actor(run,swallowed).alive:
            amount,rolls=t.dice(run,'16d6')
            out.append(t.damage(run,key,swallowed,amount,'CORROSIVE'))
    return out


def end_turn(run,key):
    out=[]
    source=t.rules(run,key).get('fright_source')
    if source and 'FRIGHTENED' in t.actor(run,key).statuses:
        check=t.roll_check(run,t.rules(run,key)['saves'].get('WIS',0),17,disadvantage=True)
        if check['success']:
            t.actor(run,key).statuses.pop('FRIGHTENED',None);t.rules(run,source)['fright_immune'].append(key)
        out.append({'type':'fright_save','target':key,'save':check})
    for beast in t.actors(run):
        r=t.rules(run,beast)
        if r.get('identity')!='tarrasque':continue
        if r['inside_damage'].pop(key,0)>=60:
            save=t.saving_throw(run,beast,'CON',20)
            if not save['success']:
                for swallowed in list(r['swallowed']):
                    who=t.actor(run,swallowed);who.statuses.pop('BLINDED',None);who.statuses.pop('RESTRAINED',None)
                    t.rules(run,swallowed).pop('swallowed_by',None)
                    run.context['combat']['terrain']['cover'].pop(swallowed,None)
                    run.context['combat']['positions'][swallowed]=list(t.position(run,beast))
                    t.condition(run,swallowed,'PRONE',10000)
                r['swallowed']=[]
            out.append({'type':'regurgitate_save','save':save})
        if beast!=key and t.actor(run,beast).alive and t.actor(run,beast).resources['legendary_actions']:
            run.context['combat']['pending'].append({'kind':'legendary','reactor':beast,'target':key})
    return out
