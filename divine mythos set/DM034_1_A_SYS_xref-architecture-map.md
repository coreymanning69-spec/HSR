---
id: DM034_1
title: "Master File Index & XREF Router"
type: sys
subtype: xref-index
load_priority: load-on-demand-deep-index
canon: ALL
verse: ALL
timeline: META
arc: system-organization
status: hard-canon
authority: defines-file-index-and-xref-routing-for-all-files
updated: 2026-09-18
volatility: slow
arc_scope: evergreen
derived_from: null
predecessor_file: DM034_0
successor_file: DM034_2
compact_pack_status: frozen-canon-archive
compact_pack_frozen: 2026-08-30
purpose: Compact master index, segment router, retirement registry, and frozen-pack inventory owner.
---

# DM034_1 — MASTER FILE INDEX & XREF ROUTER

## SEGMENT MAP

Load only the smallest segment whose coverage matches the question. Each sibling repeats its own scope and authority context.

| ID | Covered section |
|---|---|
| DM034_1 | Master file index and compact pack selection |
| DM034_1a | XREF, Drop-In, Source, and Pack Detail |
| DM034_1b | Verification and Tooling Discipline |

## 1. MASTER FILE INDEX (single source of truth)

Range = beat coverage where applicable. Split groups are indexed only by their real file IDs.

### TOPOLOGY LOCK THROUGH DM040_0

The current file-family topology from `DM000_1` through `DM040_0` is frozen after
the pre-v8 cleanup. Context restoration edits the smallest existing owner; it
does not create another child split, rename an established ID, merge file
families, or migrate suffixes in this locked range. If genuinely new scope
cannot fit an existing owner, it receives a new top-level file ID under the
normal create-and-register gate. This is a topology lock, not a content freeze:
volatile state and authorized context enrichment continue in their owners.
Recorded exceptions include Corey's 2026-07-27 atomization of DM038_L, the
2026-07-31 DM038_N2 narrative handoff, the 2026-08-08 interim three-ledger
consolidation, the 2026-08-23 SKT consolidation, and the 2026-08-31 four-domain
ledger cutover, plus Corey's 2026-09-04 authorization of DM000_4 as the
operational play-law owner consolidated out of the two resident boot files.
DM038_L is now the persistent Divine Mythos state ledger; its
active arc is keyed inside the state block and does not cause successor-file
migration. DM052_0 is the on-demand Court/endgame reference; DM038_L remains
the persistent current-state owner.

### [SYSTEM]
| ID | Title | Notes / Load |
|---|---|---|
| DM000_1 | Core Bootloader | Whole-file action, stance, write and collaboration gates — MUST-LOAD-EVERY-SESSION |
| DM000_2 | Active State | File state, current threads — FORGE-only; points here for index |
| DM000_3 | Voice Gates | Whole-file voicing, spelling and dictation gates — MUST-LOAD-EVERY-SESSION |
| DM000_4 | Operational Play Law | Voice register, visual anchors, mechanics, pacing, staging and handoff — FORGE; exact section on demand elsewhere |
| DM034_0 | Route Spine | Whole-file route gate, loaded only when work needs a route |
| DM034_0b| Route Spine — Cold Arcs | Closed/dormant arc file rows — load only when touching those arcs |
| DM034_1 | Master File Index & XREF Router | Deep index and verification — load on demand |
| DM034_2 | Tag Registry & Architecture Standards | Tag taxonomy, #RULE registry, design principles — load for tagging passes |
| DM034_3 | Storm King's Thunder Master Router | Conditional SKT source/runtime entry; never resident |
| DM035_0e | Current Corpus Event Log | Sole append-only maintenance receipt target |
| DM059_0 | Pending Corrections Queue | Decided-but-uncomposed canon corrections; load on a SCALPEL/review pass; cleared items move to DM035_0e |

### [META & CONTEXT]
| ID | Title | Range / Notes |
|---|---|---|
| DM001_0 | Project Synthesis | Theology, physics, design philosophy |
| DM002_1 | Divineverse Timeline Spine | T0–T260; T260 shared handoff anchor |
| DM002_2 | Mergeverse Timeline Spine | M0–M90; M90 shared handoff anchor |
| DM002_3 | Divineverse Timeline Spine | T260 onward; the spine's mirrored range and the closed-prose owner are both derived — see the `_N#` family rule in DM034_0 — not stated here. Current route → DM034_0 CURRENT ARC; current edge and active live ledger → `DM038_L dm-state-1.edge`. Legacy filename remains T260-T533 under topology lock. T550.2 and T550.3 were compressed on 2026-08-30; T550.4 remains an empty open lane. |
| DM002_5 | Mergeverse + Travel Records Spine | M90–M183 / TR1–TR-JP-05 |
| DM003_0 | World-Physics Axioms & Craft Notes | Minimal axiom/craft reference |
| DM004_1 | Character Matrix — Divineverse Divine Core | Yuium, Soliera, Deashi, Sera, Ember, Niv-Saiffar |
| DM004_2 | Character Matrix — Divineverse Founding Inner Circle | Founders and retirement rules |
| DM004_2b | Character Matrix — Divineverse Household & Staff | Later household/staff; Doran/Wren and Writ Six routing |
| DM004_2c | Character Matrix — Divineverse Allies & Antagonists | D&D allies, antagonists/deities, Undermountain companions |
| DM004_3 | Character Matrix — Primeverse & Mergeverse cast | |
| DM042_0 | Divine Architecture & Theology | Master theology: offices, metamorphosis circles, distributed YUIUM, Veiled Eye, consent boundaries |
| DM043_0 | Suzu Hikari and Plum Titan | Primeverse / TR-JP character and construct reference |

Routing note: DM042_0 is the master theology file; the pillars, Sera files, and
DM029_03 all point into it for architecture. Use DM028_1/DM028_2/DM028_3,
DM027_0/DM030_1, and DM029_03 for character-specific application.

### [DIVINEVERSE T-BEATS]
| ID | Title | Range / Notes |
|---|---|---|
| DM005_0 | Sanctum Foundation | T0–T50 |
| DM006_0 | Taliandra and Dracolich | T51–T100 |
| DM007_1 | Sanctum Expansion & Frostfell Approach | T101–T120 |
| DM007_2 | Frostfell Resolution & Northern Court | T121–T140 |
| DM008_1 | Convoy Ambush to Skyreach Castle | T141–T160 |
| DM008_2 | Skyreach, Sea of Ice & Waterdeep Return | T161–T190 |
| DM008_3 | ROT Begins & Kessla Baptism | T191–T220 |
| DM009_0 | Misty Forest to Wall of Dragons | T221–T290 |
| DM010_1 | Well of Dragons: The Breach | T291–T298 |
| DM010_2 | The Genesis of Ember | T299–T308 · Requires DM010_1 (T297 army state, T298 reconstitution) |
| DM010_3 | Aftermath: The Gods Walk | T309–T326 |
| DM011_0 | Post-Tiamat to Thay | T327–T355 |
| DM012_0 | Eltabbar to Waterdeep | T356–T396 |
| DM013_0 | Undermountain to Merge | T397–T429 |
| DM017_0 | Descent into Avernus | T430–T475 |
| DM018_0 | Curse of Strahd Setup / Arc Index | T476; MUST-LOAD-BEFORE-DM019_1/DM019_2 |
| DM019_1 | Curse of Strahd Part 1 | T476–T498 (Feast → Mists → Village → Gates) |
| DM019_2 | Curse of Strahd — Castle/Execution | T499–T512 |
| DM019_2b| Curse of Strahd — Dark Powers/Aftermath | T513–T515 |
| DM019_3 | Curse of Strahd Analysis | Retrospective deviations, development, theology |

### [ITINERARY LOCATIONS — COMPLETE INDEX]
| Location | Canonical owner |
|---|---|
| 01 The Sanctum · 02 Ten-Towns / Bryn Shander · 03 Mirabar | DM024_1 / DM024_1a / DM024_1b / DM024_1c |
| 04 Luskan · 05 Port Llast · 06 Neverwinter | DM024_2 / DM024_2a |
| 07 Neverwinter Wood / Mount Hotenow · 08 Silverymoon | DM024_2b / DM024_2c |
| 09 Waterdeep · 10 Baldur's Gate · 11 Candlekeep · 12 Undermountain | DM024_3 / DM024_3a / DM024_3b / DM024_3c |
| 13 Evermeet · 14 Chult / Port Nyanzaru · 15 The Astral Sea · 16 Halruaa · 17 Lantan | DM024_4 |

### [MERGEVERSE M-BEATS]
| ID | Title | Range / Notes |
|---|---|---|
| DM014_1 | Primeverse Canon Overview | Soliera Prime, Arden, locations |
| DM014_2 | Primeverse World Systems | Company, Church, technology, modular magic |
| DM014_3 | Primeverse Character Profiles | Evan, Arden, Veris, Cassian, Veyren, Varn |
| DM014_4 | Merge Recap Ledgers & Oak City Archive | Archive-only; direct/SCALPEL load; current beats override |
| DM015_1 | Oak City Arrival — Gate to Tavern Threshold | M0–M21 |
| DM015_2 | Oak City Arrival — The Feast and the Soldiers | M22–M44 |
| DM015_3 | Oak City Arrival — Company Intervention & Settlement | M45–M55 |
| DM015_4 | Transition Staging — Oak City Arrival to Settlement | M56 metadata recap |
| DM016_1 | Oak City Settlement | M57–M90 |
| DM016_2 | Badlands to Breach | M91–M125 |
| DM016_3 | Slums, Feast and Home | M126–M150 |
| DM020_1 | Return to Oak City — Compressed Beats | M151–M155 continuity lookup |
| DM020_1b| Return to Oak City — Compressed Beats | M156–M159 continuity lookup |
| DM020_2 | Return to Oak City — Scenes | M151–M160 full-prose scenes |
| DM021_1 | The Meeting | M161–M175 and M180 full prose; M176–M179 canonical staging recaps |
| DM021_2 | Mergeverse Canon | M181–M182 authorized reconstruction prose; M183 locked handoff prose |

### [PRIMEVERSE P-BEATS]
| ID | Title | Range / Notes |
|---|---|---|
| DM033_1 | Soliera Prime and Arden — Foundation | §§I–III |
| DM033_2 | Prime Ensemble | §§IV–XI |
| DM033_3 | Prime World Systems and Locations | §§XII–XIII; overlap with DM014_2 retained |
| DM033_4 | Prime Power Structure and Timeline | §§XIV–XVII |

### [CHARACTER & MECHANICS]
| ID | Title | Notes |
|---|---|---|
| DM022_0 | Primeverse Character Matrix | Primeverse T4s and Executives |
| DM043_D1 | Kiyuru Champion Runtime and Called Strikes | On-demand Kiyuru combat and d8 called-strike authority |
| DM027_0 | Sera's 5e Character Sheet | Technical combat reference |
| DM028_1 | Soliera Pillars | Voice rule: AI never voices Soliera |
| DM028_2 | Deashi Pillars | Voice rule: never speaks; Kneel T304 → 028_3 |
| DM028_3 | Ember Pillars — Framework | Local bootloader through opposition framework |
| DM028_3b| Ember — Physical/Behavioral/Combat Spec | Full Character Document Sections 1–7 |
| DM028_3c| Ember — Scene and Mental Spec | Sections 8–13 and auxiliary/meta material |
| DM029_01 | Sanctum Staff, Roles & Mortal Perceptions | |
| DM029_02 | Sanctum Full Staff Hierarchy | |
| DM029_03 | Sanctum Yuium — Ontology | Speakable Name and distributed Whole |
| DM029_04 | Sanctum — Veiled Eye and Structure | Veiled Eye and structural nature |
| DM029_05 | Sanctum — Infrastructure Instances | Cross-verse instances and systemic mechanics |
| DM029_06 | Sanctum — Horror and Comfort | Concluding structural assessment |
| DM029_07 | Sanctum — Operational and Domestic | Legal/economic/house operational reference |
| DM030_1 | Sera Internal Logic, Combat, and Reva | Origin, function, KTE, feats |
| DM030_2 | Sera Social Aura, Sanctum, and Relationships | Velvet Spiral, quotes, witness logic |
| DM040_0 | Doran & Wren Compact Character Capsules | On-demand identity, voice, relationships, and failure modes |
| DM041_0 | Doran & Wren — Steward Framework | Shared frame, teaching doctrine, ability generation |
| DM041_C | Doran — Steward Profile | Depth characterization and historical mechanics |
| DM041_D | Wren — Steward Profile | Depth characterization and historical mechanics |
| DM041_E | Doran & Wren — Pair Doctrine | Pair geometry and TR3-SKT starting route |
| DM041_A | Doran — Machine-Readable Combat Mechanics | Compact structured Fighter 20 authority: attack modes, Cleaver riders, helm vision, rule IDs. Totals live here, never in this index |
| DM041_A1 | Doran — Expanded Rules and Equipment Catalog | Maintenance-only expanded rules, equipment, and provenance |
| DM041_B | Wren — Machine-Readable Combat and Casting Mechanics | Compact structured Cleric 20 / Sorcerer 20 authority: domains, simulacrum cascade, signatures, rule IDs. Totals live here, never in this index |
| DM041_B1 | Wren — Expanded Spells and Casting Catalog | Maintenance-only expanded spells, casting, and equipment |
| DM044_0 | Combat Runtime — Protocol and Doran | Section map: roll authority, round state, giant pointers, Doran's pre-totaled level-20 sheet |
| DM044_1 | Combat Runtime — Wren | Section map: Wren's pre-totaled sheet and simulacrum rules; section-loads with DM044_0 |
| DM045_DS1| The Ordinant — Chosen of Bane | Champion-band antagonist: artifacts, runtime, T531 retroactive read, forward hooks |
| DM045_DS2| The Writ Six and Hollowmark Findings | Reusable NPC roster plus explicitly non-canon reverse-simulation evidence |
| DM045_DS3| Eclavdra — Chosen of Lolth | Champion-band control/information antagonist: runtime, Skein doctrine, counterplay |
| DM045_DS4| Belthyn — Chosen of Umberlee | Champion-band commander/controller: Tempest Cleric runtime, construct collateral, prison pressure |
| DM045_DS5| Ithreva Sazher — Lich of Myrkul | Champion-band lich: displacement doctrine, stone-giant thralls, phylactery gate, certification pending |

| DM046_0 | Hollow Star Reliquary Framework | Original-scenario target: level-20 gate, procedural system, Sandbox isolation, Forge promotion |
| DM046_1 | HSR Champion Band | Reversible Reliquary-only champion overlay; excluded from the frozen portable GPT pack |
| DM047_0 | The Blessed — Permission Tier Framework | Above-artifact object class: discretionary conferral by Soliera, register by pointer, future-optional edge cases |
| DM048_0 | The Black Bird Sigil | Sera origin, enclosed form, Sanctum dominion, Amphail open-door doctrine, and Guh's Sending token |
| DM049_0 | The Champion Era and the Pawn Awakening | Load-on-demand ambient seeds; named champion block is DM-side pointer only; author-gated |
| DM050_0 | Eclavdra Final-Operation Plot State | Host force, transformed mother, Proto-Forge role, Taliandra absence, and T536 hidden truth; no combat runtime |
| DM051_0 | Champion Tier Doctrine and Roster | Displacement doctrine and current dossier index; proposed extensions remain labeled |
| DM057_0 | Scale and Inversion Registry | Portable scale precedence, settled overlays, and inert proposed curves |
| DM058_0 | Edition Divergence Registry | Settled 3.5e/5e translations and explicit open splits |
| DM053_0 | 2014 5e Playable Profiles — T4 Roster | Proposed 5e translations for Cassian, Veyren, Kiyuru, Suzu, and Hakubai |
| DM054_0 | Mergeverse State Ledger | M/TR-beat state from the M0 seam forward, the Merge ruleset delta, and post-portal Prime character state — scaffold |
| DM055_0 | Hollow Star Run Ledger | Desktop-only, on-demand run and findings notebook; gate state is a projection, DM046_0 and the runtime stay authoritative |
| DM056_0 | Primeverse Origin Sealed Ledger | Sealed pre-M0 origin index and import provenance; no authoring in play — scaffold |

### [TRAVEL ARC TR-BEATS]
| ID | Title | Range / Notes |
|---|---|---|
| DM023_0 | Itinerary Checklist | Tracking |
| DM024_1 | Itinerary Atlas — Overview & The North | |
| DM024_2 | Itinerary Atlas — Coast & Midlands | |
| DM024_3 | Itinerary Atlas — South & Undermountain | |
| DM024_4 | Itinerary Atlas — Extraplanar & Meta | |
| DM025_0 | TR1: Luskan | COMPLETE |
| DM026_0 | TR2: Against the Giants G1/G2/G3 | COMPLETE |
| DM039_0 | TR-JP: Japan Opening | TR-JP-01–TR-JP-05 + Hisako parallel POV compiled; arc closed 2026-06-20 |

### [WORLDSTATE & GEOGRAPHY]
| ID | Title | Notes |
|---|---|---|
| DM031_0 | Divineverse Setting Changes | Faerûn, Underdark & Extraplanar |
| DM032_0 | Mergeverse & Primeverse Setting Changes | Oak City / Neon City |

### [STORM KING'S THUNDER SOURCE CONTROL]
| ID | Title | Range / Notes |
|---|---|---|
| DM038_1 | SKT Doctrine & Source-Control Index | Adapted module policy; source retrieval → DM034_3 |
| DM038_1b| SKT Arc Doctrine | Module spine through guide NPCs |
| DM038_1c| SKT Stewardship and Flavor | Stewardship crucible and early flavor |
| DM038_1d| SKT Giant History and Escalation | History, embassy context, escalation order |
| DM038_6 | SKT Chapters 10–12 & Appendices | Maelstrom, Kraken Society, and finale; scene scaffolding and Kraken voices in shards DM038_6a / DM038_6b |
| DM038_CH | SKT Meta and Sandbox Ledger | Approved prep decisions and non-canon simulation findings only |
| DM038_L | Divine Mythos State Ledger | Persistent current Divineverse state owner; active arc, edge, gates, route, readiness, regional state, and open fronts live in its structured block |
| DM052_0 | Storm King's Court and Endgame Reference | On-demand Court/endgame sequence and owner-routing guide; never a live-state or encounter-mechanics owner |
| DM038_N0| SKT Confirmed-Only Played Record | Closed continuity owner T516-T524; explicit missing-granularity markers preserve gaps without invented prose |
| DM038_N1| SKT Closed Played Narrative | Historical timeline prose T525-T532; mirrors to DM002_3 spine |
| DM038_N2| SKT Played Narrative T537–T540 | Closed rolling packet preceding DM038_N4 |
| DM038_N4| SKT Played Narrative T541–T542 | Closed rolling packet preceding DM038_N5 |
| DM038_N5| SKT Played Narrative T543–T549.2 | Closed packet preceding DM038_N6 |
| DM038_N6| Goldenfields Close and Sanctum Departure | Played T549.3–T550.0 plus recorded T550.1 departure boundary; later bare Sanctum position and refreshed readiness → DM038_L; no arrival scene authored |
| DM038_N7| Sanctum Downtime | Played T550.2 Sanctum arrival interlude; closes at the courtyard |
| DM038_N8| Sanctum Courtyard | Played T550.3 courtyard spar and glacier plan; Wren next |
| DM038_N9| Glacier Demonstration | Opened empty for unplayed T550.4 demonstration |

**Doran and Wren are indexed once, under [CHARACTER & MECHANICS].** DM040_0,
DM041_0, DM041_A, DM041_A1, DM041_B, DM041_B1, DM041_C, DM041_D, DM041_E, and
DM044_0/DM044_1 are character/mechanics owners that travel with the pair, not SKT
source-control assets; they do not retire when the module closes. Read their
rows there. Do not re-list them here — a second listing is what allowed the two
copies to drift apart in title and load note before 2026-08-02.

**The live-module contract (generic).** Any D&D module run as live play splits
across three layers: **source control** (stable module facts and prep history,
never edited during play), **live state** (one active current-story ledger —
state only, never the narrative of record), and
**timeline narrative** (played prose in an `_N` owner, each completed beat
mirrored as a compressed entry into the owning DM002 spine). Played turns are
narrated in the `_N` file and compressed into the spine; they never accrete
inside the live ledger. §3 carries the routing rule.

**Which file fills each SKT layer is owned by DM038_1** — read it there, not
here. This index does not duplicate the SKT instantiation.

### [SKT SOURCE ASSETS]

DM034_3 is the sole SKT source-navigation owner. It maps the 122 compact
page-aware segments, machine index, and split PDFs to the correct DM038 owner.
Query only its matching routing section when source navigation is necessary;
current continue/resume follows DM034_0 CURRENT ARC to DM038_L, then reads the
edge from `DM038_L dm-state-1.edge`, without mounting DM034_3. Query one index
row and retrieve one source asset;
source assets establish module facts, never Divineverse outcomes.

### [RETIRED]
| ID | Disposition |
|---|---|
| DM036 | §A → DM021_2; §L → DM034_1; Design Principles → DM034_2 (2026-05-10)|
| DM037 | §B/§C → DM000_1 (2026-05-10) |
| DM002_4 | Former T523+ live-edge spine; merged into DM002_3 (2026-07-12) |
| DM038_L2 | SKT standing regional state; consolidated into DM038_LU 2026-08-08, stub retired to `project context/TR3_SKT_ARCHIVE/retired-ledger-stubs-2026-08-23/` (2026-08-23) |
| DM038_L3 | SKT deviation and inventory; consolidated into DM038_LU/DM038_LS 2026-08-08, stub retired to `project context/TR3_SKT_ARCHIVE/retired-ledger-stubs-2026-08-23/` (2026-08-23) |
| DM038_L4 | SKT NPCs and forward hooks; consolidated into DM038_LS/DM038_LU 2026-08-08, stub retired to `project context/TR3_SKT_ARCHIVE/retired-ledger-stubs-2026-08-23/` (2026-08-23) |
| DM038_LM | SKT Steward mechanics; consolidated into DM038_LU 2026-08-08, stub retired to `project context/TR3_SKT_ARCHIVE/retired-ledger-stubs-2026-08-23/` (2026-08-23) |
| DM038_LH | SKT Steward state history; superseded by the current receipt log and retained off-corpus |
| DM038_LU | SKT utility state; consolidated into DM038_L and preserved in `project context/TR3_SKT_ARCHIVE/retired-ledger-owners-2026-08-23/` (2026-08-23) |
| DM038_LS | SKT endgame-thread state; consolidated into DM038_L and preserved in `project context/TR3_SKT_ARCHIVE/retired-ledger-owners-2026-08-23/` (2026-08-23) |
| DM000_T | Stale generated T-coverage report (`DM000_T_COVERAGE_MAP.md`, never a canon owner); moved to `divine mythos set/outputs/DM0_T_COVERAGE_MAP.md`, the path `tools/t_coverage.py --write` now targets (2026-09-18) |


### [SEGMENT SHARDS]

Split and semantic shards. Load through the parent owner's SEGMENT MAP;
never bulk-load a family when one shard answers the question.

| ID | Parent owner |
|---|---|
| DM004_1a | DM004_1 |
| DM004_1b | DM004_1 |
| DM004_0 | DM004_2c |
| DM004_4 | DM004_2c |
| DM004_3a | DM004_3 |
| DM005_0a | DM005_0 |
| DM005_0b | DM005_0 |
| DM006_0a | DM006_0 |
| DM006_0b | DM006_0 |
| DM007_2a | DM007_2 |
| DM007_2b | DM007_2 |
| DM008_1a | DM008_1 |
| DM008_1b | DM008_1 |
| DM008_2a | DM008_2 |
| DM008_2b | DM008_2 |
| DM008_2c | DM008_2 |
| DM008_3a | DM008_3 |
| DM008_3b | DM008_3 |
| DM009_0a | DM009_0 |
| DM009_0b | DM009_0 |
| DM009_0c | DM009_0 |
| DM010_3a | DM010_3 |
| DM012_0a | DM012_0 |
| DM012_0b | DM012_0 |
| DM012_0c | DM012_0 |
| DM013_0a | DM013_0 |
| DM013_0b | DM013_0 |
| DM014_4a | DM014_4 |
| DM014_4b | DM014_4 |
| DM015_1a | DM015_1 |
| DM015_1b | DM015_1 |
| DM015_2a | DM015_2 |
| DM015_2b | DM015_2 |
| DM015_2c | DM015_2 |
| DM015_3a | DM015_3 |
| DM016_1a | DM016_1 |
| DM016_2a | DM016_2 |
| DM016_2b | DM016_2 |
| DM016_3a | DM016_3 |
| DM016_3b | DM016_3 |
| DM017_0a | DM017_0 |
| DM017_0b | DM017_0 |
| DM019_1a | DM019_1 |
| DM021_1a | DM021_1 |
| DM021_1b | DM021_1 |
| DM022_0a | DM022_0 |
| DM022_0b | DM022_0 |
| DM024_1a | DM024_1 |
| DM024_1b | DM024_1 |
| DM024_1c | DM024_1 |
| DM024_2a | DM024_2 |
| DM024_2b | DM024_2 |
| DM024_2c | DM024_2 |
| DM024_3a | DM024_3 |
| DM024_3b | DM024_3 |
| DM024_3c | DM024_3 |
| DM025_0a | DM025_0 |
| DM026_0a | DM026_0 |
| DM029_01a | DM029_01 |
| DM030_2a | DM030_2 |
| DM034_2a | DM034_2 |
| DM034_2b | DM034_2 |
| DM038_6a | DM038_6 |
| DM038_6b | DM038_6 |
| DM039_0a | DM039_0 |
| DM041_A2 | DM041_A1 |
| DM041_A3 | DM041_A1 |
| DM041_B2 | DM041_B1 |
| DM041_B3 | DM041_B1 |
| DM041_B4 | DM041_B |
| DM034_1a | DM034_1 — XREF, Drop-In, Source, and Pack Detail |
| DM034_1b | DM034_1 — Verification and Tooling Discipline |
| DM002_1a | DM002_1 — Divineverse Spine T141-T260 |
| DM002_3a | DM002_3 — Divineverse Spine T260-T396 |
| DM002_3b | DM002_3 — Divineverse Spine T397-T515 |
| DM038_N3 | DM038_N1 — SKT Played Narrative T533-T536 |

## 2. XREF RULES — DETAIL ROUTE

Full read/write, drop-in, source-default, and pack-detail rules are in DM034_1a.

## 5. GPT PROJECT 25-FILE COMPACT PACK

**Frozen TR3-SKT compact archive (25 files):**
Last manually refreshed on 2026-08-30; it remains untouched until an explicit
full refresh is run.
DM000_1 / DM000_2 / DM000_3 / DM001_0 / DM003_0 / DM002_1 / DM002_1a /
DM002_2 / DM002_3a / DM002_3b / DM002_3 / DM002_5 / DM004_1 / DM004_2 /
DM004_3 / DM028_1 / DM028_2 / DM028_3 / DM029_01 / DM030_1 / DM031_0 /
DM034_0 / DM034_1 / DM038_L / DM040_0.

The pack is a preserved canon snapshot. Never hand-edit or automatically sync
it. Tooling checks its recorded inventory and hashes only; it does not require
parity with evolving canonical owners. A future replacement is an explicit
manual full refresh with a release date. HSR owners,
runtimes, snapshots, and overlays are deliberately excluded.

## 6. TOOLING MANDATE — DETAIL ROUTE

Verification and update discipline are in DM034_1b.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM034_1 — detail routes through DM034_1a and DM034_1b -->
