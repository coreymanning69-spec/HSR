"""Adversarial mailbox and single-watcher boundary checks."""
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import hsr_bridge_watch as bridge


def test_mailbox_rejects_invalid_ids_objects_and_partial_lines():
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "inbox.jsonl"
        path.write_bytes(b'[]\nnull\n{"id":[]}\n{"id":3}\n{"id":""}\n\xff\n'
                         b'{"id":"valid","command":"health"}\n{"id":"partial"}')
        with patch.object(bridge, "_log"):
            assert bridge._read_jsonl(path) == [{"id": "valid", "command": "health"}]
        with path.open("ab") as handle:
            handle.write(b"\n")
        with patch.object(bridge, "_log"):
            assert len(bridge._read_jsonl(path)) == 2


def test_oversized_line_does_not_hide_next_request():
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "inbox.jsonl"
        path.write_bytes(b"x" * (bridge.MAX_LINE_BYTES + 10) + b'\n{"id":"next"}\n')
        with patch.object(bridge, "_log"):
            assert bridge._read_jsonl(path) == [{"id": "next"}]


def test_lock_refuses_second_watcher_and_releases():
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "watcher.lock"
        with bridge._watcher_lock(path):
            try:
                with bridge._watcher_lock(path):
                    raise AssertionError("second watcher acquired the lock")
            except RuntimeError:
                pass
        with bridge._watcher_lock(path):
            pass


def test_duplicate_batch_executes_once():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        inbox, outbox = root / "inbox.jsonl", root / "outbox.jsonl"
        inbox.write_text('{"id":"one","command":"health"}\n' * 2, encoding="utf-8")
        class Host:
            def handle(self, request):
                return {"ok": True, "result": {"local_location": {"approved": True}}}
        with patch.object(bridge, "BRIDGE_DIR", root), patch.object(bridge, "INBOX", inbox), \
             patch.object(bridge, "OUTBOX", outbox), patch.object(bridge, "_log"), \
             patch.object(bridge.HSRHost, "from_options", return_value=Host()), \
             patch.object(bridge, "_process", return_value=({"id":"one", "ok":True}, False)) as process, \
             patch.object(bridge.time, "sleep", side_effect=KeyboardInterrupt):
            assert bridge._watch() == 0
            assert process.call_count == 1
        assert len(outbox.read_text().splitlines()) == 1


def test_invalid_handshake_refuses_startup():
    with tempfile.TemporaryDirectory() as raw:
        class Host:
            def handle(self, request):
                return {"ok": request["command"] == "health", "result": {"local_location": {"approved": True}}}
        with patch.object(bridge, "BRIDGE_DIR", Path(raw)), patch.object(bridge, "_log"), \
             patch.object(bridge.HSRHost, "from_options", return_value=Host()), \
             patch.object(bridge, "_read_jsonl") as read:
            assert bridge._watch() == 1
            read.assert_not_called()


def test_shutdown_request_writes_response_and_stops_watcher():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        inbox, outbox = root / "inbox.jsonl", root / "outbox.jsonl"
        inbox.write_text('{"id":"stop","command":"shutdown"}\n', encoding="utf-8")

        class Host:
            def handle(self, request):
                if request["command"] == "health":
                    return {"ok": True, "result": {"local_location": {"approved": True}}}
                if request["command"] == "validate":
                    return {"ok": True, "result": {}}
                return {"id": request["id"], "ok": True, "result": {"shutdown": True}}

        with patch.object(bridge, "BRIDGE_DIR", root), patch.object(bridge, "INBOX", inbox), \
             patch.object(bridge, "OUTBOX", outbox), patch.object(bridge, "_log") as log, \
             patch.object(bridge.HSRHost, "from_options", return_value=Host()):
            assert bridge._watch() == 0

        rows = [json.loads(line) for line in outbox.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 1
        assert rows[0]["ok"] is True
        assert any("stopped by shutdown request" in str(call.args[0]) for call in log.call_args_list)


def test_offset_reader_holds_partial_line_until_complete():
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "inbox.jsonl"
        path.write_bytes(b'{"id":"one"}\n{"id":"two"')
        with patch.object(bridge, "_log"):
            rows, offset = bridge._read_jsonl_from(path, 0)
            assert rows == [{"id": "one"}] and offset == len(b'{"id":"one"}\n')
            assert bridge._read_jsonl_from(path, offset) == ([], offset)
            with path.open("ab") as handle:
                handle.write(b'}\n{"id":"three"}\n')
            rows, offset = bridge._read_jsonl_from(path, offset)
            assert rows == [{"id": "two"}, {"id": "three"}]
            assert offset == path.stat().st_size


def test_offset_reader_restarts_after_truncation():
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "inbox.jsonl"
        path.write_bytes(b'{"id":"old-one"}\n{"id":"old-two"}\n')
        with patch.object(bridge, "_log"):
            rows, offset = bridge._read_jsonl_from(path, 0)
            assert len(rows) == 2
            path.write_bytes(b'{"id":"new"}\n')
            assert bridge._read_jsonl_from(path, offset) == ([{"id": "new"}], path.stat().st_size)
            assert bridge._read_jsonl_from(Path(raw) / "missing.jsonl", offset) == ([], 0)


def test_log_survives_closed_console():
    with tempfile.TemporaryDirectory() as raw:
        log = Path(raw) / "watch.log"
        console = io.StringIO()
        console.close()
        with patch.object(bridge, "LOG", log), patch.object(bridge.sys, "stdout", console):
            bridge._log("still answering")
        assert "still answering" in log.read_text(encoding="utf-8")


def test_watcher_info_names_current_source_and_pid():
    with tempfile.TemporaryDirectory() as raw:
        with patch.object(bridge, "BRIDGE_DIR", Path(raw)):
            bridge._write_watcher_info()
        info = json.loads((Path(raw) / "watcher.json").read_text(encoding="utf-8"))
    assert info["pid"] == os.getpid() and info["poll_seconds"] == bridge.POLL_SECONDS
    assert info["source_sha256"] == bridge._source_sha256()


def test_source_sha256_covers_the_hollowstar_package_not_just_this_file():
    """A watcher answers with whatever hollowstar/*.py it loaded at import time.
    If the staleness digest only covered this file, editing the engine package
    a watcher already has in memory would never be detected as stale, and a
    launcher would keep reusing that watcher's old code forever. Uses an
    isolated fixture root -- never the real hollowstar/ package -- so this
    test cannot touch real source under any failure mode."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "hsr_bridge_watch.py").write_bytes(Path(bridge.__file__).read_bytes())
        engine_dir = root / "hollowstar"
        engine_dir.mkdir()
        module = engine_dir / "run_service.py"
        module.write_text("SCHEMA_VERSION = 1\n", encoding="utf-8")
        with patch.object(bridge, "HSR_ROOT", root), patch.object(bridge, "__file__", str(root / "hsr_bridge_watch.py")):
            baseline = bridge._source_sha256()
            module.write_text("SCHEMA_VERSION = 2\n", encoding="utf-8")
            assert bridge._source_sha256() != baseline


def test_expired_request_is_answered_but_never_executed():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        inbox, outbox = root / "inbox.jsonl", root / "outbox.jsonl"
        inbox.write_text('{"id":"stale","command":"shutdown","expires_at":1}\n'
                         '{"id":"stop","command":"shutdown"}\n', encoding="utf-8")
        executed = []

        class Host:
            def handle(self, request):
                if request["command"] == "health":
                    return {"ok": True, "result": {"local_location": {"approved": True}}}
                if request["command"] == "validate":
                    return {"ok": True, "result": {}}
                executed.append(request)
                return {"id": request["id"], "ok": True, "result": {"shutdown": True}}

        with patch.object(bridge, "BRIDGE_DIR", root), patch.object(bridge, "INBOX", inbox), \
             patch.object(bridge, "OUTBOX", outbox), patch.object(bridge, "_log"), \
             patch.object(bridge.HSRHost, "from_options", return_value=Host()):
            assert bridge._watch() == 0
        rows = [json.loads(line) for line in outbox.read_text(encoding="utf-8").splitlines()]
    assert [row["id"] for row in rows] == ["stale", "stop"]
    assert rows[0]["error"]["code"] == "REQUEST_EXPIRED" and rows[1]["ok"] is True
    assert [request["id"] for request in executed] == ["stop"]
    assert "expires_at" not in executed[0]
