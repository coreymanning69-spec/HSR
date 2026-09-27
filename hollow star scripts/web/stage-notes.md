# The main display stage

The room screen is one persistent stage (`stage-view.js`). It draws a painted
place, lets figures walk it, turn, open doors and swing, and lights the paper
dolls with the same lamps as the set. **Presentation only**: the host decides
every outcome of a real run. The stage walks, turns, opens, swings and draws,
and carries a click to the same host calls the menus use.

```
stage-world.js   pure logic (no DOM): bodies, movement, reach, damage, swing clocks
stage-set.js     21 painted places, lighting lists, exit → door layout, bake + live layer
stage-art.js     drawing kit: sky, houses, stone, floors, 40 props, 7 door kinds
stage-fx.js      motes, sparks/blood/chips by material, debris, floats, wounds
stage-view.js    the DOM/canvas stage: layers, figures, picking, input, per-frame loop
battle-backdrop.js  the same set + lamps under the combat stage; wounds on struck figures
actor-toolbox.js    the Actor Toolbox (Simulation Mode) — the same stage with nothing behind it
```

## Layers (back to front)

`ws-bake` painted set (baked once per room/size/hour) → `ws-live` doors, fire,
water, wheels, contact shadows → `ws-things` figures and props, z-sorted by
their feet → `ws-fx` FX, wounds, health bars → `ws-light` lightmap
(`mix-blend-mode:multiply`) → `ws-glow` bloom (`screen`). Real `<button>`s for
doors and objects sit over it for keyboard and screen readers.

## The floor is a plane

`d = 0` is the near edge (`cam.front`), `d = 1` the back wall (`cam.back`).
Everything on it scales by `lerp(1, cam.farScale, d)`. World units are feet;
`px per foot = 0.0575 × scene height`. The party rail and info dock float over
the display's edges, so doors, props and figures are laid out in the clear
middle (`insets`) and the painting bleeds under the cards.

## Bodies

`bodyOf(item, weapon)` gives height, shoulder width, footprint, reach, speeds:

| body | scale | note |
|---|---|---|
| Doran | 1.25× physical | his rig already draws him 7'0", so the drawn box stays 1×; Cleaver 9 ft, reach 9.7 ft |
| tiny / small / medium / large / huge / gargantuan | .5 / .82 / 1 / 1.55 / 2.3 / 3.1 | from the host's `size`, else a name guess (ogre, giant, castellan…) |

Heavier bodies are thrown less by a blow and give way less when bodies overlap.
Weapon length scales with the body (a goblin's spear is small, a giant's large).

## Movement

Turn first (a short pivot: the figure squashes through its edge and switches
`data-facing` at the midpoint), then accelerate; brake into the goal; route
around blockers; keep out of each other's footprints. Stride rate is
`gait` = cycles/second from real speed, so feet keep pace with the ground.
Residents keep to a leash, pause, glance, chat in pairs, and turn to face the
party when it comes near; guards hold their post.

## What the rigs read (`puppet-dom.js` → `draw`)

`data-facing` (±1) · `data-gait` · `data-carry` (`stowed|shoulder|ready`) ·
`data-swing` + `data-swingAt` (Doran's Cleaver) · `data-beat` (`move`,
`windup`, `strike`, `hit`…) · `data-shadow="off"` (the stage draws contact shadows).

## Doran's Cleaver

- **stowed** on his back in friendly places (towns, taverns); **shoulder** over
  the shoulder, biangular, in hostile ones and dungeons; **ready** held out in
  front with one hand, at ease, in a fight (and after any swing, for ~3 s).
- Drawing or sheathing reaches back over the shoulder first.
- Four swings (`chop`, `cleave`, `sweep`, `rise`) are keyframed arcs with a
  95 ms hitstop at contact, a smear on the edge, sparks and ground dust.
  `DORAN_SWINGS` (rig) and `SWING_STYLES` (world) share `ms`/`contact`; the
  world's clock includes the hitstop. `tests/test_stage_world.py` pins them.
- Damage in the room and the Toolbox is local and **not canon**
  (`WEAPON_DAMAGE`); training dummies and Toolbox actors take it, residents and
  host objects never do. Real combat keeps the director; blows there leave
  wounds (Options → Combat → Wounds).

## Adding things

- **A place**: `def('id', {cam, floor, decor, live, lights, particles, paint})`
  in `stage-set.js`; map rooms to it in `themeFor` (town ids, descent words).
- **A prop**: add to `PROP_ART` (`stage-art.js`) and `PROP_TYPES`
  (`stage-world.js`: size, hp, material, blocking).
- **A door kind**: `drawDoor` + `DEST_DOOR` (which exit gets which door).
- Hours come from the host clock (`room.world_time`, seconds): morning,
  day, evening, night.

## Checking it

```bash
python -m pytest tests/test_stage_world.py tests/test_doran_carry_and_swing.py -q
node tests/stage-browser-check.cjs        # 21 sets bake, doors open, swing lands, sizes, cost
```

Open `actor-toolbox.html` (or Simulation Mode → Actor Toolbox) to play with it.
Pose sheet and frame times stay in `actor-lab.html`.
