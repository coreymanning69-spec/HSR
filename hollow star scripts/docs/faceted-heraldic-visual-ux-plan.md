# Hollow Star Reliquary: Faceted Heraldic Visual and Smooth UX Plan

> Full source plan. The condensed, actionable version of this lives in the
> session's `/goal` (4000-char limit there forced the split). This doc is
> the reference for the detailed test/acceptance matrix and assumptions.

## Summary

The revised goal is not only to make the game resemble the reference image. It is to make the entire path from title screen to active play feel like one coherent, responsive experience.

The existing rig, host, Canvas2D, socket, and receipt systems are sufficient. The main problems are:

- creator characters and gameplay characters use different presentation paths;
- menus expose too much diagnostic complexity too early;
- world art is noisier and more procedural than the reference;
- transitions, focus, feedback, and responsive behavior need to be treated as one UX system;
- legacy rendering paths create unnecessary maintenance and visual drift.

The title screen should remain recognizable and largely stable, but the full flow around it must be tightened.

## 1. Establish the Canonical Experience

Define the browser-local journey as:

`Title → Mode → Lead/Run Choice → Creator or Champion → Confirmation → Active Play`

Each screen must provide:

- one obvious primary action;
- an always-available, predictable Back path;
- visible loading, disabled, success, and error states;
- preserved keyboard focus;
- no unexplained blank transition;
- no accidental loss of entered creator state;
- consistent Title/Main Menu behavior.

Story Mode remains the player-facing route. Simulation Mode keeps its tools, but groups Actor Toolbox, Actor Lab, rehearsal, cheats, and statistics as diagnostic surfaces rather than presenting them as equal-weight gameplay choices.

Options should retain its power while using progressive disclosure. Interface, visibility, style, combat, voices, connection, and command settings remain available, but the first view should emphasize the few settings most relevant to immediate play.

The command bar remains visible above secondary navigation and may collapse, but it must never become the dominant obstacle to the main scene.

## 2. Unify Character Presentation

Make this the single character route:

`host public actor data → dollModel → actorRig → SkeletalRig/named rig → Canvas2D`

The creator preview must use the same live `HERO_RIG` presentation used by gameplay. It must support the same:

- body proportions;
- facing;
- idle, move, and attack states;
- equipment sockets;
- weapon silhouettes;
- armor and material treatment;
- reduced-motion behavior;
- accessibility labels.

Race PNGs, sprite-layer montages, and unused pose-art paths become explicit legacy fallbacks or reference-only assets. They are not silently removed during the first pass.

Wren becomes the primary Faceted Heraldic calibration reference. Generic actors are brought toward that visual language, while Doran and Wren retain their individual identities.

## 3. Create One Shared Visual Language

Use shared presentation tokens across title art, characters, equipment, environments, and effects:

- ink and contour strength;
- navy/slate/ivory/gold/leather/plum/sage palette;
- shared light direction;
- material ramps;
- facet density;
- silhouette and detail hierarchy.

The visual rules are:

- broad planes;
- clear silhouettes;
- quiet detail;
- light concentrated at the point of action;
- purposeful facets rather than random triangulation;
- limited contouring instead of outlining every surface.

The title screen should keep its moonlit, restrained atmosphere. Menus should inherit the palette, typography, dividers, and heraldic motifs without becoming visually busy.

The world pass should reduce procedural noise, repeated heavy outlines, and unnecessary surface detail. Existing props and stage themes should be audited and restyled before new environments are added.

## 4. Make Motion and Feedback Feel Continuous

Generic actors should receive the same temporal quality already present in the stronger champion rigs:

- blend from the current pose;
- preserve planted feet and weapon grips;
- layer locomotion, guard, breathing, recoil, and look channels;
- keep cloth, hair, and cape motion restrained;
- use receipt-driven casting and impact effects;
- keep ordinary transitions within the established 100–250 ms range;
- respect reduced-motion settings.

UI motion must support comprehension rather than delay it:

- title and menu transitions should settle cleanly;
- loading should show a meaningful state;
- disabled controls should explain why;
- errors should offer a clear recovery path;
- action results should be visible in the correct surface;
- no animation timer may alter game resolution or host outcomes.

## 5. First Implementation Slice

The first implementation slice covers the complete user experience around one humanoid presentation bundle:

- title screen and primary menus;
- Story Mode → Choose Lead → creator flow;
- Champion selection;
- creator live-rig preview;
- custom humanoid sword actor;
- plate, chain, leather, and robe variants;
- shield;
- staff, wand, and hand-only casting;
- one matching door, chest, lantern, village slice, cast effect, and impact effect;
- Actor Toolbox and gameplay presentation using the same identity.

Creatures, large-scale environment replacement, and a full item-family repaint come later.

## Test and Acceptance Plan

### Navigation and UX

Verify fresh and returning sessions through:

- Title → Story Mode → New Game;
- Title → Simulation Mode;
- Story Mode → Continue;
- Choose Lead → Creator;
- Choose Lead → Champion;
- Options → each expandable section → Back;
- Title/Main Menu/Back from every reachable screen;
- connection failure, loading, retry, and empty-state paths.

Test mouse, keyboard, focus order, Enter/Space activation, narrow desktop, mobile width, and short-height layouts.

### Visual and Character Proof

Capture:

- title screen;
- Story Mode;
- Simulation Mode;
- Options;
- Choose Lead;
- creator idle/move/attack;
- creator and gameplay versions of the same actor;
- both facings;
- equipment changes;
- world, tactical, and arcade presentations.

Acceptance requires no unacknowledged mixed-style humanoid route, no character clipping, no floating feet, no broken grips, and no identity mismatch between creator and gameplay.

### Performance and Smoothness

Measure:

- title/menu transition stability;
- creator preview frame time;
- world and combat frame time;
- eight actors and ten visible effects;
- DPR 1 and DPR 2;
- reduced-motion mode;
- asset loading and layout shift.

The primary desktop target must remain visually smooth with no meaningful frame-time regression, unbounded particle growth, or per-frame asset decoding.

## Assumptions

- The attached Faceted Heraldic document remains visual direction only, not gameplay or canon authority.
- Existing title/menu geometry is preserved unless a specific flow defect requires change.
- Host authority remains unchanged.
- The creator/gameplay rig unification is the first required implementation milestone.
- The plan favors a smaller number of polished, reusable presentation contracts over adding more independent art or renderer systems.
