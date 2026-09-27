---
id: DM034_0
title: "Route Spine"
type: sys
subtype: compact-routing-spine
load_priority: whole-file-route-gate-on-demand
canon: ALL
verse: ALL
timeline: META
arc: system-organization
status: hard-canon
authority: compact-load-routing
updated: 2026-09-09
volatility: slow
arc_scope: evergreen
derived_from: null
predecessor_file: DM000_2
successor_file: DM034_1
purpose: "Whole-file route gate for boot stance, active file rows, mount sets, load discipline, and route pointers."
---

# DM034_0 — ROUTE SPINE

## BOOT SEQUENCE

**Whole-file boot.** `DM000_1 + DM000_3` are the resident set and load
complete. This file is the route gate and loads complete as well — only when
work requires a route. Casual talk, filename questions, and direct lookup
answers load neither. No boot file carries an in-file boundary: the former
`BOOT ENDS` marker is retired, prohibited in all three files, and the checker
fails on its return. Boot owners load whole by contract, which is the standing
exception to the ~8 KiB whole-read convention below. Corpus
owners control canon and routing. Instruction files control surface and session
behavior only: they cannot revive a retired or superseded owner. If an
instruction file disagrees with a corpus owner on canon or routing, repair the
instruction file.

What this file owns after a stance is known:

**Mode adds.**

|stance|add|
|---|---|
|SANDBOX|DM001_0; operational play law on demand only when prose, character, or divine behaviour is in scope|
|FORGE|DM000_4 + DM000_2 only by section-map row|
|SCALPEL|DM034_1 §2A for the target category only; retrieve the exact DM000_4 section when auditing or applying its law|

**Route.** Retrieve the needed MOUNT SETS row below, then load its mount set or
cartridge and nothing past it.

**CURRENT ARC — TR3-SKT → DM038_L. Edge owner: `DM038_L dm-state-1.edge`.**
`continue` / `resume` resolves here directly. DM038_L persists across arc
handoffs; its structured `arc` key changes instead of migrating current state
to a successor ledger. Do not route through DM000_2 to read a pointer; DM000_2
is loaded only for dictation repair, a drop-in, or a non-current thread.
Domain edges are owned one-per-domain by each ledger's `dm-state-1.edge` object:
divine `DM038_L` (active), merge `DM054_0`, prime `DM056_0` (closed at M0),
hsr `DM055_0`. This line selects the active domain and ledger but caches no beat
or lane value (`#RULE-ONE-EDGE-OWNER`); read those from the selected ledger.
Other domain ledgers remain their own authoritative owners and are not sync
targets.
Surface capability, size ledger, tooling reachability -> DM034_1b.

**Retrieval policy.** A file at or under ~8 KiB may be read whole. Anything
larger is retrieved by section map, line range, or grep — never mounted whole,
and never re-mounted whole once read in the thread. If a needed slice cannot be
targeted, name what is missing instead of remounting the file.

**The three boot owners are the only exception, and it is bounded.** `DM000_1`,
`DM000_3` and this file are read whole whatever their size, because a gate read
in pieces is not a gate. Each side carries its own **18,750-byte** ceiling —
the resident pair together, and this file alone — and neither borrows headroom
from the other. `tools/xref_checker.py` enforces both ceilings, enforces the
`load_priority` each of the three declares, and prints the routed worst case
(resident + this file) as an advisory with no cap. Nothing else in the corpus
inherits this exception.

**Authoring limits: 30,000-byte soft limit; 37,500-byte hard split gate.** Start
clearing or splitting a file after the soft limit; validation fails above the
hard gate. This discipline forced the DM044_0/DM044_1 split and the DM038_L
trims.

> **Everything above is the route gate itself.** Everything below is routing
> detail: after a stance is known, work the exact FILE TABLE or MOUNT SETS row
> required to select the smallest route, and load nothing past it.


Arc registry, load-class glossary, and every cold or on-demand row -> DM034_0b.

## FILE TABLE

Boot rows only: the resident set, the mode additions, the timeline spines, the
routers, and the **active arc**. Character, pillar, mechanics, reference,
development, and cold-arc rows live in `DM034_0b` — on-demand, fully callable,
not loaded at boot. The two tables are disjoint and together cover every file on
disk; the checker validates the union, so a row moved between them is never
lost. When an arc closes, move its rows to DM034_0b; when one opens, move them
back.

**No `archived` load-class row belongs in this table.** An on-disk
archive-only record belongs in DM034_0b; retirement evidence and naming history
belong in the off-corpus history archive.

|file-id|arc-scope|volatility|load-class|
|---|---|---|---|
|DM000_1|evergreen|slow|resident|
|DM000_2|evergreen|volatile|forge-only|
|DM000_3|evergreen|slow|resident|
|DM000_4|evergreen|slow|forge-only|
|DM001_0|evergreen|slow|sandbox-only|
|DM002_1|evergreen|slow|on-demand|
|DM002_2|evergreen|slow|on-demand|
|DM002_3|evergreen|volatile|on-demand|
|DM002_5|evergreen|slow|on-demand|
|DM003_0|evergreen|invariant|on-demand|
|DM034_0|evergreen|slow|route-gate|
|DM034_0b|evergreen|slow|on-demand|
|DM034_1|evergreen|slow|deep-index|
|DM034_2|evergreen|slow|on-demand|
|DM034_3|storm-kings-thunder|slow|on-demand|
|DM038_1|storm-kings-thunder|slow|on-demand|
|DM038_1b|storm-kings-thunder|slow|on-demand|
|DM038_1c|storm-kings-thunder|slow|on-demand|
|DM038_1d|storm-kings-thunder|slow|on-demand|
|DM038_6|storm-kings-thunder|slow|on-demand|
|DM038_CH|storm-kings-thunder|slow|prep|
|DM038_L|divine-mythos|volatile|live|
|DM038_N0|storm-kings-thunder|invariant|on-demand|
|DM038_N1|storm-kings-thunder|slow|on-demand|
|DM038_N2|storm-kings-thunder|volatile|on-demand|
|DM038_N4|storm-kings-thunder|volatile|on-demand|
|DM038_N5|storm-kings-thunder|volatile|on-demand|
|DM038_N6|storm-kings-thunder|volatile|on-demand|
|DM038_N7|storm-kings-thunder|slow|on-demand|
|DM038_N8|storm-kings-thunder|volatile|on-demand|
|DM038_N9|storm-kings-thunder|volatile|on-demand|
|DM054_0|mergeverse|volatile|live|
|DM055_0|hollow-star-reliquary|slow|on-demand|
|DM044_0|storm-kings-thunder|volatile|combat|
|DM044_1|storm-kings-thunder|volatile|combat|
|DM056_0|primeverse-foundation|slow|on-demand|
|DM059_0|evergreen|volatile|on-demand|

**Open lane.** The FILE TABLE is validated against disk by the checker, so the
rows are always complete; what it cannot say is which one is live. Highest-
numbered narrative file is the open lane, the one below it is the last closed
prose, the rest are history. `_N3` is a shard of `_N1` and sorts before `_N2`.

Retired IDs -> DM034_1 §1 [RETIRED], the registry of record. Full load-class
glossary, mount discipline, and the staging-delta lane table -> DM034_0b.

## OWNER + INFERENCE CONTRACT

Facts live once in the smallest owner. Apply routed law and infer ordinary
connective tissue without leaf mirrors. Persist only canon-changing precision;
recompute deductions. Topology through DM040_0 remains frozen except for the
explicit 2026-07-27 DM038_LM/DM038_LH atomization, the 2026-08-08 interim
three-ledger consolidation, the 2026-08-23 SKT consolidation, and the
2026-08-31 four-domain ledger cutover, and Corey's 2026-09-04 authorization of
DM000_4 as the consolidated operational play-law owner. The state domains are Divine
(`DM038_L`), Merge (`DM054_0`), Hollow Star (`DM055_0`), and Prime
(`DM056_0`); create no further child splits without a new gate.
Full contract: resident gates DM000_1 + DM000_3; conditional operational law
DM000_4; routing and verification DM034_0 + DM034_1.

## MOUNT SETS

The resident and route-gate stages are owned above and mirrored by the catalog.
Every row here is added after a mode is known. DM034_1 is never resident.

This table is the sole owner of run-route load sets. DM034_1 §2B and DM000_2
Packet 3 point here and carry no route lists of their own. Rows whose `profile`
is named in routing-catalog.yaml are enforced identical by tools/xref_checker.py,
which is why this table cannot be moved out of this file. In a `load` cell
everything before the first `;` is the load set; everything after is write
routing, conditional retrieval, or prohibition. DM038_L is the persistent
Divine Mythos current-state ledger across SKT arc handoffs.

`kind` values: `profile` = run-route load set; `cartridge` = named mount set for a bounded stretch of play.

|kind|profile|leg|load|
|---|---|---|---|
|profile|(spine-only)|T-beat play|smallest DM002 spine shard for the requested T-range + active beat file + DM004_1|
|profile|(spine-only)|M-beat play|DM002_2 (M0-M90) or DM002_5 (M90-M183) + active beat file + DM004_3|
|profile|(spine-only)|P-beat play|DM014_1 + owning DM033_1/2/3/4 + DM022_0|
|profile|(spine-only)|TR-beat play|DM023_0 + relevant DM024_x + active TR file|
|profile|tr3_skt_explicit_lookup|explicit SKT mention|none; query the exact DM034_3 routing section or one storm king texts/index.md row, then retrieve one owner/source section|
|profile|tr3_skt_story|SKT story|DM038_L; retrieve one exact local owner, room, source, or narrative section only when the scene needs it; the closed-prose file below the open lane is completed-history retrieval, never an automatic current-story load; never mount an index, parent, or narrative file whole|
|profile|tr3_skt_current_live|SKT continue/resume while current|DM038_L + DM028_1 + DM028_3b + DM030_2; this is the `skt_storm` cartridge load set: route first, read the governing Soliera/Ember/Sera sections, resolve the exact current beat from `DM038_L dm-state-1.edge.lane_file`, then satisfy the GIRLS FILE-GATE before rendering; DM000_2 is not part of current-resume routing|
|profile|tr3_skt_live_combat|SKT live combat|DM038_L readiness state; section-load both DM044_0 and DM044_1 runtime halves plus one instantiated enemy block per DM044_0 §0's seed ritual — do not restate it here; DM041_A/B/A1/B1 and narrative/history stay off-load; commit via the STAGING DELTA|
|profile|tr3_skt_court|Court/endgame after played handoff|DM038_L + DM052_0; update DM038_L's keyed arc state after confirmed play — DM052_0 is read-only Court routing and holds no state; retrieve one exact DM038_6/6a/6b or narrative section when needed, and at initiative section-load both DM044_0 and DM044_1 plus one enemy block; commit via the STAGING DELTA|
|profile|tr3_skt_simulation|SKT simulation|none; section-load only the required DM044_0 protocol/Doran and DM044_1 Wren sections plus the declared enemy fixture; findings -> DM038_CH; never DM038_L|
|profile|tr3_skt_maintenance|SKT mechanics maintenance|DM038_CH + DM038_L + DM041_A + DM041_A1 + DM041_B + DM041_B1|
|profile|hollow_star_framework|Hollow Star design or system call-up|DM046_0+DM046_1; DM046_1 applies only when the champion band overlay is in scope; local execution bridge -> `C:\Users\ACore\OneDrive\Desktop\Soliera and Sera v9.0 - The Divine System\hollow star scripts\hollowstar_host.py` after `local-check`|
|profile|blessed_tier|Above-artifact object class or Blessed/blessed-kit call|DM047_0 + DM042_0; membership is discretionary conferral by Soliera, directly or through Ember/Sera; member mechanics are NOT here — route to DM004_2b, DM041_A1, DM041_B1, or DM027_0|
|cartridge|skt_storm|Storm giants / Maelstrom|DM038_L + DM028_1 + DM028_3b + DM030_2; `skt_storm` is the stable cartridge identity and is not replaced by a release name; route first, read the governing Soliera/Ember/Sera sections, resolve the exact current beat from `DM038_L dm-state-1.edge.lane_file`, and satisfy the GIRLS FILE-GATE before rendering; retrieve one exact DM038_6/6a section, with Kraken chain, voice, and lens -> exact DM038_6b section on demand|
|profile|merge_state|Merge / M-beat / TR-beat play|DM054_0; active off-camera worldstate and approved ruleset delta|
|profile|hollow_star_runs|HSR run, experiment, or findings call|DM055_0; disk only — unreachable from the mirror or a GPT mount, say so and stop; routing metadata only until HSR_HANDSHAKE.json passes local-check|
|profile|primeverse_origin|Primeverse origin / pre-M0 lookup|DM056_0; closed forward of M0; retroactive pre-M0 authoring under an explicit Corey gate|

`skt_storm` is the sole active SKT cartridge; its edge is read from the
`DM038_L dm-state-1.edge` object named by CURRENT ARC and is never restated here
(`#RULE-ONE-EDGE-OWNER`). Completed Chapters 1–9 are historical retrieval only
through `project context/TR3_SKT_ARCHIVE`.

### Court cartridge closure order

The cartridge identity remains `skt_storm`; release and corpus revision belong
in version metadata and never become a second cartridge ID. The live Court gate
closes first when Hekaton is recovered and legitimate Serissa/Hekaton authority
is restored. The later Iymrith and concurrent Thayan/Drow/Kraken fronts remain
the separate endgame convergence and do not retroactively redefine Court arrival
or rescue as a cartridge transition.

Since the 2026-08-09 semantic split, a part **parent** holds only source-route
and control tables. Read its `SEGMENT MAP` section to locate the needed shard,
then load only that shard section. A parent is a locator, not an automatic
co-load; reading it whole gets page tables and no people.

Precision adds by scene type -> DM034_1 §2B.

## POINTERS
Maintenance validation receipts append to `DM035_0e`; closed static provenance
and superseded change records remain in the locked off-corpus history shelf.
deep index -> DM034_1; current receipts -> DM035_0e; historical provenance -> project context/_history/closed-gate-history-offload-2026-09-07/; prep + simulation findings -> DM038_CH; Divineverse state -> DM038_L; operational play law + staging delta format -> DM000_4; tags -> DM034_2; SKT source router -> DM034_3; cold arcs -> DM034_0b; mutation registry -> routing-catalog.yaml editable_owners

write modes: overwrite-after-confirmed-commit · timeline-narrative-mirror-after-canon-or-play · append-only-audit-history · synchronize-from-authorities-only · tool-managed-only

<!-- Current receipts for this file -> DM035_0e; static history is off-corpus. -->

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM034_0 -->
