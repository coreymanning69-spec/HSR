"""Transactional authoring previews called by RunService; no game mechanics.

Immutable packages are addressed by digest. Each preview owns independent
state. SQLite serializes commits across local processes; expected revisions
reject stale clients and request identities make uncertain retries safe.
This is local authoring storage, not public hosting authentication.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from hollowstar.content_package import PackageError, encode, fingerprint, initial_state, public_view, transition, validate_package


class PreviewConflict(PackageError):
    """An outdated revision or reused operation identity cannot be committed."""


class PreviewStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def _connection(self, *, write=False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise PackageError("unsupported preview database version")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS packages (
                    digest TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS previews (
                    id TEXT PRIMARY KEY, digest TEXT NOT NULL REFERENCES packages(digest),
                    revision INTEGER NOT NULL, state TEXT NOT NULL,
                    start_key TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS operations (
                    preview_id TEXT NOT NULL REFERENCES previews(id), operation_id TEXT NOT NULL,
                    request TEXT NOT NULL, response TEXT NOT NULL,
                    PRIMARY KEY (preview_id, operation_id));
            """)
            if version == 0:
                connection.execute("PRAGMA user_version=1")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _key(value, label):
        if not isinstance(value, str) or not 1 <= len(value) <= 128 or not all(c.isalnum() or c in "_-" for c in value):
            raise PackageError(f"{label} must contain 1 to 128 letters, digits, underscores, or hyphens")
        return value

    @staticmethod
    def _row(connection, preview_id):
        PreviewStore._key(preview_id, "preview_id")
        row = connection.execute("SELECT previews.*, packages.payload FROM previews JOIN packages ON previews.digest=packages.digest WHERE id=?", (preview_id,)).fetchone()
        if row is None:
            raise PackageError("preview does not exist")
        return row

    @staticmethod
    def _view(row):
        return public_view(json.loads(row["payload"]), json.loads(row["state"]), row["id"], row["revision"])

    def start(self, package, operation_id):
        self._key(operation_id, "operation_id")
        package = validate_package(package)["package"]
        digest, payload = fingerprint(package), encode(package)
        with self._connection(write=True) as connection:
            existing = connection.execute("SELECT id, digest FROM previews WHERE start_key=?", (operation_id,)).fetchone()
            if existing:
                if existing["digest"] != digest:
                    raise PreviewConflict("start operation_id was already used for a different package")
                return self._view(self._row(connection, existing["id"]))
            preview_id = "preview-" + uuid.uuid4().hex
            connection.execute("INSERT OR IGNORE INTO packages(digest,payload) VALUES (?,?)", (digest, payload))
            connection.execute("INSERT INTO previews(id,digest,revision,state,start_key) VALUES (?,?,0,?,?)",
                               (preview_id, digest, encode(initial_state(package)), operation_id))
            return self._view(self._row(connection, preview_id))

    def read(self, preview_id):
        with self._connection() as connection:
            return self._view(self._row(connection, preview_id))

    def act(self, preview_id, action, expected_revision, operation_id):
        self._key(preview_id, "preview_id")
        self._key(operation_id, "operation_id")
        if type(expected_revision) is not int or expected_revision < 0:
            raise PackageError("expected_revision must be a non-negative integer")
        request = encode({"action": action, "expected_revision": expected_revision})
        with self._connection(write=True) as connection:
            previous = connection.execute("SELECT request,response FROM operations WHERE preview_id=? AND operation_id=?", (preview_id, operation_id)).fetchone()
            if previous:
                if previous["request"] != request:
                    raise PreviewConflict("operation_id was already used for a different action")
                return json.loads(previous["response"])
            row = self._row(connection, preview_id)
            if row["revision"] != expected_revision:
                raise PreviewConflict(f"stale preview revision: expected {expected_revision}, current {row['revision']}; refresh before acting")
            package = json.loads(row["payload"])
            state = transition(package, json.loads(row["state"]), action)
            revision = expected_revision + 1
            view = public_view(package, state, preview_id, revision)
            connection.execute("UPDATE previews SET revision=?,state=? WHERE id=?", (revision, encode(state), preview_id))
            connection.execute("INSERT INTO operations VALUES (?,?,?,?)", (preview_id, operation_id, request, encode(view)))
            return view

    def export(self, preview_id):
        with self._connection() as connection:
            return json.loads(self._row(connection, preview_id)["payload"])

    def list(self, limit=30):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise PackageError("limit must be an integer from 1 to 100")
        with self._connection() as connection:
            rows = connection.execute("SELECT previews.*,packages.payload FROM previews JOIN packages ON previews.digest=packages.digest ORDER BY created_at DESC,id DESC LIMIT ?", (limit,)).fetchall()
            return [{"preview_id": row["id"], "revision": row["revision"], "created_at": row["created_at"],
                     "title": json.loads(row["payload"])["title"], "package_hash": row["digest"]} for row in rows]
