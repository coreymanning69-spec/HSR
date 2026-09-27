"""Deliberate DESIGN-fixture combat. All adapters call these transitions.

Runtime-pair numbers come from the frozen run's source snapshot. This module
does not claim complete Steward fidelity. Unsupported actions fail explicitly.
"""
from __future__ import annotations

import copy
import math
import re
from functools import lru_cache

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


# Status definitions live in content/statuses.json (see statuses.py); these
# names stay importable from here for the modules that already use them.
from hollowstar import statuses
from hollowstar.statuses import CONDITIONS, CONDITION_CATEGORIES, INCAPACITATING, MENTAL_CONDITIONS

# Doran's Grand Cleave flat-damage expression (sourced: DM044_0).
# maneuvers.grand_cleave() also uses this via import so the value lives in one place.
DORAN_CLEAVER_FLAT_DAMAGE: str = "40"


def condition_category(name):
    return CONDITION_CATEGORIES.get(name, "unknown")


def number(value, label, low=0, high=10000):
    if type(value) is not int or not low <= value <= high:
        raise ActionError(f"{label} must be an integer in {low}..{high}")
    return value


_DICE_EXPRESSION = re.compile(r"(\d{1,3})d(4|6|8|10|12|20)([+-]\d+)?")


def dice_terms(expression):
    """(count, sides, modifier) for anything dice() accepts; a flat amount is (0, 0, n)."""
    if isinstance(expression, int) and not isinstance(expression, bool):
        if expression < 0:
            raise ActionError(f"unsupported dice expression: {expression}")
        return 0, 0, expression
    if isinstance(expression, str) and expression.isdigit():
        return 0, 0, int(expression)
    match = _DICE_EXPRESSION.fullmatch(expression) if isinstance(expression, str) else None
    if not match or not 1 <= int(match[1]) <= 100:
        raise ActionError(f"unsupported dice expression: {expression}")
    return int(match[1]), int(match[2]), int(match[3] or 0)


def dice(run, expression, *, critical=False, maximize=False):
    count, sides, modifier = dice_terms(expression)
    if not sides:
        return modifier, [modifier]
    values = [sides if maximize else run.rng.randint(1, sides) for _ in range(count * (2 if critical else 1))]
    return max(0, sum(values) + modifier), values


# --- Odds ---------------------------------------------------------------------
# The rolls above and below, computed instead of rolled. Planners, gambits and
# previews read these; each mirrors the resolver function its docstring names,
# so a forecast and the roll it predicts cannot disagree. Nothing here touches
# the run's RNG.

def d20_odds(advantage=False, disadvantage=False):
    """P(natural == n) at index n (1..20) for roll_check's d20; index 0 is unused."""
    if advantage and not disadvantage:
        return [0.0] + [(2 * n - 1) / 400 for n in range(1, 21)]
    if disadvantage and not advantage:
        return [0.0] + [(41 - 2 * n) / 400 for n in range(1, 21)]
    return [0.0] + [1 / 20] * 20


def attack_odds(bonus, ac, *, advantage=False, disadvantage=False, threshold=20):
    """weapon_attack's hit rule: a natural 1 misses, a natural at or above the
    critical threshold hits and crits, anything else hits on total >= AC."""
    odds = d20_odds(advantage, disadvantage)
    crit = sum(odds[n] for n in range(max(2, threshold), 21))
    hit = crit + sum(odds[n] for n in range(2, min(threshold, 21)) if n + bonus >= ac)
    return {"hit": hit, "crit": crit, "miss": 1 - hit}


def check_odds(bonus, dc, *, advantage=False, disadvantage=False):
    """P(roll_check succeeds): d20 + bonus >= dc. Saves and checks have no
    natural-1 or natural-20 rule in this engine."""
    odds = d20_odds(advantage, disadvantage)
    return sum(odds[n] for n in range(1, 21) if n + bonus >= dc)


def contest_odds(active_bonus, passive_bonus):
    """P(contest() goes to the active side): it must beat the passive total; a tie holds."""
    return sum(1 for a in range(1, 21) for b in range(1, 21)
               if a + active_bonus > b + passive_bonus) / 400


@lru_cache(maxsize=256)
def _sum_odds(count, sides):
    """Exact distribution of the sum of count dice with sides faces, indexed by sum."""
    dist = [1.0]
    for _ in range(count):
        nxt = [0.0] * (len(dist) + sides)
        window = 0.0
        for total in range(1, len(nxt)):
            if total - 1 < len(dist):
                window += dist[total - 1]
            if total - 1 - sides >= 0:
                window -= dist[total - 1 - sides]
            nxt[total] = max(0.0, window) / sides
        dist = nxt
    return tuple(dist)


def dice_odds(expression, *, critical=False, maximize=False):
    """Exact {total: probability} of what dice() returns for the same arguments."""
    count, sides, modifier = dice_terms(expression)
    if not sides:
        return {modifier: 1.0}
    count *= 2 if critical else 1
    if maximize:
        return {max(0, count * sides + modifier): 1.0}
    out = {}
    for total, p in enumerate(_sum_odds(count, sides)):
        if p > 0:
            key = max(0, total + modifier)
            out[key] = out.get(key, 0.0) + p
    return out


def add_odds(first, second):
    """Distribution of the sum of two independent amounts."""
    out = {}
    for a, p in first.items():
        for b, q in second.items():
            out[a + b] = out.get(a + b, 0.0) + p * q
    return out


def map_odds(odds, transform):
    """Distribution of transform(amount)."""
    out = {}
    for value, p in odds.items():
        key = transform(value)
        out[key] = out.get(key, 0.0) + p
    return out


def mean_odds(odds):
    return sum(value * p for value, p in odds.items())


def odds_at_least(odds, floor):
    return sum(p for value, p in odds.items() if value >= floor)


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


def _save_terms(run, key, ability, magical=False, concentration=False):
    """What saving_throw rolls: None when the creature is contained and makes
    no save, "fail" for an automatic failure, else (bonus, advantage, disadvantage)."""
    a, r = actor(run, key), rules(run, key)
    if r.get("contained_by"):
        return None
    if ability not in a.ability_scores:
        raise ActionError(f"unsupported save: {ability}")
    if ability in {"STR", "DEX"} and {"STUNNED", "PARALYZED"}.intersection(a.statuses):
        return "fail"
    adv = wren_near(run, key) or (magical and champion_rules.flag(r.get("identity"), "mental_save_advantage"))
    adv |= magical and r.get("identity")=="tarrasque"
    adv |= concentration and champion_rules.flag(r.get("identity"), "mental_save_advantage")
    adv |= ability == "DEX" and "HASTED" in a.statuses
    return (r.get("saves", {}).get(ability, a.ability_modifier(ability)), adv,
            ability == "DEX" and "RESTRAINED" in a.statuses)


def saving_throw(run, key, ability, dc, magical=False, concentration=False):
    terms = _save_terms(run, key, ability, magical, concentration)
    if terms is None:
        return None
    if terms == "fail":
        return {"success": False, "automatic": "incapacitated physical save", "dc": dc}
    a, r = actor(run, key), rules(run, key)
    result=roll_check(run, terms[0], dc, terms[1], terms[2])
    if not result['success'] and r.get('identity')=='tarrasque' and a.resources.get('legendary_resistance'):
        spend(a,'legendary_resistance');result['success']=True;result['legendary_resistance']=True
    return result


def save_odds(run, key, ability, dc, magical=False, concentration=False):
    """P(saving_throw succeeds), or None when the creature is contained and makes no save."""
    terms = _save_terms(run, key, ability, magical, concentration)
    if terms is None:
        return None
    if terms == "fail":
        return 0.0
    a, r = actor(run, key), rules(run, key)
    if r.get("identity") == "tarrasque" and a.resources.get("legendary_resistance"):
        return 1.0
    return check_odds(terms[0], dc, advantage=terms[1], disadvantage=terms[2])


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


def condition_refusal(run, key, name, *, mental=False):
    """Why condition() would refuse `name` on key, as its public fields, or None. Read-only."""
    return statuses.first_refusal(run, key, name, mental)


@statuses.refusal
def _refuse_immunity(run, key, name, mental):
    if name in rules(run, key).get("condition_immunities", []):
        return {"reason": "condition immunity"}


@statuses.refusal
def _refuse_indomitable_spirit(run, key, name, mental):
    if rules(run, key).get("spirit_until", 0) > run.round_number and name in {"CHARMED", "FRIGHTENED", "PARALYZED", "RESTRAINED", "STUNNED", "GRAPPLED", "INCAPACITATED", "PETRIFIED"}:
        return {"reason": "Indomitable Spirit"}


@statuses.refusal
def _refuse_mind_lock(run, key, name, mental):
    if rules(run, key).get("identity") == "wren" and (mental or name in MENTAL_CONDITIONS):
        return {"reason": "mind lock"}


@statuses.refusal
def _refuse_unshackled_host(run, key, name, mental):
    if name in {"GRAPPLED", "RESTRAINED", "PARALYZED", "PETRIFIED"} and wren_near(run, key):
        return {"reason": "Unshackled Host"}


@statuses.refusal
def _refuse_planted_prone(run, key, name, mental):
    if rules(run, key).get("planted") and name == "PRONE":
        return {"reason": "planted displacement immunity"}


@statuses.refusal
def _refuse_lattice(run, key, name, mental):
    from hollowstar.lattice import denies
    denial = denies(run, key, name)
    if denial:
        return {"reason": "consequence denied", "lattice": denial, "tell": denial["tell"]}


def condition(run, key, name, duration, *, mental=False):
    if name not in CONDITIONS:
        raise ActionError(f"condition requires implementation: {name}")
    number(duration, "duration", 1, 10000)
    a = actor(run, key)
    refusal = condition_refusal(run, key, name, mental=mental)
    if refusal:
        return {"condition": name, "category": condition_category(name), "applied": False, **refusal}
    a.statuses[name] = duration
    if name in INCAPACITATING:
        end_concentration(run, key)
    statuses.fire("apply", run, key, name)
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


# DM044_0 divine plate: how much of each physical subtype gets through.
DORAN_PLATE = {"PIERCING": .25, "SLASHING": .375, "BLUDGEONING": .75}


def mitigation(run, source, target, damage_type, *, bypass_resistance=False):
    """What happens to one damage instance of damage_type from source to target
    before ward, temporary HP and hit points: its conversion, the tags it
    carries, and which reductions apply. Read-only; damage() applies it through
    mitigate(), and so does every forecast."""
    if damage_type not in DamageTag.__members__:
        raise ActionError(f"damage type requires implementation: {damage_type}")
    r, source_rules = rules(run, target), rules(run, source)
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
    mundane = False
    if is_tarrasque(r.get('identity')) and damage_type in {'PIERCING','SLASHING','BLUDGEONING'} and not (is_doran(source_rules.get('identity')) or is_wren(source_rules.get('identity'))):
        from hollowstar.phases import Tier
        weapon=actor(run,source).weapon()
        mundane = not weapon or weapon.tier==Tier.MUNDANE
    plate = None
    if r.get("identity") == "doran":
        plate = 0 if damage_type in {"FIRE", "ICE"} else DORAN_PLATE.get(armor_damage_type, 1)
    affix_resistances = damage_resistances(run, target)
    return {"printed_type": printed_type, "damage_type": damage_type, "conversions": conversions,
            "source_tags": source_tags, "armor_damage_type": armor_damage_type,
            "mundane_blocked": mundane, "plate": plate,
            "immune": damage_type in r.get("immunities", []),
            "lattice_immunity": lattice.immunity(run, source, target, damage_type),
            "resisted": (damage_type in r.get("resistances", []) or damage_type in affix_resistances)
                        and not bypass_resistance and "DIVINE" not in source_tags,
            "affix_resistances": affix_resistances,
            "vulnerable": damage_type in r.get("vulnerabilities", [])}


# --- Knowledge ----------------------------------------------------------------
# What each side has seen of the creatures it fights, by creature name, so a
# lesson carries to the next room's goblin. Party forecasts price damage from
# this (known_mitigation, informed=False); enemy AI reads the engine's truth.
# It lives in run.context, so it saves, loads and survives between fights.

def knowledge(run, side="p", *, create=False):
    """The ledger for side ("p" or "e"): {"creatures": {name: {"damage": {TYPE: seen}}}}.
    Reading never writes; create=True makes the ledger so it can be recorded to."""
    if create:
        return run.context.setdefault("knowledge", {}).setdefault(side, {"creatures": {}})
    return (run.context.get("knowledge") or {}).get(side) or {"creatures": {}}


def observe_damage(run, source, target, profile):
    """Record what one landed damage instance showed source's side about target."""
    if same_side(source, target):
        return
    outcome = ("immune" if profile["immune"] or profile["lattice_immunity"]
               else "resisted" if profile["resisted"] else "normal")
    creature = knowledge(run, source[0], create=True)["creatures"].setdefault(actor(run, target).name, {"damage": {}})
    creature["damage"][profile["printed_type"]] = {
        "outcome": outcome, "vulnerable": bool(profile["vulnerable"]),
        "converted_to": profile["damage_type"] if profile["conversions"] else None,
        "round": run.round_number}


def known_mitigation(run, source, target, damage_type, *, bypass_resistance=False, informed=True):
    """mitigation(), limited to what source's side has observed when informed
    is False. Unseen damage types are priced as plain hits; plate and the
    Tarrasque's mundane-weapon rule are stat-block facts and stay visible."""
    profile = mitigation(run, source, target, damage_type, bypass_resistance=bypass_resistance)
    if informed or same_side(source, target):
        return profile
    seen = (knowledge(run, source[0])["creatures"].get(actor(run, target).name, {})
            .get("damage", {}).get(damage_type))
    can_resist = not bypass_resistance and "DIVINE" not in profile["source_tags"]
    return {**profile, "lattice_immunity": None, "conversions": [], "damage_type": damage_type,
            "immune": bool(seen) and seen["outcome"] == "immune",
            "resisted": bool(seen) and seen["outcome"] == "resisted" and can_resist,
            "vulnerable": bool(seen) and seen["vulnerable"], "observed": seen is not None}


def mitigate(amount, profile, steps=None):
    """Apply a mitigation() profile to one amount, in the resolver's order.
    When steps is a list, every change is appended to it as {label, amount}."""
    def note(label, before, after):
        if steps is not None and after != before:
            steps.append({"label": label, "amount": after})
        return after
    if profile["mundane_blocked"]:
        amount = note("mundane weapon", amount, 0)
    plate = profile["plate"]
    if plate is not None:
        amount = note(f"divine plate ×{plate:g}" if plate else "divine plate", amount, int(amount * plate))
    if profile["immune"] or profile["lattice_immunity"]:
        amount = note("immune", amount, 0)
    elif profile["resisted"]:
        amount = note("resisted", amount, amount // 2)
    if profile["vulnerable"]:
        amount = note("vulnerable", amount, amount * 2)
    return amount


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
    profile = mitigation(run, source, target, damage_type, bypass_resistance=bypass_resistance)
    printed_type, damage_type = profile["printed_type"], profile["damage_type"]
    source_tags, conversions = profile["source_tags"], profile["conversions"]
    lattice_immunity = profile["lattice_immunity"]
    # Every change between the amount dealt and the hit points lost, in order,
    # so the roll-math readout can show where each point went.
    adjustments = []
    amount = mitigate(amount, profile, adjustments)
    ward = a.resources.get("ward", 0)
    blocked = ward > 0
    if blocked:
        a.resources["ward"] = max(0, ward - amount)
        if amount:
            adjustments.append({"label": "ward", "amount": 0})
        amount = 0
    if raw and not blocked:
        observe_damage(run, source, target, profile)
    temporary = min(a.resources.get("temporary_hp", 0), amount)
    if temporary:
        a.resources["temporary_hp"] -= temporary
        amount -= temporary
        adjustments.append({"label": "temporary HP", "amount": amount})
    before = a.hp
    a.adjust_hp(-amount)
    if before - a.hp != amount:
        adjustments.append({"label": "overkill", "amount": before - a.hp})
    event = {"type": "damage", "source": source, "target": target, "raw": raw,
             "damage_type": damage_type, "damage_tags": sorted(source_tags), "damage": before-a.hp, "ward_before": ward,
             "ward_after": a.resources.get("ward", 0), "riders": [],
             "evidence": {"raw": raw, "damage_type": damage_type,
                          "bypass_resistance": bypass_resistance,
                          "source_tags": sorted(source_tags),
                          "armor_damage_type": profile["armor_damage_type"],
                          "immunity": profile["immune"],
                          "resisted": profile["resisted"],
                          "affix_resistances": sorted(profile["affix_resistances"]),
                          "vulnerable": profile["vulnerable"],
                          "armor_treatment": "doran_divine_plate" if r.get("identity") == "doran" else None,
                          "ward_before": ward, "target_hp_before": before,
                          "adjustments": adjustments}}
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
        # A contained caster makes no save (saving_throw returns None) and
        # keeps concentrating unless the blow drops it.
        if (save is not None and not save["success"]) or not a.alive:
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
    maximized = rules(run, target).get("identity") == "doran"
    amount, rolls = dice(run, expression, maximize=maximized)
    a.adjust_hp(amount)
    adjustments = [] if a.hp - hp_before == amount else [{"label": "max HP", "amount": a.hp - hp_before}]
    return {"type": "healing", "target": target, "rolls": rolls, "healing": a.hp-hp_before,
            "evidence": {"actor": a.name, "expression": expression, "rolls": list(rolls),
                         "rolled": amount, "maximized": maximized, "adjustments": adjustments,
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
        if statuses.decays(name):
            a.statuses[name] -= 1
            statuses.fire("tick", run, key, name)
            if a.statuses[name] <= 0:
                expired_statuses.append(name)
                del a.statuses[name]
                statuses.fire("expire", run, key, name)
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
    for name in statuses.turn_start_cleared():
        a.statuses.pop(name, None)
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


def _target_geometry_problem(run, source, target, maximum, enemy):
    """check_target's rules short of an item's targeting denial, as a reason or None."""
    if not actor(run, target).alive:
        return "target is not alive"
    if same_side(source, target) == enemy and rules(run,source).get("identity")!="tarrasque" and rules(run,target).get("identity")!="tarrasque":
        return "invalid target side"
    if distance(run, source, target) > maximum:
        return "target out of range"
    ceiling = run.context["combat"].get("terrain", {}).get("ceiling_z")
    if ceiling is not None and position(run, source)[2] > ceiling:
        return "source is above the room ceiling"
    if ceiling is not None and position(run, target)[2] > ceiling:
        return "target is above the room ceiling"
    terrain = run.context["combat"]["terrain"]
    if terrain.get("dark") and rules(run, source).get("vision_range") is not None \
            and distance(run, source, target) > rules(run, source)["vision_range"]:
        return "target is beyond normal sight in darkness"
    if terrain["cover"].get(target) == "total" and rules(run,source).get("swallowed_by")!=target and rules(run,target).get("swallowed_by")!=source:
        return "target behind total cover"
    return None


def target_problem(run, source, target, maximum, *, enemy=True):
    """Why check_target would refuse, or None. Read-only: an item's targeting
    denial is reported without spending its charge."""
    try:
        problem = _target_geometry_problem(run, source, target, maximum, enemy)
    except ActionError as exc:
        return str(exc)
    if problem:
        return problem
    from hollowstar.affix_runtime import targeting_denial
    denied = targeting_denial(run, source, target, spend=False)
    return f"targeting denied by {denied['item']}" if denied else None


def check_target(run, source, target, maximum, *, enemy=True):
    problem = _target_geometry_problem(run, source, target, maximum, enemy)
    if problem:
        raise ActionError(problem)
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


def weapon_mode(run, source, mode="weapon", *, bonus=False):
    """The numbers one weapon attack in `mode` would use: expression,
    damage_type, attack_bonus, reach and long_range. Read-only; raises
    ActionError for a weapon or mode this actor cannot use."""
    a, r = actor(run, source), rules(run, source)
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
    return {"mode": mode, "expression": expression, "damage_type": kind, "attack_bonus": attack_bonus,
            "reach": reach + r.get("lunge_reach", 0), "long_range": long_range}


def attack_situation(run, source, target, *, long_range, weapon=True):
    """AC, advantage and disadvantage for an attack roll from source against
    target, with the reason for each. Read-only.

    Weapon attacks, spell attacks and monster attacks all read this, so a
    condition means the same thing whoever makes the roll. Weapon-only terms
    (Aim, Precision, a Feinting Attack) are left out when weapon is False.
    Doran's mirror glare (RULE-GLARE) is reported here; resolve_glare() rolls it.
    """
    a, r = actor(run, source), rules(run, source)
    defender = actor(run, target)
    aimed = weapon and bool(r.get("aimed"))
    cover = run.context["combat"]["terrain"]["cover"].get(target)
    if aimed and cover == "half":
        cover = None
    gap = distance(run, source, target)
    advantage, disadvantage = [], []
    disadvantage += [f"attacker {name.lower()}" for name in
                     sorted({"BLINDED", "FRIGHTENED", "POISONED", "RESTRAINED", "PRONE"}.intersection(a.statuses))]
    if "DODGING" in defender.statuses:
        disadvantage.append("target dodging")
    if gap > long_range:
        disadvantage.append("beyond normal range")
    if "PRONE" in defender.statuses:
        (advantage if gap <= 5 else disadvantage).append("target prone")
    advantage += [f"target {name.lower()}" for name in
                  sorted({"RESTRAINED", "STUNNED", "PARALYZED"}.intersection(defender.statuses))]
    if "INVISIBLE" in a.statuses:
        advantage.append("attacker invisible")
    if weapon and r.get("feint_target") == target:
        advantage.append("feinting attack")
    if rules(run, target).get("distracted_by") not in {None, source}:
        advantage.append("distracted")
    # D&D Help: an ally's aid grants advantage on this actor's next attack
    # against the named foe, and is spent by that roll.
    helped = r.get("help_advantage")
    helped = helped if isinstance(helped, dict) and helped.get("target") == target else None
    if helped:
        advantage.append("helped")
    if r.get("goaded_by") not in {None, target}:
        disadvantage.append("goaded")
    return {"ac": defender.armor_class + {"half": 2, "three_quarters": 5}.get(cover, 0),
            "cover": cover, "aimed": aimed, "distance": gap,
            "advantage": bool(advantage), "disadvantage": bool(disadvantage),
            "reasons": {"advantage": advantage, "disadvantage": disadvantage}, "help": helped,
            "glare": rules(run, target).get("identity") == "doran"
                     and bool(run.context["combat"]["terrain"].get("daylight")) and gap <= 60,
            # Aim and Precision Attack's die are one-shot; the rest is permanent.
            "precision_bonus": (r.get("precision_bonus", 0) + (2 if aimed else 0)) if weapon else 0,
            "precision_die": r.get("precision_die", 0) if weapon else 0,
            "damage_bonus": r.get("damage_bonus", 0) if weapon else 0}


def resolve_glare(run, source, target):
    """RULE-GLARE (DM044_0): attacking Doran within 60 ft under daylight is a
    DC 22 CON save; failure is disadvantage, failure by 5 or more also blinds."""
    glare = saving_throw(run, source, "CON", 22)
    if glare is not None and not glare["success"] and glare.get("total", 22) <= 17:
        actor(run, source).statuses["BLINDED"] = 1
    return glare


def attack_threshold(run, source, target, mode):
    """The natural roll that crits: 16 once Doran has read this target (not
    with the Cleaver), otherwise the actor's critical_min, 20 by default."""
    r = rules(run, source)
    if r.get("identity") == "doran" and r.get("read_target") == target and mode != "cleaver":
        return 16
    return r.get("critical_min", 20)


def weapon_attack(run, source, target, mode="weapon", *, bonus=False, reaction=False):
    a, r = actor(run, source), rules(run, source)
    resources_before = dict(a.resources)
    economy_before = copy.deepcopy(economy(run, source))
    identity = r.get("identity")
    profile = weapon_mode(run, source, mode, bonus=bonus)
    expression, kind = profile["expression"], profile["damage_type"]
    attack_bonus, reach, long_range = profile["attack_bonus"], profile["reach"], profile["long_range"]
    r.pop("lunge_reach", None)
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
    situation = attack_situation(run, source, target, long_range=long_range)
    r.pop("aimed", None)
    r.pop("precision_die", None)
    ac, adv, disadv, helped = situation["ac"], situation["advantage"], situation["disadvantage"], situation["help"]
    precision_bonus, damage_bonus = situation["precision_bonus"], situation["damage_bonus"]
    attack_bonus += precision_bonus + situation["precision_die"]
    if helped:
        r.pop("help_advantage", None)
    glare = resolve_glare(run, source, target) if situation["glare"] else None
    if glare is not None and not glare["success"]:
        disadv = True
    hit = roll_check(run, attack_bonus, ac, adv, disadv)
    threshold = attack_threshold(run, source, target, mode)
    critical = hit["natural"] >= threshold
    hit["success"] = hit["natural"] != 1 and (critical or hit["total"] >= ac)
    event = {"type": "attack", "source": source, "target": target, "mode": mode, "roll": hit, "critical": critical,
             "evidence": {"actor": a.name, "target": defender.name, "range": {"distance": distance(run, source, target),
             "reach": reach, "long": long_range}, "target_ac": ac, "attack_bonus": attack_bonus,
             "permanent_bonuses": {"precision": precision_bonus, "damage": damage_bonus},
             "precision_die": situation["precision_die"], "cover": situation["cover"],
             "advantage": adv, "disadvantage": disadv, "attack_reasons": situation["reasons"],
             "critical_threshold": threshold,
             "glare": glare, "help": helped,
             "resources_before": resources_before, "economy_before": economy_before}}
    if hit["success"]:
        # damage_parts: every term of the rolled amount, so the roll-math
        # readout adds up to the number it prints.
        if expression == DORAN_CLEAVER_FLAT_DAMAGE:
            base, rolls = (80 if critical else 40), []
            parts = [{"label": "weapon", "expression": expression, "rolls": [], "modifier": 0,
                      "critical": critical, "total": base}]
        else:
            base, rolls = dice(run, expression, critical=critical)
            parts = [{"label": "weapon", "expression": expression, "rolls": list(rolls),
                      "modifier": dice_terms(expression)[2], "critical": critical, "total": base}]
        amount = base + damage_bonus
        if damage_bonus:
            parts.append({"label": "bonus", "total": damage_bonus})
        sneak = 0
        sneak_rolls = []
        if identity == "custom" and r.get("class_id") == "rogue" and r.get("sneak_attack_round") != run.round_number:
            ally_near = any(other != source and other.startswith(source[0]) and creature.alive
                            and distance(run, other, target) <= 5 for other, creature in actors(run).items())
            if adv or ally_near:
                sneak_expression = f"{r.get('sneak_attack_dice', 1)}d6"
                sneak, sneak_rolls = dice(run, sneak_expression, critical=critical)
                amount += sneak; rolls += sneak_rolls; r["sneak_attack_round"] = run.round_number
                parts.append({"label": "sneak attack", "expression": sneak_expression, "rolls": list(sneak_rolls),
                              "modifier": 0, "critical": critical, "total": sneak})
        if r.pop("feint_target",None)==target:
            extra, extra_rolls=dice(run,"1d12",critical=critical);amount+=extra;rolls+=extra_rolls
            parts.append({"label": "feint", "expression": "1d12", "rolls": list(extra_rolls),
                          "modifier": 0, "critical": critical, "total": extra})
        rules(run,target).pop("distracted_by",None)
        event["damage_rolls"] = rolls
        if sneak:
            event["sneak_attack"] = {"damage": sneak, "rolls": sneak_rolls,
                                     "dice": r.get("sneak_attack_dice", 1)}
        event["evidence"]["damage_expression"] = expression
        event["evidence"]["damage_rolls"] = list(rolls)
        event["evidence"]["damage_parts"] = parts
        event["evidence"]["damage_rolled"] = amount
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
        rolled = amount
        amount, affix_effects, affix_riders = attack_adjustment(run, source, target, amount)
        event["evidence"]["affix_effects"] = affix_effects
        event["evidence"]["damage_steps"] = [] if amount == rolled else [{"label": "affix", "amount": amount}]
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


def _attack_economy_problem(run, source, *, bonus=False, reaction=False):
    """What weapon_attack's payment would refuse, or None. Read-only."""
    a, r, e = actor(run, source), rules(run, source), economy(run, source)
    identity = r.get("identity")
    if reaction:
        if not e.get("reaction", 0):
            return "reaction already spent"
    elif bonus:
        pool = r.get("bonus_attack_resource")
        if identity not in {"doran", "wren"} and not pool:
            return "no implemented bonus-action weapon"
        if not e.get("bonus", 0):
            return "bonus already spent"
        if identity not in {"doran", "wren"} and a.resources.get(pool, 0) < 1:
            return f"insufficient {pool}: need 1, have {a.resources.get(pool, 0)}"
    elif not e.get("attacks") and not e.get("action", 0):
        return "action already spent"
    if identity == "wren" and a.resources.get("crown_motes", 0) < 1:
        return f"insufficient crown_motes: need 1, have {a.resources.get('crown_motes', 0)}"
    return None


def forecast_attack(run, source, target, mode=None, *, bonus=False, reaction=False, informed=True):
    """What weapon_attack(run, source, target, mode) would do, as odds.

    Read-only: nothing is rolled, spent or moved, and an item's targeting
    denial keeps its charge. The odds are built from the resolver's own terms
    (weapon_mode, attack_situation, attack_threshold, mitigation), so a
    planner and the roll it predicts cannot disagree. Whose turn it is stays
    the caller's question, as it is for weapon_attack.

    hit/crit/lands are probabilities; expected_damage counts misses as 0 and
    is what reaches temporary and real hit points after every reduction;
    kill is P(the blow drops the target). A defender's Shield or Parry is
    their choice and is not priced in; `notes` says when one is possible.
    informed=False prices mitigation from source's side's knowledge ledger
    (known_mitigation); legality always reads the engine.
    """
    r = rules(run, source)
    mode = mode or r.get("loadout", "weapon")
    out = {"kind": "attack", "actor": source, "target": target, "mode": mode,
           "bonus": bool(bonus), "reaction": bool(reaction), "legal": False, "reason": None,
           "hit": 0.0, "crit": 0.0, "lands": 0.0, "expected_damage": 0.0, "kill": 0.0, "notes": []}
    try:
        profile = weapon_mode(run, source, mode, bonus=bonus)
    except ActionError as exc:
        out["reason"] = str(exc)
        return out
    problem = target_problem(run, source, target, max(profile["reach"], profile["long_range"]))
    if problem:
        out["reason"] = problem
        return out
    a, defender, identity = actor(run, source), actor(run, target), r.get("identity")
    from hollowstar.affix_runtime import offensive_tags, magnitude_preview
    tags = offensive_tags(run, source, {tag.name for tag in a.offensive_tags()})
    out.update(expression=profile["expression"], damage_type=profile["damage_type"])
    if not defender.gate.is_satisfied_by({DamageTag[tag] for tag in tags if tag in DamageTag.__members__}):
        # weapon_attack returns permission_blocked here before paying anything.
        out.update(legal=True, blocked=defender.gate.tell)
        return out
    problem = _attack_economy_problem(run, source, bonus=bonus, reaction=reaction)
    if problem:
        out["reason"] = problem
        return out
    situation = attack_situation(run, source, target, long_range=profile["long_range"])
    attack_bonus = profile["attack_bonus"] + situation["precision_bonus"] + situation["precision_die"]
    threshold = attack_threshold(run, source, target, mode)
    branches = [(1.0, situation["disadvantage"])]
    if situation["glare"]:
        passed = save_odds(run, source, "CON", 22)
        passed = 1.0 if passed is None else passed
        branches = [(passed, situation["disadvantage"]), (1 - passed, True)]
    hit = crit = 0.0
    for weight, disadvantage in branches:
        odds = attack_odds(attack_bonus, situation["ac"], advantage=situation["advantage"],
                           disadvantage=disadvantage, threshold=threshold)
        hit += weight * odds["hit"]
        crit += weight * odds["crit"]
    out.update(legal=True, attack_bonus=attack_bonus, target_ac=situation["ac"], cover=situation["cover"],
               advantage=situation["advantage"], disadvantage=situation["disadvantage"],
               reasons=situation["reasons"], glare=situation["glare"], critical_threshold=threshold,
               hit=hit, crit=crit, lands=hit)
    reduction = known_mitigation(run, source, target, profile["damage_type"],
                                 bypass_resistance=identity == "doran" and mode != "cleaver", informed=informed)
    magnify = magnitude_preview(run, source, target)
    ally_near = any(other != source and other.startswith(source[0]) and creature.alive
                    and distance(run, other, target) <= 5 for other, creature in actors(run).items())
    sneak = (identity == "custom" and r.get("class_id") == "rogue"
             and r.get("sneak_attack_round") != run.round_number and (situation["advantage"] or ally_near))

    def landed(critical):
        if profile["expression"] == DORAN_CLEAVER_FLAT_DAMAGE:
            odds = {80 if critical else 40: 1.0}
        else:
            odds = dice_odds(profile["expression"], critical=critical)
        if situation["damage_bonus"]:
            odds = map_odds(odds, lambda value: value + situation["damage_bonus"])
        if sneak:
            odds = add_odds(odds, dice_odds(f"{r.get('sneak_attack_dice', 1)}d6", critical=critical))
        if r.get("feint_target") == target:
            odds = add_odds(odds, dice_odds("1d12", critical=critical))
        return map_odds(odds, lambda value: mitigate(magnify(value), reduction))

    normal, critical = landed(False), landed(True)
    if defender.resources.get("ward", 0) > 0:
        normal = critical = {0: 1.0}
        out["notes"].append("ward absorbs the hit")
    plain = hit - crit
    toughness = defender.hp + defender.resources.get("temporary_hp", 0)
    out["expected_damage"] = plain * mean_odds(normal) + crit * mean_odds(critical)
    out["kill"] = plain * odds_at_least(normal, toughness) + crit * odds_at_least(critical, toughness)
    out["damage_range"] = [min(normal), max(critical) if crit else max(normal)]
    defender_rules = rules(run, target)
    if economy(run, target)["reaction"] and conscious(defender) and not reaction and (
            (defender_rules.get("identity") == "wren" and defender.resources.get("slot_1_general", 0) > 0
             and not defender_rules.get("shield"))
            or (defender_rules.get("identity") == "doran" and defender.resources.get("superiority_dice", 0) > 0
                and distance(run, source, target) <= 5)):
        out["notes"].append("the defender may answer a hit with Shield or Parry")
    if mode == "cleaver":
        out["notes"].append("Cleaver carry-through and skid are not priced in")
    return out


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
    if r.get('identity') == 'doran':
        def champion(action_id, label, cost, text, problem=None, targets=(), **extra):
            reason = ("It is not this actor's turn." if not my_turn else
                      'Incapacitated; end the turn.' if not conscious(a) else problem)
            rows.append({'id':action_id,'label':label,'category':'champion','cost':cost,'help':text,
                         'available':reason is None,'reason':reason,'targets':list(targets),**extra})
        whole = e.get('action') and e.get('bonus') and (e.get('movement') == a.speed or r.get('planted')) and not e.get('attacks') and r.get('grand_cleave_round') != run.round_number
        champion('grand_cleave','Grand Cleave','whole_turn',
                 'Both hands; 15-foot, 180-degree arc. +19, 120+4d20; a critical doubles the final total. Seven Medium spaces; Large costs two. Allies are included. First Huge or larger stops the blade. Reaction remains.',
                 None if whole else 'Requires an unspent whole turn; cannot repeat through Action Surge.', facings=['east','west','north','south'])
        champion('read_seam','Read the Seam','bonus','Insight +16 versus AC; success gives daggers critical range 16–20 until this target hits Doran.',
                 None if e.get('bonus') else 'Bonus action spent.', [k for k in alive_foes if distance(run,key,k)<=120])
        champion('action_surge','Action Surge','free','Gain one additional full action; does not reset movement, bonus action, or Grand Cleave.',
                 None if a.resources.get('action_surge',0)>0 else 'No Action Surge uses remain.')
        champion('quick_toss','Quick Toss','bonus','Summon and throw a dagger; +d12 damage. Costs one superiority die.',
                 None if e.get('bonus') and a.resources.get('superiority_dice',0)>0 else 'Requires bonus action and a superiority die.',
                 [k for k in alive_foes if distance(run,key,k)<=70])
        from hollowstar.maneuvers import ATTACKS
        for name in ATTACKS:
            action_id = 'maneuver_' + name.lower().replace(' ', '_')
            champion(action_id, name, 'attack_and_die', 'One attack and one superiority die; save DC 22 where applicable.',
                     None if has_attack and a.resources.get('superiority_dice',0)>0 else 'Requires an attack and a superiority die.',
                     [k for k in alive_foes if distance(run,key,k)<=70], maneuver=name)
        champion('second_wind' ,'Second Wind','bonus','Restore 30 HP.',
                 None if e.get('bonus') and a.resources.get('second_wind',0)>0 else 'Requires bonus action and an unused Second Wind.')
        champion('ring_heal','Ring heal','bonus','Restore 16 HP.', None if e.get('bonus') else 'Bonus action spent.')
        champion('dagger_attack','Obsidian dagger','attack','Instant dagger access; +16, 1d8+10, range 30/70.',
                 None if has_attack else 'No attack remains.', [k for k in alive_foes if distance(run,key,k)<=70])
        reach = 5 if state.get('terrain',{}).get('human_tight') else 10
        champion('cleaver_attack','Giant Cleaver','attack','40 fixed damage, critical 80; carry through until the first survivor.',
                 None if has_attack else 'No attack remains.', [k for k in alive_foes if distance(run,key,k)<=reach])
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
                result=heal(run,key,'30' if r.get('identity') == 'doran' else f"1d10+{r.get('level',20)}")
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
                "attack": ("grand_cleave" if kind == "grand_cleave" else "dagger_throw" if r.get("identity") == "doran" and result.get("type") == "attack" and result.get("mode") != "cleaver" and (action.get("maneuver") == "Quick Toss" or (target_key and distance(run,key,target_key)>5)) else _attack_animation(a)) if kind in {"attack", "shove", "trip", "grapple", "grand_cleave", "maneuver", "reaction"} else None,
                "move": "run" if kind in {"move", "dash", "disengage"} else None,
                "defense": "block" if kind in {"block", "brace", "guard"} else None,
                "dodge": "dodge" if kind == "dodge" else None,
                "cast": "cast" if kind in {"cast", "staff_cast", "domain"} else None,
                "flight": "fly" if kind in {"wings", "fly"} else None,
            },
            "loadout": _actor_loadout_presentation(a),
            "weapon_mode": 'cleaver' if kind == 'grand_cleave' else 'dagger' if r.get('identity') == 'doran' and result.get('type') == 'attack' and result.get('mode') != 'cleaver' else result.get('mode'),
            "facing": action.get('facing') if kind == 'grand_cleave' else None,
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
