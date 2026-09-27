# Doran combat sprite assets — retired

**Retired 2026-09-23.** Doran now draws as a layered paperdoll on the shared
skeleton (`web/doran-rig.js`; see SPRITE_GUIDE.md, *Layered Champion Rig*).
Nothing in the client loads these frames any more; they stay on disk until
Corey decides whether to archive or delete them. The web server still lists
them so existing links keep working.

Asset-only handoff for the combat renderer. These files carry no mechanics,
state, RNG, or authority.

## Runtime-ready frames

All five pose PNGs use the same 435 x 724 transparent canvas. Keep their full
canvas dimensions when rendering so Doran's feet and centerline stay stable.
The suggested anchor is bottom-center (`50% 100%`).

| order | file | suggested pose key |
|---:|---|---|
| 0 | `doran-guard.png` | `guard` |
| 1 | `doran-overhead-strike.png` | `overhead-strike` |
| 2 | `doran-sweep.png` | `sweep` |
| 3 | `doran-rest.png` | `rest` |
| 4 | `doran-low-ready.png` | `low-ready` |

`doran-combat-strip.png` is the transparent master strip in the same left-to-right
order. Its dimensions are 2172 x 724; the individually normalized frames are the
safer runtime input because the supplied strip was not evenly divisible by five.

`doran-main-reference.png` is the untouched supplied full-body reference. It has
a baked checkerboard backdrop and is intentionally not marked runtime-ready.

Source art was supplied by Corey on 2026-09-14. Background extraction used the
built-in image editor. The frame files are presentation-only.
