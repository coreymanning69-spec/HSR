"""Fast structural tests for the disposable HSR benchmark harness."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import benchmark_rehearsal as benchmark


class BenchmarkHarness(unittest.TestCase):
    def test_default_matrix_is_fixed_and_ordered(self):
        self.assertEqual(benchmark.DEFAULT_SEEDS,
                         tuple(f"phase5-{index}" for index in range(1, 17)))
        self.assertEqual(benchmark.DEFAULT_WORKERS, (1, 2, 4, 8))

    def test_digest_is_stable_and_timing_independent(self):
        result = {"seed": "s", "steps": 3, "status": "cleared"}
        first = benchmark.result_digest(result)
        result["elapsed_seconds"] = 99.0
        self.assertEqual(first, benchmark.result_digest(result))
        self.assertEqual(first, benchmark.result_digest({"seed": "s", "steps": 3, "status": "cleared"}))

    def test_worker_failure_is_explicit_and_fail_closed(self):
        with patch.object(benchmark, "measure", side_effect=ValueError("invalid action")):
            result = benchmark._measure_job("bad-seed")
        self.assertFalse(result["ok"])
        self.assertEqual(result["seed"], "bad-seed")
        self.assertEqual(result["error_type"], "ValueError")
        self.assertEqual(result["error"], "invalid action")

    def test_scale_preserves_seed_order_and_checks_parity(self):
        seeds = ("a", "b")
        rows = {
            1: {"workers": 1, "runs_requested": 2, "runs_completed": 2,
                "runs_failed": 0, "elapsed_seconds": 2.0,
                "throughput_runs_per_second": 1.0,
                "results": [{"seed": "a", "ok": True, "digest": "da"},
                            {"seed": "b", "ok": True, "digest": "db"}],
                "pool_error": None},
            2: {"workers": 2, "runs_requested": 2, "runs_completed": 2,
                "runs_failed": 0, "elapsed_seconds": 1.0,
                "throughput_runs_per_second": 2.0,
                "results": [{"seed": "a", "ok": True, "digest": "da"},
                            {"seed": "b", "ok": True, "digest": "db"}],
                "pool_error": None},
        }
        with patch.object(benchmark, "_run_worker_count",
                          side_effect=lambda _seeds, workers: copy.deepcopy(rows[workers])):
            scaled = benchmark.scale(seeds, (1, 2))
        self.assertEqual([item["seed"] for item in scaled[1]["results"]], ["a", "b"])
        self.assertEqual([item["parity"] for item in scaled[1]["results"]], ["match", "match"])
        self.assertEqual(scaled[1]["speedup_vs_one_worker"], 2.0)
        self.assertEqual(scaled[1]["parallel_efficiency"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
