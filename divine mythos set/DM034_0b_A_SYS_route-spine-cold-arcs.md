---
id: DM034_0b
title: "Route Spine — Cold Arcs"
type: sys
subtype: on-demand-routing-spine
load_priority: on-demand-cold-arc-and-reference-rows
canon: ALL
verse: ALL
timeline: META
arc: system-organization
status: hard-canon
authority: on-demand-load-routing
updated: 2026-09-07
volatility: slow
arc_scope: evergreen
derived_from: null
predecessor_file: N/A
successor_file: N/A
purpose: on-demand routing spine; cold-arc, character, mechanics, and reference rows
---

# DM034_0b — ROUTE SPINE (ON-DEMAND ROWS)

**Scope note (2026-08-02):** this file was originally cold arcs only and now
holds every row a direct boot does not need. The filename keeps `Cold_Arcs`
under the topology lock; the content is broader. Three groups live here:

1. **Cold arcs** — closed and dormant story, itinerary, and Primeverse rows.
2. **Character, pillar, and mechanics rows** — DM004, DM027–DM031, DM040–DM041,
   DM045, and the Doran/Wren family. Retrieved by scene need, never at boot.
3. **Reference and development rows** — DM042_0, DM043_0, DM046_0, DM047_0, DM048_0, archives.

Nothing here is deprecated or unreachable; every row is a normal on-demand
mount. `DM034_0` carries only the resident set, the timeline spines, the routers,
and the active arc; reading it whole is sufficient once work requires route
selection after whole-file resident boot.

Load classes: resident, mode, sandbox-only, forge-only, on-demand, story, combat, deep-index,
prep, live, reference, archived. `mode` loads after SANDBOX or FORGE is chosen;
`sandbox-only` never loads in FORGE; `forge-only` never loads in SANDBOX.
Archived files stay directly loadable on explicit
request but are never auto-mounted by a route or profile.

## ARC REGISTRY

Status vocabulary: `active` (played now), `closed` (played out), `dormant`
(played, may resume), `development` (approved design target, no played beat —
do not normalize these to closed or dormant).

|arc-id|status|beat range|mounted?|
|---|---|---|---|
|against-the-giants-tsr-9058|closed|TR2-G1.01–TR2-G3.05|yes|
|archived|closed|M70–M90|no|
|champion-tier|development|T531+ / recurring-antagonist dossiers|yes|
|primeverse-champion-band|development|reference / bench-only|yes|
|curse-of-strahd|closed|T476,T476–T498,T499–T515|yes|
|descent-into-avernus|closed|T430–T475|yes|
|divine-mythos|active|current Divineverse domain state|yes|
|evergreen|active|M0–M182+ / P-reference,M0–M90,M90–M183 / TR1–TR-|yes|
|hoard-of-the-dragon-queen-part-one|closed|T141–T160|yes|
|hoard-of-the-dragon-queen-part-two|closed|T161–T190|yes|
|japan-opening|dormant|TR-JP-01–TR-JP-05|yes|
|japan-t4-and-plum-titan|dormant|reference / TR-JP|yes|
|hollow-star-reliquary|development|post-level-20 / no played beat|yes|
|leviathan-closure-meeting|closed|M161–M175 / M180|yes|
|mergeverse|active|M0–M183+ / TR|yes|
|neo-moscow-badlands-to-breach|closed|M91–M125|yes|
|oak-city-settlement-and-departure|closed|M57–M90|yes|
|post-meeting-domestic-and-japan-setup|closed|M181–M183|yes|
|post-tiamat-cooldown-thayan-prelude|closed|T327–T355|yes|
|primeverse-character-matrix|dormant|META|yes|
|primeverse-character-roster|dormant|META|yes|
|t4-roster|development|reference / 5e translation|yes|
|primeverse-foundation|closed|P0+; retroactive lane open under Corey gate|yes|
|primeverse-institutional-and-magic-scaffold|dormant|META|yes|
|return-to-oak-city-first-witness-cycle|closed|M151–M160|yes|
|rise-of-tiamat-march-to-well|closed|T221–T290|yes|
|rise-of-tiamat-transition|closed|T191–T220|yes|
|sanctum-expansion-into-tyranny-of-dragons-onramp|closed|T101–T120,T121–T140|yes|
|sanctum-foundation|closed|T0–T50|yes|
|seras-itinerary-location-04-luskan|dormant|TR1-01–TR1-13|yes|
|seras-itinerary-travel-arc|dormant|T516+|yes|
|setting-reference|dormant|META|yes|
|slum-incursion-cascade-feast-departure|closed|M126–M150|yes|
|soliera-prime-origin-outpost-seven|closed|META|yes|
|storm-kings-thunder|active|T525–onward,TR3-SKT-current,TR3-SKT-prep-control|yes|
|thayan-aftermath-undermountain-incursion|closed|T397–T429|yes|
|thayan-reckoning-eltabbar-liberation|closed|T356–T396|yes|
|the-merge-incident|closed|M0–M21,M22–M44,M45-M55|yes|
|tyranny-of-dragons-climax|closed|T291–T298,T299–T308,T309–T326|yes|
|underdark-incursion-and-soliere-dzan-reversal|closed|T51–T100|yes|

## FILE TABLE
|file-id|arc-scope|volatility|load-class|
|---|---|---|---|
|DM004_1|evergreen|slow|on-demand|
|DM004_2|evergreen|slow|on-demand|
|DM004_2b|evergreen|slow|on-demand|
|DM004_2c|evergreen|slow|on-demand|
|DM004_3|evergreen|slow|on-demand|
|DM005_0|sanctum-foundation|invariant|story|
|DM006_0|underdark-incursion-and-soliere-dzan-reversal|invariant|story|
|DM007_1|sanctum-expansion-into-tyranny-of-dragons-onramp|invariant|story|
|DM007_2|sanctum-expansion-into-tyranny-of-dragons-onramp|invariant|story|
|DM008_1|hoard-of-the-dragon-queen-part-one|invariant|story|
|DM008_2|hoard-of-the-dragon-queen-part-two|invariant|story|
|DM008_3|rise-of-tiamat-transition|invariant|story|
|DM009_0|rise-of-tiamat-march-to-well|invariant|story|
|DM010_1|tyranny-of-dragons-climax|invariant|story|
|DM010_2|tyranny-of-dragons-climax|invariant|story|
|DM010_3|tyranny-of-dragons-climax|invariant|story|
|DM011_0|post-tiamat-cooldown-thayan-prelude|invariant|story|
|DM012_0|thayan-reckoning-eltabbar-liberation|invariant|story|
|DM013_0|thayan-aftermath-undermountain-incursion|invariant|story|
|DM014_1|soliera-prime-origin-outpost-seven|slow|on-demand|
|DM014_2|primeverse-institutional-and-magic-scaffold|slow|on-demand|
|DM014_3|primeverse-character-roster|slow|on-demand|
|DM014_4|archived|slow|archived|
|DM015_1|the-merge-incident|invariant|story|
|DM015_2|the-merge-incident|invariant|story|
|DM015_3|the-merge-incident|invariant|story|
|DM015_4|the-merge-incident|invariant|reference|
|DM016_1|oak-city-settlement-and-departure|invariant|story|
|DM016_2|neo-moscow-badlands-to-breach|invariant|story|
|DM016_3|slum-incursion-cascade-feast-departure|invariant|story|
|DM017_0|descent-into-avernus|invariant|story|
|DM018_0|curse-of-strahd|slow|on-demand|
|DM019_1|curse-of-strahd|invariant|story|
|DM019_2|curse-of-strahd|invariant|story|
|DM019_2b|curse-of-strahd|invariant|story|
|DM019_3|curse-of-strahd|invariant|story|
|DM020_1|return-to-oak-city-first-witness-cycle|invariant|story|
|DM020_1b|return-to-oak-city-first-witness-cycle|invariant|story|
|DM020_2|return-to-oak-city-first-witness-cycle|invariant|story|
|DM021_1|leviathan-closure-meeting|invariant|story|
|DM021_2|post-meeting-domestic-and-japan-setup|invariant|story|
|DM022_0|primeverse-character-matrix|slow|on-demand|
|DM023_0|seras-itinerary-travel-arc|slow|on-demand|
|DM024_1|seras-itinerary-travel-arc|slow|on-demand|
|DM024_2|seras-itinerary-travel-arc|slow|on-demand|
|DM024_3|seras-itinerary-travel-arc|slow|on-demand|
|DM024_4|seras-itinerary-travel-arc|slow|on-demand|
|DM025_0|seras-itinerary-location-04-luskan|invariant|story|
|DM026_0|against-the-giants-tsr-9058|invariant|story|
|DM027_0|evergreen|slow|combat|
|DM028_1|evergreen|slow|on-demand|
|DM028_2|evergreen|slow|on-demand|
|DM028_3|evergreen|slow|on-demand|
|DM028_3b|evergreen|slow|combat|
|DM028_3c|evergreen|slow|on-demand|
|DM029_01|evergreen|slow|on-demand|
|DM029_02|evergreen|slow|on-demand|
|DM029_03|evergreen|slow|on-demand|
|DM029_04|evergreen|slow|on-demand|
|DM029_05|evergreen|slow|on-demand|
|DM029_06|evergreen|slow|on-demand|
|DM029_07|evergreen|slow|on-demand|
|DM030_1|evergreen|slow|combat|
|DM030_2|evergreen|slow|on-demand|
|DM031_0|evergreen|slow|on-demand|
|DM032_0|setting-reference|slow|on-demand|
|DM033_1|primeverse-foundation|invariant|story|
|DM033_2|primeverse-foundation|invariant|story|
|DM033_3|primeverse-foundation|invariant|story|
|DM033_4|primeverse-foundation|slow|story|
|DM052_0|storm-kings-thunder|slow|on-demand|
|DM039_0|japan-opening|invariant|story|
|DM040_0|storm-kings-thunder|slow|on-demand|
|DM041_0|storm-kings-thunder|slow|on-demand|
|DM041_A|storm-kings-thunder|slow|on-demand|
|DM041_A1|storm-kings-thunder|slow|on-demand|
|DM041_B|storm-kings-thunder|slow|on-demand|
|DM041_B1|storm-kings-thunder|slow|on-demand|
|DM041_B4|storm-kings-thunder|slow|on-demand|
|DM041_C|storm-kings-thunder|slow|on-demand|
|DM041_D|storm-kings-thunder|slow|on-demand|
|DM041_E|storm-kings-thunder|slow|on-demand|
|DM042_0|evergreen|slow|on-demand|
|DM043_0|japan-t4-and-plum-titan|slow|on-demand|
|DM043_D1|primeverse-champion-band|volatile|on-demand|
|DM045_DS1|storm-kings-thunder|slow|on-demand|
|DM045_DS2|storm-kings-thunder|slow|on-demand|
|DM045_DS3|champion-tier|slow|on-demand|
|DM045_DS4|storm-kings-thunder|slow|on-demand|
|DM045_DS5|storm-kings-thunder|slow|on-demand|
|DM046_0|hollow-star-reliquary|slow|on-demand|
|DM046_1|hollow-star-reliquary|slow|on-demand|
|DM047_0|evergreen|slow|on-demand|
|DM048_0|evergreen|slow|on-demand|
|DM049_0|champion-tier|slow|on-demand|
|DM050_0|champion-tier|slow|on-demand|
|DM051_0|champion-tier|slow|on-demand|
|DM057_0|evergreen|slow|on-demand|
|DM058_0|evergreen|slow|on-demand|
|DM053_0|t4-roster|slow|on-demand|
|DM004_1a|evergreen|slow|on-demand|
|DM004_1b|evergreen|slow|on-demand|
|DM004_0|evergreen|slow|on-demand|
|DM004_4|evergreen|slow|on-demand|
|DM004_3a|evergreen|slow|on-demand|
|DM005_0a|sanctum-foundation|invariant|on-demand|
|DM005_0b|sanctum-foundation|invariant|on-demand|
|DM006_0a|underdark-incursion-and-soliere-dzan-reversal|invariant|on-demand|
|DM006_0b|underdark-incursion-and-soliere-dzan-reversal|invariant|on-demand|
|DM007_2a|sanctum-expansion-into-tyranny-of-dragons-onramp|invariant|on-demand|
|DM007_2b|sanctum-expansion-into-tyranny-of-dragons-onramp|invariant|on-demand|
|DM008_1a|hoard-of-the-dragon-queen-part-one|invariant|on-demand|
|DM008_1b|hoard-of-the-dragon-queen-part-one|invariant|on-demand|
|DM008_2a|hoard-of-the-dragon-queen-part-two|invariant|on-demand|
|DM008_2b|rise-of-tiamat-transition|invariant|on-demand|
|DM008_2c|rise-of-tiamat-transition|invariant|on-demand|
|DM008_3a|rise-of-tiamat-transition|invariant|on-demand|
|DM008_3b|rise-of-tiamat-transition|invariant|on-demand|
|DM009_0a|rise-of-tiamat-march-to-well|invariant|on-demand|
|DM009_0b|rise-of-tiamat-march-to-well|invariant|on-demand|
|DM009_0c|rise-of-tiamat-march-to-well|invariant|on-demand|
|DM010_3a|tyranny-of-dragons-climax|invariant|on-demand|
|DM012_0a|thayan-reckoning-eltabbar-liberation|invariant|on-demand|
|DM012_0b|thayan-reckoning-eltabbar-liberation|invariant|on-demand|
|DM012_0c|thayan-reckoning-eltabbar-liberation|invariant|on-demand|
|DM013_0a|thayan-aftermath-undermountain-incursion|invariant|on-demand|
|DM013_0b|thayan-aftermath-undermountain-incursion|invariant|on-demand|
|DM014_4a|archived|slow|archived|
|DM014_4b|archived|slow|archived|
|DM015_1a|the-merge-incident|invariant|on-demand|
|DM015_1b|the-merge-incident|invariant|on-demand|
|DM015_2a|the-merge-incident|invariant|on-demand|
|DM015_2b|the-merge-incident|invariant|on-demand|
|DM015_2c|the-merge-incident|invariant|on-demand|
|DM015_3a|the-merge-incident|invariant|on-demand|
|DM016_1a|oak-city-settlement-and-departure|invariant|on-demand|
|DM016_2a|neo-moscow-badlands-to-breach|invariant|on-demand|
|DM016_2b|neo-moscow-badlands-to-breach|invariant|on-demand|
|DM016_3a|slum-incursion-cascade-feast-departure|invariant|on-demand|
|DM016_3b|slum-incursion-cascade-feast-departure|invariant|on-demand|
|DM017_0a|descent-into-avernus|invariant|on-demand|
|DM017_0b|descent-into-avernus|invariant|on-demand|
|DM019_1a|curse-of-strahd|invariant|on-demand|
|DM021_1a|leviathan-closure-meeting|invariant|on-demand|
|DM021_1b|leviathan-closure-meeting|invariant|on-demand|
|DM022_0a|primeverse-character-matrix|slow|on-demand|
|DM022_0b|primeverse-character-matrix|slow|on-demand|
|DM024_1a|seras-itinerary-travel-arc|slow|on-demand|
|DM024_1b|seras-itinerary-travel-arc|slow|on-demand|
|DM024_1c|seras-itinerary-travel-arc|slow|on-demand|
|DM024_2a|seras-itinerary-travel-arc|slow|on-demand|
|DM024_2b|seras-itinerary-travel-arc|slow|on-demand|
|DM024_2c|seras-itinerary-travel-arc|slow|on-demand|
|DM024_3a|seras-itinerary-travel-arc|slow|on-demand|
|DM024_3b|seras-itinerary-travel-arc|slow|on-demand|
|DM024_3c|seras-itinerary-travel-arc|slow|on-demand|
|DM025_0a|seras-itinerary-location-04-luskan|invariant|on-demand|
|DM026_0a|against-the-giants-tsr-9058|invariant|on-demand|
|DM029_01a|evergreen|slow|on-demand|
|DM030_2a|evergreen|slow|on-demand|
|DM034_2a|evergreen|slow|on-demand|
|DM034_2b|evergreen|slow|on-demand|
|DM035_0e|evergreen|slow|on-demand|
|DM038_6a|storm-kings-thunder|slow|on-demand|
|DM038_6b|storm-kings-thunder|slow|on-demand|
|DM039_0a|japan-opening|invariant|on-demand|
|DM041_A2|storm-kings-thunder|slow|on-demand|
|DM041_A3|storm-kings-thunder|slow|on-demand|
|DM041_B2|storm-kings-thunder|slow|on-demand|
|DM041_B3|storm-kings-thunder|slow|on-demand|
|DM034_1a|evergreen|slow|on-demand|
|DM034_1b|evergreen|slow|on-demand|
|DM002_1a|evergreen|slow|on-demand|
|DM002_3a|evergreen|volatile|on-demand|
|DM002_3b|evergreen|volatile|on-demand|
|DM038_N3|storm-kings-thunder|slow|on-demand|

## POINTERS
active spine -> DM034_0; deep index -> DM034_1


## MOUNT DISCIPLINE

Mount discipline governs **trust, not memory**. Previously read text may remain
in context, but a commit can make that view non-authoritative. Never answer a
live question from a copy that play has already invalidated.

Re-read policy keys to the `volatility` column of the FILE TABLE above.

|volatility|policy|
|---|---|
|invariant|read once; valid all session; never re-read|
|slow|valid all session unless a write lands on it|
|volatile|valid while the thread's own STAGING DELTA accounts for every change since the read; stale on a commit from outside this thread, or at session start|

**Staleness is about provenance, not elapsed turns.** A volatile file read once
in this thread does not decay because ten exchanges passed. It goes stale when
something changed it that this thread did not record — an outside commit, or a
new session. Within one thread, `file as read + STAGING DELTA` is the live
authority, and re-reading a file to recover state the delta already holds is
waste, not diligence.

Consequences for play: fight two seeds from the round-one snapshot plus the
delta, not from a fresh read. Read the file again only when the delta cannot
account for the gap — then say so, and read the section, not the file.

The only genuine way to reclaim context is to close with the DM000_4 SESSION
HANDOFF block and start a new session.


## STAGING DELTA

DM000_4 owns the block format. The delta is an in-thread running record at zero
file cost: nothing is written until Corey says save, and then each lane commits
to its owning ledger in one pass.

The four state domains are Divine (`DM038_L`), Merge (`DM054_0`), Hollow
Star (`DM055_0`), and Prime (`DM056_0`). Confirmed play still commits through
five purpose-specific lanes:

|lane|owner|holds|
|---|---|---|
|L-DELTA|DM038_L|current Divineverse story state: edge, route, gates, exact readiness, durable regional state, and open fronts; arc handoffs change keyed state, not owner|
|M-DELTA|DM054_0|Merge edge, regional state, world awareness, and open gates|
|P-DELTA|DM056_0|Prime retroactive additions only; closed forward of M0|
|CH-DELTA|DM038_CH|prep decisions, re-sources, and authorized non-canon simulation findings — never live state|
|RECEIPTS|DM035_0e|sole current append-only receipt history; static provenance is off-corpus|

`UNSAVED-CANON` is the sixth line and owns nothing: it is the running
"capture?" list of durable facts decided in play but not yet routed to a lane.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM034_0b -->
