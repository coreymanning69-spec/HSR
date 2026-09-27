---
id: DM004_1
title: "Character Matrix — Divineverse: Divine Core (Tier 1 Cast)"
type: synthesis
subtype: character-database
load_priority: load-after-DM003_0-before-narrative
canon: T
verse: Divineverse
timeline: "T0–T515 locked; T516+ TR references"
arc: character-reference
era: t-beat-cast
status: hard-canon
authority: authoritative-for-divineverse-tier1-character-data
updated: 2026-09-07
volatility: slow
arc_scope: evergreen
derived_from: null
predecessor_file: N/A
successor_file: DM004_2

scope:
  covers:
    - divine_cast            # Yuium, Soliera, Deashi, Sera, Ember, Niv-Saiffar
    - equipment_per_character    # KTE, Velvet Spiral, Velvet Spiral (Sera), etc.
    - alias_dictation_map    # Canonical dictation corrections for Tier 1 names
  use_case: first lookup for Divineverse Tier 1 identity, role, relationship, and equipment metadata
  not_for: inner-circle cast, Primeverse/Mergeverse cast, or precise character mechanics
  applies_to:
    - Divineverse
  distinct_from:
    DM004_2: "DM004_2 family = founders in DM004_2, later household/staff in DM004_2b, and allies/antagonists/Undermountain in DM004_2c."
    DM004_3: "DM004_3 = Primeverse & Mergeverse cast (M/P-beat era)."
    DM027_0: "DM027_0 = Sera's full 5e sheet (mechanics deep)."
    DM028_1: "Soliera Pillars"
    DM028_2: "Deashi Pillars"
    DM028_3: "Ember Pillars (theology deep, kintsugi, kit, forbidden list)"
    DM029: "DM029 = Sanctum Operations (Niv/staff role-deep)."
    DM030_1: "DM030_1 = Sera's Pillars (mechanics/combat/origin)."
    DM030_2: "DM030_2 = Sera's Pillars (social/relationships/voice)."
    DM033: "DM033 = Soliera Prime / Arden (Primeverse-pre-Merge deep)."
    DM022_0: "DM022_0 = Primeverse Character Matrix (Tier 4 / Japan hub deep)."


xref_concepts:
  - character-metadata
  - niv-counterweight-delusion
  - early-sera-boundary-grammar
  - tier-classification
  - canon-affiliation
  - role-taxonomy
  - relationship-graph
  - load-bearing-per-character
  - soliera-silence-rule
  - sera-joy-first
  - deashi-eternal-silence
  - ember-innocence-as-governance
  - niv-atelier-role
  - pending-codification
  - vesper
  - eight-chickens-named
  - sound-curtain


  - DM034_1   # Master Tagging / XREF Architecture

purpose: |
  Divine Core segment of the DM004 split. Master character index and quick-reference
  matrix for the Tier 1 cast of the Divineverse (T-beat era): Yuium, Soliera, Deashi,
  Sera, Ember, and Niv-Saiffar. Also contains the canonical alias/dictation map and
  immutable parsing rules.

  When you need to know a Tier 1 character exists, where they sit in the power structure,
  which canon they belong to, who they're tied to, and what equipment they carry
  — this is the file. The Tier 2+ cast is split across the DM004_2 family:
  founders in DM004_2, later household/staff in DM004_2b, and allies,
  antagonists, deities, and Undermountain companions in DM004_2c.
  Personality, theology, and mechanical depth defer to the appropriate deep-dive file.

  Authority: Tier 1 character existence, canon membership, tier, role, and relationship
  data is arbitrated here. When a deep-dive contradicts DM004_1 on metadata,
  treat as a flag for manual reconciliation.

ai_directives:
  - LOAD-AFTER-DM003_0-BEFORE-NARRATIVE
  - AUTHORITATIVE-FOR-DIVINEVERSE-TIER1-CHARACTER-METADATA
  - DEFER-TO-DM004_2-FOR-INNER-CIRCLE-AND-NPC-DATA
  - DEFER-TO-DEEP-DIVE-FILES-FOR-PSYCHE-AND-MECHANICS
  - USE-AS-FIRST-LOOKUP-WHEN-T-BEAT-TIER1-CHARACTER-NAME-APPEARS
  - APPLY-DICTATION-CORRECTIONS-FROM-MEMORY-WHEN-NAMES-ARRIVE-MANGLED
  - NEVER-INFER-CHARACTER-DATA-WHEN-MISSING-FLAG-INSTEAD

open_threads_forward:
  - Vesper entry complete (spec in DM004_2b #CHAR-LETHA — Vesper subsection)
  - Eight chickens are named situationally by Ember; no fixed roster is required
  - Sound Curtain not character-bound — lives in DM029
  - Inner Circle / Canon NPC cast in DM004_2
  - Primeverse/Mergeverse cast in DM004_3
---

## SEGMENT MAP

Load only the smallest segment whose coverage matches the question. Each sibling repeats its own scope and authority context.

| ID | Covered section |
|---|---|
| DM004_1 | Continuation |
| DM004_1a | Character Matrix Divineverse — Behavioral Logic |
| DM004_1b | Character Matrix Divineverse — Notes & Disclaimers |

Continuation material follows; the segment map above remains the retrieval route.


## MASTER CHARACTER INDEX TAGS (BY TIER)
[TIER 5: DIVINE CORE / SINGULARITIES] — entries in this file
#CHAR-YUIUM #CHAR-SOLIERA #CHAR-SERA #CHAR-DEASHI #CHAR-EMBER

[TIER 2.5: INNER CIRCLE / SANCTUM LOGISTICS] — entries in DM004_2
#CHAR-NIV-SAIFFAR #CHAR-VELIN #CHAR-MARRIK #CHAR-HOTHGAR #CHAR-PELL
#CHAR-LETHA #CHAR-KORIN #CHAR-KESSLA #CHAR-TALIANDRA #CHAR-THORIN #CHAR-CALE

[TIER 3–4: CANON NPCs / REGIONAL POWERS] — entries in DM004_2
#CHAR-ALUSTRIEL-SILVERHAND #CHAR-VAJRA-SAFAHR #CHAR-BLACKSTAFF #CHAR-DAGULT-NEVEREMBER
#CHAR-DRIZZT #CHAR-ELIA #CHAR-CLOUDGAZER #CHAR-JARLAXLE #CHAR-XANATHAR #CHAR-MACCATH
#CHAR-AURIL #CHAR-TIAMAT #CHAR-SHAR #CHAR-MYSTRA #CHAR-LOLTH #CHAR-ZARIEL #CHAR-ASMODEUS
#CHAR-STRAHD-VON-ZAROVICH #CHAR-TARNETH-SAZHER

## IMMUTABLE CHARACTER PARSING RULES
## [BEHAVIORAL GUARDRAILS]
#RULE-NO-GENRE-INFERENCE: Do not invent missing details based on standard fantasy trope logic. If a motivation isn't written, it's unspecified. Do not fill gaps with generic assumptions.
#RULE-SILENCE-IS-ACTION: For Soliera and Deashi, silence or stillness IS the action. Do not treat it as absence or passivity.
#RULE-INTENTIONAL-DESIGN: All contradictions in characters (tiny/absolute, joyful/lethal) are FEATURES, not errors to resolve. Do not attempt to "normalize" them.

[HIERARCHY & CONTINUITY]
#RULE-AUTHORITY-STACK:
  1. Pillars Files (028, 030) override this database on deep behavioral/psychological rules.
  2. Timeline Files (005-021) override this database on chronological events and current status.
  3. This File (004_1) overrides older drafts or general AI knowledge regarding D&D NPCs.
#RULE-VERSE-RULE: Do not mix T/M/P assumptions. Use only the verse stated by the character's current scene.
#RULE-HARD-CANON-SPELLING: Enforce Niv-Saiffar, Cassian, Soliera, Sera, Deashi strictly.

## DIVINE MYTHOS 004_1 — CHARACTER MATRIX: DIVINEVERSE DIVINE CORE
MASTER BEHAVIORAL AND STATISTICAL REFERENCE

PURPOSE:
Quick-reference character blocks optimized for RAG retrieval and human scanning.
Each block is self-contained.

FIELD LEGEND:
- IDENTITY: Primary name | Aliases (dictation variants in parentheses)
- VERSE: Which verses the character appears in
- FACTION: Current allegiance
- ROLE: Function tag (one line)
- STATUS: Active / Erased / Unknown / Mentioned
- INTRO/LAST: First and most recent beat appearances
- APPEARANCE: Physical description
- BEHAVIOR/PSYCHE: Core psychological drivers and rules
- MECHANICS/POWER: Combat or influence scale
- ARC-STATE: Per-arc emotional state summaries. Use when writing a character at a
  specific beat to calibrate their register. Authority: additive context only.
  Pillars and Matrix files override on conflict.


## TIER 1: DIVINE CORE


#CHAR-YUIUM

IDENTITY: Yuium | (UEM, YOUEM, U-E-M, YUEM, YEUEM, YUIUEM - dictation)
VERSE: T (foundational; exists as background truth in M/P)
FACTION: Sanctum (Origin Point)
ROLE: Primordial Godhead | Source of Soliera and Deashi
STATUS: Distributed Whole (no separate post-split agent)
INTRO: T0 | LAST: T0 (never directly appears after splitting)

APPEARANCE:
- Form: Liquid black void contained within a massive pillar of white/clear crystal
- Location: Deep in the Spine of the World mountains
- Nature: Shifts and moves freely inside incredibly dense crystal, demonstrating existence on a plane above local reality
- Scale: The crystal pillar is large; Yuium fills it as living darkness

CONCEPTUAL NATURE:
- The speakable Name and Whole, distributed after the primary split rather than dormant as a separate person
- Soliera goes and experiences; Deashi stays and ponders
- Sera and Ember are their experiences' next recursive iteration — experiences of experiences
- The architecture can nest as infinite sets, but no additional named rung is canon
- The whole-system Lion function is the nuclear deterrent against Ao or elder-god intervention
- The Veiled Eye's knowing function is expressed through Deashi and the Sanctum substrate

CORE RULES:
- Never directly manifests after T0 as a separate character; the Antechamber retains the Whole's residue/substrate
- Soliera and Deashi are the primary halves; Sera and Ember are the next recursive iteration
- His existence ensures no external cosmic force can threaten the Sanctum's sovereignty
- AI must never write YUIUM as a speaking, dormant, or observing post-split character

NARRATIVE FUNCTION:
- Anchor for cosmic power scaling
- Ensures the story can never be outgunned by FR lore entities
- Background metaphysical truth rather than active character

CROSS-REF: #CONCEPT-YUIUM, #CONCEPT-VEILED-EYE, #LOC-SPINE-OF-THE-WORLD


#CHAR-SOLIERA

IDENTITY: Soliera | Soli (by Sera) | The Lady (servants) | "That Woman" (outsiders) | (SO THE AIR, SOLIARA, SULLY/SOLI - dictation)
TITLES: The Mother Beyond Stone, The Silent Sovereign, She Who Raised the Walls, Yuium's Crown
VERSE: T/M/P (all)
FACTION: Sanctum (Infrastructure Core)
ROLE: Sovereign Axis | Reality Warden | Architect of Mercy
STATUS: Active (Divine)
INTRO: T1 | LAST: T515+ / TR era active / M183+ parallel references

ORIGIN: One of two equal halves of YUIUM. She is the going/experiencing half and the Freudian Ego: active, present, and outward-facing. Deashi is her counterpart. Neither is subordinate; their functions differ.

APPEARANCE:
- Height: ~5'5"
- Build: Maternal, fertile; regal poise
- Skin: Warm golden-tan skin
- Hair: Dark brown, near-black, often braided by Sera
- Clothing: Flowing silk-like robes with gold sacred geometry; barefoot or elegantly shod
- Movement: "Pace of inevitability" — measured, silent, intentional
- Aura: Reality bends to her perception; rooms hush when she enters

QUOTE: "Soliera stands... lavender hem brushing the stone." — DM04-T322

CORE BEHAVIORAL RULES:
- SPEAKS RARELY: Only addresses beings of incredible power or inner circle
- AI NEVER VOICES HER: Corey controls all Soliera dialogue; AI should not assume she speaks
- SILENCE IS ACTION: Her stillness, observation, and mood ARE her communication
- SERA HANDLES EXTERNALIZATION: Sera interprets Soliera's will to others
- WORDS BECOME REALITY: She limits speech because her statements have literal force
- EVERY CHILD IS SACRED: Harm to children invokes immediate, absolute wrath
- INTERNAL MANTRA: "If I can fix it, I must."

POWERS (Summary):
- Reality Warden: Reshapes matter, heals mortals, erects/folds structures at will
- Current Local Presence: Passively aware of current reality within roughly ten miles; no future sight or distant/domain omniscience
- Veiled Eye Footprint: Her visits permanently enroll locations, but the feed goes to Deashi; Soliera is purposely excluded
- Emotional Dominion: Instills calm, hush, or awe within vicinity without rewriting inner identity
- Selective Blessing: Perfects chosen beings' bodies and minds only under the applicable consent-and-comprehension law
- Construct Sovereignty: Commands countless divine constructs silently
- Scale Manipulation: Can grow to mountain-striding size; froze a dragon mid-flight

RELATIONSHIPS:
- SERA: Lover, voice, joyful enforcer; their intimacy is public sacrament
- DEASHI: Equal-opposite twin; silent mutual understanding; she "explains" him to others
- EMBER: Daughter-figure; protective but allows exploration
- NIV-SAIFFAR: Administrative head, trusted logistics master, and sole male-formed intimate of Soliera and Sera; a dragon rather than a man
- PELL: Living symbol of empathy toward the forgotten masses

NARRATIVE FUNCTIONS:
1. Sovereign Center — unmoving axis of mythic setting
2. Architect of Change — embodies restraint-as-strength and dominion-through-care
3. Moral Compass — protector of children, arbiter of mercy and consequence

META INSPIRATION: Relational metamorphosis — Child in the Ontological Circle/Bridge, Camel in the Manifest Circle; Freudian Ego; Buddhist/Taoist empathy; first Heh (Mother) / Chesed

ARC-STATE: #ARC-STATE-SOLIERA
- All Arcs (baseline): Silent maternal contentment. Observes her loved ones and infrastructure flourish with deep satisfaction. Grieves quietly when her family leaves. Experiences rare flares of anger only when a child is harmed.
- Taliandra Departure (T101): Paralyzed by genuine grief for nearly two days. She is
  not angry. Tali is the first gathered person to choose a separate, reachable life,
  and Soliera has no category for "ours, but not here."
- Mergeverse: Watches the modern world through a lens of patient curiosity. The corporate and military apparatus around her reads as familiar — another civilization organizing itself around care and structure.

CROSS-REF: #RULE-SOLIERA-SILENCE-UNLESS-DM, #CONCEPT-VEILED-EYE, #THEME-MERCY-AS-INFRASTRUCTURE


#CHAR-DEASHI

IDENTITY: Deashi | The Silent Enforcer | The Judgment | Soliera's Equal | (DAISHI, DAY-SHAY, DAY SHE - dictation)
VERSE: T/M/P (all)
FACTION: Sanctum (Silent Judgment)
ROLE: Terminal Consequence | Cosmic Horror Element | Co-Founder
STATUS: Active (Divine; normally still, not limited to one action threshold)
INTRO: T0 | LAST: T515+ / present as divine judgment baseline

ORIGIN: One of two equal halves of YUIUM. He is the staying/pondering half and the Freudian Superego — retained law, total enrolled-domain memory, silence, and judgment. Soliera is his counterpart. Neither is subordinate; their functions differ.

APPEARANCE:
- Height: 9 ft
- Weight: ~800 lbs
- Form: Skeletal juggernaut encased in bone-white armor; void-filled joints
- Material: White stone, divine alloys, metaphysical void
- Face: Helmet-like skull; eyeless voids; NO MOUTH
- Movement: Steps crack stone; can stand motionless in blizzards for days
- Presence: Corridors hush and re-orient when he passes — absence given form
- Sound: Body makes no sound except footsteps, which press an inch deep into earth

QUOTE: "The skeletal colossus pushed footprints an inch deep." — DM01-T1

CORE BEHAVIORAL RULES:
- NEVER SPEAKS: Has never spoken and never will. This is absolute.
- AI NEVER VOICES HIM: No dialogue, no internal monologue voiced
- SILENCE IS LAW: Crowds hush at his introduction
- TWO ACTION CLASSES: Witnessable causal displays answer household audacity/judgment; true retroactive pruning silently removes existential branches outside observable history
- EMOTIONAL BUT INEXPRESSIBLE: Deeply feels rage, sorrow, loyalty — cannot communicate it
- SERA IS HIS ONLY COMFORT: She treats him casually, reclines across his lap; this reaches him

POWERS (Summary):
- Concept Mimicry: Learns weapon styles instantly mid-battle
- Silent Annihilation: Delivers the IDEA of destruction, bypassing all resistance
- Absolute Scale: Violence equals cosmic reset; only concept-level negation can oppose
- Requires Nothing: No sustenance, rest, or breath
- Immune to Magic: Functionally beyond it
- Veiled Eye: Atemporally omniscient and omnipresent throughout every location Soliera or Deashi has enrolled

RELATIONSHIPS:
- SOLIERA: Twin-origin counterpart; silent mutual understanding
- SERA: Only being who treats him casually; she loves him deeply as an uncle figure
- MORTALS: Instinctive terror; approach is taboo without Soliera present

NARRATIVE FUNCTIONS:
1. Enforcer of Finality — his presence signals non-negotiable judgment
2. Tone Setter — introduces mythic gravity or cosmic horror
3. Co-Founder — walked with Soliera in humanity's first week
4. Meta Reminder — a threat beyond gods; consequence to arrogance

CURRENT STATUS:
- Stationed on his throne near Soliera's private quarters
- "The day Deashi stood" is spoken of as an apocalyptic benchmark
- Normally still but fully aware; may choose a witnessed display for household judgment, while true existential pruning remains unknowable

META INSPIRATION: Camel in the Ontological Circle and Cross-Layer Bridge; Freudian Superego; the cosmic horror of a limitless intelligence that cannot be escaped, deceived, or appealed to; Yod (Father) / Gevurah

ARC-STATE: #ARC-STATE-DEASHI
- All Arcs (baseline): Agonizing, inexpressible interiority. Feels intense rage, sorrow, and loyalty that have no outlet. Locked behind absolute silence. Not absence — trapped presence.
- Proximity to Sera: The only channel that reaches him. Her casual affection — reclining on him, treating him like a beloved uncle — produces something close to relief. Brief, real, unrepeatable.

CROSS-REF: #RULE-DEASHI-NONVERBAL-ALWAYS, #THEME-JUDGMENT-AS-SILENCE


#CHAR-SERA

IDENTITY: Sera | The Porcelain Queen | Barefoot Death | The Porcelain Executioner | (SERAH, SARAH - dictation)
ORIGIN: Was Reva, a discarded village girl — small, unhealthy, overlooked. Soliera destroyed Reva and rebuilt her as something absolute.
VERSE: T/M/P (all)
FACTION: Sanctum (Joy-First Enforcement)
ROLE: Soliera's Will Vector | Living Proof of Divine Authority | First Worshiper
STATUS: Active (Divine)
INTRO: T10 (Reva's Remaking) | LAST: T515+ / M183+ active

APPEARANCE:
- Height: 4'10"
- Weight: ~90 lbs
- Build: Willowy with exaggerated feminine ratios; wide pelvis, narrow waist, small shoulders
- Skin: Porcelain pale, human texture, perfect symmetry; does not bruise or scar unless she wills it
- Eyes: Enormous sapphire blue, pupils never contract, radiating animal intent
- Hair: Midnight black, waist-length, styled gothic/braided; colors it occasionally
- Clothing: Purple silk, tight and transparent; mismatched stockings (one thigh-high, one ankle) [DIVINEVERSE STANDARD]
- ERA WARDROBE NOTE: Sera's enormous sapphire-blue eyes are invariant across eras. Clothing is beat-specific: Mergeverse prose establishes purple silk where stated and may establish nude presentation where stated; neither is a fixed Mergeverse-wide uniform. Do not hallucinate red, burnt sienna, or any other color as an era default without the active beat.
- Feet: Usually barefoot; leaves no trace unless she wants to
- Movement: Predator's economy — no waste, no hesitation; soundless when she chooses

QUOTES:
- "Boom, bitches. God's here." — Greenest Arc
- "Aren't I smaller than you?" — To Raiders, before slaughter
- "They won't like it." — Warning about dragons
- "Just a common bitch." — After obliterating the Black Death dragon
- "Kung Fu! I told you, it's kung fu!" — Laughing while parrying Niv's strikes

CORE BEHAVIORAL RULES (AI-NOTE-SERA-BEHAVIOR):
1. JOY-FIRST: Baseline is HAPPY, not brooding. She laughs, pouts, flirts, dances, touches people by default.
2. SMALL BUT ABSOLUTE: Compact adult-woman frame (exactly 4'10", ~90 lbs). Grown woman's presence and confidence. Size NEVER implies weakness or childishness.
3. ALWAYS WOMAN-CODED: Woman in identity, presentation, desire. Never infantilize her.
4. LAUGHING BUT DEADLY: Jokes and giggles do NOT reduce threat level. Can go from lap-sitting to erasing platoons without emotional whiplash.
5. NOT CURIOUS IN ABSTRACT: Reacts to concrete things, not theory. Ember is curiosity; Sera is RESPONSE.
6. MERCY FROM POSSESSION: Spares people because someone she cares about likes them, not universal compassion.
7. NEVER FIGHTS SOLIERA: May whine, pout, cling — but always obeys. No "Sera vs Soliera" power struggle exists.
8. BINARY EMPATHY: Those with her = protected forever. Those against = erased so the protected stay safe.

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM004_1 -->
