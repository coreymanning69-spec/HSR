"""Dependency-free contracts for the shared MUD-style session UI."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar import ui  # noqa: E402
from hollowstar.session_screen import SessionScreen  # noqa: E402


def test_menu_registry_has_unique_keys_and_resolvable_commands() -> None:
    keys = [item.key for item in ui.SESSION_MENU]
    assert len(keys) == len(set(keys))
    assert {item.command for item in ui.SESSION_MENU} >= {"create", "load", "status", "observe", "roster", "save", "help", "quit"}


def test_ascii_renderer_wraps_without_unicode_or_overflow() -> None:
    rendered = SessionScreen._boxed("TEST", "This is a deliberately long sentence " * 8)
    assert all(len(line) == ui.WIDTH for line in rendered.splitlines())
    assert not any(ord(char) > 127 for char in rendered)


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} session UI contract tests passed")


if __name__ == "__main__":
    main()
