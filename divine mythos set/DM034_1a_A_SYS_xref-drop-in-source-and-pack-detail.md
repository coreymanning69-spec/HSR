---
id: DM034_1a
title: "XREF, Drop-In, Source, and Pack Detail"
type: sys
subtype: semantic-shard
load_priority: scalpel-by-section-via-DM034_1
canon: "ALL"
verse: "ALL"
timeline: "META"
arc: "system-organization"
status: "hard-canon"
authority: "canonical semantic shard of DM034_1"
updated: 2026-09-08
volatility: slow
arc_scope: evergreen
derived_from: DM034_1
predecessor_file: N/A
successor_file: N/A
purpose: "Owns XREF read/write rules, update routing, new-content and drop-in placement, source-world defaults, and precision-routing detail for the frozen 25-file archive."
segment_parent: DM034_1
segment_ordinal: 2
segment_count: 3
---

# DM034_1a — XREF, Drop-In, Source, and Pack Detail

> **Opening context:** This file is a self-contained architecture detail shard. DM034_1 remains the compact master index and pack-selection owner.

## SEGMENT MAP

Load only the smallest segment whose coverage matches the question. Each sibling repeats its own scope and authority context.

| ID | Covered section |
|---|---|
| DM034_1 | Master file index and compact pack selection |
| DM034_1a | XREF, Drop-In, Source, and Pack Detail |
| DM034_1b | Verification and Tooling Discipline |

## 2. XREF RULES — READ vs WRITE

All canonical files are readable when relevant; `load_priority` and the tables
below control what should actually enter context. Writes require Corey's explicit
request and the §2A verification pass.

Write behavior follows the work, not a repeated permission scalar in every file:

- **SANDBOX** is read-only.
- **FORGE** may write authored canon, live state, and play-derived mechanics to
  their owner files when Corey explicitly requests the update.
- **SCALPEL** may write maintenance, repair, schema, and routing changes anywhere
  in the canonical corpus when Corey explicitly requests them; it does not invent
  story content.

`routing-catalog.yaml` `editable_owners` is the sole machine-readable mutation
registry. Do not reintroduce local `write_modes` fields.

|mutation rule|binding behavior|
|---|---|
|`overwrite-after-confirmed-commit`|Fresh-read and replace only the owning current snapshot: DM000_2 or the persistent Divine Mythos ledger DM038_L.|
|`timeline-narrative-mirror-after-canon-or-play`|Append current prose to the open `_N#` lane — the highest-numbered one on disk, never a lane named here — and the compressed chronology mirror to DM002_3, only after canon/play binds.|
|`append-only-audit-history`|Append current receipts to DM035_0e or prep/simulation findings to DM038_CH; never overwrite history.|
|`synchronize-from-authorities-only`|Update authorities first, then rebuild DM044_0 and DM044_1 together.|
|`tool-managed-only`|Regenerate SKT source/indexes and the corpus manifest with their tools; never hand-edit them.|
|`immutable-hash-checked`|The frozen 25-file canon archive is not automatically repacked; verify its files and recorded hashes only. Replacement is an explicit manual full refresh.|

Tool-managed paths are outside direct owner editing: regenerate `storm king
texts/` with `tools/rebuild_skt_rag_sources.py`, verify the frozen 25-file pack
and its inventory with `tools/compact_pack_sync.py --check`, and rebuild
`corpus-verification-manifest.yaml` with
`tools/build_verification_manifests.py`. `storm king pdfs/` is read-only source
authority. The frozen pack is never regenerated.


### §2A — WRITE / UPDATE (verify before write)

These are verification rules, not load-lists. Before an edit lands on disk, the
editor verifies the named anchors against their authority files and records that
the check happened. Retrieval-based sessions (Claude, Opus, Codex on the full
corpus) do not need files "loaded" — they need the anchors CHECKED and a marker
left behind. Load-lists as presence rules survive only in §5, where the 25-file
ChatGPT deployment genuinely constrains what is physically available.

| When updating… | VERIFY BEFORE WRITE (anchor → authority) |
|---|---|
| **Divineverse T-Beat** (DM005_0–013, 017–019_2) | Chronology → DM002_1 for T0–T260 / DM002_3 for T260–T550.1; T260 is a shared handoff anchor · divine core continuity → DM004_1 · founders → DM004_2 · later household/staff → DM004_2b · allies/antagonists/Undermountain → DM004_2c · character law → DM028_1/2/3/3b/3c & DM030_1/2 · combat mechanics → DM027_0 (if combat) · geography/worldstate → DM031_0 |
| **Mergeverse M-Beat** (DM015–016, 020–021_2) | Chronology → DM002_2 for M0–M90 / DM002_5 for M90–M183; M90 is a shared handoff anchor · cast → DM004_3 · Primeverse baseline → DM014_1/2/3 · archived recap provenance → DM014_4 by direct/SCALPEL load only · T4 mechanics → DM022_0 · combat → DM027_0 · character law → DM028_1/2/3/3b/3c & DM030_1/2 · setting → DM032_0 |
| **Timeline Spine** (DM002_1/2/3/5) | Current T-live segment (DM002_3): current story state → DM038_L · confirmed-only continuity T516-T524 → DM038_N0 · played prose T525-T532 → DM038_N1 · played prose T533-T536 → DM038_N3 · later closed prose → the `_N#` chain, resolved by the family rule in DM034_0 rather than listed here · current receipts → DM035_0e. Closed segments: verify against the beat files they compress—repairs only, never new chronology |
| **Itinerary TR-Beat** (DM025_0–026, TR-JP, future)| Itinerary state → DM023_0 & DM024_1/2/3/4 · Sanctum people/operations → DM029_01/02 · physical/domestic Sanctum precision → owning DM029_03–07 file · geography → DM031_0 |
| **Primeverse P-Beat** (DM033_1–4) | Owning Prime beat → DM033_1/2/3/4 · Primeverse baseline → DM014_1/2/3 · T4 cast → DM022_0 |
| **Core Context** (DM001_0, DM003_0) | Character continuity → DM004_1/2/3 · T4s → DM022_0 · combat → DM027_0 · pillars → DM028_1/2/3/3b/3c · Sanctum people/operations → DM029_01/02 · Sanctum ontology/infrastructure → owning DM029_03–07 file · Sera logic → DM030_1/2 · theology architecture → DM042_0 |
| **Characters/Mechanics** (DM004_*, DM022_0, DM027_0, DM028_*, DM029_*, DM030_*, DM041_0/DM041_A/DM041_A1/DM041_B/DM041_B1/DM041_C/DM041_D/DM041_E/DM044_0/DM044_1/DM045_DS1/DM045_DS2/DM045_DS3) | Thesis → DM001_0 · axioms → DM003_0 · divine architecture → DM042_0 |
| **Worldstate/Geography** (DM031_0, DM032_0) | Spine cross-check by range → DM002_1/DM002_3 or DM002_2/DM002_5 · Sanctum infrastructure → owning DM029_03–07 file |
| **Hollow Star Reliquary** (DM046_0) | Thesis → DM001_0 · axioms → DM003_0 · divine architecture/specification → DM042_0 · level-20 sources → DM041_A/DM041_B · paired runtime → DM044_0/DM044_1 |
| **The Blessed** (DM047_0) | Divine specification/authorship law → DM042_0 §12 · member mechanics stay with owners → DM004_2b (Sunset, Vesper), DM041_A1 (Doran kit), DM041_B1 (Wren Robe/Staff/Crown), DM027_0 (Sera intrinsic) · never restat here |
| **System Architecture** (DM000_*, DM034_*) | Law & thesis → DM000_1/2/3 · DM001_0 · DM034_1/2 |
| **SKT Stable Prep** (DM038_1/6, DM038_CH) | Doctrine → DM038_1 · active storm/endgame source → DM038_6 · completed Chapters 1–9 → hashed archive inventory · prep/meta history → DM038_CH · prior giant canon → DM026_0/DM031_0 when implicated |
| **SKT Live State** (DM038_L) | All current Divineverse story state → DM038_L; Court and later arc handoffs update its keyed state instead of changing owners · receipts → DM035_0e · characterization → DM040_0 on demand · encounter runtime → DM044_0/DM044_1. Commit after the run, never mid-combat; simulations route to DM038_CH only. |
| **SKT Played Narrative** (the `_N#` chain) | Per-file ranges are in the DM034_1 §1 index, which the checker validates against disk; they are not duplicated here. Which member is open and which is last-closed follows the family rule in DM034_0 — highest-numbered is the open lane, the one below is last closed prose, `_N3` shards `_N1` and sorts before `_N2` · edge → active live ledger · mechanics → DM044_0/DM044_1 · spine mirror → DM002_3 |

**CODEX-PASS receipt (required).** A normal content or routing edit records one
current receipt in `DM035_0e`, naming what changed and what was verified. Do not
put a maintenance changelog in the edited owner file:

```text
"YYYY-MM-DD: CODEX-PASS (§2A <category>) — changed <owners>; verified <anchors checked>; anomalies: <none | logged in session report>."
```

No current receipt, no accepted structural edit. For a corpus-wide,
metadata-only schema pass, one receipt in `DM035_0e` plus a clean validator run
is sufficient; do not add the same maintenance line to every owner. Historical
receipts move to the locked off-corpus history shelf, never into active owners.


### §2B — READ / RUN (minimal load, playback and flesh-out only)

Beat content is the anchor. Load only what's routed; add precision files only if the scene type requires them. Writes follow stance: RUN forbids mid-scene edits, while an explicitly requested FORGE commit lands after the run.

**Minimum-load routes live in `DM034_0` MOUNT SETS — the sole owner.** This file
does not restate them. DM034_0 covers all named T, M, P, TR, and TR3-SKT routes;
the machine mirror is `routing-catalog.yaml` `profiles`, and
`tools/xref_checker.py` fails if the two disagree. What §2B owns is the precision
layer below.

**Precision adds — RUN only. Load if scene type requires it; skip otherwise:**

| Scene type | Add |
|---|---|
| Social / domestic | DM030_2 |
| Combat | DM030_1 + DM027_0 |
| Doran or Wren characterization | DM040_0 |
| Doran or Wren current values | DM038_L `dm-state-1` readiness object; the same domain ledger persists across arc handoffs |
| Doran or Wren runtime | Required sections from the DM044_0 + DM044_1 section maps (DM041_A/DM041_B are maintenance authorities, not active-combat loads) |
| T4 / Primeverse | DM022_0 |
| Sanctum operations | DM029_01/02 |
| Sanctum physical/domestic precision | owning DM029_03–07 file |
| Geography changes | DM031_0 (Divineverse) or DM032_0 (Mergeverse) |

## 3. NEW CONTENT & DROP-IN ROUTING

**New content** — where it goes by type:

| New content | Destination |
|---|---|
| Character entry | DM004_1 (Divine Core) / DM004_2 (founders) / DM004_2b (later household/staff) / DM004_2c (allies, antagonists, Undermountain) / DM004_3 (Merge/Prime roster) / DM022_0 (Prime system deep-dive) / DM043_0 (Suzu/Plum detail) |
| Sanctum operations canon | DM029_01 (staff/people) / DM029_03 (hardware/infrastructure) |
| Divineverse setting change | DM031_0 |
| Mergeverse/Primeverse setting change | DM032_0 |
| Primeverse seam / archaeology reconciliation | DM001_0 (cross-verse thesis) + owning DM033_1/2/3/4 file + DM014_1/2/3 + DM004_3/DM022_0 |
| New TR beats | Own TR-beat file (TR-JP cluster: TR-JP-01, -02, …) |
| New M-beats | New M-beat file named to range |
| New Prime context | Existing smallest owner in DM033_1/2/3/4; a genuinely new played range receives a new top-level P-beat file after explicit authorization |
| Played module turns (live module) | Closed or new prose → the appropriate rolling `_N#` packet resolved by the DM038 narrative-family rule + DM002 spine entry; current Divineverse state → DM038_L; current receipts → DM035_0e; source stays in active source control or the completed-chapter archive |
| Above-artifact object; Blessed-tier admission, boundary, or discriminator question | DM047_0 (permission test §1, register §5, gates §8) — register by pointer only; the object's mechanics stay in its owner file (DM004_2b / DM041_A1 / DM041_B1 / DM027_0). Authorship-side rules stay with DM042_0 §12. No admission without Corey's explicit word; surfaced candidates go to §5 unadmitted |
| Hollow Star Reliquary design/runtime contract | DM046_0; generated Sandbox runs stay outside the corpus; promoted Forge results route by verse and trace after review |

A **live module** (a D&D module run as live play, like TR3-SKT) splits across three
layers—source control, atomized live state, and timeline narrative. See §1's
"SKT module layer model." Played turns become _N narrative beats plus spine
entries; live ledgers hold state only and are never the narrative of record.

**Drop-ins** (any module, trope shell, kingdom-sim problem, travel encounter, or
original scenario brought in for play/analysis): for **load-packet selection**, use
DM000_2's Drop-In Active Load Packets. For **where the result is filed**, route:

- **Functional shell first:** before play or canonization, reduce the premise to
  verse/timeline position, scenario function, mortal stake, opposition model,
  divine interaction vector, and expected trace. Import functions, not scripts:
  a vampire domain becomes cursed isolation under a predatory immortal; a giant
  module becomes hierarchy, captive labor, and leadership deposition; a cult arc
  becomes apocalyptic faction infrastructure. Ask only for missing anchors that
  change routing: verse, location, canon status, or trace type.

- **By verse first:** Divineverse → DM002_1 (T0–T260) or DM002_3 (T260–T550.1 internal; filename T260-T533 locked) + active T-file · Mergeverse → DM002_2 (M0–M90) or DM002_5 (M90–M183) + active M-file + DM032_0 · Primeverse → DM014_1/2/3 + DM022_0 + the owning DM033_1/2/3/4 file · TR → DM023_0 + DM024 atlas + new TR file if canonized.
- **By trace second:** geography/portals/ruins → DM031_0/DM032_0 · institutions/laws/rulers → DM031_0/DM032_0 + active beat · recurring NPC/faction → relevant character matrix · new divine mechanic/law → relevant pillar file (not a beat file) · witness/relationship/domestic texture → active beat file or matrix per canon weight · one-off no-trace play → session notes unless Corey canonizes.
- **By source-world third:** named D&D/FR module in Divineverse keeps source names and module structure when useful while Divine Mythos adapts outcomes through live play · generic trope shell stores mythic/function names, not proprietary text · original scenario named/tagged once Corey confirms canon.
## 4. SOURCE-WORLD DEFAULT

Every named entity (character, location, item, deity, monster, faction) defaults to
**Dungeons & Dragons 5e / Forgotten Realms** canon unless the containing file's YAML
declares `verse: Mergeverse` or `verse: Primeverse`. Divineverse beats (T, TR)
inherit this default. Mergeverse and Primeverse beats are explicit overrides within
their own frames; the Merge is "Primeverse with the Girls in it" and uses Prime's
source-world rules unless DM031_0/DM032_0 logs a specific override.
## 5. GPT PROJECT 25-FILE COMPACT PACK

The 25-file ChatGPT upload set is a **frozen canon archive**, not a live runtime
or synchronization contract. Its 2026-08-30 contents are the current manually
refreshed Rev 8.5 baseline under
`project context/TR3_SKT_25_FILE_PACK/`; later corpus changes do not update it.

**Roster:** DM034_1 §5 owns the frozen list. `compact-pack-manifest.yaml`
records its 25 paths and hashes, and `tools/compact_pack_sync.py --check`
verifies integrity. No automatic or due-based refresh exists. A future
replacement is a deliberate full refresh through the tool with an explicit
release date; until then, these files remain untouched.

Do not infer the live edge, current mechanics, active routes, or omitted-file
coverage from that snapshot. Current work reads the canonical owners in
`divine mythos set/`; DM034_0 selects the current route, DM038_L owns the
present pre-Court edge, and DM034_3 routes the remaining DM038_6/6a/6b source
control.

The archived files are never a write target. Historical pack contents may be
quoted as snapshot evidence only and never override newer canonical owners.
- DM001_0 supplies theology, physics, failure guards, and cross-verse state anchors.
- DM004_3 carries the Prime/Merge cast in compact mode; DM033_1 supplies the
  general pack's Soliera Prime / Arden depth. DM033_2/3/4 and DM014_*/DM022_0
  precision remain outside the fixed pack unless swapped in.
- DM031_0 carries Divineverse geography; DM032_0's Merge/Prime setting changes are compressed into DM002_2/DM002_5 and DM004_3 pointers, with precision outside the pack.
- DM002_5 carries the Suzu Hikari / Plum Titan open-thread pointers in compact mode; precision lives in DM043_0 outside the pack, while DM004_3 keeps only the roster pointer.
- DM030_1 is the default Sera file for internal logic, origin, combat, and feat scale. DM030_2 is an optional swap for social aura, Sanctum, relationships, humor, and quote-bank precision.
- DM042_0 has no slot in this 25-file pack by default; its architecture is folded into DM001_0,
  DM004_1, DM028_1/2/3, DM029_03, and DM030_1 so the recursive five-point star, YHWH
  positions, relational metamorphosis circles, literal Metatron layer, distributed YUIUM,
  Soliera awareness/consent boundaries, Veiled Eye ownership, Deashi display-versus-pruning,
  and body-mechanics-as-theology remain available in compact mode.
- DM034_3 routes source doctrine, the smallest active DM038 source-control part,
  current-story precision in the active live ledger, and other SKT
  owners only when the question needs them.
- DM041_A/B and DM041_A1/B1 remain maintenance-only outside the fixed 25-file
  pack. DM040_0 supplies compact characterization; DM044_0 plus DM044_1 are the
  additional runtime for combat initiative or explicit simulation.

**Precision routing (when a session needs more than the compact set).** These are
load choices against the canonical owners in `divine mythos set/`. The frozen
archive is never recomposed, swapped, or restored:
- Sera social/dialogue-heavy: load DM030_2 instead of DM030_1.
- Exact completed prose or split-child precision: load the target owner directly.
- TR3-SKT source lookup or story review: let DM034_3 select one DM038 source or
  state owner; never infer the active chapter from a filename or old session.
- TR3-SKT continue/resume: follow DM034_0 CURRENT ARC to DM038_L, then read
  `DM038_L dm-state-1.edge`. DM038_L is the persistent Divine Mythos state
  owner; an arc handoff updates its structured keys rather
  than changing ledger files. Closed prose lives in the `_N#` chain and the open lane is its
  highest-numbered member — resolve both by the DM034_0 family rule, never from
  a lane named in prose; DM040_0 supplies characterization.
- TR3-SKT combat or explicit simulation: add DM044_0 + DM044_1 before the first
  resolution and use their section maps to retrieve only the required protocol,
  recruit, and enemy sections. DM041_A/B/A1/B1 remain off-load unless maintaining
  or rebuilding the runtime.

**Operating rule:** Omitted beat files are not lost canon — treat them as compressed
into the DM002 spines, DM001_0, DM031_0/DM032_0, and the character references. Flag
uncertainty only when the user asks for exact wording, line-level evidence, or scene
detail not represented in the loaded pack. File-cap mode changes retrieval behavior,
not canon: the DM000_3 gates and DM003_0 axioms always govern output.

**Owner-plus-inference rule:** Do not mirror an authority merely to make a leaf
file self-contained. Load the smallest owner, apply its global rules, and infer
ordinary connective tissue or small consequences in the moment. Corpus storage
is reserved for irreducible facts: details whose omission could change canon,
chronology, consent, routing, mechanics, or a proper noun. A deduction that can
be reproduced quickly from the owners is not corpus content.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM034_1a — architecture detail shard -->
