"""Compile Workbench runtime drafts locally; stdout by default, never publish."""
import argparse
import json
from pathlib import Path
import sys

HSR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HSR))
from hollowstar.runtime_contract import SCHEMA, compile_package, draft
from hollowstar.source_catalog import SourceCatalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", type=Path)
    parser.add_argument("--schema", action="store_true")
    parser.add_argument("--wrap-scene", action="store_true", help="Make a runtime draft from an existing scene package")
    args = parser.parse_args()
    try:
        if args.schema:
            result = SCHEMA
        else:
            if args.package is None:
                parser.error("package is required unless --schema is used")
            package = json.loads(args.package.read_text(encoding="utf-8"))
            result = compile_package(draft(package) if args.wrap_scene else package, SourceCatalog(HSR.parent))
        print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
