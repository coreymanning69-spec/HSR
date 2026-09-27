---
id: DM054_0
title: "Mergeverse State Ledger"
type: reference
subtype: merge-state-ledger
load_priority: load-on-demand-for-merge-and-tr-beat-play
canon: M
verse: Mergeverse
timeline: M0+
arc: mergeverse
status: live-ledger-active
authority: authoritative-for-current-mergeverse-state-and-ruleset-delta
updated: 2026-09-06
volatility: volatile
arc_scope: mergeverse
derived_from: null
predecessor_file: N/A
successor_file: N/A
xref_concepts: [dm-state-1, four-ledger-split]
purpose: "Live state owner for the Mergeverse worldstate, M/TR position, approved ruleset delta, and post-portal Primeverse character state."
---

# DM054_0 — MERGEVERSE STATE LEDGER

## STATE BLOCK — dm-state-1

Machine-readable current state. Validate with `tools/state_blocks.py`.

**Live ledger, 2026-09-01.** Merge runs off-camera while the Girls are in the
Divineverse. Re-entry always reads current worldstate rather than replaying departure.

```yaml
{
  "schema_version": "dm-state-1",
  "ledger": "merge",
  "owner": "DM054_0",
  "updated": "2026-09-06",
  "load": {
    "class": "live",
    "surface": "any",
    "note": "instant-read Merge worldstate; load whole on any Merge or TR re-entry"
  },
  "scaffold": false,
  "content_gate": "approved 2026-09-01 ruleset delta",
  "arc": {
    "id": "mergeverse",
    "label": "Merge",
    "status": "active_offcamera",
    "seam": "M0",
    "seam_event": "Oak City entry / Halaster's portal",
    "pre_seam_owner": "DM056_0",
    "ontology_note": "the Divineverse holds the higher ontology; from M0 the Prime world runs as the Merge"
  },
  "ruleset_delta": {
    "tone": "Domestic divinity in a working modern megacity. Deposition, never extraction. Ordinary institutional life continues next to impossible acts.",
    "threat_model": "Nothing in the Merge threatens the Girls. Live pressure is witness economy and institutional consequence.",
    "tech_level": "Post-gate near-future: megacities, mechs, carrier helicopters, tablets, clean energy grids, working magic, and functioning shrines coexist.",
    "what_magic_costs": "For the Girls, nothing. For mortals it is belief-intent, scaled by conviction and bounded by an anchor.",
    "what_counts_as_a_win": "Infrastructure deposited; a place left measurably better; a person's framework surviving contact.",
    "what_stops_being_true": "The Tier system as a ceiling, containment as a viable strategy, and scarcity as a premise in districts Soliera has walked through."
  },
  "position": {
    "girls_present": false,
    "girls_located": "Divineverse — see DM038_L",
    "world_running": true,
    "reentry_rule": "fresh current-state read; never replay the departure snapshot"
  },
  "present": [],
  "open_gates": [
    {"id": "suzu_direct_introduction", "state": "unplayed", "note": "Suzu and the Girls have not met; café sketch hypothetical only"},
    {"id": "go_master_sequence_with_ember", "state": "framed_unstaged"},
    {"id": "regeneration_shelf_life", "state": "planted_unresolved"},
    {"id": "letha_veyren_separation_stress_test", "state": "in_progress"},
    {"id": "kusanagi_went_quiet", "state": "unexplained"},
    {"id": "undermountain_portal_level_collision", "state": "unresolved"},
    {"id": "yahweh_thread", "state": "open"},
    {"id": "remaining_t4s", "state": "open"},
    {"id": "t4_death_mechanics", "state": "open"}
  ],
  "character_states": {
    "scope": "Primeverse characters after divine intervention via portal; origin stays in DM056_0",
    "girls": "absent from Merge; current location is Divineverse",
    "suzu_hikari": "T4; active with Hakubai; HAS NOT MET THE GIRLS",
    "kiyuru": "active Japan hub; carries Kusanagi no Tsurugi and Yata no Kagami",
    "veyren": "T4; stayed behind from the Japan trip",
    "letha": "in Kiyuru's orbit for the trip; partnership with Veyren, not worship"
  },
  "regional_state": {
    "gate_plaza_oak_city_entry": "ALTERED — clean energy grid, cafe, inn, provisioner; jointly managed by Sanctum logistics and Company liaisons",
    "oak_city_slums": "ALTERED — diseases cured by passive transit; infrastructure repaired",
    "oak_city_badlands": "PACIFIED — M91-M125",
    "neon_city_border_wall": "DELETED — Sera removed the militarised wall",
    "gate_leviathan": "CLOSED — former SSS-class world-ending threat",
    "japan_hub": "CONTACTED; visit complete; world continuing",
    "executive_facilities": "ACTIVE OFF-CAMERA",
    "halasters_portal": "ACTIVE — Divineverse-to-Mergeverse link",
    "sanctum_logistics_network": "ACTIVE — Mergeverse-side operation"
  },
  "world_awareness": {
    "t4_community": "much now knows about the Girls; reactions remain character-specific",
    "public": "knows the transformed Oak City contact as the Oak City Experiment",
    "japan_specifically": "pre-existing category for divine visitation; spiritual response preceded institutional response"
  },
  "routing": {
    "chronology": {"M0-M90": "DM002_2", "M90-M183": "DM002_5", "handoff_anchor": "M90"},
    "cast": "DM004_3",
    "setting_and_locations": "DM032_0",
    "t4_system": ["DM022_0", "DM022_0a", "DM022_0b"],
    "suzu": "DM043_0",
    "pre_seam_domain": "DM056_0",
    "receipts": "DM035_0e",
    "staging_delta_format": "DM000_1"
  }
}
```

## Owner Boundary

M0 is the seam and ontological handoff: the Divineverse holds the higher ontology,
so the Prime world continues as the Merge. Everything before it is indexed by
`DM056_0`. This file owns M-beats and TR-beats from M0 forward and the current state
of Primeverse characters after the portal.

Merge is a genre switch, not a sub-arc. `ruleset_delta` is the field that carries
that. The six fields were approved by Corey on 2026-09-01; Merge play is routable.

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM054_0 -->
