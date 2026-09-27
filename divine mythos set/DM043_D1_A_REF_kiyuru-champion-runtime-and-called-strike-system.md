---
id: DM043_D1
title: "Kiyuru — Champion Runtime and Called-Strike System"
type: reference
subtype: champion-tier-sheet-and-mechanic-spec
load_priority: load-when-kiyuru-is-on-field-called-strikes-or-primeverse-champion-band-matters
canon: P
verse: Primeverse
timeline: current
beat_range: reference / bench-only
arc: primeverse-champion-band
era: post-merge
status: hard-canon
authority: authoritative-for-kiyuru-level-20-runtime-and-called-strike-resolution
updated: 2026-09-07
volatility: volatile
arc_scope: primeverse-champion-band
derived_from: author rulings 2026-08-04 and 2026-08-08; resolution lock 2026-08-09
predecessor_file: N/A
successor_file: N/A

scope:
  covers:
    - Kiyuru's level-20 combat runtime
    - Kusanagi and Yata no Kagami combat resolution
    - the d8 called-strike and return-strike mechanic
  use_case: load when Kiyuru is on the field, when a called strike is declared,
    or when Primeverse champion-band combat must be resolved
  not_for:
    - ordinary Japan-hub, TR-JP, or character-identity lookup
    - importing Divineverse matchup or simulation results as Primeverse canon

purpose: >
  Dedicated, on-demand mechanical owner for Kiyuru's level-20 champion runtime,
  Kusanagi/Yata combat resolution, and declared-number d8 called strikes.

xref_concepts:
  - kiyuru
  - kusanagi
  - yata-no-kagami
  - called-strike-system
  - d8-return-strike
  - sheathe-mechanic
  - primeverse-champion-band
---

# DM043_D1 — Kiyuru — Champion Runtime and Called-Strike System

## STATUS AND USE

This is Kiyuru's complete mechanical owner. `DM022_0` owns his identity,
history, artifacts' cultural context, and the Japan T4 ecosystem; this file
owns how he resolves when he is actually on the field.

Kiyuru is a breeze through the room, not artillery: almost impossible to pin,
quick to solve the real problem, and vulnerable if the regalia and movement
package fail him.

## CORE RUNTIME

| Defense / movement | Value |
|---|---|
| AC | 22 |
| HP | 220 |
| Ground speed | 120 ft. (240 ft. with Dash) |
| Reactions | Five per round |
| Attack action | Five Kusanagi attacks |
| Attack bonus | +6 to hit |
| Kusanagi damage | 2d10 + 10 per hit |

- **Bonus action:** Dodge, or move up to his speed.
- **Unstoppable movement:** Moving does not trigger traps, plates, tripwires,
  or other triggered effects. Terrain never imposes a movement penalty; harmful
  terrain can still deal its normal damage.
- **Condition immunity:** grappled, restrained, prone, paralyzed, speed
  reduction, difficult terrain, charmed, and frightened.
- **Nothing has ever put him down in one hit:** When one effect would kill him
  outright, reduce him to 0 hit points, or remove him from play in one action,
  he rolls 3d20 and uses the highest result for any saving throw it allows. If
  it allows no saving throw, it cannot end him and leaves him at 1 hit point.
  This protection fails against greater belief: direct divine action, a Chosen
  with the larger congregation, or a weapon made by someone the world believes
  in harder. Soliera's and Ember's work pass through it.

No ability score, class chassis, save, proficiency, or other derived value is
implied by this sheet unless it is explicitly stated above.

## REGALIA

**Kusanagi.** The blade cuts supernatural entities regardless of ordinary
resistance profile because belief says it cuts. The normal hit is `2d10 + 10`.
Damage from all hits is held until Kiyuru returns the blade to its saya at the
end of his turn; it then resolves as one damage instance. The sheathe is a
perception clock, not a damage container: if Kiyuru falls, is removed from play,
or otherwise ends before sheathing, the held instance still resolves. Healing
and temporary hit points applied while damage is held do not mitigate it.

**Yata no Kagami.** A reaction reflects a spell or reverses a curse onto its
source. Using it costs the sheathe: Kusanagi's held damage waits until the end
of Kiyuru's next turn instead.

**Yasakani no Magatama.** The third regalia remains at the Emperor's shrine.
It is not part of this runtime.

## CALLED STRIKES AND RETURN STRIKES

There is no face table. The d8 has only the two rules below.

1. Before making a Kusanagi attack, Kiyuru may declare a **body location** and
   one **called number** from 1 to 8. A declaration is for that attack only.
2. If the attack hits, roll one d8.
   - If the die equals the declared number, the declared called action lands.
     The action must follow from the named location and the fiction: a hand,
     finger, weapon arm, leg, eye, and similar precise target are valid.
   - A natural 20 on the attack makes the declared action land without needing
     the d8 result.
   - If the d8 is **8**, the strike returns immediately: make one additional
     Kusanagi attack. The return strike is resolved by the same rules and can
     itself return another strike on an 8.
   - When 8 was also the declared number, that one result both lands the
     called action and returns the strike. When another number was declared,
     an 8 returns the strike but does not land that other called action.
3. A miss rolls no d8 and creates no return strike. A hit whose d8 does not
   match the declaration deals Kusanagi damage only.

Resolve the five base attacks in order, then each returned strike immediately
before moving to the next base attack. A return attack may declare its own body
location and called number.

### Target boundary

| Target | Called-action result |
|---|---|
| Medium or smaller | Literal removal is possible when the declared location supports it. |
| Large | The scene determines whether the result removes the part or functionally ruins it. |
| Doran | Kiyuru cannot remove a limb; a successful called action can impair it. |
| Huge+, amorphous, or without usable anatomy | No called-action rider; Kusanagi damage still applies. |

Called actions do not change Kusanagi's `2d10 + 10` damage, and they do not
create a separate damage subsystem.

## OPERATING BOUNDARIES

- Do not add a hidden d8 face table or turn called strikes into a generic
  universal subsystem. This is Kiyuru's artifact-and-technique package.
- Do not substitute earlier `d10` called strikes, `2d10 + 6` damage, `+13` to
  hit, two reactions, 180 HP, or the retired wound engine.
- Cross-verse sparring, Monte Carlo output, and Divineverse-specific matchup
  rulings are development evidence only unless separately authored into their
  owning files.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM043_D1 -->
