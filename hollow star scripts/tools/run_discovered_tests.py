"""Run every unittest case and top-level test function in discovered modules."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import sys
import unittest
from pathlib import Path


HSR_ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = HSR_ROOT / "tests"
sys.path.insert(0, str(HSR_ROOT))


def load_module(path: Path):
    # Stable import names matter to multiprocessing-based replay tests on
    # Windows: spawned workers must be able to import the test class again.
    name = f"tests.{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import test module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def module_suite(path: Path) -> tuple[unittest.TestSuite, int]:
    module = load_module(path)
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    function_count = 0
    for name, value in sorted(vars(module).items()):
        if (name.startswith("test_") and inspect.isfunction(value)
                and value.__module__ == module.__name__):
            suite.addTest(unittest.FunctionTestCase(value, description=f"{path.name}:{name}"))
            function_count += 1
    return suite, function_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", type=Path)
    args = parser.parse_args()
    paths = [args.module.resolve()] if args.module else sorted(TEST_DIR.glob("test_*.py"))
    if not paths:
        print("no test modules discovered", file=sys.stderr)
        return 2
    suite = unittest.TestSuite()
    function_count = 0
    for path in paths:
        current, count = module_suite(path)
        suite.addTests(current)
        function_count += count
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"DISCOVERED_MODULES={len(paths)} DISCOVERED_FUNCTION_TESTS={function_count} "
          f"EXECUTED={result.testsRun}")
    return 1 if result.failures or result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
