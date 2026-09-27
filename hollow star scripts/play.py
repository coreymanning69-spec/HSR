"""Standalone single-player HSR character screen launcher."""

from __future__ import annotations

import sys
from pathlib import Path

HSR_ROOT = Path(__file__).resolve().parent
if str(HSR_ROOT) not in sys.path:
    sys.path.insert(0, str(HSR_ROOT))


def main() -> int:
    # CLI/MCP callers keep using explicit commands. A bare play.py launch is
    # the web client so the terminal remains available for engine tooling.
    if len(sys.argv) > 1 and sys.argv[1] in {"cli", "--cli", "interactive", "-i"}:
        from hollowstar.cli import main as cli_main
        args = ["interactive", *sys.argv[2:]] if sys.argv[1] in {"cli", "--cli", "interactive", "-i"} else sys.argv[1:]
        return cli_main(args)
    from hollowstar_app import main as app_main
    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())
