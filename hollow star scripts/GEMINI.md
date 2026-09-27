# GEMINI.md — Hollow Star Engine Workspace Contract

This file is auto-loaded as context by Gemini CLI and Antigravity CLI whenever
they run inside `hollow star scripts/`. Antigravity preserves the Gemini CLI
context-file contract, so the filename remains stable while both agent
surfaces remain available. It is the equivalent of `CLAUDE.md` / `AGENTS.md`,
scoped to this folder only.

## What this is

`hollow star scripts/` is a software project: the `hollowstar` Python game
engine, its `tests/` suite, the `web/` client, and supporting tools. Work here
is ordinary software engineering — read code, run tests, write code, fix
failures.

## What this is not

**None of the Divine Mythos corpus governance applies in this folder.** There
is no STANCE line, no SANDBOX/FORGE/SCALPEL mode, no canon-file-reading gate,
and no voice restriction. Those rules live in the parent workspace's
`CLAUDE.md` and `AGENTS.md` and govern narrative/canon work only.

## Hard boundary

Never read, write, or reference as authoritative anything outside this
folder, specifically:

- `divine mythos set/` — the canon corpus
- `project context/` — snapshots, frozen pack, history archive
- Any `DM0xx_x`-numbered file

If a task seems to require corpus content (e.g. "make the game match canon
lore X"), stop and say so instead of reading corpus files directly — that
read-and-render step belongs to a Claude Code or Codex session working under
the parent workspace's rules, not to a Gemini CLI engine session.

`hollowstar/content/divine_mythos_registry.json` is the one sanctioned
exception: it is engine data already extracted for gameplay use, not a live
corpus read.

## Verification contract

Before claiming any change works, run:

```
python tools/run_discovered_tests.py
```

from `hollow star scripts/`. It is a dependency-free `unittest` runner over
every `tests/test_*.py` module — no pytest install required, zero LLM cost.
Exit code 0 means clean. `--module <path>` scopes to one file while iterating.

`hsr_full_check.py` in this folder forwards to the parent workspace's
`tools/check.py` (the corpus-side six-stage chain) — only run that when a
change actually touches the HSR bridge files (`host_config.json`,
`HSR_HANDSHAKE.json`, `snapshots/party_snapshot.json`), not for ordinary
engine changes.

## Coordination

Codex and Claude Code also work this folder. Before a multi-file pass, check
recent mtimes across `hollowstar/`, `tests/`, and `web/` for signs of a
concurrent edit in progress, and avoid stacking a change on top of one that
looks mid-flight. After any pass, the calling agent re-runs
`run_discovered_tests.py` itself before trusting the result — a green run
reported by this session is not a substitute for that re-check.
