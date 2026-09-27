---
id: DM046_1
title: "HSR Champion Band — Reliquary-Facing Overlay"
type: reference
subtype: reversible-stat-overlay-register
load_priority: load-with-DM046_0-when-champions-are-placed-inside-the-hollow-star-reliquary
canon: T-framework / HSR-facing
verse: Divineverse
timeline: post-level-20 / gate-not-yet-placed
beat_range: reference / no-played-beat
arc: hollow-star-reliquary
era: future-sanctum-stewardship
status: approved-overlay / two-fields-author-gated
authority: authoritative-for-the-hsr-champion-band-overlay-only
updated: 2026-09-09
volatility: slow
arc_scope: hollow-star-reliquary
derived_from: DM045_DS1, DM045_DS3, DM045_DS4, DM045_DS5, DM046_0, DM051_0
predecessor_file: DM046_0
successor_file: N/A
scope:
  covers:
    - the tank hit-point ceiling, caster multiplier, flat AC, and flat offensive riders applied to the four current champions inside the Hollow Star Reliquary
    - the tank/caster classification that selects each treatment
    - the ability-score floor of 12
    - the overlay's reversibility contract and its relationship to base T537 runtimes
  use_case: load alongside DM046_0 when a current champion is placed inside the Reliquary
  not_for:
    - modifying any champion's base T537 or T542 runtime
    - use at ordinary Steward-facing table scale outside the Reliquary
    - asserting that any champion has appeared inside the Reliquary in played chronology
    - resolving Ithreva's ability array or the caster save-DC equivalent
xref_concepts:
  - hollow-star-reliquary
  - hsr-champion-band
  - reversible-overlay
  - champion-tier
  - palace-rivals
  - tank-caster-split
canon_flags:
  - "OVERLAY LOCK: This is a separately labeled, reversible overlay. Base runtimes in DM045_DS1, DS3, DS4, and DS5 are unchanged and remain the authority everywhere outside the Reliquary."
  - "SCOPE LOCK: The band applies inside the Hollow Star Reliquary only. It is not a general champion buff and does not travel to SKT, the Court, or any Steward-facing encounter."
  - "TANK CEILING: 1,290 is an authored flat value set by Corey on 2026-08-27, not a multiplier output. Store it flat; never recompute it from a base pool."
  - "DOCTRINE RECONCILIATION: DM051_0's anti-hit-point-inflation reading and DM045_DS5's do-not-add-hit-points line remain in force at table scale. Neither is retired. The band is an environment profile, not a survivability fix."
  - "RUNTIME BOUNDARY: Sandbox is isolated executable play; Forge is explicit-intent, placeless, and review-only."
  - "AUTHOR-GATED: Ithreva's ability array does not exist on disk, so the floor-12 rule cannot be applied to her. The caster-side save-DC equivalent is unresolved. Neither is inferred here."
  - "CLASSIFICATION CALL: Belthyn is banded as a tank on her operative profile, not her class chassis. Flagged for Corey's override."
purpose: >
  Give the four current champions a Reliquary-facing profile without touching
  their base runtimes or contradicting champion-tier doctrine. Everything here
  can be removed in one edit and leave the corpus exactly as it was.
ai_directives:
  - never apply this band outside the Hollow Star Reliquary
  - never write these values back into DM045_DS1, DS3, DS4, or DS5
  - treat the tank hit-point value as a flat authored number, never as a multiplier result
  - apply the flat damage rider once per attack to the primary damage line only, never per damage type and never per die
  - the offensive rider touches attack rolls only; it does not raise any save DC
  - do not invent Ithreva's ability array or a save-DC equivalent; both are author-gated
---

# DM046_1 — HSR CHAMPION BAND
1. WHAT THIS IS

A Reliquary-facing overlay for the four champions in DM051_0's current dossier index. Inside the Hollow Star Reliquary they run on the numbers below. Everywhere else — SKT, the Court, any Steward-facing encounter — their base runtimes are unchanged and authoritative.

Removing this file restores the roster completely. Nothing here is a restat, a migration, or an edit to an existing owner.

2. THE BAND
Hit points — by role
Role	Treatment	Value
Tank	Flat authored ceiling	1,290
Caster	Base × 1.25	see §3

The tank number is flat, not derived. Corey set 1,290 directly on 2026-08-27, replacing an earlier ×2 pass that ran too hot. It is stored as a value, not as a multiplier, and it does not recompute if a base pool changes. Both tanks sit at the same ceiling, which keeps the tank band above the caster band without letting the second tank outrun the forward-authoritative heavy.

The caster multiplier is unchanged.

Flat riders — uniform across all four
AC +1
+2 to hit on all attack rolls, weapon and spell
+4 damage on all attacks

Damage rider rule. The +4 applies once per attack, to that attack's primary damage line. It is not added to each damage type on a multi-type hit, and it is not added per die. The Ordinant's Scepter gets +4 on the bludgeoning line and nothing on the radiant rider; Belthyn's Tidehook gets +4 on the bludgeoning line and nothing on the lightning rider.

Ability floor

All ability scores floor at 12. Higher scores are kept as printed. Listed saving throws stay flat and are not recomputed from the raised score.

3. THE FOUR
The Ordinant — Bane · DM045_DS1 · TANK

Oath of Conquest Paladin 20 in plate, front-line, maul-forward.

Field	Base	HSR band
HP	900	1,290
AC	21	22
Scepter	+16 · 2d6+10 bludgeoning + 1d8 radiant	+18 · 2d6+14 bludgeoning + 1d8 radiant
Save DC	23	23 — unchanged

Ability array needs no change; his lowest score is DEX 12.

Interaction note. Scornful Rebuke (9 psychic to anyone who hits him, ignoring armor) now runs across a longer pool. Doran's thirteen-attack peak self-inflicts 117 per round against a target that lasts roughly forty percent longer. The trap deepens without any new rule.

Belthyn — Umberlee · DM045_DS4 · TANK (classification call)
Field	Base	HSR band
HP	840	1,290
AC	22	23
Tidehook	+14 · 2d8+6 bludgeoning + 2d8 lightning	+16 · 2d8+10 bludgeoning + 2d8 lightning
Spell attack	+14	+16
Save DC	22	22 — unchanged

Ability array needs no change; her lowest score is DEX 14.

Why tank, not caster. Her chassis is Tempest Cleric 20, but her operative profile is a bruiser: highest AC on the roster, STR 22, a two-attack melee multiattack, and a grapple rider. Banding her as a caster would make the most physically durable champion the second-squishiest. Overridable.

Why the same ceiling as the Ordinant. Under the retired ×2 pass Belthyn finished above him, which inverted the roster. The shared flat ceiling keeps them level and lets AC, action economy, and grafts do the separating — which is what DM051_0 says should be doing the work in the first place.

Eclavdra — Lolth · DM045_DS3 · CASTER
Field	Base	HSR band
HP	720	900
AC	19	20
Spell attack	+14	+16
STR	10	12 (floor)
Save DC	22	22 — unchanged

STR 10 is the only sub-12 score anywhere on the champion roster.

Dead rider — flagged. Eclavdra's entire signature suite is save-based or check-based: forcecage, maze, feeblemind, mass suggestion, illusory reality. She makes essentially no attack rolls. The +2/+4 offensive rider does nothing for her as written. See §5.

Ithreva Sazher — Myrkul · DM045_DS5 · CASTER
Field	Base	HSR band
HP	700	875
AC	20	21
Blood Darts	5 darts · +15 · 4d6 necrotic each	5 darts · +17 · 4d6+4 necrotic each
Spell attack	+15	+17
Save DC	23	23 — unchanged

Ability floor unresolved. DM045_DS5 prints saves (CON +10, INT +12, WIS +9) but no ability array. The floor-12 rule has nothing to act on. Not inferred. Author-gated.

Harvest interaction — watch this. Blood Darts grant temporary hit points equal to half damage dealt. Five darts at +4 each adds 20 flat damage per turn, which converts to +10 temp HP per full-hit turn on top of the existing gain. Her Not Yet reaction costs 30 temp HP per use, so the rider directly buys her more refusals. If that reads as too much sustain, cap the rider's contribution to Harvest at zero rather than lowering the rider.

Not banded

The Named Dead (AC 16 / HP 90) and the Ledger of Attendance (AC 18 / 80 HP) are objectives and summons, not champions. They stay at printed values so the Ledger remains a solvable objective rather than a second boss.

Scale note

The tank ceiling still sits above Sera's 900-hit-point consenting boss chassis. That is not an inversion — her DR 15, DT 30, and ontological superiority carry her survival, and the 900 exists only inside a fight she has consented to — but the two numbers will be read side by side eventually. Recorded once here so it is not rediscovered as a problem later.

4. PLACEMENT — FLOOR FIVE

DM046_0 §15 lists "palace rival identities and builds" as an open decision. The banded champions are the intended answer: Floor Five's rival party, against the twenty-round cocoon clock.

This does not place all four in one room, does not fix the rival count at four, and does not resolve the Tarrasque translation. It says only that when the palace rivals are built, this roster and this band are where they come from.

Champion tier is not divine tier. The band raises Reliquary durability; it does not move any champion toward the divine family.

5. OPEN — AUTHOR-GATED
Ithreva's ability array. Required before the floor-12 rule means anything for her.
Caster save-DC equivalent. The +2/+4 rider is a martial rider. It is close to inert on Eclavdra and thin on Ithreva. If casters should get a matching uplift, the natural form is +1 save DC — not written, not applied, awaiting a ruling.
Belthyn's tank classification and shared ceiling — see §3.
Whether the band survives a full Sandbox rehearsal. Baseline and adversarial evidence is complete, but no Sandbox outcome is inferred or promoted here.
<!-- CORPUS REVISION: 9.0 -->
<!-- END DM046_1 -->
