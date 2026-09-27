"""Host-owned save retention and compact run history.

Full run files remain the only resumable state.  This module keeps a small
public lifecycle index beside them so pruning old saves does not erase the
meaning of Last Run or the reason a run stopped being resumable.
"""

from __future__ import annotations

from datetime import datetime, timezone
import copy
import json
from pathlib import Path

from hollowstar.storage import atomic_json


HISTORY_SCHEMA = "hollow-star-run-history-2"
MAX_FULL_SAVES = 5


def _now() -> str:
    # History ordering is user-visible (Last Run), so retain sub-second
    # precision when several lifecycle transitions happen in one second.
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _mode(summary: dict) -> str:
    context = summary.get("context") if isinstance(summary, dict) else {}
    return str((context or {}).get("host_mode") or summary.get("mode") or "DESIGN").upper()


def _scenario(summary: dict) -> str:
    context = summary.get("context") if isinstance(summary, dict) else {}
    return str((context or {}).get("scenario") or "")


def _party(summary: dict) -> list[str]:
    context = summary.get("context") if isinstance(summary, dict) else {}
    selectors = (context or {}).get("party_selectors")
    if isinstance(selectors, list) and selectors:
        return [str(row) for row in selectors]
    return [str(row.get("name")) for row in summary.get("party", []) if isinstance(row, dict) and row.get("name")]


def compact_summary(summary: dict) -> dict:
    """Return only public, useful run metadata for the history sidecar."""
    return {
        "run_id": summary.get("run_id"),
        "mode": _mode(summary),
        "seed": summary.get("seed"),
        "round_number": summary.get("round_number", 0),
        "finished": bool(summary.get("finished")),
        "winner": summary.get("winner"),
        "party": _party(summary),
        "scenario": _scenario(summary),
    }


METRIC_KEYS = ("rooms_entered", "rooms_cleared", "floors_reached", "floors_completed",
               "combat_encounters", "combat_rounds", "actions_resolved", "gold_earned",
               "gold_spent", "gold_lost", "gold_retained", "gold_current", "platinum_earned",
               "gameplay_minutes", "active_session_seconds")


def compact_public_metrics(state: dict | None) -> dict:
    """Copy recorded public counters only; absence is unknown, never zero."""
    if not isinstance(state, dict):
        return {}
    tracking = state.get("tracking")
    receipt = state.get("terminal_receipt")
    if not isinstance(tracking, dict):
        tracking = receipt.get("tracking", {}) if isinstance(receipt, dict) else {}
    result = {key: tracking[key] for key in METRIC_KEYS
              if type(tracking.get(key)) is int and tracking[key] >= 0}
    for key in ("started_at", "ended_at", "terminal_status", "completion_kind"):
        if isinstance(tracking.get(key), str):
            result[key] = tracking[key]
    if isinstance(receipt, dict):
        for key in ("outcome", "completion_kind", "status"):
            if isinstance(receipt.get(key), str):
                result[key] = receipt[key]
    elif isinstance(state.get("outcome"), str):
        result["outcome"] = state["outcome"]
    return result


class RunHistory:
    """Reconcile validated saves, retain five per mode, and report history."""

    def __init__(self, data_root: Path | str, run_root: Path | str, service):
        self.data_root = Path(data_root)
        self.run_root = Path(run_root)
        self.service = service
        self.path = self.data_root / "hsr_run_history.json"

    def _load(self) -> dict:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {"schema_version": HISTORY_SCHEMA, "entries": {}}
        if not isinstance(raw, dict) or raw.get("schema_version") not in {HISTORY_SCHEMA, "hollow-star-run-history-1"}:
            return {"schema_version": HISTORY_SCHEMA, "entries": {}}
        entries = raw.get("entries")
        return {"schema_version": HISTORY_SCHEMA, "entries": entries if isinstance(entries, dict) else {}}

    def _save(self, data: dict) -> None:
        atomic_json(self.path, data)

    def _entry(self, data: dict, run_id: str) -> dict:
        entries = data.setdefault("entries", {})
        value = entries.get(run_id)
        if not isinstance(value, dict):
            value = {"run_id": run_id, "status": "active", "reason": None, "ended_at": None, "pruned": False}
            entries[run_id] = value
        return value

    def _summary(self, run_id: str) -> tuple[dict, dict | None]:
        summary = self.service.inspect(run_id).as_dict()
        state = None
        try:
            state = self.service.observe(run_id)
        except Exception:  # malformed/legacy view data must not make pruning destructive
            state = None
        return summary, state

    @staticmethod
    def _terminal_from(summary: dict, state: dict | None) -> tuple[str | None, str | None, str | None]:
        context = summary.get("context") if isinstance(summary, dict) else {}
        sandbox = (context or {}).get("sandbox") if isinstance(context, dict) else None
        sandbox_status = sandbox.get("status") if isinstance(sandbox, dict) else None
        public_status = state.get("status") if isinstance(state, dict) else None
        outcome = state.get("outcome") if isinstance(state, dict) else None
        if sandbox_status and sandbox_status != "active":
            reason = "new_game" if sandbox_status == "replaced" else str(sandbox_status)
            return "ended", reason, None
        if public_status in {"closed", "defeated", "cleared", "escaped", "abandoned"}:
            reason = "player_death" if public_status == "closed" else str(public_status)
            return "ended", reason, None
        if outcome in {"dead", "completed"}:
            return "ended", str(outcome), None
        if summary.get("finished"):
            return "ended", "completed" if summary.get("winner") == "party" else "defeated", None
        return None, None, None

    def _merge_summary(self, entry: dict, summary: dict, state: dict | None = None, *, seen_at: str | None = None) -> None:
        entry["summary"] = compact_summary(summary)
        entry["mode"] = _mode(summary)
        entry["scenario"] = _scenario(summary)
        metrics = compact_public_metrics(state)
        if metrics:
            entry["metrics"] = metrics
        entry["last_seen_at"] = seen_at or entry.get("last_seen_at") or _now()

    def reconcile(self) -> tuple[dict, list[dict]]:
        data = self._load()
        valid: list[dict] = []
        changed = False
        if self.run_root.exists():
            for path in sorted(self.run_root.glob("*.json")):
                run_id = path.stem
                try:
                    summary, state = self._summary(run_id)
                except Exception:
                    # Retention must never remove a file it cannot validate.
                    continue
                entry = self._entry(data, run_id)
                before = copy.deepcopy(entry)
                self._merge_summary(entry, summary, state)
                if entry.get("status") not in {"replaced", "ended"}:
                    entry["status"] = "active"
                    entry["reason"] = None
                derived_status, reason, ended_at = self._terminal_from(summary, state)
                if derived_status and entry.get("status") != "replaced":
                    entry["status"] = derived_status
                    entry["reason"] = reason
                    entry["ended_at"] = entry.get("ended_at") or ended_at or _now()
                entry["pruned"] = False
                entry["file_mtime_ns"] = path.stat().st_mtime_ns
                valid.append({"run_id": run_id, "path": path, "summary": summary, "state": state, "entry": entry})
                changed |= entry != before
        if changed:
            self._save(data)
        return data, valid

    def mark_replaced(self, run_id: str | None) -> None:
        if not isinstance(run_id, str) or not run_id:
            return
        try:
            summary, state = self._summary(run_id)
        except Exception:
            return
        data = self._load()
        entry = self._entry(data, run_id)
        self._merge_summary(entry, summary, state)
        if entry.get("status") not in {"ended", "replaced"}:
            entry.update({"status": "replaced", "reason": "new_game", "ended_at": _now()})
        self._save(data)

    def maintain(self, protected_run_id: str | None = None) -> dict:
        data, valid = self.reconcile()
        groups: dict[str, list[dict]] = {}
        for row in valid:
            groups.setdefault(_mode(row["summary"]), []).append(row)
        pruned: list[str] = []
        for mode, rows in groups.items():
            rows.sort(key=lambda row: row["path"].stat().st_mtime_ns, reverse=True)
            keep = [row["run_id"] for row in rows[:MAX_FULL_SAVES]]
            if protected_run_id and any(row["run_id"] == protected_run_id for row in rows) and protected_run_id not in keep:
                keep = [protected_run_id] + [run_id for run_id in keep if run_id != protected_run_id][:MAX_FULL_SAVES - 1]
            for row in rows:
                if row["run_id"] in keep:
                    continue
                try:
                    # The row was successfully inspected above, so this is a
                    # validated run save and is safe to prune.
                    row["path"].unlink()
                except OSError:
                    continue
                entry = self._entry(data, row["run_id"])
                self._merge_summary(entry, row["summary"], row["state"])
                entry["pruned"] = True
                entry["pruned_at"] = _now()
                pruned.append(row["run_id"])
        if pruned:
            self._save(data)
        return {"retained": [row["run_id"] for row in valid if row["run_id"] not in pruned], "pruned": pruned}

    def statistics(self, mode: str | None = None) -> dict:
        data, valid = self.reconcile()
        wanted = str(mode).upper() if isinstance(mode, str) and mode else None
        entries = data.get("entries", {})
        saves = []
        for row in valid:
            if wanted and _mode(row["summary"]) != wanted:
                continue
            entry = self._entry(data, row["run_id"])
            saves.append(copy.deepcopy(entry))
        last = []
        for entry in entries.values():
            if not isinstance(entry, dict) or entry.get("status") not in {"ended", "replaced"}:
                continue
            if wanted and str(entry.get("mode", "")).upper() != wanted:
                continue
            last.append(entry)
        last.sort(key=lambda entry: str(entry.get("ended_at") or entry.get("last_seen_at") or ""), reverse=True)
        saves.sort(key=lambda entry: int(entry.get("file_mtime_ns", 0)), reverse=True)
        all_runs = [copy.deepcopy(entry) for entry in entries.values()
                    if isinstance(entry, dict) and (not wanted or str(entry.get("mode", "")).upper() == wanted)]
        all_runs.sort(key=lambda entry: str(entry.get("ended_at") or entry.get("last_seen_at") or ""), reverse=True)
        return {
            "schema": HISTORY_SCHEMA,
            "mode": wanted,
            "last_run": copy.deepcopy(last[0]) if last else None,
            "saves": saves,
            "all_runs": all_runs,
        }
