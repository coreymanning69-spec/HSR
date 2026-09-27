"""Authored looks for figures that have no creator sheet.

Town residents, fixture foes and filler are drawn by the same hero rig as a
custom lead, so they need the same appearance vocabulary.  content/looks.json
authors them with the creator's own field and option ids; this module resolves
an entry into the compact public shape the client draws from:

    {"race_id", "gender", "age", "aura", "appearance": {field: {"id", "hex"?}},
     "costume": [presentation rows]}

Presentation only.  Nothing here reaches a roll, a disposition, an item list or
the RNG: list choices are picked from a stable hash of the figure's id, never
from the run's generator, so a look is identical across saves, replays and
readouts.  Canon roster characters are not authored here (see looks.json note).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

LOOKS_PATH = Path(__file__).with_name("content") / "looks.json"
LOOKS_SCHEMA = "hollow-star-looks-1"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_SQUAD_NUMBER = re.compile(r"\s+\d+$")
COSTUME_KEYS = ("silhouette", "material", "fx", "rarity", "handedness", "coverage")


@lru_cache(maxsize=1)
def _content() -> dict:
    try:
        data = json.loads(LOOKS_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) and data.get("schema") == LOOKS_SCHEMA else {}


@lru_cache(maxsize=1)
def _options() -> dict:
    """Creator option rows by field and id, for hex and scale lookups."""
    from hollowstar.character_builder import _registry
    try:
        fields = _registry().get("appearance", {}).get("fields", {})
    except Exception:
        return {}
    return {field: {row["id"]: row for row in spec.get("options", []) if isinstance(row, dict) and "id" in row}
            for field, spec in fields.items() if isinstance(spec, dict)}


def _pick(value, seed: str, salt: str):
    """A list value is chosen per figure from a stable hash, never the run RNG."""
    if isinstance(value, list):
        if not value:
            return None
        digest = hashlib.sha256(f"{seed}|{salt}".encode("utf-8")).digest()
        return value[int.from_bytes(digest[:4], "big") % len(value)]
    return value


def _field_entry(field: str, value, seed: str) -> dict | None:
    value = _pick(value, seed, field)
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if _HEX.match(value):
        return {"id": "custom", "hex": value.lower()}
    option = _options().get(field, {}).get(value)
    if option is None:
        return None
    entry = {"id": option["id"]}
    for extra in ("hex", "scale"):
        if extra in option:
            entry[extra] = option[extra]
    return entry


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (over or {}).items():
        if key == "appearance" and isinstance(value, dict):
            out["appearance"] = {**out.get("appearance", {}), **value}
        elif key != "archetype":
            out[key] = copy.deepcopy(value)
    return out


def resolve(entry: dict | None, seed: str) -> dict:
    """Resolve one looks.json entry (with its archetype) into the public shape."""
    if not isinstance(entry, dict):
        return {}
    content = _content()
    archetype = content.get("archetypes", {}).get(entry.get("archetype"), {})
    spec = _merge(archetype, entry)
    look: dict = {}
    for key in ("race", "gender", "age", "aura"):
        value = _pick(spec.get(key), seed, key)
        if isinstance(value, str) and value:
            look["race_id" if key == "race" else key] = value
    appearance = {}
    for field, value in (spec.get("appearance") or {}).items():
        resolved = _field_entry(field, value, seed)
        if resolved:
            appearance[field] = resolved
    if appearance:
        look["appearance"] = appearance
    costume = []
    for row in spec.get("costume") or []:
        if isinstance(row, dict) and isinstance(row.get("silhouette"), str):
            costume.append({key: copy.deepcopy(row[key]) for key in COSTUME_KEYS if key in row})
    if costume:
        look["costume"] = costume
    return look


def for_resident(row: dict) -> dict:
    """Look for a Floor One resident: its own entry, else its class archetype."""
    if not isinstance(row, dict):
        return {}
    content = _content()
    rid = str(row.get("id", ""))
    entry = content.get("residents", {}).get(rid)
    if entry is None:
        archetype = content.get("by_class", {}).get(str(row.get("class", "")))
        entry = {"archetype": archetype or "townsfolk"}
    look = resolve(entry, rid or str(row.get("name", "")))
    species = row.get("species")
    if isinstance(species, str) and species and "race_id" not in look:
        look["race_id"] = species
    if row.get("child"):
        look["age"] = "child"
    return look


def for_actor(name: object, key: object = "") -> dict:
    """Look for a combat actor by its base name ('Town watch 2' -> 'Town watch')."""
    if not isinstance(name, str) or not name:
        return {}
    base = _SQUAD_NUMBER.sub("", name.strip())
    entry = _content().get("foes", {}).get(base)
    return resolve(entry, f"{name}|{key}") if entry else {}
