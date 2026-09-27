"""The device-bridge branch of the local-location gate.

A bridge mount cannot have the Windows path shape, so it is approved only
by proving it *is* the approved workspace: same folder name as the
handshake records, live config and snapshot bytes still hashing to the
digests that handshake bound, and a writable data root.  These tests pin
each of those, and pin that a bridge may never rewrite the handshake.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hollowstar.host import HSRHost  # noqa: E402
from hollowstar.paths import resolve_paths  # noqa: E402

WORKSPACE_NAME = "Soliera and Sera v9.0 - The Divine System"


def _mirror(temp: Path, name: str = WORKSPACE_NAME):
    """Build a byte-identical stand-in for a bridge mount of the workspace."""

    real = resolve_paths(WORKSPACE)
    mount = temp / name
    (mount / "hollow star scripts" / "snapshots").mkdir(parents=True)
    (mount / ".local").mkdir()
    config = mount / "hollow star scripts" / "host_config.json"
    snapshot = mount / "hollow star scripts" / "snapshots" / "party_snapshot.json"
    handshake = mount / "hollow star scripts" / "HSR_HANDSHAKE.json"
    shutil.copyfile(real.config_path, config)
    shutil.copyfile(real.snapshot_path, snapshot)
    shutil.copyfile(real.handshake_path, handshake)
    paths = replace(
        real,
        workspace_root=mount,
        config_path=config,
        snapshot_path=snapshot,
        handshake_path=handshake,
        data_root=mount / ".local",
    )
    return paths, config, snapshot, handshake


class BridgeGateTests(unittest.TestCase):
    def test_proven_mount_is_approved_via_bridge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hsr-bridge-") as temp:
            paths, _, _, _ = _mirror(Path(temp))
            report = paths.local_location_report()
            self.assertTrue(report["approved"])
            self.assertEqual(report["via"], "bridge")

    def test_tampered_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hsr-bridge-") as temp:
            paths, _, snapshot, _ = _mirror(Path(temp))
            snapshot.write_bytes(snapshot.read_bytes() + b"\n")
            report = paths.local_location_report()
            self.assertFalse(report["approved"])
            self.assertIn("snapshot_sha256", report["bridge_identity"]["reason"])

    def test_tampered_config_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hsr-bridge-") as temp:
            paths, config, _, _ = _mirror(Path(temp))
            config.write_bytes(config.read_bytes() + b" ")
            report = paths.local_location_report()
            self.assertFalse(report["approved"])
            self.assertIn("config_sha256", report["bridge_identity"]["reason"])

    def test_wrong_workspace_name_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hsr-bridge-") as temp:
            paths, _, _, _ = _mirror(Path(temp), name="Soliera and Sera v8.5")
            report = paths.local_location_report()
            self.assertFalse(report["approved"])
            self.assertIn("folder name", report["bridge_identity"]["reason"])

    def test_failed_handshake_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hsr-bridge-") as temp:
            paths, _, _, handshake = _mirror(Path(temp))
            payload = json.loads(handshake.read_text(encoding="utf-8"))
            payload["result"] = "fail"
            handshake.write_text(json.dumps(payload), encoding="utf-8")
            report = paths.local_location_report()
            self.assertFalse(report["approved"])

    def test_missing_handshake_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hsr-bridge-") as temp:
            paths, _, _, handshake = _mirror(Path(temp))
            handshake.unlink()
            report = paths.local_location_report()
            self.assertFalse(report["approved"])

    def test_read_only_mount_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hsr-bridge-") as temp:
            paths, _, _, _ = _mirror(Path(temp))
            with patch("hollowstar.paths.os.access", return_value=False):
                report = paths.local_location_report()
            self.assertFalse(report["approved"])
            self.assertIn("not writable", report["bridge_identity"]["reason"])

    def test_bridge_may_not_rewrite_the_handshake(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hsr-bridge-") as temp:
            paths, _, _, handshake = _mirror(Path(temp))
            before = handshake.read_bytes()
            self.assertEqual(paths.local_location_report().get("via"), "bridge")

            host = HSRHost(paths)
            result = host.handle({"id": "lc", "command": "local-check"})

            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "LOCAL_LOCATION_REQUIRED")
            self.assertEqual(handshake.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
