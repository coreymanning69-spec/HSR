"""Deliberate DESIGN-fixture combat. All adapters call these transitions.

Runtime-pair numbers come from the frozen run's source snapshot. This module
does not claim complete Steward fidelity. Unsupported actions fail explicitly.
"""
from __future__ import annotations

import copy
import math
import re

from hollowstar.actors import Actor
from hollowstar.items import public_item, item_presentation
from hollowstar.phases import Phase, Direction
from hollowstar.tags import DamageTag
from hollowstar.authored_mechanics import is_doran, is_tarrasque, is_wren
from hollowstar import champion_rules


class ActionError(ValueError):
    pass


def _attack_animation(actor: Actor) -> str:
    weapon = actor.weapon()
    if weapon is None:
        return "melee_1h"
    return item_presentation(weapon).get("animation_profile", "melee_1h")


def _actor_loadout_presentation(actor: Actor) -> dict:
    rows = [public_item(item).get("presentation", {}) for item in actor.equipment]
    weapon = next((row for row in rows if row.get("item_type") in {"weapon", "shield"}), {})
    armor = next((row for row in rows if row.get("item_type") in {"armor", "headgear"}), {})
    return {"weapon": copy.deepcopy(weapon), "armor": copy.deepcopy(armor),
            "animation_profile": weapon.get("animation_profile", "melee_1h"),
            "handedness": weapon.get("handedness", "none")}


CONDITIONS = {"PRONE", "GRAPPLED", "RESTRAINED", "STUNNED", "PARALYZED",
              "INCAPACITATED", "BLINDED", "FRIGHTENED", "CHARMED", "POISONED",
              "DODGING", "DISENGAGED", "INVISIBLE", "HASTED", "SLOWED"}
CONDITIONS |= {"CONFUSED", "DOMINATED", "POSSESSED", "MENTALLY_PARALYZED",
               "FEEBLEMIND", "MEMORY_EDIT", "PETRIFIED"}
# The "of Silence" affix has always inflicted SILENCED; until it was listed
# here a hit carrying it raised mid-attack. Silence blocks spellcasting that
# is not cast with Silent Spell (spells.cast).
CONDITIONS |= {"SILENCED"}
INCAPACITATING = {"STUNNED", "PARALYZED", "INCAPACITATED"}
MENTAL_CONDITIONS = {"CHARMED", "FRIGHTENED", "CONFUSED", "DOMINATED",
                     "POSSESSED", "MENTALLY_PARALYZED", "FEEBLEMIND", "MEMORY_EDIT"}
CONDITION_CATEGORIES = {
    **{name: "mental" for name in MENTAL_CONDITIONS},
    **{name: "physical" for name in CONDITIONS - MENTAL_CONDITIONS},
}

# Doran's Grand Cleave flat-damage expression (sourced: DM044_0).
# maneuvers.grand_cleave() also uses this via import so the value lives in one place.
DORAN_CLEAVER_FLAT_DAMAGE: str = "40"


def condition_category(name):
    return CONDITION_CATEGORIES.get(name, "unknown")


def number(value, label, low=0, high=10000):
    if type(value) is not int or not low <= value <= high:
        raise ActionError(f"{label} must be an integer in {low}..{high}")
    return value


def dice(run, expression, *, critical=False, maximize=False):
    if isinstance(expression, int) and not isinstance(expression, bool):
        if expression < 0:
            raise ActionError(f"unsupported dice expression: {expression}")
        return expression, [expression]
    if isinstance(expression, str) and expression.isdigit():
        return int(expression), [int(expression)]
    match = re.fullmatch(r"(\d{1,3})d(4|6|8|10|12|20)([+-]\d+)?", expression)
    if not match or not 1 <= int(match[1]) <= 100:
        raise ActionError(f"unsupported dice expression: {expression}")
    count, sides, modifier = int(match[1]), int(match[2]), int(match[3] or 0)
    values = [sides if maximize else run.rng.randint(1, sides) for _ in range(count * (2 if critical else 1))]
    return max(0, sum(values) + modifier), values


def actors(run):
    return {f"p{i}": a for i, a in enumerate(run.party)} | {f"e{i}": a for i, a in enumerate(run.opposition)}


def actor(run, key):
    _all = actors(run)
    if key not in _all:
        raise ActionError(f"unknown actor: {key}")
    return _all[key]


def rules(run, key):
    return run.context["combat"]["rules"][key]


def position(run, key):
    return run.context["combat"]["positions"][key]


def distance(run, first, second):
    a, b = position(run, first), position(run, second)
    return max(abs(a[i] - b[i]) for i in range(3))


def same_side(first, second):
    return first[0] == second[0]


def conscious(a):
    return a.alive and not INCAPACITATING.intersection(a.statuses)


def wren_near(run, key, radius=30):
    return any(same_side(key, k) and is_wren(r.get("identity")) and actor(run, k).alive
               and distance(run, key, k) <= radius for k, r in run.context["combat"]["rules"].items())


def roll_check(run, bonus, dc, advantage=False, disadvantage=False):
    rolls = [run.rng.d20()]
    if advantage != disadvantage:
        rolls.append(run.rng.d20())
    natural = max(rolls) if advantage and not disadvantage else min(rolls)
    return {"rolls": rolls, "natural": natural, "bonus": bonus, "total": natural + bonus,
            "dc": dc, "success": natural + bonus >= dc}


def saving_throw(run, key, ability, dc, magical=False, concentration=False):
    a, r = actor(run, key), rules(run, key)
    if r.get("contained_by"):
        return None
    if ability not in a.ability_scores:
        raise ActionError(f"unsupported save: {ability}")
    if ability in {"STR", "DEX"} and {"STUNNED", "PARALYZED"}.intersection(a.statuses):
        return {"success": False, "automatic": "incapacitated physical save", "dc": dc}
    adv = wren_near(run, key) or (magical and champion_rules.flag(r.get("identity"), "mental_save_advantage"))
    adv |= magical and r.get("identity")=="tarrasque"
    adv |= concentration and champion_rules.flag(r.get("identity"), "mental_save_advantage")
    adv |= ability == "DEX" and "HASTED" in a.statuses
    result=roll_check(run, r.get("saves", {}).get(ability, a.ability_modifier(ability)), dc, adv,
                      ability == "DEX" and "RESTRAINED" in a.statuses)
    if not result['success'] and r.get('identity')=='tarrasque' and a.resources.get('legendary_resistance'):
        spend(a,'legendary_resistance');result['success']=True;result['legendary_resistance']=True
    return result


def indomitable(run, key, failed_save):
    """Doran's authored once-per-use reroll of a failed saving throw."""
    a, r = actor(run, key), rules(run, key)
    if r.get("identity") != "doran":
        raise ActionError("Indomitable is not available")
    if not isinstance(failed_save, dict) or failed_save.get("success") is not False:
        raise ActionError("Indomitable requires a failed saving throw")
    spend(a, "indomitable")
    reroll = roll_check(run, failed_save.get("bonus", 0), failed_save.get("dc"))
    return {"type": "indomitable", "actor": key, "save": reroll,
            "evidence": {"failed_save": dict(failed_save), "reroll": dict(reroll),
                         "resources_remaining": a.resources.get("indomitable", 0)}}


def spend(a, resource, amount=1):
    number(amount, "resource cost")
    if a.resources.get(resource, 0) < amount:
        raise ActionError(f"insufficient {resource}: need {amount}, have {a.resources.get(resource, 0)}")
    a.resources[resource] -= amount
    if resource.startswith("slot_") and "spell_slots_total" in a.resources:
        a.resources["spell_slots_total"] = sum(v for k, v in a.resources.items() if k.startswith("slot_"))


STAFF_COSTS = {"detect_magic": 0, "enlarge_reduce": 0, "light": 0,
               "mage_hand": 0, "protection_from_evil_and_good": 0,
               "flaming_sphere": 2, "invisibility": 2, "knock": 2, "web": 2,
               "dispel_magic": 5, "fireball": 5, "ice_storm": 5,
               "lightning_bolt": 5, "passwall": 5, "telekinesis": 5,
               "conjure_elemental": 7, "plane_shift": 7, "fire_storm": 7}


def staff_cast(run, key, spell):
    a, r = actor(run, key), rules(run, key)
    if r.get("identity") != "wren":
        raise ActionError("Staff of the Magi is not available")
    if a.resources.get("staff_destroyed"):
        raise ActionError("staff has already been destroyed")
    spell = str(spell).lower().replace(" ", "_")
    if spell not in STAFF_COSTS:
        raise ActionError("staff spell requires an authored charge ruling")
    cost, before = STAFF_COSTS[spell], a.resources.get("staff_charges", 50)
    if before < cost:
        raise ActionError(f"insufficient staff_charges: need {cost}, have {before}")
    a.resources["staff_charges"] = before - cost
    return {"type": "staff_cast", "actor": key, "spell": spell, "charges": cost,
            "evidence": {"charges_before": before, "charges_after": a.resources["staff_charges"]}}


def staff_absorb(run, key, spell_level):
    a, r = actor(run, key), rules(run, key)
    if r.get("identity") != "wren":
        raise ActionError("Staff absorption is not available")
    if a.resources.get("staff_destroyed"):
        raise ActionError("staff has already been destroyed")
    number(spell_level, "spell level", 1, 9)
    before = a.resources.get("staff_charges", 50)
    a.resources["staff_charges"] = min(50, before + spell_level)
    return {"type": "staff_absorb", "actor": key, "spell_level": spell_level,
            "evidence": {"charges_before": before, "charges_after": a.resources["staff_charges"],
                         "absorbed": min(spell_level, 50-before)}}


def incoming_spell(run, source, target, spell_level):
    if not actor(run, source).alive or not actor(run, target).alive:
        raise ActionError("spell requires living source and target")
    if same_side(source, target) or rules(run, target).get("identity") != "wren":
        raise ActionError("Staff absorption requires an enemy spell targeting Wren")
    number(spell_level, "spell level", 1, 9)
    window={"kind":"spell","reactor":target,"source":source,
            "target":target,"spell_level":spell_level}
    run.context["combat"]["pending"].append(window)
    return {"type":"incoming_spell","source":source,"target":target,
            "spell_level":spell_level,"pending_reactions":[window]}


def incoming_failed_save(run, source, target, failed_save):
    if not actor(run, source).alive or not actor(run, target).alive or same_side(source, target):
        raise ActionError("save event requires a living enemy source")
    if not isinstance(failed_save, dict) or failed_save.get('success') is not False:
        raise ActionError("reaction conversion requires a failed save")
    wren=next((k for k,r in run.context['combat']['rules'].items()
               if r.get('identity')=='wren' and actor(run,k).alive),None)
    if wren is None or distance(run,wren,target) > 30:
        raise ActionError("no living Wren within 30 feet for save conversion")
    window={'kind':'save','reactor':wren,
            'target':target,'source':source,'feature':'Aura of the Unbound','failed_save':failed_save}
    run.context['combat']['pending'].append(window)
    return {'type':'incoming_failed_save','pending_reactions':[window]}


def staff_retributive_strike(run, key, targets):
    a, r = actor(run, key), rules(run, key)
    if r.get("identity") != "wren":
        raise ActionError("Retributive strike is not available")
    if a.resources.get("staff_destroyed"):
        raise ActionError("staff has already been destroyed")
    if not isinstance(targets, list) or not targets:
        raise ActionError("retributive strike requires targets")
    amount, rolls = dice(run, "16d6")
    results=[]
    for target in targets:
        check_target(run, key, target, 30, enemy=True)
        results.append(damage(run, key, target, amount, "FORCE"))
    a.resources["staff_destroyed"] = True
    return {"type":"staff_retributive_strike", "actor":key, "rolls":rolls,
            "targets":list(targets), "results":results,
            "evidence":{"radius":30,"damage_type":"FORCE","rolls":list(rolls),
                         "staff_destroyed":True}}


def staff_utility(run, key, mode, target=None):
    """Wren's Staff of the Magi physical utility lane."""
    if rules(run,key).get('identity') != 'wren':
        raise ActionError('staff utility belongs to Wren')
    if actor(run,key).resources.get('staff_destroyed'):
        raise ActionError('staff has already been destroyed')
    if mode not in {'prop','jam','lever','span'}:
        raise ActionError('unsupported staff utility mode')
    utility={'mode':mode,'target':target,'actor':key,'durable':True}
    run.context['combat']['terrain'].setdefault('staff_utilities',[]).append(utility)
    return {'type':'staff_utility','actor':key,'mode':mode,'target':target,
            'evidence':{'utility':mode,'target':target,
                        'state_change':'durable terrain utility added',
                        'source':'Staff of the Magi physical utility'}}


FORCE_CONSTRUCTS = {"wall_of_force", "forcecage", "resilient_sphere", "blade_barrier", "otilukes_resilient_sphere"}


def dagger_cut_structure(run, key, structure_id, mode="thrown"):
    a, r = actor(run, key), rules(run, key)
    if r.get("identity") != "doran" or mode not in {"thrown", "dual_held"}:
        raise ActionError("force-construct access requires Doran's dagger mode")
    structures = run.context["combat"]["terrain"].get("structures", [])
    if not isinstance(structure_id, int) or structure_id < 0 or structure_id >= len(structures):
        raise ActionError("unknown force construct")
    structure = structures[structure_id]
    if structure.get("kind") not in FORCE_CONSTRUCTS:
        raise ActionError("dagger bypass does not affect general abjuration")
    p = structure.get("position")
    if not isinstance(p, list) or len(p) < 2:
        raise ActionError("force construct requires a grid position")
    limit = 5 if mode == "dual_held" else 70
    if max(abs(p[i] - position(run, key)[i]) for i in range(min(3, len(p)))) > limit:
        raise ActionError("force construct is out of dagger range")
    before = structure.get("hp", 0)
    amount, rolls = dice(run, "1d8+10")
    structure["hp"] = max(0, before - amount)
    return {"type":"dagger_cut_structure", "actor":key, "mode":mode,
            "structure":structure.get("kind"), "rolls":rolls,
            "evidence":{"barrier_bypass":True,"resistance_bypassed":True,
                         "hp_before":before,"damage":amount,"hp_after":structure["hp"]}}


def economy(run, key):
    return run.context["combat"]["economy"][key]


def use(run, key, slot):
    e = economy(run, key)
    if not e.get(slot, 0):
        raise ActionError(f"{slot} already spent")
    e[slot] -= 1


def end_concentration(run, key):
    state = run.context["combat"]
    old = state["concentration"].pop(key, None)
    if old:
        for target in old.get("targets", []):
            for condition_name in old.get("conditions", []):
                actor(run, target).statuses.pop(condition_name, None)
    return copy.deepcopy(old)


def condition(run, key, name, duration, *, mental=False):
    if name not in CONDITIONS:
        raise ActionError(f"condition requires implementation: {name}")
    number(duration, "duration", 1, 10000)
    a, r = actor(run, key), rules(run, key)
    if name in r.get("condition_immunities",[]):
        return {"condition":name,"category":condition_category(name),"applied":False,"reason":"condition immunity"}
    if r.get("spirit_until",0)>run.round_number and name in {"CHARMED","FRIGHTENED","PARALYZED","RESTRAINED","STUNNED","GRAPPLED","INCAPACITATED","PETRIFIED"}:
        return {"condition":name,"category":condition_category(name),"applied":False,"reason":"Indomitable Spirit"}
    if r.get("identity") == "wren" and (mental or name in MENTAL_CONDITIONS):
        return {"condition": name, "category":condition_category(name), "applied": False, "reason": "mind lock"}
    if name in {"GRAPPLED", "RESTRAINED", "PARALYZED", "PETRIFIED"} and wren_near(run, key):
        return {"condition": name, "category":condition_category(name), "applied": False, "reason": "Unshackled Host"}
    if r.get("planted") and name == "PRONE":
        return {"condition": name, "category":condition_category(name), "applied": False, "reason": "planted displacement immunity"}
    from hollowstar.lattice import denies
    denial = denies(run, key, name)
    if denial:
        return {"condition": name, "category": condition_category(name), "applied": False,
                "reason": "consequence denied", "lattice": denial, "tell": denial["tell"]}
    a.statuses[name] = duration
    if name in INCAPACITATING:
        end_concentration(run, key)
    return {"condition": name, "category":condition_category(name), "applied": True, "duration": duration}


# House rule from the contextual-dynamics spec, not 2014 D&D: an exceptional
# score shrugs off *mundane* versions of these consequences. Magical riders
# and the authored DM044 maneuver/spell/monster paths never consult it.
ABILITY_THRESHOLD_IMMUNITIES = (
    ("CON", 18, frozenset({"POISONED"}), "an iron constitution shrugs off ordinary poison"),
    ("WIS", 18, frozenset({"FRIGHTENED", "CHARMED"}), "an unshakable will refuses ordinary fear and charm"),
    ("STR", 18, frozenset({"PRONE", "DISPLACEMENT"}), "planted strength refuses a mundane knockdown or shove"),
)


def threshold_immunity(run, key, name, *, magical=False):
    """Evidence when an ability score of 18+ refuses a mundane consequence."""
    if magical:
        return None
    a = actor(run, key)
    for ability, minimum, names, tell in ABILITY_THRESHOLD_IMMUNITIES:
        if name in names and a.ability_score(ability) >= minimum:
            return {"ability": ability, "score": a.ability_score(ability), "minimum": minimum,
                    "condition": name, "tell": tell}
    return None


def apply_rider(run, source, target, rider):
    """Resolve one CONSEQUENCE rider: threshold, saving throw, then condition.

    A rider is {name, duration} plus optional {save: {ability, dc}, magical,
    mental}. Lattice denial and the existing condition immunities live inside
    condition() so every source of a condition honours them, not only riders.
    """
    name = str(rider.get("name", "")).upper()
    duration = int(rider.get("duration", 1) or 1)
    magical = bool(rider.get("magical", False))
    base = {"condition": name, "category": condition_category(name), "source": source}
    if rider.get("source_effect"):
        base["source_effect"] = rider["source_effect"]
    if name not in CONDITIONS:
        return {**base, "applied": False, "reason": "condition requires implementation"}
    threshold = threshold_immunity(run, target, name, magical=magical)
    if threshold:
        return {**base, "applied": False, "reason": "ability threshold immunity",
                "threshold": threshold, "tell": threshold["tell"]}
    save = rider.get("save")
    if save is None and rider.get("save_ability") and rider.get("save_dc"):
        save = {"ability": rider["save_ability"], "dc": rider["save_dc"]}
    check = None
    if isinstance(save, dict):
        check = saving_throw(run, target, str(save.get("ability", "")).upper(), int(save.get("dc", 10)), magical=magical)
        if check is None:
            return {**base, "applied": False, "reason": "target is contained", "save": None}
        if check.get("success"):
            return {**base, "applied": False, "reason": "saving throw", "save": check}
    outcome = condition(run, target, name, duration, mental=bool(rider.get("mental", False)))
    outcome.update({key: value for key, value in base.items() if key not in outcome})
    if check is not None:
        outcome["save"] = check
    return outcome


def damage(run, source, target, amount, damage_type, *, bypass_resistance=False, riders=()):
    """One damage instance, followed by its riders. Wren's breaking ward stops both."""
    number(amount, "damage", 0, 100000)
    if damage_type not in DamageTag.__members__:
        raise ActionError(f"damage type requires implementation: {damage_type}")
    a, r = actor(run, target), rules(run, target)
    time_stop=run.context["combat"].get("time_stop")
    if time_stop and time_stop.get("owner") == source and target != source:
        time_stop["ended_by"]={"source":source,"target":target,"reason":"affected another creature"}
        run.context["combat"].pop("time_stop",None)
    raw = amount
    source_rules=rules(run,source)
    # DM041_B divine_damage: Wren's DIVINE tag rides beside the printed type on
    # every attack and spell. The printed type still controls immunity and
    # vulnerability; a resistance to it cannot fully blunt the alongside tag.
    from hollowstar.affix_runtime import offensive_tags, damage_resistances
    from hollowstar import lattice
    source_tags = offensive_tags(run, source, {tag.name for tag in actor(run, source).offensive_tags()})
    source_tags.add(damage_type)
    # Immunity Lattice, MAGNITUDE: a conversion changes what the damage IS
    # before any resistance, armor treatment, or immunity reads it.
    printed_type = damage_type
    damage_type, conversions = lattice.convert(run, source, target, damage_type)
    source_tags.add(damage_type)
    armor_damage_type = damage_type
    if damage_type == "PHYSICAL":
        # Untyped physical sources still need a subtype before divine-plate
        # mitigation; prefer an explicitly carried weapon tag, otherwise use
        # the conservative bludgeoning lane for the DESIGN resolver.
        armor_damage_type = next((tag for tag in ("PIERCING", "SLASHING", "BLUDGEONING")
                                  if tag in source_tags), "BLUDGEONING")
    if is_tarrasque(r.get('identity')) and damage_type in {'PIERCING','SLASHING','BLUDGEONING'} and not (is_doran(source_rules.get('identity')) or is_wren(source_rules.get('identity'))):
        from hollowstar.phases import Tier
        weapon=actor(run,source).weapon()
        if not weapon or weapon.tier==Tier.MUNDANE:amount=0
    if r.get("identity") == "doran":
        if damage_type in {"FIRE", "ICE"}:
            amount = 0
        else:
            amount = int(amount * {"PIERCING": .25, "SLASHING": .375, "BLUDGEONING": .75}.get(armor_damage_type, 1))
    affix_resistances = damage_resistances(run, target)
    lattice_immunity = lattice.immunity(run, source, target, damage_type)
    if damage_type in r.get("immunities", []) or lattice_immunity:
        amount = 0
    elif (damage_type in r.get("resistances", []) or damage_type in affix_resistances) and not bypass_resistance and "DIVINE" not in source_tags:
        amount //= 2
    if damage_type in r.get("vulnerabilities", []):
        amount *= 2
    ward = a.resources.get("ward", 0)
    blocked = ward > 0
    if blocked:
        a.resources["ward"] = max(0, ward - amount)
        amount = 0
    temporary = min(a.resources.get("temporary_hp", 0), amount)
    if temporary:
        a.resources["temporary_hp"] -= temporary
        amount -= temporary
    before = a.hp
    a.adjust_hp(-amount)
    event = {"type": "damage", "source": source, "target": target, "raw": raw,
             "damage_type": damage_type, "damage_tags": sorted(source_tags), "damage": before-a.hp, "ward_before": ward,
             "ward_after": a.resources.get("ward", 0), "riders": [],
             "evidence": {"raw": raw, "damage_type": damage_type,
                          "bypass_resistance": bypass_resistance,
                          "source_tags": sorted(source_tags),
                          "armor_damage_type": armor_damage_type,
                          "immunity": damage_type in r.get("immunities", []),
                          "resisted": (damage_type in r.get("resistances", []) or damage_type in affix_resistances) and not bypass_resistance and "DIVINE" not in source_tags,
                          "affix_resistances": sorted(affix_resistances),
                          "vulnerable": damage_type in r.get("vulnerabilities", []),
                          "armor_treatment": "doran_divine_plate" if r.get("identity") == "doran" else None,
                          "ward_before": ward, "target_hp_before": before}}
    if conversions:
        event["evidence"]["printed_damage_type"] = printed_type
        event["evidence"]["conversions"] = conversions
    if lattice_immunity:
        event["evidence"]["lattice_immunity"] = lattice_immunity
        event["tell"] = lattice_immunity["tell"]
    if not blocked:
        for rider in riders:
            event["riders"].append(apply_rider(run, source, target, rider))
    if amount and target in run.context["combat"]["concentration"]:
        save = saving_throw(run, target, "CON", max(10, amount // 2), concentration=True)
        event["concentration_save"] = save
        if not save["success"] or not a.alive:
            end_concentration(run, target)
    if rules(run,source).get('swallowed_by')==target:
        r['inside_damage'][source]=r['inside_damage'].get(source,0)+(before-a.hp)
    if not a.alive:
        end_concentration(run, target)
    event["evidence"].update({"post_mitigation": amount, "damage_applied": before-a.hp,
                               "target_hp_after": a.hp,
                               "temporary_hp_after": a.resources.get("temporary_hp", 0),
                               "concentration": event.get("concentration_save")})
    # The read ends when its subject hits Doran, even if plate negates damage.
    if r.get("read_target") == source:
        r.pop("read_target", None)
    return event


def heal(run, target, expression):
    a = actor(run, target)
    resources_before = dict(a.resources)
    hp_before = a.hp
    amount, rolls = dice(run, expression, maximize=rules(run, target).get("identity") == "doran")
    a.adjust_hp(amount)
    return {"type": "healing", "target": target, "rolls": rolls, "healing": a.hp-hp_before,
            "evidence": {"actor": a.name, "expression": expression, "rolls": list(rolls),
                         "hp_before": hp_before, "hp_after": a.hp,
                         "resources_before": resources_before, "resources_after": dict(a.resources)}}


def begin(run, party_rules=None):
    all_actors = actors(run)
    prior = run.context.get("combat", {})
    state = {"schema": 1, "order": [], "cursor": 0, "positions": {}, "rules": {},
             "economy": {}, "concentration": {}, "pending": [], "pending_movement": None, "events": [],
             "surprised": {},
             "terrain": {"width": 120, "height": 120, "difficult": [], "blocked": [], "cover": {}, "structures": [], "dark": False, "daylight": True},
             "complete": False}
    run.context["combat"] = state
    for key, a in all_actors.items():
        r = copy.deepcopy((party_rules or {}).get(key, prior.get("rules", {}).get(key, {})))
        # Content equipment is selected outside combat (for example, when a
        # player says "Doran draws the daggers").  Carry that authored
        # loadout into the encounter rules so the first attack uses the
        # selected weapon instead of silently falling back to "weapon".
        content_state = run.context.get("content_state", {}).get(key, {})
        if content_state.get("loadout") and not r.get("loadout"):
            r["loadout"] = content_state["loadout"]
        r.setdefault("saves", {k: a.ability_modifier(k) for k in a.ability_scores})
        r.setdefault("baseline_resources", dict(a.resources))
        r.setdefault("base_ac", a.armor_class)
        # DM044_0's authored Alert ruling is identity-owned for the two
        # promoted residents. Explicit encounter values remain authoritative.
        if r.get("identity") in {"doran", "wren"}:
            r.setdefault("alert", True)
        if is_doran(r.get("identity")):
            r.setdefault("vision_range", 120)
        elif r.get("identity") == "wren":
            r.setdefault("vision_range", 120)
        if r.get("identity")=="wren":
            a.resources.setdefault("misty_step_free",5)
            a.resources.setdefault("simulacrum_cast",1)
            a.resources.setdefault("staff_charges",50)
            # Older saves used a second counter; retain any spent use on migration.
            if "save_conversion" in a.resources:
                a.resources["unbound_save_conversion"] = min(
                    a.resources.get("unbound_save_conversion", 1), a.resources.pop("save_conversion"))
            a.resources.setdefault("unbound_save_conversion",1)
            r.setdefault("anchor",[10,10,0])
        state["rules"][key] = r
        if r.get("surprised") and not r.get("alert"):
            state["surprised"][key] = True
        state["positions"][key] = [10 if key.startswith("p") else 40, 10+10*int(key[1:]), 0]
        state["economy"][key] = {"action": 1, "bonus": 1, "reaction": 1, "movement": a.speed, "attacks": 0}
    # Turn 0: encounter lattice rows are validated here, the one chokepoint
    # every encounter passes, then start-of-combat triggers resolve before a
    # single initiative die is rolled. No rows means no RNG and no events.
    from hollowstar import lattice
    for key, r in state["rules"].items():
        if r.get("lattice"):
            try:
                r["lattice"] = [lattice.validate(effect) for effect in r["lattice"]]
            except ValueError as exc:
                raise ActionError(f"invalid Immunity Lattice for {key}: {exc}") from exc
    turn_zero = lattice.start_of_combat(run)
    state["turn_zero"] = turn_zero
    rolls = {key: run.rng.d20()+a.initiative_bonus for key, a in all_actors.items() if a.alive}
    state["order"] = sorted(rolls, key=lambda key: (-rolls[key], key))
    state["initiative_rolls"] = rolls
    run.round_number = 1
    if isinstance(run.context.get("dungeon"), dict):
        from hollowstar import tracking
        tracking.ensure(run.context["dungeon"])["combat_encounters"] += 1
    if turn_zero and run.finished():
        # The cascade ended the fight before Round 1; callers settle rewards.
        state["complete"] = True
    if not state["order"] and not state["complete"]:
        raise ActionError("initiative requires living actors")
    recovered = []
    for key, r in state["rules"].items():
        if r.get("identity") == "doran" and actor(run, key).resources.get("superiority_dice") == 0:
            actor(run, key).resources["superiority_dice"] = 1
            recovered.append(key)
    result = {"type": "initiative", "order": state["order"], "rolls": rolls,
              "evidence": {"relentless_recovered": recovered}}
    if turn_zero:
        result["turn_zero"] = copy.deepcopy(turn_zero)
        result["evidence"]["turn_zero_resolved_before_initiative"] = True
        result["evidence"]["turn_zero_ended_combat"] = state["complete"]
    return result


def current(run):
    state = run.context["combat"]
    return state["order"][state["cursor"]]


def finish_turn(run):
    state = run.context["combat"]
    key = current(run)
    a = actor(run, key)
    was_surprised = bool(state["surprised"].pop(key, False))
    round_before, cursor_before = run.round_number, state["cursor"]
    economy_before = copy.deepcopy(state["economy"].get(key, {}))
    expired_statuses=[]
    from hollowstar.monsters import end_turn as monster_end
    end_events=monster_end(run,key)
    for ar in state['rules'].values():
        if key in ar.get('declined_targets',[]):ar['declined_targets'].remove(key)
    for name in list(a.statuses):
        if name not in {"DODGING", "DISENGAGED"}:
            a.statuses[name] -= 1
            if a.statuses[name] <= 0:
                expired_statuses.append(name)
                del a.statuses[name]
    time_stop=state.get("time_stop")
    if time_stop and time_stop.get("owner") == key and time_stop.get("remaining",0) > 1:
        time_stop["remaining"] -= 1
        state["economy"][key] = {"action": 1, "bonus": 1, "reaction": 1,
                                   "movement": 0 if rules(run,key).get("planted") else rules(run,key).get("fly_speed", a.speed),
                                   "attacks": 0}
        return {"type":"time_stop_turn","actor":key,"round":run.round_number,
                "end_events":end_events,"start_events":[],
                "evidence":{"remaining":time_stop["remaining"],"initiative_paused":True}}
    if time_stop and time_stop.get("owner") == key:
        state.pop("time_stop",None)
    for _ in state["order"]:
        state["cursor"] += 1
        if state["cursor"] == len(state["order"]):
            state["cursor"] = 0
            run.round_number += 1
        key = current(run)
        if actor(run, key).alive:
            break
    if isinstance(run.context.get("dungeon"), dict) and run.round_number != round_before:
        from hollowstar import tracking
        tracking.ensure(run.context["dungeon"])["combat_rounds"] += max(0, run.round_number - round_before)
    for owner, concentration in list(state["concentration"].items()):
        if key in concentration.get("targets",[]) and concentration.get("repeat_save"):
            save=saving_throw(run,key,concentration["repeat_save"],22,magical=True)
            if save["success"]:
                for name in concentration.get("conditions",[]):actor(run,key).statuses.pop(name,None)
        if owner == key:
            concentration["remaining"]-=1
            if concentration["remaining"]<=0:end_concentration(run,owner)
    a, r = actor(run, key), rules(run, key)
    r.pop("goaded_by",None)
    # Help lasts until the helper's next turn begins.
    for other_rules in state["rules"].values():
        if (other_rules.get("help_advantage") or {}).get("from") == key:
            other_rules.pop("help_advantage", None)
    # A contested grapple (grapple()) ends when the grip is gone: the grappler
    # fell, was incapacitated, or is no longer within 5 feet.
    grappler = r.get("grappled_by")
    if grappler and (not conscious(actor(run, grappler)) or distance(run, grappler, key) > 5):
        _release_grapple(run, key)
    a.statuses.pop("DODGING", None)
    a.statuses.pop("DISENGAGED", None)
    a.armor_class = r["base_ac"]
    r.pop("shield", None)
    state["economy"][key] = {"action": 1, "bonus": 1, "reaction": 1,
                            "movement": 0 if r.get("planted") else r.get("fly_speed", a.speed),
                            "attacks": 0}
    if r.get("survivor") and 0 < a.hp <= a.max_hp//2:
        a.adjust_hp(5 + a.ability_modifier("CON"))
    from hollowstar.monsters import start_turn as monster_start
    start_events = monster_start(run,key)
    return {"type": "turn", "actor": key, "round": run.round_number,"end_events":end_events,"start_events":start_events,
            "evidence":{"actor":a.name,"round_before":round_before,"round_after":run.round_number,
                        "cursor_before":cursor_before,"cursor_after":state["cursor"],
                        "economy_before":economy_before,"economy_after":copy.deepcopy(state["economy"].get(key, {})),
                        "status_after":dict(a.statuses),"surprised_cleared":was_surprised,
                        "expired_statuses":expired_statuses,
                        "concentration_events":start_events}}


def check_target(run, source, target, maximum, *, enemy=True):
    if not actor(run, target).alive:
        raise ActionError("target is not alive")
    if same_side(source, target) == enemy and rules(run,source).get("identity")!="tarrasque" and rules(run,target).get("identity")!="tarrasque":
        raise ActionError("invalid target side")
    if distance(run, source, target) > maximum:
        raise ActionError("target out of range")
    ceiling = run.context["combat"].get("terrain", {}).get("ceiling_z")
    if ceiling is not None and position(run, source)[2] > ceiling:
        raise ActionError("source is above the room ceiling")
    if ceiling is not None and position(run, target)[2] > ceiling:
        raise ActionError("target is above the room ceiling")
    terrain = run.context["combat"]["terrain"]
    if terrain.get("dark") and rules(run, source).get("vision_range") is not None \
            and distance(run, source, target) > rules(run, source)["vision_range"]:
        raise ActionError("target is beyond normal sight in darkness")
    if terrain["cover"].get(target) == "total" and rules(run,source).get("swallowed_by")!=target and rules(run,target).get("swallowed_by")!=source:
        raise ActionError("target behind total cover")
    from hollowstar.affix_runtime import targeting_denial
    denied = targeting_denial(run, source, target)
    if denied:
        raise ActionError(f"targeting denied by {denied['item']}")


def _line_axis(run, source, target):
    origin, tip = position(run, source), position(run, target)
    dx, dy = tip[0] - origin[0], tip[1] - origin[1]
    axis = 0 if abs(dx) >= abs(dy) else 1
    sign = 1 if (dx if axis == 0 else dy) >= 0 else -1
    return axis, sign


def _cleaver_carry_through(run, source, target, amount, kind, reach):
    """DM044_0 ordinary carry-through: the same rolled damage parts every body
    at or below it along the swing line, in order, and stops at the first
    survivor. Each subsequent body still resolves its own resistances; the
    primary target's affix riders are not replayed onto bodies it never hit."""
    axis, sign = _line_axis(run, source, target)
    origin, tip = position(run, source), position(run, target)
    off, threshold = tip[1 - axis], (tip[axis] - origin[axis]) * sign
    candidates = [k for k in actors(run) if k not in {source, target} and actor(run, k).alive
                  and position(run, k)[1 - axis] == off
                  and (position(run, k)[axis] - origin[axis]) * sign > threshold
                  and distance(run, source, k) <= reach]
    candidates.sort(key=lambda k: distance(run, source, k))
    chain = []
    for key in candidates:
        result = damage(run, source, key, amount, kind)
        parted = not actor(run, key).alive
        chain.append({"target": key, "result": result, "parted": parted})
        if not parted:
            chain[-1]["skid"] = _cleaver_skid(run, source, key, amount)
            break
    return chain


def _cleaver_skid(run, source, target, amount):
    """DM044_0 Skid: a Cleaver survivor moves 5 x floor(damage/50) feet away
    from the swing; Gargantuan targets halve that distance, rounded down to
    the nearest 5 feet."""
    feet = 5 * (amount // 50)
    if rules(run, target).get("size") == "gargantuan":
        feet = (feet // 2) // 5 * 5
    if not feet:
        return None
    axis, sign = _line_axis(run, source, target)
    before = position(run, target)
    after = list(before)
    after[axis] = max(0, min(120, after[axis] + sign * feet))
    run.context["combat"]["positions"][target] = after
    return {"target": target, "feet": feet, "from": before, "to": after}


def weapon_attack(run, source, target, mode="weapon", *, bonus=False, reaction=False):
    a, r = actor(run, source), rules(run, source)
    resources_before = dict(a.resources)
    economy_before = copy.deepcopy(economy(run, source))
    weapon = a.weapon()
    if r.get("disarmed"):
        raise ActionError("weapon is disarmed; recover it before attacking")
    if not weapon:
        raise ActionError("no weapon equipped")
    identity = r.get("identity")
    if identity == "doran":
        if mode not in {"weapon", "dagger", "cleaver"}:
            raise ActionError("unsupported weapon mode")
        cleaver = mode == "cleaver"
        tight = run.context["combat"]["terrain"].get("human_tight", False)
        attack_bonus = 14 if cleaver and tight else 16
        expression, kind = (DORAN_CLEAVER_FLAT_DAMAGE, "SLASHING") if cleaver else ("1d8+10", "PIERCING")
        reach = (5 if tight else 10) if cleaver else 70
        long_range = 30 if not cleaver else reach
    elif identity == "wren":
        if mode not in {"weapon", "crown"}:
            raise ActionError("unsupported Wren weapon")
        if not bonus:
            raise ActionError("Crown of Stars requires a bonus action")
        expression, kind, attack_bonus, reach, long_range = "4d12", "RADIANT", 14, 120, 120
    else:
        profile = a.weapon_profile()
        if not profile or not profile["damage_dice"]:
            raise ActionError("weapon dice are not implemented")
        selected = profile
        if mode != "weapon":
            selected = weapon.alternate_modes.get(mode)
            if not isinstance(selected, dict):
                raise ActionError("unsupported weapon mode")
            if not selected.get("damage_dice"):
                raise ActionError("alternate weapon mode requires damage_dice")
            expression = selected["damage_dice"] + (f"{selected.get('damage_modifier', 0):+d}" if selected.get("damage_modifier", 0) else "")
            attack_bonus = selected.get("attack_bonus", profile["attack_bonus"])
            kind = selected.get("damage_type", r.get("damage_type", "SLASHING"))
            reach = selected.get("reach", profile["reach"])
            long_range = selected.get("range_long", profile["range"]["long"])
        else:
            expression = profile["damage_dice"] + (f"{profile['damage_modifier']:+d}" if profile["damage_modifier"] else "")
            attack_bonus = profile["attack_bonus"]
            kind = r.get("damage_type", "SLASHING")
            reach = profile["reach"]
            long_range = profile["range"]["long"]
    reach += r.pop("lunge_reach", 0)
    # Ranged modes still have melee reach, but their legality ceiling is the
    # declared long range.  Keep both values in evidence for the narrator.
    check_target(run, source, target, max(reach, long_range))
    from hollowstar.affix_runtime import offensive_tags, attack_adjustment, damage_resistances
    active_tags = offensive_tags(run, source, {tag.name for tag in a.offensive_tags()})
    if not actor(run,target).gate.is_satisfied_by({DamageTag[tag] for tag in active_tags if tag in DamageTag.__members__}):
        return {"type":"permission_blocked","source":source,"target":target,"tell":actor(run,target).gate.tell}
    if reaction:
        use(run, source, "reaction")
    elif bonus:
        # Doran and Wren carry sourced bonus-action attacks. Anyone else needs
        # a pool declared in their rules and pays it here, so a fixture
        # resident spends a real quantifier rather than getting a free swing.
        pool = r.get("bonus_attack_resource")
        if identity not in {"doran", "wren"} and not pool:
            raise ActionError("no implemented bonus-action weapon")
        use(run, source, "bonus")
        if identity not in {"doran", "wren"}:
            spend(a, pool)
    else:
        e = economy(run, source)
        if not e["attacks"]:
            use(run, source, "action")
            e["attacks"] = r.get("attacks", a.attacks_per_action)
        e["attacks"] -= 1
    if identity == "wren":
        spend(a, "crown_motes")
    defender = actor(run, target)
    aimed = bool(r.pop("aimed", False))
    cover = run.context["combat"]["terrain"]["cover"].get(target)
    if aimed and cover == "half":
        cover = None
    ac = defender.armor_class + {"half": 2, "three_quarters": 5}.get(cover, 0)
    disadv = bool({"BLINDED", "FRIGHTENED", "POISONED", "RESTRAINED", "PRONE"}.intersection(a.statuses))
    disadv |= "DODGING" in defender.statuses or distance(run, source, target) > long_range
    disadv |= "PRONE" in defender.statuses and distance(run, source, target) > 5
    adv = bool({"RESTRAINED", "STUNNED", "PARALYZED"}.intersection(defender.statuses))
    adv |= "PRONE" in defender.statuses and distance(run, source, target) <= 5
    adv |= "INVISIBLE" in a.statuses
    precision_bonus = r.get("precision_bonus",0) + (2 if aimed else 0)
    damage_bonus = r.get("damage_bonus",0)
    attack_bonus += precision_bonus
    adv |= r.get("feint_target")==target or (rules(run,target).get("distracted_by") not in {None,source})
    # D&D Help: an ally's aid grants advantage on this actor's next attack
    # against the named foe, and is spent by that roll.
    helped = r.get("help_advantage")
    if isinstance(helped, dict) and helped.get("target") == target:
        adv = True
        r.pop("help_advantage", None)
    else:
        helped = None
    disadv |= rules(run,source).get("goaded_by") not in {None,target}
    glare = None
    if rules(run,target).get("identity") == "doran" and run.context["combat"]["terrain"].get("daylight") \
            and distance(run, source, target) <= 60:
        glare = saving_throw(run, source, "CON", 22)
        if not glare["success"]:
            disadv = True
            if glare.get("total", 22) <= 17:
                actor(run, source).statuses["BLINDED"] = 1
    hit = roll_check(run, attack_bonus, ac, adv, disadv)
    threshold = 16 if identity == "doran" and r.get("read_target") == target and mode != "cleaver" else r.get("critical_min", 20)
    critical = hit["natural"] >= threshold
    hit["success"] = hit["natural"] != 1 and (critical or hit["total"] >= ac)
    event = {"type": "attack", "source": source, "target": target, "mode": mode, "roll": hit, "critical": critical,
             "evidence": {"actor": a.name, "target": defender.name, "range": {"distance": distance(run, source, target),
             "reach": reach, "long": long_range}, "target_ac": ac, "attack_bonus": attack_bonus,
             "permanent_bonuses": {"precision": precision_bonus, "damage": damage_bonus},
             "advantage": adv, "disadvantage": disadv, "critical_threshold": threshold,
             "glare": glare, "help": helped,
             "resources_before": resources_before, "economy_before": economy_before}}
    if hit["success"]:
        if expression == "40":
            amount, rolls = (80 if critical else 40) + damage_bonus, []
        else:
            amount, rolls = dice(run, expression, critical=critical)
            amount += damage_bonus
        sneak = 0
        sneak_rolls = []
        if identity == "custom" and r.get("class_id") == "rogue" and r.get("sneak_attack_round") != run.round_number:
            ally_near = any(other != source and other.startswith(source[0]) and creature.alive
                            and distance(run, other, target) <= 5 for other, creature in actors(run).items())
            if adv or ally_near:
                sneak, sneak_rolls = dice(run, f"{r.get('sneak_attack_dice', 1)}d6", critical=critical)
                amount += sneak; rolls += sneak_rolls; r["sneak_attack_round"] = run.round_number
        if r.pop("feint_target",None)==target:
            extra, extra_rolls=dice(run,"1d12",critical=critical);amount+=extra;rolls+=extra_rolls
        rules(run,target).pop("distracted_by",None)
        event["damage_rolls"] = rolls
        if sneak:
            event["sneak_attack"] = {"damage": sneak, "rolls": sneak_rolls,
                                     "dice": r.get("sneak_attack_dice", 1)}
        event["evidence"]["damage_expression"] = expression
        event["evidence"]["damage_rolls"] = list(rolls)
        defender_rules=rules(run,target)
        if economy(run,target)['reaction'] and conscious(defender) and not reaction:
            eligible_shield=defender_rules.get('identity')=='wren' and defender.resources.get('slot_1_general',0)>0 and not defender_rules.get('shield')
            eligible_parry=defender_rules.get('identity')=='doran' and defender.resources.get('superiority_dice',0)>0 and distance(run,source,target)<=5
            if eligible_shield or eligible_parry:
                window={'kind':'hit','reactor':target,'target':source,'amount':amount,'damage_type':kind,
                        'attack_total':hit['total'],'critical':critical,'bypass':identity=='doran' and mode!='cleaver',
                        'options':['shield'] if eligible_shield else ['parry']}
                run.context['combat']['pending'].append(window)
                event['pending_defense']=window
                return event
        amount, affix_effects, affix_riders = attack_adjustment(run, source, target, amount)
        event["evidence"]["affix_effects"] = affix_effects
        event["evidence"]["offensive_tags"] = sorted(active_tags)
        event["result"] = damage(run, source, target, amount, kind,
                                 bypass_resistance=identity == "doran" and mode != "cleaver",
                                 riders=affix_riders)
        event["evidence"].update({"damage_type": kind, "damage_before_resistance": amount,
                                   "resources_after": dict(a.resources),
                                   "economy_after": copy.deepcopy(economy(run, source)),
                                   "target_hp_after": defender.hp})
        if critical and identity == "doran" and r.get("critical_recovery_round") != run.round_number:
            a.resources["superiority_dice"] = min(16, a.resources.get("superiority_dice", 0)+1)
            r["critical_recovery_round"] = run.round_number
        if mode == "cleaver" and (critical or event["result"]["damage"] >= defender.max_hp/4):
            event["maim"] = True
            rules(run, target)["maimed"] = True
        if mode == "cleaver":
            if not defender.alive:
                event["carry_through"] = _cleaver_carry_through(run, source, target, amount, kind, reach)
            else:
                event["skid"] = _cleaver_skid(run, source, target, amount)
    # A persisted reaction window is offered; no UI decides it independently.
    elif rules(run, target).get("identity") == "doran" and economy(run, target)["reaction"]:
        # A miss is a real persisted reaction window.  Deft Answer remains the
        # default option; Riposte is offered only from this exact miss, never
        # from a caller assertion.
        run.context["combat"]["pending"].append({"kind": "deft_answer", "reactor": target,
                                                   "target": source,
                                                   "options": ["deft_answer", "riposte"]})
    return event


def path_squares(run, key, destination):
    """The grid squares entered walking key to destination. Read-only."""
    start = position(run, key)
    length = max(abs(start[i]-destination[i]) for i in range(3))
    if not length:
        return []
    steps = max(1, length//5)
    return [[round(start[i]+(destination[i]-start[i])*s/steps) for i in range(3)] for s in range(1, steps+1)]


def move_cost(run, key, destination):
    """Feet a legal move would spend, or None when the move cannot be made.

    Read-only, and the one place the price of a square is computed; move()
    below charges what this returns. A chooser that sizes its own step must
    ask here rather than assume five feet per square: difficult terrain and
    PRONE both change the price, and a deterministic chooser that guesses
    wrong proposes a move the rules must refuse, then proposes it forever.
    """
    if not isinstance(destination, list) or len(destination) != 3:
        return None
    if any(type(v) is not int or not 0 <= v <= 120 or v % 5 for v in destination):
        return None
    a, r = actor(run, key), rules(run, key)
    if {"GRAPPLED", "RESTRAINED"}.intersection(a.statuses) or r.get("planted"):
        return None
    if destination[2] and not r.get("fly_speed") and not (r.get("identity") == "doran" and destination[2] <= 20):
        return None
    terrain = run.context["combat"]["terrain"]
    path = path_squares(run, key, destination)
    if any(p in terrain["blocked"] for p in path):
        return None
    cost = sum(5 if "DASHING" in a.statuses or p not in terrain["difficult"] else 10 for p in path)
    return cost*2 if "PRONE" in a.statuses else cost


def move(run, key, destination):
    if not isinstance(destination, list) or len(destination) != 3:
        raise ActionError("destination must be [x,y,z] feet")
    for value in destination:
        number(value, "coordinate", 0, 120)
        if value % 5:
            raise ActionError("coordinates must lie on the 5-foot grid")
    state = run.context["combat"]
    a, r = actor(run, key), rules(run, key)
    if r.get("contained_by"):
        raise ActionError("movement is blocked by forcecage; use an authored escape")
    origin = list(position(run, key))
    if {"GRAPPLED", "RESTRAINED"}.intersection(a.statuses) or r.get("planted"):
        raise ActionError("movement is restrained")
    if destination[2] and not r.get("fly_speed") and not (r.get("identity") == "doran" and destination[2] <= 20):
        raise ActionError("no flight permission")
    ceiling = state["terrain"].get("ceiling_z")
    if ceiling is not None and destination[2] > ceiling:
        raise ActionError("destination is above the room ceiling")
    cost = move_cost(run, key, destination)
    if cost is None:
        raise ActionError("movement path is obstructed")
    if cost > economy(run, key)["movement"]:
        raise ActionError("not enough movement")
    reactions = []
    for other in actors(run):
        if same_side(other, key) or not conscious(actor(run, other)):
            continue
        if distance(run, other, key) <= 5 and max(abs(position(run, other)[i]-destination[i]) for i in range(3)) > 5:
            if key not in rules(run,other).get("declined_targets",[]) and economy(run, other)["reaction"] and not r.get("mobile") and ("DISENGAGED" not in a.statuses or rules(run, other).get("identity") == "doran"):
                reactions.append({"kind": "opportunity", "reactor": other, "target": key,
                                  "options": ["opportunity"] + (["brace"] if rules(run, other).get("identity") == "doran" else [])})
        elif rules(run, other).get("identity") == "doran" and distance(run, other, key) > 5 \
                and max(abs(position(run, other)[i]-destination[i]) for i in range(3)) <= 5 \
                and economy(run, other)["reaction"]:
            reactions.append({"kind":"brace","reactor":other,"target":key,"options":["brace"]})
    if reactions:
        state["pending"].extend(reactions)
        state["pending_movement"]={"actor":key,"destination":list(destination),"cost":cost,
                                   "origin":origin,"path":path_squares(run,key,destination)}
        return {"type": "movement_pending", "windows": reactions, "destination": destination,
                "evidence": {"actor": a.name, "origin": origin, "destination": list(destination),
                "path": path_squares(run, key, destination), "cost": cost,
                "movement_before": economy(run, key)["movement"], "reaction_windows": reactions}}
    movement_before = economy(run, key)["movement"]
    economy(run, key)["movement"] -= cost
    state["positions"][key] = destination
    return {"type": "movement", "actor": key, "destination": destination, "cost": cost,
            "evidence": {"actor": a.name, "origin": origin, "destination": list(destination),
            "path": path_squares(run, key, destination), "cost": cost,
            "movement_before": movement_before, "movement_after": economy(run, key)["movement"],
            "reaction_windows": []}}


# --- Contextual D&D actions -------------------------------------------------
# Shove, trip, and grapple replace one attack of the Attack action (2014 PHB
# "Making an Attack"), so a four-attack Steward can shove and still swing
# three times. Help and Break free spend the whole action.

SIZE_ORDER = ("tiny", "small", "medium", "large", "huge", "gargantuan")
SKILL_ABILITIES = {"Athletics": "STR", "Acrobatics": "DEX"}

# One public catalog: labels, cost, category, and the help text the clients
# print. Legality is still decided by the transitions below, never here.
ACTION_HELP = {
    "attack": ("Attack", "standard", "attack",
               "Make a weapon attack against a visible foe in reach or range."),
    "cast": ("Cast a spell", "standard", "action",
             "Cast a known spell; its cost, range, and targets follow the spell."),
    "move": ("Move", "movement", "movement",
             "Move on the 5-foot grid. Leaving a foe's reach can provoke an opportunity attack."),
    "dash": ("Dash", "standard", "action", "Gain extra movement equal to your speed this turn."),
    "dodge": ("Dodge", "standard", "action",
              "Until your next turn, attacks against you roll with disadvantage."),
    "disengage": ("Disengage", "standard", "action",
                  "Your movement this turn does not provoke opportunity attacks."),
    "shove": ("Shove", "tactical", "attack",
              "Replaces one attack. Your Athletics against the target's Athletics or Acrobatics; "
              "win and it is pushed 5 feet away."),
    "trip": ("Trip", "tactical", "attack",
             "Replaces one attack. The same contest as a shove; win and the target is knocked prone."),
    "grapple": ("Grapple", "tactical", "attack",
                "Replaces one attack. Your Athletics against the target's Athletics or Acrobatics; "
                "win and its speed drops to 0 until it breaks free."),
    "escape_grapple": ("Break free", "tactical", "action",
                       "Use your action to contest your way out of a grapple."),
    "help": ("Assist an ally", "tactical", "action",
             "Aid an ally against a foe within 5 feet of you: their next attack on it has advantage."),
    "stand": ("Stand up", "movement", "movement", "Spend half your speed to rise from prone."),
    "end_turn": ("End turn", "turn", "free", "Finish your turn. Unspent actions are lost."),
}


def _size_rank(run, key):
    size = str(rules(run, key).get("size", "medium")).lower()
    return SIZE_ORDER.index(size) if size in SIZE_ORDER else SIZE_ORDER.index("medium")


def skill_check_bonus(run, key, skill):
    """Sheet skill bonus (or the governing ability modifier) plus Rune skill modifiers."""
    a = actor(run, key)
    bonus = a.skill_bonuses.get(skill, a.skill_bonuses.get(skill.lower()))
    if bonus is None:
        bonus = a.ability_modifier(SKILL_ABILITIES.get(skill, "STR"))
    from hollowstar.affix_runtime import skill_bonus
    return int(bonus) + skill_bonus(run, key, skill)


def _best_skill(run, key, skills):
    return max(((skill, skill_check_bonus(run, key, skill)) for skill in skills), key=lambda row: row[1])


def contest(run, active, active_skills, passive, passive_skills):
    """An opposed check. The active side must beat the passive total; a tie
    leaves the situation unchanged, as in the PHB."""
    active_skill, active_bonus = _best_skill(run, active, active_skills)
    passive_skill, passive_bonus = _best_skill(run, passive, passive_skills)
    active_roll = roll_check(run, active_bonus, 0)
    passive_roll = roll_check(run, passive_bonus, 0)
    success = active_roll["total"] > passive_roll["total"]
    strip = lambda roll: {k: roll[k] for k in ("rolls", "natural", "bonus", "total")}
    return success, {"active": {"actor": active, "skill": active_skill, **strip(active_roll)},
                     "passive": {"actor": passive, "skill": passive_skill, **strip(passive_roll)},
                     "winner": active if success else passive}


def _spend_attack(run, key):
    """Spend one attack of the Attack action, opening the action if needed."""
    e = economy(run, key)
    if not e["attacks"]:
        use(run, key, "action")
        e["attacks"] = rules(run, key).get("attacks", actor(run, key).attacks_per_action)
    e["attacks"] -= 1


def _contact_check(run, key, target):
    """Shove/trip/grapple legality: a living creature within 5 ft, at most one size larger."""
    if not isinstance(target, str) or target == key:
        raise ActionError("choose another creature as the target")
    check_target(run, key, target, 5, enemy=not same_side(key, target))
    if _size_rank(run, target) > _size_rank(run, key) + 1:
        raise ActionError("target is more than one size larger")


def shove(run, key, target, mode="push"):
    """Shove a creature 5 ft away (push) or knock it prone (trip)."""
    if mode not in {"push", "prone"}:
        raise ActionError("shove mode must be push or prone")
    _contact_check(run, key, target)
    _spend_attack(run, key)
    success, check = contest(run, key, ("Athletics",), target, ("Athletics", "Acrobatics"))
    kind = "trip" if mode == "prone" else "shove"
    event = {"type": kind, "actor": key, "target": target, "mode": mode, "contest": check,
             "success": success, "evidence": {"contest": check, "replaces_attack": True,
                                              "economy_after": copy.deepcopy(economy(run, key))}}
    if not success:
        event["outcome"] = "resisted"
        return event
    consequence = "PRONE" if mode == "prone" else "DISPLACEMENT"
    threshold = threshold_immunity(run, target, consequence)
    if threshold:
        event.update({"outcome": "refused", "threshold": threshold, "tell": threshold["tell"]})
        return event
    if mode == "prone":
        # Prone lasts until the target spends movement to stand.
        event["condition"] = condition(run, target, "PRONE", 10000)
        event["outcome"] = "prone" if event["condition"]["applied"] else "refused"
        if event["condition"].get("tell"):
            event["tell"] = event["condition"]["tell"]
        return event
    from hollowstar.lattice import denies
    denial = denies(run, target, "DISPLACEMENT")
    if denial or rules(run, target).get("planted"):
        event.update({"outcome": "refused", "reason": "consequence denied" if denial else "planted",
                      "tell": denial["tell"] if denial else "The target is planted and does not move."})
        return event
    axis, sign = _line_axis(run, key, target)
    before = list(position(run, target))
    after = list(before)
    after[axis] = max(0, min(120, after[axis] + 5 * sign))
    terrain = run.context["combat"]["terrain"]
    occupied = [k for k in actors(run) if k != target and actor(run, k).alive and position(run, k) == after]
    if after == before or after in terrain.get("blocked", []) or occupied:
        event.update({"outcome": "obstructed", "push": {"from": before, "to": before}})
        return event
    run.context["combat"]["positions"][target] = after
    event.update({"outcome": "pushed", "push": {"from": before, "to": after, "feet": 5}})
    return event


def grapple(run, key, target):
    _contact_check(run, key, target)
    _spend_attack(run, key)
    success, check = contest(run, key, ("Athletics",), target, ("Athletics", "Acrobatics"))
    event = {"type": "grapple", "actor": key, "target": target, "contest": check, "success": success,
             "evidence": {"contest": check, "replaces_attack": True,
                          "economy_after": copy.deepcopy(economy(run, key))}}
    if not success:
        event["outcome"] = "resisted"
        return event
    # Ten rounds is the engine's existing grapple horizon (Grappling Strike);
    # Break free, a released grip, or distance ends it sooner.
    applied = condition(run, target, "GRAPPLED", 10)
    event["condition"] = applied
    if applied.get("applied"):
        rules(run, target)["grappled_by"] = key
        rules(run, key)["grappling"] = target
        event["outcome"] = "grappled"
    else:
        event["outcome"] = "refused"
        if applied.get("tell"):
            event["tell"] = applied["tell"]
    return event


def _release_grapple(run, target):
    grappler = rules(run, target).pop("grappled_by", None)
    actor(run, target).statuses.pop("GRAPPLED", None)
    if grappler and rules(run, grappler).get("grappling") == target:
        rules(run, grappler).pop("grappling", None)
    return grappler


def escape_grapple(run, key):
    a = actor(run, key)
    if "GRAPPLED" not in a.statuses:
        raise ActionError("not grappled")
    use(run, key, "action")
    grappler = rules(run, key).get("grappled_by")
    event = {"type": "escape_grapple", "actor": key, "grappler": grappler}
    if grappler and actor(run, grappler).alive and conscious(actor(run, grappler)):
        success, check = contest(run, key, ("Athletics", "Acrobatics"), grappler, ("Athletics",))
        event.update({"contest": check, "success": success, "evidence": {"contest": check}})
    else:
        success = True
        event.update({"success": True, "evidence": {"grip_lost": True}})
    if success:
        _release_grapple(run, key)
        event["outcome"] = "escaped"
    else:
        event["outcome"] = "held"
    return event


def help_action(run, key, target, ally=None):
    """D&D Help in combat: the aided ally has advantage on its next attack
    against a foe within 5 ft of the helper, until the helper's next turn."""
    check_target(run, key, target, 5, enemy=True)
    candidates = [k for k, v in actors(run).items() if same_side(k, key) and k != key and v.alive]
    if ally is None:
        ally = min(candidates, key=lambda k: (distance(run, k, target), k), default=None)
    if ally not in candidates:
        raise ActionError("Help needs another living ally to aid")
    use(run, key, "action")
    rules(run, ally)["help_advantage"] = {"target": target, "from": key, "round": run.round_number}
    return {"type": "help", "actor": key, "ally": ally, "target": target,
            "evidence": {"advantage_granted_to": ally, "against": target,
                         "expires": "on the aided attack or at the start of the helper's next turn"}}


def contextual_actions(run, key):
    """What this actor could legally attempt right now, with public help text.

    Availability is a projection for clients; every transition re-checks its
    own legality, so a stale row can never force an illegal action.
    """
    state = run.context.get("combat") or {}
    rows = []
    a, r = actor(run, key), rules(run, key)
    e = state.get("economy", {}).get(key, {})
    my_turn = not state.get("complete") and state.get("order") and current(run) == key and not state.get("pending")
    alive_foes = [k for k, v in actors(run).items() if not same_side(k, key) and v.alive]
    adjacent = [k for k in alive_foes if distance(run, key, k) <= 5 and _size_rank(run, k) <= _size_rank(run, key) + 1]
    allies = [k for k, v in actors(run).items() if same_side(k, key) and k != key and v.alive]
    has_attack = bool(e.get("action") or e.get("attacks"))
    cunning = bool(r.get("cunning_action"))
    for action_id, (label, category, cost, text) in ACTION_HELP.items():
        reason, targets = None, []
        if action_id == "end_turn":
            pass
        elif not my_turn:
            reason = "It is not this actor's turn."
        elif not conscious(a):
            reason = "Incapacitated; end the turn."
        elif action_id == "attack":
            targets = alive_foes
            if not (has_attack or (e.get("bonus") and r.get("identity") == "wren")):
                reason = "No attack remains this turn."
        elif action_id in {"shove", "trip", "grapple"}:
            targets = adjacent
            if not has_attack:
                reason = "No attack remains this turn."
            elif not adjacent:
                reason = "No foe within 5 feet that is at most one size larger."
        elif action_id == "help":
            targets = [k for k in alive_foes if distance(run, key, k) <= 5]
            if not e.get("action"):
                reason = "Your action is spent."
            elif not targets:
                reason = "No foe within 5 feet to help against."
            elif not allies:
                reason = "No ally to aid."
        elif action_id in {"dash", "disengage"}:
            if not (e.get("action") or (cunning and e.get("bonus"))):
                reason = "Your action is spent."
        elif action_id == "cast" and not (champion_rules.flag(r.get("identity"), "staff_caster")
                                          or (r.get("identity") == "custom" and r.get("class_id") in {"magician", "cleric"})):
            reason = "This profile has no implemented spellcasting."
        elif action_id in {"dodge", "cast"}:
            if not (e.get("action") or (action_id == "cast" and e.get("bonus"))):
                reason = "Your action is spent."
        elif action_id == "escape_grapple":
            if "GRAPPLED" not in a.statuses:
                continue
            if not e.get("action"):
                reason = "Your action is spent."
        elif action_id == "stand":
            if "PRONE" not in a.statuses:
                continue
            if e.get("movement", 0) < a.speed // 2:
                reason = "Standing costs half your speed."
        elif action_id == "move":
            if {"GRAPPLED", "RESTRAINED"}.intersection(a.statuses) or r.get("planted"):
                reason = "Your speed is 0."
            elif not e.get("movement"):
                reason = "No movement remains."
        rows.append({"id": action_id, "label": label, "category": category, "cost": cost, "help": text,
                     "available": reason is None, "reason": reason, "targets": list(targets)})
    return rows


def apply(run, action):
    if not isinstance(action, dict) or not isinstance(action.get("type"), str):
        raise ActionError("action requires a type")
    if 'bonus' in action and type(action['bonus']) is not bool:
        raise ActionError('bonus must be boolean')
    state = run.context.get("combat")
    if not state or state["complete"]:
        raise ActionError("no active combat")
    key = action.get("actor", current(run))
    kind = action["type"]
    a, r = actor(run, key), rules(run, key)
    if kind in {"flight_move", "ascend", "descend"}:
        if r.get("identity") != "wren":
            raise ActionError("only Wren may use flight controls")
        origin = list(position(run, key))
        if kind == "flight_move":
            dx = int(action.get("dx", 0)); dy = int(action.get("dy", 0))
            if dx == 0 and dy == 0:
                raise ActionError("flight movement requires a direction")
            destination = [origin[0] + dx, origin[1] + dy, origin[2]]
        else:
            delta = 5 if kind == "ascend" else -5
            destination = [origin[0], origin[1], origin[2] + delta]
        action = {**action, "type": "move", "destination": destination}
        kind = "move"
    origin_position = list(position(run, key))
    before = {"actor": a.name, "actor_id": key, "hp": a.hp,
              "statuses": dict(a.statuses), "resources": dict(a.resources),
              "economy": copy.deepcopy(state["economy"].get(key, {}))}
    if state["surprised"].get(key) and kind != "end_turn":
        raise ActionError("surprised actors must end their first turn")
    if kind in {"reaction", "decline_reaction", "legendary", "staff_absorb", "domain_reaction"}:
        windows = [w for w in state["pending"] if w["reactor"] == key]
        if not windows:
            raise ActionError("no eligible reaction window")
        window = windows[0]
        if window['kind']=='hit':
            remaining=window['amount']
            if kind!='decline_reaction':
                defense=action.get('defense')
                if defense not in window['options']:raise ActionError('choose an eligible defense')
                use(run,key,'reaction')
                if defense=='shield':
                    spend(a,'slot_1_general');a.armor_class=r['base_ac']+5;r['shield']=True
                    if not window['critical'] and window['attack_total']<a.armor_class:remaining=0
                else:
                    spend(a,'superiority_dice');reduction,rolls=dice(run,'1d12+3');remaining=max(0,remaining-reduction)
            result={'type':'defense','defense':action.get('defense','declined'),
                    'result':damage(run,window['target'],key,remaining,window['damage_type'],bypass_resistance=window['bypass'])}
        elif kind == "decline_reaction":
            # Declining this movement window suppresses repeat offers this turn.
            r.setdefault("declined_targets",[]).append(window["target"])
            result = {"type": "declined", "actor": key}
        elif window['kind']=='spell' and kind=='staff_absorb':
            use(run,key,'reaction')
            result=staff_absorb(run,key,window['spell_level'])
            result['source']=window['source'];result['pending_window']=window
        elif window['kind']=='save' and kind=='domain_reaction':
            if window.get('feature') != 'Aura of the Unbound': raise ActionError('invalid domain reaction')
            from hollowstar.domains import apply as domain
            result=domain(run,key,{'feature':'Aura of the Unbound','target':window['target'],
                                   'failed_save':window['failed_save']})
            result['pending_window']=window
        elif window['kind']=='legendary':
            from hollowstar.monsters import act as monster_act
            result=monster_act(run,key,action,legendary=True)
        elif window['kind'] in {'opportunity','brace'} and action.get('defense')=='brace':
            if r.get('identity')!='doran': raise ActionError('Brace is Doran-only')
            spend(a,'superiority_dice')
            result=weapon_attack(run,key,window['target'],reaction=True)
            if result.get('roll',{}).get('success'):
                value,rolls=dice(run,'1d12',critical=result.get('critical',False))
                result['brace_damage']=damage(run,key,window['target'],value,'PIERCING',bypass_resistance=True)
                result['brace_rolls']=rolls
        elif window['kind'] == 'deft_answer':
            defense = action.get('defense', 'deft_answer')
            if defense not in window.get('options', ['deft_answer']):
                raise ActionError('choose an eligible miss reaction')
            if defense == 'riposte':
                if r.get('identity') != 'doran':
                    raise ActionError('Riposte is Doran-only')
                spend(a, 'superiority_dice')
                result = weapon_attack(run, key, window['target'], mode='dagger', reaction=True)
                if result.get('roll', {}).get('success'):
                    value, rolls = dice(run, '1d12', critical=result.get('critical', False))
                    result['riposte_damage'] = damage(run, key, window['target'], value,
                                                       'PIERCING', bypass_resistance=True)
                    result['riposte_rolls'] = rolls
                result['feature'] = 'Riposte'
            else:
                result = weapon_attack(run, key, window['target'], mode='dagger', reaction=True)
                result['feature'] = 'Deft Answer'
        else:
            result = weapon_attack(run, key, window["target"], reaction=True)
            if window["kind"] == "opportunity" and r.get("identity") == "doran" and result["roll"]["success"]:
                economy(run, window["target"])["movement"] = 0
        state["pending"].remove(window)
        pending_movement=state.get("pending_movement")
        if pending_movement and not any(w.get('kind') in {'opportunity','brace'}
                                       and w.get('target')==pending_movement['actor']
                                       for w in state['pending']):
            mover=pending_movement['actor']
            if actor(run,mover).alive:
                economy(run,mover)['movement']-=pending_movement['cost']
                state['positions'][mover]=list(pending_movement['destination'])
                movement={'actor':mover,'destination':list(pending_movement['destination']),
                          'cost':pending_movement['cost']}
                committed=True
            else:
                movement={'actor':mover,'cancelled':'actor defeated'}
                committed=False
            result={'type':'reaction_and_movement','reaction':result,'movement':movement,
                    'evidence':{'movement_committed_after_reaction':committed,
                                'origin':pending_movement['origin'],'path':pending_movement['path']}}
            state.pop('pending_movement',None)
    else:
        if state["pending"]:
            raise ActionError("resolve or decline pending reactions first")
        if key != current(run):
            raise ActionError("not this actor's turn")
        if kind == "end_concentration":
            old=end_concentration(run,key)
            result={"type":"concentration_ended","actor":key,"spell":old.get("spell") if old else None,
                    "removed_conditions":list(old.get("conditions",[])) if old else [],
                    "evidence":{"concentration_before":old,"state_change":"concentration ended"}}
        elif kind == "end_turn":
            result = finish_turn(run)
        elif not conscious(a):
            raise ActionError("actor cannot act; end the turn")
        elif kind == "attack":
            result = weapon_attack(run, key, action.get("target"), action.get("mode", r.get("loadout", "weapon")), bonus=action.get("bonus", False))
        elif kind == "move":
            result = move(run, key, action.get("destination"))
        elif kind in {"dodge", "disengage", "dash"}:
            cunning = kind in {"disengage", "dash"} and r.get("cunning_action")
            use(run, key, "bonus" if cunning else "action")
            if kind == "dash":
                economy(run, key)["movement"] += a.speed
                a.statuses["DASHING"] = 1
            else:
                a.statuses["DODGING" if kind == "dodge" else "DISENGAGED"] = 1
            result = {"type": kind, "actor": key}
            if cunning: result["cunning_action"] = True
        elif kind == "aim":
            if not r.get("aim") or economy(run,key)["movement"] != a.speed:
                raise ActionError("Aim requires an Archer who has not moved")
            use(run,key,"bonus"); r["aimed"] = True
            result={"type":"aim","actor":key,"attack_bonus":2,"ignores":"half cover"}
        elif kind == "stand":
            if "PRONE" not in a.statuses or economy(run,key)["movement"] < a.speed//2:
                raise ActionError("cannot stand")
            economy(run,key)["movement"] -= a.speed//2
            del a.statuses["PRONE"]
            result = {"type": "stand", "actor": key}
        elif kind == "action_surge":
            spend(a,"action_surge")
            economy(run,key)["action"] += 1
            result = {"type": kind, "actor": key}
        elif kind == "indomitable":
            result = indomitable(run, key, action.get("failed_save"))
        elif kind in {"second_wind", "ring_heal", "unearthly_recovery"}:
            use(run,key,"bonus")
            if kind == "ring_heal":
                if r.get("identity") != "doran":
                    raise ActionError("no regeneration ring")
                hp_before=a.hp; a.adjust_hp(16)
                result={"type":"healing","target":key,"healing":a.hp-hp_before}
            elif kind == "unearthly_recovery":
                if r.get("identity") != "wren" or a.hp >= a.max_hp/2:
                    raise ActionError("Unearthly Recovery requires Wren below half HP")
                spend(a,kind); hp_before=a.hp; a.adjust_hp(a.max_hp//2)
                result={"type":"healing","target":key,"healing":a.hp-hp_before,
                        "actor":key,"feature":"unearthly_recovery"}
            else:
                spend(a,kind)
                result=heal(run,key,f"1d10+{r.get('level',20)}")
        elif kind == "arcane_recovery":
            if r.get("class_id") != "magician": raise ActionError("Arcane Recovery is Magician-only")
            use(run,key,"action"); spend(a,"arcane_recovery")
            before_energy=a.resources.get("casting_energy",0)
            restored=(r.get("level",1)+1)//2
            a.resources["casting_energy"]=min(r.get("casting_energy_max",before_energy),before_energy+restored)
            result={"type":"arcane_recovery","actor":key,"restored":a.resources["casting_energy"]-before_energy}
        elif kind == "channel_grace":
            if r.get("class_id") != "cleric": raise ActionError("Channel Grace is Cleric-only")
            target=action.get("target",key); check_target(run,key,target,30,enemy=False)
            use(run,key,"action"); spend(a,"channel_grace")
            wisdom=a.ability_modifier("WIS")
            result=heal(run,target,f"1d8+{max(0,wisdom+r.get('level',1))}")
            result["type"]="channel_grace";result["actor"]=key
        elif kind == "read_seam":
            if r.get("identity") != "doran":
                raise ActionError("Read the Seam is Doran's feature")
            target=action.get("target"); check_target(run,key,target,120)
            use(run,key,"bonus")
            check=roll_check(run,16,actor(run,target).armor_class)
            if check["success"]: r["read_target"]=target
            result={"type":kind,"roll":check,"target":target}
        elif kind == "stance":
            if r.get("identity") != "doran" or action.get("stance") not in {"planted","mobile","kite","recover_kite"}:
                raise ActionError("unsupported stance")
            stance=action["stance"]
            if stance in {"planted","mobile"}:
                r["planted"]=stance=="planted"
                r["mobile"]=stance=="mobile"
                if r["planted"]: economy(run,key)["movement"]=0
            else:
                r["base_ac"]=21 if stance=="kite" else 25; a.armor_class=r["base_ac"]
                target=action.get("target",key)
                check_target(run,key,target,5,enemy=False)
                if stance=="kite": state["terrain"]["cover"][target]="three_quarters"
                else: state["terrain"]["cover"].pop(target,None)
            result={"type":kind,"stance":stance}
        elif kind == "recover_weapon":
            if not r.get("disarmed"):raise ActionError("no disarmed weapon")
            use(run,key,"action");r["disarmed"]=False
            result={"type":"recover_weapon","actor":key}
        elif kind == "monster":
            from hollowstar.monsters import act as monster_act
            result=monster_act(run,key,action)
        elif kind == "force_regurgitation":
            from hollowstar.monsters import force_regurgitation
            result=force_regurgitation(run,key,action.get('target'))
        elif kind == "domain":
            from hollowstar.domains import apply as domain
            result=domain(run,key,action)
        elif kind == "maneuver":
            from hollowstar.maneuvers import apply as maneuver
            result=maneuver(run,key,action)
        elif kind == "grand_cleave":
            from hollowstar.maneuvers import grand_cleave
            result=grand_cleave(run,key,action)
        elif kind == "cast":
            from hollowstar.spells import cast
            result=cast(run,key,action)
        elif kind == "staff_cast":
            use(run,key,"action")
            result=staff_cast(run,key,action.get("spell"))
        elif kind == "staff_absorb":
            windows=[w for w in state["pending"] if w["reactor"]==key and w["kind"]=="spell"]
            if not windows: raise ActionError("no incoming single-target spell")
            window=windows[0]; use(run,key,"reaction")
            result=staff_absorb(run,key,window["spell_level"])
            result["source"]=window["source"];result["pending_window"]=window
            state["pending"].remove(window)
        elif kind == "incoming_spell":
            result=incoming_spell(run,action.get("source",key),action.get("target"),action.get("spell_level"))
        elif kind == "incoming_failed_save":
            result=incoming_failed_save(run,action.get("source",key),action.get("target"),action.get("failed_save"))
        elif kind == "staff_retributive_strike":
            use(run,key,"action")
            result=staff_retributive_strike(run,key,action.get("targets"))
        elif kind == "staff_utility":
            use(run,key,"action")
            result=staff_utility(run,key,action.get('mode'),action.get('target'))
        elif kind == "dagger_cut_structure":
            use(run,key,"action")
            result=dagger_cut_structure(run,key,action.get("structure_id"),action.get("mode","thrown"))
        elif kind in {"wings", "fly"}:
            if r.get("identity") != "wren": raise ActionError("no Otherworldly Wings")
            remaining = economy(run,key)["movement"]
            old_speed = r.get("fly_speed", a.speed)
            r["fly_speed"]=60
            economy(run,key)["movement"] = remaining * 60 // old_speed
            result={"type":"wings","speed":60}
        elif kind == "land":
            if r.get("identity") != "wren": raise ActionError("no wings to land")
            if position(run,key)[2] > 0:
                raise ActionError("descend to ground level before landing")
            old_speed = r.get("fly_speed", a.speed)
            economy(run,key)["movement"] = economy(run,key)["movement"] * a.speed // old_speed
            r.pop("fly_speed", None)
            result={"type":"land"}
        elif kind in {"shove", "trip"}:
            mode = "prone" if kind == "trip" else action.get("mode", "push")
            result = shove(run, key, action.get("target"), mode)
        elif kind == "grapple":
            result = grapple(run, key, action.get("target"))
        elif kind in {"escape_grapple", "break_free"}:
            result = escape_grapple(run, key)
        elif kind == "help":
            result = help_action(run, key, action.get("target"), action.get("ally"))
        else:
            raise ActionError(f"RULING_REQUIRED: {kind} has no executable rule")
    if run.finished():
        state["complete"]=True
        for k in actors(run):
            if rules(run,k).get("identity")=="wren": actor(run,k).resources["ward"]=75
    if isinstance(result, dict) and "evidence" not in result:
        after = {"hp": a.hp, "statuses": dict(a.statuses),
                 "resources": dict(a.resources),
                 "economy": copy.deepcopy(state["economy"].get(key, {}))}
        result["evidence"] = {
            "actor": before["actor"], "actor_id": key,
            "target": action.get("target"), "action": kind,
            "before": before, "after": after,
            "state_changes": {
                "hp": after["hp"] - before["hp"],
                "statuses_changed": after["statuses"] != before["statuses"],
                "resources_changed": after["resources"] != before["resources"],
                "economy_changed": after["economy"] != before["economy"],
            },
        }
    if isinstance(result, dict):
        target_key = action.get("target") or (action.get("targets") and action["targets"][0])
        target_position = list(position(run, target_key)) if target_key in state["positions"] else None
        final_position = list(position(run, key))
        result["presentation"] = {
            "schema": "hsr-presentation-1",
            "actor_id": key,
            "action": kind,
            "origin": origin_position,
            "destination": final_position,
            "target_id": target_key,
            "target_position": target_position,
            "animation": {
                "attack": _attack_animation(a) if kind in {"attack", "shove", "trip", "grapple"} else None,
                "move": "run" if kind in {"move", "dash", "disengage"} else None,
                "defense": "block" if kind in {"block", "brace", "guard"} else None,
                "dodge": "dodge" if kind == "dodge" else None,
                "cast": "cast" if kind in {"cast", "staff_cast", "domain"} else None,
                "flight": "fly" if kind in {"wings", "fly"} else None,
            },
            "loadout": _actor_loadout_presentation(a),
            "steps": [
                {"type": "move_to", "position": final_position, "duration_ms": 360}
                if final_position != origin_position else {"type": "hold_position"},
                {"type": "play_animation", "animation": kind},
                {"type": "resolve_hit", "target_id": target_key}
                if target_key else {"type": "hold_position"},
            ],
        }
        if isinstance(result.get("evidence"), dict):
            result["evidence"]["presentation"] = copy.deepcopy(result["presentation"])
    state["events"].append(copy.deepcopy(result))
    return result


def _view_contextual(run):
    """Contextual catalog for the party actor whose turn it is, else empty."""
    state = run.context["combat"]
    if state.get("complete") or not state.get("order"):
        return []
    key = current(run)
    if not key.startswith("p"):
        return []
    return contextual_actions(run, key)


def combat_effects(run, key):
    """Derive the effect rack from live host state; never a second mechanics store.

    No mechanical cap: ten is the screen's rack size, not permission to drop
    an eleventh condition or equipped rule. Timers retain their engine unit.
    """
    from hollowstar.explanations import public_effect
    a = actor(run, key)
    state = run.context["combat"]
    rows = []
    for name, remaining in a.statuses.items():
        if remaining <= 0:
            continue
        row = {"id": f"condition:{name}", "name": name.replace("_", " ").title(),
               "kind": "condition", "status": "active", "duration": "turn",
               "remaining": remaining, "timer_actor": key,
               "summary": f"{name.replace('_', ' ').title()}: {remaining} affected turns remaining"}
        for owner, concentration in state.get("concentration", {}).items():
            if key in concentration.get("targets", []) and name in concentration.get("conditions", []):
                row["source"] = {"kind": "spell", "id": owner, "name": concentration.get("spell", "Concentration")}
                break
        rows.append(row)
    # Keep caster concentration visible even when its targets are other actors.
    for owner, concentration in state.get("concentration", {}).items():
        if owner != key and (key not in concentration.get("targets", []) or concentration.get("conditions")):
            continue
        spell = concentration.get("spell", "Concentration")
        summary = "Concentrating" if owner == key else "Concentration maintained by caster"
        from hollowstar.spells import catalog
        if catalog(run).get(spell, {}).get("operation") == "utility":
            summary += "; secondary spell effects are recorded only"
        rows.append({"id": f"concentration:{owner}:{spell}", "name": spell,
                     "kind": "concentration", "status": "active", "duration": "concentration",
                     "remaining": concentration.get("remaining"), "timer_actor": owner,
                     "source": {"kind": "actor", "id": owner, "name": actor(run, owner).name},
                     "summary": summary})
    r = rules(run, key)
    if r.get("shield"):
        rows.append({"id": "temporary:shield", "name": "Shield", "kind": "buff",
                     "status": "active", "duration": "turn", "timer_actor": key,
                     "summary": "Active until this actor's next turn"})
    if r.get("help_advantage"):
        helper = r["help_advantage"].get("from")
        rows.append({"id": "temporary:help", "name": "Help", "kind": "buff",
                     "status": "active", "duration": "turn", "timer_actor": helper,
                     "summary": "Advantage on the next attack; ends at helper's next turn"})
    # Enemy loadouts stay hidden. Their applied conditions/concentration are
    # visible, but private equipment properties are not revealed by the rack.
    if key.startswith("p"):
        for index, effect in enumerate(a.inherent):
            if effect.is_exhausted():
                continue
            row = public_effect(effect, source={"kind": "actor", "id": key, "name": a.name})
            row.update(id=f"inherent:{key}:{index}:{row['id']}", kind="inherent")
            rows.append(row)
        for slot, item in enumerate(a.equipment):
            public = public_item(item)
            for index, row in enumerate(public.get("effect_explanations", [])):
                if row.get("status") != "active":
                    continue
                row.update(id=f"equipment:{key}:{slot}:{index}:{row['id']}", kind="equipment")
                rows.append(row)
    return rows


def formation(run):
    """Side-view battle line-up: engine-owned rows so clients never guess placement.

    Reach decides the row: a combatant whose longest reach exceeds 30 feet,
    or a caster identity, stands in the back row. Slots count within a row.
    """
    layout, counts = {}, {}
    for key in actors(run):
        side = "party" if key.startswith("p") else "enemy"
        reach = (rules(run, key).get("range") or [5, 5])[-1]
        back = is_wren(rules(run, key).get("identity")) or (isinstance(reach, int) and reach > 30)
        row = "back" if back else "front"
        slot = counts.get((side, row), 0)
        counts[(side, row)] = slot + 1
        layout[key] = {"side": side, "row": row, "slot": slot}
    return layout


def view(run):
    state=run.context["combat"]
    bands = {}
    for key, coords in state["positions"].items():
        z = coords[2]
        bands[key] = "grounded" if z <= 0 else "low" if z <= 20 else "high" if z <= 60 else "extreme"
    return {"round":run.round_number,"current":None if state["complete"] else current(run),
            "order":list(state["order"]),"positions":copy.deepcopy(state["positions"]),
            "formation":formation(run),
            "display_capacity":{"combatants":8,"effect_slots":10},
            "height_bands":bands,
            "surprised":dict(state["surprised"]),
            "economy":copy.deepcopy(state["economy"]),"pending":copy.deepcopy(state["pending"]),
            "pending_movement":copy.deepcopy(state.get("pending_movement")),
            "concentration":copy.deepcopy(state["concentration"]),"complete":state["complete"],
            "condition_categories":copy.deepcopy(CONDITION_CATEGORIES),
            "turn_zero":copy.deepcopy(state.get("turn_zero", [])),
            "contextual_actions":_view_contextual(run),
            "actors":{k:{"name":a.name,"identity":rules(run,k).get("identity", a.name.lower()),
                         "hp":a.hp,"max_hp":a.max_hp,"ac":a.armor_class,
                         "position":copy.deepcopy(state["positions"].get(k)),
                         "economy":copy.deepcopy(state["economy"].get(k, {})),
                         "ability_scores":dict(a.ability_scores),
                         "ability_modifiers":{name:a.ability_modifier(name) for name in a.ability_scores},
                         "proficiency_bonus":a.proficiency_bonus,
                         "skill_bonuses":dict(a.skill_bonuses),
                         "spell_save_dc":rules(run,k).get("spell_save_dc",22 if is_wren(rules(run,k).get("identity")) else None),
                         "spell_attack_bonus":rules(run,k).get("spell_attack_bonus",14 if is_wren(rules(run,k).get("identity")) else None),
                         "initiative_bonus":a.initiative_bonus,"speed":a.speed,
                         "statuses":dict(a.statuses),"resources":dict(a.resources),
                         "active_effects":combat_effects(run,k),
                         "equipment":[public_item(item) for item in a.equipment] if k.startswith("p") else []} for k,a in actors(run).items()}}
