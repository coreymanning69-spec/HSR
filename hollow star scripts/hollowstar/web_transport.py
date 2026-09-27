"""Optional loopback transport to the existing webhost; no local engine."""
from __future__ import annotations

import json
import uuid
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener


class WebHost:
    def __init__(self, url: str):
        parsed = urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise ValueError("HSR web URL must be a loopback HTTP origin")
        self.url = url.rstrip("/") + "/api/host"
        self.opener = build_opener(ProxyHandler({}))

    def handle(self, request: dict) -> dict:
        original_id = request.get("id")
        wire = {**request, "id": "web-client-" + uuid.uuid4().hex, "compact": False}
        try:
            raw = json.dumps(wire, allow_nan=False).encode("utf-8")
            with self.opener.open(Request(self.url, data=raw, headers={
                    "Content-Type": "application/json"}), timeout=45) as response:
                payload = json.load(response)
            if not isinstance(payload, dict) or payload.get("id") != wire["id"]:
                raise ValueError("webhost returned an invalid response identity")
            payload["id"] = original_id
            return payload
        except (URLError, OSError, ValueError) as exc:
            return {"id": original_id, "ok": False, "error": {
                "code": "WEBHOST_UNAVAILABLE", "message": str(exc) +
                "; no retry was sent; refresh before retrying an uncertain action"}}


class HostedWebHost(WebHost):
    """Desktop connector adapter for the authenticated Hosted Controls relay."""
    def __init__(self, url: str, client: str, token: str):
        super().__init__(url)
        if client not in {"claude", "gpt"} or not token:
            raise ValueError("Hosted Controls requires client=claude or gpt and a token")
        self.client, self.token = client, token
        self.url = self.url.rsplit("/api/host", 1)[0] + "/api/hosted"

    def handle(self, request: dict) -> dict:
        original_id = request.get("id")
        wire = {**request, "id": "hosted-client-" + uuid.uuid4().hex, "public_only": True}
        try:
            raw = json.dumps(wire, allow_nan=False).encode("utf-8")
            with self.opener.open(Request(self.url, data=raw, headers={
                    "Content-Type": "application/json", "X-HSR-Client": self.client,
                    "Authorization": "Bearer " + self.token}), timeout=45) as response:
                payload = json.load(response)
            payload["id"] = original_id
            return payload
        except (URLError, OSError, ValueError) as exc:
            return {"id": original_id, "ok": False, "error": {
                "code": "HOSTED_RELAY_UNAVAILABLE", "message": str(exc) +
                "; no retry was sent; refresh before retrying an uncertain action"}}
