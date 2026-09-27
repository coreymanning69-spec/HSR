"""Doran's bounded maneuver transitions, sourced to DM044_0 Maneuvers.

Unsupported geometries are errors, never a converted ordinary attack.
"""
from hollowstar import tactical as t
from hollowstar.tactical import DORAN_CLEAVER_FLAT_DAMAGE



ATTACKS = {'Disarming Attack':('STR','DISARMED'), 'Distracting Strike':(None,'DISTRACTED'),
    'Goading Attack':('WIS','GOADED'), 'Lunging Attack':(None,None),
    'Maneuvering Attack':(None,None), 'Menacing Attack':('WIS','FRIGHTENED'),
    'Pushing Attack':('STR',None), 'Trip Attack':('STR','PRONE'),
    'Precision Attack':(None,None), 'Sweeping Attack':(None,None)}
CHECKS={'Ambush':['Stealth','initiative'],'Commanding Presence':['Intimidation','Performance','Persuasion'],
        'Tactical Assessment':['Investigation','History','Insight']}


def apply(run,key,action):
    a,r=t.actor(run,key),t.rules(run,key)
    if r.get('identity')!='doran':raise t.ActionError("this maneuver set belongs to Doran")
    name=action.get('maneuver');target=action.get('target')
    if name not in set(ATTACKS)|set(CHECKS)|{'Bait and Switch','Brace',"Commander's Strike",'Evasive Footwork',
            'Feinting Attack','Grappling Strike','Parry','Quick Toss','Rally','Riposte'}:
        raise t.ActionError('unknown maneuver')
    # Event-dependent maneuvers use actual persisted windows, not caller assertions.
    if name == 'Parry':
        if not any(w.get('kind') == 'hit' and w.get('reactor') == key and
                   'parry' in w.get('options', [])
                   for w in run.context.get('combat', {}).get('pending', [])):
            raise t.ActionError('Parry requires an eligible melee-hit reaction window')
        result = t.apply(run, {'type': 'reaction', 'actor': key, 'defense': 'parry'})
        result['feature'] = 'Parry'
        return result
    if name == 'Riposte':
        if not any(w.get('kind') == 'deft_answer' and w.get('reactor') == key and
                   'riposte' in w.get('options', [])
                   for w in run.context.get('combat', {}).get('pending', [])):
            raise t.ActionError('Riposte requires the actual miss reaction window')
        result = t.apply(run, {'type': 'reaction', 'actor': key, 'defense': 'riposte'})
        result['feature'] = 'Riposte'
        return result
    if name in CHECKS:
        skill=action.get('skill')
        if skill not in CHECKS[name]:raise t.ActionError('wrong check for maneuver')
        if skill=='initiative':raise t.ActionError('Ambush initiative must be declared before initiative')
        dc=t.number(action.get('dc'),'check DC',1,100)
        t.spend(a,'superiority_dice');value,rolls=t.dice(run,'1d12')
        bonus=a.skill_bonuses.get(skill,a.skill_bonuses.get(skill.lower(),0))+value
        return {'type':'maneuver','name':name,'superiority':rolls,'check':t.roll_check(run,bonus,dc)}
    if name=='Rally':
        t.check_target(run,key,target,60,enemy=False);t.use(run,key,'bonus');t.spend(a,'superiority_dice')
        value,rolls=t.dice(run,'1d12+3');ally=t.actor(run,target)
        ally.resources['temporary_hp']=max(ally.resources.get('temporary_hp',0),value)
        return {'type':'maneuver','name':name,'target':target,'temporary_hp':value,'rolls':rolls}
    if name=='Bait and Switch':
        t.check_target(run,key,target,5,enemy=False)
        if t.economy(run,key)['movement']<5:raise t.ActionError('Bait and Switch needs five feet movement')
        t.economy(run,key)['movement']-=5;t.spend(a,'superiority_dice');value,rolls=t.dice(run,'1d12')
        p=run.context['combat']['positions'];p[key],p[target]=p[target],p[key]
        beneficiary=action.get('beneficiary',target)
        if beneficiary not in {key,target}:raise t.ActionError('invalid Bait and Switch beneficiary')
        # Doran's sourced AC lock wins all situational increases.
        if t.rules(run,beneficiary).get('identity')!='doran':t.actor(run,beneficiary).armor_class+=value
        return {'type':'maneuver','name':name,'swap':[key,target],'ac_die':rolls,'beneficiary':beneficiary,'doran_ac_lock':beneficiary==key}
    if name=='Evasive Footwork':
        if not t.economy(run,key)['movement']:raise t.ActionError('requires movement')
        raise t.ActionError('Doran AC LOCK prevents this modifier; no die spent')
    if name=='Feinting Attack':
        t.check_target(run,key,target,5);t.use(run,key,'bonus');t.spend(a,'superiority_dice')
        r['feint_target']=target
        return {'type':'maneuver','name':name,'target':target}
    if name=="Commander's Strike":
        t.check_target(run,key,target,60,enemy=False)
        e=t.economy(run,key)
        if not e['attacks']:
            t.use(run,key,'action');e['attacks']=4
        e['attacks']-=1;t.use(run,key,'bonus');t.spend(a,'superiority_dice')
        run.context['combat']['pending'].append({'kind':'command','reactor':target,'target':action.get('enemy'),'superiority':True})
        return {'type':'maneuver','name':name,'ally':target}
    if name=='Grappling Strike':
        last=run.context['combat']['events'][-1] if run.context['combat']['events'] else {}
        if last.get('type')!='attack' or last.get('source')!=key or last.get('target')!=target or not last.get('roll',{}).get('success'):
            raise t.ActionError('Grappling Strike requires the preceding hit')
        t.use(run,key,'bonus');t.spend(a,'superiority_dice');value,rolls=t.dice(run,'1d12')
        t.check_target(run,key,target,5)
        defense=t.roll_check(run,t.actor(run,target).ability_modifier('STR'),0)
        attack=t.roll_check(run,14+value,defense['total'])
        result=t.condition(run,target,'GRAPPLED',10) if attack['success'] else None
        return {'type':'maneuver','name':name,'attack':attack,'defense':defense,'result':result}
    t.spend(a,'superiority_dice')
    if name=='Lunging Attack':
        r['lunge_reach']=5
        # Doran uses a thrown dagger beyond five feet. The extra reach is used
        # only by an explicitly selected Cleaver attack.
        if action.get('mode')=='cleaver' and t.distance(run,key,target)>15:raise t.ActionError('outside lunging reach')
    if name=='Precision Attack':
        # One attack's die (DM044_0: +d12 attack before outcome). The permanent
        # precision_bonus upgrade is a separate stat and stays untouched.
        value,rolls=t.dice(run,'1d12');r['precision_die']=value
    hit=t.weapon_attack(run,key,target,action.get('mode','dagger'),bonus=name=='Quick Toss')
    if hit['roll']['success'] and name!='Precision Attack':
        value,rolls=t.dice(run,'1d12',critical=hit['critical'])
        hit['superiority_damage']=t.damage(run,key,target,value,'PIERCING',bypass_resistance=True)
        save_ability,status=ATTACKS.get(name,(None,None))
        save=t.saving_throw(run,target,save_ability,22) if save_ability else {'success':False}
        hit['maneuver_save']=save
        if not save['success']:
            if status in t.CONDITIONS:hit['condition']=t.condition(run,target,status,1,mental=status=='FRIGHTENED')
            elif status=='DISARMED':
                from hollowstar.lattice import denies
                denial=denies(run,target,'DISARMED')
                if denial:
                    hit['condition']={'condition':'DISARMED','applied':False,'reason':'consequence denied',
                                      'lattice':denial,'tell':denial['tell']}
                else:t.rules(run,target)['disarmed']=True
            elif status=='DISTRACTED':t.rules(run,target)['distracted_by']=key
            elif status=='GOADED':t.rules(run,target)['goaded_by']=key
            if name=='Pushing Attack':
                if not t.rules(run,target).get('planted'):
                    p=t.position(run,target);origin=t.position(run,key)
                    run.context['combat']['positions'][target]=[min(120,max(0,p[0]+(15 if p[0]>=origin[0] else -15))),p[1],p[2]]
        if name=='Sweeping Attack':
            second=action.get('second_target');t.check_target(run,target,second,5,enemy=False)
            hit['sweep']=t.damage(run,key,second,value,'PIERCING')
        if name=='Maneuvering Attack':
            ally=action.get('ally');t.check_target(run,key,ally,60,enemy=False)
            t.use(run,ally,'reaction');t.economy(run,ally)['movement']+=t.actor(run,ally).speed//2
            t.actor(run,ally).statuses['DISENGAGED']=1
    hit['maneuver']=name
    return hit


def grand_cleave(run,key,action):
    if t.rules(run,key).get('identity')!='doran':raise t.ActionError('Grand Cleave belongs to Doran')
    e=t.economy(run,key);a=t.actor(run,key)
    if t.rules(run,key).get('grand_cleave_round') == run.round_number:
        raise t.ActionError('Grand Cleave cannot repeat this turn, including through Action Surge')
    if not e['action'] or not e['bonus'] or (e['movement']!=a.speed and not t.rules(run,key).get('planted')) or e['attacks']:
        raise t.ActionError('Grand Cleave requires an unspent whole turn')
    facing=action.get('facing')
    if facing not in {'east','west','north','south'}:raise t.ActionError('choose a cardinal facing for the 180-degree arc')
    origin=t.position(run,key);axis=0 if facing in {'east','west'} else 1;sign=1 if facing in {'east','north'} else -1
    targets=[k for k,v in t.actors(run).items() if k!=key and v.alive and t.distance(run,key,k)<=15 and (t.position(run,k)[axis]-origin[axis])*sign>=0]
    targets.sort(key=lambda k:(t.distance(run,key,k),k))
    if not targets:raise t.ActionError('empty arc')
    e['action']=0;e['bonus']=0;e['movement']=0;e['attacks']=0
    t.rules(run,key)['planted']=True;t.rules(run,key)['mobile']=False
    t.rules(run,key)['grand_cleave_round']=run.round_number
    natural=run.rng.d20();amount,rolls=t.dice(run,'4d20+120');amount*=2 if natural==20 else 1
    reached=[];capacity=7
    for target in targets:
        size=t.rules(run,target).get('size','medium');cost=2 if size=='large' else 1
        if cost>capacity:break
        hit=natural!=1 and (natural==20 or natural+19>=t.actor(run,target).armor_class)
        if hit:
            result=t.damage(run,key,target,amount,'SLASHING')
            if size in {'medium','small','tiny','large'}:
                t.actor(run,target).hp=0;result['parted']=True
            reached.append({'target':target,'result':result})
        else:reached.append({'target':target,'miss':True})
        capacity-=cost
        if size in {'huge','gargantuan'}:break
    structures=[]
    if run.context['combat']['terrain'].get('human_tight'):
        terrain=run.context['combat']['terrain']
        for structure in terrain.get('structures',[]):
            p=structure.get('position')
            if not isinstance(p,list) or len(p)<2:
                continue
            if max(abs(p[i]-origin[i]) for i in range(min(3,len(p),len(origin)))) <= 15 \
                    and (p[axis]-origin[axis])*sign >= 0:
                before=structure.get('hp',0)
                structure['hp']=max(0,before-amount)
                structures.append({'object_id':structure.get('object_id'),
                                   'kind':structure.get('kind','structure'),
                                   'name':structure.get('name','structure'),
                                   'damage':amount,'hp_before':before,
                                   'hp_after':structure['hp'],'destroyed':structure['hp']==0})
    return {'type':'grand_cleave','actor':key,'roll':natural,'critical':natural==20,'bonus':19,'damage_rolls':rolls,'damage':amount,'targets':reached,'structures':structures,'includes_allies':True,'facing':facing}


# --- Read-only twin ------------------------------------------------------------
# forecast_maneuver is apply() run as odds for the attack-shaped maneuvers:
# the same weapon_attack terms (through forecast_attack), the superiority die
# as its own PIERCING damage call, and the rider's save at DC 22. Nothing is
# rolled, spent or moved. Window-driven maneuvers (Parry, Riposte, Brace),
# checks, and the ally/position ones have no forecast yet and report so.
SUPERIORITY_DIE = '1d12'
MANEUVER_DC = 22
FORECAST_MANEUVERS = tuple(ATTACKS) + ('Quick Toss',)


def forecast_maneuver(run, key, action, informed=True):
    """What apply(run, key, action) would do for an attack maneuver, as odds.

    Returns forecast_attack's shape with kind "maneuver", the maneuver name,
    `control` (P(the rider lands: condition, push, distraction or goad)) and
    `effect` naming it. expected_damage includes the superiority die and a
    Sweeping Attack's second instance; kill reads the primary target only.
    """
    name = action.get('maneuver')
    target = action.get('target')
    mode = action.get('mode') or 'dagger'
    out = {'kind': 'maneuver', 'maneuver': name, 'actor': key, 'target': target, 'mode': mode,
           'legal': False, 'reason': None, 'hit': 0.0, 'crit': 0.0, 'lands': 0.0,
           'expected_damage': 0.0, 'kill': 0.0, 'control': 0.0, 'effect': None, 'notes': []}
    a, r = t.actor(run, key), t.rules(run, key)
    if r.get('identity') != 'doran':
        out['reason'] = 'this maneuver set belongs to Doran'
        return out
    if name not in FORECAST_MANEUVERS:
        out['reason'] = 'no forecast for this maneuver'
        return out
    if a.resources.get('superiority_dice', 0) <= 0:
        out['reason'] = 'no superiority dice'
        return out
    second = action.get('second_target')
    if name == 'Sweeping Attack':
        problem = ('Sweeping Attack needs a second target' if not second else
                   t.target_problem(run, target, second, 5, enemy=False) if target in t.actors(run) else None)
        if problem:
            out['reason'] = problem
            return out
    if name == 'Maneuvering Attack':
        ally = action.get('ally')
        problem = ('Maneuvering Attack needs an ally' if not ally else
                   t.target_problem(run, key, ally, 60, enemy=False)
                   or (None if t.economy(run, ally).get('reaction') else 'the ally has no reaction left'))
        if problem:
            out['reason'] = problem
            return out
    if name == 'Lunging Attack' and mode == 'cleaver' and target in t.actors(run) \
            and t.distance(run, key, target) > 15:
        out['reason'] = 'outside lunging reach'
        return out
    precision = name == 'Precision Attack'
    base = t.forecast_attack(run, key, target, mode, bonus=name == 'Quick Toss', informed=informed,
                             extra_damage=() if precision else ((SUPERIORITY_DIE, 'PIERCING', True),),
                             attack_die=SUPERIORITY_DIE if precision else None)
    notes = out['notes'] + list(base.get('notes') or [])
    out.update(base)
    out.update(kind='maneuver', maneuver=name, notes=notes, control=0.0, effect=None)
    if not out['legal'] or out.get('blocked'):
        return out
    lands = out['lands']
    if name == 'Sweeping Attack':
        profile = t.known_mitigation(run, key, second, 'PIERCING', informed=informed)
        sweep = t.map_odds(t.dice_odds(SUPERIORITY_DIE), lambda value: t.mitigate(value, profile))
        out['sweep_target'] = second
        out['sweep_expected_damage'] = lands * t.mean_odds(sweep)
        out['expected_damage'] += out['sweep_expected_damage']
    ability, status = ATTACKS.get(name, (None, None))
    fails = 1.0
    if ability:
        passed = t.save_odds(run, target, ability, MANEUVER_DC)
        fails = 0.0 if passed is None else 1.0 - passed
        out['save'] = {'ability': ability, 'dc': MANEUVER_DC, 'fail': fails}
    if status in t.CONDITIONS:
        refusal = t.condition_refusal(run, target, status, mental=status == 'FRIGHTENED')
        out['effect'] = status
        out['control'] = 0.0 if refusal else lands * fails
        if refusal:
            out['notes'].append(f"{status} would be refused: {refusal.get('reason')}")
    elif status == 'DISARMED':
        from hollowstar.lattice import denies
        out['effect'] = 'DISARMED'
        out['control'] = 0.0 if denies(run, target, 'DISARMED') else lands * fails
    elif status in {'DISTRACTED', 'GOADED'}:
        out['effect'] = status
        out['control'] = lands * fails
    elif name == 'Pushing Attack':
        out['effect'] = 'PUSHED'
        out['control'] = 0.0 if t.rules(run, target).get('planted') else lands * fails
    elif name == 'Maneuvering Attack':
        out['effect'] = 'ALLY_REPOSITIONS'
        out['ally'] = action.get('ally')
    out['cost'] = {'economy': {'bonus': 1} if name == 'Quick Toss' else {'attack': 1},
                   'resources': {'superiority_dice': 1}}
    return out
