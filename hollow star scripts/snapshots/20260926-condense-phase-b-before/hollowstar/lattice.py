"""The Immunity Lattice: conversion, immunity, consequence denial, and Turn 0.

One small declarative vocabulary for the "broken build" layer, resolved inside
the live tactical path instead of a parallel engine.  Each row is a dict with a
``kind`` and a ``tell``; the phase each kind belongs to is fixed below so the
seven-phase order in ``hollowstar.phases`` stays the single ordering authority.

Sources, merged in this order for an actor key:

1. encounter rules   ``run.context['combat']['rules'][key]['lattice']``
2. attuned Legendary slots (``attunement.attuned_lattice``)
3. equipped Imprints that carry a ``lattice`` list

DM046_0 section 11 is enforced by construction: every strong row carries a
tell, and damage immunity never implies condition immunity; those are
separate kinds.  DM046_0 section 12 asks combination testing to *detect*
permanently invulnerable builds, and ``audit`` is that detector.  It reports
and never forbids.
"""
from __future__ import annotations

import copy

from hollowstar.phases import Phase, Tier
from hollowstar.tags import DamageTag


KINDS = {
    "convert_incoming": Phase.MAGNITUDE,       # damage taken changes concept
    "convert_outgoing": Phase.MAGNITUDE,       # damage dealt changes concept
    "damage_immunity": Phase.APPLICATION,      # the concept never touches
    "deny_condition": Phase.CONSEQUENCE,       # riders and conditions refused
    "start_of_combat_ward": Phase.PERMISSION,  # Turn 0, before initiative
    "start_of_combat_condition": Phase.PERMISSION,
    "start_of_combat_strike": Phase.PERMISSION,
}
TURN_ZERO_ORDER = ("start_of_combat_ward", "start_of_combat_condition", "start_of_combat_strike")
PHYSICAL = ("SLASHING", "PIERCING", "BLUDGEONING")
# Pseudo-conditions a deny row may name alongside real tactical conditions.
DENIABLE_EXTRAS = {"DISARMED", "DISPLACEMENT"}


def _tags(values, label: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{label} requires a non-empty tag list")
    tags = [str(value).upper() for value in values]
    unknown = [tag for tag in tags if tag not in DamageTag.__members__]
    if unknown:
        raise ValueError(f"{label} names unknown damage tags: {', '.join(unknown)}")
    return tags


def validate(effect: dict) -> dict:
    """Return a normalized copy of one lattice row, or raise ValueError."""
    from hollowstar.tactical import CONDITIONS
    if not isinstance(effect, dict) or effect.get("kind") not in KINDS:
        raise ValueError(f"unknown lattice kind: {effect.get('kind') if isinstance(effect, dict) else effect}")
    row = copy.deepcopy(effect)
    kind = row["kind"]
    if not str(row.get("tell", "")).strip():
        raise ValueError(f"{kind} requires an observable tell (DM046_0 section 11)")
    if kind in {"convert_incoming", "convert_outgoing"}:
        row["from"] = _tags(row.get("from"), kind)
        row["to"] = _tags([row.get("to")], kind)[0]
    elif kind == "damage_immunity":
        row["tags"] = _tags(row.get("tags"), kind)
        row["tier"] = str(row.get("tier", "ARTIFACT")).upper()
        if row["tier"] not in Tier.__members__:
            raise ValueError(f"damage_immunity tier is unknown: {row['tier']}")
    elif kind == "deny_condition":
        names = [str(name).upper() for name in row.get("conditions", [])]
        unknown = [name for name in names if name not in CONDITIONS | DENIABLE_EXTRAS]
        if not names or unknown:
            raise ValueError(f"deny_condition names unknown conditions: {', '.join(unknown) or 'none'}")
        row["conditions"] = names
    elif kind == "start_of_combat_ward":
        amount, percent = row.get("amount"), row.get("percent_max_hp")
        if not (isinstance(amount, int) and amount > 0) and not (isinstance(percent, int) and 0 < percent <= 100):
            raise ValueError("start_of_combat_ward requires a positive amount or percent_max_hp 1..100")
    elif kind == "start_of_combat_condition":
        row["condition"] = str(row.get("condition", "")).upper()
        if row["condition"] not in CONDITIONS:
            raise ValueError(f"start_of_combat_condition names an unknown condition: {row['condition']}")
        row["duration"] = int(row.get("duration", 1))
        row["scope"] = str(row.get("scope", "self"))
        if row["scope"] not in {"self", "allies"}:
            raise ValueError("start_of_combat_condition scope must be self or allies")
    elif kind == "start_of_combat_strike":
        row["damage_type"] = _tags([row.get("damage_type")], kind)[0]
        if not isinstance(row.get("dice"), str) or not row["dice"]:
            raise ValueError("start_of_combat_strike requires a dice expression")
        row["targets"] = str(row.get("targets", "all_enemies"))
        if row["targets"] not in {"all_enemies", "lowest_hp_enemy", "nearest_enemy"}:
            raise ValueError("start_of_combat_strike targets must be all_enemies, lowest_hp_enemy, or nearest_enemy")
        save = row.get("save")
        if save is not None:
            if not isinstance(save, dict) or str(save.get("ability", "")).upper() not in {"STR", "DEX", "CON", "INT", "WIS", "CHA"} \
                    or not isinstance(save.get("dc"), int):
                raise ValueError("start_of_combat_strike save requires an ability and an integer dc")
            row["save"] = {"ability": str(save["ability"]).upper(), "dc": int(save["dc"]), "half": bool(save.get("half", True))}
    row["phase"] = KINDS[kind].name
    return row


def effects(run, key: str, kinds: set[str] | None = None) -> list[tuple[dict, str]]:
    """Every lattice row active for ``key``, with a public source label."""
    rows: list[tuple[dict, str]] = []
    combat = run.context.get("combat") if isinstance(run.context.get("combat"), dict) else {}
    encounter = (combat.get("rules") or {}).get(key, {}) if isinstance(combat, dict) else {}
    for effect in encounter.get("lattice", []) if isinstance(encounter, dict) else []:
        rows.append((effect, "encounter"))
    if key.startswith("p"):
        from hollowstar.attunement import attuned_lattice
        rows.extend(attuned_lattice(run, key))
        from hollowstar.affix_runtime import _equipped
        for item in _equipped(run, key):
            for effect in item.get("lattice", []) or []:
                rows.append((effect, str(item.get("name", "equipped item"))))
    return [(effect, source) for effect, source in rows
            if isinstance(effect, dict) and (kinds is None or effect.get("kind") in kinds)]


def convert(run, source: str, target: str, damage_type: str) -> tuple[str, list[dict]]:
    """Apply at most one outgoing and then one incoming conversion.

    One conversion per side is the loop guard: A->B on the attacker and B->C
    on the defender resolve in that order, and nothing converts twice.
    """
    steps = []
    for side, key, kind in (("outgoing", source, "convert_outgoing"), ("incoming", target, "convert_incoming")):
        for effect, origin in effects(run, key, {kind}):
            if damage_type in effect.get("from", []):
                steps.append({"side": side, "actor": key, "from": damage_type, "to": effect["to"],
                              "source": origin, "tell": effect.get("tell", ""), "phase": "MAGNITUDE"})
                damage_type = effect["to"]
                break
    return damage_type, steps


def immunity(run, source: str, target: str, damage_type: str) -> dict | None:
    """Evidence when ``target`` is lattice-immune to ``damage_type``.

    An encounter may give a source ``authority_tier``; a source whose authority
    outranks the immunity's tier pierces it (DM046_0: higher tier wins
    same-phase collisions), which is the authored counterplay to a lattice.
    """
    combat = run.context.get("combat") or {}
    authority = str(((combat.get("rules") or {}).get(source) or {}).get("authority_tier", "")).upper()
    for effect, origin in effects(run, target, {"damage_immunity"}):
        if damage_type not in effect.get("tags", []):
            continue
        tier = effect.get("tier", "ARTIFACT")
        if authority in Tier.__members__ and Tier[authority] > Tier[tier]:
            continue
        return {"damage_type": damage_type, "tier": tier, "source": origin,
                "tell": effect.get("tell", ""), "phase": "APPLICATION"}
    return None


def denies(run, target: str, name: str) -> dict | None:
    """Evidence when ``target`` refuses the named condition or pseudo-condition."""
    for effect, origin in effects(run, target, {"deny_condition"}):
        if name in effect.get("conditions", []):
            return {"condition": name, "source": origin, "tell": effect.get("tell", ""), "phase": "CONSEQUENCE"}
    return None


def _turn_zero_order(run) -> list[str]:
    from hollowstar import tactical as t
    return sorted(t.actors(run), key=lambda k: (k[0] != "p", int(k[1:])))


def start_of_combat(run) -> list[dict]:
    """Resolve Turn 0: wards, then auras, then pre-emptive strikes.

    Runs inside ``tactical.begin`` after the encounter is built and before
    initiative is rolled.  With no Turn 0 rows present it draws no RNG and
    returns an empty list, so replays of lattice-free encounters are
    unchanged.
    """
    from hollowstar import tactical as t
    events: list[dict] = []
    order = _turn_zero_order(run)
    for kind in TURN_ZERO_ORDER:
        for key in order:
            creature = t.actor(run, key)
            rows = effects(run, key, {kind})
            if not rows or not creature.alive:
                continue
            if kind == "start_of_combat_ward":
                total = sum(int(effect.get("amount") or creature.max_hp * int(effect.get("percent_max_hp", 0)) // 100)
                            for effect, _ in rows)
                before = creature.resources.get("ward", 0)
                creature.resources["ward"] = max(before, total)
                events.append({"type": "turn_zero_ward", "actor": key, "ward_before": before,
                               "ward_after": creature.resources["ward"],
                               "sources": [origin for _, origin in rows],
                               "tell": rows[0][0].get("tell", "")})
            elif kind == "start_of_combat_condition":
                for effect, origin in rows:
                    recipients = [key] if effect.get("scope") == "self" else \
                        [k for k in order if t.same_side(k, key) and t.actor(run, k).alive]
                    for recipient in recipients:
                        applied = t.condition(run, recipient, effect["condition"], int(effect.get("duration", 1)))
                        events.append({"type": "turn_zero_condition", "actor": key, "target": recipient,
                                       "condition": applied, "source": origin, "tell": effect.get("tell", "")})
            else:
                for effect, origin in rows:
                    events.append(_turn_zero_strike(run, key, effect, origin))
            if run.finished():
                return events
    return events


def _turn_zero_strike(run, key: str, effect: dict, origin: str) -> dict:
    from hollowstar import tactical as t
    foes = [k for k, v in t.actors(run).items() if not t.same_side(k, key) and v.alive]
    if effect.get("targets") == "lowest_hp_enemy":
        foes = sorted(foes, key=lambda k: (t.actor(run, k).hp / max(1, t.actor(run, k).max_hp), k))[:1]
    elif effect.get("targets") == "nearest_enemy":
        foes = sorted(foes, key=lambda k: (t.distance(run, key, k), k))[:1]
    amount, rolls = t.dice(run, effect["dice"])
    results = []
    for target in foes:
        dealt = amount
        save = None
        if effect.get("save"):
            save = t.saving_throw(run, target, effect["save"]["ability"], effect["save"]["dc"], magical=True)
            if save and save.get("success"):
                dealt = amount // 2 if effect["save"].get("half", True) else 0
        results.append({"target": target, "save": save,
                        "result": t.damage(run, key, target, dealt, effect["damage_type"])})
    return {"type": "turn_zero_strike", "actor": key, "damage_type": effect["damage_type"],
            "rolls": rolls, "damage": amount, "results": results, "source": origin,
            "tell": effect.get("tell", ""),
            "defeated": [row["target"] for row in results if not t.actor(run, row["target"]).alive]}


def audit(run, key: str) -> dict:
    """Report what this actor's lattice makes it immune to (DM046_0 s12 Phase 2).

    ``physical_invulnerable`` is the flag the combination tester looks for:
    every physical subtype either is immune directly or converts into a type
    that is.  Encounter ``authority_tier`` can still pierce it; the audit
    reports the build, not a guarantee.
    """
    immune = {tag: effect.get("tier", "ARTIFACT") for effect, _ in effects(run, key, {"damage_immunity"})
              for tag in effect.get("tags", [])}
    conversions = {}
    for effect, _ in effects(run, key, {"convert_incoming"}):
        for tag in effect.get("from", []):
            conversions.setdefault(tag, effect["to"])
    effective = sorted(tag for tag in DamageTag.__members__
                       if tag in immune or conversions.get(tag) in immune)
    denied = sorted({name for effect, _ in effects(run, key, {"deny_condition"})
                     for name in effect.get("conditions", [])})
    physical = all(tag in effective for tag in PHYSICAL)
    flags = []
    if physical:
        flags.append("physical_invulnerable")
    if len(effective) == len(DamageTag.__members__):
        flags.append("permanently_invulnerable")
    if physical and {"STUNNED", "PARALYZED"} <= set(denied):
        flags.append("action_denial_proof")
    return {"actor": key, "immune_tags": sorted(immune), "incoming_conversions": conversions,
            "effectively_immune": effective, "denied_conditions": denied,
            "physical_invulnerable": physical, "flags": flags}
