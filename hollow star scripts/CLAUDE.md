# HSR (Hollow Star Reliquary) — working notes

See root `README.md` first for the cloud-working-copy rules (branch,
what never gets copied back, the location-guard test caveat).

## Verifying a UI change: don't screenshot first, don't re-derive a driver

`tools/ui-probe.cjs` already exists for exactly this. Full usage, the
in-page `HollowStarUI` probe object's schema, and this container's
Chromium/location-guard gotchas are documented in
`.claude/skills/hsr-ui-probe/SKILL.md` — read that before writing any new
Playwright script or asking to look at a screenshot. Short version:

```bash
cd "hollow star scripts"   # note the space in the dir name
NODE_PATH="$PWD/node_modules" node tools/ui-probe.cjs --mock --do "nav:journey"
```

`--mock` fakes the host and drives to `phase: 'ready'`, since the real
Python engine (`hollowstar_web_server.py`) can't boot in this cloud copy
(location-guard fails closed off the real desktop). Prefer this over trying
to get a live host running here.

## Tests

`cd "hollow star scripts" && python tools/run_discovered_tests.py` for the
Python engine suite (two location-guard tests are expected to fail here,
per root README). For the web client's Playwright suites:
`NODE_PATH="$PWD/node_modules" node tools/run_ui_tests.cjs`, or run one file
directly the same way as `ui-probe.cjs` above.

## Backend-only probing

`tools/probe_compact.py` — one compact JSON line per call against the
Python engine directly, no browser: `python3 tools/probe_compact.py status
<run_id>`. Output size is hard-capped so it never dumps a multi-MB state
tree back at a token-metered caller.
