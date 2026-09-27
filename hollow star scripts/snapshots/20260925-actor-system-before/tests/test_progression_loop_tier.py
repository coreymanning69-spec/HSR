"""A completed run advances the account's loop tier; a dead run does not.

The tier a run plays at is frozen into `run.context['loop_tier']` at launch
(RunService.create) and never re-derived mid-run, even if the account's
tier advances elsewhere while this run is still open. `Progression.settle`
records the tier actually played and only advances the account's next tier
for a public `completed` outcome (see `TERMINAL_OUTCOMES` in dungeon.py and
loop_tier.py).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar import dungeon  # noqa: E402
from hollowstar.progression import Progression  # noqa: E402
from hollowstar.run_service import RunService  # noqa: E402
from hollowstar.storage import atomic_json  # noqa: E402


class LoopTierProgressionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="hsr-looptier-")
        self.root = Path(self.tmp.name) / ".local" / "reliquary_runs"
        self.progress = Progression(self.root.parent / "reliquary_progress")

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_identity_starts_at_loop_tier_one(self):
        data = self.progress.load("divine:Doran")
        self.assertEqual(data["loop_tier"], 1)

    def test_completed_outcome_advances_tier_for_the_next_run(self):
        service = RunService(self.root)
        service.create("run-a", ["divine:Doran"], ["Townsperson"], "tier-seed-a")
        service.design_start("run-a")
        run_a = service._active["run-a"]
        self.assertEqual(run_a.context["loop_tier"], 1)
        dungeon.end(run_a, "cleared")

        settled = self.progress.settle("divine:Doran", "run-a", run_a)
        self.assertEqual(settled["runs"]["run-a"]["outcome"], "completed")
        self.assertEqual(settled["runs"]["run-a"]["loop_tier_played"], 1)
        self.assertEqual(settled["loop_tier"], 2)

        # A second run created afterwards freezes the *new* tier at launch.
        service.create("run-b", ["divine:Doran"], ["Townsperson"], "tier-seed-b")
        service.design_start("run-b")
        run_b = service._active["run-b"]
        self.assertEqual(run_b.context["loop_tier"], 2)
        self.assertEqual(run_b.context["replay_contract"]["loop_tier"], 2)

    def test_dead_outcome_does_not_advance_tier(self):
        service = RunService(self.root)
        service.create("run-c", ["divine:Doran"], ["Townsperson"], "tier-seed-c")
        service.design_start("run-c")
        run_c = service._active["run-c"]
        dungeon.end(run_c, "defeated")

        settled = self.progress.settle("divine:Doran", "run-c", run_c)
        self.assertEqual(settled["runs"]["run-c"]["outcome"], "dead")
        self.assertEqual(settled["loop_tier"], 1)

    def test_settlement_is_idempotent_for_loop_tier_too(self):
        service = RunService(self.root)
        service.create("run-d", ["divine:Doran"], ["Townsperson"], "tier-seed-d")
        service.design_start("run-d")
        run_d = service._active["run-d"]
        dungeon.end(run_d, "cleared")

        first = self.progress.settle("divine:Doran", "run-d", run_d)
        second = self.progress.settle("divine:Doran", "run-d", run_d)
        self.assertEqual(first["loop_tier"], 2)
        self.assertEqual(second["loop_tier"], 2)

    def test_replay_identity_keeps_launch_meta_after_account_changes(self):
        service = RunService(self.root)
        service.create("run-replay", ["divine:Doran"], ["Townsperson"], "replay-seed")
        service.design_start("run-replay")
        before = service.replay_token("run-replay")["payload"]
        data = self.progress.load("divine:Doran")
        data["platinum"] = data["currency"] = 99
        atomic_json(self.progress.path("divine:Doran"), data)
        after = service.replay_token("run-replay")["payload"]
        self.assertEqual(after["account_meta_hash"], before["account_meta_hash"])
        self.assertEqual(after["account_meta"], before["account_meta"])


if __name__ == "__main__":
    unittest.main()
