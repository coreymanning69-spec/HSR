"""HSR local MCP server -- a native, always-native access route into HSRHost.

Speaks the Model Context Protocol (stdio transport: newline-delimited JSON-RPC
2.0) directly, using only the standard library -- no `mcp` pip package, no
new dependency, same "pure Python" posture as the rest of this engine. It is a
thin adapter, exactly like hsr_bridge_watch.py: it does no dice/rules math of
its own, and only ever calls into the existing HSRHost. Every tool result
carries the host's own structured JSON verbatim, so narrate only what comes
back -- never invent rolls, hidden state, or divine dialogue.

Why this exists (vs. the phone_bridge JSONL mailbox)
------------------------------------------------------
hsr_bridge_watch.py is a polling mailbox: a client appends to inbox.jsonl and
waits, at 0.12-second granularity (the watcher's host update interval), for a
matching line in outbox.jsonl. That
works, but only while somebody remembers to double-click the watcher first,
and it never gives an MCP client (Claude Desktop, or any MCP-aware Codex
build) a first-class tool-call surface.

This process, once registered as a local MCP server with a client that runs
ON THIS DESKTOP, is spawned by that client as a native Windows subprocess --
so it inherits the real workspace path and clears HSRHost's own location
gate the same way a native Codex or Claude Code session does. A bridged
Cowork session cannot pass that gate (confirmed: its mounted view of this
folder does not match `C:/Users/ACore/OneDrive/Desktop/...`), so this
server is only useful once it is actually registered as a LOCAL server on
this machine -- see "Registering it" below. Nothing about that registration
step can be done from a bridged session; it has to happen here, natively.

Run it directly to sanity-check framing (no MCP client needed):

    python hsr_mcp_server.py < some_test_input.jsonl

Registering it
--------------
Exactly how a client registers a local MCP server varies by client and by
version, so this file does not try to auto-install itself anywhere. In
general terms: point the client's local-MCP-server configuration at

    <bundled-or-system-python> "<this folder>/hsr_mcp_server.py"

with the working directory left as this folder (the launcher is
path-independent regardless, exactly like hollowstar_host.py). Use
hsr_mcp_server.bat to get the same Codex-bundled-Python-first,
py.exe-fallback resolution the other launchers here already use.

Tool surface
------------
A handful of ergonomic tools cover the documented, stable commands
(health, boot, validate, design_turn, readout, the validation_* async job
trio). Everything else -- checkpoint, profiles, character building, content
catalog, sandbox/forge probes, and anything the host grows later -- goes
through `hsr_command`, a direct passthrough to HSRHost.handle() that mirrors
the existing JSON-lines contract exactly. Call
`hsr_command(command="inspect", params={"target": "capabilities"})` to read
the host's own live command list rather than trusting a hardcoded copy of
it here -- the same "derive it, never copy it" rule this workspace already
holds for corpus numbers.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

HSR_ROOT = Path(__file__).resolve().parent
if str(HSR_ROOT) not in sys.path:
    sys.path.insert(0, str(HSR_ROOT))

from hollowstar import __version__ as ENGINE_VERSION  # noqa: E402
from hollowstar.host import HSRHost  # noqa: E402
from hollowstar.transfer import capsule  # noqa: E402

SERVER_NAME = "hollow-star-reliquary"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"


# --------------------------------------------------------------------------
# HSRHost bridging
# --------------------------------------------------------------------------

class HostUnavailable(RuntimeError):
    pass


def _load_host() -> HSRHost:
    try:
        if os.environ.get("HSR_HOSTED_URL"):
            from hollowstar.web_transport import HostedWebHost
            return HostedWebHost(os.environ["HSR_HOSTED_URL"], os.environ.get("HSR_HOSTED_CLIENT", ""), os.environ.get("HSR_HOSTED_TOKEN", ""))
        if os.environ.get("HSR_WEB_URL"):
            from hollowstar.web_transport import WebHost
            return WebHost(os.environ["HSR_WEB_URL"])
        return HSRHost.from_options()
    except Exception as exc:  # noqa: BLE001 - report, never crash the process
        raise HostUnavailable(f"{type(exc).__name__}: {exc}") from exc


class Bridge:
    """Owns the one long-lived HSRHost instance for this process's life."""

    def __init__(self) -> None:
        self._host: HSRHost | None = None
        self._init_error: str | None = None
        self._call_counter = 0
        try:
            self._host = _load_host()
        except HostUnavailable as exc:
            self._init_error = str(exc)

    def _next_id(self, prefix: str) -> str:
        self._call_counter += 1
        return f"mcp-{prefix}-{self._call_counter}"

    def call(self, command: str, fields: dict[str, Any]) -> dict:
        if self._host is None:
            return {
                "id": self._next_id(command),
                "ok": False,
                "type": "error",
                "command": command,
                "error": {
                    "code": "HOST_INIT_FAILED",
                    "message": self._init_error or "HSRHost failed to initialize",
                },
            }
        fields = dict(fields)
        compact = bool(fields.pop("compact", command in {"design_turn", "readout"}))
        request = {"id": self._next_id(command), "command": command, **fields}
        try:
            result = self._host.handle(request)
            if compact and result.get("ok") and command in {"design_turn", "readout"}:
                return capsule(result, request=request)
            return result
        except Exception as exc:  # noqa: BLE001 - always answer, never die silently
            return {
                "id": request["id"],
                "ok": False,
                "type": "error",
                "command": command,
                "error": {"code": "BRIDGE_EXCEPTION", "message": f"{type(exc).__name__}: {exc}"},
            }


# --------------------------------------------------------------------------
# Tool definitions -- name, description, JSON Schema, and a fields-builder
# --------------------------------------------------------------------------

def _fields(*keys: str) -> Callable[[dict], dict]:
    """Build a fields-extractor that copies only the given keys when present."""

    def extract(args: dict) -> dict:
        return {k: args[k] for k in keys if k in args}

    return extract


TOOLS: list[dict] = [
    {
        "name": "hsr_health",
        "description": (
            "Check the HSR host process is alive and report whether this "
            "process is running from an approved local desktop location "
            "(local_location.approved). Always safe to call; never blocked."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "command": "health",
        "fields": lambda args: {},
    },
    {
        "name": "hsr_boot",
        "description": (
            "Boot the host into a mode (DESIGN, REVIEW, SANDBOX, or FORGE). "
            "SANDBOX requires current 6/6 evidence and remains isolated "
            "non-canon play. FORGE additionally requires an explicit `intent` "
            "and an authored entry fixture."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["DESIGN", "REVIEW", "SANDBOX", "FORGE"], "default": "DESIGN"},
                "intent": {"type": "string", "description": "Required (non-empty) only when mode is FORGE."},
            },
            "additionalProperties": False,
        },
        "command": "boot",
        "fields": _fields("mode", "intent"),
    },
    {
        "name": "hsr_validate",
        "description": (
            "Read-only validation of one target: all, paths, snapshot, "
            "location, handshake, or content. Use this before trusting "
            "certification or snapshot state."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["all", "paths", "snapshot", "location", "handshake", "content"],
                    "default": "all",
                },
            },
            "additionalProperties": False,
        },
        "command": "validate",
        "fields": _fields("target"),
    },
    {
        "name": "hsr_design_turn",
        "description": (
            "Submit one player-conversational turn for an existing run: "
            "translate Corey's spoken intent into a single structured "
            "action when one is supplied, or let the host translate and "
            "validate the intent deterministically. Returns only "
            "narrator-safe visible state -- never invent what isn't in the "
            "response. Requires DESIGN to already be booted and the run to "
            "already exist (see hsr_command with command=create_run)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "intent": {"type": "string", "description": "The player's spoken/typed intent, verbatim or lightly cleaned up."},
                "action": {
                    "type": "object",
                    "description": "The structured action this intent resolves to, e.g. {\"type\": \"investigate\", \"actor\": \"p0\"}.",
                },
                "public_only": {"type": "boolean", "default": False, "description": "Omit the redundant visible_state payload and return the narrator-safe public projection."},
                "compact": {"type": "boolean", "default": True, "description": "Return the bounded transfer capsule instead of the full host envelope."},
            },
            "required": ["run_id", "intent"],
            "additionalProperties": False,
        },
        "command": "design_turn",
        "fields": _fields("run_id", "intent", "action", "public_only", "compact"),
    },
    {
        "name": "hsr_session_intent",
        "description": (
            "Translate a session-level natural-language request such as "
            "start the game, load a run, show equipment, or enable auto "
            "into the shared HSR session envelope. This parse is read-only; "
            "the calling adapter performs any required follow-up command."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"intent": {"type": "string"}},
            "required": ["intent"],
            "additionalProperties": False,
        },
        "command": "session_intent",
        "fields": _fields("intent"),
    },
    {
        "name": "hsr_readout",
        "description": (
            "Fresh phone-sized visible-state refresh for a run after a "
            "reconnect. Never advances the run -- read-only."
        ),
            "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "identity": {"type": "string", "description": "Optional persistent progression identity, such as divine:Wren."},
                "public_only": {"type": "boolean", "default": False, "description": "Omit the redundant visible_state payload and return the narrator-safe public projection."},
                "compact": {"type": "boolean", "default": True, "description": "Return the bounded transfer capsule instead of the full host envelope."},
            },
            "required": ["run_id"],
            "additionalProperties": False,
        },
        "command": "readout",
        "fields": _fields("run_id", "identity", "public_only", "compact"),
    },
    {
        "name": "hsr_validation_start",
        "description": (
            "Start one asynchronous full validation/rehearsal job on the "
            "local PC. Returns a job_id immediately; poll with "
            "hsr_validation_status, then fetch hsr_validation_result once "
            "status is completed or failed. Do not replay unchanged logs -- "
            "poll at 30-60 second intervals."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "command": "validation_start",
        "fields": lambda args: {},
    },
    {
        "name": "hsr_validation_status",
        "description": "Compact status for a validation job started by hsr_validation_start.",
        "inputSchema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
            "additionalProperties": False,
        },
        "command": "validation_status",
        "fields": _fields("job_id"),
    },
    {
        "name": "hsr_validation_result",
        "description": (
            "Compact final receipt for a completed/failed validation job -- "
            "status, exit code, duration, and final stage summaries only. "
            "Raw logs stay in validation_jobs/ on disk."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
            "additionalProperties": False,
        },
        "command": "validation_result",
        "fields": _fields("job_id"),
    },
    {
        "name": "hsr_meta_shop",
        "description": (
            "Read the account Meta Shop: every permanent upgrade track "
            "(precision, force, ward, reserve, mastery_capacity, and the "
            "prefix/suffix/legendary Attunement capacity tracks) with its "
            "tier, cap, and next Platinum cost. Read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"identity": {"type": "string", "description": "Progression identity, e.g. divine:Doran."}},
            "required": ["identity"],
            "additionalProperties": False,
        },
        "command": "meta_shop",
        "fields": _fields("identity"),
    },
    {
        "name": "hsr_meta_shop_purchase",
        "description": (
            "Buy one tier of a Meta Shop track with banked Platinum. Cost is "
            "base_cost x (tier + 1); a capped track or short balance fails "
            "closed and nothing is spent."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "identity": {"type": "string"},
                "upgrade": {"type": "string", "description": "Track key from hsr_meta_shop, e.g. prefix_capacity."},
            },
            "required": ["identity", "upgrade"],
            "additionalProperties": False,
        },
        "command": "meta_shop_purchase",
        "fields": _fields("identity", "upgrade"),
    },
    {
        "name": "hsr_decant_item",
        "description": (
            "Decant (devour) one identified Imprint, relic, or legendary item "
            "outside combat: the item is destroyed and its Prefix, Suffix, "
            "and legendary power move into the actor's Attunement Matrix. "
            "When a lane is full, name the attuned power to `replace`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "item": {"type": "string", "description": "Inventory item id, e.g. item-3."},
                "actor": {"type": "string", "default": "p0"},
                "replace": {"description": "Attuned power name (or {lane: name}) to overwrite when full."},
            },
            "required": ["run_id", "item"],
            "additionalProperties": False,
        },
        "command": "decant",
        "fields": _fields("run_id", "item", "actor", "replace"),
    },
    {
        "name": "hsr_contextual_action",
        "description": (
            "Submit one contextual combat action: dodge, dash, disengage, "
            "shove, trip, grapple, escape_grapple, help, stand, or any other "
            "action type. Read public_view.combat.contextual_actions from "
            "hsr_readout first: it lists what is legal now, with help text "
            "and legal target ids."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "action": {"type": "object", "description": "e.g. {\"type\": \"shove\", \"actor\": \"p0\", \"target\": \"e0\", \"mode\": \"prone\"}"},
                "intent": {"type": "string", "description": "Optional player phrasing; defaults to the action type."},
            },
            "required": ["run_id", "action"],
            "additionalProperties": False,
        },
        "command": "design_turn",
        "fields": lambda args: {"run_id": args.get("run_id"), "action": args.get("action"),
                                "intent": args.get("intent") or str((args.get("action") or {}).get("type") or "act"),
                                "public_only": True},
    },
    {
        "name": "hsr_configure_gambits",
        "description": (
            "Replace the run's Gambit (Macro) lists: {actor_id: [{priority, "
            "when: {...}, then: {type, target, ...}}]}. Conditions include "
            "self/ally/enemy_hp_below/above, round_number_gte/lte, "
            "cocoon_rounds_gte/lte, has_resource, enemy_casting, "
            "enemy_status, self_status, enemy_count_gte, enemy_adjacent, "
            "spell_ready (spell id or list), self_concentrating (bool), and "
            "forecast conditions judged on the resolved then-action: "
            "hit_chance_gte and kill_chance_gte (percent), expected_damage_gte "
            "(points). Target selectors: self, lowest_hp_ally, lowest_hp_enemy, "
            "highest_hp_enemy, nearest_enemy, casting_enemy, adjacent_enemy, "
            "killable_enemy, likeliest_hit_enemy, most_damage_enemy; an area "
            "spell's center may name a selector. then {type: 'plan', goal: "
            "'damage'|'kill'|'heal', spend: bool} lets the planner pick the "
            "action. Party forecasts use only what the party has observed. "
            "Unknown condition keys fail closed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}, "macros": {"type": "object"}},
            "required": ["run_id", "macros"],
            "additionalProperties": False,
        },
        "command": "design_action",
        "fields": lambda args: {"run_id": args.get("run_id"),
                                "action": {"type": "configure_macros", "macros": args.get("macros")}},
    },
    {
        "name": "hsr_expedition",
        "description": (
            "Encounters expedition over the dungeon route. step=start builds the "
            "seeded node map; choose enters `node` resolved by mode arcade, "
            "tactical or auto (gambits); auto is the AFK loop for up to "
            "`max_nodes` nodes, pausing below `retreat_below` party health; "
            "resolve auto-finishes the current room; view is read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "step": {"type": "string", "enum": ["start", "choose", "auto", "resolve", "view"]},
                "node": {"type": "string"},
                "mode": {"type": "string", "enum": ["arcade", "tactical", "auto"]},
                "max_nodes": {"type": "integer", "minimum": 1, "maximum": 6},
                "retreat_below": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["run_id", "step"],
            "additionalProperties": False,
        },
        "command": "design_action",
        "fields": lambda args: {"run_id": args.get("run_id"), "action": {
            "type": f"expedition_{args.get('step')}",
            **{key: args[key] for key in ("node", "mode", "max_nodes", "retreat_below") if key in args}}},
    },
    {
        "name": "hsr_examine",
        "description": (
            "Examine one visible entity (actor, target/enemy, item, object, or text query) "
            "and return its read-only public explanation, lore, stats, and condition breakdown."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "query": {"type": "string", "description": "Name or query string of the target to examine."},
                "entity_type": {"type": "string", "enum": ["actor", "target", "item", "object", "result"]},
                "entity_id": {"type": "string", "description": "Specific entity identifier if known."},
            },
            "required": ["run_id"],
            "additionalProperties": False,
        },
        "command": "examine",
        "fields": _fields("run_id", "query", "entity_type", "entity_id"),
    },
    {
        "name": "hsr_create_run",
        "description": "Create and initialize a new Story or Simulation run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "Unique identifier for the new run."},
                "mode": {"type": "string", "enum": ["SANDBOX", "FORGE"], "default": "SANDBOX"},
                "party": {"type": "array", "items": {"type": "string"}, "description": "Party member names or profiles."},
                "lead": {"type": "string", "description": "Name of the lead character."},
            },
            "required": ["run_id"],
            "additionalProperties": False,
        },
        "command": "create_run",
        "fields": _fields("run_id", "mode", "party", "lead"),
    },
    {
        "name": "hsr_load_run",
        "description": "Load an active or saved run into the host session context.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
            "additionalProperties": False,
        },
        "command": "load_run",
        "fields": _fields("run_id"),
    },
    {
        "name": "hsr_save_run",
        "description": "Persist the current state of a run to disk.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
            "additionalProperties": False,
        },
        "command": "save_run",
        "fields": _fields("run_id"),
    },
    {
        "name": "hsr_action",
        "description": "Submit a structured gameplay action (attack, move, search_object, open_object, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "action": {"type": "object", "description": "Structured action dictionary."},
            },
            "required": ["run_id", "action"],
            "additionalProperties": False,
        },
        "command": "design_action",
        "fields": _fields("run_id", "action"),
    },
    {
        "name": "hsr_command",
        "description": (
            "Direct passthrough to HSRHost.handle() for any command not "
            "covered by a dedicated tool above -- e.g. create_run, "
            "load_run, list_runs, inspect_run, save_run, create_profile, "
            "update_profile, list_profiles, inspect_profile, list_roster, "
            "character_options, build_character, content_catalog, "
            "spell_catalog, checkpoint, bank_checkpoint, resume_checkpoint, "
            "terminal_receipt, progression, settle_run, upgrade, inspect, "
            "inspect_modules, status, shutdown, and the available mode-scoped "
            "sandbox_*/forge_* commands. `params` is merged directly "
            "into the request alongside `command`. Call "
            "command=\"inspect\", params={\"target\": \"capabilities\"} to "
            "read the host's live command list."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "params": {"type": "object", "description": "Extra request fields, merged in as-is."},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
        "command": None,  # resolved dynamically from arguments
        "fields": None,
    },
]

for _name, _command, _description, _properties in (
    ("hsr_probe_effect", "packet_effect_probe", "Probe a package effect by ID and elapsed phase units; does not apply gameplay changes.", {"package": {"type": "object"}, "effect_id": {"type": "string"}, "elapsed": {"type": "number", "minimum": 0}}),
    ("hsr_probe_run_effect", "packet_run_effect_probe", "Probe package potency using a run's clock counter minus since. Read-only; no tick, save, or gameplay changes.", {"package": {"type": "object"}, "effect_id": {"type": "string"}, "run_id": {"type": "string"}, "since": {"type": "integer", "minimum": 0}}),
    ("hsr_compile_package", "packet_compile", "Validate and fingerprint a Workbench runtime draft; does not publish or change a run.", {"package": {"type": "object"}}),
    ("hsr_runtime_schema", "packet_runtime_schema", "Inspect the Workbench runtime package JSON Schema.", {}),
    ("hsr_validate_rule", "packet_rule_validate", "Check a generated rule manifest, source hash and restricted Python syntax.", {"binding": {"type": "object"}}),
    ("hsr_probe_rule", "packet_rule_probe", "Probe a numeric generated rule twice in bounded workers; never changes game state.", {"binding": {"type": "object"}, "inputs": {"type": "object"}}),
):
    TOOLS.append({"name": _name, "command": _command, "description": _description,
                  "inputSchema": {"type": "object", "properties": _properties,
                                  "required": list(_properties), "additionalProperties": False},
                  "fields": _fields(*_properties)})

TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}


def _run_tool(bridge: Bridge, name: str, arguments: dict) -> dict:
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        raise KeyError(f"unknown tool: {name}")
    if name == "hsr_command":
        command = arguments.get("command")
        if not isinstance(command, str) or not command:
            return {
                "id": "mcp-invalid",
                "ok": False,
                "type": "error",
                "command": None,
                "error": {"code": "INVALID_REQUEST", "message": "hsr_command requires a non-empty 'command' string"},
            }
        params = arguments.get("params") or {}
        if not isinstance(params, dict):
            return {
                "id": "mcp-invalid",
                "ok": False,
                "type": "error",
                "command": command,
                "error": {"code": "INVALID_REQUEST", "message": "'params' must be an object"},
            }
        return bridge.call(command, params)
    fields = tool["fields"](arguments)
    return bridge.call(tool["command"], fields)


# --------------------------------------------------------------------------
# Minimal MCP-over-stdio (JSON-RPC 2.0, newline-delimited) -- stdlib only
# --------------------------------------------------------------------------

def _rpc_result(msg_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _rpc_error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _tool_call_result(payload: dict) -> dict:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
    return {"content": [{"type": "text", "text": text}], "isError": not bool(payload.get("ok"))}


def _log(message: str) -> None:
    print(f"[hsr_mcp_server] {message}", file=sys.stderr, flush=True)


def serve(input_stream=None, output_stream=None) -> int:
    src = input_stream or sys.stdin
    dst = output_stream or sys.stdout
    bridge = Bridge()
    if bridge._init_error:  # noqa: SLF001 - internal, logged once at startup only
        _log(f"HSRHost failed to initialize: {bridge._init_error}")
        _log("tools/list will still work; every tool call will report HOST_INIT_FAILED "
             "until this is fixed (usually: launched from the wrong working directory).")

    for raw_line in src:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            message = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            _log(f"skipping malformed JSON-RPC line: {exc}")
            continue
        if not isinstance(message, dict):
            _log("skipping non-object JSON-RPC message")
            continue

        method = message.get("method")
        has_id = "id" in message
        msg_id = message.get("id")
        params = message.get("params") or {}

        if method is None:
            # A bare response/result with no method isn't expected on this
            # side of the conversation; ignore rather than crash.
            continue

        try:
            if method == "initialize":
                requested = params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION
                result = {
                    "protocolVersion": requested,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "_engineVersion": ENGINE_VERSION,
                }
                if has_id:
                    dst.write(json.dumps(_rpc_result(msg_id, result)) + "\n")
                    dst.flush()
                continue

            if method in ("notifications/initialized", "notifications/cancelled", "exit"):
                continue  # no response for notifications

            if method == "ping":
                if has_id:
                    dst.write(json.dumps(_rpc_result(msg_id, {})) + "\n")
                    dst.flush()
                continue

            if method == "shutdown":
                if has_id:
                    dst.write(json.dumps(_rpc_result(msg_id, {})) + "\n")
                    dst.flush()
                continue

            if method in ("resources/list", "prompts/list"):
                key = method.split("/")[0]
                if has_id:
                    dst.write(json.dumps(_rpc_result(msg_id, {key: []})) + "\n")
                    dst.flush()
                continue

            if method == "tools/list":
                listed = [
                    {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
                    for t in TOOLS
                ]
                if has_id:
                    dst.write(json.dumps(_rpc_result(msg_id, {"tools": listed})) + "\n")
                    dst.flush()
                continue

            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if not isinstance(name, str) or name not in TOOLS_BY_NAME:
                    if has_id:
                        dst.write(json.dumps(_rpc_error(msg_id, -32602, f"unknown tool: {name!r}")) + "\n")
                        dst.flush()
                    continue
                if not isinstance(arguments, dict):
                    if has_id:
                        dst.write(json.dumps(_rpc_error(msg_id, -32602, "'arguments' must be an object")) + "\n")
                        dst.flush()
                    continue
                payload = _run_tool(bridge, name, arguments)
                if has_id:
                    dst.write(json.dumps(_rpc_result(msg_id, _tool_call_result(payload))) + "\n")
                    dst.flush()
                continue

            # Unknown method
            if has_id:
                dst.write(json.dumps(_rpc_error(msg_id, -32601, f"method not found: {method}")) + "\n")
                dst.flush()
        except Exception as exc:  # noqa: BLE001 - never let one bad message kill the process
            _log(f"unhandled exception on method={method!r}: {exc}\n{traceback.format_exc()}")
            if has_id:
                dst.write(json.dumps(_rpc_error(msg_id, -32603, f"internal error: {type(exc).__name__}: {exc}")) + "\n")
                dst.flush()

    return 0


def main() -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
