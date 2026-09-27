#!/usr/bin/env python3
"""Compact HSR driver for token-metered callers (Cowork/Claude sessions).

Every command prints ONE short JSON line -- never the full engine state tree.
Full state always stays on disk under .local/reliquary_runs/<run_id>.json;
this only surfaces what's needed to decide the next move.

    python3 tools/probe_compact.py newrun <run_id> --race human --class rogue --level 4
    python3 tools/probe_compact.py act <run_id> --type attack --actor p0 --target e0
    python3 tools/probe_compact.py status <run_id>

Exit code is always 0; failures come back as {"ok": false, "error": "..."} so a
caller never has to parse a traceback.

HARD SIZE GUARD: the engine's raw state (party/room/combat/event history/full
item catalog) is measured -- as a byte count only, never printed -- before this
tool touches it. If it's grown past MAX_RAW_STATE_CHARS, the tool refuses to
build a summary and returns a short error instead. That protects the caller
from ever accidentally piping a multi-megabyte blob back through a token-metered
channel; it does NOT fix the underlying growth, it just fails loud and cheap
instead of failing expensive.
"""
from __future__ import annotations
import sys, json, argparse
from pathlib import Path

HSR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HSR_ROOT))

from hollowstar.character_builder import preview
from hollowstar.profiles import ProfileService
from hollowstar.run_service import RunService

MAX_RAW_STATE_CHARS = 5_000_000  # ~5MB of raw engine state; tune if legitimate runs need more


class StateTooLargeError(Exception):
    def __init__(self, raw_chars: int):
        self.raw_chars = raw_chars
        super().__init__(f"raw engine state is {raw_chars:,} chars (hard limit {MAX_RAW_STATE_CHARS:,})")


def get_paths(data_root: str | Path | None = None) -> tuple[Path, Path]:
    if data_root:
        base = Path(data_root).expanduser().resolve()
        if base.name == "reliquary_runs":
            run_root = base
            profile_root = base.parent / "reliquary_profiles"
        else:
            run_root = base / "reliquary_runs"
            profile_root = base / "reliquary_profiles"
    else:
        try:
            from hollowstar.paths import resolve_paths
            # No data_root override: the host config decides, so probes see the
            # same runs as HSRHost.from_options() (MCP server, bridge watcher).
            hp = resolve_paths()
            run_root = hp.run_root
            profile_root = hp.profile_root
        except Exception:
            run_root = (HSR_ROOT / ".local/reliquary_runs").resolve()
            profile_root = (HSR_ROOT / ".local/reliquary_profiles").resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    profile_root.mkdir(parents=True, exist_ok=True)
    return run_root, profile_root


def _runs(data_root: str | Path | None = None) -> RunService:
    run_root, profile_root = get_paths(data_root)
    return RunService(
        run_root,
        snapshot_path=(HSR_ROOT / "snapshots/party_snapshot.json").resolve(),
        profile_root=profile_root,
        module_root=(HSR_ROOT / "hollowstar/content/modules").resolve(),
    )


def _profile_root(data_root: str | Path | None = None) -> Path:
    _, profile_root = get_paths(data_root)
    return profile_root


def _guarded_size(obj) -> int:
    """Measure how big obj would be as JSON, without ever holding the printed
    form anywhere a caller could see it. Cheap on the device regardless of size."""
    return len(json.dumps(obj, default=str))


def _compact_state(state: dict) -> dict:
    raw_chars = _guarded_size(state)
    if raw_chars > MAX_RAW_STATE_CHARS:
        raise StateTooLargeError(raw_chars)
    room = state.get("room", {}) or {}
    combat = state.get("combat", {}) or {}
    party = [{"id": a.get("id"), "name": a.get("name"), "hp": a.get("hp"),
              "max_hp": a.get("max_hp"), "ac": a.get("ac")} for a in state.get("party", [])]
    actors = combat.get("actors") or {}
    enemies = [{"id": k, "name": v.get("name"), "hp": v.get("hp"), "max_hp": v.get("max_hp")}
               for k, v in actors.items() if k.startswith("e")]
    return {
        "floor": state.get("floor"),
        "room": {"title": room.get("title"), "resolved": room.get("resolved"),
                  "resident": room.get("resident")},
        "party": party,
        "enemies": enemies,
        "combat": ({"round": combat.get("round"), "current": combat.get("current"),
                     "order": combat.get("order"), "complete": combat.get("complete")}
                    if combat else None),
        "gold": state.get("gold"),
        "_raw_state_chars": raw_chars,
    }


def cmd_status(args) -> dict:
    data_root = getattr(args, "data_root", None)
    runs = _runs(data_root)
    runs.load(args.run_id)
    result = runs.design_action(args.run_id, {"type": "inspect"})
    return {"ok": True, "run_id": args.run_id, "state": _compact_state(result["state"])}


def cmd_act(args) -> dict:
    data_root = getattr(args, "data_root", None)
    runs = _runs(data_root)
    runs.load(args.run_id)
    action = {"type": args.type}
    if args.actor: action["actor"] = args.actor
    if args.target: action["target"] = args.target
    result = runs.design_action(args.run_id, action)
    event = result.get("event", result)
    event_size = _guarded_size(event)
    if event_size > MAX_RAW_STATE_CHARS:
        raise StateTooLargeError(event_size)
    ev_summary = {k: event[k] for k in ("type", "check", "damage") if k in event}
    status = cmd_status(argparse.Namespace(run_id=args.run_id, data_root=data_root))
    return {"ok": True, "run_id": args.run_id, "action": action,
            "event": ev_summary or {"type": event.get("type")}, "state": status["state"]}


def cmd_newrun(args) -> dict:
    data_root = getattr(args, "data_root", None)
    run_root, profile_root = get_paths(data_root)
    build = {"name": args.name or f"{args.race.title()} {args.klass.title()}",
              "creation_seed": args.seed or args.run_id, "race": args.race,
              "character_class": args.klass, "level": args.level,
              "background": args.background}
    profile = preview(build)["profile"]
    profiles = ProfileService(profile_root)
    slug = args.run_id + "-pc"
    if not (profile_root / f"{slug}.json").exists():
        profiles.save(slug, profile, replace=False)

    runs = _runs(data_root)
    run_path = run_root / f"{args.run_id}.json"
    if run_path.exists():
        return {"ok": False, "error": f"run already exists: {args.run_id}"}

    summary = runs.create(
        args.run_id, party=[f"custom:{slug}"], opposition=[args.opposition],
        seed=args.seed or args.run_id, module_id=args.module, scenario="reliquary",
        run_mode="SANDBOX",
    )
    started = runs.design_start(args.run_id)
    status = cmd_status(argparse.Namespace(run_id=args.run_id, data_root=data_root))
    return {"ok": True, "run_id": args.run_id,
            "build": {"race": profile.get("race_id"), "class": profile.get("class_id"),
                       "level": profile.get("level"), "max_hp": profile.get("max_hp"),
                       "ac": profile.get("armor_class")},
            "event": {"type": started.get("event", {}).get("type")},
            "state": status["state"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", default=None, help="Root folder for .local data (containing reliquary_runs/profiles)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-root", default=argparse.SUPPRESS, help="Root folder for .local data (containing reliquary_runs/profiles)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("newrun", parents=[common])
    p_new.add_argument("run_id")
    p_new.add_argument("--race", default="human")
    p_new.add_argument("--class", dest="klass", default="warrior")
    p_new.add_argument("--level", type=int, default=1)
    p_new.add_argument("--background", default="veteran")
    p_new.add_argument("--name")
    p_new.add_argument("--seed")
    p_new.add_argument("--module", default="reliquary-template")
    p_new.add_argument("--opposition", default="Townsperson")

    p_act = sub.add_parser("act", parents=[common])
    p_act.add_argument("run_id")
    p_act.add_argument("--type", required=True)
    p_act.add_argument("--actor")
    p_act.add_argument("--target")

    p_status = sub.add_parser("status", parents=[common])
    p_status.add_argument("run_id")

    args = p.parse_args()
    fn = {"newrun": cmd_newrun, "act": cmd_act, "status": cmd_status}[args.cmd]
    try:
        out = fn(args)
    except StateTooLargeError as exc:
        out = {"ok": False, "run_id": getattr(args, "run_id", None),
               "error": "STATE_TOO_LARGE", "raw_chars": exc.raw_chars,
               "limit": MAX_RAW_STATE_CHARS,
               "message": "engine state exceeded the hard size guard; refusing to "
                           "summarize it to avoid a huge token-costing dump. "
                           "Investigate on-disk state directly before continuing."}
    except Exception as exc:
        out = {"ok": False, "run_id": getattr(args, "run_id", None),
               "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(out, default=str, separators=(",", ":")))


if __name__ == "__main__":
    main()
