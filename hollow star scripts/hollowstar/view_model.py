"""Stable public view model for terminal and future graphical clients.

This is a projection, never a second state store.  It accepts the host's
already-public state and deliberately omits debug/private fields.  Clients
may render this shape without knowing whether the run is DESIGN or SANDBOX.
"""
from __future__ import annotations

import copy
from hollowstar import champion_rules, looks, salience
from hollowstar.profiles import presentation_sprite_id
from hollowstar.scene import build_scene
from hollowstar.explanations import actor_explanation
from hollowstar.items import Item, public_item


VISIBLE_EVENTS_LIMIT = 5


def _public_macros(macros):
    """Expose configured Macro intent without leaking runtime or private state."""
    if not isinstance(macros, dict):
        return {}
    visible = {}
    for actor, entries in macros.items():
        if not isinstance(entries, list):
            continue
        visible[str(actor)] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            visible[str(actor)].append({
                key: copy.deepcopy(entry[key])
                for key in ("id", "name", "priority", "when", "then", "cooldown")
                if key in entry
            })
    return visible


PUBLIC_EVENT_DROP_KEYS = {
    "audit",
    "audit_events",
    "debug",
    "debug_readout",
    "sealed_record",
    "state",
    "visible_state",
}
PUBLIC_EVENT_KEEP_KEYS = {
    "action",
    "actor",
    "atmosphere",
    "commentary",
    "damage",
    "evidence",
    "event",
    "healing",
    "message",
    "note",
    "object",
    "object_id",
    "outcome",
    "pressure",
    "purchase",
    "presentation",
    "reaction_kind",
    "receipt",
    "result",
    "reward",
    "roll",
    "round",
    "sfx",
    "status",
    "target",
    "total",
    "type",
    "voice",
}


def narrator_state(state: dict) -> dict:
    """Return bounded non-narrator state beside the compact public projection."""
    if not isinstance(state, dict):
        return {}
    # Drop the bulky pieces before copying, not after: `content` is discarded
    # and only the visible tail of `events` survives.
    trimmed = {key: value for key, value in state.items() if key != "content"}
    events = trimmed.get("events")
    if isinstance(events, list):
        trimmed["events"] = events[-VISIBLE_EVENTS_LIMIT:]
    return copy.deepcopy(trimmed)


def redact_public(value):
    """Remove true Rune identity from narrator-facing nested event data."""
    if isinstance(value, Item):
        # A live equipment instance must never reach the wire as an object.
        value = public_item(value)
    if isinstance(value, list):
        return [redact_public(item) for item in value]
    if not isinstance(value, dict):
        return value
    if value.get("kind") == "imprint" and not value.get("identified", False):
        return {"id": value.get("id"), "kind": "imprint",
                "name": value.get("unidentified_descriptor", "unidentified Rune"),
                "temporary": True, "slot": value.get("slot"),
                "identified": False, "rarity": "unknown", "level": value.get("level", 1),
                "presentation": {"rarity": "unknown", "silhouette": "trinket",
                                 "material": "unknown", "slot": value.get("slot"),
                                 "fx": [], "tells": [], "affixes": []}}
    return {
        key: redact_public(item)
        for key, item in value.items()
        if key != "true_name" and key not in PUBLIC_EVENT_DROP_KEYS
    }


def public_event_summary(value):
    """Return a compact narrator-safe event receipt for repeated transport."""
    redacted = redact_public(value)
    if not isinstance(redacted, dict):
        return {}
    if isinstance(redacted.get("combat"), dict):
        public = public_event_summary(redacted["combat"])
        for key in ("reward", "commentary", "sfx", "pressure"):
            if key in redacted: public[key] = copy.deepcopy(redacted[key])
        return public
    if redacted.get("type") == "reaction_and_movement" and isinstance(redacted.get("reaction"), dict):
        # The strike is what a viewer sees; the committed step rides along.
        public = public_event_summary(redacted["reaction"])
        public.setdefault("reaction_kind", redacted.get("reaction_kind"))
        if redacted.get("presentation") and not public.get("presentation"):
            public["presentation"] = copy.deepcopy(redacted["presentation"])
        public["movement"] = copy.deepcopy(redacted.get("movement"))
        return public
    public = {key: redacted[key] for key in PUBLIC_EVENT_KEEP_KEYS if key in redacted}
    if redacted.get("type") in {"cast", "staff_cast"}:
        # Spell choreography carries only visible presentation and resolved outcomes.
        # Do not publish the ruling, private resources, or arbitrary nested evidence.
        spec = redacted.get("ruling") or {}
        element = str(spec.get("damage_type") or redacted.get("damage_type") or "force").lower()
        stance = ("mend" if spec.get("operation") == "heal" else
                  "overhead" if spec.get("radius") else
                  "ward" if spec.get("condition") else
                  "gather" if element == "force" else "aim")
        presentation = copy.deepcopy(public.get("presentation") or {})
        authored_presentation = spec.get("presentation") or {}
        authored = authored_presentation.get("casting") if isinstance(authored_presentation, dict) else None
        explicit = presentation.get("casting")
        visual = {}
        # Only visible choreography crosses this boundary. Invalid overrides
        # fall back without leaking arbitrary spell-spec fields.
        for candidate in (authored, explicit):
            if not isinstance(candidate, dict):
                continue
            if candidate.get("stance") in ("aim", "gather", "overhead", "ward", "mend"):
                visual["stance"] = candidate["stance"]
            if type(candidate.get("hands")) is int and candidate["hands"] in {1, 2}:
                visual["hands"] = candidate["hands"]
            if candidate.get("source") in ("hands", "implement", "auto"):
                visual["source"] = candidate["source"]
        stance = visual.get("stance", stance)
        presentation["casting"] = {"stance": stance,
                                   "hands": visual.get("hands", 2 if stance in {"gather", "overhead", "ward"} else 1),
                                   "source": visual.get("source", "implement" if redacted["type"] == "staff_cast" else "hands"),
                                   "element": "heal" if stance == "mend" else element}
        public["presentation"] = presentation
        if "damage_type" in redacted:
            public["damage_type"] = redacted["damage_type"]
        events = []
        for event in redacted.get("events", []):
            if not isinstance(event, dict):
                continue
            visible = {key: copy.deepcopy(event[key]) for key in
                       ("type", "target", "damage", "damage_type", "healing") if key in event}
            for roll_key in ("attack", "save"):
                roll = event.get(roll_key)
                if isinstance(roll, dict):
                    visible[roll_key] = {key: roll[key] for key in
                                        ("success", "natural", "total", "bonus", "dc") if key in roll}
            result = event.get("result")
            if isinstance(result, dict):
                visible["result"] = {key: copy.deepcopy(result[key]) for key in
                                     ("type", "target", "damage", "damage_type", "healing", "condition", "applied") if key in result}
            events.append(visible)
        public["events"] = events
    if redacted.get('type') == 'grand_cleave':
        public['critical'] = redacted.get('critical') is True
        public['bonus'] = redacted.get('bonus',19)
        public['damage_rolls'] = [n for n in redacted.get('damage_rolls',[])[:4] if type(n) is int]
        public['includes_allies'] = True
        public['facing'] = redacted.get('facing')
        public['targets'] = []
        for event in redacted.get('targets', []):
            if not isinstance(event, dict): continue
            result = event.get('result') or {}
            public['targets'].append({'target':event.get('target'),'miss':event.get('miss') is True,
                'result':{k:copy.deepcopy(result[k]) for k in ('target','damage','damage_type','parted') if k in result}})
        public['structures'] = [{k:copy.deepcopy(row[k]) for k in ('object_id','name','damage','destroyed') if k in row}
                                for row in redacted.get('structures',[]) if isinstance(row,dict)]
    return public


def _arcade_view(state: dict, event: dict | None = None) -> dict | None:
    """Select only the host's public arcade frame, including its final receipt."""
    candidate = state.get("arcade") if isinstance(state.get("arcade"), dict) else None
    if candidate is None and isinstance(event, dict):
        nested = event.get("arcade") if isinstance(event.get("arcade"), dict) else event
        candidate = nested.get("arcade_view") if isinstance(nested, dict) else None
    return copy.deepcopy(candidate) if isinstance(candidate, dict) else None



def _available_actions(state: dict, combat: dict) -> list[dict]:
    """Describe visible affordances; legality remains owned by the host."""
    if state.get("schema") == "hollow-star-floor-one-public-1":
        return [{"id": action, "label": label} for action, label in (
            ("investigate", "Look around"), ("talk", "Talk"), ("inspect", "Inspect"),
            ("move", "Travel"), ("idle_tick", "Advance safely"), ("descend", "Descend"),)]
    if combat and not combat.get("complete"):
        if combat.get("pending"):
            return [{"id": "resolve_reaction", "label": "Resolve reaction"},
                    {"id": "decline_reaction", "label": "Decline reaction"}]
        rows = [{"id": action, "label": label} for action, label in (
            ("attack", "Attack"), ("move", "Move"), ("cast", "Cast"),
            ("inspect", "Inspect"), ("end_turn", "End turn"),)]
        # The engine's contextual catalog (tactical.contextual_actions) adds
        # help text to the core five and appends whatever else is legal now:
        # dodge, dash, disengage, shove, trip, grapple, help, break free, stand.
        catalog = {row.get("id"): row for row in combat.get("contextual_actions") or [] if isinstance(row, dict)}
        for row in rows:
            extra = catalog.get(row["id"])
            if extra:
                row.update({"category": extra.get("category"), "cost": extra.get("cost"),
                            "help": extra.get("help"), "available": extra.get("available", True)})
                if extra.get("reason"):
                    row["reason"] = extra["reason"]
        known = {row["id"] for row in rows}
        for action_id, extra in catalog.items():
            if action_id not in known and extra.get("available"):
                rows.append({"id": action_id, "label": extra.get("label", action_id),
                             "category": extra.get("category"), "cost": extra.get("cost"),
                             "help": extra.get("help"), "targets": list(extra.get("targets") or [])})
        return rows
    if state.get("schema") == "hollow-star-dd-sandbox-1":
        return [{"id": action, "label": label} for action, label in (
            ("conversation", "Talk"), ("inspect", "Inspect"),
            ("move_room", "Move"), ("attack", "Attack"),
            ("end_turn", "Wait"), ("escape", "Escape"),)]
    actions = [("investigate", "Investigate"), ("enter", "Enter"),
               ("inspect", "Inspect"), ("rest", "Rest"), ("exit", "Leave")]
    if state.get("room", {}).get("identification_service"):
        actions.append(("identify", "Identify a Rune"))
    return [{"id": action, "label": label} for action, label in actions]


def _combat_effect_row(effect: dict) -> dict:
    """Whitelist the visible effect and its source; never export private ruling data."""
    result = {field: redact_public(copy.deepcopy(effect[field])) for field in (
        "id", "name", "kind", "status", "duration", "remaining", "timer_actor",
        "summary", "tell", "operation", "stat", "condition", "stack_group",
    ) if field in effect}
    source = effect.get("source")
    if isinstance(source, dict):
        result["source"] = {field: copy.deepcopy(source[field]) for field in ("id", "name", "kind") if field in source}
    return result


def _actor(row: dict, key: str) -> dict:
    scores = row.get("ability_scores", {})
    modifiers = row.get("ability_modifiers", {})
    if not modifiers and isinstance(scores, dict):
        modifiers = {name: (int(value) - 10) // 2 for name, value in scores.items()}
    explanation = actor_explanation({**row, "id": key, "armor_class": row.get("ac", row.get("armor_class"))})
    item = {
        "id": key,
        "name": row.get("name", key),
        "identity": row.get("identity"),
        "sprite_id": row.get("sprite_id") or presentation_sprite_id(row.get("race_id", "human"), row.get("gender", "other")),
        "race_id": row.get("race_id"), "gender": row.get("gender"), "class_id": row.get("class_id"),
        # Body size class (tiny..gargantuan), when the rules name one. The client
        # sizes a figure's box and hit box from it; nothing here changes a rule.
        "size": str(row.get("size")).lower() if row.get("size") else None,
        # Cosmetic selections from character creation.  Presentation only; the
        # client tints its layer stack from these and nothing else reads them.
        "appearance": copy.deepcopy(row.get("appearance", {})),
        "controller": row.get("controller", "unknown"),
        "hp": row.get("hp"),
        "max_hp": row.get("max_hp"),
        "armor_class": row.get("ac", row.get("armor_class")),
        "ability_scores": copy.deepcopy(scores),
        "ability_modifiers": copy.deepcopy(modifiers),
        "proficiency_bonus": row.get("proficiency_bonus", 0),
        "initiative_bonus": row.get("initiative_bonus", 0),
        "speed": row.get("speed", 0),
        "economy": copy.deepcopy(row.get("economy", {})),
        "movement": row.get("movement"),
        "status": row.get("statuses", row.get("status", [])),
        "position": row.get("position"),
        # redact_public() converts any live Item to its public dict on its
        # own (see its guard above); no need to pre-convert here too.
        "equipment": redact_public(copy.deepcopy(row.get("equipment", []) or [])),
        # These are public explanation projections, not a second mechanics
        # store.  They let the client render examine/tooltips from host data.
        "features": copy.deepcopy(explanation["features"]),
        "resources": copy.deepcopy(row.get("resources", {})),
        "spell_save_dc": row.get("spell_save_dc"),
        "spell_attack_bonus": row.get("spell_attack_bonus"),
        "ability_options": copy.deepcopy(row.get("ability_options", [])),
        "skill_bonuses": copy.deepcopy(explanation["skills"]),
        "conditions": copy.deepcopy(explanation["conditions"]),
        "effects": redact_public(copy.deepcopy(explanation["effects"])),
        "active_effects": [
            _combat_effect_row(effect)
            for effect in row.get("active_effects") or [] if isinstance(effect, dict)
        ],
        "weapon_profile": copy.deepcopy(explanation["weapon"]),
        "armor_profile": copy.deepcopy(explanation["armor"]),
    }
    _dress(item, row)
    return item


def _dress(item: dict, row: dict) -> None:
    """Presentation for figures with no creator sheet, and what people notice.

    A fixture foe or filler actor ('Town watch 2') takes its authored look from
    content/looks.json; a custom lead keeps its own appearance.  `notice` is the
    compact salience read (content/salience.json).  Presentation only.
    """
    if not item.get("appearance"):
        look = looks.for_actor(item.get("name"), item.get("id"))
        for key in ("race_id", "gender", "age", "aura", "costume", "appearance"):
            if look.get(key) and not item.get(key):
                item[key] = look[key]
    item["notice"] = salience.public_notice({**item, "hp": row.get("hp"), "max_hp": row.get("max_hp")})


def _flight_arena(state: dict, actors: list[dict], opposition: list[dict]) -> dict | None:
    """Return a public 2D flight projection over the authoritative combat state."""
    combat = state.get("combat")
    if not isinstance(combat, dict) or combat.get("complete"):
        return None
    wren_key = next((row["id"] for row in actors
                     if champion_rules.flag(row.get("identity"), "flight_arena") or str(row.get("name", "")).lower() == "wren"), None)
    if wren_key is None:
        return None
    positions = combat.get("positions") or {}
    bounds = {"x": [0, 120], "y": [0, 120], "z": [0, 120]}
    def projected(rows):
        result = []
        for row in rows:
            key = row.get("id")
            pos = positions.get(key) or row.get("position") or [0, 0, 0]
            result.append({"id": key, "x": pos[0], "y": pos[1], "z": pos[2],
                           "facing": "left" if pos[0] > 60 else "right",
                           "animation": "idle" if key != wren_key else "glide",
                           "movement": (combat.get("economy", {}).get(key) or {}).get("movement", 0)})
        return result
    return {
        "schema": "hollow-star-flight-arena-1",
        "bounds": bounds,
        "controller": wren_key,
        "actors": projected(actors),
        "opposition": projected(opposition),
        "valid_actions": ["flight_move", "ascend", "descend", "dash", "attack", "cast", "land", "escape"],
    }


def _combat_view(combat: dict) -> dict | None:
    """Project tactical state needed by the UI without exposing combat rules."""
    if not isinstance(combat, dict):
        return None
    pending = []
    for window in combat.get("pending", []):
        if not isinstance(window, dict):
            continue
        pending.append({key: copy.deepcopy(window[key]) for key in (
            "kind", "reactor", "target", "options", "source", "feature",
            "spell_level", "damage_type", "amount", "critical",
        ) if key in window})
    economy = {}
    for actor, values in (combat.get("economy") or {}).items():
        if isinstance(values, dict):
            economy[str(actor)] = {key: values[key] for key in (
                "action", "bonus", "reaction", "movement",
            ) if key in values}
    positions = copy.deepcopy(combat.get("positions", {}))
    current = combat.get("current")
    target_context = []
    if isinstance(current, str) and current.startswith("p") and current in positions:
        origin = positions[current]
        if isinstance(origin, list):
            for target, destination in positions.items():
                if not str(target).startswith("e") or not isinstance(destination, list):
                    continue
                axes = range(min(3, len(origin), len(destination)))
                if not axes:
                    continue
                distance = max(abs(origin[index] - destination[index]) for index in axes)
                target_context.append({"id": str(target), "distance_ft": distance})
    disabled_reasons = {}
    if combat.get("pending"):
        disabled_reasons = {action: "Resolve or decline the open reaction first."
                            for action in ("attack", "move", "cast", "end_turn")}
    elif current and not str(current).startswith("p"):
        disabled_reasons = {action: "It is not a player-controlled turn."
                            for action in ("attack", "move", "cast", "end_turn")}
    projected = {
        "schema": "hollow-star-public-combat-1",
        "round": combat.get("round"),
        "current": current,
        "order": copy.deepcopy(combat.get("order", [])),
        "economy": economy,
        "positions": positions,
        "pending": pending,
        "complete": bool(combat.get("complete")),
        "surprised": copy.deepcopy(combat.get("surprised", {})),
        "target_context": target_context,
        "disabled_reasons": disabled_reasons,
    }
    # Public catalog rows (label, category, cost, help, availability, legal
    # target ids) and any Turn 0 cascade that opened this fight; omitted when
    # empty to keep idle envelopes inside their wire budget.
    for key in ("contextual_actions", "turn_zero", "formation", "display_capacity"):
        if combat.get(key):
            projected[key] = redact_public(copy.deepcopy(combat[key]))
    return projected


def build_public_view(state: dict, *, event: dict | None = None, mode: str | None = None,
                      progression: dict | None = None, run_id: str | None = None) -> dict:
    """Normalize visible state into the client-facing HSR presentation model."""
    state = state if isinstance(state, dict) else {}
    actors: list[dict] = []
    opposition: list[dict] = []
    raw_actors = state.get("actors")
    if not isinstance(raw_actors, dict) and isinstance(state.get("combat"), dict):
        raw_actors = state["combat"].get("actors")
    combat_rules = state.get("combat", {}).get("rules") if isinstance(state.get("combat"), dict) else None
    if isinstance(raw_actors, dict):
        for key, row in raw_actors.items():
            if not isinstance(row, dict):
                continue
            item = _actor(row, str(key))
            if item["position"] is None and isinstance(state.get("combat"), dict):
                item["position"] = (state["combat"].get("positions") or {}).get(key)
            if not item.get("identity") and isinstance(combat_rules, dict):
                item["identity"] = (combat_rules.get(key) or {}).get("identity")
            if not item.get("size") and isinstance(combat_rules, dict) and (combat_rules.get(key) or {}).get("size"):
                item["size"] = str((combat_rules.get(key) or {}).get("size")).lower()
            if item["controller"] == "player" or str(key).startswith("p"):
                actors.append(item)
            else:
                opposition.append(item)
    party = state.get("party")
    party_rows = party.items() if isinstance(party, dict) else enumerate(party or [])
    for key, row in party_rows:
        if isinstance(row, dict):
            actor_key = row.get("id", str(key) if isinstance(key, str) else f"p{key}")
            if not any(actor["id"] == actor_key for actor in actors):
                item = _actor(row, actor_key)
                if not item.get("identity") and isinstance(combat_rules, dict):
                    item["identity"] = (combat_rules.get(actor_key) or {}).get("identity")
                actors.append(item)
    # Tactical combat intentionally projects mechanics first. Reattach the
    # already-public party presentation fields so a custom lead does not turn
    # into a generic human when combat starts.
    party_by_id = {row.get("id"): row for row in (party or []) if isinstance(row, dict) and row.get("id")}
    for item in actors:
        source = party_by_id.get(item.get("id"))
        if not source:
            continue
        for key in ("sprite_id", "race_id", "gender", "appearance", "class_id", "equipment"):
            if source.get(key):
                item[key] = (redact_public(copy.deepcopy(source[key]))
                             if key == "equipment" else copy.deepcopy(source[key]))
        item["notice"] = salience.public_notice(item)
    mob = state.get("mob")
    if isinstance(mob, dict):
        opposition.append({"id": mob.get("id", "mob"), "name": mob.get("name", "mob"),
                           "count": mob.get("count"), "controller": "npc", "status": mob.get("status", [])})
    if not actors and isinstance(state.get("player"), dict):
        player = copy.deepcopy(state["player"])
        player.setdefault("name", "Lead")
        player.setdefault("id", "p0")
        player.setdefault("controller", "player")
        actors.append(_actor(player, "p0"))

    room = state.get("room") if isinstance(state.get("room"), dict) else {}
    room_world = room.get("world_state") if isinstance(room.get("world_state"), dict) else {}
    if not room_world:
        room_world = {
            "objects": state.get("objects", {}),
            "npcs": state.get("npcs", {}),
            "subrooms": state.get("subrooms", []),
        }
    persistence = room.get("persistence") if isinstance(room.get("persistence"), dict) else {}
    combat = state.get("combat") if isinstance(state.get("combat"), dict) else {}
    recent_event = public_event_summary(event) if isinstance(event, dict) else {}
    arcade = _arcade_view(state, event)
    if arcade:
        arcade_entities = arcade.get("entities", {})
        for item in actors + opposition:
            frame = arcade_entities.get(item["id"]) if isinstance(arcade_entities, dict) else None
            if isinstance(frame, dict) and isinstance(frame.get("position"), list):
                item["position"] = copy.deepcopy(frame["position"])
    inventory = state.get("inventory", {})
    visible_inventory = redact_public(copy.deepcopy(list(inventory.values()) if isinstance(inventory, dict)
                                                     else inventory if isinstance(inventory, list) else []))
    result = {
        "schema": "hollow-star-public-view-1",
        "mode": mode,
        # Exploration views are intentionally smaller than the persisted Run
        # object and therefore do not always carry the run identity.  The
        # adapter owns that identity; preserve it in the public projection so
        # reconnecting clients can correlate a readout without inspecting a
        # private save or relying on an outer envelope.
        "run_id": state.get("run_id") or run_id,
        "status": state.get("status"),
        # The engine has exactly two public terminal outcomes -- "completed" or
        # "dead" -- and this is `None` while the run is still active. `status`
        # keeps the finer-grained reason (cleared/escaped/defeated/ejected);
        # `outcome` is what a client should branch display on.
        "outcome": state.get("outcome"),
        "round": state.get("round", combat.get("round")),
        "turn": state.get("turn", combat.get("current")),
        "event_clock": copy.deepcopy(state.get("event_clock", {})),
        "conversation": copy.deepcopy(state.get("conversation", [])),
        "world_time": state.get("world_time"),
        "progression": {
            "hsr_rank": state.get("hsr_rank", (progression or {}).get("rank")),
            "rank_xp": state.get("rank_xp", (progression or {}).get("rank_xp")),
            "rooms_cleared": state.get("rooms_cleared"),
            "currency": state.get("currency", state.get("meta_currency", (progression or {}).get("currency"))),
            "platinum": state.get("platinum", (progression or {}).get("platinum", (progression or {}).get("currency"))),
            "gold": state.get("gold", state.get("currency")),
            "gems": state.get("gems", state.get("components")),
            "discoveries": state.get("discoveries", []),
            "upgrades": (progression or {}).get("upgrades", {}),
            "settled_runs": sorted((progression or {}).get("runs", {})),
            "account_tracking": copy.deepcopy((progression or {}).get("tracking", {})),
        },
        "tracking": copy.deepcopy(state.get("tracking", {})),
        "scene": build_scene(state),
        "inventory": visible_inventory,
        "imprints": redact_public(copy.deepcopy(state.get("imprints", {}))),
        "attunement": redact_public(copy.deepcopy(state.get("attunement", {}))),
        "unidentified_runes": [item for item in visible_inventory
                               if item.get("kind") == "imprint" and not item.get("identified", False)],
        "room": {
            "id": room.get("id") or room.get("room_id") or persistence.get("room_id"),
            "name": room.get("name", room.get("title")),
            "apparent_function": room.get("apparent_function"),
            "resident": room.get("resident"),
            "posture": room.get("posture"),
            "law": room.get("law"),
            "terrain": room.get("terrain"),
            "encounter_mode": room.get("encounter_mode"),
            "condition": room.get("condition"),
            # Lifecycle state is public gameplay state, not hidden room
            # metadata. The browser uses these flags to keep reward and
            # checkpoint messaging truthful after a reconnect/readout.
            "resolved": bool(room.get("resolved", False)),
            "reward_claimed": bool(room.get("reward_claimed", False)),
            "exits": room.get("exits", {}),
            "visible_tells": room.get("tells", room.get("perceived_facts", [])),
            "objects": redact_public(room_world.get("objects", {})),
            "npcs": redact_public(room_world.get("npcs", {})),
            "subrooms": redact_public(room_world.get("subrooms", [])),
            "world_time": state.get("world_time"),
        },
        "party": actors,
        "opposition": opposition,
        "combat": _combat_view(combat),
        "arcade": arcade,
        "narration": recent_event.get("message", recent_event.get("outcome", recent_event.get("atmosphere"))),
        "last_event": recent_event,
        "recent_receipts": [public_event_summary(item) for item in list(state.get("events", []))[-5:]],
        "pressure_tells": state.get("pressure_tells", {}),
        "available_actions": state.get("available_actions") or _available_actions(state, combat),
        "checkpoint": redact_public(copy.deepcopy(state.get("checkpoint", {}))),
        "descent": copy.deepcopy(state.get("descent")),
        "auto": {"supported": True, "active": bool(state.get("auto_enabled", False)),
                 "step_command": "design_auto_combat" if combat and not combat.get("complete") else "design_auto",
                 "macros": _public_macros(state.get("macros", {}))},
        "hooks": {
            "weapons": "acquire_weapon",
            "armor": "acquire_armor",
            "rune_imprint": "imprint_rune",
            "currency": "readout progression.currency",
            "npcs": "npc_list",
            "conversation": "conversation",
            "idle_preparation": "prepare_idle",
            "auto_battle": "auto_battle",
            "salvage": "salvage",
            "trade": "trade",
            "shops": "buy",
        },
    }
    if isinstance(state.get("expedition"), dict):
        result["expedition"] = redact_public(copy.deepcopy(state["expedition"]))
    result["flight_arena"] = _flight_arena(state, actors, opposition)
    result["next_actions"] = copy.deepcopy(result["available_actions"])
    return result
