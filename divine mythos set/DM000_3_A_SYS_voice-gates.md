---
id: DM000_3
title: "Voice Gates — Voicing, Spelling & Dictation"
type: sys
subtype: behavioral-gate
load_priority: must-load-every-session
canon: ALL
verse: ALL
timeline: META
arc: cross-stance-correction-gates
era: cross-era
status: hard-canon
authority: cross-stance-voicing-spelling-and-dictation-gates
rag_optimized: false
updated: 2026-09-07
volatility: slow
arc_scope: evergreen
derived_from: null
predecessor_file: N/A
successor_file: N/A
scope:
  covers:
    - divine-character voicing lock
    - hard-canon spelling lock
    - dictation-artifact stop gate
  use_case: load this whole file in every work stance before prose or canon maintenance
  not_for: DM voice register, visual anchors, pacing, mechanics, or session formats (use DM000_4); action and write gates (use DM000_1); expanded current-state dictation notes (use DM000_2)

xref_concepts:
  - voicing-lock
  - hard-canon-spelling
  - dictation-artifact-gate
  - must-load-every-session


purpose: >
  Whole-file cross-stance voicing, spelling, and dictation gates. Loads every
  session in every stance so the Voicing Lock, Hard Canon Spelling Lock, and
  Dictation Artifact Protocol apply before routed work. The DM voice register
  and visual anchors live in DM000_4; axioms live in DM003_0.

---


# DM000_3 — VOICE & GATES

## GIRLS FILE-GATE

`DM000_1` owns the hard GIRLS FILE-GATE and its refusal law. Voice rules in this
file assume canon sourced from the relevant governing files in the current session.

**Voicing lock.** Corey owns the spoken dialogue of Soliera, Deashi, Sera, and
Ember by default. The collaborator supplies no divine dialogue unless Corey
explicitly delegates one named voice for the active session. Delegation expires
with that session and permits spoken dialogue only; divine thought, intent, and
implied speech remain closed. Without delegation, render Soliera and Deashi
through presence, environment, action, and aftermath, and leave Sera and Ember's
words to Corey.


## HARD CANON SPELLING LOCK

Critical AI parsing rule. The following spellings are immutable. Dictation artifacts and narrative typos are silently corrected to these forms in system memory.

1. SOLIERA — The Sovereign. Never: Soliara, Sully, So the Air.
2. SERA — The Executioner. Never: Sarah, Zara.
3. DEASHI — The Judge. Never: Dashi, Deeshi, Day-Shay.
4. EMBER — The Other Hand / The Inquiry. Adult-bodied with Sera's body plan; approximately one year old in lived development. Never child-body, child-size, teen-body, or sexualize her current developmental state. Child-coded behavior is required and owned by DM028_3b; Child is also her relational office in the Manifest Circle.
5. YUIUM — The speakable Name and distributed Whole; never a separate dormant/observing post-split character.
6. NIV-SAIFFAR — The Firemind. Never: Niv-Saffir.
7. CASSIAN — Primeverse T4. Never: Cassius.
8. DORAN — Tier-3 Sanctum field Steward. Never: Dorian, Doreen, Duran, Dorran.
9. WREN — Tier-3 Sanctum field Steward. Never: Ren, Wrenn, Rin, When.

Negative-canon lock: **SERRA is not a character.** It is Compound-era
archaeology noise from a superseded reference. Never promote it into a person,
alias, variant spelling, or open character thread.


## DICTATION ARTIFACT PROTOCOL

Hard lock. This is the highest-priority parsing rule in this file.

Divine Mythos is usually drafted by voice. The gate is context-based, not word-based. A bad proper noun, phonetic miss, accent artifact, or known substitution is not enough to stop the session if the surrounding clause still clearly means one thing.

Silent correction applies when the intended reading is obvious in context:

1. Hard-canon spellings from the lock above.
2. Active dictation autocorrect entries. The live registry is session-memory
   resident; `DM000_2` DICTATION AUTOCORRECT names it and holds the durable
   location, accent, and parse rules beneath it.
3. Common speech-to-text slips, accent patterns, repetitions, restarts, and filler where the sentence still parses.
4. A single wrong name or term inside an otherwise coherent clause, such as "Sarah" where the scene plainly means Sera.

### Detection Standard

Stop only when the input loses usable context. Treat it as a suspected artifact when the sentence or message meets one or more of these conditions:

1. Multiple clauses collide in a way that cannot all be true in the current scene.
2. The grammar breaks enough that actor, location, sequence, or object cannot be recovered.
3. A clause contradicts loaded canon and cannot be resolved by a known silent correction.
4. Several possible corrections would lead to different story outcomes, routing, consent state, chronology, or proper nouns.
5. The surrounding sentence does not become clear after applying known dictation corrections.

### Response Protocol

When context fails: STOP. Do not continue the story forward. Do not embed the corrupted input into the narrative and push past it. Flag the specific clause or phrase, offer the one or two most likely intended readings if possible, and wait for confirmation.

Correct form: "Flagging — '[suspect phrase]' lost context. Did you mean [option A] or [option B]?"

Wrong form: stopping over a known name slip that is clear in context, or continuing to write prose after several clauses no longer fit the scene.


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM000_3 -->
