"""Deterministic D&D sandbox slice.

The sandbox is deliberately separate from the existing Reliquary five-floor
fixture.  It shares the authoritative Encounter, RunRNG, save envelope, and
host boundary, but keeps its richer room, social, and environmental state in
``run.context['sandbox']``.  The module returns public receipts while retaining
complete audit receipts in the run-local state for explicit debug inspection.
"""

from __future__ import annotations

import copy
from hollowstar.items import public_item
import math
from typing import Any

from hollowstar import tactical as t


SCHEMA = "hollow-star-dd-sandbox-1"
RULES_VERSION = "hybrid-5e-35-core-1"
BUILD_VERSION = "dd-sandbox-vertical-slice-1"

# Per-faction goal thresholds: at what suspicion/fear level does the NPC act?
FACTION_THRESHOLDS: dict[str, dict] = {
    "guard":    {"confront": 30, "alert_guard": 50, "hostile": 80},
    "civilian": {"flee": 35, "alert_guard": 60},
    "cultist":  {"hostile": 20, "flee": 90},
    "merchant": {"flee": 45, "alert_guard": 70},
    "default":  {"confront": 40, "flee": 60, "hostile": 85},
}


def _room(room_id: str, name: str, coordinates: list[int], exits: dict, *, airflow: dict | None = None) -> dict:
    return {
        "id": room_id,
        "name": name,
        "coordinates": coordinates,
        "exits": copy.deepcopy(exits),
        "light": {"level": 3, "sources": ["hearth"]},
        "sound": {"level": 0, "last_event": None},
        "airflow": copy.deepcopy(airflow or {}),
        "terrain": {"kind": "floor", "difficult": False, "cover": 0},
        "hazards": [],
        "fire": {"active": False, "intensity": 0, "source": None},
        "smoke": 0,
        "damage": 0,
        "condition": "intact",
        "blocked": False,
        "objects": {},
        "npcs": [],
    }


def _fixture_rooms() -> dict[str, dict]:
    rooms = {
        "tavern_main": _room(
            "tavern_main", "The Crooked Crown Tavern", [0, 0, 0],
            {
                "north": {"room": "tavern_back", "door": "tavern_door", "distance_ft": 10},
                "east": {"room": "street", "door": None, "distance_ft": 20},
            }, airflow={"north": 0.45, "east": 0.20},
        ),
        "tavern_back": _room(
            "tavern_back", "The Tavern Back Room", [0, 10, 0],
            {"south": {"room": "tavern_main", "door": "tavern_door", "distance_ft": 10}},
            airflow={"south": 0.45},
        ),
        "street": _room(
            "street", "Rain-Slick Lantern Street", [20, 0, 0],
            {"west": {"room": "tavern_main", "door": None, "distance_ft": 20},
             "north": {"room": "crypt_entry", "door": "iron_gate", "distance_ft": 30}},
            airflow={"north": 0.35, "west": 0.15},
        ),
        "crypt_entry": _room(
            "crypt_entry", "The Sealed Crypt Entry", [20, 30, 0],
            {"south": {"room": "street", "door": "iron_gate", "distance_ft": 30}},
            airflow={"south": 0.35},
        ),
    }
    rooms["tavern_main"]["objects"] = {
        "tavern_door": {"id": "tavern_door", "name": "oak door", "kind": "door", "material": "wood",
                        "weight": 80, "hp": 18, "max_hp": 18, "flammable": True, "open": False,
                        "visible": True, "position": [0, 10, 0], "tags": ["structure", "door"]},
        "bar": {"id": "bar", "name": "the bar", "kind": "furniture", "material": "wood",
                "weight": 240, "hp": 35, "max_hp": 35, "flammable": True, "visible": True,
                "position": [5, 0, 0], "tags": ["cover", "furniture"]},
        "oil_lamp": {"id": "oil_lamp", "name": "oil lamp", "kind": "light", "material": "glass",
                     "weight": 1, "hp": 3, "max_hp": 3, "flammable": True, "visible": True,
                     "position": [5, 5, 5], "tags": ["light", "flammable"]},
        "coin_crate": {"id": "coin_crate", "name": "coin crate", "kind": "container", "material": "iron",
                       "weight": 60, "hp": 20, "max_hp": 20, "flammable": False, "visible": True,
                       "position": [10, 5, 0], "open": False, "contents": [{"id": "coin_pouch", "name": "coin pouch", "weight": 2, "value": 25}],
                       "tags": ["container", "treasure"]},
    }
    rooms["tavern_back"]["objects"] = {
        "dry_straw": {"id": "dry_straw", "name": "dry straw", "kind": "debris", "material": "straw",
                      "weight": 12, "hp": 4, "max_hp": 4, "flammable": True, "visible": True,
                      "position": [0, 10, 0], "tags": ["flammable", "debris"]},
        "support_beam": {"id": "support_beam", "name": "support beam", "kind": "support", "material": "wood",
                         "weight": 180, "hp": 30, "max_hp": 30, "flammable": True, "visible": True,
                         "position": [5, 10, 5], "tags": ["structure", "support"]},
    }
    rooms["street"]["objects"] = {
        "barrel": {"id": "barrel", "name": "rain barrel", "kind": "container", "material": "wood",
                   "weight": 40, "hp": 15, "max_hp": 15, "flammable": True, "visible": True,
                   "position": [20, 0, 0], "open": False, "contents": [{"id": "water", "name": "water", "weight": 30}],
                   "tags": ["container", "flammable"]},
        "iron_gate": {"id": "iron_gate", "name": "iron gate", "kind": "door", "material": "iron",
                      "weight": 180, "hp": 30, "max_hp": 30, "flammable": False, "visible": True, "open": False,
                      "position": [20, 20, 0], "tags": ["structure", "door"]},
    }
    rooms["crypt_entry"]["objects"] = {
        "altar": {"id": "altar", "name": "cracked altar", "kind": "structure", "material": "stone",
                  "weight": 500, "hp": 50, "max_hp": 50, "flammable": False, "visible": True,
                  "position": [20, 30, 0], "tags": ["structure", "cover"]},
    }
    return rooms


def _fixture_npcs() -> dict[str, dict]:
    return {
        "mara": {"id": "mara", "name": "Mara Venn", "role": "bartender", "room": "tavern_main",
                 "position": [5, 0, 0], "perception_ft": 30, "ac": 11, "hp": 18, "max_hp": 18,
                 "attack_bonus": 3, "damage_dice": "1d4+1", "faction": "crooked_crown",
                 "disposition": "neutral", "suspicion": 0, "fear": 0, "knowledge": [],
                 "relationships": {"tavern": "protective"}, "goals": ["keep the peace"], "reaction": "watching"},
        "brann": {"id": "brann", "name": "Brann Holt", "role": "town guard", "room": "tavern_main",
                  "position": [10, 0, 0], "perception_ft": 40, "ac": 16, "hp": 24, "max_hp": 24,
                  "attack_bonus": 5, "damage_dice": "1d6+3", "faction": "town_watch",
                  "disposition": "neutral", "suspicion": 0, "fear": 0, "knowledge": [],
                  "relationships": {"mara": "protective"}, "goals": ["prevent violence"], "reaction": "at ease"},
        "elric": {"id": "elric", "name": "Elric Vale", "role": "patron", "room": "tavern_main",
                  "position": [0, 0, 0], "perception_ft": 25, "ac": 10, "hp": 10, "max_hp": 10,
                  "attack_bonus": 2, "damage_dice": "1d4+0", "faction": "civilians",
                  "disposition": "neutral", "suspicion": 0, "fear": 0, "knowledge": [],
                  "relationships": {"tavern": "loyal"}, "goals": ["finish his drink"], "reaction": "curious"},
        "nessa": {"id": "nessa", "name": "Nessa Quill", "role": "patron", "room": "tavern_main",
                  "position": [0, 5, 0], "perception_ft": 25, "ac": 10, "hp": 10, "max_hp": 10,
                  "attack_bonus": 2, "damage_dice": "1d4+0", "faction": "civilians",
                  "disposition": "neutral", "suspicion": 0, "fear": 0, "knowledge": [],
                  "relationships": {"tavern": "loyal"}, "goals": ["learn useful gossip"], "reaction": "curious"},
        "ives": {"id": "ives", "name": "Ives Cook", "role": "cook", "room": "tavern_back",
                 "position": [0, 10, 0], "perception_ft": 20, "ac": 10, "hp": 12, "max_hp": 12,
                 "attack_bonus": 2, "damage_dice": "1d4+0", "faction": "crooked_crown",
                 "disposition": "neutral", "suspicion": 0, "fear": 0, "knowledge": [],
                 "relationships": {"mara": "loyal"}, "goals": ["protect the kitchen"], "reaction": "working"},
    }


# Fixture room an authored module actor lands in when its room row does not
# name one. The sealed crypt entry is the only fixture room with no residents,
# so a module's own threshold has somewhere to be without displacing the town.
DEFAULT_MODULE_ROOM = "crypt_entry"


def _module_npcs(run, rooms: dict[str, dict]) -> dict[str, dict]:
    """Instantiate a loaded module's authored actors as sandbox NPCs.

    The fixture town is hardcoded; module content is not. Without this the
    engine would validate an authored actor at run creation and then build a
    world that never contains it, which is how a selected opposition could go
    missing from every room.
    """
    content = run.context.get("module_content")
    if not isinstance(content, dict):
        return {}
    actor_rows = {row["actor_id"]: row
                  for row in content.get("actors", {}).get("actors", [])
                  if row.get("actor_id")}
    out: dict[str, dict] = {}
    for room_row in content.get("rooms", {}).get("rooms", []):
        actor_id = room_row.get("actor_id")
        row = actor_rows.get(actor_id)
        if row is None:
            continue
        room_id = room_row.get("sandbox_room", DEFAULT_MODULE_ROOM)
        if room_id not in rooms:
            continue
        hp = int(row.get("hp", 10))
        out[actor_id] = {
            "id": actor_id, "name": row.get("name", actor_id),
            "role": room_row.get("kind", "resident"), "room": room_id,
            "position": [0, 0, 0], "perception_ft": int(row.get("perception_ft", 30)),
            "ac": int(row.get("ac", 10)), "hp": hp, "max_hp": hp,
            "attack_bonus": int(row.get("attack", 0)),
            "damage_dice": row.get("dice", "1d4+0"),
            "faction": row.get("faction", "module"),
            "disposition": row.get("disposition",
                                   "hostile" if room_row.get("kind") == "combat" else "neutral"),
            "suspicion": 0, "fear": 0, "knowledge": [], "relationships": {},
            "goals": [room_row.get("tell", "hold the threshold")],
            "reaction": "holding the threshold",
            "module_actor_id": actor_id,
        }
    return out


def _state(run) -> dict:
    state = run.context.get("sandbox")
    if not isinstance(state, dict):
        raise t.ActionError("start a D&D sandbox first")
    return state


def _actor(run, actor_id: str | None = None):
    state = _state(run)
    actor_id = actor_id or state.get("active_actor", "p0")
    if not isinstance(actor_id, str) or not actor_id.startswith("p") or not actor_id[1:].isdigit():
        raise t.ActionError("sandbox actor must be a party actor such as p0")
    index = int(actor_id[1:])
    if index >= len(run.party):
        raise t.ActionError("unknown sandbox party actor")
    actor = run.party[index]
    if not actor.alive:
        raise t.ActionError("the actor is unconscious or dead")
    return actor_id, actor


def _room_for_actor(state: dict, actor_id: str) -> dict:
    room_id = state["actor_rooms"].get(actor_id)
    if room_id not in state["rooms"]:
        raise t.ActionError("actor is not in a valid room")
    return state["rooms"][room_id]


def _clean_name(value: Any) -> str:
    return str(value or "").strip(" ,.!?:;\"'()[]{}").lower().removeprefix("the ")


def _npc(state: dict, raw: Any, room_id: str | None = None) -> dict:
    query = _clean_name(raw)
    candidates = []
    for npc in state["npcs"].values():
        if room_id is not None and npc["room"] != room_id:
            continue
        labels = {npc["id"], _clean_name(npc["name"]), _clean_name(npc["role"])}
        if query in labels or query in {_clean_name(npc["name"]).split()[0], _clean_name(npc["role"]).split()[0]}:
            candidates.append(npc)
    if len(candidates) != 1:
        if not candidates:
            raise t.ActionError(f"unknown NPC: {raw}")
        raise t.ActionError(f"NPC target is ambiguous: {raw}")
    return candidates[0]


def _object(state: dict, room_id: str, raw: Any) -> dict:
    query = _clean_name(raw)
    candidates = []
    for obj in state["rooms"][room_id]["objects"].values():
        labels = {obj["id"], _clean_name(obj["name"])}
        labels.update(_clean_name(tag) for tag in obj.get("tags", []))
        if query in labels or query in {_clean_name(obj["name"]).split()[0]}:
            candidates.append(obj)
    if len(candidates) != 1:
        if not candidates:
            raise t.ActionError(f"unknown room object: {raw}")
        raise t.ActionError(f"room object is ambiguous: {raw}")
    return candidates[0]


def _distance(first: list[int], second: list[int]) -> int:
    return max(abs(first[i] - second[i]) for i in range(3))


def _ability_mod(actor, ability: str) -> int:
    return actor.ability_modifier(ability)


def _skill_bonus(actor, skill: str, ability: str) -> int:
    return actor.skill_bonuses.get(skill, actor.skill_bonuses.get(skill.lower(), _ability_mod(actor, ability)))


def _check(run, actor, skill: str, ability: str, dc: int) -> tuple[dict, dict]:
    bonus = _skill_bonus(actor, skill, ability)
    roll = run.rng.d20()
    result = {"roll": roll, "natural": roll, "skill": skill, "ability": ability,
              "bonus": bonus, "total": roll + bonus, "dc": dc,
              "success": roll != 1 and (roll == 20 or roll + bonus >= dc)}
    return result, {"rng_calls_after": run.rng.calls, "roll_formula": f"d20({roll}) + {bonus} vs DC {dc}"}


def _carried_weight(state: dict, actor_id: str) -> int:
    return sum(int(item.get("weight", 0)) for item in state["carried"].get(actor_id, {}).values())


def _capacity(actor) -> int:
    return max(15, actor.ability_score("STR") * 15)


def _public_actor(run, state: dict, actor_id: str) -> dict:
    actor = run.party[int(actor_id[1:])]
    carried = _carried_weight(state, actor_id)
    capacity = _capacity(actor)
    # Presentation keys: the client draws champions from identity (authored
    # pose art) and everyone else from sprite_id; neither affects rules.
    rules = (run.context.get("party_rules") or {}).get(actor_id) or {}
    identity = rules.get("identity")
    return {"id": actor_id, "name": actor.name, "hp": actor.hp, "max_hp": actor.max_hp,
            **({"identity": identity} if identity else {}),
            **({"sprite_id": actor.sprite_id} if getattr(actor, "sprite_id", "") else {}),
            "ac": actor.armor_class, "alive": actor.alive, "room": state["actor_rooms"].get(actor_id),
            "statuses": sorted(actor.statuses), "equipment": [public_item(item) for item in actor.equipment],
            "carried_weight": carried, "capacity": capacity,
            "encumbrance": "heavy" if carried > actor.ability_score("STR") * 5 else "normal"}


def _public_npc(npc: dict, *, known: bool = False) -> dict:
    row = {"id": npc["id"], "name": npc["name"], "role": npc["role"], "room": npc["room"],
           "alive": npc["hp"] > 0, "hp": npc["hp"], "max_hp": npc["max_hp"], "disposition": npc["disposition"],
           "reaction": npc["reaction"]}
    if known:
        row["knowledge"] = copy.deepcopy(npc.get("knowledge", []))
    return row


def _public_room(state: dict, room_id: str) -> dict:
    room = state["rooms"][room_id]
    objects = {}
    for object_id, obj in room["objects"].items():
        row = {k: copy.deepcopy(obj[k]) for k in ("id", "name", "kind", "material", "hp", "max_hp", "flammable", "open", "position", "tags", "burning", "destroyed") if k in obj}
        if "contents" in obj and obj.get("open"):
            row["contents"] = [{k: copy.deepcopy(item[k]) for k in ("id", "name", "weight", "value") if k in item} for item in obj["contents"]]
        objects[object_id] = row
    return {"id": room["id"], "name": room["name"], "coordinates": copy.deepcopy(room["coordinates"]),
            "exits": copy.deepcopy(room["exits"]), "light": copy.deepcopy(room["light"]),
            "sound": copy.deepcopy(room["sound"]), "terrain": copy.deepcopy(room["terrain"]),
            "hazards": copy.deepcopy(room["hazards"]), "fire": copy.deepcopy(room["fire"]),
            "smoke": room["smoke"], "damage": room["damage"], "condition": room["condition"],
            "blocked": room["blocked"], "objects": objects}


def view(run, *, debug: bool = False) -> dict:
    state = _state(run)
    actor_id = state.get("active_actor", "p0")
    room_id = state["actor_rooms"].get(actor_id, "tavern_main")
    public = {
        "schema": SCHEMA, "rules_version": RULES_VERSION, "build_version": BUILD_VERSION,
        "status": state["status"], "round": state["round"], "turn": state["turn"],
        "phase": state["phase"], "current_room": room_id,
        "room": _public_room(state, room_id),
        "actors": {f"p{i}": _public_actor(run, state, f"p{i}") for i in range(len(run.party))},
        "npcs": {}, "visible_witnesses": copy.deepcopy(state.get("visible_witnesses", [])),
        "mob": copy.deepcopy(state.get("mob")), "combat": copy.deepcopy(state.get("combat")),
        "conversation": copy.deepcopy(state.get("conversation")),
        "concentration": copy.deepcopy(state.get("concentration")),
        "events": copy.deepcopy(state.get("events", [])[-12:]),
        "prestige": copy.deepcopy(state.get("prestige")),
    }
    for npc in state["npcs"].values():
        if npc["room"] == room_id and npc["hp"] > 0:
            public["npcs"][npc["id"]] = _public_npc(npc, known=npc.get("known_by_player", False))
    if debug:
        public["debug"] = {
            "seed": run.rng.seed, "rng_calls": run.rng.calls, "rng_state_available": True,
            "rng_state": run.rng.getstate(),
            "rooms": copy.deepcopy(state["rooms"]), "npcs": copy.deepcopy(state["npcs"]),
            "carried": copy.deepcopy(state["carried"]), "audit_events": copy.deepcopy(state.get("audit_events", [])),
            "hidden": {"npc_goals": {k: copy.deepcopy(v.get("goals", [])) for k, v in state["npcs"].items()},
                       "suspicion": {k: v.get("suspicion", 0) for k, v in state["npcs"].items()},
                       "rng_calls": run.rng.calls},
        }
    return public


def start(run) -> dict:
    if "sandbox" in run.context:
        raise t.ActionError("D&D sandbox already started")
    rooms = _fixture_rooms()
    npcs = _fixture_npcs()
    npcs.update(_module_npcs(run, rooms))
    actor_rooms = {f"p{i}": "tavern_main" for i in range(len(run.party))}
    carried = {}
    for i, actor in enumerate(run.party):
        carried[f"p{i}"] = {
            "travel_pack": {"id": "travel_pack", "name": "travel pack", "weight": 20, "kind": "gear"},
            "torch": {"id": "torch", "name": "torch", "weight": 1, "kind": "gear"},
        }
        if actor.weapon() is not None:
            carried[f"p{i}"]["equipped_weapon"] = {"id": "equipped_weapon", "name": actor.weapon().display_name,
                                                       "weight": 4, "kind": "equipped"}
    run.context["sandbox"] = {
        "schema": SCHEMA, "rules_version": RULES_VERSION, "build_version": BUILD_VERSION,
        "status": "active", "phase": "exploration", "round": 1, "turn": 1,
        "active_actor": "p0", "current_room": "tavern_main", "rooms": rooms, "npcs": npcs,
        "actor_rooms": actor_rooms, "carried": carried, "events": [], "audit_events": [],
        "visible_witnesses": [], "conversation": None, "combat": None, "mob": None,
        "concentration": None, "prestige": None, "finished_record": None,
    }
    event = _event(run, "sandbox_started", {"room": "tavern_main", "visible": True,
        "message": "The Crooked Crown Tavern is open around you. The engine has instantiated its local people, objects, exits, and physical rules."},
        {"rooms_instantiated": sorted(rooms), "npc_ids": sorted(npcs),
         "module_npc_ids": sorted(k for k, v in npcs.items() if v.get("module_actor_id")),
         "hidden_fields": ["goals", "suspicion", "knowledge"]})
    return {"event": event, "state": view(run)}


def _event(run, event_type: str, public: dict, debug: dict) -> dict:
    state = _state(run)
    public_receipt = {"schema": "hsr-public-receipt-1", "event": event_type,
                      "round": state["round"], "turn": state["turn"], **copy.deepcopy(public)}
    audit = {"schema": "hsr-debug-receipt-1", "public": copy.deepcopy(public_receipt),
             "debug": copy.deepcopy(debug), "rng_calls": run.rng.calls}
    state["events"].append(copy.deepcopy(public_receipt))
    state["audit_events"].append(audit)
    return {"type": event_type, "receipt": public_receipt,
            "evidence": {"public_fields": sorted(public_receipt), "debug_receipt_stored": True,
                          "rng_calls": run.rng.calls}}


def _perceivers(state: dict, room_id: str, source_position: list[int], *, loudness: int) -> list[dict]:
    room = state["rooms"][room_id]
    if room["light"]["level"] <= 0:
        return []
    out = []
    for npc in state["npcs"].values():
        if npc["room"] != room_id or npc["hp"] <= 0:
            continue
        distance = _distance(npc.get("position", [0, 0, 0]), source_position)
        if distance <= max(int(npc.get("perception_ft", 20)), loudness * 5) and room["smoke"] < 6:
            out.append({"id": npc["id"], "name": npc["name"], "distance_ft": distance,
                        "reason": "same room, visible, within perception range"})
    return out


def _record_witnesses(state: dict, witnesses: list[dict], fact: str) -> None:
    state["visible_witnesses"] = copy.deepcopy(witnesses)
    for witness in witnesses:
        npc = state["npcs"][witness["id"]]
        if fact not in npc["knowledge"]:
            npc["knowledge"].append(fact)
        npc["known_by_player"] = True


def _hostile_mob(state: dict, room_id: str, *, trigger: str) -> dict | None:
    members = [npc for npc in state["npcs"].values() if npc["room"] == room_id and npc["hp"] > 0
               and npc["disposition"] == "hostile"]
    if len(members) < 2:
        return None
    mob = {"id": f"tavern_mob:{room_id}:1", "name": "Crooked Crown mob", "room": room_id,
           "members": [npc["id"] for npc in members], "trigger": trigger,
           "status": "forming", "count": len(members)}
    state["mob"] = mob
    state["phase"] = "combat"
    state["combat"] = {"active": True, "round": state["round"], "turn_order": [state["active_actor"]] + mob["members"],
                        "cursor": 0, "reason": trigger, "opportunity_attacks": []}
    for npc in members:
        npc["reaction"] = "joining the mob"
    return mob


def _advance_environment(run, state: dict) -> dict:
    spreads = []
    for room in state["rooms"].values():
        fire = room["fire"]
        if not fire["active"]:
            continue
        fire["intensity"] = min(5, fire["intensity"] + 1)
        room["smoke"] = min(10, room["smoke"] + fire["intensity"])
        room["damage"] += fire["intensity"]
        if room["damage"] >= 20:
            room["condition"] = "ruined"
        elif room["damage"] >= 8:
            room["condition"] = "damaged"
        burning = [obj for obj in room["objects"].values() if obj.get("burning")]
        for obj in room["objects"].values():
            if obj.get("burning") or not obj.get("flammable") or obj.get("destroyed"):
                continue
            if not burning:
                continue
            distance = min(_distance(obj.get("position", [0, 0, 0]), source.get("position", [0, 0, 0])) for source in burning)
            airflow = max(room.get("airflow", {}).values() or [0.0])
            base = 0.80 if distance <= 5 else 0.45 if distance <= 10 else 0.15
            chance = min(0.95, base + airflow * 0.20 + (fire["intensity"] * 0.03))
            roll = run.rng.random()
            if roll < chance:
                obj["burning"] = True
                spreads.append({"room": room["id"], "object": obj["id"], "distance_ft": distance,
                                "chance": round(chance, 4), "roll": round(roll, 4), "airflow": airflow})
        for direction, edge in room["exits"].items():
            target_room = state["rooms"].get(edge["room"])
            if target_room is None or target_room["fire"]["active"] or not room.get("airflow", {}).get(direction):
                continue
            chance = min(0.80, 0.10 + fire["intensity"] * 0.08 + room["airflow"].get(direction, 0.0) * 0.35)
            roll = run.rng.random()
            if roll < chance:
                target_room["fire"] = {"active": True, "intensity": 1, "source": f"airflow:{room['id']}"}
                spreads.append({"from_room": room["id"], "to_room": target_room["id"], "chance": round(chance, 4),
                                "roll": round(roll, 4), "airflow": room["airflow"].get(direction, 0.0)})
    return {"spreads": spreads}


#: Ordered preference when a weapon carries several damage tags. PHYSICAL is a
#: category marker rather than a damage type, so it never wins on its own.
_DAMAGE_TYPE_ORDER = ("PIERCING", "SLASHING", "BLUDGEONING", "DIVINE", "RADIANT",
                      "NECROTIC", "FIRE", "ICE", "SONIC", "PSYCHIC", "FORCE",
                      "ARCANE", "CORROSIVE")


def _weapon_damage_type(weapon) -> str:
    """The damage type a weapon actually deals, from its own tags."""
    names = {tag.name for tag in getattr(weapon, "tags", set())}
    for candidate in _DAMAGE_TYPE_ORDER:
        if candidate in names:
            return candidate
    return "SLASHING"


def _attack_npc(run, state: dict, actor_id: str, target: dict) -> tuple[dict, dict]:
    actor = run.party[int(actor_id[1:])]
    weapon = actor.weapon()
    # HSR gear uses either dice (``1d8``) or a flat ``base_damage``; blessed
    # items such as Soliera's obsidian dagger use the latter. Accepting only
    # dice silently disarmed those actors and dropped them to an unarmed strike.
    if weapon and (weapon.damage_dice or weapon.base_damage):
        attack_bonus = actor.equipment_attack_bonus()
        damage_dice = weapon.damage_dice or weapon.base_damage
        damage_modifier = weapon.damage_modifier
        damage_type = _weapon_damage_type(weapon)
        weapon_name = weapon.display_name
    else:
        attack_bonus = _ability_mod(actor, "STR") + actor.proficiency_bonus
        damage_dice = "1d6"
        damage_modifier = _ability_mod(actor, "STR")
        damage_type = "BLUDGEONING"
        weapon_name = "improvised strike"
    if attack_bonus is None:
        attack_bonus = _ability_mod(actor, "STR") + actor.proficiency_bonus
    distance = _distance([0, 0, 0], target.get("position", [0, 0, 0]))
    if distance > 5:
        raise t.ActionError("melee attack is out of range; the sandbox vertical slice has no ranged NPC targeting yet")
    natural = run.rng.d20()
    critical = natural == 20
    hit = critical or (natural != 1 and natural + attack_bonus >= target["ac"])
    debug = {"actor": actor_id, "target": target["id"], "weapon": weapon_name, "attack_bonus": attack_bonus,
             "target_ac": target["ac"], "natural": natural, "total": natural + attack_bonus,
             "critical": critical, "hit": hit, "damage_type": damage_type, "target_position": target.get("position")}
    public = {"actor": actor.name, "target": target["name"], "weapon": weapon_name,
              "attack": {"natural": natural, "bonus": attack_bonus, "total": natural + attack_bonus,
                          "ac": target["ac"], "critical": critical, "hit": hit}}
    if hit:
        damage, rolls = t.dice(run, damage_dice, critical=critical)
        damage += damage_modifier
        damage = max(0, damage)
        before = target["hp"]
        target["hp"] = max(0, target["hp"] - damage)
        target["reaction"] = "staggering" if target["hp"] else "dead"
        public["damage"] = {"rolls": rolls, "modifier": damage_modifier, "amount": damage,
                             "hp_before": before, "hp_after": target["hp"], "type": damage_type}
        debug.update({"damage_dice": damage_dice, "damage_rolls": rolls, "damage_modifier": damage_modifier,
                      "damage": damage, "target_hp_before": before, "target_hp_after": target["hp"]})
    return public, debug


def _saving_throw(run, state: dict, action: dict) -> tuple[dict, dict]:
    actor_id, actor = _actor(run, action.get("actor"))
    ability = str(action.get("ability", "DEX")).upper()
    if ability not in {"STR", "DEX", "CON", "INT", "WIS", "CHA"}:
        raise t.ActionError("saving throw ability must be a D&D ability")
    dc = action.get("dc", 10)
    if type(dc) is not int or not 1 <= dc <= 40:
        raise t.ActionError("saving throw DC must be an integer from 1 through 40")
    configured = run.context.get("party_rules", {}).get(actor_id, {}).get("saves", {})
    bonus = configured.get(ability, actor.ability_modifier(ability))
    natural = run.rng.d20()
    success = natural != 1 and (natural == 20 or natural + bonus >= dc)
    public = {"actor": actor.name, "ability": ability, "save": {"natural": natural, "bonus": bonus,
                                                                   "total": natural + bonus, "dc": dc, "success": success}}
    debug = {"actor_id": actor_id, "ability": ability, "bonus": bonus, "dc": dc, "natural": natural,
             "success": success, "party_rule_source": bool(configured)}
    condition = action.get("on_fail")
    if not success and isinstance(condition, str) and condition:
        actor.statuses[condition.upper()] = int(action.get("duration", 1))
        public["condition_applied"] = {"name": condition.upper(), "duration": actor.statuses[condition.upper()]}
        debug["condition_applied"] = condition.upper()
    return public, debug


def _cast(run, state: dict, action: dict) -> tuple[dict, dict]:
    actor_id, actor = _actor(run, action.get("actor"))
    room = _room_for_actor(state, actor_id)
    spell = _clean_name(action.get("spell"))
    if spell in {"bless", "shield of faith"}:
        if state.get("concentration") is not None:
            raise t.ActionError("the actor is already concentrating")
        state["concentration"] = {"actor": actor_id, "spell": spell, "remaining_rounds": 10,
                                   "targets": list(action.get("targets") or [actor_id])}
        actor.statuses["CONCENTRATING"] = 10
        return ({"actor": actor.name, "spell": spell, "concentration": copy.deepcopy(state["concentration"])},
                {"actor_id": actor_id, "spell": spell, "concentration_started": True})
    if spell not in {"fire bolt", "firebolt"}:
        raise t.ActionError("sandbox spells currently support Fire Bolt, Bless, and Shield of Faith")
    target = _npc(state, action.get("target") or action.get("target_id"), room["id"])
    natural = run.rng.d20()
    spell_bonus = _ability_mod(actor, "INT") + actor.proficiency_bonus
    critical = natural == 20
    hit = natural != 1 and (critical or natural + spell_bonus >= target["ac"])
    public = {"actor": actor.name, "spell": "Fire Bolt", "target": target["name"],
              "attack": {"natural": natural, "bonus": spell_bonus, "total": natural + spell_bonus,
                          "ac": target["ac"], "hit": hit, "critical": critical}}
    debug = {"actor_id": actor_id, "target_id": target["id"], "spell_attack_bonus": spell_bonus,
             "target_ac": target["ac"], "natural": natural, "hit": hit}
    if hit:
        damage, rolls = t.dice(run, "1d10", critical=critical)
        before = target["hp"]
        target["hp"] = max(0, target["hp"] - damage)
        target["disposition"] = "hostile"
        target["reaction"] = "burning" if target["hp"] else "dead"
        public["damage"] = {"rolls": rolls, "amount": damage, "type": "FIRE", "hp_before": before, "hp_after": target["hp"]}
        debug.update({"damage_rolls": rolls, "damage": damage, "target_hp_before": before, "target_hp_after": target["hp"]})
    witnesses = _perceivers(state, room["id"], [0, 0, 0], loudness=7)
    _record_witnesses(state, witnesses, f"saw {actor.name} cast Fire Bolt at {target['name']}")
    public["witnesses"] = witnesses
    debug["witness_candidates"] = witnesses
    state["phase"] = "combat"
    return public, debug


def _end_concentration(run, state: dict, action: dict) -> tuple[dict, dict]:
    actor_id, actor = _actor(run, action.get("actor"))
    concentration = state.get("concentration")
    if not concentration or concentration.get("actor") != actor_id:
        raise t.ActionError("the actor is not concentrating")
    actor.statuses.pop("CONCENTRATING", None)
    state["concentration"] = None
    return ({"actor": actor.name, "spell": concentration["spell"], "ended": True},
            {"actor_id": actor_id, "concentration_before": concentration})


def _conversation(run, state: dict, action: dict) -> tuple[dict, dict]:
    actor_id, actor = _actor(run, action.get("actor"))
    room = _room_for_actor(state, actor_id)
    target = _npc(state, action.get("target"), room["id"])
    mode = str(action.get("mode", "speak")).lower()
    text = str(action.get("text", "")).strip()
    if mode not in {"speak", "ask", "threaten", "lie", "insult", "trade"}:
        raise t.ActionError("unsupported conversation mode")
    dc = {"speak": 10, "ask": 11, "threaten": 12, "lie": 13, "insult": 10, "trade": 10}[mode] + target["suspicion"]
    skill, ability = {"speak": ("Persuasion", "CHA"), "ask": ("Persuasion", "CHA"),
                      "threaten": ("Intimidation", "CHA"), "lie": ("Deception", "CHA"),
                      "insult": ("Persuasion", "CHA"), "trade": ("Persuasion", "CHA")}[mode]
    check, check_debug = _check(run, actor, skill, ability, dc)
    room["sound"] = {"level": 5 if mode in {"insult", "threaten"} else 2,
                     "last_event": f"conversation:{mode}"}
    witnesses = _perceivers(state, room["id"], [0, 0, 0], loudness=2 if mode in {"speak", "ask", "lie", "trade"} else 5)
    public = {"actor": actor.name, "target": target["name"], "mode": mode, "text": text or None,
              "check": copy.deepcopy(check), "witnesses": copy.deepcopy(witnesses),
              "outcome": "succeeded" if check["success"] else "failed"}
    debug = {"actor_id": actor_id, "target_id": target["id"], "dc": dc, "target_suspicion_before": target["suspicion"],
             "target_goals": copy.deepcopy(target["goals"]), "check": check_debug, "witness_candidates": witnesses}
    state["conversation"] = {"actor": actor_id, "target": target["id"], "mode": mode, "last_text": text}
    if mode in {"insult", "threaten"} or not check["success"]:
        target["suspicion"] += 2 if mode in {"insult", "threaten"} else 1
        target["disposition"] = "hostile" if mode in {"insult", "threaten"} or target["suspicion"] >= 3 else "suspicious"
        target["reaction"] = "calling for help" if target["disposition"] == "hostile" else "watching closely"
    elif mode in {"speak", "ask"}:
        target["reaction"] = "answering"
    if mode == "lie" and not check["success"]:
        target["knowledge"].append("the visitor attempted a failed lie")
    if mode == "insult":
        _record_witnesses(state, witnesses, f"heard {actor.name} insult {target['name']}")
        for witness in witnesses:
            witness_npc = state["npcs"][witness["id"]]
            witness_npc["disposition"] = "hostile"
            witness_npc["reaction"] = "turning against you"
    elif mode in {"threaten", "lie"} and witnesses:
        _record_witnesses(state, witnesses, f"heard {actor.name} {mode} {target['name']}")
    mob = _hostile_mob(state, room["id"], trigger=f"conversation:{mode}")
    if mob:
        public["mob_formed"] = copy.deepcopy(mob)
        debug["mob_formed"] = copy.deepcopy(mob)
    return public, debug


def _move(run, state: dict, action: dict) -> tuple[dict, dict]:
    actor_id, actor = _actor(run, action.get("actor"))
    if actor_id != state["active_actor"]:
        raise t.ActionError("only the active sandbox character may move")
    room = _room_for_actor(state, actor_id)
    direction = _clean_name(action.get("direction"))
    edge = room["exits"].get(direction)
    if edge is None:
        raise t.ActionError(f"no exit leads {direction}")
    if room["blocked"]:
        raise t.ActionError("the room is collapsed and movement is blocked")
    door_id = edge.get("door")
    door = room["objects"].get(door_id) if door_id else None
    if door and not door.get("open") and not door.get("destroyed"):
        raise t.ActionError(f"{door['name']} blocks the {direction} exit")
    carried = _carried_weight(state, actor_id)
    capacity = _capacity(actor)
    if carried > capacity:
        raise t.ActionError(f"encumbrance is over capacity: {carried} lb carried, {capacity} lb capacity")
    heavy = carried > actor.ability_score("STR") * 5
    origin = room["id"]
    opportunity_attacks = []
    if (state.get("combat") or {}).get("active"):
        for npc in state["npcs"].values():
            if npc["room"] != origin or npc["hp"] <= 0 or npc["disposition"] != "hostile":
                continue
            if _distance(npc.get("position", [0, 0, 0]), [0, 0, 0]) > 5:
                continue
            natural = run.rng.d20()
            total = natural + npc["attack_bonus"]
            hit = natural != 1 and (natural == 20 or total >= actor.armor_class)
            reaction = {"npc": npc["name"], "attack": {"natural": natural, "bonus": npc["attack_bonus"],
                                                          "total": total, "ac": actor.armor_class, "hit": hit}}
            if hit:
                damage, rolls = t.dice(run, npc["damage_dice"])
                before = actor.hp
                actor.adjust_hp(-damage)
                reaction["damage"] = {"rolls": rolls, "amount": damage, "hp_before": before, "hp_after": actor.hp}
            opportunity_attacks.append(reaction)
        if opportunity_attacks:
            state["combat"].setdefault("opportunity_attacks", []).extend(copy.deepcopy(opportunity_attacks))
    if not actor.alive:
        public = {"actor": actor.name, "from": origin, "to": origin, "direction": direction,
                  "movement_cost": 0, "blocked_by_opportunity_attack": True,
                  "opportunity_attacks": opportunity_attacks}
        debug = {"actor_id": actor_id, "capacity": capacity, "carried_weight": carried,
                 "opportunity_attacks": opportunity_attacks, "movement_committed": False}
        return public, debug
    destination = state["rooms"].get(edge["room"])
    if destination is None or destination["blocked"]:
        raise t.ActionError("the destination is collapsed or unavailable")
    state["actor_rooms"][actor_id] = destination["id"]
    state["current_room"] = destination["id"]
    state["turn"] += 1
    public = {"actor": actor.name, "from": origin, "to": destination["id"], "direction": direction,
              "distance_ft": edge.get("distance_ft", 5), "movement_cost": 2 if heavy else 1,
              "encumbrance": "heavy" if heavy else "normal", "opportunity_attacks": opportunity_attacks}
    debug = {"actor_id": actor_id, "capacity": capacity, "carried_weight": carried, "heavy_threshold": actor.ability_score("STR") * 5,
             "edge": copy.deepcopy(edge), "door": copy.deepcopy(door), "opportunity_attacks": opportunity_attacks}
    return public, debug


def _object_action(run, state: dict, action: dict, kind: str) -> tuple[dict, dict]:
    actor_id, actor = _actor(run, action.get("actor"))
    room = _room_for_actor(state, actor_id)
    obj = _object(state, room["id"], action.get("object") or action.get("object_id"))
    if kind == "inspect":
        public = {"actor": actor.name, "object": {k: copy.deepcopy(obj[k]) for k in ("id", "name", "kind", "material", "hp", "max_hp", "flammable", "open", "position", "tags") if k in obj}}
        debug = {"object": copy.deepcopy(obj), "room": room["id"]}
        return public, debug
    if kind == "open_object":
        if obj.get("kind") not in {"door", "container"}:
            raise t.ActionError("object is not openable")
        if obj.get("destroyed"):
            raise t.ActionError("the object is destroyed")
        obj["open"] = True
        public = {"actor": actor.name, "object": obj["name"], "state": "open"}
        debug = {"object_id": obj["id"], "object_before": False, "object_after": copy.deepcopy(obj)}
        return public, debug
    if kind == "take":
        if obj.get("kind") in {"door", "structure", "support", "furniture"}:
            raise t.ActionError("that object is fixed to the room")
        weight = int(obj.get("weight", 0))
        if _carried_weight(state, actor_id) + weight > _capacity(actor):
            raise t.ActionError("taking the object would exceed carrying capacity")
        state["carried"][actor_id][obj["id"]] = copy.deepcopy(obj)
        del room["objects"][obj["id"]]
        public = {"actor": actor.name, "object": obj["name"], "weight": weight,
                  "carried_weight": _carried_weight(state, actor_id), "capacity": _capacity(actor)}
        debug = {"object": copy.deepcopy(obj), "carried_after": copy.deepcopy(state["carried"][actor_id])}
        return public, debug
    if kind == "drop":
        carried = state["carried"].get(actor_id, {})
        query = _clean_name(action.get("object") or action.get("object_id"))
        matches = [item for item in carried.values() if query in {_clean_name(item.get("id")), _clean_name(item.get("name"))}]
        if len(matches) != 1:
            raise t.ActionError("carried object is unknown or ambiguous")
        item = matches[0]
        del carried[item["id"]]
        item["position"] = [0, 0, 0]
        room["objects"][item["id"]] = item
        public = {"actor": actor.name, "object": item["name"], "room": room["id"]}
        debug = {"dropped": copy.deepcopy(item), "carried_after": copy.deepcopy(carried)}
        return public, debug
    raise t.ActionError(f"unsupported sandbox object action: {kind}")


def _environment_action(run, state: dict, action: dict, kind: str) -> tuple[dict, dict]:
    actor_id, actor = _actor(run, action.get("actor"))
    room = _room_for_actor(state, actor_id)
    obj = _object(state, room["id"], action.get("object") or action.get("object_id"))
    if kind == "ignite":
        if not obj.get("flammable"):
            raise t.ActionError("the material is not flammable")
        obj["burning"] = True
        room["fire"] = {"active": True, "intensity": 1, "source": obj["id"]}
        room["sound"] = {"level": 5, "last_event": "fire started"}
        witnesses = _perceivers(state, room["id"], obj.get("position", [0, 0, 0]), loudness=5)
        _record_witnesses(state, witnesses, f"saw {actor.name} ignite {obj['name']}")
        public = {"actor": actor.name, "object": obj["name"], "room": room["name"], "fire": copy.deepcopy(room["fire"]),
                  "smoke": room["smoke"], "witnesses": witnesses}
        debug = {"object_before": {"burning": False}, "object_after": copy.deepcopy(obj), "room_after": copy.deepcopy(room),
                 "witness_candidates": witnesses}
        return public, debug
    if kind == "damage_object":
        amount = action.get("amount", 10)
        if type(amount) is not int or amount <= 0 or amount > 1000:
            raise t.ActionError("object damage amount must be an integer from 1 through 1000")
        before = obj["hp"]
        obj["hp"] = max(0, before - amount)
        if obj["hp"] == 0:
            obj["destroyed"] = True
            if obj.get("kind") == "door":
                obj["open"] = True
            if obj.get("kind") == "support":
                room["blocked"] = True
                room["condition"] = "collapsed"
        room["damage"] += amount
        if room["damage"] >= 20 and room["condition"] != "collapsed":
            room["condition"] = "ruined"
        witnesses = _perceivers(state, room["id"], obj.get("position", [0, 0, 0]), loudness=6)
        _record_witnesses(state, witnesses, f"saw {actor.name} damage {obj['name']}")
        public = {"actor": actor.name, "object": obj["name"], "damage": amount, "hp_before": before,
                  "hp_after": obj["hp"], "destroyed": bool(obj.get("destroyed")), "room_condition": room["condition"],
                  "witnesses": witnesses}
        debug = {"object_before": before, "object_after": copy.deepcopy(obj), "room_after": copy.deepcopy(room),
                 "witness_candidates": witnesses}
        return public, debug
    raise t.ActionError(f"unsupported sandbox environment action: {kind}")


def _attack(run, state: dict, action: dict) -> tuple[dict, dict]:
    actor_id, actor = _actor(run, action.get("actor"))
    room = _room_for_actor(state, actor_id)
    target = _npc(state, action.get("target"), room["id"])
    public, debug = _attack_npc(run, state, actor_id, target)
    witnesses = _perceivers(state, room["id"], [0, 0, 0], loudness=8)
    _record_witnesses(state, witnesses, f"saw {actor.name} attack {target['name']}")
    target["disposition"] = "hostile"
    target["reaction"] = "attacking back" if target["hp"] else "dead"
    for witness in witnesses:
        npc = state["npcs"][witness["id"]]
        npc["disposition"] = "hostile"
        npc["reaction"] = "drawing a weapon" if npc["hp"] else npc["reaction"]
    state["phase"] = "combat"
    room["sound"] = {"level": 8, "last_event": "attack"}
    mob = _hostile_mob(state, room["id"], trigger="attack")
    public["witnesses"] = witnesses
    public["combat_started"] = True
    public["mob_formed"] = copy.deepcopy(mob)
    debug["witness_candidates"] = witnesses
    debug["mob_formed"] = copy.deepcopy(mob)
    state["combat"] = state.get("combat") or {"active": True, "round": state["round"], "turn_order": [actor_id, target["id"]],
                                               "cursor": 0, "reason": "attack", "opportunity_attacks": []}
    return public, debug


def _end_turn(run, state: dict) -> tuple[dict, dict]:
    actor_id, actor = _actor(run, None)
    state["turn"] += 1
    state["round"] += 1
    npc_events = []
    if (state.get("combat") or {}).get("active"):
        room_id = state["actor_rooms"].get(actor_id)
        for npc in state["npcs"].values():
            if npc["room"] != room_id or npc["disposition"] != "hostile" or npc["hp"] <= 0:
                continue
            natural = run.rng.d20()
            total = natural + npc["attack_bonus"]
            hit = natural != 1 and (natural == 20 or total >= actor.armor_class)
            row = {"npc": npc["name"], "attack": {"natural": natural, "bonus": npc["attack_bonus"], "total": total,
                                                    "ac": actor.armor_class, "hit": hit}}
            if hit:
                damage, rolls = t.dice(run, npc["damage_dice"])
                before = actor.hp
                actor.adjust_hp(-damage)
                row["damage"] = {"rolls": rolls, "amount": damage, "type": "BLUDGEONING",
                                  "hp_before": before, "hp_after": actor.hp}
                concentration = state.get("concentration")
                if concentration and concentration.get("actor") == actor_id:
                    save_roll = run.rng.d20()
                    save_bonus = _ability_mod(actor, "CON")
                    save_dc = max(10, damage // 2)
                    maintained = save_roll != 1 and (save_roll == 20 or save_roll + save_bonus >= save_dc)
                    row["concentration_save"] = {"natural": save_roll, "bonus": save_bonus,
                                                  "total": save_roll + save_bonus, "dc": save_dc,
                                                  "maintained": maintained}
                    if not maintained:
                        actor.statuses.pop("CONCENTRATING", None)
                        state["concentration"] = None
            npc_events.append(row)
    environment = _advance_environment(run, state)
    concentration = state.get("concentration")
    if concentration:
        concentration["remaining_rounds"] -= 1
        actor.statuses["CONCENTRATING"] = concentration["remaining_rounds"]
        if concentration["remaining_rounds"] <= 0:
            state["concentration"] = None
            actor.statuses.pop("CONCENTRATING", None)
    if actor.hp <= 0:
        state["status"] = "dead"
    public = {"actor": actor.name, "round": state["round"], "npc_reactions": npc_events,
              "environment": {"spreads": environment["spreads"]}, "status": state["status"]}
    debug = {"actor_id": actor_id, "npc_reactions": copy.deepcopy(npc_events), "environment": environment,
             "actor_hp": actor.hp, "rng_calls": run.rng.calls}
    return public, debug


def _finish(run, state: dict, status: str) -> tuple[dict, dict]:
    if status not in {"cleared", "escaped", "surrendered", "dead"}:
        raise t.ActionError("unsupported sandbox terminal status")
    if status == "dead":
        for actor in run.party:
            actor.hp = 0
    state["status"] = status
    flat = 3 if status == "cleared" else 1 if status == "escaped" else 0
    percent = 2 if len([r for r in state["rooms"].values() if r["condition"] != "intact"]) >= 2 else 0
    bonus = math.floor(flat * percent / 100)
    state["prestige"] = {"flat": flat, "percent": percent, "bonus": bonus, "total": flat + bonus,
                          "status": status, "rules_version": RULES_VERSION}
    public = {"status": status, "prestige": copy.deepcopy(state["prestige"]),
              "rooms_visited": sorted(set(state["actor_rooms"].values())),
              "message": "The one-run sandbox has ended; the finished-run audit is being written."}
    debug = {"final_party": [{"name": a.name, "hp": a.hp, "max_hp": a.max_hp} for a in run.party],
             "final_rooms": copy.deepcopy(state["rooms"]), "final_npcs": copy.deepcopy(state["npcs"]),
             "audit_event_count": len(state["audit_events"])}
    return public, debug


def act(run, action: dict) -> dict:
    if not isinstance(action, dict):
        raise t.ActionError("sandbox action must be an object")
    state = _state(run)
    kind = str(action.get("type", "")).lower()
    if kind in {"observe", "inspect_room"}:
        return {"type": "sandbox_observation", "evidence": {"read_only": True, "state_embedded": False}}
    if state["status"] != "active":
        raise t.ActionError("sandbox run has ended")
    public: dict
    debug: dict
    if kind in {"conversation", "speak", "ask", "threaten", "lie", "insult", "trade"}:
        payload = dict(action)
        if kind != "conversation":
            payload["mode"] = kind
        public, debug = _conversation(run, state, payload)
        event_type = "conversation_resolved"
    elif kind == "attack":
        public, debug = _attack(run, state, action)
        event_type = "attack_resolved"
    elif kind in {"move_room", "go", "move"}:
        public, debug = _move(run, state, action)
        event_type = "room_transition"
    elif kind in {"inspect", "open_object", "take", "drop"}:
        public, debug = _object_action(run, state, action, kind)
        event_type = f"{kind}_resolved"
    elif kind in {"ignite", "damage_object"}:
        public, debug = _environment_action(run, state, action, kind)
        event_type = f"{kind}_resolved"
    elif kind in {"save", "saving_throw"}:
        public, debug = _saving_throw(run, state, action)
        event_type = "saving_throw_resolved"
    elif kind == "cast":
        public, debug = _cast(run, state, action)
        event_type = "spell_resolved"
    elif kind in {"end_concentration", "end-concentration"}:
        public, debug = _end_concentration(run, state, action)
        event_type = "concentration_ended"
    elif kind in {"end_turn", "wait"}:
        public, debug = _end_turn(run, state)
        event_type = "turn_resolved"
    elif kind in {"clear", "escape", "surrender"}:
        public, debug = _finish(run, state, {"clear": "cleared", "escape": "escaped", "surrender": "surrendered"}[kind])
        event_type = "sandbox_ended"
    elif kind == "kill_self":
        public, debug = _finish(run, state, "dead")
        event_type = "sandbox_ended"
    else:
        raise t.ActionError(f"unsupported sandbox action: {kind}")
    environment = _advance_environment(run, state) if kind not in {"end_turn", "wait", "ignite", "damage_object"} else {"spreads": []}
    if environment["spreads"]:
        public["environment_spreads"] = environment["spreads"]
        debug["environment_spreads"] = environment
    if state["status"] == "active" and run.party and not any(actor.alive for actor in run.party):
        state["status"] = "dead"
    if state["status"] == "dead" and state.get("prestige") is None:
        terminal_public, terminal_debug = _finish(run, state, "dead")
        public["terminal"] = terminal_public
        debug["terminal"] = terminal_debug
    return _event(run, event_type, public, debug)


def finished_record(run, run_id: str) -> dict:
    state = _state(run)
    return {
        "record_type": "finished_run", "schema": "hsr-dd-finished-run-1", "run_id": run_id,
        "seed": run.rng.seed, "rules_version": state["rules_version"], "build_version": state["build_version"],
        "status": state["status"], "final_state": {"round": state["round"], "turn": state["turn"],
            "current_room": state.get("current_room"), "rooms": copy.deepcopy(state["rooms"]),
            "actors": [{"name": a.name, "hp": a.hp, "max_hp": a.max_hp, "alive": a.alive} for a in run.party],
            "npcs": copy.deepcopy(state["npcs"]), "prestige": copy.deepcopy(state["prestige"])},
        "events": copy.deepcopy(state.get("audit_events", [])),
        "combat_receipts": [event for event in state.get("events", []) if event.get("event") in {"attack_resolved", "turn_resolved"}],
        "cause_of_death": "sandbox actor reached 0 HP" if state["status"] == "dead" else None,
        "rewards": copy.deepcopy(state.get("prestige")),
    }
