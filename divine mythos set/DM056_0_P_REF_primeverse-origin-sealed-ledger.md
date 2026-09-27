---
id: DM056_0
title: "Primeverse Origin Closed-at-M0 Ledger"
type: reference
subtype: primeverse-origin-closed-at-m0-index
load_priority: load-cold-only-during-an-explicit-primeverse-pass
canon: P
verse: Primeverse
timeline: P0 — Pre-Merge (Before M0)
arc: primeverse-foundation
status: closed-at-seam-active-recap
authority: authoritative-for-primeverse-final-state-recap-and-retroactive-lane
updated: 2026-09-19
volatility: slow
arc_scope: primeverse-foundation
derived_from: null
predecessor_file: N/A
successor_file: N/A
xref_concepts: [dm-state-1, four-ledger-split, prime-retroactive-lane]
purpose: "Primeverse final-state recap closed forward of M0, with an author-gated retroactive pre-M0 lane."
---

# DM056_0 — PRIMEVERSE ORIGIN CLOSED-AT-M0 LEDGER

## STATE BLOCK — dm-state-1

Machine-readable current state. Validate with `tools/state_blocks.py`.

**Closed at M0, 2026-09-01.** The state is indexed and recap-ready; forward
authoring is closed while a gated retroactive pre-M0 lane remains available.

```yaml
{
  "schema_version": "dm-state-1",
  "ledger": "prime",
  "owner": "DM056_0",
  "updated": "2026-09-19",
  "load": {
    "class": "on-demand",
    "surface": "any",
    "note": "recap-and-retroactive owner; closed forward of M0"
  },
  "scaffold": false,
  "content_gate": "closed forward of M0; retroactive authoring under an explicit Corey gate",
  "sealed": false,
  "seal": {
    "boundary": "closed forward of M0",
    "declared_by": "Corey 2026-09-01",
    "excludes": "Oak City entry / Halaster's portal threshold — that is DM054_0",
    "write_rule": "retroactive pre-M0 authoring is permitted only under an explicit Corey gate"
  },
  "boundary": {
    "closed_forward_of": "M0",
    "retroactive_lane": {
      "state": "open",
      "scope": "pre-M0 early-timeline work: P0-P3 prose compilation, DIVIDE institutional history, Cradle-era expansion",
      "write_rule": "authoring permitted under an explicit Corey gate; nothing lands unprompted"
    }
  },
  "arc": {
    "id": "primeverse-foundation",
    "label": "Primeverse",
    "status": "closed_at_seam",
    "seam": "M0",
    "seam_event": "Oak City entry / Halaster's portal",
    "successor_owner": "DM054_0",
    "ontology_note": "the Divineverse holds the higher ontology; at M0 the Prime world does not end, it continues as the Merge"
  },
  "edge": {
    "beat": "P4",
    "lane_file": "DM033_2",
    "lane_section": "V — Veris arc close",
    "lane_state": "closed",
    "last_played_beat": "P4",
    "authored_ahead": false,
    "note": "Goodnight across the hall; the arc pauses there. Final Prime beat by the M0 boundary."
  },
  "position": {
    "site": "outpost_seven",
    "situation": "night; Soliera Prime and Veris in rooms across the hall, both asleep",
    "region": "the_field_zone"
  },
  "present": ["soliera_prime", "arden", "veris", "evan", "cassian", "veyren", "varn", "gold"],
  "provenance": [
    {"owner": "DM033_1", "scope": "Prime foundation timeline and origin"},
    {"owner": "DM033_2", "scope": "Veris arc close and P4 goodnight"},
    {"owner": "DM033_3", "scope": "Prime power and institutional context"},
    {"owner": "DM033_4", "scope": "Prime docket and retroactive coverage"},
    {"owner": "DM014_1", "scope": "Prime focused state and profiles"},
    {"owner": "DM014_2", "scope": "Pre-gate Earth, Gate emergence, the Great War, Brazil Gate, chupacabra confirmation, Company/Church institutionalization"},
    {"owner": "DM022_0", "scope": "Prime T4 and matrix context"}
  ],
  "coverage": {
    "status": "indexed",
    "existing_owners": ["DM033_1", "DM033_2", "DM033_3", "DM033_4", "DM014_1", "DM014_2", "DM022_0"],
    "note": "indexes and dates landed Prime owners; does not duplicate their prose"
  },
  "open_gates": [
    {"id": "veris_soliera_continuation", "state": "unplayed"},
    {"id": "p_beat_prose_compilation", "state": "landed", "note": "pre-gate origin, Great War, Brazil Gate, chupacabra composed into DM014_2 2026-09-19; receipt in DM035_0e"},
    {"id": "divide_institutional_history", "state": "retroactive_lane", "note": "explicit Corey gate required"},
    {"id": "prime_meets_divine_soliera", "state": "has_not_happened"}
  ],
  "routing": {
    "foundation_and_docket": ["DM033_1", "DM033_2", "DM033_3", "DM033_4"],
    "focused_state_and_profiles": ["DM014_1", "DM014_2", "DM014_3"],
    "t4_and_matrix": ["DM022_0", "DM022_0a", "DM022_0b"],
    "successor_domain": "DM054_0",
    "receipts": "DM035_0e",
    "staging_delta_format": "DM000_1"
  }
}
```

## Owner Boundary

This ledger owns the Primeverse final-state recap through the M0 seam. The Primeverse
world does not end at M0; because the Divineverse holds the higher ontology, the Prime
world continues as the Merge under `DM054_0`. Forward work is closed here. The
retroactive pre-M0 lane remains open only under an explicit Corey gate and indexes
`DM033_1/2/3/4`, `DM014_1`, and `DM022_0` rather than duplicating them.

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM056_0 -->
