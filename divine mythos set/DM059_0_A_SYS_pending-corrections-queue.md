---
id: DM059_0
title: "Pending Corrections Queue"
type: sys
subtype: pending-corrections-queue
load_priority: load-on-demand-scalpel-or-review-pass
canon: ALL
verse: ALL
timeline: META
arc: session-control
era: cross-era
status: operational-queue-not-canon
authority: conditional-operational-queue
rag_optimized: false
updated: 2026-09-19
volatility: volatile
arc_scope: evergreen
derived_from: null
predecessor_file: N/A
successor_file: N/A

scope:
  covers:
    - canon corrections and dictated lore Corey has decided but that are not yet composed into their owning corpus files
    - the decided/contested split and the mechanical-fix/needs-composing weight tag
    - the clearing rule that strikes an item once it lands
  use_case: load during a SCALPEL maintenance pass or any session doing a landing sweep; also the first thing a review pass diffs against DM035_0e
  not_for: live state (use the routed ledger), receipts of what already landed (use DM035_0e), file routing (use DM034_0/DM034_1)

xref_concepts:
  - pending-corrections-queue
  - staging-delta
  - receipt-by-state
  - founding-era-corrections
  - primeverse-origin-corrections
  - sanctum-counterweight-relocation

purpose: >
  Sibling to DM035_0e. DM035_0e is the record of what already happened to the
  corpus. This file is the record of what Corey has already decided but that
  has not yet been composed into its owning file. An item lives here between
  "Corey said so" and "the corpus says so."

  Registered 2026-09-19 (see DM035_0e). Index row: DM034_1 §1 [SYSTEM]. Mutation
  rule: routing-catalog.yaml editable_owners (overwrite-after-confirmed-commit).
---

# DM059_0 — PENDING CORRECTIONS QUEUE

## OWNER BOUNDARY

This file owns decided-but-uncomposed canon corrections and dictated lore. It
does not own live state (the routed ledgers do), receipts of landed work
(`DM035_0e` does), or open play decisions (`UNSAVED-CANON` / `CH-DELTA` do,
and only for the duration of a thread). An item's stay here ends the moment
`DM035_0e` shows it landed — not before, and not by assumption.

## HOW THIS FILE IS KEPT HONEST

`#RULE-RECEIPT-BY-STATE` (`DM034_1b`) governs clearing here exactly as it
governs any other landed-state claim: check `DM035_0e` first, then the
current owner and its validator, before striking a line. This file does not
get to invent its own exception.

Three operating rules, adopted 2026-09-19 after two items sat marked pending
here for a week past the day `DM035_0e` had already receipted them landed:

1. **Corey's stated correction is decided, not contested, by default.** It
   goes under Decided the moment he says it with conviction. It only moves to
   Contested if he says it's open himself. No review pass re-litigates a
   Decided line into limbo.
2. **A compound item splits the instant part of it lands.** Do not hold a
   whole bullet open because one clause of it still is — write the landed
   clause out and leave only the remainder queued.
3. **Every Decided item carries a weight tag.** `[mechanical]` = a specific
   wrong word, actor, citation, or misplaced sentence in a named file — should
   not survive more than one landing pass. `[composing]` = real prose has to
   be drafted or rewritten — fine to sit queued across several sessions, but
   should say so rather than reading as equally overdue.

---

## DIVINEVERSE — FOUNDING ERA (T0–T50)

### Decided — queued for composing

- `[composing]` Reva's history before the Remaking is the root of Sera's
  women-only boundary and part of her protectiveness. The core facts (bent
  back, kept alive for the line, 4'10" frame, soft feet, protectiveness) are
  landed in `DM005_0` T6 (2026-09-17 pass, `DM035_0e`); the phrase "full
  detail belongs in the corpus delta" implied more than that was intended.
  Held open for Corey to say what additional detail, if any, is still owed.

**Landed 2026-09-19 (this pass, see `DM035_0e`):** every other founding-era
`[composing]` item previously queued here — first village, Soliera's mother
form, the spoken-command cold-removal, birth/death/creation under her domain,
her purpose as a pragmatic god, her speech as authorship-not-foreknowledge,
mind-rewriting as preference-not-inability, and the full First No encounter —
was already composed in the 2026-09-17 founding-era reconciliation
(`DM005_0`/`0a`/`0b`, `DM028_1`, `DM030_2`) before this queue was even
drafted. Both `[mechanical]` items (Sera's four-partner list; the T25 "trust
me" line moving to Sera) were also already landed. Struck here rather than
left to read as still owed.

### Contested — Corey asked to keep these open

- What actually happened at the two T17 bandit quests once the First No
  encounter moves earlier, and where it lands in the T7–T16 span. (Confirmed
  still unrecovered in `DM005_0a` as of this pass.)
- Cause of Soliera's shift to word-sparse speech between T102 and about
  T290 (only a partial sweep done); Velin's T477 protocol that runs the
  danger toward speaking to her.
- T31 growth language and the Sera phase-map gap from T31 to T209.
- Tali week: Soliera's T49 reason for stopping and T50 "Come and stand
  beside me" under the speech law.
- Missing POV renders: Letha T19–T21 and T27–T31, Korin T27–T31, Taliandra
  before T34–T35.
- Unresolved dictation: "another god" or "another guard" in Sera killing
  twenty or thirty in a line.

**Landed 2026-09-19:** the `DM030_1`-cites-`DM005_0`-by-line-number
`[mechanical]` fix — it now cites by section (§T10: The Remaking). Struck.

---

## PRIMEVERSE — ORIGIN (PRE-M0 RETROACTIVE LANE)

### Landed 2026-09-19 (this pass, see `DM035_0e`)

All seven previously-queued `[composing]` items — Primeverse starting as
ordinary Earth; Gates opening sparsely over 10–20 years, not bound to land;
belief as the mechanism that activates a Gate; technology/medicine/witchcraft
improving as Gates open; the single ~1930 Great War; the hostile Brazil Gate;
and the chupacabra becoming real — are composed into `DM014_2`'s existing
"Timeline – Soliera Prime" section (the correct existing owner: it already
covered Gates Emergence, the Church's Rise, and Company Expansion). `DM056_0`
`p_beat_prose_compilation` gate updated to landed.

### Contested — Corey asked to keep open

- Corey described a counterpart figure ("Sera negative"), probably male,
  functioning as an Arden-equivalent — insanely strong, genuinely hard to
  kill even for the divine — open question whether this is the same entity
  as canon's Soliera Negative (female, doctrinal antichrist/intercessor
  counterfeit) or a separate figure.

---

## SANCTUM COUNTERWEIGHT RELOCATION (CROSS-FILE)

- **Landed 2026-09-12** (DM035_0e receipt): the "opposing force / counterweight
  as Soliera's dominion nears completion" sentence pair was pruned from
  `DM029_06` — it was Primeverse-only material that had leaked into a
  `canon: ALL`-tagged Divineverse Sanctum file.
- **Contested — still open:** where the counterweight concept itself gets
  new prose. Candidates named in the original staging delta: `DM033_4`
  (Soliera Prime doctrine) vs. `DM056_0`'s retroactive pre-M0 lane. Corey's
  call needed before either gets drafted; hold verbatim until then.

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM059_0 -->
