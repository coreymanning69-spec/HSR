---
description: Launch and drive the HSR web client (hollow star scripts/web) for verification. Use this to check a UI change, inspect what a screen shows, or reach a gameplay screen — without a real backend and without a screenshot unless one is actually needed.
---

# HSR UI probe

Don't hand-roll a Playwright driver for this repo. `tools/ui-probe.cjs`
already exists, is text-first (no screenshot unless you ask for one), and
handles this container's Chromium quirk. Run everything from
`"hollow star scripts"` (the quoted dir with a space in its name) and put
`node_modules` on `NODE_PATH` since scripts run outside that directory
otherwise fail to resolve `playwright`:

```bash
cd "hollow star scripts"
NODE_PATH="$PWD/node_modules" node tools/ui-probe.cjs --help
```

First time in a fresh container: `npm install` in that directory (installs
`@playwright/test`; the browser binary itself is already pre-fetched at
`/opt/pw-browsers`, so nothing downloads).

## Why not just Playwright + screenshots

- This container's pre-fetched Chromium revision can trail whatever
  `@playwright/test` version is pinned in `package.json`. A bare
  `chromium.launch()` (no `executablePath`) either errors
  ("Executable doesn't exist at .../chrome-headless-shell") or hangs with
  zero output. `ui-probe.cjs` already detects `/opt/pw-browsers/chromium`
  and launches straight at it with `--no-sandbox`; don't re-litigate this,
  just call the tool.
- The real Python engine (`hollowstar_web_server.py`) refuses to boot in
  this cloud copy — its location-guard fails closed off the real desktop
  (see repo root `README.md`). Don't spend time trying to get a live host
  running here; use `--mock` (below) instead.
- Screenshots cost tokens and only answer visual questions. Everything
  else — is the right data showing, did a click do anything, is the DOM
  structurally broken — is a text/JS question. Ask it as one.

## Usage

```bash
# Title screen, text-only readout: status, errors, headings, controls, layout issues
node tools/ui-probe.cjs

# Click through and land on a specific gameplay screen, no real backend needed
node tools/ui-probe.cjs --mock --do "nav:journey"
node tools/ui-probe.cjs --mock --do "nav:room" --do "eval:HollowStarUI.getPublicView().room"

# Custom fixture instead of the built-in one-party/one-room default
node tools/ui-probe.cjs --mock --view my-fixture.json --do "nav:battle"

# Only take a screenshot when the question is genuinely visual
node tools/ui-probe.cjs --mock --do "nav:equipment" --shot equipment-tab
node tools/ui-probe.cjs --mock --baseline before   # save a reference
node tools/ui-probe.cjs --mock --diff before        # % changed + hottest region, not a picture
```

Steps for `--do` (run in order): `click:<button text>` · `hover:<button text>` ·
`key:<Key>` · `type:<text>` · `wait:<ms>` · `nav:<screen>` (any of the 10 tabs:
journey, room, battle, equipment, roster, residents, journal, map, library,
options) · `eval:<js expression>` (prints the JSON result — this is the main
way to check state without a screenshot).

## The in-page probe object

Once the client is running (mocked or live), `globalThis.HollowStarUI`
(schema `hsr-ui-client-3`, defined near the bottom of `web/app.js`) is
available in any `eval:` step or page-level `page.evaluate()`:

- `getStatus()` — `{phase, run_id, transport, busy}`
- `getPublicView()` — deep clone of the full public game state (party, room,
  scene, inventory, opposition, everything the host reports)
- `getCombatStatus()` — NPC-drain state, combat style, open radial menu,
  threat warnings, focus target, combat history
- `navigate(screen)` — jump straight to a tab (only works once `phase` is
  `'ready'`, i.e. after `--mock`'s boot sequence or a real host session)
- `refresh()` / `refreshReadout()` — re-render / re-pull from host

It's read-only by design ("no setters, nothing a click can't reach") — drive
state changes with `--do click:`/`key:`/`type:`, then read the result back
through these getters.

## Known gap

The probe's OVERLAP/OFFSCREEN layout checks are plain pairwise bounding-box
math — they don't know about an ancestor's `overflow: hidden|auto|scroll`.
The main nav bar (`.top-nav-tabs`) is an intentionally horizontally-scrollable,
edge-masked strip, so tabs that don't fit at the current viewport width will
report as "OVERLAP"ping the status HUD even though they're actually clipped
(invisible) until scrolled, and remain fully clickable via
`scrollIntoView()` + `click()`. Don't treat every OVERLAP finding in that one
region as a real bug without checking — everywhere else in the app, it's a
reliable signal.

## Other existing tools, don't duplicate

- `tools/probe_compact.py` — same idea for the Python engine directly (no
  browser at all): `python3 tools/probe_compact.py status <run_id>` etc.,
  one JSON line per call, hard-capped output size.
- `tests/*-check.cjs` — the full Playwright regression suites (title
  screen, options panels, combat, etc.). Run one directly the same way
  (`NODE_PATH=... node tests/ui-browser-check.cjs`), or `npm test` /
  `node tools/run_ui_tests.cjs` for all of them. These already mock the
  host the same way `--mock` does; `ui-probe.cjs` is for one-off
  ad hoc checks, the `tests/` suite is for asserted regressions.
