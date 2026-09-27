"""Authoritative account-scoped HSR progression and deterministic migration."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from hollowstar.storage import atomic_json
from hollowstar.snapshot import assert_safe_write_path


UPGRADES = {
    "precision": {"cap": 5, "base_cost": 2, "effect": "+1 permanent accuracy per tier"},
    "force": {"cap": 5, "base_cost": 2, "effect": "+1 permanent weapon damage per tier"},
    "ward": {"cap": 5, "base_cost": 2, "effect": "+1 permanent AC per tier"},
    "reserve": {"cap": 5, "base_cost": 2, "effect": "+1 starting healing potion per tier"},
    "mastery_capacity": {"cap": 5, "base_cost": 3, "effect": "+1 Gem upgrade capacity per tier"},
    # Attunement Matrix capacity (hollowstar/attunement.py). Each lane starts
    # at one slot; five tiers take a lane to six.
    "prefix_capacity": {"cap": 5, "base_cost": 3, "effect": "+1 decanted Prefix attunement slot per tier"},
    "suffix_capacity": {"cap": 5, "base_cost": 3, "effect": "+1 decanted Suffix attunement slot per tier"},
    "legendary_capacity": {"cap": 5, "base_cost": 4, "effect": "+1 decanted Legendary attunement slot per tier"},
}

LEGACY_UPGRADE_ALIASES = {"supplies": "reserve", "crafting": "mastery_capacity"}


def _default(identity: str) -> dict:
    upgrades = {key: 0 for key in UPGRADES}
    upgrades.update({"supplies": 0, "crafting": 0})
    return {"schema": 3, "identity": identity, "account_id": identity,
            "rank_xp": 0, "rank": 1,
            "platinum": 0, "currency": 0, "upgrades": upgrades, "runs": {},
            "loop_tier": 1, "account_meta": {"loop_tier": 1, "meta_currency": 0},
            "life_account": {"schema": "hollow-star-life-account-1", "meta_currency": 0, "closed_worlds": []},
            "tracking": {"gold_earned": 0, "gold_spent": 0,
            "gold_lost": 0, "gold_retained": 0, "platinum_earned": 0,
            "rooms_entered": 0, "rooms_cleared": 0, "floors_reached": 0,
            "combat_encounters": 0, "combat_rounds": 0, "actions_resolved": 0,
            "gameplay_minutes": 0, "active_session_seconds": 0}}


def _canonical_upgrades(values: dict) -> dict:
    if not isinstance(values, dict):
        raise ValueError("invalid upgrade levels")
    result = {key: 0 for key in UPGRADES}
    for key in UPGRADES:
        value = values.get(key, 0)
        if type(value) is not int or not 0 <= value <= UPGRADES[key]["cap"]:
            raise ValueError("invalid upgrade levels")
        result[key] = value
    for old, new in LEGACY_UPGRADE_ALIASES.items():
        if old in values:
            value = values[old]
            if type(value) is not int or not 0 <= value <= UPGRADES[new]["cap"]:
                raise ValueError("invalid legacy upgrade levels")
            if new not in values:
                result[new] = value
    result.update({"supplies": result["reserve"], "crafting": result["mastery_capacity"]})
    return result


def shop_catalog(upgrades: dict | None = None) -> list[dict]:
    """The Meta Shop as rows: tier, cap, and the Platinum cost of the next tier."""
    levels = upgrades if isinstance(upgrades, dict) else {}
    rows = []
    for key, spec in UPGRADES.items():
        level = int(levels.get(key, 0) or 0)
        rows.append({"key": key, "effect": spec["effect"], "tier": level, "cap": spec["cap"],
                     "base_cost": spec["base_cost"], "capped": level >= spec["cap"],
                     "next_cost": None if level >= spec["cap"] else spec["base_cost"] * (level + 1)})
    return rows


class Progression:
    def __init__(self, root):
        self.root = Path(root)

    def path(self, identity):
        if not isinstance(identity, str) or not re.fullmatch(r"(custom|divine|hsr):[A-Za-z0-9 _-]+", identity):
            raise ValueError("invalid progression identity")
        return assert_safe_write_path(self.root / (identity.replace(":", "_") + ".json"))

    def load(self, identity):
        path = self.path(identity)
        if not path.exists():
            return _default(identity)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("identity") != identity:
            raise ValueError("invalid progression contract")
        if data.get("schema") not in {1, 2, 3}:
            raise ValueError("invalid progression contract")
        platinum = data.get("platinum", data.get("currency", 0))
        if any(type(data.get(key)) is not int or data.get(key) < 0 for key in ("rank_xp", "rank")) \
                or type(platinum) is not int or platinum < 0 \
                or data["rank"] != min(10, 1 + data["rank_xp"] // 4):
            raise ValueError("invalid earned progression totals")
        if not isinstance(data.get("runs"), dict):
            raise ValueError("invalid completion receipts")
        loop_tier = data.get("loop_tier", 1)
        if type(loop_tier) is not int or loop_tier < 1:
            raise ValueError("invalid loop tier")
        result = _default(identity)
        result.update({"rank_xp": data["rank_xp"], "rank": data["rank"],
                       "platinum": platinum, "currency": platinum,
                       "runs": copy.deepcopy(data["runs"]), "loop_tier": loop_tier})
        result["upgrades"] = _canonical_upgrades(data.get("upgrades", {}))
        result["account_id"] = data.get("account_id", identity)
        result["account_meta"] = copy.deepcopy(data.get("account_meta", {"loop_tier": loop_tier, "meta_currency": platinum}))
        result["account_meta"].update({"loop_tier": loop_tier, "meta_currency": platinum})
        life = data.get("life_account")
        if isinstance(life, dict):
            result["life_account"].update(copy.deepcopy(life))
        old_tracking = data.get("tracking", {})
        if isinstance(old_tracking, dict):
            result["tracking"].update({key: int(old_tracking.get(key, 0)) for key in result["tracking"]
                                       if isinstance(old_tracking.get(key, 0), int) and old_tracking.get(key, 0) >= 0})
        # Schema 1/2 files are read as-is but upgraded deterministically on disk.
        if data.get("schema") != 3:
            atomic_json(path, result)
        return result

    def migrate_life_account(self, identity):
        """Fold the legacy singleton Floor One account into the lead account once."""
        data = self.load(identity)
        legacy = self.root.parent / "reliquary_life_account.json"
        if legacy.exists() and not data["life_account"].get("closed_worlds"):
            raw = json.loads(legacy.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data["life_account"].update({"meta_currency": int(raw.get("meta_currency", 0)),
                    "closed_worlds": copy.deepcopy(raw.get("closed_worlds", []))})
                data["platinum"] += data["life_account"]["meta_currency"]
                data["currency"] = data["platinum"]
                data["account_meta"]["meta_currency"] = data["platinum"]
                atomic_json(self.path(identity), data)
        return data

    def settle(self, identity, run_id, run):
        d = run.context["dungeon"]
        if d["status"] not in {"cleared", "defeated", "ejected", "escaped"}:
            raise ValueError("only ended runs may award persistent progress")
        if identity not in [s if ":" in s else "divine:" + s
                            for s in run.context.get("party_selectors", [])]:
            raise ValueError("identity was not in this run")
        from hollowstar.dungeon import TERMINAL_OUTCOMES
        data = self.load(identity)
        terminal = copy.deepcopy(d.get("terminal_receipt") or {})
        outcome = terminal.get("outcome") or TERMINAL_OUTCOMES.get(d["status"])
        receipt = {
            "seed": run.rng.seed,
            "status": d["status"],
            "outcome": outcome,
            "rooms": d["rooms_cleared"],
            "platinum": d["meta_currency"],
            "currency": d["meta_currency"],
            "checkpoint_id": terminal.get("checkpoint_id"),
            "retained": copy.deepcopy(terminal.get("retained", {})),
            "lost_unbanked_items": copy.deepcopy(terminal.get("lost_unbanked_items", [])),
            "conducts": copy.deepcopy(terminal.get("conducts", [])),
            # The tier this specific run was played at, frozen by RunService.create
            # into run.context at launch -- never re-derived from the account's
            # current tier, which may have already advanced past it.
            "loop_tier_played": run.context.get("loop_tier", 1),
            "tracking": copy.deepcopy(d.get("tracking", {})),
        }
        if run_id in data["runs"]:
            if data["runs"][run_id] != receipt:
                raise ValueError("completion receipt conflicts with prior settlement")
            return data
        data["runs"][run_id] = receipt
        data["rank_xp"] += d["rooms_cleared"]
        data["platinum"] += d["meta_currency"]
        data["currency"] = data["platinum"]
        run_tracking = receipt["tracking"]
        for key in data["tracking"]:
            data["tracking"][key] += int(run_tracking.get(key, 0))
        # Only a public `completed` outcome advances the account toward a
        # harder/richer next world; `dead` (defeated or forced ejection) does
        # not, so retrying after a death starts back at the same tier.
        if outcome == "completed":
            data["loop_tier"] += 1
        data["rank"] = min(10, 1 + data["rank_xp"] // 4)
        atomic_json(self.path(identity), data)
        return copy.deepcopy(data)

    def purchase(self, identity, key):
        key = LEGACY_UPGRADE_ALIASES.get(key, key)
        if key not in UPGRADES:
            raise ValueError("unknown persistent upgrade")
        data = self.load(identity)
        level = data["upgrades"][key]
        spec = UPGRADES[key]
        if level >= spec["cap"]:
            raise ValueError("upgrade is capped")
        cost = spec["base_cost"] * (level + 1)
        if data["platinum"] < cost:
            raise ValueError("insufficient Platinum")
        data["platinum"] -= cost
        data["currency"] = data["platinum"]
        data["upgrades"][key] += 1
        data["upgrades"]["supplies"] = data["upgrades"]["reserve"]
        data["upgrades"]["crafting"] = data["upgrades"]["mastery_capacity"]
        atomic_json(self.path(identity), data)
        return copy.deepcopy(data)
