---
id: DM055_0
title: "Hollow Star Run Ledger"
type: reference
subtype: hollow-star-run-and-findings-ledger
load_priority: load-on-demand-on-disk-only-for-hollow-star-runs-and-findings
canon: T-framework / HSR-facing
verse: ALL
timeline: reference / no-played-beat
arc: hollow-star-reliquary
status: runtime-gated-run-ledger
authority: authoritative-for-hsr-run-history-and-gate-projection-only
updated: 2026-09-09
volatility: slow
arc_scope: hollow-star-reliquary
derived_from: null
predecessor_file: N/A
successor_file: N/A
xref_concepts: [dm-state-1, four-ledger-split]
purpose: "Lab notebook for the Hollow Star Reliquary: run history, findings, executable mode boundaries, and a projection of gate state. Desktop-only; the runtime remains the authority for engine facts."
---

# DM055_0 — HOLLOW STAR RUN LEDGER

## STATE BLOCK — dm-state-1

Machine-readable current state. Validate with `tools/state_blocks.py`.

**Runtime-gated, 2026-09-06.** The route is live on the local desktop. The
run notebook remains empty until an actual run produces a receipt; its gate
projection defers to the generated handshake so it cannot become a second
runtime authority.

```yaml
{
  "schema_version": "dm-state-1",
  "ledger": "hsr",
  "owner": "DM055_0",
  "updated": "2026-09-09",
  "load": {
    "class": "gated",
    "surface": "local_desktop",
    "note": "routed on demand through hollow_star_runs; never resident boot"
  },
  "scaffold": false,
  "content_gate": "hollow star scripts/ runtime, via the handshake file",
  "surface": {
    "requires": "local_desktop",
    "unreachable_from": [
      "claude_ai_mirror",
      "gpt_project",
      "cloud_workspace"
    ],
    "on_unreachable": "say HSR is off-surface and stop; do not reason about engine state"
  },
  "runtime_authority": {
    "root": "hollow star scripts/",
    "contract": "hsr-bootloader.md",
    "handshake": "hollow star scripts/HSR_HANDSHAKE.json",
    "execution_gate": "unless the handshake exists and passes read-only validation, this profile is routing metadata only; Sandbox is isolated and Forge requires explicit intent with a review-only receipt",
    "rule": "engine facts come from the runtime; this file never becomes a second source of truth"
  },
  "runs": [],
  "open_author_gates": [],
  "closed_author_gates": [
    {
      "id": "wren_divine_damage_tag",
      "question": "does Wren's divine-source casting carry DamageTag.DIVINE",
      "ruling": "yes — DIVINE is carried on every spell and attack, alongside the printed type, never replacing it",
      "closed": "2026-09-05",
      "owner": "DM041_B divine_damage"
    }
  ]
}
```

## Owner Boundary

This is a lab notebook, not a status file. Its content is *runs* — what was
tried, against which fixture, what came out, what it proved or killed. Gate state
is a projection carried for convenience.

**It is not a source of truth for engine facts.** The runtime under `hollow
star scripts/` owns mechanics and state; its schema-2 handshake owns derived
integrity evidence.

Unless `HSR_HANDSHAKE.json` exists and passes read-only validation, this ledger
is routing metadata only. A passing handshake proves source freshness; it does
not override the Sandbox and Forge blocks projected from `DM046_0`. Findings
that would change live Divineverse state go to `DM038_CH` and
reach a story ledger only by a separate confirmed commit.

<!-- CORPUS REVISION: 9.0 -->

<!-- END DM055_0 -->
