# Work Order: HSR Arcade (Side-Scrolling) Combat Mode — Server Transport + Client Renderer

**Assignee:** GitHub Copilot coding agent
**Author:** Claude Sonnet 5, on behalf of Corey (project owner)
**Status:** Ready to start. Engine-layer prerequisites are already merged (see "What already exists" below) — this order covers only what remains.
**Repo root for all paths below:** `hollow star scripts/`

---

## 0. Read this whole section before writing any code

This work order exists because the easy version of this task is to fake it: stub
the hard parts, hardcode one test room, skip real collision math, and call it
"done" with a green checkmark and no actual playable feature. **That version of
this task is a failure, even if every existing test still passes.** The
acceptance criteria at the bottom are the actual definition of done, not the
test suite alone — a PR that passes tests but does not produce a real,
playable, browser-verified side-scrolling encounter with real hitboxes,
real obstacle gating, and real server-authoritative state is incomplete work
and will be sent back.

If you hit a design ambiguity this document doesn't resolve, do not silently
pick the easiest interpretation and move on. Say so explicitly in the PR
description under "Open questions I resolved myself" with your reasoning, so
it can be reviewed — but still ship a real, working decision, not a stub with
a comment.

### Things that are explicitly not acceptable, anywhere in this PR

- A hitbox/collision function that always returns `True`, always returns
  `False`, or ignores its arguments and returns a canned result.
- A canvas renderer that draws a static placeholder image instead of moving
  sprites in response to real position data.
- Client-side code that computes damage, decides whether an attack hits, or
  otherwise makes authoritative combat decisions. The server (`arcade.py`)
  is authoritative for everything except animation interpolation between
  ticks. If you find yourself computing HP or hit/miss in JavaScript, stop —
  you are re-deriving state the server already owns.
- A single hardcoded arcade room used to "prove the concept" left as the only
  content wired up, with no path for any other room to opt in. The content
  schema (`encounter_mode: "arcade"`) must work for **any** room that declares
  it, not just one you special-cased.
- Obstacles that exist in data but are never actually checked against the
  moving entity's current movement mode (i.e., decorative obstacles that
  don't block anything).
- Wren's flight or Doran's climb/jump treated as cosmetic animation state that
  doesn't actually gate movement through obstacles.
- Deleting, weakening, or skip-marking any existing test to make the suite
  pass. If an existing test seems to conflict with new work, that is a signal
  to investigate, not to silence the test.
- `# TODO`, `# FIXME`, `pass  # not implemented`, or any placeholder function
  body left in the final PR. Every function you add must do the real thing.
- Committing without running the verification steps in Section 6 and pasting
  the actual output into the PR description. "Should work" is not a
  verification.

### Workspace rules that bind this work (from `AGENTS.md`, this repo's root policy)

- **This is not a Git repository at the workspace root**, but your work
  happens through GitHub/Copilot's own repo mechanism as normal — that
  restriction is about the local desktop folder, not about how Copilot
  delivers this PR. Follow GitHub's normal PR workflow.
- **Never touch anything under `divine mythos set/`** (the `DM0xx` corpus
  files) in this PR. This work order is scoped entirely to
  `hollow star scripts/`. If you believe a corpus fact is missing (e.g. no
  authored vertical flight speed for Wren), note it in the PR description
  under "Corpus gaps found" instead of inventing or editing the number
  yourself.
- **Never touch `project context/TR3_SKT_25_FILE_PACK/`.**
- Run the existing verification tooling (Section 6) before calling anything
  done — this project treats "checker clean" as a real exit criterion, not a
  suggestion.
- Filename convention: new authored files use lowercase kebab-case for
  human-readable portions; the existing Python package
  (`hollow star scripts/hollowstar/`) already uses `snake_case.py` module
  names — match the existing convention in whichever directory you're adding
  to. Don't invent a third style.

---

## 1. What already exists (do not re-build these; read them first)

All paths relative to `hollow star scripts/`.

### Engine (Python), already merged

- **`hollowstar/spatial.py`** — the shared spatial data model. Contains:
  - `MovementMode` enum: `RUN`, `JUMP`, `CLIMB`, `FLY`, `FALL`.
  - `SpatialEntity` dataclass: position, facing, movement_mode, hurtbox,
    velocity, grounded, status_tags.
  - `Hitbox` dataclass: owner id, shape, active-frame window, damage type/expression.
  - `movement_capabilities(identity)` — Doran gets `{RUN, JUMP, CLIMB}`, Wren
    gets `{RUN, JUMP, FLY}`, everyone else gets `{RUN, JUMP}`.
  - `resolve_hitbox_overlap(entities, hitboxes, frame)` — pure AABB overlap
    function, frame-gated, returns hit events. **Read this function's
    signature carefully before calling it from `arcade.tick`** — it already
    exists and works; do not write a second collision function.
- **`hollowstar/arcade.py`** — the real-time encounter engine. Contains:
  - `enter_from_room(run, row)` — builds an `ArcadeEncounter` at
    `run.context["arcade"]` from `room_state.combat_geometry(row)` and the
    actors already set up by `t.begin` (i.e. it assumes `combat()` has already
    run for this room — see Section 2.1, this assumption needs verifying and
    hardening, not replacing).
  - `tick(run, inputs)` — the one place server state changes per frame.
    Applies movement deltas, resolves hitbox overlaps via `spatial.py`, routes
    damage through `tactical.damage` (via `spawn_hit`), detects wave-clear,
    sets `gate_open`/`complete` on the encounter.
  - `toggle_flight(run, key, on)` / `set_movement_mode(run, key, mode_name)` —
    gate on `is_wren` + the existing `fly_speed` resource flag (see below).
  - `move_entity` / `_blocked_by_obstacles` — obstacle gating by movement mode.
  - `view(run)` — a read-only projection of arcade state for the client.
  - **This file is unfinished plumbing, not a finished feature.** It has never
    been called from `dungeon.act`, never been exercised by a test, and never
    been driven by a real client. Treat every function in it as needing
    verification, not as ground truth to build blindly on top of.
- **`hollowstar/tactical.py`** — flight already partially existed here before
  this work order (`wings`/`flight_move`/`ascend`/`descend` actions,
  `r["fly_speed"]`). A `land` action was added (~line 1082-1085) and `fly` is
  now an alias for `wings` in the action dispatcher inside `apply()`. This is
  the turn-based mode's flight toggle — **arcade mode's flight must read the
  same `r.get("fly_speed")` flag**, never a second, competing flight flag.
- **`hollowstar/intent.py`** — `fly` and `land` are parseable free-text
  commands (see the `aliases` dict and `supported` set around line 436-438,
  and the dispatch branch around line 450).
- **Web client button** — `hollow star scripts/web/app.js` around line 619
  has "Take Flight"/"Land" buttons in the existing turn-based flight-controls
  panel. This is unrelated to arcade mode's UI (Section 4) but confirms the
  flight flag convention end-to-end for the turn-based mode.

### What is explicitly NOT done yet (this work order's actual scope)

1. `arcade.py` is never invoked from anywhere in the request-handling chain.
   No player action can ever reach it today.
2. There is no content schema support (`encounter_mode: "arcade"`,
   `"waves"`, `required_mode` on structures) actually read by `dungeon.py` —
   `room_state.combat_geometry` already returns `structures` with whatever
   is in room data, but nothing generates or consumes `required_mode` end to
   end yet.
3. There is no client code for arcade mode at all: no canvas, no input
   handling, no rendering of entities/obstacles/waves.
4. `arcade.enter_from_room` has never been called with real room data and may
   have bugs that only show up against `room_state.combat_geometry`'s actual
   output shape — verify this, don't assume it works.
5. No automated tests exist for `spatial.py` or `arcade.py` at all.

---

## 2. Server-side integration (Python)

### 2.1 Wire `arcade.py` into the action pipeline

Read `hollowstar/dungeon.py`, function `act(run, action)` (starts at line
1232). This is the actual dispatcher every player action passes through —
confirmed by tracing `hollowstar_web_server.py` → `hollowstar/host.py`
(`design_action`/`design_turn` commands, around line 785-820) →
`hollowstar/run_service.py` (`design_action`, line 401-443, which calls
`dungeon.act(run, action)` for the default dungeon scenario) → `dungeon.act`.
**Do not invent a new transport layer or a new host command.** The existing
`design_action` command already forwards an arbitrary `{"type": ..., ...}`
action dict all the way to `dungeon.act` — that is your transport. Confirm
this yourself by tracing the call chain before writing code; don't take this
paragraph's word for it.

Inside `dungeon.act`, there is already a block (around line 1288):

```python
if 'combat' in run.context and not run.context['combat']['complete']:
    if kind in {'investigate', 'negotiate', 'avoid'}:
        ...
    result = _complete_combat_action(run, row, t.apply(run, action))
```

Add a new branch **before** the `_complete_combat_action(run, row, t.apply(run, action))` fallback, for arcade-specific action kinds:

```python
if kind in {'arcade_tick', 'arcade_toggle_flight', 'arcade_set_movement_mode'}:
    from hollowstar import arcade
    if 'arcade' not in run.context:
        raise t.ActionError('arcade mode is not active for this room')
    if kind == 'arcade_tick':
        result = arcade.tick(run, action.get('inputs'))
    elif kind == 'arcade_toggle_flight':
        result = arcade.toggle_flight(run, action.get('actor'), bool(action.get('on')))
    else:
        result = arcade.set_movement_mode(run, action.get('actor'), action.get('mode'))
    d['events'].append(copy.deepcopy(result))
    return result
```

This is a starting sketch, not a copy-paste final answer — check it compiles,
check `t.ActionError` is the right exception type to raise here (match the
surrounding code's convention exactly), and check whether `_pressure()` (the
call earlier in `act`, line ~1245) should be skipped for `arcade_tick` given
it runs many times per second (it almost certainly should — a room-time-cost
model built for one action per turn will blow up if charged once per animation
frame; **do not just let this silently run and see what happens** — read
`_pressure`'s cost table and either give arcade actions an explicit zero-cost
entry or route them around the pressure call entirely, with a comment
explaining which you chose and why).

### 2.2 Start an arcade encounter when a room opts in

Read `dungeon.py`'s `combat(run, boss=False)` function (line 568-617,
approximately — re-locate it, don't trust a stale line number after your
edits shift things). Today, every combat/boss room calls `t.begin(run, rs)`
and sets up terrain. You need to add: after `t.begin` and the terrain setup,
if the room row has `row.get('encounter_mode') == 'arcade'`, call
`arcade.enter_from_room(run, row)`.

You must also add the reverse cleanup: when a room's combat concludes (the
existing "combat complete" handling — trace `_complete_combat_action` in
`dungeon.py` to find where `run.context.pop('combat', None)` or equivalent
cleanup already happens for the turn-based mode), pop `run.context.pop('arcade', None)`
too, so a stale arcade encounter never leaks into the next room. **Find this
by reading the existing turn-based cleanup path, don't guess where it is.**

### 2.3 Content schema (additive only — do not touch existing room data files' meaning)

In `hollowstar/content/dungeon.json` and/or
`hollowstar/content/modules/reliquary-template/floors.json` (check which one
actually defines the floor/room structures consumed by `dungeon.start`/`enter`
— read `dungeon.py`'s `config()` and `start()` functions to confirm which file
is load-bearing for the room you're about to edit), add `encounter_mode` and
`waves` to **exactly one real room** as your vertical-slice test room — pick
a floor-1 combat room. Also add at least one `structures` entry with a
non-empty `required_mode` (e.g. a gap requiring `["jump", "fly"]`) to that
room's data, following the existing `structures` shape already validated by
`room_state.combat_geometry` (line 190-209 of `room_state.py` — read its
validation rules, your JSON must satisfy them: integer 3D `position`,
non-negative integer `hp`, non-empty `kind`/`object_id`).

Untagged rooms (no `encounter_mode` key) must continue to run the existing
turn-based combat exactly as before — **prove this** with a test that starts
a normal room and confirms `run.context` has no `arcade` key.

### 2.4 Wave-clear → room progression

`arcade.tick`'s `_wave_cleared` check already sets `arcade["complete"] = True`
and `arcade["gate_open"] = True` when the last wave is cleared. You must wire
this to the same room-resolution path the turn-based mode uses
(`row['resolved'] = True`, `award(run, method)` — trace how the turn-based
combat-complete path calls `award`, in `_complete_combat_action` or wherever
`run.context['combat']['complete']` is checked after a turn-based fight ends).
When `arcade["complete"]` becomes `True` inside a `tick()` call, the same
room-resolution call must fire — do not leave the room permanently "cleared
but not marked resolved," which would strand the player unable to progress.

### 2.5 Tests (mandatory, not optional)

Add a new file `hollow star scripts/tests/test_arcade.py` following the
existing style of `tests/test_gameplay.py` (same `unittest.TestCase` +
`RunService`/fixture-setup conventions — copy the setup pattern from an
existing combat test, don't invent a new harness). At minimum, cover:

- `spatial.resolve_hitbox_overlap`: a hit that should land (owner and target
  overlap, hitbox active in the current frame), a hit that should not land
  because the hitbox is outside its active-frame window, a hit that should
  not land because the boxes don't overlap, and same-side entities not
  producing a hit event (or confirm this is `arcade.tick`'s job — trace which
  layer is actually responsible and test that layer, don't test both loosely).
- `arcade.enter_from_room`: called against a real room built through
  `dungeon.start`/`dungeon.enter` (not a hand-built fake dict) for the vertical
  slice room from 2.3, confirming entities exist for every actor and obstacles
  exist for every `required_mode` structure.
- `arcade.tick`: a full scenario — spawn a wave, land a hit that kills the one
  enemy, confirm `gate_open`/`complete` flip true, confirm the underlying
  actor's HP actually went through `tactical.damage` (check `event.get("result")`
  or whatever `spawn_hit` returns carries the real damage event shape, not a
  fabricated one).
- Obstacle gating: an entity in `RUN` mode blocked by a gap requiring `FLY`;
  the same entity switched to `FLY` via `set_movement_mode` then able to pass.
- Wren-only flight gate: `toggle_flight` raising `ArcadeError` for Doran, and
  raising for Wren when `fly_speed` is not set (wings not manifested), and
  succeeding once `wings`/`fly` has been applied through `tactical.apply`
  first (chain the two calls in the test — don't fake the flag directly
  unless you also have one test that goes through the real `tactical.apply`
  path).
- The 2.3 regression: a normal (non-arcade) room produces no `arcade` key in
  `run.context`.
- `dungeon.act` routing: an `arcade_tick` action reaching `arcade.tick` through
  the real `dungeon.act` function (not by calling `arcade.tick` directly),
  proving the wiring in 2.1 actually works end-to-end.

---

## 3. Client-side renderer (JavaScript, `hollow star scripts/web/`)

This is the part most likely to get half-built. A canvas that draws once and
never updates, or that doesn't actually read server state, does not satisfy
this section.

### 3.1 `arcade-canvas.js` (new file)

- A `<canvas>` element, created and appended to the DOM only when the current
  room's public view indicates `encounter_mode === "arcade"` (you will need to
  add this field to whatever `dungeon.public_room`/`build_public_view`
  currently returns for a room — check `hollowstar/view_model.py` and
  `dungeon.public_room` (line ~486) and add `encounter_mode` to the visible
  room fields there; it is not there today).
- A real `requestAnimationFrame` loop that:
  - Reads the latest server-provided arcade state (positions, movement modes,
    obstacles — the shape `arcade.view(run)` returns, which you must also
    expose through the server response; check what `arcade_tick`'s result
    dict contains today and extend it if the client needs more than events —
    it likely needs the full `view()` payload alongside the tick's event
    diff, not just the diff, for the client to render without accumulating
    drift).
  - Draws every entity as a positioned sprite (reuse existing sprite lookup —
    see `sprite-renderer.js`'s sprite-selection logic and factor it into a
    function usable by both the old DOM renderer and this canvas renderer;
    do not duplicate the sprite-id-to-asset-path logic in two places).
  - Draws obstacles distinctly from entities (different color/shape is fine
    for a first pass, but they must be visibly present and positioned
    correctly relative to entities — verify this visually, not just "the
    array has objects in it").
  - Interpolates entity position between the last two server ticks for smooth
    motion — do not snap positions instantly on every tick if ticks arrive
    slower than the animation frame rate (they will: server ticks are
    request/response over HTTP, animation frames are ~60/sec).
- Mounted/unmounted from `app.js`'s existing room-render point — find where
  `app.js` currently decides what to render for the "battle" view (the
  `battle()` function, line ~615) and add the `encounter_mode === "arcade"`
  branch there, replacing the DOM battle stage for that mode only. Every
  other room kind must render exactly as it does today — **run the existing
  UI manually against a non-arcade room after your change and confirm nothing
  regressed** (Section 6.3).

### 3.2 `arcade-input.js` (new file)

- Keyboard input (arrow keys or WASD — pick one, document your choice) mapped
  to movement deltas sent via `command: "design_action"` /
  `{"type": "arcade_tick", "inputs": [{"actor": <controller's key>, "dx": ..., "dy": ...}]}`
  through the existing `hsr-client.js` fetch wrapper (`hsr-client.js`, lines
  13-92 — reuse its existing request method, do not write a second fetch
  wrapper).
- A dedicated key or on-screen button for the Wren flight toggle
  (`arcade_toggle_flight`) and for cycling movement mode where relevant
  (jump/climb) via `arcade_set_movement_mode` — these need visible UI
  affordance (a button, not just an undocumented keybinding), since this is
  explicitly one of the things Corey asked to be checked for in an earlier
  pass on this project (buttons must exist for the actions, not just server
  support).
- Basic touch/mobile consideration is not required for this PR; keyboard-only
  is acceptable, but say so explicitly in the PR description rather than
  silently shipping desktop-only with no note.

### 3.3 `arcade-loop.js` (new file)

- Owns the fixed-cadence polling of `arcade_tick` (e.g. every 100-150ms —
  pick a real number, justify it in a comment: too fast floods the Python
  backend with HTTP round-trips per tick, too slow feels unresponsive).
- Must handle a `gate_open`/`complete: true` response by transitioning the UI
  back to the normal room view (call the existing room-refresh/reload path in
  `app.js` — find it, don't build a second one) so the player can actually
  progress after clearing a wave. **This is the single most important thing
  to get right end-to-end** — if this doesn't work, the feature doesn't
  actually let anyone finish an arcade room, which is the entire point.

---

## 4. Explicit non-goals for this PR (do not scope-creep, but do not use this list as an excuse to skip Sections 2-3)

- Turn-based Gambit/macro combat is a separate future milestone. Do not start
  it in this PR.
- CLI-only and point-and-click-only play modes for arcade combat are not in
  scope — the canvas client is the only client surface required here.
- Multiple simultaneous arcade rooms / floors beyond the one vertical-slice
  room from 2.3 are not required, but the **code path** must not be
  special-cased to that one room's ID — it must work for any room with
  `encounter_mode: "arcade"` in its data. If you find yourself writing
  `if room_id == "1:3":` anywhere, that's a hardcode violation, not a
  simplification.
- Custom third-character support beyond what `spatial.movement_capabilities`
  already provides (default `{RUN, JUMP}` for unknown identities) is
  sufficient — do not invent new lore-bound abilities for a hypothetical
  custom character.

---

## 5. File manifest (everything this PR should touch)

New:
- `hollow star scripts/tests/test_arcade.py`
- `hollow star scripts/web/arcade-canvas.js`
- `hollow star scripts/web/arcade-input.js`
- `hollow star scripts/web/arcade-loop.js`

Edited:
- `hollow star scripts/hollowstar/dungeon.py` (Section 2.1, 2.2, 2.4)
- `hollow star scripts/hollowstar/view_model.py` and/or `dungeon.py`'s
  `public_room` (Section 3.1 — exposing `encounter_mode` publicly)
- `hollow star scripts/hollowstar/content/dungeon.json` or
  `hollow star scripts/hollowstar/content/modules/reliquary-template/floors.json`
  (Section 2.3 — confirm which one is authoritative before editing)
- `hollow star scripts/web/app.js` (Section 3.1 mount point)
- `hollow star scripts/web/sprite-renderer.js` (Section 3.1 — extract the
  shared sprite-lookup helper; refactor, don't duplicate)
- `hollow star scripts/web/hsr-client.js` only if it genuinely needs a new
  thin passthrough method — check first whether the existing generic action
  method already suffices before adding anything here.

Do not touch: anything under `divine mythos set/`,
`project context/TR3_SKT_25_FILE_PACK/`, `.local/`, or any `DM0xx` file.

---

## 6. Verification (required before marking this PR ready for review)

Run every one of these and paste the actual terminal output (not a summary of
what you expect it to say) into the PR description.

1. **Full existing test suite**, to prove nothing regressed:
   ```
   PYTHONIOENCODING=utf-8 python -m unittest discover -s "hollow star scripts/tests" -v
   ```
2. **New arcade tests specifically**, isolated:
   ```
   PYTHONIOENCODING=utf-8 python -m unittest "hollow star scripts.tests.test_arcade" -v
   ```
3. **Repo verification chain**:
   ```
   PYTHONIOENCODING=utf-8 python tools/check.py
   ```
   If any step fails, fix the underlying issue — do not report "checker clean"
   without this actually passing, and do not silence a failing step.
4. **Manual browser verification** — start the web server
   (`hollowstar_web_server.py`), open the client, enter the vertical-slice
   arcade room from Section 2.3, and confirm, describing what you actually
   observed:
   - An enemy is visible entering from the right side of the canvas.
   - Moving the player character produces visible, smooth movement.
   - Attacking produces a real hit or miss against the enemy, and the
     enemy's HP visibly changes (or it dies) — not a canned animation with no
     underlying state change.
   - The gap/obstacle you added blocks normal movement, and Doran's jump (or
     Wren's flight toggle) actually lets the character cross it — demonstrate
     both the blocked case and the successful bypass.
   - Clearing the wave transitions the UI back to the normal room flow and
     the room shows as resolved/progressable.
   - A normal, non-arcade room still renders and plays exactly as before your
     change.

A PR description that skips step 4 or reports it without specific, concrete
observations ("it worked") will be treated as unverified and sent back.

---

## 7. PR description template (use this structure)

```
## Summary
<what was built, in plain terms>

## Section 2 (server) verification
<paste actual test output>

## Section 3 (client) verification
<describe the manual browser walkthrough from Section 6.4, concretely>

## Open questions I resolved myself
<any ambiguity in this work order you had to decide on your own, and why>

## Corpus gaps found
<any missing authored fact you noticed but did not invent a number for>

## Known limitations / explicitly out of scope
<anything deliberately deferred, per Section 4>
```
