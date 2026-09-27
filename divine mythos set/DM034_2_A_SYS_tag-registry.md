---
id: DM034_2
title: "Tag Registry & Architecture Standards"
type: sys
subtype: tag-registry
load_priority: load-on-demand-for-tagging-passes
canon: ALL
verse: ALL
timeline: META
arc: system-organization
era:
  - meta-document
  - tag-reference
  - split-from-DM034_1
status: hard-canon
authority: defines-tag-taxonomy-and-naming-standards
updated: 2026-09-17
volatility: slow
arc_scope: evergreen
derived_from: null
predecessor_file: DM034_1
successor_file: N/A
scope:
  covers:
    - inline tag taxonomy (#CHAR / #LOC / #CONCEPT / #THEME / #RULE / #CLAN / #ITEM / #OBSERVER / #THREAD)
    - tag authority model (binding vs. retrieval-only layers)
    - syntax standard (kebab-case rules for inline tags and xref_concepts)
    - concept semantics (core / arc / moment scales)
    - variant & deprecation table (canonical forms vs. legacy spellings)
    - core #RULE- registry (corpus-wide behavioral law tags + source files)
    - index-tag quick registry (most-used inline anchors)
    - xref_concepts YAML format standard
    - V8 architecture design principles
  use_case: load during tagging passes, audits, or when authoring new file headers
  not_for: file routing or the master file index (use DM034_1)

xref_concepts:
  - tag-taxonomy
  - tag-authority-model
  - variant-deprecation-table
  - core-rule-registry
  - index-tag-quick-registry
  - xref-concepts-format
  - r6-design-principles
  - searchable-canon
  - naming-standards
  - module-cluster-filename-roles
  - live-module-layer-contract
  - tetragrammaton-tetrad
  - recursive-five-point-architecture
  - ontological-circle
  - manifest-circle
  - cross-layer-bridge
  - soliera-hinge
  - yuium-distributed-whole
  - kabbalah-frame
  - metatron-literal-manifestation
  - metamorphoses-relational
  - soliera-current-awareness
  - soliera-mind-consent
  - veiled-eye-soliera-exclusion
  - body-mechanics-as-theology
  - preserved-causality
  - deashi-causal-display
  - silent-annihilation-true-pruning
  - divine-specification
  - cleaver-hand-gate
  - configuration-competence-gate
  - dagger-summoning
  - dagger-resistance-bypass
  - grand-cleave
  - skt-giant-scale
  - the-ordinant
  - writ-six

canon_flags:
  - "#RULE-INLINE-TAGS-USE-UPPERCASE-KEBAB-CASE"
  - "#RULE-XREF-CONCEPTS-USE-LOWERCASE-KEBAB-CASE"
  - "#RULE-NO-NEW-TAG-PREFIXES-WITHOUT-ARCHITECTURE-PASS"
  - "#RULE-THEME-TAGS-NEVER-OVERRIDE-MECHANICS"
  - "#RULE-DO-NOT-BULK-REPLACE-LEGACY-TAG-VARIANTS"


purpose: >
  Reference annex for tag taxonomy and architecture naming standards. Split from
  DM034_1 on 2026-06-06 so the architecture map stays a lean file-routing index.
  Load this file during tagging passes, schema audits, or when writing new file
  headers. DM034_1 points here for all tag-vocabulary questions.

ai_directives:
  - this file is reference data, not routing — DM034_1 owns the file index and XREF rules
  - when tagging new content, use the CANONICAL form from the Variant & Deprecation table
  - do not bulk-replace legacy tag variants in old files unless doing a full tagging pass
  - inline #RULE-* and YAML canon_flags are binding; xref_concepts and #THEME-* are not
  - do not add new inline tag prefixes without a dedicated architecture pass

open_threads_forward:
  - tag taxonomy refinements
  - tag taxonomy refinements after future architecture passes
---

## SEGMENT MAP

Load only the smallest segment whose coverage matches the question. Each sibling repeats its own scope and authority context.

| ID | Covered section |
|---|---|
| DM034_2 | DM034_2 — TAG REGISTRY & ARCHITECTURE STANDARDS |
| DM034_2a | 3. CORE #RULE- REGISTRY (canonical behavioral law tags) |
| DM034_2b | 4. INDEX-TAG QUICK REGISTRY |


# DM034_2 — TAG REGISTRY & ARCHITECTURE STANDARDS

This annex holds the tag vocabulary and naming standards formerly carried inline
in DM034_1 §6–§7. DM034_1 itself is now a lean router (file index + XREF rules +
new-content routing). Load this file for any tagging, auditing, or header-authoring
work.

## 1. CANONICAL INLINE TAG REGISTRY

Inline tags follow the format `#PREFIX-NAME`. Nine prefixes are active:

  #CHAR-    character present or directly referenced in the beat
  #LOC-     physical location where action occurs
  #CONCEPT- mechanical/theological concept deployed in the scene
  #THEME-   narrative/emotional resonance layer
  #RULE-    behavioral/canon law enforced by the scene or file
  #CLAN-    family, lineage, or inherited-house anchor
  #ITEM-    named object or artifact anchor
  #OBSERVER- non-participant presence or watching entity
  #THREAD-  explicit continuing plot-thread anchor

**Parsing rule:** All inline tags are searchable as plain-text strings. Beat files
use them as scene-level anchors. Reference files use them as concept anchors in
their front matter `xref_concepts:` or body headers.

### TAG AUTHORITY MODEL

Tags do not all carry the same authority. Treat them by layer:

- `canon_flags:` and inline `#RULE-*` tags are binding canon law. They cite rules
  the AI must obey when generating, summarizing, or correcting content.
- `xref_concepts:` is soft retrieval metadata. It says what a file is useful for
  finding; it does not create new canon by itself.
- Inline `#CHAR-*`, `#LOC-*`, `#CONCEPT-*`, `#THEME-*`, `#CLAN-*`,
  `#ITEM-*`, `#OBSERVER-*`, and `#THREAD-*` tags are searchable body anchors.
  They improve lookup precision and scene routing.
- `#THEME-*` tags are interpretive/emotional resonance only. They never override
  mechanics, chronology, character law, or `#RULE-*` tags.

### SYNTAX STANDARD

- Inline tags use uppercase kebab-case: `#CHAR-SERA`, `#LOC-OAK-CITY`,
  `#CONCEPT-VELVET-SPIRAL`, `#THEME-WITNESS-ECONOMY`,
  `#RULE-SOLIERA-SILENCE-UNLESS-DM`.
- Front matter `xref_concepts:` uses lowercase kebab-case:
  `velvet-spiral`, `witness-economy`, `soliera-silence-rule`.
- The active inline namespaces are `CHAR`, `LOC`, `CONCEPT`, `THEME`, `RULE`,
  `CLAN`, `ITEM`, `OBSERVER`, and `THREAD`. Do not add new prefixes without a
  dedicated architecture pass.
- Do not add new YAML `themes:` or `tags:` fields. Migrate their values into
  `xref_concepts:` only when they are retrieval-useful.

### CONCEPT SEMANTICS

`#CONCEPT-*` marks a searchable idea in body text. `xref_concepts:` decides
whether that idea should help retrieve the whole file. Use three concept scales:

- Core concepts are project-wide theology, physics, or design principles
  (examples: `divine-domesticity`, `witness-economy`, `infrastructure-not-empire`).
- Arc concepts are module or storyline retrieval anchors
  (examples: `module-inversion`, `curse-of-strahd-inversion`, `skyreach-approach`).
- Moment concepts are local beat labels. Use them inline when a scene needs a
  precise anchor; add them to `xref_concepts:` only if future retrieval should
  load the whole file for that moment.

### XREF_CONCEPTS FORMAT (V8 standard)

All YAML `xref_concepts:` fields use flat kebab-case lists. No sub-keys. No prose.
No parenthetical explanations. Example:

```yaml
xref_concepts:
  - divine-domesticity
  - mercy-as-infrastructure
  - soliera-silence-rule
  - tier-classification
```

The `themes:` and `tags:` YAML fields are retired under the V8 standard. All values
from those fields have been merged into `xref_concepts:`. Do not add new `themes:`
or `tags:` fields to any file.

## 2. VARIANT & DEPRECATION NOTICES

The following tags have known duplicates or truncations. Use the CANONICAL form
when tagging new content. The variants remain in old files for backward
compatibility — do not bulk-replace them unless doing a full tagging pass.

| Variant / Truncation                         | Canonical Form                                     | Notes                         |
|----------------------------------------------|----------------------------------------------------|-------------------------------|
| #RULE-CHARACTERS-DO-NOT-KNOW-PRIME           | #RULE-CHARACTERS-DO-NOT-KNOW-PRIME-DIVINE-MONIKER  | Truncated form — 4 files      |
| #RULE-PREDATION-EQUALS-ERASURE               | #RULE-PREDATION-RESULTS-ERASURE                    | Alternate phrasing — 1 file   |
| #RULE-SANCTUM-IS-INFRASTRUCTURE-NOT-EMPIRE   | #RULE-INFRASTRUCTURE-NOT-EMPIRE                    | Redundant form — 1 file       |
| #RULE-SANCTUM-NOT-A-CAGE                     | #RULE-SANCTUM-FREEDOM-NO-PREDATION                 | Covered by broader rule       |
| #RULE-SANCTUM-NOT-PRISON                     | #RULE-SANCTUM-FREEDOM-NO-PREDATION                 | Covered by broader rule       |
| #RULE-DEASHI-NO-SPEECH-EVER                  | #RULE-DEASHI-NONVERBAL-ALWAYS                      | Redundant — 1 file            |
| #RULE-DEASHI-NONVERBAL                       | #RULE-DEASHI-NONVERBAL-ALWAYS                      | Truncated form — 1 file       |
| #RULE-SOLIERA-DOES-NOT-SPEAK                 | #RULE-SOLIERA-SILENCE-UNLESS-DM                    | Redundant form — 1 file       |
| #RULE-SOLIERA-SILENCE                        | #RULE-SOLIERA-SILENCE-UNLESS-DM                    | Truncated form — 2 files      |
| #RULE-AI-NEVER-VOICES-SOLIERA                | #RULE-SOLIERA-SILENCE-UNLESS-DM                    | Covered by main rule          |
| #RULE-UNMASTERED-WEAPON                      | #RULE-CLEAVER-HAND-GATE                            | Superseded and closed: T532 STR 25 makes the Cleaver live one- or two-handed without disadvantage |
| #RULE-CONSENT-RULE                           | #RULE-CONSENT-AND-COMPREHENSION                    | Alternate phrasing — 4 files  |
| #RULE-CONSENT-LOCKED                         | #RULE-CONSENT-AND-COMPREHENSION                    | Partial form — 1 file         |
| #RULE-SERA-CONSENT-LOCKED                    | #RULE-SERA-INVIOLABLE-BODY                          | Retired collision: Sera's native body law is not her T12.5 First No |
| #CHAR-AMARA-WINDBREAKER                      | LEGACY — content migrated to DM015_3 appendix | Still appears in M-beat body text where Amara is present as a character; do not add to new files |
| #CHAR-AMARA                                  | #CHAR-AMARA-WINDBREAKER (if the character)         | Truncated — 1 file            |
| #CHAR-AMARA-QUEUED                           | Retired concept tag — do not reuse                 | 1 file, legacy only           |
| #CHAR-DRIZZT-DO                              | #CHAR-DRIZZT                                       | Dictation truncation — 1 file |
| #CHAR-C / #CHAR-D / #CHAR-E / #CHAR-F / etc.| Dictation truncation artifacts — do not tag        | Single-letter tags are noise  |
| #LOC-A / #LOC-C / #LOC-E / #LOC-F / etc.   | Dictation truncation artifacts — do not tag        | Single-letter tags are noise  |
| #RULE-E / #RULE-S / #RULE-V / #RULE-P       | Dictation truncation artifacts — do not tag        | Single-letter tags are noise  |
| #CONCEPT-C / #CONCEPT-D / #CONCEPT-G / etc. | Dictation truncation artifacts — do not tag        | Single-letter tags are noise  |
| #THEME-D / #THEME-I / #THEME-P / #THEME-W  | Dictation truncation artifacts — do not tag        | Single-letter tags are noise  |
| #THEME-ABSTRACT-JUDGEMENT                    | #THEME-ABSTRACT-JUDGMENT                           | British spelling — 1 file     |
| #RULE-ARDEN-KILL-ON-INTENT                   | #RULE-ARDEN-KILLS-ON-HOSTILE-INTENT                | Truncated form — 3 files      |
| #LOC-NEVEREMBERS-ESTATE                      | #LOC-NEVEREMBER-ESTATE                             | Apostrophe variant — 1 file   |
| #LOC-UNDRMOUNTAIN-LEVEL-1                    | #LOC-UNDERMOUNTAIN-LEVEL-1 (or just #LOC-UNDERMOUNTAIN) | Typo — 1 file           |
| #LOC-THAY-COASTAL-HUB / #LOC-THAYAN-COASTAL-HUB | #LOC-THAY-COASTAL-BASE                         | Three variants — consolidate  |
| #CONCEPT-HEXAGRAM-GEOMETRY                  | #CONCEPT-RECURSIVE-FIVE-POINT-ARCHITECTURE        | Deprecated architecture alias; never use for new content |

### "Blessed" — discretionary conferral, not a power test (2026-08-23)

**Both senses are correct. Neither is being retired.** Sanctum-made things may
carry ordinary blessing, while *the Blessed* is a discretionary named tier.
Soliera gives that status directly or through Ember or Sera's delegated
judgment. There is no objective boundary to infer from power, authorship,
rarity, bearer, or construction method.

| Sense | Written as | Means | Do not |
|-------|-----------|-------|--------|
| Tier membership | *the Blessed*, *Blessed tier*, `#CONCEPT-BLESSED-TIER` | A discretionary status given by Soliera, directly or through Ember/Sera | Do not infer or self-admit a member |
| Ordinary imbued sense | *blessed kit*, *blessed equipment*, *blessed wand*, *Sanctum-blessed* | Divine-imbued gear or faction status — DM009_0 Vanguard kit, DM031_0 Zhentarim trinkets, DM038_CH Wren's wand, DM024_2/DM031_0 Neverember | Do not read existing lowercase uses as membership claims; do not bulk-promote or bulk-rewrite them |

The distinction is discretionary, not a discoverable cut. Soliera's grant or
delegated grant is the event that makes membership true.

<!-- CORPUS REVISION: 9.0 -->
<!-- END DM034_2 -->
