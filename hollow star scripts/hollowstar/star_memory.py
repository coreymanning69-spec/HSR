"""The Hollow Star's own memory: the one thing that outlives every vessel.

Account-wide rather than per identity: the Star rides custom builds, Doran and
Wren alike, so each settled run from any vessel lands in one ledger. This is
engine save data under ``.local/``; it never writes to the corpus, so Sandbox
isolation and Forge promotion rules are untouched.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from hollowstar.save_migrations import migrate
from hollowstar.snapshot import assert_safe_write_path
from hollowstar.storage import atomic_json

SCHEMA = "hollow-star-memory-1"
MAX_VESSELS = 200  # oldest vessel records drop off; totals keep counting

# (tier, name, needs) -- a tier is reached when ANY listed threshold is met.
AWARENESS_TIERS = (
    (0, "Ember", {}),
    (1, "Echo", {"runs": 1}),
    (2, "Witness", {"runs": 3, "completions": 1}),
    (3, "Keeper", {"runs": 8, "completions": 3}),
    (4, "Star", {"flag": "star_revealed"}),
)

_CUTSCENE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_FLAG_ID = _CUTSCENE_ID


def _default() -> dict:
    return {"schema": SCHEMA, "runs": 0, "completions": 0, "deaths": 0,
            "vessels": [], "settled_run_ids": [], "flags": [], "seen_cutscenes": [],
            "last_victor": None}


def awareness(data: dict) -> dict:
    reached = AWARENESS_TIERS[0]
    for row in AWARENESS_TIERS[1:]:
        needs = row[2]
        if "flag" in needs:
            hit = needs["flag"] in data["flags"]
        else:
            hit = any(data.get(key, 0) >= value for key, value in needs.items())
        if hit:
            reached = row
    return {"tier": reached[0], "name": reached[1]}


class StarMemory:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    @property
    def path(self) -> Path:
        return assert_safe_write_path(self.root / "hollow_star_memory.json")

    def load(self) -> dict:
        path = self.path
        if not path.exists():
            return _default()
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("invalid Hollow Star memory contract")
        raw, _ = migrate(raw, "hollow-star-memory", 1)
        data = _default()
        for key in ("runs", "completions", "deaths"):
            value = raw.get(key, 0)
            if type(value) is not int or value < 0:
                raise ValueError("invalid Hollow Star memory totals")
            data[key] = value
        for key in ("vessels", "settled_run_ids", "flags", "seen_cutscenes"):
            if not isinstance(raw.get(key, []), list):
                raise ValueError("invalid Hollow Star memory lists")
            data[key] = copy.deepcopy(raw.get(key, []))
        if raw.get("last_victor") is not None and not isinstance(raw["last_victor"], dict):
            raise ValueError("invalid Hollow Star victor record")
        data["last_victor"] = copy.deepcopy(raw.get("last_victor"))
        return data

    def view(self) -> dict:
        """Public readout: the memory plus the derived values the client gates on."""
        data = self.load()
        return {**data, "awareness": awareness(data),
                "meta_shop_unlocked": data["runs"] >= 1}

    def record_run(self, run_id: str, identity: str, receipt: dict, vessel: dict | None = None) -> dict:
        """Fold one settled run into the Star. Idempotent per run id."""
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run id required")
        data = self.load()
        if run_id in data["settled_run_ids"]:
            return self.view()
        outcome = receipt.get("outcome")
        data["settled_run_ids"].append(run_id)
        data["runs"] += 1
        if outcome == "completed":
            data["completions"] += 1
        elif outcome == "dead":
            data["deaths"] += 1
        row = {"run_id": run_id, "identity": identity, "outcome": outcome,
               "status": receipt.get("status"), "rooms": receipt.get("rooms", 0),
               "loop_tier": receipt.get("loop_tier_played", 1)}
        if vessel:
            row["name"] = vessel.get("name")
        data["vessels"] = (data["vessels"] + [row])[-MAX_VESSELS:]
        if outcome == "completed" and vessel:
            # The mirror the Star will wear inside the next cocoon.
            data["last_victor"] = {"run_id": run_id, "identity": identity, **copy.deepcopy(vessel)}
        atomic_json(self.path, data)
        return self.view()

    def absorb_history(self, entries: list) -> dict:
        """Fold ended runs from RunHistory into the Star.

        The web client doesn't always call ``settle_run``, so run history is
        the reliable record that a vessel's run ended. Replaced (abandoned for
        a new game) runs are not memories. Idempotent per run id.
        """
        data = self.load()
        known = set(data["settled_run_ids"])
        fresh = [row for row in entries if isinstance(row, dict) and row.get("status") == "ended"
                 and isinstance(row.get("run_id"), str) and row["run_id"] not in known]
        for row in fresh:
            reason = str(row.get("reason") or "")
            outcome = ("completed" if reason in {"completed", "cleared", "escaped"}
                       else "dead" if reason in {"player_death", "dead", "defeated"} else reason or None)
            party = (row.get("summary") or {}).get("party") or []
            identity = party[0] if party and isinstance(party[0], str) else "unknown"
            self.record_run(row["run_id"], identity, {"outcome": outcome, "status": reason},
                            {"name": identity.split(":", 1)[-1]})
        return self.view()

    def mark_seen(self, cutscene_id: object) -> dict:
        if not isinstance(cutscene_id, str) or not _CUTSCENE_ID.fullmatch(cutscene_id):
            raise ValueError("invalid cutscene id")
        data = self.load()
        if cutscene_id not in data["seen_cutscenes"]:
            data["seen_cutscenes"].append(cutscene_id)
            atomic_json(self.path, data)
        return self.view()

    def set_flag(self, flag: object) -> dict:
        if not isinstance(flag, str) or not _FLAG_ID.fullmatch(flag):
            raise ValueError("invalid story flag")
        data = self.load()
        if flag not in data["flags"]:
            data["flags"].append(flag)
            atomic_json(self.path, data)
        return self.view()

    # ---- debug tools (Simulation > Cheats) ---------------------------------
    def debug(self, op: object, value: object = None) -> dict:
        """Dev-only edits: set totals, clear flags, forget cutscenes, or reset."""
        data = self.load()
        if op == "reset":
            data = _default()
        elif op in {"runs", "completions", "deaths"}:
            if type(value) is not int or not 0 <= value <= 100000:
                raise ValueError("totals are non-negative integers")
            data[op] = value
        elif op == "clear_flag":
            data["flags"] = [f for f in data["flags"] if f != value]
        elif op == "set_flag":
            return self.set_flag(value)
        elif op == "forget_cutscenes":
            data["seen_cutscenes"] = []
        else:
            raise ValueError("unknown Star debug operation")
        atomic_json(self.path, data)
        return self.view()
