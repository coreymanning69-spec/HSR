"""Run-local Prefix/Suffix projection for the live dungeon resolver.

The content catalog is declarative.  This module is the narrow bridge that
turns an identified, equipped Imprint into combat, skill, and utility facts.
It deliberately reads only active HSR affixes; the staged Endless Engagement
import remains design/reference material until it is promoted explicitly.
"""

from __future__ import annotations

import copy

from hollowstar.loader import load_affixes


def _catalog():
    return load_affixes()


def materialize(name: str | None, expected_type: str | None = None) -> dict | None:
    """Return a JSON-safe active affix record, or reject unknown/staged names."""
    if not name:
        return None
    affix = _catalog().get(str(name))
    if affix is None or (expected_type and affix.affix_type != expected_type):
        return None
    return {
        "name": affix.name, "affix_type": affix.affix_type,
        "description": affix.description,
        "effects": [
            {
                "name": effect.name, "phase": effect.phase.name,
                "direction": effect.direction.name, "tier": effect.tier.name,
                "scope": effect.scope.name, "condition": effect.condition,
                "flat_bonus": effect.flat_bonus, "multiplier": effect.multiplier,
                "per_stack_bonus": effect.per_stack_bonus,
                "per_stack_source": effect.per_stack_source,
                "grants_tags": sorted(tag.name for tag in effect.grants_tags),
                "opens_gate": effect.opens_gate, "closes_gate": effect.closes_gate,
                "inflicts_status": effect.inflicts_status,
                "status_duration": effect.status_duration,
                "save_ability": effect.save_ability,
                "save_dc": effect.save_dc,
                "charges": effect.charges, "tell": effect.tell,
                "description": effect.description,
            }
            for effect in affix.effects
        ],
    }


def materialize_item_affixes(item: dict) -> dict:
    """Upgrade legacy string fields in-place without trusting arbitrary data."""
    for kind in ("prefix", "suffix"):
        value = item.get(kind)
        if isinstance(value, str):
            item[kind] = materialize(value, kind)
        elif isinstance(value, dict):
            name = value.get("name")
            canonical = materialize(name, kind)
            if canonical is not None:
                # Preserve only runtime charge depletion from an existing save.
                previous = value.get("effects", [])
                for index, effect in enumerate(canonical["effects"]):
                    if index < len(previous) and isinstance(previous[index], dict) and "charges" in previous[index]:
                        effect["charges"] = previous[index]["charges"]
                item[kind] = canonical
    return item


def display_name(item: dict) -> str:
    materialize_item_affixes(item)
    parts = []
    if isinstance(item.get("prefix"), dict) and item["prefix"].get("name"):
        parts.append(str(item["prefix"]["name"]))
    parts.append(str(item.get("name", "item")))
    if isinstance(item.get("suffix"), dict) and item["suffix"].get("name"):
        parts.append(str(item["suffix"]["name"]))
    return " ".join(parts)


def _equipped(run, actor_key: str) -> list[dict]:
    dungeon = run.context.get("dungeon", {})
    inventory = dungeon.get("inventory", {})
    equipped = dungeon.get("imprints", {}).get(actor_key, {})
    if not isinstance(inventory, dict) or not isinstance(equipped, dict):
        return []
    rows = []
    for item_id in equipped.values():
        item = inventory.get(item_id)
        if isinstance(item, dict) and item.get("identified"):
            rows.append(materialize_item_affixes(item))
    return rows


def effects(run, actor_key: str) -> list[tuple[dict, dict]]:
    """Return mutable active effect rows with their source.

    Equipped Imprints come first, then affixes decanted into the actor's
    Attunement Matrix. Both are live dicts, so charge depletion persists.
    """
    result = []
    for item in _equipped(run, actor_key):
        for kind in ("prefix", "suffix"):
            affix = item.get(kind)
            if isinstance(affix, dict):
                for effect in affix.get("effects", []):
                    if isinstance(effect, dict) and effect.get("charges") != 0:
                        result.append((effect, item))
    from hollowstar.attunement import attuned_affixes
    for affix, source in attuned_affixes(run, actor_key):
        for effect in affix.get("effects", []):
            if isinstance(effect, dict) and effect.get("charges") != 0:
                result.append((effect, source))
    return result


def _matches(effect: dict, attacker, defender) -> bool:
    condition = effect.get("condition", "always")
    if condition in (None, "", "always"):
        return True
    if condition == "enemy_full_hp":
        return defender.hp >= defender.max_hp
    if condition == "enemy_bloodied":
        return defender.hp <= defender.max_hp // 2
    if condition == "enemy_casting":
        return "CASTING" in defender.statuses
    if condition == "self_bloodied":
        return attacker.hp <= attacker.max_hp // 2
    if condition == "target_has_status":
        return bool(defender.statuses)
    return False


def offensive_tags(run, actor_key: str, base: set[str]) -> set[str]:
    tags = set(base)
    for effect, _item in effects(run, actor_key):
        if effect.get("phase") in {"PERMISSION", "PERSISTENCE", "MAGNITUDE"}:
            tags.update(str(tag) for tag in effect.get("grants_tags", []))
    return tags


def targeting_denial(run, source: str, target: str) -> dict | None:
    """Spend one eligible defensive targeting charge and return public evidence."""
    from hollowstar import tactical as t
    attacker, defender = t.actor(run, source), t.actor(run, target)
    for effect, item in effects(run, target):
        if (effect.get("phase") == "TARGETING" and effect.get("direction") == "DENY"
                and _matches(effect, attacker, defender)):
            charges = effect.get("charges")
            if isinstance(charges, int):
                effect["charges"] = charges - 1
            return {"effect": effect.get("name"), "item": display_name(item),
                    "tell": effect.get("tell", ""), "charges_after": effect.get("charges")}
    return None


def attack_adjustment(run, source: str, target: str, amount: int) -> tuple[int, list[dict], list[dict]]:
    """Resolve active MAGNITUDE and CONSEQUENCE effects for a confirmed hit."""
    from hollowstar import tactical as t
    attacker, defender = t.actor(run, source), t.actor(run, target)
    matched = [(effect, item) for effect, item in effects(run, source) if _matches(effect, attacker, defender)]
    magnitude = [(effect, item) for effect, item in matched if effect.get("phase") == "MAGNITUDE"
                 and effect.get("direction") == "MODIFY"]
    for effect, _item in magnitude:
        amount += int(effect.get("flat_bonus", 0) or 0)
        if effect.get("per_stack_bonus") and effect.get("per_stack_source") == "debuffs_on_target":
            amount += int(effect["per_stack_bonus"]) * len(defender.statuses)
    for effect, _item in magnitude:
        amount = int(amount * float(effect.get("multiplier", 1) or 1))
    riders = []
    for effect, item in matched:
        if effect.get("phase") == "CONSEQUENCE" and effect.get("direction") == "GRANT" and effect.get("inflicts_status"):
            rider = {"name": str(effect["inflicts_status"]), "duration": int(effect.get("status_duration", 1) or 1),
                     "source_effect": effect.get("name")}
            if effect.get("save_ability") and effect.get("save_dc"):
                rider["save"] = {"ability": str(effect["save_ability"]).upper(), "dc": int(effect["save_dc"])}
            riders.append(rider)
            if isinstance(effect.get("charges"), int):
                effect["charges"] -= 1
    applied = [{"effect": effect.get("name"), "item": display_name(item),
                "flat_bonus": effect.get("flat_bonus", 0), "multiplier": effect.get("multiplier", 1)}
               for effect, item in magnitude]
    return max(0, amount), applied, riders


def _active_modifiers(run, actor_key: str) -> list[dict]:
    """Rune modifiers from equipped Imprints plus attuned Legendary slots."""
    from hollowstar.attunement import attuned_modifiers
    rows = [modifier for item in _equipped(run, actor_key) for modifier in item.get("modifiers", [])]
    rows.extend(attuned_modifiers(run, actor_key))
    return [modifier for modifier in rows if isinstance(modifier, dict)]


def damage_resistances(run, actor_key: str) -> set[str]:
    result = set()
    for modifier in _active_modifiers(run, actor_key):
        if modifier.get("effect") == "resistance":
            result.add(str(modifier.get("value", "")).upper())
    return result


def skill_bonus(run, actor_key: str, skill: str) -> int:
    """Add explicit Rune skill modifiers; untyped modifiers never leak into checks."""
    total = 0
    for modifier in _active_modifiers(run, actor_key):
        if modifier.get("effect") != "skill_bonus":
            continue
        allowed = modifier.get("skill")
        if allowed in (None, "", skill, "all"):
            total += int(modifier.get("value", 0) or 0)
    return total
