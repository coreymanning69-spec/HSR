"""Deterministic event-clock support shared by the city and gauntlet."""
from __future__ import annotations

import copy


SCHEMA = "hollow-star-event-clock-1"
HISTORY_LIMIT = 120


def ensure(container: dict) -> dict:
    clock = container.get("event_clock")
    if not isinstance(clock, dict) or clock.get("schema") != SCHEMA:
        clock = {
            "schema": SCHEMA,
            "tick": 0,
            "seconds": 0,
            "round": 0,
            "turn": 0,
            "rooms_entered": 0,
            "rooms_resolved": 0,
            "history": [],
        }
        container["event_clock"] = clock
    return clock


def emit(container: dict, event_type: str, *, seconds: int = 0,
         room: str | None = None, phase: str | None = None,
         payload: dict | None = None) -> dict:
    """Advance and record a deterministic public event-clock marker."""
    if not isinstance(event_type, str) or not event_type:
        raise ValueError("event_type must be a non-empty string")
    if type(seconds) is not int or seconds < 0:
        raise ValueError("clock seconds must be a non-negative integer")
    clock = ensure(container)
    clock["tick"] += 1
    clock["seconds"] += seconds
    if event_type == "round_start":
        clock["round"] += 1
    if event_type == "turn_end":
        clock["turn"] += 1
    if event_type == "room_enter":
        clock["rooms_entered"] += 1
    if event_type == "room_resolved":
        clock["rooms_resolved"] += 1
    event = {
        "tick": clock["tick"],
        "type": event_type,
        "seconds": seconds,
        "total_seconds": clock["seconds"],
        "round": clock["round"],
        "turn": clock["turn"],
    }
    if room is not None:
        event["room"] = room
    if phase is not None:
        event["phase"] = phase
    if payload:
        event["payload"] = copy.deepcopy(payload)
    clock["history"].append(event)
    del clock["history"][:-HISTORY_LIMIT]
    return copy.deepcopy(event)


def view(container: dict) -> dict:
    """Return a safe public clock projection."""
    return copy.deepcopy(ensure(container))


def daylight(elapsed_seconds: int | float = 0) -> dict:
    """Pure saved-clock projection: day one begins at 08:00."""
    elapsed = max(0, int(elapsed_seconds or 0))
    total = 8 * 3600 + elapsed
    minute = (total % 86400) / 60
    phase = "dawn" if 300 <= minute < 420 else "day" if 420 <= minute < 1020 else "dusk" if 1020 <= minute < 1140 else "night"
    return {"day": total // 86400 + 1, "minute_of_day": minute, "lighting_phase": phase}
