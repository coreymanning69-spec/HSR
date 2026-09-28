"""Doran and Wren's Story Mode unlock ladder."""
import tempfile
from pathlib import Path
from types import SimpleNamespace as N

from hollowstar.unlock_ladder import UnlockLadder, action_locked, apply_slot_cap, level_for, picks_for


def _ladder():
    return UnlockLadder(Path(tempfile.mkdtemp(prefix="hsr-ladder-")))


def test_levels_and_picks_scale_to_one_hundred():
    assert level_for(0) == 1 and level_for(10_000) == 100
    assert picks_for(5) == 1 and picks_for(25) == 6 and picks_for(100) == 24


def test_grand_cleave_waits_for_level_fifty_and_a_pick():
    ladder = _ladder()
    ladder.debug_set_level("doran", 49)
    try:
        ladder.pick("doran", "grand_cleave")
    except ValueError as exc:
        assert "level 50" in str(exc)
    else:
        raise AssertionError("grand cleave unlocked early")
    ladder.debug_set_level("doran", 50)
    view = ladder.pick("doran", "grand_cleave")
    assert next(e for e in view["entries"] if e["key"] == "grand_cleave")["unlocked"]


def test_level_one_hundred_unlocks_everything():
    view = _ladder().debug_set_level("wren", 100)
    assert all(e["unlocked"] for e in view["entries"]) and view["slot_cap"] == 9


def test_run_credit_is_once_per_run():
    ladder = _ladder()
    ladder.credit("doran", "r1", 10)
    assert ladder.credit("doran", "r1", 10)["xp"] == 10


def test_locks_refuse_actions_and_close_high_slots():
    locks = _ladder().run_locks("doran")
    assert action_locked(locks, {"type": "grand_cleave"}) == "grand_cleave"
    assert action_locked(locks, {"type": "maneuver", "maneuver": "Riposte"}) == "maneuver:Riposte"
    assert action_locked(locks, {"type": "attack"}) is None
    actor = N(resources={"slot_1_general": 4, "slot_5_general": 2, "slot_9_general": 1})
    assert apply_slot_cap(actor, 1) == ["slot_5_general", "slot_9_general"]
    assert actor.resources == {"slot_1_general": 4, "slot_5_general": 0, "slot_9_general": 0}
