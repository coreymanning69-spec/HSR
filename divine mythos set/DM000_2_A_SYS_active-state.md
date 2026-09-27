---
id: DM000_2
title: "Active State — Current Threads & Dictation"
type: sys
subtype: active-state
load_priority: forge-only
canon: ALL
verse: ALL
timeline: META
arc: active-session-state
era: current-live-edge
status: hard-canon
authority: session-context
rag_optimized: false
updated: 2026-09-09
volatility: volatile
arc_scope: evergreen
derived_from: null
predecessor_file: DM000_1
successor_file: DM034_0

scope:
  covers:
    - current continuation point and active thread state
    - active load packets and compact-pack routing
    - unresolved play-gated decisions
  use_case: load for FORGE and current-state work
  not_for: universal law (use DM000_1), cold-load routing (use DM034_0), deep index (use DM034_1), or exact played prose (use the owning beat file)

xref_concepts:
  - active-state
  - forge-only-load
  - current-narrative-threads
  - dictation-autocorrect
  - session-context
  - beat-namespace-overview
  - behavioral-guardrails
  - canon-thread-tracking
  - sandbox-drop-in-system
  - active-play-load-packet

purpose: >
  Active session context. Loads for FORGE and current-state work only.
  Contains current narrative threads, dictation autocorrect, and behavioral guardrails.
  Defines active load packet selection for drop-in sandbox play.
  Updated as canon evolves.
---


# DM000_2 — ACTIVE STATE

## ACTIVE-STATE SECTION MAP

Load only the row that matches the task. Add the single relevant `PACKET 4`
line only when a character or mechanic becomes load-bearing.

**Resume does not come through this file.** `DM034_0` BOOT SEQUENCE carries the
CURRENT ARC line, so `continue` / `resume` reaches DM038_L directly. Open
DM000_2 for dictation repair, a drop-in, or a non-current thread — not to read a
pointer.

| Need | Retrieve |
|---|---|
| Continue/resume current play | nothing here — `DM034_0` CURRENT ARC → DM038_L |
| Start initiative | `DM044_0 §0` seed gate — it owns the ritual |
| Find a non-current verse/thread | `HOW TO READ THIS PROJECT` + the matching packet only |
| Track Primeverse or Hollow Star status | matching entry under `CURRENT STATE` only |
| Inspect frozen project-pack membership | `GPT PROJECT 25-FILE FROZEN PACK` only |
| Canon/write maintenance | `FILE ARCHITECTURE` + the exact `CURRENT STATE` thread |
| Dictation repair | `DICTATION AUTOCORRECT` only |

Do not load this file whole merely because FORGE mode is active.

**This file states no edge value.** Rev 8.5.2 removed the three restatements
that lived here; all had drifted stale. `DM034_0` CURRENT ARC selects the active
ledger; `DM038_L dm-state-1.edge` owns the Divine edge value.


## HOW TO READ THIS PROJECT

Four beat namespaces. NEVER conflate them.

- **T-beats** — Divineverse main line.
- **M-beats** — Mergeverse.
- **P-beats** — Primeverse.
- **TR-beats** — Travel Arc / Itinerary, numbered `TR1`, `TR2`, `TR-JP-nn`.

**`TR3-SKT` is a label, not a beat namespace.** Storm King's Thunder was slotted
as the third travel record and kept the name, but it is played as a Divineverse
module and every one of its beats is T-numbered (T525 onward). Write `T537`, not
`TR3-03`. The machine-readable arc-id is `storm-kings-thunder`.

Beat ranges per arc are in DM034_0's ARC REGISTRY; which file owns which range is
in DM034_1 §1. Neither list is repeated here.

Search project knowledge BEFORE asking questions. Reference line ranges when citing files. Search by character name + scene content/action for best retrieval — outperforms beat ID searches alone.


## DROP-IN ACTIVE LOAD PACKETS

Use this section when a sandbox premise becomes playable or canon-candidate material. The goal is to load enough context to infer correctly without dragging the whole corpus into every scene.

**PACKET 0: Core Cold Load** — owned by the project instruction layer and
`DM034_0` BOOT SEQUENCE. Not restated here. Add DM001_0 only for SANDBOX
premise, trope-conversion, or project-thesis work.

**PACKET 1: Active Drop-In Load** — Packet 0 plus the matching section-map row
at the top of this file. Use when picking up a live thread or deciding where a
drop-in attaches. DM003_0 is an on-demand world-physics owner, not a FORGE
co-load.

**PACKET 2: Verse/Timeline Load**
- Divineverse before Merge: add DM002_1
- Divineverse after Return / post-Strahd: add DM002_3
- Mergeverse or Travel Records: add DM002_2
- Primeverse: add DM014_1/2/3 + DM022_0, then the smallest owning Prime beat:
  DM033_1 (Soliera Prime/Arden), DM033_2 (ensemble), DM033_3 (world systems),
  or DM033_4 (power/timeline)

**PACKET 3: Route Load**

Route load sets are owned by `DM034_0` MOUNT SETS. They are not restated here.
This packet carries only the cross-arc trigger and pointer for the **current**
arc:

Rev 8.5.2 removed this packet's arc line. It had been registered as the
deliberate second half of a two-place pair; in practice the pair became five
places and three went stale within a day of play. One owner, no mirrors.

- To route the current arc: read `DM034_0` CURRENT ARC, then the matching
  `DM034_0` MOUNT SETS row. Never create or route to a separate live-edge alias.
  For a local SKT source, query one DM034_3 row and retrieve one compact source
  or owner section; never load the 122-file source layer or either index whole.

**PACKET 4: Character/Mechanic Load**
- Retrieve the exact relevant section from DM004_1 (Divineverse divine core), DM004_2 (founding Sanctum inner
  circle), DM004_2b (later Sanctum household/staff, Taliandra, and
  Doran/Wren/Writ Six routing), DM004_2c (Divineverse allies, antagonists,
  deity avatars, module cast, and Undermountain companions), and
  DM004_3 (Primeverse/Mergeverse cast) for cast behavior as needed.
- Retrieve only the owning section from DM028_1/2, DM028_3/3b/3c, or
  DM030_1/DM030_2 when divine-pillar precision becomes necessary.
- Retrieve the exact DM027_0 section only if 5e combat translation matters.
- Outside combat, the active live ledger leads. Retrieve its readiness section for current numbers and
  `DM040_0` only for a compact-characterization question.
  Add DM041_0 only for deep biography, relationship, training, or
  historical-launch precision.
- **Combat and simulation seeding is owned by `DM044_0 §0`.** Follow it; it is
  not restated here or in any other file. Off-load list, fail-closed rule, and
  the LIVE/SIMULATION split all live there. Later fights in the same thread seed
  from the round-one snapshot plus the STAGING DELTA, not a fresh read.
- Add DM029_01/02 when Sanctum staff, hierarchy, or institutional operations are
  load-bearing. Add the owning DM029_03–07 file when Sanctum ontology, physical
  structure, infrastructure instances, horror/comfort, or domestic operations
  are load-bearing.

**Drop-In Routing Question:** Before running a new drop-in, answer these four items silently or explicitly:
- Which verse owns it: T, M, P, or TR?
- Is it a canon module, a generic trope shell, or an original scenario?
- What trace will remain after the girls pass through: worldstate, witness-state, relationship-state, institutional-state, domestic texture, or non-canon table-play?
- Which file receives the result under DM034_1 routing?


## GPT PROJECT 25-FILE FROZEN PACK

DM034_1 §5 owns the frozen archive inventory, coverage map, and precision
routing. The 25-file set is a manually refreshed frozen baseline for casual
ChatGPT Project context, not a live pack: never infer the live edge from it. It
remains untouched until Corey explicitly runs a deliberate full refresh. Load
only when file-cap behavior matters.


## FILE ARCHITECTURE

DM034_1 §1 owns the file index, split-file routing, retired IDs, timeline split,
and beat-system definitions. Do not duplicate the index here.


## CURRENT STATE

### SESSION PACKET - 2026-07-05
- DM038_1: duplicate External Forces section removed (orphan draft deleted); expanded version is sole authority.
- DM013_0: continuation label patched to "(Gate to Tavern Threshold)".
- DM041_0 checkpoint: Doran launched as Battle Master Fighter 13 with 267 HP.
  From T537.0, Doran and Wren are full Tier-3 field Stewards at their settled
  level-20 values in DM038_L; DM041_A and DM041_B own source mechanics, and
  every combat or simulation loads DM044_0 plus DM044_1 together. Doran retains
  five languages; T536 establishes Undercommon as Wren's seventh language
  without retiring one.
- Historical corpus health scan: 119 files, clean (reading recorded 2026-07-05).
  Current live corpus after the authorized atomization: 118 files; certification
  is recorded in the 2026-07-27 SCALPEL completion report.
  Current live-corpus release identity: **V8**.


**TR-JP Namespace — Japan Arc (arc CLOSED 2026-06-20):**
New naming convention: TR-JP-01, TR-JP-02, etc. Region prefix locks the Japan cluster.
- DM039_0 owns hard-canon scene detail for TR-JP-01 through TR-JP-05 plus Hisako's parallel POV.
- The compiled arc includes shrine arrival, the Tachibana household, the garden, and Suzu Hikari's cold open. The café sketch is hypothetical and unplayed; Suzu and the Girls have not met.
- Tachibana family (TR-JP): Kiyuru (eldest son, artifact-line custodian), Hisako (shrine matriarch), Tsubaki (daughter), Chiyo (grandmother ~90, sharp, "hears the trees"), Tachibana Sōjirō (late father / previous custodian, returned by the accepted resurrection offer).
- Post-arc status: Hisako's family accepted the resurrection offer and Tachibana Sōjirō returned. The Amagatsu Initiative, Hakubai / 白梅, facility transport, and the café threshold through Soliera's entrance are established. Kiyuru carries Kusanagi + Yata no Kagami. The Emperor continuously wears Yasakani no Magatama at his shrine; while worn it can extend life for centuries or millennia. Japan's correct belief in the Emperor as a demigod gives him substantial personal strength.
- The Japan universe continues while the camera is elsewhere. Suzu remains active with Hakubai, fighting and training; she and Kiyuru and other Japan-hub figures communicate. The wider T4 community is increasingly aware of the Girls, and the transformed Oak City contact is publicly known as the **Oak City Experiment**. These are continuing-world facts, not a resumed TR-JP scene.
- Do not resume TR-JP unless Corey explicitly routes back. On return, fresh-read the
  current Japan/Mergeverse owners and allow elapsed time, personality development,
  institutional awareness, and Sanctum-technology diffusion to matter; do not freeze
  the region at the departure snapshot or pre-author exact changes. Current continuation
  is owned by `DM034_0` CURRENT ARC.

### THREAD 2: Mergeverse Prose Expansion (M181+)
- M180: Full prose compiled (2026-06-20) into DM021_2. Executive J and Kiyuru receive the Leviathan closure from the Japan hub. "The world is quieter than it was." Cassian's margin note: "There is no ceiling." J: "Win." Letter thread opens.
- M181: Full prose compiled (2026-06-20) into DM021_2. Letha & Veyren, first night. Partnership grammar established — casual but valued, not worship.
- M182: Full prose compiled (2026-06-20) into DM021_2. Dressing ritual, breakfast, Sera's outfit reveal ("edible"), Letha dusky-bronze blush, Veyren chokes on coffee, Cassian: "Breathe. Breathe slower." Regeneration shelf-life thread planted (hand-to-shoulder, Cassian files it).
- M183: The Japanese flag. Kiyuru's letter surfaces from Velin's notebook at breakfast. Lands on top of the night Veyren is still processing. Locked as the bridge into TR-JP; TR-JP-01 begins after M183.3.


- **Non-current thread status.** The current arc, its edge, its live ledger, and
  its open narrative lane are **not recorded here** — route through `DM034_0`
  CURRENT ARC, then read `DM038_L dm-state-1.edge`.
  Receipts are DM035_0e. TR-JP remains CLOSED (2026-06-20). M180-M182
  are authorized reconstruction prose in DM021_2; M183 is the locked handoff
  to TR-JP; and TR-JP-01 through TR-JP-05 plus Hisako's parallel POV are in
  DM039_0.

### THREAD 3: Primeverse (Parallel Development)
- Base: Outpost Seven. Soliera Prime age 18.
- Veris and Prime friendship developing (poolside, proximity increasing).
- Japan hub established (Meiji-era aesthetic, Shinto framework).
- Executive J and Kiyuru introduced. Gable (America's T4) introduced.
- Arden and Sera have not met. The standoff is a future possibility, not an active
  unresolved scene; do not imply contact, detection, or an exit protocol.
- The first meeting between Primeverse and Divine girls has not happened. Keep it
  as a future milestone only; no pre-meeting reactions are canon.

### PROJECT TRACKER: Hollow Star Reliquary

- Owner: DM046_0. This section tracks status only and does not duplicate the
  framework, room logic, runtime rules, or promotion contract.
- The generated snapshot and schema-2 handshake bind the source-derived
  runtime to the approved desktop workspace.
- Hollow Star Sandbox and Hollow Star Forge are executable under their
  isolation contracts; Forge requires explicit intent and remains review-only.
- Sandbox results create no chronology, inventory, relationship, or worldstate
  trace. Promotion requires the explicit DM046_0 process.

### THREAD 4: V8 REREAD / FOUNDING-CORPUS RESTORATION

- V8 records the live reread deltas plus a full standardization pass. Its purpose
  is to restore small played details lost when the original corpus was built under
  approximately 128k-token context limits.
- T0–T40 has been examined. T36–T40 are locked at the current local-source
  resolution without inventing missing scene prose.
- T0–T50 is approximately 10:1 compressed. Restore warmth and witness-interiority
  alongside horror whenever an early summary beat is expanded.
- Four canonical POV renders are registered but their verbatim prose was not in
  the supplied delta: Letha T19–T21; Letha T27–T31; Korin T27–T31; Taliandra
  pre-T34 through T35. Preserve the registry; do not reconstruct the prose.
- Taliandra restoration is high priority. The future `[TALI-TRACK]` layer records
  what she is doing while the main camera is elsewhere from T35–T50. Governing
  thesis: the household's cruelty is legible to her; its kindness is not; kneeling
  is fluency, not degradation.
- **SETTLED 2026-08-03:** external-IP shorthand is translated to plain functional
  description. An annotation must be readable without knowing the outside work it
  pointed at — describe the quality or behaviour, not the reference. Applied
  corpus-wide in the same pass; write new annotations this way and do not
  reintroduce the shorthand.

### OPEN THREADS REGISTRY

There is no separate numeric open-thread registry. Open status belongs in the
owning file and must be typed: active, dormant, future-optional, or closed. Do
not quote a global item count or rely on an unowned companion file. Historical
forward hooks may remain as routing notes, but they are not automatically live
threads.

### COMPLETED ARCS
- T0–T515: HotDQ, Rise of Tiamat, Thayan Arc, Descent into Avernus, Curse of Strahd — ALL COMPLETE
- TR1 Luskan — COMPLETE
- TR2 Against the Giants G1/G2/G3 — COMPLETE
- TR-JP — arc CLOSED (2026-06-20). Exit beat: Ember wanted home → Soliera teleported the party. Casual goodbye to Kiyuru.

## WHAT NOT TO DO

- Don't create anti-feats. If data doesn't show a limitation, one doesn't exist.
- Don't voice Soliera or Deashi.
- Don't ask for confirmation on direct corrections. Apply them.
- Don't rehash information more than twice in the same reply.
- Don't fall into cycles of agreeing.
- Don't use Soliera's speech casually in narration. Her words are system commands.
- Don't treat the Merge as a bleed-over. It is: Primeverse → Merge ← Divineverse.
- Don't conflate T-beats, M-beats, P-beats, and TR-beats.
- Don't pad responses with summary recaps Corey didn't ask for.
- Don't soften Sera's violence or add moral hesitation she doesn't have.
- Don't give Sera goals, introspection, or growth arcs. She is content. Utterly.
- Don't flatten Primeverse T4s into Divineverse power logic. Different ontology.
- Don't give nameless characters names. People don't receive names until the girls know them.
- Don't restate the current arc or edge in this file. Route selection is
  `DM034_0` CURRENT ARC; the Divine edge value lives once in `DM038_L`.
- Don't assume Ember governs Sera through authority. Her presence — innocence and curiosity modulate the stronger through the weaker.


## DICTATION AUTOCORRECT

**Owner.** The live autocorrect registry is **session-memory resident**, not
stored here. Memory holds the volatile half — the running cast and location
substitutions that accumulate in play. This section is the disk-side anchor
`DM000_3` points at: it names where the live entries live and carries only the
durable rules that must survive a memory reset. Treat memory as the working
registry and this section as the floor beneath it.

**Cast.** `DM000_3` HARD CANON SPELLING LOCK owns the nine locked names and the
SERRA negative lock. Not repeated here.

**Locations and proper nouns.** Corpus spelling governs and the owning file wins
over the phonetic guess. Frequent dictation targets: Menzoberranzan, Ironslag,
Bryn Shander, Soliere-Dzan, Zaltember, Blackstaff Tower, Waterdeep, Maegera,
Vajra Safahr, Taliandra Zauviir, Xorlarrin. Never coin a proper noun from a
phonetic miss — resolve to an existing name or stop.

**Accent.** Corey drafts by voice in a Southern North Carolina accent. Dropped
final consonants, merged vowels, and clauses run together are accent artifacts,
not new names or new canon.

**Parse rules.**
- **Second version wins.** When a clause is restarted, the later phrasing is the
  intended one. Discard the abandoned start without comment.
- **"and stuff / whatever"** is shorthand for connective tissue Corey does not
  intend to dictate — infer it (`DM000_1` OUTPUT & COLLABORATION LAW).
- **Bryn is a place, never a person.** `Bryn` resolves to Bryn Shander or
  Brynwater-Taltree. A dictated "Bryn" that plainly means a person is **Wren**;
  if the clause does not make that plain, it is a stop, not a silent correction.

Escalation is unchanged: `DM000_3` DICTATION ARTIFACT PROTOCOL owns the
silent-correction list, the Detection Standard, and the stop-and-flag response.


<!-- CORPUS REVISION: 9.0 -->

<!-- END DM000_2 -->
