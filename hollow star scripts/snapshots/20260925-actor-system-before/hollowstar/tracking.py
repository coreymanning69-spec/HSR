"""Additive run and account tracking helpers.

Tracking mirrors authoritative dungeon fields; it never drives gameplay.
"""
from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure(d: dict) -> dict:
    tracking = d.setdefault("tracking", {})
    defaults = {
        "schema": "hollow-star-run-tracking-1", "gold_starting": 0,
        "gold_earned": 0, "gold_spent": 0, "gold_lost": 0,
        "gold_current": int(d.get("currency", 0)), "gold_retained": 0,
        "platinum_earned": 0, "rooms_entered": 0, "rooms_cleared": int(d.get("rooms_cleared", 0)),
        "floors_reached": int(d.get("floor", 1)), "combat_encounters": 0,
        "combat_rounds": 0, "actions_resolved": 0, "gameplay_minutes": 0,
        "rooms_by_kind": {}, "rooms_resolved_by_kind": {}, "floors_completed": 0,
        "completed_floor_numbers": [], "completion_kind": None,
        "active_session_seconds": 0, "active_seconds_remainder": 0.0,
        "started_at": now_utc(),
        "last_active_at": None, "ended_at": None, "terminal_status": None,
    }
    for key, value in defaults.items():
        tracking.setdefault(key, value)
    tracking["gold_current"] = max(0, int(d.get("currency", tracking["gold_current"])))
    tracking["rooms_cleared"] = max(0, int(d.get("rooms_cleared", tracking["rooms_cleared"])))
    tracking["floors_reached"] = max(int(tracking["floors_reached"]), int(d.get("floor", 1)))
    tracking["gameplay_minutes"] = int(d.get("pressure", {}).get("minutes_elapsed", tracking["gameplay_minutes"]))
    return tracking


def room_entered(d: dict, kind: str) -> None:
    tracking = ensure(d)
    counts = tracking.setdefault("rooms_by_kind", {})
    key = str(kind)
    counts[key] = int(counts.get(key, 0)) + 1


def room_resolved(d: dict, kind: str) -> None:
    tracking = ensure(d)
    counts = tracking.setdefault("rooms_resolved_by_kind", {})
    key = str(kind)
    counts[key] = int(counts.get(key, 0)) + 1


def floor_completed(d: dict, floor: int) -> None:
    tracking = ensure(d)
    completed = tracking.setdefault("completed_floor_numbers", [])
    floor = int(floor)
    if floor not in completed:
        completed.append(floor)
        tracking["floors_completed"] = len(completed)


def gold(d: dict, amount: int, *, kind: str) -> None:
    tracking = ensure(d)
    amount = max(0, int(amount))
    if kind == "earned": tracking["gold_earned"] += amount
    elif kind == "spent": tracking["gold_spent"] += amount
    elif kind == "lost": tracking["gold_lost"] += amount
    elif kind == "retained": tracking["gold_retained"] += amount
    else: raise ValueError(f"unknown gold tracking kind: {kind!r}")
    tracking["gold_current"] = int(d.get("currency", 0))


def action(d: dict) -> None:
    ensure(d)["actions_resolved"] += 1


def active_seconds(d: dict, seconds: float) -> None:
    tracking = ensure(d)
    try: seconds = max(0.0, float(seconds))
    except (TypeError, ValueError): seconds = 0.0
    total = max(0.0, float(tracking.get("active_seconds_remainder", 0.0))) + seconds
    whole, tracking["active_seconds_remainder"] = divmod(total, 1.0)
    tracking["active_session_seconds"] = max(0, int(tracking.get("active_session_seconds", 0)) + int(whole))
    if seconds > 0: tracking["last_active_at"] = now_utc()


def finish(d: dict, status: str) -> None:
    tracking = ensure(d)
    if tracking.get("ended_at") is not None:
        return
    tracking["terminal_status"] = status
    tracking["ended_at"] = now_utc()
    tracking["gold_current"] = int(d.get("currency", 0))
    tracking["rooms_cleared"] = int(d.get("rooms_cleared", 0))
    tracking["gameplay_minutes"] = int(d.get("pressure", {}).get("minutes_elapsed", 0))
