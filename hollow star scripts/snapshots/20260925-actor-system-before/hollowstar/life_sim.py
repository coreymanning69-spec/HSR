"""Deterministic persistent Floor One life-simulation scenario.

This deliberately small vertical slice shares the HSR encounter/save boundary.
It keeps public observations separate from private motives while making physical
evidence, witnesses, social knowledge, and civic response durable in a run.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from hollowstar import clock
from hollowstar.conversation import options as conversation_options
from hollowstar.conversation import resolve as resolve_conversation

from hollowstar.storage import atomic_json


CONTENT_PATH = Path(__file__).with_name("content") / "floor_one_life.json"
TICK_SECONDS = 30
MAX_TICK_BATCHES = 120


CHAMPION_ABILITY_OPTIONS = {
    "doran": [
        {"id": "Rally", "label": "Rally", "kind": "maneuver", "phase": "combat"},
        {"id": "Commanding Presence", "label": "Commanding Presence", "kind": "maneuver", "phase": "social check"},
        {"id": "Trip Attack", "label": "Trip Attack", "kind": "maneuver", "phase": "combat"},
        {"id": "Menacing Attack", "label": "Menacing Attack", "kind": "maneuver", "phase": "combat"},
    ],
    "wren": [
        {"id": "Indomitable Spirit", "label": "Indomitable Spirit", "kind": "feature", "phase": "combat"},
        {"id": "simulacrum", "label": "Call Simulacrum", "kind": "domain", "phase": "combat or exploration"},
        {"id": "Crown of Stars", "label": "Crown of Stars", "kind": "ability", "phase": "combat"},
        {"id": "Take Flight", "label": "Take Flight", "kind": "movement", "phase": "combat"},
    ],
}


class LifeError(ValueError):
    pass


def _content() -> dict:
    try:
        value = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LifeError("Floor One life content is unavailable") from exc
    if not isinstance(value, dict) or value.get("schema") != "hollow-star-floor-one-life-1":
        raise LifeError("Floor One life content has an unsupported schema")
    return value


def _world(run) -> dict:
    world = run.context.get("life_world")
    if not isinstance(world, dict):
        raise LifeError("start the Floor One life world first")
    return world


def _actor(run, actor_id: str = "p0"):
    if actor_id != "p0":
        raise LifeError("Floor One currently has one player-controlled actor")
    if not run.party:
        raise LifeError("world has no player actor")
    return run.party[0]


def _resident(world: dict, raw: object) -> dict:
    if not isinstance(raw, str) or not raw.strip():
        raise LifeError("resident target is required")
    key = raw.strip().lower().replace(" ", "-")
    matches = [row for row in world["residents"].values()
               if row["id"] == key or row["name"].lower() == raw.strip().lower()]
    if len(matches) != 1:
        raise LifeError("resident is unknown or ambiguous in the current world")
    return matches[0]


def _location(world: dict, raw: object | None = None) -> dict:
    key = raw or world["player"]["location"]
    if not isinstance(key, str) or key not in world["locations"]:
        raise LifeError("location is unknown")
    return world["locations"][key]


def _visible_residents(world: dict, location: str) -> list[dict]:
    return [row for row in world["residents"].values()
            if row["location"] == location and row["alive"]]


def _event(world: dict, event_type: str, public: dict, *, private: dict | None = None) -> dict:
    event_id = f"life:{world['event_counter']:06d}"
    world["event_counter"] += 1
    event = {"id": event_id, "type": event_type, "world_time": world["world_time"],
             "public": copy.deepcopy(public)}
    if private:
        event["private"] = copy.deepcopy(private)
    world["events"].append(event)
    world["events"] = world["events"][-100:]
    return event


def _knowledge(resident: dict, fact: str) -> None:
    if fact not in resident["knowledge"]:
        resident["knowledge"].append(fact)


def _witnesses(world: dict, location: str) -> list[dict]:
    return [row for row in _visible_residents(world, location) if row["id"] != world["player"].get("resident_id")]


def _alarm(world: dict, *, reason: str, witnesses: list[dict], location: str) -> None:
    world["civic_alarm"] = {"active": True, "reason": reason, "origin": location,
                            "raised_at": world["world_time"], "witnesses": [r["id"] for r in witnesses]}
    for resident in world["residents"].values():
        if not resident["alive"]:
            continue
        if resident["faction"] in {"town", "guard"}:
            resident["disposition"] = "hostile"
            resident["reaction"] = "mobilizing for the civic alarm"


def _advance(run, world: dict, elapsed: int) -> list[dict]:
    if not isinstance(elapsed, int) or elapsed < 1:
        raise LifeError("elapsed_seconds must be a positive integer")
    batches = min(MAX_TICK_BATCHES, max(1, (elapsed + TICK_SECONDS - 1) // TICK_SECONDS))
    advanced = min(elapsed, batches * TICK_SECONDS)
    world["world_time"] += advanced
    updates: list[dict] = []
    # Schedules are intentionally bounded: named residents switch to their
    # next authored anchor; offscreen facts never become narration by default.
    for resident in world["residents"].values():
        if not resident["alive"]:
            continue
        schedule = resident.get("schedule", [])
        if schedule:
            slot = (world["world_time"] // 3600) % len(schedule)
            destination = schedule[slot]
            if destination in world["locations"] and destination != resident["location"]:
                resident["location"] = destination
    intruder = world["intruder_party"]
    if intruder["status"] == "scheduled" and world["world_time"] >= intruder["arrival_at"]:
        intruder["status"] = "active"
        intruder["location"] = "market"
        updates.append({"type": "intruder_arrived", "location": "market"})
    elif intruder["status"] == "active":
        route = intruder["route"]
        step = min(intruder["route_step"], len(route) - 1)
        intruder["location"] = route[step]
        intruder["route_step"] = min(step + 1, len(route) - 1)
        updates.append({"type": "intruder_progress", "location": intruder["location"],
                        "goal": intruder["goal"]})
    # Civic force is local, physical, and fully receipted: a guard must be in
    # the same place before an alarm can harm the player.  No global damage.
    actor = _actor(run)
    local_guards = [row for row in _visible_residents(world, world["player"]["location"])
                    if row["faction"] == "guard" and row["disposition"] == "hostile"]
    if world["civic_alarm"].get("active") and local_guards and actor.hp > 0:
        guard = local_guards[0]
        natural = run.rng.d20()
        total = natural + 3
        hit = natural == 20 or (natural != 1 and total >= actor.armor_class)
        damage = run.rng.randint(1, 6) + 2 if hit else 0
        actor.hp = max(0, actor.hp - damage)
        updates.append({"type": "guard_response", "guard": guard["name"], "attack": total,
                        "hit": hit, "damage": damage, "player_hp": actor.hp})
    return updates


def _award_account(run, world: dict, reason: str) -> dict:
    from hollowstar.progression import Progression
    identity = run.context.get("account_identity")
    if not isinstance(identity, str):
        raise LifeError("life account identity is unavailable")
    progress = Progression(Path(run.context["progression_root"]))
    account = progress.migrate_life_account(identity)
    life = account["life_account"]
    award = max(1, len(world["events"]) // 3)
    life["meta_currency"] += award
    life["closed_worlds"].append({"seed": world["seed"], "reason": reason,
                                     "world_time": world["world_time"], "award": award})
    life["closed_worlds"] = life["closed_worlds"][-100:]
    account["platinum"] += award
    account["currency"] = account["platinum"]
    account["account_meta"]["meta_currency"] = account["platinum"]
    atomic_json(progress.path(identity), account)
    return {"account": identity, "award": award, "meta_currency": account["platinum"]}


def _public_resident(row: dict) -> dict:
    public = {key: copy.deepcopy(row[key]) for key in
              ("id", "name", "role", "faction", "location", "alive", "disposition", "reaction", "hp", "max_hp",
               "child", "species", "tier", "tells")}
    public["traits"] = copy.deepcopy(row.get("traits", []))[:4]
    public["offers"] = copy.deepcopy(row.get("offers", {}))
    public["dialogue"] = conversation_options(row)
    public["state"] = {"disposition": row.get("disposition", "neutral"),
                       "reaction": row.get("reaction", "going about their business"),
                       "alive": bool(row.get("alive"))}
    return public


def _resolve_band(score: int, bands: list[dict]) -> str:
    score = max(0, score)
    for band in bands:
        if score <= band["max"]:
            return band["id"]
    return bands[-1]["id"] if bands else "neutral"


def _resolve_possessions(run, resident_id: str, candidates: list[str]) -> list[str]:
    """Pick which authored possessions a resident is actually carrying this run.

    Authored possessions are candidates, not guarantees -- which ones (if any)
    are present, and in what order they are found, varies seed to seed so two
    runs of the same town do not read identically. This draws on a fork keyed
    by resident identity, never on `run.rng` directly, so adding or reordering
    a possession list here can never shift an unrelated draw elsewhere in the
    dungeon (see the RNG fork discipline in dungeon.py/rng.py).
    """
    if not candidates:
        return []
    fork = run.rng.fork(f"floor-one-possessions-{resident_id}")
    count = 1 if len(candidates) == 1 else fork.randint(1, len(candidates))
    remaining = list(candidates)
    picked = []
    for _ in range(count):
        item = fork.choice(remaining)
        picked.append(item)
        remaining.remove(item)
    return picked


def _lead_identity(run) -> dict:
    """The lead party member's custom-profile identity, if any.

    `run.context["party_identity"]` is populated by run_service.create() from
    ProfileService.inspect() for custom-built characters only; stock/divine
    party members carry an empty dict here, never Actor attributes -- Actor
    has no race_id/gender fields at all (see character_builder.py profile vs
    Actor dataclass).
    """
    identities = run.context.get("party_identity") or []
    return identities[0] if identities else {}


def view(run, *, debug: bool = False) -> dict:
    world = _world(run)
    location = _location(world)
    visible = _visible_residents(world, location["id"])
    lead_identity = _lead_identity(run)
    lead = run.party[0]
    identity = str(getattr(lead, "name", "")).lower()
    public = {
        "schema": "hollow-star-floor-one-public-1",
        "status": world["status"],
        "world_time": world["world_time"],
        "event_clock": clock.view(world),
        "room": {"id": location["id"], "title": location["name"], "terrain": location["description"],
                 "law": "The town remembers public harm.", "resident": "Town population", "motive": "visible behavior only",
                 "tells": location.get("tells", []),
                 "exits": {f"route_{index + 1}": destination for index, destination in enumerate(location.get("exits", []))}},
        "player": {"name": lead.name, "hp": lead.hp, "max_hp": lead.max_hp,
                   "ac": lead.armor_class, "armor_class": lead.armor_class,
                   "location": location["id"], "identity": identity,
                   "sprite_id": lead.sprite_id,
                   "race_id": lead_identity.get("race_id"),
                   "gender": lead_identity.get("gender"),
                   "class_id": lead_identity.get("class_id"),
                   "appearance": copy.deepcopy(lead_identity.get("appearance", {})),
                   "ability_scores": copy.deepcopy(lead.ability_scores),
                   "proficiency_bonus": lead.proficiency_bonus,
                   "initiative_bonus": lead.initiative_bonus,
                   "speed": lead.speed,
                   "features": copy.deepcopy(lead.features),
                   "resources": copy.deepcopy(lead.resources),
                   "ability_options": copy.deepcopy(CHAMPION_ABILITY_OPTIONS.get(identity, [])),
                   "equipment": copy.deepcopy(getattr(lead, "equipment", []))},
        "travel": copy.deepcopy(world.get("travel", {"active": False, "mode": "manual"})),
        "npcs": {row["id"]: _public_resident(row) for row in visible},
        "objects": copy.deepcopy(location.get("objects", {})),
        "bodies": copy.deepcopy(location.get("bodies", [])),
        "civic_alarm": copy.deepcopy(world["civic_alarm"]),
        "intruder_party": {k: copy.deepcopy(world["intruder_party"][k]) for k in
                            ("status", "location", "goal", "members")},
        "available_actions": [
            {"type": "survey", "label": "Look around or search the area"},
            {"type": "move", "label": "Travel to a connected place"},
            {"type": "talk", "label": "Talk, ask, lie, threaten, or insult"},
            {"type": "attack", "label": "Attack a visible resident"},
            {"type": "inspect", "label": "Inspect an object or body"},
            {"type": "take", "label": "Take a visible object"},
            {"type": "world_tick", "label": "Let time pass"},
        ],
        "recent_events": [copy.deepcopy(row["public"]) for row in world["events"][-5:]],
        "conversation": copy.deepcopy(world.get("conversation", [])[-8:]),
    }
    if location["id"] in {"well", "waterwheel"}:
        public["available_actions"].append({"type": "descend", "label": "Descend into the Reliquary"})
    if debug:
        public["debug"] = {"residents": copy.deepcopy(world["residents"]), "events": copy.deepcopy(world["events"])}
    return public


def start(run) -> dict:
    if isinstance(run.context.get("life_world"), dict):
        return {"event": {"type": "life_world_resumed"}, "state": view(run)}
    from hollowstar import loop_tier as lt
    content = _content()
    locations = {row["id"]: copy.deepcopy(row) for row in content["locations"]}
    bands = content.get("reaction_bands", [])
    tier = run.context.get("loop_tier", 1)
    stat_mult = lt.resident_stat_multiplier(tier)
    hostility_shift = lt.hostility_threshold_shift(tier)
    residents = {}
    for row in content["residents"]:
        item = copy.deepcopy(row)
        # tier/species/class/stances/traits/relationships/offers/tells/child/
        # tier_scaling arrive from the merged eighteen-resident population
        # layer (content/floor_one_life.json) and are carried through as-is;
        # only run-local, mutable state is set fresh here. Loop tier scales
        # HP and the hostility banding, never a child's protected status.
        base_hp = item.get("hp", 8)
        scaled_hp = max(base_hp, round(base_hp * stat_mult))
        item.update({"alive": True, "knowledge": [], "reaction": "going about their business",
                     "hp": scaled_hp, "max_hp": scaled_hp,
                     "disposition": _resolve_band(item.get("disposition_base", 0) + hostility_shift, bands),
                     "possessions": _resolve_possessions(run, item["id"], item.get("possessions", []))})
        residents[item["id"]] = item
    start_location = run.context.get("starting_location") or "market"
    if start_location not in locations:
        start_location = "market"
    run.context["life_world"] = {
        "schema": "hollow-star-floor-one-life-1", "status": "active", "seed": run.rng.seed,
        "world_time": 8 * 3600, "event_counter": 1, "events": [], "locations": locations,
        "residents": residents, "player": {"location": start_location, "resident_id": None},
        "civic_alarm": {"active": False},
        "intruder_party": {"status": "scheduled", "arrival_at": 10 * 3600, "location": None,
                           "goal": "find the old waterwheel and reach the well", "route": ["market", "well", "waterwheel"],
                           "route_step": 0, "members": ["Asha", "Bram", "Celia", "Dunn"]},
        "account": {"id": "default", "milestones": []},
        "event_clock": {"schema": clock.SCHEMA, "tick": 0, "seconds": 0,
                        "round": 0, "turn": 0, "rooms_entered": 1,
                        "rooms_resolved": 0, "history": []},
        "conversation": [],
        "travel": {"active": False, "mode": "manual", "animation": "idle",
                   "destination": "well", "path": [], "steps": 0},
    }
    world = run.context["life_world"]
    event = _event(world, "life_world_started", {"event": "life_world_started", "location": start_location,
                   "message": "A seeded Floor One town has begun its day; people, objects, and consequences now persist."})
    return {"event": {"type": "life_world_started", "receipt": event}, "state": view(run)}


def _attack(run, world: dict, action: dict) -> dict:
    location = world["player"]["location"]
    target = _resident(world, action.get("target"))
    if target.get("child"):
        raise LifeError("a directed attack against a child is never permitted")
    if target["location"] != location or not target["alive"]:
        raise LifeError("target is not a living visible resident")
    actor = _actor(run)
    natural = run.rng.d20()
    bonus = actor.proficiency_bonus + max((actor.ability_scores.get("STR", 10) - 10) // 2, 0)
    total = natural + bonus
    damage = max(1, 1 + max((actor.ability_scores.get("STR", 10) - 10) // 2, 0)) if total >= 10 else 0
    target["hp"] = max(0, target["hp"] - damage)
    witnesses = _witnesses(world, location)
    fact = f"saw {actor.name} attack {target['name']}"
    for row in witnesses:
        _knowledge(row, fact)
        row["disposition"] = "hostile"
        row["reaction"] = "drawing away or drawing steel"
    target["disposition"] = "hostile"
    target["reaction"] = "under attack"
    killed = target["hp"] == 0
    if killed:
        target["alive"] = False
        target["reaction"] = "dead"
        _location(world)["bodies"].append({"name": target["name"], "resident_id": target["id"], "cause": "violence", "at": world["world_time"]})
        _alarm(world, reason=f"public killing of {target['name']}", witnesses=witnesses, location=location)
    event = _event(world, "resident_attacked", {"event": "resident_killed" if killed else "resident_attacked",
                   "target": target["name"], "attack": {"natural": natural, "bonus": bonus, "total": total, "damage": damage},
                   "witnesses": [row["name"] for row in witnesses], "civic_alarm": world["civic_alarm"]["active"]})
    return {"event": {"type": "resident_killed" if killed else "resident_attacked", "receipt": event}, "state": view(run)}


SURVEY_ACTIONS = {"survey", "search", "look", "look_around", "observe_room", "inspect_room",
                  "investigate", "search_room", "test-perception"}
AREA_WORDS = {"room", "area", "square", "around", "place", "surroundings", "scene", "here", "town", "street"}
SUPPORTED_HINT = ("look around / search the area, go to <place>, talk/ask/threaten <resident>, "
                  "inspect/open/take <object>, attack <resident>, wait")


def _names_area(location: dict, raw: object) -> bool:
    if not isinstance(raw, str):
        return False
    words = set(raw.replace("-", " ").replace("_", " ").lower().split())
    location_words = set(str(location.get("name", "")).lower().split()) | {str(location.get("id", "")).lower()}
    return bool(words & AREA_WORDS) or (bool(words) and words <= location_words)


def _survey(run, world: dict) -> dict:
    location = _location(world)
    visible = _visible_residents(world, location["id"])
    objects = {key: row.get("name", key) for key, row in location.get("objects", {}).items()}
    event = _event(world, "area_surveyed", {
        "event": "area_surveyed", "location": location["id"], "title": location["name"],
        "description": location["description"], "tells": copy.deepcopy(location.get("tells", [])),
        "objects": objects, "residents": [row["name"] for row in visible],
        "bodies": len(location.get("bodies", [])), "exits": list(location.get("exits", [])),
        "hint": SUPPORTED_HINT,
    })
    _advance(run, world, 60)
    clock.emit(world, "area_surveyed", seconds=60, phase="city", payload={"location": location["id"]})
    return {"event": {"type": "area_surveyed", "receipt": event}, "state": view(run)}


def act(run, action: dict) -> dict:
    if not isinstance(action, dict):
        raise LifeError("life action must be an object")
    world = _world(run)
    if world["status"] != "active":
        raise LifeError("this world-cycle is closed")
    kind = action.get("type")
    if kind == "world_tick":
        elapsed = int(action.get("elapsed_seconds", TICK_SECONDS))
        updates = _advance(run, world, elapsed)
        clock.emit(world, "world_tick", seconds=elapsed, phase="city",
                   payload={"updates": updates})
        closed = None
        if _actor(run).hp <= 0:
            world["status"] = "closed"
            closed = _award_account(run, world, "player_death")
        event = _event(world, "world_tick", {"event": "world_tick", "elapsed_seconds": elapsed, "updates": updates})
        if closed:
            event["public"].update({"world_cycle_closed": True, **closed})
        return {"event": {"type": "world_tick", "receipt": event}, "state": view(run)}
    if kind == "end_cycle":
        actor = _actor(run)
        if actor.hp > 0:
            raise LifeError("a world-cycle can close only after the player character dies")
        world["status"] = "closed"
        award = _award_account(run, world, "player_death")
        event = _event(world, "world_cycle_closed", {"event": "world_cycle_closed", "reason": "player_death", **award})
        return {"event": {"type": "world_cycle_closed", "receipt": event}, "state": view(run)}
    if kind == "move":
        location = _location(world)
        destination = action.get("destination")
        if not isinstance(destination, str) or destination not in location.get("exits", []):
            raise LifeError("destination is not connected to the current location")
        world["player"]["location"] = destination
        updates = _advance(run, world, 300)
        clock.emit(world, "move", seconds=300, phase="city",
                   payload={"destination": destination, "updates": updates})
        event = _event(world, "moved", {"event": "moved", "destination": destination})
        return {"event": {"type": "moved", "receipt": event}, "state": view(run)}
    if kind in {"descend", "enter_gauntlet", "enter_reliquary"}:
        if world["player"]["location"] not in {"well", "waterwheel"}:
            raise LifeError("the descent route is not available from this location")
        clock.emit(world, "descent", seconds=60, phase="city",
                   payload={"location": world["player"]["location"]})
        event = _event(world, "descent_started", {
            "event": "descent_started", "location": world["player"]["location"],
            "next": "procedural_gauntlet",
        })
        return {"event": {"type": "descent_started", "receipt": event}, "state": view(run)}
    if kind == "talk":
        target = _resident(world, action.get("target"))
        if target["location"] != world["player"]["location"] or not target["alive"]:
            raise LifeError("resident is not available to talk here")
        mode = str(action.get("mode", "speak"))
        if mode not in {"speak", "ask", "lie", "threaten", "insult", "trade"}:
            raise LifeError("unsupported conversation mode")
        text = str(action.get("text", action.get("intent", ""))).strip()
        conversation = resolve_conversation(target, text, mode)
        target["disposition"] = conversation["disposition_after"]
        target["reaction"] = conversation["reaction"]
        if conversation["consequence"] == "knowledge_shared":
            fact = conversation["text"]
            _knowledge(target, fact)
        world.setdefault("conversation", []).append({
            "speaker": target["name"], "text": conversation["text"],
            "target": target["id"], "mode": mode,
            "at": world["world_time"], "consequence": conversation["consequence"],
        })
        _advance(run, world, 60)
        clock.emit(world, "conversation", seconds=60, phase="city",
                   payload={"target": target["id"], "mode": mode,
                            "consequence": conversation["consequence"]})
        event = _event(world, "conversation_resolved", {"event": "conversation_resolved", "target": target["name"],
                       "mode": mode, "text": text, "reply": conversation["text"],
                       "reaction": target["reaction"], "consequence": conversation["consequence"],
                       "visible_tell": target.get("tell", "")})
        return {"event": {"type": "conversation_resolved", "receipt": event}, "state": view(run)}
    if kind in SURVEY_ACTIONS:
        return _survey(run, world)
    if kind in {"inspect", "take", "open"}:
        location = _location(world)
        object_id = action.get("object") or action.get("object_id")
        if kind == "inspect" and _names_area(location, object_id):
            return _survey(run, world)
        if not isinstance(object_id, str) or object_id not in location.get("objects", {}):
            names = ", ".join(sorted(location.get("objects", {}))) or "none"
            raise LifeError(f"object is not visible in this location (visible objects: {names})")
        obj = location["objects"][object_id]
        if kind == "open":
            if not obj.get("container"):
                raise LifeError("object is not an openable container")
            obj["open"] = True
        if kind == "take":
            if obj.get("fixed"):
                raise LifeError("object is fixed in place")
            del location["objects"][object_id]
        event = _event(world, f"object_{kind}", {"event": f"object_{kind}", "object": obj.get("name", object_id), "location": location["id"]})
        seconds = {"inspect": 120, "take": 30, "open": 60}[kind]
        _advance(run, world, seconds)
        clock.emit(world, f"object_{kind}", seconds=seconds, phase="city",
                   payload={"object": object_id})
        return {"event": {"type": f"object_{kind}", "receipt": event}, "state": view(run)}
    if kind == "attack":
        return _attack(run, world, action)
    raise LifeError(f"unsupported Floor One life action {kind!r}; the town supports: {SUPPORTED_HINT}")
