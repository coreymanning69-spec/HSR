from __future__ import annotations

import unittest

from hollowstar import tracking


class TrackingRegressionTests(unittest.TestCase):
    def test_fractional_active_seconds_are_not_lost(self):
        data = {"currency": 4, "floor": 1, "pressure": {"minutes_elapsed": 0}}
        tracking.active_seconds(data, 0.4)
        tracking.active_seconds(data, 0.7)
        self.assertEqual(data["tracking"]["active_session_seconds"], 1)
        self.assertAlmostEqual(data["tracking"]["active_seconds_remainder"], 0.1, places=6)

    def test_finish_is_idempotent(self):
        data = {"currency": 4, "floor": 1, "pressure": {"minutes_elapsed": 0}}
        tracking.finish(data, "escaped")
        ended = data["tracking"]["ended_at"]
        tracking.finish(data, "defeated")
        self.assertEqual(data["tracking"]["terminal_status"], "escaped")
        self.assertEqual(data["tracking"]["ended_at"], ended)

    def test_unknown_gold_kind_fails_loudly(self):
        with self.assertRaises(ValueError):
            tracking.gold({"currency": 1, "floor": 1, "pressure": {}}, 1, kind="refund")

    def test_room_and_floor_tracking_is_additive(self):
        data = {"currency": 0, "floor": 1, "rooms_cleared": 0, "pressure": {}}
        tracking.room_entered(data, "combat")
        tracking.room_entered(data, "combat")
        tracking.room_resolved(data, "combat")
        tracking.floor_completed(data, 1)
        tracking.floor_completed(data, 1)
        self.assertEqual(data["tracking"]["rooms_by_kind"], {"combat": 2})
        self.assertEqual(data["tracking"]["rooms_resolved_by_kind"], {"combat": 1})
        self.assertEqual(data["tracking"]["floors_completed"], 1)
        self.assertEqual(data["tracking"]["completed_floor_numbers"], [1])


if __name__ == "__main__":
    unittest.main()
