# Story Foundations — How the Pieces Fit

Engine save data lives under `.local/reliquary_progress/`. None of it is corpus canon.

| System | Files | What to do with it |
|---|---|---|
| Story flags + event bus | `hollowstar/story_state.py` | Call `emit("event", {...})` whenever something story-relevant happens. Register consequences with `@on("event")`. Host: `story_emit`, `story_flag`, `story_state`. |
| Run-end pipeline | `hollowstar/run_end.py` | One call per run: settles Platinum, feeds the Star, emits `run_ended`. Client calls `run_end` automatically when a run's status leaves `active`. |
| Save migrations | `hollowstar/save_migrations.py` | When a save format changes, bump the version and register `@migration(kind, old_version)`. Newer-than-build saves are refused. |
| Star memory | `hollowstar/star_memory.py` | Awareness tiers, vessels, seen cutscenes, last victor. Debug ops via `star_debug`. |
| Codex | `story_state.discover(kind, id, title)` | Kinds: floor, monster, resident, item, lore, location. Screen: Memory Archive → Codex. |
| Cutscenes | `web/cutscene-player.js`, `web/cutscenes.js` | Layers take `asset: 'id'`; shots take `audio: {music, ambience, sfx, stinger}`. |
| Dialogue | `web/dialogue-runner.js`, `web/dialogues.js` | Nodes with `if`/`else`, `choices`, `set` flags, `emit` events. `voice_gate: true` or `'[COREY]'` = unwritten slot, shown as a marked placeholder. |
| Audio | `web/audio-system.js`, `web/assets/audio-manifest.json` | Add `id -> {src, category, volume, loop}`. Unlisted ids are skipped silently. Volume per category in Options. |
| Art | `web/asset-registry.js`, `web/assets/manifest.json` | Add `id -> {src, w, h}`. Cutscene ids in use: `cs.bg.void`, `cs.bg.palace`, `cs.hollow-star`, `cs.reliquary`, `cs.well`, `cs.cocoon`, `sprite.vessel.{cloak,body,head,core}`, `sprite.star-mirror.{…}`. |
| Interface text | `web/strings.js` | `t('key', {vars})`. Missing keys show the key itself. |
| Settings | Options → Story, audio and accessibility | Text speed, skip seen cutscenes, floor cards, colour-blind patterns, volumes. |
| Debug | Simulation → Cheats → Story debug | Awareness, reveal Star, forget/replay cutscenes, run dialogues, set flags, audio/art manifest status. |
| Transitions | `web/transitions.js` | `titleCard(eyebrow, title)` for floors/chapters, `storyToast(text)` for unlocks. |

## Notes: minimal versions, extend later

- **Codex auto-fills floors only.** Monsters, residents and items appear once the engine emits `discover` for them (e.g. from combat or conversation). The hook exists; nothing calls it yet.
- **Audio and art manifests are empty.** Sound ids already referenced: `music.hollow-star-theme`, `sfx.star-ignite`, `amb.palace-silence`.
- **Only interface text for the new screens uses `strings.js`.** Older screens still have inline text, so move them over as they get touched.
- **Dialogue is client-side.** Flags it sets are saved through `story_flag`. It isn't triggered from NPCs in play yet; it's reachable from the Memory Archive and Cheats.
- **Not verified live** (the engine can't boot in the cloud copy): the `run_end` call at a real run's end, the Meta Shop unlock toast, the floor-1 title card in a real run.
- `web/assets/art-manifest.json` is the existing *provenance* record for generated art. The new `manifest.json` is the *id lookup*. Keep both.

## Round 2 additions

- **Cocoon:** 30 rounds (`dungeon.json: cocoon_rounds`). The Tarrasque rises for `tarrasque_rise_rounds` (5), during which it takes no turns or legendary actions, then launches `tarrasque_launch_delay` (2) rounds later and attacks everything alive, rivals included. If rivals are still alive when it dies, `tarrasque_loot = "rivals"`. When the party is the last one standing after the cocoon opens, `star_reveal` is set. `run_end` then flags `star_revealed` (awareness 4), emits `star_revealed`, and the client plays "I Won Again".
- **Champion Ladder:** `hollowstar/unlock_ladder.py`, with data in `hollowstar/content/story/unlock_ladder.json`. **Story Mode (FORGE) only.** Simulation and rehearsal keep full sheets. Level = 1 + XP/2, and XP = rooms cleared, credited at run end. Picks come every 5 levels, plus a bonus every 25. Level 100 unlocks everything. Wren's slots open by level (1 slot level per 11 levels). Locked actions are refused by `tactical.apply`. Screen: Story Mode → Champion Ladder. Debug: Cheats → set level 1/25/50/100.
- **Codex:** the client now records every creature/resident it sees in opposition (`codex_discover`).
- **NPC dialogue:** talking to a resident plays `DIALOGUES['npc:<name-slug>']` first when one exists (example in `web/dialogues.js`).

### Not built yet (basic stand-ins noted)
- **Mirror fight vs. the Star.** The reveal plays and `last_victor` is saved, but no combat spawns the Star. It needs a post-reveal encounter that builds an opponent from `last_victor`. Blocked on deciding its stat source: a snapshot of the winning sheet, or the corrupted version.
- **Rival AI doesn't fight back against the Tarrasque.** Rivals share a side with it, so they keep targeting the party. A three-way faction needs `same_side` to understand a "feral" side.
- **Ladder ordering and min levels are a first pass.** `[COREY]` should retune them in the JSON.
- The design corpus (DM046_0) still says twenty rounds. It is read-only here, so update the master copy if 30 is final.
