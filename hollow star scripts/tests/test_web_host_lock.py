"""The threaded web server must never run two HSRHost calls at once."""
import threading
import time
from unittest.mock import patch

import hollowstar_web_server as web


class _OverlapDetectingHost:
    """Stand-in host that records whether any two calls ever overlapped."""

    booted = True

    def __init__(self):
        self.inside = 0
        self.max_inside = 0
        self.calls = 0
        self._guard = threading.Lock()

    def handle(self, request):
        with self._guard:
            self.inside += 1
            self.max_inside = max(self.max_inside, self.inside)
        time.sleep(0.002)  # widen the race window
        with self._guard:
            self.inside -= 1
            self.calls += 1
        return {"ok": True, "id": request.get("id")}


def test_engine_serializes_concurrent_host_calls():
    host = _OverlapDetectingHost()
    errors = []

    def worker(n):
        try:
            for i in range(10):
                web._engine({"id": f"{n}:{i}", "command": "health"})
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    with patch.object(web, "_host", host), patch.object(web, "_say", lambda *_: None):
        threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert not errors
    assert host.calls == 80
    assert host.max_inside == 1


def test_host_lock_is_reentrant():
    # A host call that re-enters the engine on the same thread must not deadlock.
    with web._host_lock:
        with web._host_lock:
            pass
