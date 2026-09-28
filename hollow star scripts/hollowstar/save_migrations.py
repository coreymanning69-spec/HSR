"""Save-file versioning: one migration chain per save kind.

Every account-level save the story layer grows (Star memory, story state,
unlock ladder picks) declares a schema string ``<kind>-<n>`` and registers a
step for each version bump. Loading runs the chain oldest-to-newest, so a save
from any earlier build still opens. A save from a *newer* build is refused
rather than silently truncated.

    @migration("hollow-star-story", 1)
    def _v1_to_v2(data):  # receives v1, returns v2
        data["codex"] = {}
        return data
"""
from __future__ import annotations

import copy
from typing import Callable

_STEPS: dict[str, dict[int, Callable[[dict], dict]]] = {}


class SaveVersionError(ValueError):
    pass


def migration(kind: str, from_version: int):
    def register(fn: Callable[[dict], dict]):
        _STEPS.setdefault(kind, {})[from_version] = fn
        return fn
    return register


def schema_of(kind: str, version: int) -> str:
    return f"{kind}-{version}"


def parse_schema(value: object, kind: str) -> int:
    if not isinstance(value, str) or not value.startswith(kind + "-"):
        raise SaveVersionError(f"not a {kind} save")
    try:
        return int(value[len(kind) + 1:])
    except ValueError as exc:
        raise SaveVersionError(f"unreadable {kind} version") from exc


def migrate(data: dict, kind: str, current: int) -> tuple[dict, bool]:
    """Return ``(data at current version, changed)``."""
    version = parse_schema(data.get("schema"), kind)
    if version > current:
        raise SaveVersionError(f"{kind} save v{version} is newer than this build (v{current})")
    changed = False
    out = copy.deepcopy(data)
    while version < current:
        step = _STEPS.get(kind, {}).get(version)
        if step is None:
            raise SaveVersionError(f"no migration for {kind} v{version} -> v{version + 1}")
        out = step(out)
        version += 1
        out["schema"] = schema_of(kind, version)
        changed = True
    return out, changed
