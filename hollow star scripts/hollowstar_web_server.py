"""Local browser adapter: static presentation plus the existing HSRHost JSON contract."""
from __future__ import annotations

import atexit
import hashlib
import json
import argparse
import math
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
from collections import deque
from urllib.parse import urlsplit, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from hollowstar.host import HSRHost
from hollowstar.session_intent import vocabulary
from hollowstar.hosted_controls import HostedControls
from hollowstar.transfer import capsule

ROOT = Path(__file__).resolve().parent
_startup_lock = threading.Lock()
_host = None  # the one in-process HSRHost every request is served from
# ThreadingHTTPServer runs each request on its own thread, and the life-tick
# loop runs on another. HSRHost is not thread-safe (session cache, companion
# memory, active-run dicts), so every call into it is serialized here.
# Re-entrant so a handler that re-enters the host on the same thread is safe.
_host_lock = threading.RLock()
_server = None  # set once main() binds the port; lets a dead engine stop the host itself
_shutting_down = threading.Event()
_hosted_controls = HostedControls(ROOT / ".local" / "hosted_controls.json")

STATS_SECONDS = 20
# How often an active Floor One life-sim world advances on its own, so time
# keeps passing while nobody is actively taking a turn.
LIFE_TICK_SECONDS = 30
# Digest of the code this host loaded; the launcher refuses to reuse an older host.
SERVER_SHA256 = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
# Request-body ceilings: 1 MiB and 8 KiB, each raised by 30% (rounded down)
# on 2026-09-23.
MAX_REQUEST_BYTES = 1_363_148
MAX_CLIENT_LOG_BYTES = 10_649

_startup = {}
_began = time.monotonic()
_stats_lock = threading.Lock()
_stats = {"requests": 0, "errors": 0, "total_ms": 0.0, "max_ms": 0.0, "fresh": False}
_recent_ms = deque(maxlen=1000)
_console = queue.Queue(maxsize=4000)
_console_lock = threading.Lock()
_console_thread = None
_console_dropped = 0


def _say(message):
    """Queue one console line; a stalled or closed console never blocks a request."""
    global _console_thread, _console_dropped
    if _console_thread is None:
        with _console_lock:
            if _console_thread is None:
                _console_thread = threading.Thread(target=_console_writer, name="hsr-console", daemon=True)
                _console_thread.start()
                # Drain before interpreter shutdown; a daemon thread still inside
                # print() at finalization aborts the process with a fatal error.
                atexit.register(_flush_console)
    try:
        _console.put_nowait(message)
    except queue.Full:
        _console_dropped += 1


def _console_writer():
    global _console_dropped
    while True:
        message = _console.get()
        if _console_dropped:
            dropped, _console_dropped = _console_dropped, 0
            message = f"[web] {dropped} console line(s) dropped while output was stalled\n{message}"
        try:
            print(message, flush=True)
        except (OSError, ValueError):
            pass
        _console.task_done()


def _flush_console(timeout=1.0):
    deadline = time.monotonic() + timeout
    while _console.unfinished_tasks and time.monotonic() < deadline:
        time.sleep(0.01)


def _clip(value, limit: int = 120) -> str:
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


def _record(ms, ok=True):
    with _stats_lock:
        _stats["requests"] += 1
        _stats["errors"] += not ok
        _stats["total_ms"] += ms
        _stats["max_ms"] = max(_stats["max_ms"], ms)
        _recent_ms.append(ms)
        _stats["fresh"] = True


def _stats_line(force=False):
    """Cumulative request readout, or None when nothing happened since the last one."""
    with _stats_lock:
        if not _stats["requests"] or not (_stats["fresh"] or force):
            return None
        _stats["fresh"] = False
        stats, ordered = dict(_stats), sorted(_recent_ms)

    def rank(q):
        return ordered[max(0, math.ceil(q * len(ordered)) - 1)]
    count, up = stats["requests"], int(time.monotonic() - _began)
    return (f"[web] stats {count} req, {stats['errors']} err | "
            f"round trip ms avg {stats['total_ms'] / count:.1f} p50 {rank(.5):.1f} "
            f"p95 {rank(.95):.1f} max {stats['max_ms']:.1f} | up {up // 3600}:{up // 60 % 60:02d}:{up % 60:02d}")


def _stats_loop(stop):
    while not stop.wait(STATS_SECONDS):
        line = _stats_line()
        if line:
            _say(line)


def _advance_life_worlds(now, last_tick: dict[str, float]) -> None:
    """Let active Floor One worlds advance through the host on their own."""
    with _host_lock:
        service = _host._run_service
        if not _host.booted or service is None:
            return
        active = list(service._active.items())
    for run_id, run in active:
        if not isinstance(run.context.get("life_world"), dict):
            continue
        previous = last_tick.get(run_id, now)
        elapsed = int(now - previous)
        if elapsed < LIFE_TICK_SECONDS:
            continue
        elapsed = min(elapsed, LIFE_TICK_SECONDS * 120)
        with _host_lock:
            result = _host.handle({"id": f"life-tick:{run_id}:{int(now)}", "command": "design_action",
                                   "run_id": run_id, "action": {"type": "world_tick", "elapsed_seconds": elapsed}})
        if result.get("ok"):
            last_tick[run_id] = now
            _say(f"[web] life tick {run_id}: {elapsed}s")
        else:
            _say(f"[web] life tick failed {run_id}: {result.get('error', {}).get('code', 'unknown')}")


def _life_tick_loop(stop):
    last_tick: dict[str, float] = {}
    while not stop.wait(LIFE_TICK_SECONDS):
        _advance_life_worlds(time.time(), last_tick)


def start_engine(data_root=None):
    """Serialize startup so a concurrent request cannot race host construction."""
    with _startup_lock:
        return _start_engine(data_root=data_root)


def _start_engine(data_root=None):
    global _host
    # The launcher's passing check covers the first start only; a manual
    # restart re-runs it.
    if os.environ.pop("HSR_LOCAL_CHECK_DONE", "") == "1":
        checked = "skipped (launcher already passed it)"
    else:
        check = subprocess.run([sys.executable, "hollowstar_host.py", "local-check"],
                               cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        if check.returncode:
            raise RuntimeError("HSR local-check failed: " + (check.stdout + check.stderr).strip())
        checked = "ran and passed"
    _host = HSRHost.from_options(data_root=data_root or ROOT / ".local")
    _startup.update(engine="in-process HSRHost", local_check=checked)
    _say(f"[web] engine: in-process HSRHost | local-check {checked}")


def _engine(request, route="POST /api/host"):
    command = _clip(request.get("command"), 60)
    _say(f"[web] IN  {route} {_describe_request(request)}")
    began = time.perf_counter()
    try:
        with _host_lock:
            result = _host.handle(request)
    except Exception as exc:
        ms = (time.perf_counter() - began) * 1000
        _record(ms, ok=False)
        _say(f"[web] OUT {route} {command} failed {type(exc).__name__}: {_clip(str(exc))} {ms:.1f}ms")
        raise
    ms = (time.perf_counter() - began) * 1000
    ok = bool(result.get("ok"))
    _record(ms, ok=ok)
    _say(f"[web] OUT {route} {command} {'ok' if ok else 'ERR ' + _error_text(result)} {ms:.1f}ms")
    # design_turn/readout are sent through the narrator-safe capsule by
    # default: it is the one thing standing between the browser and a raw
    # dump of visible_state, which is debug/audit-only and never narrator
    # source. A caller may opt out with an explicit "compact": false.
    compact = request.get("compact", command in {"design_turn", "readout"})
    if compact and command in {"design_turn", "readout"}:
        return capsule(result, request=request)
    return result


class Handler(BaseHTTPRequestHandler):
    # Only presentation assets are web-readable. Saves/config/corpus stay local.
    assets = {
        "/": "web/index.html", "/hsr-ui-mockup.html": "hsr-ui-mockup.html",
        "/web/index.html": "web/index.html", "/web/manifest.webmanifest": "web/manifest.webmanifest",
        "/web/assets/favicon.svg": "web/assets/favicon.svg", "/web/app.js": "web/app.js",
        "/web/hsr-client.js": "web/hsr-client.js",
        "/web/arcade-canvas.js": "web/arcade-canvas.js",
        "/web/arcade-input.js": "web/arcade-input.js",
        "/web/arcade-loop.js": "web/arcade-loop.js",
        "/web/sprite-renderer.js": "web/sprite-renderer.js",
        "/web/fx-engine.js": "web/fx-engine.js", "/fx-engine.js": "web/fx-engine.js",
        "/web/puppet-renderer.js": "web/puppet-renderer.js", "/puppet-renderer.js": "web/puppet-renderer.js",
        "/web/puppet-dom.js": "web/puppet-dom.js", "/puppet-dom.js": "web/puppet-dom.js",
        "/web/skeletal-rig.js": "web/skeletal-rig.js", "/skeletal-rig.js": "web/skeletal-rig.js",
        "/web/magic-articulation.js": "web/magic-articulation.js", "/magic-articulation.js": "web/magic-articulation.js",
        "/web/traversal-controller.js": "web/traversal-controller.js", "/traversal-controller.js": "web/traversal-controller.js",
        "/web/paperdoll.js": "web/paperdoll.js", "/paperdoll.js": "web/paperdoll.js",
        "/web/combat-director.js": "web/combat-director.js", "/combat-director.js": "web/combat-director.js",
        "/web/voice-feed.js": "web/voice-feed.js", "/voice-feed.js": "web/voice-feed.js",
        "/web/tokens.css": "web/tokens.css", "/tokens.css": "web/tokens.css",
        "/web/stage.css": "web/stage.css", "/stage.css": "web/stage.css",
        "/web/styles.css": "web/styles.css",
        "/app.js": "web/app.js", "/hsr-client.js": "web/hsr-client.js",
        "/arcade-canvas.js": "web/arcade-canvas.js", "/arcade-input.js": "web/arcade-input.js",
        "/arcade-loop.js": "web/arcade-loop.js", "/sprite-renderer.js": "web/sprite-renderer.js",
        "/styles.css": "web/styles.css", "/character-creation.css": "web/character-creation.css",
        "/visual-character-creation.css": "web/visual-character-creation.css",
        "/ui-components.js": "web/ui-components.js", "/ui-components.css": "web/ui-components.css",
    }

    presentation_assets = (
        "content-workbench.html", "content-workbench.js", "content-workbench.css",
        "content-package-example.json", "content-package.schema.json",
        "tokens.css", "stage.css", "ui-components.js", "ui-components.css", "ui-polish.js", "character-creation.css", "visual-character-creation.css", "item-preview.json",
        "magic-articulation.js", "puppet-renderer.js", "puppet-dom.js", "fx-engine.js", "skeletal-rig.js", "traversal-controller.js", "visual-armory.json",
        "doran-rig.js", "doran-combat.js", "wren-rig.js", "battle-scene.js", "expedition-map.js", "battle.css",
        "assets/favicon.svg", "manifest.webmanifest", "assets/townsperson.png", "assets/longsword.png", "assets/chain-shirt.png",
        "assets/unidentified-rune.png", "assets/character-sprite-sheet.png", "assets/npc-portrait-sheet.png", "assets/art-manifest.json",
        "assets/sprites/layers/cloak.svg", "assets/sprites/layers/headgear.svg",
        "assets/sprites/layers/shield.svg", "assets/sprites/layers/trinket.svg",
        "assets/sprites/layers/cloak-v1.png", "assets/sprites/layers/headgear-v1.png",
        "assets/sprites/layers/shield-v1.png", "assets/sprites/layers/trinket-v1.png",
        # Doran's retired frame art. He draws through web/doran-rig.js now
        # (2026-09-23); the files stay served while they remain on disk.
        *(f"assets/sprites/characters/doran/doran-{pose}.png"
          for pose in ("guard", "overhead-strike", "sweep", "rest", "low-ready")),
        *(f"assets/sprites/characters/{race}-{variant}.png"
          for race in ("human", "elf", "half-elf", "orc", "goblin")
          for variant in ("female", "male")),
    )
    assets.update({"/web/" + name: "web/" + name for name in presentation_assets})
    assets.update({"/" + name: "web/" + name for name in presentation_assets})

    # Discover and allow any presentation assets inside web/
    _web_dir = ROOT / "web"
    if _web_dir.is_dir():
        for _p in _web_dir.rglob("*"):
            if _p.is_file():
                _rel = _p.relative_to(_web_dir).as_posix()
                assets.setdefault("/web/" + _rel, "web/" + _rel)
                assets.setdefault("/" + _rel, "web/" + _rel)

    def _json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Host-Time", str(int(time.time() * 1000)))
        self.end_headers()
        self.wfile.write(data)

    def _trusted_origin(self):
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in allowed:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {"http://" + host for host in allowed}

    def _safe_error(self, status, code, message):
        """Best-effort JSON error; swallowed if the connection is already gone."""
        try:
            self._json({"ok": False, "error": {"code": code, "message": message}}, status)
        except Exception:
            pass

    def _hosted_request(self):
        """Authenticate and authorize one desktop-connected Hosted Controls call."""
        if not self._trusted_origin():
            self._safe_error(403, "HOSTED_ORIGIN_REJECTED", "Hosted Controls accepts only the local desktop connector")
            return
        client = self.headers.get("X-HSR-Client", "").strip().lower()
        token = self.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token[7:].strip()
        ok, code = _hosted_controls.authenticate(client, token)
        if not ok:
            self._safe_error(401, code, "Hosted Controls credentials were rejected")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= MAX_REQUEST_BYTES:
                raise ValueError("Request body must be between 1 byte and 1.3 MiB")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("Request must be an object")
            request_id = request.get("id")
            if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 256:
                raise ValueError("Request requires a nonempty string id")
            replay = _hosted_controls.replay(client, request_id)
            if replay is not None:
                self._json(replay)
                return
            command = request.get("command")
            if command == "hosted_capabilities":
                result = {"id": request_id, "ok": True, "result": {"hosted_controls": _hosted_controls.capabilities()}}
            elif command == "hosted_lease":
                valid, error, detail = _hosted_controls.lease(client, str(request.get("run_id", "")), str(request.get("operation", "")))
                result = {"id": request_id, "ok": valid}
                result["result" if valid else "error"] = detail if valid else {"code": error, "details": detail}
            else:
                valid, error, detail = _hosted_controls.authorize(client, request)
                if not valid:
                    result = {"id": request_id, "ok": False, "error": {"code": error, "details": detail}}
                else:
                    wire = {**request, "id": "hosted-" + uuid.uuid4().hex, "public_only": True}
                    result = _engine(wire, route="POST /api/hosted")
                    result["id"] = request_id
                    result.setdefault("hosted", {})
                    result["hosted"].update({"client": client, "transport": "hosted-controls", "lease": detail})
            _hosted_controls.remember(client, request_id, result)
            self._json(result, 200 if result.get("ok") else 409)
        except (ValueError, OSError) as exc:
            self._safe_error(400, "INVALID_REQUEST", str(exc))

    NETWORK_ERRORS = (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, TimeoutError)

    def do_GET(self):
        try:
            self._route_get()
        except self.NETWORK_ERRORS:
            pass  # the client went away mid-response; nothing left to send
        except Exception as exc:
            _say(f"[web] ERROR GET {_clip(self.path)}: {type(exc).__name__}: {_clip(str(exc))}")
            _say(_clip(traceback.format_exc(), 4000))
            self._safe_error(500, "INTERNAL_ERROR", str(exc))

    def do_POST(self):
        try:
            self._route_post()
        except self.NETWORK_ERRORS:
            pass
        except Exception as exc:
            _say(f"[web] ERROR POST {_clip(self.path)}: {type(exc).__name__}: {_clip(str(exc))}")
            _say(_clip(traceback.format_exc(), 4000))
            self._safe_error(500, "INTERNAL_ERROR", str(exc))

    def _handle_client_log(self):
        """Sink for browser-side errors, so a client-only crash still shows up
        in this console instead of only in DevTools no one has open."""
        if not self._trusted_origin():
            _say(f"[web] 403 POST {_clip(self.path)}")
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= MAX_CLIENT_LOG_BYTES:
                raise ValueError("Request body must be between 1 byte and 10.4 KiB")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Request must be an object")
        except (ValueError, OSError) as exc:
            self._safe_error(400, "INVALID_REQUEST", str(exc))
            return
        level = payload.get("level") if payload.get("level") in {"error", "warn"} else "error"
        message = _clip(payload.get("message", ""), 500)
        where = _clip(payload.get("where", ""), 200)
        _say(f"[client] {level}: {message}" + (f" ({where})" if where else ""))
        self._json({"ok": True})

    def _route_get(self):
        if not self._trusted_origin():
            _say(f"[web] 403 GET {_clip(self.path)}")
            self.send_error(403)
            return
        route = urlsplit(self.path)
        if route.path == "/api/ui":
            _say("[web] GET /api/ui")
            self._json({"schema": "hsr-ui-manifest-1", "name": "HSR Interface", "version": "2026-09-13",
                "primary": "/", "compact": "/web/index.html",
                "screens": ["room", "battle", "equipment", "roster", "residents", "journal", "map", "library", "create", "options"],
                "encounter_modes": {"turn_based": "tactical host actions", "arcade": "fixed-cadence host frames with public interpolation"},
                "screen_reference": "/#<screen>", "health": "/api/health",
                "public_readout": "/api/readout?run_id=<id>", "host": "/api/host",
                "public_schema": "hollow-star-public-view-1",
                "affix_catalog": "/api/affixes",
                "content_catalog": "/api/content",
                "browser_reference": "window.HollowStarUI", "session_vocabulary": "/api/session/vocabulary",
                "item_fields": ["name", "display_name", "slot", "tier", "base_damage", "damage_dice", "base_ac", "prefix", "suffix", "inherent", "modifiers", "appearance"],
                "assets": "/web/assets/art-manifest.json", "server_sha256": SERVER_SHA256})
            return
        if route.path == "/api/session/vocabulary":
            _say("[web] GET /api/session/vocabulary")
            self._json({"ok": True, "result": vocabulary()})
            return
        if route.path == "/api/affixes":
            self._json(_engine({"id": "http-get-" + uuid.uuid4().hex,
                                "command": "affix_catalog"}, route="GET /api/affixes"))
            return
        if route.path == "/api/content":
            self._json(_engine({"id": "http-get-" + uuid.uuid4().hex,
                                "command": "content_catalog"}, route="GET /api/content"))
            return
        if route.path == "/api/capabilities":
            self._json(_engine({"id": "http-get-" + uuid.uuid4().hex, "command": "inspect",
                                "target": "capabilities"}, route="GET /api/capabilities"))
            return
        if route.path in {"/api/health", "/api/readout"}:
            request = {"id": "http-get-" + uuid.uuid4().hex, "command": "health"}
            if route.path == "/api/readout":
                run_id = parse_qs(route.query).get("run_id", [""])[0]
                if not run_id.strip() or len(run_id) > 256:
                    _say("[web] GET /api/readout rejected: RUN_ID_REQUIRED")
                    self._json({"ok": False, "error": {"code": "RUN_ID_REQUIRED"}}, 400)
                    return
                request.update(command="readout", run_id=run_id, public_only=True, compact=False)
            try:
                result = _engine(request, route="GET " + route.path)
            except OSError:
                result = {"ok": False, "error": {"code": "ENGINE_UNAVAILABLE"}}
            self._json(result, 200 if result.get("ok") else 503)
            return
        clean_path = route.path.split("?", 1)[0]
        rel = self.assets.get(clean_path)
        if rel is None:
            # Safe runtime fallback: resolve strictly within web/
            candidate = clean_path.removeprefix("/web").lstrip("/")
            web_file = (ROOT / "web" / candidate).resolve()
            try:
                web_file.relative_to((ROOT / "web").resolve())
                if web_file.is_file():
                    rel = "web/" + web_file.relative_to((ROOT / "web").resolve()).as_posix()
            except ValueError:
                pass
        if rel is None or not (ROOT / rel).is_file():
            _say(f"[web] 404 GET {_clip(self.path)}")
            self.send_error(404)
            return
        path = ROOT / rel
        data = path.read_bytes()
        kind = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml",
                ".webmanifest": "application/manifest+json; charset=utf-8",
                ".json": "application/json; charset=utf-8"}.get(path.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _route_post(self):
        if self.path == "/api/client-log":
            self._handle_client_log()
            return
        if self.path == "/api/hosted":
            self._hosted_request()
            return
        if self.path != "/api/host":
            _say(f"[web] 404 POST {_clip(self.path)}")
            self.send_error(404)
            return
        if not self._trusted_origin():
            _say(f"[web] 403 POST {_clip(self.path)}")
            self.send_error(403)
            return
        request_id = None
        try:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= MAX_REQUEST_BYTES:
                raise ValueError("Request body must be between 1 byte and 1.3 MiB")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("Request must be an object")
            request_id = request.get("id")
            if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 256:
                raise ValueError("Request requires a nonempty string id of at most 256 characters")
            if not isinstance(request.get("command"), str):
                raise ValueError("Request requires a command")
            # A fresh internal id per call keeps concurrent CLI/MCP/browser
            # callers that reuse the same client-side id from colliding in
            # the console log or in any host-side per-id bookkeeping.
            wire = {**request, "id": "http-" + uuid.uuid4().hex}
            result = _engine(wire)
            result["id"] = request_id
            if request.get("command") == "shutdown" and result.get("ok"):
                # Let the HTTP response reach the caller before stopping the
                # server.  This is the clean-exit path owned by the launcher.
                _shutting_down.set()
                threading.Thread(target=self.server.shutdown, daemon=True).start()
        except (ValueError, OSError) as exc:
            _say(f"[web] POST /api/host rejected INVALID_REQUEST: {_clip(str(exc))}")
            result = {"id": request_id, "ok": False, "error": {"code": "INVALID_REQUEST", "message": str(exc)}}
        data = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


class LoopbackServer(ThreadingHTTPServer):
    """Claims its port exclusively. On Windows, SO_REUSEADDR lets a second host
    bind the same port beside the first, and requests then land on either one."""
    allow_reuse_address = os.name != "nt"
    allow_reuse_port = False
    daemon_threads = True  # a request thread still running at exit must never block it

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def handle_error(self, request, client_address):
        """Replace socketserver's raw stderr traceback dump with one line
        routed through the same console queue as everything else -- quiet
        for an ordinary disconnect, still fully visible for a real bug."""
        exc_type = sys.exc_info()[0]
        if exc_type is not None and issubclass(exc_type, Handler.NETWORK_ERRORS):
            _say(f"[web] client {client_address} disconnected mid-request")
            return
        _say(f"[web] ERROR handling request from {client_address}:")
        _say(_clip(traceback.format_exc(), 4000))


def main():
    global _server
    parser = argparse.ArgumentParser(description="Hollow Star loopback web host")
    parser.add_argument("--data-root", type=Path, default=ROOT / ".local",
                        help="override host data root (useful for isolated runs and tests)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("HSR_WEB_PORT", "8765")),
                        help="loopback port (default: HSR_WEB_PORT or 8765)")
    args = parser.parse_args()
    began = time.monotonic()
    try:
        try:
            # Bind before booting the engine so a second web launcher cannot
            # race this one for the port.
            server = LoopbackServer(("127.0.0.1", args.port), Handler)
        except OSError as exc:
            _say(f"[web] could not bind port {args.port}: {exc}")
            _say("[web] a previous Hollow Star process may still be holding this port; "
                 "end any lingering python.exe for this workspace and try again")
            return 1
        _server = server
        with server:
            start_engine(data_root=args.data_root)
            _say(f"HSR 2D client: http://127.0.0.1:{args.port}")
            _say(f"[web] ready on port {server.server_port} in {(time.monotonic() - began) * 1000:.0f} ms"
                 f" | stats every {STATS_SECONDS}s while active")
            stop = threading.Event()
            threading.Thread(target=_stats_loop, args=(stop,), name="hsr-stats", daemon=True).start()
            threading.Thread(target=_life_tick_loop, args=(stop,), name="hsr-life-tick", daemon=True).start()
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                _shutting_down.set()
                _say("HSR server interrupted")
            finally:
                _shutting_down.set()
                stop.set()
                final = _stats_line(force=True)
                if final:
                    _say(final)
                _say("HSR server stopped")
    finally:
        _flush_console()


if __name__ == "__main__":
    raise SystemExit(main())
