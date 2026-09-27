"""Compact machine-readable transfer capsules for remote adapters.

The engine keeps full state and receipts locally.  A capsule is the bounded
projection sent through MCP/mailbox/UI adapters; it is not a second state
store and never owns rules, RNG, or persistence.
"""
from __future__ import annotations

from typing import Any


SCHEMA = "hollow-star-transfer-capsule-1"


def _public_event(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    keep = ("type", "actor", "target", "action", "result", "outcome", "message",
            "roll", "total", "damage", "healing", "status", "round", "receipt",
            "commentary", "sfx")
    return {key: value[key] for key in keep if key in value}


def _state_summary(state: Any) -> dict:
    if not isinstance(state, dict):
        return {}
    combat = state.get("combat") if isinstance(state.get("combat"), dict) else {}
    actors = {}
    raw = combat.get("actors") or state.get("actors") or {}
    if isinstance(raw, dict):
        for key, row in raw.items():
            if isinstance(row, dict):
                actors[str(key)] = {k: row[k] for k in ("hp", "max_hp", "status", "statuses") if k in row}
    room = state.get("room") if isinstance(state.get("room"), dict) else {}
    return {
        "round": state.get("round", combat.get("round")),
        "turn": state.get("turn", combat.get("current")),
        "status": state.get("status"),
        "actors": actors,
        "room": {k: room[k] for k in ("id", "room_id", "name", "title", "resident", "exits") if k in room},
        "choices": state.get("available_actions") or [],
    }


def _auto_summary(rows: Any) -> list[dict]:
    result = []
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, dict):
            continue
        body = row.get("result") if isinstance(row.get("result"), dict) else row
        event = body.get("event") if isinstance(body, dict) else None
        item = _public_event(event)
        if item:
            result.append(item)
    return result


def capsule(response: dict, *, request: dict | None = None) -> dict:
    """Turn one full host response into a compact adapter-safe envelope."""
    request = request or {}
    out = {
        "v": SCHEMA,
        "id": response.get("id", request.get("id")),
        "run": request.get("run_id"),
        "ok": bool(response.get("ok")),
    }
    if not response.get("ok"):
        error = response.get("error") or {}
        out["error"] = {k: error[k] for k in ("code", "message") if k in error}
        return out
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    if isinstance(result.get("turn"), dict):
        turn = result["turn"]
    elif isinstance(result.get("readout"), dict):
        turn = result["readout"]
    else:
        turn = result
    event = turn.get("outcome") or turn.get("event") or result.get("event")
    public = turn.get("public_view") or result.get("public_view")
    state = turn.get("visible_state") or result.get("state") or result.get("settled_state")
    out["event"] = _public_event(event)
    if isinstance(turn.get("public_receipt"), dict):
        out["receipt"] = turn["public_receipt"]
    if isinstance(public, dict):
        # The public view is already narrator-safe; avoid duplicating raw state.
        out["view"] = public
    else:
        out["state"] = _state_summary(state)
    auto = _auto_summary(response.get("auto_resolved"))
    if auto:
        out["auto"] = auto
    if response.get("settled_state") and "view" not in out:
        out["state"] = _state_summary(response["settled_state"])
    if isinstance(turn.get("narrator"), dict):
        out["narrator"] = {"source": "engine", "next": turn["narrator"].get("next_input")}
    return out
