"""Delegate a scoped HSR engine task to headless Gemini CLI.

Offloads well-defined ``hollow star scripts/`` engineering tasks (bug fixes,
small features, test maintenance) to Gemini CLI. Read-only by default;
``--write`` lets Gemini edit files. Every write run is re-verified with the
dependency-free HSR test runner unless ``--skip-verify`` is supplied.

Usage
-----
  python tools/gemini_dispatch.py "explain why test_combat.py:42 fails"
  python tools/gemini_dispatch.py --write "fix the failing assertion in test_combat.py"
  python tools/gemini_dispatch.py --write --timeout 1200 "<task>"

Requires a one-time interactive ``gemini`` login (OAuth) and folder-trust
acceptance -- this script cannot perform that step itself.
"""

from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

HSR_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = HSR_ROOT / ".gemini_dispatch"
DEFAULT_TIMEOUT = 900


def find_gemini_bin() -> str:
    override = os.environ.get("GEMINI_CLI_PATH")
    if override:
        return override
    found = shutil.which("gemini")
    if found:
        return found
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidate = Path(appdata) / "npm" / "gemini.cmd"
        if candidate.exists():
            return str(candidate)
    raise SystemExit(
        "gemini CLI not found on PATH, and GEMINI_CLI_PATH is not set. "
        "Open a fresh shell so the npm global bin is on PATH, or set "
        "GEMINI_CLI_PATH to the gemini executable."
    )


def run_verification() -> int:
    return subprocess.run(
        [sys.executable, str(HSR_ROOT / "tools" / "run_discovered_tests.py")],
        cwd=HSR_ROOT,
    ).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task", help="Task description / prompt for Gemini.")
    parser.add_argument(
        "--write", action="store_true",
        help="Allow Gemini to edit files (approval-mode auto_edit). Without this flag, runs read-only (approval-mode plan).",
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"Seconds before the Gemini call is killed (default {DEFAULT_TIMEOUT}).",
    )
    parser.add_argument("--model", help="Passed through as --model to gemini.")
    parser.add_argument(
        "--skip-verify", action="store_true",
        help="Skip the automatic test re-run after a --write dispatch.",
    )
    args = parser.parse_args()

    gemini_bin = find_gemini_bin()
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"{stamp}.log"
    approval_mode = "auto_edit" if args.write else "plan"
    command = [
        gemini_bin,
        "-p", args.task,
        "--include-directories", str(HSR_ROOT),
        "--approval-mode", approval_mode,
        "--skip-trust",
    ]
    if args.model:
        command += ["--model", args.model]

    print(f"Dispatching to Gemini CLI ({'write' if args.write else 'read-only'} mode)...")
    print(f"Log: {log_path}")
    try:
        proc = subprocess.run(
            command, cwd=HSR_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=args.timeout,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        returncode = proc.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "") + f"\n\n[TIMED OUT after {args.timeout}s]"
        returncode = 124

    log_path.write_text(
        f"task: {args.task}\nmode: {approval_mode}\ncommand: {command}\n\n{output}",
        encoding="utf-8",
    )
    print(output.strip()[-4000:])

    if returncode != 0:
        print(f"\nGemini CLI exited {returncode}. See {log_path} for the full transcript.")
        return returncode

    if args.write and not args.skip_verify:
        print("\nRe-verifying with tools/run_discovered_tests.py ...")
        verify_code = run_verification()
        if verify_code != 0:
            print("Verification FAILED after Gemini's change -- do not trust this result as-is.")
            return verify_code
        print("Verification clean.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
