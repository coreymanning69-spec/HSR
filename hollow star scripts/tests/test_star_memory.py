"""The Hollow Star's account-wide memory across vessels."""
import tempfile
from pathlib import Path

from hollowstar.star_memory import StarMemory


def _root():
    return Path(tempfile.mkdtemp(prefix="hsr-star-"))


def test_fresh_star_is_unaware_and_shop_is_sealed():
    tmp_path = _root()
    view = StarMemory(tmp_path).view()
    assert view["runs"] == 0
    assert view["awareness"] == {"tier": 0, "name": "Ember"}
    assert view["meta_shop_unlocked"] is False


def test_first_ended_run_unlocks_meta_shop_and_is_idempotent():
    tmp_path = _root()
    star = StarMemory(tmp_path)
    star.record_run("r1", "custom:Ash", {"outcome": "dead", "status": "defeated"}, {"name": "Ash"})
    view = star.record_run("r1", "custom:Ash", {"outcome": "dead"}, {"name": "Ash"})
    assert view["runs"] == 1 and view["deaths"] == 1
    assert view["meta_shop_unlocked"] is True
    assert view["awareness"]["name"] == "Echo"


def test_completion_records_victor_and_raises_awareness():
    tmp_path = _root()
    star = StarMemory(tmp_path)
    view = star.record_run("r1", "divine:Doran", {"outcome": "completed"}, {"name": "Doran"})
    assert view["last_victor"]["identity"] == "divine:Doran"
    assert view["awareness"]["tier"] == 2


def test_revealed_flag_reaches_full_star():
    tmp_path = _root()
    assert StarMemory(tmp_path).set_flag("star_revealed")["awareness"] == {"tier": 4, "name": "Star"}


def test_history_absorbs_only_ended_runs():
    tmp_path = _root()
    rows = [{"run_id": "a", "status": "ended", "reason": "player_death", "summary": {"party": ["custom:Ash"]}},
            {"run_id": "b", "status": "replaced", "reason": "new_game"},
            {"run_id": "c", "status": "active"}]
    view = StarMemory(tmp_path).absorb_history(rows)
    assert view["runs"] == 1 and view["vessels"][0]["name"] == "Ash"
    assert StarMemory(tmp_path).absorb_history(rows)["runs"] == 1


def test_seen_cutscenes_validate_ids():
    tmp_path = _root()
    star = StarMemory(tmp_path)
    assert star.mark_seen("opening")["seen_cutscenes"] == ["opening"]
    try:
        star.mark_seen("../../etc")
    except ValueError:
        return
    raise AssertionError("path-like cutscene id was accepted")
