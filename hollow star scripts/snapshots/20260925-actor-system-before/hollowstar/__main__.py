"""Allow ``python -m hollowstar`` when the HSR project is on sys.path."""

from hollowstar.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
