"""Benchmark deterministic HSR rehearsals and emit local performance receipts.

The benchmark deliberately parallelizes only whole independent rehearsals.
Each worker owns one RunService and one seed; the action loop inside a run is
always serial.  Outputs are disposable evidence under ``.local`` and never
touch the canon, handshake, or host protocol.
"""
from __future__ import annotations

import argparse
import cProfile
import hashlib
import io
import json
import multiprocessing as mp
import os
import platform
import pstats
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HSR_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = HSR_ROOT.parent
BENCHMARK_ROOT = PROJECT_ROOT / ".local" / "benchmarks"
sys.path.insert(0, str(HSR_ROOT / "tools"))

from run_rehearsal_report import measure  # noqa: E402
from hollowstar import __version__ as ENGINE_VERSION  # noqa: E402


DEFAULT_PROFILE_SEED = "benchmark-baseline"
DEFAULT_SEEDS = tuple(f"phase5-{index}" for index in range(1, 17))
DEFAULT_WORKERS = (1, 2, 4, 8)


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def result_digest(result: dict) -> str:
    """Hash only deterministic rehearsal output, never timing metadata."""
    payload = {key: value for key, value in result.items()
               if key not in {"elapsed_seconds", "wall_seconds", "throughput_runs_per_second"}}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _failure(seed: str, exc: BaseException) -> dict:
    return {
        "seed": seed,
        "ok": False,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }


def _measure_job(seed: str) -> dict:
    """Run one independent rehearsal in a spawned worker."""
    try:
        result = measure(seed, strategy="baseline", run_mode="DESIGN")
        return {
            "seed": seed,
            "ok": True,
            "digest": result_digest(result),
            "steps": result["steps"],
            "status": result["status"],
        }
    except Exception as exc:  # noqa: BLE001 - receipt must name failed seeds
        return _failure(seed, exc)


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")


def _validate_output_dir(path: Path) -> Path:
    resolved = path if path.is_absolute() else PROJECT_ROOT / path
    resolved = resolved.resolve()
    try:
        resolved.relative_to(BENCHMARK_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("benchmark outputs must stay under .local/benchmarks") from exc
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def profile_one(seed: str, output_dir: Path) -> dict:
    """Profile exactly one deterministic rehearsal and write its receipts."""
    profile_path = output_dir / "one_rehearsal.prof"
    stats_path = output_dir / "one_rehearsal.pstats.txt"
    started = time.perf_counter_ns()
    profiler = cProfile.Profile()
    try:
        result = profiler.runcall(measure, seed, strategy="baseline", run_mode="DESIGN")
        record = {
            "seed": seed,
            "ok": True,
            "digest": result_digest(result),
            "steps": result["steps"],
            "status": result["status"],
        }
    except Exception as exc:  # noqa: BLE001 - preserve profile on failure
        record = _failure(seed, exc)
    elapsed = (time.perf_counter_ns() - started) / 1_000_000_000
    profiler.dump_stats(str(profile_path))
    stream = io.StringIO()
    (pstats.Stats(profiler, stream=stream)
     .strip_dirs()
     .sort_stats("cumulative")
     .print_stats(50))
    stats_path.write_text(stream.getvalue(), encoding="utf-8", newline="\n")
    return {
        "seed": seed,
        "elapsed_seconds": elapsed,
        "result": record,
        "profile_path": _relative(profile_path),
        "stats_path": _relative(stats_path),
    }


def _run_worker_count(seeds: tuple[str, ...], workers: int) -> dict:
    started = time.perf_counter_ns()
    pool_error = None
    try:
        context = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
            results = list(pool.map(_measure_job, seeds))
    except Exception as exc:  # noqa: BLE001 - report pool failures in receipt
        results = [_failure(seed, exc) for seed in seeds]
        pool_error = {"error_type": type(exc).__name__, "error": str(exc)}
    elapsed = (time.perf_counter_ns() - started) / 1_000_000_000
    successful = sum(1 for result in results if result.get("ok"))
    return {
        "workers": workers,
        "runs_requested": len(seeds),
        "runs_completed": successful,
        "runs_failed": len(seeds) - successful,
        "elapsed_seconds": elapsed,
        "throughput_runs_per_second": successful / elapsed if elapsed else 0.0,
        "results": results,
        "pool_error": pool_error,
    }


def scale(seeds: tuple[str, ...], workers: tuple[int, ...]) -> list[dict]:
    """Run the same ordered seed matrix at every worker count."""
    rows = [_run_worker_count(seeds, count) for count in workers]
    baseline = next((row for row in rows if row["workers"] == 1), None)
    baseline_elapsed = baseline["elapsed_seconds"] if baseline else None
    baseline_digests = {
        result["seed"]: result.get("digest")
        for result in baseline["results"]
        if result.get("ok")
    } if baseline else {}
    for row in rows:
        row["speedup_vs_one_worker"] = (
            baseline_elapsed / row["elapsed_seconds"]
            if baseline_elapsed and row["elapsed_seconds"] else None
        )
        row["parallel_efficiency"] = (
            row["speedup_vs_one_worker"] / row["workers"]
            if row["speedup_vs_one_worker"] is not None else None
        )
        for result in row["results"]:
            if row["workers"] == 1:
                result["parity"] = "baseline"
            elif not result.get("ok"):
                result["parity"] = "not_available"
            elif baseline_digests.get(result["seed"]) == result.get("digest"):
                result["parity"] = "match"
            else:
                result["parity"] = "mismatch"
    return rows


def _environment() -> dict:
    return {
        "engine_version": ENGINE_VERSION,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "project_root": str(PROJECT_ROOT),
    }


def build_receipt(profile_seed: str, seeds: tuple[str, ...], workers: tuple[int, ...],
                  output_dir: Path, *, profile_only: bool = False,
                  scale_only: bool = False) -> tuple[dict, int]:
    profile = None if scale_only else profile_one(profile_seed, output_dir)
    scaling = [] if profile_only else scale(seeds, workers)
    failures = []
    if profile and not profile["result"].get("ok"):
        failures.append({"stage": "profile", **profile["result"]})
    for row in scaling:
        for result in row["results"]:
            if not result.get("ok") or result.get("parity") == "mismatch":
                failures.append({"stage": "scaling", "workers": row["workers"], **result})
    receipt = {
        "schema": "hollow-star-benchmark-receipt-1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "environment": _environment(),
        "workload": {
            "strategy": "baseline",
            "run_mode": "DESIGN",
            "durable_saves": False,
            "profile_seed": profile_seed,
            "scaling_seeds": list(seeds),
            "worker_counts": list(workers),
            "action_loop": "single-threaded per run",
        },
        "profile": profile,
        "scaling": scaling,
        "failures": failures,
        "success": not failures,
    }
    return receipt, 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-seed", default=DEFAULT_PROFILE_SEED)
    parser.add_argument("--seed", action="append", dest="seeds",
                        help="override the fixed scaling seed matrix; repeat for each seed")
    parser.add_argument("--workers", nargs="+", type=int, default=list(DEFAULT_WORKERS))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--profile-only", action="store_true")
    parser.add_argument("--scale-only", action="store_true")
    args = parser.parse_args()
    if args.profile_only and args.scale_only:
        parser.error("--profile-only and --scale-only are mutually exclusive")
    if not args.workers or any(count < 1 for count in args.workers):
        parser.error("worker counts must be positive")
    seeds = tuple(args.seeds) if args.seeds else DEFAULT_SEEDS
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = _validate_output_dir(args.output_dir or BENCHMARK_ROOT / timestamp)
    receipt, exit_code = build_receipt(
        args.profile_seed, seeds, tuple(args.workers), output_dir,
        profile_only=args.profile_only, scale_only=args.scale_only)
    receipt_path = output_dir / "benchmark_receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
    print(json.dumps({
        "receipt": _relative(receipt_path),
        "success": receipt["success"],
        "failures": len(receipt["failures"]),
    }, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
