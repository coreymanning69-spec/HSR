"""Deterministic, composable Hollow Star character creation."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from hollowstar.actors import DND_ABILITIES
from hollowstar.profiles import ProfileError, _integer, normalize_appearance, presentation_sprite_id
from hollowstar.rng import RunRNG


REGISTRY_PATH = Path(__file__).with_name("content") / "character_creation.json"
REGISTRY_SCHEMA = "hollow-star-character-creation-1"
BUILDER_VERSION = "hollow-star-character-builder-3"



def _registry() -> dict:
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError("character creation registry is unavailable") from exc
    if not isinstance(data, dict) or data.get("schema") != REGISTRY_SCHEMA:
        raise ProfileError("character creation registry contract mismatch")
    return data


def _slug(value: object, label: str, choices: dict) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"{label} must be a non-empty string")
    wanted = value.strip().lower().replace("_", "-").replace(" ", "-")
    aliases = {key.lower(): key for key in choices}
    aliases.update({row["name"].lower().replace(" ", "-"): key for key, row in choices.items()})
    if wanted not in aliases:
        raise ProfileError(f"unsupported {label} {value!r}; available: {', '.join(row['name'] for row in choices.values())}")
    return aliases[wanted]


def options() -> dict:
    data = _registry()
    return {
        "schema": data["schema"], "version": data["version"],
        "ability_method": data["ability_method"], "rerolls": 1,
        "level_range": data["level_range"], "default_level": data["default_level"],
        "races": [{"id": key, **copy.deepcopy(row)} for key, row in data["races"].items()],
        "classes": [{"id": key, **copy.deepcopy(row)} for key, row in data["classes"].items()],
        "backgrounds": [{"id": key, **copy.deepcopy(row)} for key, row in data["backgrounds"].items()],
        "skills": copy.deepcopy(data["skills"]),
        # Cosmetic pickers.  Options carry their own `races` gate where one
        # applies, so the creator can filter without duplicating that rule.
        "appearance": copy.deepcopy(data.get("appearance", {})),
        "spell_budget": "5 x level for Magician and Cleric; cantrip 1, ranked spell rank + 1",
        "assist": ["ability_assignment", "advancements", "skills", "spells"],
        "note": "Any listed race and one listed class compose. Specializations and multiclassing are reserved, not silently simulated.",
    }


def roll_abilities(seed: str | int, roll_set: int = 0) -> dict:
    if isinstance(seed, bool) or not isinstance(seed, (str, int)) or not str(seed):
        raise ProfileError("creation_seed must be a non-empty string or integer")
    roll_set = _integer(roll_set, "roll_set", 0, 1)
    rng = RunRNG(seed).fork(f"abilities:{roll_set}")
    rows = []
    for _ in DND_ABILITIES:
        dice = [rng.randint(1, 6) for _ in range(4)]
        dropped = min(dice)
        rows.append({"dice": dice, "dropped": dropped, "total": sum(dice) - dropped})
    return {"method": "4d6-drop-lowest", "creation_seed": str(seed), "roll_set": roll_set,
            "rolls": rows, "scores": [row["total"] for row in rows]}


def _auto_assignment(scores: list[int], primary: list[str]) -> dict[str, int]:
    ability_order = list(primary) + [ability for ability in DND_ABILITIES if ability not in primary]
    return dict(zip(ability_order, sorted(scores, reverse=True)))


def _assignment(value: object, scores: list[int], primary: list[str]) -> dict[str, int]:
    if value in (None, "auto"):
        return _auto_assignment(scores, primary)
    if not isinstance(value, dict) or set(value) != set(DND_ABILITIES):
        raise ProfileError("ability_assignment must be auto or contain all six abilities")
    out = {ability: _integer(value[ability], ability, 3, 18) for ability in DND_ABILITIES}
    if sorted(out.values()) != sorted(scores):
        raise ProfileError("ability_assignment must use each rolled score exactly once")
    return out


def _advance(scores: dict[str, int], value: object, points: int, primary: list[str], cap: int) -> tuple[dict, dict]:
    allocation = {ability: 0 for ability in DND_ABILITIES}
    if value in (None, "auto"):
        order = list(primary) + [ability for ability in DND_ABILITIES if ability not in primary]
        for _ in range(points):
            target = next((ability for ability in order if scores[ability] + allocation[ability] < cap), None)
            if target is None:
                raise ProfileError("advancement points cannot be allocated below the creation cap")
            allocation[target] += 1
    else:
        if not isinstance(value, dict) or set(value) - set(DND_ABILITIES):
            raise ProfileError("advancements must be auto or an ability-point object")
        allocation.update({ability: _integer(amount, f"advancement {ability}", 0, points)
                           for ability, amount in value.items()})
        if sum(allocation.values()) != points:
            raise ProfileError(f"advancements must allocate exactly {points} points")
    final = {ability: scores[ability] + allocation[ability] for ability in DND_ABILITIES}
    if any(score > cap for score in final.values()):
        raise ProfileError(f"advancements cannot raise an ability above {cap}")
    return final, allocation


def _choose_skills(value: object, class_row: dict, race_row: dict, seed: str) -> list[str]:
    registry = _registry()
    count = class_row["skill_count"] + race_row.get("extra_skills", 0)
    available = list(dict.fromkeys(class_row["skills"] + list(registry["skills"])))
    if value in (None, "auto"):
        rng = RunRNG(seed).fork("skills")
        class_choices = list(class_row["skills"]); chosen = []
        while class_choices and len(chosen) < class_row["skill_count"]:
            pick = rng.choice(class_choices); class_choices.remove(pick); chosen.append(pick)
        remaining = [skill for skill in available if skill not in chosen]
        while len(chosen) < count:
            pick = rng.choice(remaining); remaining.remove(pick); chosen.append(pick)
        return chosen
    if not isinstance(value, list) or len(value) != count or len(set(value)) != count:
        raise ProfileError(f"choose exactly {count} distinct trained skills")
    if any(skill not in available for skill in value):
        raise ProfileError("unsupported trained skill")
    if sum(skill in class_row["skills"] for skill in value) < class_row["skill_count"]:
        raise ProfileError(f"at least {class_row['skill_count']} skills must come from the class list")
    return list(value)


def _spell_specs() -> dict:
    from hollowstar.spells import SPELLS, CLERIC_SPELLS
    return SPELLS | CLERIC_SPELLS


def _choose_spells(value: object, class_row: dict, level: int, budget: int, seed: str) -> tuple[list[str], int]:
    allowed = class_row.get("spells", [])
    if not allowed:
        if budget or value not in (None, "auto", []):
            raise ProfileError("this class does not use a spell budget")
        return [], 0
    specs = _spell_specs(); rank_cap = min(9, (level + 1) // 2)
    eligible = [spell for spell in allowed if spell in specs and specs[spell].get("level", 0) <= rank_cap]
    def cost(spell: str) -> int:
        rank = specs[spell].get("level", 0)
        return 1 if rank == 0 else rank + 1
    if value in (None, "auto"):
        rng = RunRNG(seed).fork(f"spells:{class_row['name'].lower()}")
        pool = list(eligible); chosen = []; remaining = budget
        signature = next((spell for spell in pool if specs[spell].get("level", 0) == 0), None)
        if signature is not None and cost(signature) <= remaining:
            pool.remove(signature); chosen.append(signature); remaining -= cost(signature)
        while pool:
            affordable = [spell for spell in pool if cost(spell) <= remaining]
            if not affordable:
                break
            pick = rng.choice(affordable); pool.remove(pick); chosen.append(pick); remaining -= cost(pick)
        return sorted(chosen), budget - remaining
    if not isinstance(value, list) or len(set(value)) != len(value) or any(spell not in eligible for spell in value):
        raise ProfileError("spells must be distinct entries from the class list within the level rank cap")
    spent = sum(cost(spell) for spell in value)
    if spent > budget:
        raise ProfileError(f"spell selections cost {spent}, above the budget of {budget}")
    return list(value), spent


def _origin(seed: str) -> dict:
    table = _registry()["origin_table"]; total = sum(row["weight"] for row in table)
    rng = RunRNG(seed).fork("origin")
    try:
        row = rng.weighted_choice(table, [item["weight"] for item in table])
    except ValueError as exc:
        raise ProfileError("origin table has invalid weights") from exc
    # Preserve the public receipt shape. The weighted selector intentionally
    # does not expose the PRNG's internal float; this is the first integer
    # slot occupied by the selected row in the cumulative table.
    row_start = 1 + sum(item["weight"] for item in table[:table.index(row)])
    return {**copy.deepcopy(row), "roll": row_start, "table_total": total}


def _background_gold(seed: str, background: dict) -> dict:
    spec = background["gold"]
    rng = RunRNG(seed).fork("background-gold")
    dice = [rng.randint(1, spec["sides"]) for _ in range(spec["dice"])]
    return {"dice": dice, "sides": spec["sides"], "bonus": spec["bonus"],
            "total": sum(dice) + spec["bonus"],
            "formula": f"{spec['dice']}d{spec['sides']}+{spec['bonus']}"}


def _heirloom(seed: str, origin_id: str) -> dict:
    rng = RunRNG(seed).fork("heirloom")
    roll = rng.randint(1, 100)
    result = {"roll": roll, "threshold": 20, "triggered": roll <= 20, "item": None}
    if not result["triggered"]:
        return result
    rows = [copy.deepcopy(row) for row in _registry()["origin_table"]
            if row["category"] == "heirloom" and row["id"] != origin_id]
    if not rows:
        raise ProfileError("heirloom table cannot avoid duplicating the origin item")
    result["item"] = rng.weighted_choice(rows, [row["weight"] for row in rows])
    return result


def _equipment(class_row: dict, mods: dict[str, int], prof: int) -> tuple[list[dict], int, str]:
    equipment = copy.deepcopy(class_row["equipment"])
    armor = next((item for item in equipment if item.get("base_ac")), None)
    ac = 10 + mods["DEX"]
    if armor:
        dex = mods["DEX"]
        if armor.get("dex_cap") is not None:
            dex = min(dex, armor["dex_cap"])
        ac = armor["base_ac"] + dex
    ac += sum(item.get("shield_bonus", 0) for item in equipment)
    damage_type = "SLASHING"
    for item in equipment:
        if item.get("damage_dice"):
            ability = item.get("attack_ability", "STR")
            item["damage_modifier"] = mods[ability]
            item["attack_bonus"] = mods[ability] + prof
            damage_type = item.pop("damage_type", damage_type)
        else:
            item.pop("damage_type", None)
    return equipment, ac, damage_type


def _hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def preview(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ProfileError("character build must be an object")
    allowed = {"name", "creation_seed", "roll_set", "race", "gender", "character_class", "level",
               "ability_assignment", "ability_scores", "floating_bonuses", "advancements",
               "skills", "spell_budget", "spells", "background", "appearance"}
    if set(data) - allowed:
        raise ProfileError(f"unsupported character build fields: {sorted(set(data) - allowed)}")
    registry = _registry(); races = registry["races"]; classes = registry["classes"]; backgrounds = registry["backgrounds"]
    race_id = _slug(data.get("race", "human"), "race", races)
    class_id = _slug(data.get("character_class", "warrior"), "class", classes)
    background_id = _slug(data.get("background", "veteran"), "background", backgrounds)
    race_row, class_row, background_row = races[race_id], classes[class_id], backgrounds[background_id]
    # Cosmetic only -- resolved here purely so the race gate applies, and never
    # read by the ability, AC, or roll paths below.
    appearance = normalize_appearance(data.get("appearance"), registry.get("appearance", {}), race_id)
    raw_gender = str(data.get("gender", "other")).strip().lower()
    # Accept legacy labels on stored/imported sheets, but emit the public vocabulary.
    gender_aliases = {"feminine": "female", "masculine": "male"}
    gender = gender_aliases.get(raw_gender, raw_gender)
    if gender not in {"male", "female", "other"}:
        raise ProfileError("gender must be male, female, or other")
    level = _integer(data.get("level", registry["default_level"]), "level", *registry["level_range"])
    seed = data.get("creation_seed", data.get("name"))
    if isinstance(seed, bool) or not isinstance(seed, (str, int)) or not str(seed).strip():
        raise ProfileError("creation_seed or character name is required")
    seed = str(seed); roll_set = _integer(data.get("roll_set", 0), "roll_set", 0, 1)
    roll_receipts = [roll_abilities(seed, 0)]
    if roll_set == 1:
        roll_receipts.append(roll_abilities(seed, 1))
    rolled = roll_receipts[-1]["scores"]
    if "ability_scores" in data:
        explicit = data["ability_scores"]
        if not isinstance(explicit, dict) or set(explicit) != set(DND_ABILITIES):
            raise ProfileError("ability_scores must contain exactly the six D&D abilities")
        assigned = {ability: _integer(explicit[ability], ability, 3, 18) for ability in DND_ABILITIES}
        if all(score == 18 for score in assigned.values()):
            raise ProfileError("ability_scores cannot set all six abilities to 18; use the rolled score set")
        assignment_source = "explicit legacy input"
    else:
        assigned = _assignment(data.get("ability_assignment", "auto"), rolled, class_row["primary"])
        assignment_source = f"roll set {roll_set}"
    applied_bonuses = {ability: race_row.get("bonuses", {}).get(ability, 0) for ability in DND_ABILITIES}
    floating = []
    if race_row.get("floating_bonus"):
        rule = race_row["floating_bonus"]; raw = data.get("floating_bonuses", "auto")
        available = [ability for ability in class_row["primary"] + list(DND_ABILITIES) if ability not in rule["exclude"]]
        if raw in (None, "auto"):
            floating = list(dict.fromkeys(available))[:rule["count"]]
        elif (not isinstance(raw, list) or len(raw) != rule["count"] or len(set(raw)) != rule["count"]
              or any(ability not in DND_ABILITIES or ability in rule["exclude"] for ability in raw)):
            raise ProfileError("floating_bonuses must select two distinct non-CHA abilities")
        else:
            floating = list(raw)
        for ability in floating:
            applied_bonuses[ability] += rule["amount"]
    cap = registry["creation_score_cap"]
    ancestry = {ability: min(cap, assigned[ability] + applied_bonuses[ability]) for ability in DND_ABILITIES}
    background_bonus = {ability: 1 if ability == background_row["ability"] else 0 for ability in DND_ABILITIES}
    post_background = {ability: min(cap, ancestry[ability] + background_bonus[ability]) for ability in DND_ABILITIES}
    advancement_points = 2 * sum(level >= threshold for threshold in registry["advancement_levels"])
    final_scores, advancement = _advance(post_background, data.get("advancements", "auto"), advancement_points,
                                         class_row["primary"], cap)
    mods = {ability: (score - 10) // 2 for ability, score in final_scores.items()}; prof = 2 + (level - 1) // 4
    trained = _choose_skills(data.get("skills", "auto"), class_row, race_row, seed)
    skill_bonuses = {skill: mods[registry["skills"][skill]] + prof for skill in trained}
    if class_id == "rogue":
        for skill in trained[:2]: skill_bonuses[skill] += prof
    for skill, bonus in race_row.get("skill_bonuses", {}).items():
        skill_bonuses[skill] = skill_bonuses.get(skill, 0) + bonus
    caster = bool(class_row.get("spells")); max_spell_budget = 5 * level if caster else 0
    spell_budget = _integer(data.get("spell_budget", max_spell_budget), "spell_budget", 0, max_spell_budget)
    known_spells, spell_spent = _choose_spells(data.get("spells", "auto"), class_row, level, spell_budget, seed)
    equipment, armor_class, damage_type = _equipment(class_row, mods, prof)
    origin = _origin(seed)
    heirloom = _heirloom(seed, origin["id"])
    background_gold = _background_gold(seed, background_row)
    equipment.extend(copy.deepcopy(background_row["gear"]))
    equipment.append({key: origin[key] for key in ("name", "slot", "flavor") if key in origin})
    if heirloom["item"] is not None:
        equipment.append({key: heirloom["item"][key] for key in ("name", "slot", "flavor") if key in heirloom["item"]})
    fixed = {10: 6, 8: 5, 6: 4}[class_row["hit_die"]]
    max_hp = max(1, class_row["hit_die"] + mods["CON"] + (level - 1) * max(1, fixed + mods["CON"]))
    resources = {}; attacks = 1
    if class_id == "warrior":
        resources["second_wind"] = 1; attacks = 4 if level >= 17 else 3 if level >= 11 else 2 if level >= 5 else 1
    elif class_id == "archer": attacks = 3 if level >= 11 else 2 if level >= 5 else 1
    elif class_id == "magician": resources.update({"casting_energy": level + 2, "arcane_recovery": 1})
    elif class_id == "cleric": resources.update({"casting_energy": level + 2, "channel_grace": 1})
    saves = {ability: mods[ability] + (prof if ability in class_row["saves"] else 0) for ability in DND_ABILITIES}
    rules = {
        "builder": BUILDER_VERSION, "registry_version": registry["version"], "identity": "custom",
        "race_id": race_id, "gender": gender, "class_id": class_id, "background_id": background_id, "level": level, "saves": saves,
        "attacks": attacks, "damage_type": damage_type, "features": list(class_row["features"]),
        "interaction_tags": list(race_row["interaction_tags"]), "known_spells": list(known_spells),
        "spell_rank_cap": min(9, (level + 1) // 2) if caster else 0,
        "spell_attack_bonus": prof + mods["INT" if class_id == "magician" else "WIS"] if caster else 0,
        "spell_save_dc": 8 + prof + mods["INT" if class_id == "magician" else "WIS"] if caster else 0,
        "casting_energy_max": level + 2 if caster else 0,
        "origin_hook": origin.get("hook"), "origin_item_id": origin["id"],
        "starting_gold": background_gold["total"], "starting_gold_source": "custom_background",
        "sneak_attack_dice": (level + 1) // 2 if class_id == "rogue" else 0,
        "aim": class_id == "archer", "cunning_action": class_id == "rogue" and level >= 2,
        "derivation": {"HP": f"d{class_row['hit_die']} maximum + CON, then {level-1} x ({fixed} + CON; minimum 1)",
                       "AC": f"equipment armor plus eligible DEX and shield = {armor_class}",
                       "proficiency": f"2 + floor(({level} - 1) / 4) = {prof}"},
    }
    receipt = {
        "schema": "hollow-star-character-creation-receipt-1", "builder": BUILDER_VERSION,
        "registry_version": registry["version"], "creation_seed": seed, "selected_roll_set": roll_set,
        "roll_sets": roll_receipts, "assignment_source": assignment_source, "assigned_scores": assigned,
        "race_bonuses": applied_bonuses, "gender": gender, "legacy_gender": raw_gender if raw_gender != gender else None, "floating_bonuses": floating, "post_race_scores": ancestry,
        "background": {"id": background_id, "name": background_row["name"], "ability": background_row["ability"],
                       "ability_bonus": background_bonus, "gold": background_gold,
                       "gear": copy.deepcopy(background_row["gear"])},
        "post_background_scores": post_background,
        "advancement_points": advancement_points, "advancements": advancement, "final_scores": final_scores,
        "trained_skills": trained, "spell_budget": spell_budget, "spell_points_spent": spell_spent,
        "known_spells": known_spells,
        "origin_roll": {"roll": origin["roll"], "out_of": origin["table_total"],
                        "item_id": origin["id"], "category": origin["category"]},
        "heirloom_roll": {"roll": heirloom["roll"], "threshold": heirloom["threshold"],
                          "triggered": heirloom["triggered"],
                          "item_id": heirloom["item"]["id"] if heirloom["item"] else None},
    }
    profile = {
        "name": data.get("name"), "race": race_row["name"], "race_id": race_id, "gender": gender,
        "sprite_id": presentation_sprite_id(race_id, gender), "appearance": appearance,
        "character_class": class_row["name"], "class_id": class_id, "background": {"id": background_id, "name": background_row["name"], "ability": background_row["ability"], "starting_gold": background_gold["total"], "gear": copy.deepcopy(background_row["gear"])}, "heirloom_item": copy.deepcopy(heirloom["item"] or {}), "specialization": "Unselected",
        "level": level, "hsr_rank": 1, "ability_scores": final_scores, "max_hp": max_hp,
        "armor_class": armor_class, "initiative_bonus": mods["DEX"], "speed": race_row["speed"],
        "proficiency_bonus": prof, "skill_bonuses": skill_bonuses, "resources": resources,
        "features": list(class_row["features"]), "interaction_tags": list(race_row["interaction_tags"]),
        "known_spells": known_spells, "origin_item": {key: origin[key] for key in origin if key != "weight"},
        "equipment": equipment, "build_rules": rules, "creation_receipt": receipt,
    }
    return {"profile": profile, "receipt": receipt,
            "build_hash": _hash({"profile": profile, "receipt": receipt})}


def build(data: dict) -> tuple[dict, dict]:
    """Compatibility wrapper for direct callers; the host uses preview plus hash."""
    result = preview(data)
    return result["profile"], result["profile"]["build_rules"]
