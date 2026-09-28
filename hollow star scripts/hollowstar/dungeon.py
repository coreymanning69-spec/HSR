"""Lazy five-floor DESIGN fixtures and run-local rewards, using shared combat."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from hollowstar import __version__ as ENGINE_VERSION
from hollowstar.actors import Actor, Band, Provenance
from hollowstar.fastcopy import fast_deepcopy
from hollowstar.rng import clone_random
from hollowstar.items import Item, public_item
from hollowstar.tags import DamageTag
from hollowstar import tactical as t
from hollowstar.content_registry import load_registry, room_content, visible_catalog
from hollowstar import tracking
from hollowstar import clock


# Module-level caches for read-only dungeon configuration files.
# These JSON files never change at runtime; reading them once is sufficient.
_CONFIG_CACHE: dict | None = None
_RUNE_CACHE: dict | None = None
_HOOKS_CACHE: dict | None = None


def rune_config():
    global _RUNE_CACHE
    if _RUNE_CACHE is None:
        _RUNE_CACHE = json.loads((Path(__file__).parent/'content/runes.json').read_text(encoding='utf-8'))
    return _RUNE_CACHE


def system_hooks():
    global _HOOKS_CACHE
    if _HOOKS_CACHE is None:
        _HOOKS_CACHE = json.loads((Path(__file__).parent/'content/system_hooks.json').read_text(encoding='utf-8'))
    return _HOOKS_CACHE


def config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = json.loads((Path(__file__).parent/'content/dungeon.json').read_text(encoding='utf-8'))
    return copy.deepcopy(_CONFIG_CACHE)


def content_fingerprint(config_data, module_content=None):
    payload={'dungeon':config_data, 'runes':rune_config(), 'module':module_content or {}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def _module_floor_rooms(d, floor):
    """Return the authored room layout for one module floor, if present."""
    layout = d.get('config', {}).get('module_rooms_by_floor')
    if isinstance(layout, dict):
        rows = layout.get(str(floor), [])
        return rows if isinstance(rows, list) else []
    rows = d.get('config', {}).get('module_rooms', [])
    return rows if isinstance(rows, list) else []


def _room_types_for_floor(d, floor):
    rows = _module_floor_rooms(d, floor)
    if isinstance(d.get('config', {}).get('module_rooms_by_floor'), dict):
        return [str(row.get('kind', 'combat')) for row in rows]
    return list(d.get('config', {}).get('room_types', []))


def start(run):
    if 'dungeon' in run.context:
        raise t.ActionError('dungeon already started')
    dungeon_config = config()
    registry = load_registry()
    module_content = run.context.get('module_content')
    if module_content:
        # A module may provide a complete floor table and room-kind sequence.
        # The engine still owns generation, RNG, combat, and state transitions.
        floors = module_content.get('floors', {}).get('floors', [])
        room_defs = module_content.get('rooms', {}).get('rooms', [])
        if floors and room_defs:
            dungeon_config = copy.deepcopy(dungeon_config)
            dungeon_config['floors'] = floors
            if any('floor' in row for row in room_defs):
                layout = {}
                for row in room_defs:
                    floor_number = row.get('floor')
                    if type(floor_number) is not int or not 1 <= floor_number <= len(floors):
                        raise t.ActionError('module room floor must identify an authored floor')
                    layout.setdefault(str(floor_number), []).append(row)
                if set(layout) != {str(number) for number in range(1, len(floors) + 1)}:
                    raise t.ActionError('module rooms must cover every authored floor')
                if any(not rows for rows in layout.values()):
                    raise t.ActionError('module floors must contain at least one authored room')
                dungeon_config['module_rooms_by_floor'] = layout
                dungeon_config['module_rooms'] = room_defs
                dungeon_config['room_types'] = []
            else:
                if len(floors) != 1:
                    raise t.ActionError('flat module rooms require exactly one authored floor')
                dungeon_config['room_types'] = [str(row.get('kind', 'combat')) for row in room_defs]
                dungeon_config['module_rooms'] = room_defs
    run.context['content_registry'] = registry
    run.context['system_hooks'] = system_hooks()
    run.context['content_state'] = {}
    launch = run.context.get('run_launch', {})
    starting_gold = launch.get('starting_gold', dungeon_config.get('starting_gold', 0))
    if not isinstance(starting_gold, int) or isinstance(starting_gold, bool) or starting_gold < 0:
        raise t.ActionError('run launch has invalid starting gold')
    run.context['dungeon']={'schema':3,'config':dungeon_config,'floor':1,'room':0,'rooms':{},
        'currency':starting_gold,'components':0,'inventory':{},'permanent_gear':{},'imprints':{},'discoveries':[],
        'receipts':[],'events':[],'status':'active','rooms_cleared':0,'rank_xp':0,'hsr_rank':1,'next_item':1,
        'baseline_party':copy.deepcopy(run.party),'party_rules':copy.deepcopy(run.context.get('party_rules',{})),
        'upgrades':{'precision':0,'force':0,'ward':0,'reserve':0,
                    'mastery_capacity':0,'supplies':0,'crafting':0,
                    'prefix_capacity':0,'suffix_capacity':0,'legendary_capacity':0},
        'attunement':{},
        'meta_currency':0,'meta_reward_history':[],'alert':0,
        'event_clock':{'schema':clock.SCHEMA,'tick':0,'seconds':0,'round':0,'turn':0,
                       'rooms_entered':0,'rooms_resolved':0,'history':[]},
        'commentary':{'enabled':True,'turn':0,'last':{}},
        'content_registry_version':registry['registry_version'],
        'checkpoint':{'current':None,'history':[],'banked':None},'navigation_history':[],
        'terminal_receipt':None,'last_terminal_receipt':None,
        'greed':0.0,'attrition':0.0,
        'pressure':{'minutes_elapsed':0,'fatigue':0,'light_minutes':120,
                    'noise':0,'alarm':0,'scale':'mortal',
                    'clocks':{'environment':0,'faction':0},'history':[]},
        'run_capsule':{'schema':'hollow-star-run-capsule-1','retention':'temporary','terminal':None}}
    tracking.ensure(run.context['dungeon'])['gold_starting'] = int(starting_gold)
    d=run.context['dungeon']
    d['opposition_scale']=_party_scale(run, dungeon_config)
    run.context['replay_contract']={'schema':'hollow-star-replay-1','engine_version':ENGINE_VERSION,
                                    'content_fingerprint':content_fingerprint(dungeon_config, module_content),
                                    # Account meta and tier are launch-frozen, so a replay
                                    # remains identical after the account changes.
                                    'loop_tier':run.context.get('loop_tier',1),
                                    'account_meta_hash':run.context.get('account_meta_hash'),
                                    'account_meta':copy.deepcopy(run.context.get('account_meta',{}))}
    selectors=run.context.get('party_selectors',[])
    for index,actor in enumerate(run.party):
        selector=selectors[index] if index<len(selectors) else actor.name
        progress=run.context.get('earned_progress',{}).get(selector,{})
        upgrades=progress.get('upgrades',{})
        reserve=int(upgrades.get('reserve', upgrades.get('supplies', 0)))
        mastery=int(upgrades.get('mastery_capacity', upgrades.get('crafting', 0)))
        d['components']+=mastery
        for key in ('precision','force','ward','reserve','mastery_capacity',
                    'prefix_capacity','suffix_capacity','legendary_capacity'):
            d['upgrades'][key]=max(int(d['upgrades'].get(key,0)),int(upgrades.get(key,0)))
        d['upgrades'].update({'supplies':max(int(d['upgrades'].get('supplies',0)),reserve),
                              'crafting':max(int(d['upgrades'].get('crafting',0)),mastery)})
        d['meta_modifier_cap']=int(d['config'].get('modifier_cap',5))+d['upgrades']['mastery_capacity']
        rules=run.context.get('party_rules',{}).setdefault(f'p{index}',{})
        rules['precision_bonus']=int(upgrades.get('precision',0))
        rules['damage_bonus']=int(upgrades.get('force',0))
        ward=int(upgrades.get('ward',0))
        if ward:
            actor.armor_class+=ward
            rules['base_ac']=actor.armor_class
        for _ in range(reserve):add_item(run,'potion')
    return enter(run)


def state(run):
    if 'dungeon' not in run.context: raise t.ActionError('start a DESIGN dungeon first')
    return run.context['dungeon']


def ancestry_hook(run, key, kind, row):
    """Return the explicit ancestry lane used by a public noncombat check."""
    rules = run.context.get('party_rules', {}).get(key, {})
    tags = set(rules.get('interaction_tags', []))
    room_kind = row.get('kind')
    if 'monster_kin' in tags and kind == 'negotiate' and room_kind in {'combat', 'social'}:
        return {'id': 'monster_kin_parley', 'bonus': 3, 'skill': 'Persuasion',
                'effect': 'monster-facing parley is available'}
    if 'scrapwise' in tags and kind == 'avoid' and room_kind == 'hazard':
        return {'id': 'goblin_luck_hazard', 'bonus': 0, 'skill': 'Luck',
                'effect': 'the authored hazard calls for Luck'}
    if 'common_ground' in tags and kind == 'negotiate':
        return {'id': 'human_common_ground', 'bonus': 1, 'skill': 'Persuasion',
                'effect': 'shared institutions soften the opening position'}
    if 'old_magic' in tags and kind == 'investigate':
        return {'id': 'elf_old_magic', 'bonus': 2, 'skill': 'Investigation',
                'effect': 'old construction and magical residue are legible'}
    if 'bridge_kin' in tags and kind == 'negotiate':
        return {'id': 'half_elf_bridge_kin', 'bonus': 2, 'skill': 'Persuasion',
                'effect': 'dual cultural access opens a mediation lane'}
    if 'force_route' in tags and kind == 'disarm':
        return {'id': 'orc_force_route', 'bonus': 2, 'skill': 'Athletics',
                'effect': 'a force-based mechanism solution is available'}
    return None


def origin_hook(run, key, kind, row):
    hook = run.context.get('party_rules', {}).get(key, {}).get('origin_hook')
    room_kind = row.get('kind')
    rules = {
        'family_connection_1': ({'negotiate'}, None, 1, 'remembered family connection'),
        'route_clue_1': ({'investigate','avoid'}, None, 1, 'weathered route clue'),
        'light_source_1': ({'investigate'}, {'hazard','secret'}, 1, 'reliable lantern'),
        'trade_token_1': ({'negotiate'}, {'shop'}, 1, 'recognized trade token'),
        'tool_mechanism_2': ({'disarm'}, None, 2, 'balanced mechanism tools'),
        'tool_climb_2': ({'avoid'}, None, 2, 'climbing equipment'),
        'tool_medicine_2': ({'investigate'}, {'hazard'}, 2, 'field medicine kit'),
        'tool_scout_2': ({'investigate'}, None, 2, 'survey lens'),
        'tool_deception_2': ({'negotiate'}, None, 2, 'marked cards and misdirection'),
        'legacy_1': ({'negotiate'}, None, 1, 'ancestor heirloom'),
        'brace_1': ({'avoid'}, {'hazard'}, 1, 'old guard clasp'),
        'ward_thread_1': ({'disarm'}, {'hazard'}, 1, 'protective ward thread'),
        'safe_rest_1': ({'investigate'}, {'rest'}, 1, 'pilgrim rest tradition'),
        'passage_warmth_2': ({'investigate'}, {'secret'}, 2, 'warm whisper coin'),
        'ember_light_1': ({'investigate'}, {'hazard','secret'}, 1, 'ember glass light'),
        'echo_tone_1': ({'investigate'}, None, 1, 'echoed construction tone'),
        'truth_glint_1': ({'negotiate'}, None, 1, 'truth glint'),
        'salvage_luck_1': ({'avoid'}, {'hazard'}, 1, 'salvage tug'),
    }
    if hook not in rules:
        return None
    actions, room_kinds, bonus, effect = rules[hook]
    if kind not in actions or room_kinds is not None and room_kind not in room_kinds:
        return None
    return {'id': hook, 'bonus': bonus, 'effect': effect}


def wayfinder_check(run, key, row):
    rules = run.context.get('party_rules', {}).get(key, {})
    used = row.setdefault('origin_triggers', [])
    if rules.get('origin_hook') != 'wayfinder_25' or 'wayfinder_25' in used:
        return None
    chance = run.rng.randint(1, 100); used.append('wayfinder_25')
    return {'roll': chance, 'threshold': 25, 'triggered': chance <= 25,
            'item': rules.get('origin_item_id')}


def clone_for_transition(run):
    """Clone a run transactionally without recopying immutable content.

    ``RunService`` must be able to roll back a failed action, so the candidate
    still owns every mutable runtime object that a transition changes. Dungeon
    configuration and the validated module and registry payloads are source
    snapshots, however, and are only read after a run starts. Append-only
    history records are shallow-copied at their record boundary because the
    engine never mutates a committed record. Memo-sharing those payloads avoids
    repeated O(history) deep copies while retaining the non-mutation boundary
    for returned state.
    """
    candidate = copy.copy(run)
    # One memo per roster (as deepcopy did) so effects shared between actors
    # stay shared; each Actor copies itself via Actor.__deepcopy__/fast_clone.
    candidate.party = fast_deepcopy(run.party)
    candidate.opposition = fast_deepcopy(run.opposition)
    candidate.environment = fast_deepcopy(run.environment)
    candidate.transcript = list(run.transcript)
    candidate.rng = copy.copy(run.rng)
    candidate.rng._r = clone_random(run.rng._r)

    def share_append_only_records(memo, records):
        if not isinstance(records, list):
            return
        memo[id(records)] = [dict(record) if isinstance(record, dict) else record
                             for record in records]

    shared = {}
    dungeon_state = run.context.get('dungeon')
    if isinstance(dungeon_state, dict) and 'config' in dungeon_state:
        shared[id(dungeon_state['config'])] = dungeon_state['config']
        share_append_only_records(shared, dungeon_state.get('events'))
        share_append_only_records(shared, dungeon_state.get('discoveries'))
        share_append_only_records(shared, dungeon_state.get('receipts'))
        share_append_only_records(shared, dungeon_state.get('navigation_history'))
        share_append_only_records(shared, dungeon_state.get('meta_reward_history'))
        pressure = dungeon_state.get('pressure')
        if isinstance(pressure, dict):
            share_append_only_records(shared, pressure.get('history'))
        checkpoint = dungeon_state.get('checkpoint')
        if isinstance(checkpoint, dict):
            share_append_only_records(shared, checkpoint.get('history'))
        event_clock = dungeon_state.get('event_clock')
        if isinstance(event_clock, dict):
            share_append_only_records(shared, event_clock.get('history'))
        baseline_party = dungeon_state.get('baseline_party')
        if baseline_party is not None:
            shared[id(baseline_party)] = baseline_party
        rooms = dungeon_state.get('rooms')
        if isinstance(rooms, dict):
            active_key = f"{dungeon_state.get('floor')}:{dungeon_state.get('room')}"
            for r_key, r_val in rooms.items():
                if r_key != active_key and isinstance(r_val, dict):
                    shared[id(r_val)] = r_val
    for key in ('world', 'content_registry', 'module_content', 'party_rules',
                'baseline_party', 'earned_progress'):
        value = run.context.get(key)
        if value is not None:
            shared[id(value)] = value
    combat_state = run.context.get('combat')
    if isinstance(combat_state, dict):
        share_append_only_records(shared, combat_state.get('events'))
    share_append_only_records(shared, run.context.get('dungeon_history'))
    share_append_only_records(shared, run.context.get('reset_history'))
    # JSON-shaped state walks through fast_deepcopy; Actors/Items/dataclasses
    # inside it still reach copy.deepcopy with the same memo.
    candidate.context = fast_deepcopy(run.context, shared)
    return candidate


def room(run):
    d=state(run)
    return d['rooms'][f"{d['floor']}:{d['room']}"]


def _pressure(run, action_type, *, minutes=None, noise=0, rest=False):
    """Advance transparent run-local pressure; never secretly buffs opposition."""
    d = state(run)
    pressure = d.setdefault('pressure', {'minutes_elapsed':0, 'fatigue':0,
        'light_minutes':120, 'noise':0, 'alarm':0, 'scale':'mortal',
        'clocks':{'environment':0,'faction':0}, 'history':[]})
    if minutes is None:
        minutes = {'observe_room':1,'inspect_room':2,'inspect_object':2,
                   'search_object':10,'open_object':5,'light_source':1,
                   'enter_subroom':5,'investigate':5,'negotiate':3,
                   'avoid':5,'fight':1,'attack':1,'cast':1,'move':1,
                   'rest':360}.get(action_type, 0)
    minutes = max(0, int(minutes))
    before = dict(pressure)
    pressure['minutes_elapsed'] += minutes
    pressure['light_minutes'] = max(0, pressure.get('light_minutes', 120) - minutes)
    pressure['fatigue'] = max(0, pressure.get('fatigue', 0) + (minutes // 60 if not rest else -6))
    pressure['noise'] = max(0, pressure.get('noise', 0) + int(noise) - (1 if action_type in {'observe_room','rest'} else 0))
    if noise:
        pressure['alarm'] += max(0, int(noise))
    pressure['clocks']['environment'] += minutes
    if pressure['noise'] >= 10:
        pressure['clocks']['faction'] += 1
    d['greed'] = round(min(1.0, sum(int(item.get('value', 0)) for item in d.get('inventory', {}).values()) / 100), 4)
    d['attrition'] = round(min(1.0, (d.get('rooms_cleared', 0) / 20) + pressure['noise'] / 100 + pressure['alarm'] / 200), 4)
    fatigue = pressure['fatigue']
    pressure['scale'] = 'divine' if any(getattr(a, 'band', None) and getattr(a.band, 'name', '') == 'STEWARD' for a in run.party) else ('legendary' if d['floor'] >= 3 else 'mortal')
    receipt = {'action': action_type, 'minutes': minutes,
               'time_after_minutes': pressure['minutes_elapsed'],
               'fatigue_after': fatigue, 'light_minutes_after': pressure['light_minutes'],
               'noise_after': pressure['noise'], 'alarm_after': pressure['alarm'],
               'greed': d['greed'], 'attrition': d['attrition'],
               'observable_escalation': pressure['noise'] >= 10 or pressure['fatigue'] >= 6,
               'scale': pressure['scale']}
    pressure['history'].append(receipt)
    clock.emit(d, 'action', seconds=minutes * 60,
               room=f"{d['floor']}:{d['room']}", phase='gauntlet',
               payload={'action': action_type, 'minutes': minutes})
    tracking.ensure(d)['gameplay_minutes'] = pressure['minutes_elapsed']
    tracking.action(d)
    return receipt


def available_actions(run, row):
    """Project only actions the current public room can actually accept."""
    d = state(run)
    combat_state = run.context.get('combat')
    if isinstance(combat_state, dict) and not combat_state.get('complete'):
        return []
    actions = [('inspect', 'Inspect current state'), ('observe_room', 'Observe room')]
    from hollowstar.attunement import eligibility
    decantable = any(eligibility(item)[0] for item in d.get('inventory', {}).values())
    if row.get('resolved'):
        actions.append(('exit', 'Continue to the next room'))
        if row.get('checkpoint') and row.get('safe_room'):
            banked = d.get('checkpoint', {}).get('banked')
            if not banked or banked.get('room_id') != f"{d['floor']}:{d['room']}":
                actions.append(('checkpoint', 'Bank threshold checkpoint'))
        if d.get('navigation_history'):
            actions.append(('recover_previous_room', 'Return to previous room'))
        if decantable:
            actions.append(('decant', 'Decant an item into your Attunement'))
        return [{'id': action, 'label': label} for action, label in actions]

    labels = {
        'investigate': 'Investigate', 'negotiate': 'Negotiate',
        'avoid': 'Avoid', 'disarm': 'Disarm the hazard', 'fight': 'Fight',
    }
    approaches = list(row.get('counterplay', []))
    if row.get('kind') == 'hazard' and 'disarm' not in approaches:
        approaches.append('disarm')
    attempted = set(row.get('attempts', []))
    for approach in approaches:
        if approach in labels and approach not in attempted:
            actions.append((approach, labels[approach]))

    if row.get('kind') == 'rest':
        actions.append(('rest', 'Rest'))
    if row.get('kind') == 'shop':
        stock = row.get('stock', {})
        if any(d.get('currency', 0) >= int(cost) and row.get('purchases', []).count(product) < 3
               for product, cost in stock.items() if product != 'room'):
            actions.append(('buy', 'Buy an available item'))
    room_cost = int(d.get('config', {}).get('shop', {}).get('room', 10))
    if (row.get('floor') == 1 and row.get('kind') == 'social'
            and 'room' not in row.get('purchases', []) and d.get('currency', 0) >= room_cost):
        actions.append(('buy', f'Rent room — {room_cost} gold'))
    identification_cost = int(d.get('config', {}).get('identification_cost', 5))
    if (row.get('identification_service') and d.get('currency', 0) >= identification_cost
            and any(item.get('kind') == 'imprint' and not item.get('identified', False)
                    for item in d.get('inventory', {}).values())):
        actions.append(('identify', f'Identify a Rune — {identification_cost} gold'))

    from hollowstar import room_state
    world = room_state.observe(row)
    objects = list((world.get('objects') or {}).values())
    if objects:
        actions.extend((('inspect_object', 'Inspect a visible object'),
                        ('search_object', 'Search a visible object')))
    if any(obj.get('kind') in {'cabinet', 'container'} and not obj.get('open') for obj in objects):
        actions.append(('open_object', 'Open a visible container'))
    if (not world.get('lighting', {}).get('illuminated')
            and any(getattr(actor, 'name', '').lower() == 'wren' for actor in run.party)):
        actions.append(('light_source', 'Create a supported light source'))
    if world.get('subrooms'):
        actions.append(('enter_subroom', 'Enter a visible subroom'))
    if d.get('navigation_history'):
        actions.append(('recover_previous_room', 'Return to previous room'))
    if decantable:
        actions.append(('decant', 'Decant an item into your Attunement'))
    return [{'id': action, 'label': label} for action, label in actions]


def _party_scale(run, dungeon_config):
    """Launch-frozen opposition factor in (0, 1]. Only a party carrying a
    custom profile is scaled, and never upward."""
    rule = dungeon_config.get('party_scaling')
    selectors = [str(s) for s in run.context.get('party_selectors', [])]
    if not isinstance(rule, dict) or not any(s.startswith('custom:') for s in selectors):
        return 1.0
    total = sum(max(1, int(actor.max_hp)) for actor in run.party)
    factor = total / max(1, int(rule.get('reference_party_hp', total)))
    return round(max(float(rule.get('min_factor', 0.2)), min(1.0, factor)), 3)


def scaled_enemy_spec(spec, factor, rule):
    """The floor's own fixture, shrunk toward a weaker party. Tells, types,
    resistances and traits are untouched; only the numbers move."""
    if factor >= 1:
        return spec
    spec = copy.deepcopy(spec)
    gap = 1 - factor
    spec['hp'] = max(1, round(spec['hp'] * factor))
    spec['ac'] = spec['ac'] - round(gap * rule.get('ac_step', 4))
    spec['attack'] = spec['attack'] - round(gap * rule.get('attack_step', 6))
    die, _, modifier = spec['dice'].partition('+')
    spec['dice'] = f"{die}+{round(int(modifier or 0) * factor)}"
    if factor < rule.get('single_attack_below', 0.5):
        spec['attacks'] = 1
        spec.pop('pool', None)
        spec.pop('bonus_attack_resource', None)
    weapon = spec.get('weapon')
    if isinstance(weapon, dict):
        if 'damage_modifier' in weapon:
            weapon['damage_modifier'] = round(int(weapon['damage_modifier']) * factor)
        if 'attack_bonus' in weapon:
            weapon['attack_bonus'] = int(weapon['attack_bonus']) - round(gap * rule.get('attack_step', 6))
    return spec


def enemy(spec,index,boss=False):
    """One fixture resident, carrying the systems the engine actually runs.

    Until 2026-09-05 this built hp/ac/attack/dice and nothing else, so a
    resident had default 10s across the board, no saves worth rolling, no
    pool to spend and one attack. Against a STEWARD-band pair that is an
    inert target, which is why every finishing rehearsal landed identically.
    The Actor shape already carried band, ability scores, multiattack and
    resources; the fixture simply never filled them in. It does now, from
    `content/dungeon.json`, and every value there is an editable DESIGN
    number rather than certified balance.
    """
    hp=spec['hp']*(2 if boss else 1)
    pool=spec.get('pool')
    optional={}
    if spec.get('abilities'): optional['ability_scores']=dict(spec['abilities'])
    weapon = spec.get('weapon', {})
    return Actor(name=f"{spec['name']} {index+1}",max_hp=hp,hp=hp,armor_class=spec['ac'],
        band=Band(spec.get('band',10)),
        speed=spec['speed'],initiative_bonus=2,controller='npc',
        attacks_per_action=spec.get('attacks',1),
        **optional,
        resources={pool['name']:pool['amount']} if pool else {},
        equipment=[Item(name=weapon.get('name', 'resident weapon'),slot='hand',
            damage_dice=weapon.get('damage_dice', spec['dice'].split('+')[0]),
            damage_modifier=int(weapon.get('damage_modifier', spec['dice'].split('+')[1])),
            attack_bonus=int(weapon.get('attack_bonus', spec['attack'])),
            tags={DamageTag[weapon.get('type', spec['type'])]})],
        provenance=Provenance(owner_file='hollowstar/content/dungeon.json',snapshot_version='hsr-design-1',
            fidelity='fixture',verified=False,note='Explicit DESIGN opposition; no certification or level-20 balance claim.'))


def procedural_enemy(run, spec, index=0, tier=None):
    from hollowstar import npc_generator
    resolved_tier = tier or spec.get('tier') or ('champion' if spec.get('boss') else 'elite' if spec.get('elite') else 'common')
    return npc_generator.generate_enemy(spec, spec.get('name', 'foe'), tier=resolved_tier, index=index, rng=getattr(run, 'rng', None))


def enter(run):
    d=state(run)
    previous_floor,previous_room=d['floor'],d['room']
    if d['status']!='active': raise t.ActionError('run has ended; re-enter with a new run ID')
    if d['room'] and not room(run)['resolved']: raise t.ActionError('resolve or leave this room first')
    floor_count = len(d['config']['floors'])
    room_count = len(_room_types_for_floor(d, d['floor']))
    if room_count < 1:
        raise t.ActionError(f"authored floor {d['floor']} has no rooms")
    if d['floor']==floor_count and d['room']==room_count:
        tracking.floor_completed(d, d['floor'])
        return end(run,'cleared')
    d['room']+=1
    if d['room']>room_count:
        tracking.floor_completed(d, d['floor'])
        d['floor']+=1;d['room']=1
    if d['floor']>floor_count:
        return end(run,'cleared')
    room_id=f"{d['floor']}:{d['room']}"
    tracking.ensure(d)['rooms_entered'] += 1
    tracking.ensure(d)['floors_reached'] = max(tracking.ensure(d)['floors_reached'], d['floor'])
    if room_id in d['rooms']:
        row=d['rooms'][room_id]
        if row.get('kind') in {'combat','boss'} and not row.get('resolved'):
            combat(run,boss=row.get('kind')=='boss')
        result={'type':'reentered','room':public_room(row),'world':copy.deepcopy(run.context.get('world',{})),
                'evidence':{'room_id':room_id,'state_reused':True,'hidden_metadata_omitted':True}}
        d['events'].append(result)
        clock.emit(d, 'room_enter', room=room_id, phase='gauntlet',
                   payload={'reentered': True})
        return result
    floor=d['config']['floors'][d['floor']-1]
    room_types = _room_types_for_floor(d, d['floor'])
    kind = room_types[d['room']-1]
    # An Encounters expedition picks the next node's kind and wave ladder;
    # see hollowstar/expedition.py. Generation, rolls and rewards stay here.
    next_room = d.pop('next_room', None)
    next_room = next_room if isinstance(next_room, dict) else {}
    kind = next_room.get('kind', kind)
    module_rooms = _module_floor_rooms(d, d['floor'])
    module_row = module_rooms[d['room']-1] if module_rooms else {}
    room_overrides = floor.get('room_overrides', {})
    if not isinstance(room_overrides, dict):
        raise t.ActionError('floor room_overrides must be an object')
    room_override = room_overrides.get(kind, {})
    if not isinstance(room_override, dict):
        raise t.ActionError(f'room override for {kind} must be an object')
    encounter_mode = module_row.get('encounter_mode', room_override.get(
        'encounter_mode', floor.get('encounter_mode')))
    encounter_mode = next_room.get('encounter_mode', encounter_mode)
    if encounter_mode not in {None, 'turn_based', 'arcade'}:
        raise t.ActionError(f'unsupported encounter mode: {encounter_mode}')
    if encounter_mode == 'arcade' and kind not in {'combat', 'boss'}:
        raise t.ActionError('arcade encounters must be combat or boss rooms')
    registry = run.context.get('content_registry') or load_registry()
    run.context['content_registry'] = registry
    authored = room_content(registry, d['floor']) or {}
    rng=run.rng.fork(f"room:{d['floor']}:{d['room']}")
    greed = float(d.get('greed', 0))
    attrition = float(d.get('attrition', 0))
    chance=min(.92,.12+.14*(d['floor']-1)+.025*(d['room']-1)+(.25 if kind=='boss' else 0)+.10*greed)
    stacked=rng.random()<chance
    if next_room.get('stacked'):
        stacked=True
    tell={'id':f"tell:{d['floor']}:{d['room']}:0",'text':module_row.get('tell', floor['tell']),
          'dc':int(floor.get('observation_dc',10+d['floor']))}
    authored_tells=[{'id':f"tell:{d['floor']}:{d['room']}:{item['id']}",
                     'text':item['text'],'dc':int(floor.get('observation_dc',10+d['floor']))}
                    for item in authored.get('tells',[])]
    authored_objects=[]
    authored_hooks=[]
    for hook in authored.get('hooks',[]):
        item=copy.deepcopy(hook)
        object_id=item.get('object_id')
        if isinstance(object_id,str) and ':' not in object_id:
            item['object_id']=f"{d['floor']}:{d['room']}:{object_id}"
        authored_hooks.append(item)
    for item in authored.get('objects',[]):
        obj=copy.deepcopy(item)
        object_id=f"{d['floor']}:{d['room']}:{obj['id']}"
        obj['runtime_object_id']=object_id
        authored_objects.append(obj)
        hook=obj.get('hook')
        if isinstance(hook,dict):
            authored_hooks.append({'id':f"{d['floor']}:{d['room']}:{obj['id']}:hook",
                                   'trigger':hook.get('trigger','inspect'),
                                   'object_id':object_id,'text':hook.get('text',''),
                                   'reward':copy.deepcopy(hook.get('reward'))})
    row={'floor':d['floor'],'number':d['room'],'kind':kind,'title':module_row.get('title', f"{floor['name']} - {kind}"),
        'function':module_row.get('function', floor.get('true_function',kind)),
        'apparent_function':module_row.get('apparent_function', floor.get('apparent_function',kind)),
        'resident':module_row.get('resident',floor['resident']),
        'motive':module_row.get('motive',floor['motive']),
        'law':module_row.get('law',floor['law']),
        'terrain':module_row.get('terrain',floor['terrain']),
        'posture':module_row.get('posture',floor.get('posture','present')),'tells':[tell]+authored_tells,
        'counterplay':module_row.get('counterplay',['investigate','negotiate','avoid','fight']),
        'persistence':{'room_id':f"{d['floor']}:{d['room']}",'state':'generated and retained for return visits'},
        'perceived_facts':[],
        'resolved':False,'visited':True,'attempts':[],'reward_claimed':False,
        'secret':module_row.get('secret',floor['secret']),'hazard':module_row.get('hazard',floor['hazard']),
        'revealed':False,'stacked':stacked,
        'prose_revealed':False,'content_source':copy.deepcopy(authored.get('source')),
         'atmosphere':authored.get('atmosphere',''),'authored_objects':authored_objects,
         'authored_hooks':authored_hooks,'fired_hooks':[],
         'checkpoint':bool(module_row.get('checkpoint', kind=='rest')),
         'safe_room':bool(module_row.get('safe_room', kind=='rest')),
          'escape_routes':copy.deepcopy(module_row.get('escape_routes', ['balconies','lower route'] if d['floor']==5 and kind=='boss' else [])),
          'identification_service': d['floor'] < 5 and kind in {'social','shop','rest'},
          'coordination_pressure': round(min(1.0, attrition), 4),
         'stock':dict(d['config']['shop']) if kind=='shop' else {},'purchases':[], 'night_patrol':False,
         'encounter_mode': encounter_mode}
    structures = module_row.get('structures', room_override.get('structures', floor.get('structures')))
    if structures:
        row['structures'] = copy.deepcopy(structures)
    for field in ('waves', 'arcade_enemy_count'):
        if field in next_room:
            row[field] = copy.deepcopy(next_room[field])
        elif field in module_row:
            row[field] = copy.deepcopy(module_row[field])
        elif field in room_override:
            row[field] = copy.deepcopy(room_override[field])
        elif field in floor:
            row[field] = copy.deepcopy(floor[field])
    if module_row.get('actor_id'):
        row['actor_id'] = module_row['actor_id']
    from hollowstar import room_state
    room_state.generate(run, row)
    d['rooms'][room_id]=row
    tracking.room_entered(d, kind)
    run.opposition=[]
    run.context.pop('combat',None)
    if kind in {'combat','boss'}:
        combat(run,boss=kind=='boss')
    result={'type':'entered','room':public_room(row),'world':copy.deepcopy(run.context.get('world',{})),
            'narrator':{'voice':'residents and environment; divine dialogue remains Corey-owned',
                        'purpose':'adventure, curiosity, investigation, and shared enjoyment'}}
    result['evidence']={'room_id':f"{d['floor']}:{d['room']}",
                        'generated_lazily':True,'hidden_metadata_omitted':True,
                        'hidden_metadata_count':2}
    if d['floor'] != previous_floor:
        result['floor_transition']={'from':previous_floor,'to':d['floor'],
                                     'completed_room':previous_room}
    d['events'].append(result)
    clock.emit(d, 'room_enter', room=room_id, phase='gauntlet',
               payload={'generated_lazily': True, 'floor': d['floor']})
    return result


def public_room(row, *, include_prose: bool | None = None):
    prose_visible = row.get('prose_revealed',False) if include_prose is None else include_prose
    visible={k:copy.deepcopy(row[k]) for k in (
        'floor','number','title','apparent_function','resident','posture','law','terrain',
        'tells','persistence','perceived_facts','resolved','visited','attempts','reward_claimed',
        'escape_routes','purchases','night_patrol','checkpoint','safe_room','content_source',
        'identification_service','encounter_mode') if k in row}
    from hollowstar import room_state
    visible['world_state'] = room_state.observe(row)
    known={fact.get('tell_id') for fact in row.get('perceived_facts',[])}
    visible['tells']=[]
    for tell in row.get('tells',[]):
        item={'id':tell['id']}
        if prose_visible or tell.get('id') in known:
            item['text']=tell['text']
        visible['tells'].append(item)
    visible['prose_available']=bool(row.get('atmosphere'))
    if prose_visible:
        visible['atmosphere']=row.get('atmosphere','')
        visible['authored_tells']=[{'id':tell['id'],'text':tell['text']} for tell in row.get('tells',[])]
    return visible


def discover(run,row):
    """Compatibility helper: perception now owns all durable discoveries."""
    return bool(row.get('perceived_facts'))


def _tell(row, tell_id=None):
    tells=row.get('tells',[])
    if tell_id is None and tells:
        return tells[0]
    for tell in tells:
        if tell.get('id') == tell_id:
            return tell
    raise t.ActionError('unknown room tell')


def test_perception(run, action):
    d=state(run);row=room(run)
    actor_id=action.get('actor','p0')
    actor=t.actor(run,actor_id)
    if not actor.alive: raise t.ActionError('invalid party actor')
    if 'combat' in run.context and not run.context['combat']['complete']:
        if actor_id != t.current(run): raise t.ActionError('not this actor turn')
        if not action.get('_action_spent'):
            t.use(run,actor_id,'action')
    tell=_tell(row,action.get('tell_id'))
    known={fact.get('tell_id') for fact in row.get('perceived_facts',[])}
    if tell['id'] in known:
        fact=next(f for f in row['perceived_facts'] if f.get('tell_id')==tell['id'])
        return {'type':'perception_already_known','tell_id':tell['id'],
                'fact':copy.deepcopy(fact),
                'evidence':{'new_fact':False,'room_id':f"{d['floor']}:{d['room']}"}}
    from hollowstar.affix_runtime import skill_bonus
    bonus=actor.skill_bonuses.get('Perception',actor.skill_bonuses.get('perception',0)) + skill_bonus(run,actor_id,'Perception')
    check=t.roll_check(run,bonus,int(tell['dc']))
    fact={'tell_id':tell['id'],'text':tell['text'],'source':'tested perception'}
    if check['success']:
        row.setdefault('perceived_facts',[]).append(fact)
        if fact['text'] not in d['discoveries']: d['discoveries'].append(fact['text'])
    return {'type':'perception_test','check':check,
            'fact':copy.deepcopy(fact) if check['success'] else None,
            'evidence':{'actor':actor.name,'skill':'Perception','bonus':bonus,'dc':tell['dc'],
                        'new_fact':bool(check['success']),'room_id':f"{d['floor']}:{d['room']}"}}


def reveal_room_record(run):
    d=state(run);row=room(run)
    room_id=f"{d['floor']}:{d['room']}"
    sealed={k:copy.deepcopy(row[k]) for k in (
        'floor','number','title','function','motive','law','terrain','kind','tells',
        'counterplay','secret','hazard','stacked','stock','escape_routes','atmosphere',
        'content_source','authored_objects','authored_hooks') if k in row}
    receipt={'receipt_id':f"sealed-room:{room_id}:{len(d.get('receipts',[]))+1}",
             'command':'reveal-room-record','room_id':room_id,'sealed_record':sealed}
    d.setdefault('receipts',[]).append(copy.deepcopy(receipt))
    return {'type':'room_record_revealed','sealed_record':sealed,
            'receipt':{'receipt_id':receipt['receipt_id'],'room_id':room_id,
                       'fields':sorted(sealed)},
            'evidence':{'explicit_fetch':True,'receipt_id':receipt['receipt_id']}}


def combat(run,boss=False):
    d=state(run);floor=d['config']['floors'][d['floor']-1];row=room(run)
    enemy_spec = floor['enemy']
    module_actors = run.context.get('module_content', {}).get('actors', {}).get('actors', [])
    actor_id = row.get('actor_id') or floor.get('actor_id')
    if actor_id and module_actors:
        matches = [entry for entry in module_actors if entry.get('actor_id') == actor_id]
        if not matches:
            raise t.ActionError(f'module actor fixture not found: {actor_id}')
        authored = copy.deepcopy(matches[0])
        enemy_spec = copy.deepcopy(floor['enemy'])
        enemy_spec.update({k: v for k, v in authored.items() if k != 'actor_id'})
        equipment_id = authored.get('equipment_id')
        module_equipment = run.context.get('module_content', {}).get('equipment', {}).get('equipment', [])
        if equipment_id and module_equipment:
            equipment = [item for item in module_equipment if item.get('equipment_id') == equipment_id]
            if not equipment:
                raise t.ActionError(f'module equipment fixture not found: {equipment_id}')
            enemy_spec['weapon'] = copy.deepcopy(equipment[0])
    scale = d.get('opposition_scale', 1.0)
    if scale < 1:
        enemy_spec = scaled_enemy_spec(enemy_spec, scale, d['config'].get('party_scaling', {}))
    configured_count = row.get('arcade_enemy_count')
    if configured_count is not None:
        if type(configured_count) is not int or configured_count < 1:
            raise t.ActionError('arcade_enemy_count must be a positive integer')
        count = configured_count
    else:
        count=5 if d['floor']==5 and boss else 2 if row['stacked'] else 1
    run.opposition=[enemy(enemy_spec,i,boss) for i in range(count)]
    if actor_id and enemy_spec.get('equipment_ids'):
        from hollowstar.modules import module_roster
        prototype = module_roster(run.context['module_content'])[actor_id]
        run.opposition = [copy.deepcopy(prototype) for _ in range(count)]
    rs=copy.deepcopy(d['party_rules'])
    spec=enemy_spec
    for i in range(count):
        # A stacked room adds SLASHING on top of the floor's own sourced
        # resistances rather than replacing them, so the stack reads as an
        # extra layer with its own tell instead of a substitution.
        resistances=list(spec.get('resistances',[]))
        if row['stacked'] and 'SLASHING' not in resistances: resistances.append('SLASHING')
        weapon = run.opposition[i].weapon()
        rs[f'e{i}']={'damage_type':spec['type'],'range':[weapon.range_normal, weapon.range_long] if weapon else [5,5],
                    'size':spec.get('size','medium'),
                    'resistances':resistances,
                    'condition_immunities':list(spec.get('condition_immunities',[])),
                    'saves':dict(spec.get('saves',{})) or None,
                    'attacks':spec.get('attacks',1),
                    'bonus_attack_resource':spec.get('bonus_attack_resource') or (spec.get('pool') or {}).get('name'),
                    'trait':spec.get('trait',''),
                    'formation':'stacked' if row['stacked'] else 'screen',
                    'motive':row['motive'],'counterplay':list(row['counterplay']),
                    'retreat_threshold':spec.get('retreat_threshold',0.20),
                    'base_ac':run.opposition[i].armor_class,
                    # Optional authored Immunity Lattice rows and source
                    # authority (hollowstar/lattice.py); absent means none.
                    'lattice':copy.deepcopy(spec.get('lattice')) or None,
                    'authority_tier':spec.get('authority_tier')}
        rs[f'e{i}']={k:v for k,v in rs[f'e{i}'].items() if v is not None}
    t.begin(run,rs)
    terrain=run.context['combat']['terrain']
    from hollowstar import room_state
    terrain.update(room_state.combat_geometry(row))
    terrain['human_tight']=d['floor']==1
    terrain['difficult']=[[25,y,0] for y in range(0,120,5)] if d['floor'] in {2,4} else []
    terrain['dark']=d['floor']==4
    if d['floor']==5 and boss:
        row['cocoon']={'rounds':d['config']['cocoon_rounds'],'opened':False}
    if row.get('encounter_mode') == 'arcade':
        from hollowstar import arcade
        arcade.enter_from_room(run, row)


def award(run,method):
    d=state(run);row=room(run)
    if row['reward_claimed']: raise t.ActionError('room reward already claimed')
    row['resolved']=True;row['reward_claimed']=True
    d['rooms_cleared']+=1;d['rank_xp']+=1
    tracking.room_resolved(d, row['kind'])
    d['hsr_rank']=min(10,1+d['rank_xp']//4)
    reward=5+d['floor']*3
    d['currency']+=reward;d['components']+=1
    tracking.gold(d, reward, kind='earned')
    # Platinum is a persistent run-value currency.  It scales with depth,
    # room count, and discoveries while remaining separate from run Gold and
    # Gems.  The old boss bonus remains as a final-floor premium.
    meta_award = max(1, d['floor'] + ((d['room'] - 1) // 3))
    meta_award += min(2, len(d.get('discoveries', [])) // 2)
    if row['kind']=='boss':
        has_tarrasque=any(t.rules(run,k).get('identity')=='tarrasque' for k in t.actors(run))
        d['final_floor']='actual_final_floor_complete' if has_tarrasque else 'boss_victory_only'
        add_item(run,'imprint',identified=False)
        meta_award += 2
    d['meta_currency'] += meta_award
    d.setdefault('meta_reward_history', []).append({
        'room': f"{d['floor']}:{d['room']}", 'kind': row['kind'],
        'amount': meta_award, 'depth': d['floor'],
        'discoveries': len(d.get('discoveries', [])),
    })
    tracking.ensure(d)['platinum_earned'] += meta_award
    clock.emit(d, 'room_resolved', room=f"{d['floor']}:{d['room']}",
               phase='gauntlet', payload={'method': method, 'meta_award': meta_award})
    relic = None
    if run.rng.fork(f"relic-room-{d['floor']}:{d['room']}").random() < min(.18, .03 + .02 * d['floor']):
        relic = add_item(run, 'relic')
    return {'type':'room_resolved','method':method,'currency':reward,'gold':reward,
            'components':1,'gems':1,'hsr_rank':d['hsr_rank'],'relic':copy.deepcopy(relic),
            'evidence':{'room_id':f"{d['floor']}:{d['room']}",
                        'state_change':'room resolved and reward claimed',
                        'currency_after':d['currency'],'gold_after':d['currency'],
                        'components_after':d['components'],'gems_after':d['components'],
                        'platinum_awarded':d['meta_currency'],
                        'meta_reward':meta_award}}


def resolved_check_event(kind, check, evidence, reward):
    """Keep successful room checks flat for every adapter surface."""
    return {'type':'room_resolved','method':kind,'check':check,'evidence':evidence,
            'reward':reward,'receipt':reward}


def record_final_floor_completion(run):
    """Upgrade the classification when a spawned Tarrasque dies.

    The ordinary boss can resolve and claim the room reward before the cocoon
    expires, so completion cannot depend on calling ``award`` again.
    """
    d=state(run)
    if d['floor'] != 5:
        return None
    tarrasques=[k for k in t.actors(run) if t.rules(run,k).get('identity')=='tarrasque']
    if tarrasques and all(not t.actor(run,k).alive for k in tarrasques):
        # Whoever is still standing on the rival side when it dies takes its loot.
        rivals=[k for k in t.actors(run) if not k.startswith('p') and k not in tarrasques and t.actor(run,k).alive]
        d.setdefault('tarrasque_loot', 'rivals' if rivals else 'party')
        _check_star_reveal(run)
        d['final_floor']='actual_final_floor_complete'
        return 'actual_final_floor_complete'
    _check_star_reveal(run)
    return None


def _check_star_reveal(run):
    """Last one standing in the palace, after the cocoon opened: the Star appears."""
    d=state(run)
    row=room(run) or {}
    if d.get('star_reveal') or not (row.get('cocoon') or {}).get('opened'):
        return None
    others=[k for k in t.actors(run) if not k.startswith('p') and t.actor(run,k).alive]
    party=[k for k in t.actors(run) if k.startswith('p') and t.actor(run,k).alive]
    if party and not others:
        d['star_reveal']={'round': run.round_number, 'survivors': [t.actor(run,k).name for k in party]}
    return d.get('star_reveal')


def add_item(run,kind,*,identified=None):
    d=state(run);ident=f"item-{d['next_item']}";d['next_item']+=1
    rng=run.rng
    slot=rng.choice(d['config']['imprint_slots']) if kind=='imprint' else None
    permanent=kind=='permanent_gear'
    if identified is None:
        identified = True
    item={'id':ident,'kind':kind,'name':'Permanent ward' if permanent else 'Healing potion',
        'temporary':not permanent,'slot':slot,'level':1,'modifiers':[],
        'rarity':'common','upgradeable':kind in {'imprint','permanent_gear'},
        'prefix':None,'suffix':None,'percentage_bonus':0,'value':5 if kind=='imprint' else 1,
        'identified':bool(identified),'unidentified_descriptor':None}
    if kind == 'relic':
        chosen=run.rng.fork(f'relic-{ident}').choice(rune_config()['relics'])
        item.update({'name':chosen['name'],'identified':True,'rarity':'rare','value':int(chosen.get('value',25)),
                     'upgradeable':False,'relic':True,'modifiers':[copy.deepcopy(chosen['modifier'])]})
    if kind=='imprint':
        catalog=rune_config()['runes']
        chosen=run.rng.fork(f'rune-{ident}').choice(catalog)
        item.update({'true_name':chosen['name'],'name':chosen['descriptor'],
                     'unidentified_descriptor':chosen['descriptor'],
                     'rarity':chosen['rarity'],'modifiers':copy.deepcopy(chosen['modifiers']),
                     'prefix':copy.deepcopy(chosen.get('prefix')),'suffix':copy.deepcopy(chosen.get('suffix')),
                     'identified':bool(identified),'value':int(chosen.get('value', 5))})
        if identified:
            item['name']=chosen['name']
        from hollowstar.affix_runtime import materialize_item_affixes, display_name
        materialize_item_affixes(item)
        item['display_name'] = display_name(item)
    d['inventory'][ident]=item
    if permanent:
        d['permanent_gear'][ident]=copy.deepcopy(d['inventory'][ident])
    return copy.deepcopy(d['inventory'][ident])


def _public_item(item):
    result=copy.deepcopy(item)
    if result.get('kind') == 'imprint' and not result.get('identified', False):
        descriptor=result.get('unidentified_descriptor', 'unidentified Rune')
        return {'id':result['id'],'kind':'imprint','name':descriptor,'temporary':True,
                'slot':result.get('slot'),'identified':False,'rarity':'unknown',
                'level':result.get('level', 1),'value':result.get('value', 0)}
    result.pop('true_name', None)
    from hollowstar.affix_runtime import materialize_item_affixes, display_name
    materialize_item_affixes(result)
    result['display_name'] = display_name(result)
    return result


def identify_item(run, item_id):
    d=state(run); row=room(run); item=d['inventory'].get(item_id)
    if not row.get('identification_service'):
        raise t.ActionError('no altar or traveling merchant can identify Runes here')
    if item is None or item.get('kind') != 'imprint':
        raise t.ActionError('only a Rune can be identified')
    if item.get('identified'):
        raise t.ActionError('Rune is already identified')
    cost=int(d['config'].get('identification_cost', 5))
    if d['currency'] < cost:
        raise t.ActionError('insufficient currency for identification')
    d['currency'] -= cost
    tracking.gold(d, cost, kind='spent')
    item['identified']=True; item['name']=item['true_name']
    return {'type':'rune_identified','item':copy.deepcopy(item),'cost':cost,
            'evidence':{'service':row.get('title'),'truth_revealed':True,
                        'currency_after':d['currency']}}


def combine_items(run, first_id, second_id, actor_key='p0'):
    d=state(run); first=d['inventory'].get(first_id); second=d['inventory'].get(second_id)
    if not first or not second or first.get('kind') != 'imprint' or second.get('kind') != 'imprint':
        raise t.ActionError('combining requires two Imprints')
    if not first.get('identified') or not second.get('identified'):
        raise t.ActionError('both Runes must be identified before combining')
    if d['components'] < 1:
        raise t.ActionError('combining requires one Gem')
    d['components'] -= 1
    new=add_item(run, 'imprint'); new_id=new['id']
    new['identified']=True; new['name']=f"{first['name']} / {second['name']}"
    new['true_name']=new['name']; new['rarity']='rare'; new['modifiers']=copy.deepcopy(first.get('modifiers', [])) + copy.deepcopy(second.get('modifiers', []))
    new['modifiers']=new['modifiers'][:int(d['config'].get('modifier_cap', 5))]
    # A combined Rune carries at most one prefix and one suffix.  The first
    # compatible source wins deterministically; no hidden stacking occurs.
    new['prefix']=copy.deepcopy(first.get('prefix') or second.get('prefix'))
    new['suffix']=copy.deepcopy(first.get('suffix') or second.get('suffix'))
    from hollowstar.affix_runtime import materialize_item_affixes, display_name
    materialize_item_affixes(new); new['display_name']=display_name(new)
    d['inventory'][new_id]=new; del d['inventory'][first_id]; del d['inventory'][second_id]
    for slots in d['imprints'].values():
        for slot, ident in list(slots.items()):
            if ident in {first_id, second_id}: del slots[slot]
    return {'type':'imprints_combined','item':copy.deepcopy(new),'actor':actor_key,
            'evidence':{'inputs':[first_id,second_id],'gem_spent':1,'modifier_cap':len(new['modifiers'])}}


def reforge_affix(run, item_id, affix_name, actor_key='p0'):
    """Attach one active Prefix or Suffix to an identified, run-local item."""
    d=state(run); item=d['inventory'].get(item_id)
    if item is None or item.get('kind') != 'imprint':
        raise t.ActionError('reforging requires an Imprint')
    if not item.get('identified'):
        raise t.ActionError('identify the Rune before reforging it')
    from hollowstar.affix_runtime import materialize, materialize_item_affixes, display_name
    affix=materialize(affix_name)
    if affix is None:
        raise t.ActionError('affix is not in the active HSR catalog')
    cost=int(d.get('config',{}).get('affix_reforge_cost',1))
    if d['components'] < cost:
        raise t.ActionError('reforging requires one Gem')
    previous=copy.deepcopy(item.get(affix['affix_type']))
    d['components']-=cost
    item[affix['affix_type']]=affix
    materialize_item_affixes(item); item['display_name']=display_name(item)
    if item_id in d.get('permanent_gear',{}): d['permanent_gear'][item_id]=copy.deepcopy(item)
    return {'type':'affix_reforged','item':copy.deepcopy(item),'actor':actor_key,
            'evidence':{'item':item_id,'affix':affix['name'],'affix_type':affix['affix_type'],
                        'replaced':previous.get('name') if isinstance(previous,dict) else None,
                        'gems_spent':cost,'gems_after':d['components']}}


def _open_system_hook(run, action):
    """Resolve small adapter-owned inventory/social hooks in the shared engine.

    These hooks intentionally mutate the run-local dungeon state only.  They
    give the browser and CLI a stable seam while leaving authored room rules
    and combat resolution in their existing paths.
    """
    d = state(run)
    kind = str(action.get('type', '')).lower()
    if kind in {'npc_list', 'list_npcs'}:
        return {'type': 'npc_list', 'npcs': copy.deepcopy(room(run).get('world_state', {}).get('npcs', {}))}
    if kind in {'conversation', 'talk', 'speak', 'bribe'}:
        target = str(action.get('target') or action.get('npc') or room(run).get('resident') or 'resident')
        mode = str(action.get('mode', 'speak'))
        if mode not in {'speak', 'ask', 'trade', 'threaten', 'insult', 'lie', 'bribe'}:
            raise t.ActionError('unsupported conversation mode')
        from hollowstar import conversation
        current_room = room(run)
        target_dict = {
            'name': target,
            'disposition': current_room.get('resident_disposition', 'neutral'),
            'traits': current_room.get('resident_traits', ['watchful']),
            'core_motive': current_room.get('resident_motive', 'duty'),
        }
        conv_res = conversation.resolve(target_dict, str(action.get('text', '')).strip(), mode=mode)
        current_room['resident_disposition'] = conv_res['disposition_after']
        return {'type': 'conversation_resolved', 'target': target, 'mode': mode,
                'text': conv_res['text'], 'reaction': conv_res['reaction'],
                'disposition': conv_res['disposition_after'], 'consequence': conv_res['consequence'],
                'surrender_offered': conv_res.get('surrender_offered', False),
                'truce_agreed': conv_res.get('truce_agreed', False),
                'evidence': {'npc_hook': True, 'room_id': f"{d['floor']}:{d['room']}",
                             'state_change': f"conversation receipt recorded: {conv_res['consequence']}"}}
    if kind in {'prepare_idle', 'idle_prepare'}:
        d['auto_preparation'] = {'enabled': bool(action.get('enabled', True)),
                                 'strategy': str(action.get('strategy', 'conservative')),
                                 'prepared_at': f"{d['floor']}:{d['room']}"}
        return {'type': 'idle_preparation', 'preparation': copy.deepcopy(d['auto_preparation'])}
    if kind in {'auto_battle', 'idle_battle', 'battle_prepare'}:
        d['auto_battle'] = {'enabled': bool(action.get('enabled', True)),
                            'strategy': str(action.get('strategy', 'safe'))}
        return {'type': 'auto_battle_prepared', 'auto_battle': copy.deepcopy(d['auto_battle']),
                'evidence': {'combat_present': bool(run.context.get('combat'))}}
    if kind in {'configure_macros', 'set_macros', 'macros'}:
        macros = action.get('macros')
        if not isinstance(macros, dict):
            raise t.ActionError('macros must be an object keyed by actor id')
        clean = {}
        for actor_key, entries in macros.items():
            if actor_key not in t.actors(run) or not actor_key.startswith('p'):
                raise t.ActionError('macros may only target living party actors')
            if not isinstance(entries, list) or len(entries) > 24:
                raise t.ActionError('each Macro list must be an array of at most 24 entries')
            clean[actor_key] = copy.deepcopy(entries)
        run.context['macros'] = clean
        return {'type': 'macros_configured', 'macros': copy.deepcopy(clean),
                'evidence': {'state_change': 'run-local Macro policy updated'}}
    if kind == 'salvage':
        item_id = action.get('item') or action.get('item_id')
        item = d['inventory'].get(item_id)
        if item is None:
            raise t.ActionError('unknown inventory item')
        value = max(1, int(item.get('value', 1)))
        del d['inventory'][item_id]
        d['components'] += 1
        return {'type': 'salvaged', 'item_id': item_id, 'currency': value,
                'components_after': d['components'],
                'evidence': {'inventory_removed': True, 'currency_before': d['currency']}}
    if kind in {'trade', 'trade_item'}:
        item_id = action.get('item') or action.get('item_id')
        item = d['inventory'].get(item_id)
        if item is None:
            raise t.ActionError('unknown inventory item')
        value = max(1, int(item.get('value', 1)))
        del d['inventory'][item_id]
        d['currency'] += value
        return {'type': 'trade_completed', 'item_id': item_id, 'currency': value,
                'currency_after': d['currency']}
    if kind in {'acquire_weapon', 'acquire_armor'}:
        name = str(action.get('name') or ('weapon' if kind == 'acquire_weapon' else 'armor')).strip()
        item = add_item(run, 'permanent_gear')
        item.update({'name': name, 'gear_type': 'weapon' if kind == 'acquire_weapon' else 'armor',
                     'slot': 'hand' if kind == 'acquire_weapon' else 'armor',
                     'base_damage': int(action.get('base_damage', 1)),
                     'base_ac': int(action.get('base_ac', 10))})
        d['inventory'][item['id']] = item
        d['permanent_gear'][item['id']] = copy.deepcopy(item)
        return {'type': 'gear_acquired', 'item': copy.deepcopy(item)}
    if kind in {'imprint_rune', 'rune_imprint'}:
        item_id = action.get('item') or action.get('item_id')
        item = d['inventory'].get(item_id)
        if item is None or item.get('kind') != 'imprint':
            raise t.ActionError('rune imprint requires an Imprint item')
        if not item.get('identified'):
            raise t.ActionError('identify the Rune before imprinting it')
        actor = str(action.get('actor', 'p0'))
        slot = str(action.get('slot') or item.get('slot') or 'ring')
        d['imprints'].setdefault(actor, {})[slot] = item_id
        return {'type': 'rune_imprinted', 'actor': actor, 'slot': slot, 'item': _public_item(item)}
    raise t.ActionError(f'unsupported system hook: {kind}')


def evaluate_conducts(run):
    d=state(run); events=d.get('events', [])
    spawned={key for key,row in d.get('rooms', {}).items() if isinstance(row, dict)}
    rested=any(event.get('method') == 'long_rest' or event.get('type') == 'night_patrol' for event in events if isinstance(event, dict))
    identified=any(event.get('type') == 'rune_identified' for event in events if isinstance(event, dict))
    machine_spawned=any(key.startswith('2:') and row.get('kind') == 'combat' for key,row in d.get('rooms', {}).items())
    machine_clean=machine_spawned and not any(
        event.get('type') == 'conflict' and event.get('evidence', {}).get('room_kind') == 'combat'
        for event in events if isinstance(event, dict))
    return [
        {'id':'clean-machine-works','status':'achieved' if machine_clean else 'failed' if machine_spawned else 'never_spawned',
         'description':'Clear the Machine Works without killing a Cleaner.'},
        {'id':'never-rest','status':'failed' if rested else 'achieved' if d.get('status') in {'cleared','escaped','ejected','defeated'} else 'live',
         'description':'Clear a run without resting.'},
        {'id':'rune-blind','status':'failed' if identified else 'achieved' if d.get('status') in {'cleared','escaped','ejected','defeated'} else 'live',
         'description':'Clear a run without identifying a Rune.'},
    ]


def upgrade_item(run, item_id, actor_key='p0'):
    """Spend run-local Gems on a deterministic 1..5 item track."""
    d=state(run);item=d['inventory'].get(item_id)
    if item is None: raise t.ActionError('unknown item instance')
    if not item.get('upgradeable'): raise t.ActionError('item is not upgradeable')
    cap=int(d.get('meta_modifier_cap',d['config'].get('modifier_cap',5)))
    if item['level']>=min(5,cap): raise t.ActionError('item is fully upgraded')
    cost=item['level']
    if d['components']<cost: raise t.ActionError('insufficient Gems')
    before=copy.deepcopy(item)
    d['components']-=cost
    item['level']+=1
    if item['level']==2:
        for modifier in item['modifiers']:
            if isinstance(modifier.get('value'), (int, float)):
                modifier['value']+=1
    elif item['level']==3:
        for modifier in item['modifiers']:
            if isinstance(modifier.get('value'), (int, float)):
                modifier['value']+=2
    elif item['level']==4:
        item['suffix']={'name':'Reliquary Temper','effect':'healing_bonus','value':1}
        item['modifiers'].append({'effect':'healing_bonus','value':1,'source':'Reliquary Temper'})
    elif item['level']==5:
        item['percentage_bonus']=10
    if item_id in d.get('permanent_gear',{}):
        d['permanent_gear'][item_id]=copy.deepcopy(item)
    return {'type':'upgrade','item':copy.deepcopy(item),'actor':actor_key,
            'evidence':{'actor':actor_key,'item':item_id,'item_kind':item['kind'],
                        'level_before':before['level'],'level_after':item['level'],
                        'gems_spent':cost,'gold_after':d['currency'],'gems_after':d['components'],
                        'modifier_before':before.get('modifiers',[]),
                        'modifier_after':copy.deepcopy(item.get('modifiers',[])),
                        'suffix':copy.deepcopy(item.get('suffix')),
                        'percentage_bonus':item.get('percentage_bonus',0)}}


def _compact_items(items):
    return [{'id':item.get('id'),'name':item.get('name'),'kind':item.get('kind'),
             'temporary':bool(item.get('temporary',True))} for item in items.values()]


def _room_order(floor, number):
    return int(floor) * 1000 + int(number)


def _checkpoint_snapshot(run, checkpoint_id):
    d=state(run)
    room_id=f"{d['floor']}:{d['room']}"
    known_rooms={key:copy.deepcopy(value) for key,value in d.get('rooms',{}).items()
                 if ':' in key and _room_order(*key.split(':',1)) <= _room_order(d['floor'],d['room'])}
    return {
        'schema':'hollow-star-checkpoint-1','checkpoint_id':checkpoint_id,
        'floor':d['floor'],'room':d['room'],'room_id':room_id,
        'party':copy.deepcopy(run.party),'opposition':copy.deepcopy(run.opposition),
        'round_number':run.round_number,'rng_seed':run.rng.seed,
        'rng_calls':run.rng.calls,'rng_state':run.rng.getstate(),
        'room_discoveries':[{"room_id":key,'perceived_facts':copy.deepcopy(value.get('perceived_facts',[])),
                             'resolved':bool(value.get('resolved',False)),
                             'reward_claimed':bool(value.get('reward_claimed',False))}
                            for key,value in sorted(known_rooms.items())],
        'rooms':known_rooms,'discoveries':copy.deepcopy(d['discoveries']),
        'resources':[copy.deepcopy(actor.resources) for actor in run.party],
        'inventory':copy.deepcopy(d['inventory']),'imprints':copy.deepcopy(d['imprints']),
        'permanent_gear':copy.deepcopy(d['permanent_gear']),
        'attunement':copy.deepcopy(d.get('attunement',{})),
         'rooms_cleared':d['rooms_cleared'],'next_item':d['next_item'],
         'greed':d.get('greed', 0.0),'attrition':d.get('attrition', 0.0),
        'events':copy.deepcopy(d.get('events',[])),
        'commentary':copy.deepcopy(d.get('commentary',{})),
        'content_state':copy.deepcopy(run.context.get('content_state',{})),
        'final_floor':d.get('final_floor'),'currency':d['currency'],'components':d['components'],'rank_xp':d['rank_xp'],
        'hsr_rank':d['hsr_rank'],'meta_currency':d['meta_currency'],'alert':d['alert'],
        'event_receipts':copy.deepcopy(d.get('receipts',[])),
        'temporary_rewards':copy.deepcopy({key:value for key,value in d['inventory'].items()
                                           if value.get('temporary',True)}),
    }


def _checkpoint_summary(snapshot):
    if not snapshot:
        return None
    return {'checkpoint_id':snapshot['checkpoint_id'],'room_id':snapshot['room_id'],
            'floor':snapshot['floor'],'room':snapshot['room'],
            'discoveries':len(snapshot.get('discoveries',[])),
            'banked_items':[item['id'] for item in _compact_items(snapshot.get('inventory',{}))],
            'rng_calls':snapshot['rng_calls']}


def bank_checkpoint(run):
    d=state(run);row=room(run)
    if d['status']!='active': raise t.ActionError('cannot bank a completed run')
    if 'combat' in run.context and not run.context['combat']['complete']:
        raise t.ActionError('checkpoint banking requires a safe pause; combat is active')
    if not row.get('checkpoint') or not row.get('safe_room') or not row.get('resolved'):
        raise t.ActionError('checkpoint banking requires an explicit authored checkpoint or resolved safe room')
    checkpoint_id=f"checkpoint:{d['floor']}:{d['room']}:{len(d['checkpoint'].get('history',[]))+1}"
    snapshot=_checkpoint_snapshot(run,checkpoint_id)
    d['checkpoint']['banked']=snapshot
    d['checkpoint']['current']=snapshot
    d['checkpoint']['history'].append(_checkpoint_summary(snapshot))
    return {'type':'checkpoint_banked','checkpoint':_checkpoint_summary(snapshot),
            'banked':{'party':len(snapshot['party']),'room_discoveries':len(snapshot['room_discoveries']),
                      'inventory':len(snapshot['inventory']),'event_receipts':len(snapshot['event_receipts']),
                      'rng_calls':snapshot['rng_calls']},
            'evidence':{'authored_checkpoint':True,'safe_room':True,
                        'atomic_persistence':'RunService commits this candidate with atomic save'}}


def resume_checkpoint(run):
    """Reconnect an in-progress run to its last banked safe point.

    Checkpoints exist for active-run pause, reconnect, and safe banking only.
    A run that has already reached a public terminal outcome (`completed` or
    `dead`) is closed for good: this never rewinds a death or undoes a
    completion. Retrying after either outcome is an account-level action that
    creates a new run, not a resume of this one.
    """
    d=state(run);snapshot=d.get('checkpoint',{}).get('banked')
    if not snapshot:
        raise t.ActionError('no banked checkpoint is available')
    if d['status']!='active':
        raise t.ActionError(
            'this run has reached a terminal outcome and cannot be resumed; '
            'checkpoints do not rewind a completed or dead run -- start a new run instead'
        )
    run.party=copy.deepcopy(snapshot['party'])
    run.opposition=copy.deepcopy(snapshot.get('opposition',[]))
    run.round_number=snapshot['round_number']
    run.rng.setstate(snapshot['rng_state']);run.rng.calls=snapshot['rng_calls']
    d['status']='active';d['floor']=snapshot['floor'];d['room']=snapshot['room']
    d['rooms']=copy.deepcopy(snapshot['rooms']);d['discoveries']=copy.deepcopy(snapshot['discoveries'])
    d['inventory']=copy.deepcopy(snapshot['inventory']);d['imprints']=copy.deepcopy(snapshot['imprints'])
    d['permanent_gear']=copy.deepcopy(snapshot['permanent_gear'])
    if 'attunement' in snapshot:
        # Items decanted after the bank come back to inventory, so their
        # attunements must roll back with them.
        d['attunement']=copy.deepcopy(snapshot['attunement'])
    d['rooms_cleared']=snapshot.get('rooms_cleared',d['rooms_cleared'])
    d['next_item']=snapshot.get('next_item',d['next_item'])
    d['events']=copy.deepcopy(snapshot.get('events',d.get('events',[])))
    d['commentary']=copy.deepcopy(snapshot.get('commentary',d.get('commentary',{})))
    if snapshot.get('final_floor') is None:
        d.pop('final_floor',None)
    else:
        d['final_floor']=snapshot['final_floor']
    run.context['content_state']=copy.deepcopy(snapshot.get('content_state',run.context.get('content_state',{})))
    for key in ('currency','components','rank_xp','hsr_rank','meta_currency','alert'):
        d[key]=snapshot[key]
    d['greed']=snapshot.get('greed', d.get('greed', 0.0)); d['attrition']=snapshot.get('attrition', d.get('attrition', 0.0))
    # status was already 'active' on entry (checked above), so terminal_receipt
    # was already None; nothing terminal is ever un-set by this resume.
    d['run_capsule']['resumed_from_checkpoint']=snapshot['checkpoint_id']
    run.context.pop('combat',None)
    return {'type':'checkpoint_resumed','checkpoint':_checkpoint_summary(snapshot),
            'evidence':{'state_restored':['party','rng_namespace','room_discoveries','resources',
                                          'inventory','imprints','event_receipts'],
                        'unbanked_rewards_discarded':True}}


def _apply_authored_hook(run,row,event,action):
    if not isinstance(event,dict) or action.get('type') not in {'inspect_object','search_object','open_object'}:
        return event
    object_id=event.get('object_id') or (event.get('object') or {}).get('object_id')
    if not object_id:
        return event
    d=state(run)
    matches=[]
    for hook in row.get('authored_hooks',[]):
        if hook.get('object_id') != object_id or hook.get('trigger') != 'inspect' or hook.get('id') in row.get('fired_hooks',[]):
            continue
        row.setdefault('fired_hooks',[]).append(hook['id'])
        matches.append(hook)
    if matches:
        texts=[]; rewards=[]
        for hook in matches:
            if hook.get('text'):
                texts.append(hook['text'])
            consequence_reward=hook.get('reward')
            if isinstance(consequence_reward,dict):
                rewards.append(consequence_reward)
        consequence={'text':' '.join(texts),'source':copy.deepcopy(row.get('content_source')),
                     'hooks':[hook['id'] for hook in matches]}
        for reward in rewards:
            kind=reward.get('kind')
            if kind=='component':
                d['components']+=1
                consequence.setdefault('temporary_rewards',[]).append({'kind':'component','name':reward.get('name','component')})
            elif kind in {'imprint','potion','permanent_gear'}:
                item=add_item(run,kind,identified=False)
                if reward.get('name'):
                    item_id=item['id'];d['inventory'][item_id]['name']=reward['name'];
                    if item_id in d.get('permanent_gear',{}):d['permanent_gear'][item_id]['name']=reward['name']
                    item=copy.deepcopy(d['inventory'][item_id])
                consequence.setdefault('temporary_rewards',[]).append(item)
            else:
                consequence.setdefault('reward_deferred',[]).append(f"unknown authored reward kind: {kind}")
        if len(consequence.get('temporary_rewards',[]))==1:
            consequence['temporary_reward']=consequence['temporary_rewards'][0]
        event['consequence']=consequence
        event.setdefault('evidence',{})['authored_hooks']=[hook['id'] for hook in matches]
        return event
    return event


#: The engine has exactly two public terminal outcomes. Every internal status
#: this dungeon has ever produced -- cleared, escaped, defeated, ejected --
#: resolves to one of these two. `completion_kind` on the terminal receipt
#: keeps the former, more specific reason; `outcome` is what every other
#: system (progression, replay, the statistics page) is allowed to branch on.
#: Forced ejection counts as death: an authored extraction route is the only
#: non-victory way to leave with a `completed` outcome.
TERMINAL_OUTCOMES = {'cleared': 'completed', 'escaped': 'completed',
                     'defeated': 'dead', 'ejected': 'dead'}


def end(run,status):
    d=state(run);d['status']=status
    outcome=TERMINAL_OUTCOMES.get(status)
    if outcome is None:
        raise t.ActionError(f"unknown terminal status {status!r}; expected one of {sorted(TERMINAL_OUTCOMES)}")
    final_floor=d.get('final_floor','not-reached' if d['floor']<5 else 'boss_victory_only')
    completion_kind=('actual_final_floor_complete' if final_floor=='actual_final_floor_complete'
                     else 'boss_victory_only' if final_floor == 'boss_victory_only'
                     else 'unmeasured' if final_floor=='unmeasured'
                     else 'escaped' if final_floor=='escaped' else status)
    tracking.ensure(d)['completion_kind'] = completion_kind
    current_inventory=copy.deepcopy(d.get('inventory',{}))
    current_temporary={key:value for key,value in current_inventory.items() if value.get('temporary',True)}
    banked=d.get('checkpoint',{}).get('banked') or {}
    banked_inventory=copy.deepcopy(banked.get('inventory',{}))
    if status=='cleared':
        retained_temporary=current_temporary
    else:
        retained_temporary={key:value for key,value in banked_inventory.items() if value.get('temporary',True)}
    lost_unbanked={key:value for key,value in current_temporary.items() if key not in retained_temporary}
    retained_items={**copy.deepcopy(d.get('permanent_gear',{})),**copy.deepcopy(retained_temporary)}
    tracking.finish(d, status)
    if status != 'cleared':
        tracking.gold(d, d.get('currency', 0), kind='lost')
    else:
        tracking.gold(d, d.get('currency', 0), kind='retained')
    receipt_tracking = {
        key: value for key, value in d.get('tracking', {}).items()
        if key not in {'started_at', 'last_active_at', 'ended_at', 'active_seconds_remainder'}
    }
    terminal_receipt={'schema':'hollow-star-terminal-receipt-1','status':status,
                      'outcome':outcome,'completion_kind':completion_kind,
                      'floor':d['floor'],'room':d['room'],
                      'rooms_cleared':d['rooms_cleared'],'checkpoint_id':banked.get('checkpoint_id'),
                      'retained':{'items':_compact_items(retained_items),'currency':d['currency'],
                                  'gold':d['currency'],'components':d['components'],'gems':d['components'],
                                  'discoveries':list(d['discoveries']),
                                  'meta_currency':d['meta_currency'],'platinum':d['meta_currency']},
                       'lost_unbanked_items':_compact_items(lost_unbanked),
                       'conducts':evaluate_conducts(run),
                      'known_room_ids':sorted(d.get('rooms',{})),
                      'tracking':receipt_tracking,
                      'future_rooms_exposed':False}
    d['terminal_receipt']=terminal_receipt
    d['run_capsule']['terminal']=copy.deepcopy(terminal_receipt)
    d.setdefault('events',[]).append({'type':'run_ended','status':status,
                                      'floor':d['floor'],'room':d['room'],
                                      'rooms_cleared':d['rooms_cleared'],
                                      'completion_kind':completion_kind})
    clock.emit(d, 'run_end', room=f"{d['floor']}:{d['room']}",
               phase='terminal', payload={'status': status, 'outcome': outcome,
                                          'meta_currency': d['meta_currency']})
    carry_out=copy.deepcopy(list(d.get('permanent_gear',{}).values()))
    d['inventory'].clear();d['imprints'].clear()
    return {'type':'ended','status':status,'outcome':outcome,'completion_kind':completion_kind,'carry_out':carry_out,'rooms_cleared':d['rooms_cleared'],
        'meta_currency':d['meta_currency'],'platinum':d['meta_currency'],'final_floor':final_floor,
            'terminal_receipt':copy.deepcopy(terminal_receipt),
            'retained':copy.deepcopy(terminal_receipt['retained']),
            'lost_unbanked_items':copy.deepcopy(terminal_receipt['lost_unbanked_items']),
            'reentry':'create a new run; old transcript remains inspectable',
            'evidence':{'terminal_status':status,'rooms_cleared':d['rooms_cleared'],
                        'permanent_gear_carried':[item['id'] for item in carry_out],
                        'terminal_record':'compact useful outcomes only; full capsule remains temporary'}}


def escape(run, route):
    d=state(run);row=room(run)
    if d['floor'] != 5 or route not in row.get('escape_routes',[]):
        raise t.ActionError('escape route is not available in this room')
    d['final_floor']='escaped'
    event=end(run,'escaped')
    event['escape_route']=route
    event['escape_routes']=list(row['escape_routes'])
    event['rivals_preserved']=bool(run.opposition)
    event['cocoon_state']=copy.deepcopy(row.get('cocoon'))
    return event


def reset(run):
    """Start a fresh DESIGN run in-place, retaining an explicit reset receipt."""
    d=state(run)
    if d['status']=='active': raise t.ActionError('reset requires an ended run')
    previous={'status':d['status'],'floor':d['floor'],'room':d['room'],
              'rooms_cleared':d['rooms_cleared'],
              'events':copy.deepcopy(d.get('events',[])),
              'terminal_receipt':copy.deepcopy(d.get('terminal_receipt'))}
    permanent=copy.deepcopy(d.get('permanent_gear',{}))
    run.context.setdefault('dungeon_history',[]).append(previous)
    history=run.context.setdefault('reset_history',[])
    history.append(previous)
    run.party=copy.deepcopy(d['baseline_party'])
    run.opposition=[]
    run.context.pop('combat',None)
    run.context.pop('dungeon',None)
    result=start(run)
    new_d=state(run)
    new_d['permanent_gear']=permanent
    new_d['inventory'].update(copy.deepcopy(permanent))
    result['reset']={'previous':previous,'reset_count':len(history),
                     'permanent_gear_carried':list(permanent),
                     'state_change':'new dungeon started; prior run summary and permanent gear retained'}
    return result


def cocoon(run,row):
    """Apply the authoritative final-floor cocoon clock."""
    clock = row['cocoon']['rounds']
    row['cocoon']['emerges_at_round'] = clock
    if not row['cocoon'].get('opened') and run.round_number >= clock:
        from hollowstar.monsters import spawn_tarrasque
        row['cocoon']['opened'] = True
        event = spawn_tarrasque(run)
        # It rises for several rounds (untouchable by its own turn, but hittable),
        # then launches and attacks everything alive: party and rivals alike.
        rise = int(state(run)['config'].get('tarrasque_rise_rounds', 5))
        delay = int(state(run)['config'].get('tarrasque_launch_delay', 2))
        beast_rules = t.rules(run, event['actor'])
        beast_rules['rising_until'] = run.round_number + rise
        beast_rules['launches_at'] = run.round_number + rise + delay
        beast_rules['feral'] = True
        row['cocoon'].update({'rising_until': beast_rules['rising_until'], 'launches_at': beast_rules['launches_at']})
        event.update({'type': 'cocoon_opened', 'emerges_at_round': clock,
                      'rising_until': beast_rules['rising_until'], 'launches_at': beast_rules['launches_at'],
                      'tell': 'The Tarrasque drags itself out of the cocoon. It is not ready yet.',
                      'rules_version': 'regular 2014 Tarrasque',
                      'certification': 'Step 6 final-floor fixture'})
        return event
    if not row['cocoon'].get('cracked') and run.round_number >= max(1, clock - 2):
        row['cocoon']['cracked'] = True
        return {'type': 'cocoon_cracked', 'round': run.round_number,
                'emerges_at_round': clock,
                'tell': 'The egg cracks and crumbles like glass.'}
    return {'type': 'cocoon_waiting', 'round': run.round_number,
            'emerges_at_round': clock}


def _complete_combat_action(run,row,result):
    completion=record_final_floor_completion(run)
    if completion and isinstance(result,dict):
        result['final_floor_completion']=completion
    if run.context['combat']['complete']:
        if any(a.alive for a in run.party): result={'combat':result,'reward':award(run,'combat')}
        else: result={'combat':result,'ending':end(run,'defeated')}
    if row.get('cocoon') and not row['cocoon']['opened'] and run.round_number >= max(1, row['cocoon']['rounds']-2):
        result={'combat':result,'crisis':cocoon(run,row)}
    return result


def _settle_turn_zero(run,row,result):
    """A Turn 0 cascade can end an encounter before initiative is rolled.

    tactical.begin marks such a combat complete; route it through the same
    reward/defeat boundary an ordinary final blow uses.
    """
    combat_state=run.context.get('combat') or {}
    if combat_state.get('complete'):
        settled=_complete_combat_action(run,row,result)
        if isinstance(settled,dict):
            settled['turn_zero_resolution']=True
        return settled
    return result


def _complete_arcade_action(run, row, result):
    """Close an arcade gate through the ordinary room reward boundary."""
    if not isinstance(result, dict) or not result.get('complete'):
        return result
    from hollowstar import arcade
    result = copy.deepcopy(result)
    result.setdefault('arcade_view', arcade.view(run))
    run.context['combat']['complete'] = True
    if any(actor.alive for actor in run.party):
        reward = award(run, 'arcade')
        run.context.pop('arcade', None)
        return {'arcade': result, 'reward': reward}
    run.context.pop('arcade', None)
    return {'arcade': result, 'ending': end(run, 'defeated')}


def recover_previous_room(run):
    """Return to the last visited room without rolling back consequences."""
    d=state(run)
    combat_state=run.context.get('combat')
    if combat_state and not combat_state.get('complete'):
        raise t.ActionError('previous-room recovery is unavailable during active combat')
    history=d.get('navigation_history',[])
    if not history:
        raise t.ActionError('no previous room is available for recovery')
    target=history.pop()
    if not isinstance(target,dict) or not isinstance(target.get('floor'),int) or not isinstance(target.get('room'),int):
        raise t.ActionError('previous-room recovery history is invalid')
    room_id=f"{target['floor']}:{target['room']}"
    row=d.get('rooms',{}).get(room_id)
    if not isinstance(row,dict):
        raise t.ActionError('previous room state is unavailable for recovery')
    from_room=f"{d['floor']}:{d['room']}"
    d['floor'],d['room']=target['floor'],target['room']
    receipt={'type':'previous_room_recovered','from_room':from_room,'to_room':room_id,
             'state_preserved':True,'reason':'player_requested_recovery'}
    d.setdefault('receipts',[]).append(copy.deepcopy(receipt))
    return {'type':'previous_room_recovered','room':public_room(row),'receipt':receipt,
            'evidence':{'room_transition':True,'state_preserved':True,'from_room':from_room,'to_room':room_id}}


def act(run,action):
    d=state(run);row=room(run)
    kind=action.get('type')
    if kind in {'npc_list','list_npcs','conversation','talk','speak',
                'prepare_idle','idle_prepare','auto_battle','idle_battle',
                'battle_prepare','salvage','trade','trade_item',
                'acquire_weapon','acquire_armor','imprint_rune','rune_imprint',
                'reforge_affix','affix_reforge',
                # _open_system_hook has always implemented these, but act()
                # never routed them there, so configure_macros failed with
                # "unsupported dungeon action" from every client.
                'configure_macros','set_macros','macros'}:
        if kind in {'reforge_affix','affix_reforge'}:
            result=reforge_affix(run, action.get('item') or action.get('item_id'), action.get('affix'), action.get('actor','p0'))
            d['events'].append(copy.deepcopy(result)); return result
        result = _open_system_hook(run, action)
        d['events'].append(copy.deepcopy(result))
        return result
    if isinstance(kind, str) and kind.startswith('expedition_'):
        from hollowstar import expedition
        if d['status'] != 'active' and kind != 'expedition_view':
            raise t.ActionError('run has ended')
        result = expedition.act(run, action)
        d['events'].append(copy.deepcopy({k: v for k, v in result.items() if k != 'expedition'}))
        return result
    if kind in {'decant', 'devour', 'disenchant', 'release_attunement', 'grant_legendary'}:
        from hollowstar import attunement
        if d['status'] != 'active':
            raise t.ActionError('run has ended')
        if kind == 'release_attunement':
            result = attunement.release(run, action.get('actor', 'p0'), action.get('lane'), action.get('name'))
        elif kind == 'grant_legendary':
            # A design/simulation seam until a drop table rolls legendaries.
            if run.context.get('host_mode') not in {None, 'DESIGN', 'SANDBOX'}:
                raise t.ActionError('granting a legendary is a DESIGN or Simulation Mode tool')
            item = attunement.grant_legendary(run, action.get('legendary') or action.get('legendary_id'))
            result = {'type': 'legendary_granted', 'item': _public_item(item),
                      'evidence': {'source': 'design grant', 'state_change': 'legendary added to inventory'}}
        else:
            result = attunement.decant(run, action.get('item') or action.get('item_id'),
                                       action.get('actor', 'p0'), action.get('replace'))
        d['events'].append(copy.deepcopy(result))
        return result
    if kind in {'arcade_tick', 'arcade_toggle_flight', 'arcade_set_movement_mode', 'fly', 'land'}:
        if d['status'] != 'active':
            raise t.ActionError('run has ended')
        if not isinstance(run.context.get('combat'), dict) or run.context['combat'].get('complete'):
            raise t.ActionError('no active arcade combat')
        if not isinstance(run.context.get('arcade'), dict):
            raise t.ActionError('current room is not an arcade encounter')
        from hollowstar import arcade
        if kind == 'arcade_tick':
            result = arcade.tick(run, action.get('inputs', []))
            return _complete_arcade_action(run, row, result)
        if kind in {'arcade_toggle_flight', 'fly', 'land'}:
            on = action.get('on') if kind == 'arcade_toggle_flight' else kind == 'fly'
            return arcade.toggle_flight(run, action.get('actor', 'p0'), on)
        return arcade.set_movement_mode(
            run, action.get('actor', 'p0'), action.get('mode', action.get('movement_mode')))
    product={'gem':'component','gems':'component'}.get(action.get('product'),action.get('product')) if kind == 'buy' else None
    lodging_purchase = kind == 'buy' and product == 'room'
    pressure_kind = 'rest' if lodging_purchase else kind
    pressure_receipt = _pressure(run, pressure_kind, noise=2 if kind in {'fight','attack','cast','open_object'} else 0,
                                 rest=pressure_kind == 'rest')
    if kind=='reset': return reset(run)
    if kind in {'resume_checkpoint','resume-checkpoint'}: return resume_checkpoint(run)
    if d['status']!='active': raise t.ActionError('run has ended')
    if kind == 'inspect':
        return {'type': 'inspection',
                'pressure': pressure_receipt,
                'note': 'inspection returns public readout only; unopened rooms and hidden rules remain concealed',
                'evidence': {'read_only': True, 'state_embedded': False}}
    if kind in {'test_perception','test-perception'}:
        return test_perception(run,action)
    if kind in {'reveal_room_record','reveal-room-record'}:
        return reveal_room_record(run)
    if kind in {'observe_room','inspect_room','inspect_object','search_object','open_object','light_source','enter_subroom'}:
        from hollowstar import room_state
        if kind in {'observe_room','inspect_room'}:
            row['prose_revealed']=True
        result=room_state.interact(run, row, action)
        return _apply_authored_hook(run,row,result,action)
    if kind=='enter': return enter(run)
    if kind=='exit':
        if not row['resolved']: raise t.ActionError('resolve this room before exiting')
        from_room=f"{d['floor']}:{d['room']}"
        d.setdefault('navigation_history',[]).append({'floor':d['floor'],'room':d['room']})
        result=enter(run)
        return {'type':'exited','from_room':from_room,'next':result,
                'evidence':{'room_transition':True,'from_room':from_room,
                            'to_room':f"{d['floor']}:{d['room']}"}}
    if kind in {'recover_previous_room','recover-previous-room'}: return recover_previous_room(run)
    if kind in {'leave','retreat'}: return end(run,'ejected')
    if kind=='escape': return escape(run,action.get('route'))
    if kind=='check_in':
        if 'combat' in run.context and not run.context['combat']['complete']: raise t.ActionError('check-ins require a safe pause')
        return {'type':'check_in','channel':'available','reports':list(d['discoveries']),'divine_dialogue':None}
    if kind in {'checkpoint','bank_checkpoint','bank-checkpoint'}:
        return bank_checkpoint(run)
    if kind in {'content','use_content','use-content'}:
        from hollowstar.content_registry import dispatch
        result=dispatch(run,action)
        if 'combat' in run.context and not run.context['combat']['complete']:
            return _complete_combat_action(run,row,result)
        return result
    if 'combat' in run.context and not run.context['combat']['complete'] and kind not in {'equip', 'consume', 'identify', 'combine', 'decant', 'craft', 'upgrade', 'configure_macros'}:
        if kind in {'investigate','negotiate','avoid'}:
            key=action.get('actor',t.current(run));a=t.actor(run,key)
            if key!=t.current(run): raise t.ActionError('not this actor turn')
            if kind == 'negotiate' and action.get('target'):
                requested=str(action['target']).lower().replace('_',' ').removeprefix('the ')
                resident=str(row.get('resident','')).lower().replace('_',' ').removeprefix('the ')
                if requested != resident: raise t.ActionError('negotiation target is not the visible room resident')
            t.use(run,key,'action')
            if kind=='investigate':
                perception=test_perception(run,{'type':'test_perception','actor':key,'_action_spent':True})
                check=perception['check']
                evidence={'actor':a.name,'skill':'Perception','bonus':perception['evidence']['bonus'],
                          'dc':perception['evidence']['dc'],'action_spent':'action',
                          'perception':perception}
            else:
                skill={'negotiate':'Persuasion','avoid':'Stealth'}[kind]
                ancestry=ancestry_hook(run,key,kind,row); origin=origin_hook(run,key,kind,row)
                if ancestry: skill=ancestry['skill']
                hooks=[hook for hook in (ancestry,origin) if hook]
                from hollowstar.affix_runtime import skill_bonus
                bonus=a.skill_bonuses.get(skill,a.skill_bonuses.get(skill.lower(),0)) + skill_bonus(run,key,skill) + sum(hook['bonus'] for hook in hooks); dc=12+d['floor']
                check=t.roll_check(run,bonus,dc)
                evidence={'actor':a.name,'skill':skill,'bonus':bonus,'dc':dc,'action_spent':'action'}
                if ancestry: evidence['ancestry_hook']=ancestry
                if origin: evidence['origin_hook']=origin
                if kind == 'negotiate': evidence['counterparty']=row.get('resident')
            if check['success'] and kind!='investigate':
                run.context['combat']['complete']=True
                evidence['state_change']='room resolved'
                return resolved_check_event(kind,check,evidence,award(run,kind))
            if kind=='investigate' and check['success']:
                for k in t.actors(run):
                    if k.startswith('e'):t.rules(run,k)['resistances']=[]
            evidence['discovery_revealed']=False
            return {'type':kind,'check':check,'evidence':evidence,
                    'perception':perception if kind=='investigate' else None}
        result = _complete_combat_action(run,row,t.apply(run,action))
        if isinstance(result, dict): result.setdefault('pressure', pressure_receipt)
        return result
    if kind in {'investigate','negotiate','avoid','disarm'}:
        if row['resolved']:raise t.ActionError('room already resolved')
        if kind in row['attempts']:raise t.ActionError('this approach was already attempted; choose another')
        if kind == 'negotiate' and action.get('target'):
            requested=str(action['target']).lower().replace('_',' ').removeprefix('the ')
            resident=str(row.get('resident','')).lower().replace('_',' ').removeprefix('the ')
            if requested != resident: raise t.ActionError('negotiation target is not the visible room resident')
        key=action.get('actor','p0');a=run.party[int(key[1:])] if isinstance(key,str) and key.startswith('p') and key[1:].isdigit() and int(key[1:])<len(run.party) else None
        if a is None or not a.alive:raise t.ActionError('invalid party actor')
        row['attempts'].append(kind)
        skill={'investigate':'Investigation','negotiate':'Persuasion','avoid':'Stealth','disarm':'Athletics'}[kind]
        ancestry=ancestry_hook(run,key,kind,row); origin=origin_hook(run,key,kind,row)
        if ancestry: skill=ancestry['skill']
        hooks=[hook for hook in (ancestry,origin) if hook]
        from hollowstar.affix_runtime import skill_bonus
        bonus=a.skill_bonuses.get(skill,a.skill_bonuses.get(skill.lower(),0)) + skill_bonus(run,key,skill) + sum(hook['bonus'] for hook in hooks); dc=10+d['floor']
        check=t.roll_check(run,bonus,dc)
        evidence={'actor':a.name,'skill':skill,'bonus':bonus,'dc':dc}
        if ancestry: evidence['ancestry_hook']=ancestry
        if origin: evidence['origin_hook']=origin
        if kind == 'negotiate': evidence['counterparty']=row.get('resident')
        if kind=='investigate':
            discover(run,row)
        if check['success']:
            evidence['state_change']='room resolved'
            return resolved_check_event(kind,check,evidence,award(run,kind))
        if kind=='avoid':
            combat(run);return _settle_turn_zero(run,row,{'type':'avoidance_failed','check':check,'evidence':evidence,'combat':t.view(run)})
        if row['kind']=='hazard':
            wayfinder=wayfinder_check(run,key,row)
            if wayfinder:
                evidence['wayfinder']=wayfinder
                if wayfinder['triggered']:
                    evidence['damage']=0
                    return {'type':'hazard_avoided_by_heirloom','check':check,'evidence':evidence,'damage':0,'rolls':[]}
            amount,rolls=t.dice(run,'2d6');a.adjust_hp(-amount)
            evidence['damage']=amount; return {'type':'hazard','check':check,'evidence':evidence,'damage':amount,'rolls':rolls}
        return {'type':kind,'check':check,'evidence':evidence,'tell':row['tells'][0]}
    if kind=='fight':
        if row['resolved']:raise t.ActionError('room already resolved')
        combat(run)
        state_view=t.view(run)
        return _settle_turn_zero(run,row,{'type':'conflict','combat':state_view,
                'evidence':{'room_kind':row['kind'],'room_title':row['title'],
                            'opposition':[a.name for a in run.opposition],
                            'initiative_order':list(state_view['order'])}})
    if kind=='rest':
        if row['kind']!='rest' or row['resolved']:raise t.ActionError('rest is unavailable')
        safe=action.get('safe',False)
        if type(safe)is not bool:raise t.ActionError('safe must be boolean')
        if d['floor']==1 and not safe:
            d['alert']+=1;row['night_patrol']=True;combat(run)
            return _settle_turn_zero(run,row,{'type':'night_patrol','tell':'The residents assemble while the party settles to sleep.',
                    'evidence':{'safe_rest':False,'alert_after':d['alert'],'combat_started':True}})
        if safe and not d['discoveries']:raise t.ActionError('investigate a safe route before claiming a safe rest')
        staff_recovery=[]
        for i,a in enumerate(run.party):
            staff_before=a.resources.get('staff_charges')
            a.hp=a.max_hp;a.statuses.clear()
            a.resources=copy.deepcopy(d['baseline_party'][i].resources)
            if staff_before is not None:
                _, rolls=t.dice(run,'4d6+2')
                a.resources['staff_charges']=min(50,staff_before+sum(rolls)+2)
                staff_recovery.append({'actor':f'p{i}','charges_before':staff_before,
                                       'rolls':rolls,'charges_after':a.resources['staff_charges']})
        result=award(run,'long_rest')
        result['evidence']={'safe_rest':safe,'party_restored':True,'alert_after':d['alert'],
                            'staff_recovery':staff_recovery}
        return result
    if kind=='buy':
        if product == 'room':
            if d['floor'] != 1 or row['kind'] != 'social' or row['resolved']:
                raise t.ActionError('lodging is unavailable in this room')
            if 'room' in row['purchases']:
                raise t.ActionError('a room has already been purchased here')
            cost=int(d['config'].get('shop',{}).get('room',10))
            if d['currency']<cost:raise t.ActionError('insufficient currency')
            before=d['currency'];d['currency']-=cost;tracking.gold(d, cost, kind='spent');row['purchases'].append('room')
            d['alert']+=1;row['night_patrol']=True;combat(run)
            return _settle_turn_zero(run,row,{'type':'night_patrol','tell':'The residents assemble while the party settles to sleep.',
                    'purchase':{'product':'room','cost':cost},'pressure':pressure_receipt,
                    'evidence':{'resident':row.get('resident'),'gold_before':before,
                                'gold_after':d['currency'],'rest_started':True,
                                'rest_completed':False,'party_restored':False,
                                'room_resolved':False,'reward_claimed':False,
                                'alert_after':d['alert'],'combat_started':True}})
        if row['kind']!='shop' or product not in row['stock']:raise t.ActionError('product unavailable')
        if row['purchases'].count(product)>=3:raise t.ActionError('stock exhausted')
        cost=row['stock'][product]
        if d['currency']<cost:raise t.ActionError('insufficient currency')
        d['currency']-=cost;tracking.gold(d, cost, kind='spent');row['purchases'].append(product)
        if product=='component':d['components']+=1;item=None
        else:item=add_item(run,product,identified=False)
        return {'type':'purchase','cost':cost,'item':item,
                'evidence':{'product':product,'currency_before':d['currency']+cost,
                            'gold_before':d['currency']+cost,'currency_after':d['currency'],
                            'gold_after':d['currency'],'stock_purchases':len(row['purchases'])}}
    if kind == 'identify':
        return identify_item(run, action.get('item'))
    if kind == 'combine':
        return combine_items(run, action.get('item'), action.get('other_item'), action.get('actor', 'p0'))
    if kind in {'equip','craft','upgrade','consume','unequip'}:
        key=action.get('actor','p0')
        if key not in {f'p{i}' for i in range(len(run.party))}:raise t.ActionError('invalid party actor')
        if kind == 'unequip':
            actor_idx = int(key[1:])
            target_actor = run.party[actor_idx]
            slot = action.get('slot')
            ident = action.get('item')
            removed = None
            for eq in list(target_actor.equipment):
                if (slot and eq.slot == slot) or (ident and (getattr(eq, 'name', '') == ident or getattr(eq, 'sprite_id', '') == ident)):
                    removed = eq
                    target_actor.equipment.remove(eq)
                    break
            if removed:
                derived_ac = target_actor.equipment_armor_class()
                if derived_ac is not None:
                    target_actor.armor_class = derived_ac
            return {'type':'unequip','slot':slot or getattr(removed, 'slot', None),'actor':key,
                    'evidence':{'actor':key,'unequipped':removed is not None}}
        ident=action.get('item');item=d['inventory'].get(ident)
        if item is None:raise t.ActionError('unknown item instance')
        if kind=='equip':
            if item['kind']=='potion':
                raise t.ActionError('potions cannot be equipped')
            if item['kind']=='imprint':
                if not item.get('identified', False):
                    raise t.ActionError('identify the Rune before equipping it')
                for slots in d['imprints'].values():
                    for slot in list(slots):
                        if slots[slot]==ident:del slots[slot]
                d['imprints'].setdefault(key,{})[item['slot']]=ident
            else:
                actor_idx = int(key[1:])
                target_actor = run.party[actor_idx]
                target_slot = item.get('slot') or ('hand' if item.get('gear_type') == 'weapon' or item.get('kind') in {'weapon', 'permanent_gear'} else 'armor' if item.get('gear_type') == 'armor' else 'hand')
                target_actor.equipment = [eq for eq in target_actor.equipment if eq.slot != target_slot]
                new_item = Item(
                    name=item.get('name', 'Equipment'),
                    slot=target_slot,
                    sprite_id=str(item.get('sprite_id', '')),
                    base_damage=int(item.get('base_damage', 0)),
                    attack_bonus=int(item.get('attack_bonus', 0)),
                    damage_dice=str(item.get('damage_dice', '')),
                    damage_modifier=int(item.get('damage_modifier', 0)),
                    reach=int(item.get('reach', 5)),
                    range_normal=int(item.get('range_normal', 5)),
                    range_long=int(item.get('range_long', 5)),
                    critical_dice=str(item.get('critical_dice', '')),
                    base_ac=int(item.get('base_ac', 0)),
                    dex_cap=int(item['dex_cap']) if item.get('dex_cap') is not None else None,
                    ac_bonus=int(item.get('ac_bonus', 0)),
                    shield_bonus=int(item.get('shield_bonus', 0)),
                    attack_ability=str(item.get('attack_ability', '')),
                    silhouette=str(item.get('silhouette', '')),
                    material=str(item.get('material', '')),
                    item_type=str(item.get('item_type', '')),
                    handedness=str(item.get('handedness', '')),
                    coverage=str(item.get('coverage', '')),
                    animation_profile=str(item.get('animation_profile', '')),
                    flavor=str(item.get('flavor', '')),
                    density=float(item.get('density', 1.0)),
                    weight=float(item.get('weight', 1.0)),
                )
                target_actor.equipment.append(new_item)
                derived_ac = target_actor.equipment_armor_class()
                if derived_ac is not None:
                    target_actor.armor_class = derived_ac
                elif target_slot == 'armor' and new_item.base_ac > 0:
                    target_actor.armor_class = new_item.base_ac

                if isinstance(run.context.get('combat'), dict):
                    rules_dict = run.context['combat'].get('rules', {})
                    if key in rules_dict:
                        if derived_ac is not None:
                            rules_dict[key]['base_ac'] = derived_ac
                        elif target_slot == 'armor' and new_item.base_ac > 0:
                            rules_dict[key]['base_ac'] = new_item.base_ac
        elif kind in {'craft','upgrade'}:
            return upgrade_item(run,ident,key)
        else:
            if item['kind']!='potion':raise t.ActionError('item is not consumable')
            rolled,rolls=t.dice(run,'2d4+2')
            equipped=[d['inventory'][i] for i in d['imprints'].get(key,{}).values()
                      if i in d['inventory']]
            flat=sum(int(modifier.get('value',0)) for equipped_item in equipped
                     for modifier in equipped_item.get('modifiers',[])
                     if modifier.get('effect')=='healing_bonus')
            percentage=sum(int(equipped_item.get('percentage_bonus',0)) for equipped_item in equipped)
            value=int(round((rolled+flat)*(100+percentage)/100))
            a=run.party[int(key[1:])];before=a.hp;a.adjust_hp(value);del d['inventory'][ident]
            return {'type':'consume','healing':a.hp-before,'rolls':rolls,'item':ident,
                    'evidence':{'actor':a.name,'item':ident,'hp_before':before,'hp_after':a.hp,
                                'healing':a.hp-before,'rolled':rolled,'flat_bonus':flat,
                                'percentage_bonus':percentage}}
        return {'type':kind,'item':copy.deepcopy(item),'actor':key,
                'evidence':{'actor':key,'item':ident,'item_kind':item['kind'],
                            'components_after':d['components'],'gems_after':d['components']}}
    raise t.ActionError(f'unsupported dungeon action: {kind}')


def _attunement_view(run):
    from hollowstar import attunement
    return attunement.public_view(run)


def _expedition_view(run):
    from hollowstar import expedition
    return expedition.view(run)


def _descent_view(d):
    """Where the party stands in the floor stack, for banners and end screens."""
    floors = d['config'].get('floors', [])
    floor = int(d.get('floor', 1))
    current = floors[floor-1] if 0 < floor <= len(floors) else {}
    return {'floor': floor, 'floors_total': len(floors),
            'floor_name': current.get('name'),
            'room': int(d.get('room', 0)), 'rooms_on_floor': len(_room_types_for_floor(d, floor)),
            'status': d.get('status'), 'rooms_cleared': d.get('rooms_cleared', 0),
            'opposition_scale': d.get('opposition_scale', 1.0)}


OPPOSITION_TURN_CAP = 60


def _opposition_holds_initiative(run):
    combat_state = run.context.get('combat')
    if not isinstance(combat_state, dict) or combat_state.get('complete'):
        return False
    if isinstance(run.context.get('arcade'), dict) or state(run).get('status') != 'active':
        return False
    if combat_state.get('pending') or combat_state.get('pending_movement'):
        return False
    return t.actor(run, t.current(run)).controller != 'player'


def act_and_advance(run, action):
    """Apply a player action, then play every non-player-controlled turn until
    a player-controlled actor holds initiative, a party reaction is offered, or the encounter ends.
    Each opposition step is an ordinary engine action chosen by the same
    policy ``design_auto_combat`` uses, so it rolls and records normally."""
    result = act(run, action)
    if run.context.get('manual_opposition'):
        return result
    from hollowstar.policies import combat_action
    # Windows held by AI-controlled reactors (an enemy's opportunity attack,
    # the Tarrasque's legendary action) resolve here, in the same step, so the
    # player is never left facing a window only an NPC could answer.
    reactions = _settle_npc_reactions(run)
    turns = []
    for _ in range(OPPOSITION_TURN_CAP):
        if not _opposition_holds_initiative(run):
            break
        turns.append(act(run, combat_action(run)))
        turns.extend(_settle_npc_reactions(run))
    if isinstance(result, dict):
        if reactions:
            result = {**result, 'auto_reactions': reactions}
        if turns:
            result = {**result, 'opposition_turns': turns}
    return result


def _settle_npc_reactions(run):
    """tactical.settle_npc_reactions through act(), so each answer gets the
    room's combat bookkeeping (completion, rewards) like any other step."""
    combat_state = run.context.get('combat')
    if not isinstance(combat_state, dict) or combat_state.get('complete') or not combat_state.get('pending'):
        return []
    if isinstance(run.context.get('arcade'), dict) or state(run).get('status') != 'active':
        return []
    return t.settle_npc_reactions(run, apply_fn=lambda choice: act(run, choice))


def view(run):
    d=state(run)
    arcade_view = None
    if isinstance(run.context.get('arcade'), dict):
        from hollowstar import arcade
        arcade_view = arcade.view(run)
    cocoon_state=copy.deepcopy(room(run).get('cocoon'))
    events=[]
    for event in d.get('events', [])[-20:]:
        safe=copy.deepcopy(event)
        safe.pop('sealed_record',None)
        events.append(safe)
    registry=run.context.get('content_registry') or load_registry()
    owners={actor.name for actor in run.party if actor.name.lower() in {'doran','wren'}}
    banked=d.get('checkpoint',{}).get('banked')
    banked_ids=set(banked.get('inventory',{})) if banked else set()
    unbanked=[item['id'] for item in _compact_items(d.get('inventory',{}))
              if item['temporary'] and item['id'] not in banked_ids]
    checkpoint={'available':bool(room(run).get('checkpoint') and room(run).get('safe_room')),
                'current':_checkpoint_summary(d.get('checkpoint',{}).get('current')),
                'history':copy.deepcopy(d.get('checkpoint',{}).get('history',[])),
                'unbanked_item_ids':unbanked}
    combat_view = t.view(run) if 'combat' in run.context else None
    combat_actors = (combat_view or {}).get('actors', {})
    combat_positions = (combat_view or {}).get('positions', {})
    combat_economy = (combat_view or {}).get('economy', {})
    party=[]
    for index, actor in enumerate(run.party):
        rules = run.context.get('party_rules', {}).get(f'p{index}', {})
        presentation = rules.get('presentation', {}) if isinstance(rules, dict) else {}
        row={'id':f'p{index}','name':actor.name,'controller':actor.controller,
             'sprite_id':actor.sprite_id,
             'race_id': presentation.get('race_id'), 'gender': presentation.get('gender'),
             'class_id': presentation.get('class_id'),
             'appearance': copy.deepcopy(presentation.get('appearance', {})),
             'hp':actor.hp,'max_hp':actor.max_hp,'ac':actor.armor_class,
             'statuses':sorted(actor.statuses),
             'equipment':[public_item(item) for item in actor.equipment]}
        if combat_view:
            row.update({'identity': combat_actors.get(f'p{index}', {}).get('identity', actor.name.lower()),
                        'position': copy.deepcopy(combat_positions.get(f'p{index}')),
                        'economy': copy.deepcopy(combat_economy.get(f'p{index}', {})),
                        'movement': combat_economy.get(f'p{index}', {}).get('movement', actor.speed)})
        party.append(row)
    result={'status':d['status'],'outcome':TERMINAL_OUTCOMES.get(d['status']),
        'floor':d['floor'],'room':public_room(room(run)),
        'party':party,
        'currency':d['currency'],'gold':d['currency'],
        'tracking':copy.deepcopy(tracking.ensure(d)),
        'event_clock':clock.view(d),
        'daylight_offset_seconds':run.context.get('city_world', {}).get('event_clock', {}).get('seconds', 0),
        'components':d['components'],'gems':d['components'],
        'platinum':d['meta_currency'],'inventory':{key:_public_item(item) for key,item in d['inventory'].items()},
        'events':events,
        'dungeon_history':copy.deepcopy(run.context.get('dungeon_history',[])),
        'reset_history':copy.deepcopy(run.context.get('reset_history',[])),
        'imprints':copy.deepcopy(d['imprints']),'permanent_gear':{key:_public_item(item) for key,item in d['permanent_gear'].items()},
        'discoveries':list(d['discoveries']),
         'hsr_rank':d['hsr_rank'],'rank_xp':d['rank_xp'],'rooms_cleared':d['rooms_cleared'],
        'meta_upgrades':copy.deepcopy(d.get('upgrades',{})),
        'attunement':_attunement_view(run),
        'meta_reward_history':copy.deepcopy(d.get('meta_reward_history', [])),
        'commentary':copy.deepcopy(d.get('commentary',{})),
          'combat':combat_view,
          'arcade':arcade_view,
          'expedition':_expedition_view(run),
        'final_floor':d.get('final_floor','not-reached' if d['floor']<5 else 'boss_victory_only'),
         'final_floor_clock':cocoon_state,
         'star_reveal':copy.deepcopy(d.get('star_reveal')),'tarrasque_loot':d.get('tarrasque_loot'),
         'fixture_status':d['config']['status'],'carry_out':d['config']['carry_out'],
         'pending_carry_out':copy.deepcopy(list(d.get('permanent_gear',{}).values())),
         'content':visible_catalog(registry,{owner.lower() for owner in owners}),
         'checkpoint':checkpoint,
        'terminal_receipt':copy.deepcopy(d.get('terminal_receipt')),
        'last_terminal_receipt':copy.deepcopy(d.get('last_terminal_receipt')),
         'pressure':copy.deepcopy(d.get('pressure', {})),
         'pressure_tells':{'greed': 'unbanked rewards are drawing attention' if d.get('greed', 0) else 'the party carries little unbanked value',
                           'attrition': 'residents are coordinating against repeated disturbance' if d.get('attrition', 0) >= .2 else 'local response remains loosely organized'},
         'scale_of_consequence':d.get('pressure', {}).get('scale', 'mortal'),
         'descent':_descent_view(d)}
    projected_actions=available_actions(run,room(run))
    if projected_actions:
        result['available_actions']=projected_actions
    return result
