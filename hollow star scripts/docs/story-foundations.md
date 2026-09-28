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
