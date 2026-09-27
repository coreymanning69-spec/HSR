"""JSON-lines protocol for Codex, Cowork, tests, and future UI adapters."""

from __future__ import annotations

import json
import sys
from typing import TextIO


def response(
    request_id: object,
    command: str | None,
    *,
    ok: bool,
    result: dict | None = None,
    code: str | None = None,
    message: str | None = None,
) -> dict:
    out = {
        "id": request_id,
        "ok": ok,
        "type": "result" if ok else "error",
        "command": command,
    }
    if ok:
        out["result"] = result or {}
        event = (result or {}).get("event") if isinstance(result, dict) else None
        if isinstance(event, dict) and isinstance(event.get("type"), str):
            out["event_type"] = event["type"]
    else:
        out["error"] = {"code": code or "UNSUPPORTED_OPERATION", "message": message or "operation failed"}
    return out


def write_response(payload: dict, stream: TextIO) -> None:
    stream.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
    stream.flush()


def run_stdio(host, input_stream: TextIO | None = None, output_stream: TextIO | None = None) -> int:
    """Serve one JSON request per line until EOF or a successful shutdown."""

    source = input_stream or sys.stdin
    target = output_stream or sys.stdout
    for line_number, raw_line in enumerate(source, start=1):
        if not raw_line.strip():
            continue
        try:
            request = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            write_response(
                response(None, None, ok=False, code="INVALID_REQUEST", message=f"line {line_number}: invalid JSON"),
                target,
            )
            print(f"invalid JSON on stdin line {line_number}: {exc}", file=sys.stderr)
            continue
        try:
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
            payload = host.handle(request)
        except ValueError as exc:
            payload = response(
                request.get("id") if isinstance(request, dict) else None,
                request.get("command") if isinstance(request, dict) else None,
                ok=False,
                code="INVALID_REQUEST",
                message=str(exc),
            )
        except Exception as exc:  # pragma: no cover - last-resort process guard
            payload = response(
                request.get("id") if isinstance(request, dict) else None,
                request.get("command") if isinstance(request, dict) else None,
                ok=False,
                code="INTERNAL_ERROR",
                message="host failed while handling the request",
            )
            print(f"host error: {type(exc).__name__}: {exc}", file=sys.stderr)
        write_response(payload, target)
        if payload.get("result", {}).get("shutdown") is True:
            break
    return 0
