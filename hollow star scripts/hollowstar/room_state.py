"""Run-local rooms, physical observation, objects, and NPC occupancy."""
from __future__ import annotations

import copy

from hollowstar import tactical as t


ARCHETYPES = {
    "social": {
        "fixtures": [
            {"id": "bar", "kind": "counter", "tags": ["bar", "furniture"], "state": "stocked"},
            {"id": "bottles", "kind": "shelf", "tags": ["container", "bottles"], "contents": ["bottle"]},
            {"id": "rags", "kind": "bundle", "tags": ["rag", "cleaning"], "state": "used"},
            {"id": "dishes", "kind": "stack", "tags": ["dish", "kitchen"], "contents": ["dish", "dish"]},
            {"id": "cabinet", "kind": "cabinet", "tags": ["container", "cabinet", "staff_storage"], "contents": ["ledger", "rag"]},
        ],
        "subrooms": [{"id": "bar_back", "kind": "staff_area", "tags": ["bar_back", "kitchen", "staff"]}],
        "npcs": [{"id": "staff", "role": "bar staff", "location": "bar_back", "tags": ["staff", "social"]}],
    },
    "combat": {"fixtures": [{"id": "cover", "kind": "terrain", "tags": ["cover"]}], "subrooms": [], "npcs": []},
    "hazard": {"fixtures": [{"id": "hazard", "kind": "hazard", "tags": ["hazard"]}], "subrooms": [], "npcs": []},
    "shop": {"fixtures": [{"id": "counter", "kind": "counter", "tags": ["shop"]}], "subrooms": [], "npcs": []},
    "secret": {"fixtures": [{"id": "seam", "kind": "wall", "tags": ["secret", "structure"]}], "subrooms": [], "npcs": []},
    "rest": {"fixtures": [{"id": "bedrolls", "kind": "resting_place", "tags": ["rest"]}], "subrooms": [], "npcs": []},
    "boss": {"fixtures": [{"id": "central_platform", "kind": "platform", "tags": ["elevated", "boss"]}], "subrooms": [], "npcs": []},
}


def _band(z: int, floor: int = 0) -> str:
    delta = z - floor
    if delta <= 0:
        return "grounded"
    if delta <= 20:
        return "low"
    if delta <= 60:
        return "high"
    return "extreme"


def _contents(rng, spec, quest_hooks):
    contents = []
    base_id = spec.get("id", spec.get("object_id", "object").split(":")[-1])
    for index, item in enumerate(spec.get("contents", []), 1):
        contents.append({"id": f"{base_id}_item_{index}", "kind": item, "visible": False})
    for index, hook in enumerate(quest_hooks or [], 1):
        if spec.get("tags", []) and any(tag in spec["tags"] for tag in hook.get("eligible_tags", [])):
            placed = rng.random() < float(hook.get("chance", 0.5))
            if placed:
                contents.append({"id": hook.get("item_id", f"quest_item_{index}"), "kind": "quest_item", "quest": hook.get("quest_id"), "visible": False})
    return contents


def generate(run, row):
    """Generate once on entry; all later interactions resolve stored instances."""
    if row.get("world_state"):
        return row["world_state"]
    archetype = ARCHETYPES.get(row["kind"], ARCHETYPES["social"])
    rng = run.rng.fork(f"room:{row['floor']}:{row['number']}:contents")
    hooks = run.context.get("quest_hooks", [])
    objects = {}
    for fixture in archetype.get("fixtures", []):
        obj = copy.deepcopy(fixture)
        obj["object_id"] = f"{row['floor']}:{row['number']}:{obj.pop('id')}"
        obj["location"] = row.get("location", "room")
        obj["open"] = obj.get("kind") not in {"cabinet", "container"}
        obj["discovered"] = obj.get("kind") in {"counter", "bundle", "stack", "terrain", "hazard", "wall", "resting_place", "platform"}
        obj["contents"] = _contents(rng, obj, hooks)
        objects[obj["object_id"]] = obj
    # Source-linked authored objects are added to the same run-local object
    # table as the generic fixture furniture.  Their prose and hook payloads
    # are stripped by _visible until the player explicitly inspects them.
    for fixture in row.get("authored_objects", []):
        obj = copy.deepcopy(fixture)
        object_id = obj.pop("runtime_object_id", f"{row['floor']}:{row['number']}:{obj.pop('id', 'authored-object')}")
        obj.pop("id", None)
        obj["object_id"] = object_id
        obj["location"] = row.get("location", "room")
        obj["open"] = obj.get("kind") in {"container", "cabinet"}
        obj["discovered"] = bool(obj.get("visible", False))
        obj["visible"] = bool(obj.get("visible", False))
        obj["authored"] = True
        objects[object_id] = obj
    npcs = {}
    for spec in archetype.get("npcs", []):
        npc = copy.deepcopy(spec)
        npc["npc_id"] = f"{row['floor']}:{row['number']}:{npc.pop('id')}"
        npc["location"] = npc.get("location", row.get("location", "room"))
        npc["visible"] = True
        npcs[npc["npc_id"]] = npc
    state = {
        "schema": 1, "location": row.get("location", f"room:{row['floor']}:{row['number']}"),
        "lighting": {"baseline": "dark" if row["floor"] == 4 else "dim", "sources": [], "illuminated": False},
        "objects": objects, "npcs": npcs, "subrooms": copy.deepcopy(archetype.get("subrooms", [])),
        "events": [], "generation": {"seed_namespace": f"room:{row['floor']}:{row['number']}:contents", "quest_rolls_committed": True},
    }
    row["world_state"] = state
    return state


def _visible(state):
    out = copy.deepcopy(state)
    out.pop("generation", None)
    out.pop("events", None)
    for obj in out["objects"].values():
        obj.pop("contents", None)
        obj.pop("inspect_text", None)
        obj.pop("hook", None)
        obj.pop("authored_hook", None)
        if not obj.get("discovered"):
            obj["visible"] = False
    out["objects"] = {k: v for k, v in out["objects"].items() if v.get("visible", True) and (v.get("discovered") or state["lighting"]["illuminated"])}
    out["npcs"] = {k: v for k, v in out["npcs"].items() if v.get("visible", False)}
    return out


def observe(row):
    return _visible(row["world_state"])


def _object(state, object_id):
    obj = state["objects"].get(object_id)
    if obj is None and isinstance(object_id, str) and ":" not in object_id:
        visible = _visible(state).get("objects", {})
        matches = [value for key, value in visible.items() if key.endswith(f":{object_id}")]
        if len(matches) == 1:
            obj = state["objects"].get(matches[0]["object_id"])
    if obj is None:
        raise t.ActionError("unknown room object")
    return obj


def interact(run, row, action):
    state = row["world_state"]
    kind = action.get("type")
    if kind in {"observe_room", "inspect_room"}:
        return {"type": "room_observation", "room": observe(row),
                "atmosphere": row.get("atmosphere", ""),
                "authored_tells": copy.deepcopy(row.get("tells", [])),
                "content_source": copy.deepcopy(row.get("content_source")),
                "evidence": {"physical_observation": True, "prose_revealed": True}}
    if kind == "light_source":
        source = str(action.get("source", ""))
        if source not in {"crown_of_stars", "light"}:
            raise t.ActionError("unsupported room light source")
        if source == "crown_of_stars":
            actor_id = action.get("actor", "")
            combat_rules = run.context.get("combat", {}).get("rules", {})
            valid = any(k == actor_id and r.get("identity") == "wren" for k, r in combat_rules.items())
            valid = valid or any(f"p{i}" == actor_id and getattr(a, "name", "").lower() == "wren" for i, a in enumerate(run.party))
            if not valid:
                raise t.ActionError("Crown of Stars requires Wren")
        state["lighting"]["sources"].append({"source": source, "actor": action.get("actor"), "active": True})
        state["lighting"]["illuminated"] = True
        event = {"type": "room_lit", "source": source, "evidence": {"state_change": "room illumination enabled"}}
        state["events"].append(copy.deepcopy(event))
        return {**event, "room": observe(row)}
    if kind == "enter_subroom":
        location = str(action.get("location", ""))
        valid = {s["id"] for s in state.get("subrooms", [])}
        if location not in valid:
            raise t.ActionError("unknown room or subroom")
        actor_id = action.get("actor")
        state.setdefault("actor_locations", {})[actor_id] = location
        event = {"type": "entered_subroom", "actor": actor_id, "location": location,
                 "evidence": {"state_change": "actor location updated"}}
        state["events"].append(copy.deepcopy(event))
        return {**event, "room": observe(row)}
    obj = _object(state, action.get("object_id"))
    if kind in {"inspect_object", "search_object"}:
        obj["discovered"] = True
        if kind == "search_object":
            for item in obj.get("contents", []): item["visible"] = True
        result = copy.deepcopy(obj)
        result["contents"] = [copy.deepcopy(x) for x in obj.get("contents", []) if x.get("visible")]
        event = {"type": kind, "object": result, "evidence": {"physical_observation": True, "object_id": obj["object_id"]}}
        state["events"].append(copy.deepcopy(event))
        return event
    if kind == "open_object":
        if obj.get("kind") not in {"cabinet", "container"}:
            raise t.ActionError("object is not openable")
        obj["open"] = True; obj["discovered"] = True
        for item in obj.get("contents", []): item["visible"] = True
        event = {"type": "object_opened", "object_id": obj["object_id"], "contents": copy.deepcopy(obj["contents"]), "evidence": {"state_change": "container opened"}}
        state["events"].append(copy.deepcopy(event))
        return event
    raise t.ActionError(f"unsupported room interaction: {kind}")


def combat_geometry(row):
    state = row.get("world_state", {})
    structures = copy.deepcopy(row.get("structures", []))
    if not isinstance(structures, list):
        raise t.ActionError("room structures must be a list")
    for index, structure in enumerate(structures):
        if not isinstance(structure, dict) or not isinstance(structure.get("position"), list):
            raise t.ActionError("each room structure needs a position")
        if not isinstance(structure.get("hp", 0), int) or structure.get("hp", 0) < 0:
            raise t.ActionError("each room structure needs non-negative integer hp")
        if len(structure["position"]) != 3 or any(type(value) is not int for value in structure["position"]):
            raise t.ActionError("each room structure needs an integer 3D position")
        structure.setdefault("object_id", f"structure-{index}")
        structure.setdefault("kind", "structure")
        structure.setdefault("name", structure["object_id"])
        if not isinstance(structure["object_id"], str) or not structure["object_id"]:
            raise t.ActionError("each room structure needs a non-empty object_id")
        if not isinstance(structure["kind"], str) or not structure["kind"]:
            raise t.ActionError("each room structure needs a non-empty kind")
    return {"floor_z": 0, "ceiling_z": 120, "height_bands": {"grounded": 0, "low": [5, 20], "high": [25, 60], "extreme": [65, 120]}, "lighting": copy.deepcopy(state.get("lighting", {})), "structures": structures}
