---
id: DM046_0
title: "Hollow Star Reliquary — Design, Runtime, and Promotion Framework"
type: reference
subtype: scenario-system-ref
load_priority: load-on-explicit-hollow-star-design-sandbox-or-forge-call
canon: T-framework / SANDBOX-system / FORGE-candidate
verse: Divineverse
timeline: post-level-20 / gate-not-yet-placed
beat_range: reference / no-played-beat
arc: hollow-star-reliquary
era: future-sanctum-stewardship
status: approved-design-target / implementation-and-balance-pending
authority: authoritative-for-hollow-star-design-target-run-boundaries-and-promotion-contract
updated: 2026-09-09
volatility: slow
arc_scope: hollow-star-reliquary
derived_from: null
predecessor_file: N/A
successor_file: DM046_1

scope:
  covers:
    - the approved Hollow Star Reliquary premise and five-floor identity
    - the separation of permanent design rules, disposable run state, and promoted Forge results
    - procedural room, opposition, resistance, equipment, and reward generation
    - provisional depth-based probabilities for stacked enemy loadouts
    - Sera and Ember's design role, Soliera's creation authority, and the Sanctum commentary channel
    - the intended Python engine, agent command surface, and eventual mobile play path
    - the testing and tuning required before live use
  use_case: load when designing, implementing, testing, invoking, or promoting the Hollow Star Reliquary
  not_for:
    - asserting that the gate has appeared in played chronology
    - inventing or overriding finalized level-20 statistics outside their source authorities
    - treating provisional percentages, item caps, or encounter numbers as settled balance
    - storing generated rooms, seeds, temporary equipment, or Sandbox outcomes in the corpus
    - allowing an AI narrator to voice Soliera, Sera, Ember, or Deashi without Corey's explicit active-session delegation
    - replacing DM041_A, DM041_B, DM044_0, or DM044_1 as Doran and Wren's mechanical authorities

xref_concepts:
  - hollow-star-reliquary
  - original-scenario-system
  - level-20-dungeon
  - procedural-room-generation
  - deterministic-seed
  - depth-pressure
  - stacked-loadouts
  - reliquary-imprints
  - sandbox-run-isolation
  - forge-promotion-receipt
  - mobile-agent-play
  - divine-specification

canon_flags:
  - "FRAMEWORK LOCK: This file is the approved build target. The implementation, final level-20 balance, generated rooms, and played outcomes do not yet exist in canon."
  - "GATE STATUS: The Hollow Star gate has not yet appeared at the live edge. Its location, moment of arrival, and first response remain play-gated."
  - "DIVINE CREATION: Sera and Ember may imagine the Reliquary together; Sera may ask Soliera to make it real; Soliera's authored yes is sufficient to instantiate the specified dungeon. Corey supplies the girls' actual dialogue and consent."
  - "RUNTIME INTEGRITY: The generated snapshot and schema-2 handshake establish source and surface integrity; Sandbox is isolated and Forge requires explicit intent."
  - "TEST-AND-TUNE: Every percentage, modifier cap, room budget, reward rule, and encounter target here is provisional until simulation and table play show that it is legible, dangerous, and enjoyable."
  - "SANDBOX ISOLATION: Sandbox seeds, rooms, loot, damage, deaths, discoveries, and dialogue create no chronology, inventory, relationship, or worldstate trace."
  - "FORGE PROMOTION: Forge play may produce a canon-candidate receipt, but no generated result enters an owner without Corey's explicit promotion."
  - "BLIND-PLAY PROTECTION: Store generation rules and public floor identity, not unopened room contents. Do not volunteer future rooms, hidden loadouts, or generated counters."
  - "MECHANICS ROUTE: DM041_A and DM041_B own source mechanics; DM044_0 and DM044_1 together are the Doran/Wren combat and simulation runtime pair."


purpose: >
  Preserve what the Hollow Star Reliquary is being built toward without
  pretending unfinished balance is settled or its gate has already appeared.
  Executable rules belong in the Python project; disposable run state remains
  outside the corpus; only explicitly promoted Forge results become history.

ai_directives:
  - treat the floor identities and divine creation premise as approved design, not a played event
  - label numeric generation rules as provisional until simulation and table play establish that they are legible, dangerous, and enjoyable
  - never generate or reveal unopened room contents during a blind run
  - use deterministic seeds so disputed resolutions can be replayed without exposing future rooms
  - keep canonical character equipment separate from temporary Reliquary overlays
  - make strong defenses observable and learnable; failed actions should reveal information rather than produce arbitrary nullification
  - keep the rules engine authoritative for rolls and state while the conversational agent handles narration and intent translation
  - never let a Sandbox run update canon and never let a Forge receipt self-promote
  - preserve Corey's default voice ownership of Soliera, Sera, Ember, and Deashi; any delegation is named and active-session-only
---

# DM046_0 — Hollow Star Reliquary — Design, Runtime, and Promotion Framework

## 1. STATUS AND PURPOSE

The Hollow Star Reliquary is an **approved build target**. It is not yet a
completed dungeon, balanced level-20 module, appeared gateway, or played event.
This file exists so the concept can be implemented consistently without turning
unfinished balance decisions or future generated rooms into premature canon.

Three categories must remain distinct:

1. **Settled design intent:** the Reliquary's identity, five-floor structure,
   divine creation premise, room-driven procedure, stacked-equipment threat
   model, Sandbox/Forge boundary, and blind-play requirement.
2. **Provisional implementation targets:** percentages, affix caps, temporary
   item slots, encounter budgets, persistence format, command interface, and
   carry-out rules. These are hypotheses to test, not immutable mechanics.
3. **Unmade and unplayed content:** generated rooms, enemy builds, loot,
   conversations, casualties, and chronology. The generated Step 5 party
   snapshot and certified engine receipts exist outside the corpus; neither
   creates played canon or authorizes a corpus write.

The operating principle is: **encode enough to build and run the system, but do
not pre-author the experience the system exists to produce.**


## 2. NARRATIVE AND DIVINE PREMISE

Sera and Ember imagine a dungeon together. Sera asks Soliera to make it happen
as they imagine it. If Corey authors Soliera's yes, Soliera creates a real place
to that specification. A gateway can then appear wherever the played scene
establishes it, and the Sanctum can send the field Stewards to investigate.

The Reliquary's artificial rules are real because Soliera makes a real
environment whose specification contains them. Percentages, room boundaries,
temporary item laws, procedural residents, transitions, resets, and reward
restrictions need no mortal spell-system explanation. Sera and Ember provide the
whimsy, horror, curiosity, and game-like confidence; Soliera's creation gives
those ideas ontological force.

This framework does **not** place the gate. Its location, witnesses, staff
response, dialogue, and first entry are preserved for Forge play.


## 3. DESIGN GOALS

The finished system should:

- challenge level-20 Doran and Wren without confiscating or suppressing their
  finished identities;
- make ordinary-looking people dangerous through equipment, coordination, local
  knowledge, and stacked interactions rather than universal superhuman stats;
- support extreme monsters, resistances, permissions, and conceptual defenses
  while keeping those rules discoverable;
- use the same equipment grammar for residents, monsters, rivals, and temporary
  field-Steward rewards;
- preserve shopping, negotiation, theft, murder, rest, avoidance, investigation,
  exploration, and environmental play;
- increase pressure on lower floors and in later rooms on the same floor;
- preserve semi-blind play by generating unopened rooms only when reached;
- support consequence-free Sandbox runs and later binding Forge runs through the
  same engine;
- run locally first and later accept a mobile or hosted interface without
  rewriting its mechanics.

The dungeon should feel like a real world governed by game laws. Residents can
trade, form factions, hoard complementary pieces, study earlier rooms, exploit
resets, lie about item properties, and recognize dangerous newcomers.


## 4. FIVE-FLOOR PUBLIC BLUEPRINT

Floor identities are public design information. Exact rooms, residents,
loadouts, paths, and counters remain hidden until discovery.

### Floor One — The Town Above the Well

A functioning town is populated by apparently normal people who are subtly
creepy. The field Stewards may shop, investigate, steal, threaten, kill, leave, or
sleep. If they sleep under the town's control, the residents organize and try to
overwhelm them at night.

The townspeople become dangerous through coordinated items, resistance sharing,
prepared terrain, alarms, formation effects, and knowledge of local rules. They
do not all need level-20 character sheets. The well conceals or constitutes the
route downward.

### Floor Two — The Machine Works

An industrial metal environment contains slow-moving machines with extreme
durability and armor. Cleaners classify the field Stewards as trash or contamination.
Larger units include humanoid colossi approximately forty feet high and twenty
feet wide.

The floor tests target priority, armor solutions, movement around slow threats,
industrial hazards, and subsystem damage. The route downward is a hatch that
must be located, reached, opened, or made usable.

### Floor Three — The Three Dragons

A large dungeon is divided among one white dragon, one red dragon, and one black
dragon. Each has an approximately ten-person organization and may have young,
hatchlings, or other draconic dependents. Territories, servants, alliances,
rivalries, and equipment strategies differ.

This is not automatically three consecutive dragon fights. Negotiation,
territorial manipulation, alliance, assassination, theft, misdirection, and
provoking conflict between lairs remain valid.

### Floor Four — The Sunless Sea

The horror floor contains lightless water, drowned structures, ruined vessels,
unstable shores, and uncertain distances. Ghosts, ghouls, demons, abyssal
creatures, possession, corpse-eating ecologies, and hostile manifestations
belong here.

Fear should emerge from environment, implication, navigation, pursuit, voices,
and things that violate bodily expectations—not only higher undead hit points.
The atmosphere can obscure understanding, but the mechanics remain fair and
discoverable.

### Floor Five — The Opulent Palace and Cocoon

The final floor is a perfectly clean, super-opulent palace. A rival party of five
level-20 adventurers waits in a chamber containing a large cocoon. The working
target is a twenty-round crisis clock. If the rival party is not fully defeated
before it expires, the cocoon opens and releases a Tarrasque.

The resulting conflict can include surviving rivals, Doran and Wren, the
Tarrasque, and competing goals of survival, victory, escape, or control. Rival
builds, geometry, cocoon interactions, timer visibility, Tarrasque translation,
and victory conditions require level-20 testing. Twenty rounds is an approved
dramatic target but remains a tuneable variable.


## 5. RUNTIME INTEGRITY

The Reliquary uses finalized source authorities and the paired DM044_0/DM044_1
runtime. `local-check` writes a schema-2 handshake binding source hashes,
snapshot, and desktop workspace identity. The runtime suite is on demand, not
a mode gate. Sandbox remains isolated; Forge still requires explicit intent and
an authored entry fixture. The snapshot is derived input, never corpus authority.


## 6. THREE-LAYER IMPLEMENTATION

### Corpus reference

This REF owns stable intent, call-up rules, divine premise, floor identity,
state boundaries, and promotion. It does not reproduce generated content or
become a second copy of the executable tables.

### Executable Python engine

The game project owns deterministic mechanics:

- room and encounter generation;
- floor and room depth pressure;
- equipment, affixes, sets, permissions, and resistances;
- enemy and faction loadouts;
- initiative, damage, conditions, clocks, and resources;
- shops, rewards, and temporary inventory;
- seeds, replay information, and save/load behavior;
- structured outcomes consumed by a narrator or interface.

A likely organization is:

```text
docs/hollow_star_reliquary.md
data/reliquary/
  floors
  room_templates
  equipment
  affixes
  sets
  resistance_packages
  rewards
sera/reliquary/
  engine
  generation
  state
  resolution
  storage
  adapters
```

Exact filenames remain subordinate to the existing game's architecture.

### Disposable run state

Sandbox saves remain outside the corpus, manifests, and canon ledgers. A local
implementation should use an excluded location such as:

```text
.local/reliquary_runs/<run-id>.json
```

The code repository should ignore that directory. The Divine Mythos corpus is
not a Git repository and should never receive these saves.

A run stores mode, engine version, party snapshot version, seed, current floor
and room, rooms already reached, revealed facts, resources, temporary inventory,
mechanical events, and receipt status. Unopened rooms should not be serialized
in human-readable form merely for convenience.


## 7. SANDBOX AND FORGE

### SANDBOX

A Sandbox run uses the real engine and dice but produces no
Divineverse history. It may test builds, tune probabilities, find degenerate
item combinations, run a complete blind dungeon for fun, or replay a seed after
an engine dispute.

It will not update timeline beats, live ledgers, inventories, relationships,
setting state, or divine biography. Mechanical lessons can inform later
maintenance, but the simulated event remains non-canon.

### FORGE

Forge uses the same engine and state schema with a generic, placeless threshold
fixture. Location, chronology, and dialogue remain unset; no corpus write
occurs mid-room or mid-combat; and the completed receipt waits for Corey's
explicit promotion.

Promotion is selective. Chronology, inventory, relationships, witnesses, or a
carried-out item may be promoted while seeds, debug events, and hidden tables
remain implementation data.


## 8. ROOM CONTRACT

Every generated room should define:

1. **Function:** settlement, transit, market, lair, hazard, sanctuary, ambush,
   faction node, boss approach, or exit.
2. **Residents and motives:** who is present, what they want, and what they do if
   ignored.
3. **Terrain and law:** geometry, visibility, hazards, exits, and local
   exceptions.
4. **Loadout identity:** equipment, set interactions, resistances, permissions,
   and group synergies.
5. **Readable tells:** evidence that points toward the build.
6. **Counterplay:** several ways to exploit, bypass, separate, disable, bargain
   with, or overpower the room.
7. **Escalation:** what changes after delay, violence, rest, theft, or retreat.
8. **Reward:** information, access, currency, temporary item, component,
   alliance, safe rest, shortcut, or nothing.
9. **Persistence:** what remains true if the field Stewards leave and return.

The engine knows the record. The narrator reveals only what the characters can
perceive, infer, test, or learn.

The transport boundary is explicit. Each beat carries a separate PERCEIVED
artifact for narration and retains a SEALED room record for engine resolution.
PERCEIVED contains terrain and law, visible residents and posture, an authored
apparent function, readable tells, cumulative persistence, and facts already
earned by play. SEALED contains true function, motives and ignored behavior,
loadout identity, counterplay, escalation, reward, and unrevealed room data.
The narrator never receives SEALED implicitly. A deliberate room-record fetch
is receipted, and every reveal moves one-way into the run's durable perceived
facts rather than being recomputed or re-sealed on a return visit.

Every planted tell carries an authored observation DC and stable identifier.
`test-perception` resolves that DC in Python, records the roll and result, and
returns a new perceived fact. It is not a prose decision about whether the
party noticed something.


## 9. STACKED ITEMS AND RELIQUARY IMPRINTS

Doran and Wren retain their canonical level-20 equipment. Difficulty should not
come from confiscating their identities. Dungeon rewards are therefore best
implemented as temporary **Reliquary Imprints** layered over normal gear.

The first target uses eight positions matching the existing Python grammar:
helmet, necklace, cloak, torso, two rings, legs, and boots. Eight is provisional;
testing may favor fewer active seals or a simpler overlay.

Enemy equipment should form coherent builds. An ordinary human group can become
dangerous when one member projects a shared resistance, another redirects
healing, another interrupts spellcasting, paired rings reflect an attack, and a
formation bonus persists only while a keystone wearer remains in position.

The provisional maximum is five meaningful modifiers on one exceptional item or
loadout element. Cognitive load must be measured across the whole encounter,
not per item. Strong effects should often be horizontal: permissions,
conversions, conditional immunity, reflection, group resistance, terrain
authority, navigation protection, or a one-use exception to a room law.

Most Imprints should dissolve or become inert outside. Whether a clear permits
one item per field Steward, one shared prize, conversion into a Sanctum-made item, or
no permanent carry-out reward remains an explicit testing decision.


## 10. PROVISIONAL DEPTH FORMULA

The first implementation should test:

```text
P(stacked loadout) = clamp(
    0.12
    + 0.14 × (floor - 1)
    + 0.025 × (room - 1)
    + encounter modifier,
    0.00,
    0.92
)
```

| Encounter class | Modifier |
|---|---:|
| Ordinary room | +0% |
| Large coordinated group | +10% |
| Elite group | +18% |
| Boss or floor guardian | +25% |

| Example | Provisional chance |
|---|---:|
| Floor 1, Room 1, ordinary | 12% |
| Floor 1, Room 10, ordinary | 34.5% |
| Floor 2, Room 5, large group | 46% |
| Floor 3, Room 5, ordinary | 50% |
| Floor 4, Room 8, elite | 89.5% |
| Floor 5 boss | 92% cap |

This roll determines whether an encounter receives a deliberately synergistic
package. It does not decide whether anyone owns any magic item and does not
replace floor logic. Machines may always possess subsystems, dragons may always
have hoards, and the palace rivals should always have complete builds.

After success, a second weighted process chooses complexity, rarity, cohesion,
resistance strength, and keystone structure. All numbers remain provisional.
Testing must avoid both extremes: stacks too rare to matter, or every late room
becoming an unreadable wall of exceptions.


## 11. FAIRNESS AND MONSTER-DRIVEN PUZZLES

The Reliquary's puzzles emerge from monsters, equipment, terrain, motives, and
behavior—not detached riddles or logic grids.

- Every strong resistance or immunity has an observable tell.
- A failed action reveals useful information when the characters could notice
  the failure.
- Damage immunity does not automatically imply immunity to movement, restraint,
  terrain, conditions, theft, separation, or negotiation.
- Delivery blocking, damage blocking, effect immunity, and conceptual permission
  remain distinct.
- Every mandatory room preserves more than one meaningful response category.
- Enemies may lie, but the engine does not lie about resolved mechanics.
- Blind play protects future information; it never excuses a counter invented
  retroactively after the field Stewards act.

The goal is not “solve the designer's answer.” It is “understand enough of the
living threat to create an answer.”


## 12. SERA, EMBER, AND WREN'S CHANNEL

The dungeon may support intermittent check-ins through Wren's divine-family
line. Wren's divine source remains Soliera/the overgod. Ember may stabilize,
inspect, or mediate the connection, and Sera's voice or presence may ride the
family connection when permitted. Commentary is separate from spellcasting;
disrupting contact does not switch off Wren's class features.

Sera supplies reaction, appetite, mockery, alarm, and delight. Ember supplies
curiosity, pattern questions, and fascination. Neither becomes an omniscient
solution dispenser. Check-ins should occur deliberately in safe rooms, rarely
interrupt for something extraordinary, and respond only to what the field Stewards
report or transmit.

Corey owns the girls' words. An automated narrator may make contact available or
describe channel status. It does not invent their dialogue unless Corey
explicitly delegates a voice in the active session.


## 13. AGENT AND MOBILE TARGET

The engine must not depend on one AI provider. Codex, ChatGPT, Claude, Cowork, a
future phone UI, or a human terminal should call the same state transitions.

The first adapter should expose one-action commands:

```text
start-run
observe
submit-action
resolve-round
show-party
show-revealed-loadouts
reveal-room-record
test-perception
show-temporary-inventory
sanctum-check-in
save-run
resume-run
end-run
create-forge-receipt
```

Inputs and outputs should be structured. The conversational agent translates
intent and narrates revealed results; Python owns rolls, hit points, resources,
conditions, item triggers, clocks, and persistence.

`reveal-room-record` is an affirmative SEALED fetch and must land in the run
receipt. `test-perception` accepts a party actor and tell identifier, resolves
the authored DC using the run RNG, and returns only the resulting perceived
fact and visible evidence. Both commands are available to the DESIGN adapter;
they do not open Sandbox or Forge.

The near-term phone target is remote control of a local desktop agent while the
Windows host runs the project. After the engine proves fun, the same commands
can be exposed through an authenticated service or MCP server with room status,
action buttons, inventory, initiative, and revealed resistances. Vendor and
hosting details are implementation concerns and must be refreshed against
then-current product capabilities.


## 14. TEST AND TUNING PROGRAM

### Phase 1 — Correctness

- Reproduce the certified level-20 runtime pair exactly.
- Verify deterministic replay and save/resume.
- Verify that identical seeds and actions reproduce perceived facts, sealed
  fetch receipts, and return-visit persistence exactly.
- Verify that ordinary narrator payloads contain no sealed room fields and that
  sealed data appears only after `reveal-room-record`.
- Verify triggers, resistances, permissions, clocks, and resources.
- Confirm Sandbox cannot write corpus paths.
- Confirm a Forge receipt remains inert until promoted.

### Phase 2 — Combination testing

- Generate thousands of loadouts without narrative prose.
- Detect contradictory, circular, permanently invulnerable, or action-denying
  combinations.
- Measure complexity per encounter, not only per item.
- Test ordinary-human group builds separately from monsters and rivals.

### Phase 3 — Level-20 encounters

- Establish how quickly Doran and Wren erase unprepared opposition.
- Test bosses, coordinated groups, machines, dragons, undead, abyssal threats,
  and rival level-20 parties.
- Test strongest openings, conservation, retreat, stealth, negotiation, theft,
  rest, and environmental exploitation.
- Tune depth pressure without making late rooms monotonously stacked.

### Phase 4 — Blind and mobile usability

- Confirm tells support inference without designer knowledge.
- Confirm no hidden loadout or future-room leakage.
- Confirm summaries remain understandable on a phone.
- Confirm Sera/Ember check-ins add character without solving rooms.

### Phase 5 — Full rehearsal

- Measure attrition, rests, shopping, rewards, and variety across whole floors.
- Check that long room counts do not cap the formula too early.
- Run all five floors in Sandbox before Forge.
- Revisit the cocoon clock only after the rivals and Tarrasque are stable.

The first certified version must keep Doran and Wren recognizably themselves,
produce explainable mechanical results, make ordinary residents dangerous for
legible reasons, preserve multiple solutions, prevent Sandbox contamination,
prevent self-promotion, and support phone play without manual Python operation.


## 15. OPEN DECISIONS

The following remain intentionally unresolved design choices:

- final Imprint slot count and modifier cap;
- branch/depth handling and the final probability formula;
- item drops versus affix components, currency, or reward choices;
- carry-out rewards and possible Sanctum conversion;
- death, reset, ejection, recovery, and re-entry rules;
- whether inhabitants are created people, volunteers, imported residents,
  procedural manifestations, or a mixture;
- palace rival identities and builds;
- the gate's first location and chronology.

The perceived/sealed transport boundary is resolved: apparent function is
authored separately from true function, and every planted tell owns an
authored observation DC. The remaining section-15 decisions above are
unaffected.

These are not blanks to fill casually. They are the author and test decisions
between this framework and a certified release.


### 15A. LOCAL CUSTOM CHARACTER CREATION CONTRACT

The desktop runtime may create non-canon local adventurer profiles without
altering the imported Divine Mythos roster or advancing certification. The
initial versioned registry exposes five ancestries — Human, Elf, Half-Elf, Orc,
and Goblin — and five HSR-native, 5e-shaped classes — Warrior, Magician,
Archer, Rogue, and Cleric. Every ancestry/class pairing is legal at levels
1–20. Multiclassing and specializations remain reserved extension points.

Ability generation is deterministic 4d6-drop-lowest with a receipt and no more
than one complete replacement set; automatic and explicit assignment are both
supported. Ancestry modifiers apply after the base array. Goblins carry Luck
+5 for authored Luck checks and a monster-facing interaction lane; every other
ancestry likewise owns at least one explicit noncombat hook.

Magician and Cleric known spells cost five selection points per level, with
cantrips costing one and ranked spells costing rank plus one; maximum spell
rank is `min(9, ceil(level / 2))`. Selection points do not replace the separate
casting-energy resource. Each profile receives one deterministic weighted
origin item. The Wayfinder amulet may negate a failed trap check on a d100 result
of 25 or less, once for that trap.

Clients must preview a build and return its build hash to confirm the exact
draft before an atomic local-profile write. Profiles retain their build receipt,
known spells, ancestry/class rules, interaction tags, and origin item; a run
freezes the chosen profile state. The runtime reads legacy local profile schema
v1 with additive defaults and writes schema v2. It never writes these choices
into canon, rewrites an imported Divine actor, or lets narration choose RNG,
legality, hidden state, persistence, or math.


## 16. CALL-UP AND PROMOTION

- **“Hollow Star design”** loads this REF for architecture or implementation.
- **“Hollow Star Sandbox”** will load this REF plus the certified DM044_0 and
  DM044_1 runtime pair, then start or resume an isolated non-canon run.
- **“Hollow Star Forge”** will load full Forge context, establish the gate in
  authored play, and run with binding state only after explicit Forge intent;
  the default fixture is generic and placeless.
- **“Promote Hollow Star run <id>”** inspects the finished receipt, identifies
  exact owners, and requests approval for bounded corpus changes. It does not
  itself authorize automatic writing.

The compact router mounts the design, review, sandbox, and Forge contracts;
dedicated run and profile roots remain disposable local state.


<!-- CORPUS REVISION: 9.0 -->

<!-- END DM046_0 — generated runs remain outside the corpus until explicit promotion -->
