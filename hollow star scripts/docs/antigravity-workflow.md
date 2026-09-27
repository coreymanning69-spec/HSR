# Antigravity workflow

Antigravity CLI is an optional peer agent surface for Hollow Star. Gemini CLI,
Claude Code, and Codex remain supported; nothing in this document changes the
default agent or authority boundary. The repository keeps the CLI and SDK
paths separate so ordinary engine tests do not require the optional compiled
SDK runtime.

## Install and authenticate

On Windows PowerShell, install the CLI with:

```powershell
irm https://antigravity.google/cli/install.ps1 | iex
```

Start `agy` once in an interactive terminal to complete Google sign-in. For
headless API-key use, set `modelProvider` to `gemini` in
`~/.gemini/antigravity-cli/settings.json` and export `GEMINI_API_KEY`.

The Antigravity workspace MCP profile is kept at `.agents/mcp_config.json`.
It points at the existing local Hollow Star MCP server and does not change the
host-authoritative game boundary.

## Dispatch a task

From `hollow star scripts/`:

```powershell
python tools/antigravity_dispatch.py "inspect the combat test failures and report the cause"
python tools/antigravity_dispatch.py --write "repair the focused combat test failure"
```

The dispatcher uses `--mode=plan` by default and `--mode=accept-edits` only
with `--write`. Write dispatches automatically run
`tools/run_discovered_tests.py`; use `--skip-verify` only when the caller will
perform an equivalent verification pass.

Set `AGY_CLI_PATH` when `agy` is installed outside the normal PATH or local
Windows install directory. Logs are written to `.antigravity_dispatch/`.

## Use the Python API

Install the optional SDK:

```powershell
pip install -r requirements-antigravity.txt
```

Then run:

```powershell
python tools/antigravity_api.py "summarize the HSR web transport boundary"
python tools/antigravity_api.py --write "implement the approved focused change"
```

The API adapter lazy-loads `google-antigravity`, uses the workspace skills
directory when present, and restricts default calls to the SDK's read-only
built-in tool set. The API-key and Vertex or Gemini Enterprise authentication
options are configured by the SDK environment, not stored in this repository.

## Relationship to Gemini CLI

`tools/gemini_dispatch.py` remains the Gemini CLI path. Antigravity is exposed
independently through `tools/antigravity_dispatch.py`; callers choose which
agent to use for a task. Both paths retain the same post-write HSR test
verification contract.
