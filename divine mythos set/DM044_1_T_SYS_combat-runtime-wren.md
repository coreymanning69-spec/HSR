---
id: DM044_1
title: "Combat Runtime — Wren"
type: sys
subtype: combat-runtime-derived-sheet
load_priority: section-load-at-combat-or-simulation-start-with-DM044_0
canon: T+TR
verse: Divineverse
timeline: T537.0+
beat_range: TR3-SKT-current
arc: sanctum-next-generation-stewards
era: global-tour
status: derived-artifact
authority: authoritative-derived-wren-combat-runtime
updated: 2026-09-07
volatility: volatile
arc_scope: storm-kings-thunder
derived_from:
  - DM041_B
  - DM038_L
predecessor_file: DM044_0
successor_file: N/A
maintenance_authorities:
  - DM041_B
  - DM038_L
source_schema: dm-combat-source-1
commit_to:
  live_combat: DM038_L
  simulation_findings: DM038_CH
scope:
  covers:
    - pre-totaled Wren combat and casting statistics at Cleric 20 / Sorcerer 20
    - slots, sorcery points, metamagic, turn tax, and spell access
    - domain features, Channel Divinity expressions, signatures, and items
  use_case: section-load together with DM044_0 when combat initiative or an explicit simulation starts
  not_for:
    - protocol, roll authority, the round-state block, or Doran (use DM044_0)
    - routine noncombat characterization (use DM040_0)
    - source maintenance or rebuild reasoning (use DM041_B)
    - long-term state persistence before or after combat (use the active live ledger)

xref_concepts:
  - combat-runtime
  - wren
  - ward-overflow-nullification
  - portal-domain
  - liberation-domain
  - portal-shear
  - nivs-descent
  - metamagic-turn-tax
  - staff-of-the-magi
  - robe-of-the-archmagi

purpose: >
  Wren's half of the two-file table runtime. DM044_0 carries the protocol, roll
  authority, round-state block, and Doran. DM041_B wins on standing-mechanics
  conflict; the active live ledger wins on current values and readiness.

canon_flags:
  - "DERIVED RUNTIME: DM041_B owns Wren's standing mechanics; the active live ledger owns current values/readiness. Repair the applicable owner and then update DM044_1."
  - "PAIRED SECTION LOAD: DM044_0 and DM044_1 are one runtime split across two files. Retrieve the required sections from both halves; mounting either file whole is unnecessary."
  - "INTENTIONAL HOMEBREW: Wren's Ember-granted, Soliera-routed metamagic and component-free casting use the permissions printed here; do not import ordinary 5e eligibility or scarcity ceilings."
  - "EDITION PERMISSION: Either the AD&D 2nd edition or the 5e version of a spell may be used, chosen at the table."
  - "NO WISH, NO INTERVENTION BUTTON: Reality-scale requests route to Sera, Ember, or Soliera as divine-tier action that Corey declares and nobody rolls."
  - "STAFF INTERPOSITION: Wren may stop a weapon edge with the indestructible staff in a described moment, but the force still transfers. This is table adjudication and grants no standing AC or damage reduction."
  - "LIVE PROTOCOL: DM044_0 owns the fresh active-live-ledger readiness seed gate, the one-time seed, every-round Corey stop, and final commit. This half never creates a second ledger."

ai_directives:
  - use the section maps to retrieve the required DM044_0 and DM044_1 sections together at combat or simulation start; neither half is valid alone
  - use the full pre-totaled values below without inventing additional table modifiers
  - the round-state block lives in DM044_0; do not emit a second ledger here
  - follow DM044_0 mode/seed discipline; never consult source owners during active combat and never emit a second ledger here
---

# DM044_1 — COMBAT RUNTIME: WREN

#RULE-WREN-TURN-TAX #RULE-WREN-QUICKEN #RULE-NIVS-DESCENT #RULE-PORTAL-SHEAR #RULE-PORTAL-TOLL #RULE-UNBOUND-AURA #RULE-IRON-FLASK-DIVINATION #RULE-WREN-EDITION-CHOICE #RULE-GRID-GOVERNS-RESOLUTION

Section-load with `DM044_0`. The protocol, roll authority, round-state block,
and pair openings live there; neither whole file is an automatic mount.

## COMBAT SECTION MAP

| Need | Retrieve |
|---|---|
| Wren enters initiative or is targeted | Core statistics + Slots and action economy |
| Domain or Channel Divinity action | Domain features only |
| Metamagic choice | Metamagic only |
| Choose or resolve a spell | Spell access + the matching Signature spells entry when applicable |
| Any damage roll she makes | Divine damage (one paragraph; it applies to everything) |
| Concentration, force lane, or visible pools | Concentration, force lane, and visible pools only |
| Item interaction or table ruling | Items and operative rulings only |
| Simulacrum present | Simulacrum at the table only |
| Pair geometry after opening | Pair doctrine at the table only |

Start with Core statistics plus Slots and action economy. Retrieve the one
action, spell, item, simulacrum, or pair subsection that the turn actually
needs; do not mount the entire casting sheet for every initiative.

## 1. WREN — PRE-TOTALED COMBAT SHEET

**Current field role:** Sanctum Steward, accepted at T537.0.

**Current build:** Cleric 20 / Sorcerer 20 stacked, by divine uplift at T537.0.

### Core statistics

| HP | Ward | AC | Speed | Initiative | Proficiency | Passive Perception |
|---:|---:|---|---|---:|---:|---:|
| **220** | **75** all-type | **18** in the Robe of the Archmagi / **23** with *shield* | 30 ft; **fly 60 ft**, wings free to manifest | **+6** | +6 | 19 |

| Ability | STR | DEX | CON | INT | WIS | CHA |
|---|---:|---:|---:|---:|---:|---:|
| Score / modifier | 10 / +0 | 13 / +1 | 16 / +3 | 16 / +3 | 17 / +3 | 20 / +5 |
| **Save, final** | **+3** | **+10** | **+12** | **+12** | **+18** | **+14** |

**Advantage on all saving throws against spells and other magical effects**, from
the Robe of the Archmagi. INT and WIS include the +5 sigil and Wren's separate
**Personal Blessing (+1 INT/WIS saves)**. All saves also include the robe, cloak,
and Blessing of Protection where applicable. STR +3 is her only shallow save.

| Retained skill | Final modifier |
|---|---:|
| Arcana / History / Investigation / Nature | **+9** each |
| Perception / Survival | **+9** each |
| Insight | **+7** |
| Persuasion | **+11** |
| Stealth | **+7** |

**Tool:** calligrapher's supplies.

| Spell save DC | Spell attack | Sorcery points | Channel Divinity |
|---:|---:|---:|---:|
| **22** | **+14** | **50** | **3/rest** |

The Staff of the Magi's printed +2 spell attack is **declined by design**. Her
attack stays +14 so that tier-3 and tier-4 targets remain missable.

### Slots and action economy

| Level | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th | 9th |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| General | 20 | 16 | 16 | 16 | 20 | 12 | 10 | 14 | 8 |
| Domain-only | +2 | +2 | +2 | +2 | +2 | +2 | +2 | +2 | +2 |

**132 general through 9th + 18 domain through 9th = 150 total slots.**

| Slot | Options |
|---|---|
| Action | Cast · Channel Divinity · robe star · enter/leave Astral · raise the Staff of the Magi · Dodge · Help · object |
| Bonus action | Quicken · crown mote · *healing word* · *spiritual weapon* · Font conversion · free *misty step* (5/LR) · Unearthly Recovery |
| Reaction | *shield* · *absorb elements* · *counterspell* · War Caster opportunity spell · staff spell absorption · Portal anchor return · Aura of the Unbound save conversion |
| Free | manifest or dismiss Otherworldly Wings |
| Rest resources | Channel Divinity 3/rest · Favored by the Gods 1/rest · *Portal Shear* 1/LR · sealed *imprisonment* 1/LR · Unearthly Recovery 1/LR · Portal anchor 1/LR · save conversion 1/LR · Sorcerous Restoration 4 SP/short rest |

**Her reaction is the tightest slot on either sheet.** Seven options, one
reaction, and *shield* and *counterspell* are both usually correct. This mirrors
Doran's reaction asymmetry on purpose.

**Crown of Stars is permanently active.** Seven motes, no slot, no
concentration, refreshed daily. A bonus-action mote is **+14 for 4d12 radiant**,
spent on hit or miss. It is also permanently visible; she cannot be subtle while
wearing it.

Permanent immunity: **all mind-altering effects**. Nothing may alter, suppress,
override, control, rewrite, disable, enter, read, or involuntarily access
Wren's mind. Charm, fear, compulsion, domination, confusion, mental stun or
paralysis, possession, *feeblemind*, and thought/memory/identity/emotion edits
all fail. Non-mental spatial containment or relocation remains live.

**Languages:** Common, Draconic, Elvish, Gnomish, Infernal, Orc, Undercommon.

### Domain features

**Channel Divinity — Dimensional Shift (Portal).** Action. Wren and up to six
willing creatures within 30 ft teleport to any point she can see, or any place
she has physically stood within the last 24 hours, up to one mile. No
concentration, no components, does not provoke. This is the pair's exit.

**Channel Divinity — Indomitable Spirit (Liberation).** Action. Wren and every
ally within 30 ft immediately end any charmed, frightened, paralyzed, restrained,
stunned, grappled, incapacitated, or petrified condition, and cannot be subjected
to them for 1 minute. Forced movement against them fails.

**Portal 14 — Unbarred.** Her teleportation cannot be blocked by *dimensional
lock*, *forcecage*, anti-teleport wards, or any effect of 8th level or lower. She
knows on sight when a space is sealed and what leaving would require. Free
*misty step* as a bonus action, 5/LR, no slot.

**Portal 17 — The Open Door.**
*Anchor:* set at the end of each long rest. Once in 24 hours, as a **reaction**,
she and every willing creature within 30 ft return to it — usable while
restrained, grappled, incapacitated, or at 0 HP, so long as she is alive.
*Toll:* anything teleporting into or out of a 60-ft radius makes a **CHA save vs
DC 22** or the attempt fails and is wasted. She chooses exemptions.

**Liberation 14 — Unshackled Host.** Allies within 30 ft have *freedom of
movement* permanently, no slot or concentration. An ally dropping to 0 HP within
30 ft may immediately use its reaction to move full speed without provoking.

**Liberation 17 — Aura of the Unbound.** Allies within 30 ft have **advantage on
all saving throws**. Once per long rest she may use her reaction to convert an
ally's failed save within 30 ft into a success, including against save-or-die.

Turn Undead remains live at Destroy Undead CR 4. Wren has no percentile Divine
Intervention button and the Cleric 20 automatic version stays excluded — when
the situation exceeds her she asks Sera, Ember, or Soliera, and that is a scene
Corey declares rather than a resource.

### Metamagic

Ember directly consents to this engine and Soliera routes it. It is always
available and cannot be removed, suppressed, or narrowed by ordinary 5e
eligibility rules. The printed SP costs, Quicken exclusivity, and turn tax are
the intended limits; do not invent another balance ceiling.

| Metamagic | Cost | Final effect |
|---|---:|---|
| Energy Substitution | 0 | swap damage type |
| Silent / Still | 0 | elective through ring; excluded from turn-tax count |
| Enlarge / Extend / Sculpt / Careful | 1 | double range / duration; reshape area; allies auto-succeed |
| Empower / Split Ray / Seeking | 2 | numerics ×1.5; second ray target; reroll miss |
| Maximize / Widen / Chain / Repeat | 3 | maximum numerics; double area; arc; repeat next round |
| Twin | 4 | spell takes effect twice; same target and multi-target allowed |
| Quicken | 4 | bonus-action cast, once per round; cannot combine with another Wren-performed metamagic |
| Heighten | variable | raise DC; pay the difference |

| Metamagics on one spell | Turn tax |
|---|---|
| One | points only |
| Two | points plus bonus action |
| Three or more | points plus entire turn: no movement, bonus action, or reaction |

Ring-elected Silent/Still do not count. Wren's Quicken permits a bonus-action
leveled spell and an action leveled spell in the same turn. At 50 sorcery points
she can now sustain heavy stacks across a long fight rather than spending her
whole pool on one turn; price the turn tax, not the points.

### Spell access

All spells use **DC 22** or **+14 spell attack** unless an item states otherwise.
The full cleric list is live without preparation. Wren requires no material or
costly component, focus, holy symbol, or channeling tool. Wren's healing rolls
normally except on Doran, where his Blessing of Wound Closure maximizes it.

**Either the 2e or the 5e version of any spell may be used, chosen at the table.**
Grid geometry determines mechanical targets and outcomes; prose describes that
resolved footprint and never adds targets or resolutions.

Wren knows every normal published Cleric and Sorcerer/Divine Soul spell. Only
*wish*, Karsus-origin magic, and individually NPC-exclusive spells are excluded;
the named examples below do not limit runtime spell selection.

| Tier | Known / primary combat access | Domain-only |
|---|---|---|
| Cantrips | *guidance, thaumaturgy, toll the dead, sacred flame, spare the dying, light, fire bolt, mind sliver, prestidigitation, minor illusion, mage hand* | — |
| 1st | *shield, absorb elements, magic missile, mage armor* (known but redundant with the robe), *silvery barbs, feather fall, fog cloud, disguise self*; cleric: *bless, healing word, sanctuary, command, guiding bolt, cure wounds, shield of faith, bane, inflict wounds* | *alarm, heroism* |
| 2nd | *scorching ray, misty step, darkness, suggestion, detect thoughts*; cleric: *warding bond, spiritual weapon, lesser restoration, aid, silence, hold person, protection from poison, blindness/deafness, continual flame*. *Detect thoughts* is a cast, concentration-bound spell, never a Weave-sight passive. | *analyze portal, lesser restoration* |
| 3rd | ***fireball***, *counterspell, haste, hypnotic pattern, fly*; cleric: *spirit guardians, revivify, dispel magic, beacon of hope, mass healing word, remove curse, protection from energy, magic circle, daylight, tongues*. *Daylight* is non-concentration, dispels 3rd-level-or-lower darkness, and activates RULE-GLARE on Doran's plate at DC 22. | *magic circle, remove curse* |
| 4th | *polymorph, greater invisibility, dimension door, wall of fire, stoneskin, sickening radiance*; cleric: *death ward, freedom of movement, banishment, guardian of faith* | *banishment, freedom of movement* |
| 5th | *telekinesis, hold monster, synaptic static, wall of stone, far step, dominate person*; signature: *Niv's Descent*; cleric: *greater restoration, raise dead, mass cure wounds, flame strike, dispel evil and good, commune, contagion, insect plague* | *teleportation circle, greater restoration* |
| 6th | *disintegrate, arcane gate, chain lightning, mass suggestion, globe of invulnerability*; cleric: *heal, true seeing, heroes' feast, blade barrier, word of recall, harm* | *arcane gate, dispel magic* |
| 7th | *teleport, reverse gravity, finger of death, crown of stars*; sigil force lane: ***forcecage*** 1/LR; cleric: *resurrection, divine word, regenerate, fire storm, etherealness, plane shift, symbol, temple of the gods* | *etherealness, teleport* |
| 8th | ***demiplane***; granted: *telepathy, Otiluke's telekinetic sphere, dimensional lock, discern location, dominate monster, prismatic wall*; cleric: *antimagic field, earthquake* and the full live cleric list | *maze, mind blank* |
| 9th | ***gate, time stop, mass heal, true resurrection, meteor swarm*** | *freedom* (2e) |

*Wish*, Karsus-origin magic, and individually NPC-exclusive spells are excluded.

**#RULE-IRON-FLASK-DIVINATION:** A contained creature has no plane or
coordinates, so location-divination returns null; the physical flask remains
trackable.

### Divine damage

Every spell and every attack Wren makes carries **DIVINE**, **alongside** the
printed damage type and never replacing it — a radiant spell is radiant *and*
divine. Vulnerability interactions are unchanged; resistance to the printed type
no longer fully blunts her. Cleric source: Ember's ability. Divine Soul source:
**Soliera Herself**. Owner `DM041_B` `divine_damage`; theology `DM042_0`,
`DM047_0`.

### Signature spells

| Spell | Runtime resolution |
|---|---|
| **Niv's Descent** | 5th level; requires a 20-ft intentional dive; full-turn commit, no fall damage, wings remain; free baked-in Sculpt plus up to three additional metamagics. Shockwave 20-ft radius, DEX 22: fail = disadvantage on next attack + rough terrain, success = rough terrain; leave it spherical or freely shape it as a one-creature-excluding wedge, 5-ft terrain wall for 1–2 rounds, or air/thunder knockback. Elemental wave 30-ft radius, CON 22: enemies take 8d6, half on save; allies heal the roll, but Doran heals 48 through his own blessing. Twin, Enlarge, and Quicken are dead; Widen/Extend affect control, while Maximize/Empower/Repeat affect enemy damage only. |
| **Portal Shear ("The Eraser")** | Ordinary: 1/LR force-lane signature; **entire turn — planting**, so no quickened second spell that round; a straight line leaving a **1 cm radius** circle, 50 ft, or 100 ft with Distant; CON 22 binary, zero on success; 8d20 force/teleportation on failure with normal piercing, immunity, and 65%-HP behavior. The level-10 capstone is Shear's own maturity — specified, not acquired, unavailable at runtime: one 4 cm × 200-ft wave, one CON 22 save, zero on success, 960 on failure, at 40 SP plus the day's Portal Shear. Ordinary Portal Shear retains its long-rest cycle. |
| **Portal Slash ("Slash")** | **Its own lane, not a Shear mode and not the capstone.** Specified, not acquired, not a runtime option; unlock is narrative. Action, mid-combat — her only fast erasure. A line crossing horizontally in a whip arc: a facing-dependent cone widening 2/3/4/5/6/7/8 squares, thirty-five squares total, eight at the far end. **Narrow at origin** — anything directly beside her is missed, and a square or two off her facing leaves the arc. **DEX 22** binary, not CON: it travels through air and speed evades it. 8d20 force/teleportation per crossed target; uncontrolled cut height; architecture-capable along its whole path; piercing, teleportation-only block, and the 65%-HP death check inherited. Spends the day's Portal Shear. |
| **Time stop** | 1d4+1 turns of uninterrupted action. Ends early if she affects another creature or an object another creature carries. The purest expression of her doctrine: control the tempo, set the exit, leave before it worsens. |
| **Gate** | Portal domain's capstone in spell form. Opens a portal to any plane and can pull a named creature through. Concentration. |

### Concentration, force lane, and visible pools

| Resource | Runtime rule |
|---|---|
| Personal concentration | One spell; War Caster grants advantage on concentration saves |
| Ring concentration | One long-rest-loaded spell; choose/swap only during a long rest or explicitly equivalent relaxed, safe downtime outside combat; ignores damage, 0 HP, death, and printed duration |
| Force lane | One independent cast/LR each: *Portal Shear, wall of force, Bigby's hand, Otiluke's resilient sphere, Mordenkainen's private sanctum, forcecage, Otiluke's freezing sphere* |
| Sealed capstone | *imprisonment* 1/LR; full action; visible tell |
| Robe stars | Six/day; action; 5th-level *magic missile*, seven automatic **1d4+1** darts |
| Crown of stars | Permanently active; seven motes; bonus action; **+14**, **4d12 radiant**; mote spent hit or miss |
| Staff of the Magi | 50 charges, 4d6+2 daily at dawn; see the item table |
| Unearthly Recovery | 1/LR; bonus action while below half HP; regain **110** |

### Items and operative rulings

| Item/rule | Combat effect |
|---|---|
| Black-Bird Sigil | +5 INT/WIS saves; ward 75; +1 spell DC/attack; force lane and *imprisonment* |
| Robe of the Archmagi | White and gold; AC 15 + DEX when unarmored; **advantage on saves vs spells and magical effects**; +2 spell DC and attack; carries the six robe stars, the solo Astral door, +1 all saves, and permanent *crown of stars* |
| Staff of the Magi | **Indestructible** — cannot bend, break, or shatter by any force in play; 50 charges, 4d6+2 daily; casts *detect magic, enlarge/reduce, light, mage hand, protection from evil and good* (0), *flaming sphere, invisibility, knock, web* (2), *dispel magic, fireball, ice storm, lightning bolt, passwall, telekinesis* (5), *conjure elemental, plane shift, fire storm* (7); reaction spell absorption on spells targeting only her, gaining charges equal to level; retributive strike 16d6 in 30 ft, destroying it, only by her deliberate intent; **its +2 spell attack is declined**; usable as an unbreakable prop, brace, wedge, span, or lever for Doran; Wren may interpose it crosswise to stop a weapon edge in a described moment, but force still transfers and may drive her back, knock her prone, numb her hands, or crack ribs; this grants **no standing AC or damage reduction** and is adjudicated at the table |
| Personal Blessing | +1 INT and WIS saves; already included in +12/+18 |
| Elective Silent/Still ring | Remove verbal/somatic components by intent, zero cost/action |
| Ring of Concentration | Working name; independent held concentration lane described above; *haste* end-lag is absorbed by the relaxed long-rest swap |
| Weave-sight | Invisible creatures appear as targetable shapes; illusions, shapechanging, and Ethereal effects register as magical work but are not seen through; not truesight |
| Cloak of Protection | +1 AC and all saves |
| Blessing of Protection | +1 AC and all saves |
| Ward | If an instance is no greater than the remainder, subtract it normally. If it exceeds the remainder, set ward to 0 and nullify the entire ward-breaking instance plus riders; the next separate hit resolves normally. Recharges at combat end |
| Divine metamagic | Ember-granted and Soliera-routed; always available under the listed SP/action taxes; ordinary eligibility ceilings do not apply |
| Component-free casting | No material/costly components or channeling tool required; optional ritual props are free and unlimited through the Sanctum |
| Doran-only maximum healing | Wren rolls healing normally; Doran's own Blessing of Wound Closure maximizes healing that lands on him |
| No attunement | Wren's divine-made equipment cannot be attuned away |

### Simulacrum at the table

*Simulacrum* is a current 7th-level Wren spell. Casting consumes her **entire
turn**: no movement, bonus action, or reaction. It is once per long rest for
Wren and for each copy. The created body is autonomous and exact Wren except
HP, every spell-slot tier, and sorcery points halve and round down; it rolls its
own initiative and has its own reaction. Ward 75, Channel Divinity 3, Portal
Shear readiness, working Robe/Staff/Crown, current staff charges, stars, and
motes remain identical. If its caster is flying, it is born flying.

The runtime tracks G1/G2/G3/G4 at 110/55/27/13 HP, 75/32/14/5 total slots, and
25/12/6/3 SP. G4 has zero 7th-level slots and cannot continue the cascade.
All item behavior is fully working; this does not reopen the Blessed-tier
framework. Each body sustains one personally cast copy and the global ceiling
is four active copies. Copies persist through long rests and survive their
parent's death. Original Wren feels the death of every copy in her descendant
chain immediately, but receives no last thoughts, moments, pain, replay, cause,
sensory transfer, or forensic detail.

### Pair doctrine at the table

Doran holds and fights. Wren leaves, and she gets hurt doing it. A simulacrum
adds a second soft body with its own extraction turn and reactions; Doran remains
the sole hard target. That asymmetry is the design, not a problem to solve.

Her *gate*, *demiplane*, *time stop*, Dimensional Shift, and the staff's *plane
shift* are the answer to Doran's standing "no exit" lane. A simulacrum's own
Dimensional Shift can extract Doran while Wren exits separately or hold the
door; Doran still receives no independent extraction.

Every normal published Cleric and Sorcerer/Divine Soul spell is a runtime option
unless it is *wish*, Karsus-origin magic, or individually NPC-exclusive.

Combat end, the round-state block, and all handoff routing live in `DM044_0` §5.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM044_1 -->
