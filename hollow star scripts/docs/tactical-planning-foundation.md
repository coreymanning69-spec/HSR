# Tactical planning foundation

> **Module**: Hollow Star Reliquary engine, `hollowstar/tactical.py`, `spells.py`, `policies.py`
> **Status**: Foundational, first two capability sources live (weapons, spells)
> **Written**: 2026-09-26, tactical/planning pass part 2

This note records what the planning layer is, what it promises, and how the rest
of an actor's abilities (maneuvers, domains, items, skills, movement and
location) join it. Where the pass had to make a call nobody had made yet, the
call is written down here as a **decision**, with what would change it.

## 1. The one rule

**A forecast is the resolver, run as odds.** Every predictor reads the same
terms the resolver rolls against, so a plan and the roll it predicts cannot
disagree:

| Resolver (rolls, spends, moves) | Read-only twin (odds, no RNG, no writes) |
|---|---|
| `weapon_attack` | `forecast_attack` |
| `spells.cast` | `spells.preview_cast` |
| `check_target` (spends targeting-denial charges) | `target_problem` |
| `condition` | `condition_refusal` |
| `damage` | `mitigation` + `mitigate` (+ `known_mitigation`) |
| `saving_throw` | `save_odds` |
| `roll_check` / `dice` | `check_odds`, `attack_odds`, `dice_odds` |
| `spells._pay` on live dicts | `spells.payment_problem` / `payment_cost` on copies |

`cast()` is now built as: `_prepare` (pure legality) → `payment_problem`
(simulated payment) → `check_target` (spends denial charges) → `_pay` (live)
→ resolve. `preview_cast` runs the first two and stops. The test
`test_preview_legality_equals_cast` holds them together: for every case and
state, preview legality and reason equal what `cast()` does on a deep copy.

## 2. The candidate catalog: one shape for every ability

`policies.candidate_actions(run, key)` lists every concrete thing an actor can
do right now. Every row has the same shape, whatever produced it:

```
{id, source, kind, label, action, target, legal, reason, cost,
 hit, kill, expected_damage, expected_healing, forecast}
```

- `action` is a canonical action `tactical.apply` accepts unchanged.
- `cost` is `{economy: {slot: n}, resources: {name: n}}`.
- `forecast` is the full predictor output: reasons, AC, cover, per-target rows.

Planning (`plan_action`), forecast selectors (`killable_enemy`,
`likeliest_hit_enemy`, `most_damage_enemy`) and forecast conditions
(`hit_chance_gte`, `kill_chance_gte`, `expected_damage_gte`) all read this one
catalog. **A new ability becomes plannable by adding one source function to
`CANDIDATE_SOURCES`**, never by teaching the planner about it.

### 2.1 How the rest of the actor's kit joins

This is the tracking answer for "actions, locations, parts, skills and
abilities." Each is a *source* that projects rows into the catalog, and each
must bring its read-only twin first:

| Source | State it reads today | Twin still needed |
|---|---|---|
| Weapon modes (live) | `weapon_mode`, loadout, alternate modes, bonus pools | done |
| Spells (live) | spell catalog, `known_spells`, slots, energy, metamagic | done |
| Maneuvers | superiority dice, `maneuvers.apply` | `forecast_maneuver` built on `forecast_attack` + save odds |
| Domains / signature features | `domains.apply`, per-feature resources | per feature; most are save or heal shaped and can reuse `_target_forecast` |
| Items and consumables | dungeon inventory, affixes (`affix_runtime`) | `preview_consume`; potions are heal shaped |
| Skills and contests | `skill_check_bonus`, `contest` | `contest_odds` exists; shove/grapple/trip rows need only a wrapper |
| Movement and location | positions, `move_cost`, terrain, cover, `path_squares` | a movement source that proposes squares scored by what they unlock (cover, range bands, flanking) |
| Body parts / rig state | paperdoll and puppet presentation only | nothing mechanical yet; if parts ever carry rules (a maimed arm, a broken wing), they enter as statuses or rule flags and every twin above reads them for free |

**States a row can be in.** The catalog already distinguishes the states that
matter to automation, and new sources should reuse them rather than invent new
ones:

- *legal*: `legal: True`.
- *blocked by rule*: `legal: False`, `reason` is the resolver's own refusal
  text (range, cover, side, silenced, target count).
- *unaffordable*: `legal: False`, `reason` is the payment refusal
  (`bonus already spent`, `insufficient slot_3_general: …`).
- *permission-blocked*: legal, with `forecast.blocked` carrying the target's
  tell, which is how `weapon_attack` reports it.
- *priced / unpriced*: `forecast.notes` says when an operation (teleport, gate,
  utility) is legal but has no numbers.
- *contained target*: per-target `notes: ["target is contained"]`, no effect.
- *concentrating*: `self_concentrating` reads combat `concentration`.

Hidden state is filtered by the source, never by the planner (see §3).

## 3. What the party knows (decision: uninformed player macros)

Corey's call, 2026-09-26: **party forecasts are uninformed, enemy AI is
informed.**

- `tactical.knowledge(run, side)` is a ledger in `run.context["knowledge"]`,
  keyed by **creature name** so a lesson learned on one Town watch carries to
  the next one, and it survives save and load.
- `damage()` records what each landed, unwarded instance showed the attacking
  side: `immune`, `resisted` or `normal`, plus `vulnerable` and any conversion.
- `known_mitigation(..., informed=False)` prices an unseen damage type as a
  plain hit and a seen one by what was seen.
- `policies.informed(run, key)` is False for `p*` actors and True for `e*`.
  `run.context["forecast_informed"] = {"p": true}` switches the party to full
  information, for an easy mode or debugging.

**Decision: legality stays informed.** A targeting-denial affix or total cover
still makes a forecast illegal even if the party has never seen it. Otherwise
a gambit would pick an action the engine then refuses, and automation would
stall. The leak is one bit ("that doesn't work"), and it matches what a player
learns by trying. **Revisit** if a hidden denial should be *discovered*: record
it in the ledger on first refusal, and let an uninformed forecast report
`legal: True, risk: "unknown"` until then.

**Decision: stat-block facts stay visible.** Doran's divine plate and the
Tarrasque's mundane-weapon rule are printed, not hidden, so the mask keeps them.
Lattice conversions and affix resistances are hidden until seen.

## 4. Planning

`plan_action(run, key, goal, spend=True)`, where goal is one of:

- `damage`: most expected damage. Friendly fire in an area counts against it.
- `kill`: best chance to drop an enemy with this one action. **Decision:**
  returns None when no candidate can kill, so a gambit list falls through to its
  next line instead of quietly downgrading to `damage`. Put a `damage` plan
  below it if that is what you want.
- `heal`: the most-hurt ally any candidate can reach, then the most healing.

**Decision: thrift band.** Candidates within `PLAN_BAND` (90%) of the best score
are treated as tied, and the tie goes to the one that burns the least:
`resource_weight` weighs a level-N slot as N and anything else as its count.
`spend=False` restricts the planner to candidates costing no limited resource.
Ties then break on the catalog id, so plans are deterministic and replayable.

## 5. Gambit vocabulary added

| Key | Where | Meaning |
|---|---|---|
| `hit_chance_gte` | when | percent, judged on the resolved then-action |
| `kill_chance_gte` | when | percent, same |
| `expected_damage_gte` | when | points, same |
| `spell_ready` | when | spell id or list: payable now, no metamagic, targets ignored |
| `self_concentrating` | when | bool |
| `killable_enemy`, `likeliest_hit_enemy`, `most_damage_enemy` | target / center | forecast-ranked enemy; None when nothing scores |
| `{"type": "plan", "goal": …, "spend": bool}` | then | planner picks the action |
| `center: "<selector>"` | then (area spell) | aim at that actor's square |

Forecast conditions **fail closed**: an action with no forecast (move, dodge)
or a save spell with no hit chance never satisfies `hit_chance_gte`.
`_legal_now` now also rejects an attack or cast whose forecast is illegal, on
the actor's own turn only, so an unreachable gambit falls through. The default
`combat_action` fallback is unchanged. It now works for Wren's Healing Word,
because `cast()` accepts `target` as a one-item `targets`.

## 6. Roll math on screen

Every damage event carries `evidence.damage_parts` (rolled terms: label,
expression, rolls, modifier, critical, maximized, total) and
`evidence.damage_steps` (engine changes before mitigation: affix, empower,
`saved: half`). The damage result adds `evidence.adjustments` (plate,
resisted, immune, vulnerable, ward, temporary HP, overkill). The combat
director's `damageMath` prints them in order:

`2d6×2+4 [6,5,4,4] +sneak attack 2d6 [3,1] = 27 slashing → 13 (resisted)`

Heals print from `evidence.expression/rolls/rolled/adjustments`:
`1d4+5 [4] max = +9 → 4 (max HP)`.

## 7. Rulings made in this pass (flag if wrong)

- Spell attacks crit on a natural 20 only (`spells.SPELL_CRITICAL`); no caster
  feature lowers it yet.
- Maximize and Empower now apply to each Magic Missile / Robe Star dart. Before,
  their cost was paid and the effect thrown away.
- Empower remains the engine's ×1.5 (floored), not 5e's reroll.
- An area spell rolls once per cast (per Twin repeat), and every creature in it
  takes that roll, which is the 5e reading and what the old code meant.
- A contained creature (Forcecage, Imprisonment) is untouched by a save spell:
  it makes no save and takes nothing. Niv's Descent skips it the same way.
- Tarrasque attacks now read the shared attack situation (cover, prone, Help,
  distraction) and RULE-GLARE against Doran, and carry `damage_parts`.

Left as is, by instruction: Grand Cleave's crit doubles its final total
(DM044_0); ranged-in-melee disadvantage is unmodelled.
