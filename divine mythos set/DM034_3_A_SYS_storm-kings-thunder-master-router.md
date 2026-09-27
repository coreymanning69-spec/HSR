---
id: DM034_3
title: "Storm King's Thunder Master Router"
type: sys
subtype: module-source-router
load_priority: section-query-only-on-explicit-SKT-source-navigation
canon: ALL
verse: Divineverse
timeline: META
arc: system-organization
status: hard-canon
authority: authoritative-for-SKT-source-and-runtime-retrieval-routing
updated: 2026-09-07
volatility: slow
arc_scope: storm-kings-thunder
derived_from: null
predecessor_file: N/A
successor_file: N/A

scope:
  covers:
    - exact routing to the 122 compact SKT source segments
    - current Storm/endgame state, narrative, mechanics, and write targets
    - archive-level historical retrieval for completed Chapters 1–9
  use_case: query one routing section on an explicit SKT source-navigation need; continue/resume follows DM034_0 CURRENT ARC to DM038_L, whose dm-state-1.edge owns the value
  not_for:
    - unrelated requests
    - bulk-loading source segments or retired chapter controls

xref_concepts:
  - storm-kings-thunder
  - conditional-module-routing
  - source-segment-index
  - storm-court-endgame

purpose: >
  Row-addressable router for the remaining active Storm King's Thunder family.
  Chapters 1–9 are historical evidence; DM038_6/6a/6b is the sole active
  module-control route.

ai_directives:
  - continue or resume follows DM034_0 CURRENT ARC to DM038_L, then reads dm-state-1.edge
  - query one exact router row, owner section, or source-index row
  - source files supply module facts only; DM038 files own Divineverse state and played outcomes
  - never use retired Chapters 1–9 control as an active cartridge or continuation route
---

# DM034_3 — STORM KING'S THUNDER MASTER ROUTER

## Trigger Gate

| Request state | Load |
|---|---|
| Explicitly mentions SKT source material | Query the matching row here, then retrieve one smallest owner/source section |
| Continue/resume at the current edge | DM034_0 CURRENT ARC → `DM038_L dm-state-1.edge`; query this router only if source navigation becomes necessary |
| Unrelated request | Do not load this router or SKT source |

## Active Owner Map

| Need | Owner |
|---|---|
| Doctrine and completed-chapter traceability | DM038_1 / DM038_1b / DM038_1c / DM038_1d |
| Chapters 10–12 and appendices | DM038_6; section-route to DM038_6a or DM038_6b below |
| Current Divineverse edge, no-preauthoring gate, active route, exact readiness, durable regional resolution, and open fronts | DM038_L structured state |
| Court/endgame story after the played handoff | DM038_L; update its keyed arc state after confirmed play rather than changing ledger owners |
| Goldenfields close and departure prose | DM038_N6 |
| Older played prose | Exact DM038_N0/N1/N2/N3/N4/N5 section |
| Approved prep decisions and non-canon simulation findings | DM038_CH |
| Combat or explicit simulation | Exact DM044_0 and DM044_1 sections plus one enemy block |
| Eclavdra operation state/runtime | DM050_0 / DM045_DS3 |
| Champion roster | DM051_0 |

## Segment Key Disambiguation (Rev 8.5, 2026-08-23)

**The `NN_qNN` key is not unique.** Chapters 9, 10 and 11 are each split across two
PDFs, and the `q` counter restarts at `q01` in the second part. Eleven keys
therefore name two different segments each, distinguished only by page range. The eight
active-endgame keys are tabled below; the three archived-tier keys
follow in their own table.

Two offsets stack on top of that, and both are easy to trip on:

- **The leading number is the PDF file number, not the chapter number.**
  `11_` is Chapter 10. `12_` is Chapter 11. `13_` is Chapter 12.
- **The page numbers in the filename are PDF pages, not book pages.** The
  segment header carries both. Verified at `chapter_10_1-q01`:
  `pdf-pages=202-203` is `book-pages=201-202`, an offset of -1. Treat -1 as the
  working offset and confirm against the segment's own header comment before
  citing a book page in prep or play.

### Collision table - resolve by page range, never by key alone

| Key | PDF pages | Resolves to | Book pages (-1) |
|---|---|---|---|
| `11_q01` | p202-203 | Ch. 10 *Hold of the Storm Giants* - Part 1 of 2, seg 1/4 | 201-202 |
| `11_q01` | p209-210 | Ch. 10 - **Part 2 of 2**, seg 1/4 | 208-209 |
| `11_q02` | p204-205 | Ch. 10 - Part 1 of 2, seg 2/4 | 203-204 |
| `11_q02` | p211-212 | Ch. 10 - **Part 2 of 2**, seg 2/4 | 210-211 |
| `11_q03` | p206-207 | Ch. 10 - Part 1 of 2, seg 3/4 | 205-206 |
| `11_q03` | p213-214 | Ch. 10 - **Part 2 of 2**, seg 3/4 | 212-213 |
| `11_q04` | p208-208 | Ch. 10 - Part 1 of 2, seg 4/4 | 207 |
| `11_q04` | p215-215 | Ch. 10 - **Part 2 of 2**, seg 4/4 | 214 |
| `12_q01` | p216-217 | Ch. 11 *Caught in the Tentacles* - Part 1 of 2, seg 1/4 | 215-216 |
| `12_q01` | p221-222 | Ch. 11 - **Part 2 of 2**, seg 1/4 | 220-221 |
| `12_q02` | p218-218 | Ch. 11 - Part 1 of 2, seg 2/4 | 217 |
| `12_q02` | p223-223 | Ch. 11 - **Part 2 of 2**, seg 2/4 | 222 |
| `12_q03` | p219-219 | Ch. 11 - Part 1 of 2, seg 3/4 | 218 |
| `12_q03` | p224-224 | Ch. 11 - **Part 2 of 2**, seg 3/4 | 223 |
| `12_q04` | p220-220 | Ch. 11 - Part 1 of 2, seg 4/4 | 219 |
| `12_q04` | p225-225 | Ch. 11 - **Part 2 of 2**, seg 4/4 | 224 |

### Archived-tier collisions — Chapter 9 (Rev 8.75, 2026-09-05)

Chapter 9 is also split across two PDFs under prefix `10_`, so its `q` counter
restarts the same way. These keys sit in the archived-evidence tier (PDF pages
1–201), not the active endgame. The citation rule above applies to them
unchanged.

| Key | PDF pages | Resolves to | Book pages (-1) |
|---|---|---|---|
| `10_q02` | p190-191 | Ch. 9 *Castle of the Cloud Giants* — Part 1 of 2, seg 2/4 | 189-190 |
| `10_q03` | p192-193 | Ch. 9 — Part 1 of 2, seg 3/4 | 191-192 |
| `10_q04` | p194-194 | Ch. 9 — Part 1 of 2, seg 4/4 | 193 |
| `10_q01` | p195-196 | Ch. 9 — **Part 2 of 2**, seg 1/4 | 194-195 |
| `10_q02` | p197-198 | Ch. 9 — **Part 2 of 2**, seg 2/4 | 196-197 |
| `10_q03` | p199-200 | Ch. 9 — **Part 2 of 2**, seg 3/4 | 198-199 |
| `10_q04` | p201-201 | Ch. 9 — **Part 2 of 2**, seg 4/4 | 200 |

Part 1 seg 1/4 (`10_q01`, expected p188-189) is not present on the project
mount. Confirm against `storm king texts/` and add its row if it exists there.

### Non-colliding active segments

Single-part PDFs; the key is unique and safe to cite alone.

| Prefix | Material | PDF pages | Keys |
|---|---|---:|---|
| `13_` | Ch. 12 *Doom of the Desert* | 226-231 | q01-q04 |
| `14_` | Appendix A - Linked Adventures | 232-233 | q01-q02 |
| `15_` | Appendix B - Magic Items | 234-240 | q01-q04 |
| `16_` | Appendix C - Creatures | 241-247 | q01-q04 |
| `17_` | Appendix D - Special NPCs | 248-257 | q01-q04 |

**Citation rule.** A source citation names the key *and* the page range -
`11_q02 p211-212` - or the header id, which is already unambiguous
(`skt-source-chapter_10_2-q02`). A bare `11_q02` is not a citation. Prefer the
header id where one is to hand.

## Storm/Endgame Section Routing

`skt_storm` is the sole active cartridge and its mount set is owned by DM034_0
MOUNT SETS. Load DM038_L, then only the source-local section needed from this
family. After a played Court handoff, the `tr3_skt_court` profile still loads
DM038_L; the handoff updates that domain ledger's keyed arc state.

| Question | Owner |
|---|---|
| source pages, Maelstrom location control, endgame control | DM038_6 |
| storm-court NPCs, creatures, factions, plot-critical items, scene scaffolding | DM038_6a |
| voices, character lenses, Kraken Society flow | DM038_6b |

DM038_L owns the current route and play boundary. This router supplies only
source-local detail; exact site geometry and discoveries remain for play.

## Completed Chapters 1–9 Archive

The former control owners are preserved under
`project context/TR3_SKT_ARCHIVE/chapters-01-09/`. Its `INVENTORY.json` records
exact filenames, retired identifiers, and SHA-256 hashes. The inventory is the
archive registry; no retired identifier is part of current routing.

Generated source evidence stays in `storm king texts/`: PDF pages 1–201 are
archived evidence and pages 202–257 remain active. Query one `index.md` row or
one `_index.jsonl` record, then retrieve one segment.

| Prefix | Material | PDF pages | Scope / route |
|---|---|---:|---|
| 00–10 | Front matter through Chapter 9 | 1–201 | archived evidence; completed-leg facts only |
| 11–17 | Chapters 10–12 and appendices | 202–257 | active; DM038_6/6a/6b |

## Runtime and Write Routes

| Situation | Read route | Write route |
|---|---|---|
| Continue current play | DM034_0 CURRENT ARC → `DM038_L dm-state-1.edge` + one exact local section | current Divineverse state → DM038_L; prose → rolling `_N#` owner; spine mirror → DM002_3 |
| Story review | active live ledger + exact narrative/owner section | owning file only |
| Initiative/live combat | DM038_L structured readiness + exact DM044_0/1 sections + one enemy block | current story state → DM038_L; receipts → DM035_0e |
| Explicit simulation | exact DM044_0/1 sections + declared fixture | findings → DM038_CH; never live state |
| Source lookup | one source-index row + one segment | source layer remains tool-managed |
| Completed Chapters 1–9 lookup | archive inventory + one archived file/section | no active-state write from archive evidence alone |

Played prose mirrors one compressed line into DM002_3. Source facts and archived
control never overwrite Divineverse outcomes.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM034_3 -->
