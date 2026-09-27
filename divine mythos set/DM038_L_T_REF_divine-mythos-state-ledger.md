---
id: DM038_L
title: "Divine Mythos State Ledger"
type: reference
subtype: divine-mythos-state-ledger
load_priority: load-every-current-Divineverse-story-session; section-retrieve-readiness-at-initiative
canon: T
verse: Divineverse
timeline: T-SKT
beat_range: T550.1-T550.3-closed; T550.4-open
arc: divine-mythos
era: current-domain-state
status: live-ledger-active
authority: authoritative-for-current-Divineverse-domain-edge-route-readiness-regional-state-and-open-fronts
updated: 2026-09-06
volatility: volatile
arc_scope: divine-mythos
derived_from: null
predecessor_file: N/A
successor_file: N/A
purpose: "Sole current Divine Mythos domain ledger: the active arc is a keyed state field, so arc handoffs update this ledger instead of spawning successor ledgers."
---

# DM038_L — DIVINE MYTHOS STATE LEDGER

## STATE BLOCK — dm-state-1

Authoritative machine-readable current state. `tools/state_blocks.py` is a hard verification stage.

**Hard swap, 2026-08-31.** This block owns every field it defines. Prose may
explain a silence or a play boundary, but it must not restate current state.
A disagreement with another current-state surface is a build defect.

```yaml
{
  "schema_version": "dm-state-1",
  "ledger": "divine",
  "owner": "DM038_L",
  "updated": "2026-09-06",
  "load": {
    "class": "live",
    "surface": "any",
    "note": "authoritative current state; prose below carries only non-structured play doctrine"
  },
  "arc": {
    "id": "storm-kings-thunder",
    "label": "TR3-SKT",
    "status": "active"
  },
  "edge": {
    "beat": "T550.4",
    "lane_file": "DM038_N9",
    "lane_state": "open_empty",
    "last_played_beat": "T550.3",
    "last_played_file": "DM038_N8",
    "authored_ahead": false,
    "note": "opened empty 2026-08-26 so Wren's turn has a home; no prose, no site detail, no result"
  },
  "position": {
    "site": "sanctum_grass_courtyard",
    "situation": "party broken to change clothes before glacier departure",
    "departed": false
  },
  "present": [
    "doran",
    "wren",
    "letha",
    "sera",
    "ember",
    "soliera"
  ],
  "turn": {
    "complete": [
      "doran"
    ],
    "next": "wren",
    "declared_intent": "capstone_four_to_one",
    "resolved": false
  },
  "open_gates": [
    {
      "id": "glacier_demonstration",
      "records_to": "DM038_N9",
      "state": "planned_unplayed"
    },
    {
      "id": "sera_races_the_cut",
      "state": "agreed_no_result",
      "agreed_by": "letha"
    },
    {
      "id": "cut_has_far_end",
      "state": "untested"
    },
    {
      "id": "eraser_pointed_inside_sanctum",
      "state": "unruled_resolved_sideways"
    }
  ],
  "route": {
    "interposed": {
      "id": "glacier_demonstration",
      "beat": "T550.4",
      "reached_by": "teleport",
      "displaces_route": false
    },
    "steps": [
      "sansuri_conch_to_maelstrom",
      "expose_iymrith_at_court",
      "chapter_12_iymrith_lair_finale",
      "grand_dame_morkoth_hekaton_rescue",
      "slarkrethel_belthyn_operation",
      "ithreva_ordinant_and_eclavdra_converge"
    ],
    "route_notes": {
      "iymrith_location": "ROUTED 2026-09-06 — Iymrith is exposed and may be confronted at the Court after the Sansuri conch route; the final major fights are intended for Chapter 12 at her desert lair. Her death is likely but remains a played outcome, not a pre-authored result. Maelstrom is the route into the Court, not the sole location of the Iymrith finale.",
      "finale_shape": "multi-front engagement: champions and dragons together, sized to challenge even Doran and Wren",
      "convergence": "slarkrethel_belthyn_operation and ithreva_ordinant_and_eclavdra_converge are NO LONGER causally independent — see thayan_linkage below. Convergence is confirmed by play, never inferred from a routing file.",
      "preserved": "the Court is restored THROUGH Serissa and Hekaton's legitimate authority, not replaced by divine fiat"
    },
    "thayan_linkage": {
      "canon": "the Thayan remnant that approached Sansuri is in league with the Drow and the Kraken Society",
      "recorded": "2026-09-05",
      "propagates_to": ["DM038_6b", "DM050_0"],
      "left_for_play": "closed 2026-09-06 — Sansuri knows only that the Thayan remnant approached her; she does not know it is loosely allied with the Drow and Kraken Society. She is allied with the Sanctum through a transactional bargain: the Sanctum offers the highest available knowledge, wealth, and status, and she gives Niv the Conch. She remains a possible route to influence over the wider Giants. Wren and Doran have not yet seen Hekaton. The Thayan, Drow, and Kraken fronts operate mostly concurrently and converge toward the planned multi-front boss/wave fight."
    }
  },
  "regional_state": {
    "goldenfields": "closed",
    "hill": "closed_no_reply_owed",
    "frost_svardborg": "closed",
    "fire_ironslag": "closed"
  },
  "readiness": {
    "snapshot_beat": "T550.1",
    "stands_verbatim_at": "T550.3",
    "all_finite_pools_at_max": true,
    "dice_rolled_since_snapshot": false,
    "accepted_as_stewards": "T537.0",
    "doran": {
      "class": "battle_master_fighter_20",
      "xp": 165000,
      "xp_frozen": true,
      "hp": [
        370,
        370
      ],
      "ac": 25,
      "superiority": {
        "dice": [
          16,
          16
        ],
        "die": "d12",
        "dc": 22
      },
      "action_surge": [
        2,
        2
      ],
      "second_wind": [
        1,
        1
      ],
      "indomitable": [
        3,
        3
      ],
      "reaction_ready": true,
      "conditions": [],
      "kit": "full_white_plate_as_of_T550.3; helm carried not worn"
    },
    "wren": {
      "class": "cleric_20_sorcerer_20",
      "xp": 165000,
      "xp_frozen": true,
      "hp": [
        220,
        220
      ],
      "ward": [
        75,
        75
      ],
      "sorcery_points": [
        50,
        50
      ],
      "slots_total": [
        150,
        150
      ],
      "slots_general": 132,
      "slots_domain": 18,
      "slots_general_by_tier": {
        "1": 20,
        "2": 16,
        "3": 16,
        "4": 16,
        "5": 20,
        "6": 12,
        "7": 10,
        "8": 14,
        "9": 8
      },
      "slots_domain_by_tier": 2,
      "channel_divinity": [
        3,
        3
      ],
      "favored_by_the_gods": [
        1,
        1
      ],
      "crown": [
        7,
        7
      ],
      "robe_stars": [
        6,
        6
      ],
      "staff_charges": 50,
      "portal_shear": "restored_unspent",
      "simulacra_active": 0,
      "concentration_free": true,
      "ring_holds": "haste_on_doran",
      "reaction_ready": true,
      "conditions": []
    },
    "seed_gate": {
      "state": "satisfied",
      "doran": "complete",
      "wren": "complete",
      "open": "none; Wren knows every normal published Cleric and Sorcerer/Divine Soul spell except Wish, Karsus-origin magic, and individually NPC-exclusive spells"
    },
    "capstone": {
      "state": "declared_intent_only",
      "beat": "T550.3",
      "ever_cast": false
    },
    "eraser_capstone_l10": {
      "specified": true,
      "acquired": false,
      "is_runtime_option": false
    },
    "portal_slash": {
      "specified": true,
      "acquired": false,
      "is_runtime_option": false,
      "note": "renamed from portal_shear_nanowire_whip 2026-09-05 and promoted to its own top-level lane in DM041_B; unlock is narrative"
    },
    "confirmed_t550_2_t550_3_facts": {
      "sanctum_texture_and_locations": "DM029_07",
      "character_continuity": ["DM041_C", "DM041_D"],
      "doran_mechanics": "DM041_A",
      "sera_pair_doctrine": "DM041_E",
      "wren_mechanics": "DM041_B"
    }
  },
  "fronts": {
    "eclavdra": {
      "runtime_owner": "DM045_DS3",
      "plot_state_owner": "DM050_0",
      "maegera_and_flask": "removed_not_a_party_objective",
      "patron_house": "unnamed_non_xorlarrin",
      "taliandra": "absent"
    },
    "ithreva_ordinant": {
      "runtime_owner": "DM045_DS1",
      "coordination_with_eclavdra": "tactical_only_no_shared_command"
    },
    "simulation_boundary": {
      "findings_owner": "DM038_CH",
      "stored_here": false,
      "changes_live_state": "only_by_separate_confirmed_commit"
    }
  },
  "routing": {
    "receipts": "DM035_0e",
    "prep_and_simulation": "DM038_CH",
    "edge_owner": "DM038_L dm-state-1.edge",
    "staging_delta_format": "DM000_4"
  }
}
```

## Prose Outside the State Block

The structured block above is the sole owner of current Divineverse state.
Played prose remains in the rolling narrative family; mechanics remain in their
character authorities; prep and non-canon simulation findings remain in
`DM038_CH`; current maintenance receipts append to `DM035_0e`.

### Soliera's Silence

Soliera's silence is action, not missing narration. Her unvoiced presence may
change how a room behaves, but no collaborator supplies words, thoughts, or an
unplayed decision for her.

### Blind-Play Boundary

Corey plays the module blind. Never volunteer deviation or replacement logic,
or the contents of an unopened room. Corey voices Soliera, Deashi, Sera, and
Ember by default; the collaborator runs NPCs, dice, and environment. Corey may
explicitly delegate one named divine voice for the active session only. That
delegation permits spoken dialogue, not invented thought, intent, or durable
voice ownership. The stable doctrine and the relentless-court consequence clock
are owned by `DM038_1b`.

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM038_L -->
