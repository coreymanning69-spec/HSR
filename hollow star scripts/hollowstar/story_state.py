"""Story flags, the story event bus, and the codex.

One account-wide ledger of "what has happened" that cutscenes, dialogue,
unlocks and the Star's commentary all read. Anything that matters to the story
calls ``emit`` instead of hardcoding its consequences where it happens.

Events are counted (``counts``) and the most recent kept (``recent``). Flags
are named values set directly or by listeners. The codex records discoveries
(floors, monsters, residents, items, lore) the first time they are seen.

Listeners are in-process Python callables registered with ``on``; they run in
emit order and may set flags or discover codex entries. Engine save data only
(``.local/``); never corpus canon.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from hollowstar.save_migrations import SaveVersionError, migrate, schema_of
from hollowstar.snapshot import assert_safe_write_path
from hollowstar.storage import atomic_json

KIND = "hollow-star-story"
VERSION = 1
MAX_RECENT = 100
CODEX_KINDS = ("floor", "monster", "resident", "item", "lore", "location")
_ID = re.compile(r"[a-z0-9][a-z0-9_.:-]{0,95}")

_LISTENERS: dict[str, list[Callable[["StoryState", dict, dict], None]]] = {}


def on(event: str):
    """Register ``fn(story, data, payload)`` for an event name (``*`` = all)."""
    def register(fn):
        _LISTENERS.setdefault(event, []).append(fn)
        return fn
    return register


def _valid_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def _default() -> dict:
    return {"schema": schema_of(KIND, VERSION), "flags": {}, "counts": {}, "recent": [], "codex": {}}


class StoryState:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    @property
    def path(self) -> Path:
        return assert_safe_write_path(self.root / "hollow_star_story.json")

    def load(self) -> dict:
        if not self.path.exists():
            return _default()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise SaveVersionError("invalid story save")
        data, changed = migrate(raw, KIND, VERSION)
        base = _default()
        for key in ("flags", "counts", "codex"):
            if isinstance(data.get(key), dict):
                base[key] = data[key]
        if isinstance(data.get("recent"), list):
            base["recent"] = data["recent"][-MAX_RECENT:]
        if changed:
            atomic_json(self.path, base)
        return base

    def _save(self, data: dict) -> dict:
        atomic_json(self.path, data)
        return copy.deepcopy(data)

    # ---- flags -------------------------------------------------------------
    def set_flag(self, name: object, value: object = True, *, data: dict | None = None) -> dict:
        name = _valid_id(name, "story flag")
        if not isinstance(value, (bool, int, float, str)) or (isinstance(value, str) and len(value) > 200):
            raise ValueError("story flag values are short scalars")
        own = data is None
        data = self.load() if own else data
        data["flags"][name] = value
        return self._save(data) if own else data

    def clear_flag(self, name: object) -> dict:
        data = self.load()
        data["flags"].pop(_valid_id(name, "story flag"), None)
        return self._save(data)

    # ---- codex -------------------------------------------------------------
    def discover(self, kind: object, entry_id: object, title: object = None, *, data: dict | None = None) -> dict:
        if kind not in CODEX_KINDS:
            raise ValueError("unknown codex kind")
        entry_id = _valid_id(entry_id, "codex entry")
        own = data is None
        data = self.load() if own else data
        shelf = data["codex"].setdefault(kind, {})
        if entry_id not in shelf:
            shelf[entry_id] = {"title": str(title or entry_id)[:120],
                               "discovered_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        return self._save(data) if own else data

    # ---- events ------------------------------------------------------------
    def emit(self, event: object, payload: dict | None = None) -> dict:
        event = _valid_id(event, "story event")
        payload = payload if isinstance(payload, dict) else {}
        data = self.load()
        data["counts"][event] = int(data["counts"].get(event, 0)) + 1
        data["recent"] = (data["recent"] + [{"event": event, "payload": copy.deepcopy(payload),
                          "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}])[-MAX_RECENT:]
        for fn in _LISTENERS.get(event, []) + _LISTENERS.get("*", []):
            fn(self, data, payload)
        return self._save(data)


# ---- built-in listeners ------------------------------------------------------
@on("floor_entered")
def _codex_floor(story: StoryState, data: dict, payload: dict) -> None:
    floor = payload.get("floor")
    if isinstance(floor, int) and floor > 0:
        story.discover("floor", f"floor-{floor}", payload.get("floor_name") or f"Floor {floor}", data=data)
        best = data["flags"].get("deepest_floor", 0)
        if not isinstance(best, int) or floor > best:
            data["flags"]["deepest_floor"] = floor


@on("run_ended")
def _run_flags(story: StoryState, data: dict, payload: dict) -> None:
    if payload.get("outcome") == "completed":
        data["flags"]["reliquary_cleared"] = True
