"""Validated, read-only HSR module manifests.

Modules are content inputs, not Python plugins.  They describe the authored
contract the engine must validate before a future Sandbox or Forge run can
load them.  Runtime state remains under ``.local`` and module files are never
written by the engine.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


class ModuleError(ValueError):
    """Raised when a module manifest is unsafe or incomplete."""


_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_REQUIRED = {
    "schema_version", "module_id", "version", "title", "ruleset",
    "entry_fixture", "content", "blind_play", "status",
}
_CONTENT_KEYS = {
    "floors", "rooms", "actors", "equipment", "spells",
    "encounter_tables", "rules", "authored_tells",
}


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModuleError(f"module {name} must be a non-empty string")
    return value.strip()


def validate_manifest(raw: object, *, source: str = "<module>") -> dict:
    if not isinstance(raw, dict):
        raise ModuleError(f"{source}: manifest root must be an object")
    missing = _REQUIRED - set(raw)
    if missing:
        raise ModuleError(f"{source}: missing fields: {', '.join(sorted(missing))}")
    if raw["schema_version"] != "hollow-star-module-1":
        raise ModuleError(f"{source}: unsupported module schema")
    module_id = _string(raw["module_id"], "module_id")
    if not _ID.fullmatch(module_id):
        raise ModuleError(f"{source}: module_id is not safe: {module_id!r}")
    _string(raw["version"], "version")
    _string(raw["title"], "title")
    _string(raw["ruleset"], "ruleset")
    if raw["status"] not in {"editable", "candidate", "certified"}:
        raise ModuleError(f"{source}: status must be editable, candidate, or certified")
    if not isinstance(raw["entry_fixture"], dict):
        raise ModuleError(f"{source}: entry_fixture must be an object")
    if not _string(raw["entry_fixture"].get("fixture_id"), "entry_fixture.fixture_id"):
        raise ModuleError(f"{source}: entry_fixture.fixture_id is required")
    if not isinstance(raw["content"], dict):
        raise ModuleError(f"{source}: content must be an object")
    absent = _CONTENT_KEYS - set(raw["content"])
    if absent:
        raise ModuleError(f"{source}: content missing: {', '.join(sorted(absent))}")
    if not all(isinstance(raw["content"][key], str) and raw["content"][key].strip()
               for key in _CONTENT_KEYS):
        raise ModuleError(f"{source}: every content entry must name a file or data source")
    blind = raw["blind_play"]
    if not isinstance(blind, dict) or blind.get("sealed_room_boundary") is not True:
        raise ModuleError(f"{source}: blind_play.sealed_room_boundary must be true")
    result = json.loads(json.dumps(raw))
    result["source"] = source
    return result


def load_manifest(path: Path | str) -> dict:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ModuleError(f"cannot read module manifest: {path}") from exc
    return validate_manifest(raw, source=str(path))


def load_module(path: Path | str) -> dict:
    """Load a manifest and verify every declared content source stays local."""
    manifest_path = Path(path).resolve()
    manifest = load_manifest(manifest_path)
    module_dir = manifest_path.parent
    for key, relative in manifest["content"].items():
        candidate = (module_dir / relative).resolve()
        try:
            candidate.relative_to(module_dir)
        except ValueError as exc:
            raise ModuleError(f"{manifest_path}: content path escapes module: {key}") from exc
        if not candidate.is_file():
            raise ModuleError(f"{manifest_path}: missing content source for {key}: {relative}")
    return manifest


def load_module_content(path: Path | str, manifest: dict | None = None) -> dict:
    """Read the declared JSON sources after manifest/path validation."""
    manifest_path = Path(path).resolve()
    manifest = manifest or load_module(manifest_path)
    out = {}
    for key, relative in manifest["content"].items():
        source = (manifest_path.parent / relative).resolve()
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ModuleError(f"{manifest_path}: invalid JSON content for {key}") from exc
        if not isinstance(value, dict):
            raise ModuleError(f"{manifest_path}: content source {key} must contain an object")
        out[key] = value
    actor_ids = {row.get("actor_id") for row in out.get("actors", {}).get("actors", [])}
    equipment_ids = {row.get("equipment_id") for row in out.get("equipment", {}).get("equipment", [])}
    for row in out.get("rooms", {}).get("rooms", []):
        actor_id = row.get("actor_id")
        if actor_id and actor_id not in actor_ids:
            raise ModuleError(f"{manifest_path}: room references missing actor: {actor_id}")
    for row in out.get("actors", {}).get("actors", []):
        equipment_id = row.get("equipment_id")
        if equipment_id and equipment_id not in equipment_ids:
            raise ModuleError(f"{manifest_path}: actor references missing equipment: {equipment_id}")
        for item_id in row.get("equipment_ids", []):
            if item_id not in equipment_ids:
                raise ModuleError(f"{manifest_path}: actor references missing equipment: {item_id}")
    return out


def module_roster(content: dict) -> dict:
    """Build engine Actors from a module's authored actor rows.

    Module content uses the authoring schema (``actor_id``, ``hp``, ``ac``,
    ``attack``, ``dice``, ``type``, numeric ``band``); the engine wants
    :class:`Actor` objects keyed by name, exactly like ``load_roster``.  This is
    the one translation point between the two, so an authored actor can be
    selected as party or opposition without being copied into the stock roster.
    """
    from hollowstar.actors import Actor, Band, Provenance
    from hollowstar.items import Item
    from hollowstar.tags import DamageTag, GATES

    def _tags(value) -> set:
        if not value:
            return set()
        names = [value] if isinstance(value, str) else list(value)
        return {DamageTag[str(n).upper()] for n in names if str(n).upper() in DamageTag.__members__}

    equipment = {}
    for row in content.get("equipment", {}).get("equipment", []):
        equipment[row["equipment_id"]] = Item(
            name=row.get("name", row["equipment_id"]),
            slot=row.get("slot", "hand"),
            base_damage=int(row.get("base_damage", 0)),
            attack_bonus=int(row.get("attack_bonus", 0)),
            damage_dice=row.get("damage_dice", ""),
            damage_modifier=int(row.get("damage_modifier", 0)),
            reach=int(row.get("reach", 5)),
            range_normal=int(row.get("range_normal", 5)),
            range_long=int(row.get("range_long", 5)),
            base_ac=int(row.get("base_ac", 0)),
            ac_bonus=int(row.get("ac_bonus", 0)),
            attack_ability=row.get("attack_ability", ""),
            tags=_tags(row.get("type") or row.get("tags")),
            flavor=row.get("flavor", ""),
        )

    out = {}
    for row in content.get("actors", {}).get("actors", []):
        band = row.get("band", Band.MORTAL)
        try:
            band = Band(int(band)) if not isinstance(band, str) else Band[band.upper()]
        except (ValueError, KeyError) as exc:
            raise ModuleError(f"actor {row.get('actor_id')!r}: unknown band {band!r}") from exc
        held = equipment.get(row.get("equipment_id"))
        max_hp = int(row.get("hp", row.get("max_hp", 10)))
        actor = Actor(
            name=row.get("name", row["actor_id"]),
            band=band,
            controller=row.get("controller", "npc"),
            max_hp=max_hp,
            hp=max_hp,
            armor_class=int(row.get("ac", row.get("armor_class", 10))),
            initiative_bonus=int(row.get("initiative_bonus", 0)),
            speed=int(row.get("speed", 30)),
            attacks_per_action=int(row.get("attacks", row.get("attacks_per_action", 1))),
            reactions=int(row.get("reactions", 1)),
            natural_tags=_tags(row.get("type") or row.get("natural_tags")),
            gate=GATES.get(row.get("gate", "none"), GATES["none"]),
            features=list(row.get("features", [])),
            equipment=[equipment[item_id] for item_id in row["equipment_ids"]] if row.get("equipment_ids") else [held] if held else [],
            resources=dict(row.get("resources", {})),
            ability_scores=dict(row.get("abilities", {key:10 for key in ('STR','DEX','CON','INT','WIS','CHA')})),
            provenance=Provenance(
                owner_file=f"module:{row['actor_id']}",
                snapshot_version="hsr-module-data-1",
                verified=False,
                fidelity="authored",
                note="Authored module actor. Not a balance source until the module is certified.",
            ),
        )
        if row.get("derive_ac_from_equipment"):
            derived_ac = actor.equipment_armor_class()
            if derived_ac is None:
                raise ModuleError(f"actor {row['actor_id']}: equipment-derived AC requires armor")
            actor.armor_class = derived_ac
        out[actor.name] = actor
        # Authored rows are addressable by their stable actor_id as well as by
        # display name, so a caller can select either without a second lookup.
        out.setdefault(row["actor_id"], actor)
    return out


def list_manifests(root: Path | str) -> list[dict]:
    root = Path(root)
    if not root.exists():
        return []
    manifests = []
    for path in sorted(root.glob("*/manifest.json")):
        manifests.append(load_module(path))
    return manifests
