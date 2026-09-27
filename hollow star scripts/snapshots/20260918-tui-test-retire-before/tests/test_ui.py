"""Focused tests for the retro box-drawing terminal UI primitives."""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar import ui  # noqa: E402


class _FakeTTY(io.StringIO):
    def isatty(self) -> bool:  # noqa: D102
        return True


def test_box_lines_are_a_fixed_width() -> None:
    assert len(ui.box_top()) == ui.WIDTH
    assert len(ui.box_bot()) == ui.WIDTH
    assert len(ui.box_divider()) == ui.WIDTH
    assert len(ui.box_line("hello")) == ui.WIDTH
    assert len(ui.box_line("x" * 500)) == ui.WIDTH


def test_box_line_alignment() -> None:
    left = ui.box_line("hi", "left")
    right = ui.box_line("hi", "right")
    center = ui.box_line("hi", "center")
    assert left.index("hi") < right.index("hi")
    assert left.index("hi") <= center.index("hi") <= right.index("hi")


def test_bar_renders_full_empty_and_partial() -> None:
    assert ui.bar(0, 10, width=10) == "[----------] 0/10"
    assert ui.bar(10, 10, width=10) == "[##########] 10/10"
    assert ui.bar(5, 10, width=10) == "[#####-----] 5/10"


def test_bar_handles_zero_max_without_crashing() -> None:
    assert ui.bar(0, 0, width=4) == "[----] 0/0"


def test_refresh_is_a_no_op_off_a_real_terminal() -> None:
    # io.StringIO().isatty() is False, so this must not touch the console.
    ui.refresh(io.StringIO())


def test_read_line_returns_stripped_text_then_none_at_eof() -> None:
    incoming = io.StringIO("hello\n")
    output = io.StringIO()
    assert ui.read_line(incoming, output, "> ") == "hello"
    assert ui.read_line(incoming, output, "> ") is None
    assert output.getvalue() == "> > "


def test_pause_does_not_block_off_a_real_terminal() -> None:
    incoming = io.StringIO("")  # would raise/hang if pause tried to read
    output = io.StringIO()
    ui.pause(incoming, output)
    assert output.getvalue() == ""


def test_pause_reads_one_line_on_a_real_terminal() -> None:
    incoming = io.StringIO("\n")
    output = _FakeTTY()
    ui.pause(incoming, output)
    assert incoming.tell() == len(incoming.getvalue())


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} ui tests passed")


if __name__ == "__main__":
    main()
