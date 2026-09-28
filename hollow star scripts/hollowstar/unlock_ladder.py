"""Doran and Wren's level 1-100 unlock ladder (Story Mode overlay).

They enter with complete level-20 sheets; this overlay locks what they have not
yet earned back. Level comes from champion XP (rooms cleared in settled runs).
Every ``picks.every`` levels grants a pick, every ``bonus_every`` grants one
more; a pick unlocks one ladder entry whose ``min_level`` has been reached.
Level 100 unlocks everything regardless of picks. Wren's spell slots open by
level (``slot_levels``) rather than by pick.

Canon sheets are never touched: the lock is copied into a run's party rules at
launch and the engine refuses locked actions (tactical.apply).
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

from hollowstar.save_migrations import migrate, schema_of
from hollowstar.snapshot import assert_safe_write_path
from hollowstar.storage import atomic_json

LADDER_PATH = Path(__file__).parent / "content" / "story" / "unlock_ladder.json"
KIND = "hollow-star-unlocks"
MAX_LEVEL = 100


def ladder() -> dict:
    return json.loads(LADDER_PATH.read_text(encoding="utf-8"))


def champion_of(selector: str) -> str | None:
    name = str(selector).split(":", 1)[-1].lower()
    return name if name in ladder()["champions"] else None


def level_for(xp: int, spec: dict | None = None) -> int:
    spec = spec or ladder()
    return max(1, min(MAX_LEVEL, 1 + int(xp) // int(spec.get("xp_per_level", 2))))


def picks_for(level: int, spec: dict | None = None) -> int:
    p = (spec or ladder())["picks"]
    return level // p["every"] + level // p["bonus_every"]


def slot_cap(level: int, champ: dict) -> int | None:
    rule = champ.get("slot_levels")
    if not rule:
        return None
    return min(rule["max"], math.ceil(level / rule["per_levels"])) if level < MAX_LEVEL else rule["max"]


class UnlockLadder:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    @property
    def path(self) -> Path:
        return assert_safe_write_path(self.root / "hollow_star_unlocks.json")

    def _load(self) -> dict:
        if not self.path.exists():
            return {"schema": schema_of(KIND, 1), "champions": {}}
        data, changed = migrate(json.loads(self.path.read_text(encoding="utf-8")), KIND, 1)
        if changed:
            atomic_json(self.path, data)
        return data

    def _row(self, data: dict, champ: str) -> dict:
        return data["champions"].setdefault(champ, {"xp": 0, "picked": [], "credited_runs": []})

    def view(self, champ: str) -> dict:
        spec = ladder()
        if champ not in spec["champions"]:
            raise ValueError("no unlock ladder for this champion")
        row = copy.deepcopy(self._row(self._load(), champ))
        c = spec["champions"][champ]
        level = level_for(row["xp"], spec)
        unlocked = {e["key"] for e in c["unlocks"]} if level >= MAX_LEVEL else set(row["picked"])
        entries = [{**e, "unlocked": e["key"] in unlocked, "available": e["min_level"] <= level and e["key"] not in unlocked}
                   for e in c["unlocks"]]
        return {"champion": champ, "xp": row["xp"], "level": level, "max_level": MAX_LEVEL,
                "picks_total": picks_for(level, spec), "picks_spent": len(row["picked"]),
                "picks_left": max(0, picks_for(level, spec) - len(row["picked"])),
                "slot_cap": slot_cap(level, c), "always": list(c["always"]), "entries": entries}

    def pick(self, champ: str, key: object) -> dict:
        view = self.view(champ)
        entry = next((e for e in view["entries"] if e["key"] == key), None)
        if entry is None:
            raise ValueError("unknown unlock")
        if entry["unlocked"]:
            raise ValueError("already unlocked")
        if not entry["available"]:
            raise ValueError(f"{entry['label']} unlocks at level {entry['min_level']}")
        if view["picks_left"] <= 0:
            raise ValueError("no picks left; earn more levels")
        data = self._load()
        self._row(data, champ)["picked"].append(key)
        atomic_json(self.path, data)
        return self.view(champ)

    def credit(self, champ: str, run_id: str, xp: int) -> dict:
        data = self._load()
        row = self._row(data, champ)
        if run_id not in row["credited_runs"]:
            row["credited_runs"] = (row["credited_runs"] + [run_id])[-500:]
            row["xp"] += max(0, int(xp))
            atomic_json(self.path, data)
        return self.view(champ)

    def debug_set_level(self, champ: str, level: object) -> dict:
        if type(level) is not int or not 1 <= level <= MAX_LEVEL:
            raise ValueError("level must be 1-100")
        data = self._load()
        self._row(data, champ)["xp"] = (level - 1) * int(ladder().get("xp_per_level", 2))
        atomic_json(self.path, data)
        return self.view(champ)

    def run_locks(self, champ: str) -> dict:
        """What a Story run copies into party rules: locked keys and slot cap."""
        view = self.view(champ)
        return {"locked_actions": sorted(e["key"] for e in view["entries"] if not e["unlocked"]),
                "champion_level": view["level"], "slot_cap": view["slot_cap"]}


_SLOT = re.compile(r"slot_(\d+)_")


def apply_slot_cap(actor, cap: int | None) -> list[str]:
    """Zero this run's copy of spell-slot pools above the cap."""
    if cap is None:
        return []
    closed = []
    for name in list(actor.resources):
        m = _SLOT.match(name)
        if m and int(m.group(1)) > cap and actor.resources[name]:
            actor.resources[name] = 0
            closed.append(name)
    return closed


def action_locked(rules: dict, action: dict) -> str | None:
    locked = rules.get("locked_actions")
    if not locked:
        return None
    kind = action.get("type")
    sub = action.get("maneuver") or action.get("feature") or action.get("spell")
    for key in (kind, f"{kind}:{sub}" if sub else None):
        if key and key in locked:
            return key
    return None
