---
id: DM034_1b
title: "Verification and Tooling Discipline"
type: sys
subtype: semantic-shard
load_priority: scalpel-by-section-via-DM034_1
canon: "ALL"
verse: "ALL"
timeline: "META"
arc: "system-organization"
status: "hard-canon"
authority: "canonical semantic shard of DM034_1"
updated: 2026-09-09
volatility: slow
arc_scope: evergreen
derived_from: DM034_1
predecessor_file: N/A
successor_file: N/A
purpose: "Owns the tooling mandate, edit and verification sequence, manifest discipline, and size and rolling T-beat contract."
segment_parent: DM034_1
segment_ordinal: 3
segment_count: 3
---

# DM034_1b — Verification and Tooling Discipline

> **Opening context:** This file is a self-contained architecture detail shard. DM034_1 remains the compact master index and pack-selection owner.

## SEGMENT MAP

Load only the smallest segment whose coverage matches the question. Each sibling repeats its own scope and authority context.

| ID | Covered section |
|---|---|
| DM034_1 | Master file index and compact pack selection |
| DM034_1a | XREF, Drop-In, Source, and Pack Detail |
| DM034_1b | Verification and Tooling Discipline |

## 6. TOOLING MANDATE & EDIT DISCIPLINE (V8)

**Checker mandate.** Any UPDATE session that edits this file's §1 index, the
routing contract, or file topology ends by running `tools/check.py` from the
workspace root. That wrapper runs the chain in
dependency order — frozen-pack integrity through `compact_pack_sync.py`, then `build_verification_manifests.py`,
then `tools/xref_checker.py` — because each stage consumes what the previous one
writes, and running them out of order surfaces stale-artifact mismatches that are
not real defects. `tools/check.py --fix` refreshes active manifests but never
rebuilds the frozen 25-file canon archive.
Invoking `tools/xref_checker.py` directly remains valid when nothing upstream
changed. A clean run — zero ERRORs —
is the exit criterion for the session, not a suggestion. WARN-tier findings route
to their owner tasks (encoding → Playbook 2 / V8 group E; terminators →
Playbook 11 / V8 group E) and are logged, never fixed opportunistically.

**Mount-side fallback (tooling absent).** The checker, `routing-catalog.yaml`, and
`tools/compact_pack_sync.py` live in the workspace, not in the project upload. A
session running against a mount without them can verify anchors by grep, but it
cannot run the checker, cannot validate the catalog mirror, and cannot certify
§1 index-vs-disk drift. Such a session records `checker: not run (tooling absent
from mount)` in the central DM035_0e receipt rather than claiming clean, and any edit
touching §1, routing, or file creation/retirement/rename is flagged for a
workspace-side checker run before it counts as landed. A clean run
is still the exit criterion; absent tooling defers it, never waives it.

**Checker scope (current V8 contract).**
- ERROR tier: dead DM-references (a reference to a file that does not exist,
  excluding [RETIRED] IDs and lines carrying the "(transient session inputs,
  not archived)" annotation), §1 index-vs-disk drift in either direction
  (an index row with no file on disk, or a DM-prefixed file with no index row),
  a failed stale-view canary, V8 frontmatter/catalog or workspace-policy
  drift, broken reciprocal reading chains, and verification
  manifest/frozen-pack disagreement or retired-archive hash drift.
- WARN tier: UTF-8 BOM, CRLF line endings, mojibake byte-signatures, and a
  missing END-style terminator on SYS/REF/synthesis files (beat files are
  report-only — terminators there need author approval per Playbook 11).
- Body-level self-references are counted as info, never flagged — a file naming
  its own ID is not a defect.

**One writer, one central receipt.** Edits to this file land only with a dated
receipt in `DM035_0e`, and that receipt notes the checker result ("checker clean"
or "checker: N warnings logged"). Maintenance history does not remain as a
per-file changelog.

**Tail discipline (cloud-sync hazard).** Before editing any corpus file, confirm
its last line is a plausible ending (terminator line or complete sentence). After
writing, re-read the tail and confirm the intended ending survived. On suspected
truncation: STOP — check a verified pre-maintenance snapshot, the last
manifest-verified compact-pack copy, or OneDrive version history for the intact tail before
touching anything. Full countermeasures live in MAINTENANCE_PLAYBOOKS.

**Frozen 25-file canon archive.** `divine mythos set/` is authoritative. The
directory `project context/TR3_SKT_25_FILE_PACK/` preserves a manually selected
25-file snapshot and is never an automatic synchronization target. Never
hand-edit it. Normal `tools/compact_pack_sync.py --check` operation verifies
only its inventory and hashes; later source drift is irrelevant. The 2026-08-30
pack is the current manual baseline. A future replacement is an explicit full
manual refresh with a release date, after which the pack is frozen again.
`--apply-if-due` remains forbidden. The manifest owns the
frozen hashes and status; HSR is excluded from membership.


## SIZE AND ROLLING T-BEAT CONTRACT

- Canonical Markdown has a 30,000-byte soft warning and a 37,500-byte hard
  split gate.
- Semantic siblings are loaded through the stable owner's `SEGMENT MAP`; never
  bulk-load a family when one shard answers the question.
- Rolling Divineverse narrative packets close at ten completed beats or
  30,000 bytes, whichever comes first.
- `tools/tbeat_packets.py check` verifies size, packet ownership, and spine
  mirrors. `scaffold --beat <number> --title <title> --packet <DM id>` creates
  only an explicit draft with required fields; it cannot authorize or invent
  canon.
- `tools/check.py` runs this contract after pack, manifest, and XREF checks.

## SURFACE & TOOLING REACHABILITY

`#RULE-SURFACE-CAPABILITY` — added Rev 8.5.2, 2026-08-27. Rewritten 2026-09-04
on Corey's ruling that claude.ai is one project-mount surface, not separate
code-on and code-off surfaces.

**Five surfaces reach some or all of this corpus.** Establish which one is
running before claiming a validator ran, naming a write target, or drawing a
negative conclusion.

| surface | where | writes |
|---|---|---|
| desktop | Diaspora, direct | canonical — the corpus |
| bridged desktop | Diaspora, through the device shell | canonical — the corpus; deletion needs a per-session grant |
| claude.ai project mount | phone or web, uploaded corpus | stages deltas only — never the corpus |
| ChatGPT project | frozen 25-file pack | none |
| cowork, no device bridge | phone or web, via the Project's doc API — not `/mnt/project` | stages deltas only, standing permission, no per-instance ask needed — never the corpus docs directly; a doc-API write persists in the mount itself but is destroyed with no diff on the next full reupload, so the mount copy is disposable and disk is the only real target |

**Desktop** is Codex or Claude Code working in the folder directly. **Bridged
desktop** is Cowork reaching the same folder through the device shell. Both use
the same physical computer and canonical files; only the resolved workspace
path differs, which is what gates HSR below.

**The claude.ai project mount stages and does nothing else.** With code
execution on, section reads, line ranges, `grep`, `sed`, `awk`, `stat`, and
`find` work against `/mnt/project` and are the normal read path. The 95,000-byte
turn budget still applies, so target reads instead of mounting large files.
The upload does not contain `tools/`, `project context/`, or `hollow star
scripts/`, and it has no write path back to the corpus. Staged deltas go only to
`/mnt/user-data/outputs`; Corey lands them on Diaspora through Codex.

**Code execution is a precondition, not a modeled surface.** Verify it once at
session open with `ls /mnt/project | wc -l`. A returned count establishes the
project mount's full uploaded-corpus read capability for that session. If the
command errors, report that the setting is supposed to be on and do not
substitute semantic search for a filesystem read while calling it a read.

**ChatGPT is coverage-limited to the frozen 25-file pack.** That is a coverage
limit rather than a read-tool capability claim. Pack membership is owned by
`DM034_1 §5` and `DM000_2` GPT PROJECT 25-FILE FROZEN PACK; measure the live
corpus inventory on disk instead of caching its count here.

**Negative-claim discipline.** `#RULE-ABSENCE-NOT-EVIDENCE`

Absence of a hit is not absence from the corpus. Before writing "X is not
present," name what was searched and what that surface could not reach. A token
audit across the uploaded corpus is settleable from the project mount and should
be run; a claim about `tools/`, `project context/`, or the scripts folder is not
settleable there. A negative claim without named scope and a settling check is a
hypothesis and is recorded as one.

**Validation and receipt lookup:** `#RULE-RECEIPT-BY-STATE`

When looking for validation or a receipt for a change, check `DM035_0e` first,
then check the current owner and the applicable validator output. Also inspect
the negative space: if the claimed change is already embodied by the current
owner and the validator confirms that state, treat that state as positive
evidence even when no separate receipt line is found. Do not report the absent
line as a defect or repeat that it is already listed elsewhere. Silently add
the item to the next maintenance-history offload list; current receipts stay in
`DM035_0e`, and closed history moves to the locked off-corpus archive.

**Scope extension, 2026-09-19:** `#RULE-RECEIPT-BY-STATE` also governs
`DM059_0` (Pending Corrections Queue). An item does not get struck from that
queue on say-so or elapsed time; it gets struck only after this same
DM035_0e-first check confirms it landed. Where a queued item is compound,
split it into its landed and unlanded parts the moment any part clears this
check — do not hold the whole item open because one part still is. This
extension exists because the failure already happened once: two corrections
sat marked pending in chat-side notes for a week after DM035_0e had already
receipted them landed, because nothing ran this rule against those notes.

**The working folder on disk is the corpus. The project mount is a read-only
upload and is never canon.** As of 2026-08-27 it carried different filenames and byte counts for the same T550.2-T550.4 beats; verified 2026-09-04 against corpus-verification-manifest.yaml, all 217 canonical files on the mount are now byte-exact sha256 matches, while the six Divine narrative packet filenames still flatten their T-beat decimal to an underscore. Byte-identity is verifiable from the mount and may be claimed when measured; it does not make the upload canon, and a conflict is still never resolved in its favour. Never resolve a
conflict in the upload's favour.

**Read-only is plumbing, not filesystem permission.** Verified 2026-09-04: a
write under `/mnt/project` may return success but is discarded and never reaches
the project or corpus. It can also corrupt the session's own file-count view.
The project mount is therefore never a write target; constrain staged output to
`/mnt/user-data/outputs` before writing.

**Working on disk, a structural change is not finished until the checker runs.**
Quote its real numbers in the receipt. **Working where the tools are not
reachable, never write "checker clean"** — record the canonical string
`checker: not run (tooling absent from mount)`, the same one the central receipt
uses. One condition, one string. On disk the tools are reachable and neither
string is ever correct — run the checker.

## HSR BRIDGE AND THE SURFACE GATE

`#RULE-HSR-SURFACE-BINDING` — added Rev 8.5.2, 2026-09-04.

**This section owns only the verification half of Hollow Star: which chain
checks what, and why the optional runtime suite is surface-bound.** Design is
`DM046_0`; the run and findings ledger and its
`surface.unreachable_from` declaration are `DM055_0`; routing, the host path
and `local-check` are `DM034_0` MOUNT SETS `hollow_star_framework` and
`hollow_star_runs`; local boot and mode selection are `hollow star
scripts/hsr-bootloader.md`.

**The bridge is checked twice, by two stages, at two tiers.**

Step 4, `tools/xref_checker.py`, runs the surface-independent bridge scan on
every surface, all of it ERROR tier: the four bridge files present
(`host_config.json`, `hsr-bootloader.md`, `snapshots/party_snapshot.json`,
`HSR_HANDSHAKE.json`), each valid UTF-8 with no BOM or CRLF; the host config's
schema version and handshake path; the DM authority contract — design owner
`DM046_0`, runtime pair `DM044_0` + `DM044_1`, `SIMULATION` seed mode, and both
`corpus_writes` and `runtime_story_markdown_reads` false; the mode gate; and the
generated snapshot's own contract. **A step 4 bridge error is real on every
surface and is never explained away as off-surface.**

Those values are topology invariants. `host_config.json` carries mode policy;
the schema-2 handshake is integrity-only and contains no certification or mode
projection. `tools/check_hollow_star_runtime.py` is an on-demand, surface-bound
runtime suite: it re-checks the exported party snapshot, handshake, and every
discovered test module.

**What binds it: path identity, not machine identity.** `HSR_HANDSHAKE.json`
records `validated_workspace_root` — the absolute path the handshake was
validated under — and the runtime re-resolves that root at read time. Any mount
whose resolved root differs fails with
`HANDSHAKE_INVALID ... changed=validated_workspace_root`. A bridged session is
running on the same computer that wrote the handshake, but the workspace
resolves to the session mount path rather than the recorded desktop path, so
step 6 cannot pass there and no amount of re-running changes it. **That is the
surface, not a corpus defect, and it is not evidence about engine state.**

Step 4 handles the same condition without failing. When the recorded root does
not match, it skips only the live handshake subprocess and prints an `i` line
under V8 METADATA; every contract above still runs. **The guard fails open:** a
missing, unreadable, or root-less handshake makes the question unanswerable, and
an unanswerable question runs the live check rather than skipping it. Absence
never buys a pass.

**Exit criterion by surface.** Steps 0-5 are the default criterion on every
surface where tools are reachable. The runtime suite is requested explicitly
with `tools/check.py --with-runtime`; on a mismatched bridge it remains
surface-blocked rather than a corpus failure. On the project mount, `tools/` does not exist: record
`checker: not run (tooling absent from mount)` and claim nothing about the
bridge. Off the desktop, say HSR is off-surface and stop; do not reason about
engine state from memory.

## SIZE LEDGER — DERIVED, NOT CACHED

`#RULE-BUDGET-ARITHMETIC` — added Rev 8.5.2.

Per-file byte tables are forbidden here: this cache drifted twice while still
claiming to guard the ceilings. The working files are the source of truth.
`tools/xref_checker.py` prints the measured whole-file resident total, route-gate
slice, combined hard limit, headroom, and whole-file DM034_0 size on every run; `tools/tbeat_packets.py
check` measures every canonical Markdown file and enforces the general rollover
warning and hard ceiling. Quote those current outputs in receipts instead of
copying their numbers into an owner.

**Two boot ceilings the checker enforces, and they are independent by ruling.**
The complete resident files DM000_1 and DM000_3 must together stay at or under
**18,750 bytes**, and DM034_0 as a whole file must stay at or under **18,750
bytes**. The former combined resident-plus-slice budget is retired with the
two-stage split: routing is a separate conditional load, not a tail of boot, so
each side is bounded on its own and neither borrows headroom from the other.
The checker also prints the routed worst case (resident + route gate) as an
advisory — it is not a gate, and no ruling caps it. All three boot owners are
read whole at any size up to their ceiling, which is the standing exception to
the ~8 KiB whole-read convention in DM034_0 RETRIEVAL POLICY; the checker
enforces the `load_priority` each one declares so the frontmatter cannot drift
from the retrieval it advertises. Resident files must contain no conditional
play-law sections, and the retired BOOT ENDS marker is prohibited in DM000_1,
DM000_3, DM000_4 and DM034_0; its return is an ERROR, not a warning. Anything
new that wants to be resident must fit the checker-reported headroom; otherwise
put it in a conditional owner and point at it from boot.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM034_1b — architecture detail shard -->
