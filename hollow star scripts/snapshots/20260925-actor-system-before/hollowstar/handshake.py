"""Durable, fail-closed integrity handshake for the local HSR host.

``local-check`` is the only command that writes this artifact.  Every other
consumer verifies it byte-for-data against the current workspace, source-owner
hashes and party snapshot.  Play-mode policy is deliberately independent.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from hollowstar.paths import HostPaths


SCHEMA_VERSION = "hollow-star-handshake-2"
FINGERPRINT_ALGORITHM = "sha256-owner-hash-v1"
SNAPSHOT_SCHEMA = "hollow-star-party-snapshot-1"


class HandshakeError(ValueError):
    """Raised when the durable HSR gate cannot be trusted."""


MAX_JSON_BYTES = 10_905_190  # 8 MiB + 30%, rounded down (2026-09-23)


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise HandshakeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise HandshakeError(f"non-finite JSON number: {value}")


def _read_json(path: Path, label: str) -> dict:
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            raise HandshakeError(f"{label} exceeds JSON size limit")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
    except FileNotFoundError as exc:
        raise HandshakeError(f"missing {label}: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise HandshakeError(f"invalid {label}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HandshakeError(f"{label} root must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _checked_at(value: str | None) -> str:
    if value is None:
        return (
            _dt.datetime.now(_dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    if not isinstance(value, str) or not value.endswith("Z"):
        raise HandshakeError("checked_at_utc must be a UTC timestamp ending in Z")
    try:
        parsed = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HandshakeError("checked_at_utc is not a valid timestamp") from exc
    if parsed.utcoffset() != _dt.timedelta(0) or parsed.microsecond:
        raise HandshakeError("checked_at_utc must use whole UTC seconds")
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise HandshakeError("checked_at_utc must use canonical UTC format")
    if parsed > _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(minutes=5):
        raise HandshakeError("checked_at_utc is in the future")
    return value


def _validated_sources(paths: HostPaths, snapshot: dict) -> tuple[list[dict], str]:
    sources = snapshot.get("sources")
    if not isinstance(sources, list) or not sources:
        raise HandshakeError("party snapshot has no source-owner list")

    corpus = paths.corpus_root.resolve()
    seen: set[str] = set()
    normalized: list[dict] = []
    for source in sources:
        if not isinstance(source, dict):
            raise HandshakeError("party snapshot contains a non-object source record")
        owner = source.get("owner")
        filename = source.get("file")
        recorded = source.get("sha256")
        if not all(isinstance(item, str) and item for item in (owner, filename, recorded)):
            raise HandshakeError("party snapshot source record is incomplete")
        if owner in seen:
            raise HandshakeError(f"duplicate snapshot source owner: {owner}")
        seen.add(owner)
        if Path(filename).name != filename or len(Path(filename).parts) != 1:
            raise HandshakeError(f"snapshot source must be directly under the corpus: {filename}")
        source_path = (corpus / filename).resolve()
        if source_path.parent != corpus:
            raise HandshakeError(f"snapshot source escapes the corpus root: {filename}")
        if not source_path.is_file():
            raise HandshakeError(f"missing snapshot source owner: {source_path}")
        actual = _sha256(source_path)
        if recorded != actual:
            raise HandshakeError(
                f"stale snapshot source {owner}: recorded {recorded}, current {actual}"
            )
        normalized.append({"owner": owner, "sha256": actual})
    full_fingerprint = hashlib.sha256(
        "".join(
            f"{entry['owner']}:{entry['sha256']}"
            for entry in sorted(normalized, key=lambda item: item["owner"])
        ).encode("utf-8")
    ).hexdigest()
    if snapshot.get("source_fingerprint") != full_fingerprint[:12]:
        raise HandshakeError("party snapshot source_fingerprint does not match its owner hashes")
    return normalized, full_fingerprint


def _validated_root(paths: HostPaths) -> str:
    """The workspace root as the approved local PC sees it.

    A device-bridge mount proves its identity *against* the root already
    recorded in the handshake, so recomputation must quote that same
    Windows root rather than the mount's own path.  Otherwise a read-only
    verification from the bridge would report a difference that does not
    exist.  Only a fully proven bridge reaches this branch.
    """

    report = paths.local_location_report()
    if report.get("via") == "bridge":
        recorded = (report.get("bridge_identity") or {}).get("validated_workspace_root")
        if isinstance(recorded, str) and recorded:
            return recorded
    return str(paths.workspace_root.resolve())


def build_handshake_payload(paths: HostPaths, checked_at_utc: str | None = None) -> dict:
    """Recompute the complete handshake from current read-only authorities."""

    paths.assert_workspace_layout()
    snapshot = _read_json(paths.snapshot_path, "party snapshot")
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA:
        raise HandshakeError("party snapshot schema mismatch")
    if snapshot.get("seed_mode") != "SIMULATION":
        raise HandshakeError("party snapshot is not a SIMULATION seed")
    sources, fingerprint = _validated_sources(paths, snapshot)
    return {
        "schema_version": SCHEMA_VERSION,
        "result": "pass",
        "checked_at_utc": _checked_at(checked_at_utc),
        "validated_workspace_root": _validated_root(paths),
        "snapshot": {
            "schema_version": snapshot["schema_version"],
            "snapshot_version": snapshot.get("snapshot_version"),
            "source_fingerprint": snapshot.get("source_fingerprint"),
        },
        "artifact_hashes": {
            "snapshot_sha256": _sha256(paths.snapshot_path),
            "config_sha256": _sha256(paths.config_path),
        },
        "corpus_fingerprint": {
            "algorithm": FINGERPRINT_ALGORITHM,
            "source_owner_count": len(sources),
            "value": fingerprint,
        },
    }


def verify_handshake(paths: HostPaths) -> dict:
    """Read and exactly recompute the durable handshake without writing."""

    actual = _read_json(paths.handshake_path, "HSR handshake")
    if actual.get("schema_version") != SCHEMA_VERSION:
        raise HandshakeError("HSR handshake schema mismatch")
    expected = build_handshake_payload(paths, actual.get("checked_at_utc"))
    if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(
            key for key in set(actual) & set(expected) if json.dumps(actual[key], sort_keys=True) != json.dumps(expected[key], sort_keys=True)
        )
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extra:
            details.append("extra=" + ",".join(extra))
        if changed:
            details.append("changed=" + ",".join(changed))
        raise HandshakeError("HSR handshake does not match current authorities: " + "; ".join(details))
    return actual


def write_handshake(paths: HostPaths) -> dict:
    """Atomically replace the durable handshake only after every check passes."""

    target = paths.handshake_path.resolve()
    if target.parent != paths.hsr_root.resolve():
        raise HandshakeError(f"handshake path must be directly under the HSR root: {target}")
    payload = build_handshake_payload(paths)
    rendered = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    fd = -1
    temporary = ""
    try:
        fd, temporary = tempfile.mkstemp(prefix=".HSR_HANDSHAKE.", suffix=".tmp", dir=target.parent)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = -1
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        temporary = ""
    except OSError as exc:
        raise HandshakeError(f"could not atomically write HSR handshake: {exc}") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary:
            Path(temporary).unlink(missing_ok=True)
    return payload
