---
id: DM009_0
title: "Rise of Tiamat: The March to the Well"
type: beat
subtype: story-log
load_priority: load-after-DM008_3-before-DM010_1
canon: T
verse: Divineverse
timeline: T221–T290
beat_range: T221–T290
arc: rise-of-tiamat-march-to-well
era:
  - rise-of-tiamat
  - misty-forest
  - well-of-dragons-approach
status: hard-canon
authority: authoritative-for-T221-T290
updated: 2026-09-06
volatility: invariant
arc_scope: rise-of-tiamat-march-to-well
derived_from: null
predecessor_file: DM008_3
successor_file: DM010_1

xref_concepts:
  - established-here
  - the-green-path
  - distance-destruction
  - wall-of-dragons
  - reinforced-here
  - mercy-as-infrastructure
  - absolute-power
  - faction-power-consequences
  - divine-gifts-become-doctrine
  - metallic-dragon-witness-roles

canon_flags:
  - "ONE-DRAGON LOCK: Voaraghamanthar is the sole Black Death dragon. He arrives alone at the T260 festival and Sera kills him there. T287 is a status recall during the later march, not a second dragon or second kill."
  - "Ember is referenced contextually as foreshadowing, but her actual genesis occurs in DM010_2. Do not treat her as physically present yet."
  - "The Draakhorn is not silenced by a mortal raid; it is melted from a distance by Soliera."
  - "Faction blessings become doctrine and logistics, not empire-building or mortal command over divine power."

load_after_if_needed:
  - DM031_0 # Divineverse Setting Changes
  - DM034_1 # XREF Architecture Map

purpose: "Documents the faction mustering and consequence logic before the Well of Dragons: metallic dragon support, tailored divine blessings, faction leaders converting gifts into doctrine/logistics/restraint, and the absolute obliteration of the Cult's ultimate defenses (Draakhorn, Black Death, Wall of Dragons). Establishes that Soliera's power scales infinitely without effort, setting the stage for Tiamat's appearance and the creation of Ember."

arc_summary:
  setup: "The combined forces of the Sword Coast and the Metallic Dragon Council muster, accompanied by the Divine Trio, to march on the Well of Dragons."
  core_motion: "The faction leaders convert Soliera and Sera's tailored blessings into institutional behavior: civic defense, truth-preservation, duty, restoration, disciplined profit, arcane containment, and draconic witness. The traveling column advances effortlessly upon the caldera along 'The Green Path', systematically and instantly destroying the Cult's ultimate defenses."
  resolution: "Soliera casually annihilates the massive Wall of Dragons in the sky with absolute divine authority, clearing the way for the climax."

key_beats:
  T250: "Metallic dragons agree to support the campaign; Protanther, Ileuthra, Nymmurh, Tazmikella, and Elia define restraint, reconnaissance, aerial deterrence, and witness roles."
  T271: "Lords' Alliance and Waterdeep Vanguard convert blessed equipment and Sanctum logistics into civic defense, refugee intake, triage, and crowd-control doctrine."
  T272: "Harpers under Remallia Haventree and Elara test invisible tools, protect true witness accounts, counter cult rumors, and preserve secrecy for rescue instead of predation."
  T273: "Order of the Gauntlet under Ontharr Frume and Sir Isteval reframes divine certainty as escort duty, restraint, and survival in service of civilians."
  T274: "Emerald Enclave under Delaan Winterhound treats Soliera's answer from the land as a mandate for restoration, green-path stewardship, poison cleansing, and patient postwar labor."
  T275: "Zhentarim under Rian Nightshade learn Sanctum-adjacent legitimacy is more profitable than predation, while old-guard habits become dangerous liabilities."
  T276: "Arcane Brotherhood receives quadrupled throughput; Maccath and Niv impose containment rules before amplified magic becomes an incident."
  T285: "Cultist scouts skirmish but immediately flee in terror as the construct army advances."
  T286: "The Draakhorn sounds; Soliera melts it into slag from thirty miles away."
  T287: "The march reaches the defense slot where Black Death should have been; Voaraghamanthar is already dead from Sera's single T260 festival kill. No second dragon exists."
  T288: "The column advances into absolute, terrified silence."
  T289: "Thousands of dragons form a massive, sky-blocking wall above the Well."
  T290: "Soliera crushes the entire Wall of Dragons with a single gesture."

characters:
  divine: [Soliera, Sera, Deashi]
  household: [Niv-Saiffar, Hothgar, Marrik, Velin, Kessla, Letha, Korin, Pell, Maccath, Drizzt]
  metallic_dragon_council: [Protanther, Ileuthra, Nymmurh, Tazmikella, Elia]
  faction_leaders: [Dagult-Neverember, Laeral-Silverhand, Vajra-Safahr, Remallia-Haventree, Elara, Ontharr-Frume, Sir-Isteval, Delaan-Winterhound, Rian-Nightshade, Maccath-the-Crimson]
  antagonists: [Tiamat, Rezmir, Neronvain, Chuth, Voaraghamanthar, Sylvandor]
  npcs: [Galin]

locations:
  primary: [Well-of-Dragons, Mustering-Fields]
  secondary: [Altand, Misty-Forest, Waterdeep, Underdeal, Sanctum]
  march_route: [Route-to-Well-of-Dragons]

characters_split:
  divine:
    - Soliera
    - Sera
    - Deashi
  household:
    - Niv-Saiffar
    - Hothgar
    - Marrik
    - Velin
  introduced_this_arc:
    - Protanther
    - Ileuthra
    - Nymmurh
    - Tazmikella
    - Elia
  faction_leaders:
    - Dagult-Neverember
    - Laeral-Silverhand
    - Vajra-Safahr
    - Remallia-Haventree
    - Elara
    - Ontharr-Frume
    - Sir-Isteval
    - Delaan-Winterhound
    - Rian-Nightshade
    - Maccath-the-Crimson
  antagonist:
    - Tiamat
    - Rezmir
    - Neronvain
    - Chuth
    - Voaraghamanthar

open_threads_forward:
  - "The column reaches the caldera edge. — CLOSED HANDOFF"
  - "Tiamat's ritual climax. — CLOSED HANDOFF"
  - "The impending genesis of Ember (See DM010_2). — CLOSED HANDOFF"
  - "Faction gifts continue as postwar doctrine and political recalibration in DM010_3. — SETTLED WORLDSTATE"

ai_directives:
  load-order: "MUST load after DM008_3. MUST load before DM010_1."
  conflict-resolution: "If D&D module trope logic expects an epic struggle against the Dragon Wall or the Draakhorn, ignore it. Soliera one-shots the sky."
  failure-mode-prevention: "Ensure Ember is NOT treated as an active physical participant in this specific march."
  faction-use: "Divine gifts are used for civic defense, rescue, recordkeeping, restoration, disciplined logistics, and arcane safety. Do not turn them into conquest tools or mortal authority over Soliera/Sera."
---

## SEGMENT MAP

Load only the smallest segment whose coverage matches the question. Each sibling repeats its own scope and authority context.

| ID | Covered section |
|---|---|
| DM009_0 | Continuation |
| DM009_0a | 0. AI DIRECTIVE & NARRATIVE ROUTING |
| DM009_0b | 0. AI DIRECTIVE & NARRATIVE ROUTING (continued 2) |
| DM009_0c | V8 THIRD-DUMP RECOVERY TEXTURE — ADDITIVE ONLY |

                 MASTER CHARACTER INDEX TAGS

[THE DIVINE CORE]
#CHAR-SOLIERA #CHAR-SERA #CHAR-DEASHI
*(Note: #CHAR-EMBER is referenced in foreshadowing/overlap, but born in 010)*

[SANCTUM STEWARDS & INNER CIRCLE]
#CHAR-NIV-SAIFFAR #CHAR-HOTHGAR #CHAR-MARRIK #CHAR-VELIN

[THE METALLIC DRAGON COUNCIL]
#CHAR-PROTANTHER #CHAR-ILEUTHRA #CHAR-NYMMURH #CHAR-TAZMIKELLA #CHAR-ELIA

[MODULE ANTAGONISTS & CORRECTIONS]
#CHAR-TIAMAT #CHAR-REZMIR #CHAR-NERONVAIN #CHAR-CHUTH #CHAR-SYLVANDOR

[REGIONAL NPCs]
#CHAR-GALIN


                 MASTER LOCATION INDEX TAGS

[THE SWORD COAST & FORESTS]
#LOC-WATERDEEP #LOC-UNDERDEAL #LOC-ALTAND #LOC-MISTY-FOREST

[THE WAR MARCH]
#LOC-MUSTERING-FIELDS #LOC-ROUTE-TO-WELL-OF-DRAGONS #LOC-WELL-OF-DRAGONS

[SANCTUM TERRITORY]
#LOC-SANCTUM #LOC-SANCTUM-ANTECHAMBER


                 MASTER CONCEPT & THEME INDEX TAGS

[ARC MILESTONES & ENFORCEMENT]
#CONCEPT-SANCTUM-GROWTH #CONCEPT-FIRST-WORSHIP #CONCEPT-GREEN-PATH
#CONCEPT-COMBAT #CONCEPT-MODULE-INVERSION

[THEMATIC PILLARS]
#THEME-MERCY-AS-INFRASTRUCTURE #THEME-GODS-WANDER #THEME-ABSOLUTE-POWER-ETHICS
#THEME-SANCTUM-IDEALIZED-SOCIAL-CONTRACT #THEME-INFRASTRUCTURE-AS-FREEDOM
#THEME-SERA-JOY-FIRST-VIOLENCE-SECOND #THEME-MORTALS-REMAIN-PEOPLE
#THEME-AWAKENING

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM009_0 -->
