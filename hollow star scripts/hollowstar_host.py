"""Path-independent launcher for the HSR local host.

It deliberately bootstraps only the adjacent HSR package.  It does not add
the Divine Mythos corpus to Python's import path.
"""

from __future__ import annotations

import sys
from pathlib import Path


HSR_ROOT = Path(__file__).resolve().parent
if str(HSR_ROOT) not in sys.path:
    sys.path.insert(0, str(HSR_ROOT))

from hollowstar.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
