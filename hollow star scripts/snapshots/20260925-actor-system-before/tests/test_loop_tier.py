"""Loop tier scaling formulas are pure, deterministic, and tier-1-neutral."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar import loop_tier as lt  # noqa: E402


def test_tier_one_is_the_authored_baseline() -> None:
    assert lt.resident_stat_multiplier(1) == 1.0
    assert lt.hostility_threshold_shift(1) == 0
    assert lt.filler_density_multiplier(1) == 1.0
    assert lt.event_table_weight_shift(1) == 0.0
    assert lt.equipment_budget(1, base_budget=2) == 2
    assert lt.alarm_response_seconds(1, base_seconds=30) == 30


def test_formulas_are_monotonic_and_deterministic() -> None:
    for fn in (lt.resident_stat_multiplier, lt.filler_density_multiplier,
               lt.hostility_threshold_shift, lt.event_table_weight_shift):
        values = [fn(tier) for tier in range(1, 11)]
        assert values == sorted(values), f"{fn.__name__} must never decrease as tier rises"
        # Same tier, called twice, must return the exact same value -- these
        # are pure functions of tier alone, nothing else.
        assert fn(5) == fn(5)

    for tier in range(1, 21):
        assert lt.equipment_budget(tier, base_budget=1) >= lt.equipment_budget(1, base_budget=1)
        assert lt.alarm_response_seconds(tier, base_seconds=30) <= 30
        assert lt.alarm_response_seconds(tier, base_seconds=30) >= 30 // 4


def test_alarm_response_never_reaches_zero_or_negative() -> None:
    for tier in range(1, 100):
        assert lt.alarm_response_seconds(tier, base_seconds=30) >= 1


def test_event_table_weight_shift_is_capped() -> None:
    assert lt.event_table_weight_shift(1000) <= 0.6


def test_clamp_tier_rejects_non_positive_or_non_int() -> None:
    assert lt.clamp_tier(0) == 1
    assert lt.clamp_tier(-5) == 1
    try:
        lt.clamp_tier(2.5)  # type: ignore[arg-type]
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_describe_is_one_deterministic_replayable_snapshot() -> None:
    snapshot = lt.describe(3)
    assert snapshot["tier"] == 3
    assert snapshot == lt.describe(3)
    assert snapshot["schema"] == "hollow-star-loop-tier-1"
