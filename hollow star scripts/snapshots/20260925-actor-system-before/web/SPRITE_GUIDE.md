# Sprite System Guide

Simple geometric sprite support for HSR characters and items.

## Structure

```
web/assets/sprites/
├── characters/
│   ├── sera-happy.svg
│   ├── sera-serious.svg
│   └── [other-character].svg
└── items/
    ├── longsword.svg
    ├── shield-iron.svg
    ├── ring-of-protection.svg
    └── [other-item].svg
```

## Adding Sprites to Actors

Set the `sprite_id` field when creating or loading an actor:

```python
from hollowstar.actors import Actor

sera = Actor(
    name="Sera",
    sprite_id="sera-happy",  # Links to sera-happy.svg
    max_hp=100,
    hp=100,
    # ... other fields
)
```

For dynamic mood changes:
```python
if sera.hp < sera.max_hp // 2:
    sera.sprite_id = "sera-serious"
else:
    sera.sprite_id = "sera-happy"
```

## Adding Sprites to Items

Set the `sprite_id` field on Item instances:

```python
from hollowstar.items import Item

sword = Item(
    name="Longsword",
    sprite_id="longsword",
    slot="hand",
    base_damage=8,
    # ... other fields
)
```

## Using Sprites in the Web UI

Import the sprite renderer module:

```javascript
import {
  createCharacterSprite,
  createItemSprite,
  renderCharacterRoster,
  renderInventory
} from './sprite-renderer.js';

// Create a single character sprite
const actor = { name: "Sera", sprite_id: "sera-happy", hp: 80, max_hp: 100, armor_class: 15 };
const sprite = createCharacterSprite(actor, { size: 'medium', showName: true });
container.appendChild(sprite);

// Create an item sprite
const item = { name: "Longsword", sprite_id: "longsword", slot: "hand" };
const itemSprite = createItemSprite(item, { size: 'small', showName: true });
container.appendChild(itemSprite);

// Render a full roster
const actors = [actor1, actor2, actor3];
renderCharacterRoster(actors, rosterContainer);

// Render inventory
const equipment = [sword, shield, ring];
renderInventory(equipment, inventoryContainer);
```

## Creating New Sprites

Style guidelines:
- **Keep it minimal**: Simple geometric shapes (circles, polygons, rectangles)
- **Flat colors**: Solid fills, no gradients
- **Limited palette**: 3–5 colors per sprite
- **Consistent viewBox**: Use appropriate size (e.g., 80x120 for characters, 24x96 for swords)
- **Centered**: Design from the viewBox center for consistency

Example character template (80×120):
```svg
<svg viewBox="0 0 80 120" xmlns="http://www.w3.org/2000/svg">
  <!-- Head -->
  <circle cx="40" cy="20" r="14" fill="#e8d7c3"/>
  <!-- Body -->
  <polygon points="26,34 54,34 54,65 40,72 26,65" fill="#2d5a6b"/>
  <!-- Legs -->
  <rect x="34" y="72" width="6" height="30" fill="#0f1418"/>
  <rect x="40" y="72" width="6" height="30" fill="#0f1418"/>
</svg>
```

## Color Palette

From the game design:
- **Pale/Skin**: `#e8d7c3`, `#d4c5b3`
- **Dark/Hair**: `#0f1418`, `#0a0d1a`
- **Teal/Navy**: `#2d5a6b`, `#1a2f42`
- **Gold/Accent**: `#d4a574`, `#c9a961`, `#8b7a5c`
- **Blue/Eyes**: `#4a8fb0`, `#3a6f8a`
- **Metal**: `#c0c0c0` (silver), `#6b7280` (iron)
- **Brown/Leather**: `#5c4033`, `#8b7355`

## Fallback Behavior

If a sprite fails to load or `sprite_id` is empty:
- Characters show their name initial
- Items show their item initial
- Styling applies a fallback appearance

No sprite? No problem—the system degrades gracefully.

## Clean Cel — the one rig style (2026-09-23)

Every rigged figure (custom puppets in `puppet-renderer.js`, Doran in
`doran-rig.js`) follows one rule set, tuned for reading at combat scale:

- **One ink weight** (`LW`) around every shape; limb chains are outlined as one
  piece, then filled, so joints never seam.
- **Flat two-tone fills**: base colour plus one shadow cel on the back side
  (`celShade` / `celLight`). No smooth gradients — Doran's shading ramps are
  posterized into hard bands (`celStops`). Glows and the portrait backdrop are
  the only soft fills.
- **Far side one step darker** than the near side, so overlapping limbs read.
- **Details are shapes, not lines.** If a feature is unreadable at ~80 px tall
  it is not drawn. Every creator option still changes the silhouette or a fill.
- **Poses read as silhouettes**: each combat state has its own stance width,
  lean and weapon arc. `attack` is one arc — coil (0-.35), snap (.35-.5),
  settle — and `windup` / `strike` hold its two keyframes.

## Layered custom-character art

The scene renderer uses a catalog-driven stack for unnamed/custom characters.
The base stack draws the body and clothing, then public equipment descriptions
select presentation overlays from `assets/sprites/layers/`:

| public equipment cue | overlay |
|---|---|
| helm, helmet, hood, cowl | `headgear-v1.png` |
| cloak, mantle, cape | `cloak-v1.png` |
| shield, buckler | `shield-v1.png` |
| ring, amulet, signet, charm | `trinket-v1.png` |

Armor cues also change the clothing treatment: plate, chain/mail, leather/hide,
and robe/vestment. These are visual projections only; they do not affect
mechanics, RNG, saves, or canon. Champion identities bypass this stack: Doran
draws through his layered rig (see *Layered Champion Rig* below).

The detailed generated PNGs are deliberately routed only to item-picture
surfaces such as the creator's starting-kit cards. They are not used as actor
layers. Actor layers remain the small abstract SVG treatment so the two visual
engines stay distinct and readable in scenes.

## Unified Canvas FX Engine (`web/fx-engine.js`)

A high-performance 60 FPS procedural visual effect system that runs directly
on the HTML5 2D Canvas in arcade mode and via a transparent overlay canvas over
the turn-based `.combat-stage`.

### Capabilities:
- **12 Damage Palettes**: `fire`, `cold`, `lightning`, `radiant`, `necrotic`, `force`, `acid`, `poison`, `psychic`, `thunder`, `heal`, and `physical`.
- **Projectiles & Tracers**: Velocity-aligned glowing cores, fading ribbons, and particle trails (arrows, magical bolts, elemental motes).
- **Impact Shockwaves**: Expanding concentric shockwave rings with outward particle bursts.
- **Multi-Socket Auras**:
  - `ground`: Foreshortened, rotating geometric runic circles beneath actor feet.
  - `body`: Shimmering hexagonal energy shields with edge luminescence around the torso.
  - `head`: Overhead radiant halos, crowns, or status wisps.

### Usage:
```javascript
import {FXEngine, createFXOverlay, getPalette} from './fx-engine.js';
// Or imported via sprite-renderer.js / paperdoll.js

// 1. Spawning a flying projectile:
fx.spawnProjectile({
  fromX: 100, fromY: 200,
  toX: 450, toY: 180,
  damageType: 'fire',
  archetype: 'bolt', // 'arrow' or 'bolt'
  onHit: (x, y, type) => fx.spawnImpact(x, y, type, {radius: 36, count: 20}),
});

// 2. Setting persistent auras:
fx.setAura('actor-1', {socket: 'ground', auraType: 'radiant', radius: 32});
fx.setAura('actor-2', {socket: 'body', auraType: 'force', radius: 36});
```

## 2D Skeletal Rig & Socket System (`web/skeletal-rig.js`)

An articulated 2D hierarchical bone system providing procedural kinematics and
standardized attachment sockets for equipment and visual FX.

### Bone Tree:
- `root` $\to$ `pelvis` $\to$ `spine` $\to$ `torso` $\to$ `neck` $\to$ `head`
- `torso` $\to$ `left_shoulder` $\to$ `left_upper_arm` $\to$ `left_lower_arm` $\to$ `left_hand`
- `torso` $\to$ `right_shoulder` $\to$ `right_upper_arm` $\to$ `right_lower_arm` $\to$ `right_hand`
- `pelvis` $\to$ `left_hip` $\to$ `left_thigh` $\to$ `left_shin` $\to$ `left_foot`
- `pelvis` $\to$ `right_hip` $\to$ `right_thigh` $\to$ `right_shin` $\to$ `right_foot`

### Standard Sockets:
- `main_hand`: Weapon mount and projectile/spell casting emitter.
- `off_hand`: Shield mount and secondary focus.
- `chest`: Target impact receiver and body shield barrier anchor.
- `head`: Overhead aura anchor (halos, crowns).
- `ground`: Shadow plane and ground rune circle anchor.

### Procedural Kinematics:
- `'idle'`: Breathing cycle, subtle shoulder dip, and ready weapon posture.
- `'run'`: Continuous stride cycle with pelvis bob, leg extension, and counter-swinging arms.
- `'jump'`: Takeoff crouch, airborne ballistic knee tuck, and landing cushion.
- `'climb'`: Alternating hand reach and vertical leg stepping up wall/ladder surfaces.
- `'vault'`: Two-hand ledge plant, body tuck, and leg sweep over obstacle crests.

### Dual-Mode Rendering:
- **Articulated Puppet (`drawSegmented`)**: Draws segmented body pieces (skin, tunic, armor plates, boots, weapon/shield) flexed along bone transforms.
- **Monolithic Pose Anchor (`drawMonolithic`)**: Anchors a champion's authored pose frames to the bone root while tracking socket coordinates in world space. No champion uses frame art today (`CHAMPION_POSE_ART` in `sprite-renderer.js` is empty); the path remains for a future frame-art champion.
- **Per-character proportions (`reshape`)** and **two-bone IK (`reach` for arms, `plant` for legs)**: a layered champion measures its own skeleton and pins hands to grips and sabatons to the floor.

## Layered Champion Rig — Doran (`web/doran-rig.js`)

Doran is a paperdoll of vector parts drawn in Corey's 2026-09-23 style guide
(clean cel plate, navy cloth, brown leather, charcoal gauntlets), each part
painted in its bone's local frame on the shared `SkeletalRig`. He replaced the
old five-frame pose strip on 2026-09-23.

- **Design locks** (Doran paperdoll spec + DM041_A): 7'0" in the enclosed helm
  (1.25x the 5'8" puppet baseline, `RIG_UNITS_PER_FOOT`); lit gold visor slit;
  kite shield fused to the shield-arm vambrace (near/right chain); the Giant
  Cleaver in the weapon hand (far/left chain) as a 6 ft x 3 ft white razor slab
  — flat spine, mirror face, hollow-ground bevel, keen edge, angled chisel tip —
  on a 3 ft handle (`CLEAVER`).
- **Layers**: `DORAN_PAPERDOLL_LAYERS` (re-exported by `paperdoll.js`) lists
  every part with its slot, bone and paint order. Weapons move between z bands
  with the pose: a forward blade paints over the body, a raised one behind it.
- **Poses**: `DORAN_POSES` are blendable channel sets — combat (`guard`,
  `windup`, `strike`, `follow`, `sweep*`, `hit`, `brace`, `low`, `bash`,
  `command`), traversal (`run`, `jump`, `land`, `climb`, `down`) and downtime
  fidgets from the guide (`look`, `point`, `cheer`, `crossed`, `scratch`,
  `tired`, `kneel`). IK pins the weapon hand to its grip, the second hand to
  the handle in choked strikes, and both sabatons to the floor in stances.
- **Motion language**: anticipation on `windup`; the `strike` beat snaps in
  ~95 ms, holds a hitstop, then follows through past centre with a silver
  crescent wake, an impact ripple and ground rupture where the tip lands.
  Figures marked `data-beat-tempo="heavy"` get a longer wind-up from the
  combat director.
- **Loadouts**: `cleaver` (default) or `daggers` (host `loadout`/`weapon_mode`
  naming a dagger) — obsidian daggers in both hands, Cleaver latched on his
  back. At ease he plants the Cleaver upright beside him, hands free.
- **Canvas**: `.doll-rig .puppet-canvas` overhangs the figure box so the blade
  is never clipped; `puppet-dom.js` maps drawing and sockets back to the box.
  The voice-card medallion is a bust drawn by the same rig (`doranPortrait`).
- **Tests**: `tests/test_doran_paperdoll.py` (wiring + rig behaviour in Node)
  and the Doran block in `tests/puppet-browser-check.cjs`.

## Kinematic Traversal Subsystem (`web/traversal-controller.js`)

Manages obstacle parkour for characters traversing the screen Left $\to$ Right.

### Parkour State Machine:
1. **Approach**: Senses upcoming obstacles requiring climb or jump.
2. **Climb**: Elevates the entity vertically along the obstacle face using procedural climb kinematics.
3. **Vault**: Plants hands on the obstacle top lip, raises torso above crest, and sweeps legs forward over the geometry.
4. **Land / Drop**: Transitions smoothly back to grounded running on the other side.
5. **Jump**: Provides smooth parabolic ballistic arcs over gaps and low obstacles.

### Authority Model:
- **Server (`arcade.py`, `tactical.py`)**: Authoritative on movement legality, obstacle collision gating, and tick coordinates.
- **Client (`TraversalController`, `SkeletalRig`)**: Authoritative on 60 FPS kinematic interpolation, ledge-grabbing, climb stepping, and vault clearance between server ticks.

## Cross-Module Integration

All subsystems are re-exported through the central presentation modules:
- `web/sprite-renderer.js`: Re-exports `SkeletalRig`, `Bone`, `TraversalController`, `FXEngine`, `createFXOverlay`, `getPalette`, `DAMAGE_PALETTES`, and owns `CHAMPION_RIGS` / `championRig()` (Doran's rig).
- `web/paperdoll.js`: Re-exports all of the above plus `DOLL_SOCKET_OFFSETS`, and equips every `dollModel` with a `sockets` map.
- `web/combat-director.js`: Mounts the FX overlay atop `.combat-stage` and resolves spell/ranged beats into projectile flights, impacts, and auras.
- `web/arcade-canvas.js`: Renders live projectile ribbons, entity auras, articulated rigs (including rigged champions), and traversal over obstacles.
- `web/puppet-dom.js`: One scheduler for every DOM figure; rigged champions draw through their rig with the live combat beat.
