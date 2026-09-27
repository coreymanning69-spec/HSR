"""Authenticated Hosted Controls policy for the local HSR relay."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
from pathlib import Path

SCHEMA = "hollow-star-hosted-controls-1"
LEASE_SECONDS = 90
READ_COMMANDS = {
    "health", "ready", "status", "inspect", "readout", "content_catalog",
    "affix_catalog", "scenario_catalog", "character_options", "list_runs",
    "session_intent",
}
MUTATION_COMMANDS = {"design_turn", "design_action", "sandbox_action", "sandbox_start", "sandbox_release"}
FORBIDDEN_COMMANDS = {
    "shutdown", "validate", "local-check", "validation_start", "validation_status",
    "validation_result", "save_run", "create_profile", "update_profile", "forge_start",
    "forge_action", "forge_receipt", "sandbox_debug", "reveal-room-record",
}


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class HostedControls:
    """Credential, allowlist, replay, and single-controller lease boundary."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._replay: dict[tuple[str, str], tuple[float, dict]] = {}
        self._leases: dict[str, dict] = {}

    def _load(self) -> dict:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}

    def provision(self, clients=("claude", "gpt")) -> dict:
        """Create protected token hashes and return plaintext tokens once."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tokens = {name: secrets.token_urlsafe(32) for name in clients}
        payload = {"schema_version": SCHEMA, "clients": {
            name: {"enabled": True, "token_sha256": _digest(token)}
            for name, token in tokens.items()
        }}
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return tokens

    def authenticate(self, client: str, token: str) -> tuple[bool, str]:
        data = self._load()
        record = data.get("clients", {}).get(client) if isinstance(data.get("clients"), dict) else None
        if not isinstance(record, dict) or not record.get("enabled"):
            return False, "HOSTED_CLIENT_UNKNOWN"
        if not isinstance(token, str) or not hmac.compare_digest(record.get("token_sha256", ""), _digest(token)):
            return False, "HOSTED_AUTH_INVALID"
        return True, ""

    def capabilities(self) -> dict:
        return {"read": sorted(READ_COMMANDS), "mutation": sorted(MUTATION_COMMANDS), "forbidden": sorted(FORBIDDEN_COMMANDS), "lease_seconds": LEASE_SECONDS}

    def _lease(self, run_id: str) -> dict | None:
        lease = self._leases.get(run_id)
        if lease and lease["expires_at"] <= time.monotonic():
            self._leases.pop(run_id, None)
            return None
        return lease

    def authorize(self, client: str, request: dict) -> tuple[bool, str, dict | None]:
        command = request.get("command")
        run_id = request.get("run_id")
        if command in FORBIDDEN_COMMANDS or command not in READ_COMMANDS | MUTATION_COMMANDS:
            return False, "HOSTED_COMMAND_FORBIDDEN", None
        with self._lock:
            lease = self._lease(str(run_id)) if run_id else None
            if command in MUTATION_COMMANDS:
                if not isinstance(run_id, str) or not run_id:
                    return False, "HOSTED_RUN_REQUIRED", None
                if lease and lease["client"] != client:
                    return False, "HOSTED_LEASE_CONFLICT", lease
                if not lease:
                    return False, "HOSTED_LEASE_REQUIRED", None
            return True, "", lease

    def lease(self, client: str, run_id: str, operation: str) -> tuple[bool, str, dict | None]:
        with self._lock:
            current = self._lease(run_id)
            if operation == "acquire":
                if current and current["client"] != client:
                    return False, "HOSTED_LEASE_CONFLICT", current
                lease = {"client": client, "run_id": run_id, "expires_at": time.monotonic() + LEASE_SECONDS}
                self._leases[run_id] = lease
                return True, "", {**lease, "expires_in": LEASE_SECONDS}
            if operation == "renew":
                if not current or current["client"] != client:
                    return False, "HOSTED_LEASE_NOT_OWNER", current
                current["expires_at"] = time.monotonic() + LEASE_SECONDS
                return True, "", {**current, "expires_in": LEASE_SECONDS}
            if operation == "release":
                if current and current["client"] != client:
                    return False, "HOSTED_LEASE_NOT_OWNER", current
                self._leases.pop(run_id, None)
                return True, "", {"run_id": run_id, "released": True}
            return False, "HOSTED_LEASE_OPERATION_INVALID", None

    def replay(self, client: str, request_id: str) -> dict | None:
        with self._lock:
            item = self._replay.get((client, request_id))
            if item and item[0] > time.monotonic():
                return item[1]
            return None

    def remember(self, client: str, request_id: str, response: dict) -> None:
        with self._lock:
            self._replay[(client, request_id)] = (time.monotonic() + 300, response)

