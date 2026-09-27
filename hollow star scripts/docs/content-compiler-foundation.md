---
title: Hollow Star content compiler foundation
updated: 2026-09-26
---

# Content compiler foundation

## Generated-systems foundation (2026-09-26)

### Hooks for other files and runs

```python
from hollowstar.runtime_hooks import load_package, evaluate_effect

package = load_package("my-package.json", workspace_root=workspace)
receipt = evaluate_effect(package, "frost", elapsed=2)
# receipt["output"]["potency"]; no gameplay state changed

# Existing RunService: uses the active run or reads its save without loading it.
receipt = runs.probe_package_effect("my-run", package, "frost", since=5)
```

Host calls use `packet_effect_probe` with `package`, `effect_id`, `elapsed`,
or `packet_run_effect_probe` with `package`, `effect_id`, `run_id`, `since`.
MCP exposes `hsr_probe_effect` and `hsr_probe_run_effect` with the same fields.
For run probes, elapsed is the host's current phase counter minus `since`:
`turn_end` uses turns, `round_start` uses rounds, and `world_tick` uses seconds.
`since` is an explicit application counter, default zero on the Python/host API;
MCP requires it. Missing clocks and future/negative anchors are rejected.
Package fingerprints and rule fingerprints accompany the output. These hooks
calculate potency only; they do not apply immunity, resistance, stacking, expiry,
damage or rewards. Run probes do not tick clocks, consume RNG, load active state,
or save. Direct Python callers may supply `catalog=SourceCatalog(workspace)`
to recheck source provenance on each evaluation; host calls always do so.

The first implementation phase adds a runtime draft compiler to this same
Workbench host surface. It does not yet bind these drafts to gameplay.
`runtime_ready: false` and `stage: validated-foundation` are explicit in every
compile receipt. Existing previews, gameplay, saves, and the browser remain on
their existing contracts. No local-state reset has been performed.

The `hollow-star-runtime-package-1` draft wraps the source-linked scene package
and validates actors, items, effects, encounters, clocks, assets, state machines,
and generated rule bindings. Compilation checks references, versions, duplicate
IDs, source receipts, module hashes, finite numeric parameters, transition
ambiguity, and the package hash. A changed sealed draft must remove its old
`content_fingerprint` before recompilation. Validation does not certify balance
or authorize publication. Transition guards and actions, runtime conversion,
and executable state-machine integration remain subsequent work.

Host commands on the existing local authoring route:

| Command | Input | Result |
|---|---|---|
| `packet_runtime_schema` | none | portable JSON Schema |
| `packet_compile` | `package` | validated package, fingerprint, counts, diagnostics |
| `packet_rule_validate` | `binding` | source hash and restricted-language validation |
| `packet_rule_probe` | `binding`, `inputs` | two-worker reproducibility check; no state mutation |

The local MCP equivalents are `hsr_runtime_schema`, `hsr_compile_package`,
`hsr_validate_rule`, and `hsr_probe_rule`. Restart an existing MCP or host process
to load the new commands. Hosted Controls continues to deny authoring commands.

`tools/compile_content.py --schema` prints the schema.
`tools/compile_content.py web/content-package-example.json --wrap-scene`
compiles the existing example as a runtime draft. Output is JSON on stdout;
the tool never publishes packages or changes source files.

Generated modules live in `hollowstar/generated`. The worker parses a bounded
Python subset and interprets its AST; it never imports or executes supplied
Python bytecode. Only `def resolve(inputs)`, local assignments, conditions,
JSON literals, subscripting, arithmetic and named numeric functions are
supported. Imports, attributes, loops, arbitrary calls, and I/O are rejected.
A subprocess supplies a timeout and crash boundary; the restricted language
supplies the I/O boundary. Rule inputs and outputs are schema-validated.

The initial `decay.py` rule supports linear, exponential, logarithmic, and
threshold potency decay with floor, ceiling, or half-up rounding. Inputs are
explicit elapsed time, initial potency, rate, model and rounding. Values are
nonnegative, with no wall clock or independent RNG. These are formula probes;
they do not yet change live status effects. The host owns future application,
immunity, resistance, stacking, clock and save integration.

Schemas use a deliberately limited draft-2020-12 vocabulary, validated locally
without an extra dependency. Unsupported keywords fail closed. The schema is
available through the API and CLI rather than maintained as a second copy.

Focused test: `python tools/run_discovered_tests.py --module tests/test_compiler_foundation.py`.

Remaining expansion: gameplay binding and content conversion, the host revision
envelope, Workbench browser controls, frontend scaffolds, asset compilation,
additional generated-rule contracts, and the verified save cutover.

The **Content Workbench** is a local authoring surface backed by `HSRHost` and
`RunService`. Open **Content Workbench** from the Hollow Star title screen, or
visit `/content-workbench.html` on the existing local web server. Restart an
already-running server after installing engine changes.

It connects workspace sources to versioned, data-only packages that render as
interactive scenes and screens. It supports character, item, and prop cards;
inspection; authored interaction text; scene navigation; and durable isolated
preview sessions. A local Markdown interpreter now creates reviewable drafts
from explicit document structure. It is not a general semantic compiler or
public multiplayer server.

## Source access

`source_search` inventories supported content anywhere below the resolved
workspace root, independent of the current working directory. Searches match
relative filenames or text. Canonical-folder matches are listed first; this is
a location label, **not a determination of authority between owners**. The
compiler must still respect the corpus routing and ownership rules.

Supported text inputs are UTF-8 Markdown, text, JSON, YAML, CSV, and TSV. PDFs,
images, and audio are discoverable asset references; their contents are not
decoded by this adapter. Use the existing text extracts for PDFs. A future
format adapter can extend ingestion without changing the scene package.

Hidden files, runtime state, dependency/build folders, links/junctions, and
rollback snapshots are excluded. `include_archives: true` explicitly enables
historical archives and the frozen pack for reading, labeled `archive`. The
workbench never writes these sources. It does not expose arbitrary filesystem
paths, execute source text, or treat retrieved instructions as engine commands.

Limits are explicit: at most 20,000 files per search, 64 MB of text searched,
2 MB per text file, 100 results per page, and 400 lines per read. Search receipts
report scanned and skipped counts, truncation, pagination, and relative paths.
A source read returns a full-file SHA-256 plus the selected line range and
heading positions. Source edits invalidate a package's reference at validation
and at the start of a new preview. Existing previews retain their immutable
package; source changes do not rewrite a session in progress.

**Use excerpt as a screen** copies the selected text verbatim. **Interpret as
draft** uses Markdown headings as ordered screens, recognizes explicit
`Character:`, `Item:`, and `Prop:` labels, and recognizes
`Interaction: Target | Label | Result` for a visible entity in the same
section. Unclear content remains in scene prose and receives a line-numbered
review flag. The draft and its source evidence appear in the editor before
preview; editorial screen order does not imply canon chronology or mechanics.

## Compiler contract

The machine-readable contract is
[`content-package.schema.json`](../web/content-package.schema.json).
[`content-package-example.json`](../web/content-package-example.json) is a
non-canon two-scene example with a character, items, a prop, and interactions.
`hollowstar/content_package.py` supplies the authoritative semantic validator.

The root contains `schema_version`, `id`, `version`, `title`, `universe`,
`entry_scene`, `sources`, `scenes`, and `entities`. `timeline` and `notes` are
optional descriptive metadata. Universe and chronology are carried as metadata,
so Divineverse, Mergeverse, and other packets use the same contract.

Each source reference contains its own identifier, workspace-relative path,
SHA-256, and inclusive start/end lines. Scenes and entities link to source IDs.
Packages without sources are allowed as **unsourced drafts** and receive a
warning. Matching source hashes proves which bytes were referenced, not that a
compiler faithfully interpreted them or that the package is approved canon.

Scenes have IDs, titles, descriptions, visible entity references, source
references, and explicit exits. A scene can be a `scene` or `screen`. Entity
kinds are `character`, `item`, and `prop`; each has a description and optional
named interactions with authored result text. The built-in themes are
`astral`, `ember`, `forest`, and `stone`. Rendering uses text nodes and fixed
presentation styles, never package-supplied HTML, scripts, or arbitrary URLs.
An entity can optionally select an `asset_id` from the existing local artwork:
`townsperson`, `longsword`, `chain-shirt`, or `unidentified-rune`. The host resolves
these IDs to approved static assets; art conveys no mechanical identity.

Validation rejects unsupported schemas and fields, duplicate IDs, dangling
references, unreachable scenes, invalid source ranges, stale hashes, illegal
paths, oversized input, and mechanical fields such as damage or stat changes.
The package limit is 512 KB; there are at most 256 scenes, 512 entities, and 128
source references. JSON Schema checks shape; host validation additionally
checks graph integrity, bounds, references, and live source provenance.

## Host API

Send ordinary host requests through the existing JSON-lines, local MCP, or
`POST /api/host` transport. No AI service or network compiler is required.
Authoring commands do not boot or change the player's current mode or run.

```json
{"id":"find","command":"source_search","query":"T550","offset":0,"limit":30}
{"id":"read","command":"source_read","path":"hollow star scripts/docs/content-compiler-foundation.md","start_line":1,"line_count":20}
```

Use `packet_starter` with the same source-read parameters to receive a draft
package and validation receipt. Pass `expected_sha256` to detect an edit
between selection and extraction. The package commands are:

`packet_interpret` takes the same parameters for a Markdown source and returns
the validated draft package plus `review_flags`. It leaves the current run and
mode untouched. Source hashes are rechecked at validation and preview start.

| Command | Required request fields | Result |
|---|---|---|
| `packet_validate` | `package` | normalized package, digest, counts, warnings, source verification |
| `packet_preview_start` | `package`, `operation_id` | preview public view and validation receipt |
| `packet_preview_read` | `preview_id` | current public view, without advancing state |
| `packet_preview_action` | `preview_id`, `expected_revision`, `operation_id`, `action` | committed public view |
| `packet_preview_list` | optional `limit` | latest preview identities and package titles |
| `packet_preview_export` | `preview_id` | original immutable authoring package |

An `operation_id` is a caller-generated unique string, such as a UUID. Retain
it when retrying an uncertain operation. An exact action retry returns the
original response without advancing the revision again. Reusing the operation
ID with different contents is rejected. Repeating a successful start with the
same operation ID returns the same preview's current view.

```json
{"id":"inspect","command":"packet_preview_action","preview_id":"preview-REPLACE","expected_revision":0,"operation_id":"unique-inspection-id","action":{"type":"inspect","target":"lantern"}}
{"id":"choose","command":"packet_preview_action","preview_id":"preview-REPLACE","expected_revision":1,"operation_id":"unique-choice-id","action":{"type":"interact","target":"guide","interaction_id":"map"}}
{"id":"move","command":"packet_preview_action","preview_id":"preview-REPLACE","expected_revision":2,"operation_id":"unique-move-id","action":{"type":"navigate","target":"archive"}}
```

Navigate targets an exit ID on the current scene, not an arbitrary destination.
Inspection and interaction require an entity visible in that scene. Hidden
entities and unopened scenes are omitted from the public view. The local
authoring editor/export can see the full package; it is not a player endpoint.

`CONTENT_INVALID` reports validation or source errors. `PREVIEW_CONFLICT`
reports a stale revision or conflicting operation identity. Refresh the preview
and make a new decision after a revision conflict. The browser retains operation
IDs across uncertain retries and refreshes a stale scene before accepting a new
action.

## State and future hosting

`RunService.content_previews()` owns the authoring preview store under the
configured data root at `content_workbench/previews.sqlite3` (normally under
`.local`). It contains immutable digest-keyed packages, independent preview
state, and operation receipts. SQLite transactions serialize local writers,
including separate processes. Revision checks prevent stale tabs from silently
overwriting each other. Do not place an actively used SQLite database on a
network filesystem for multi-host workers; a hosted repository should provide
the same transaction and revision contract using its server database.

Preview state is not a gameplay Encounter and does not enter the five-save
retention policy, accounts, inventories, RNG, progression, or canon receipts.
The existing Python gameplay resolver remains authoritative. The workbench's
`mechanics: unbound` flag is deliberate: an inspectable sword is not yet an
equipped weapon, and a character card is not a stat block.

The authenticated Hosted Controls relay currently **denies every authoring
command** through its allowlist. Before public multiplayer hosting, add server
identities and authorization scoped to each session, a publication boundary
for reviewed packages, quotas, and a shared transactional storage adapter.
Serve only approved public projections. Never offer workspace search, raw
source reads, package uploads, or authoring exports to ordinary players.

Any later mechanics binding must use existing engine registries and actions.
Missing rules remain unresolved diagnostics; they must not become browser-side
rules or guessed combat statistics. The generated-systems foundation above
permits explicit restricted Python rule drafts and probes; applying them to
gameplay still requires an engine binding.

## Verification

Run the focused acceptance suite from `hollow star scripts`:

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools/run_discovered_tests.py --module tests/test_content_workbench.py
```

`tests/ui-content-workbench-check.cjs` checks the real HTTP host, scene and entity
interactions, source extraction, persistence across browser contexts, conflict
recovery, and desktop/mobile overflow. Use an isolated server and data root:

```powershell
python hollowstar_web_server.py --port 8767 --data-root .local/content-workbench-check
$env:HSR_UI_URL='http://127.0.0.1:8767'
node tests/ui-content-workbench-check.cjs
```

`--data-root` points the real Python `HSRHost` at an isolated save directory
instead of the real one; it is not a mocked engine. Browser evidence and test
outputs belong under `.local`, never in canonical packet files.
