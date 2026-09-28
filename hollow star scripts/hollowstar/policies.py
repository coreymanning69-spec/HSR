"""Automated choices only. No rolls, damage, reward or state mutations live here."""
from hollowstar import tactical as t


SELECTORS = {"self", "self_only", "lowest_hp_ally", "lowest_health_ally", "lowest_hp_enemy",
             "lowest_health_enemy", "nearest_enemy", "highest_hp_enemy", "casting_enemy",
             "adjacent_enemy", "killable_enemy", "likeliest_hit_enemy", "most_damage_enemy"}
# Selectors that read forecasts rather than the board.
FORECAST_SELECTORS = {"killable_enemy": "kill", "likeliest_hit_enemy": "hit",
                      "most_damage_enemy": "expected_damage"}
TARGETED_TYPES = {"attack", "cast", "reaction", "shove", "trip", "grapple", "help"}
# Conditions judged against the forecast of the resolved "then" action.
# Values are percentages, like the HP conditions, except expected_damage_gte (points).
FORECAST_CONDITIONS = {"hit_chance_gte", "kill_chance_gte", "expected_damage_gte"}
PLAN_GOALS = {"damage", "kill", "heal", "control", "defend"}


# --- Candidates -----------------------------------------------------------------
# One catalog of every concrete thing an actor could do right now, each row in
# the same shape whatever produced it:
#   {id, source, kind, label, action, target, legal, reason, cost,
#    hit, kill, expected_damage, expected_healing, forecast}
# `action` is a canonical action tactical.apply accepts unchanged. Planning,
# forecast selectors and forecast conditions all read this one catalog, so a
# new ability becomes plannable by adding one source function below.
# Contract and extension notes: docs/tactical-planning-foundation.md.

def informed(run, actor_key):
    """Whether actor_key's forecasts may read hidden resistances and affixes.
    Enemy AI is informed; the party prices from what it has seen, unless
    run.context["forecast_informed"] = {"p": true} says otherwise."""
    override = (run.context.get("forecast_informed") or {}).get(actor_key[0])
    return bool(override) if override is not None else not actor_key.startswith("p")


def _row(source, kind, label, action, forecast, cost):
    anchor = action.get("target") or ",".join(map(str, action.get("center") or []))
    variant = action.get("mode") or action.get("spell") or ""
    if action.get("maneuver"):
        variant = f"{action['maneuver']}/{variant}"
    return {"id": ":".join(str(part) for part in (kind, variant, "bonus" if action.get("bonus") else "", anchor)),
            "source": source, "kind": kind, "label": label, "action": action,
            "target": action.get("target"), "legal": bool(forecast.get("legal")), "reason": forecast.get("reason"),
            "cost": cost, "hit": forecast.get("hit"), "kill": forecast.get("kill", 0.0),
            "expected_damage": forecast.get("expected_damage", 0.0),
            "expected_healing": forecast.get("expected_healing", 0.0),
            "control": forecast.get("control", 0.0), "forecast": forecast}


def _weapon_candidates(run, key, know):
    r, a = t.rules(run, key), t.actor(run, key)
    identity = r.get("identity")
    modes = [r.get("loadout", "weapon")]
    weapon = a.weapon()
    if identity == "doran":
        modes += ["weapon", "dagger", "cleaver"]
    elif weapon is not None and isinstance(getattr(weapon, "alternate_modes", None), dict):
        modes += list(weapon.alternate_modes)
    modes = list(dict.fromkeys(modes))
    bonus_lanes = [False]
    if identity in {"doran", "wren"} or r.get("bonus_attack_resource"):
        bonus_lanes.append(True)
    rows = []
    for target, foe in t.actors(run).items():
        if t.same_side(key, target) or not foe.alive:
            continue
        for mode in modes:
            for bonus in bonus_lanes:
                forecast = t.forecast_attack(run, key, target, mode, bonus=bonus, informed=know)
                action = {"type": "attack", "actor": key, "target": target, "mode": mode, "bonus": bonus}
                if identity == "wren":
                    resources = {"crown_motes": 1}
                elif bonus and identity != "doran":
                    resources = {r["bonus_attack_resource"]: 1}
                else:
                    resources = {}
                cost = {"economy": {"bonus": 1} if bonus else {"attack": 1}, "resources": resources}
                rows.append(_row("weapon", "attack", f"{mode} attack" + (" (bonus)" if bonus else ""),
                                 action, forecast, cost))
    return rows


def _castable(run, key):
    """Spell ids worth previewing: the actor's known list, or for a staff
    caster every priced catalog spell it can pay for now."""
    from hollowstar import spells
    r = t.rules(run, key)
    book = spells.catalog(run)
    listed = r.get("known_spells") or [spell for spell, spec in book.items()
                                       if spec.get("operation") in spells.PRICED_OPERATIONS]
    return [spell for spell in listed if spell in book and spells.spell_ready(run, key, spell)]


def _spell_candidates(run, key, know):
    from hollowstar import spells
    castable = _castable(run, key)
    if not castable:
        return []
    book = spells.catalog(run)
    living = {k: v for k, v in t.actors(run).items() if v.alive}
    foes = [k for k in living if not t.same_side(key, k)]
    friends = [k for k in living if t.same_side(key, k)]
    rows = []
    for spell in castable:
        spec = book[spell]
        operation = spec.get("operation")
        if spec.get("radius"):
            centers = sorted({tuple(t.position(run, k)) for k in foes})
            actions = [{"type": "cast", "actor": key, "spell": spell, "center": list(c)} for c in centers]
        elif operation == "heal":
            actions = [{"type": "cast", "actor": key, "spell": spell, "target": k} for k in friends
                       if living[k].hp < living[k].max_hp]
        elif operation in {"attack", "darts", "damage", "condition"}:
            actions = [{"type": "cast", "actor": key, "spell": spell, "target": k} for k in foes]
        else:
            actions = []
        for action in actions:
            forecast = spells.preview_cast(run, key, action, informed=know)
            label = spec.get("name", spell) + (f" at {action['center']}" if "center" in action else "")
            rows.append(_row("spell", "cast", label, action, forecast, forecast.get("cost")))
    return rows


def _maneuver_candidates(run, key, know):
    """Doran's attack maneuvers, priced by maneuvers.forecast_maneuver."""
    from hollowstar import maneuvers
    if t.rules(run, key).get("identity") != "doran" or t.actor(run, key).resources.get("superiority_dice", 0) <= 0:
        return []
    living = {k: v for k, v in t.actors(run).items() if v.alive}
    rows = []
    for target in living:
        if t.same_side(key, target):
            continue
        for name in maneuvers.FORECAST_MANEUVERS:
            for mode in ("dagger", "cleaver"):
                if name == "Quick Toss" and mode == "cleaver":
                    continue
                action = {"type": "maneuver", "actor": key, "maneuver": name, "target": target, "mode": mode}
                if name == "Sweeping Attack":
                    second = min((k for k in living if k != target and t.same_side(k, target)
                                  and t.distance(run, target, k) <= 5), key=lambda k: (living[k].hp, k), default=None)
                    if second is None:
                        continue
                    action["second_target"] = second
                if name == "Maneuvering Attack":
                    ally = min((k for k in living if k != key and t.same_side(k, key)
                                and t.economy(run, k).get("reaction")), key=lambda k: (t.distance(run, key, k), k),
                               default=None)
                    if ally is None:
                        continue
                    action["ally"] = ally
                forecast = maneuvers.forecast_maneuver(run, key, action, informed=know)
                cost = forecast.get("cost") or {"economy": {"attack": 1}, "resources": {"superiority_dice": 1}}
                rows.append(_row("maneuver", "maneuver", f"{name} ({mode})", action, forecast, cost))
    return rows


def _contest_candidates(run, key, know):
    """Shove, trip, grapple and Help against each foe, plus Dodge, Disengage and Dash."""
    rows = []
    living = {k: v for k, v in t.actors(run).items() if v.alive}
    for target in living:
        if t.same_side(key, target):
            continue
        for action, label in (({"type": "shove", "actor": key, "target": target, "mode": "push"}, "Shove"),
                              ({"type": "shove", "actor": key, "target": target, "mode": "prone"}, "Trip"),
                              ({"type": "grapple", "actor": key, "target": target}, "Grapple"),
                              ({"type": "help", "actor": key, "target": target}, "Help")):
            forecast = t.forecast_contest(run, key, {**action, "type": "trip"} if label == "Trip" else action)
            if label == "Help" and forecast.get("ally"):
                action["ally"] = forecast["ally"]
            rows.append(_row("contest", action["type"], label, action, forecast, forecast.get("cost")))
    for kind in ("dodge", "disengage", "dash"):
        action = {"type": kind, "actor": key}
        forecast = t.forecast_contest(run, key, action)
        rows.append(_row("contest", kind, kind.title(), action, forecast, forecast.get("cost")))
    return rows


# Every source of candidates, in catalog order. Domains and items join here as
# (name, function) once each has a read-only forecast.
CANDIDATE_SOURCES = [("weapon", _weapon_candidates), ("spell", _spell_candidates),
                     ("maneuver", _maneuver_candidates), ("contest", _contest_candidates)]


def candidate_actions(run, key, *, informed_forecast=None, include_illegal=False):
    """Every concrete action key could take now, each with its forecast. Read-only.
    Whose turn it is stays the caller's question, as it is for tactical.apply."""
    know = informed(run, key) if informed_forecast is None else bool(informed_forecast)
    rows = []
    for _name, source in CANDIDATE_SOURCES:
        rows.extend(source(run, key, know))
    return rows if include_illegal else [row for row in rows if row["legal"]]


def _spends_resources(row):
    return any((row.get("cost") or {}).get("resources", {}).values())


def resource_weight(row):
    """How much limited resource a candidate burns: a level-N slot weighs N,
    anything else weighs its count. Economy (action, bonus) weighs nothing."""
    weight = 0
    for name, amount in ((row.get("cost") or {}).get("resources") or {}).items():
        parts = str(name).split("_")
        level = int(parts[1]) if parts[0] == "slot" and len(parts) > 1 and parts[1].isdigit() else 1
        weight += level * amount
    return weight


# A candidate within this share of the best score is "as good"; among those
# the planner spends the least. 0.9 keeps a 70-point heal from burning a
# ninth-level slot to top off a 9-point wound.
PLAN_BAND = 0.9


def _thrifty(rows, score):
    if not rows:
        return None
    best = max(score(row) for row in rows)
    band = [row for row in rows if score(row) >= best * PLAN_BAND]
    return min(band, key=lambda row: (resource_weight(row), -score(row), row["id"]))


def plan_action(run, key, goal, *, spend=True, candidates=None):
    """The canonical action that best serves goal ("damage", "kill" or "heal"), or None.

    damage: most expected damage (friendly fire counts against it).
    kill:   best chance to drop an enemy with this one action; None when no
            candidate can, so a gambit list falls through to its next line.
    heal:   the most-hurt ally that any candidate can reach, then the most
            expected healing.
    control: the likeliest to land a consequence (prone, grappled, pushed,
            frightened, disarmed, ...) on an enemy; None when nothing can.
    defend: Dodge (or Disengage, when Cunning Action makes it a bonus action)
            while a conscious foe is within 5 feet; None when unthreatened.
    Anything within PLAN_BAND of the best score counts as tied, and the tie
    goes to the candidate that burns the least (resource_weight), then the
    catalog id, so the choice is deterministic. spend=False keeps to
    candidates that cost no limited resource at all.
    """
    if goal not in PLAN_GOALS:
        return None
    rows = candidate_actions(run, key) if candidates is None else candidates
    if not spend:
        rows = [row for row in rows if not _spends_resources(row)]
    if goal == "damage":
        best = _thrifty([row for row in rows if row["expected_damage"] > 0], lambda row: row["expected_damage"])
    elif goal == "kill":
        best = _thrifty([row for row in rows if row["kill"] > 0], lambda row: row["kill"])
    elif goal == "control":
        best = _thrifty([row for row in rows if row.get("control", 0) > 0 and row["target"]
                         and not t.same_side(key, row["target"])], lambda row: row["control"])
    elif goal == "defend":
        guards = [row for row in rows if row["kind"] in {"dodge", "disengage"}
                  and (row["forecast"].get("threatened_by") or [])]
        # Dodge while the action is free; a bonus-action Disengage otherwise.
        best = min(guards, key=lambda row: (row["kind"] != "dodge", row["id"]), default=None)
    else:
        rows = [row for row in rows if row["expected_healing"] > 0]
        actors = t.actors(run)

        def need(row):
            target = row["target"] or (row["forecast"].get("targets") or [None])[0]
            return _pct(actors[target]) if target in actors else 100
        neediest = min((need(row) for row in rows), default=None)
        best = _thrifty([row for row in rows if need(row) == neediest], lambda row: row["expected_healing"])
    return dict(best["action"]) if best else None


def _forecast_target(run, actor_key, metric):
    """The living enemy with the best single-target forecast on metric, or None."""
    best = {}
    for row in candidate_actions(run, actor_key):
        target = row["target"]
        if target is None or t.same_side(actor_key, target):
            continue
        value = row.get(metric)
        if value is None:
            continue
        best[target] = max(best.get(target, 0.0), value)
    actors = t.actors(run)
    ranked = [k for k, v in best.items() if v > 0]
    return min(ranked, key=lambda k: (-best[k], actors[k].hp, k), default=None)


def forecast_action(run, actor_key, action):
    """The forecast of one canonical action, or None when nothing forecasts its type."""
    know = informed(run, actor_key)
    kind = action.get("type")
    if kind == "attack" and action.get("target"):
        return t.forecast_attack(run, actor_key, action["target"], action.get("mode"),
                                 bonus=bool(action.get("bonus")), informed=know)
    if kind == "cast":
        from hollowstar import spells
        return spells.preview_cast(run, actor_key, action, informed=know)
    if kind == "maneuver":
        from hollowstar import maneuvers
        return maneuvers.forecast_maneuver(run, actor_key, action, informed=know)
    if kind in t.CONTEST_TYPES:
        return t.forecast_contest(run, actor_key, action)
    return None


def _forecast_matches(run, actor_key, when, action):
    """Judge the FORECAST_CONDITIONS in when against the resolved action. Fails closed."""
    keys = [key for key in when if key in FORECAST_CONDITIONS]
    if not keys:
        return True
    forecast = forecast_action(run, actor_key, action)
    if not forecast or not forecast.get("legal"):
        return False
    for key in keys:
        value = float(when[key])
        if key == "hit_chance_gte":
            ok = forecast.get("hit") is not None and forecast["hit"] * 100 >= value
        elif key == "kill_chance_gte":
            ok = forecast.get("kill", 0.0) * 100 >= value
        else:
            ok = forecast.get("expected_damage", 0.0) >= value
        if not ok:
            return False
    return True


def _macro_target(run, actor_key, selector):
    """Resolve a public Macro target selector without mutating the run."""
    actors = t.actors(run)
    allies = [k for k, v in actors.items()
              if t.same_side(k, actor_key) and v.alive]
    enemies = [k for k, v in actors.items()
               if not t.same_side(k, actor_key) and v.alive]
    selector = str(selector or "nearest_enemy").lower()
    if selector in {"self", "self_only"}:
        return actor_key
    if selector in {"lowest_hp_ally", "lowest_health_ally"}:
        return min(allies, key=lambda k: (actors[k].hp / max(1, actors[k].max_hp), k), default=None)
    if selector in {"lowest_hp_enemy", "lowest_health_enemy"}:
        return min(enemies, key=lambda k: (actors[k].hp / max(1, actors[k].max_hp), k), default=None)
    if selector == "highest_hp_enemy":
        # Boss focus: the most current hit points, not the highest percentage.
        return min(enemies, key=lambda k: (-actors[k].hp, k), default=None)
    if selector == "casting_enemy":
        casting = [k for k in enemies if "CASTING" in actors[k].statuses]
        return min(casting, key=lambda k: (t.distance(run, actor_key, k), k), default=None)
    if selector in FORECAST_SELECTORS:
        return _forecast_target(run, actor_key, FORECAST_SELECTORS[selector])
    if selector == "adjacent_enemy":
        near = [k for k in enemies if t.distance(run, actor_key, k) <= 5]
        return min(near, key=lambda k: (actors[k].hp, k), default=None)
    return min(enemies, key=lambda k: (t.distance(run, actor_key, k), actors[k].hp, k), default=None)


def _pct(actor):
    return actor.hp * 100 / max(1, actor.max_hp)


def _has_resource(run, actor, name):
    name = str(name)
    if name == "spell_slot":
        return any(value > 0 for key, value in actor.resources.items() if key.startswith("slot_"))
    if name == "potion":
        inventory = (run.context.get("dungeon") or {}).get("inventory", {})
        return any(item.get("kind") == "potion" for item in inventory.values() if isinstance(item, dict))
    return actor.resources.get(name, 0) > 0


def _cocoon(run):
    """The live final-floor cocoon clock, or None outside that chamber."""
    dungeon = run.context.get("dungeon")
    if not isinstance(dungeon, dict):
        return None
    row = (dungeon.get("rooms") or {}).get(f"{dungeon.get('floor')}:{dungeon.get('room')}") or {}
    return row.get("cocoon") if isinstance(row.get("cocoon"), dict) else None


def _macro_matches(run, actor_key, macro):
    """Evaluate the data-only Macro (Gambit) condition vocabulary.

    Every key in ``when`` must hold. Unknown keys fail closed so a typo never
    turns a conditional gambit into an unconditional one.
    """
    when = macro.get("when", {}) if isinstance(macro, dict) else {}
    if not isinstance(when, dict):
        return False
    actor = t.actor(run, actor_key)
    actors = t.actors(run)
    enemies = [k for k, v in actors.items() if not t.same_side(k, actor_key) and v.alive]
    target = _macro_target(run, actor_key, when.get("target", macro.get("target")))
    for key, value in when.items():
        if key == "target" or key in FORECAST_CONDITIONS:
            continue  # judged after the "then" action resolves
        if key == "self_hp_below":
            ok = actor.hp <= actor.max_hp * float(value) / 100
        elif key == "self_hp_above":
            ok = actor.hp >= actor.max_hp * float(value) / 100
        elif key in {"ally_hp_below", "ally_hp_above"}:
            ally = _macro_target(run, actor_key, "lowest_hp_ally")
            ok = ally is not None and (_pct(actors[ally]) <= float(value) if key == "ally_hp_below"
                                       else _pct(actors[ally]) >= float(value))
        elif key in {"enemy_hp_below", "enemy_hp_above"}:
            ok = target is not None and (_pct(actors[target]) <= float(value) if key == "enemy_hp_below"
                                         else _pct(actors[target]) >= float(value))
        elif key == "enemy_status":
            ok = target is not None and str(value) in actors[target].statuses
        elif key == "self_status":
            ok = str(value) in actor.statuses
        elif key == "self_status_absent":
            ok = str(value) not in actor.statuses
        elif key == "round_number_gte":
            ok = run.round_number >= int(value)
        elif key == "round_number_lte":
            ok = run.round_number <= int(value)
        elif key in {"cocoon_rounds_gte", "cocoon_rounds_lte"}:
            clock = _cocoon(run)
            ok = clock is not None and not clock.get("opened") and (
                run.round_number >= int(value) if key == "cocoon_rounds_gte" else run.round_number <= int(value))
        elif key == "has_resource":
            names = value if isinstance(value, list) else [value]
            ok = all(_has_resource(run, actor, name) for name in names)
        elif key == "enemy_casting":
            ok = any("CASTING" in actors[k].statuses for k in enemies) == bool(value)
        elif key == "enemy_count_gte":
            ok = len(enemies) >= int(value)
        elif key == "enemy_adjacent":
            ok = any(t.distance(run, actor_key, k) <= 5 for k in enemies) == bool(value)
        elif key == "spell_ready":
            from hollowstar import spells
            names = value if isinstance(value, list) else [value]
            ok = all(spells.spell_ready(run, actor_key, str(name)) for name in names)
        elif key == "self_concentrating":
            concentrating = actor_key in ((run.context.get("combat") or {}).get("concentration") or {})
            ok = concentrating == bool(value)
        else:
            ok = False
        if not ok:
            return False
    return True


def _legal_now(run, actor_key, action):
    """Skip a gambit whose contextual action the engine already knows is illegal.

    Only meaningful on the actor's own turn; an off-turn preview returns the
    first matching gambit exactly as before.
    """
    combat = run.context.get("combat") or {}
    if combat.get("complete") or combat.get("pending") or not combat.get("order") or t.current(run) != actor_key:
        return True
    catalog = {row["id"]: row for row in t.contextual_actions(run, actor_key)}
    row = catalog.get(action.get("type"))
    if row is None:
        return True  # not a catalogued action: its own transition decides
    if not row["available"]:
        return False
    if row["targets"] and action.get("target") not in row["targets"]:
        return False
    # The forecast and preview share the resolver's legality, including range,
    # cover, payment and targeting denial, so a gambit the engine would refuse
    # falls through to the next one instead.
    forecast = forecast_action(run, actor_key, action)
    return forecast is None or bool(forecast.get("legal"))


def macro_action(run, actor_key, macros):
    """Return the first valid canonical action from an ordered Macro list."""
    for macro in sorted(macros or [], key=lambda item: int(item.get("priority", 100))):
        if not _macro_matches(run, actor_key, macro):
            continue
        then = macro.get("then", {})
        if not isinstance(then, dict) or not then.get("type"):
            continue
        if then.get("type") == "plan":
            action = plan_action(run, actor_key, then.get("goal"), spend=then.get("spend", True) is not False)
            if action is None:
                continue
        else:
            action = dict(then)
            action.setdefault("actor", actor_key)
            for field in ("target", "ally"):
                if action.get(field) in SELECTORS:
                    action[field] = _macro_target(run, actor_key, action[field])
            if isinstance(action.get("center"), str):
                # An area spell may aim at whoever a selector names.
                anchor = _macro_target(run, actor_key, action["center"]) if action["center"] in SELECTORS else None
                if anchor is None:
                    continue
                action["center"] = list(t.position(run, anchor))
            if action.get("type") in TARGETED_TYPES and not action.get("target") and not (
                    action.get("type") == "cast" and (action.get("center") or action.get("targets"))):
                continue
        if not _legal_now(run, actor_key, action):
            continue
        when = macro.get("when", {}) if isinstance(macro.get("when", {}), dict) else {}
        if not _forecast_matches(run, actor_key, when, action):
            continue
        return action
    return None


def approach(run,key,target,maximum,cap=10):
    """The largest step toward target this actor can actually pay for.

    Returns None when no step is affordable, so the caller ends the turn
    instead of re-proposing a refused move. Steps stay small so terrain and
    threat windows land between them, and every candidate is priced by
    tactical.move_cost rather than assumed to be five feet per square: the
    difficult columns on floors two and four cost ten, so a ten-foot step
    there is a fifteen- or twenty-foot bill.
    """
    start=t.position(run,key);goal=t.position(run,target)
    budget=t.economy(run,key)['movement']
    reach=min(max(0,t.distance(run,key,target)-maximum),cap,budget)//5*5
    while reach>=5:
        destination=list(start)
        for axis in (0,1):
            delta=goal[axis]-start[axis]
            destination[axis]+=min(abs(delta),reach)*(1 if delta>0 else -1)
        cost=t.move_cost(run,key,destination)
        if destination!=start and cost is not None and cost<=budget:
            return destination
        reach-=5
    return None


# A Parry (1d12+3, about 9.5) is worth a superiority die against a blow at
# least this large, or any blow that would drop the defender.
PARRY_FLOOR = 10
# The Tarrasque's routine by expected damage, and each attack's reach.
TARRASQUE_PREFERENCE = ("bite", "horns", "claw", "tail")
TARRASQUE_REACH = {"bite": 10, "horns": 10, "claw": 15, "tail": 20}


def _legendary_choice(run, key, window):
    """The Tarrasque's legendary action at the end of another creature's turn:
    a claw (one point) at whoever it can reach, else a tail sweep, else none."""
    a = t.actor(run, key)
    if t.rules(run, key).get("identity") != "tarrasque" or a.resources.get("legendary_actions", 0) <= 0:
        return None
    if run.round_number < t.rules(run, key).get("rising_until", 0):
        return None
    foes = _tarrasque_foes(run, key)
    preferred = window.get("target")
    for mode in ("claw", "tail"):
        reach = TARRASQUE_REACH[mode]
        near = [k for k in foes if t.distance(run, key, k) <= reach]
        if near:
            target = preferred if preferred in near else min(near, key=lambda k: (t.actor(run, k).hp, k))
            return {"type": "legendary", "actor": key, "mode": mode, "target": target}
    return None


def reaction_action(run, window):
    """The automated answer to one reaction window, for whoever holds it.

    opportunity: take the attack.  brace: brace while a superiority die lasts.
    hit: Shield when offered and a slot remains; Parry when the blow is at
    least PARRY_FLOOR or would drop the defender.  legendary: the Tarrasque
    spends a point (_legendary_choice).  spell: Wren's staff absorbs it.
    save: Aura of the Unbound when offered.  deft_answer and command: take it.
    Anything else, or an answer the reactor cannot pay for, declines.
    """
    key = window.get("reactor")
    kind = window.get("kind")
    options = window.get("options") or []
    decline = {"type": "decline_reaction", "actor": key}
    if key not in t.actors(run):
        return decline
    a = t.actor(run, key)
    if not t.conscious(a):
        return decline
    if kind == "hit":
        if "shield" in options and a.resources.get("slot_1_general", 0) > 0:
            return {"type": "reaction", "actor": key, "defense": "shield"}
        if "parry" in options and a.resources.get("superiority_dice", 0) > 0 and (
                window.get("amount", 0) >= PARRY_FLOOR or window.get("amount", 0) >= a.hp):
            return {"type": "reaction", "actor": key, "defense": "parry"}
        return decline
    if kind == "legendary":
        return _legendary_choice(run, key, window) or decline
    if kind == "spell":
        return {"type": "staff_absorb", "actor": key} if t.economy(run, key).get("reaction") else decline
    if kind == "save":
        return {"type": "domain_reaction", "actor": key} if window.get("feature") == "Aura of the Unbound" else decline
    if kind == "brace":
        return {"type": "reaction", "actor": key, "defense": "brace"} \
            if a.resources.get("superiority_dice", 0) > 0 else decline
    if kind in {"opportunity", "deft_answer", "command"}:
        target = window.get("target")
        if kind != "command" and (target not in t.actors(run) or not t.actor(run, target).alive):
            return decline
        return {"type": "reaction", "actor": key}
    return decline


def _tarrasque_foes(run, key):
    """Before launch it fights the party; once launched it attacks everything alive."""
    r = t.rules(run, key)
    feral = r.get("feral") and run.round_number >= r.get("launches_at", 0)
    return [k for k, v in t.actors(run).items() if k != key and v.alive
            and (feral or not t.same_side(k, key))
            and "total" != run.context["combat"]["terrain"]["cover"].get(k)]


def _tarrasque_turn(run, key, target):
    """One step of the Tarrasque's own turn: the five-attack routine at
    whatever it can reach, closing the distance when nothing reaches."""
    r, e = t.rules(run, key), t.economy(run, key)
    if run.round_number < r.get("rising_until", 0):
        return {"type": "end_turn", "actor": key}  # still hauling itself out of the cocoon
    routine = r.get("routine") or []
    if not routine and not e["action"]:
        return {"type": "end_turn", "actor": key}
    remaining = routine or ["bite", "claw", "claw", "horns", "tail"]
    foes = _tarrasque_foes(run, key)
    if r.get("feral") and run.round_number >= r.get("launches_at", 0) and foes:
        target = min(foes, key=lambda k: (t.distance(run, key, k), t.actor(run, k).hp, k))
    for mode in TARRASQUE_PREFERENCE:
        if mode not in remaining:
            continue
        near = [k for k in foes if t.distance(run, key, k) <= TARRASQUE_REACH[mode]]
        if mode == "bite" and r.get("bite_target") in near:
            victim = r["bite_target"]
            large = t.rules(run, victim).get("size", "medium") in {"huge", "gargantuan"}
            return {"type": "monster", "actor": key, "target": victim, "mode": "bite" if large else "swallow"}
        if mode == "bite" and r.get("bite_target") is not None and r.get("bite_target") not in near:
            continue  # the jaws are holding someone out of reach
        if near:
            victim = target if target in near else min(near, key=lambda k: (t.actor(run, k).hp, k))
            return {"type": "monster", "actor": key, "target": victim, "mode": mode}
    reach = max(TARRASQUE_REACH[mode] for mode in remaining)
    destination = approach(run, key, target, reach) if e.get("movement") else None
    if destination is not None:
        return {"type": "move", "actor": key, "destination": destination}
    return {"type": "end_turn", "actor": key}


def _enemy_spell(run, key, e):
    """A spellcasting enemy's best damaging cast, when it beats its weapon."""
    if key.startswith("p") or not t.rules(run, key).get("known_spells") or not (e["action"] or e["bonus"]):
        return None
    rows = candidate_actions(run, key)
    spell = plan_action(run, key, "damage", candidates=[row for row in rows if row["kind"] == "cast"])
    if spell is None:
        return None
    weapon = max((row["expected_damage"] for row in rows if row["kind"] == "attack"), default=0.0)
    cast = max(row["expected_damage"] for row in rows if row["action"] == spell)
    return spell if cast > weapon else None


def combat_action(run):
    state=run.context['combat']
    if state['pending']:
        return reaction_action(run, state['pending'][0])
    key=t.current(run);a=t.actor(run,key);e=t.economy(run,key)
    if not t.conscious(a):return {'type':'end_turn','actor':key}
    targets=[k for k,v in t.actors(run).items() if not t.same_side(k,key) and v.alive]
    target=min(targets,key=lambda k:(t.distance(run,key,k),t.actor(run,k).hp,k))
    identity=t.rules(run,key).get('identity')
    if t.rules(run,key).get('retreated'):
        return {'type':'end_turn','actor':key}
    configured = run.context.get("macros", {}).get(key, [])
    selected = macro_action(run, key, configured)
    if selected is not None:
        return selected
    if identity == 'doran' and e['bonus'] and a.hp < a.max_hp / 2 and a.resources.get('second_wind'):
        return {'type':'second_wind','actor':key}
    if identity == 'wren' and e['bonus'] and a.hp < a.max_hp / 2 and a.resources.get('unearthly_recovery'):
        return {'type':'unearthly_recovery','actor':key}
    if identity=='wren':
        # Preserve a real support line in automated rehearsals.  Healing Word
        # is a declared bonus-action spell, so this is an ordinary engine cast
        # with normal range, slot consumption, and healing rolls—not a policy
        # side effect.
        ally = next((k for k, v in t.actors(run).items()
                     if t.same_side(k, key) and k != key and v.alive
                     and v.hp <= v.max_hp // 2), None)
        if ally and e['bonus'] and a.resources.get('slot_1_general'):
            return {'type':'cast','actor':key,'spell':'Healing Word@5e','target':ally}
        if e['bonus'] and a.resources.get('crown_motes'):
            return {'type':'attack','actor':key,'target':target,'bonus':True}
        if e['action'] and a.resources.get('slot_3_general'):
            return {'type':'cast','actor':key,'spell':'Fireball@5e','center':list(t.position(run,target))}
        # Out of slots and motes she falls back to her Sacred Flame cantrip
        # rather than idling out the fight.
        if e['action']:
            if t.distance(run,key,target)>60:
                destination=approach(run,key,target,60)
                if destination is not None and e.get('movement'):
                    return {'type':'move','actor':key,'destination':destination}
            else:
                return {'type':'cast','actor':key,'spell':'Sacred Flame@5e','targets':[target]}
        return {'type':'end_turn','actor':key}
    if identity=='tarrasque':
        return _tarrasque_turn(run,key,target)
    spell=_enemy_spell(run,key,e)
    if spell is not None:
        return spell
    maximum=70 if identity=='doran' else t.rules(run,key).get('range',[5,5])[1]
    if t.distance(run,key,target)>maximum:
        destination=approach(run,key,target,maximum)
        if destination is None:return {'type':'end_turn','actor':key}
        return {'type':'move','actor':key,'destination':destination}
    if e['action'] or e['attacks']:return {'type':'attack','actor':key,'target':target}
    if identity=='doran' and e['bonus']:return {'type':'attack','actor':key,'target':target,'bonus':True}
    # A fixture resident spends its declared pool for the extra press rather
    # than ending a turn with a quantifier it was never able to use.
    pool=t.rules(run,key).get('bonus_attack_resource')
    if pool and e['bonus'] and a.resources.get(pool):
        return {'type':'attack','actor':key,'target':target,'bonus':True}
    return {'type':'end_turn','actor':key}


def exploration_action(run):
    from hollowstar.dungeon import room
    d=run.context['dungeon'];r=room(run)
    if 'combat' in run.context and not run.context['combat']['complete']:
        return combat_action(run)
    if r['resolved']:return {'type':'enter'}
    if r['kind']=='rest':return {'type':'rest','safe':bool(d['discoveries'])}
    if 'investigate' not in r['attempts']:return {'type':'investigate'}
    return {'type':'avoid'}
