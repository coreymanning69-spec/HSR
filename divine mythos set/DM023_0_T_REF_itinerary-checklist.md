---
id: DM023_0
title: "Sera's Itinerary - Checklist and Tracking File"
type: reference
subtype: itinerary-status-and-tr-beat-routing
load_priority: must-load-before-all-travel-arc-files
canon: T
verse: Divineverse
timeline: T516+
beat_range: T516+
arc: seras-itinerary-travel-arc
era:
  - post-avernus
  - post-barovia
  - global-tour
  - tr-beats
status: hard-canon
authority: authoritative-for-itinerary-status-checklist-reader-requirement-and-tr-beat-routing
updated: 2026-09-07
volatility: slow
arc_scope: seras-itinerary-travel-arc
derived_from: null
predecessor_file: DM019_3
successor_file: DM025_0

scope:
  covers:
    - per-location tour status (visited / first visit / pending / extraplanar)
    - TR-beat routing across DM025_0 / DM026_0 / future TR files
    - Reading Gag protocol (Sera carries dossier, cannot read it; designated Readers required)
    - reputation tier lookup handoff to the DM024 atlas files
  use_case: load before any TR-beat file to confirm location status, reader presence, and routing stack
  not_for: live active-session continuation, per-location atlas content, or full file-index/tag ownership

xref_concepts:
  - travel-arc-initialization
  - itinerary-dossier-as-in-world-meta-text
  - tr-beats-numbering-scheme
  - social-friction-over-combat
  - witness-economy
  - reputation-tiers
  - reading-gag
  - inverse-cosmic-horror
  - normalcy-as-comedy
  - no-victory-laps
  - mercy-as-infrastructure
  - mortal-recalibration
  - let-ember-cook

canon_flags:
  - "#RULE-HARD-CANON-SPELLING"
  - "#RULE-SOLIERA-SILENCE-UNLESS-DM"
  - "#RULE-SERA-JOY-FIRST"
  - "#RULE-DEASHI-NONVERBAL-ALWAYS"


purpose: >
  Itinerary status board and travel-routing checkpoint for the global tour.
  This file tracks which itinerary stops are complete, which remain pending,
  which designated Reader is required for dossier readout, and where each
  optional destination routes. Load before any TR-beat file or
  itinerary atlas read.

ai_directives:
  - The itinerary is an in-world dossier prepared by Velin and Niv.
  - Sera cannot read; a designated Reader must vocalize the dossier at each new stop.
  - Check this file before writing any first-visit reaction or routing a new TR-beat.
  - Do not auto-resolve location encounters; TR beats default to social friction over combat.
  - Use DM024_1 through DM024_4 for local fame versions, texture, and region detail; DM000_4 owns the fame constant.
  - Use DM000_2 for live current continuation state; do not treat this file as the active-state dashboard.

---

# DM023_0 - Sera's Itinerary Checklist

## Use Standard

Load this file before any TR-beat or itinerary-atlas work to answer four questions:

1. Has this location already been visited?
2. Is this stop part of the Faerun checklist, the extraplanar branch, or a parallel regional cluster?
3. Who is the designated Reader for the dossier at this stop?
4. Which unresolved travel hooks still need to remain open?

This file does not replace `DM034_1` for file routing, `DM034_2` for rule ownership,
or `DM000_2` for live active-state continuation.

## Support Stack

- `DM034_1` owns the file index and retrieval rules.
- `DM024_1` through `DM024_4` own region detail, local fame versions, and hook texture; `DM000_4` owns baseline recognition.
- `DM025_0` and `DM026_0` own the canonical record for completed TR1 / TR2 travel beats.
- `DM030_1` and `DM030_2` remain the Sera owner files.
- `DM031_0` and `DM032_0` own setting-change implications when a stop touches those domains.

## Reader Requirement

The dossier is an in-world object. Sera carries it but cannot read it.
At each new stop, one designated Reader must vocalize the itinerary material.

Current sanctioned Readers for this travel scaffold:

- Letha for the Divineverse travel arc
- Velin for embassy / logistics-heavy routing
- Ember on an ad hoc basis when the beat intentionally uses her voice

For `TR3-SKT`, Bryn Shander is a return stop, not a first-contact stop. Velin
handles the short route / crisis brief; do not stage a first-visit dossier read.

## Location Checklist and TR Routing

- `[ ]` **not reached**: no visit is recorded.
- `[X]` **completed itinerary stop**: the itinerary stop itself is complete.
- `[~]` **partial visit**: visited, but the itinerary stop is not complete.
- `[V]` **visited outside itinerary**: visited by another route; it remains uncompleted as an itinerary stop.
- Luskan is a completed itinerary stop through `TR1-01` to `TR1-13` in `DM025_0`.
- The Sanctum, Bryn Shander, and Waterdeep are outside-itinerary visits. Bryn Shander was the `TR3-SKT` play entry: an established-allies return preserved in played narrative and the hashed Chapters 1–9 archive. Current continuation never restarts there.
- Port Llast remains the next ordinary southbound checklist stop after the SKT route unless Corey routes elsewhere.
- TR-JP is a parallel regional cluster, not one of the 17 Faerun checklist stops.

[V] LOCATION 01: THE SANCTUM (VISITED OUTSIDE ITINERARY)
[V] LOCATION 02: TEN-TOWNS / BRYN SHANDER (VISITED OUTSIDE ITINERARY; RETURN STOP; TR3-SKT OPENS HERE)
[ ] LOCATION 03: MIRABAR
[X] LOCATION 04: LUSKAN (TR1-01 through TR1-13)
[ ] LOCATION 05: PORT LLAST
[ ] LOCATION 06: NEVERWINTER
[ ] LOCATION 07: NEVERWINTER WOOD / MOUNT HOTENOW
[ ] LOCATION 08: SILVERYMOON
[V] LOCATION 09: WATERDEEP (VISITED OUTSIDE ITINERARY)
[ ] LOCATION 10: BALDUR'S GATE
[ ] LOCATION 11: CANDLEKEEP
[~] LOCATION 12: UNDERMOUNTAIN (PARTIAL VISIT)
[ ] LOCATION 13: EVERMEET
[ ] LOCATION 14: CHULT / PORT NYANZARU
[ ] LOCATION 15: THE ASTRAL SEA
[ ] LOCATION 16: HALRUAA
[ ] LOCATION 17: LANTAN

### THREAD 1: Sera's Itinerary (TR-beats, T516+ / post-Strahd)
- 17-location tour of the Sword Coast and beyond
- Begins after T515: Barovia handoff is complete (Sanctum protectorate, portal installed); TR records start at T516.
- Framed as Velin and Niv presenting the girls with a comprehensive overview of their sphere of influence
- Low-stakes, high-texture domestic energy
- Prior travel companion through TR-JP: Letha (now also carrying Vesper). She does not deploy for TR3-SKT.
- Completed: Luskan (TR1, DM025_0), Against the Giants G1/G2/G3 (TR2, DM026_0)
- Post-TR2 background: Eclavdra completed an observation cycle and withdrew toward the Underdark. A later return is possible, but no active continuation is owed.
- Background post-TR2 worldstate: the claimed Steading continues without Sanctum mediation under Sera's absolute no-attacks-on-humans term; Yrsa returned to her clan home; giant political fallout continues; the Hall of the Fire Giant King remains claimed-but-unoccupied; giant alliance intelligence is filed with Letha.
- Standing itinerary hooks: TR-01 through TR-50 remain valid atlas anchors, but TR-01/TR-02/TR-03 are not the current priority unless Corey chooses to route back to Ten-Towns.
- Legacy TR-number anchors remain in DM024_1/2/3/4 for optional destinations; removed hooks are not renumbered or revived.
- Next Faerun itinerary location: Port Llast (Location 05) remains checklist-next after Luskan/TR2, unless Corey selects another Faerun TR stop.
- TR-JP arc is CLOSED (2026-06-20). Exit beat: Ember wanted home → Soliera teleported the party. Casual goodbye to Kiyuru.
- TR-JP-01 through TR-JP-05 + Hisako parallel POV, all compiled as authorized reconstruction prose in DM039_0 (2026-06-20).
- Current continuation point: **route through DM034_0 CURRENT ARC**, then read
  the sole Divine edge owner `DM038_L dm-state-1.edge`
  (`#RULE-ONE-EDGE-OWNER`); no edge value is restated here. Goldenfields
  is closed and the Stewards are restored; no arrival scene or next route is
  pre-authored. Continue via DM038_L and fresh-read its Mechanics Snapshot. Closed
  played prose is the DM038_N2/N4/N5/N6 chain; the open lane is derived from the
  `_N#` family rule in DM034_0, not stated here.
- TR3-SKT rolling party: Doran and Wren. Doran is Korin's impressive,
  dagger-forward chosen recruit: a proud solo clearer whose excessive formality
  manages desire and must soften into real pair-presence. He is locked as a pure
  Battle Master Fighter 20 by the T537.0 divine uplift (source mechanics in
  DM041_A; encounter runtime DM044_0); no rebuild
  is pending.
  Wren is a proven Sanctum population leader who remained an Abjuration Wizard
  through T531, reached Cleric 13 / Sorcerer 15 at T535, and is now a Cleric 20 /
  Sorcerer 20 stacked chassis by the T537.0 divine uplift; source mechanics are
  in DM041_B and encounter runtime is DM044_1. Soliera, Sera, and Ember
  accompanied through Nightstone, the cave rescue, the T522 morning gifts, the
  Waterdeep arrival, and the Blackstaff debrief/rest. They stayed behind for
  the no-net Bryn Shander leg, then agreed to come behind the recruits for the
  frost-giant movement and completed the Svardborg treaty. Velin may travel
  whenever she wants; no structural ban applies, and she is not an automatic
  rolling character. On-demand compact characterization: DM040_0. Shared framework: DM041_0. Full depth profiles: DM041_C.
- Deashi does not deploy for TR3-SKT; he remains a non-deployed divine reference.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM023_0 -->
