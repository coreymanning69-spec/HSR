"""Automated choices only. No rolls, damage, reward or state mutations live here."""
from hollowstar import tactical as t


SELECTORS = {"self", "self_only", "lowest_hp_ally", "lowest_health_ally", "lowest_hp_enemy",
             "lowest_health_enemy", "nearest_enemy", "highest_hp_enemy", "casting_enemy",
             "adjacent_enemy"}
TARGETED_TYPES = {"attack", "cast", "reaction", "shove", "trip", "grapple", "help"}


def _macro_target(run, actor_key, selector):
    """Resolve a public Macro target selector without mutating the run."""
    actors = t.actors(run)
    allies = [k for k, v in actors.items()
              if t.same_side(k, actor_key) and v.alive]
    enemies = [k for k, v in actors.items()
               if not t.same_side(k, actor_key) and v.alive]
    selector = str(selector or "nearest_enemy").lower()
    if selector in {"self", "self_only"}:
        return actor_key
    if selector in {"lowest_hp_ally", "lowest_health_ally"}:
        return min(allies, key=lambda k: (actors[k].hp / max(1, actors[k].max_hp), k), default=None)
    if selector in {"lowest_hp_enemy", "lowest_health_enemy"}:
        return min(enemies, key=lambda k: (actors[k].hp / max(1, actors[k].max_hp), k), default=None)
    if selector == "highest_hp_enemy":
        # Boss focus: the most current hit points, not the highest percentage.
        return min(enemies, key=lambda k: (-actors[k].hp, k), default=None)
    if selector == "casting_enemy":
        casting = [k for k in enemies if "CASTING" in actors[k].statuses]
        return min(casting, key=lambda k: (t.distance(run, actor_key, k), k), default=None)
    if selector == "adjacent_enemy":
        near = [k for k in enemies if t.distance(run, actor_key, k) <= 5]
        return min(near, key=lambda k: (actors[k].hp, k), default=None)
    return min(enemies, key=lambda k: (t.distance(run, actor_key, k), actors[k].hp, k), default=None)


def _pct(actor):
    return actor.hp * 100 / max(1, actor.max_hp)


def _has_resource(run, actor, name):
    name = str(name)
    if name == "spell_slot":
        return any(value > 0 for key, value in actor.resources.items() if key.startswith("slot_"))
    if name == "potion":
        inventory = (run.context.get("dungeon") or {}).get("inventory", {})
        return any(item.get("kind") == "potion" for item in inventory.values() if isinstance(item, dict))
    return actor.resources.get(name, 0) > 0


def _cocoon(run):
    """The live final-floor cocoon clock, or None outside that chamber."""
    dungeon = run.context.get("dungeon")
    if not isinstance(dungeon, dict):
        return None
    row = (dungeon.get("rooms") or {}).get(f"{dungeon.get('floor')}:{dungeon.get('room')}") or {}
    return row.get("cocoon") if isinstance(row.get("cocoon"), dict) else None


def _macro_matches(run, actor_key, macro):
    """Evaluate the data-only Macro (Gambit) condition vocabulary.

    Every key in ``when`` must hold. Unknown keys fail closed so a typo never
    turns a conditional gambit into an unconditional one.
    """
    when = macro.get("when", {}) if isinstance(macro, dict) else {}
    if not isinstance(when, dict):
        return False
    actor = t.actor(run, actor_key)
    actors = t.actors(run)
    enemies = [k for k, v in actors.items() if not t.same_side(k, actor_key) and v.alive]
    target = _macro_target(run, actor_key, when.get("target", macro.get("target")))
    for key, value in when.items():
        if key == "target":
            continue
        if key == "self_hp_below":
            ok = actor.hp <= actor.max_hp * float(value) / 100
        elif key == "self_hp_above":
            ok = actor.hp >= actor.max_hp * float(value) / 100
        elif key in {"ally_hp_below", "ally_hp_above"}:
            ally = _macro_target(run, actor_key, "lowest_hp_ally")
            ok = ally is not None and (_pct(actors[ally]) <= float(value) if key == "ally_hp_below"
                                       else _pct(actors[ally]) >= float(value))
        elif key in {"enemy_hp_below", "enemy_hp_above"}:
            ok = target is not None and (_pct(actors[target]) <= float(value) if key == "enemy_hp_below"
                                         else _pct(actors[target]) >= float(value))
        elif key == "enemy_status":
            ok = target is not None and str(value) in actors[target].statuses
        elif key == "self_status":
            ok = str(value) in actor.statuses
        elif key == "self_status_absent":
            ok = str(value) not in actor.statuses
        elif key == "round_number_gte":
            ok = run.round_number >= int(value)
        elif key == "round_number_lte":
            ok = run.round_number <= int(value)
        elif key in {"cocoon_rounds_gte", "cocoon_rounds_lte"}:
            clock = _cocoon(run)
            ok = clock is not None and not clock.get("opened") and (
                run.round_number >= int(value) if key == "cocoon_rounds_gte" else run.round_number <= int(value))
        elif key == "has_resource":
            names = value if isinstance(value, list) else [value]
            ok = all(_has_resource(run, actor, name) for name in names)
        elif key == "enemy_casting":
            ok = any("CASTING" in actors[k].statuses for k in enemies) == bool(value)
        elif key == "enemy_count_gte":
            ok = len(enemies) >= int(value)
        elif key == "enemy_adjacent":
            ok = any(t.distance(run, actor_key, k) <= 5 for k in enemies) == bool(value)
        else:
            ok = False
        if not ok:
            return False
    return True


def _legal_now(run, actor_key, action):
    """Skip a gambit whose contextual action the engine already knows is illegal.

    Only meaningful on the actor's own turn; an off-turn preview returns the
    first matching gambit exactly as before.
    """
    combat = run.context.get("combat") or {}
    if combat.get("complete") or combat.get("pending") or not combat.get("order") or t.current(run) != actor_key:
        return True
    catalog = {row["id"]: row for row in t.contextual_actions(run, actor_key)}
    row = catalog.get(action.get("type"))
    if row is None:
        return True  # not a catalogued action: its own transition decides
    if not row["available"]:
        return False
    return not row["targets"] or action.get("target") in row["targets"]


def macro_action(run, actor_key, macros):
    """Return the first valid canonical action from an ordered Macro list."""
    for macro in sorted(macros or [], key=lambda item: int(item.get("priority", 100))):
        if not _macro_matches(run, actor_key, macro):
            continue
        action = dict(macro.get("then", {}))
        if not action.get("type"):
            continue
        action.setdefault("actor", actor_key)
        for field in ("target", "ally"):
            if action.get(field) in SELECTORS:
                action[field] = _macro_target(run, actor_key, action[field])
        if action.get("type") in TARGETED_TYPES and not action.get("target"):
            continue
        if not _legal_now(run, actor_key, action):
            continue
        return action
    return None


def approach(run,key,target,maximum,cap=10):
    """The largest step toward target this actor can actually pay for.

    Returns None when no step is affordable, so the caller ends the turn
    instead of re-proposing a refused move. Steps stay small so terrain and
    threat windows land between them, and every candidate is priced by
    tactical.move_cost rather than assumed to be five feet per square: the
    difficult columns on floors two and four cost ten, so a ten-foot step
    there is a fifteen- or twenty-foot bill.
    """
    start=t.position(run,key);goal=t.position(run,target)
    budget=t.economy(run,key)['movement']
    reach=min(max(0,t.distance(run,key,target)-maximum),cap,budget)//5*5
    while reach>=5:
        destination=list(start)
        for axis in (0,1):
            delta=goal[axis]-start[axis]
            destination[axis]+=min(abs(delta),reach)*(1 if delta>0 else -1)
        cost=t.move_cost(run,key,destination)
        if destination!=start and cost is not None and cost<=budget:
            return destination
        reach-=5
    return None


def combat_action(run):
    state=run.context['combat']
    if state['pending']:
        window=state['pending'][0]
        if window['kind']=='hit':
            return {'type':'reaction','actor':window['reactor'],'defense':'shield'} if 'shield' in window['options'] else {'type':'decline_reaction','actor':window['reactor']}
        if window['kind']=='legendary':return {'type':'decline_reaction','actor':window['reactor']}
        return {'type':'reaction','actor':window['reactor']}
    key=t.current(run);a=t.actor(run,key);e=t.economy(run,key)
    if not t.conscious(a):return {'type':'end_turn','actor':key}
    targets=[k for k,v in t.actors(run).items() if not t.same_side(k,key) and v.alive]
    target=min(targets,key=lambda k:(t.distance(run,key,k),t.actor(run,k).hp,k))
    identity=t.rules(run,key).get('identity')
    if t.rules(run,key).get('retreated'):
        return {'type':'end_turn','actor':key}
    configured = run.context.get("macros", {}).get(key, [])
    selected = macro_action(run, key, configured)
    if selected is not None:
        return selected
    if identity == 'doran' and e['bonus'] and a.hp < a.max_hp / 2 and a.resources.get('second_wind'):
        return {'type':'second_wind','actor':key}
    if identity == 'wren' and e['bonus'] and a.hp < a.max_hp / 2 and a.resources.get('unearthly_recovery'):
        return {'type':'unearthly_recovery','actor':key}
    if identity=='wren':
        # Preserve a real support line in automated rehearsals.  Healing Word
        # is a declared bonus-action spell, so this is an ordinary engine cast
        # with normal range, slot consumption, and healing rolls—not a policy
        # side effect.
        ally = next((k for k, v in t.actors(run).items()
                     if t.same_side(k, key) and k != key and v.alive
                     and v.hp <= v.max_hp // 2), None)
        if ally and e['bonus'] and a.resources.get('slot_1_general'):
            return {'type':'cast','actor':key,'spell':'Healing Word@5e','target':ally}
        if e['bonus'] and a.resources.get('crown_motes'):
            return {'type':'attack','actor':key,'target':target,'bonus':True}
        if e['action'] and a.resources.get('slot_3_general'):
            return {'type':'cast','actor':key,'spell':'Fireball@5e','center':list(t.position(run,target))}
        # Out of slots and motes she falls back to her Sacred Flame cantrip
        # rather than idling out the fight.
        if e['action']:
            if t.distance(run,key,target)>60:
                destination=approach(run,key,target,60)
                if destination is not None and e.get('movement'):
                    return {'type':'move','actor':key,'destination':destination}
            else:
                return {'type':'cast','actor':key,'spell':'Sacred Flame@5e','targets':[target]}
        return {'type':'end_turn','actor':key}
    maximum=70 if identity=='doran' else t.rules(run,key).get('range',[5,5])[1]
    if t.distance(run,key,target)>maximum:
        destination=approach(run,key,target,maximum)
        if destination is None:return {'type':'end_turn','actor':key}
        return {'type':'move','actor':key,'destination':destination}
    if e['action'] or e['attacks']:return {'type':'attack','actor':key,'target':target}
    if identity=='doran' and e['bonus']:return {'type':'attack','actor':key,'target':target,'bonus':True}
    # A fixture resident spends its declared pool for the extra press rather
    # than ending a turn with a quantifier it was never able to use.
    pool=t.rules(run,key).get('bonus_attack_resource')
    if pool and e['bonus'] and a.resources.get(pool):
        return {'type':'attack','actor':key,'target':target,'bonus':True}
    return {'type':'end_turn','actor':key}


def exploration_action(run):
    from hollowstar.dungeon import room
    d=run.context['dungeon'];r=room(run)
    if 'combat' in run.context and not run.context['combat']['complete']:
        return combat_action(run)
    if r['resolved']:return {'type':'enter'}
    if r['kind']=='rest':return {'type':'rest','safe':bool(d['discoveries'])}
    if 'investigate' not in r['attempts']:return {'type':'investigate'}
    return {'type':'avoid'}
