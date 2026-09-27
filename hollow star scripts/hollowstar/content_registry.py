"""Source-linked Divine Mythos content for the disposable HSR runtime.

The JSON registry is deliberately data-only.  It records where a row came
from and what the engine can currently do with it; it does not replace the
snapshot, canon owners, or the tactical resolver.  A runtime action is first
matched to one visible registry row and then lowered to an existing
authoritative engine action.  Unknown, ambiguous, or deferred rows fail
closed.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path


REGISTRY_PATH = Path(__file__).parent / "content" / "divine_mythos_registry.json"
_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_ENTRY_REQUIRED = {"id", "name", "aliases", "owner", "kind", "rule_summary", "source", "execution", "action"}
_ACTION_REQUIRED = {"cost", "range", "targeting", "legality", "visible_result", "runtime"}
_OWNERS = {"doran", "wren"}

# Module-level read-through cache for the default registry path.
# The registry JSON never changes at runtime, so we read it once and reuse it.
# Tests that supply a custom ``path`` bypass this cache (path != REGISTRY_PATH).
_REGISTRY_CACHE: dict | None = None
_REGISTRY_UNVERIFIED_CACHE: dict | None = None



class ContentRegistryError(ValueError):
    """Raised when source-linked content is malformed or unavailable."""


class ContentRegistryClarification(ContentRegistryError):
    """Raised when one visible alias names more than one content row."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _norm(value: object) -> str:
    if not isinstance(value, str):
        return ""
    value = value.replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentRegistryError(f"{label} must be a non-empty string")
    return value.strip()


def _source(source: object, label: str) -> None:
    if not isinstance(source, dict):
        raise ContentRegistryError(f"{label}.source must be an object")
    _string(source.get("owner_file"), f"{label}.source.owner_file")
    supporting = source.get("supporting_files", [])
    if not isinstance(supporting, list) or any(not isinstance(item, str) or not item.strip() for item in supporting):
        raise ContentRegistryError(f"{label}.source.supporting_files must be strings")
    rule_ids = source.get("source_rule_ids", [])
    if not isinstance(rule_ids, list) or any(not isinstance(item, str) or not item.strip() for item in rule_ids):
        raise ContentRegistryError(f"{label}.source.source_rule_ids must be strings")
    for path in [source["owner_file"], *supporting]:
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ContentRegistryError(f"{label}.source contains an unsafe path: {path!r}")


def validate_registry(raw: object) -> dict:
    """Validate the registry contract without touching the corpus."""
    if not isinstance(raw, dict):
        raise ContentRegistryError("content registry root must be an object")
    if raw.get("schema_version") != "hollow-star-divine-mythos-content-1":
        raise ContentRegistryError("content registry schema mismatch")
    _string(raw.get("registry_version"), "registry_version")
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ContentRegistryError("content registry needs a non-empty entries list")
    seen_ids: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"entries[{index}]"
        if not isinstance(entry, dict) or set(entry) != _ENTRY_REQUIRED:
            raise ContentRegistryError(f"{label} fields do not match the registry contract")
        identifier = _string(entry.get("id"), f"{label}.id")
        if identifier in seen_ids:
            raise ContentRegistryError(f"duplicate content id: {identifier}")
        seen_ids.add(identifier)
        _string(entry.get("name"), f"{label}.name")
        aliases = entry.get("aliases")
        if not isinstance(aliases, list) or any(not isinstance(alias, str) or not alias.strip() for alias in aliases):
            raise ContentRegistryError(f"{label}.aliases must be a list of strings")
        if not isinstance(entry.get("owner"), str) or entry["owner"].lower() not in _OWNERS:
            raise ContentRegistryError(f"{label}.owner must be Doran or Wren")
        _string(entry.get("kind"), f"{label}.kind")
        _string(entry.get("rule_summary"), f"{label}.rule_summary")
        _source(entry.get("source"), label)
        execution = entry.get("execution")
        if not isinstance(execution, dict) or set(execution) != {"status", "resolver", "deferred"}:
            raise ContentRegistryError(f"{label}.execution fields do not match the registry contract")
        if execution.get("status") not in {"implemented", "partial", "deferred"}:
            raise ContentRegistryError(f"{label}.execution.status is invalid")
        _string(execution.get("resolver"), f"{label}.execution.resolver")
        if not isinstance(execution.get("deferred"), list) or any(not isinstance(item, str) for item in execution["deferred"]):
            raise ContentRegistryError(f"{label}.execution.deferred must be a list of strings")
        action = entry.get("action")
        if action is None:
            if execution["status"] != "deferred":
                raise ContentRegistryError(f"{label}.action may be null only for deferred content")
        else:
            if not isinstance(action, dict) or not _ACTION_REQUIRED <= set(action):
                raise ContentRegistryError(f"{label}.action is missing structured action fields")
            for key in ("cost", "range", "targeting", "legality"):
                if not isinstance(action.get(key), dict):
                    raise ContentRegistryError(f"{label}.action.{key} must be an object")
            _string(action.get("visible_result"), f"{label}.action.visible_result")
            if not isinstance(action.get("runtime"), dict) or not isinstance(action["runtime"].get("type"), str):
                raise ContentRegistryError(f"{label}.action.runtime.type is required")
    rooms = raw.get("rooms")
    if not isinstance(rooms, list) or not rooms:
        raise ContentRegistryError("content registry needs authored rooms")
    room_ids: set[str] = set()
    floor_numbers: set[int] = set()
    for index, room in enumerate(rooms):
        label = f"rooms[{index}]"
        if not isinstance(room, dict):
            raise ContentRegistryError(f"{label} must be an object")
        identifier = _string(room.get("id"), f"{label}.id")
        if identifier in room_ids:
            raise ContentRegistryError(f"duplicate authored room id: {identifier}")
        room_ids.add(identifier)
        floor = room.get("floor")
        if type(floor) is not int or floor < 1:
            raise ContentRegistryError(f"{label}.floor must be a positive integer")
        floor_numbers.add(floor)
        _source(room.get("source"), label)
        _string(room.get("atmosphere"), f"{label}.atmosphere")
        tells = room.get("tells")
        if not isinstance(tells, list) or any(not isinstance(tell, dict) or not _string(tell.get("id"), f"{label}.tell.id") or not _string(tell.get("text"), f"{label}.tell.text") for tell in tells):
            raise ContentRegistryError(f"{label}.tells must contain id/text objects")
        objects = room.get("objects", [])
        if not isinstance(objects, list):
            raise ContentRegistryError(f"{label}.objects must be a list")
        for object_index, obj in enumerate(objects):
            if not isinstance(obj, dict):
                raise ContentRegistryError(f"{label}.objects[{object_index}] must be an object")
            _string(obj.get("id"), f"{label}.objects[{object_index}].id")
            _string(obj.get("name"), f"{label}.objects[{object_index}].name")
            _string(obj.get("kind"), f"{label}.objects[{object_index}].kind")
            _string(obj.get("inspect_text"), f"{label}.objects[{object_index}].inspect_text")
        if not isinstance(room.get("hooks", []), list):
            raise ContentRegistryError(f"{label}.hooks must be a list")
    if floor_numbers != set(range(1, max(floor_numbers) + 1)):
        raise ContentRegistryError("authored room floors must be contiguous from floor one")
    result = copy.deepcopy(raw)
    return result


def audit_sources(registry: dict, corpus_root: Path | str | None = None) -> dict:
    """Confirm that every declared owner and supporting file exists."""
    root = Path(corpus_root) if corpus_root is not None else _WORKSPACE_ROOT
    missing: list[str] = []
    checked: list[str] = []

    def check(path: str) -> None:
        candidate = (root / path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise ContentRegistryError(f"source escapes corpus root: {path}") from exc
        checked.append(path)
        if not candidate.is_file():
            missing.append(path)

    for entry in registry["entries"]:
        source = entry["source"]
        check(source["owner_file"])
        for path in source.get("supporting_files", []):
            check(path)
    for room in registry["rooms"]:
        source = room["source"]
        check(source["owner_file"])
        for path in source.get("supporting_files", []):
            check(path)
    for deferred in registry.get("deferred_rules", []):
        source = deferred.get("source", {})
        if source:
            check(source["owner_file"])
            for path in source.get("supporting_files", []):
                check(path)
    if missing:
        raise ContentRegistryError("content registry has missing source files: " + ", ".join(sorted(set(missing))))
    return {"registry_version": registry["registry_version"], "checked_files": sorted(set(checked)), "missing": []}


def load_registry(path: Path | str | None = None, *, corpus_root: Path | str | None = None, verify_sources: bool = True) -> dict:
    global _REGISTRY_CACHE, _REGISTRY_UNVERIFIED_CACHE
    target = Path(path) if path is not None else REGISTRY_PATH
    # Module caches serve the canonical default path only (verified and
    # unverified are kept apart); explicit-path callers always re-read.
    use_cache = path is None or Path(path) == REGISTRY_PATH
    cached = _REGISTRY_CACHE if verify_sources else (_REGISTRY_UNVERIFIED_CACHE or _REGISTRY_CACHE)
    if use_cache and cached is not None:
        return cached
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentRegistryError(f"cannot read content registry: {target}") from exc
    registry = validate_registry(raw)
    if verify_sources:
        audit_sources(registry, corpus_root)
    if use_cache:
        if verify_sources:
            _REGISTRY_CACHE = registry
        else:
            _REGISTRY_UNVERIFIED_CACHE = registry
    return registry



def entries(registry: dict, *, owners: set[str] | None = None, include_deferred: bool = True) -> list[dict]:
    owners = {owner.lower() for owner in owners} if owners else None
    result = []
    for entry in registry["entries"]:
        if owners is not None and entry["owner"].lower() not in owners:
            continue
        if not include_deferred and entry["execution"]["status"] == "deferred":
            continue
        result.append(copy.deepcopy(entry))
    return result


def visible_catalog(registry: dict, owners: set[str]) -> list[dict]:
    """Return the compact catalog safe to show to a player/narrator."""
    out = []
    for entry in entries(registry, owners=owners):
        out.append({
            "id": entry["id"],
            "name": entry["name"],
            "aliases": list(entry["aliases"]),
            "owner": entry["owner"],
            "kind": entry["kind"],
            "execution": copy.deepcopy(entry["execution"]),
            "rule_summary": entry["rule_summary"],
        })
    return out


def _candidates(registry: dict, query: str, *, owner: str | None = None, kind: str | None = None) -> list[dict]:
    needle = _norm(query)
    if not needle:
        return []
    owner_key = owner.lower() if isinstance(owner, str) else None
    kind_key = kind.lower() if isinstance(kind, str) else None
    out = []
    for entry in registry["entries"]:
        if owner_key and entry["owner"].lower() != owner_key:
            continue
        if kind_key and entry["kind"].lower() != kind_key:
            continue
        labels = [entry["id"], entry["name"], *entry["aliases"]]
        if any(_norm(label) == needle for label in labels):
            out.append(entry)
    return out


def resolve(registry: dict, query: str, *, owner: str | None = None, kind: str | None = None) -> dict:
    matches = _candidates(registry, query, owner=owner, kind=kind)
    if len(matches) == 1:
        return copy.deepcopy(matches[0])
    if len(matches) > 1:
        labels = ", ".join(sorted(entry["name"] for entry in matches))
        raise ContentRegistryClarification(f"I need clarification: which item or ability do you mean — {labels}?")
    raise ContentRegistryError(f"unknown visible content: {query!r}")


def room_content(registry: dict, floor: int) -> dict | None:
    for room in registry.get("rooms", []):
        if room.get("floor") == floor:
            return copy.deepcopy(room)
    return None


def _party_owner_ids(run, owner: str) -> list[str]:
    owner_key = owner.lower()
    result = []
    combat = run.context.get("combat") or {}
    for key, rule in combat.get("rules", {}).items():
        if rule.get("identity") == owner_key and run_party_actor(run, key).alive:
            result.append(key)
    if result:
        return result
    for index, actor in enumerate(run.party):
        if actor.name.lower() == owner_key:
            result.append(f"p{index}")
    return result


def run_party_actor(run, key: str):
    if isinstance(key, str) and key.startswith("p") and key[1:].isdigit():
        index = int(key[1:])
        if 0 <= index < len(run.party):
            return run.party[index]
    if isinstance(key, str) and key.startswith("e") and key[1:].isdigit():
        index = int(key[1:])
        if 0 <= index < len(run.opposition):
            return run.opposition[index]
    raise ContentRegistryError(f"unknown actor id for content action: {key!r}")


def _actor_id(run, entry: dict, action: dict) -> str:
    supplied = action.get("actor")
    if supplied is not None:
        if not isinstance(supplied, str):
            raise ContentRegistryError("content action actor must be an actor id")
        return supplied
    candidates = _party_owner_ids(run, entry["owner"])
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ContentRegistryClarification(
            "I need clarification: which " + entry["owner"] + " is using " + entry["name"] + "?"
        )
    raise ContentRegistryError(f"{entry['owner']} is not in this party")


def _identity(run, actor_id: str) -> str:
    combat = run.context.get("combat") or {}
    if actor_id in combat.get("rules", {}):
        return str(combat["rules"][actor_id].get("identity", "")).lower()
    actor = run_party_actor(run, actor_id)
    return actor.name.lower()


def _lower_cast(runtime, action, actor_id):
    return {"type": "cast", "actor": actor_id, "spell": runtime.get("spell")}


def _lower_domain(runtime, action, actor_id):
    return {"type": "domain", "actor": actor_id, "feature": runtime.get("feature")}


def _lower_maneuver(runtime, action, actor_id):
    return {"type": "maneuver", "actor": actor_id, "maneuver": runtime.get("maneuver")}


def _lower_staff_absorb(runtime, action, actor_id):
    return {"type": "staff_absorb", "actor": actor_id}


def _lower_staff_retributive_strike(runtime, action, actor_id):
    return {"type": "staff_retributive_strike", "actor": actor_id}


def _lower_read_seam(runtime, action, actor_id):
    return {"type": "read_seam", "actor": actor_id}


def _lower_grand_cleave(runtime, action, actor_id):
    return {"type": "grand_cleave", "actor": actor_id}


def _lower_ring_heal(runtime, action, actor_id):
    return {"type": "ring_heal", "actor": actor_id}


def _lower_stance(runtime, action, actor_id):
    return {"type": "stance", "actor": actor_id, "stance": runtime.get("stance")}


def _lower_staff(runtime, action, actor_id):
    # Internal branching on mode; returns None to signal content_ready passthrough.
    mode = (action.get("parameters") or {}).get("mode")
    if mode in {"prop", "jam", "lever", "span"}:
        lowered = {"type": "staff_utility", "actor": actor_id, "mode": mode}
        if (action.get("parameters") or {}).get("target") is not None:
            lowered["target"] = (action.get("parameters") or {})["target"]
        return lowered
    if mode == "absorb":
        return {"type": "staff_absorb", "actor": actor_id}
    if mode == "retributive_strike":
        return {"type": "staff_retributive_strike", "actor": actor_id}
    return None  # signals content_ready


def _lower_cast_modifier(runtime, action, actor_id):
    parameters = action.get("parameters")
    if not isinstance(parameters, dict) or not isinstance(parameters.get("spell"), str):
        raise ContentRegistryError("Metamagic requires parameters.spell and optional parameters.metamagic")
    return {"type": "cast", "actor": actor_id, "spell": parameters["spell"], "metamagic": parameters.get("metamagic", [])}


_RUNTIME_DISPATCH = {
    "cast": _lower_cast,
    "domain": _lower_domain,
    "maneuver": _lower_maneuver,
    "staff_absorb": _lower_staff_absorb,
    "staff_retributive_strike": _lower_staff_retributive_strike,
    "read_seam": _lower_read_seam,
    "grand_cleave": _lower_grand_cleave,
    "ring_heal": _lower_ring_heal,
    "stance": _lower_stance,
    "staff": _lower_staff,
    "cast_modifier": _lower_cast_modifier,
}


def _materialize(registry: dict, run, action: dict) -> tuple[dict, str, dict | None]:
    content_id = action.get("content_id")
    if not isinstance(content_id, str) or not content_id:
        raise ContentRegistryError("content action requires content_id")
    try:
        entry = next(entry for entry in registry["entries"] if entry["id"] == content_id)
    except StopIteration as exc:
        raise ContentRegistryError(f"unknown content id: {content_id}") from exc
    if entry["execution"]["status"] == "deferred":
        deferred = "; ".join(entry["execution"].get("deferred", [])) or "source rule is deferred"
        raise ContentRegistryError(f"RULING_REQUIRED: {entry['name']} is deferred: {deferred}")
    actor_id = _actor_id(run, entry, action)
    if _identity(run, actor_id) != entry["owner"].lower():
        raise ContentRegistryError(f"{entry['name']} belongs to {entry['owner']}")
    runtime = entry["action"]["runtime"]
    runtime_type = runtime["type"]
    if runtime_type in {"passive", "content_equip"}:
        return entry, actor_id, None
    handler = _RUNTIME_DISPATCH.get(runtime_type)
    if handler is None:
        raise ContentRegistryError(f"RULING_REQUIRED: unsupported registry resolver {runtime_type}")
    lowered = handler(runtime, action, actor_id)
    if lowered is None:
        # staff handler signals content_ready when no mode matches
        return entry, actor_id, {"type": "content_ready", "actor": actor_id}
    for key in ("target", "targets", "destination", "plane", "named_creature", "center", "dive", "shape", "facing", "mode", "second_target", "ally", "beneficiary", "skill", "dc", "failed_save"):
        if key in action:
            lowered[key] = copy.deepcopy(action[key])
    parameters = action.get("parameters")
    if isinstance(parameters, dict):
        for key, value in parameters.items():
            if key not in {"spell", "metamagic", "mode", "target"}:
                lowered[key] = copy.deepcopy(value)
    return entry, actor_id, lowered


def dispatch(run, action: dict) -> dict:
    """Resolve one registry action through the existing tactical runtime."""
    from hollowstar import tactical as t

    if not isinstance(action, dict):
        raise t.ActionError("content action must be an object")
    registry = run.context.get("content_registry") or load_registry()
    try:
        entry, actor_id, lowered = _materialize(registry, run, action)
    except ContentRegistryError as exc:
        raise t.ActionError(str(exc)) from exc
    if lowered is None:
        runtime = entry["action"]["runtime"] if entry.get("action") else {}
        if runtime.get("type") == "content_equip":
            content_state = run.context.setdefault("content_state", {}).setdefault(actor_id, {})
            loadout = runtime.get("loadout")
            content_state["loadout"] = loadout
            combat = run.context.get("combat")
            if combat and actor_id in combat.get("rules", {}):
                combat["rules"][actor_id]["loadout"] = loadout
            result = {"type": "content_equipped", "actor": actor_id, "loadout": loadout}
        else:
            result = {"type": "content_ready", "actor": actor_id, "content": entry["name"]}
    else:
        if "combat" not in run.context or run.context["combat"].get("complete"):
            raise t.ActionError(f"{entry['name']} requires active combat")
        result = t.apply(run, lowered)
    result = copy.deepcopy(result)
    result["content"] = {
        "id": entry["id"],
        "name": entry["name"],
        "owner": entry["owner"],
        "kind": entry["kind"],
        "execution": copy.deepcopy(entry["execution"]),
        "source": copy.deepcopy(entry["source"]),
    }
    return result

