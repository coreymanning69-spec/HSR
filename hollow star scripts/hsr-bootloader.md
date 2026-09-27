# Hollow Star Reliquary — Local Bootloader Contract

This is the HSR-specific boot contract for Codex, Cowork, and direct desktop
use. It is additive to the canonical Divine Mythos routing system. It does not
replace or edit `DM034_0` or `routing-catalog.yaml`.

## Trigger

Use this bootloader when the user mentions or clearly implies Hollow Star,
HSR, the Reliquary, HSR design, Sandbox, Forge, HSR character creation, HSR
items, HSR progression, or HSR run review.

If the user is asking for ordinary story play, remain on the story route. Do
not switch into HSR merely because a story character or location is mentioned.

## Mode selection

- `DESIGN` is available for architecture, inspection, and implementation work.
- `REVIEW` is available for snapshot, receipt, and validation inspection.
- `SANDBOX` is available and runs in isolation from canon.
- `FORGE` additionally requires explicit user intent and an authored module
  entry fixture; its placeless receipt remains review-only.

Do not infer Forge permission from a casual HSR mention.

## Context boundary

Load only the smallest context needed:

1. HSR design and promotion contract: `DM046_0`.
2. Canonical combat/runtime references: `DM044_0` and `DM044_1`, together when
   runtime work is authorized.
3. Certified machine-readable snapshot for executable party input.
4. An explicit future Forge entry fixture, if Forge is eventually enabled.

The Python host does not parse the full story Markdown corpus during every
turn. Sandbox does not read live story readiness. Forge receives an explicit
fixture rather than rummaging through the live ledger.

## Responsibilities

The conversational layer:

- identifies HSR intent and mode;
- loads context and presents the available capabilities;
- translates natural-language intent into structured host commands;
- narrates only the host's structured results and visible consequences.

The Python host:

- resolves workspace and data paths;
- validates snapshots, fixtures, and commands;
- owns deterministic mechanics and later run state;
- returns JSON-lines results and stable error codes;
- runs long validation and rehearsal work on the local PC, asynchronously;
- exposes compact validation status and final receipts instead of making the
  conversational layer carry raw logs;
- keeps generated state under `.local`;
- never writes to the Divine Mythos corpus;
- never invents mechanical facts or dialogue.

## Cowork conversation contract — Revision 9.0

`DESIGN` now exposes a deliberately narrow shared-turn adapter. Cowork or another
conversational reader translates Corey's spoken intent into one validated action,
then calls `design_turn` through the same local JSON-lines host. The request must
carry `run_id`, a non-empty `intent`, and the proposed structured `action`.

The response records the submitted intent in the saved run, returns the resolved
event and a compact status envelope, and labels the narrator boundary. Read and
narrate only the returned `public_view` block. `visible_state` remains available
by default for debug and audit consumers, with static `content` omitted and only
the latest five events retained; it is not the narrator source. Fetch reference
data once through `content_catalog` when needed instead of expecting it on every
turn. `public_only: true` is an optional transport optimization for clients that
do not need the debug envelope. Do not invent rolls, hidden room state, or divine
dialogue. Use `readout` for a fresh phone-sized public-view refresh after a
reconnect; it never advances the run.

This is a live **DESIGN** conversation loop. Sandbox and Forge share the same
RunService schema while keeping their non-canon and review-only boundaries;
Forge additionally requires explicit intent and an authored entry fixture.

## Local computation and token-saving contract

Long work belongs to the desktop. Codex and Cowork should submit a job, return
control to the local process, poll only for compact status, and request the
final receipt after completion. They should not repeatedly request raw checker
logs, replay unchanged output, or simulate validation in conversation.

Start one asynchronous full validation job after a stable implementation pass:

```json
{"id":"check-start","command":"validation_start"}
```

Poll at increasing intervals (30 seconds, then 60 seconds) with:

```json
{"id":"check-status","command":"validation_status","job_id":"<returned id>"}
```

When `status` is `completed` or `failed`, request the compact final receipt:

```json
{"id":"check-result","command":"validation_result","job_id":"<returned id>"}
```

The local PC owns CPU, RAM, deterministic RNG, save/resume, full rehearsals,
export checks, and validator execution. The conversational layer owns intent,
user-facing choices, and narration from returned state. The current Python
engine is CPU-bound; do not spend tokens or add GPU plumbing unless a measured
workload demonstrates a benefit from vector or tensor computation. The local
job log remains on disk and is fetched only for diagnosis.

## Local launch

From the Court workspace root:

```powershell
python "hollow star scripts/hollowstar_host.py" health
python "hollow star scripts/hollowstar_host.py" validate
python "hollow star scripts/hollowstar_host.py" local-check
python "hollow star scripts/hollowstar_host.py" --stdio
```

Example JSON-lines turn after boot, create-run, and design-start:

```json
{"id":"turn-1","command":"design_turn","run_id":"phone-demo","intent":"I study the room before committing.","action":{"type":"investigate","actor":"p0"}}
```

The launcher is path-independent and does not require a manually configured
`PYTHONPATH`. The local-check must approve a workspace directly beneath
`C:\Users\ACore\OneDrive\Desktop` whose name begins with `Soliera and Sera`.
UNC paths, cloud/project mounts, and other workspace locations fail closed.

`local-check` validates the current snapshot against every cited corpus owner
and atomically writes `hollow star scripts/HSR_HANDSHAKE.json`. A failed check
leaves the previous handshake byte-for-byte unchanged. `validate --target
handshake` is read-only and recomputes the artifact exactly; a missing, stale,
malformed, relocated, or extra-field handshake fails closed.

Handshake verification also binds SHA-256 digests of the complete snapshot and
host configuration. Duplicate JSON keys, non-finite numbers, oversized JSON,
noncanonical timestamps, and timestamps more than five minutes in the future
are rejected. These are local integrity checks, not signatures or authentication
against someone who can rewrite both the code and its data.

The phone watcher owns an OS-held per-workspace lock, including direct Python
launches. It refuses startup without a valid handshake and approved desktop,
waits for newline-terminated mailbox records, bounds each line to 1.3 MiB (1,363,148 bytes),
requires nonempty string IDs, and suppresses repeated IDs within a batch and
across answered records. Keep mailbox access restricted to trusted local users;
this file transport does not authenticate senders. A crash between executing a
command and saving its response still requires manual reconciliation before retry.

The handshake is durable routing evidence, not gameplay permission. Forge
still requires explicit intent and all run commands remain mode-bound; no run
command may infer permission from the mere existence of the file.

## Registered access routes

### Hosted Controls

Hosted Controls is a desktop-connected authenticated relay, not a public HSR
server. The engine and saves remain local and `HSRHost` remains authoritative.
Provision named Claude and GPT credentials once with:

```powershell
python "hollow star scripts/setup/hosted_controls_setup.py"
```

The command prints each token once and stores only SHA-256 token hashes under
`.local/hosted_controls.json`. The relay endpoint is `POST /api/hosted` and
requires `X-HSR-Client` plus `Authorization: Bearer <token>`. Hosted callers
may use health, capabilities, catalogs, public readouts, session intent, and
bounded design or sandbox turns. State-changing turns require a per-run lease
through `hosted_lease`; only one named client may hold that lease at a time.
Hosted requests always receive public-only projections. Shutdown, validation,
Forge, raw debug, profile administration, and corpus-affecting commands are
blocked at the relay before reaching the engine.

Three ways in, all landing on the same `HSRHost`:

1. **Local MCP server.** `hsr_mcp_server.py` is registered on this desktop as
   `hollow-star-reliquary` in the Claude desktop app and as `hollow-star` in
   Codex. The client spawns it natively, so it clears the location gate. Its
   tools are `hsr_health`, `hsr_boot`, `hsr_validate`, `hsr_design_turn`,
   `hsr_readout`, `hsr_session_intent`, the three `hsr_validation_*` job tools,
   and `hsr_command` as a
   direct passthrough to `HSRHost.handle()`. Call
   `hsr_command(command="inspect", params={"target": "capabilities"})` for the
   host's live command list rather than trusting a copy of it.
2. **Phone-bridge watcher.** `hsr_bridge_watch.py` drains
   `.local/phone_bridge/inbox.jsonl` and appends correlated responses to
   `outbox.jsonl`. Start it through `hsr_start_hollow_star.bat`, which refreshes
   the handshake first and holds a lock so a second copy refuses rather than
   races it; the desktop shortcut `Start Hollow Star` and the per-user Startup
   entry both point there. Task Scheduler will not accept an ONLOGON trigger
   without elevation, hence the Startup folder. One instance per workspace.
3. **Direct stdio**, as under Local launch above.

The `HSR Handshake Refresh` scheduled task runs `local-check` daily at 18:00 so
`HSR_HANDSHAKE.json` tracks owner-file changes instead of going stale between
manual runs.

Registration is native-only: a bridged session can neither write the client
configs nor satisfy the location gate on its own.

## JSON-lines examples

```json
{"id":"1","command":"health"}
{"id":"2","command":"boot","mode":"DESIGN"}
{"id":"3","command":"validate","target":"snapshot"}
{"id":"4","command":"validate","target":"handshake"}
{"id":"5","command":"inspect","target":"capabilities"}
{"id":"6","command":"shutdown"}
```

Each input produces exactly one JSON response on stdout. Diagnostics go to
stderr. Invalid requests, blocked modes, stale snapshots, and unsafe paths
fail closed with a machine-readable error code.
