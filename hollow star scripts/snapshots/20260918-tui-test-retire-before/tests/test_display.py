"""Focused tests for the presentation-only display profile."""

from __future__ import annotations

import io
import os
import sys
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar import display  # noqa: E402


def test_non_interactive_profile_is_deterministic() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("HSR_UI_MODE", None)
        os.environ.pop("HSR_UI_WIDTH", None)
        profile = display.resolve(io.StringIO())
    assert profile.mode == "standard"
    assert profile.width == 88
    assert profile.logical_aspect == "standard"


def test_overrides_are_clamped_and_do_not_touch_game_state() -> None:
    with patch.dict(os.environ, {
        "HSR_UI_MODE": "wide",
        "HSR_UI_WIDTH": "200",
        "HSR_UI_HEIGHT": "10",
        "HSR_UI_REFRESH_HZ": "0",
        "HSR_UI_MOTION": "off",
    }, clear=False):
        profile = display.resolve(io.StringIO())
    assert profile.mode == "wide"
    assert profile.width == 140
    assert profile.height == 20
    assert profile.refresh_hz == 1
    assert profile.motion == "off"


def test_profile_is_serializable() -> None:
    payload = display.resolve(io.StringIO()).as_dict()
    assert payload["mode"] == "standard"
    assert payload["color"] is False
