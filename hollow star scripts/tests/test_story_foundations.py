"""Story event bus, codex, save migrations, and the run-end pipeline."""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace as N

from hollowstar import save_migrations
from hollowstar.run_end import finalize
from hollowstar.story_state import StoryState


def _root():
    return Path(tempfile.mkdtemp(prefix="hsr-story-"))


def test_floor_event_discovers_codex_and_tracks_deepest_floor():
    story = StoryState(_root())
    story.emit("floor_entered", {"floor": 2, "floor_name": "The Machine Works"})
    data = story.emit("floor_entered", {"floor": 1})
    assert data["codex"]["floor"]["floor-2"]["title"] == "The Machine Works"
    assert data["flags"]["deepest_floor"] == 2
    assert data["counts"]["floor_entered"] == 2


def test_flags_and_codex_reject_bad_ids():
    story = StoryState(_root())
    assert story.set_flag("spared_the_baker")["flags"]["spared_the_baker"] is True
    for call in (lambda: story.set_flag("../x"), lambda: story.discover("weapon", "x")):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("invalid id accepted")


def test_migration_chain_upgrades_and_refuses_newer_saves():
    @save_migrations.migration("test-kind", 1)
    def _v1(data):
        data["added"] = True
        return data
    out, changed = save_migrations.migrate({"schema": "test-kind-1"}, "test-kind", 2)
    assert changed and out == {"schema": "test-kind-2", "added": True}
    try:
        save_migrations.migrate({"schema": "test-kind-3"}, "test-kind", 2)
    except save_migrations.SaveVersionError:
        return
    raise AssertionError("newer save accepted")


def _ended_run(status="defeated"):
    dungeon = {"status": status, "rooms_cleared": 3, "meta_currency": 5, "floor": 1,
               "terminal_receipt": {"outcome": "completed" if status == "cleared" else "dead"}, "tracking": {}}
    return N(context={"dungeon": dungeon, "party_selectors": ["custom:Ash"], "loop_tier": 1}, rng=N(seed="s1"))


def test_run_end_settles_feeds_star_and_emits_once():
    root = _root()
    first = finalize(root, "run-1", _ended_run())
    assert first["settled"]["custom:Ash"]["platinum"] == 5
    assert first["star"]["runs"] == 1 and first["meta_shop_newly_unlocked"] is True
    assert first["story"]["counts"]["run_ended"] == 1
    again = finalize(root, "run-1", _ended_run())
    assert again["already_finalized"] and again["story"]["counts"]["run_ended"] == 1
    assert again["settled"]["custom:Ash"]["platinum"] == 5


def test_run_end_refuses_active_runs():
    run = _ended_run()
    run.context["dungeon"]["status"] = "active"
    try:
        finalize(_root(), "run-2", run)
    except ValueError:
        return
    raise AssertionError("active run finalized")
