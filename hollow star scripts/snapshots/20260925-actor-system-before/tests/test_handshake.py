"""Durable HSR handshake tests; runnable without pytest."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hollowstar.handshake import HandshakeError, verify_handshake, write_handshake  # noqa: E402
from hollowstar.paths import resolve_paths  # noqa: E402


def _json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory() as raw:
        workspace = Path(raw) / "Soliera and Sera fixture"
        corpus = workspace / "divine mythos set"
        hsr = workspace / "hollow star scripts"
        content = hsr / "hollowstar" / "content"
        content.mkdir(parents=True)
        corpus.mkdir(parents=True)

        owners = ["DM041_A", "DM041_A1", "DM041_B", "DM041_B1", "DM044_0", "DM044_1", "DM046_0", "DM047_0"]
        certification = {
            "schema_version": "dm-certification-progress-1",
            "owner": "DM046_0",
            "progress": {"completed": 5, "total": 6, "display": "5/6"},
            "steps": [
                {"step": 5, "status": "artifact-created", "deferred_rule_count": 30},
                {"step": 6, "status": "complete"},
            ],
            "run_modes": {"design": "available", "sandbox": "available", "forge": "available"},
        }
        for owner in owners:
            body = f"---\nid: {owner}\n---\n\n# {owner}\n"
            if owner == "DM046_0":
                body += "\n```yaml\n" + json.dumps(certification, indent=2) + "\n```\n"
            (corpus / f"{owner}.md").write_text(body, encoding="utf-8", newline="\n")

        sources = []
        for owner in owners:
            path = corpus / f"{owner}.md"
            sources.append(
                {
                    "owner": owner,
                    "file": path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "source_schema": "fixture",
                }
            )
        fingerprint = hashlib.sha256(
            "".join(
                f"{item['owner']}:{item['sha256']}"
                for item in sorted(sources, key=lambda item: item["owner"])
            ).encode()
        ).hexdigest()
        snapshot = {
            "schema_version": "hollow-star-party-snapshot-1",
            "snapshot_version": "fixture+" + fingerprint[:12],
            "source_fingerprint": fingerprint[:12],
            "seed_mode": "SIMULATION",
            "certification": {"framework_owner": "DM046_0", "step": 6},
            "sources": sources,
            "characters": {
                "doran": {"deferred": [f"doran-{n}" for n in range(18)]},
                "wren": {"deferred": [f"wren-{n}" for n in range(12)]},
            },
        }
        _json(hsr / "snapshots" / "party_snapshot.json", snapshot)
        config = {
            "schema_version": "hollow-star-host-config-1",
            "local_pc_required": False,
            "paths": {
                "corpus_dir": "divine mythos set",
                "hsr_dir": "hollow star scripts",
                "content_dir": "hollow star scripts/hollowstar/content",
                "snapshot": "hollow star scripts/snapshots/party_snapshot.json",
                "handshake": "hollow star scripts/HSR_HANDSHAKE.json",
                "data_dir": ".local",
                "runs_dir": ".local/reliquary_runs",
                "profiles_dir": ".local/reliquary_profiles",
            },
            "modes": {"DESIGN": "available", "REVIEW": "available", "SANDBOX": "available", "FORGE": "available"},
        }
        config_path = hsr / "host_config.json"
        _json(config_path, config)
        yield resolve_paths(workspace, config_path=config_path)


def _expect_failure(callable_) -> None:
    try:
        callable_()
    except HandshakeError:
        return
    raise AssertionError("untrusted handshake was accepted")


def test_round_trip_is_exact_and_complete() -> None:
    with fixture() as paths:
        written = write_handshake(paths)
        assert verify_handshake(paths) == written
        assert written["corpus_fingerprint"]["source_owner_count"] == 8
        assert written["schema_version"] == "hollow-star-handshake-2"
        assert "certification" not in written
        assert "deferred_rules" not in written
        assert "blocked_modes" not in written


def test_missing_and_extra_fields_fail_closed() -> None:
    with fixture() as paths:
        write_handshake(paths)
        value = json.loads(paths.handshake_path.read_text(encoding="utf-8"))
        value.pop("result")
        value["untrusted_extra"] = True
        _json(paths.handshake_path, value)
        _expect_failure(lambda: verify_handshake(paths))


def test_wrong_workspace_root_fails_closed() -> None:
    with fixture() as paths:
        write_handshake(paths)
        value = json.loads(paths.handshake_path.read_text(encoding="utf-8"))
        value["validated_workspace_root"] = str(paths.workspace_root / "wrong")
        _json(paths.handshake_path, value)
        _expect_failure(lambda: verify_handshake(paths))


def test_stale_owner_hash_fails_closed() -> None:
    with fixture() as paths:
        write_handshake(paths)
        owner = paths.corpus_root / "DM041_A.md"
        owner.write_text(owner.read_text(encoding="utf-8") + "changed\n", encoding="utf-8", newline="\n")
        _expect_failure(lambda: verify_handshake(paths))


def test_failed_refresh_preserves_previous_bytes() -> None:
    with fixture() as paths:
        write_handshake(paths)
        before = paths.handshake_path.read_bytes()
        owner = paths.corpus_root / "DM041_A.md"
        owner.write_text(owner.read_text(encoding="utf-8") + "changed\n", encoding="utf-8", newline="\n")
        _expect_failure(lambda: write_handshake(paths))
        assert paths.handshake_path.read_bytes() == before


def test_mode_and_deferred_fields_do_not_control_integrity_handshake() -> None:
    with fixture() as paths:
        assert write_handshake(replace(paths, modes={**paths.modes, "FORGE": "blocked"}))
        snapshot = json.loads(paths.snapshot_path.read_text(encoding="utf-8"))
        snapshot["characters"]["wren"]["deferred"].pop()
        _json(paths.snapshot_path, snapshot)
        assert write_handshake(paths)


def test_full_snapshot_and_config_edits_invalidate_handshake() -> None:
    for target in ("snapshot_path", "config_path"):
        with fixture() as paths:
            write_handshake(paths)
            path = getattr(paths, target)
            value = json.loads(path.read_text(encoding="utf-8"))
            value["untracked_edit"] = "tampered"
            _json(path, value)
            _expect_failure(lambda: verify_handshake(paths))


def test_duplicate_nonfinite_and_oversized_json_fail_closed() -> None:
    from hollowstar.handshake import MAX_JSON_BYTES
    for raw in ('{"schema_version":0,"schema_version":1}', '{"x":NaN}', ' ' * (MAX_JSON_BYTES + 1)):
        with fixture() as paths:
            paths.handshake_path.write_text(raw, encoding="utf-8")
            _expect_failure(lambda: verify_handshake(paths))


def test_future_timestamp_and_bool_number_substitution_fail_closed() -> None:
    for key, value in (("checked_at_utc", "2999-01-01T00:00:00Z"), ("checked_at_utc", "2026-09-07 00:00:00Z")):
        with fixture() as paths:
            payload = write_handshake(paths)
            payload[key] = value
            _json(paths.handshake_path, payload)
            _expect_failure(lambda: verify_handshake(paths))
    with fixture() as paths:
        payload = write_handshake(paths)
        payload["snapshot"]["snapshot_version"] = True
        _json(paths.handshake_path, payload)
        _expect_failure(lambda: verify_handshake(paths))


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    main()
