"""Launch the local HSR web client as a standalone Windows app window."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import argparse
import json
import logging
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = int(os.environ.get("HSR_WEB_PORT", "8765"))
PROFILE = ROOT / ".local" / "app-profile"
LOG_DIR = ROOT / ".local" / "logs"

# The first-party desktop composition is measured from Corey's 3840 x 2160
# reference: a 3132 x 1569 outer window at (423, 211).  Ratios keep the same
# generous, cinematic footprint on smaller displays and across Windows DPI
# scaling without baking a 4K-only pixel size into the launcher.
WINDOW_WIDTH_RATIO = 3132 / 3839
WINDOW_HEIGHT_RATIO = 1569 / 2159
WINDOW_LEFT_RATIO = 423 / 3839
WINDOW_TOP_RATIO = 211 / 2159
MIN_WINDOW_WIDTH = 1180
MIN_WINDOW_HEIGHT = 720


class WindowGeometry(NamedTuple):
    width: int
    height: int
    left: int
    top: int


def _windows_work_area() -> tuple[int, int, int, int] | None:
    """Return the cursor monitor's usable bounds in launcher/logical pixels."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class MonitorInfo(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        user32 = ctypes.windll.user32
        cursor = wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(cursor)):
            monitor = user32.MonitorFromPoint(cursor, 2)  # nearest monitor
            info = MonitorInfo(cbSize=ctypes.sizeof(MonitorInfo))
            if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                work = info.rcWork
                return work.left, work.top, work.right, work.bottom

        # Cursor access can be unavailable in a managed or freshly spawned
        # desktop process. SPI_GETWORKAREA still returns the DPI-virtualized
        # primary work area expected by Chromium's window flags.
        primary = wintypes.RECT()
        if user32.SystemParametersInfoW(48, 0, ctypes.byref(primary), 0):
            return primary.left, primary.top, primary.right, primary.bottom
        return None
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _launch_geometry(work_area: tuple[int, int, int, int] | None = None) -> WindowGeometry | None:
    """Scale the reference composition to the active monitor's work area."""
    bounds = work_area if work_area is not None else _windows_work_area()
    if bounds is None:
        return None
    left, top, right, bottom = bounds
    work_width = max(0, right - left)
    work_height = max(0, bottom - top)
    if work_width < 640 or work_height < 480:
        return None
    width = min(work_width, max(min(MIN_WINDOW_WIDTH, work_width), round(work_width * WINDOW_WIDTH_RATIO)))
    height = min(work_height, max(min(MIN_WINDOW_HEIGHT, work_height), round(work_height * WINDOW_HEIGHT_RATIO)))
    launch_left = left + min(max(0, round(work_width * WINDOW_LEFT_RATIO)), work_width - width)
    launch_top = top + min(max(0, round(work_height * WINDOW_TOP_RATIO)), work_height - height)
    return WindowGeometry(width, height, launch_left, launch_top)


def _python() -> str:
    return sys.executable


def _say(message: str) -> None:
    """Launcher console line; a closed console never stops the game."""
    try:
        print(message, flush=True)
    except (OSError, ValueError):
        pass


def _browser_command(url: str, geometry: WindowGeometry | None = None, kiosk: bool = False) -> list[str] | None:
    geometry = geometry if geometry is not None else _launch_geometry()
    candidates = [
        ("app", shutil.which("msedge")),
        ("app", shutil.which("chrome")),
        ("app", os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe")),
        ("app", os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe")),
        ("app", os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")),
        ("firefox", shutil.which("firefox")),
        ("firefox", os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe")),
        ("firefox", os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe")),
    ]
    for kind, candidate in candidates:
        if candidate and Path(candidate).is_file():
            if kind == "firefox":
                command = [candidate, "--new-window", url]
                if kiosk:
                    command.append("--kiosk")
                elif geometry:
                    command.extend(["-width", str(geometry.width), "-height", str(geometry.height),
                                    "-left", str(geometry.left), "-top", str(geometry.top)])
                return command
            command = [
                candidate,
                f"--app={url}",
                f"--user-data-dir={PROFILE}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-features=Translate,OptimizationHints,MediaRouter,CalculateNativeWinOcclusion",
            ]
            if kiosk:
                command.extend(["--kiosk", "--start-fullscreen"])
            elif geometry:
                command.extend([f"--window-size={geometry.width},{geometry.height}",
                                f"--window-position={geometry.left},{geometry.top}"])
            return command
    return None


def _server_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except OSError:
        return False


def _wait_for_server(process: subprocess.Popen[bytes], url: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("HSR web server exited before becoming ready")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError("HSR web server did not become ready")


def _shutdown(url: str, timeout: float = 5) -> None:
    endpoint = url.split("/web/", 1)[0] + "/api/host"
    payload = json.dumps({"id": "launcher-shutdown", "command": "shutdown"}).encode("utf-8")
    request = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout):
        return


def _server_build(url: str) -> str:
    """Source digest the running web host reports for itself; '' for an older host."""
    try:
        with urllib.request.urlopen(url.split("/web/", 1)[0] + "/api/ui", timeout=2) as response:
            return str(json.load(response).get("server_sha256", ""))
    except (OSError, ValueError, AttributeError):
        return ""


def _retire_outdated_server(url: str) -> bool:
    """True when a web host running older code held the port and has been stopped.

    Reusing it would silently keep the old transport, so it is asked to shut
    down cleanly; if it will not let go of the port, startup stops and says so."""
    current = hashlib.sha256((ROOT / "hollowstar_web_server.py").read_bytes()).hexdigest()
    if _server_build(url) == current:
        return False
    _say("[app] the web host on this port runs older code; asking it to stop")
    deadline = time.monotonic() + 20
    while _server_ready(url):
        if time.monotonic() >= deadline:
            raise RuntimeError(
                "an older Hollow Star web host is still serving this port; close old Hollow Star "
                "windows or end its python process, then launch again"
            )
        try:
            _shutdown(url, timeout=10)
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.2)
    _say("[app] older web host stopped")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the HSR browser app")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="loopback port (default: HSR_WEB_PORT or 8765)")
    parser.add_argument("--kiosk", action="store_true",
                        help="launch in borderless fullscreen kiosk mode without OS window frame")
    parser.add_argument("--fullscreen", action="store_true",
                        help="launch in fullscreen mode")
    args = parser.parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "hsr_app.log"
    logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    url = f"http://127.0.0.1:{args.port}/web/index.html"
    server_args = [_python(), "hollowstar_web_server.py", "--port", str(args.port)]
    server = None
    mirror = None
    try:
        if _server_ready(url) and not _retire_outdated_server(url):
            _say(f"[app] reusing the web host already serving {url}")
        else:
            began = time.monotonic()
            server = subprocess.Popen(
                server_args,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            # Mirror diagnostics to this console and the log without blocking the server pipe.
            def _mirror() -> None:
                assert server is not None and server.stdout is not None
                for line in server.stdout:
                    text = line.rstrip()
                    logging.info("server: %s", text)
                    _say(text)
            mirror = threading.Thread(target=_mirror, daemon=True)
            mirror.start()
            _wait_for_server(server, url)
            _say(f"[app] server ready in {(time.monotonic() - began) * 1000:.0f} ms")
        command = _browser_command(url, kiosk=bool(args.kiosk or args.fullscreen))
        if command is None:
            raise RuntimeError(
                "Microsoft Edge or Google Chrome is required for the standalone app window"
            )
        browser = subprocess.Popen(command, cwd=ROOT)
        _say("[app] game window opened")

        def _terminate_browser() -> None:
            if browser.poll() is None:
                try:
                    browser.terminate()
                except Exception:
                    pass

        import atexit
        atexit.register(_terminate_browser)

        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes
                HandlerRoutine = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
                def _ctrl_handler(dwCtrlType: int) -> bool:
                    _terminate_browser()
                    if server is not None and server.poll() is None:
                        try:
                            server.terminate()
                        except Exception:
                            pass
                    return False
                _win_handler = HandlerRoutine(_ctrl_handler)
                ctypes.windll.kernel32.SetConsoleCtrlHandler(_win_handler, True)
            except Exception:
                pass
        # Watch both ends: a normal exit closes the browser first, but a dead
        # engine/web host must close the game window too, not leave it open
        # and broken with nothing left answering it.
        engine_died = False
        while True:
            if browser.poll() is not None:
                break
            if server is not None and server.poll() is not None:
                engine_died = True
                break
            time.sleep(0.2)
        if engine_died:
            _say("[app] engine/web host stopped unexpectedly; closing game window")
            if browser.poll() is None:
                browser.terminate()
                try:
                    browser.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    browser.kill()
        else:
            _say("[app] game window closed; shutting down")
        # Browser close is the normal game exit.  A failed server remains
        # visible in the log and is never silently treated as a clean exit.
        if server is not None and server.poll() is None:
            try:
                _shutdown(url)
                server.wait(timeout=8)
            except (OSError, TimeoutError, urllib.error.URLError, subprocess.TimeoutExpired) as exc:
                logging.exception("clean shutdown failed: %s", exc)
                _say(f"[app] clean shutdown failed: {exc}")
        if mirror is not None:
            mirror.join(timeout=2)  # let the server's last lines reach the console
        _say("[app] stopped")
        return browser.returncode or 0
    except (OSError, RuntimeError, TimeoutError) as exc:
        logging.exception("HSR app failed: %s", exc)
        print(f"HSR app could not start: {exc}", file=sys.stderr)
        print(f"Diagnostics: {log_path}", file=sys.stderr)
        return 1
    finally:
        # Do not terminate a server here: a crash must leave its diagnostics
        # and process state available for inspection.
        logging.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
