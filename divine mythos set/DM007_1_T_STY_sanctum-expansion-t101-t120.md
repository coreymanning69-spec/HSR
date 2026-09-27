---
id: DM007_1
title: "Waterdeep Integration & Frostfell Approach"
type: beat
subtype: story-log
load_priority: load-after-DM006_0-before-DM008_1
canon: T
verse: Divineverse
timeline: T101–T120
beat_range: T101–T120
arc: sanctum-expansion-into-tyranny-of-dragons-onramp
era:
  - post-taliandra
  - waterdeep-beach
  - frostfell-arc
  - silverymoon-arc
status: hard-canon
authority: authoritative-for-T101-T120
updated: 2026-09-07
volatility: invariant
arc_scope: sanctum-expansion-into-tyranny-of-dragons-onramp
derived_from: null
predecessor_file: DM006_0
successor_file: DM007_2

xref_concepts:
  - knife-thought-edge-origin
  - xanathar-underdeal
  - auril-domain-rewrite
  - vajra-incident
  - waterdeep-beach-episode
  - sanctum-expansion
  - module-inversion
  - frostfell-arc

canon_flags:
  - Sanctum-is-NOT-a-cage-people-stay-for-logistics-and-consent
  - Knife-Thought-Edge-originates-here-at-T114-as-adaptive-fear-response
  - Sera-power-is-physics-not-magic-shockwaves-are-canon
  - Soliere-Dzan-is-intentional-spelling-do-not-autocorrect
  - Soliera-silence-is-active-action-not-absence
  - Auril-is-preserved-and-rewritten-not-killed
  - Xanathar-submits-and-lives-forming-the-Underdeal

load_after_if_needed:
  - DM031_0 # Divineverse Setting Changes — Faerûn, Underdark & Extraplanar Atlas
  - DM034_1 # Master Tagging & XREF Architecture Map

purpose: |
  Bridges the initial Sanctum building phase into the broader Faerûn political
  theater (Waterdeep, Silverymoon). Establishes how the Divineverse cast handles
  established D&D lore entities (Xanathar, Auril) and sets up the module intercept.

  Three load-bearing events:
  1. KNIFE-THOUGHT EDGE (T114) — Sera's terror at being too slow to protect Soliera
     from unannounced teleportation forces her powers to adapt. She now reacts to
     hostile intent before physical action.
  2. THE UNDERDEAL (T117.5-T118) — Xanathar is subdued instead of killed.
     The establishment of the Underdeal proves the Sanctum's approach to
     integrating/domesticating existing power structures.
  3. THE AURIL REWRITE (T120) — Soliera asserts total jurisdictional dominance
     over D&D gods by rewriting Auril's domain into winter's preservation rather
     than erasing her, proving power-as-mercy on a divine scale.

arc_summary:
  setup: >
    T101 — Sanctum continues its rapid expansion post-Taliandra. The divine trio
    begins shifting focus from local Underdark containment to broader geopolitical
    integration, testing how Faerûn's major powers handle sudden divine proximity.
  core_motion: >
    The party establishes a diplomatic footprint in Waterdeep, violently restructures
    Skullport by domesticating Xanathar to form the Underdeal, and flexes absolute
    jurisdictional override in the Frostfell by rewriting Auril's domain. Sera's
    power permanently adapts via the Knife-Thought Edge at T114.
  resolution: >
    T140 — A formal alliance with Silverymoon is struck as Soliera passively collapses
    their wards. Drizzt joins the household's orbit, and the party moves toward Greenest,
    actively intersecting the Tyranny of Dragons timeline with overwhelming force.

key_beats:
  T101:   "Sanctum expansion continues; post-Taliandra equilibrium established"
  T107:   "Waterdeep Beach Episode — casual divine presence in a mortal hub"
  T114:   "The Vajra Incident — teleportation fear triggers Sera's Knife-Thought Edge"
  T117.5: "Descent to Xanathar's Lair ('For Pell!')"
  T118:   "Xanathar submits; the Underdeal is established"
  T118.5: "Auril's hall walk (post-T123) — sees her dead cultists; departs when mortals appear"
  T120:   "Frostfell confrontation — Soliera rewrites Auril's domain without combat"
  T129:   "Arrival in Silverymoon — Soliera's presence collapses the Mythal wards"
  T138:   "Sword Coast dragon raids escalate (HOTDQ Onramp)"
  T140:   "Departure for Greenest; Drizzt joins the household orbit"

characters:
  divine:
    - Soliera
    - Sera
    - Deashi
  household:
    - Niv-Saiffar
    - Kessla
    - Korin
    - Marrik
    - Velin
    - Letha
    - Pell
    - Taliandra
  introduced_this_arc:
    - Vajra-Safahr
    - Dagult-Neverember
    - Alustriel-Silverhand
    - Drizzt
  antagonist:
    - Xanathar                # Domesticated, not destroyed
    - Auril                   # Domain rewritten, not destroyed

locations:
  primary:
    - Waterdeep
    - Underdeal (formerly Xanathar's Lair)
    - Silverymoon
  secondary:
    - Sanctum
    - Frostfell
    - Greenest

ai_directives:
  - LOAD-AFTER-DM006_0-BEFORE-DM008_1
  - ENFORCE-PHYSICS-FOR-SERA-SPEED
  - APPLY-KNIFE-THOUGHT-EDGE-MECHANICS-ONLY-AFTER-T114
  - SOLIERA-SILENCE-UNLESS-DM-VOICED
  - PRESERVE-QUOTE-ANCHORS-IN-PROSE
  - NO-GENRE-INFERENCE-DO-NOT-INVENT-MISSING-DETAILS

open_threads_forward:
  - Hoard of the Dragon Queen interception at Greenest — CLOSED HANDOFF to DM008_1
  - Drizzt's household integration — SETTLED THROUGH LATER PLAY; future visits optional
  - Knife-Thought Edge mechanics — SETTLED RULE, not an open thread
---

# DM007_1 — WATERDEEP INTEGRATION & NORTHERN COURT DIPLOMACY

## HARD CANON NOTES

1. This file is authoritative for T101–T140.
2. SCALPEL protocol: verify and read only; no new canon without DM confirmation.
3. These are story beat summaries and anchors — full prose exists separately; absent scene detail is unspecified, not non-existent.
4. Cross-verse contamination is prohibited; this file governs T-verse Divineverse beats only.
5. The Sanctum is NOT a cage — exits are always available; residence is consent or logistics.
6. Physics law: Sera's power is speed and density, not magic. Shockwaves, air displacement, and friction burns are real consequences of her movement.
7. Knife-Thought Edge (T114): Sera's adaptive response to Vajra's unannounced teleportation. Reads hostile intent before physical action, at any distance. Not a spell or granted power — it emerged from terror of being too slow to protect Soliera.
8. The Xanathar Correction ("For Pell," T117.5): An execution, not a boss fight. Xanathar submits; the Underdeal is born. He is NOT killed.
9. Auril Redemption (T120–T122): Soliera rewrites Auril's domain to winter's preservation; she does NOT destroy Auril. This canonically establishes Soliera's absolute jurisdictional override of native D&D gods.
10. Soliere-Dzan is an intentional proper noun — not a misspelling of Soliera. Do not autocorrect.


                         ERA: POST-TALIANDRA GRIEF
                              (T101-T103)


T101: Sorrow in the Sanctum #CHAR-SOLIERA #CHAR-SERA #CHAR-TALIANDRA #CHAR-PELL #CHAR-VELIN #CHAR-NIV #CONCEPT-DIVINE-GRIEF #LOC-SANCTUM

Soliera and Sera remain secluded in their chamber for nearly two days—paralyzed by
Tali's decision to stay behind as Matron of the Drow city (Soliere-Dzan). No speech,
no movement; emotional gravity holds the room in stasis. The absence is a wound even
gods cannot ignore.

They are not angry at Taliandra. Until this moment, everything they gathered was
kept. Tali is the first person to receive everything they offered and choose
something else while remaining theirs, Sanctum-adjacent, and reachable. Their
emotional architecture has no shelf for "she's ours, but she's not here." The grief
is a missing category, not a punishment for her choice.

BEHAVIORAL DETAIL:
- Sera didn't let the door open—not magically (she has no magic or reality warping
  powers) but simply by telling everyone "no" before they knocked.
- Only three people would come anyway: Niv, Velin, and Pell. Everyone else wouldn't
  feel comfortable approaching.
- This is the first time since Sera's creation that she has been emotionally
  paralyzed. Her usual joy-first enforcement mode is suspended.
- Soliera's stillness here is NOT absence—it is processing a chosen separation for
  which neither woman has an internal category.

THEMATIC NOTE: Taliandra's departure proves that Soliera's "divine math" can be
refused. Someone can choose NOT to stay in paradise. This is foundational for
understanding why Soliera later develops more nuanced approaches to attachment.

CROSS-REF: #ARC-TALIANDRA (T34-T100), #LOC-SOLIERE-DZAN, #THEME-DIVINE-MATH


T102: The 300,000 Festival #CHAR-SOLIERA #CHAR-SERA #CHAR-DEASHI #CONCEPT-SANCTUM-GROWTH #LOC-SANCTUM #LOC-SPINE-OF-THE-WORLD

After emerging from mourning, Soliera turns outward. The Sanctum has reached
approximately 300,000 souls across roughly 21 cubic miles of mountainous caverns.
A celebration is warranted.

FESTIVAL BEATS:
- Sera jumps from the top of the mountain and craters the majority of a peak into
  a caldera—this becomes the festival grounds.
- Soliera, Niv, Sera, stewards, and common citizens all form the festival areas
  together.
- Soliera introduces Deashi publicly and speaks to everyone gathered, apologizing
  for being distant during the Taliandra arc.
- This is one of the rare moments Soliera speaks at length to a crowd.

INFRASTRUCTURE NOTE: The festival demonstrates Sanctum's self-sufficiency. Food,
entertainment, shelter—all provided without strain. The "numbers go up" handwave
from T11 pays off here; logistics are solved.


T103: Windows and Rest Days — Soliera's Middle Ground Develops #CHAR-SOLIERA #CHAR-PELL #CHAR-HALF-ORC-STEWARD #CONCEPT-WINDOWS-WISH #LOC-SANCTUM

Soliera wanders the halls after the festival, processing. She finds Pell and a
half-orc worker sitting at a table together—two people who would never have met
outside the Sanctum's structure.

THE WINDOWS WISH:
- The half-orc steward petitions for "weekends"—a 2-day rest cycle for workers.
- Pell had previously wished for windows—literal sunlight frames in mountain stone.
- Soliera grants both. Folded reality portals now function as "windows" showing
  external views. Rest days become institutionalized.

THEMATIC NOTE: This beat shows Soliera developing her "middle ground"—caring about
the small comforts that make life livable, not just survivable. The half-orc and
Pell represent mortals who can ask for things and receive them without being
"special" in any cosmic sense.

CROSS-REF: #THEME-INFRASTRUCTURE-AS-FREEDOM, #RULE-SANCTUM-FREEDOM-NO-PREDATION


                         ERA: WATERDEEP ARRIVAL
                              (T104-T114)


T104: Departure for Waterdeep #CHAR-SOLIERA #CHAR-SERA #CHAR-PELL #CHAR-LETHA #CHAR-KORIN #LOC-SANCTUM #LOC-TRAVELING

Sera grows restless after the festival. Pell mentions the beaches of Waterdeep as
an interesting spot she'd heard about. Sera loves the idea immediately.

PARTY COMPOSITION FOR WATERDEEP:
- Soliera (silent, observing)
- Sera (excited, leading)
- Pell (nervous but game)
- Letha (handling logistics and conversation)
- Korin (protection and navigation)

MODE OF TRAVEL: Divine sleigh—radiant, gold-inlaid vehicle symbolizing motherhood
and power. Used for dignified travel across harsh terrain.


T105-T106: Travel and Transition #CHAR-SOLIERA #CHAR-SERA #LOC-TRAVELING #LOC-BRYN-SHANDER

The party travels south via divine sleigh. Korin handles introductions at various
stops. Letha manages conversations as the Girls observe. This is slice-of-life
travel—no major conflicts, just the world adjusting to divine presence moving
through it. Along the way, Sera enjoys the sights and asks the party members questions and they even camp once, so Sera can "rough it". It goes well, the party bonds.

ENVIRONMENTAL NOTE: The sleigh is parked on Waterdeep's beach upon arrival—immune
to damage, a symbol of divine power and travel capacity. Constructs establish a
perimeter. Early mortal reactions range from awe to confusion.


T107: Beach Arrival — The Divine Beach Episode #CHAR-SOLIERA #CHAR-SERA #CHAR-PELL #CHAR-LETHA #CHAR-KORIN #LOC-WATERDEEP-BEACH

The divine sleigh glides into Waterdeep under dawn's hush. Classic anime beach
episode turned divine.

SCENE DETAILS:
- Sera: topless, feral glee in the water, experiencing waves for perhaps the first
  time since her transformation.
- Soliera: modest divine beauty, quiet curiosity, observing mortal reactions.
- Pell: overwhelmed but enjoying herself.
- Letha: managing social dynamics, explaining to confused locals.
- Korin: alert, protective, slightly amused.

MORTAL REACTIONS: A communal day of laughter and peace while the city quietly fears
the implications of gods on their shore. Guards are dispatched but don't know what
to do. No one approaches directly.


T108: Project X Tavern Night #CHAR-SERA #CHAR-LETHA #CHAR-SOLIERA #LOC-WATERDEEP #CONCEPT-PROJECT-X-PARTY

Evening brings the party to an upscale tavern. What follows becomes legend.

THE LETHA BEAT:
- Letha's divine lute (Sunset) shakes the building's foundation.
- The music is not just entertainment—it's a soft power demonstration.
- The crowd experiences genuine joy in the presence of the divine.
- Sera carries a keg above her head at one point, amusing herself and terrifying
  anyone who understands what her casual strength implies.

AFTERMATH: This becomes a "mythic event" that commoners reference. The first night
when Waterdeep got to see the joy of being in the gods' presence.


T109-T110: City Wandering and Observation #CHAR-SOLIERA #CHAR-SERA #LOC-WATERDEEP

The days following the tavern party involve exploration. Sera experiences mundane
mortal foods and social structures, bringing chaos and laughter. Soliera observes
calmly, letting them live under her watchful presence.

BLUE SIGIL SIGHTING: During wandering, they notice a cold-blue sigil appearing in
various locations. When mentioned, locals say it's from up north—the faith of an
entirely new goddess (Auril) is growing in popularity. This plants the seed for the
Frostfell arc.


T111: Guard Encounter and Escort #CHAR-SOLIERA #CHAR-SERA #CHAR-KORIN #LOC-WATERDEEP

After the tavern event, guards intercept the party. This is not hostility—it's the
city's power structure attempting to understand what has arrived.

The party is escorted toward Lord Neverember's estate. Letha handles conversation.
The Girls are content to observe the city's nervous response.


T112-T114: Neverember Estate Sequence #CHAR-SOLIERA #CHAR-SERA #CHAR-DAGULT-NEVEREMBER #CHAR-KORIN #CHAR-LETHA #CHAR-PELL #LOC-NEVEREMBER-ESTATE

T112: ARRIVAL

SERA'S PROTOCOL ENFORCEMENT:

The ride to the Estate, Neverember's - all the way around Neverwinter - was pleasant. The path to his actual house was lined with bush and hedge. All pretty and pleasing, Sera cooed in agreement with Soliera's silent positive judgement of the area.

When they arrived at the landing area and were being greeted; Sera hopped off the carriage and immediately made everyone bow before Soliera
stepped down. She didn't think it was acceptable for people to see Soliera turned
around, stepping down, as if following in Sera's footsteps. Sera only permits
certain introductions.

They arrive and enter the manor/estate—massive and though the estate were impressive, the overall quality was leagues below what the Girls had at the Sanctum. Sera makes herself
at home immediately. Pell follows Letha. Soliera wanders. Korin chats with Lord
Neverember directly.


QUOTE ANCHOR: This was the first sign for Neverember that he was dealing with
aspects he couldn't understand or control.


T113: Feasting and the Question #CHAR-SOLIERA #CHAR-DAGULT-NEVEREMBER #CHAR-SERA

Conversation got boring quickly. Food was finished. Sera ate everything; Soliera
munched on bread. The "adults" (Korin, Letha, etc.) conversed with Neverember.

THE RARE SPEECH:
Soliera looks at Neverember. Conversation stops. She asks him, in a rare moment
of speech: "What do you want?"

NEVEREMBER'S RESPONSE: "I need time to see my things come to an end, my Lady Soliera."
- He was half a second from prostrating but knew that would be more unacceptable
  than replying from his current position.
- Sera laughs ecstatically—she loves when Soliera takes part in things.

SOLIERA'S ACTION: She raises her hand. Guards attempt to think about intervening
for a split second. Sera looks at the commander. Soliera remakes Neverember—similar
to Korin's transformation. He is healed, rejuvenated, granted decades of additional
life.


T114: The Vajra Incident — Knife-Thought Edge Formation #CHAR-SOLIERA #CHAR-SERA #CHAR-VAJRA-SAFAHR #CHAR-DAGULT-NEVEREMBER #CONCEPT-KNIFE-THOUGHT-EDGE #LOC-NEVEREMBER-ESTATE

THE TELEPORTATION:
Vajra Safahr (Blackstaff of Waterdeep) teleports into the room unannounced.

SERA'S REACTION:
Sera reacts instantly, grabbing Vajra by the throat as she materializes. To Sera,
this was an affront to her role as protector—someone appeared near Soliera without
warning.

THE CRITICAL MOMENT:
Korin yells "STOP!" at everyone attempting to react. Soliera lowers her eyes and
goes back to eating bread. Sera lets Vajra go. Vajra pukes. Stewards and Neverember
rush to help her. Letha explains the situation while the Girls wander off to see
the otters.

KNIFE-THOUGHT EDGE FORMATION:
This moment crystallizes Sera's terror into power. Explicitly, Knife-Thought Edge
forms as a reaction to Vajra using teleportation and entering Soliera's space.
Sera was there near-instantly, but to her, that time was enough to act—which means
someone else could have done the same thing in that window.

That fear, that perceived failure, led her main ability—Adaptation for God's
Protection—to generate the ability to read the intention of others if it's related
to her God, over any space, at any distance.

MECHANICAL DEFINITION:
- Knife-Thought Edge: Sera acts on intent, not action. She is never surprised,
  never outpaced. The moment danger forms as a thought, she is already countering it.
- This is NOT magic. It is divine adaptation born from love expressed as fear.


T114.5: The Burning and the Cost #CHAR-SERA #CHAR-SOLIERA #CHAR-KORIN #CHAR-LETHA #CHAR-PELL #LOC-NEVEREMBER-ESTATE

After the Vajra incident, the party wanders to see the otters. At the gate, trouble
starts. A few of the other rich lords come to posture, to find out who is visiting
and what noble house they're backing.

THE TRIGGER:
They burn a bush. Sera and Soliera wander peacefully over. Neverember's staff freaks
out. A bird drops from the sky—the same bird family that Soliera watched as they
rode into the estate.

Soliera frowns.

THE CONSEQUENCE:
Sera slaughters everyone involved and makes a nice neat path through the bodies for
Soliera to walk. The path is exactly three feet wide. Otherwise, the bodies are left
where they fell.

AFTERMATH:
- Korin, Letha, and Pell are there to make things make sense.
- This is the first time of many the Sanctum has to fix the Girls' wake.
- The second and third wealthiest lords of Waterdeep are dead, along with their
  entourage, for disrupting Soliera's observation of birds.
- The Sanctum already has an Embassy in the northern towns, various stewards arrive and start the process.
THEMATIC NOTE: This beat demonstrates the inescapable consequence layer—mortals
learn that while the gods are content, peace reigns. Disobedience or disruption
is annihilation. Soliera restored the hedges and birds, but with constructs, not
souls. A direct lesson: consequences are real, swift, and final.


                         ERA: WATERDEEP EMBASSY & UNDERDEAL
                              (T115-T118)


T115: The Waterdeep Embassy Established #CHAR-SOLIERA #CHAR-SERA #CHAR-VAJRA-SAFAHR #CHAR-KESSLA #CHAR-VELIN #CHAR-PELL #LOC-WATERDEEP #CONCEPT-WALKING-GOD-CHURCH

With political formalities completed, Soliera's embassy is founded. The location is
in the old Thieves' Guild tunnels—below ground, retrofitted with cleaning and
maintenance constructs.

EMBASSY STAFF:
- Kessla: Manages city politics and spymaster duties (she exists in the background
  of the earlier sewer scenes, watching)
- Velin: Organizational logistics
- Pell: Emotional anchor and mortal-scale interface

POLITICAL LANDSCAPE:
- Blackstaff Vajra becomes a cautious ally after surviving Sera's intervention.
- Harpers and Lords' Alliance observe but don't interfere.
- The Masked Lords are recalibrating their understanding of power in the city.

THE WALKING GOD CHURCH:
Word spreads of Soliera's presence. A church of the "Walking God" is spreading at
a rate no other individual god can claim. This is organic, not mandated—people who
witnessed her actions tell others.


T116: Auril Cult Plot Revealed #CHAR-SERA #CHAR-SOLIERA #CONCEPT-AURIL-CULT #LOC-WATERDEEP

Signs of sabotage and unnatural cold sweep the city—Auril cultists attempt an
assassination on Soliera's group during a market stroll.

SERA'S RESPONSE:
She intervenes, crushing the plotters in a silent, precise fury. Not playful. Not
joyful. Just efficient elimination of threat.

SOLIERA'S MOOD:
Growing annoyed with this goddess of frost and her many small bothers. The blue
sigils they've been seeing are confirmed as Auril's mark.

SERA'S POSITION:
Straight ready to destroy the entire cult and their goddess. She's been wanting
an excuse.


T117: Xanathar and the Underdeal — Pell's Affliction #CHAR-SERA #CHAR-SOLIERA #CHAR-PELL #CHAR-LETHA #CHAR-KORIN #CHAR-NIHILOOR #CHAR-XANATHAR #LOC-UNDERDEAL

Investigation leads below. Sera, Letha, Korin, and Pell descend into Waterdeep's
sewers, confronting Xanathar's guild.

FIRST CONTACT — THIEVES' GUILD NODE:
The party clears the sewers and converts various smaller groups of thieves to their
side. Soliera actually blesses a large group of them. Sera walks around flirting
and having a good time.

NAMED NPCs ENCOUNTERED:
- Caliseya: Tiefling broker, golden eyes, eventually sits cross-legged sipping tea
  and says "Never thought I'd be sharing a table with a goddess..."
- Threlk: Githyanki lieutenant, warns about frost cult starving trade routes
- Rask: Half-Orc enforcer, scarred hands, says "Thanks for... letting us live."
- Rillen: Halfling, manages safehouse operations with his twin

PELL'S AFFLICTION:
Due to a dice roll, Pell is afflicted with a Mind Flayer's mental trap and collapses.
The Mind Flayer responsible is Nihiloor—a named, canonical Waterdeep: Dragon Heist
villain now operating in this timeline.

SOLIERA'S RESPONSE:
She undoes the trap, blesses Pell so it can never happen again, and is visibly
upset that someone would be stupid enough to harm her weakest companion. This is
one of the few times Soliera shows open anger.

THE XANATHAR DEMAND:
Someone reminds them of Xanathar. Everyone gets silent. Sera laughs—wants to meet.
She is told that no one meets him, to which she replies: "That's unacceptable."


T117.5: The Descent — "For Pell!" #CHAR-SERA #CHAR-SOLIERA #CHAR-XANATHAR #CHAR-NIHILOOR #CHAR-LETHA #CHAR-KORIN #CHAR-PELL #CONCEPT-FOR-PELL #LOC-XANATHAR-LAIR

Xanathar sends a representative. That is also unacceptable. He opens a door in the
wall, hoping for cat and mouse.

SOLIERA'S PERCEPTION:
She rolls a spot check with +20 and looks through the floors, finding him directly.

SERA'S APPROACH:
She goes to the corner and punches down, breaking row after row of dungeon floor
until she's on the last level with the main bosses. Soliera walks calmly in the
air behind her.

QUOTE ANCHOR — SERA:
"For Pell!"

She proclaims this as she tears through Mind Flayer and guild alike. Sera takes
Nihiloor by the head and crushes it. There is no roll or contest. Soliera is
present for the kill; Letha, Korin, and Pell remain above securing the cleared
areas. Sera carries the body to Xanathar.

COMBAT NOTE: Letha and Korin work above with the new recruits and with Pell,
securing the cleared areas while Sera handles the vertical assault.


T118: Dominion and Renewal — Xanathar Subdued #CHAR-SOLIERA #CHAR-SERA #CHAR-XANATHAR #LOC-UNDERDEAL #LOC-XANATHAR-LAIR

Sera hand-delivers Nihiloor's body to Xanathar and offers him an ultimatum.
Xanathar is the confirmed recipient and witness to the delivered result.

XANATHAR'S CHOICE:
He accepts. Becomes an orphan/city handler for the good of the Sanctum. The Embassy
now flows downward and covers the entire Underdeal into the very layer of Xanathar
himself.

TRANSFORMATION OF SPACE:
Food, warmth, and safety replace crime and exploitation. Sera enforces the new
order; mortals are awed. Constructs clean and maintain. The Underdeal becomes
a Sanctum-controlled sanctuary.

INFRASTRUCTURE NOTE: The Underdark <--> Sanctum <--> Rest stop <--> Waterdeep
Embassy <--> Undermountain route is planned for underground expansion.


T118.5: Auril's Hall Walk [POST-T123] #CHAR-AURIL #CHAR-SOLIERA #CHAR-SERA #LOC-LOWER-HALLS

POSITION NOTE: This event occurs after the Frostfell truce (T123). Indexed here
for continuity with the Underdeal arc it closes; the narrative slot is immediately
post-return from Frostfell.

After the truce is sealed and Soliera and Sera return from the Frostfell, Auril
comes back with them — not summoned, not escorted. The invitation is casual:
come see what's up. She accepts.

THE LOWER HALLS:
They bring her through the tunnel sections near the cult site — the same passage
where Sera worked down the line of cultists at T119 before Auril's avatar formed.
The bodies are still here. Her people: the true believers who stood in that row
and died waiting for her to come, thirty-odd of them. The coerced mothers and the
children were pulled out and spared before Sera started. These were not.

Auril sees them.

She doesn't speak. She walks the passage slowly. A few minutes, nothing more.
Cold mist at her ankles, contained. She is the goddess of winter moving among
the dead who prayed to her — who died in the act of summoning her, because of her
avatar's formation, because of what she is. She came. Just not in time to save
them. Or she came and that's exactly why they're dead, depending on the angle.

Soliera doesn't explain it. Sera doesn't fill the silence.

THE MORTALS:
Hall traffic begins — constructs, staff, Sanctum residents moving through on
ordinary business. The halls don't stay empty long.

Auril does not engage. She simply stops walking.

AURIL'S EXIT:
She goes. No drama, no declaration, no parting word. She was finished, or she
didn't want to be seen, or both. The mist clears a little behind her.

The moment is not announced. It happened.


                         ERA: FROSTFELL CONFRONTATION
                              (T119-T123)


T119: Auril's Portal — The Descent Begins #CHAR-SERA #CHAR-SOLIERA #CHAR-AURIL #LOC-UNDERDEAL #LOC-FROSTFELL

They travel deeper into older tunnels. The Cultist base is here—this was the main
reason they were coming into the sewers. The Xanathar escapade was because the
monsters overstepped their bounds.

SERA'S APPROACH:
Sera starts killing. Soliera saves the children.

THE MOTHERS:
Sera asks the mothers how they thought letting children turn blue and nearly freeze
constantly is the right thing to do. No one can answer with anything Sera wants to
hear.

SOLIERA'S TRIAGE:
She saves a few mothers who looked coerced, plus all infants and young children.

SERA'S ULTIMATUM:
She lines the rest of the cultists up. She asks them:

QUOTE ANCHOR — SERA:
"How many of you in a row do I have to kill before your goddess actually comes
and saves you?"

She starts. Making her way down. About thirty in, a dice is rolled, and an avatar
of Auril forms.

COMBAT:
Sera defeats the avatar. But Soliera walks over to it and calls out to Auril:

QUOTE ANCHOR — SOLIERA:
"False God. Weakness of Winter. Mother of Nothing. Failure of Frost."

To Soliera, these are about the most fighting words she can say.

A portal opens.


T120: Stepping into Frostfell #CHAR-SOLIERA #CHAR-SERA #LOC-FROSTFELL

The party enters the Frostfell—an alien, glittering wasteland of silence and holy
ice. The boundary between mortal and divine thins.

ENVIRONMENTAL DESCRIPTION:
The scale is maddening—literal miles of perfectly flat ice with mountains the size
of giants' teeth looming in the distance. Sera's breath hangs in the air as Soliera
steps forward, unreadable.

AURIL'S GAMBIT:
Auril drops them into a random desert of ice, far from her throne. Sera laughs.
Soliera is not impressed.

SOLIERA'S RESPONSE:
She looks at Sera. Sera grins.
Soliera grows.

SCALE:
Twelve miles tall. Above mountain height. Sera grasps a hair and rides Soliera
as she crushes mountain ranges and leaves a mile-deep imprint in the Frost
Goddess's realm.

They walk to Auril's throne.

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM007_1 -->
