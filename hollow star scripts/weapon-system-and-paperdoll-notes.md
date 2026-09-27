# Weapon system + paperdoll fit — session notes (2026-09-21)

Working notes for the ongoing "outfits/items for the paperdoll, starting with
a weapon system that has real range" pass. Not a design doc — a handoff for
whoever (Corey, Claude, or Codex) picks this up next.

## What shipped

**`hollowstar/content/items.json`** — every hand-slot weapon now carries a
complete mechanical block: `damage_dice`, `attack_ability`, `reach`,
`range_normal`/`range_long`, and a physical subtype tag (PIERCING/SLASHING/
BLUDGEONING) alongside `PHYSICAL`. Before this, 8 of the file's 9 weapons
(everything except Doran's signature watchblade) had no `damage_dice` at all
— a custom-identity character wielding any of them would have hit
`tactical.weapon_attack()`'s `"weapon dice are not implemented"` guard.
Added two new weapons (`hunting bow`, `war pick`) so the file has a working
long-range example and a second finesse-adjacent piercing weapon.

**`hollowstar/loader.py`** — `load_items()` and `load_roster()` were silently
dropping `silhouette`/`material`/`item_type`/`handedness`/`coverage`/
`animation_profile` when building `Item` objects from JSON. This is the
actual "items don't fit properly" bug: an author's explicit visual override
(the field `items.py`'s docstring says exists specifically because "some
items cannot be told apart by their maths") was never reaching the paperdoll.
A warhammer's only mechanical tell is `BLUDGEONING`, which `_silhouette()`'s
heuristic reads as a spellcaster's implement (right for a cleric's mace,
wrong for a STR warhammer) — so it rendered as a wizard's staff. Fixed the
loader to pass all six fields through; the `character_creation.json` /
`profiles.py` path (used by player-built characters at chargen) already did
this correctly, so this bug was specific to the world-loot table and to
actor-embedded equipment in `content/actors.json`.

Verified in-browser (Simulation Mode, `javascript_tool` dynamic-importing
`paperdoll.js` directly): the `axe` and `bow` silhouettes render distinctly
and correctly for the first time — they existed in `styles.css` and in
`items.py`'s `_WEAPON_SILHOUETTES` tuple, but no item had ever actually
produced them through the live loader before this fix.

**Tests** — `tests/test_item_presentation.py` gained three tests that load
the real `content/items.json` (not a synthetic fixture) and assert: every
weapon with `base_damage` has a working `Actor.weapon_profile()` (reach,
range, dice all present); the loader-fix regression case specifically
(warhammer/battleaxe → axe, greatsword/glaive → two-handed, rapier → sword);
glaive's polearm reach and the two ranged weapons' range bands. Full suite:
193 tests, all green (one `test_clone_beats_full_deepcopy_by_a_measurable_margin`
timing flake reproduced once, passed clean on retry and on a full re-run —
unrelated to this change, it's a wall-clock margin test).

## Two combat resolvers — read this before adding weapon content

- `hollowstar/tactical.py` (`weapon_attack`, via `Actor.weapon_profile()`) is
  the live dungeon run. It needs `damage_dice` + `attack_ability` +
  `reach`/`range_normal`/`range_long` on every weapon, or a `"custom"`
  identity wielder can't attack with it at all.
- `hollowstar/resolution.py` (`resolve_attack`, via `combat.py`'s `Encounter`)
  is the older SIMULATION/rehearsal engine — it reads `base_damage` directly
  and ignores `damage_dice` entirely.

Every weapon needs both `base_damage` and `damage_dice` populated, or it
silently works in one engine and breaks in the other.

## Found, not yet fixed — flagging rather than guessing

- **`content/items.json` isn't wired to a live equip-swap action yet.**
  `dungeon.py`'s `'equip'` action kind only handles Imprints (the rune/overlay
  system, `d['imprints']`) — there's no path today where a player picks up
  one of these named weapons mid-run and it replaces their hand-slot weapon.
  `host.py:863` is the only other reader of `load_items()`, and that's a
  listing, not an equip flow. So the weapons fixed above are correct and
  tested at the data/engine level, but not yet reachable by a player. That's
  the natural next slice if loot-weapon-swapping is wanted for real.
- **Loot-weapon damage doesn't get the wielder's ability modifier baked in.**
  Starting-kit weapons (`character_creation.json` → `character_builder.py`'s
  `_equipment()`) bake `damage_modifier = ability_mod` at chargen time. There
  is no equivalent step for a hypothetical loot-weapon equip, so once that
  path exists it needs the same treatment or loot weapons will under-deal
  compared to a starting weapon of the same dice.
- **No CSS silhouette reads as a polearm.** Glaive (reach 10, two-handed)
  falls back to the generic `sword` shape — visually indistinguishable from
  a longsword despite the mechanical reach difference. Not wrong, just not
  distinct. A `polearm` shape would need a new `.char-weapon.polearm` rule in
  `styles.css` plus a branch in `items.py`'s `_silhouette()` or another
  explicit `"silhouette"` override.
- **The six-shape vocabulary (`sword/staff/bow/shield/dagger/axe`) has real
  ambiguity at the edges** — a rapier and a war pick both landed on
  explicit overrides in this pass because the heuristic's default guess was
  wrong for them. Any new weapon whose mechanics don't cleanly signal its
  shape should get an explicit `silhouette` override rather than trusting
  the derivation; that's what the field is for.

## Paperdoll "skeleton" — scoped, not started

Corey's ask: a proper skeleton so items attach correctly regardless of pose,
and so building new outfits doesn't mean re-tuning pixel offsets by hand.
Current state, read directly from `web/styles.css`: the doll is ~30 named
CSS layers (`char-head`, `char-arm-front`, `char-weapon`, etc.), each with
its own hand-authored `left`/`top`/`transform` inside one implicit ~185x310px
canvas, plus per-pose (`pose-combat`/`pose-travel`) and per-silhouette
(`.char-weapon.dagger`/`.axe`/`.bow`/`.staff`/`.shield`) overrides layered on
top. It already works and already differentiates weapon shapes (see above) —
it is not broken as a whole, just fragile: every new item or pose is another
hand-tuned override, and there's no single source of truth for "where does a
hand-held item's grip point sit."

Did not start a rewrite this session — a full skeleton pass touches ~30
CSS rules across poses, rarities, and outfits, and needs visual verification
per combination, which is a focused session of its own rather than a
tack-on. The concrete next step, if this is picked up: extract the existing
per-layer coordinates above into one explicit anchor registry (a small JS/JSON
module keyed by layer name -> {x, y, rotation} per pose), have `styles.css`
read it via CSS custom properties instead of duplicating numbers in ~30
selectors, and verify each existing pose/outfit/rarity combination still
renders before calling it done. That registry is also the natural anchor
system a future canvas or skeletal-animation renderer would consume instead
of the DOM/CSS one — same data, two renderers, which is the "shared base
framework" this session's mid-flight steer asked for.

Open question for Corey, not blocking: the "eventually five layers" comment
— unclear what the five layers refers to (the SPRITE_LAYER_CATALOG's `slot`
groups today are `ground/effect/clothing/body/equipment/weapon`, which is
six, not five) and it changes how the anchor registry above should be shaped.
Worth a one-line clarification whenever convenient.

## Future champion progression — Corey direction (2026-09-26)

Doran and Wren will use a dedicated level range of **0–100**. Created characters
will retain the normal **1–20** range. This is a future implementation direction,
not an active rules change; do not remap current statistics or progression yet.

Current priority: refine Doran and Wren combat playability one issue at a time
before expanding custom-character work. Doran should read as exceptionally fast
with his obsidian daggers and still fairly fast with his two-handed cleaver;
weapon weight alone must not dictate his character-specific presentation speed.
