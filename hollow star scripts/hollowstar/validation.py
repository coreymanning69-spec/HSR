"""Asynchronous local validation jobs with compact model-facing receipts."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path


_JOB_ID = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"validation job state is unavailable: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("validation job state must be an object")
    return value


def _paths(data_root: Path, job_id: str) -> tuple[Path, Path]:
    if not _JOB_ID.fullmatch(job_id):
        raise ValueError("invalid validation job id")
    root = data_root.parent / "validation_jobs"
    return root / f"{job_id}.json", root / f"{job_id}.log"


def start(workspace: Path, data_root: Path, *, job_id: str | None = None) -> dict:
    job_id = job_id or f"check-{uuid.uuid4().hex[:16]}"
    status_path, log_path = _paths(data_root, job_id)
    if status_path.exists():
        current = _read(status_path)
        if current.get("status") == "running":
            return compact(current)
        raise ValueError(f"validation job already exists: {job_id}")
    status = {"schema": 1, "job_id": job_id, "status": "running", "started_at": _now(),
              "workspace": str(workspace), "log_path": str(log_path), "pid": None}
    _write(status_path, status)
    worker = Path(__file__).resolve()
    process = subprocess.Popen(
        [sys.executable, str(worker), "--worker", str(workspace), str(status_path), str(log_path)],
        cwd=str(workspace), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    status["pid"] = process.pid
    _write(status_path, status)
    return compact(status)


def worker(workspace: Path, status_path: Path, log_path: Path) -> int:
    started = time.monotonic()
    status = _read(status_path)
    try:
        with log_path.open("w", encoding="utf-8", newline="\n") as log:
            result = subprocess.run(
                [sys.executable, str(workspace / "tools" / "check.py")],
                cwd=str(workspace), stdout=log, stderr=subprocess.STDOUT, text=True,
            )
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        summary = [line.strip() for line in lines if "RESULT:" in line or line.strip().startswith(("PASS ", "FAIL "))]
        status.update({"status": "completed" if result.returncode == 0 else "failed",
                       "exit_code": result.returncode, "finished_at": _now(),
                       "duration_seconds": round(time.monotonic() - started, 3),
                       "summary": summary[-12:]})
    except Exception as exc:
        status.update({"status": "failed", "exit_code": -1, "finished_at": _now(),
                       "duration_seconds": round(time.monotonic() - started, 3),
                       "summary": [f"VALIDATION WORKER ERROR: {type(exc).__name__}: {exc}"]})
    _write(status_path, status)
    return int(status["exit_code"])


def compact(status: dict) -> dict:
    """Return the only payload conversational clients need while polling."""
    return {key: status[key] for key in (
        "schema", "job_id", "status", "started_at", "finished_at", "duration_seconds", "exit_code", "summary"
    ) if key in status}


def status(data_root: Path, job_id: str) -> dict:
    status_path, _ = _paths(data_root, job_id)
    value = _read(status_path)
    return compact(value)


def result(data_root: Path, job_id: str, *, include_log: bool = False) -> dict:
    status_path, log_path = _paths(data_root, job_id)
    value = _read(status_path)
    out = compact(value)
    if include_log:
        out["log"] = log_path.read_text(encoding="utf-8", errors="replace")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "--worker":
        raise SystemExit("usage: validation.py --worker WORKSPACE STATUS_PATH LOG_PATH")
    raise SystemExit(worker(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])))
