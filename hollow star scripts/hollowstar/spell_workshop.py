"""Isolated spell-construction and enchantment-name workshop.

This module is an experiment API. It never resolves combat and never alters a
live character or spell catalog. A composed recipe is data for future adapters.
"""
from __future__ import annotations

import copy
from pathlib import Path

from hollowstar.storage import atomic_json


SCHEMA = "hsr-spell-workshop-1"
METAMAGIC = {
    "energy": {"name": "Energy Substitution", "edition": "3.5e + 5e", "cost": 0, "requires": ["damage"], "effect": "choose a replacement damage type", "status": "parameterized"},
    "silent": {"name": "Silent", "edition": "3.5e", "cost": 0, "requires": ["verbal"], "effect": "remove verbal component", "status": "preview-only"},
    "still": {"name": "Still", "edition": "3.5e", "cost": 0, "requires": ["somatic"], "effect": "remove somatic component", "status": "preview-only"},
    "enlarge": {"name": "Enlarge / Distant", "edition": "3.5e + 5e", "cost": 1, "requires": ["range"], "effect": "double range", "status": "preview-only"},
    "extend": {"name": "Extend", "edition": "3.5e + 5e", "cost": 1, "requires": ["duration"], "effect": "double duration", "status": "preview-only"},
    "sculpt": {"name": "Sculpt", "edition": "3.5e", "cost": 1, "requires": ["area"], "effect": "reshape area and designate exclusions", "status": "parameterized"},
    "careful": {"name": "Careful", "edition": "5e", "cost": 1, "requires": ["save"], "effect": "chosen allies succeed on saves", "status": "preview-only"},
    "empower": {"name": "Empower", "edition": "3.5e + 5e", "cost": 2, "requires": ["numeric"], "effect": "multiply numeric effects by 1.5", "status": "preview-only"},
    "split_ray": {"name": "Split Ray", "edition": "3.5e", "cost": 2, "requires": ["ray"], "effect": "add a secondary ray target", "status": "parameterized"},
    "seeking": {"name": "Seeking", "edition": "3.5e", "cost": 2, "requires": ["spell_attack"], "effect": "reroll a missed spell attack", "status": "preview-only"},
    "maximize": {"name": "Maximize", "edition": "3.5e + 5e", "cost": 3, "requires": ["numeric"], "effect": "maximize numeric effects", "status": "preview-only"},
    "widen": {"name": "Widen", "edition": "3.5e", "cost": 3, "requires": ["area"], "effect": "double area", "status": "preview-only"},
    "chain": {"name": "Chain", "edition": "3.5e", "cost": 3, "requires": ["target"], "effect": "arc to secondary targets", "status": "parameterized"},
    "repeat": {"name": "Repeat", "edition": "3.5e", "cost": 3, "requires": ["duration"], "effect": "repeat next round without another action", "status": "deferred-effect"},
    "twin": {"name": "Twin", "edition": "3.5e + 5e", "cost": 4, "requires": ["target"], "effect": "apply spell twice", "status": "preview-only"},
    "quicken": {"name": "Quicken", "edition": "3.5e + 5e", "cost": 4, "requires": ["action"], "effect": "cast as a bonus action", "status": "preview-only"},
    "heighten": {"name": "Heighten", "edition": "3.5e + 5e", "cost": "variable", "requires": ["save"], "effect": "raise save DC by the declared amount", "status": "parameterized"},
}

_ALIASES = {row["name"].lower(): key for key, row in METAMAGIC.items()}
_ALIASES.update({key: key for key in METAMAGIC})
_ALIASES.update({"transmuted": "energy", "energy substitution": "energy", "distant": "enlarge", "extended": "extend", "sculpted spell": "sculpt", "split ray": "split_ray"})
_PREFIXES = {
    "energy": "Transmuted", "silent": "Whispering", "still": "Unmoving",
    "enlarge": "Far-reaching", "extend": "Enduring", "sculpt": "Sculpted",
    "careful": "Warded", "empower": "Empowered", "split_ray": "Forked",
    "seeking": "Seeking", "maximize": "Perfected", "widen": "Expansive",
    "chain": "Arcing", "repeat": "Echoing", "twin": "Twinned",
    "quicken": "Swift", "heighten": "Grave",
}
_SUFFIXES = {"damage": " of Ruin", "heal": " of Mending", "utility": " of Artifice", "condition": " of Binding", "teleport": " of Passage"}


class WorkshopError(ValueError):
    pass


def catalog() -> dict:
    """Return stable option descriptors for UI/CLI adapters."""
    return {"schema": SCHEMA, "scope": "sandbox/debug experiment; no live cast integration", "stacking": {
        "sorcery_point_cost": "sum of selected option costs plus declared variable costs",
        "one_option_turn_tax": "spell action only", "two_options_turn_tax": "spell action plus bonus action",
        "three_or_more_turn_tax": "entire turn: action, bonus action, reaction, and movement",
        "quicken": "exclusive with other counted metamagics; Silent/Still are uncounted per Wren rule",
    }, "options": copy.deepcopy(METAMAGIC)}


def _spell_catalog() -> dict:
    from hollowstar.spells import SPELLS, CLERIC_SPELLS
    return SPELLS | CLERIC_SPELLS


def _key(option: object) -> str:
    if not isinstance(option, str) or not option.strip():
        raise WorkshopError("each metamagic option must be a name or id")
    value = option.strip().lower().replace("-", "_")
    key = _ALIASES.get(value) or _ALIASES.get(value.replace("_", " "))
    if key is None:
        raise WorkshopError(f"unknown metamagic option: {option}")
    return key


def compose(spell_id: str, options: list, parameters: dict | None = None, *, spell_catalog: dict | None = None,
            available_sorcery_points: int | None = None) -> dict:
    """Validate and describe one experimental stack without executing effects."""
    spells = spell_catalog if spell_catalog is not None else _spell_catalog()
    if spell_id not in spells:
        raise WorkshopError("spell must use an exact registered spell@edition id")
    if not isinstance(options, list):
        raise WorkshopError("metamagic must be a list")
    selected = [_key(value) for value in options]
    if len(set(selected)) != len(selected):
        raise WorkshopError("a metamagic option cannot be selected twice yet")
    params = {} if parameters is None else parameters
    if not isinstance(params, dict):
        raise WorkshopError("parameters must be an object")
    spell = copy.deepcopy(spells[spell_id])
    props = {"action"}
    if spell.get("damage_type"):
        props |= {"damage", "numeric"}
    if spell.get("dice"):
        props.add("numeric")
    if spell.get("radius"):
        props.add("area")
    if spell.get("save"):
        props.add("save")
    if spell.get("duration"):
        props.add("duration")
    if spell.get("range") is not None:
        props.add("range")
    if spell.get("operation") == "attack":
        props |= {"spell_attack", "target"}
    if spell.get("operation") in {"damage", "heal", "utility", "condition", "teleport"}:
        props.add("target")
    # Imported spell records do not all carry component/shape tags yet. The
    # workshop uses the common V/S default, and accepts explicit sandbox tags
    # for properties that the compact live spell record cannot express.
    props.update({"verbal", "somatic"})
    declared_tags = params.get("spell_tags", [])
    if not isinstance(declared_tags, list) or any(tag not in {"ray", "area", "damage", "numeric", "spell_attack", "target", "duration", "save", "range", "verbal", "somatic", "action"} for tag in declared_tags):
        raise WorkshopError("spell_tags must be a list of supported sandbox spell tags")
    props.update(declared_tags)
    if spell.get("operation") == "ray" or "ray" in spell_id.lower():
        props.add("ray")
    missing = {key: sorted(set(METAMAGIC[key]["requires"]) - props) for key in selected if not set(METAMAGIC[key]["requires"]).issubset(props)}
    if missing:
        raise WorkshopError("incompatible option(s): " + "; ".join(f"{key} needs {', '.join(value)}" for key, value in missing.items()))
    counted = [key for key in selected if key not in {"silent", "still"}]
    if "quicken" in counted and len(counted) > 1:
        raise WorkshopError("Quicken is exclusive with other counted metamagics")
    cost = 0
    for key in selected:
        amount = METAMAGIC[key]["cost"]
        if amount == "variable":
            amount = params.get("heighten_sp", params.get(key))
            if type(amount) is not int or amount < 0:
                raise WorkshopError(f"{key} requires a non-negative integer SP spend in parameters")
        cost += amount
    if "energy" in selected and params.get("damage_type") not in {"ACID", "COLD", "FIRE", "FORCE", "LIGHTNING", "NECROTIC", "POISON", "PSYCHIC", "RADIANT", "THUNDER"}:
        raise WorkshopError("Energy Substitution requires parameters.damage_type from the supported damage types")
    if "heighten" in selected and (type(params.get("dc_increase", 0)) is not int or params.get("dc_increase", 0) < 0):
        raise WorkshopError("Heighten dc_increase must be a non-negative integer")
    effect = copy.deepcopy(spell)
    if "energy" in selected:
        effect["damage_type"] = params["damage_type"]
    if "enlarge" in selected:
        effect["range"] = effect["range"] * 2
    if "extend" in selected and effect.get("duration") is not None:
        effect["duration"] *= 2
    if "widen" in selected and effect.get("radius") is not None:
        effect["radius"] *= 2
    if "heighten" in selected:
        effect["dc_increase"] = params.get("dc_increase", 0)
    tax = "spell action only" if len(counted) <= 1 else "spell action + bonus action" if len(counted) == 2 else "entire turn (no movement, bonus action, or reaction)"
    if "quicken" in counted:
        tax = "bonus-action spell; one action spell remains permitted under Wren's rule"
    pending = [key for key in selected if METAMAGIC[key]["status"] != "implemented"]
    if available_sorcery_points is not None and (type(available_sorcery_points) is not int or available_sorcery_points < 0):
        raise WorkshopError("available_sorcery_points must be a non-negative integer")
    resource_check = None if available_sorcery_points is None else {
        "available": available_sorcery_points, "cost": cost,
        "remaining": available_sorcery_points - cost,
        "affordable": available_sorcery_points >= cost,
    }
    return {"schema": SCHEMA, "spell_id": spell_id, "metamagic": selected, "parameters": copy.deepcopy(params),
            "sorcery_point_cost": cost, "turn_tax": tax, "effective_preview": effect,
            "option_effects": [{"id": key, **copy.deepcopy(METAMAGIC[key])} for key in selected],
            "unresolved_execution": pending, "execution": "preview only; live spell resolver was not called",
            "resource_check": resource_check,
            "recipe_id": _recipe_id(spell_id, selected, params),
            "item_affixes": item_affixes(spell, selected)}


def _recipe_id(spell_id: str, options: list[str], parameters: dict) -> str:
    import hashlib, json
    payload = json.dumps([spell_id, options, parameters], sort_keys=True, separators=(",", ":"))
    return "spell-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def item_affixes(spell: dict, options: list[str]) -> dict:
    """Generate provisional item name hooks from effect and installed modifiers."""
    prefixes = [_PREFIXES[key] for key in options if key in _PREFIXES]
    prefix = " ".join(prefixes[-2:])
    suffix = _SUFFIXES.get(spell.get("operation"), " of Enchantment")
    return {"prefix": prefix, "suffix": suffix, "display_name_template": f"{{prefix}} {{base_name}}{{suffix}}".strip(),
            "source": "derived from recipe effects; naming is provisional", "recipe_bound": True}


def item_name(base_name: str, spell: dict, options: list[str]) -> str:
    """Apply the derived enchantment prefix/suffix to a proposed item name."""
    if not isinstance(base_name, str) or not base_name.strip():
        raise WorkshopError("base item name must be a non-empty string")
    affixes = item_affixes(spell, options)
    return f"{affixes['prefix'] + ' ' if affixes['prefix'] else ''}{base_name.strip()}{affixes['suffix']}"


def _store_path(data_root: Path | str) -> Path:
    return Path(data_root) / "metamagic_workshop" / "recipes.json"


def list_recipes(data_root: Path | str) -> list[dict]:
    path = _store_path(data_root)
    if not path.exists():
        return []
    import json
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != SCHEMA or not isinstance(raw.get("recipes"), list):
        raise WorkshopError("saved workshop recipe file has an unsupported schema")
    return raw["recipes"]


def save_recipe(data_root: Path | str, recipe: dict, name: str | None = None) -> dict:
    if not isinstance(recipe, dict) or recipe.get("schema") != SCHEMA or not recipe.get("recipe_id"):
        raise WorkshopError("save requires a recipe returned by compose")
    rows = list_recipes(data_root)
    stored = {**copy.deepcopy(recipe), "name": (name or recipe["spell_id"].split("@")[0]).strip(), "saved_scope": "local workshop only"}
    if not stored["name"]:
        raise WorkshopError("recipe name must not be empty")
    rows = [row for row in rows if row.get("recipe_id") != stored["recipe_id"]]
    rows.append(stored)
    rows.sort(key=lambda row: (row.get("name", "").casefold(), row["recipe_id"]))
    atomic_json(_store_path(data_root), {"schema": SCHEMA, "recipes": rows})
    return stored
