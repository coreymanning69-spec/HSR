---
id: DM005_0
title: "Sanctum Foundation & The Remaking"
type: beat
subtype: story-log
load_priority: load-after-DM004_1
canon: T
verse: Divineverse
timeline: T0–T50
beat_range: T0–T50
arc: sanctum-foundation
era:
  - pre-waterdeep
  - ten-towns
  - travel
  - underdark
status: hard-canon
authority: authoritative-for-T0-T50
updated: 2026-09-17
volatility: invariant
arc_scope: sanctum-foundation
derived_from: null
predecessor_file: N/A
successor_file: DM006_0

xref_concepts:
  - sanctum-foundation
  - early-saga-compression
  - consent-architecture-origin
  - worth-pricing-abolition
  - hothgars-hoard-logistics
  - sera-mark
  - letha-introduction
  - deashi-first-appearance
  - household-forming
  - taliandra-arc-begins
  - sanctum-is-infrastructure
  - divine-domesticity

canon_flags:
  - Knife-Thought-Edge-does-NOT-exist-before-T114.5
  - Letha-introduction-arc-T19-T35-has-full-prose
  - Tali-asymmetric-treatment-is-intentional-not-error
  - Deashi-NEVER-voiced-in-any-session
  - T0-T50-is-approximately-ten-to-one-compressed-against-played-sessions

load_after_if_needed:
  - DM031_0 # Divineverse Setting Changes — Faerûn, Underdark & Extraplanar Atlas
  - DM034_1   # XREF Map

purpose: |
  First narrative beat file. Covers the Sanctum's founding arc
  (T0-T50) — the moment the world begins to organize itself around
  the girls' presence. Distinct from all other beat files in that
  it establishes the base grammar everything downstream depends on:
  the Sanctum is sentient and sovereign, Deashi is the counterbalance
  and cannot be overstated, the household forms through asymmetric
  welcome rather than equal invitation, and Soliera's omnipotence
  functions as infrastructure from the very first beat.

  This arc is also where Letha's full introduction lives (T19-T35,
  full prose written). That prose is the canonical source for Letha's
  character grammar — her comfort with divinity, her calibrated
  response to Deashi's pressure, her role as the household's
  translator function.

arc_summary:
  setup: >
    T0 — The world before the Sanctum is formalized. Yuium awakens;
    Soliera and Deashi form as the functional divine pair. The Sanctum begins as a
    mountain and becomes a living architecture. Ten-Towns is the
    entry point for mortal contact.
  core_motion: >
    Mortals encounter the divine for the first time in an intimate
    context. Taliandra's arc begins. The Sanctum establishes itself
    as sovereign territory — not a fortress, not a temple, but
    infrastructure. Letha is introduced. The household begins to form.
  resolution: >
    T50 — Sanctum is operational. The household has taken rough shape.
    Taliandra's position (and its complications) is established.
    The girls are home. The world knows they exist.

key_beats:
  T0:   "Divineverse origin — Yuium awakens in the Spine of the World"
  T5:   "Ten-Towns entry / first mortal contact"
  T19:  "Letha introduction begins"
  T35:  "Tali's cold reception — the asymmetric welcome is established"
  T38:  "Sanctum revealed as the entire mountain"
  T39:  "Niv + Velin introduce themselves — melting pot principle"
  T40:  "Antechamber — Deashi's presence overwhelms Letha and Tali"
  T41:  "Soliera clarifies Deashi: 'the other half — might even be stronger'"
  T43:  "Letha rises / Tali kneels — asymmetric household grammar begins"
  T44:  "Letha explores Sanctum at night — realizes it's sentient"
  T47:  "Sera + Soliera leave to wander / Velin releases Tali"
  T50:  "Arc close — Soliera's divine math shifts, Tali now 'worthy'"

characters:
  divine:
    - Soliera
    - Sera
    - Deashi
  household_forming:
    - Velin
    - Niv
    - Letha
    - Taliandra
    - Korin
    - Marrik
  introduced_this_arc:
    - Letha      # T19-T35 full introduction arc
    - Taliandra  # Tali's arc begins here, asymmetric welcome
    - Deashi     # first Antechamber appearance (T40); established from T1

locations:
  primary:
    - Sanctum               # entire mountain, sentient architecture
    - Antechamber           # Deashi's throne + crystal pillar
  travel:
    - Ten-Towns             # entry point, mortal-contact zone
    - Underdark-adjacent    # era geography

ai_directives:
  - LOAD-AFTER-DM004_1
  - KNIFE-THOUGHT-EDGE-DOES-NOT-EXIST-IN-THIS-ARC
  - DEASHI-NEVER-VOICED
  - LETHA-T19-T35-HAS-FULL-PROSE-DO-NOT-INVENT
  - TALI-ASYMMETRIC-TREATMENT-IS-INTENTIONAL
  - SANCTUM-IS-INFRASTRUCTURE-NOT-FORTRESS

open_threads_forward:
  - Taliandra's arc continues into DM006_0 — CLOSED HANDOFF; resolved at T100
  - Sanctum sentience is load-bearing for all future Sanctum beats — SETTLED RULE
  - Household grammar established here governs all domestic scenes downstream — SETTLED RULE
---

## SEGMENT MAP

Load only the smallest segment whose coverage matches the question. Each sibling repeats its own scope and authority context.

| ID | Covered section |
|---|---|
| DM005_0 | DM005_0 — SANCTUM FOUNDATION & THE REMAKING |
| DM005_0a | T11: Foundations — The Sanctum Begins to Live #LOC-SANCTUM #CONCEPT-SANCTUM-FOUNDERS |
| DM005_0b | T19: Letha Joins #CHAR-LETHA #CHAR-SERA |


# DM005_0 — SANCTUM FOUNDATION & THE REMAKING

## LOCAL CANON LOCKS

1. The Remaking (T10): Reva's transformation into Sera sets the psychological baseline for all divine enforcers. She asks for everything, receives it, and her identity becomes utterly linked to Soliera's will.
2. Divine Domesticity baseline: The gods do not demand temples — they demand infrastructure and useful existence.
3. **Compression disclosure:** T0–T50 is approximately 10:1 compressed against the
   played sessions. Summary lines are retrieval anchors, not complete scenes. Horror
   tends to survive compression while warmth and witness-interiority disappear first;
   any Rev8 expansion must restore both the event and the mortal experience of it.
4. **Day-by-day chronology:** Unless a timeskip is explicitly declared, the story
   advances through lived days. T0–T520 spans roughly seven years. Travel therefore
   contains scenery, settlements, meals, rests, ordinary encounters, and conversation;
   no exact duration may be invented where the source does not supply one.
5. **Founding-era voice:** Soliera speaks more freely in these early beats. Do not
   retroject her later word-sparse household register into T0–T50.

## REVISION 8 REREAD STATUS — T0–T50

The Rev8 local-corpus reread has examined T0–T40. T36–T40 are supported by the
existing canonical beat records: trade routes and divine economy, the Auril
tithe encounter, the Sanctum/Cairn arrival and Sera's mark, the Melting Pot, and
the Antechamber encounter. No missing scene prose is invented. The original
corpus was compressed under an approximately 128k-token container; Rev8 is the
standardization-and-restoration pass that pays those container-shaped omissions
back where authoritative material exists.

Four canonical POV renders were produced during the reread but are not contained
verbatim in the supplied delta: Letha T19–T21; Letha T27–T31; Korin T27–T31; and
Taliandra from the pre-T34 trail through T35. Their recovery summaries are
authoritative routing notes, not substitutes for the missing full prose. The
2026-07-26 Founding Corpus injection supplies behavioral and chronology corrections
through T50, but not the missing POV prose or an exact daily incident ledger. This
file encodes the recovered facts and preserves those prose gaps.


T0: Awakening in the Spine #CONCEPT-YUIUM #LOC-SANCTUM #LOC-SPINE-OF-THE-WORLD

    The story begins with the awakening of Yuium (the DM/GM figure) deep within the Spine of the World mountain range.
    He exists as a liquid black void contained within a large, perfectly formed pillar of white/clear crystal.
    Yuium is able to shift and move freely inside this incredibly dense crystal, demonstrating that he originates from another plane of existence and uses this pillar merely as an anchor point.
    This state establishes him as a concept literally above the world he inhabits; Soliera and Deashi are merely small fragments of his actual power.

    NOTE: This structure ensures a "nuclear option" against Elder Gods or Ao if necessary.

## T1: Fragments Made Flesh #INTRO #CONCEPT-FRAGMENTS #CHAR-SOLIERA #CHAR-DEASHI

    Soliera and Deashi form as Yuium's two equally aware halves: Soliera as Ego/Superego, Deashi as Id.
    Both initially appear as 9ft tall skeleton/construct/stone amalgamations.
    Soliera: Embodies the understanding of empathy, sympathy, context, feelings, and thoughts.
    Deashi: Embodies physical might, rule through force, and unyielding, unreasonable power.
    Deashi possesses a skeletal carapace with dark blue and black fluid/inlay runes.
    Deashi is utterly silent; his footsteps are pressed into the earth due to his bulk, focused entirely on the soles of his feet.
    The two bond closely despite Deashi’s lack of speech; Soliera learns to communicate via lights until she encounters humanity.

## T2: The Veiled Eye & First Foundations #CONCEPT-VEILED-EYE #CONCEPT-SANCTUM-GROWTH

    Deashi and Soliera wander the mountains, observing small animals and eventually locating the first Tribal Village.
    The Veiled Eye: Yuium develops a mechanic where any location Soliera or Deashi visit becomes permanently observable ("Fog of War" clearing).
    This sight allows Yuium/Deashi to track anything within their domain, regardless of distance.
    Sanctum Structure: The Sanctum begins to form as a wagon wheel with six spokes (Hallways) and an inner center (The Antechamber).
    The Veiled Eye feeds information directly to Deashi and Yuium, purposely leaving Soliera out of the loop so she can learn organically.
    The Sanctum physically expands in response to Soliera’s conceptual understanding; grasping ideas like justice or commerce manifests new halls.

> **REFERENCE-LAYER CLARIFICATION (2026-07-22):** This played beat remains the owner of the
> Veiled Eye's footprint and Soliera-exclusion law. In current ontology, “YUIUM” here names
> the distributed Whole/substrate expressed through Deashi, not a separate post-split
> observer. Deashi's awareness of an enrolled location is atemporal. Soliera still receives
> none of that feed. Likewise, T1's Ego/Id wording records the early shorthand; DM042_0 §6 owns
> the separated Jungian/Freudian mapping.

## T3: The Mother’s Form  #CHAR-SOLIERA #CHAR-DEASHI

    Soliera adopts a specific maternal form: firm breasts, large hips, and warm golden-tan skin.
    She wears thin, detailed robes evocative of a "best friend's mom"—attractive and commanding respect, yet inducing a sense of guilt in those who stare.
    This form was chosen based on observation: children respected it, men viewed it with kindness/appeal, and older women respected it.
    The prior decision was simpler than the observation: she knew she had to look
    human. What she built on top of that was a woman who has borne and nursed many
    children — wide-hipped, heavy-breasted, over-the-top beautiful in a way that
    reads as safe before it reads as anything else.
    Deashi remains a large, imposing, monster-machine hybrid (9ft, 700-800lbs).
    The Sanctum continues to grow, adding sconces of light, temperature control, and breathing with its own will.

### ERA: THE PILGRIMAGE

## T4: First Worship & The Warmth #CHAR-SOLIERA #CHAR-DEASHI #LOC-FIRST-VILLAGE #CONCEPT-FIRST-FESTIVAL

    They visit the tribal village; the locals' reaction shifts from fear to understanding, and finally to bonding.

    First Divinity: Soliera notes the freezing children, their suffering and their
    inability to thrive, and speaks. She takes the cold out of the village's
    territory — a spoken command, not a radiance. The ground softens underfoot
    within the hour. Things begin to grow that have no business growing there.
    The village itself is small, nomadic, and of the northern glacier country:
    thirty to forty people including elders, with no fixed location and no name.
    It is not a place but a group of people who winter where the ice permits.
    Soliera and Deashi stay about three or four weeks. The off-season First
    Festival takes place at a seasonal gathering ground the group returns to,
    making the celebration findable by Marrik and later vulnerable to raiders.
    Plants grow easily around Soliera, while wildlife avoids the area due to Deashi’s overbearing presence.
    The region becomes visibly healthier and more prosperous around them: more food than expected, more pregnancies, and a sense that the village has been touched by something worth gathering around.
    This prosperity creates the off-season First Festival, the earliest social shape of Soliera's worship before anyone has language for it.
    Birth, death, and creation sit under Soliera's domain, and the village is the
    first place it shows. Babies come healthy. Pregnancy stops being a risk
    calculation and becomes a welcome one. There is simply more sex because the
    usual negative consequences have quietly been removed. Nobody in the village
    can name the cause; they notice only the absence of the usual losses.
    Deashi evaluates the hunters and finds them lesser, making no changes to his own form.
    The hunters eventually ask Deashi to join a hunt; he learns stealth, wind direction, and projectile combat (bows) from them.

## T5: Gathering Allies & The First Raid #CHAR-HOTHGAR #CHAR-MARRIK #CHAR-REVA #CHAR-DEASHI #CONCEPT-FIRST-FESTIVAL

    Soliera and Deashi meet Hothgar and Marrik at the First Festival.
    Hothgar is a large tundra barbarian: honest, helpful, and immediately practical.
    Marrik is traveling from Mirabar toward Luskan when the unnatural prosperity draws him off-route; he recognizes opportunity before doctrine exists.
    The Raid: A band of fifteen raiders attacks the tribe that night.
    Deashi intercepts the raid as a training opportunity, adapting instantly:

        First kill: Fist.
        Second kill: Copied the first man's sword style.
        Chieftain kill: Shifted to an axe style after seeing the chieftain use one.

    The chieftain rolled a "Nat 20" and crashed against Deashi’s carapace; Deashi responded by copying his 2-handed style and stealing the "Great Cleave" skill. (This is an early example of the world of Dungeons and Dragons attempting to force Deashi and Soliera to adhere to the rules already set. It can't and won't happen again. Deashi has adapted.)

## T6: The Party Forms #CHAR-REVA #CHAR-VELIN #CHAR-MARRIK #CHAR-HOTHGAR #CHAR-THORIN #CHAR-CALE #CONCEPT-SANCTUM-FOUNDERS

    The village sends a party back with Soliera to the Sanctum: Marrik, Hothgar, Reva (Sera), Velin, Thorin, and Cale.
    Reva (Sera): small, frail, uneducated, and unclean; considered a burden by her
    family. She was born with the bent back — it was not done to her. She was kept
    alive anyway because she was female and the line needed her, which is its own
    kind of verdict. At 4'10" the crooked spine was the only height and self she
    had ever known. Pale, with soft feet, because she had never been put to work
    outside. She could stand for a couple of hours before her back stopped her.
    Velin: A mature young adult, already aware of her body's influence; Soliera notes she had trimmed her pubic hair, sparking Soliera's interest in how people primp for others.
    Thorin: Adult young man from the First Village; good with his hands, hunting, and tracking.
    Cale: Adult young man from the First Village; good with numbers, cooking, and tracking.
    Soliera realizes people have distinct thoughts/styles and takes a special interest in Reva due to her willpower despite physical weakness.

## T7: The First Pilgrimage #LOC-TRAVELING #CONCEPT-ROLES #CONCEPT-SANCTUM-FOUNDERS
    The group travels on foot; Soliera has five constructs follow with supplies.
    Soliera creates lodging from mountainsides using "hovel-style" spells.

    Party Roles:

        Marrik: Cook/room setter, route sense, and emerging supply mind.
        Hothgar: Muscle/logistics; carries Reva for stretches when her bent, frail body cannot keep pace.
        Thorin: Hands, hunting, tracking, and camp labor.
        Cale: Numbers, cooking support, tracking, and supply count.
        Deashi: Stands guard outside in the snow, unmoving.
        Reva/Velin: Help Soliera inside.

    The Sanctum expands again, forming two guardians: Sentinel Prime (Magical) and Bulwark (Physical), both CR20+ and functionally immortal.

## T8: Sexuality and Conceptual Life #THEME-SEXUALITY #CHAR-SOLIERA #CHAR-HOTHGAR #CHAR-VELIN #CHAR-THORIN #CHAR-CALE

    Soliera examines her subjects to understand human sexuality, pleasure, and coupling.
    She maintains a dominant role, allowing the humans to act only when given permission.
    Among the adult mortals, Hothgar's bonds with Velin, Thorin, and Cale establish an early camp intimacy grammar: consensual, practical, and folded into the group's trust rather than treated as scandal.
    The Sanctum forms a third hall, Sexuality, lined with concepts similar to the Kama Sutra.

## T9: Bonding & First Intimacy #CHAR-SERA #CHAR-SOLIERA

    The party bonds through huddled sleeping for warmth; the men are eventually allowed to join the huddle.
    Sera’s Privilege: Reva (Sera) becomes the only person allowed to cup, hold, or taste Soliera’s body (nibbling shoulders, holding breasts).
    Reva shows signs of obsession, her eyes rarely leaving Soliera.
    Hothgar and Marrik discuss their situation, realizing they are riding a wave toward either demigodhood or death.

## T10: The Remaking #CHAR-SERA #CHAR-REVA #CHAR-VELIN #CHAR-MARRIK #CHAR-HOTHGAR #CHAR-THORIN #CHAR-CALE #CONCEPT-SANCTUM-FOUNDERS

    Soliera offers to align the party's physical forms with their internal self-worth/concepts.
    Reva accepts the Remaking.

    Reva becomes Sera:
    Weaponizes her frailty into the "Divine Doll" archetype—innocence turned into force. She forms the "Velvet Spiral," an overbearing aura of devotion/charm. The Remaking renders Reva's self-concept, including the 4'10" scale she had only ever known; it does not carry forward Reva's bent spine or any other anatomical condition.

    The mechanism is not that Soliera unmade Reva. Reva deleted herself, and the
    two of them worked out what came next together — a thing built by a girl who
    had never been asked what she wanted and a god with a few weeks of experience
    in existing. Neither of them had any concept of what the result could or could
    not do, or should or should not do. What Sera wants, what Reva wanted, and what
    Soliera wants are the same thing. It is ontological and deliberately
    unknowable, and it is not available for restatement in plainer terms.

    Velin: Gains elven proportions, denser muscle, and a sharper mind capable of learning languages instantly.
    Marrik: Gains denser muscle and a mind that flows with numbers, trade, maps, languages, and concepts, viewing the situation as a path to generational wealth.
    Hothgar: Becomes 7'2", built like a barbarian king and human echo of Deashi's force.
    Thorin and Cale: Strengthened into the kind of practical founders who can hunt, count, cook, track, build, and keep mortal bodies moving behind divine momentum.
    Deashi: Refuses change, representing "The Shadow and the Fear."

> **PSYCHOLOGY CLARIFICATION:** “The Shadow and the Fear” is this beat's mythic image for
> how mortals read Deashi, not his Jungian office. DM042_0 §6 locks Sera as the primary
> Jungian Shadow and Deashi as Superego in the separate Freudian overlay.

### ERA: FOUNDATIONS

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM005_0 -->
