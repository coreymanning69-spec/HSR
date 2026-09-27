"""Small Python API adapter for the optional Google Antigravity SDK.

Install the optional dependency with ``pip install -e .[antigravity]`` or
``pip install -r requirements-antigravity.txt``. The adapter is deliberately
lazy-imported so the normal HSR engine and test suite do not require the
compiled SDK runtime.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

HSR_ROOT = Path(__file__).resolve().parents[1]


async def run_agent(task: str, *, write: bool = False) -> str:
    """Run one task through the Antigravity SDK and return its text response."""

    try:
        from google.antigravity import Agent, CapabilitiesConfig, LocalAgentConfig
        from google.antigravity.types import BuiltinTools
    except ImportError as exc:
        raise SystemExit(
            "The Antigravity SDK is not installed. Run "
            "pip install -r requirements-antigravity.txt."
        ) from exc

    instruction = task
    config_kwargs: dict[str, object] = {}
    skills_root = HSR_ROOT / ".agents" / "skills"
    if skills_root.exists():
        config_kwargs["skills_paths"] = [str(skills_root)]

    if not write:
        instruction = (
            "READ-ONLY TASK. Do not create, edit, move, rename, or delete files. "
            "You may inspect files and run safe diagnostics, then report findings.\n\n"
            + task
        )
        config_kwargs["capabilities"] = CapabilitiesConfig(
            enabled_tools=BuiltinTools.read_only()
        )

    config = LocalAgentConfig(**config_kwargs)
    async with Agent(config) as agent:
        response = await agent.chat(instruction)
        return await response.text()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", help="Task description / prompt for Antigravity.")
    parser.add_argument("--write", action="store_true", help="Allow write-capable SDK tools.")
    args = parser.parse_args()
    print(asyncio.run(run_agent(args.task, write=args.write)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
