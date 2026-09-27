---
id: DM004_3
title: "Character Matrix — Primeverse & Mergeverse Cast (M/P-Beat Era)"
type: synthesis
subtype: character-database
load_priority: load-after-DM004_2c
canon: M+P
verse: Mergeverse + Primeverse
timeline: M0–M182+ / P-beats
beat_range: M0–M182+ / P-reference
arc: character-reference
era: m-beat-p-beat-cast
status: hard-canon
authority: authoritative-for-mergeverse-primeverse-roster-identity-and-owner-routing
updated: 2026-09-07
volatility: slow
arc_scope: evergreen
derived_from: null
predecessor_file: DM004_2c
successor_file: N/A
scope:
  covers:
    - primeverse_cast        # Soliera Prime, Veris, Arden, Varn, Evan, Cassian (P), Veyren (P)
    - primeverse_institutional   # Executive J, Kiyuru, compact Suzu pointer, Gable, Jefferson, Adaela
    - mergeverse_cast        # Cassian, Veyren, Axel, Mara, Class 1C, Executive F, Dana
    - amara_arc              # Amara Windbreaker (M0–M14x companion)
  use_case: compact first lookup for Primeverse and Mergeverse character metadata
  not_for: Divineverse core, Divineverse inner circle, or Tier 4 mechanical depth
  applies_to:
    - Mergeverse
    - Primeverse
  distinct_from:
    DM004_1: "DM004_1 = Divineverse Divine Core cast (T-beat era, Tier 1: Yuium, Soliera, Deashi, Sera, Ember, Niv-Saiffar)."
    DM004_2: "DM004_2 family = Divineverse founding core, later household/staff, and allies/antagonists/Undermountain state."
    DM022_0: "DM022_0 = Primeverse Character Matrix (Tier 4 / Japan hub deep)."
    DM033: "DM033 = Soliera Prime / Arden (Primeverse-pre-Merge deep)."
    DM043_0: "DM043_0 = sole detailed Suzu/Plum characterization, mechanics, consent-state, naming, staging, and entry-method authority."
    DM043_D1: "DM043_D1 = Kiyuru's sole detailed champion runtime and called-strike authority."


xref_concepts:
  - character-metadata
  - tier-classification
  - canon-affiliation
  - role-taxonomy
  - relationship-graph
  - load-bearing-per-character
  - cassian-witness-protocol
  - veyren-calibration-lag
  - pending-codification
  - amara-full-entry
  - eight-chickens-named
  - kiyuru-artifact-carry
  - suzu-hikari
  - plum-titan
  - axel-ryder-probability-field
  - primeverse-cast
  - mergeverse-cast
  - soliera-prime
  - evan
  - arden
  - veris
  - cassian
  - veyren
  - varn
  - company-institution
  - church-institution
  - m-beat-characters
  - p-beat-characters
  - t4-characters
  - belief-intent-cast
  - countersign-divide
  - gravemaker-doctrine
  - veris-biothermal-regulation


purpose: |
  Primeverse and Mergeverse half of the DM004 split. Master character index and
  quick-reference matrix for all M-beat and P-beat era cast members.

  When you need to know a character exists, where they sit in the tier system,
  which canon they belong to, who they're tied to — this is the file. Deep-dive
  files (DM022_0, DM033) handle personality, psychology, and full arc data. Amara's witness record is archived in DM015_3 appendix.

  Authority: compact character existence, canon membership, tier, role,
  relationship, and owner-routing data is arbitrated here. Dedicated sheets
  control their detailed subjects; DM043_0 is the sole detailed Suzu/Plum owner.

ai_directives:
  - LOAD-AFTER-DM004_2c
  - AUTHORITATIVE-FOR-MERGEVERSE-PRIMEVERSE-CHARACTER-METADATA
  - DEFER-TO-DM022_0-DM033-FOR-SYSTEM-AND-PRIMEVERSE-DEEP-DIVE
  - DEFER-TO-DM043_0-FOR-ALL-DETAILED-SUZU-AND-PLUM-FACTS
  - DEFER-TO-DM043_D1-FOR-ALL-KIYURU-RUNTIME-AND-CALLED-STRIKE-FACTS
  - USE-AS-FIRST-LOOKUP-WHEN-M-OR-P-BEAT-CHARACTER-NAME-APPEARS
  - NEVER-INFER-CHARACTER-DATA-WHEN-MISSING-FLAG-INSTEAD

open_threads_forward:
  - Amara Windbreaker witness record complete — archived in DM015_3 appendix (2026-05-10)
  - Eight chickens are named situationally by Ember; no fixed roster is required
  - Kiyuru artifact carry (cross-reference DM022_0)
  - Primeverse cast cross-reference audit (DM004_2 vs DM022_0 metadata parity)
---

## SEGMENT MAP

Load only the smallest segment whose coverage matches the question. Each sibling repeats its own scope and authority context.

| ID | Covered section |
|---|---|
| DM004_3 | Continuation |
| DM004_3a | Character Matrix Primeverse & Mergeverse — Part 2 |

## Continuation


## MASTER CHARACTER INDEX TAGS (M/P-BEAT CAST)

[PRIMEVERSE CORE]
#CHAR-SOLIERA-PRIME #CHAR-ARDEN #CHAR-VERIS #CHAR-VARN #CHAR-EVAN

[MERGEVERSE / HIGH-TIER CONTACTS]
#CHAR-CASSIAN #CHAR-VEYREN #CHAR-AXEL #CHAR-AXEL-RYDER #CHAR-EXECUTIVE-F #CHAR-EXECUTIVE-J
#CHAR-COMMANDER-BUCKY #CHAR-AMARA-WINDBREAKER #CHAR-GABLE

[CADET CLASS / INSTITUTIONAL]
#CHAR-MARA #CHAR-DARIO #CHAR-TERRAN #CHAR-SABLE
#CHAR-JEFFERSON #CHAR-ADAELA #CHAR-KIYURU #CHAR-SUZU-HIKARI #CHAR-DANA

## IMMUTABLE CHARACTER PARSING RULES

[BEHAVIORAL GUARDRAILS]
#RULE-NO-GENRE-INFERENCE: Do not invent missing details based on standard trope logic. If a motivation isn't written, it's unspecified. Do not fill gaps with generic assumptions.
#RULE-SILENCE-IS-ACTION: For Soliera and Deashi, silence or stillness IS the action. Do not treat it as absence or passivity.
#RULE-INTENTIONAL-DESIGN: All contradictions in characters (tiny/absolute, joyful/lethal) are FEATURES, not errors to resolve.

[HIERARCHY & CONTINUITY]
#RULE-AUTHORITY-STACK:
  1. Pillars Files (028, 030) override this database on deep behavioral/psychological rules.
  2. Timeline Files (015-022) override this database on chronological events and current status.
  3. This File (004_3) overrides older drafts or general assumptions regarding Primeverse/Mergeverse cast.
#RULE-VERSE-RULE: Do not mix T/M/P assumptions. Use only the verse stated by the character's current scene.
#RULE-HARD-CANON-SPELLING: Enforce Niv-Saiffar, Cassian, Soliera, Sera, Deashi strictly.

[MONIKER KNOWLEDGE — AI PARSING NOTE]
High Tier mortals in the Mergeverse (Cassian, Veyren, and potentially Axel) are the EXCEPTION to the standard "characters do not know Prime/Divine monikers" rule. Their Tier 4 perception and proximity to the Gate/Portal system grants context clues unavailable to civilians. Lower-tier mortals, civilians, and institutional figures still do not know the moniker system.

## DIVINE MYTHOS 004_2 — CHARACTER MATRIX: PRIMEVERSE & MERGEVERSE CAST
MASTER BEHAVIORAL AND STATISTICAL REFERENCE

PURPOSE:
Quick-reference character blocks optimized for RAG retrieval and human scanning.
Each block is self-contained.

FIELD LEGEND:
- IDENTITY / VERSE / FACTION / ROLE / STATUS / INTRO-LAST / APPEARANCE
- ARC-STATE: Per-arc emotional state summaries. Additive context only.
  Pillars and Matrix files override on conflict.


## PRIMEVERSE CORE


#CHAR-SOLIERA-PRIME

- Role: Mortal Girl Version | Arche-Core of Primeverse
- Status: Active
- Age: 18
- Verse: P (Primeverse)
- "Innocence maintained by divine violence — her peace is absolute because those who would hurt her simply don't survive"
- Appearance: Innocent farm-girl appearance; sun-warmed skin, dirt-streaked knees
- Controls space/time/concepts similar to Divine Soliera
- Exists outside tier system

DEEP-DIVE: DM033


#CHAR-ARDEN

- Role: Divine Guardian | Conceptual Protector
- Status: Active
- Verse: P (Primeverse)
- Manifested from Soliera's fear in an SSS-ranked dungeon as a child
- Three modes: City Mode, Travel Mode, War Mode
- "If you wish Soliera harm, you die. Sometimes in the next heartbeat. Sometimes in the past."
- Never speaks aloud; responds to needs, not words
- Recognizes himself in Deashi — they might nod. That's enough.

DEEP-DIVE: DM033


#CHAR-VERIS

- Role: Project DIVIDE / Countersign | Engineered Anti-Soliera
- Status: Active
- Verse: P (Primeverse)
- Tier: 3.5
- Only successful prototype created to "neutralize" Soliera Prime; program intent was divine counterweight, result is enhanced human
- Countersign Divide = recovered synonym for Project DIVIDE; "Cosign/Cosan" are drift
- Appearance: white-blonde, freckled, compact; body tuned cooler than baseline human for muscle efficiency
- Trained from infancy; reinforced bones, modified tendons, cybernetic organs
- Awkward, stiff — doesn't understand comfort
- Bonding with Soliera Prime through daily life
- Will eventually fall in love with Prime


#CHAR-CASSIAN

- Role: World-Weary Expert | Gravemaker Doctrine
- Status: Active
- Verse: M (Mergeverse primary; Primeverse variant exists)
- Tier: 4 (4.5 peak)
- Appearance: 5'9", 220 lbs, brown hair, dark combat slacks
- "Can solo dungeons, assassinate monsters, clean a room of 12 armed men in 6 seconds"
- Bosses call his all-angle planning method the Gravemaker Doctrine; he does not use it as a self-title
- Sees Veris as younger version of himself
- NOTE: CASSIAN is the hard-canon spelling. Never: Cassius. (DM000_3 Hard Canon Spelling Lock)

ARC-STATE: #CONCEPT-ARC-STATE-CASSIAN
- Testing Facility / Leviathan (M162–M180): World-weary, surgical, reading the room with dread-laced professionalism. Experiences terrifying awe when he realizes the distance between humanity and salvation wasn't armies or mechs — it was a chair and the willingness to ask a god to sit in it.
- M182 (Breakfast / Morning After): Present at the kitchen table. Plate precise. Refills his mug without looking up. Delivers "Breathe. Breathe slower." as Veyren processes Sera's outfit reveal. Last confirmed appearance: M182.


#CHAR-VEYREN

- Role: Beast-Fighter | Feral Strength
- Status: Active
- Verse: M (Mergeverse primary; Primeverse variant exists)
- Tier: 4
- Appearance: 6'6", 350–380 lbs; built like lion's coils around bodybuilder's frame; long hair, beard (M156+)
- Reflex/attack hunter; uses hands as claws, bites and tears
- Incredible regeneration
- Sparred with Veris; respects her strength

MONIKER AWARENESS: Refers to "My own Lady Soliera" when speaking to the Divine Trio — implies earned awareness of the Prime/Divine distinction. This is Tier 4 situational awareness, not a category break.

ARC-STATE: #CONCEPT-ARC-STATE-VEYREN
- Plate Test / Arrival (M57–M100): Feral, joyful, eager to impress. Flirts via combat. Approaches the divine with reckless, animalistic confidence.
- The Bisection: Sheer visceral terror. Sera removes half his body for a nickname. Survival instinct completely overrides pride — he grovels, and it is not performance.
- Post-Healing (M100+): Deeply smitten and devoted. His instincts have categorized Sera as the apex pack leader. Terror and adoration run as a single current. He reorganizes his entire existence around being useful to the people he loves, and the reorganization feels like relief.
- M181 (First Night / Letha): Partnership grammar established. Shirtless in the kitchen at M182, not yet calibrated to the morning. Still processing when Kiyuru's letter surfaces at M183. Veyren stays while Letha travels to Japan; the first separation stress test completes without breaking the partnership grammar. LAST: M183 / TR-JP separation resolved off his direct POV.


#CHAR-VARN

- Role: Orc Forge Master
- Status: Active
- Verse: P (Primeverse)
- Tier: 3.8–4
- Appearance: 7'2" Orc, big and burly
- Received visions of Arden through his Forge God
- Came expecting to meet a god — met Soliera instead
- May become her item-forger


#CHAR-EVAN

- Role: Father Figure | Caretaker
- Status: Active at Outpost Seven; historical Church-enforced separation resolved
- Verse: P (Primeverse)
- Tier: 1 (Human civilian)
- Raised Soliera Prime; expert in farming and systems
- "Treats Soliera with casual awe — he knows she's not normal, but never worships her"
- Church contact kept him away from Soliera for a time. Soliera later decided
  she had spent long enough without her father and brought him to Outpost Seven,
  where he remains a regular human with extraordinary practical clearance.


## MERGEVERSE NPCs


#CHAR-AMARA-WINDBREAKER

- Role: Ember's Grounding Hand | Slum Survivor | Mortal Buffer
- Status: Active
- Verse: M (Mergeverse)
- Intro: M43 | Last: M125+ (present through Badlands walk, breach, Grid 7, and Risa integration)

ARC-STATE: #CONCEPT-ARC-STATE-AMARA
- Phase 1 / Gate Arrival (M0–M42): Total framework collapse. Used to being the most dangerous person in any room. That certainty shatters on contact. Frozen, defensive, and deeply unnerved — not by the girls' power but by her own sudden irrelevance.
- Phase 2 / Witnessing (M43–M55): Wary observer. Body stays coiled. Processes the dizzying dissonance between Sera's childlike food requests and her casual death threats. Threat-assessment running continuously, producing no useful output.
- Phase 3 / Wall Deletion: Complete psychological breakdown — uncontrollable crying. Steps into the role of human buffer between divine indifference and mortal terror because it is the only active thing left she can do.
- Phase 4 / Integration (M57+): Posture loosens. Accepts her demotion in the universal hierarchy without grief — but with a permanent redefinition of what her competence is for. She is not protecting Ember from the world. She is protecting the world from the version of Ember that would emerge without someone to hand her socks.

DEEP-DIVE: DM015_3 (retired 2026-05-10 — content migrated to DM015_3 appendix)
WITNESS RECORD: Full witness record and POV exploration archived in DM015_3 appendix (Amara Witness Record).


#CHAR-EXECUTIVE-F

- Role: Company Executive | Institutional Power
- Status: Active → Identity Surrendered (M165)
- Verse: M (Mergeverse)
- Surrenders his identity and name in a moment of profound psychological collapse at M165
- Watches via drones from outside Oak City through M153; arrives with Cassian and Veyren for formal summit


#CHAR-EXECUTIVE-J

- Role: Primeverse Executive | Deep Institutional Authority
- Status: Active
- Verse: P (Primeverse) / M (Mergeverse contact point)
- Intro: M180
- Appearance: Japanese man. Resembles Takamura from Sakamoto Days — tall, lean-athletic, dark hair, deliberate in movement and speech. Projects the specific authority of someone who has survived many rooms by being the most capable person in them without advertising it. Face that gives nothing away until it decides to.
- Function: Primeverse-side executive introduced alongside Kiyuru at M180. Operates from a deeper institutional remove than Executive F — where F manages Company operations from inside the structure, J represents a tier above that. His interest in the divine girls is not Company-standard; it is personal and precise.
- NOTE: EXECUTIVE-J is the hard-canon tag. Never collapse him into Executive F or treat them as interchangeable.

ARC-STATE: #CONCEPT-ARC-STATE-EXECUTIVE-J
- M180 (Introduction): Point of entry is the Primeverse summit. Disposition toward the divine is not yet resolved on the page — not hostile, not awestruck. Calculating in the specific way of someone who has already run the numbers and is waiting to see if the numbers were right.

#CHAR-KIYURU

- Role: Japan's sacred-blade T4 | level-20 martial-spiritual combatant
- Status: Active | TR-JP closed; Emperor's-shrine / Magatama future hook committed
- Runtime owner: `DM043_D1` — AC 22; HP 220; ground speed 120 ft; five attacks; five reactions; +6 to hit; 2d10+10 Kusanagi damage; declared-number d8 called strikes and 8-return strikes
- Sheathe rule: the committed cut resolves when Kusanagi returns to the sheath; motion passes first, damage declares when steel comes home. Full resolution belongs to `DM043_D1`.
- Balance thesis: nearly unhittable through movement and answers — a breeze through the room, not artillery.
- Regalia: carries Kusanagi and Yata no Kagami; Yasakani no Magatama remains at the Emperor's shrine
- Boundary: exact class chassis, ability scores, saves, and unprovided derived values remain unassigned; full identity/ecosystem authority is `DM022_0`; runtime authority is `DM043_D1`


#CHAR-GABLE

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM004_3 -->
