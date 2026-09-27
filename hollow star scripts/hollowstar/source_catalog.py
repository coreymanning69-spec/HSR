"""Read-only local source discovery for compiler tools, never a gameplay loader.

Source text is inert input. A source match conveys neither canon precedence nor
permission to execute mechanics. Paths are relative to one explicit workspace.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path, PurePosixPath


TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".tsv"}
ASSET_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ogg", ".mp3", ".wav"}
EXCLUDED = {"node_modules", "__pycache__", "vendor", "venv", "env", "dist", "build", "_snapshots"}
ARCHIVES = {"_history", "tr3_skt_25_file_pack", "tr3_skt_archive"}
MAX_TEXT_BYTES = 2_600_000  # 2,000,000 + 30% (2026-09-23)
MAX_FILES = 20_000
MAX_SEARCH_BYTES = 83_200_000  # 64,000,000 + 30% (2026-09-23)
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")


class SourceError(ValueError):
    """Invalid, unavailable, oversized, or out-of-scope source input."""


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise SourceError(f"{name} must be an integer from {low} to {high}")
    return value


def relative_path(value):
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise SourceError("source path must be a non-empty workspace-relative path")
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise SourceError("source path contains invalid characters")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or any(p in {".", ".."} or ":" in p for p in path.parts):
        raise SourceError("source path must stay inside the workspace")
    return path


class SourceCatalog:
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).resolve(strict=True)

    def resolve(self, value: str, *, include_archives=False) -> Path:
        path = relative_path(value)
        parts = {p.lower() for p in path.parts}
        if any(p.startswith(".") for p in path.parts) or parts & EXCLUDED:
            raise SourceError("runtime, dependency, hidden, and backup files are not content sources")
        if not include_archives and parts & ARCHIVES:
            raise SourceError("archive source requires include_archives=true")
        candidate = self.workspace.joinpath(*path.parts)
        # Reject links/junctions even when their current target happens to be local.
        for parent in (candidate, *candidate.parents):
            if parent == self.workspace:
                break
            if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
                raise SourceError("linked source paths are not supported")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(self.workspace) or not resolved.is_file():
            raise SourceError("source must be a file inside the workspace")
        if resolved.suffix.lower() not in TEXT_SUFFIXES | ASSET_SUFFIXES:
            raise SourceError("unsupported source format")
        return resolved

    def _text(self, path):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            raise SourceError("binary asset: use its source extract or a future format adapter")
        with path.open("rb") as stream:
            raw = stream.read(MAX_TEXT_BYTES + 1)
        if len(raw) > MAX_TEXT_BYTES:
            raise SourceError("text source exceeds the 2 MB adapter limit")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeError as exc:
            raise SourceError("source is not UTF-8 text") from exc
        if "\x00" in text:
            raise SourceError("binary content is not a text source")
        return raw, text

    def read(self, path, *, start_line=1, line_count=120, include_archives=False, expected_sha256=None):
        integer(start_line, "start_line", 1, 2_000_000)
        integer(line_count, "line_count", 1, 400)
        file = self.resolve(path, include_archives=include_archives)
        raw, text = self._text(file)
        digest = hashlib.sha256(raw).hexdigest()
        if expected_sha256 is not None and expected_sha256 != digest:
            raise SourceError("source changed; refresh the reference before compiling")
        lines = text.splitlines()
        if start_line > max(1, len(lines)):
            raise SourceError("start_line is beyond the source")
        end = min(len(lines), start_line + line_count - 1)
        return {"path": file.relative_to(self.workspace).as_posix(), "sha256": digest,
                "start_line": start_line, "end_line": end, "total_lines": len(lines),
                "text": "\n".join(lines[start_line - 1:end]),
                "headings": [{"line": n, "title": match.group(1)}
                             for n, line in enumerate(lines, 1) if (match := HEADING.match(line))][:500],
                "classification": self.classification(file), "read_only": True}

    def classification(self, path):
        parts = {p.lower() for p in path.relative_to(self.workspace).parts}
        if parts & ARCHIVES:
            return "archive"
        return "canonical-source" if "divine mythos set" in parts else "reference"

    def search(self, query="", *, offset=0, limit=40, include_archives=False):
        if not isinstance(query, str) or len(query) > 200:
            raise SourceError("query must be a string of at most 200 characters")
        if type(include_archives) is not bool:
            raise SourceError("include_archives must be a boolean")
        integer(offset, "offset", 0, MAX_FILES)
        integer(limit, "limit", 1, 100)
        terms = query.casefold().split()
        matches, scanned, read_bytes, skipped, truncated = [], 0, 0, 0, False
        for base, dirs, files in os.walk(self.workspace, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                             and d.lower() not in EXCLUDED
                             and (include_archives or d.lower() not in ARCHIVES)
                             and not (Path(base) / d).is_symlink()
                             and not getattr(Path(base) / d, "is_junction", lambda: False)())
            for name in sorted(files):
                file = Path(base) / name
                if name.startswith(".") or file.suffix.lower() not in TEXT_SUFFIXES | ASSET_SUFFIXES:
                    continue
                scanned += 1
                if scanned > MAX_FILES:
                    truncated = True
                    break
                relative = file.relative_to(self.workspace).as_posix()
                try:
                    file = self.resolve(relative, include_archives=include_archives)
                    size = file.stat().st_size
                    searchable = relative.casefold()
                    snippet, line_number = "", None
                    if terms and not all(term in searchable for term in terms) and file.suffix.lower() in TEXT_SUFFIXES:
                        if size > MAX_TEXT_BYTES or read_bytes + size > MAX_SEARCH_BYTES:
                            skipped += 1
                            continue
                        raw, text = self._text(file)
                        read_bytes += len(raw)
                        searchable += "\n" + text.casefold()
                        for n, line in enumerate(text.splitlines(), 1):
                            if all(term in line.casefold() for term in terms):
                                snippet, line_number = line[:220], n
                                break
                    if not all(term in searchable for term in terms):
                        continue
                    matches.append({"path": relative, "name": name, "bytes": size,
                                    "format": file.suffix[1:].lower(), "text_readable": file.suffix.lower() in TEXT_SUFFIXES and size <= MAX_TEXT_BYTES,
                                    "classification": self.classification(file), "snippet": snippet,
                                    "line": line_number})
                except (OSError, SourceError):
                    skipped += 1
            if truncated:
                break
        matches.sort(key=lambda row: (row["classification"] != "canonical-source", row["path"].casefold()))
        return {"sources": matches[offset:offset + limit], "total": len(matches),
                "offset": offset, "limit": limit, "has_more": offset + limit < len(matches),
                "scanned": min(scanned, MAX_FILES), "skipped": skipped, "truncated": truncated,
                "read_only": True}
