"""Versioned spell rulings; no edition substitution and no arbitrary code execution."""
from __future__ import annotations

import copy

from hollowstar.tactical import (ActionError, actor, actors, rules, economy, use, spend,
    dice, damage, heal, saving_throw, check_target, position, distance, condition,
    end_concentration, number, roll_check)
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


def display_catalog(run):
    """Return player-facing spell names while retaining exact canonical IDs."""
    return [
        {"id": spell_id, "display_name": spec["name"], "source": spec["edition"],
         "level": spec["level"], "authority": spec["authority"],
         "operation": spec["operation"], "range": spec["range"],
         "radius": spec.get("radius"), "resource": spec.get("resource"),
         "bonus": bool(spec.get("bonus")), "full_turn": bool(spec.get("full_turn")),
         "concentration": bool(spec.get("concentration")),
         "resolution": "record_only" if spec["operation"] == "utility" else "resolved"}
        for spell_id, spec in sorted(catalog(run).items(), key=lambda item: (item[1]["level"], item[1]["name"]))
    ]


def cast(run,key,action):
    a,r=actor(run,key),rules(run,key)
    custom_caster = r.get("identity") == "custom" and r.get("class_id") in {"magician", "cleric"}
    if not champion_rules.flag(r.get("identity"), "staff_caster") and not custom_caster:
        raise ActionError("spellcasting is not implemented for this profile")
    spell_id=action.get("spell")
    if spell_id not in catalog(run):
        raise ActionError("RULING_REQUIRED: name an exact spell@edition or register an explicit executable ruling")
    spec=validate_ruling(catalog(run)[spell_id])
    if custom_caster and spell_id not in r.get("known_spells", []):
        raise ActionError("spell is not in this character's known-spell list")
    if custom_caster and spec.get("level") == 0 and isinstance(spec.get("dice"), str):
        import re
        match=re.fullmatch(r"1d(4|6|8|10|12|20)([+-]\d+)?",spec["dice"])
        if match:
            count=4 if r.get("level",1)>=17 else 3 if r.get("level",1)>=11 else 2 if r.get("level",1)>=5 else 1
            spec["dice"]=f"{count}d{match.group(1)}{match.group(2) or ''}"
    modifiers=action.get("metamagic",[])
    costs={"energy":0,"silent":0,"still":0,"enlarge":1,"extend":1,"careful":1,"empower":2,"maximize":3,"widen":3,"twin":4,"quicken":4}
    if not isinstance(modifiers,list) or len(set(modifiers))!=len(modifiers) or any(m not in costs for m in modifiers):
        raise ActionError("RULING_REQUIRED: unsupported or duplicate metamagic")
    if "SILENCED" in a.statuses and "silent" not in modifiers:
        # Simplification: every catalog spell is treated as having a verbal
        # component; Silent Spell is the authored way around it.
        raise ActionError("silenced: this spell needs Silent Spell metamagic")
    counted=[m for m in modifiers if m not in {"silent","still"}]
    if "quicken" in counted and len(counted)>1:
        raise ActionError("Quicken is exclusive")
    if any(m in modifiers for m in {"extend"}) and not spec.get("duration"):
        raise ActionError("Extend requires an implemented duration")
    if "widen" in modifiers and not spec.get("radius"):
        raise ActionError("Widen requires an area spell")
    bonus=spec.get("bonus",False) or "quicken" in modifiers
    maximum=spec["range"]*(2 if "enlarge" in modifiers else 1)
    events=[]
    if spec.get("full_turn"):
        current=economy(run,key)
        if current["movement"] != r.get("fly_speed",a.speed) or not current["action"] or not current["bonus"] or not current["reaction"]:
            raise ActionError("Niv's Descent requires an unspent entire turn")
    targets=action.get("targets",[])
    if not isinstance(targets,list) or len(set(targets))!=len(targets):
        raise ActionError("targets must be distinct actor IDs")
    if spec["operation"]=="teleport":
        destination=action.get("destination")
        if not isinstance(destination,list) or len(destination)!=3 or any(type(x)is not int or x<0 or x>120 or x%5 for x in destination):
            raise ActionError("teleport destination must be a visible grid point")
        if max(abs(position(run,key)[i]-destination[i]) for i in range(3))>maximum:
            raise ActionError("teleport out of range")
        if destination in run.context["combat"]["terrain"]["blocked"]:
            raise ActionError("teleport destination obstructed")
    elif spec["operation"] == "niv_descent":
        if action.get("dive") is not True:
            raise ActionError("Niv's Descent requires an intentional dive")
    elif spec["operation"] == "forcecage":
        if len(targets) != 1:
            raise ActionError("Forcecage requires exactly one target")
    elif spec["operation"] == "gate":
        plane=action.get("plane")
        if not isinstance(plane,str) or not plane.strip():
            raise ActionError("Gate requires a named destination plane")
        named=action.get("named_creature")
        if named is not None and (not isinstance(named,str) or not named.strip()):
            raise ActionError("Gate named_creature must be a non-empty name")
    elif spec["operation"] == "time_stop":
        if targets or action.get("center") is not None:
            raise ActionError("Time Stop cannot target another creature or area")
    elif spec["operation"] == "imprisonment":
        if len(targets) != 1:
            raise ActionError("Imprisonment requires exactly one target")
        if action.get("mode") not in {"burial","chaining","hedged prison","minimus containment","slumber","thralldom"}:
            raise ActionError("Imprisonment requires an explicit 5e mode")
    elif spec["operation"] == "utility":
        if len(targets) > spec.get("targets_max", 20):
            raise ActionError("utility spell target count exceeds its declared limit")
    elif spec.get("radius"):
        center=action.get("center")
        if not isinstance(center,list) or len(center)!=3 or any(type(x)is not int or x%5 for x in center):
            raise ActionError("area spell requires a grid center")
        if max(abs(position(run,key)[i]-center[i]) for i in range(3))>maximum:
            raise ActionError("spell center out of range")
        radius=spec["radius"]*(2 if "widen" in modifiers else 1)
        targets=[k for k,v in actors(run).items() if v.alive and max(abs(position(run,k)[i]-center[i]) for i in range(3))<=radius]
    elif not targets or len(targets)> (spec.get("darts",1)):
        raise ActionError("spell needs its supported target count")
    for target in targets:
        if not spec.get("radius"):
            check_target(run,key,target,maximum,enemy=spec["operation"]!="heal")
    if spec.get("full_turn"):
        use(run,key,"action");use(run,key,"bonus");use(run,key,"reaction")
        economy(run,key)["movement"] = 0
    elif len(counted)>=3:
        if economy(run,key)["movement"] != r.get("fly_speed",a.speed) or not economy(run,key)["bonus"] or not economy(run,key)["reaction"]:
            raise ActionError("three metamagics require an unspent entire turn")
        use(run,key,"action");use(run,key,"bonus");use(run,key,"reaction")
        economy(run,key)["movement"]=0
    elif spec["operation"] == "utility":
        use(run,key,"bonus" if bonus else "action")
        events.append({"type": "utility", "actor": key, "spell": spell_id,
                       "targets": list(targets), "duration": spec.get("duration"),
                       "concentration": bool(spec.get("concentration")),
                       "evidence": {"rules_authority": spec["authority"],
                                    "state_committed": True}})
    else:
        use(run,key,"bonus" if bonus else "action")
        if len(counted)==2:
            if bonus: raise ActionError("two metamagics need a separate bonus-action tax")
            use(run,key,"bonus")
    metamagic_cost=sum(costs[m] for m in modifiers)
    if metamagic_cost:
        if a.resources.get("sorcery_points", 0) >= metamagic_cost:
            spend(a, "sorcery_points", metamagic_cost)
        elif a.resources.get("casting_energy", 0) >= metamagic_cost:
            spend(a, "casting_energy", metamagic_cost)
        else:
            slot_key = next((f"slot_{lvl}_general" for lvl in range(metamagic_cost, 10) if a.resources.get(f"slot_{lvl}_general", 0) > 0), None)
            if slot_key:
                spend(a, slot_key, 1)
            elif custom_caster:
                spend(a, "casting_energy", metamagic_cost)
            else:
                spend(a, "sorcery_points", metamagic_cost)
    if spec.get("resource"):
        spend(a,spec["resource"])
    elif spec["level"]:
        spend(a,"casting_energy",spec["level"]) if custom_caster else spend(a,f"slot_{spec['level']}_general")
    if spec.get("concentration"):end_concentration(run,key)
    if spec["operation"]=="teleport":
        run.context["combat"]["positions"][key]=destination
        events.append({"type":"teleport","actor":key,"destination":destination})
    elif spec["operation"] == "niv_descent":
        origin=position(run,key)
        shockwave=[]; wave=[]
        for target, creature in actors(run).items():
            if not creature.alive or target == key:
                continue
            distance_from_origin=max(abs(origin[i]-position(run,target)[i]) for i in range(3))
            if distance_from_origin <= spec["shockwave_radius"]:
                save=saving_throw(run,target,spec["shockwave_save"],22,magical=True)
                result={"target":target,"save":save,"rough_terrain":True,
                        "disadvantage_next_attack":not save["success"]}
                rules(run,target)["rough_terrain_until"]=run.round_number + (2 if action.get("shape") == "wall" else 1)
                if not save["success"]:
                    rules(run,target)["disadvantage_next_attack_until"]=run.round_number+1
                shockwave.append(result)
            if distance_from_origin <= spec["elemental_radius"]:
                amount,rolls=dice(run,spec["elemental_dice"])
                save=saving_throw(run,target,spec["elemental_save"],22,magical=True)
                if target[0] == key[0]:
                    result=heal(run,target,spec["elemental_dice"])
                    if rules(run,target).get("identity") == "doran":
                        result=heal(run,target,"8d6")
                else:
                    if save["success"]:
                        amount//=2
                    # The source calls this an elemental wave rather than a
                    # fixed school; FIRE is the engine's explicit elemental
                    # lane and remains visible in the resolution evidence.
                    result=damage(run,key,target,amount,"FIRE")
                    result["damage_before_half"]=amount*2 if save["success"] else amount
                    result["damage_after_save"]=amount
                wave.append({"target":target,"save":save,"rolls":rolls,"result":result})
        events.append({"type":"niv_descent","actor":key,"dive":True,"shockwave":shockwave,"elemental_wave":wave,
                       "evidence":{"shockwave_radius":spec["shockwave_radius"],"elemental_radius":spec["elemental_radius"],
                                   "shockwave_dc":22,"elemental_dc":22,"full_turn":True}})
    elif spec["operation"] == "forcecage":
        target=targets[0]
        object_id=f"forcecage-{run.round_number}-{len(run.context['combat']['terrain'].get('structures',[]))}"
        structure={"object_id":object_id,"kind":"forcecage","name":"Forcecage",
                   "position":list(position(run,target)),"hp":1,"indestructible":True,
                   "occupants":[target],"escape":"Portal 14 or an authored escape ruling"}
        run.context["combat"]["terrain"].setdefault("structures",[]).append(structure)
        rules(run,target)["contained_by"]=object_id
        events.append({"type":"forcecage","actor":key,"target":target,
                       "structure":copy.deepcopy(structure),
                       "evidence":{"save":False,"spatial_containment":True,
                                   "mind_immunity_irrelevant":True}})
    elif spec["operation"] == "gate":
        plane=action["plane"]
        portal_id=f"gate-{run.round_number}-{len(run.context['combat'].get('portals',[]))}"
        portal={"portal_id":portal_id,"kind":"gate","plane":plane,
                "opened_by":key,"named_creature":action.get("named_creature"),
                "concentration_bound":True}
        run.context["combat"].setdefault("portals",[]).append(portal)
        events.append({"type":"gate","actor":key,"portal":copy.deepcopy(portal),
                       "evidence":{"concentration":True,"plane":plane,
                                   "named_pull":action.get("named_creature") is not None}})
    elif spec["operation"] == "time_stop":
        roll,rolls=dice(run,"1d4+1")
        run.context["combat"]["time_stop"]={"owner":key,"remaining":roll,
                                               "rolls":rolls,"ended_by":None}
        events.append({"type":"time_stop","actor":key,"turns":roll,
                       "rolls":rolls,"evidence":{"uninterrupted":True,
                                                  "ends_on_affecting_another":True}})
    elif spec["operation"] == "imprisonment":
        target=targets[0]
        save=saving_throw(run,target,"CHA",22,magical=True)
        event={"type":"imprisonment","actor":key,"target":target,"mode":action["mode"],"save":save,"applied":False}
        if not save["success"]:
            object_id=f"imprisonment-{run.round_number}-{len(run.context['combat']['terrain'].get('structures',[]))}"
            structure={"object_id":object_id,"kind":"imprisonment","name":"Imprisonment","position":list(position(run,target)),"hp":None,"indestructible":True,"occupants":[target],"mode":action["mode"],"escape":"No escape rule is inferred; resolve only by the registered mode."}
            run.context["combat"]["terrain"].setdefault("structures",[]).append(structure)
            rules(run,target)["contained_by"]=object_id
            event.update({"applied":True,"structure":copy.deepcopy(structure),"evidence":{"spatial_containment":True,"mind_altering":False,"visible_tell":True}})
        events.append(event)
    else:
        for repeat in range(2 if "twin" in modifiers else 1):
            amount,rolls=(dice(run,spec["dice"],maximize="maximize" in modifiers) if "dice" in spec else (0,[]))
            if "empower" in modifiers: amount=int(amount*1.5)
            for target in targets:
                if spec["operation"]=="heal":
                    events.append(heal(run,target,spec["dice"]))
                    continue
                spell_dc = r.get("spell_save_dc", 22)
                spell_attack = r.get("spell_attack_bonus", 14)
                check=saving_throw(run,target,spec["save"],spell_dc,magical=True) if spec.get("save") else {"success":False}
                if "careful" in modifiers and target[0]==key[0]: check={"success":True,"reason":"Careful"}
                if spec["operation"]=="condition":
                    events.append({"target":target,"type":"condition","save":check,"result":None if check["success"] else condition(run,target,spec["condition"],spec.get("duration",1)*(2 if "extend" in modifiers else 1),mental=spec.get("mental",False))})
                elif spec["operation"]=="attack":
                    hit=roll_check(run,spell_attack,actor(run,target).armor_class)
                    hit["success"]=hit["natural"]!=1 and (hit["natural"]==20 or hit["success"])
                    if hit["natural"]==20: amount,rolls=dice(run,spec["dice"],critical=True)
                    events.append({"target":target,"type":"attack","attack":hit,"result":damage(run,key,target,amount,spec["damage_type"]) if hit["success"] else None})
                elif spec["operation"]=="darts":
                    if len(targets)!=1: raise ActionError("robe darts currently require one target; distribution needs a ruling")
                    for _ in range(spec["darts"]):
                        value,individual=dice(run,spec["dice"])
                        events.append({"target":target,"type":"dart","rolls":individual,"result":damage(run,key,target,value,spec["damage_type"])})
                else:
                    resolved=amount//2 if check["success"] and spec.get("half") else 0 if check["success"] else amount
                    events.append({"target":target,"type":"damage","rolls":rolls,"save":check,"result":damage(run,key,target,resolved,spec["damage_type"])})
    if spec.get("concentration"):
        run.context["combat"]["concentration"][key]={"spell":spell_id,"targets":targets,
            "conditions":[spec["condition"]] if "condition" in spec else [],"remaining":spec.get("duration",10),"repeat_save":spec.get("save")}
    receipt = {"type":"cast","actor":key,"spell":spell_id,"ruling":spec,"metamagic":modifiers,"events":events}
    if events and isinstance(events[0], dict):
        if "attack" in events[0]:
            receipt["roll"] = events[0]["attack"]
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
