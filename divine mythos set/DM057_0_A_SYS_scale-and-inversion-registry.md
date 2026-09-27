---
id: DM057_0
title: "Scale and Inversion Registry"
type: sys
subtype: scale-and-inversion-registry
load_priority: on-demand-by-instantiation-or-encounter-rule
canon: T+TR
verse: ALL
timeline: T537.0+
arc: cross-system-mechanics
era: global-tour
status: hard-canon
authority: canonical scale precedence and inversion registry
updated: 2026-09-08
volatility: slow
arc_scope: evergreen
derived_from: null
predecessor_file: N/A
successor_file: N/A
purpose: "Owns portable scale, inversion, and curve rows without duplicating arc-specific doctrine."
---

# DM057_0 — SCALE AND INVERSION REGISTRY

## ROW SCHEMA

Every scale is one row. A row that cannot fill these fields is a ruling and
belongs with its subject owner.

- `scale` — marker written onto the instantiated creature in the Field ledger.
- `type` — `delta`, `inversion`, or `curve`.
- `scope` — creature families, module, or location matched by the row.
- `exclusions` — explicit non-matches; use `none` deliberately when empty.
- `effective_from` — beat or condition; rows are not retroactive.
- `application` — `exact-once` unless stated otherwise.
- `application_order` — position in statblock assembly.
- `payload` — deltas, pricing rule, or curve.
- `unchanged` — values the row cannot touch.
- `replaces` — superseded row; rows with the same axis never stack.

## PRECEDENCE

1. A named family row that matches.
2. A location-keyed curve row, if the creature is instantiated there.
3. The generic encounter fallback.

A creature never takes two rows of the same type. A `delta` and an `inversion`
may both apply because they operate on different axes; a `delta` and a `curve`
may not. If a family row wins over a matching curve, record the skipped curve
in the Field line rather than failing silently.

## ROWS

### `SKT-GIANT-v2` — `delta` — MIGRATED, CANON

Migrated from `DM038_1 #RULE-SKT-GIANT-SCALE`; values are unchanged.

```json
{
  "scale": "SKT-GIANT-v2",
  "type": "delta",
  "effective_from": "T537.0+",
  "module": "storm-kings-thunder",
  "ancestries": ["hill", "stone", "frost", "fire", "cloud", "storm"],
  "named_variants": "included",
  "allegiance": "irrelevant",
  "exclusions": ["ogre", "troll", "ettin", "oni", "fomorian", "construct", "animal", "shapechanged_non-giant"],
  "application": "exact-once",
  "application_order": "after-printed-or-template-modifiers",
  "deltas": {"ac": 1, "weapon_or_spell_attack_rolls": 1, "damage": 3, "save_dcs": 1, "hp_max": 200, "hp_current": 200},
  "preserve_existing_damage": true,
  "replaces": "GENERIC-ENCOUNTER-HP",
  "unchanged": ["proficiency_bonus", "hit_dice", "challenge_rating", "xp", "saves", "speed", "ability_scores", "actions", "reactions", "resistances"],
  "other_stat_changes": "none"
}
```

The marker makes the overlay idempotent. Matching giants receive the fixed
tuple after printed or template modifiers; the generic encounter-HP row does
not stack. Shapechanged non-giants do not match.

### `CHAMPION-DENIAL` — `inversion` — MIGRATED POINTER, CANON

Authority remains `DM051_0`. Champion survivability is priced through visible
action denial, positioning, and encounter structure, not hit-point inflation.
Legendary Resistance answers only its owner's failed saving throw; it is not a
general counter to attack-roll damage, an attended object's separate save, or a
fixed-cost refusal layer. Exclusion: divine tier. It may stack with a matching
delta only if a champion is also a matching giant.

### `GENERIC-ENCOUNTER-HP` — `delta` — MIGRATED POINTER, CANON

Authority remains `DM034_2a`. Add 30–60% HP only where no named family row
matches. `SKT-GIANT-v2` supersedes it for matching giants; the two never stack.
Hit points are the floor of encounter design, not its whole solution.

### `HSR-DEPTH` — `curve` — PROPOSED, NOT CANON

This row is intentionally inert. It is not applied to an encounter, does not
create a tier, and does not alter Hollow Star runtime or routing.

Open fields:

- input: room depth, floor band, or promotion tier;
- curve: linear or stepped;
- axes: available SKT-style tuple versus a lower-HP action-economy curve;
- ceiling: required before any future activation.

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM057_0 -->
