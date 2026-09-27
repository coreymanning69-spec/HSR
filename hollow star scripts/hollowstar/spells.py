"""Versioned spell rulings; no edition substitution and no arbitrary code execution."""
from __future__ import annotations

import copy

from hollowstar.tactical import (ActionError, actor, actors, rules, economy, use, spend,
    dice, damage, heal, saving_throw, check_target, position, distance, condition,
    end_concentration, number, roll_check, same_side, target_problem, attack_situation,
    resolve_glare, dice_terms, dice_odds, map_odds, add_odds, mean_odds, odds_at_least,
    attack_odds, save_odds, condition_refusal, known_mitigation, mitigate)
from hollowstar import champion_rules


# Each row names its interpretation. Adding a spell is a data operation only
# when its mechanics fit a supported operation; otherwise the engine refuses it.
SPELLS = {
    "Arcane Bolt@HSR": {"name":"Arcane Bolt","edition":"HSR","authority":"HSR character creation registry",
        "operation":"attack","level":0,"dice":"1d10","damage_type":"FORCE","range":120},
    "Magic Missile@5e": {"name":"Magic Missile","edition":"5e","authority":"5e 2014 SRD spell",
        "operation":"darts","level":1,"dice":"1d4+1","darts":3,"damage_type":"FORCE","range":120},
    "Mage Armor@5e": {"name":"Mage Armor","edition":"5e","authority":"5e 2014 SRD spell",
        "operation":"utility","level":1,"range":5,"duration":480},
    "Sleep@5e": {"name":"Sleep","edition":"5e","authority":"5e 2014 SRD spell",
        "operation":"utility","level":1,"range":90,"duration":10},
    "Scorching Ray@5e": {"name":"Scorching Ray","edition":"5e","authority":"5e 2014 SRD spell",
        "operation":"attack","level":2,"dice":"2d6","damage_type":"FIRE","range":120},
    "Counterspell@5e": {"name":"Counterspell","edition":"5e","authority":"5e 2014 SRD spell",
        "operation":"utility","level":3,"range":60},
    "Imprisonment@5e": {"name":"Imprisonment","edition":"5e","authority":"DM041_B sealed sigil spell",
        "operation":"imprisonment","level":9,"save":"CHA","range":30,"resource":"sealed_imprisonment"},
    "Fireball@5e": {"name":"Fireball","edition":"5e","authority":"5e 2014 SRD spell",
        "operation":"damage","level":3,"dice":"8d6","damage_type":"FIRE","save":"DEX","half":True,"range":150,"radius":20},
    "Cure Wounds@5e": {"name":"Cure Wounds","edition":"5e","authority":"5e 2014 SRD spell",
        "operation":"heal","level":1,"dice":"1d8+5","range":5},
    "Healing Word@5e": {"name":"Healing Word","edition":"5e","authority":"5e 2014 SRD spell",
        "operation":"heal","level":1,"dice":"1d4+5","range":60,"bonus":True},
    "Portal Shear@DM": {"name":"Portal Shear","edition":"DM","authority":"DM044_1 Signature spells",
        "operation":"damage","level":7,"dice":"8d20","damage_type":"FORCE","save":"CON","half":False,"range":50,"resource":"portal_shear"},
    "Misty Step@5e": {"name":"Misty Step","edition":"5e","authority":"DM044_1 Unbarred; 5e geometry",
        "operation":"teleport","level":2,"range":30,"bonus":True},
    "Crown Mote@DM": {"name":"Crown Mote","edition":"DM","authority":"DM044_1 Crown of Stars",
        "operation":"attack","level":0,"dice":"4d12","damage_type":"RADIANT","range":120,"bonus":True,"resource":"crown_motes"},
    "Robe Star@DM": {"name":"Robe Star","edition":"DM","authority":"DM044_1 Robe stars",
        "operation":"darts","level":5,"dice":"1d4+1","darts":7,"damage_type":"FORCE","range":120,"resource":"robe_stars"},
    "Hold Monster@5e": {"name":"Hold Monster","edition":"5e","authority":"5e 2014 SRD; DESIGN target exclusions explicit",
        "operation":"condition","level":5,"condition":"PARALYZED","mental":True,"save":"WIS","duration":10,"range":90,"concentration":True},
    "Niv's Descent@DM": {"name":"Niv's Descent","edition":"DM","authority":"DM044_1 Niv's Descent",
        "operation":"niv_descent","level":5,"range":0,"shockwave_radius":20,
        "elemental_radius":30,"elemental_dice":"8d6","shockwave_save":"DEX",
        "elemental_save":"CON","full_turn":True},
    "Forcecage@5e": {"name":"Forcecage","edition":"5e","authority":"DM044_1 sigil force lane",
        "operation":"forcecage","level":7,"range":100,"resource":"forcecage"},
    "Gate@5e": {"name":"Gate","edition":"5e","authority":"DM044_1 Portal domain capstone",
        "operation":"gate","level":9,"range":60,"concentration":True},
    "Time Stop@5e": {"name":"Time Stop","edition":"5e","authority":"DM044_1 tempo-control ruling",
        "operation":"time_stop","level":9,"range":0},
}

# Wren's assigned live list is the complete 2014 PHB Cleric list. Entries
# without a specialized tactical lane still use the authoritative ``utility``
# operation: the cast consumes the declared slot, validates range/targets, and
# records concentration and duration without inventing hidden effects.
_CLERIC_LEVELS = {
    0: "Guidance|Light|Mending|Resistance|Sacred Flame|Spare the Dying|Thaumaturgy",
    1: "Bane|Bless|Command|Create or Destroy Water|Cure Wounds|Detect Evil and Good|Detect Magic|Detect Poison and Disease|Guiding Bolt|Healing Word|Inflict Wounds|Protection from Evil and Good|Sanctuary|Shield of Faith",
    2: "Aid|Augury|Blindness/Deafness|Calm Emotions|Continual Flame|Enhance Ability|Find Traps|Gentle Repose|Hold Person|Lesser Restoration|Locate Object|Prayer of Healing|Protection from Poison|Silence|Spiritual Weapon|Warding Bond|Zone of Truth",
    3: "Animate Dead|Beacon of Hope|Bestow Curse|Clairvoyance|Create Food and Water|Dispel Magic|Glyph of Warding|Mass Healing Word|Meld into Stone|Protection from Energy|Remove Curse|Revivify|Sending|Speak with Dead|Spirit Guardians|Tongues|Water Walk",
    4: "Banishment|Control Water|Death Ward|Divination|Freedom of Movement|Guardian of Faith|Locate Creature|Stone Shape",
    5: "Commune|Contagion|Dispel Evil and Good|Flame Strike|Geas|Greater Restoration|Hallow|Insect Plague|Legend Lore|Mass Cure Wounds|Planar Binding|Raise Dead|Scrying",
    6: "Blade Barrier|Create Undead|Find the Path|Forbiddance|Harm|Heal|Heroes' Feast|Planar Ally|True Seeing|Word of Recall",
    7: "Conjure Celestial|Divine Word|Etherealness|Fire Storm|Plane Shift|Regenerate|Resurrection|Symbol",
    8: "Antimagic Field|Control Weather|Earthquake|Holy Aura",
    9: "Astral Projection|Gate|Mass Heal|True Resurrection",
}


def _standard_cleric_registry() -> dict:
    entries = {}
    for level, names in _CLERIC_LEVELS.items():
        for name in names.split("|"):
            key = f"{name}@5e"
            if key in SPELLS:
                continue
            entries[key] = {
                "name": name, "edition": "5e", "authority": "5e 2014 PHB Cleric list",
                "operation": "utility", "level": level, "range": 60,
            }
    specialized = {
        "Sacred Flame@5e": {"operation": "damage", "dice": "1d8", "damage_type": "RADIANT", "save": "DEX"},
        "Guiding Bolt@5e": {"operation": "attack", "dice": "4d6", "damage_type": "RADIANT"},
        "Inflict Wounds@5e": {"operation": "attack", "dice": "3d10", "damage_type": "NECROTIC", "range": 5},
        "Spiritual Weapon@5e": {"operation": "attack", "dice": "1d8", "damage_type": "FORCE", "bonus": True},
        "Spirit Guardians@5e": {"operation": "damage", "dice": "3d8", "damage_type": "RADIANT", "save": "WIS", "half": True, "radius": 15, "concentration": True, "duration": 10},
        "Flame Strike@5e": {"operation": "damage", "dice": "8d6", "damage_type": "FIRE", "save": "DEX", "half": True, "radius": 10},
        "Harm@5e": {"operation": "damage", "dice": "14d6", "damage_type": "NECROTIC", "save": "CON", "half": True},
        "Heal@5e": {"operation": "heal", "dice": "70", "range": 60},
        "Mass Cure Wounds@5e": {"operation": "heal", "dice": "3d8+5", "range": 60},
        "Mass Healing Word@5e": {"operation": "heal", "dice": "1d4+5", "range": 60, "bonus": True},
        "Mass Heal@5e": {"operation": "heal", "dice": "700", "range": 60},
        "Hold Person@5e": {"operation": "condition", "condition": "PARALYZED", "mental": True, "save": "WIS", "duration": 10, "range": 60, "concentration": True},
        "Bless@5e": {"concentration": True, "duration": 10, "range": 30},
        "Silence@5e": {"concentration": True, "duration": 10, "range": 120, "radius": 20},
        "Banishment@5e": {"concentration": True, "duration": 1, "save": "CHA", "range": 60},
        "Death Ward@5e": {"duration": 8, "range": 30},
    }
    for key, values in specialized.items():
        if key in entries:
            entries[key].update(values)
    return entries


CLERIC_SPELLS = _standard_cleric_registry()

FIELDS = {"name","edition","authority","operation","level","dice","damage_type","save","half",
          "range","radius","bonus","resource","condition","mental","duration","concentration","darts",
          "shockwave_radius","elemental_radius","elemental_dice","shockwave_save","elemental_save","full_turn","targets_max"}


def validate_ruling(spec):
    if not isinstance(spec,dict) or set(spec)-FIELDS:
        raise ActionError("ruling contains unsupported fields")
    if not all(isinstance(spec.get(k),str) and spec[k].strip() for k in ("name","edition","authority","operation")):
        raise ActionError("ruling needs name, edition, authority, operation")
    if spec["edition"] not in {"2e","3.5e","5e","DM","HSR"}:
        raise ActionError("unsupported spell edition")
    if spec["operation"] not in {"utility","damage","heal","attack","teleport","condition","darts","niv_descent","forcecage","gate","time_stop","imprisonment"}:
        raise ActionError("RULING_REQUIRED: operation is not implemented")
    number(spec.get("level"),"spell level",0,9)
    number(spec.get("range"),"spell range",0,5280)
    if spec["operation"] in {"damage","heal","attack","darts"}:
        import re
        if not isinstance(spec.get("dice"),str) or not re.fullmatch(r"(?:\d+|(?:[1-9]|[1-9][0-9]|100)d(?:4|6|8|10|12|20)(?:[+-]\d+)?)",spec["dice"]):
            raise ActionError("ruling needs supported dice")
    if spec.get("save") not in {None,"STR","DEX","CON","INT","WIS","CHA"}:
        raise ActionError("unsupported save")
    from hollowstar.tactical import CONDITIONS
    if spec["operation"]=="condition" and spec.get("condition") not in CONDITIONS:
        raise ActionError("unsupported condition")
    for field in ("bonus","half","mental","concentration"):
        if field in spec and type(spec[field]) is not bool:
            raise ActionError(f"{field} must be boolean")
    for field in ("radius","duration","darts"):
        if field in spec: number(spec[field],field,1,1000)
    if spec["operation"] == "niv_descent":
        for field in ("shockwave_radius","elemental_radius"):
            number(spec.get(field),field,1,1000)
        import re
        if not isinstance(spec.get("elemental_dice"),str) or not re.fullmatch(r"(?:[1-9]|[1-9][0-9]|100)d(?:4|6|8|10|12|20)(?:[+-]\d+)?",spec["elemental_dice"]):
            raise ActionError("Niv's Descent needs supported elemental dice")
        if spec.get("shockwave_save") not in {"DEX"} or spec.get("elemental_save") not in {"CON"}:
            raise ActionError("Niv's Descent save lanes are fixed")
        if spec.get("full_turn") is not True:
            raise ActionError("Niv's Descent requires a full-turn commit")
    if spec["operation"] == "imprisonment" and (spec.get("level") != 9 or spec.get("save") != "CHA" or spec.get("range") != 30):
        raise ActionError("Imprisonment ruling must be the registered 5e spell")
    return copy.deepcopy(spec)


def catalog(run):
    return copy.deepcopy(SPELLS | CLERIC_SPELLS | run.context.get("spell_rulings",{}))


_SPELL_PRESENTATION = {
    "Arcane Bolt": ("evocation", "force", "A disciplined force lance that rewards a clear line and a steady hand.", "A compact bolt of shaped force strikes one creature. It is reliable, visible, and deliberately modest beside the dangerous spells that follow."),
    "Magic Missile": ("evocation", "force", "Three unerring force darts divide across visible creatures.", "The darts do not test armor or reflex. Once released, each finds its chosen target unless the target is protected by a specific magical defense."),
    "Fireball": ("evocation", "fire", "A sudden sphere of fire fills the marked radius; every creature inside must endure the blast.", "The detonation is fast, indiscriminate, and difficult to contain. Allies are not exempt unless the caster reshapes the area through a legal modification."),
    "Scorching Ray": ("evocation", "fire", "Separate rays of concentrated flame seek the caster's chosen targets.", "This is not a single explosion but a sequence of aimed releases. Each ray is resolved independently and leaves a brief incandescent trail."),
    "Guiding Bolt": ("evocation", "radiant", "Radiant force strikes a creature and marks the opening it leaves behind.", "The impact is bright enough to expose the target's movement and silhouette. Its tactical value is as much the revealed weakness as the wound."),
    "Inflict Wounds": ("necromancy", "necrotic", "A close-range touch tears vitality from the target.", "This spell is intimate, immediate, and dangerous to attempt at arm's reach. It is not a harmless shadow effect: the target's living strength is the material consumed."),
    "Healing Word": ("evocation", "healing", "A brief word calls a wounded ally back from the edge at range.", "The spell restores function rather than erasing every injury. It is fast enough for a crisis, but its small working cannot replace deliberate treatment."),
    "Cure Wounds": ("evocation", "healing", "A deliberate touch closes injury through sustained restorative magic.", "The caster must reach the subject and hold the working steady. The result is tangible recovery, not a cosmetic glow."),
    "Bless": ("enchantment", "radiant", "Allies within the working carry a measured divine advantage while concentration holds.", "Blessing is a maintained relationship between caster and chosen allies. Breaking concentration breaks the bridge."),
    "Mage Armor": ("abjuration", "ward", "A protective field replaces ordinary clothing as the target's first defense.", "The ward does not make the wearer invulnerable. It changes how force meets the body and remains a commitment with a finite duration."),
    "Sleep": ("enchantment", "control", "A wave of unnatural exhaustion can remove weaker creatures from the fight.", "Sleep is selective by vitality, not a universal command. Stronger bodies resist the working, while a sleeping target remains vulnerable to the consequences of the battlefield."),
    "Hold Person": ("enchantment", "control", "A failed mental defense leaves a humanoid rigid and unable to act.", "This is restraint through the target's own nervous command, not a rope or a visual stun. Concentration is required to keep the pattern closed."),
    "Hold Monster": ("enchantment", "control", "A stronger binding can arrest a living creature that fails its mental defense.", "The spell imposes stillness on a creature that may be physically impossible to restrain. It remains a concentration working and invites immediate retaliation against the caster."),
    "Silence": ("illusion", "control", "A radius becomes acoustically dead while the caster maintains the field.", "Within the boundary, speech and sound cannot travel normally. The quiet is tactical and absolute enough to interrupt ordinary verbal spellcasting."),
    "Misty Step": ("conjuration", "teleportation", "The caster folds a short distance and reappears at a visible destination.", "This is a rapid relocation, not flight. The destination must be legal, reachable, and clear enough for the host to validate before the step is paid for."),
    "Portal Shear": ("conjuration", "planar", "A violent seam in space cuts through the chosen target.", "The spell does not throw a decorative portal. It briefly exposes incompatible geometries and closes them through the target's occupied space."),
    "Niv's Descent": ("evocation", "elemental", "A full-turn descent converts the caster's position into a catastrophic elemental impact.", "The caster commits the entire turn to the descent. The shockwave and elemental rupture are separate consequences, and both announce the working to every witness nearby."),
    "Forcecage": ("evocation", "force", "A sealed lattice of force makes escape a problem of magic rather than muscle.", "The cage is a spatial verdict. It does not merely slow a creature; it changes which routes remain real until the working ends or a suitable countermeasure is applied."),
    "Imprisonment": ("abjuration", "control", "A ninth-rank binding removes a creature from ordinary freedom through a chosen prison form.", "This is an irreversible-feeling act with a serious cost and a deliberate target requirement. It should be treated as a world event, not a routine combat animation."),
    "Time Stop": ("transmutation", "time", "The caster tears a short private interval out of the shared turn.", "The spell is powerful because it changes sequence, not because it deals damage. Its duration and termination conditions must remain visible to the player."),
}

_EFFECT_PROFILE = {"force":"force","fire":"fire","cold":"cold","lightning":"lightning","radiant":"radiant","necrotic":"necrotic","healing":"heal","control":"control","teleportation":"teleport","planar":"planar","elemental":"elemental","ward":"ward","time":"time"}

def _presentation(spec):
    name = spec["name"]
    school, family, summary, description = _SPELL_PRESENTATION.get(name, ("arcane", "arcane", f"A {spec['operation']} working resolved by the host.", "The host validates this working's target, cost, and consequence before anything is committed."))
    action = "Full turn" if spec.get("full_turn") else "Bonus action" if spec.get("bonus") else "Action"
    save = spec.get("save")
    method = f"{save} saving throw" if save else "Spell attack" if spec.get("operation") == "attack" else "Automatic resolution"
    # Keep the established wire value for clients and saves; the clearer
    # player-facing distinction is carried by status_text below.
    resolution = "resolved" if spec.get("operation") != "utility" else "record_only"
    return {"school": school, "family": family, "effect_profile": _EFFECT_PROFILE.get(family, "arcane"),
            "summary": summary, "description": description, "casting_time": action,
            "components": "V, S" if spec.get("operation") != "utility" else "V, S, M",
            "method": method, "resolution": resolution,
            "status_text": "Resolved by host" if resolution == "resolved" else "Adjudication required",
            "warning": "Requires concentration." if spec.get("concentration") else ("High-tier working: consequences are difficult to reverse." if spec.get("level", 0) >= 7 else None)}


def display_catalog(run):
    """Return player-facing spell names while retaining exact canonical IDs."""
    return [
        {"id": spell_id, "display_name": spec["name"], "source": spec["edition"],
         "level": spec["level"], "authority": spec["authority"],
         "operation": spec["operation"], "range": spec["range"],
         "radius": spec.get("radius"), "resource": spec.get("resource"),
         "bonus": bool(spec.get("bonus")), "full_turn": bool(spec.get("full_turn")),
         "concentration": bool(spec.get("concentration")),
         **_presentation(spec)}
        for spell_id, spec in sorted(catalog(run).items(), key=lambda item: (item[1]["level"], item[1]["name"]))
    ]


METAMAGIC_COSTS = {"energy":0,"silent":0,"still":0,"enlarge":1,"extend":1,"careful":1,"empower":2,"maximize":3,"widen":3,"twin":4,"quicken":4}
# Spell attacks crit on a natural 20 only; no caster feature lowers it yet.
SPELL_CRITICAL = 20
# Operations whose outcome preview_cast can price. The rest are legal to
# preview but report no numbers.
PRICED_OPERATIONS = {"attack", "darts", "damage", "heal", "condition"}


def _custom_caster(run, key):
    """Whether key casts from casting_energy; raises when it cannot cast at all."""
    r = rules(run, key)
    custom = r.get("identity") == "custom" and r.get("class_id") in {"magician", "cleric"}
    if not champion_rules.flag(r.get("identity"), "staff_caster") and not custom:
        raise ActionError("spellcasting is not implemented for this profile")
    return custom


def _action_targets(action):
    targets = action.get("targets")
    if targets is None:
        # A single-target spell may name its target the way every other
        # action does; gambits and the default policy send "target".
        targets = [action["target"]] if action.get("target") is not None else []
    if not isinstance(targets, list) or len(set(map(str, targets))) != len(targets):
        raise ActionError("targets must be distinct actor IDs")
    return list(targets)


def _prepare(run, key, action):
    """Everything cast() decides before it pays or rolls, as a plan. Pure:
    raises ActionError for an illegal cast and changes nothing. Targeting
    denial is read without spending its charge; cast() spends it."""
    a, r = actor(run, key), rules(run, key)
    custom_caster = _custom_caster(run, key)
    spell_id = action.get("spell")
    known = catalog(run)
    if spell_id not in known:
        raise ActionError("RULING_REQUIRED: name an exact spell@edition or register an explicit executable ruling")
    spec = validate_ruling(known[spell_id])
    if custom_caster and spell_id not in r.get("known_spells", []):
        raise ActionError("spell is not in this character's known-spell list")
    if custom_caster and spec.get("level") == 0 and isinstance(spec.get("dice"), str):
        import re
        match = re.fullmatch(r"1d(4|6|8|10|12|20)([+-]\d+)?", spec["dice"])
        if match:
            count = 4 if r.get("level",1) >= 17 else 3 if r.get("level",1) >= 11 else 2 if r.get("level",1) >= 5 else 1
            spec["dice"] = f"{count}d{match.group(1)}{match.group(2) or ''}"
    modifiers = action.get("metamagic", [])
    if not isinstance(modifiers, list) or len(set(map(str, modifiers))) != len(modifiers) or any(m not in METAMAGIC_COSTS for m in modifiers):
        raise ActionError("RULING_REQUIRED: unsupported or duplicate metamagic")
    if "SILENCED" in a.statuses and "silent" not in modifiers:
        # Simplification: every catalog spell is treated as having a verbal
        # component; Silent Spell is the authored way around it.
        raise ActionError("silenced: this spell needs Silent Spell metamagic")
    counted = [m for m in modifiers if m not in {"silent","still"}]
    if "quicken" in counted and len(counted) > 1:
        raise ActionError("Quicken is exclusive")
    if "extend" in modifiers and not spec.get("duration"):
        raise ActionError("Extend requires an implemented duration")
    if "widen" in modifiers and not spec.get("radius"):
        raise ActionError("Widen requires an area spell")
    bonus = spec.get("bonus", False) or "quicken" in modifiers
    maximum = spec["range"] * (2 if "enlarge" in modifiers else 1)
    speed = r.get("fly_speed", a.speed)
    if spec.get("full_turn"):
        current = economy(run, key)
        if current["movement"] != speed or not current["action"] or not current["bonus"] or not current["reaction"]:
            raise ActionError("Niv's Descent requires an unspent entire turn")
    targets = _action_targets(action)
    plan = {"spell_id": spell_id, "spec": spec, "custom_caster": custom_caster, "modifiers": list(modifiers),
            "counted": counted, "bonus": bool(bonus), "maximum": maximum, "speed": speed,
            "destination": None, "center": None, "radius": None}
    operation = spec["operation"]
    if operation == "teleport":
        destination = action.get("destination")
        if not isinstance(destination,list) or len(destination)!=3 or any(type(x) is not int or x<0 or x>120 or x%5 for x in destination):
            raise ActionError("teleport destination must be a visible grid point")
        if max(abs(position(run,key)[i]-destination[i]) for i in range(3)) > maximum:
            raise ActionError("teleport out of range")
        if destination in run.context["combat"]["terrain"]["blocked"]:
            raise ActionError("teleport destination obstructed")
        plan["destination"] = list(destination)
    elif operation == "niv_descent":
        if action.get("dive") is not True:
            raise ActionError("Niv's Descent requires an intentional dive")
    elif operation == "forcecage":
        if len(targets) != 1:
            raise ActionError("Forcecage requires exactly one target")
    elif operation == "gate":
        plane = action.get("plane")
        if not isinstance(plane,str) or not plane.strip():
            raise ActionError("Gate requires a named destination plane")
        named = action.get("named_creature")
        if named is not None and (not isinstance(named,str) or not named.strip()):
            raise ActionError("Gate named_creature must be a non-empty name")
    elif operation == "time_stop":
        if action.get("targets") or action.get("center") is not None:
            raise ActionError("Time Stop cannot target another creature or area")
        targets = []
    elif operation == "imprisonment":
        if len(targets) != 1:
            raise ActionError("Imprisonment requires exactly one target")
        if action.get("mode") not in {"burial","chaining","hedged prison","minimus containment","slumber","thralldom"}:
            raise ActionError("Imprisonment requires an explicit 5e mode")
    elif operation == "utility":
        if len(targets) > spec.get("targets_max", 20):
            raise ActionError("utility spell target count exceeds its declared limit")
    elif spec.get("radius"):
        center = action.get("center")
        if not isinstance(center,list) or len(center)!=3 or any(type(x) is not int or x%5 for x in center):
            raise ActionError("area spell requires a grid center")
        if max(abs(position(run,key)[i]-center[i]) for i in range(3)) > maximum:
            raise ActionError("spell center out of range")
        radius = spec["radius"] * (2 if "widen" in modifiers else 1)
        targets = [k for k,v in actors(run).items() if v.alive and max(abs(position(run,k)[i]-center[i]) for i in range(3)) <= radius]
        plan.update(center=list(center), radius=radius)
    elif not targets or len(targets) > spec.get("darts", 1):
        raise ActionError("spell needs its supported target count")
    if not spec.get("radius"):
        for target in targets:
            problem = target_problem(run, key, target, maximum, enemy=operation != "heal")
            if problem:
                raise ActionError(problem)
    plan["targets"] = targets
    return plan


def _pay(plan, econ, res):
    """Spend what the planned cast costs from an economy and a resource dict,
    in cast()'s order. cast() runs it on copies first and then on the live
    dicts, so a refused payment changes nothing. Raises as use() and spend() do."""
    def use_slot(slot):
        if not econ.get(slot, 0):
            raise ActionError(f"{slot} already spent")
        econ[slot] -= 1

    def spend_resource(name, amount=1):
        if res.get(name, 0) < amount:
            raise ActionError(f"insufficient {name}: need {amount}, have {res.get(name, 0)}")
        res[name] -= amount
        if name.startswith("slot_") and "spell_slots_total" in res:
            res["spell_slots_total"] = sum(v for k, v in res.items() if k.startswith("slot_"))

    spec, modifiers, counted, bonus = plan["spec"], plan["modifiers"], plan["counted"], plan["bonus"]
    if spec.get("full_turn"):
        use_slot("action"); use_slot("bonus"); use_slot("reaction")
        econ["movement"] = 0
    elif len(counted) >= 3:
        if econ.get("movement") != plan["speed"] or not econ.get("bonus") or not econ.get("reaction"):
            raise ActionError("three metamagics require an unspent entire turn")
        use_slot("action"); use_slot("bonus"); use_slot("reaction")
        econ["movement"] = 0
    else:
        use_slot("bonus" if bonus else "action")
        if spec["operation"] != "utility" and len(counted) == 2:
            if bonus:
                raise ActionError("two metamagics need a separate bonus-action tax")
            use_slot("bonus")
    metamagic_cost = sum(METAMAGIC_COSTS[m] for m in modifiers)
    if metamagic_cost:
        if res.get("sorcery_points", 0) >= metamagic_cost:
            spend_resource("sorcery_points", metamagic_cost)
        elif res.get("casting_energy", 0) >= metamagic_cost:
            spend_resource("casting_energy", metamagic_cost)
        else:
            slot_key = next((f"slot_{lvl}_general" for lvl in range(metamagic_cost, 10) if res.get(f"slot_{lvl}_general", 0) > 0), None)
            if slot_key:
                spend_resource(slot_key, 1)
            elif plan["custom_caster"]:
                spend_resource("casting_energy", metamagic_cost)
            else:
                spend_resource("sorcery_points", metamagic_cost)
    if spec.get("resource"):
        spend_resource(spec["resource"])
    elif spec["level"]:
        if plan["custom_caster"]:
            spend_resource("casting_energy", spec["level"])
        else:
            spend_resource(f"slot_{spec['level']}_general")


def payment_problem(run, key, plan):
    """Why the planned cast cannot be paid for, or None. Read-only."""
    econ, res = copy.deepcopy(economy(run, key)), dict(actor(run, key).resources)
    try:
        _pay(plan, econ, res)
    except ActionError as exc:
        return str(exc)
    return None


def payment_cost(run, key, plan):
    """What the planned cast spends: {"economy": {slot: n}, "resources": {name: n}}. Read-only."""
    econ, res = copy.deepcopy(economy(run, key)), dict(actor(run, key).resources)
    before_econ, before_res = copy.deepcopy(econ), dict(res)
    try:
        _pay(plan, econ, res)
    except ActionError:
        return None
    return {"economy": {k: before_econ[k] - econ.get(k, 0) for k in before_econ
                        if isinstance(before_econ[k], int) and before_econ[k] != econ.get(k, 0)},
            "resources": {k: before_res[k] - res.get(k, 0) for k in before_res
                          if k != "spell_slots_total" and before_res[k] != res.get(k, 0)}}


def spell_ready(run, key, spell_id):
    """Whether key could pay for spell_id right now with no metamagic, ignoring targets. Read-only."""
    try:
        custom = _custom_caster(run, key)
        known = catalog(run)
        if spell_id not in known:
            return False
        spec = validate_ruling(known[spell_id])
    except ActionError:
        return False
    r = rules(run, key)
    if custom and spell_id not in r.get("known_spells", []):
        return False
    if "SILENCED" in actor(run, key).statuses:
        return False
    plan = {"spec": spec, "modifiers": [], "counted": [], "bonus": bool(spec.get("bonus")),
            "custom_caster": custom, "speed": r.get("fly_speed", actor(run, key).speed)}
    if spec.get("full_turn"):
        current = economy(run, key)
        if current["movement"] != plan["speed"] or not current["action"] or not current["bonus"] or not current["reaction"]:
            return False
    return payment_problem(run, key, plan) is None


def _roll_spell_damage(run, spec, modifiers, *, critical=False):
    """Roll a spell's damage dice once: (amount, rolls, parts, steps).
    Maximize and Empower hold on a critical hit."""
    maximize = "maximize" in modifiers
    count, sides, modifier = dice_terms(spec["dice"])
    amount, rolls = dice(run, spec["dice"], critical=critical, maximize=maximize)
    parts = [{"label": "spell", "expression": spec["dice"], "rolls": list(rolls) if sides else [],
              "modifier": modifier, "critical": critical, "maximized": maximize and bool(sides), "total": amount}]
    steps = []
    if "empower" in modifiers:
        amount = int(amount * 1.5)
        steps.append({"label": "empower ×1.5", "amount": amount})
    return amount, (list(rolls) if sides else []), parts, steps


def _damage_evidence(spec, amount, rolls, parts, steps):
    return {"damage_expression": spec["dice"], "damage_rolls": list(rolls), "damage_parts": parts,
            "damage_steps": steps, "damage_rolled": parts[0]["total"] + sum(p["total"] for p in parts[1:]),
            "damage_type": spec.get("damage_type"), "damage_dealt_before_mitigation": amount}


def _spell_attack(run, key, target, spec, plan, attack_bonus):
    """One spell attack roll, read through the same situation weapon attacks use."""
    r = rules(run, key)
    situation = attack_situation(run, key, target, long_range=plan["maximum"], weapon=False)
    if situation["help"]:
        r.pop("help_advantage", None)
    glare = resolve_glare(run, key, target) if situation["glare"] else None
    disadvantage = situation["disadvantage"] or (glare is not None and not glare["success"])
    hit = roll_check(run, attack_bonus, situation["ac"], situation["advantage"], disadvantage)
    critical = hit["natural"] >= SPELL_CRITICAL
    hit["success"] = hit["natural"] != 1 and (critical or hit["success"])
    event = {"target": target, "type": "attack", "attack": hit, "critical": critical and hit["success"], "result": None,
             "evidence": {"target_ac": situation["ac"], "attack_bonus": attack_bonus, "cover": situation["cover"],
                          "advantage": situation["advantage"], "disadvantage": disadvantage,
                          "attack_reasons": situation["reasons"], "critical_threshold": SPELL_CRITICAL,
                          "glare": glare, "help": situation["help"]}}
    if hit["success"]:
        rules(run, target).pop("distracted_by", None)
        amount, rolls, parts, steps = _roll_spell_damage(run, spec, plan["modifiers"], critical=critical)
        event["evidence"].update(_damage_evidence(spec, amount, rolls, parts, steps))
        event["result"] = damage(run, key, target, amount, spec["damage_type"])
    return event


def cast(run,key,action):
    plan = _prepare(run, key, action)
    a, r = actor(run, key), rules(run, key)
    spec, spell_id, modifiers, targets = plan["spec"], plan["spell_id"], plan["modifiers"], plan["targets"]
    problem = payment_problem(run, key, plan)
    if problem:
        raise ActionError(problem)
    if not spec.get("radius"):
        for target in targets:
            # Legality was read in _prepare; this pass spends targeting-denial charges.
            check_target(run, key, target, plan["maximum"], enemy=spec["operation"] != "heal")
    _pay(plan, economy(run, key), a.resources)
    events = []
    if spec["operation"] == "utility":
        events.append({"type": "utility", "actor": key, "spell": spell_id,
                       "targets": list(targets), "duration": spec.get("duration"),
                       "concentration": bool(spec.get("concentration")),
                       "evidence": {"rules_authority": spec["authority"],
                                    "state_committed": True}})
    if spec.get("concentration"): end_concentration(run, key)
    if spec["operation"] == "teleport":
        destination = plan["destination"]
        run.context["combat"]["positions"][key] = destination
        events.append({"type":"teleport","actor":key,"destination":destination})
    elif spec["operation"] == "niv_descent":
        origin = position(run, key)
        shockwave = []; wave = []
        for target, creature in actors(run).items():
            if not creature.alive or target == key:
                continue
            distance_from_origin = max(abs(origin[i]-position(run,target)[i]) for i in range(3))
            if distance_from_origin <= spec["shockwave_radius"]:
                save = saving_throw(run,target,spec["shockwave_save"],22,magical=True)
                if save is not None:
                    result = {"target":target,"save":save,"rough_terrain":True,
                              "disadvantage_next_attack":not save["success"]}
                    rules(run,target)["rough_terrain_until"] = run.round_number + (2 if action.get("shape") == "wall" else 1)
                    if not save["success"]:
                        rules(run,target)["disadvantage_next_attack_until"] = run.round_number+1
                    shockwave.append(result)
            if distance_from_origin <= spec["elemental_radius"]:
                amount, rolls = dice(run, spec["elemental_dice"])
                save = saving_throw(run,target,spec["elemental_save"],22,magical=True)
                if target[0] == key[0]:
                    result = heal(run,target,spec["elemental_dice"])
                    if rules(run,target).get("identity") == "doran":
                        result = heal(run,target,"8d6")
                elif save is None:
                    result = {"target": target, "contained": True, "damage": 0}
                else:
                    if save["success"]:
                        amount //= 2
                    # The source calls this an elemental wave rather than a
                    # fixed school; FIRE is the engine's explicit elemental
                    # lane and remains visible in the resolution evidence.
                    result = damage(run,key,target,amount,"FIRE")
                    result["damage_before_half"] = amount*2 if save["success"] else amount
                    result["damage_after_save"] = amount
                wave.append({"target":target,"save":save,"rolls":rolls,"result":result})
        events.append({"type":"niv_descent","actor":key,"dive":True,"shockwave":shockwave,"elemental_wave":wave,
                       "evidence":{"shockwave_radius":spec["shockwave_radius"],"elemental_radius":spec["elemental_radius"],
                                   "shockwave_dc":22,"elemental_dc":22,"full_turn":True}})
    elif spec["operation"] == "forcecage":
        target = targets[0]
        object_id = f"forcecage-{run.round_number}-{len(run.context['combat']['terrain'].get('structures',[]))}"
        structure = {"object_id":object_id,"kind":"forcecage","name":"Forcecage",
                     "position":list(position(run,target)),"hp":1,"indestructible":True,
                     "occupants":[target],"escape":"Portal 14 or an authored escape ruling"}
        run.context["combat"]["terrain"].setdefault("structures",[]).append(structure)
        rules(run,target)["contained_by"] = object_id
        events.append({"type":"forcecage","actor":key,"target":target,
                       "structure":copy.deepcopy(structure),
                       "evidence":{"save":False,"spatial_containment":True,
                                   "mind_immunity_irrelevant":True}})
    elif spec["operation"] == "gate":
        plane = action["plane"]
        portal_id = f"gate-{run.round_number}-{len(run.context['combat'].get('portals',[]))}"
        portal = {"portal_id":portal_id,"kind":"gate","plane":plane,
                  "opened_by":key,"named_creature":action.get("named_creature"),
                  "concentration_bound":True}
        run.context["combat"].setdefault("portals",[]).append(portal)
        events.append({"type":"gate","actor":key,"portal":copy.deepcopy(portal),
                       "evidence":{"concentration":True,"plane":plane,
                                   "named_pull":action.get("named_creature") is not None}})
    elif spec["operation"] == "time_stop":
        roll, rolls = dice(run,"1d4+1")
        run.context["combat"]["time_stop"] = {"owner":key,"remaining":roll,
                                              "rolls":rolls,"ended_by":None}
        events.append({"type":"time_stop","actor":key,"turns":roll,
                       "rolls":rolls,"evidence":{"uninterrupted":True,
                                                 "ends_on_affecting_another":True}})
    elif spec["operation"] == "imprisonment":
        target = targets[0]
        save = saving_throw(run,target,"CHA",22,magical=True)
        event = {"type":"imprisonment","actor":key,"target":target,"mode":action["mode"],"save":save,"applied":False}
        if save is None:
            event["reason"] = "target is contained"
        elif not save["success"]:
            object_id = f"imprisonment-{run.round_number}-{len(run.context['combat']['terrain'].get('structures',[]))}"
            structure = {"object_id":object_id,"kind":"imprisonment","name":"Imprisonment","position":list(position(run,target)),"hp":None,"indestructible":True,"occupants":[target],"mode":action["mode"],"escape":"No escape rule is inferred; resolve only by the registered mode."}
            run.context["combat"]["terrain"].setdefault("structures",[]).append(structure)
            rules(run,target)["contained_by"] = object_id
            event.update({"applied":True,"structure":copy.deepcopy(structure),"evidence":{"spatial_containment":True,"mind_altering":False,"visible_tell":True}})
        events.append(event)
    elif spec["operation"] != "utility":
        operation = spec["operation"]
        spell_dc = r.get("spell_save_dc", 22)
        spell_attack = r.get("spell_attack_bonus", 14)
        for repeat in range(2 if "twin" in modifiers else 1):
            # An area spell rolls once and every creature in it takes that roll.
            shared = _roll_spell_damage(run, spec, modifiers) if operation == "damage" else None
            for target in targets:
                if operation == "heal":
                    events.append(heal(run,target,spec["dice"]))
                    continue
                if operation == "attack":
                    events.append(_spell_attack(run, key, target, spec, plan, spell_attack))
                    continue
                if operation == "darts":
                    if len(targets) != 1: raise ActionError("robe darts currently require one target; distribution needs a ruling")
                    for _ in range(spec["darts"]):
                        value, individual, parts, steps = _roll_spell_damage(run, spec, modifiers)
                        events.append({"target":target,"type":"dart","rolls":individual,
                                       "evidence":_damage_evidence(spec, value, individual, parts, steps),
                                       "result":damage(run,key,target,value,spec["damage_type"])})
                    continue
                check = saving_throw(run,target,spec["save"],spell_dc,magical=True) if spec.get("save") else {"success":False}
                if "careful" in modifiers and target[0] == key[0]: check = {"success":True,"reason":"Careful"}
                if check is None:
                    # A contained creature makes no save and the spell does not reach it.
                    events.append({"target":target,"type":operation,"save":None,"result":None,"reason":"target is contained"})
                    continue
                if operation == "condition":
                    events.append({"target":target,"type":"condition","save":check,"result":None if check["success"] else condition(run,target,spec["condition"],spec.get("duration",1)*(2 if "extend" in modifiers else 1),mental=spec.get("mental",False))})
                    continue
                amount, rolls, parts, steps = shared
                steps = list(steps)
                resolved = amount//2 if check["success"] and spec.get("half") else 0 if check["success"] else amount
                if check["success"]:
                    label = "careful" if check.get("reason") == "Careful" else "saved"
                    steps.append({"label": f"{label}: {'half' if spec.get('half') else 'none'}", "amount": resolved})
                events.append({"target":target,"type":"damage","rolls":rolls,"save":check,
                               "evidence":_damage_evidence(spec, resolved, rolls, parts, steps),
                               "result":damage(run,key,target,resolved,spec["damage_type"])})
    if spec.get("concentration"):
        run.context["combat"]["concentration"][key] = {"spell":spell_id,"targets":targets,
            "conditions":[spec["condition"]] if "condition" in spec else [],"remaining":spec.get("duration",10),"repeat_save":spec.get("save")}
    receipt = {"type":"cast","actor":key,"spell":spell_id,"ruling":spec,"metamagic":modifiers,"events":events,
               "presentation":{"spell":{"display_name":spec["name"], **_presentation(spec)},
                               "casting":{"element":_presentation(spec)["effect_profile"]}}}
    if events and isinstance(events[0], dict):
        if "attack" in events[0]:
            receipt["roll"] = events[0]["attack"]
            receipt["critical"] = bool(events[0].get("critical"))
        if "save" in events[0]:
            receipt["save"] = events[0]["save"]
    primary_damage = None
    primary_damage_type = spec.get("damage_type")
    primary_healing = None
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if "healing" in ev and isinstance(ev["healing"], (int, float)):
            primary_healing = (primary_healing or 0) + ev["healing"]
        res = ev.get("result")
        if isinstance(res, dict):
            if "damage" in res and isinstance(res["damage"], (int, float)):
                primary_damage = (primary_damage or 0) + res["damage"]
            if "damage_type" in res:
                primary_damage_type = res["damage_type"]
        elif "damage" in ev and isinstance(ev["damage"], (int, float)):
            primary_damage = (primary_damage or 0) + ev["damage"]
    if primary_damage is not None:
        receipt["damage"] = primary_damage
        if primary_damage_type:
            receipt["damage_type"] = primary_damage_type
    if primary_healing is not None:
        receipt["healing"] = primary_healing
    if targets:
        receipt["target"] = targets[0]
        receipt["targets"] = targets
    return receipt


# --- Preview --------------------------------------------------------------------
# What cast() would do, as odds. Built from _prepare, payment_problem and the
# tactical odds functions, so a preview and the cast it predicts share every
# legality rule. Nothing is rolled, spent, or moved.

def _damage_odds(spec, modifiers, *, critical=False):
    odds = dice_odds(spec["dice"], critical=critical, maximize="maximize" in modifiers)
    if "empower" in modifiers:
        odds = map_odds(odds, lambda value: int(value * 1.5))
    return odds


def _landed(run, key, target, spec, odds, informed):
    """Damage odds after the target's mitigation, as the observer knows it."""
    reduction = known_mitigation(run, key, target, spec["damage_type"], informed=informed)
    odds = map_odds(odds, lambda value: mitigate(value, reduction))
    if actor(run, target).resources.get("ward", 0) > 0:
        return {0: 1.0}
    return odds


def _target_forecast(run, key, target, plan, informed):
    """{hit, expected_damage, expected_healing, applied, damage_odds} for one target, one repeat."""
    spec, modifiers, operation = plan["spec"], plan["modifiers"], plan["spec"]["operation"]
    r, who = rules(run, key), actor(run, target)
    row = {"target": target, "hit": None, "expected_damage": 0.0, "expected_healing": 0.0, "applied": None,
           "damage_odds": {0: 1.0}, "notes": []}
    if operation == "heal":
        rolled = dice_odds(spec["dice"], maximize=rules(run, target).get("identity") == "doran")
        room = max(0, who.max_hp - who.hp)
        row["expected_healing"] = mean_odds(map_odds(rolled, lambda value: min(value, room)))
        row["healing_range"] = [min(rolled), max(rolled)]
        return row
    if operation == "attack":
        situation = attack_situation(run, key, target, long_range=plan["maximum"], weapon=False)
        bonus = r.get("spell_attack_bonus", 14)
        branches = [(1.0, situation["disadvantage"])]
        if situation["glare"]:
            passed = save_odds(run, key, "CON", 22)
            passed = 1.0 if passed is None else passed
            branches = [(passed, situation["disadvantage"]), (1 - passed, True)]
        hit = crit = 0.0
        for weight, disadvantage in branches:
            odds = attack_odds(bonus, situation["ac"], advantage=situation["advantage"],
                               disadvantage=disadvantage, threshold=SPELL_CRITICAL)
            hit += weight * odds["hit"]; crit += weight * odds["crit"]
        normal = _landed(run, key, target, spec, _damage_odds(spec, modifiers), informed)
        critical = _landed(run, key, target, spec, _damage_odds(spec, modifiers, critical=True), informed)
        row.update(hit=hit, crit=crit, target_ac=situation["ac"], cover=situation["cover"],
                   advantage=situation["advantage"], disadvantage=situation["disadvantage"],
                   reasons=situation["reasons"])
        miss = 1 - hit
        combined = {0: miss} if miss else {}
        for weight, odds in ((hit - crit, normal), (crit, critical)):
            for value, p in odds.items():
                combined[value] = combined.get(value, 0.0) + weight * p
        row["damage_odds"] = combined
    elif operation == "darts":
        one = _landed(run, key, target, spec, _damage_odds(spec, modifiers), informed)
        total = {0: 1.0}
        for _ in range(spec["darts"]):
            total = add_odds(total, one)
        row.update(hit=1.0, damage_odds=total)
    elif operation in {"damage", "condition"}:
        careful = "careful" in modifiers and target[0] == key[0]
        passed = 1.0 if careful else (save_odds(run, target, spec["save"], r.get("spell_save_dc", 22), magical=True)
                                      if spec.get("save") else 0.0)
        if passed is None:
            row["notes"].append("target is contained")
            row["applied"] = 0.0
            return row
        row["save_success"] = passed
        if operation == "condition":
            refused = condition_refusal(run, target, spec["condition"], mental=spec.get("mental", False))
            row["applied"] = 0.0 if refused else 1 - passed
            if refused:
                row["notes"].append(refused["reason"])
            return row
        rolled = _damage_odds(spec, modifiers)
        full = _landed(run, key, target, spec, rolled, informed)
        # cast() halves a saved amount before mitigation, so the preview does too.
        halved = (_landed(run, key, target, spec, map_odds(rolled, lambda value: value // 2), informed)
                  if spec.get("half") else {0: 1.0})
        combined = {}
        for weight, odds in ((1 - passed, full), (passed, halved)):
            for value, p in odds.items():
                combined[value] = combined.get(value, 0.0) + weight * p
        row["damage_odds"] = combined
    row["expected_damage"] = mean_odds(row["damage_odds"])
    return row


def preview_cast(run, key, action, *, informed=True):
    """What cast(run, key, action) would do, as odds, without doing it.

    legal/reason are exactly what cast() would decide, including payment.
    For priced operations each target gets hit/save/applied odds and
    expected damage or healing; kill is P(the cast drops that target).
    informed=False prices damage the way the observer's side knows the
    target (tactical.known_mitigation) instead of the way the engine does.
    """
    out = {"kind": "cast", "actor": key, "spell": action.get("spell"), "legal": False, "reason": None,
           "targets": [], "per_target": [], "expected_damage": 0.0, "expected_healing": 0.0,
           "kill": 0.0, "hit": None, "cost": None, "notes": []}
    try:
        plan = _prepare(run, key, action)
    except ActionError as exc:
        out["reason"] = str(exc)
        return out
    problem = payment_problem(run, key, plan)
    if problem:
        out["reason"] = problem
        return out
    spec = plan["spec"]
    out.update(legal=True, targets=list(plan["targets"]), cost=payment_cost(run, key, plan),
               operation=spec["operation"], bonus=plan["bonus"], center=plan["center"], radius=plan["radius"])
    if spec["operation"] not in PRICED_OPERATIONS:
        out["notes"].append(f"{spec['operation']} is not priced")
        return out
    repeats = 2 if "twin" in plan["modifiers"] else 1
    best_kill = 0.0
    for target in plan["targets"]:
        row = _target_forecast(run, key, target, plan, informed)
        odds = row.pop("damage_odds")
        total = {0: 1.0}
        for _ in range(repeats):
            total = add_odds(total, odds)
        row["expected_damage"] = mean_odds(total)
        row["expected_healing"] *= repeats
        who = actor(run, target)
        toughness = who.hp + who.resources.get("temporary_hp", 0)
        row["kill"] = odds_at_least(total, toughness) if who.alive and not same_side(key, target) and spec["operation"] != "heal" else 0.0
        row["ally"] = same_side(key, target)
        out["per_target"].append(row)
        # Friendly fire counts against the cast's damage score.
        out["expected_damage"] += -row["expected_damage"] if row["ally"] else row["expected_damage"]
        out["expected_healing"] += row["expected_healing"]
        best_kill = max(best_kill, row["kill"])
        if row["hit"] is not None:
            out["hit"] = row["hit"] if out["hit"] is None else max(out["hit"], row["hit"])
    out["kill"] = best_kill
    return out
