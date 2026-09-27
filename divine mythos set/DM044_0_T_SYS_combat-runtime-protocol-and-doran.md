---
id: DM044_0
title: "Combat Runtime — Protocol and Doran"
type: sys
subtype: combat-runtime-derived-sheet
load_priority: section-load-at-combat-or-simulation-start-with-DM044_1
canon: T+TR
verse: Divineverse
timeline: T537.0+
beat_range: TR3-SKT-current
arc: sanctum-next-generation-stewards
era: global-tour
status: derived-artifact
authority: authoritative-combat-session-protocol-and-derived-doran-runtime
updated: 2026-09-07
volatility: volatile
arc_scope: storm-kings-thunder
derived_from:
  - DM041_A
  - DM038_L
predecessor_file: N/A
successor_file: DM044_1
maintenance_authorities:
  - DM041_A
  - DM038_L
source_schema: dm-combat-source-1
commit_to:
  live_combat: [DM038_L, DM035_0e]
  simulation_findings: DM038_CH
scope:
  covers:
    - AI DM roll authority and Corey-narration override
    - complete volatile round-state block and combat-end handoff
    - pre-totaled Doran combat statistics at Battle Master Fighter 20
    - Doran's action economy, attacks, maneuvers, items, and operative rulings
    - always-on 120-foot Doran-helm darkness sight and mirror-plate RULE-GLARE overlay
  use_case: section-load together with DM044_1 as the only Doran/Wren runtime when combat initiative or an explicit simulation starts
  not_for:
    - Wren's pre-totaled sheet (use DM044_1)
    - routine noncombat characterization (use DM040_0)
    - source maintenance or rebuild reasoning (use DM041_A and DM041_B)
    - long-term state persistence before or after combat (use the active live ledger)

xref_concepts:
  - combat-runtime
  - roll-authority
  - round-state-block
  - turn-resolution
  - precomputed-modifiers
  - active-effect-overlays
  - combat-stop-conditions
  - live-seed-gate
  - skt-giant-scale
  - doran
  - dagger-summoning
  - dagger-resistance-bypass
  - grand-cleave
  - helm-vision
  - ac-lock
  - iron-flask-divination

purpose: >
  Paired protocol/Doran runtime. LIVE reads the active ledger's exact readiness,
  seeds once, and uses the encounter ledger until commit. DM041_A wins standing
  mechanics; the active ledger wins current values/readiness.

canon_flags:
  - "DERIVED RUNTIME: DM041_A owns standing mechanics; the active live ledger owns current values/readiness. Repair the owner, then update DM044_0."
  - "PAIRED SECTION LOAD: DM044_0 and DM044_1 are one runtime split across two files. Retrieve the required sections from both halves; mounting either file whole is unnecessary."
  - "TWO-FILE COMBAT: Selected DM044_0/1 sections plus their state block replace combat-time source reads."
  - "LIVE SEED GATE: Immediately before initiative, fresh-read DM038_L structured readiness and seed exactly once. The same domain ledger persists across arc handoffs. Missing, stale, or contradictory state fails closed; printed baselines are not a LIVE fallback."
  - "COREY OVERRIDE: Corey's explicit narration overrides a roll wholly or partially. Otherwise the AI DM rolls and resolves without confirmation gates."
  - "LEVEL-20 RUNTIME: Both field Stewards were raised by divine uplift and accepted at T537.0. Campaign XP remains 165,000 and is no longer the advancement basis."
  - "AC LOCK: Doran's AC is a flat 25. PLANTED, Dual Wielder, and ring-held haste do not raise it. Deploying the kite drops him to 21."
  - "CLEAVER FINAL LOCK: Ordinary is +16, or +14 choked, for 40 fixed damage (80 crit) at reach 10/5 ft. Grand Cleave is +19 for 120+4d20 (double the final total on crit) in a 15-ft, 180-degree arc."
  - "ENCLOSED COLLATERAL LOCK: In human-scale tight space, the attack and reach penalties remain and every struck wall, fixture, or structural element along the adjudicated arc takes the listed Cleaver damage."

ai_directives:
  - use the section maps to retrieve the required DM044_0 and DM044_1 sections together at combat or simulation start; neither half is valid alone
  - for LIVE mode, fresh-read active exact readiness before initiative; seed once and fail closed on unavailable, stale, or contradictory state
  - after seeding, use the encounter ledger alone and do not consult the active live ledger again until the final state is committed
  - use the full pre-totaled values and explicit active-effect overlays below without inventing additional table modifiers
  - emit one complete volatile-state block at the top of every round
  - roll and resolve all non-divine actions unless Corey narrates the outcome
  - never consult DM041_A or DM041_B during active combat; active-live-ledger reads are seed-before-initiative and commit-after-combat only
---

# DM044_0 — Combat Runtime — Protocol and Doran

#RULE-ROLL-AUTHORITY #RULE-STATE-BLOCK #RULE-TURN-SEQUENCE #RULE-PRECOMPUTED #RULE-STOP-GATE #RULE-SKT-GIANT-SCALE #RULE-DAGGER-SUMMONING #RULE-DAGGER-RESISTANCE-BYPASS #RULE-DAGGER-WARD-BYPASS #RULE-GRAND-CLEAVE #ITEM-HELM #RULE-GLARE #RULE-WREN-SIMULACRUM #RULE-GRID-GOVERNS-RESOLUTION

Combat and explicit simulations only. Section-load `DM044_1` alongside the
required sections here; neither runtime half is valid alone, but neither whole
file is an automatic mount. Enemy/module statblocks must be instantiated before
initiative, including any exact-once registered overlay.

## COMBAT SECTION MAP

| Need | Retrieve |
|---|---|
| Mode, seed, rolls, stops, and round ledger | §§0–3 |
| Pair opening or pre-combat buff | §3A only |
| Any SKT hill/stone/frost/fire/cloud/storm giant | §3B + the one named source row |
| Doran acts or is targeted | §4; within it, retrieve only the relevant action/ruling subsection after Core statistics |
| End and commit | §5 only |

Minimum LIVE load: §§0–3, active exact readiness, relevant Doran/Wren action
sections, and one enemy block. Retrieve §3A or §3B only when used. Do not load DM041_A/B/A1/B1,
full SKT indexes/parents, or narrative/history for initiative.

## 0. MODE AND SEED GATE

Declare `mode=LIVE` or `mode=SIMULATION` before initiative.

- **LIVE:** fresh-read DM038_L and its exact structured readiness. Seed the round-state block
  once. If unavailable, stale, contradictory, or incomplete for a finite pool,
  **STOP; LIVE combat fails closed**. Printed baselines are not a fallback.
  The encounter block is the sole ledger until its final state is committed.
- **SIMULATION:** seed from the declared scenario fixture or the explicit full
  baselines. Never read from or write to a live story ledger. If Corey
  separately authorizes a post-run SCALPEL finding, write it only to DM038_CH.

Record `mode` and `seed` in every state block. Seeding happens exactly once.

Persisted finite pools and carried effects come from the fresh live seed. Opening
posture—positions, wielded weapon, mobile/planted stance, current speed, Wren's
Wings/Shield state, and a Read target—belongs to the opening fiction and must be
declared in the round-1 block before initiative. It is not a duplicate ledger
field and is never inferred from a prior encounter.

## 1. ROLL AUTHORITY

| Case | Binding resolution |
|---|---|
| Default | The **AI DM rolls and resolves every die**: initiative, attacks, damage, saves, checks, morale, reactions, enemy actions, crits, and death saves |
| Corey narrates the whole result | No roll; Corey's narrated result is canon |
| Corey narrates part of the result | Preserve that part and roll only the unresolved remainder |
| Divine tier acts | Never roll; Corey declares presence and effect |
| Field-Steward resource or reaction | Spend and log it without asking for confirmation |

Dice bind once initiative begins. Report one resolution per line:

`d20+16 = 31 vs AC 21 → hit · 1d8+10 = 16 piercing`

Call natural 20 and natural 1 explicitly. Show both dice for advantage or
disadvantage. Report enemy rolls in the same visible format.

## 2. TURN AND STOP PROTOCOL

The mandatory round-top gate and the standing exceptional gates below are
exhaustive. Consent, canon, and unresolved-rule gates may halt at any time,
including before or after Corey releases a round.

1. **Mandatory round-top Corey gate:** emit the complete state block at the top
   of every round, then halt for Corey's direction before resolving that round's
   first turn. This gate fires every round even when no exceptional issue exists.
2. After Corey releases the round, state initiative once in round 1 (and only
   when it changes later), then resolve each turn as declare → roll → resolve →
   apply → log delta. Resolve enemy turns in the same pass without another
   ordinary prompt. Close with a narrative beat, not a second mechanical recap.

During a released round, halt exceptionally only when:

- consent is absent, withdrawn, or too unclear to bind;
- a canon conflict would be created or an authoritative fact cannot be reconciled;
- an unresolved rule would materially change the pending resolution or state;
- a divine-tier action becomes relevant;
- a pending result would make permanent death or party wipe final; halt before
  applying it and route divine-tier preservation;
- a field Steward must make a judgment or social choice with no mechanical answer;
- the required ruling contradicts a standing value in either runtime file; or
- dictation cannot be parsed against the active context.

Defeat, capture, injury, humiliation, public error, lost ground, and failed
objectives do not require a stop.

## 3. ROUND STATE BLOCK

Seed round 1 exactly once under §0. Thereafter this block is the sole encounter
ledger. Repeat every finite pool and active state every round; scrollback,
prose, and pre-seed owner text are not encounter ledgers.

```text
R{n} · mode {LIVE|SIMULATION} · seed {DM038_L|fixture}
     Doran HP {cur}/370 · SD {cur}/16d12 · AS {cur}/2 · SW {ready|spent}
       IND {cur}/3 · {daggers|cleaver|grand-cleave/buried} · {mobile|planted}
       AC {25 | 21 kite deployed} · Speed {cur}
       Haste {on/off; restricted action and DEX-save advantage; no AC change}
       Read {target|none} · Reaction {ready|spent} · cond {conditions|none}
     Wren HP {cur}/220 · Ward {cur}/75 · AC {18|23} · SP {cur}/50
       GS 1:{x}/20 2:{x}/16 3:{x}/16 4:{x}/16 5:{x}/20 6:{x}/12 7:{x}/10 8:{x}/14 9:{x}/8
       DS 1:{x}/2 2:{x}/2 3:{x}/2 4:{x}/2 5:{x}/2 6:{x}/2 7:{x}/2 8:{x}/2 9:{x}/2
       CD {cur}/3 · FBG {ready|spent} · Force {ready/spent list} · IMP {ready|spent}
       Anchor {set/used} · Unbound {ready|spent} · UR {ready|spent}
       Stars {cur}/6 · Crown {cur}/7 · Staff {cur}/50
       Wings {up|down} · Shield {remaining|off}
       Reaction {ready|spent} · Misty {cur}/5 · Sim Cast {ready|spent}
       conc-self {spell/start/remaining|none}
       conc-ring {spell/target/long-rest-locked|none}
       cond {conditions|none}
     Simulacra {none | G1..G4 each: initiative {n}; HP {cur}/{110|55|27|13}; Ward {cur}/75;
       G1 GS [10,8,8,8,10,6,5,7,4] DS [1,1,1,1,1,1,1,1,1] total 75;
       G2 GS [5,4,4,4,5,3,2,3,2] DS [0,0,0,0,0,0,0,0,0] total 32;
       G3 GS [2,2,2,2,2,1,1,1,1] DS [0,0,0,0,0,0,0,0,0] total 14;
       G4 GS [1,1,1,1,1,0,0,0,0] DS [0,0,0,0,0,0,0,0,0] total 5;
       SP {cur}/{25|12|6|3}; CD {cur}/3; Portal Shear {ready|spent}; Stars {cur}/6;
       Crown {cur}/7; Staff {cur}/50; Wings {up|down}; reaction {ready|spent}; cond {conditions|none}}
     Field · scale {SKT-GIANT-v2 target IDs|none; named variants regardless of allegiance} · {enemy HP/states}
       {positions} · {clocks} · {initiative change|none}
```

`GS` means general spell slots; `DS` means domain-only slots. `Anchor` is Wren's
Portal 17 return, `Unbound` her Aura of the Unbound save conversion, and `UR`
Unearthly Recovery. `Misty` is Wren's five-per-long-rest free *misty step*;
`Sim Cast` is her once-per-long-rest *simulacrum* availability. The Ring of
Concentration is tracked separately from Wren's
personal concentration: it ignores damage, unconsciousness, death, and printed
duration while loaded. Its choice changes only during a long rest or explicitly
equivalent relaxed, safe downtime outside combat.

Doran's AC is a constant. Print it, but never modify it for planting, daggers,
or haste. The only value that changes it is deploying the kite.

Fill the template from the single authorized seed and carry every changed
counter forward. Do not keep illustrative parallel receipts inside this runtime;
the emitted block is the encounter ledger.

Grid geometry resolves mechanical targets, distances, and outcomes. Describe the
resulting footprint generously where the room supports it, but never add a
target or resolution beyond the grid result.

### Simulacrum turn and target protocol

Each extant simulacrum is its own Steward-side combatant: roll and print its own
initiative, track its own turn and one reaction, and include it in enemy target
allocation. It is a soft body, as Wren is; Doran remains the only hard body.
Do not spend Wren's reaction, resources, or turn on a copy's action, or vice
versa. A creation consumes the caster's full turn and adds the new body to the
next available initiative position only after that turn ends. The creator's
current state supplies the copied working gear resources at creation; only HP,
per-tier slots, and sorcery points halve. If no seventh-level slot remains, a
copy cannot create another. Each body may sustain one personally cast copy,
and no more than four copies may be active globally. Copies persist through
long rests and survive the death of their parent. On a copy's death, original
Wren immediately feels the loss anywhere in her descendant chain, but receives
no last thoughts, moments, pain, replay, cause, sensory transfer, or forensic
detail.

## 3A. PAIR OPENINGS AND PRE-COMBAT BUFFS

**Dark screen — Wren *darkness* + Doran helm:** Wren may place *darkness* as a
screen Doran can fight inside. His helm sees normally through magical and
nonmagical darkness to 120 feet; this is not truesight. Drow cannot see through
their own *darkness* without a separate feature that says otherwise. The spell
uses Wren's personal concentration; the helm uses none, so ring-held *haste*
remains active.

**Mirror glare — *daylight* on Doran or his kit:** One 3rd-level slot, one hour,
no concentration. The spell supplies 60 feet of bright light and dispels
overlapping darkness of 3rd level or lower; drow *darkness* is 2nd level.
*Daylight* is not sunlight and does not itself trigger Sunlight Sensitivity.

Within the bright radius, a creature attacking Doran or starting its turn with
line of sight to him makes a **DC 22 Constitution save**. On a failure it has
disadvantage on attacks against Doran until the start of its next turn; on a
failure by 5 or more it is blinded for that duration. Sunlight-sensitive
creatures have disadvantage on this save because of the reflected glare, an
explicit house ruling. Doran, Wren, and creatures not looking at him do not
roll. *Dispel magic*, *counterspell*, broken line of sight, and range beyond 60
feet are the live counters.

**Standing pair auras.** While Doran is within 30 feet of Wren he has
*freedom of movement* at all times and **advantage on all saving throws** from
Liberation 14 and 17. These cost nothing and are always on. Separating the pair
is now the correct enemy play and should be written as deliberate opposition
tactics, not coincidence.

The helm and *daylight* use no concentration and stack with Wren's ward and the
Ring of Concentration load. The *darkness* opening still uses Wren's personal
concentration.

## 3B. SKT GIANT SCALE — RUNTIME PROJECTION

`DM057_0` § `SKT-GIANT-v2` is authoritative. At instantiation, retrieve the row,
apply it exact-once after printed or template modifiers, mark the enemy with
`scale=SKT-GIANT-v2` in the Field ledger, and never scale a marked target again.
The registry owns the tuple, exclusions, precedence, and non-stacking rule.

Runtime scope: hill, stone, frost, fire, cloud, storm giants; named variants
regardless of allegiance. Exact tuple: AC +1 · every weapon or spell attack
roll +1 · damage +3 · save DC +1 · max HP +200 · current HP +200.

For the current runtime acceptance contract, the projection remains explicit:
`#RULE-SKT-GIANT-SCALE`; `scale=SKT-GIANT-v2` **exact-once** only to SKT hill,
stone, frost, fire, cloud, or storm giants, including named variants regardless
of allegiance. After all printed
or template modifiers: `AC +1 · every weapon or spell attack roll +1 · damage
+3 · save DC +1 · max HP +200 · current HP +200`. Adding 200 to both HP values
preserves existing damage; the rule replaces the generic 30–60% encounter-HP
rule and never stacks. Ogres, trolls, ettins, oni, fomorians, constructs,
animals, and shapechanged non-giants such as Iymrith do not match. Change no
proficiency bonus, Hit Dice, CR, XP, save, speed, ability score, action,
reaction, resistance, or other statistic.

### Named giant source pointers

Retrieve one row only. The ordinary baseline is the exact-name core 5e creature
block; those Monster Manual baselines are not duplicated in this corpus. The
linked SKT source section supplies its optional ancestry actions. A named or
room-specific variant comes from that exact local room/source section instead.
Apply the retrieved registry row after the selected printed or template
modifiers. The Field line remains:
`Field · scale {registry marker target IDs|none} · {enemy HP/states}`.

| Giant block | Optional SKT actions |
|---|---|
| Hill giant | `storm king texts/16_q04_appendix_c_creatures_p247-247.md` § Hill Giants |
| Stone giant | `storm king texts/16_q04_appendix_c_creatures_p247-247.md` § Stone Giants |
| Frost giant | `storm king texts/16_q04_appendix_c_creatures_p247-247.md` § Frost Giants |
| Fire giant | `storm king texts/16_q03_appendix_c_creatures_p245-246.md` § Fire Giants |
| Cloud giant | `storm king texts/16_q03_appendix_c_creatures_p245-246.md` § Cloud Giants |
| Storm giant | `storm king texts/16_q04_appendix_c_creatures_p247-247.md` § Storm Giants |

## 4. DORAN — PRE-TOTALED COMBAT SHEET

**Current build:** Battle Master Fighter 20.

### Core statistics

| HP | AC | Speed | Size | Initiative | Proficiency | Passive Perception |
|---:|---|---|---|---:|---:|---:|
| **370** | **25**, flat | 30 ft in kit / 40 ft without; 60/80 if hasted; up to 20 ft may become flight | Large; 10-ft square | **+21** | +6 | 20 |

| Ability | STR | DEX | CON | INT | WIS | CHA |
|---|---:|---:|---:|---:|---:|---:|
| Score / modifier | 27 / +8 | 16 / +3 | 18 / +4 | 16 / +3 | 18 / +4 | 16 / +3 |
| **Save, final** | **+15** | **+4** | **+11** | **+10** | **+11** | **+4** |

| Skill | Final modifier |
|---|---:|
| Insight | **+16** |
| Athletics | +14 |
| Perception | +10 |
| Survival | +10 |
| Persuasion | +9 |

The former INT +2 seam is closed; Resilient (INT) and the T537.0 uplift carry it
to +10. DEX +4 and CHA +4 are the shallowest numbers now. Doran's helm grants
normal sight through magical and nonmagical darkness to 120 feet but is not
truesight. Ring-held *haste* grants advantage on Dexterity saves but does not
change the printed +4.

While within 30 feet of Wren, every save above is rolled with **advantage**.

### AC — flat and locked

| State | AC |
|---|---:|
| Any configuration: standing, planted, one or both daggers, hasted | **25** |
| Kite deployed elsewhere | **21** |

PLANTED, Dual Wielder, and ring-held *haste* no longer contribute AC. PLANTED
still gives speed 0 and immunity to displacement-based forced movement and
displacement-based prone; that immunity is now its entire value. Dropping the
kite for Wren is the only thing that moves his armor class, and it costs four
points against a threat band that already hits 25 roughly half the time.

### Action economy and pools

| Slot | Options |
|---|---|
| Action | Attack, **4 attacks** · ring-haste restricted action when active: Attack (**one weapon attack**), Dash, Disengage, Hide, or Use an Object · Action Surge for a second or third full action · Dodge · Grapple · Shove |
| Bonus action | Read the Seam · Quick Toss · off-hand dagger · Second Wind **30 HP** · Ring heal **16 HP** |
| Reaction | Deft Answer · Riposte · opportunity attack |
| Movement rider | Bait and Switch |
| Pools | **16d12 superiority, DC 22** · Action Surge **2/SR** · Second Wind 1/SR · Indomitable **3/LR** · Relentless: regain one die when initiative is rolled with none |

One expended superiority die returns when Doran scores a critical hit, maximum
once per round. Current peak burst is **thirteen attacks**: three Attack actions
plus Quick Toss; it becomes fourteen while ring-hasted. A dagger appears in his
open hand at the instant it is needed; there is no draw, drop, stow, or
transition cost. Grand Cleave is the exception because it commits both hands and
the whole turn.

**Reaction asymmetry is intentional.** Opportunity attack, Deft Answer, and
Riposte all contend for one reaction, and the latter two share the on-miss
trigger. Do not grant a second reaction to smooth this out.

### Attacks and signature rules

| Attack | Final line | Rules |
|---|---|---|
| Obsidian dagger | **+16 · 1d8+10 · 30/70** | five attacks on a normal full routine, six while ring-hasted, thirteen at full Action Surge burst; summon/dismiss and return instantly; ignores damage-type resistance without doubling damage; lethal/nonlethal depth by choice |
| Giant Cleaver | **+16 · 40 fixed · crit 80 · reach 10 ft** | one- or two-handed; carry-through parts targets at or below actual damage and stops at first survivor |
| Cleaver in human-scale tight space | **+14 · 40 fixed · crit 80 · reach 5 ft** | no extra squeezing tax; each struck wall, fixture, or structural element takes the listed damage; giant architecture, caverns, forge halls, and open ground are exempt |
| Grand Cleave | **+19 · 120+4d20 · crit doubles final total · 180° arc · reach 15 ft** | whole-turn, both-hands mode; seven Medium-unit capacity, Large costs two; Medium/Large automatically parted; first Huge+ takes damage and stops it |

**Read the Seam:** bonus-action Insight +16 vs target AC. Success gives dagger
critical range 16–20 against that target until it hits Doran.

**Deft Answer:** when a creature misses Doran, he may use his reaction for one
free dagger attack without spending a superiority die.

**Instant dagger access:** summon or dismiss either dagger with no action,
including mid-motion. Doran may hold the Cleaver one-handed and fill the other
hand in the same instant. This access is universal.

**Grand Cleave resolution:** Grand Cleave consumes the whole turn: no movement
or bonus action. Both hands remain on the haft during resolution, but Doran
retains his reaction and its normal lanes after the turn, including Deft Answer
when triggered. Action Surge does not produce a second Grand Cleave.

1. Make one attack roll and apply it to every body in the 180° arc in order. A
   natural 20 doubles the final damage total against each body reached.
2. The arc has seven Medium-unit spaces; Medium costs one and Large costs two.
   A hit automatically parts those bodies until capacity is exhausted.
3. The first Huge-or-larger body takes damage and stops the blade.
4. The arc does not distinguish allies from enemies.
5. A parted body is destroyed. *Revivify* works inside one minute; *raise dead*
   does not. Wren's *true resurrection* can answer the loss without a body.

**Ordinary carry-through:** along the chosen swing line, part each target at or
below actual damage and continue; the first survivor takes damage and stops the
blade. **Maim:** any Cleaver hit dealing at least one-quarter of maximum HP, or
rolled on a natural 20, maims the reached limb. **Skid:** a survivor moves
`5 × floor(damage/50)` feet; Gargantuan targets halve this and round down to the
nearest 5 feet.

**Configuration competence gate:** the former ordinary Cleaver-to-dagger
drop/stow cost is retired. The only surviving gate is the Grand Cleave turn
itself.

### Maneuvers

All 23 PHB/Tasha maneuvers are live. Add **d12** where stated; save DC is **22**.

| Maneuver | Runtime effect |
|---|---|
| Ambush | +d12 Stealth or initiative |
| Bait and Switch | swap while moving; +d12 AC to one participant |
| Brace | reaction attack on reach entry; +d12 damage |
| Commander's Strike | forgo attack + bonus action; ally reaction attack +d12 damage |
| Commanding Presence | +d12 Intimidation, Performance, or Persuasion |
| Disarming Attack | +d12 damage; STR save or drop held object |
| Distracting Strike | +d12 damage; next ally attack gains advantage |
| Evasive Footwork | +d12 AC while moving |
| Feinting Attack | bonus action; advantage and +d12 damage |
| Goading Attack | +d12 damage; WIS save or disadvantage vs others |
| Grappling Strike | after hit, bonus-action grapple with +d12 Athletics |
| Lunging Attack | +5 ft reach and +d12 damage |
| Maneuvering Attack | +d12 damage; ally reaction moves half speed safely |
| Menacing Attack | +d12 damage; WIS save or frightened |
| Parry | reduce melee damage by **1d12+3** |
| Precision Attack | +d12 attack before outcome |
| Pushing Attack | +d12 damage; STR save or push up to 15 ft |
| Quick Toss | bonus-action thrown attack +d12 damage |
| Rally | ally gains **1d12+3** temporary HP |
| Riposte | reaction attack after miss +d12 damage |
| Sweeping Attack | carry d12 damage to adjacent second target |
| Tactical Assessment | +d12 Investigation, History, or Insight |
| Trip Attack | +d12 damage; STR save or prone |

Parry adds Doran's current Dexterity modifier (+3). Rally separately adds his
current Charisma modifier (+3). Their equal totals are coincidental, not one
shared Fighting Style modifier.

### Items and operative rulings

| Item/rule | Combat effect |
|---|---|
| Divine plate | Soliera-remade mirror-white divine plate: stage one transmits 1/3 piercing, 1/2 slashing as bludgeoning, and all bludgeoning; stage two absorbs 1/4 of every transmitted type. Net physical damage: 1/4 piercing, 3/8 slashing, 3/4 bludgeoning. The mirror-white surface emits no light and returns incident light at high efficiency. |
| Helm | Soliera's T537 remake: normal sight through magical and nonmagical darkness to 120 ft; always on; no attunement; not truesight; supplies a breathable atmosphere while worn, including underwater and volcanic environments; Doran still requires oxygen and can suffocate without it |
| RULE-GLARE | *Daylight* on Doran/kit: DC 22 CON within 60 ft when attacking Doran or starting in line of sight; fail = disadvantage vs Doran, fail by 5+ = blinded, until start of next turn; sunlight-sensitive creatures save at disadvantage; explicit house rule |
| Obsidian daggers | Summon/dismiss and return instantly; no hand-transition cost; damage-type resistance never reduces their 1d8+10 line |
| Grand Cleave | Mode swap, not upgrade: seven-unit non-discriminating arc; no movement, bonus action, dagger, Quick Toss, or Deft Answer that turn; reaction remains available |
| Planted | Speed 0; displacement movement/prone fails if the surface accepts the boot ridges. **No AC change** |
| Deployable kite | Object interaction; 3/4 cover to crouching Medium target or half cover standing; drops Doran to **AC 21** while deployed |
| Ring + Wound Closure | Bonus action, unlimited **16 HP**, requires at least 1 HP; all healing received is maximized, including Second Wind at **30 HP** |
| Ring-held *haste* | When Wren's long-rest load targets Doran: speed 60/80, advantage on DEX saves, and the restricted haste action (Attack for one weapon attack, Dash, Disengage, Hide, or Use an Object); **no AC bonus**; 20-ft vind-rune flight cap remains |
| Vind-rune boots | Convert up to 20 ft movement to flight; *feather fall* 1/rest; preserve planted |
| Alert | Cannot be surprised while conscious; unseen attackers gain no advantage solely for being unseen |
| Sentinel | Opportunity hit stops movement; ignores Disengage; adjacent ally-targeting can trigger reaction attack |
| Mobile | Melee attack suppresses that target's opportunity attack for the turn |
| Dual Wielder | No live mechanical effect; its +1 AC is retired under the AC LOCK |
| Thermal immunity | Heat, fire, cold, and freezing deal no damage and cannot numb him; ordinary carried matter may burn and ice may restrain. The worn helm supplies a breathable atmosphere in underwater and volcanic environments, but Doran still requires oxygen and can suffocate without the helm or its support |
| No attunement | Doran's divine-made equipment cannot be attuned away |
| Liberation auras | Within 30 ft of Wren: *freedom of movement* always on, and advantage on every saving throw |

## 5. COMBAT END

1. Emit the final complete state block.
2. End any encounter-only condition or clock only when its rule says so.
3. Close the paired encounter-runtime register; after handoff, neither runtime
   half is the authority for prose or persistent state.
4. After LIVE combat, commit the confirmed position, arc clocks, active route,
   current numeric state, durable regional/artifact state, and unresolved
   endgame front/thread → DM038_L; lasting receipts → DM035_0e. After a
   simulation, never write live state;
   route requested tactical or prep findings to DM038_CH.
5. After the commit, fresh-read any volatile owner before making another
   current-state claim. Return to prose register: single camera, no beat labels.

Life-preserving intervention refunds no resources, position, local objectives,
or grade.

**Final T537.0 values:** Doran 370 HP, AC 25, 16d12 superiority. Wren 220 HP,
ward 75, 50 sorcery points, 150 total slots, DC 22.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM044_0 -->
