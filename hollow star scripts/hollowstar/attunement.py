"""The Attunement Matrix: decanted Prefix, Suffix, and Legendary slots.

A character carries three equipped-gear lanes plus an independent matrix of
powers absorbed from destroyed loot.  Decanting (alias: devouring,
disenchanting) destroys an identified item and slots what it carried:

  prefix     <- the item's active catalog Prefix
  suffix     <- the item's active catalog Suffix
  legendary  <- a relic's or legendary item's modifiers and Immunity Lattice rows

Capacity is account meta-progression.  Each lane starts at BASE_SLOTS and the
Meta Shop tracks in ``progression.UPGRADES`` (``prefix_capacity`` and friends)
add one slot per tier.  RunService freezes those tiers into the run at launch,
so a replay never changes when the account buys more.

Contents are run-local.  DM046_0 section 9 keeps "whether a clear permits any
permanent carry-out reward" an explicit testing decision, and says most
Imprints should dissolve outside, so the matrix lives in
``run.context['dungeon']['attunement']`` and ends with the run.  NOTE: if Corey
decides decanted powers should persist across runs, ``Progression.settle`` is
the one place to copy them out; nothing else needs to change.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from hollowstar import tactical as t


LANES = ("prefix", "suffix", "legendary")
BASE_SLOTS = 1
CAPACITY_TRACKS = {"prefix": "prefix_capacity", "suffix": "suffix_capacity",
                   "legendary": "legendary_capacity"}
ELIGIBLE_RARITIES = {"rare", "legendary"}
# One copy of each named power per actor lane. Stacking six copies of the same
# flat bonus is the degenerate build DM046_0 asks combination testing to catch,
# and it adds no decision.  Flip this only with a balance pass behind it.
ALLOW_DUPLICATES = False
LEGENDARY_CATALOG = Path(__file__).resolve().parent / "content" / "legendaries.json"


def legendary_catalog() -> dict[str, dict]:
    """Authored legendary powers keyed by id. Not in any drop table yet."""
    from hollowstar import lattice
    data = json.loads(LEGENDARY_CATALOG.read_text(encoding="utf-8"))
    rows = {}
    for row in data.get("legendaries", []):
        if not isinstance(row, dict) or not row.get("id") or not row.get("name"):
            raise ValueError("legendary rows require an id and a name")
        clean = copy.deepcopy(row)
        clean["lattice"] = [lattice.validate(effect) for effect in row.get("lattice", [])]
        rows[str(row["id"])] = clean
    return rows


def _dungeon(run) -> dict | None:
    d = run.context.get("dungeon")
    return d if isinstance(d, dict) else None


def capacity(run) -> dict[str, int]:
    """Slots per lane, from the Meta Shop tiers frozen into this run."""
    d = _dungeon(run) or {}
    upgrades = d.get("upgrades", {}) if isinstance(d.get("upgrades"), dict) else {}
    return {lane: BASE_SLOTS + max(0, int(upgrades.get(track, 0) or 0))
            for lane, track in CAPACITY_TRACKS.items()}


def matrix(run, actor_key: str) -> dict[str, list]:
    """The live (mutable) matrix for one actor, created on first use."""
    d = _dungeon(run)
    if d is None:
        raise t.ActionError("attunement requires an active dungeon run")
    table = d.setdefault("attunement", {})
    row = table.setdefault(actor_key, {})
    for lane in LANES:
        row.setdefault(lane, [])
    return row


def _peek(run, actor_key: str) -> dict[str, list]:
    """Read-only matrix access that never creates state (safe in combat math)."""
    d = _dungeon(run) or {}
    row = (d.get("attunement") or {}).get(actor_key) or {}
    return {lane: row.get(lane, []) if isinstance(row.get(lane), list) else [] for lane in LANES}


def attuned_affixes(run, actor_key: str) -> list[tuple[dict, dict]]:
    """Attuned Prefix/Suffix affixes with a display source for evidence rows."""
    rows = []
    for lane in ("prefix", "suffix"):
        for entry in _peek(run, actor_key)[lane]:
            if isinstance(entry, dict) and isinstance(entry.get("effects"), list):
                source = {"name": f"Attuned {entry.get('name', lane)}", "attuned": True,
                          "lane": lane, "source_item": entry.get("source_item")}
                rows.append((entry, source))
    return rows


def attuned_modifiers(run, actor_key: str) -> list[dict]:
    """Rune-vocabulary modifiers carried by attuned Legendary slots."""
    return [modifier for entry in _peek(run, actor_key)["legendary"] if isinstance(entry, dict)
            for modifier in entry.get("modifiers", []) if isinstance(modifier, dict)]


def attuned_lattice(run, actor_key: str) -> list[tuple[dict, str]]:
    """Immunity Lattice rows carried by attuned Legendary slots."""
    return [(effect, f"Attuned {entry.get('name', 'legendary')}")
            for entry in _peek(run, actor_key)["legendary"] if isinstance(entry, dict)
            for effect in entry.get("lattice", []) if isinstance(effect, dict)]


def _extract(item: dict) -> dict[str, dict]:
    """What decanting this item would yield, lane by lane."""
    from hollowstar.affix_runtime import materialize
    parts: dict[str, dict] = {}
    for lane in ("prefix", "suffix"):
        carried = item.get(lane)
        name = carried.get("name") if isinstance(carried, dict) else carried
        canonical = materialize(name, lane) if name else None
        if canonical is None:
            # Legacy or upgrade-track suffixes (e.g. Reliquary Temper) carry no
            # active effect rows, so there is nothing to absorb.
            continue
        previous = carried.get("effects", []) if isinstance(carried, dict) else []
        for index, effect in enumerate(canonical["effects"]):
            # Spent charges stay spent: decanting is not a recharge exploit.
            if index < len(previous) and isinstance(previous[index], dict) and "charges" in previous[index]:
                effect["charges"] = previous[index]["charges"]
        parts[lane] = canonical
    if item.get("kind") == "legendary" or item.get("relic") or item.get("rarity") == "legendary":
        parts["legendary"] = {
            "name": str(item.get("true_name") or item.get("name") or "legendary power"),
            "description": str(item.get("description", "")),
            "modifiers": copy.deepcopy([m for m in item.get("modifiers", []) if isinstance(m, dict)]),
            "lattice": copy.deepcopy([e for e in item.get("lattice", []) if isinstance(e, dict)]),
        }
    return parts


def eligibility(item: dict) -> tuple[bool, str]:
    if not isinstance(item, dict):
        return False, "unknown inventory item"
    if not item.get("identified", False):
        return False, "identify the item before decanting it"
    if item.get("kind") != "imprint" and item.get("rarity") not in ELIGIBLE_RARITIES:
        return False, "only Imprints and rare or legendary items can be decanted"
    if not _extract(item):
        return False, "this item carries no active Prefix, Suffix, or legendary power to decant"
    return True, ""


def _replacement(replace, lane: str, slots: list) -> int | None:
    """Resolve a caller's replace choice to a slot index in this lane."""
    if isinstance(replace, dict):
        choice = replace.get(lane)
    else:
        choice = replace
    if choice is None:
        return None
    if isinstance(choice, int) and not isinstance(choice, bool):
        return choice if 0 <= choice < len(slots) else None
    wanted = str(choice).strip().lower()
    return next((index for index, entry in enumerate(slots)
                 if str(entry.get("name", "")).lower() == wanted), None)


def _require_party_actor(run, actor_key: str) -> None:
    if not isinstance(actor_key, str) or not actor_key.startswith("p") \
            or not actor_key[1:].isdigit() or int(actor_key[1:]) >= len(run.party):
        raise t.ActionError("attunement belongs to a party actor")


def _combat_active(run) -> bool:
    combat = run.context.get("combat")
    return isinstance(combat, dict) and not combat.get("complete")


def decant(run, item_id, actor_key: str = "p0", replace=None) -> dict:
    """Destroy one eligible item and slot its powers into ``actor_key``'s matrix.

    All-or-nothing: every lane the item feeds must have room (or a named
    replacement) before anything is destroyed.
    """
    _require_party_actor(run, actor_key)
    if _combat_active(run):
        raise t.ActionError("decanting requires a safe pause; combat is active")
    d = _dungeon(run)
    if d is None:
        raise t.ActionError("decanting requires an active dungeon run")
    item = d.get("inventory", {}).get(item_id)
    if item is None:
        raise t.ActionError("unknown inventory item")
    ok, reason = eligibility(item)
    if not ok:
        raise t.ActionError(reason)
    parts = _extract(item)
    slots_max = capacity(run)
    live = matrix(run, actor_key)
    plan = {}
    for lane, payload in parts.items():
        slots = live[lane]
        if not ALLOW_DUPLICATES and any(str(entry.get("name")) == payload["name"] for entry in slots):
            raise t.ActionError(f"{payload['name']} is already attuned in this {lane} lane")
        if len(slots) < slots_max[lane]:
            plan[lane] = None
            continue
        index = _replacement(replace, lane, slots)
        if index is None:
            raise t.ActionError(
                f"{lane} slots are full ({len(slots)}/{slots_max[lane]}); name an attuned {lane} "
                f"to replace, or expand {lane} capacity in the Meta Shop")
        plan[lane] = index
    from hollowstar.affix_runtime import display_name
    source_name = display_name(copy.deepcopy(item))
    here = f"{d.get('floor')}:{d.get('room')}"
    extracted, replaced = {}, {}
    for lane, payload in parts.items():
        entry = {**payload, "source_item": item_id, "source_name": source_name, "decanted_at": here}
        if plan[lane] is None:
            live[lane].append(entry)
        else:
            replaced[lane] = live[lane][plan[lane]].get("name")
            live[lane][plan[lane]] = entry
        extracted[lane] = payload["name"]
    del d["inventory"][item_id]
    unequipped = []
    for owner, equipped in d.get("imprints", {}).items():
        for slot, ident in list(equipped.items()):
            if ident == item_id:
                del equipped[slot]
                unequipped.append({"actor": owner, "slot": slot})
    d.get("permanent_gear", {}).pop(item_id, None)
    return {"type": "item_decanted", "actor": actor_key, "item_id": item_id, "item": source_name,
            "extracted": extracted, "replaced": replaced,
            "slots_used": {lane: len(live[lane]) for lane in LANES}, "slots_max": slots_max,
            "evidence": {"item_destroyed": True, "unequipped": unequipped,
                         "carry_out": "run-local; the matrix ends with this run",
                         "state_change": f"{', '.join(sorted(extracted))} attuned to {actor_key}"}}


def release(run, actor_key: str, lane: str, name) -> dict:
    """Empty one attuned slot. The power is gone; nothing returns to inventory."""
    _require_party_actor(run, actor_key)
    if lane not in LANES:
        raise t.ActionError("choose a prefix, suffix, or legendary slot")
    if _combat_active(run):
        raise t.ActionError("releasing an attunement requires a safe pause; combat is active")
    slots = matrix(run, actor_key)[lane]
    index = _replacement(name, lane, slots)
    if index is None:
        raise t.ActionError(f"no attuned {lane} named {name}")
    removed = slots.pop(index)
    return {"type": "attunement_released", "actor": actor_key, "lane": lane, "name": removed.get("name"),
            "slots_used": {key: len(value) for key, value in matrix(run, actor_key).items()},
            "slots_max": capacity(run),
            "evidence": {"state_change": f"{removed.get('name')} released from {actor_key}'s {lane} lane"}}


def grant_legendary(run, legendary_id: str) -> dict:
    """Place one authored legendary item in the run inventory (identified).

    Drop tables do not roll legendaries yet; this is the seam a Floor 5 reward,
    a Simulation Mode cheat, or a test uses.
    """
    d = _dungeon(run)
    if d is None:
        raise t.ActionError("granting a legendary requires an active dungeon run")
    spec = legendary_catalog().get(str(legendary_id))
    if spec is None:
        raise t.ActionError(f"unknown legendary: {legendary_id}")
    ident = f"item-{d['next_item']}"
    d["next_item"] += 1
    item = {"id": ident, "kind": "legendary", "name": spec["name"], "true_name": spec["name"],
            "legendary_id": spec["id"], "temporary": True, "slot": None, "level": 1,
            "rarity": "legendary", "upgradeable": False, "prefix": None, "suffix": None,
            "percentage_bonus": 0, "value": int(spec.get("value", 50)), "identified": True,
            "unidentified_descriptor": spec.get("descriptor"), "description": spec.get("description", ""),
            "modifiers": copy.deepcopy(spec.get("modifiers", [])),
            "lattice": copy.deepcopy(spec["lattice"])}
    d.setdefault("inventory", {})[ident] = item
    return copy.deepcopy(item)


def public_view(run) -> dict:
    """Narrator-safe projection: run capacity once, then only non-empty matrices.

    Kept compact on purpose; the design_turn wire budget (tests/test_host.py)
    guards against the turn envelope growing into a state dump.
    """
    d = _dungeon(run) or {}
    table = d.get("attunement") or {}
    actors = {}
    for index, member in enumerate(run.party):
        key = f"p{index}"
        row = _peek(run, key)
        if key not in table or not any(row[lane] for lane in LANES):
            continue
        actors[key] = {"actor": member.name,
                       "lanes": {lane: [{"name": entry.get("name"), "source": entry.get("source_name"),
                                         "decanted_at": entry.get("decanted_at"),
                                         "description": entry.get("description", ""),
                                         "lattice": [effect.get("kind") for effect in entry.get("lattice", [])]}
                                        for entry in row[lane] if isinstance(entry, dict)]
                                 for lane in LANES}}
    return {"capacity": capacity(run), "actors": actors}
