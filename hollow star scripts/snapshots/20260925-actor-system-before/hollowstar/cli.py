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
    if command == "readout":
        request["run_id"] = args.run_id
        if args.public_only:
            request["public_only"] = True
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
