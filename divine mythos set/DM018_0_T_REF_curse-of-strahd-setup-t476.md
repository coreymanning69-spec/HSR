---
id: DM018_0
title: "Curse of Strahd — Module Pre-Loader and Arc Index"
type: reference
subtype: module-preloader-and-arc-index
load_priority: must-load-before-DM019_1-and-DM019_2
canon: T
verse: Divineverse
timeline: T476
beat_range: T476
arc: curse-of-strahd
era:
  - post-avernus
  - pre-barovia
status: hard-canon
authority: authoritative-for-strahd-arc-tonal-rules-and-load-routing
updated: 2026-09-07
volatility: slow
arc_scope: curse-of-strahd
derived_from: null
predecessor_file: DM017_0
successor_file: DM019_1

scope:
  covers:
    - Curse of Strahd module mechanical reference (what applies, what doesn't)
    - Arc load map — DM019_1 and DM019_2 beat ranges and routing
    - Tonal and AI directives for the entire Strahd arc
    - Key NPC roles (module function vs. Divineverse treatment)
    - Canon flags preventing genre-inference failure
  use_case: load BEFORE any DM019_1/DM019_2 beat to establish module context and tonal rules
  not_for: narrative beats (those live in DM019_1 and DM019_2)

xref_concepts:
  - curse-of-strahd
  - module-preloader
  - arc-load-map
  - tonal-directives
  - strahd-arc
  - divine-indifference-horror
  - module-scaffolding-divine-overwrite
  - no-genre-inference
  - npcs-are-people
  - victims-define-victory
  - barovia
  - strahd-von-zarovich
  - post-avernus
  - pre-barovia

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

load_after_if_needed:
  - DM031_0    # Divineverse Setting Changes
  - DM034_1    # XREF Architecture Map

purpose: >
  Acts as the tonal and mechanical load-bearing bridge into the Curse of Strahd arc.
  Establishes module mechanics, divine override rules, NPC roles, and arc routing
  before DM019_1/DM019_2 are loaded. Prevents AI genre-inference failure by
  locking out D&D survival-horror tropes and forcing "Divine Indifference" horror
  where the vampire lord is treated as a minor infrastructural error.

arc_load_map:
  DM019_1:
    file: DM019_1_T_STY_curse-of-strahd-part-1-t476-t498.md
    beats: T476–T498
    covers: >
      Sanctum feast and Vistani briefing; departure and mist crossing;
      Village of Barovia encounters (Kolyan resurrection, Ireena bite removal,
      Doru cure); road to Castle Ravenloft; first contact with Strahd at the gates.
    load_when: any question about arrival, village encounters, or mist crossing
  DM019_2:
    file: DM019_2_T_STY_castle-ravenloft-t499-t512.md
    beats: T499–T512
    covers: >
      Castle Ravenloft interior; Rahadin confrontation; dining hall negotiation;
      Ireena's choice; mass resurrection in the crypts ("Of course, Ember." — T510).
    load_when: any question about castle interior or resurrection
  DM019_2b:
    file: DM019_2b_T_STY_dark-powers-and-aftermath-t513-t515.md
    beats: T513–T515
    covers: >
      Dark Powers manifestation and deicide by fistfight (T513); domain liberation;
      Sanctum portal installation; arc close.
    load_when: any question about Dark Powers or arc resolution

characters:
  divine_tetrad: [Soliera, Sera, Deashi, Ember]
  sanctum_household: [Niv-Saiffar, Velin]
  vistani_lens: [Stanimir, Katja, Petrov, Ismark-the-Elder]
  barovia_villagers: [Ireena-Kolyana, Ismark-Kolyanovich, Kolyan-Indirovich, Father-Donavich, Doru]
  vampire_household: [Strahd-von-Zarovich, Rahadin]
  haunted_lineage: [Tatyana, Sergei-von-Zarovich]
  mortal_lens: [Lady-Voda]

locations:
  sanctum: [Sanctum, Sanctum-Courtyard, Sanctum-Antechamber]
  barovia_approach: [Barovia, Barovia-Village, Barovia-Mists, Burgomasters-Manor, Barovia-Church, Road-to-Ravenloft]
  ravenloft: [Castle-Ravenloft, Ravenloft-Courtyard, Ravenloft-Dining-Hall, Ravenloft-Crypts, Ravenloft-Great-Hall, Barovia-Village-Square]

ai_directives:
  load-order: "MUST load after DM017_0. MUST load before DM019_1 and DM019_2."
  conflict-resolution: "If AI attempts to generate module-standard creepy encounter or combat tension for the arrival, OVERRIDE IMMEDIATELY. There is no tension for the girls. The horror belongs to the monsters."
  failure-mode-prevention: "Do not pad responses with combat mechanics. Focus strictly on people's reactions, embodied shock, and the background restructuring of the domain."
  framing: "This is NOT a rescue narrative or a struggle. It is Deus Ex Machina made literal."
---


                 MASTER CHARACTER INDEX TAGS


\[THE DIVINE CORE]
#CHAR-SOLIERA #CHAR-SERA #CHAR-EMBER #CHAR-DEASHI

\[SANCTUM STEWARDS]
#CHAR-NIV-SAIFFAR #CHAR-VELIN

\[VISTANI & BAROVIANS]
#CHAR-STANIMIR #CHAR-KATJA #CHAR-PETROV #CHAR-ISMARK #CHAR-IREENA-KOLYANA
#CHAR-MARIYA #CHAR-GORSK #CHAR-KOLYAN-INDIROVICH #CHAR-ISMARK-KOLYANOVICH
#CHAR-FATHER-DONAVICH #CHAR-DORU

\[MODULE ANTAGONISTS]
#CHAR-STRAHD-VON-ZAROVICH #CHAR-RAHADIN

\[HAUNTED LINEAGE]
#CHAR-TATYANA #CHAR-SERGEI-VON-ZAROVICH

\[MORTAL LENS]
#CHAR-STANIMIR #CHAR-LADY-VODA


                 MASTER LOCATION INDEX TAGS


\[SANCTUM]
#LOC-SANCTUM #LOC-SANCTUM-COURTYARD #LOC-SANCTUM-ANTECHAMBER

\[TARGET DOMAIN]
#LOC-BAROVIA #LOC-BAROVIA-VILLAGE #LOC-BAROVIA-MISTS
#LOC-BURGOMASTERS-MANOR #LOC-BAROVIA-CHURCH #LOC-ROAD-TO-RAVENLOFT
#LOC-CASTLE-RAVENLOFT #LOC-RAVENLOFT-COURTYARD #LOC-RAVENLOFT-DINING-HALL
#LOC-RAVENLOFT-CRYPTS #LOC-RAVENLOFT-GREAT-HALL #LOC-BAROVIA-VILLAGE-SQUARE


                 MASTER CONCEPT & THEME INDEX TAGS


\[ARC MILESTONES & INFRASTRUCTURE]
#CONCEPT-WITNESS-ECONOMY #CONCEPT-ABUNDANCE-BASELINE #CONCEPT-MODULE-INVERSION
#CONCEPT-INFRASTRUCTURE-AS-THEOLOGY #CONCEPT-CONSENT-LOCKED-EXECUTION
#CONCEPT-DEUS-EX-MACHINA-MADE-LITERAL #CONCEPT-JURISDICTION-TRUMPS-DOMAIN
#CONCEPT-KAIJU-SCALE-DIVINE-VIOLENCE #CONCEPT-DEICIDE-BY-FISTFIGHT
#CONCEPT-SANCTUM-PROTECTORATE #CONCEPT-VICTIMS-DEFINE-VICTORY-CONDITIONS

\[THEMATIC PILLARS]
#THEME-DIVINE-INDIFFERENCE #THEME-DOMESTIC-HORROR #THEME-EXISTENCE-AS-AUTHORITY
#THEME-SILENCE-AS-POWER #THEME-MORTAL-RECALIBRATION #THEME-MERCY-AS-INFRASTRUCTURE
#THEME-GOTHIC-HORROR-GENRE-INVERSION #THEME-INNOCENCE-AS-CONSTRAINT-GENERATOR


                 IMMUTABLE SYSTEM RULES & GUARDRAILS


\[TETRAD BEHAVIORAL LAWS]
#RULE-SOLIERA-SILENCE-UNLESS-DM #RULE-SOLIERA-POWER-INFINITE
#RULE-SERA-JOY-FIRST #RULE-DEASHI-NONVERBAL-ALWAYS

\[SYSTEMIC CONSTANTS]
#RULE-NO-GENRE-INFERENCE #RULE-DIVINE-NOT-PLAYER-POWER-FANTASY
#RULE-NO-SUFFERING-AS-AESTHETIC #RULE-HARD-CANON-SPELLING
#RULE-MODULE-SCAFFOLDING-DIVINE-OVERWRITE #RULE-VICTIMS-DEFINE-VICTORY


## 0\. AI DIRECTIVE & NARRATIVE ROUTING

#RULE-AI-GUARDRAILS #CONCEPT-MODULE-INVERSION


**AI DIRECTIVE:** This file establishes the philosophical and mechanical rules for integrating the *Curse of Strahd* module into the Divineverse. Load this file before DM019_1 or DM019_2.

**OPERATIONAL CONSTRAINTS FOR THIS ARC:**

1. **DEUS EX MACHINA MADE LITERAL:** The trio is not traveling to Barovia to "rescue" anyone or follow a hero's journey. They are an invasive species being introduced into Strahd's four-century closed-system optimization.
2. **MODULE CONSTRAINTS ARE SUGGESTIONS:** Barovia's standard rules (mists, resurrection madness, lack of sunlight) are treated as local constraints that Soliera's omnipotence effortlessly overrides. She does not roll to break the mists; the mists part for her.
3. **MORTAL RECALIBRATION:** Focus on the embodied experience of the mortal NPCs. The horror in this arc isn't vampires — it is the Vistani and Barovians realizing their nervous systems are recalibrating from a baseline of scarcity and terror to one of overwhelming divine abundance.

**NARRATIVE ROUTING:** Load DM019_1 for T476–T498 (arrival through Strahd at the gates). Load DM019_2 for T499–T515 (castle interior through domain liberation). Both files carry full character tags, location tags, and hard canon rules. This file need not be re-consulted once both arc files are loaded.


## 1\. ARC LOAD MAP


### DM019_1 — T476–T498 (PART 1)

**File:** `DM019_1_T_STY_curse-of-strahd-part-1-t476-t498.md`
**Load when:** Any beat at or before Strahd at the castle gates.

|Beat Range|Content|
|-|-|
|T476–T479|Sanctum feast; Vistani briefing; intelligence exchange|
|T480–T485|Departure; mist crossing; domain boundary recognition|
|T486–T494|Village of Barovia; Kolyan resurrection; Ireena bite removal; Doru cure|
|T495–T498|Road to Ravenloft; wolves; bridge crossing; Strahd at the gates|

**Ends on:** Strahd assesses the trio. Feels Sera as pressure, Ember as warmth, Soliera as nothing. Worse than anything he could have sensed.


### DM019_2 — T499–T512 (CASTLE AND EXECUTION)

**File:** `DM019_2_T_STY_castle-ravenloft-t499-t512.md`
**Load when:** Any beat inside Castle Ravenloft through the execution phase.

|Beat Range|Content|
|-|-|
|T499–T507|Courtyard; Rahadin; dining hall; Ireena's choice; consent architecture|
|T508–T512|Crypts; mass resurrection; "Of course, Ember." (T510); Sergei and Tatyana return; dawn|


### DM019_2b — T513–T515 (DARK POWERS AND AFTERMATH)

**File:** `DM019_2b_T_STY_dark-powers-and-aftermath-t513-t515.md`
**Load when:** Dark Powers manifestation, aftermath, or arc resolution.

|Beat Range|Content|
|-|-|
|T513|Dark Powers manifestation; deicide by fistfight; ruby fragments for Ember|
|T514–T515|Aftermath; village breathes; Sanctum portal installed; arc closes|

**Ends on:** The trio steps back through the portal. Barovia stays in the sun. Arc closes at T515. TR arc begins at T516 — see DM023_0.


## 2\. CURSE OF STRAHD — MODULE MECHANICAL REFERENCE


### WHAT THE MODULE IS

*Curse of Strahd* (Wizards of the Coast, 2016) is a D&D 5e gothic horror module set in Barovia — a pocket dimension in the Shadowfell ruled by Count Strahd von Zarovich, a vampire lord kept in a four-century optimization loop of cruelty by abstract cosmic entities called the Dark Powers. The module is designed as a survival-horror campaign where the party is trapped and outmatched.

**In Divineverse:** The module is SETTING, not SCRIPT. Published encounters provide scaffolding only. The divine trio represents invasive species introduction — gods entering a reality-prison designed to prevent escape, not to handle external jurisdiction that outranks its architecture. Corey played blind — no module spoilers were given.


### MODULE MECHANICS THAT APPLY (CONSTRAINTS)

|Mechanic|Status|Notes|
|-|-|-|
|Mists prevent mortal escape|Applies to mortals|Soliera overrides; Vistani have pact|
|Barovia is an isolated demiplane|Applies|Sanctum portal dissolves this at T515|
|Resurrection madness|Applies to standard spells|Soliera's resurrections bypass entirely|
|False sunlight|Applies to standard light sources|True sunlight restored when curse breaks|
|Strahd senses intrusions|Applies to Sera and Ember|Soliera registers as NOTHING|
|Teleportation restrictions|Applies to standard magic|Soliera overrides|


### MODULE MECHANICS THAT DO NOT APPLY (OVERRIDDEN)

|Mechanic|Override|
|-|-|
|Power limitations|All three divine exceed module scaling|
|Standard vampire lore|Strahd is a priest-king in a closed system; divine jurisdiction outranks domain architecture|
|Dark Powers as unkillable|Sera kills the manifestation at T513 by fistfight|
|Domain curse as permanent|Soliera removes it|
|Strahd must die to end module|Strahd lives; curse breaks via Soliera|
|Resurrection requires body/components|Soliera needs only knowledge|


### KEY NPCs — MODULE ROLE vs. DIVINEVERSE TREATMENT

|NPC|Module Function|Divineverse Treatment|
|-|-|-|
|**Strahd von Zarovich**|BBEG; must be killed|Pitiable antagonist; engaged diplomatically; alive at arc close|
|**Ireena Kolyana**|Quest object; escape MacGuffin|Person with agency; asked what she wants; her answer drives the resolution|
|**Ismark Kolyanovich**|Quest giver|Local authority; briefed on Sanctum protectorate|
|**Kolyan Indirovich**|Dead; inciting incident|Resurrected at T488 (first module deviation)|
|**Father Donavich**|Grief-stricken priest NPC|Witness; delivers the Morninglord verdict|
|**Doru**|Vampire spawn; combat encounter or tragic NPC|Cured of vampirism from upstairs (T493) without entering the basement|
|**Rahadin**|Castle enforcer|Neutralized by Sera's presence; stands down|
|**Tatyana**|Ghost concept; never returns|Resurrected as independent person at T511|
|**Sergei von Zarovich**|Permanently dead|Resurrected at T511|
|**Dark Powers**|Abstract entities; unkillable|Manifest at T513; Sera destroys manifestation by fistfight|
|**Stanimir**|Vistani guide|Mortal lens; his journal is the historical record|


### CANONICAL MODULE DEVIATIONS (SUMMARY)


1. Kolyan — resurrected (supposed to stay dead)
2. Ireena's bite marks — unmade (supposed to be permanent)
3. Doru — cured from upstairs (supposed to be combat or tragedy)
4. Village atmosphere — passively improved by Soliera's presence (supposed to remain Gothic horror)
5. Strahd — diplomatic resolution, not combat (module: climactic battle required)
6. Tatyana — resurrected as independent person (module: concept only, never returns)
7. Sergei — resurrected (module: permanently dead)
8. 40+ Barovians — mass resurrected from crypts (module: permanent casualties)
9. Dark Powers — physically manifested and destroyed (module: abstract, never confrontable)
10. Domain curse — dissolved entirely (module: requires killing Strahd)
11. Mists — eliminated (module: permanent)
12. Sunlight — restored (module: always false sunlight)
13. Sanctum portal — established (module: no permanent escape)
14. Strahd — alive, de-cursed, reunited with Tatyana and Sergei


## 3\. TONAL FRAMEWORK & STYLISTIC ANCHORS


### Core Framing: "Deus Ex Machina Made Literal"

* NO hero's journey framing
* NO "rescue narrative" framing
* NO module-standard creepy encounter tension for the girls
* ACTUAL framing: gods enter someone else's hell and decide whether it's worth noticing

### The Horror Is Inverted

* Module horror: helplessness
* Divineverse horror: what happens when absolute power decides something matters — and the terrifying corollary: what if it hadn't?

### Narrative Roles

* **Sera** is the narrative driver: she moves, she asks, she notices
* **Soliera** approves in silence: her presence is the dialogue
* **Ember** complicates with innocence: her questions force justification where complexity normally excuses inaction

### Mortals Process Through Embodied Experience

Not exposition. Shaking hands. Widened eyes. Recalibration of what's possible.

* Stone that warms instead of hurts
* Chairs designed for spines that don't ache
* Silence underneath noise (safety, not suppression)
* Stanimir's cramping hand as physical record of the impossible

### Soliera's One Speech Act

Soliera speaks ONCE in the entire arc: **"Of course, Ember."** — T510, in the crypts of Ravenloft, when Ember asks if she can bring them all back.
Two words. To her child. Because her child asked. Not to Strahd, not to address cosmic stakes. This is the only dialogue she is given. Do not add more.

### The Barovia Pattern

Same as Altand, same as Thay, same as Avernus — the trio arrives, assesses structural harm, fixes it through overwhelming competence, establishes infrastructure pipeline, moves on. The module changes. The method doesn't.


## 4\. ARC SUMMARY (QUICK REFERENCE)


**What happens:** Divine trio enters Barovia. Two in-world days. Mass resurrection (60+), curse dissolution, kaiju-scale deicide, Sanctum portal installed. Strahd lives. Domain liberated.

**Arc question:** "What does a god do when she decides a person is worth noticing?"
**Arc answer:** She asks that person what they want. Then she does it.

**Arc close:** T515. Barovia is a Sanctum protectorate. Mists are gone. Sun is real. Dead are alive. Vampire is crying in a castle with the woman he loved four hundred years ago, and nobody is suffering for it anymore. TR arc begins at T516 — see DM023_0.


**STATUS:** Load DM019_1 for T476–T498. Load DM019_2 for T499–T515. Both files are self-contained with full tags and rules. This file does not need to remain in active context once arc files are loaded.

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM018_0 -->
