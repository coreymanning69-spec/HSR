"""Compatibility entrypoint for the authoritative workspace check.

``tools/check.py`` owns the complete six-stage chain. This wrapper preserves
the historical command name while forwarding every argument and reporting the
number of discovered HSR test modules without maintaining a second inventory
or state root.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


HSR_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = HSR_ROOT.parent
TEST_DIR = HSR_ROOT / "tests"


def discovered_test_count() -> int:
    return len(sorted(TEST_DIR.glob("test_*.py")))


def main() -> int:
    count = discovered_test_count()
    print(f"Discovered HSR test modules: {count}")
    proc = subprocess.run(
        [sys.executable, str(WORKSPACE_ROOT / "tools" / "check.py"), *sys.argv[1:]],
        cwd=WORKSPACE_ROOT,
    )
    print(f"Authoritative check: tools/check.py; discovered modules: {count}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
