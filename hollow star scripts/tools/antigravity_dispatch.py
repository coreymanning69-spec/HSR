"""Dispatch a scoped Hollow Star task to Antigravity CLI.

This is a parallel headless dispatcher alongside the existing Gemini CLI
dispatcher. It keeps the HSR verification contract local to this project: a write dispatch
is followed by ``tools/run_discovered_tests.py`` unless verification is
explicitly skipped.

Usage
-----
  python tools/antigravity_dispatch.py "explain why test_combat.py:42 fails"
  python tools/antigravity_dispatch.py --write "fix the failing assertion"
  python tools/antigravity_dispatch.py --model gemini-3-pro "review this module"

Antigravity CLI must be installed and authenticated once with an interactive
``agy`` session. For a Gemini API key, configure ``modelProvider`` as
``gemini`` in Antigravity's settings and export ``GEMINI_API_KEY``.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HSR_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = HSR_ROOT / ".antigravity_dispatch"
DEFAULT_TIMEOUT = 900


def find_antigravity_bin() -> str:
    """Resolve ``agy`` without requiring a shell profile refresh."""

    override = os.environ.get("AGY_CLI_PATH")
    if override:
        return override

    found = shutil.which("agy")
    if found:
        return found

    local_bin = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin"
    for name in ("agy.exe", "agy.cmd", "agy"):
        candidate = local_bin / name
        if candidate.exists():
            return str(candidate)

    raise SystemExit(
        "Antigravity CLI not found. Install it from "
        "https://antigravity.google/docs/cli/install/ or set AGY_CLI_PATH."
    )


def prompt_for_mode(task: str, write: bool) -> str:
    """Add an explicit scope guard while preserving the caller's task."""

    if write:
        return task
    return (
        "READ-ONLY TASK. Do not create, edit, move, rename, or delete files. "
        "You may inspect files and run safe diagnostics, then report findings.\n\n"
        + task
    )


def build_command(
    executable: str,
    task: str,
    *,
    write: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    model: str | None = None,
    agent: str | None = None,
    effort: str | None = None,
) -> list[str]:
    """Build a machine-readable, one-shot Antigravity invocation."""

    command = [
        executable,
        "-p",
        prompt_for_mode(task, write),
        "--mode=accept-edits" if write else "--mode=plan",
        "--output-format",
        "json",
        "--print-timeout",
        f"{timeout}s",
    ]
    if model:
        command.extend(["--model", model])
    if agent:
        command.extend(["--agent", agent])
    if effort:
        command.extend(["--effort", effort])
    return command


def response_from_output(stdout: str) -> tuple[str, dict[str, Any] | None]:
    """Extract the response and metadata from Antigravity JSON output."""

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout.strip(), None

    if not isinstance(payload, dict):
        return str(payload), None

    response = payload.get("response")
    if response is None:
        response = payload.get("text", "")
    return str(response).strip(), payload


def run_verification() -> int:
    return subprocess.run(
        [sys.executable, str(HSR_ROOT / "tools" / "run_discovered_tests.py")],
        cwd=HSR_ROOT,
    ).returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("task", help="Task description / prompt for Antigravity.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Use accept-edits mode. Without this flag, use plan mode.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Seconds before the Antigravity call is killed (default {DEFAULT_TIMEOUT}).",
    )
    parser.add_argument("--model", help="Passed through as --model to agy.")
    parser.add_argument("--agent", help="Passed through as --agent to agy.")
    parser.add_argument(
        "--effort",
        choices=("low", "medium", "high"),
        help="Passed through as --effort to agy.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip the automatic test run after a --write dispatch.",
    )
    args = parser.parse_args()

    antigravity_bin = find_antigravity_bin()
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"{stamp}.log"
    command = build_command(
        antigravity_bin,
        args.task,
        write=args.write,
        timeout=args.timeout,
        model=args.model,
        agent=args.agent,
        effort=args.effort,
    )

    print(f"Dispatching to Antigravity CLI ({'write' if args.write else 'plan'} mode)...")
    print(f"Log: {log_path}")
    try:
        proc = subprocess.run(
            command,
            cwd=HSR_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        returncode = proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        returncode = 124
        stderr += f"\n\n[TIMED OUT after {args.timeout}s]"

    response, metadata = response_from_output(stdout)
    log_path.write_text(
        f"task: {args.task}\nmode: {'accept-edits' if args.write else 'plan'}\n"
        f"command: {command!r}\n\nstdout:\n{stdout}\n\nstderr:\n{stderr}\n",
        encoding="utf-8",
    )

    if response:
        print(response[-4000:])
    elif stdout.strip():
        print(stdout.strip()[-4000:])
    if stderr.strip():
        print(stderr.strip()[-2000:], file=sys.stderr)

    if returncode != 0:
        print(f"Antigravity CLI exited {returncode}. See {log_path} for the full transcript.")
        return returncode

    if metadata is not None and metadata.get("status") in {
        "ERROR",
        "CANCELED",
        "INTERRUPTED",
        "INVALID",
    }:
        print(f"Antigravity reported status {metadata['status']}. See {log_path} for details.")
        return 1
    if metadata is not None and not response:
        print(f"Antigravity returned an empty response. See {log_path} for details.")
        return 1

    if args.write and not args.skip_verify:
        print("\nRe-verifying with tools/run_discovered_tests.py ...")
        verify_code = run_verification()
        if verify_code != 0:
            print("Verification FAILED after Antigravity's change -- do not trust this result as-is.")
            return verify_code
        print("Verification clean.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
