---
id: DM008_1
title: "Convoy Ambush to Skyreach Castle (T141-T160)"
type: beat
subtype: story-log
load_priority: load-after-DM007_2-before-DM008_2
canon: T
verse: Divineverse
timeline: T141–T160
beat_range: T141–T160
arc: hoard-of-the-dragon-queen-part-one
era:
  - hotdq-opening
  - greenest-restoration
  - waterdeep-underdeal
  - hunting-lodge
  - skyreach-approach
  - pre-ember
status: hard-canon
authority: authoritative-for-hotdq-inversion-and-skyreach-approach
updated: 2026-09-23
volatility: invariant
arc_scope: hoard-of-the-dragon-queen-part-one
derived_from: null
predecessor_file: DM007_2
successor_file: DM008_2

xref_concepts:
  - hotdq-inversion
  - clap-and-drop-origin
  - party-split-T148
  - module-inversion
  - greenest-restoration
  - ember-does-not-exist-yet
  - velvet-spiral

canon_flags:
  - "#RULE-NO-ANTI-FEATS"
  - "#RULE-SOLIERA-SILENCE-UNLESS-DM"
  - "#RULE-DEASHI-NONVERBAL-ALWAYS"
  - "#RULE-MODULE-SCAFFOLDING-DIVINE-OVERWRITE"
  - "#RULE-NPCS-ARE-PEOPLE-NOT-QUEST-OBJECTS"


purpose: >
  Owns the HotDQ inversion methodology and the canonical Sera origin beat
  (clap-and-drop descent at T141). Authoritative for the party split at
  T148 and for the Talis-vs-Taliandra naming distinction. AI must not
  apply Ember pillars to this file — she does not exist yet at T141-T160.

module_source: Tyranny of Dragons / Hoard of the Dragon Queen (PDF)  # optional beat-file field

module_treatment: MODULE-INVERSION   # optional beat-file field; run as administration, not desperate battle

arc_summary: >
  HotDQ opening, run inverted. Convoy ambush near Greenfields Road answered
  with surgical Velvet Spiral deployment. Greenest is restored, not defended.
  Letha, Korin, and Pell stay behind at T148 to oversee restoration. Sera,
  Soliera, and Drizzt continue north pursuing the cult. Waterdeep sewers /
  Underdeal contact at T151-T153. Hunting Lodge encounter (Talis — NOT
  Taliandra) at T154-T155. Approach to Skyreach Castle T156-T160.
  Maccath's later entry belongs to the DM008_2 continuation, not this range.
  Ember does NOT exist yet in this file — Soliera/Deashi
  pillars apply, Ember pillars do not.

key_beats:
  - T141  Convoy ambush; Sera discovers clap-and-drop descent (origin beat)
  - T144  Greenest reached
  - T148  Party split — Letha/Korin/Pell remain in Greenest
  - T151-T153  Waterdeep sewers / Underdeal; Xanathar co-opted
  - T154-T155  Hunting Lodge; Talis encountered
  - T156-T160  Skyreach Castle approach

party_primary:
  - Soliera
  - Sera
  - Drizzt

party_secondary:
  - Letha       # departs at T148, stays in Greenest
  - Korin       # departs at T148, stays in Greenest
  - Pell        # departs at T148, stays in Greenest
  - Niv-Saiffar # off-screen logistics; no arrival asserted in this range

party_split_at: T148

party_split_note: >
  Letha, Korin, and Pell remain in Greenest to oversee restoration.
  Sera, Soliera, and Drizzt continue north pursuing the cult.

ember_status: DOES NOT EXIST YET   # optional beat-file field; canon: Ember is born at T299 (DM010_2)

characters:
  divine_present: [Soliera, Sera]
  party_primary: [Drizzt]
  party_secondary: [Letha, Korin, Pell, Niv-Saiffar]
  module_npcs: [Talis, Xanathar]   # Talis is NOT Taliandra — distinct character

locations:
  greenfields: [Greenfields-Road]
  greenest_arc: [Greenest]
  road_north: [Sword-Coast-Road-North]
  waterdeep: [Waterdeep-Sewers, Underdeal]
  hunting_lodge: [Hunting-Lodge]
  skyreach: [Skyreach-Castle-approach]

ai_directives:
  - Ember does NOT exist in this file — apply Soliera/Deashi pillars only
  - Talis at the Hunting Lodge is a separate character from Taliandra (DM006_0)
  - module is run inverted — never write desperate-battle framing
  - Greenest is restoration, not defense — civilians are observers, not victims
  - clap-and-drop descent is canon Sera technique from T141 forward
  - Letha/Korin/Pell stay in Greenest from T148 — do not include in later beats this file

open_threads_forward:
  - Skyreach Castle interior → DM008_2 — CLOSED HANDOFF
  - Maccath's later introduction → DM008_2 — retrieve the owning continuation
  - Greenest as Sanctum-protected node — SETTLED WORLDSTATE; future contact optional
---

## SEGMENT MAP

Load only the smallest segment whose coverage matches the question. Each sibling repeats its own scope and authority context.

| ID | Covered section |
|---|---|
| DM008_1 | PARTY STATE |
| DM008_1a | Convoy Ambush to Skyreach Castle — Notes |
| DM008_1b | Convoy Ambush to Skyreach Castle — Notes, Part 2 |


### PARTY STATE
party_primary:
  - Soliera
  - Sera
  - Drizzt

party_secondary:
  - Letha       # departs at T148, stays in Greenest
  - Korin       # departs at T148, stays in Greenest
  - Pell        # departs at T148, stays in Greenest
  - Niv-Saiffar # off-screen logistics; no arrival asserted in this range

party_split_at: T148
party_split_note: >
  Letha, Korin, and Pell remain in Greenest to oversee restoration.
  Sera, Soliera, and Drizzt continue north pursuing the cult.

ember_status: DOES NOT EXIST YET

### LOCATIONS
locations:
  - Greenfields Road          # T141-T143
  - Greenest                  # T144-T148
  - Sword Coast Road North    # T149-T153
  - Waterdeep (Sewers/Underdeal) # T151-T153
  - Hunting Lodge             # T154-T155
  - Skyreach Castle (approach) # T156-T160

### CHARACTERS PRESENT OR REFERENCED
characters:
  - #CHAR-SOLIERA
  - #CHAR-SERA
  - #CHAR-DRIZZT
  - #CHAR-LETHA
  - #CHAR-PELL
  - #CHAR-KORIN
  - #CHAR-NIV-SAIFFAR
  - #CHAR-TALIS         # T154-T155 — NOT Taliandra, separate character
  - #CHAR-XANATHAR      # T152, co-opted

### ORIGIN BEATS (FIRSTS)
origin_beats:
  - id: ORIGIN-CRATER-STRIKE
    beat: T141
    note: >
      Sera discovers the clap-and-drop descent technique mid-combat.
      Not planned — adaptive. Becomes her standard AOE opener.
  - id: ORIGIN-FOOT-SKULL
    beat: T141
    note: >
      First use of boot-stomp as post-combat execution method.
      Barefoot. Methodical. Walks the crater perimeter.
  - id: ORIGIN-PARTY-DOG
    beat: T143
    note: >
      Starving dog found in supply cage. Bonds with Sera and Pell.
      Calm in the hush — animals read Velvet Spiral as correct order.

### ABILITY NOTES
ability_notes:
  - ability: Knife-Thought Edge
    active_since: T114
    first_combat_application: T145
    note: >
      Intent-sensing fully operational by T141. Hiding cult affiliation
      from Sera in a crowd is structurally impossible.

### BEAT CORRECTIONS
beat_corrections:
  - beat: T145
    original_tags:
      - EXECUTION-SILENT
      - NO-SPECTACLE
    corrected_tags:
      - KNIFE-THOUGHT-EDGE-USE
      - CROWD-JUSTICE
      - PUBLIC-CONFRONTATION
      - VELVET-SPIRAL-CONFESSION
      - MODULE-GATE-BETRAYERS
    correction_note: >
      Original compression was wrong. Sera identified betrayers publicly
      in the town square, they confessed under aura, and the MOB executed
      them — not Sera. The "quiet/surgical" label belongs to a secondary
      cleanup phase (T145.5, now added separately).

### DEPENDENCIES
load_before:
  - DM000_1
  - DM004_1
  - DM007_2   # party state entering this file
  - DM027_0   # combat mechanics reference
  - DM030_1                                # Sera internal logic / combat behavior
  - DM030_2                                # Sera social aura / relationships

load_after_if_needed:
  - DM008_2                                # continuation (T161-T190)
  - DM031_0  # Greenest / Skyreach world state

<!-- CORPUS REVISION: 9.25 -->
<!-- END DM008_1 -->
