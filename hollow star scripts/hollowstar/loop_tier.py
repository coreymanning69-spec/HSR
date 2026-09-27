"""Deterministic loop-tier scaling formulas.

A loop tier is a single small positive integer, starting at 1, that an
account advances by completing runs (see `Progression.settle` in
`progression.py`). It is not stored per-character and it is not something a
resident remembers -- residents never remember prior runs (see
`content/floor_one_life.json` MEMORY POLICY). It exists purely to make a new
world at tier N play differently from tier 1 without hand-authoring a
separate content set per tier.

Every function here is a pure function of `tier` alone (uncapped upward,
clamped only where a formula would otherwise divide by zero or invert). That
determinism is load-bearing: `RunService.replay_token` and the terminal
receipt both need "loop tier N" to reproduce the exact same scaling on
replay, with no hidden dependency on wall-clock time, prior rng draws, or
anything outside the tier number itself.
"""
from __future__ import annotations

MIN_TIER = 1


def clamp_tier(tier: int) -> int:
    if not isinstance(tier, int) or isinstance(tier, bool):
        raise ValueError("loop tier must be an int")
    return max(MIN_TIER, tier)


def resident_stat_multiplier(tier: int) -> float:
    """HP/save/skill scaling for named and filler residents alike.

    +12% per tier above 1, so tier 1 is exactly the authored baseline
    (multiplier 1.0) and nothing here can push a stat below its authored
    floor.
    """
    tier = clamp_tier(tier)
    return round(1.0 + 0.12 * (tier - 1), 4)


def equipment_budget(tier: int, base_budget: int) -> int:
    """Scale a resident's `tier_scaling.gear_budget` (see life_sim residents).

    Grows by ceil(one budget step per two tiers) so an armed resident starts
    outgearing a civilian faster than a civilian ever catches up.
    """
    tier = clamp_tier(tier)
    base_budget = max(0, int(base_budget))
    return base_budget + (tier - 1 + 1) // 2


def hostility_threshold_shift(tier: int) -> int:
    """Signed shift applied to a reaction-band score before banding.

    Positive at higher tiers: the same disposition_base reads one band more
    guarded per two tiers, so residents are quicker to go wary/hostile in a
    high-tier world without changing their authored baseline disposition.
    """
    tier = clamp_tier(tier)
    return (tier - 1) // 2


def alarm_response_seconds(tier: int, base_seconds: int) -> int:
    """Local guard arrival delay after an alarm is raised.

    Shrinks toward a floor of a quarter of the authored delay; never reaches
    zero, so a response is never instantaneous regardless of tier.
    """
    tier = clamp_tier(tier)
    base_seconds = max(0, int(base_seconds))
    floor = max(1, base_seconds // 4)
    decay = round(base_seconds * (0.85 ** (tier - 1)))
    return max(floor, decay)


def filler_density_multiplier(tier: int) -> float:
    """Background/filler NPC spawn-weight multiplier for a room or location.

    +8% per tier; deliberately gentler than resident_stat_multiplier so a
    high-tier world reads as busier and better-defended without every filler
    encounter individually hitting as hard as a named resident does.
    """
    tier = clamp_tier(tier)
    return round(1.0 + 0.08 * (tier - 1), 4)


def event_table_weight_shift(tier: int) -> float:
    """Additive shift toward the more dangerous/valuable rows of an event
    or loot table (consumed the same way §10's pressure clamp is: added into
    an existing weighted-choice call, never a second parallel table).

    +0.05 per tier, capped at 0.6 so no tier ever fully zeroes out the gentle
    rows -- a high-tier world is harder and richer, not scripted.
    """
    tier = clamp_tier(tier)
    return round(min(0.6, 0.05 * (tier - 1)), 4)


def describe(tier: int) -> dict:
    """One deterministic, replayable snapshot of every scaling formula at
    `tier`, suitable for embedding in a terminal receipt or replay token."""
    tier = clamp_tier(tier)
    return {
        "schema": "hollow-star-loop-tier-1",
        "tier": tier,
        "resident_stat_multiplier": resident_stat_multiplier(tier),
        "hostility_threshold_shift": hostility_threshold_shift(tier),
        "alarm_response_seconds_at_base_30": alarm_response_seconds(tier, 30),
        "filler_density_multiplier": filler_density_multiplier(tier),
        "event_table_weight_shift": event_table_weight_shift(tier),
    }
