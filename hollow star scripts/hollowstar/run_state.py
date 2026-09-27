"""Fail-closed JSON save/resume for isolated Hollow Star simulations.

Run state is disposable derived data. It belongs under ``.local`` and never
flows back into the Divine Mythos corpus. The serializer uses a small
whitelist of engine dataclasses and enums rather than pickle or import-by-name
deserialization, so malformed or foreign save files fail closed.
"""

from __future__ import annotations

import json
from hollowstar.storage import atomic_json
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path

from hollowstar import __version__ as ENGINE_VERSION
from hollowstar.actors import Actor, Band, Provenance
from hollowstar.combat import Encounter
from hollowstar.effects import Affix, Effect
from hollowstar.items import Item
from hollowstar.phases import Direction, Phase, Scope, Tier
from hollowstar.resolution import Resolution, ResolutionStep
from hollowstar.rng import RunRNG
from hollowstar.tags import DamageTag, Gate
from hollowstar.snapshot import RUN_SAVE_ROOT, SnapshotError, assert_safe_write_path


RUN_SCHEMA_VERSION = "hollow-star-run-1"

# RUN_SAVE_ROOT is a relative path; resolving it directly would anchor the
# containment check to the CURRENT WORKING DIRECTORY, which the path-
# independent host is explicitly allowed to differ from the workspace root
# (see hollowstar.paths / test_path_independent_launcher_from_another_
# working_directory). Match on the trailing path segments instead so a host
# passing an absolute path under some-workspace/.local/reliquary_runs is
# accepted no matter what directory the process started in.
_RUN_SAVE_SUFFIX = RUN_SAVE_ROOT.parts


def _under_run_save_root(target: Path) -> bool:
    parts = target.resolve().parts
    width = len(_RUN_SAVE_SUFFIX)
    return any(
        parts[i : i + width] == _RUN_SAVE_SUFFIX for i in range(len(parts) - width + 1)
    )


class RunStateError(SnapshotError):
    """Raised whenever a run save cannot be trusted or resumed."""


_DATACLASSES = {
    "Actor": Actor,
    "Provenance": Provenance,
    "Effect": Effect,
    "Affix": Affix,
    "Item": Item,
    "Resolution": Resolution,
    "ResolutionStep": ResolutionStep,
    "Gate": Gate,
}
_ENUMS = {
    "Band": Band,
    "DamageTag": DamageTag,
    "Direction": Direction,
    "Phase": Phase,
    "Scope": Scope,
    "Tier": Tier,
}


def _encode(value):
    if isinstance(value, Enum):
        return {"__enum__": type(value).__name__, "name": value.name}
    if is_dataclass(value):
        return {
            "__dataclass__": type(value).__name__,
            "fields": {f.name: _encode(getattr(value, f.name)) for f in fields(value)},
        }
    if isinstance(value, set):
        return {"__set__": [_encode(v) for v in sorted(value, key=str)]}
    if isinstance(value, frozenset):
        return {"__frozenset__": [_encode(v) for v in sorted(value, key=str)]}
    if isinstance(value, tuple):
        return {"__tuple__": [_encode(v) for v in value]}
    if isinstance(value, list):
        return [_encode(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _encode(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise RunStateError(f"unsupported value in run state: {type(value).__name__}")


def _decode(value):
    if isinstance(value, list):
        return [_decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    if "__enum__" in value:
        if set(value) != {"__enum__", "name"}:
            raise RunStateError("malformed enum value")
        cls = _ENUMS.get(value["__enum__"])
        if cls is None:
            raise RunStateError(f"unknown enum {value['__enum__']!r}")
        try:
            return cls[value["name"]]
        except KeyError as exc:
            raise RunStateError(f"unknown {value['__enum__']} member") from exc
    if "__set__" in value:
        if set(value) != {"__set__"}:
            raise RunStateError("malformed set value")
        return set(_decode(v) for v in value["__set__"])
    if "__frozenset__" in value:
        if set(value) != {"__frozenset__"}:
            raise RunStateError("malformed frozenset value")
        return frozenset(_decode(v) for v in value["__frozenset__"])
    if "__tuple__" in value:
        if set(value) != {"__tuple__"}:
            raise RunStateError("malformed tuple value")
        return tuple(_decode(v) for v in value["__tuple__"])
    if "__dataclass__" in value:
        if set(value) != {"__dataclass__", "fields"} or not isinstance(value["fields"], dict):
            raise RunStateError("malformed dataclass value")
        cls = _DATACLASSES.get(value["__dataclass__"])
        if cls is None:
            raise RunStateError(f"unknown dataclass {value['__dataclass__']!r}")
        decoded = {k: _decode(v) for k, v in value["fields"].items()}
        allowed = {f.name for f in fields(cls)}
        # Additive migration for saves made before explicit weapon dice.
        if cls is Item:
            decoded.setdefault("damage_dice", "")
            decoded.setdefault("damage_modifier", 0)
        if set(decoded) != allowed:
            raise RunStateError(f"field mismatch for {cls.__name__}")
        try:
            return cls(**decoded)
        except (TypeError, ValueError) as exc:
            raise RunStateError(f"invalid {cls.__name__} state") from exc
    return {k: _decode(v) for k, v in value.items()}


def _default_snapshot_version(encounter: Encounter) -> str:
    versions = {
        actor.provenance.snapshot_version
        for actor in encounter.party
        if actor.provenance.snapshot_version != "unversioned"
    }
    if len(versions) > 1:
        return "hsr-selectable-party-1"
    if not versions:
        raise RunStateError("encounter party must carry a snapshot version")
    return versions.pop()


def _payload(encounter: Encounter, run_id: str, snapshot_version: str) -> dict:
    if encounter.mode != "SIMULATION":
        raise RunStateError("only SIMULATION encounters may be saved")
    if not run_id or not isinstance(run_id, str):
        raise RunStateError("run_id must be a non-empty string")
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "mode": encounter.mode,
        "engine_version": ENGINE_VERSION,
        "snapshot_version": snapshot_version,
        "seed": encounter.rng.seed,
        "rng_calls": encounter.rng.calls,
        "rng_state": _encode(encounter.rng.getstate()),
        "encounter": {
            "party": _encode(encounter.party),
            "opposition": _encode(encounter.opposition),
            "environment": _encode(encounter.environment),
            "round_number": encounter.round_number,
            "transcript": _encode(encounter.transcript),
            "context": _encode(encounter.context),
        },
    }


def save_run(
    encounter: Encounter,
    run_id: str,
    path: Path | str | None = None,
    snapshot_version: str | None = None,
) -> Path:
    """Save an isolated simulation and return its path."""
    target = Path(path) if path is not None else RUN_SAVE_ROOT / f"{run_id}.json"
    target = assert_safe_write_path(target)
    if not _under_run_save_root(target):
        raise RunStateError(f"run saves must stay under a {RUN_SAVE_ROOT}/ directory")
    data = _payload(encounter, run_id, snapshot_version or _default_snapshot_version(encounter))
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(target, data)
    return target


def _load_data(path: Path) -> dict:
    assert_safe_write_path(path)
    if not path.exists():
        raise RunStateError(f"run save does not exist: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RunStateError(f"invalid run save: {path}") from exc
    if not isinstance(data, dict):
        raise RunStateError("run save root must be an object")
    required = {
        "schema_version", "run_id", "mode", "engine_version", "snapshot_version",
        "seed", "rng_calls", "rng_state", "encounter",
    }
    if set(data) != required:
        raise RunStateError("run save has missing or unexpected top-level fields")
    if data["schema_version"] != RUN_SCHEMA_VERSION:
        raise RunStateError("run save schema mismatch")
    if data["mode"] != "SIMULATION":
        raise RunStateError("only SIMULATION run saves may be resumed")
    if data["engine_version"] != ENGINE_VERSION:
        raise RunStateError("run save engine version is incompatible")
    if not isinstance(data["snapshot_version"], str) or not data["snapshot_version"]:
        raise RunStateError("run save has no snapshot version")
    if not isinstance(data["encounter"], dict):
        raise RunStateError("run save encounter must be an object")
    if set(data["encounter"]) not in ({"party", "opposition", "environment", "round_number", "transcript"}, {"party", "opposition", "environment", "round_number", "transcript", "context"}):
        raise RunStateError("run save encounter fields are incomplete")
    return data


def resume_run(path: Path | str, expected_run_id: str | None = None) -> Encounter:
    """Load a saved simulation, restoring its exact RNG continuation."""
    data = _load_data(Path(path))
    if expected_run_id is not None and data["run_id"] != expected_run_id:
        raise RunStateError("run save identity does not match requested run")
    try:
        party = _decode(data["encounter"]["party"])
        opposition = _decode(data["encounter"]["opposition"])
        environment = _decode(data["encounter"]["environment"])
        transcript = _decode(data["encounter"]["transcript"])
        context = _decode(data["encounter"].get("context", {}))
        rng_state = _decode(data["rng_state"])
        round_number = data["encounter"]["round_number"]
        rng_calls = data["rng_calls"]
    except RunStateError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise RunStateError("run save contains invalid encoded state") from exc
    if not isinstance(party, list) or not all(isinstance(a, Actor) for a in party):
        raise RunStateError("run save party is invalid")
    if not isinstance(opposition, list) or not all(isinstance(a, Actor) for a in opposition):
        raise RunStateError("run save opposition is invalid")
    if not isinstance(environment, list) or not all(isinstance(e, Effect) for e in environment):
        raise RunStateError("run save environment is invalid")
    if not isinstance(transcript, list) or not all(isinstance(r, Resolution) for r in transcript):
        raise RunStateError("run save transcript is invalid")
    if not isinstance(round_number, int) or round_number < 0:
        raise RunStateError("run save round number is invalid")
    if not isinstance(rng_calls, int) or rng_calls < 0:
        raise RunStateError("run save RNG call count is invalid")
    if not isinstance(context, dict):
        raise RunStateError("run context must be an object")
    from hollowstar.world import world_context
    context.setdefault("world", world_context())
    rng = RunRNG(data["seed"])
    try:
        rng.setstate(rng_state)
    except (TypeError, ValueError) as exc:
        raise RunStateError("run save RNG state is invalid") from exc
    rng.calls = rng_calls
    return Encounter(
        party=party,
        opposition=opposition,
        rng=rng,
        environment=environment,
        round_number=round_number,
        transcript=transcript,
        context=context,
        mode=data["mode"],
    )
