"""Native file-mailbox bridge for HSR.

Drains this folder's .local/phone_bridge/inbox.jsonl into the same HSRHost
used by --stdio, and appends correlated responses to outbox.jsonl -- plus,
for a design_turn/design_action that lands in combat, every NPC turn (and
NPC/monster reaction) the engine auto-resolves on its own before the next
player-controlled decision point.

Run this NATIVELY (double-click hsr_bridge_watch.bat, or `python
hsr_bridge_watch.py` from this folder) on the real desktop workspace --
HSRHost's own location gate requires that real path, not a bridged or
mounted copy of it. On-demand only: start it before a phone-driven session,
Ctrl+C or close the window when done. This file does no dice/rules math of
its own; it only ever calls into the existing HSRHost/RunService/policies
modules, so all computation stays on the computer, never on the AI side.

Protocol
--------
inbox.jsonl   One JSON object per line, appended by whichever side is
              sending a request: {"id": "...", "command": "...", ...} --
              exactly the shape hollowstar_host.py --stdio already accepts
              (design_turn, observe, readout, create_run, boot, health, ...).
              Either side -- Cowork through its device bridge, or Codex/
              Claude Code sitting at the keyboard -- can append here.
              An optional "expires_at" (epoch seconds) marks a speculative
              request: picked up after that moment, it is answered
              REQUEST_EXPIRED and never executed.

outbox.jsonl  One JSON object per line per inbox id, appended by this
              watcher: the host's normal response for that id, plus (only
              when the turn landed in combat) two extra keys:
                "auto_resolved": [ ...each design_auto_combat response... ]
                "settled_state": the visible state after the last auto step
              so a reader only has to narrate one bundle per player intent,
              not one round trip per NPC action.

watcher.json  Written at startup: pid, start time, host update interval and
              the sha256 of this file plus every hollowstar/*.py module, so a
              launcher can tell a watcher running current code from one left
              over from an older version.

Only one instance of this watcher should run against a given workspace at
once -- it is the sole thing calling HSRHost.handle() here, so a second
instance would double-answer or race the same inbox lines.
"""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
import sys
import time
from pathlib import Path

HSR_ROOT = Path(__file__).resolve().parent
if str(HSR_ROOT) not in sys.path:
    sys.path.insert(0, str(HSR_ROOT))

from hollowstar.host import HSRHost  # noqa: E402
from hollowstar.transfer import capsule  # noqa: E402

BRIDGE_DIR = HSR_ROOT / ".local" / "phone_bridge"
INBOX = BRIDGE_DIR / "inbox.jsonl"
OUTBOX = BRIDGE_DIR / "outbox.jsonl"
LOG = BRIDGE_DIR / "watch.log"

# Host update interval: the idle sleep between inbox checks, so a request waits
# at most this long for pickup. After a batch the loop checks again at once.
POLL_SECONDS = 0.12
# Chained requests (a turn, then its readout) arrive back to back; poll hot for
# a moment after activity so the follow-up is not charged a full host update.
HOT_POLL_SECONDS = 0.01
HOT_WINDOW_SECONDS = 2.0
MAX_AUTO_STEPS = 40
HEARTBEAT_SECONDS = 60
MAX_LINE_BYTES = 1_363_148  # 1 MiB + 30%, rounded down (2026-09-23)
LOG_VALUE_CHARS = 120

TURN_COMMANDS = {"design_turn", "design_action"}
LIFE_TICK_SECONDS = 30
_last_auto_steps = 0


def _log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    try:
        print(line, flush=True)
    except (OSError, ValueError):
        pass  # a closed or broken console pipe must never stop the engine
    try:
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def _clip(value, limit: int = LOG_VALUE_CHARS) -> str:
    """Printable single-line text for log lines, truncated; client text is never trusted."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = "".join(ch if ch.isprintable() else " " for ch in text)
    return text if len(text) <= limit else text[:limit - 3] + "..."


def _describe_request(request: dict) -> str:
    """`command run=... intent="..." action=...` for one request log line."""
    parts = [_clip(request.get("command"), 60)]
    if request.get("run_id") is not None:
        parts.append("run=" + _clip(request["run_id"], 60))
    if request.get("intent") is not None:
        parts.append(f'intent="{_clip(request["intent"])}"')
    action = request.get("action")
    if isinstance(action, dict) and action.get("type") is not None:
        parts.append("action=" + _clip(action["type"], 60))
    return " ".join(parts)


def _error_text(response: dict) -> str:
    """`CODE: message` from a full or compact error response."""
    error = response.get("error") if isinstance(response, dict) else None
    if isinstance(error, dict):
        return _clip(f"{error.get('code', 'UNKNOWN')}: {error.get('message', '')}".rstrip(": "))
    return _clip(error if error is not None else "no error detail")


def _read_jsonl_from(path: Path, offset: int = 0) -> tuple[list[dict], int]:
    """Parse complete mailbox lines past byte `offset`; return rows and the next offset.

    A partial final line stays unread for the next call. A file shorter than
    `offset` was truncated or replaced, so reading restarts from byte 0."""
    try:
        size = path.stat().st_size
    except OSError:
        return [], 0
    if size < offset:
        offset = 0
    if size == offset:
        return [], offset
    rows: list[dict] = []
    with path.open("rb") as handle:
        handle.seek(offset)
        while True:
            raw = handle.readline(MAX_LINE_BYTES + 1)
            if not raw:
                break
            if len(raw) > MAX_LINE_BYTES:
                while raw and not raw.endswith(b"\n"):
                    raw = handle.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    break  # oversized record still being written; never skip past it early
                offset = handle.tell()
                _log("skipping oversized mailbox line")
                continue
            # Writers may still be appending the final record.
            if not raw.endswith(b"\n"):
                break
            offset = handle.tell()
            try:
                row = json.loads(raw.decode("utf-8"))
            except (UnicodeError, ValueError, RecursionError):
                _log("skipping malformed mailbox line")
                continue
            if not isinstance(row, dict):
                continue
            request_id = row.get("id")
            if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 256:
                continue
            rows.append(row)
    return rows, offset


def _read_jsonl(path: Path) -> list[dict]:
    return _read_jsonl_from(path, 0)[0]


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False) + "\n")
        handle.flush()


def _source_sha256() -> str:
    """Digest of everything this watcher actually runs: this file plus every
    module under hollowstar/, the package HSRHost/RunService/policies live in.
    Hashing only this file left an edit to hollowstar/*.py invisible to the
    staleness check below -- a watcher already running would keep answering
    with the old engine code forever, no matter how many times a launcher
    restarted around it, since it never looked stale from here."""
    digest = hashlib.sha256(Path(__file__).resolve().read_bytes())
    engine_root = HSR_ROOT / "hollowstar"
    for path in sorted(engine_root.rglob("*.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


_LOADED_SHA256 = _source_sha256()


def _write_watcher_info() -> dict:
    """Record which code this watcher runs, so launchers can retire an outdated one."""
    info = {"pid": os.getpid(), "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "poll_seconds": POLL_SECONDS, "source_sha256": _LOADED_SHA256}
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    (BRIDGE_DIR / "watcher.json").write_text(json.dumps(info) + "\n", encoding="utf-8")
    return info


def _clear_watcher_info() -> None:
    path = BRIDGE_DIR / "watcher.json"
    try:
        if json.loads(path.read_text(encoding="utf-8")).get("pid") == os.getpid():
            path.unlink()
    except (OSError, ValueError, AttributeError):
        pass


def _auto_drain_npc_turns(host: HSRHost, run_id: str) -> list[dict]:
    """Auto-play every NPC decision (and any reaction whose reactor is NPC-
    controlled) until the next player-controlled decision point, using the
    same policy tests/test_gameplay.py exercises. Returns each raw
    design_auto_combat response, in order."""
    resolved: list[dict] = []
    for _ in range(MAX_AUTO_STEPS):
        step = host.handle({"id": "auto", "command": "design_auto_combat", "run_id": run_id,
                            "npc_only": True})
        if step.get("ok"):
            resolved.append(step)
            continue
        code = (step.get("error") or {}).get("code")
        if code in {"PLAYER_TURN", "NOT_IN_COMBAT"}:
            break
        resolved.append(step)  # an unexpected error is worth keeping, not swallowing
        break
    else:
        _log(f"auto-drain hit the {MAX_AUTO_STEPS}-step safety cap for run {run_id!r}")
    return resolved


def _is_shutdown_response(response: dict) -> bool:
    result = response.get("result") if isinstance(response, dict) else None
    return isinstance(result, dict) and result.get("shutdown") is True


def _is_arcade_action(request: dict) -> bool:
    action = request.get("action")
    return isinstance(action, dict) and action.get("type") in {
        "arcade_tick", "arcade_toggle_flight", "arcade_set_movement_mode",
    }


def _process(host: HSRHost, request: dict) -> tuple[dict, bool]:
    global _last_auto_steps
    _last_auto_steps = 0
    command = request.get("command")
    response = host.handle(request)
    run_id = request.get("run_id")
    # Arcade ticks are fixed-cadence frame updates, not tactical turns. The
    # normal bridge auto-drain would incorrectly let an NPC consume a
    # turn-sized decision between two client frames.
    if (command in TURN_COMMANDS and not _is_arcade_action(request)
            and response.get("ok") and isinstance(run_id, str)):
        auto_events = _auto_drain_npc_turns(host, run_id)
        _last_auto_steps = len(auto_events)  # compact capsules drop the raw list
        if auto_events:
            response = dict(response)
            response["auto_resolved"] = auto_events
            last = auto_events[-1]
            if last.get("ok"):
                response["settled_state"] = last.get("result", {}).get("state")
    # The watcher may have advanced NPCs after the submitted turn. Project
    # the final public frame through the host instead of shipping stale UI state.
    if response.get("auto_resolved"):
        final = host.handle({"id": "settled-readout", "command": "readout",
                             "run_id": run_id, "public_only": True})
        if final.get("ok"):
            readout = final["result"]["readout"]
            body = response.setdefault("result", {})
            target = body.get("turn", body)
            target["public_view"] = readout["public_view"]
            target["public_receipt"] = readout.get("public_receipt", {})
        else:
            response["settled_error"] = final.get("error", {})
    compact = request.get("compact", command in {"design_turn", "readout"})
    if compact and command in {"design_turn", "readout"}:
        projected = capsule(response, request=request)
        if response.get("settled_error"):
            projected["settled_error"] = response["settled_error"]
        return projected, _is_shutdown_response(response)
    return response, _is_shutdown_response(response)


def _reply_line(req_id: str, request: dict, response: dict, elapsed_ms: float, auto_steps: int) -> str:
    line = f"<- {_clip(req_id)} {_clip(request.get('command'), 60)} ok={response.get('ok')} {elapsed_ms:.1f}ms"
    if auto_steps:
        line += f" (+{auto_steps} auto)"
    if not response.get("ok"):
        line += " " + _error_text(response)
    return line


def _advance_life_worlds(host: HSRHost, now: float, last_tick: dict[str, float]) -> None:
    """Let active Floor One worlds advance through the host, never watcher math."""
    service = host._run_service
    if not host.booted or service is None:
        return
    for run_id, run in list(service._active.items()):
        if not isinstance(run.context.get("life_world"), dict):
            continue
        previous = last_tick.get(run_id, now)
        elapsed = int(now - previous)
        if elapsed < LIFE_TICK_SECONDS:
            continue
        elapsed = min(elapsed, LIFE_TICK_SECONDS * 120)
        result = host.handle({"id": f"life-tick:{run_id}:{int(now)}", "command": "design_action",
                              "run_id": run_id, "action": {"type": "world_tick", "elapsed_seconds": elapsed}})
        if result.get("ok"):
            last_tick[run_id] = now
            _log(f"life tick {run_id}: {elapsed}s")
        else:
            _log(f"life tick failed {run_id}: {result.get('error', {}).get('code', 'unknown')}")


@contextmanager
def _watcher_lock(path: Path):
    """OS-owned workspace lock; released even when the process exits abruptly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("HSR watcher is already running for this workspace") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def main() -> int:
    with _watcher_lock(BRIDGE_DIR / "watcher.lock"):
        return _watch()


def _watch() -> int:
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    host = HSRHost.from_options()
    health = host.handle({"id": "startup-health", "command": "health"})
    location = health.get("result", {}).get("local_location", {})
    _log(f"HSR bridge watcher starting. pid={os.getpid()} workspace={location.get('workspace_root')} "
         f"approved={location.get('approved')}")
    if not location.get("approved"):
        _log("WARNING: local_location.approved is False -- boot/design commands will fail closed "
             "until this runs from the real desktop workspace, not a mounted/bridged copy of it.")

    validation = host.handle({"id": "startup-handshake", "command": "validate", "target": "handshake"})
    if not location.get("approved") or not validation.get("ok"):
        _log("startup refused: approved desktop and current handshake required")
        return 1

    answered_ids = {row.get("id") for row in _read_jsonl(OUTBOX) if row.get("id")}
    inbox_offset = 0
    last_life_tick: dict[str, float] = {}
    last_beat = time.monotonic()
    last_activity = last_beat - HOT_WINDOW_SECONDS
    try:
        _write_watcher_info()
    except OSError as exc:
        _log(f"WARNING: could not write watcher.json ({exc}); launchers will treat this watcher as outdated")
    _log(f"watcher pid {os.getpid()} watching {INBOX} (host update every {POLL_SECONDS}s) -- Ctrl+C to stop")
    try:
        while True:
            rows, inbox_offset = _read_jsonl_from(INBOX, inbox_offset)
            new_requests = [row for row in rows if row["id"] not in answered_ids]
            if not new_requests:
                hot = time.monotonic() - last_activity < HOT_WINDOW_SECONDS
                time.sleep(HOT_POLL_SECONDS if hot else POLL_SECONDS)
                _advance_life_worlds(host, time.time(), last_life_tick)
                if time.monotonic() - last_beat >= HEARTBEAT_SECONDS:
                    last_beat = time.monotonic()
                    _log(f"idle, {len(answered_ids)} request(s) answered so far")
                continue
            for request in new_requests:
                req_id = request["id"]
                if req_id in answered_ids:
                    continue
                _log(f"-> {_clip(req_id)} {_describe_request(request)}")
                began = time.perf_counter()
                expires_at = request.pop("expires_at", None)
                if isinstance(expires_at, (int, float)) and time.time() > expires_at:
                    # Its sender stopped waiting; running it now would act on nobody's behalf.
                    response = {"id": req_id, "ok": False, "type": "error", "error": {
                        "code": "REQUEST_EXPIRED", "message": "picked up after its sender stopped waiting; not executed"}}
                    stop_requested, auto_steps = False, 0
                else:
                    try:
                        response, stop_requested = _process(host, request)
                        auto_steps = _last_auto_steps
                    except Exception as exc:  # noqa: BLE001 - always answer, never die silently
                        response = {
                            "id": req_id, "ok": False, "type": "error",
                            "error": {"code": "BRIDGE_EXCEPTION", "message": str(exc)},
                        }
                        stop_requested, auto_steps = False, 0
                        _log(f"!! exception handling {req_id}: {exc!r}")
                elapsed_ms = (time.perf_counter() - began) * 1000
                _append_jsonl(OUTBOX, response)
                answered_ids.add(req_id)
                _log(_reply_line(req_id, request, response, elapsed_ms, auto_steps))
                if stop_requested:
                    _log("stopped by shutdown request")
                    return 0
            last_activity = last_beat = time.monotonic()  # heartbeat means a full idle minute
    except KeyboardInterrupt:
        _log("stopped")
    finally:
        _clear_watcher_info()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
