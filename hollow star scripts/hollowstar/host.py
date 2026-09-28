"""The local HSR host boundary.

The host exposes the same JSON-lines surface for DESIGN, REVIEW, SANDBOX, and
FORGE.  Mode selection changes the write/receipt boundary; it does not fork a
second gameplay API.
"""

from __future__ import annotations

import json
import copy
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from hollowstar import __version__ as ENGINE_VERSION
from hollowstar.world import world_context
from hollowstar.protocol import response
from hollowstar.view_model import narrator_state, public_event_summary, redact_public
from hollowstar.profiles import ProfileError, ProfileService
from hollowstar.run_service import RunService, RunServiceError, runtime_for, validate_launch
from hollowstar.run_history import RunHistory
from hollowstar.run_state import RunStateError
from hollowstar.snapshot import import_party, load_snapshot
from hollowstar.session_intent import parse_session_intent
from hollowstar.view_model import build_public_view
from hollowstar.explanations import examine_view, resolution_explanation
from hollowstar.paths import HostPathError, HostPaths, resolve_paths
from hollowstar.handshake import HandshakeError, verify_handshake, write_handshake
from hollowstar.storage import atomic_json


HOST_VERSION = "0.2.0"
CONVERSATION_CONTRACT_VERSION = "8.76-public-status-1"
SUPPORTED_MODES = {"DESIGN", "SANDBOX", "FORGE", "REVIEW"}
CONTENT_COMMANDS = {
    "packet_effect_probe", "packet_run_effect_probe",
    "packet_compile", "packet_runtime_schema", "packet_rule_probe", "packet_rule_validate",
    "source_search", "source_read", "packet_starter", "packet_interpret", "packet_validate",
    "packet_preview_start", "packet_preview_read", "packet_preview_action",
    "packet_preview_list", "packet_preview_export",
}
RUN_MUTATION_COMMANDS = {
    "create_run", "load_run", "save_run", "start-run", "design_start", "design_action",
    "design_turn", "idle_tick", "auto_travel", "forge_start", "forge_action",
    "sandbox_start", "sandbox_release", "sandbox_action", "sandbox_branch",
    "checkpoint", "bank_checkpoint", "resume_checkpoint", "design_auto", "design_auto_combat",
    "design_drain_npc", "arcade_tick", "arcade_toggle_flight", "arcade_set_movement_mode",
    "expedition_start", "expedition_choose", "expedition_auto", "expedition_resolve",
}
EXPEDITION_COMMANDS = {"expedition_start", "expedition_choose", "expedition_auto",
                       "expedition_resolve", "expedition_view"}


def _public_receipt(event: dict) -> dict:
    """Return the single narrator-facing receipt for an event."""
    if not isinstance(event, dict):
        return {}
    for key in ("receipt", "reward", "purchase", "evidence"):
        value = event.get(key)
        if isinstance(value, dict):
            return redact_public(value)
    return redact_public(event)


def _readout_receipt(visible_state: dict) -> dict | str:
    events = visible_state.get("events") if isinstance(visible_state, dict) else None
    if isinstance(events, list):
        for event in reversed(events):
            if isinstance(event, dict):
                return _public_receipt(event)
    return "readout contains no private debug state"


# Event keys whose nested steps each played on screen: NPC reactions settled
# inside the step, the opposition turns that followed, and a drain's steps.
STEP_RECEIPT_KEYS = ("auto_reactions", "opposition_turns", "steps")


def _step_receipts(event: dict) -> list[dict]:
    """Every nested step an event carries, as compact public receipts, in order.

    view.recent_receipts holds one summary per transition, so the enemy
    turns played inside one transition would otherwise never reach the
    combat director; clients queue these after that summary.
    """
    rows = []
    if not isinstance(event, dict):
        return rows
    for key in STEP_RECEIPT_KEYS:
        steps = event.get(key)
        for step in steps if isinstance(steps, list) else []:
            if isinstance(step, dict):
                summary = public_event_summary(step)
                if summary:
                    rows.append(summary)
    return rows


def _public_outcome(outcome: dict, *, mode: str | None, run_id: str) -> dict:
    """Project a run transition before it crosses the JSON host boundary."""
    if not isinstance(outcome, dict) or not isinstance(outcome.get("state"), dict):
        return outcome
    event = redact_public(outcome.get("event", {}))
    state = redact_public(narrator_state(outcome["state"]))
    projected = {
        **outcome,
        "event": event,
        "state": state,
        "public_view": build_public_view(state, event=event, mode=mode, run_id=run_id),
        "public_receipt": _public_receipt(event),
    }
    receipts = _step_receipts(event)
    if receipts:
        projected["receipts"] = receipts
    return projected


# ---------------------------------------------------------------------------
# Command registry (Open-Closed dispatch for HSRHost.handle)
# ---------------------------------------------------------------------------
# Each handler is an HSRHost method ``(self, request, command) -> dict | None``.
# Adding a command means adding one decorated method; handle() never changes.
CommandHandler = Callable[["HSRHost", dict, str], "dict | None"]
_HANDLERS: dict[str, CommandHandler] = {}


def command_handler(*command_names: str):
    """Register the decorated HSRHost method for each named command."""
    def decorator(fn: CommandHandler) -> CommandHandler:
        for name in command_names:
            if name in _HANDLERS:
                raise RuntimeError(f"duplicate command handler: {name}")
            _HANDLERS[name] = fn
        return fn
    return decorator


@dataclass
class HSRHost:
    paths: HostPaths
    mode: str | None = None
    booted: bool = False
    _run_service: RunService | None = field(default=None, init=False, repr=False)
    _profile_service: ProfileService | None = field(default=None, init=False, repr=False)
    _run_history: RunHistory | None = field(default=None, init=False, repr=False)
    _active_clocks: dict[str, float] = field(default_factory=dict, init=False, repr=False)
    _session_cache: dict | None = field(default=None, init=False, repr=False)


    @classmethod
    def from_options(
        cls,
        workspace_root: Path | str | None = None,
        data_root: Path | str | None = None,
        config_path: Path | str | None = None,
    ) -> "HSRHost":
        return cls(resolve_paths(workspace_root, data_root, config_path))

    def _request_identity(self, request: dict) -> tuple[object, str | None]:
        if "id" not in request:
            raise ValueError("request requires an id")
        command = request.get("command")
        if not isinstance(command, str) or not command:
            raise ValueError("request requires a command")
        return request["id"], command

    def _ok(self, request: dict, result: dict) -> dict:
        request_id, command = self._request_identity(request)
        if command in RUN_MUTATION_COMMANDS:
            self._maintain_runs(request.get("run_id"))
        return response(request_id, command, ok=True, result=result)

    def _error(self, request: dict, code: str, message: str) -> dict:
        request_id = request.get("id")
        command = request.get("command") if isinstance(request.get("command"), str) else None
        return response(request_id, command, ok=False, code=code, message=message)

    def _validate_paths(self) -> dict:
        self.paths.assert_workspace_layout()
        return {
            "workspace_root": str(self.paths.workspace_root),
            "hsr_root": str(self.paths.hsr_root),
            "corpus_root": str(self.paths.corpus_root),
            "content_root": str(self.paths.content_root),
            "snapshot_path": str(self.paths.snapshot_path),
            "handshake_path": str(self.paths.handshake_path),
            "data_root": str(self.paths.data_root),
            "run_root": str(self.paths.run_root),
            "profile_root": str(self.paths.profile_root),
            "config_path": str(self.paths.config_path),
            "rules_profile": self.paths.rules_profile,
            "local_location": self.paths.local_location_report(),
        }

    def _refresh_party_snapshot(self) -> None:
        """Re-derive the party snapshot from current corpus owners.

        The snapshot's cited source hashes go stale the moment DM041_A/A1,
        DM041_B/B1, DM044_0, or DM044_1 is edited; `write_handshake` only
        re-checks those hashes, it never regenerates them. Running the
        exporter here, ahead of every `local-check`, is what makes the
        scheduled and watcher-triggered refreshes self-healing instead of
        merely detecting the drift and failing again tomorrow.
        """

        exporter = self.paths.hsr_root / "tools" / "export_party_snapshot.py"
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(exporter),
                    "--corpus",
                    str(self.paths.corpus_root),
                    "--out",
                    str(self.paths.snapshot_path),
                ],
                cwd=self.paths.hsr_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            raise HandshakeError(f"could not run party snapshot exporter: {exc}") from exc
        if proc.returncode != 0:
            detail = (proc.stdout or "") + (proc.stderr or "")
            raise HandshakeError(f"party snapshot export failed: {detail.strip()}")

    def _boot(self, request: dict) -> dict:
        mode = str(request.get("mode", "DESIGN")).upper()
        if mode not in SUPPORTED_MODES:
            return self._error(request, "INVALID_REQUEST", f"unsupported HSR mode: {mode}")
        if mode == "FORGE":
            intent = request.get("intent", request.get("forge_intent"))
            explicit = intent is True or (isinstance(intent, str) and intent.strip())
            if not explicit:
                return self._error(
                    request, "FORGE_INTENT_REQUIRED",
                    "FORGE boot requires an explicit intent acknowledgement",
                )
        try:
            paths = self._validate_paths()
            self.paths.assert_local_pc_workspace()
            self.paths.ensure_state_dirs()
        except HostPathError as exc:
            code = "LOCAL_LOCATION_REQUIRED" if "local ACore" in str(exc) else "PATH_NOT_FOUND"
            return self._error(request, code, str(exc))
        self.mode = mode
        self.booted = True
        return self._ok(
            request,
            {
                "state": "booted",
                "mode": mode,
                "paths": paths,
                "context": {
                    "world": world_context(),
                    "design_owner": "DM046_0",
                    "runtime_pair": ["DM044_0", "DM044_1"],
                    "snapshot": str(self.paths.snapshot_path),
                    "story_markdown_loaded": False,
                },
                "capabilities": self.capabilities(),
            },
        )

    @property
    def _session_path(self) -> Path:
        return self.paths.data_root / "hsr_session.json"

    def _session(self) -> dict:
        if self._session_cache is not None:
            return self._session_cache
        try:
            raw = json.loads(self._session_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raw = {}
        result = raw if isinstance(raw, dict) else {}
        self._session_cache = result
        return result


    def _record_session(self, summary: dict, public_summary: str = "Saved HSR run ready to resume.") -> None:
        from datetime import datetime, timezone
        atomic_json(self._session_path, {
            "schema_version": "hollow-star-session-1",
            "last_run_id": summary["run_id"],
            "last_turn_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "party": [member["name"] for member in summary.get("party", [])],
            "opposition": [member["name"] for member in summary.get("opposition", [])],
            "seed": summary.get("seed"),
            "scenario": summary.get("context", {}).get("scenario", "reliquary"),
            "room": summary.get("context", {}).get("sandbox", {}).get("current_room"),
            "public_summary": public_summary,
        })

    def _ready(self, request: dict) -> dict:
        return self._ok(request, {
            "surface": self.paths.local_location_report(),
            "engine": {"id": "hollow-star", "version": ENGINE_VERSION, "modes": self.paths.modes},
            "transport": {"stdio": True},
            "resume": self._session(),
            "defaults": self._ready_defaults(),
            "invalidated_by": "a later create_run, load_run, or design_turn; this pointer is disposable local state",
        })

    def _ready_defaults(self) -> dict:
        # Keep the default fixture aligned with the authored actor registry.
        # ``goblin`` was a stale pre-registry placeholder and made a plain
        # create_run fail before a new player could reach the interface.
        return {"party": ["Doran", "Wren"], "opposition": ["Townsperson"], "seed": "hsr-default", "scenario": "reliquary"}

    def _touch_active_clock(self, run_id: str | None) -> None:
        if not run_id or self._run_service is None:
            return
        run = self._run_service._active.get(run_id)
        if run is None or not isinstance(run.context.get("dungeon"), dict):
            return
        now = time.monotonic()
        previous = self._active_clocks.setdefault(run_id, now)
        elapsed = max(0.0, now - previous)
        self._active_clocks[run_id] = now
        if elapsed:
            from hollowstar import tracking
            tracking.active_seconds(run.context["dungeon"], elapsed)

    def _examine_run(self, request: dict) -> dict:
        """Return a read-only, public explanation for one visible entity."""
        run_id = request.get("run_id") or self._session().get("last_run_id")
        if not run_id:
            raise RunServiceError("examine requires a run_id")
        visible_state = narrator_state(self._runs().observe(run_id))
        public_view = build_public_view(visible_state, mode=self.mode, run_id=run_id)
        entity_type = str(request.get("entity_type") or "").lower() or None
        if entity_type in {"result", "last_result", "last_event"}:
            explanation = resolution_explanation(public_view.get("last_event"))
        else:
            explanation = examine_view(
                public_view,
                entity_type=entity_type,
                entity_id=request.get("entity_id"),
                query=request.get("query"),
            )
        return {
            "run_id": run_id,
            "mode": self.mode,
            "examine": explanation,
            "public_view": public_view,
            "public_receipt": {"type": "examine", "read_only": True},
        }

    def _companion_talk(self, request: dict) -> dict:
        """Read-only companion reply built from the public view. Never mutates the run."""
        from hollowstar import doran_voice
        run_id = request.get("run_id") or self._session().get("last_run_id")
        if not run_id:
            raise RunServiceError("companion_talk requires a run_id")
        speaker = str(request.get("speaker") or "doran").lower()
        text = str(request.get("text") or "").strip()[:500]
        visible_state = narrator_state(self._runs().observe(run_id))
        public_view = build_public_view(visible_state, mode=self.mode, run_id=run_id)
        names = {str(row.get("name", "")).lower() for row in public_view.get("party") or []}
        if speaker not in names:
            raise ValueError(f"{speaker.title()} is not in this party")
        if speaker != "doran":
            raise ValueError(f"{speaker.title()}'s voice is not wired yet")
        memory = self.__dict__.setdefault("_companion_memory", {}).setdefault(f"{run_id}:{speaker}", {})
        return {"run_id": run_id, "reply": doran_voice.reply(public_view, text, memory),
                "public_receipt": {"type": "companion_talk", "read_only": True}}

    def _validate(self, request: dict) -> dict:
        target = str(request.get("target", "all")).lower()
        if target not in {"all", "paths", "snapshot", "location", "handshake", "content"}:
            return self._error(request, "INVALID_REQUEST", f"unsupported validation target: {target}")
        result = {}
        if target in {"all", "location"}:
            location = self.paths.local_location_report()
            result["location"] = location
            if self.paths.local_pc_required and not location["approved"]:
                return self._error(
                    request,
                    "LOCAL_LOCATION_REQUIRED",
                    str(location["reason"]),
                )
        if target in {"all", "paths"}:
            try:
                result["paths"] = self._validate_paths()
            except HostPathError as exc:
                return self._error(request, "PATH_NOT_FOUND", str(exc))
        if target in {"all", "snapshot"}:
            try:
                data = load_snapshot(self.paths.snapshot_path)
                roster, report = import_party(self.paths.snapshot_path)
            except Exception as exc:
                return self._error(request, "SNAPSHOT_INVALID", str(exc))
            result["snapshot"] = {
                "schema_version": data.get("schema_version"),
                "snapshot_version": data.get("snapshot_version"),
                "source_fingerprint": data.get("source_fingerprint"),
                "characters": sorted(roster),
                "deferred_rules": {name: len(items) for name, items in report.deferred.items()},
                "seed_mode": data.get("seed_mode"),
            }
        if target in {"all", "handshake"}:
            try:
                result["handshake"] = verify_handshake(self.paths)
            except (HostPathError, HandshakeError) as exc:
                return self._error(request, "HANDSHAKE_INVALID", str(exc))
        if target in {"all", "content"}:
            try:
                from hollowstar.content_registry import audit_sources, load_registry
                registry=load_registry(verify_sources=False)
                result["content"]={"registry_version":registry["registry_version"],
                                    "entries":len(registry["entries"]),
                                    "rooms":len(registry["rooms"]),
                                    "sources":audit_sources(registry,self.paths.workspace_root)}
            except (ValueError, OSError) as exc:
                return self._error(request, "CONTENT_REGISTRY_INVALID", str(exc))
        return self._ok(request, result)

    def capabilities(self) -> dict:
        return {
                "commands": [
                *sorted(CONTENT_COMMANDS),
                "health", "boot", "validate", "local-check", "status", "party_status", "inspect", "shutdown",
                "examine", "companion_talk",
                "session_intent",
                "start-run", "observe", "submit-action", "resolve-round", "test-perception", "reveal-room-record", "show-temporary-inventory", "sanctum-check-in", "save-run", "create-forge-receipt",
                "conversation", "npc_list", "prepare_idle", "idle_tick", "auto_travel", "auto_battle", "salvage", "trade", "buy", "acquire_weapon", "acquire_armor", "imprint_rune",
                "decant", "release_attunement", "meta_shop", "meta_shop_purchase",
                "character_options", "character_roll", "peek_creation_seed", "randomize_build", "preview_character", "build_character", "content_catalog", "affix_catalog", "scenario_catalog", "design_start", "design_action", "design_turn", "arcade_tick", "arcade_toggle_flight", "arcade_set_movement_mode", "readout", "report", "register_ruling", "spell_catalog", "spell_workshop_catalog", "spell_workshop_preview", "spell_workshop_save", "spell_workshop_list", "design_auto", "design_auto_combat", "design_drain_npc", "checkpoint", "bank_checkpoint", "resume_checkpoint", "terminal_receipt", "progression", "settle_run", "upgrade", "identify", "combine", "replay_token", "inspect_replay_token",
                "sandbox_start", "sandbox_release", "sandbox_action", "sandbox_debug", "sandbox_branch", "finished_runs", "sandbox_prestige",
                *sorted(EXPEDITION_COMMANDS),
                "create_run", "load_run", "list_runs", "inspect_run", "save_run", "statistics",
                "inspect_modules", "forge_start", "forge_action", "forge_receipt",
                "validation_start", "validation_status", "validation_result",
                "create_profile", "update_profile", "list_profiles", "inspect_profile", "list_roster",
            ],
            "modes": {
                "DESIGN": "available",
                "REVIEW": "available",
                "SANDBOX": "available",
                "FORGE": "available; explicit boot intent, 6/6 evidence, and authored entry fixture required",
            },
            # Creating, loading, listing, inspecting, and saving a Run manages
            # PERSISTENCE only -- it never resolves an attack or advances a
            # round. The retired generic gameplay aliases remain rejected;
            # callers use the explicit DESIGN/SANDBOX/FORGE command families.
            "world": world_context(),
            "run_management": True,
            "profile_management": True,
            "module_manifests": {
                "available": True,
                "command": "inspect_modules",
                "status": "validated-read-only; mode boot controls execution",
                "schema": "hollow-star-module-1",
            },
            "selectable_party": True,
            "divine_mythos_imports": "owner-derived-read-only",
            "gameplay": True,
            "design_fixtures": True,
            "design_note": "Sandbox requires current 6/6 evidence; Forge additionally requires explicit intent and an authored placeless entry fixture",
            "natural_language_parsing": "deterministic command translation",
            "public_view": {
                "schema": "hollow-star-public-view-1",
                "command": "readout",
                "description": "normalized public-only party, opposition, room, narration, and action view for clients",
            },
            "examination": {
                "available": True,
                "command": "examine",
                "schema": "hollow-star-examine-1",
                "targets": ["actor", "target", "item", "object", "result"],
                "mutates_run": False,
                "text_examples": ["examine the item", "explain that", "why did that happen"],
            },
            "conversation_adapter": {
                "revision": CONVERSATION_CONTRACT_VERSION,
                "status": "available in DESIGN, REVIEW, and SANDBOX; FORGE remains receipt-bound",
                "command": "design_turn",
                "contract": "A conversational agent supplies a non-empty intent; the host deterministically translates common commands when action is omitted, then validates, persists, and returns a compact public_view status block for narration. Static content is retrieved once through content_catalog; visible_state is debug/audit-only and carries at most the latest five events.",
                "narrator_may_not": ["invent rolls", "invent hidden state", "voice divine dialogue"],
                "narration_source": "public_view",
                "content_policy": "reference data is fetched once via content_catalog, not resent per turn",
            },
            "dd_sandbox": {
                "available": True,
                "status": "DESIGN/SIMULATION vertical slice",
                "scenario": "dd_sandbox",
                "rules_profile": "hybrid-5e-35-core-1",
                "public_receipt": "visible observations and committed state changes only",
                "debug_receipt": "explicit sandbox_debug command only; never narrator input",
                "features": ["d20 checks", "social escalation", "witness locality", "fire and destruction", "weight", "save/resume", "finished-run audit", "branch copies"],
            },
            "story_markdown_runtime_reads": False,
            "snapshot_seed_mode": "SIMULATION",
            "durable_handshake_required": True,
            "hosted_controls": {
                "available": True,
                "transport": "authenticated-loopback-relay",
                "endpoint": "/api/hosted",
                "clients": ["claude", "gpt"],
                "authorization": "named-client-token",
                "concurrency": "single-active-controller-lease-per-run",
                "public_only": True,
            },
        }

    def _require_booted(self, request: dict) -> dict | None:
        if not self.booted:
            return self._error(
                request, "NOT_BOOTED", "boot the host in an explicit HSR mode before managing runs"
            )
        return None

    def _runs(self) -> RunService:
        if self._run_service is None:
            self._run_service = RunService(self.paths.run_root, self.paths.snapshot_path,
                                           self.paths.profile_root, self.paths.content_root / "modules")
        return self._run_service

    def _history(self) -> RunHistory:
        if self._run_history is None:
            self._run_history = RunHistory(self.paths.data_root, self.paths.run_root, self._runs())
        return self._run_history

    def _maintain_runs(self, protected_run_id: str | None = None) -> dict:
        protected = protected_run_id or self._session().get("last_run_id")
        return self._history().maintain(protected if isinstance(protected, str) else None)

    def _profiles(self) -> ProfileService:
        if self._profile_service is None:
            self._profile_service = ProfileService(self.paths.profile_root, self.paths.snapshot_path)
        return self._profile_service

    def _profile_command(self, request: dict, command: str) -> dict:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        try:
            if command in {"create_profile", "update_profile"} and self.mode == "FORGE":
                return self._error(
                    request, "LAUNCH_ROLE_INVALID",
                    "Story Mode accepts Doran or Wren Champions only; create custom profiles in Simulation Mode",
                )
            if command == "create_profile":
                result = self._profiles().save(request.get("profile_id"), request.get("profile"), replace=False)
                return self._ok(request, {"profile": result})
            if command == "update_profile":
                result = self._profiles().save(request.get("profile_id"), request.get("profile"), replace=True)
                return self._ok(request, {"profile": result})
            if command == "inspect_profile":
                return self._ok(request, {"profile": self._profiles().inspect(request.get("profile_id"))})
            if command == "list_profiles":
                return self._ok(request, {"profiles": self._profiles().list()})
            return self._ok(request, {"roster": self._profiles().roster()})
        except ProfileError as exc:
            return self._error(request, "PROFILE_INVALID", str(exc))

    def _create_run(self, request: dict) -> dict:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        previous = self._session().get("last_run_id")
        if isinstance(previous, str) and previous and previous != request.get("run_id"):
            self._history().mark_replaced(previous)
        defaults = self._ready_defaults()
        party = request.get("party", defaults["party"])
        opposition = request.get("opposition", defaults["opposition"])
        seed = request.get("seed", defaults["seed"])
        if not isinstance(party, list) or not party or not all(isinstance(p, str) for p in party):
            return self._error(request, "INVALID_REQUEST", "party must be a non-empty list of actor names")
        if not isinstance(opposition, list) or not opposition or not all(
            isinstance(o, str) for o in opposition
        ):
            return self._error(
                request, "INVALID_REQUEST", "opposition must be a non-empty list of actor names"
            )
        if not isinstance(seed, (str, int)) or seed == "":
            return self._error(request, "INVALID_REQUEST", "seed must be a non-empty string or integer")
        try:
            summary = self._runs().create(request.get("run_id"), party, opposition, str(seed),
                                          module_id=request.get("module_id"),
                                          scenario=request.get("scenario", "reliquary"),
                                          run_mode=str(request.get("mode", self.mode or "DESIGN")).upper(),
                                          lead_selector=request.get("lead_selector"),
                                          starting_location=request.get("starting_location"))
        except (RunStateError, OSError) as exc:
            return self._error(request, "RUN_INVALID", str(exc))
        run = summary.as_dict()
        self._record_session(run)
        self._maintain_runs(run["run_id"])
        return self._ok(request, {"run": run})

    def _load_run(self, request: dict) -> dict:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        try:
            summary = self._runs().load(request.get("run_id"))
        except (RunStateError, OSError) as exc:
            return self._error(request, "RUN_INVALID", str(exc))
        run = summary.as_dict()
        self._record_session(run)
        self._maintain_runs(run["run_id"])
        return self._ok(request, {"run": run})

    def _list_runs(self, request: dict) -> dict:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        retention = self._maintain_runs()
        return self._ok(request, {"runs": retention.get("retained", [])})

    def _inspect_run(self, request: dict) -> dict:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        try:
            summary = self._runs().inspect(request.get("run_id"))
            sheets = self._runs().sheets(request.get("run_id"))
        except (RunStateError, OSError) as exc:
            return self._error(request, "RUN_INVALID", str(exc))
        return self._ok(request, {"run": summary.as_dict(), "sheets": sheets})

    def _save_run(self, request: dict) -> dict:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        try:
            summary = self._runs().save(request.get("run_id"))
        except (RunStateError, OSError) as exc:
            return self._error(request, "RUN_INVALID", str(exc))
        self._maintain_runs(request.get("run_id"))
        return self._ok(request, {"run": summary.as_dict()})

    def _statistics(self, request: dict) -> dict:
        mode = request.get("mode")
        if mode is not None and (not isinstance(mode, str) or mode.upper() not in SUPPORTED_MODES):
            return self._error(request, "INVALID_REQUEST", "statistics mode must be DESIGN, REVIEW, SANDBOX, or FORGE")
        wanted = mode.upper() if isinstance(mode, str) else None
        self._maintain_runs()
        result = self._history().statistics(wanted)
        from hollowstar.progression import Progression
        identities = {selector if ":" in selector else "divine:" + selector
                      for row in result["all_runs"]
                      for selector in (row.get("summary") or {}).get("party", [])
                      if isinstance(selector, str) and selector}
        result["lifetime_accounts"] = []
        progress = Progression(self.paths.run_root.parent / "reliquary_progress")
        for identity in sorted(identities)[:20]:
            try:
                account = progress.load(identity)
            except (ValueError, OSError):
                continue
            result["lifetime_accounts"].append({"identity": identity, "rank": account["rank"],
                                               "platinum": account["platinum"], "loop_tier": account["loop_tier"],
                                               "settled_runs": len(account["runs"]), "tracking": account["tracking"]})
        run_id = request.get("run_id")
        if run_id:
            entry = next((row for row in result["all_runs"] if row.get("run_id") == run_id), None)
            if entry is None:
                return self._error(request, "RUN_INVALID", "run is not in the selected statistics mode")
            result["selected_run"] = entry
            if entry.get("pruned"):
                return self._ok(request, result)
            try:
                summary = self._runs().inspect(run_id).as_dict()
                resolved_mode = str(summary.get("context", {}).get("host_mode") or summary.get("mode") or "DESIGN").upper()
                if wanted and resolved_mode != wanted:
                    return self._error(request, "RUN_INVALID", "save does not belong to the selected statistics mode")
                try:
                    visible_state = narrator_state(self._runs().observe(run_id))
                except (RunServiceError, ValueError):
                    # A valid full save may be inspectable before its first
                    # gameplay start. Select a Save remains read-only in that
                    # state, so project its persisted summary instead of
                    # booting or mutating a gameplay surface.
                    visible_state = {
                        "run_id": run_id,
                        "status": "active" if not summary.get("finished") else "closed",
                        "round": summary.get("round_number", 0),
                        "party": copy.deepcopy(summary.get("party", [])),
                        "opposition": copy.deepcopy(summary.get("opposition", [])),
                    }
                result["selected_save"] = {
                    "summary": summary,
                    "sheets": self._runs().sheets(run_id),
                    "public_view": build_public_view(visible_state, mode=resolved_mode, run_id=run_id),
                }
            except (RunStateError, RunServiceError, OSError, ValueError) as exc:
                return self._error(request, "RUN_INVALID", str(exc))
        return self._ok(request, result)

    def _content_command(self, request: dict, command: str) -> dict:
        """Local compiler authoring surface, excluded by the hosted allowlist."""
        import sqlite3
        from hollowstar.source_catalog import SourceCatalog, SourceError
        from hollowstar.content_package import PackageError, source_starter, validate_package
        from hollowstar.content_preview import PreviewConflict
        try:
            self.paths.assert_local_pc_workspace()
            self.paths.assert_state_path(self.paths.run_root.parent / "content_workbench" / "previews.sqlite3")
            catalog = SourceCatalog(self.paths.workspace_root)
            if command == "packet_effect_probe":
                from hollowstar.runtime_hooks import evaluate_effect
                return self._ok(request, evaluate_effect(request.get("package"), request.get("effect_id"),
                                                        elapsed=request.get("elapsed"), catalog=catalog))
            if command == "packet_run_effect_probe":
                return self._ok(request, self._runs().probe_package_effect(
                    request.get("run_id"), request.get("package"), request.get("effect_id"),
                    since=request.get("since", 0), catalog=catalog))
            if command in {"packet_compile", "packet_runtime_schema", "packet_rule_probe", "packet_rule_validate"}:
                from hollowstar.runtime_contract import SCHEMA, BINDING, compile_package, probe
                from hollowstar.schema_contract import validate as validate_contract
                from hollowstar.generated_rules import source_for
                if command == "packet_runtime_schema":
                    return self._ok(request, {"schema": SCHEMA, "stage": "validated-foundation"})
                if command == "packet_compile":
                    return self._ok(request, compile_package(request.get("package"), catalog))
                binding = request.get("binding")
                validate_contract(binding, BINDING)
                if command == "packet_rule_validate":
                    source_for(binding)
                    return self._ok(request, {"valid": True, "rule_id": binding["id"]})
                return self._ok(request, probe(binding, request.get("inputs")))
            include_archives = request.get("include_archives", False)
            if type(include_archives) is not bool:
                raise SourceError("include_archives must be a boolean")
            if command == "source_search":
                return self._ok(request, catalog.search(request.get("query", ""),
                    offset=request.get("offset", 0), limit=request.get("limit", 40), include_archives=include_archives))
            if command in {"source_read", "packet_starter", "packet_interpret"}:
                source = catalog.read(request.get("path"), start_line=request.get("start_line", 1),
                    line_count=request.get("line_count", 120), include_archives=include_archives,
                    expected_sha256=request.get("expected_sha256"))
                if command == "source_read":
                    return self._ok(request, {"source": source})
                if command == "packet_interpret":
                    from hollowstar.markdown_interpreter import interpret_markdown
                    draft = interpret_markdown(source)
                    report = validate_package(draft["package"], catalog)
                    return self._ok(request, {**report, "review_flags": draft["review_flags"]})
                package = source_starter(source, title=request.get("title"), universe=request.get("universe", "unspecified"))
                return self._ok(request, validate_package(package, catalog))
            if command in {"packet_validate", "packet_preview_start"}:
                report = validate_package(request.get("package"), catalog)
                if command == "packet_validate":
                    return self._ok(request, report)
                view = self._runs().content_previews().start(report["package"], request.get("operation_id"))
                return self._ok(request, {"public_view": view, "validation": {k: v for k, v in report.items() if k != "package"}})
            previews = self._runs().content_previews()
            if command == "packet_preview_list":
                return self._ok(request, {"previews": previews.list(request.get("limit", 30))})
            if command == "packet_preview_export":
                return self._ok(request, {"package": previews.export(request.get("preview_id"))})
            if command == "packet_preview_read":
                return self._ok(request, {"public_view": previews.read(request.get("preview_id"))})
            return self._ok(request, {"public_view": previews.act(request.get("preview_id"), request.get("action"),
                request.get("expected_revision"), request.get("operation_id"))})
        except PreviewConflict as exc:
            return self._error(request, "PREVIEW_CONFLICT", str(exc))
        except (SourceError, PackageError, HostPathError, RunStateError, OSError, sqlite3.Error, ValueError) as exc:
            return self._error(request, "CONTENT_INVALID", str(exc))

    def handle(self, request: dict) -> dict:
        """Route one request to its registered command handler.

        Handlers are ``_cmd_*`` methods registered with ``@command_handler``; a
        handler returning ``None`` means "not mine" and falls through to the
        unknown-command error, exactly as the old if-chain did.
        """
        # Reset per-request session cache so each handle() call starts fresh.
        # This preserves cross-request isolation while allowing multiple _session()
        # calls within the same handle() invocation to hit the cache.
        self._session_cache = None
        _request_id, command = self._request_identity(request)

        if command in CONTENT_COMMANDS:
            return self._content_command(request, command)

        request, command = self._resolve_alias(request, command)
        handler = _HANDLERS.get(command)
        if handler is not None:
            result = handler(self, request, command)
            if result is not None:
                return result
        return self._error(request, "UNSUPPORTED_OPERATION", f"unknown command: {command}")

    def _resolve_alias(self, request: dict, command: str) -> tuple[dict, str]:
        """Rewrite legacy/verb-style command names onto the canonical runtime commands."""
        if command == "submit-action":
            request = {**request, "command": "design_turn"}
            command = "design_turn"
        elif command == "resolve-round":
            request = {**request, "command": "design_action",
                       "action": request.get("action") or {"type": "end_turn"}}
            command = "design_action"
        elif command == "sanctum-check-in":
            request = {**request, "command": "design_action",
                       "action": request.get("action") or {"type": "check_in"}}
            command = "design_action"
        elif command == "create-forge-receipt":
            request = {**request, "command": "forge_receipt"}
            command = "forge_receipt"
        elif command == "save-run":
            request = {**request, "command": "save_run"}
            command = "save_run"
        elif command == "show-temporary-inventory":
            request = {**request, "command": "readout", "public_only": True,
                       "_temporary_inventory_only": True}
            command = "readout"
        elif command in {"conversation", "npc_list", "prepare_idle", "auto_battle",
                         "salvage", "trade", "buy", "acquire_weapon", "acquire_armor",
                         "imprint_rune", "decant", "release_attunement"}:
            action = dict(request.get("action") or {})
            action.update({key: request[key] for key in
                           ("item", "item_id", "actor", "target", "npc", "mode",
                           "text", "strategy", "product", "name", "slot", "base_damage", "base_ac", "max_steps", "macros",
                           "replace", "lane")
                           if key in request and request[key] is not None})
            request = {**request, "command": "design_action",
                       "action": {**action, "type": command}}
            command = "design_action"
        return request, command

    @command_handler("start-run")
    def _cmd_start_run_launch(self, request: dict, command: str) -> dict | None:
        # Party decides the runtime when the caller does not name one:
        # Doran and Wren are the Forge Stewards, everyone else is Sandbox.
        if request.get("mode") is None:
            party = request.get("party")
            requested_mode = (runtime_for(party)
                              if isinstance(party, list) and all(isinstance(p, str) for p in party)
                              else (self.mode or "SANDBOX"))
        else:
            requested_mode = str(request.get("mode")).upper()
        requested_scenario = request.get("scenario") or (
            "floor_one_life" if requested_mode == "SANDBOX" else "reliquary"
        )
        launch_request = {
            **request, "mode": requested_mode, "scenario": requested_scenario,
        }
        try:
            validate_launch(
                mode=requested_mode,
                party=request.get("party"),
                scenario=requested_scenario,
                module_id=request.get("module_id"),
                require_authored_module=True,
            )
        except RunServiceError as exc:
            return self._error(request, "LAUNCH_INVALID", str(exc))
        if not self.booted:
            booted = self._boot(launch_request)
            if not booted.get("ok"):
                return booted
        created = None
        run_id = request.get("run_id")
        if run_id:
            loaded = self._load_run({**launch_request, "run_id": run_id})
            if not loaded.get("ok") and loaded.get("error", {}).get("code") == "RUN_INVALID":
                created = self._create_run(launch_request)
                if not created.get("ok"):
                    return created
                loaded = self._load_run({**launch_request, "run_id": run_id})
            if not loaded.get("ok"):
                return loaded
        else:
            created = self._create_run(launch_request)
            if not created.get("ok"):
                return created
            run_id = created["result"]["run"]["run_id"]
            loaded = self._load_run({**launch_request, "run_id": run_id})
            if not loaded.get("ok"):
                return loaded
        # The authored Story surface opens in the first village and only
        # later descends into the generic Forge/dungeon threshold.  It is
        # still a FORGE launch, so the champion-only and authored-module
        # gates remain in force.
        starter = {"SANDBOX": ("sandbox_start" if requested_scenario == "dd_sandbox"
                               else "design_start"),
                   "FORGE": ("design_start" if requested_scenario in {"floor_one_life", "reliquary_city"}
                             else "forge_start")}.get(requested_mode, "design_start")
        started = self.handle({**launch_request, "command": starter, "run_id": run_id})
        if not started.get("ok"):
            return started
        # start-run is also a public transport boundary.  The normal
        # design_start/readout calls project this state before it reaches
        # the browser, so do the same here instead of serializing live
        # Item instances from the champion's equipment.
        started_result = started["result"]
        if isinstance(started_result, dict) and isinstance(started_result.get("state"), dict):
            visible_state = redact_public(narrator_state(started_result["state"]))
            started_result = {
                **started_result,
                "state": visible_state,
                "public_view": build_public_view(
                    visible_state, event=started_result.get("event"),
                    mode=self.mode, run_id=run_id,
                ),
                "public_receipt": _public_receipt(started_result.get("event", {})),
            }
        return self._ok(request, {"run": created["result"]["run"] if created else
                                  {"run_id": run_id}, "start": started_result})

    @command_handler("health")
    def _cmd_health(self, request: dict, command: str) -> dict | None:
        if command == "submit-action":
            request = {**request, "command": "design_turn"}
            command = "design_turn"
        elif command == "resolve-round":
            request = {**request, "command": "design_action",
                       "action": request.get("action") or {"type": "end_turn"}}
            command = "design_action"
        elif command == "sanctum-check-in":
            request = {**request, "command": "design_action",
                       "action": request.get("action") or {"type": "check_in"}}
            command = "design_action"
        elif command == "create-forge-receipt":
            request = {**request, "command": "forge_receipt"}
            command = "forge_receipt"
        elif command == "save-run":
            request = {**request, "command": "save_run"}
            command = "save_run"
        elif command == "show-temporary-inventory":
            request = {**request, "command": "readout", "public_only": True,
                       "_temporary_inventory_only": True}
            command = "readout"
        elif command in {"conversation", "npc_list", "prepare_idle", "auto_battle",
                         "salvage", "trade", "buy", "acquire_weapon", "acquire_armor",
                         "imprint_rune", "decant", "release_attunement"}:
            action = dict(request.get("action") or {})
            action.update({key: request[key] for key in
                           ("item", "item_id", "actor", "target", "npc", "mode",
                           "text", "strategy", "product", "name", "slot", "base_damage", "base_ac", "max_steps", "macros",
                           "replace", "lane")
                           if key in request and request[key] is not None})
            request = {**request, "command": "design_action",
                       "action": {**action, "type": command}}
            command = "design_action"
        return self._ok(
            request,
            {
                "host_version": HOST_VERSION,
                "engine_version": ENGINE_VERSION,
                "state": "booted" if self.booted else "ready",
                "local_location": self.paths.local_location_report(),
            },
        )

    @command_handler("ready")
    def _cmd_ready(self, request: dict, command: str) -> dict | None:
        return self._ready(request)

    @command_handler("boot")
    def _cmd_boot(self, request: dict, command: str) -> dict | None:
        return self._boot(request)

    @command_handler("validate")
    def _cmd_validate(self, request: dict, command: str) -> dict | None:
        return self._validate(request)

    @command_handler("local-check")
    def _cmd_local_check(self, request: dict, command: str) -> dict | None:
        try:
            self.paths.assert_workspace_layout()
            location = self.paths.assert_local_pc_workspace()
            if location.get("via") == "bridge":
                return self._error(
                    request,
                    "LOCAL_LOCATION_REQUIRED",
                    "local-check writes the handshake and must run natively on the "
                    "approved desktop; a bridge mount may verify it but never rewrite it",
                )
            self._refresh_party_snapshot()
            handshake = write_handshake(self.paths)
        except HostPathError as exc:
            code = "LOCAL_LOCATION_REQUIRED" if "local ACore" in str(exc) else "PATH_NOT_FOUND"
            return self._error(request, code, str(exc))
        except HandshakeError as exc:
            return self._error(request, "HANDSHAKE_INVALID", str(exc))
        return self._ok(
            request,
            {
                "location": location,
                "handshake_path": str(self.paths.handshake_path),
                "handshake": handshake,
            },
        )

    @command_handler("status")
    def _cmd_status(self, request: dict, command: str) -> dict | None:
        return self._ok(
            request,
            {
                "state": "booted" if self.booted else "not_booted",
                "mode": self.mode,
                "workspace_root": str(self.paths.workspace_root),
            },
        )

    @command_handler("party_status")
    def _cmd_party_status(self, request: dict, command: str) -> dict | None:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        run_id = request.get("run_id") or self._session().get("last_run_id")
        if not run_id:
            return self._error(request, "INVALID_REQUEST", "party_status requires a run_id")
        try:
            visible_state = narrator_state(self._runs().observe(run_id))
            return self._ok(request, {
                "run_id": run_id,
                "public_view": build_public_view(
                    visible_state, mode=self.mode, run_id=run_id,
                ),
                "narrator": {"source": "host-returned visible state only"},
            })
        except (RunStateError, OSError, ValueError) as exc:
            return self._error(request, "RUN_INVALID", str(exc))

    @command_handler("examine")
    def _cmd_examine(self, request: dict, command: str) -> dict | None:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        try:
            return self._ok(request, self._examine_run(request))
        except (RunStateError, RunServiceError, OSError, ValueError) as exc:
            return self._error(request, "EXAMINE_INVALID", str(exc))

    @command_handler("companion_talk")
    def _cmd_companion_talk(self, request: dict, command: str) -> dict | None:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        try:
            return self._ok(request, self._companion_talk(request))
        except (RunStateError, RunServiceError, OSError, ValueError) as exc:
            return self._error(request, "COMPANION_INVALID", str(exc))

    @command_handler("session_intent")
    def _cmd_session_intent(self, request: dict, command: str) -> dict | None:
        intent = request.get("intent")
        if not isinstance(intent, str) or not intent.strip():
            return self._error(request, "INVALID_REQUEST", "session_intent requires a non-empty intent")
        parsed = parse_session_intent(intent)
        if parsed is None:
            return self._error(request, "SESSION_INTENT_UNSUPPORTED", "could not translate session intent")
        return self._ok(request, {
            "session": parsed,
            "input": intent.strip(),
            "execution": "adapter-owned; host returned the shared envelope without mutating a run",
        })

    @command_handler(*{"validation_start", "validation_status", "validation_result"})
    def _cmd_validation_jobs(self, request: dict, command: str) -> dict | None:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        if self.mode not in {"DESIGN", "REVIEW"}:
            return self._error(request, "MODE_BLOCKED", "local validation requires DESIGN or REVIEW mode")
        try:
            from hollowstar import validation
            if command == "validation_start":
                result = validation.start(self.paths.workspace_root, self.paths.data_root, job_id=request.get("job_id"))
            elif command == "validation_status":
                result = validation.status(self.paths.data_root, request.get("job_id"))
            else:
                result = validation.result(self.paths.data_root, request.get("job_id"), include_log=bool(request.get("include_log", False)))
            return self._ok(request, {"validation": result})
        except (ValueError, OSError) as exc:
            return self._error(request, "VALIDATION_INVALID", str(exc))

    @command_handler("inspect")
    def _cmd_inspect(self, request: dict, command: str) -> dict | None:
        target = str(request.get("target", "capabilities")).lower()
        if target == "modules":
            from hollowstar.modules import list_manifests
            return self._ok(request, {"modules": list_manifests(self.paths.content_root / "modules")})
        if target != "capabilities":
            return self._error(request, "INVALID_REQUEST", f"unsupported inspection target: {target}")
        return self._ok(request, {"capabilities": self.capabilities()})

    @command_handler("inspect_modules")
    def _cmd_inspect_modules(self, request: dict, command: str) -> dict | None:
        from hollowstar.modules import list_manifests
        return self._ok(request, {"modules": list_manifests(self.paths.content_root / "modules")})

    @command_handler("shutdown")
    def _cmd_shutdown(self, request: dict, command: str) -> dict | None:
        self.booted = False
        return self._ok(request, {"shutdown": True, "state": "stopped"})

    @command_handler("affix_catalog")
    def _cmd_affix_catalog(self, request: dict, command: str) -> dict | None:
        from hollowstar.loader import affix_catalog
        return self._ok(request, {"affixes": affix_catalog()})

    @command_handler("scenario_catalog")
    def _cmd_scenario_catalog(self, request: dict, command: str) -> dict | None:
        # Read-only content description: answerable before boot so the client
        # can show the scenario picker without holding an engine.
        from hollowstar.run_service import RunService
        mode = request.get("mode")
        if mode is not None and not isinstance(mode, str):
            return self._error(request, "INVALID_REQUEST", "mode must be a string")
        return self._ok(request, {"scenarios": RunService.scenario_catalog(mode)})

    @command_handler("statistics")
    def _cmd_statistics(self, request: dict, command: str) -> dict | None:
        return self._statistics(request)

    @command_handler(*{"spell_workshop_catalog", "spell_workshop_preview", "spell_workshop_save", "spell_workshop_list"})
    def _cmd_spell_workshop(self, request: dict, command: str) -> dict | None:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        if self.mode not in {"DESIGN", "SANDBOX"}:
            return self._error(request, "MODE_BLOCKED", "spell workshop is available only in DESIGN or SANDBOX mode")
        try:
            from hollowstar import spell_workshop
            if command == "spell_workshop_catalog":
                return self._ok(request, {"workshop": spell_workshop.catalog()})
            if command == "spell_workshop_list":
                return self._ok(request, {"recipes": spell_workshop.list_recipes(self.paths.data_root), "scope": "local workshop only"})
            recipe = spell_workshop.compose(
                request.get("spell_id"), request.get("metamagic", []), request.get("parameters", {}),
                available_sorcery_points=request.get("available_sorcery_points"),
            )
            if command == "spell_workshop_preview":
                return self._ok(request, {"recipe": recipe})
            stored = spell_workshop.save_recipe(self.paths.data_root, recipe, request.get("name"))
            return self._ok(request, {"recipe": stored, "storage": str(self.paths.data_root / "metamagic_workshop" / "recipes.json")})
        except (spell_workshop.WorkshopError, OSError, ValueError, TypeError) as exc:
            return self._error(request, "SPELL_WORKSHOP_INVALID", str(exc))

    @command_handler(*({"character_options", "character_roll", "peek_creation_seed", "allocate_creation_seed", "randomize_build", "preview_character", "build_character", "content_catalog", "design_start", "design_action", "design_turn", "arcade_tick", "arcade_toggle_flight", "arcade_set_movement_mode", "idle_tick", "auto_travel", "observe", "readout", "report", "reveal-room-record", "test-perception", "register_ruling", "spell_catalog", "design_auto", "design_auto_combat", "design_drain_npc", "checkpoint", "bank_checkpoint", "resume_checkpoint", "terminal_receipt", "progression", "settle_run", "upgrade", "meta_shop", "meta_shop_purchase", "star_memory", "star_mark_seen", "identify", "combine", "replay_token", "inspect_replay_token", "design_auto", "sandbox_start", "sandbox_release", "sandbox_action", "sandbox_debug", "sandbox_branch", "finished_runs", "sandbox_prestige", "forge_start", "forge_action", "forge_receipt"} | EXPEDITION_COMMANDS))
    def _cmd_design_runtime(self, request: dict, command: str) -> dict | None:
        blocked = self._require_booted(request)
        if blocked:
            return blocked
        if command in {"design_turn", "observe", "readout", "report"} and not request.get("run_id"):
            request = {**request, "run_id": self._session().get("last_run_id")}
        if command not in {"observe", "readout", "report"}:
            # These three are read-only reports of current state; advancing
            # the active-time clock here would make re-reading a run mutate
            # it, so two back-to-back readouts would no longer agree.
            self._touch_active_clock(request.get("run_id"))
        try:
            if command in {"star_memory","star_mark_seen"}:
                from hollowstar.star_memory import StarMemory
                star=StarMemory(self.paths.run_root.parent / "reliquary_progress")
                if command=="star_mark_seen": return self._ok(request,{"star":star.mark_seen(request.get("cutscene"))})
                try:
                    history=self._history().statistics(None)["all_runs"]
                except Exception:  # history is a convenience source; memory still reads
                    history=[]
                return self._ok(request,{"star":star.absorb_history(history)})
            if command in {"progression","settle_run","upgrade","meta_shop","meta_shop_purchase"}:
                from hollowstar.progression import Progression, shop_catalog
                progress=Progression(self.paths.run_root.parent / "reliquary_progress")
                identity=request.get("identity")
                if command=="progression": return self._ok(request,{"progression":progress.load(identity)})
                if command=="meta_shop":
                    # Read-only: every track with its tier, cap, and next Platinum cost.
                    data=progress.load(identity)
                    return self._ok(request,{"progression":data,"meta_shop":shop_catalog(data["upgrades"])})
                if command=="meta_shop_purchase":
                    data=progress.purchase(identity,request.get("upgrade") or request.get("track"))
                    return self._ok(request,{"progression":data,"meta_shop":shop_catalog(data["upgrades"])})
                if command=="upgrade" and request.get("run_id") and request.get("item"):
                    action={"type":"upgrade","item":request.get("item"),
                            "actor":request.get("actor","p0")}
                    return self._ok(request,{"outcome":self._runs().design_action(
                        request.get("run_id"),action)["event"]})
                if command=="upgrade": return self._ok(request,{"progression":progress.purchase(identity,request.get("upgrade"))})
                run=self._runs()._active.get(request.get("run_id"))
                if run is None:raise RunServiceError("load the run first")
                settled=progress.settle(identity,request.get("run_id"),run)
                from hollowstar.star_memory import StarMemory
                receipt=settled["runs"][request.get("run_id")]
                star=StarMemory(self.paths.run_root.parent / "reliquary_progress").record_run(
                    request.get("run_id"),identity,receipt,{"name":identity.split(":",1)[1]})
                return self._ok(request,{"progression":settled,"star":star})
            if command == "content_catalog":
                catalog = self._runs().content_catalog(request.get("run_id"))
                from hollowstar.loader import load_items
                dungeon_path = self.paths.content_root / "dungeon.json"
                dungeon = json.loads(dungeon_path.read_text(encoding="utf-8")) if dungeon_path.is_file() else {}
                item_rows = []
                for item in load_items().values():
                    item_rows.append({
                        "name": item.name, "slot": item.slot, "tier": item.tier.name,
                        "base_damage": item.base_damage, "attack_bonus": item.attack_bonus,
                        "base_ac": item.base_ac, "tags": sorted(tag.name for tag in item.tags),
                        "flavor": item.flavor, "utility_uses": list(item.utility_uses),
                    })
                catalog.update({
                    "items": item_rows,
                    "rooms": [{
                        "id": str(index + 1), "name": row.get("name"),
                        "type": row.get("apparent_function"), "terrain": row.get("terrain"),
                        "resident": row.get("resident"), "law": row.get("law"),
                        "exit": row.get("exit"),
                    } for index, row in enumerate(dungeon.get("floors", [])) if isinstance(row, dict)],
                    "source": "hollowstar/content/items.json + hollowstar/content/dungeon.json",
                })
                return self._ok(request, {"content": catalog})
            if command == "replay_token":
                return self._ok(request, {"replay":self._runs().replay_token(request.get("run_id"))})
            if command == "inspect_replay_token":
                return self._ok(request, {"replay":self._runs().inspect_replay_token(request.get("token"))})
            if command == "character_options":
                from hollowstar.character_builder import options
                payload = options()
                payload["champions"] = [
                    {"id": row["name"], "title": row.get("identity", {}).get("name", "Tier-3 Sanctum field Steward"),
                     "blurb": row.get("provenance", {}).get("note", "Certified Sanctum field Steward")}
                    for row in self._profiles().roster()
                    if row.get("name") in {"Doran", "Wren"} and row.get("kind") == "divine_mythos"
                ]
                return self._ok(request, payload)
            if command == "character_roll":
                from hollowstar.character_builder import roll_abilities
                return self._ok(request, {"ability_roll": roll_abilities(
                    request.get("creation_seed"), request.get("roll_set", 0))})
            if command == "preview_character":
                from hollowstar.character_builder import preview_with_notes
                if not isinstance(request.get("build"), dict) or "background" not in request["build"]:
                    raise ProfileError("background is required for a new character build")
                return self._ok(request, {"character": preview_with_notes(request.get("build"))})
            if command == "allocate_creation_seed":
                return self._ok(request, {"seed": self._profiles().allocate_creation_seed()})
            if command == "peek_creation_seed":
                return self._ok(request, {"seed": self._profiles().peek_creation_seed()})
            if command == "randomize_build":
                from hollowstar.character_builder import preview_with_notes, randomize_build
                build = randomize_build(request.get("creation_seed"), request.get("level"))
                if isinstance(request.get("name"), str) and request["name"].strip():
                    build["name"] = request["name"].strip()
                return self._ok(request, {"build": build, "character": preview_with_notes(build)})
            if command == "build_character":
                from hollowstar.character_builder import preview
                if not isinstance(request.get("build"), dict) or "background" not in request["build"]:
                    raise ProfileError("background is required for a new character build")
                result = preview(request.get("build"))
                if request.get("expected_build_hash") != result["build_hash"]:
                    raise ProfileError("build hash mismatch; preview the exact character before saving")
                saved, created = self._profiles().save_confirmed_build(
                    request.get("profile_id"), result["profile"]
                )
                seed_commit = self._profiles().commit_creation_seed(result["receipt"]["creation_seed"])
                return self._ok(request, {"profile": saved, "build_hash": result["build_hash"],
                                          "creation_receipt": result["receipt"], "seed_commit": seed_commit,
                                          "created": created})
            if command == "design_start":
                outcome = self._runs().design_start(request.get("run_id"))
                return self._ok(request, _public_outcome(
                    outcome, mode=self.mode, run_id=request.get("run_id"),
                ))
            if command == "idle_tick":
                outcome = self._runs().idle_tick(
                    request.get("run_id"), max_steps=request.get("max_steps", 1),
                )
                visible_state = narrator_state(outcome["state"])
                return self._ok(request, {"idle": {
                    "run_id": request.get("run_id"),
                    "event": redact_public(outcome["event"]),
                    "public_view": build_public_view(
                        visible_state, event=outcome["event"], mode=self.mode,
                        run_id=request.get("run_id"),
                    ),
                    "public_receipt": _public_receipt(outcome["event"]),
                }})
            if command == "auto_travel":
                outcome = self._runs().auto_travel(
                    request.get("run_id"), destination=request.get("destination", "well"),
                    max_steps=request.get("max_steps", 4),
                    enter_descent=bool(request.get("enter_descent", False)),
                )
                visible_state = narrator_state(outcome["state"])
                return self._ok(request, {"travel": {
                    "run_id": request.get("run_id"),
                    "event": redact_public(outcome["event"]),
                    "public_view": build_public_view(visible_state, event=outcome["event"], mode=self.mode, run_id=request.get("run_id")),
                    "public_receipt": _public_receipt(outcome["event"]),
                }})
            if command == "forge_start":
                outcome = self._runs().forge_start(request.get("run_id"))
                return self._ok(request, _public_outcome(
                    outcome, mode=self.mode, run_id=request.get("run_id"),
                ))
            if command == "forge_action":
                return self._ok(request, self._runs().design_action(
                    request.get("run_id"), request.get("action"), intent=request.get("intent")))
            if command == "forge_receipt":
                run = self._runs()._active.get(request.get("run_id"))
                if run is None:
                    raise RunServiceError("load the run first")
                forge = run.context.get("forge")
                if not isinstance(forge, dict):
                    raise RunServiceError("run is not a Forge run")
                return self._ok(request, {"receipt": forge.get("receipt"), "status": forge.get("status")})
            if command == "sandbox_start":
                return self._ok(request, self._runs().sandbox_start(request.get("run_id")))
            if command == "sandbox_release":
                return self._ok(request, self._runs().sandbox_release(request.get("run_id")))
            if command == "sandbox_action":
                return self._ok(request, self._runs().design_action(request.get("run_id"), request.get("action"), intent=request.get("intent")))
            if command == "sandbox_debug":
                return self._ok(request, self._runs().sandbox_debug(request.get("run_id")))
            if command == "sandbox_branch":
                return self._ok(request, {"run": self._runs().branch(request.get("run_id"), request.get("new_run_id")).as_dict()})
            if command == "finished_runs":
                return self._ok(request, {"runs": self._runs().finished_runs()})
            if command == "sandbox_prestige":
                return self._ok(request, {"prestige": self._runs().sandbox_prestige()})
            if command in EXPEDITION_COMMANDS:
                action = {"type": command}
                for field in ("node", "mode", "max_nodes", "retreat_below"):
                    if field in request:
                        action[field] = request[field]
                outcome = self._runs().design_action(request.get("run_id"), action)
                return self._ok(request, _public_outcome(
                    outcome, mode=self.mode, run_id=request.get("run_id"),
                ))
            if command in {"checkpoint","bank_checkpoint","resume_checkpoint"}:
                action_type="resume_checkpoint" if command=="resume_checkpoint" else "bank_checkpoint"
                return self._ok(request, self._runs().design_action(request.get("run_id"), {"type":action_type}))
            if command == "terminal_receipt":
                run=self._runs()._active.get(request.get("run_id"))
                if run is None: raise RunServiceError("load the run first")
                return self._ok(request, {"terminal_receipt":run.context["dungeon"].get("terminal_receipt")})
            if command == "design_auto":
                from hollowstar.policies import exploration_action
                run = self._runs()._active.get(request.get("run_id"))
                if run is None: raise RunServiceError("load the run first")
                outcome = self._runs().design_action(request.get("run_id"), exploration_action(run))
                return self._ok(request, _public_outcome(
                    outcome, mode=self.mode, run_id=request.get("run_id"),
                ))
            if command == "design_auto_combat":
                run = self._runs()._active.get(request.get("run_id"))
                if run is None: raise RunServiceError("load the run first")
                from hollowstar import tactical as _t
                if "combat" not in run.context or run.context["combat"].get("complete"):
                    return self._error(request, "NOT_IN_COMBAT", "no active combat to auto-resolve")
                # npc_only callers stepping one NPC action at a time must stop
                # at a player decision; the client's Auto-turn button omits it.
                # (design_drain_npc runs its own multi-step loop instead.)
                if request.get("npc_only"):
                    combat_state = run.context["combat"]
                    decider = combat_state["pending"][0]["reactor"] if combat_state["pending"] else _t.current(run)
                    if _t.actor(run, decider).controller == "player":
                        return self._error(request, "PLAYER_TURN",
                                           f"{decider} is player-controlled; awaiting a player decision")
                from hollowstar.policies import combat_action
                outcome = self._runs().design_action(request.get("run_id"), combat_action(run))
                return self._ok(request, _public_outcome(
                    outcome, mode=self.mode, run_id=request.get("run_id"),
                ))
            if command == "design_drain_npc":
                run = self._runs()._active.get(request.get("run_id"))
                if run is None: raise RunServiceError("load the run first")
                combat_state = run.context.get("combat")
                if not isinstance(combat_state, dict) or combat_state.get("complete"):
                    return self._error(request, "NOT_IN_COMBAT", "no active combat to drain")
                from hollowstar.run_service import DRAIN_NPC_LIMIT
                outcome = self._runs().drain_npc(request.get("run_id"),
                                                 max_steps=request.get("max_steps", DRAIN_NPC_LIMIT))
                public = _public_outcome(outcome, mode=self.mode, run_id=request.get("run_id"))
                event = outcome.get("event") or {}
                public["receipts"] = _step_receipts(redact_public(event))
                public["drain"] = {"steps": len(event.get("steps") or []), "stopped": event.get("stopped"),
                                   "next_actor": event.get("next_actor")}
                return self._ok(request, public)
            if command in {"arcade_tick", "arcade_toggle_flight", "arcade_set_movement_mode"}:
                action = request.get("action")
                if not isinstance(action, dict):
                    action = {"type": command, **{k: v for k, v in request.items() if k not in {"command", "id", "run_id", "compact", "public_only"}}}
                outcome = self._runs().design_action(request.get("run_id"), action)
                return self._ok(request, _public_outcome(
                    outcome, mode=self.mode, run_id=request.get("run_id"),
                ))
            if command == "design_action":
                outcome = self._runs().design_action(request.get("run_id"), request.get("action"))
                return self._ok(request, _public_outcome(
                    outcome, mode=self.mode, run_id=request.get("run_id"),
                ))
            if command == "design_turn":
                public_only = request.get("public_only", True)
                if type(public_only) is not bool:
                    return self._error(request, "INVALID_REQUEST", "public_only must be a boolean")
                intent = request.get("intent")
                if not isinstance(intent, str) or not intent.strip():
                    return self._error(request, "INVALID_REQUEST", "design_turn requires a non-empty intent")
                if len(intent) > 2000:
                    return self._error(request, "INVALID_REQUEST", "design_turn intent must be at most 2000 characters")
                action = request.get("action")
                if action is None:
                    from hollowstar.intent import IntentClarification, parse_intent
                    try:
                        visible_context = self._runs().observe(request.get("run_id"))
                        action = parse_intent(intent, visible_context)
                    except IntentClarification as exc:
                        return self._error(request, "INTENT_CLARIFICATION", exc.message)
                if isinstance(action, dict) and action.get("type") in {"examine", "explain"}:
                    try:
                        fields = dict(request)
                        if action.get("type") == "explain":
                            fields["entity_type"] = "result"
                        else:
                            fields.update({key: action[key] for key in ("entity_type", "entity_id", "query") if key in action})
                        inspected = self._examine_run(fields)
                    except (RunStateError, RunServiceError, OSError, ValueError) as exc:
                        return self._error(request, "EXAMINE_INVALID", str(exc))
                    return self._ok(request, {"turn": {
                        "run_id": request.get("run_id"),
                        "mode": self.mode,
                        "player_intent": intent.strip(),
                        "action": action,
                        "examine": inspected["examine"],
                        "public_view": inspected["public_view"],
                        "public_receipt": inspected["public_receipt"],
                        "narrator": {"source": "host-returned explanation and public view only",
                                     "narration_source_block": "public_view"},
                    }})
                if isinstance(action, dict) and action.get("type") == "query" and action.get("data") == "party_status":
                    visible_state = narrator_state(self._runs().observe(request.get("run_id")))
                    public_view = build_public_view(
                        visible_state, mode=self.mode, run_id=request.get("run_id"),
                    )
                    return self._ok(request, {"turn": {
                        "run_id": request.get("run_id"),
                        "mode": self.mode,
                        "player_intent": intent.strip(),
                        "action": action,
                        "public_view": public_view,
                        "public_receipt": {"type": "party_status", "read_only": True},
                        "narrator": {"source": "host-returned visible state only", "narration_source_block": "public_view"},
                    }})
                outcome = self._runs().design_action(
                    request.get("run_id"), action, intent=intent,
                )
                visible_state = narrator_state(outcome["state"])
                turn = {
                    "run_id": request.get("run_id"),
                    "mode": self.mode,
                    "player_intent": intent.strip(),
                    "action": action,
                    "outcome": redact_public(outcome["event"]),
                    "public_view": build_public_view(
                        visible_state, event=outcome["event"], mode=self.mode,
                        run_id=request.get("run_id"),
                    ),
                    "public_receipt": _public_receipt(outcome["event"]),
                    "narrator": {
                        "source": "host-returned visible state only",
                        "narration_source_block": "public_view",
                        "receipt_policy": "public receipt only; private sandbox debug requires explicit sandbox_debug",
                        "voice": "residents and environment; divine dialogue remains Corey-owned",
                        "next_input": "Ask for the next intent when the visible state leaves a decision open.",
                    },
                }
                receipts = _step_receipts(redact_public(outcome["event"]))
                if receipts:
                    turn["receipts"] = receipts
                if not public_only:
                    turn["visible_state"] = visible_state
                self._record_session(
                    self._runs().inspect(request.get("run_id")).as_dict(),
                    turn["public_view"].get("summary", "Saved HSR run ready to resume."),
                )
                return self._ok(
                    request,
                    {"turn": turn},
                )
            if command == "observe":
                return self._ok(request, {"state": self._runs().observe(request.get("run_id"))})
            if command == "readout":
                public_only = request.get("public_only", True)
                if type(public_only) is not bool:
                    return self._error(request, "INVALID_REQUEST", "public_only must be a boolean")
                visible_state = self._runs().observe(request.get("run_id"))
                persisted_progression = None
                identity = request.get("identity")
                if isinstance(identity, str) and identity.strip():
                    from hollowstar.progression import Progression
                    persisted_progression = Progression(self.paths.run_root.parent / "reliquary_progress").load(identity)
                visible_state = narrator_state(visible_state)
                readout = {
                    "run_id": request.get("run_id"),
                    "mode": self.mode,
                    "progression": persisted_progression,
                    "public_view": build_public_view(
                        visible_state,
                        event=visible_state.get("events", [])[-1] if visible_state.get("events") else None,
                        mode=self.mode, progression=persisted_progression,
                        run_id=request.get("run_id"),
                    ),
                    "public_receipt": _readout_receipt(visible_state),
                    "narrator": {
                        "source": "host-returned visible state only",
                        "narration_source_block": "public_view",
                        "receipt_policy": "public state only; private sandbox debug requires explicit sandbox_debug",
                        "voice": "residents and environment; divine dialogue remains Corey-owned",
                    },
                }
                if not public_only:
                    readout["visible_state"] = visible_state
                if request.get("_temporary_inventory_only"):
                    readout["temporary_inventory"] = [
                        item for item in readout["public_view"].get("inventory", [])
                        if item.get("temporary", True)
                    ]
                return self._ok(
                    request,
                    {"readout": readout},
                )
            if command == "report":
                visible_state = narrator_state(self._runs().observe(request.get("run_id")))
                identity = request.get("identity")
                account = None
                if isinstance(identity, str) and identity.strip():
                    from hollowstar.progression import Progression
                    account = Progression(self.paths.run_root.parent / "reliquary_progress").load(identity)
                public_view = build_public_view(visible_state, mode=self.mode,
                                                 progression=account, run_id=request.get("run_id"))
                return self._ok(request, {"report": {"run": public_view,
                    "account": account, "public_receipt": _readout_receipt(visible_state)}})
            if command in {"reveal-room-record", "test-perception"}:
                action_type = command.replace('-', '_')
                action = {"type": action_type, "actor": request.get("actor", "p0")}
                if request.get("tell_id"):
                    action["tell_id"] = request["tell_id"]
                outcome = self._runs().design_action(request.get("run_id"), action)
                return self._ok(request, {"outcome": outcome["event"], "visible_state": outcome["state"]})
            if command == "register_ruling":
                return self._ok(request, self._runs().register_ruling(request.get("run_id"), request.get("ruling")))
            from hollowstar.spells import display_catalog
            run = self._runs()._active.get(request.get("run_id"))
            if run is None:
                raise RunServiceError("load the run first")
            return self._ok(request, {"spells": display_catalog(run)})
        except (ValueError, RunStateError, OSError) as exc:
            return self._error(request, "ACTION_INVALID", str(exc))

    @command_handler("create_run")
    def _cmd_create_run(self, request: dict, command: str) -> dict | None:
        return self._create_run(request)

    @command_handler("load_run")
    def _cmd_load_run(self, request: dict, command: str) -> dict | None:
        return self._load_run(request)

    @command_handler("list_runs")
    def _cmd_list_runs(self, request: dict, command: str) -> dict | None:
        return self._list_runs(request)

    @command_handler("inspect_run")
    def _cmd_inspect_run(self, request: dict, command: str) -> dict | None:
        return self._inspect_run(request)

    @command_handler("save_run")
    def _cmd_save_run(self, request: dict, command: str) -> dict | None:
        return self._save_run(request)

    @command_handler(*{"create_profile", "update_profile", "list_profiles", "inspect_profile", "list_roster"})
    def _cmd_profiles(self, request: dict, command: str) -> dict | None:
        return self._profile_command(request, command)

    @command_handler(*{"start_run", "resume_run", "apply_action"})
    def _cmd_service_runs(self, request: dict, command: str) -> dict | None:
        # Retired generic aliases: explicit mode-scoped commands preserve
        # the authority and boundary of each gameplay surface.
        return self._error(
            request,
            "UNSUPPORTED_OPERATION",
            f"{command} is a retired generic alias; use design_start/design_turn/design_action or the corresponding sandbox/forge command",
        )
