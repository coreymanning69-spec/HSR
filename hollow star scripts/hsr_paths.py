#!/usr/bin/env python3
"""
HSR-specific path resolution.

Works from any directory: HSR folder, root, or via import.
Use this in all HSR entry points.

    from hsr_paths import HSR_ROOT, LOCAL_HSR, LOCAL_PROFILES
"""

from pathlib import Path

# HSR root (works from anywhere)
HSR_ROOT = Path(__file__).parent
PROJECT_ROOT = HSR_ROOT.parent

# Unified runtime state
LOCAL_ROOT = PROJECT_ROOT / ".local"
LOCAL_HSR = LOCAL_ROOT / "hsr"

# HSR-specific runtime
LOCAL_BENCHMARKS = LOCAL_HSR / "benchmarks"
LOCAL_PROFILES = LOCAL_HSR / "reliquary_profiles"
LOCAL_RUNS = LOCAL_HSR / "reliquary_runs"
LOCAL_VALIDATION = LOCAL_HSR / "validation_jobs"

# Corpus
CORPUS_ROOT = PROJECT_ROOT / "divine mythos set"

def ensure_directories() -> None:
    """Ensure all HSR-related directories exist."""
    for directory in [LOCAL_HSR, LOCAL_BENCHMARKS, LOCAL_PROFILES, LOCAL_RUNS, LOCAL_VALIDATION]:
        directory.mkdir(parents=True, exist_ok=True)
