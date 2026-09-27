"""Command-line entrypoint for the local HSR host."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from hollowstar.host import HSRHost
from hollowstar.protocol import run_stdio, write_response


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hollow Star local host")
    parser.add_argument("command", nargs="?", choices=[
        "health", "ready", "boot", "validate", "local-check", "status", "inspect",
        "readout", "session-intent", "shutdown", "conversation", "npc_list",
        "prepare_idle", "auto_battle", "salvage", "trade", "buy",
        "acquire_weapon", "acquire_armor", "imprint_rune", "content_catalog", "affix_catalog", "scenario_catalog",
        "create_run", "load_run", "list_runs", "design_start", "design_action",
        "design_turn", "submit-action",
        "examine", "party_status", "character_options", "preview_character", "build_character",
        "save_run", "inspect_run", "meta_shop", "interactive", "cli",
    ])
    parser.add_argument("--stdio", action="store_true", help="serve JSON-lines requests on stdin/stdout")
    parser.add_argument("--mode", default="DESIGN", help="mode for boot, such as DESIGN, SANDBOX, or FORGE")
    parser.add_argument("--target", default="all", help="validation or inspection target")
    parser.add_argument("--workspace", type=Path, help="Court workspace root")
    parser.add_argument("--data-root", type=Path, help="override disposable local data root")
    parser.add_argument("--config", type=Path, help="host_config.json override")
    parser.add_argument("--intent", help="natural-language session intent for session-intent")
    parser.add_argument("--run-id", help="run identifier for readout")
    parser.add_argument("--item", help="inventory item id for salvage, trade, or rune imprint")
    parser.add_argument("--product", help="shop product for buy actions")
    parser.add_argument("--actor", default="p0", help="actor id for an action hook")
    parser.add_argument("--strategy", default="safe", help="idle/auto battle strategy")
    parser.add_argument("--identity", help="persistent progression identity for readout")
    parser.add_argument("--public-only", action="store_true", help="omit redundant visible state from readout")
    parser.add_argument("--query", help="entity query or name for examine")
    parser.add_argument("--entity-type", help="entity type for examine (actor, target, item, object)")
    parser.add_argument("--entity-id", help="entity id for examine")
    parser.add_argument("--web-url", help="route through the running loopback webhost and watcher")
    parser.add_argument("--hosted-url", help="route through the authenticated Hosted Controls relay")
    parser.add_argument("--hosted-client", choices=["claude", "gpt"], help="Hosted Controls client identity")
    parser.add_argument("--hosted-token", help="Hosted Controls token (prefer HSR_HOSTED_TOKEN)")
    parser.add_argument("--request", help="one host request as a JSON object (all host commands)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.hosted_url:
            if args.workspace or args.data_root or args.config or not args.hosted_client:
                raise ValueError("hosted transport requires --hosted-client and uses the running server workspace")
            from hollowstar.web_transport import HostedWebHost
            host = HostedWebHost(args.hosted_url, args.hosted_client, args.hosted_token or os.environ.get("HSR_HOSTED_TOKEN", ""))
        elif args.web_url:
            if args.workspace or args.data_root or args.config:
                raise ValueError("web transport uses the running server workspace and configuration")
            from hollowstar.web_transport import WebHost
            host = WebHost(args.web_url)
        else:
            host = HSRHost.from_options(args.workspace, args.data_root, args.config)
    except Exception as exc:
        print(f"HSR host configuration error: {exc}", file=sys.stderr)
        return 2

    if args.stdio:
        return run_stdio(host)

    command = args.command or "health"
    if command in {"interactive", "cli"}:
        return run_interactive(host, run_id=args.run_id, mode=args.mode)

    request = {"id": "cli-1", "command": command}
    if command == "boot":
        request["mode"] = args.mode
    if command == "validate":
        request["target"] = args.target
    if command == "inspect":
        request["target"] = args.target if args.target != "all" else "capabilities"
    if command == "session-intent":
        request["command"] = "session_intent"
        request["intent"] = args.intent or ""
    if command in {"readout", "party_status", "save_run", "inspect_run"}:
        request["run_id"] = args.run_id
        if args.public_only:
            request["public_only"] = True
        if args.identity:
            request["identity"] = args.identity
    if command == "examine":
        request["run_id"] = args.run_id
        if args.query:
            request["query"] = args.query
        if args.entity_type:
            request["entity_type"] = args.entity_type
        if args.entity_id:
            request["entity_id"] = args.entity_id
    if command == "meta_shop":
        if args.identity:
            request["identity"] = args.identity
    if command in {"conversation", "npc_list", "prepare_idle", "auto_battle", "salvage",
                   "trade", "buy", "acquire_weapon", "acquire_armor", "imprint_rune"}:
        request.update({"run_id": args.run_id, "actor": args.actor, "item": args.item,
                        "strategy": args.strategy, "product": args.product})
        if command == "conversation":
            request["target"] = args.target if args.target != "all" else "resident"
    if args.request:
        try:
            request = json.loads(args.request)
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
            request.setdefault("id", "cli-1")
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    try:
        payload = host.handle(request)
    except Exception as exc:  # pragma: no cover - final CLI guard
        print(f"HSR host error: {exc}", file=sys.stderr)
        return 1
    write_response(payload, sys.stdout)
    return 0 if payload.get("ok") else 1


def run_interactive(host: HSRHost, run_id: str | None = None, mode: str = "SANDBOX") -> int:
    """Run an interactive playthrough session directly in the terminal."""
    import time
    boot_res = host.handle({"id": "cli-boot", "command": "boot", "mode": mode})
    if not boot_res.get("ok"):
        print(f"Failed to boot {mode}: {boot_res.get('error')}", file=sys.stderr)
        return 1

    active_run_id = run_id
    if not active_run_id:
        list_res = host.handle({"id": "cli-list", "command": "list_runs"})
        runs = list_res.get("result", {}).get("runs", [])
        print("\n" + "=" * 65)
        print("         H O L L O W   S T A R   R E L I Q U A R Y")
        print(f"              Interactive CLI Playthrough [{mode}]")
        print("=" * 65)
        if runs:
            print("Existing runs:")
            for r in runs[:5]:
                r_id = r if isinstance(r, str) else r.get("run_id", "unknown")
                lead = r.get("lead") or (r.get("party") or [{}])[0].get("name", "hero") if isinstance(r, dict) else "run"
                print(f"  [{r_id}] {lead}")
            prompt_text = "Enter run ID to load, or press [Enter] to start new run: "
        else:
            prompt_text = "Press [Enter] to start a new run with Doran: "

        try:
            choice = input(prompt_text).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return 0

        run_ids = [r if isinstance(r, str) else r.get("run_id") for r in runs]
        if choice and choice in run_ids:
            active_run_id = choice
        else:
            active_run_id = f"cli-{int(time.time())}"
            create_res = host.handle({
                "id": "cli-create",
                "command": "create_run",
                "run_id": active_run_id,
                "mode": mode,
                "party": ["Doran"],
            })
            if not create_res.get("ok"):
                print(f"Could not create run: {create_res.get('error')}", file=sys.stderr)
                return 1
            host.handle({"id": "cli-start", "command": "design_start", "run_id": active_run_id})

    # Ensure run is loaded
    load_res = host.handle({"id": "cli-load", "command": "load_run", "run_id": active_run_id})
    if not load_res.get("ok"):
        print(f"Could not load run {active_run_id}: {load_res.get('error')}", file=sys.stderr)
        return 1

    print(f"\n[Run '{active_run_id}' loaded and active.]")
    print("Type 'help' for command list, or type actions in natural language ('look', 'attack', 'examine', etc.).\n")

    def _show_room(public_view: dict) -> None:
        room = public_view.get("room") or {}
        descent = public_view.get("descent") or {}
        party = public_view.get("party") or []
        opposition = public_view.get("opposition") or []
        narration = public_view.get("narration") or ""

        floor_str = f"Floor {descent.get('floor', 1)}/{descent.get('floors_total', 1)}"
        room_str = f"Room {descent.get('room', 1)}/{descent.get('rooms_on_floor', 1)}"
        room_name = room.get("name") or room.get("id") or "The Reliquary"
        print("-" * 65)
        print(f"[{floor_str} · {room_str}] {room_name}")
        desc = room.get("description") or room.get("atmosphere") or narration
        if desc:
            print(f"  {desc}")
        exits = room.get("exits")
        if exits:
            if isinstance(exits, dict):
                exits_str = ", ".join(f"{k}: {v}" for k, v in exits.items())
            else:
                exits_str = ", ".join(str(e) for e in exits)
            print(f"  Exits: {exits_str}")
        objs = room.get("objects")
        if objs:
            if isinstance(objs, dict):
                obj_names = [o.get("name", k) for k, o in objs.items() if isinstance(o, dict)]
            else:
                obj_names = [str(o) for o in objs]
            print(f"  Objects: {', '.join(obj_names)}")
        print("  Party:")
        for m in party:
            hp = m.get("hp", "?")
            max_hp = m.get("max_hp", "?")
            ac = m.get("armor_class") or m.get("ac", "?")
            statuses = ", ".join(m.get("statuses") or m.get("status") or ["normal"]) if isinstance(m.get("statuses") or m.get("status"), list) else (m.get("status") or "normal")
            print(f"    * {m.get('name', 'Hero')} ({hp}/{max_hp} HP | AC {ac}) [{statuses}]")
        if opposition:
            print("  Opposition:")
            for foe in opposition:
                f_hp = foe.get("hp", "?")
                f_max = foe.get("max_hp", "?")
                f_stat = foe.get("status") or "active"
                print(f"    ! {foe.get('name', 'Enemy')} ({f_hp}/{f_max} HP) [{f_stat}]")
        print("-" * 65)

    rd = host.handle({"id": "cli-rd-init", "command": "readout", "run_id": active_run_id, "public_only": True})
    pv = rd.get("result", {}).get("readout", {}).get("public_view") or rd.get("result", {}).get("public_view") or {}
    _show_room(pv)

    while True:
        room_name = (pv.get("room") or {}).get("name") or "HSR"
        try:
            line = input(f"({room_name}) > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaving and quitting...")
            host.handle({"id": "cli-save", "command": "save_run", "run_id": active_run_id})
            break

        if not line:
            continue

        low = line.lower()
        if low in {"quit", "exit", "q"}:
            host.handle({"id": "cli-save", "command": "save_run", "run_id": active_run_id})
            print("Session saved. Exiting Hollow Star CLI.")
            break

        if low in {"help", "?"}:
            print("\nAvailable Commands:")
            print("  look, l                  - Look at the current room again")
            print("  status, party            - Show party details and HP")
            print("  inventory, inv, i        - View carried items and equipment")
            print("  examine <target>         - Inspect an actor, foe, item, or room object")
            print("  move <exit>, enter <exit>- Move to another room")
            print("  attack <target>, strike  - Attack an enemy in combat")
            print("  search <object>, open <object> - Interact with room objects")
            print("  auto                     - Take automatic step or combat turn")
            print("  save                     - Persist the current run state")
            print("  quit, exit               - Save and exit interactive mode")
            print("  <any other phrase>       - Natural language turn resolution via design_turn\n")
            continue

        if low in {"look", "l"}:
            rd = host.handle({"id": "cli-rd", "command": "readout", "run_id": active_run_id, "public_only": True})
            pv = rd.get("result", {}).get("readout", {}).get("public_view") or {}
            _show_room(pv)
            continue

        if low in {"status", "party"}:
            ps = host.handle({"id": "cli-ps", "command": "party_status", "run_id": active_run_id})
            if ps.get("ok"):
                members = ps.get("result", {}).get("party") or pv.get("party") or []
                for m in members:
                    print(f"  {m.get('name')}: {m.get('hp')}/{m.get('max_hp')} HP, AC {m.get('armor_class') or m.get('ac')}, Level {m.get('level', 1)}")
            else:
                for m in pv.get("party") or []:
                    print(f"  {m.get('name')}: {m.get('hp')}/{m.get('max_hp')} HP, AC {m.get('armor_class') or m.get('ac')}")
            continue

        if low in {"inventory", "inv", "i", "items"}:
            for m in pv.get("party") or []:
                print(f"  [{m.get('name')}] Equipment:")
                for item in m.get("equipment") or []:
                    i_name = item.get("name") if isinstance(item, dict) else str(item)
                    print(f"    - {i_name}")
            continue

        if low.startswith(("examine ", "inspect ", "ex ")):
            parts = line.split(maxsplit=1)
            target = parts[1].strip() if len(parts) > 1 else ""
            ex_res = host.handle({"id": "cli-ex", "command": "examine", "run_id": active_run_id, "query": target})
            if not ex_res.get("ok"):
                found_id = None
                for m in (pv.get("party") or []) + (pv.get("opposition") or []):
                    if target.lower() in m.get("name", "").lower() or target.lower() == m.get("id", "").lower():
                        found_id = m.get("id")
                        break
                if found_id:
                    ex_res = host.handle({"id": "cli-ex", "command": "examine", "run_id": active_run_id, "entity_type": "actor", "entity_id": found_id})
            if ex_res.get("ok"):
                info = ex_res.get("result", {}).get("examine") or {}
                print(f"\n[Examine: {info.get('name', target)}]")
                print(f"  {info.get('short') or info.get('description') or 'No description.'}")
                if info.get("ability_scores"):
                    scores = ", ".join(f"{k}: {v}" for k, v in info["ability_scores"].items())
                    print(f"  Scores: {scores}")
                if info.get("conditions"):
                    print(f"  Conditions: {', '.join(info['conditions'])}")
                print()
            else:
                print(f"Could not examine '{target}': {ex_res.get('error', {}).get('message', 'Not found')}")
            continue

        if low == "save":
            sv = host.handle({"id": "cli-save", "command": "save_run", "run_id": active_run_id})
            print(f"Run saved: {'OK' if sv.get('ok') else sv.get('error')}")
            continue

        if low in {"auto", "step"}:
            cmd = "design_auto_combat" if pv.get("opposition") else "design_auto"
            res = host.handle({"id": "cli-auto", "command": cmd, "run_id": active_run_id})
            if res.get("ok"):
                rd = host.handle({"id": "cli-rd-after", "command": "readout", "run_id": active_run_id, "public_only": True})
                pv = rd.get("result", {}).get("readout", {}).get("public_view") or pv
                _show_room(pv)
            else:
                print(f"Auto action failed: {res.get('error')}")
            continue

        turn_res = host.handle({
            "id": "cli-turn",
            "command": "design_turn",
            "run_id": active_run_id,
            "intent": line,
            "public_only": True,
        })
        if turn_res.get("ok"):
            turn_data = turn_res.get("result", {}).get("turn") or {}
            event = turn_data.get("event") or {}
            narr = turn_data.get("narration") or event.get("message") or event.get("narrative") or "Action resolved."
            print(f"\n>> {narr}\n")
            pv = turn_data.get("public_view") or pv
            if event.get("new_room") or any(k in line.lower() for k in ("descend", "move", "enter")):
                _show_room(pv)
        else:
            err = turn_res.get("error") or {}
            print(f">> Error: {err.get('message', 'Action could not be performed')}")

    return 0
