"""Encoding and line-ending contract for maintained HSR text artifacts."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
# Repair side: tools/hsr_line_endings.py (run by tools/check.py --fix); keep in step.
TEXT_SUFFIXES = {".py", ".json", ".md", ".js", ".cjs", ".mjs", ".css", ".html"}
IGNORED_PARTS = {"__pycache__", ".local", "node_modules", "snapshots", ".pytest_cache"}


def maintained_text_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in TEXT_SUFFIXES
        and not (set(path.parts) & IGNORED_PARTS)
    )


def test_hsr_text_is_utf8_lf_without_bom() -> None:
    """Keep code, configuration, docs, and generated JSON portable and diffable."""
    files = maintained_text_files()
    assert files, "HSR text inventory is unexpectedly empty"
    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"UTF-8 BOM: {path}"
        raw.decode("utf-8")
        assert b"\r" not in raw, f"non-LF line ending: {path}"


if __name__ == "__main__":
    test_hsr_text_is_utf8_lf_without_bom()
    print("1 hygiene test passed")
