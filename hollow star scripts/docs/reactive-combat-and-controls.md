# Reactive combat, autonomous enemy turns, and combat controls

> **Module**: `hollowstar/policies.py`, `tactical.py`, `maneuvers.py`, `dungeon.py`,
> `run_service.py`, `host.py`, `view_model.py`; `web/app.js`, `web/combat-input.js`,
> `web/combat-director.js`
> **Status**: Alpha foundation. Engine side is tested; the client side is
> covered by one real-browser check (`tests/reactive-combat-browser-check.cjs`).
> **Written**: 2026-09-27

The Python engine stays authoritative. Every automated choice below is an
ordinary engine action picked by `policies.py` and resolved by
`tactical.apply`, so it rolls, spends and records like a clicked one. The
client only turns input into those same actions and plays the receipts.

## 1. NPC reactions no longer freeze a fight

**Before:** `tactical.move` opened an opportunity window for the enemy and
`apply` then refused every other action until someone answered it. The web
turn panel only drew windows for party reactors, so an enemy's window (or
the Tarrasque's legendary window at the end of every turn) stalled the
encounter behind a manual "Advance NPC turn".

**Now:**

- `policies.reaction_action(run, window)` answers any window for whoever
  holds it:

  | window | answer |
  |---|---|
  | `opportunity` | take the attack (declines if the target is already down) |
  | `brace` | Brace while a superiority die remains |
  | `hit` | Shield when offered and a level-1 slot remains; Parry when the blow is at least `PARRY_FLOOR` (10) or would drop the defender |
  | `legendary` | the Tarrasque spends a point: claw (15 ft), else tail (20 ft), else declines |
  | `spell` | Wren's staff absorbs it while her reaction lasts |
  | `save` | Aura of the Unbound when the window offers it |
  | `deft_answer`, `command` | take it |
  | anything else | decline |

  `combat_action` now delegates its pending branch to it. Before, a `spell`
  or `save` window fell through to a weapon attack.
- `tactical.settle_npc_reactions(run, apply_fn=None)` resolves every
  pending window whose reactor is AI-controlled (`actor.controller != "player"`),
  in order, bounded by `AUTO_REACTION_LIMIT`. A refused choice is declined,
  so it can't loop. Windows held by player-controlled reactors stay pending.
- `dungeon.act_and_advance` runs it after the player's action and after
  every opposition step, going through `dungeon.act` so combat
  completion, rewards and defeat get their usual bookkeeping. Settled
  reactions ride on the result as `auto_reactions`.
- `tactical.apply({"type": "move"})` does the same **only when
  `run.context["auto_npc_reactions"]` is set**. **Decision:** plain
  `tactical.move` keeps returning `movement_pending`, which is what the
  existing reaction-timing tests (and anything calling the tactical layer
  directly) rely on. Orchestrators opt in; the dungeon path already does.
- Every reaction result is tagged `reaction_kind` (the window it answered).
  `public_event_summary` shows a `reaction_and_movement` receipt as its
  strike (roll, target, damage) plus the committed step, so the combat
  director has something to animate.

## 2. Enemy aggression

- **Multiattack** already worked: `combat_action` keeps attacking while
  `economy.action or economy.attacks`, then presses a declared bonus pool.
  It's now pinned by `test_multiattack_keeps_swinging_until_the_attacks_are_spent`.
- **Tarrasque turns** (`_tarrasque_turn`): the five-attack routine goes
  through the `monster` action, choosing bite → horns → claw → tail by
  expected damage among the attacks whose reach touches a foe. Swallow
  fires when the bite already holds a Large-or-smaller target. When nothing
  reaches, it closes the distance through `approach`, and it ends the turn
  once the routine is spent. Before this, the Tarrasque sent a plain
  `attack`.
- **Spellcasting enemies** (`_enemy_spell`): a non-party actor with
  `known_spells` casts the planner's best damaging spell when it beats its
  best weapon expected damage.

## 3. `design_drain_npc`: one call plays the NPC steps

`RunService.drain_npc(run_id, max_steps=12)` and the host command
`design_drain_npc` play consecutive AI steps (moves, attacks, reactions, end
of turn) and stop **before acting** when:

- a player-controlled actor holds the turn (`player_turn`),
- the first pending window belongs to one (`player_reaction`),
- combat completes (`combat_complete`) or the dungeon run ends (`run_ended`),
- or after `DRAIN_NPC_LIMIT` (12) steps (`step_limit`: call again).

A refused policy choice becomes a decline or an `end_turn` (marked
`policy_refused`), so a bad choice can't stall the drain. The reply carries
`receipts` (one public receipt per step, in order) and
`drain: {steps, stopped, next_actor}`. Off a player's turn it is a no-op
with `stopped: "player_turn"`.

`design_action` and `design_turn` replies also carry `receipts`: every
nested `auto_reactions` / `opposition_turns` step. **Why:**
`view.recent_receipts` holds one summary per transition, so the enemy
turns played inside a player's end-of-turn never reached the combat
director. Before this, their damage only showed as "inferred" hits from HP
drops.

## 4. Planning: maneuver and contest candidates

Two read-only twins (no RNG, no writes; tested against a deep snapshot):

- `maneuvers.forecast_maneuver(run, key, action, informed)`: the attack
  maneuvers plus Quick Toss. It uses `forecast_attack` with two new
  keywords: `extra_damage` (the superiority die as its own PIERCING,
  resistance-bypassing damage call, doubled on a crit) and `attack_die`
  (Precision Attack's d12 on the roll). It adds the rider's DC 22 save
  (`save_odds`) and the consequence's refusals as `control` = P(rider
  lands), plus `effect`. Sweeping Attack adds the second target's expected
  damage; Maneuvering Attack requires an ally with a reaction.
- `tactical.forecast_contest(run, key, action)`: shove (push), trip
  (shove/prone), grapple, help, dodge, disengage, dash. It uses the
  transitions' legality (contact range, size, economy, Cunning Action),
  `contest_odds` over the same skills as `success`, and the consequence's
  refusals (threshold immunity, lattice denial, planted, obstructed square)
  for `control`. `hit` is None, so `hit_chance_gte` gambits never match a
  contest.

`_maneuver_candidates` and `_contest_candidates` join `CANDIDATE_SOURCES`.
Rows gained a `control` field, and ids gained the maneuver name
(`maneuver:Trip Attack/dagger::e0`), so every id stays unique. A test
checks that forecast legality equals `tactical.apply` on a deep copy for
every maneuver and contest row.

`plan_action` has two new goals:

- `control`: the likeliest consequence on an enemy; None when nothing can.
- `defend`: Dodge (else a bonus-action Disengage) while a conscious foe is
  within 5 ft; None when unthreatened.

**Changed behaviour, on purpose:** `plan_action(goal="damage")` for Doran
may now pick a maneuver, which costs one superiority die. A thrift weight
of 1 loses to a d12 of extra damage. `test_gambit_plan_and_forecast_conditions`
now accepts `attack` or `maneuver`. **Revisit** if dice should be saved for
kills: weigh `superiority_dice` higher in `resource_weight`, or plan with
`spend: false`.

## 5. Client: autonomous opposition

- After any `work()` completes, `scheduleNpcDrain()` checks whether the
  host has handed the decision (turn or first reaction window) to a
  non-player combatant. If so, it calls `design_drain_npc`, up to 8 times
  while it reports `step_limit`. A drain that changes nothing isn't
  retried until the combat state moves, so a bad state can't make it spin.
- In dungeon runs the host usually plays the opposition inside the
  player's own request (`act_and_advance`), so the drain mostly matters
  for `manual_opposition` runs, the turn cap, and any other orchestrator.
  Both paths feed the same receipts to the director.
- Options → Combat presentation → Controls → **Automatic enemy turns**
  (`combat.autoNpc`, default on). With it off, the NPC button reads
  "Play enemy turns" and sends `design_drain_npc`.
- Banners (combat director, `banner` beat style): "Opposition phase" before
  enemy steps, "<Hero>'s turn" when control returns, plus reaction banners
  ("⚡ Opportunity attack", "🛡 Shield reaction", "🛡 Parry reaction",
  "☄ Legendary action", …) queued before the strike they announce.
- **Decision: who is player-controlled.** The public view reports
  `controller` as `player`, `npc` or `unknown`. Only an explicit `npc` hands
  a party member to the policy; `unknown` falls back to the `p` prefix.

## 6. Client: three combat styles (`combat.style`)

| style | keys | mouse |
|---|---|---|
| `hybrid` (default) | WASD/arrows, Space, 1–4, Tab/Q, E, Esc | click ground, click/double-click foe, right-click wheel |
| `turn_based` | legacy: A attacks, E ends turn, Tab/[ ] cycle | legacy focus/double-click |
| `direct_wasd` | WASD/arrows, Space, 1–4, Tab/Q, E, Esc | legacy focus/double-click |
| `mouse_click` | legacy A/E | click ground, click/double-click foe, right-click wheel |

The command dock is always on in every style.

- **W/A/S/D** (and arrows): one 5-ft step on the host grid (+y north).
  **Space**: attack the focused foe, else the nearest in reach (5 ft;
  Doran 70 with thrown daggers; Wren 60 with Crown of Stars) while an attack
  remains; otherwise end the turn. **1–4**: hotbar from the host's
  contextual rows (`hotbarSlots`). Doran: attack / dagger / Quick Toss /
  Trip Attack; Wren: attack / dodge / cast / dash; others: attack / shove /
  cast / dodge. **Tab/Q** cycle targets.
- **Left-click the ground** walks toward that spot. It's capped to the
  movement left and stops short of an occupied square. On the flight stage
  both axes map back to the grid. On the formation (side-view) stage x
  isn't a grid projection, so a click on the foes' half closes on the
  nearest foe and one on the party's half falls back.
- **Right-click a foe** opens the action wheel: Attack, Cast, Maneuver
  (Doran), Shove, Trip, Grapple, Inspect. Items the host marks unavailable,
  or out of reach of that foe, are disabled with the host's reason.
  **Right-click the ground** clears focus and menus.
- **Opportunity-attack warning** (`combat.threatWarn`, default on): a step
  that would leave a foe's reach rings that foe in red and asks for the
  same step again within 2.6 s to commit. This is a warning only; the host
  still decides (Disengage, mobile stance).
- Hotkeys ignore input while typing (`isTypingTarget`: input, textarea,
  select, contenteditable) and while a dialog, the system menu or the
  bookbag is open. Handled keys stop propagating, so the older global
  Space/1–9 handler doesn't fire twice.
- **Changed:** in `hybrid` and `direct_wasd`, **A** steps west instead of
  attacking. Space, 1 or the wheel attack instead; `turn_based` keeps A.

## 7. Known gaps and notes for the next pass

- **Occupancy:** `tactical.move` doesn't refuse ending on an occupied
  square. The client avoids it, but the engine should own it. Watch
  Tarrasque swallow and regurgitation positions, which place creatures on
  the same square on purpose.
- **Space reach** for custom characters is a flat 5 ft. Ranged builds
  should read their weapon's range from the host (a `reach` field on the
  contextual `attack` row would do).
- **Formation-stage click-to-move** is approximate (see §6). A true
  top-down grid overlay would make the mouse style exact.
- **Enemy maneuvers/contests:** candidates exist for every actor, but enemy
  `combat_action` doesn't choose shove/grapple yet. `plan_action(goal="control")`
  is the hook.
- **Banner timing:** the "<Hero>'s turn" banner queues behind the enemy
  beats. With motion reduced, beats are near-instant, so banners flash
  quickly.
- **Arcade mode** is untouched: `arcade-input.js` keeps its own WASD, and
  the router is inactive while an arcade encounter runs
  (`tacticalActive()` is false).

## 8. Verification

- `tests/test_reactive_combat.py` (24 tests): reaction policy per window
  kind, settle and opt-in move, legendary and Tarrasque routine,
  multiattack, drain stop conditions over the host, step receipts on
  `design_action` and `design_turn`, candidate catalog shape, uniqueness,
  read-only forecasts, legality equal to the resolver, the `control` and
  `defend` goals.
- `tests/test_combat_input_js.py`: the pure input mapping under Node
  (skipped when Node is absent).
- `tests/reactive-combat-browser-check.cjs`: real host + real browser.
  Typing doesn't move a hero; D steps; Q focuses; Space attacks;
  right-click opens the wheel; the enemy turn plays itself; ground click
  walks; the client drains a `manual_opposition` turn itself. Run it with
  `node tests/reactive-combat-browser-check.cjs`. Set `HSR_PYTHON` or
  `HSR_CHROMIUM_PATH` / `HSR_BROWSER_CHANNEL` if needed.
