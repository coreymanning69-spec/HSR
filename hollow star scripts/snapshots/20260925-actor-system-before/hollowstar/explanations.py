"""Public explanations for the HSR inspection and tooltip surfaces.

This module is deliberately projection-only.  It accepts already-visible
state or JSON-safe content and never changes a run.  The host owns resolution;
the browser consumes these bounded summaries to render hover, examine, and
"why did that happen?" views.
"""

from __future__ import annotations

import copy
import re
from collections import defaultdict
from typing import Any


def _clean(value: Any) -> str:
    return re.sub(r"[_-]+", " ", str(value or "")).strip()


def _signed(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:+d}"


def effect_summary(effect: dict) -> str:
    """Return a short, player-readable effect explanation."""
    if not isinstance(effect, dict):
        return "No effect details reported."
    if effect.get("public_summary"):
        return str(effect["public_summary"])
    parts: list[str] = []
    operation = effect.get("operation", "add")
    stat = _clean(effect.get("stat"))
    flat = effect.get("flat_bonus", 0)
    multiplier = effect.get("multiplier", 1)
    if stat and flat:
        parts.append(f"{_signed(flat)} {stat}")
    elif flat:
        parts.append(f"{_signed(flat)} magnitude")
    if stat and operation not in {"add", ""}:
        parts.append(operation.replace("_", " "))
    if multiplier not in (None, 1, 1.0):
        parts.append(f"x{multiplier} {_clean(stat or 'magnitude')}")
    if effect.get("per_stack_bonus"):
        parts.append(f"{_signed(effect['per_stack_bonus'])} per {_clean(effect.get('per_stack_source', 'stack'))}")
    if effect.get("inflicts_status"):
        duration = effect.get("status_duration")
        suffix = f" for {duration} turns" if duration else ""
        parts.append(f"applies {_clean(effect['inflicts_status'])}{suffix}")
    if effect.get("blocks_statuses"):
        parts.append("blocks " + ", ".join(_clean(item) for item in effect["blocks_statuses"]))
    if effect.get("grants_tags"):
        parts.append("grants " + ", ".join(_clean(item) for item in effect["grants_tags"]))
    if effect.get("opens_gate"):
        parts.append("opens " + _clean(effect["opens_gate"]))
    if effect.get("closes_gate"):
        parts.append("closes " + _clean(effect["closes_gate"]))
    return " · ".join(parts) or str(effect.get("description") or "No effect details reported.")


def public_effect(effect: dict, *, source: dict | None = None, status: str = "active",
                  reason: str | None = None) -> dict:
    """Normalize one effect for safe public rendering."""
    effect = effect if isinstance(effect, dict) else {}
    result = {
        "id": effect.get("id") or effect.get("name") or "effect",
        "name": effect.get("name") or effect.get("id") or "Effect",
        "phase": effect.get("phase"),
        "direction": effect.get("direction"),
        "operation": effect.get("operation", "add"),
        "stat": effect.get("stat"),
        "condition": effect.get("condition", "always"),
        "duration": effect.get("duration", "permanent"),
        "stack_group": effect.get("stack_group"),
        "priority": effect.get("priority", 0),
        "status": status,
        "summary": effect_summary(effect),
    }
    if source:
        result["source"] = copy.deepcopy(source)
    if reason:
        result["reason"] = reason
    if effect.get("tell"):
        result["tell"] = effect["tell"]
    if effect.get("description"):
        result["description"] = effect["description"]
    return result


def _effect_rows(item: dict, source_kind: str, source_id: str, source_name: str) -> list[dict]:
    rows = []
    for effect in item.get("inherent", []) or []:
        rows.append(public_effect(effect, source={"kind": source_kind, "id": source_id, "name": source_name}))
    for affix_kind in ("prefix", "suffix"):
        affix = item.get(affix_kind)
        if not isinstance(affix, dict):
            continue
        affix_name = affix.get("name") or affix_kind.title()
        for effect in affix.get("effects", []) or []:
            rows.append(public_effect(effect, source={
                "kind": "affix", "id": f"{source_id}:{affix_kind}", "name": affix_name,
            }))
    return rows


def item_explanation(item: dict) -> dict:
    """Return a compact and detailed explanation for one visible item."""
    item = item if isinstance(item, dict) else {}
    hidden = item.get("kind") == "imprint" and not item.get("identified", False)
    result = {
        "schema": "hollow-star-examine-1",
        "entity_type": "item",
        "entity_id": item.get("id") or item.get("name"),
        "name": item.get("display_name") or item.get("name") or item.get("id") or "Item",
        "slot": item.get("slot"),
        "rarity": item.get("rarity") or item.get("tier"),
        "short": "Identify to reveal properties" if hidden else (
            item.get("flavor") or item.get("description") or "Inspect this item for its public properties."
        ),
        "identified": not hidden,
        "stats": [],
        "effects": [],
        "actions": ["inspect"],
    }
    if hidden:
        return result
    for key, label in (("damage_dice", "Damage"), ("base_damage", "Base damage"),
                       ("attack_bonus", "Attack bonus"), ("base_ac", "Base AC"),
                       ("ac_bonus", "AC bonus"), ("shield_bonus", "Shield bonus"),
                       ("reach", "Reach"), ("range_normal", "Normal range"),
                       ("range_long", "Long range"), ("value", "Value")):
        if item.get(key) not in (None, "") and (item.get(key) != 0 or key in {"reach", "value"}):
            result["stats"].append({"label": label, "value": item[key]})
    item_id = str(item.get("id") or item.get("name") or "item")
    result["effects"] = _effect_rows(item, "item", item_id, result["name"])
    for key in ("prefix", "suffix"):
        affix = item.get(key)
        if isinstance(affix, dict) and affix.get("description"):
            result.setdefault("affixes", []).append({"kind": key, "name": affix.get("name"),
                                                       "description": affix["description"]})
    if item.get("utility_uses"):
        result["utility"] = copy.deepcopy(item["utility_uses"])
    return result


def actor_explanation(actor: dict) -> dict:
    """Return public sheet details and effect sources for one actor row."""
    actor = actor if isinstance(actor, dict) else {}
    name = actor.get("name") or actor.get("id") or "Actor"
    effects = []
    for effect in actor.get("inherent", []) or []:
        effects.append(public_effect(effect, source={"kind": "actor", "id": actor.get("id"), "name": name}))
    equipment = actor.get("equipment", []) or []
    if isinstance(equipment, dict):
        equipment = list(equipment.values())
    for item in equipment:
        if isinstance(item, dict):
            effects.extend(_effect_rows(item, "item", str(item.get("id") or item.get("name") or "item"),
                                        item.get("display_name") or item.get("name") or "Item"))
    scores = actor.get("ability_scores") or {}
    modifiers = actor.get("ability_modifiers") or {}
    if not modifiers and isinstance(scores, dict):
        modifiers = {key: (int(value) - 10) // 2 for key, value in scores.items()
                     if isinstance(value, (int, float))}
    return {
        "schema": "hollow-star-examine-1",
        "entity_type": "actor",
        "entity_id": actor.get("id"),
        "name": name,
        "short": f"{name}: {actor.get('hp', '—')}/{actor.get('max_hp', '—')} HP · AC {actor.get('armor_class', '—')}",
        "ability_scores": copy.deepcopy(scores),
        "ability_modifiers": copy.deepcopy(modifiers),
        "skills": copy.deepcopy(actor.get("skill_bonuses", {})),
        "features": copy.deepcopy(actor.get("features", [])),
        "conditions": copy.deepcopy(actor.get("status", actor.get("statuses", []))),
        "effects": effects,
        "weapon": copy.deepcopy(actor.get("weapon_profile")),
        "armor": copy.deepcopy(actor.get("armor_profile")),
        "actions": ["inspect", "explain"],
    }


def resolution_explanation(event: dict | None) -> dict:
    """Turn a public event or evidence bundle into a readable breakdown."""
    event = event if isinstance(event, dict) else {}
    evidence = event.get("evidence") if isinstance(event.get("evidence"), dict) else event
    attack = evidence.get("attack") if isinstance(evidence.get("attack"), dict) else {}
    damage = evidence.get("damage") if isinstance(evidence.get("damage"), dict) else {}
    contributors = copy.deepcopy(evidence.get("contributors", []))
    breakdown = []
    if attack:
        breakdown.extend([
            {"label": "Roll", "value": attack.get("rolls") or attack.get("natural")},
            {"label": "Attack bonus", "value": attack.get("bonus", 0)},
            {"label": "Target AC", "value": attack.get("target_ac")},
            {"label": "Result", "value": "Hit" if attack.get("hit") else "Miss"},
        ])
    if damage:
        breakdown.extend([
            {"label": "Damage dice", "value": damage.get("dice")},
            {"label": "Damage rolls", "value": damage.get("rolls")},
            {"label": "Damage modifier", "value": damage.get("modifier", 0)},
        ])
    return {
        "schema": "hollow-star-examine-1",
        "entity_type": "result",
        "short": event.get("message") or event.get("outcome") or "Resolved action",
        "breakdown": breakdown,
        "contributors": contributors,
        "stacking_notes": copy.deepcopy(evidence.get("stacking_notes", [])),
        "suppressed": copy.deepcopy(evidence.get("suppressed", [])),
        "state_changes": copy.deepcopy(evidence.get("state_changes", {})),
    }


def _rows(value: Any) -> list[dict]:
    if isinstance(value, dict):
        return [row for row in value.values() if isinstance(row, dict)]
    return [row for row in value or [] if isinstance(row, dict)] if isinstance(value, list) else []


def examine_view(view: dict, *, entity_type: str | None = None,
                 entity_id: str | None = None, query: str | None = None) -> dict:
    """Find one visible entity and return its public explanation."""
    view = view if isinstance(view, dict) else {}
    wanted = (query or entity_id or "").strip().lower()
    candidates: list[tuple[str, dict]] = []
    for kind, rows in (("actor", view.get("party")), ("target", view.get("opposition")),
                       ("item", view.get("inventory"))):
        for row in rows or []:
            if isinstance(row, dict):
                candidates.append((kind, row))
    room = view.get("room") if isinstance(view.get("room"), dict) else {}
    for kind, rows in (("object", room.get("objects")), ("target", room.get("npcs"))):
        for row in _rows(rows):
            candidates.append((kind, row))
    if entity_type:
        candidates = [(kind, row) for kind, row in candidates if kind == entity_type or
                      (entity_type == "actor" and kind == "target")]
    matches = []
    for kind, row in candidates:
        row_id = row.get("id") or row.get("object_id") or row.get("npc_id")
        labels = {str(value).lower() for value in
                  (row_id, row.get("name"), row.get("display_name")) if value}
        if not wanted or (entity_id is not None and str(row_id) == str(entity_id)) or wanted in labels:
            matches.append((kind, row))
    if len(matches) > 1:
        names = sorted({row.get("name") or row.get("id") or "unknown" for _, row in matches})
        raise ValueError("which visible entity do you mean: " + ", ".join(names))
    if len(matches) != 1:
        raise ValueError(f"visible entity not found: {query or entity_id}")
    kind, row = matches[0]
    if kind == "item":
        return item_explanation(row)
    if kind in {"actor", "target"}:
        result = actor_explanation(row)
        result["entity_type"] = "actor" if kind == "actor" else "target"
        return result
    return {
        "schema": "hollow-star-examine-1",
        "entity_type": "object", "entity_id": row.get("id") or row.get("object_id"),
        "name": row.get("name") or row.get("id") or "Object",
        "short": row.get("description") or row.get("material") or "A visible object in the current room.",
        "details": {key: copy.deepcopy(row[key]) for key in
                    ("kind", "material", "hp", "max_hp", "open", "flammable", "tags") if key in row},
        "actions": ["inspect"],
    }
