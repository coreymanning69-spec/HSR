"""Atomic UTF-8 JSON replacement; a failed write preserves the previous save."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def atomic_json(path: Path, data: dict) -> None:
    # Run state is rewritten after every authoritative action.  It remains
    # human-readable JSON, but indentation multiplies the cost of long
    # rehearsals without adding replay information.  Keep atomic replacement
    # and fsync; only remove formatting whitespace.
    encoded = json.dumps(data, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
