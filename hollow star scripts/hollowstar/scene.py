"""Public floor-scene and bounded idle helpers."""
from __future__ import annotations

import copy

from hollowstar.clock import daylight


FLOOR_ONE_ROUTE = {
    "market": (0.00, "town-market-dusk"), "tavern": (0.18, "town-tavern-evening"),
    "guardhouse": (0.34, "town-guardhouse-evening"), "waterwheel": (0.62, "town-waterwheel-night"),
    "well": (0.82, "town-well-night"), "camp": (0.48, "town-camp-night"),
    "alley": (0.40, "town-alley-night"), "warehouse": (0.54, "town-warehouse-night"),
    "shrine": (0.68, "town-shrine-night"), "homes": (0.28, "town-homes-evening"),
    "docks": (0.72, "town-docks-night"), "rooms": (0.22, "town-tavern-rooms-night"),
}


def build_scene(state: dict) -> dict:
    """Return a safe client-facing side-scroll scene projection."""
    state = state if isinstance(state, dict) else {}
    room = state.get("room") if isinstance(state.get("room"), dict) else {}
    room_id = room.get("id") or room.get("room_id") or "unknown"
    progress, background = FLOOR_ONE_ROUTE.get(str(room_id), (0.0, "reliquary-unknown"))
    combat = state.get("combat") if isinstance(state.get("combat"), dict) else {}
    party = state.get("party") if isinstance(state.get("party"), list) else []
    if not party and isinstance(state.get("player"), dict):
        party = [{"id": "p0", **state["player"]}]
    npcs = state.get("npcs") if isinstance(state.get("npcs"), dict) else {}
    visible = []
    for key, row in npcs.items():
        if isinstance(row, dict):
            visible.append({"id": row.get("id", key), "name": row.get("name", key),
                            "role": row.get("role"), "disposition": row.get("disposition"),
                            "presentation": row.get("presentation", "resident")})
    encounter = None
    if combat and not combat.get("complete"):
        # The scene is a presentation hint, not a transport for tactical
        # state. Keep only enough for a renderer to label the encounter;
        # combat actors, rules, terrain, and receipts belong to the bounded
        # public view assembled by view_model.py.
        encounter = {
            "round": combat.get("round"),
            "current": combat.get("current"),
            "pending": bool(combat.get("pending")),
            "actor_ids": sorted((combat.get("actors") or {}).keys()),
        }
    travel = state.get("travel") if isinstance(state.get("travel"), dict) else {}
    return {
        "schema": "hollow-star-scene-1",
        "floor_id": "floor-1-town" if state.get("schema") == "hollow-star-floor-one-public-1" else state.get("floor_id", "reliquary"),
        "phase": "social" if state.get("schema") == "hollow-star-floor-one-public-1" else ("combat" if combat and not combat.get("complete") else "exploration"),
        "progress": progress, "direction": "right", "background_id": background,
        "animation": "travel" if travel.get("active") else "idle",
        "travel": {"active": bool(travel.get("active")), "mode": travel.get("mode", "manual"),
                   "destination": travel.get("destination"), "steps": travel.get("steps", 0)},
        "landmarks": [{"id": room_id, "label": room.get("title") or room.get("name") or room_id, "progress": progress}],
        "party_positions": [{"id": row.get("id", f"p{index}"), "progress": progress, "lane": index}
                            for index, row in enumerate(party) if isinstance(row, dict)],
        "time": daylight(state.get("event_clock", {}).get("seconds", 0) + state.get("daylight_offset_seconds", 0)),
        "ambient_events": copy.deepcopy(state.get("ambient_events", [])),
        "location": str(room_id),
        "visible_entities": visible,
        "encounter": encounter,
    }


def idle_pause(state: dict) -> dict | None:
    """Return a public reason to stop before a risky Floor One decision."""
    state = state if isinstance(state, dict) else {}
    if state.get("outcome") in {"completed", "dead"} or state.get("status") in {"closed", "defeated"}:
        return {"code": "run_closed", "message": "The run is no longer active."}
    if state.get("npcs"):
        return {"code": "social_choice", "message": "A resident is present; choose whether to speak, observe, or pass by."}
    objects = state.get("objects")
    if isinstance(objects, dict) and objects:
        return {"code": "inspectable_object", "message": "An object is visible; choose whether to inspect, open, or leave it."}
    room = state.get("room") if isinstance(state.get("room"), dict) else {}
    if room.get("id") in {"well", "waterwheel"}:
        return {"code": "descent_decision", "message": "The descent is available; choose whether to enter the Reliquary."}
    return None
