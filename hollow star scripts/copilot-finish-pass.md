# Copilot prompt — HSR Interface finish & polish pass

Paste everything below the line into Copilot. It is written to be run as-is.

---

You are working in `hollow star scripts/` of the Hollow Star Reliquary project (Windows, Python 3.14, no Git — do not run any git command, do not create a `.git` directory). The Python engine is authoritative for all rules; the web client only calls the host and renders what comes back. Never add game logic to JavaScript.

**Files you will touch:** `web/app.js`, `web/styles.css`, and only if a fix genuinely requires it, `hollowstar/view_model.py` or `hollowstar/intent.py`.

**How to run and verify:**
```
PYTHONIOENCODING=utf-8 python hollowstar_web_server.py --port 8765
```
then open http://127.0.0.1:8765. After any Python edit run:
```
python tools/run_discovered_tests.py
```
Two failures are pre-existing and NOT yours to fix unless trivial: `test_cross_adapter_contract` (compact vs public readout mismatch) and `test_hygiene` (CRLF line endings in `hollowstar/character_builder.py`). Everything else must stay green.

## What already landed (do not redo)

A previous pass added: Story Mode (FORGE) and Simulation Mode (SANDBOX) on the title screen; a party-select screen offering "Build a custom character" vs "Play as a Champion" (Doran / Wren, launched by name through `start-run`); one unified bottom console (`.hsr-dock` > `.hsr-console`) that serves as the command/chat input (since 2026-09-13 the busy state is a centered `#hsr-loading` popup outside `#app`, not a dock ticker — do not move it back); a room-objects panel; a Reliquary Imprints panel in Equipment; an auto-resolve toggle and identity-gated Wren/Doran signature buttons in Battle; a progression/Platinum/upgrades/stats panel and a run-report (conducts) panel in the Chronicle screen; and `identity` plumbed into the public view from `combat.rules`.

## Fix these — each one is confirmed reproducible

1. **Generic `inspect` action is broken in life-sim rooms.** Clicking the engine action-bar "Inspect" sends `{type:'inspect', actor}` with no target and the host answers `unknown room object: None`. The action bar in `actionBar()` / its `[data-engine-action]` handler in `bind()` must supply the parameters each action needs. `inspect`/`inspect_object`/`search_object`/`open_object` need `object_id`; `attack` and most maneuvers need `target`; `move_room` needs a destination. Add a lightweight target picker: when an action needs a target the client does not have, render a small chooser (room objects, exits, or visible opposition as appropriate) instead of firing a request that is guaranteed to fail. Do not guess a default silently.

2. **Free-text intents are rejected even when they match the advertised vocabulary.** `/api/session/vocabulary` advertises "look around", "show my equipment", "show room", "talk to <resident>", but submitting "look around" through the console returns `could not translate intent; use a supported combat, room, or dungeon action`. Reconcile `hollowstar/intent.py`'s `parse_intent` with the vocabulary the host publishes, in the `floor_one_life` / `dd_sandbox` scenarios specifically. Either the parser learns those phrases or the vocabulary stops advertising them — parser side is preferred. Add a test in `tests/` asserting every phrase the vocabulary endpoint publishes parses to a legal action.

3. **`.run-row` has no CSS.** On the Continue Game screen each saved run renders as run-id and "Saved run" jammed together with the Load button on its own line. Style `.run-row` as a proper row (flex, space-between, aligned button) in `web/styles.css`.

4. **Room description falls back to terrain.** In `room()` the chain `r.description || r.posture || r.terrain` prints the terrain ("floor") as the description when description and posture are null. Prefer the room's `atmosphere` or the latest narration, and drop the terrain fallback since terrain already has its own field in the facts grid.

5. **"Continue Game" always boots DESIGN.** The `continue` handler in `bind()` calls `boot('DESIGN')` regardless of the mode the saved run was created in, so resuming a Forge or Sandbox run boots the host into the wrong mode. Read the run's own mode (from `list_runs` / `inspect_run`) and boot to match before loading.

6. **Conversation modes are unverified.** Resident cards now render Ask / Lie / Threaten / Insult / Trade buttons that prime the console and submit through the `conversation` host command with `{npc, mode, text}`. This path was never exercised against a room with visible residents. Find or create a run whose room has `room.npcs` populated, click through every mode, and fix whatever the host rejects.

7. **Unverified panels.** These render only when the host supplies data, and no test run produced that data yet: the Imprints panel (`view.imprints` was `{}`), the room-objects panel (`view.room.objects` was `{}`), and the Wren/Doran signature buttons (`identity` only populates once combat starts). Drive a run into combat and into a room that has objects and imprints, confirm each panel renders correctly, and fix what breaks.

## Adaptability pass

Check every screen at 1920 wide, 1280, 768 (tablet) and 375 (mobile), and at a short landscape height (~600px):

- The `.hsr-dock` is `position: sticky; bottom: 0` and wraps both the engine action bar and the console. Confirm it never covers the last card on short viewports, that it stays reachable with the on-screen keyboard open on mobile, and that the action bar scrolls horizontally rather than wrapping into a tall stack.
- The console input must not be clipped at 375 wide; the Send button and the Cancel button (shown while a conversation mode is primed) must both stay tappable.
- The title screen is `position: fixed; inset: 0` — anything rendered after it in `#app` collapses to the top of the page. Any new persistent chrome must account for that, and must not appear on the title, transport, party-select or champion screens.
- Verify the three layout preferences in Options (Sanctum / Focus / Idle text-first), the text-size slider, reduced motion, and soft effects all still behave with the new panels.

## Rules

Keep changes minimal and surgical; do not refactor working screens. No new dependencies. No comments explaining what code does — only a short line where a non-obvious constraint needs recording. Report at the end: what you fixed, what you could not reproduce, and anything you deliberately left alone.
