"""Encounters expedition: a branching route laid over the dungeon's rooms.

The dungeon walks a fixed room sequence. An expedition turns each room slot
into a column of choices -- fight, elite, rest, loot, shop, hazard -- ending
in a boss column, and lets the player pick the next node and how to resolve
it: real-time ``arcade``, hand-driven ``tactical``, or gambit-driven ``auto``.

Nothing here rolls dice, deals damage or grants rewards. Choosing a node only
sets ``dungeon['next_room']`` for :func:`hollowstar.dungeon.enter`; every
resolution runs through :func:`hollowstar.dungeon.act`, and every automatic
choice comes from :mod:`hollowstar.policies`.
"""
from __future__ import annotations

import copy

from hollowstar import tactical as t

SCHEMA = 1
MODES = {"arcade", "tactical", "auto"}
# node type -> dungeon room kind
NODE_KINDS = {"fight": "combat", "elite": "combat", "rest": "rest", "loot": "secret",
              "shop": "shop", "hazard": "hazard", "social": "social", "boss": "boss"}
NODE_LABELS = {"fight": "Fight", "elite": "Elite ladder", "rest": "Rest", "loot": "Cache",
               "shop": "Merchant", "hazard": "Hazard", "social": "Residents", "boss": "Boss"}
MIDDLE_WEIGHTS = (("fight", 5), ("elite", 2), ("loot", 2), ("hazard", 2),
                  ("rest", 1), ("shop", 1), ("social", 1))
COMBAT_NODES = {"fight", "elite", "boss"}
MAX_AUTO_NODES = 6
MAX_AUTO_ACTIONS = 600


class ExpeditionError(t.ActionError):
    pass


def _dungeon(run):
    d = run.context.get("dungeon")
    if not isinstance(d, dict):
        raise ExpeditionError("start a dungeon run before an expedition")
    return d


def _floor_room_count(d, floor):
    from hollowstar.dungeon import _room_types_for_floor
    return len(_room_types_for_floor(d, floor))


def ladder(node_type, floor, column):
    """Wave ladder for a combat node: enemy count and per-wave split."""
    if node_type == "elite":
        waves = [1, 1, 2] if floor >= 3 else [1, 1, 1]
    elif node_type == "fight":
        waves = [1, 1] if column >= 3 or floor >= 2 else [1]
    else:
        return None
    return {"arcade_enemy_count": sum(waves),
            "waves": [{"enemy_count": count} for count in waves]}


def build_floor(run, floor):
    """Seeded route graph for one floor; the same seed always draws the same map."""
    d = _dungeon(run)
    count = _floor_room_count(d, floor)
    if count < 2:
        raise ExpeditionError("an expedition floor needs at least two rooms")
    rng = run.rng.fork(f"expedition:{floor}")
    columns = []
    for column in range(1, count + 1):
        if column == count:
            types = ["boss"]
        elif column == 1 and floor == 1:
            # The dungeon already entered room 1:1 when it started.
            types = [d["rooms"].get("1:1", {}).get("kind", "social")]
            types = ["fight" if types[0] == "combat" else "loot" if types[0] == "secret" else types[0]]
        elif column == count - 1:
            types = ["rest", rng.weighted_choice([n for n, _ in MIDDLE_WEIGHTS], [w for _, w in MIDDLE_WEIGHTS])]
        else:
            width = 2 + (1 if rng.random() < 0.5 else 0)
            types = [rng.weighted_choice([n for n, _ in MIDDLE_WEIGHTS], [w for _, w in MIDDLE_WEIGHTS])
                     for _ in range(width)]
        nodes = []
        for index, node_type in enumerate(types):
            node = {"id": f"{floor}:{column}:{index}", "floor": floor, "column": column,
                    "type": node_type, "kind": NODE_KINDS[node_type],
                    "label": NODE_LABELS[node_type], "links": []}
            waves = ladder(node_type, floor, column)
            if waves:
                node["ladder"] = waves
            nodes.append(node)
        columns.append(nodes)
    # Every node links forward to at least one node; every forward node has a parent.
    for current, following in zip(columns, columns[1:]):
        for index, node in enumerate(current):
            primary = following[min(index * len(following) // max(1, len(current)), len(following) - 1)]
            node["links"].append(primary["id"])
            if len(following) > 1 and rng.random() < 0.45:
                other = rng.choice(following)
                if other["id"] not in node["links"]:
                    node["links"].append(other["id"])
        linked = {link for node in current for link in node["links"]}
        for node in following:
            if node["id"] not in linked:
                current[-1]["links"].append(node["id"])
    return {"floor": floor, "columns": columns}


def ensure(run):
    d = _dungeon(run)
    if d.get("config", {}).get("module_rooms"):
        raise ExpeditionError("authored modules keep their fixed room order; no expedition route")
    exp = d.get("expedition")
    if not isinstance(exp, dict):
        exp = d["expedition"] = {"schema": SCHEMA, "maps": {}, "position": None,
                                 "visited": [], "log": [], "last_auto": None}
        if d.get("floor") == 1 and d.get("room") == 1:
            exp["position"] = "1:1:0"
            exp["visited"].append("1:1:0")
    key = str(d["floor"])
    if key not in exp["maps"]:
        exp["maps"][key] = build_floor(run, d["floor"])
    return exp


def _node(exp, node_id):
    floor = node_id.split(":", 1)[0]
    for column in exp["maps"].get(floor, {}).get("columns", []):
        for node in column:
            if node["id"] == node_id:
                return node
    return None


def _next_slot(run):
    d = _dungeon(run)
    if d["room"] >= _floor_room_count(d, d["floor"]):
        return d["floor"] + 1, 1
    return d["floor"], d["room"] + 1


def choices(run, *, store=True):
    """Node ids the party may take next."""
    d = _dungeon(run)
    exp = ensure(run)
    if d.get("status") != "active":
        return []
    floor, column = _next_slot(run)
    if floor > len(d["config"]["floors"]):
        return []
    key = str(floor)
    if key not in exp["maps"]:
        if not store:
            # Views stay read-only; the graph is seeded, so this draw matches the stored one.
            graph = build_floor(run, floor)
            return [node["id"] for node in graph["columns"][column - 1]]
        exp["maps"][key] = build_floor(run, floor)
    nodes = exp["maps"][key]["columns"][column - 1]
    current = _node(exp, exp["position"]) if exp.get("position") else None
    if current and current["floor"] == floor:
        return [node["id"] for node in nodes if node["id"] in current["links"]]
    return [node["id"] for node in nodes]


def _room_resolved(run):
    from hollowstar.dungeon import room
    d = _dungeon(run)
    if not d.get("room"):
        return True
    return bool(room(run).get("resolved"))


def choose(run, node_id, mode="tactical"):
    """Commit to a node and enter it through the dungeon's own room boundary."""
    from hollowstar import dungeon
    if mode not in MODES:
        raise ExpeditionError("mode must be arcade, tactical or auto")
    d = _dungeon(run)
    exp = ensure(run)
    if not _room_resolved(run):
        raise ExpeditionError("resolve the current room before choosing the next node")
    allowed = choices(run)
    if node_id not in allowed:
        raise ExpeditionError("that node is not reachable from here")
    node = _node(exp, node_id)
    if mode == "arcade" and node["type"] not in COMBAT_NODES:
        mode = "tactical"
    override = {"kind": node["kind"],
                "encounter_mode": "arcade" if mode == "arcade" else "turn_based"}
    if node["type"] == "elite":
        override["stacked"] = True
    if node.get("ladder"):
        override.update(copy.deepcopy(node["ladder"]))
    d["next_room"] = override
    entered = dungeon.act(run, {"type": "exit"})
    exp["position"] = node_id
    exp["visited"].append(node_id)
    entry = {"node": node_id, "type": node["type"], "mode": mode,
             "room": f"{d['floor']}:{d['room']}"}
    exp["log"].append(entry)
    result = {"type": "expedition_node_entered", "node": copy.deepcopy(node), "mode": mode,
              "entered": entered,
              "evidence": {"source": "hollowstar.expedition", "room_boundary": "dungeon.enter",
                           "rolls_here": False}}
    if mode == "auto":
        result["auto"] = resolve_auto(run)
    return result


def _party_health(run):
    party = [actor for actor in run.party]
    if not party:
        return 0.0
    return sum(max(0, actor.hp) / max(1, actor.max_hp) for actor in party) / len(party)


def resolve_auto(run, *, action_cap=MAX_AUTO_ACTIONS):
    """Drive the current room to resolution with the gambit/exploration policies."""
    from hollowstar import dungeon
    from hollowstar.policies import exploration_action
    d = _dungeon(run)
    steps = 0
    while d.get("status") == "active" and steps < action_cap:
        in_combat = "combat" in run.context and not run.context["combat"].get("complete")
        if not in_combat and _room_resolved(run):
            break
        if isinstance(run.context.get("arcade"), dict) and in_combat:
            return {"steps": steps, "stopped": "arcade_needs_player"}
        action = exploration_action(run)
        if action.get("type") == "enter":
            break
        dungeon.act(run, action)
        steps += 1
    stopped = ("run_ended" if d.get("status") != "active"
               else "resolved" if _room_resolved(run) else "action_cap")
    return {"steps": steps, "stopped": stopped}


def _auto_pick(run, options, exp):
    """Prefer rest when hurt, otherwise the most rewarding reachable node."""
    health = _party_health(run)
    order = (["rest", "shop", "loot", "social", "hazard", "fight", "elite", "boss"] if health < 0.5
             else ["elite", "loot", "fight", "hazard", "shop", "social", "rest", "boss"])
    return min(options, key=lambda node_id: (order.index(_node(exp, node_id)["type"])
                                             if _node(exp, node_id)["type"] in order else 99, node_id))


def auto_run(run, *, max_nodes=3, retreat_below=0.3):
    """AFK expedition: take up to ``max_nodes`` nodes on gambits, pausing when hurt."""
    d = _dungeon(run)
    exp = ensure(run)
    if type(max_nodes) is not int or not 1 <= max_nodes <= MAX_AUTO_NODES:
        raise ExpeditionError(f"max_nodes must be an integer from 1 to {MAX_AUTO_NODES}")
    if isinstance(retreat_below, bool) or not isinstance(retreat_below, (int, float)) or not 0 <= retreat_below < 1:
        raise ExpeditionError("retreat_below must be a fraction from 0 to 1")
    gold_before = d.get("currency", 0)
    cleared, stop = [], "budget_spent"
    pending = resolve_auto(run)
    if pending["stopped"] not in {"resolved"}:
        stop = pending["stopped"]
    else:
        while len(cleared) < max_nodes:
            if d.get("status") != "active":
                stop = "run_ended"
                break
            if _party_health(run) < retreat_below:
                stop = "retreat_threshold"
                break
            options = choices(run)
            if not options:
                stop = "route_complete"
                break
            node_id = _auto_pick(run, options, exp)
            outcome = choose(run, node_id, "auto")
            cleared.append({"node": node_id, "type": outcome["node"]["type"],
                            "stopped": outcome["auto"]["stopped"]})
            if outcome["auto"]["stopped"] != "resolved":
                stop = outcome["auto"]["stopped"]
                break
    summary = {"nodes": cleared, "stopped": stop,
               "gold_gained": d.get("currency", 0) - gold_before,
               "party_health": round(_party_health(run), 3),
               "status": d.get("status")}
    exp["last_auto"] = summary
    return {"type": "expedition_auto", "summary": summary,
            "evidence": {"source": "hollowstar.expedition", "policy": "hollowstar.policies",
                         "retreat_below": retreat_below}}


def view(run):
    """Public expedition projection for clients."""
    d = run.context.get("dungeon")
    if not isinstance(d, dict) or d.get("config", {}).get("module_rooms"):
        return None
    exp = d.get("expedition")
    if not isinstance(exp, dict):
        return {"active": False, "floor": d.get("floor"), "room": d.get("room")}
    reachable = set(choices(run, store=False)) if _room_resolved(run) else set()
    visited = set(exp["visited"])
    floor, _ = _next_slot(run)
    maps = {}
    for key, graph in exp["maps"].items():
        columns = []
        for column in graph["columns"]:
            nodes = []
            for node in column:
                public = {k: copy.deepcopy(v) for k, v in node.items()}
                # "reach", not "state": the public projection drops every "state" key.
                public["reach"] = ("current" if node["id"] == exp.get("position")
                                   else "visited" if node["id"] in visited
                                   else "available" if node["id"] in reachable else "locked")
                nodes.append(public)
            columns.append(nodes)
        maps[key] = {"floor": graph["floor"], "columns": columns}
    return {"active": True, "floor": d.get("floor"), "room": d.get("room"),
            "next_floor": floor, "position": exp.get("position"),
            "choices": sorted(reachable), "room_resolved": _room_resolved(run),
            "party_health": round(_party_health(run), 3),
            "maps": maps, "log": copy.deepcopy(exp["log"][-20:]),
            "last_auto": copy.deepcopy(exp.get("last_auto")), "modes": sorted(MODES)}


def act(run, action):
    kind = action.get("type")
    if kind == "expedition_start":
        ensure(run)
        return {"type": "expedition_started", "expedition": view(run),
                "evidence": {"source": "hollowstar.expedition", "seeded": True}}
    if kind == "expedition_choose":
        return choose(run, action.get("node"), action.get("mode", "tactical"))
    if kind == "expedition_resolve":
        ensure(run)
        return {"type": "expedition_resolved", "auto": resolve_auto(run)}
    if kind == "expedition_auto":
        return auto_run(run, max_nodes=action.get("max_nodes", 3),
                        retreat_below=action.get("retreat_below", 0.3))
    if kind == "expedition_view":
        return {"type": "expedition_view", "expedition": view(run),
                "evidence": {"read_only": True}}
    raise ExpeditionError(f"unsupported expedition action: {kind}")
