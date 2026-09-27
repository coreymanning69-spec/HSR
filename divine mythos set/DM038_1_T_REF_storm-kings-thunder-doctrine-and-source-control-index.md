---
id: DM038_1
title: "Storm King's Thunder — Doctrine and Source-Control Index"
type: reference
subtype: module-doctrine-and-source-control-index
load_priority: load-after-DM034_3-when-SKT-doctrine-or-source-control-matters
canon: T
verse: Divineverse
timeline: T-SKT
beat_range: TR3-SKT-source-control
arc: storm-kings-thunder
era: global-tour
status: hard-canon
authority: authoritative-for-storm-kings-thunder-doctrine-and-adapted-source-control-policy
updated: 2026-09-07
volatility: slow
arc_scope: storm-kings-thunder
derived_from: null
predecessor_file: DM026_0
successor_file: DM038_1b
runtime_state_owner: DM038_L
runtime_numeric_owner: DM038_L
runtime_history_owner: DM035_0e

scope:
  covers:
    - Storm King's Thunder doctrine and adapted source-control policy
    - active DM038_6 Chapters 10–12 and appendices map
    - archived Chapters 1–9 traceability
    - DM038_CH prep-change routing and audit ledger
    - key module spine and NPC/location/control tables
    - filled CoWork/Claude Divineverse treatment
  use_case: load after DM034_3 for SKT doctrine, adapted chapter control, or story review
  not_for: live play deviations; those belong in the persistent Divine Mythos ledger DM038_L

xref_concepts:
  - storm-kings-thunder
  - module-doctrine-index
  - arc-load-map
  - source-control-map
  - skt-giant-scale

canon_flags:
  - "#RULE-SOLIERA-SILENCE-UNLESS-DM"
  - "#RULE-DEASHI-NONVERBAL-ALWAYS"
  - "#RULE-PROTECT-CHILDREN"
  - "#RULE-INFRASTRUCTURE-NOT-EMPIRE"
  - "#RULE-JOY-FIRST-ENFORCEMENT"
  - "#RULE-CONSENT-AND-COMPREHENSION"
  - "#RULE-NO-ANTI-FEATS"
  - "#RULE-MODULE-SCAFFOLDING-DIVINE-OVERWRITE"
  - "#RULE-NPCS-ARE-PEOPLE-NOT-QUEST-OBJECTS"
  - "#RULE-VICTIMS-DEFINE-VICTORY"
  - "#RULE-NO-GENRE-INFERENCE"
  - "#RULE-DIVINE-NOT-PLAYER-POWER-FANTASY"
  - "#RULE-STEWARDS-ARE-THE-ROLLING-PARTY"
  - "#RULE-SOLIERA-PREVENTS-NEEDLESS-DEATH-AND-SUFFERING"
  - "#RULE-ONE-MODE-NOT-TWO"
  - "#RULE-NARRATIVE-COMBAT-GATE"
  - "#RULE-MODULE-NONCOMBAT-LIVE"
  - "#RULE-SKT-GIANT-SCALE"


purpose: >
  Doctrine and adapted source-control owner for Storm King's Thunder. DM034_3
  owns source-asset retrieval and selects this file only when its policy or
  chapter-control map is needed.

arc_load_map:
  DM038_6:
    file: DM038_6_T_REF_storm-kings-thunder-endgame-source-control.md
    source_chapters: chapters-10-through-12-and-appendices
    covers: Maelstrom, Kraken Society, Hekaton rescue, Iymrith finale, appendices
    load_when: source-control questions about storm giant court, Kraken Society, Hekaton, Iymrith, or endgame routing
  DM038_CH:
    file: DM038_CH_T_REF_storm-kings-thunder-meta-and-sandbox-ledger.md
    source_chapters: prep-change-routing
    covers: prep migration queue, source-control edit audit, sorting decisions
    load_when: deciding where new SKT source notes should be moved or auditing prep changes

retired_chapter_control:
  archive: project context/TR3_SKT_ARCHIVE/chapters-01-09
  registry: INVENTORY.json
  use: historical retrieval only; never an active cartridge or continuation route

characters:
  opening_divine_weather: [Soliera, Sera, Ember]
  non_deployed_divine_reference: [Deashi]
  field_stewards: [Doran, Wren]
  guide_and_lore_npcs: [Zephyros, Harshnag]
  giant_lords: [Guh, Kayalithica, Storvald, Zalto, Sansuri]
  storm_court: [Hekaton, Neri, Serissa, Mirran, Nym, Uthor]
  hidden_antagonists: [Iymrith, Slarkrethel, Kraken-Society]

locations:
  opener_and_frontier: [Nightstone, Bryn-Shander, Goldenfields, Triboar, Savage-Frontier, Eye-of-the-All-Father]
  giant_lord_sites: [Grudd-Haug, Deadstone-Cleft, Svardborg, Ironslag, Lyn-Armaal]
  endgame: [Maelstrom, Grand-Dame, Morkoth, Iymriths-Lair]

ai_directives:
  - enter SKT source and runtime retrieval through DM034_3
  - keep source extraction paraphrased and table-driven; do not paste module prose
  - route current Divineverse story state to DM038_L across arc handoffs; route current receipts to DM035_0e
  - write played prose to the rolling DM038_N# owner resolved by the family rule and mirror completed beats into DM002_3; never pre-author an open lane
  - preserve CoWork Divineverse treatment unless Corey explicitly revises it
  - check DM026_0 before finalizing any giant-handling interpretation
---

# DM038_1 — Storm King's Thunder — Doctrine and Source-Control Index

## Module Layer Model

Storm King's Thunder runs on three layers (the live-module contract; see DM034_1 §1
and DM034_2 §6). Keep them separate:

- **Source control** — this file, active DM038_6/6a/6b, and DM038_CH. Stable
  Chapters 10–12 facts, maps, stat blocks, doctrine, and prep history. Retired
  Chapters 1–9 control is preserved in `project context/TR3_SKT_ARCHIVE`.
- **Live state** — DM038_L is the persistent Divine Mythos domain ledger. It
  owns the continuation edge, gates, route, exact Steward readiness, durable
  regional/mechanical state, and open fronts; Court and later handoffs update
  its keyed arc state rather than moving those lanes. DM035_0e owns current
  append-only receipts.
  State only—never narrative.
- **Timeline narrative** — all SKT narrative packets remain canonical. DM038_N6
  owns the played T549.3–T550.0 close and recorded T550.1 departure boundary.
  Each completed beat mirrors a one-line entry into the DM002_3 live-edge spine.

Runtime load sets for every SKT route live in `DM034_0` MOUNT SETS and are not
restated here. The only active part is DM038_6/6a/6b, selected through
`skt_storm`; DM040_0 is retrieved only for characterization.
T516–T524 continuity now belongs to the confirmed-only DM038_N0 record; it
preserves missing granularity explicitly and never reconstructs dialogue.

## Module Content Preservation Gate

`#RULE-MODULE-NONCOMBAT-LIVE` `#RULE-NARRATIVE-COMBAT-GATE`

The module is a world to play through, not a chain of stat blocks. Social
encounters, travel, investigation, exploration, hazards, local customs,
environmental pressure, named NPC motives, captives, witnesses, and ordinary
life at each site remain active material. Divine capability and high Steward
competence change how those situations resolve; they do not delete the
situations or compress every location into its boss fight.

Before running a module leg or site, consult the active DM038 part's location,
NPC, atmosphere, scene-scaffolding, and source-routing sections. Surface the
material relevant to the characters' route. Random tables remain optional, but
noncombat content that is already present on the chosen route is not skipped
merely because no fight is required.

Run people as people. Wren looks, listens, thinks, follows implications, and
forms opinions; obvious evidence within her senses or training is narrated to
her without a permission roll. Doran is also a thinker and tactician, and in
most mortal rooms he is plainly the strongest man present; routine physical
work beneath that established capability simply succeeds. Roll when an outcome
is concealed, opposed, dangerous, time-sensitive, or otherwise meaningfully
uncertain. If initiative begins or a combat/simulation is declared, DM000_1's
mechanical gate takes over and the dice bind.

## SKT Giant Scale

`#RULE-SKT-GIANT-SCALE`

Authority migrated to `DM057_0` § `SKT-GIANT-v2` (2026-09-06). The scale is one
row of the corpus scale registry; values are unchanged. Retrieve `DM057_0` for
the tuple and precedence. This file no longer carries the definition.

<!-- Validator compatibility projection: DM057_0 is the authority; this exact
tuple remains machine-readable here for the existing R8 acceptance contract. -->
```json
{
  "scale": "SKT-GIANT-v2",
  "effective_from": "T537.0+",
  "module": "storm-kings-thunder",
  "ancestries": ["hill", "stone", "frost", "fire", "cloud", "storm"],
  "named_variants": "included",
  "allegiance": "irrelevant",
  "exclusions": ["ogre", "troll", "ettin", "oni", "fomorian", "construct", "animal", "shapechanged_non-giant"],
  "application": "exact-once",
  "application_order": "after-printed-or-template-modifiers",
  "deltas": {"ac": 1, "weapon_or_spell_attack_rolls": 1, "damage": 3, "save_dcs": 1, "hp_max": 200, "hp_current": 200},
  "preserve_existing_damage": true,
  "replaces": "generic-30-60-percent-hp",
  "unchanged": ["proficiency_bonus", "hit_dice", "challenge_rating", "xp", "saves", "speed", "ability_scores", "actions", "reactions", "resistances"],
  "other_stat_changes": "none"
}
```

## Source Assets and Roles

| Asset | Drive title | Role in DM038 extraction | Notes |
|-------|-------------|--------------------------|-------|
| PDF | Storm King's Thunder.pdf | Page/chapter authority | Use for final page verification. |
| TXT | Storm Kings Thunder.txt | Searchable OCR/source locator | Noisy extraction; use for section finding, not direct prose import. |
| Sheet | Copy of My SKT Master Index (Shared) | Prep/index support | Google Sheet ID `1T9aXhKw7I5eZJ7kXajYczZhpdOjnHcknbcJako9E1yA`. Tabs cover lore, monsters, random encounters, giant-bag items, treasure, and wish list. Use this as the spreadsheet source; do not build a parallel tracker. |

## Local Source Chunk Layer

DM034_3 owns source navigation. It routes the 122 compact page-aware segments,
the machine index, and split PDFs by chapter, page, and prefix. Query one index
row and load one source asset; do not read
the source layer or either index whole. Official errata overrides the older PDF
wording; the split PDF remains visual authority.

## Source Sheet Tab Routing

| Sheet tab | Primary use | Routes to | Handling rule |
|-----------|-------------|-----------|---------------|
| Foreshadowing and Lore | Lore breadcrumbs, reveal order, homebrew causal notes. | DM038_1 or DM038_6; archive for Chapters 1–9 | Extract concept summaries and reveal conduits. Completed-leg material is historical only. |
| Monsters | Encounter/stat index by chapter, SKT page, heading, named creature, monster base, CR, and source page. | DM038_6; archive for Chapters 1–9 | Use as lookup support. Active additions belong only to the storm/endgame owners. |
| Random Encounters | Chapter 3 / travel-facing encounter ideas. | Chapters 1–9 archive | Historical lookup only. |
| Giants Bag | d100 giant-bag props. | Chapters 1–9 archive | Historical lookup only. |
| Treasure | Chapter/page/location item index, including conches and artifacts. | DM038_6; active live ledger for current state; archive for Chapters 1–9 | Ordinary completed-leg loot remains historical. |
| Wish List | Player-requested magic item wish list. | DM038_CH / table prep only | Do not route to canon files unless an item enters play. |

## SKT Owner and Write Map

This is the SKT projection of `routing-catalog.yaml` `editable_owners`, not a
second permission system. SANDBOX is read-only.

| Owner group | Function | Central mode |
|---|---|---|
| DM038_1/1b/1c/1d and DM038_6/6a/6b | Active doctrine and storm/endgame source control | canonical owner; never edit during play |
| `project context/TR3_SKT_ARCHIVE/chapters-01-09/` | Retired Chapters 1–9 control files | historical retrieval only; inventory and hashes enforced |
| DM038_CH | Approved prep decisions and explicitly non-canon simulation findings | `append-only-audit-history` |
| DM038_L | Persistent Divine Mythos current state across arc handoffs | `overwrite-after-confirmed-commit` |
| DM038_LH | Advancement, adaptation, injury, capture, spellbook, equipment receipts | **Archived 2026-08-08** — content in DM035_0e |
| DM038_N1/N3 | Closed T525–T536 played prose | repair-only historical narrative |
| DM038_N2/N4/N5/N6 | Played prose T537–T550.1 | `timeline-narrative-mirror-after-canon-or-play`; closed narrative chain; mirror completed beats to DM002_3 |
| `storm king texts/` and indexes | Generated page-aware source segments and indexes | `tool-managed-only`; rebuild tool only |

## Chapter Source Map

| Source segment | Book pages | Routes to | Source-control notes |
|----------------|-------|-----------|----------------------|
| Introduction through Ch. 9 | 7-200 | Chapters 1–9 archive | Completed evidence only; the matching generated segments, PDF pages 1–201, are archived. Segment headers carry both `pdf-pages` and `book-pages`; DM034_3 routes by PDF page. |
| Ch. 10 - Hold of the Storm Giants | 201-214 | DM038_6 | Maelstrom and storm giant court. |
| Ch. 11 - Caught in the Tentacles | 215-224 | DM038_6 | Grand Dame, Morkoth, Kraken Society, Hekaton rescue. |
| Ch. 12 - Doom of the Desert | 225-230 | DM038_6 | Iymrith's lair and adventure conclusion. |
| Appendices A-D | 231-256 | DM038_6 | Linked adventures, magic items, creatures, special NPCs. |


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM038_1 -->
