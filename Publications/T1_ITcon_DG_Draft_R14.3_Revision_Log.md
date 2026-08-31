---
type: revision-log
paper: T1
round: R14.3 (in place)
date: 2026-08-31
artifact: Publications/T1_ITcon_DG_Draft_R14.3.docx
source_package: Publications/T1_ITcon_DG_Draft_R14.4.docx (S1-S4)
comments_addressed: [C45, C46, C55, C75]
status: complete
edits: {applied: 17, by_agent: 15, by_author: 2, superseded: 3, paragraphs: [56, 79, 99, 107, 109, 111, 147, 333, refs]}
vault_note: DG_OBSIDIAN/dissemination/revisions/T1 R14.3 - R14.4 package port and C45 resolution.md
---

> **R14.3 Revision Log.** Working change list for the 2026-08-31 R14.4-package port and C45
> resolution, kept in the form it was executed from: per-edit find/replace text, Ctrl+F navigation
> tables, verification results, and recorded author decisions.
>
> **PART 2 is marked SUPERSEDED and must not be executed.** It is retained because the reasoning
> that retired it — a Design State trail is partitioned rather than linear, and reformulation
> redefines a state space rather than linking two states — is the substance of this round. PART 1
> and PART 3 are what was applied.
>
> Narrative summary: `DG_OBSIDIAN/dissemination/revisions/T1 R14.3 — R14.4 package port and C45 resolution.md`

---

# Porting the R14.4 fix package into T1_ITcon_DG_Draft_R14.3.docx — S2 + C45 applied

## Context

`R14.3` and `R14.4` diverged. `R14.4` (2026-08-30) holds the approved fix package for
`AU-R143-C02` / C45; `R14.3` (2026-08-31) holds the 89 tone edits and **none** of that package.
The author asked for one piece of it — **S2**, the Function–Behaviour–Structure ↔ Design State
mapping in § 3.3 — brought into `R14.3` in the register the tone pass established.

S2 comes first for a reason. Per the R14.4 summary: *"S3's derivation rule is only legible once
the mapping is stated."* R14.3's § 3.3 currently lists the three state kinds without saying which
FBS role each holds, so the § 6.1 material cannot be ported until this is in place.

No new revision file, no supporting files. The change list below was produced first for manual
insertion; M0 and M1 were applied by the author, M2–M4 by agent on request.

Target: `Publications/T1_ITcon_DG_Draft_R14.3.docx`
Locations are given as `[Pnn]` = paragraph index in the accepted-changes view, with an
anchor phrase to Ctrl+F in Word.

**Read-first caveat:** the file holds 161 unaccepted tracked changes (all authored
`Scientific Paper Revision Agent`) and 57 comment anchors. Every quotation below is from the
*all-insertions-accepted* text. `python-docx` alone silently omits `w:ins` runs, so text read that
way looks truncated — the quotations here were taken from the XML including insertions.

**Numbering note:** `[P79]` follows this file's and `zippy-purring-dawn.md`'s scheme (body
paragraph index). The R14.4 revision summary numbers the same paragraph **¶158** on a full-XML
count that includes table cells. Same paragraph, two schemes.

---

## EXECUTION STATUS — applied 2026-08-31

**All 5 edits are applied. `Publications/T1_ITcon_DG_Draft_R14.3.docx` was modified in place.**

| | |
|---|---|
| M0, M1 | **FIXED by the author**, with reworded M1 (see *Register notes*) |
| M2, M3, M4 | **FIXED by agent** via `paper-revision/scripts/docx_replace.py`, 3/3 matched as declared |
| Scope | § 3.3 `[P79]` only — full-document diff confirms **P79 is the only paragraph changed** |
| Not included | S1 (§ 2.2), S3 (§ 6.1), S4 (Figure 5) — see *Carried forward* |
| Pre-edit backup | `…\scratchpad\R14.3_BACKUP_before_S2_port.docx` (5 376 669 bytes) |

**Verified after write:** 31 package parts unchanged · 141 `w:ins` / 14 `w:del` preserved ·
56 comments and 56 comment references preserved · opens cleanly (212 paragraphs, 6 tables) ·
`rather than` in `[P79]` still 4 (no new contrast) · `ObjState`/`ParamState`/`PropState` counts
unchanged.

**Validation:** the one `[FAIL] table-numbering` and one `[WARN] table-cited` are **pre-existing** —
identical in the backup, and unrelated to this edit.

---

## Register adaptation

R14.4's S2 wording predates the 2026-08-31 tone pass, so two patterns were removed before
transplanting it:

| R14.4 original | Pattern | Resolution |
|---|---|---|
| `…which is what allows a sequence of them to be read as design movement` | cleft emphasis — pass cut 12 → 1 | → `…so a sequence of them records…` |
| `…as design movement rather than as successive versions` | `rather than` — `[P79]` already carries 4 | dropped; the foil is unnecessary once the positive statement stands |

`records the route a scheme travelled` is taken from R14.4's own § 6.1 ¶284, so a later S3 port
stays consistent with itself.

R14.4's separate tweak `a neutral reference to its geometry` is **not** carried — it is not part of
the mapping and would widen the diff.

---

## Edits

### M0 — [P79] `everything that determines it at a given (Figure 5)` — **STATUS: FIXED (author)**
→ `everything that determines it at a given moment (Figure 5)`
*Reason:* prerequisite, not cosmetic. The tone-pass insertion ends at `at a given ` and dropped
`moment`; R14.4 has it intact. **M2 below says "at that moment" and has no antecedent until this
is fixed.** The sentence currently reads *"…determines it at a given (Figure 5)."*

### M1 — [P79] `It comprises three kinds of states.` — **STATUS: FIXED (author, reworded)**
→ *proposed:* `It comprises three kinds of states, and between them they carry the three roles of the core band.`
→ **as applied by the author:** `It comprises three types of states, which together fulfill the three roles of the core band.`
*Reason:* R14.4 `S2a`. Announces the mapping before the three clauses that carry it, so each role
assignment below reads as part of one statement. The author's rewording preserves this function;
see *Register notes* for the one spelling consequence.

### M2 — [P79] `The ObjState binds the object and a reference to its geometry;` — **STATUS: FIXED**
→ `The ObjState binds the object and a reference to its geometry, holding the Structure as realised at that moment;`
*Reason:* R14.4 `S2b`. Assigns **Structure**. Depends on M0.

### M3 — [P79] `the data property it constrains, and the observed value.` — **STATUS: FIXED**
→ `the data property it constrains, and the observed value, and so holds the Function the object is required to fulfil.`
*Reason:* R14.4 `S2c`. Assigns **Function**. Match the occurrence in the PropState clause — the
later `one PropState per rule, property and observed-value triple` is different wording and is not
a target.

### M4 — [P79] insertion before `A validation Run consumes such a snapshot` — **STATUS: FIXED**
→ insert, as a new sentence directly after the PropState sentence amended by M3:
`A Design State is in this sense a Function–Behaviour–Structure triple resolved at a single moment, so a sequence of them records the route a scheme travelled.`
*Reason:* R14.4 `S2d`, de-clefted and with the `rather than` foil dropped. States the triple once,
which is what § 6.1's derivation rule later depends on. En-dashes in
`Function–Behaviour–Structure`, as elsewhere in the paper.

### No edit — Behaviour was already assigned
`[P79]` already carried the Behaviour role: `the sliders, toggles, and value inputs of the
Behavio(u)r`. The R14.4 summary notes the paper *"already asserted one third of it."* The author
additionally changed this instance `Behavior` → `Behaviour` while applying M0/M1 — see
*Register notes*.

---

## Navigation

`P79` is **not** a Word feature. It is the paragraph's ordinal position in the document body,
used here only to give each edit a stable label. `Ctrl+G` (Go To) cannot reach it — it offers
page, section, line and bookmark only.

**Navigate by anchor phrase instead.**

1. **First, switch off markup display:** Review → Display for Review → **No Markup**.
   The file holds 161 pending tracked changes. Under *All Markup*, deleted text is shown inline,
   which splits phrases and makes `Ctrl+F` miss. *No Markup* renders the accepted-changes text —
   exactly what the anchors below were taken from.
2. `Ctrl+F`, paste the anchor, Enter.
3. For the section jump use the Navigation pane's **Headings** tab (`Ctrl+F` then Headings):
   **3.3 Design State: the unit of lifecycle traceability**.

| P | Section | Ctrl+F anchor (paragraph opening) |
|---|---|---|
| P78 | 3.3 Design State | `3.3 Design State: the unit of lifecycle traceability` *(heading)* |
| P79 | 3.3 Design State | `The Design State is the second entity introduced by the schema itself` |

All five edits sit in the single paragraph `P79`. Within it, Ctrl+F these in order:

| Edit | Ctrl+F within P79 |
|---|---|
| M0 | `at a given (Figure 5)` |
| M1 | `It comprises three kinds of states.` |
| M2 | `binds the object and a reference to its geometry;` |
| M3 | `the data property it constrains, and the observed value.` |
| M4 | `A validation Run consumes such a snapshot` *(insert before)* |

Apply **M0 → M4 in order**. M1–M3 each extend a phrase rather than replace it, so applying them
out of order still works, but M0 must precede M2 for the anaphor to read.

---

## Register notes — two spelling consequences of the applied wording

Both arise from the author's M0/M1 pass, not from M2–M4. Neither is fixed — recorded for decision.

**1. `fulfill` / `fulfil` — ✅ RESOLVED by the author** (file mtime 2026-08-31 17:54).
`[P79]` now reads `which together fulfil the three roles`. Document-wide: `fulfil` 4, `fulfill` 0.

**2. `Behavior` is now the lone US spelling in the paper.** After the author's change to `[P79]`,
counts are `Behaviour` 9, `Behavior` 1. The remaining instance is `[P64]`:
`An Object carries Behavior, the generative, parametric…`. `[P38]` lists the core-band classes as
`Object, Function, Behaviour, Structure` and `[P157]` reads `retaining Behaviour and Structure on
the Object`, so the paper's prose already treats these entity names as British and `[P79]` now
matches them. Fix would be `[P64]` `Behavior` → `Behaviour`.

*Caveat for both:* the Neo4j node label is `Behavior` (US) per `CLAUDE.md`, so prose and schema
label diverge by design. This is a prose-consistency call, not a schema one.

---

## Verified after insertion

1. `[P79]` reads `at a given moment (Figure 5)` — word restored, single spaces either side. ✅
2. Three role assignments present and distinct: ObjState → **Structure**, ParamState →
   **Behaviour** (pre-existing), PropState → **Function**. ✅
3. The triple sentence sits between the PropState sentence and `A validation Run consumes…`. ✅
4. No new `rather than` in `[P79]` — the count in that paragraph stays at 4. ✅
5. Terminology unchanged: `ObjState` 3, `ParamState` 2, `PropState` 2, `Design State`. ✅
6. Nothing edited outside `[P79]` — full-document paragraph diff returns `[79]` only. ✅

---

## PART 2 — C45: S1 + S3 — ⚠️ SUPERSEDED BY PART 3

**Do not execute this part.** It was drafted before the author's correction that a Design State
trail is not linear. Its S3b derivation rule is unsound; see PART 3 for why and for the replacement.
Retained only as the reasoning trail.

### Why

`C45` — Evgenii Ermolenko, 2026-08-26, anchored to *"the situated-FBS process model, with its
formulation and reformulation cycle, is not represented"* — reads:
**"Why not presented? It should be presented now, check other sections."**

Checking the other sections, as asked, finds the paper making three different claims:

| Section | Current claim |
|---|---|
| **§ 2.2** `[P56]` | `the situated-FBS process model … is not represented` ← the anchor |
| **§ 3.3** `[P79]` | `a sequence of them records the route a scheme travelled` ← added by PART 1 |
| **§ 6.1** `[P147]` | `describes the movement that Design States already record as data … the schema keeps the trail without naming the process that produced it` |

§ 2.2 is the only false one. **PART 1 sharpened the contradiction** — § 3.3 now positively asserts
the movement record, so § 2.2's denial is contradicted two sections later.

### What the implementation supports — verified, not assumed

- **The trail is real data.** `CapturedAtUtc` is a required, validated ISO-8601 timestamp on every
  Design State — `DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs:56-64`,
  `DesignStatePayloadV2Serializer.cs:71`. The `DS_t0 … DS_tn` series is orderable, not rhetorical.
- **Transition semantics do not exist.** No `PRECEDES` / `NEXT_STATE` / `PREVIOUS_STATE` /
  `DERIVED_FROM` / `REFORMULATES` / `FOLLOWS` edge or property anywhere in the schema. Nothing
  distinguishes a state reached by refinement from one reached by reframing.

The paper may therefore claim the **trail** as held, and must not claim the **process labelling** as
implemented. R14.4's S3 respects that line: it presents the labelling as a derivation the schema
*admits* — `Naming that route takes a single addition` — and grounds the derivation in data that
already exists (`PropState`, `ObjState`, `ParamState` per state). No new capture is implied.

**Correction to an earlier assessment in this session.** It was first stated that the stronger
reading was "not honestly available" because no transition edge exists. That was true of the
*implemented* schema and wrong about what the paper can *specify*: S3 claims no edge, only a
derivable relation. S3 is available and honest.

**Author decision recorded:** **S1 + S3** — the full C45 answer as R14.4 framed it.
Deciding evidence: R14.4's threaded reply to `AU-R143-C02` states *"Justified in section 2.2 and
specified in section 6.1"* — S1 is the justification, S3 the specification. That reply is **absent
from R14.3** (grep count 0), so without S3 it would overstate this document.

### Interaction with the C46 fix already applied

`[P56]` already carries the author's C46 fix: `Three of these boundaries — generated vocabulary,
IFC alignment, and movement between Design States — are developed in section 6.1…`. Two
consequences:

1. R14.4's S1 clause ends `, developed in section 6.1` — **dropped here as redundant**, since the
   C46 sentence three clauses later already routes this item to § 6.1.
2. The C46 label `movement between Design States` is **correct as it stands** and needs no change.
   S3 relabels § 6.1's third item from `The third concerns process.` to `The third concerns
   movement.`, so the two sections match. An earlier draft of this plan proposed rewording § 2.2 to
   `the process behind that movement` — **dropped**, since it would break that match.

### Edits

#### S1 — [P56] `On the absorbed side, what FBS contributes is the three-way decomposition of design  — the situated-FBS process model, with its formulation and reformulation cycle, is not represented — and what DCM contributes is the Body→Head criterion form together with the semantic, topological and geometric split.` — **STATUS: PLANNED**

→ `On the absorbed side, what FBS contributes is the three-way decomposition of design, and from the situated extension (Gero & Kannengiesser, 2004), which treats designing as movement, the schema takes what its own data sustains — the sequence of states that movement passes through — while the designer's interpretation of those states belongs to protocol study. What DCM contributes is the Body→Head criterion form together with the semantic, topological and geometric split.`

*Reason:* R14.4 `S1`. Replaces the denial with what the schema takes, plus a permanent scope
boundary (interpretation → protocol study) that is a real limit rather than an open question.
Resolves the three-way contradiction and answers *"check other sections"*.

*Side effects:* fixes the double space in `design  —`; splits one over-long sentence at
`What DCM contributes`, matching R14.4.

*Register:* no negation-led framing, no `rather than`, no intensifier. The `what X contributes is`
clefts are **pre-existing in both R14.3 and R14.4** and are left alone — rewriting them is not part
of C45.

*Citation:* `Gero & Kannengiesser, 2004` is already in the reference list `[P178]` and cited at
`[P64]` and `[P147]`. No bibliography change.

#### S3a — [P147] term alignment with § 2.2 — **STATUS: PLANNED**

- **old:** `Three of the exclusions recorded in section 2.2 are open questions rather than settled boundaries.`
- **new:** `Three of the boundaries recorded in section 2.2 are open questions rather than settled limits.`

*Reason:* two mismatches, both created by the applied C46 fix. § 2.2 now says `Three of these
boundaries`, while § 6.1 says `exclusions` for the same three **and** uses `boundaries` for what
they are *not*. `exclusions` → `boundaries` matches § 2.2; `settled boundaries` → `settled limits`
frees the word. R14.4 uses both of these terms. The existing `rather than` is pre-existing and left
in place.

#### S3b — [P147] the derivation rule — **STATUS: PLANNED**

- **old:** `The third concerns process. FBS is absorbed here as a structural decomposition, yet the situated-FBS framework's formulation and reformulation cycle (Gero & Kannengiesser, 2004) describes the movement that Design States already record as data: a scheme that is reformulated leaves a trail of states, and the schema keeps the trail without naming the process that produced it. Representing that process allows the graph to distinguish between a state reached through refinement and one achieved through reframing — a distinction discussed in the co-evolution literature. (Schön, 1992; Poon & Maher, 1997; Dorst & Cross, 2001; Dorst, 2011).`

- **new:** `The third concerns movement. The situated extension of FBS (Gero & Kannengiesser, 2004) treats designing as movement between states, and section 3.3 has already established what the schema holds at each: a Design State resolves Function, Behaviour and Structure at one moment, so a sequence of them records the route a scheme travelled. Naming that route takes a single addition — a typed relation between successive Design States — and the type follows from the states themselves. Where the PropState differs, the Function has been recast, which is reformulation in the framework's sense; where the ObjState or ParamState differs while the Function holds, the scheme has been refined within it. The co-evolution literature treats that distinction between reframing and refinement as central (Schön, 1992; Poon & Maher, 1997; Dorst & Cross, 2001; Dorst, 2011), and the schema reaches it from what it already keeps. Two boundaries give such a relation its shape: it describes movement between the moments an architect chose to validate, at the granularity of those checkpoints, and it reaches the framework's external world in the authoring model and its expected world in the rules, while the designer's interpretation of either belongs to protocol study.`

*Reason:* R14.4 `S3`. Turns the possibility into a specified derivation, which is the half of the
reply that S1 does not deliver. Depends on PART 1 — the sentence `section 3.3 has already
established what the schema holds at each` is only true because S2 is applied.

*Register adaptation:* R14.4 reads `That distinction between reframing and refinement is the one the
co-evolution literature treats as central` — a specificational cleft. Rewritten active:
`The co-evolution literature treats that distinction … as central`. Everything else is R14.4's
wording unchanged. The closing line `Each is a direction the schema admits rather than a commitment
it makes.` is **already identical** in R14.3 and is not touched.

*Side effect:* fixes a punctuation defect — R14.3 currently reads `co-evolution literature. (Schön,
1992; …).`, with a stray full stop before the citation.

*Citations:* `Schön, 1992; Poon & Maher, 1997; Dorst & Cross, 2001; Dorst, 2011` are all already
present in this same sentence. No bibliography change.

*Accepted repetition:* both S1 and S3 end on `the designer's interpretation … belongs to protocol
study`. R14.4 ships this deliberately — its reply says the two boundaries are *"stated rather than
left for a reader to find"*. Kept for fidelity; flagged so it is a choice, not an oversight.

### Navigation — PART 2

Same procedure as PART 1: **Review → Display for Review → No Markup** first, then `Ctrl+F`.

| P | Section | Ctrl+F anchor (paragraph opening) |
|---|---|---|
| P56 | 2.2 Conceptualisation | `Figure 2 maps external knowledge sources onto the schema` |
| P147 | 6.1 (open questions) | `Three of the exclusions recorded in section 2.2` |

| Edit | Ctrl+F within the paragraph |
|---|---|
| S1 | `On the absorbed side, what FBS contributes is` |
| S3a | `Three of the exclusions recorded in section 2.2` |
| S3b | `The third concerns process.` |

Apply **S3a before S3b** — S3a rewrites the sentence S3b's paragraph opens with, and doing it second
risks matching text S3b has already replaced.

### Method

`~/.claude/skills/paper-revision/scripts/docx_replace.py --from-json`, `--dry-run` first, applied to
a temp file, `validate_docx.py`, then moved over `R14.3.docx`. Backup to scratchpad first, as in
PART 1.

### Verification

1. Dry run reports **1/1** for all three edits (S1, S3a, S3b); nothing written on any mismatch.
2. `[P56]`: no `is not represented`; no `  —` double space.
3. `[P147]`: no `exclusions`; no `settled boundaries`; no stray `literature. (Schön`.
4. Full-document paragraph diff returns **`[56, 147]` only**.
5. Preservation vs backup: 31 parts, `w:ins` 141, `w:del` 14, comments 56, commentRefs 56.
6. `validate_docx.py` shows only the two **pre-existing** table findings, byte-identical to backup.
7. **Cross-section consistency re-read** — the point of the whole change. §§ 2.2, 3.3 and 6.1 must
   make one claim: the trail is held data; the process label is a derivable addition, not a
   capability. No section may say the movement is unrepresented.
8. Third-item label matches across sections: § 2.2 `movement between Design States` ↔ § 6.1
   `The third concerns movement.`
9. `Gero & Kannengiesser, 2004` in-text count 2 → 3. Co-evolution citation group still appears
   exactly once.
10. No new `rather than` beyond those already counted in each paragraph.

---

## PART 3 — C45 revised: the trail is partitioned, not linear

### Two author corrections that reset this part

1. **T1 fixes a project stage at which no implemented system exists.** The paper is the foundation
   for future changes to the real ontology schema, so it need not match the implemented ontology.
   Specifying schema structure ahead of implementation is its job. The only thing it must not do is
   claim *deployment* status — which R14.4's own reply already honours
   (*"No ontology version was created and no deployment status is claimed"*).
2. **A Design State trail is not necessarily forward or backward.** States may be alternatives
   within one design space; they may belong to different design spaces (facade design vs plan layout
   of the same building); and within one object a design space may divide by typology (a hexagonal
   glazed facade set beside a timber structural facade set).

Correction 1 **removes** the objection this plan raised earlier (unimplemented ⇒ unclaimable).
Correction 2 **invalidates S3b**, which is a stronger objection than the first one relieved.

### Why S3b is unsound — two independent reasons

**(a) It presumes a linear order the data does not carry.** S3b types "a typed relation between
**successive** Design States". Under correction 2 there is no single successor; states form a
partitioned collection, not a chain. `CapturedAtUtc` gives a total time order, but time-ordering two
facade alternatives does not make them a movement.

**(b) It misreads what reformulation is.** Verified against the framework literature
(Gero & Kannengiesser; Gero's reformulation types 1–3): **reformulation redefines a state space**
— `S→S'`, `S→Be'`, `S→F'` — it does not connect two members of one space. So a pairwise diff of two
Design States cannot separate *"an alternative admitted by the current Function space"* from
*"the Function space was recast"*. S3b's rule — `Where the PropState differs, the Function has been
recast` — reads the first case as the second. This is a defect in the rule itself, not only in the
word "successive".

Established terminology for the missing structure (same sources): **design space** and **design
sub-space**; **alternative set** (mutually exclusive, one selected) vs **variant set** (retained in
parallel); **partitioned design space by typology** (`DS = ⋃ᵢ DSᵢ`); **design trajectory** for the
temporal axis. The literature's own summary is *branching in space* vs *movement in time*.

### The series constraint — decisive, and it was missed

`DG_OBSIDIAN/dissemination/Series coherence map.md` allocates concepts across the four ITcon papers:

| Concept | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| OntoGraph/Metagraph schema | **defines** | ref | ref | ref |
| DesignStateSnapshot | — | — | **defines** | ref |
| ValidationRun / ValidationEntity | — | — | **defines** | ref |
| REINSTATE component | — | — | **defines** | ref |
| DesignSpaceGraph, MetricSpec | — | — | — | **defines** |

- **T3** *(Design State Tracking and Longitudinal Validation)* owns state tracking, and its case
  study is `3 массы alternatives (Alt A, B, C), 9 runs` with **`REINSTATE для нелинейной
  навигации`** — non-linear navigation is already T3's stated subject.
- **T4** *(Design Space Analysis, Generation and Prediction)* owns the design space itself:
  `Σ = collection of DesignSpacePoint`, the `DesignSpaceGraph` fourth layer, partitioning, metrics.
- T1's own row for Design State is a **dash**, and the case-study matrix lists T1 `States: —`.

So the design-space structure correction 2 describes **is T4's contribution**, and non-linear state
navigation **is T3's**. T1 must not formalise either. Note also that R14.3 currently carries a whole
§ 3.3 on Design State, which already sits beyond the map's original allocation — worth a separate
decision, out of scope here.

**Vocabulary check on R14.3:** `design space` 0 · `variant` 0 · `branch` 0 · `non-linear` 0.
`alternative` appears twice, both unrelated (modelling alternatives; Table 7 approaches). T1 has no
design-space vocabulary to build on, which confirms that introducing it belongs elsewhere.

**Citation mechanism:** T1 has exactly one self-citation — `(Ermolenko et al., 2026)`, a precedent
ptBIM conference paper `[P28, P173]`. No `2026a–d` codes, no `companion`, no `forthcoming`. So a
forward reference to T3/T4 would be a **new** apparatus, not an existing one. See the open question.

### What the honest answer to C45 now is

T1 defines the **unit** — a Design State as an FBS triple resolved at one moment. Typing *movement*
between states requires one thing T1 can legitimately name as a prerequisite without formalising it:
**which design space and partition a state belongs to**. That is a schema requirement, which is
exactly the register correction 1 licenses, and it hands the formalisation to the companion work
rather than performing it.

This is a better contribution than S3b's rule: instead of a derivation that is wrong, § 6.1 states
the *precondition* for any such derivation.

### Edits

#### E1 — [P79] § 3.3 — repair the single-route clause introduced by PART 1 — **STATUS: FIXED**

- **old:** `A Design State is, in this sense, a Function–Behaviour–Structure triple resolved at a single moment, so a sequence of them records the route a scheme travelled.`
- **new:** `A Design State is, in this sense, a Function–Behaviour–Structure triple resolved at a single moment. A collection of them therefore records the configurations a scheme has occupied, whether these follow one another in time or stand beside one another as alternatives.`

> **Find-string note:** the author re-punctuated this sentence to `is, in this sense,` after PART 1
> was applied (file mtime 2026-08-31 17:54). The comma form above is verified against the live file;
> the uncomma'd form matches **0** times.

*Reason:* `the route a scheme travelled` asserts one trajectory and is wrong under correction 2.
This clause came from PART 1 (M4, R14.4's S2d), so PART 1 must be corrected too — the FBS mapping
itself (ObjState→Structure, ParamState→Behaviour, PropState→Function) is unaffected and stands.

#### E1b — [P79] § 3.3 — the pre-existing linearity claim — **STATUS: FIXED**

- **old:** `the graph accumulates an ordered series DS_t0 … DS_tn that can be compared, replayed, and selectively reinstated`
- **new:** `the graph accumulates a collection DS_t0 … DS_tn whose members can be compared, replayed, and selectively reinstated`

*Reason:* pre-existing R14.3 text, brought into scope by E1. `an ordered series` asserts a single
chain; after E1 the same paragraph says states may `stand beside one another as alternatives`, so
leaving it would put a contradiction three sentences apart inside one paragraph. Author decision
recorded: **fix it**. The `DS_t0 … DS_tn` notation is kept — it names members, not an order.

#### E2 — [P56] § 2.2 — S1, revised for non-linearity — **STATUS: FIXED**

- **old:** `On the absorbed side, what FBS contributes is the three-way decomposition of design  — the situated-FBS process model, with its formulation and reformulation cycle, is not represented — and what DCM contributes is the Body→Head criterion form together with the semantic, topological and geometric split.`
- **new:** `On the absorbed side, what FBS contributes is the three-way decomposition of design, and from the situated extension (Gero & Kannengiesser, 2004), which treats designing as movement between state spaces, the schema takes the state as its unit of record: each Design State is a triple resolved at one moment. Typing the movement between states is treated in section 6.1. What DCM contributes is the Body→Head criterion form together with the semantic, topological and geometric split.`

*Reason:* resolves C45's contradiction as S1 did, but drops R14.4's `the sequence of states that
movement passes through`, which carries the same linearity presumption as S3b. `movement between
state spaces` is the framework's own formulation. Also fixes the `design  —` double space.

#### E3a — [P147] § 6.1 — term alignment with § 2.2 — **STATUS: FIXED**

- **old:** `Three of the exclusions recorded in section 2.2 are open questions rather than settled boundaries.`
- **new:** `Three of the boundaries recorded in section 2.2 are open questions rather than settled limits.`

*Reason:* unchanged from S3a — § 2.2 says `boundaries` after the author's C46 fix, while § 6.1 says
`exclusions` for the same three and uses `boundaries` for what they are not.

#### E3b — [P147] § 6.1 — the precondition, replacing S3b's derivation rule — **STATUS: FIXED**

- **old:** `The third concerns process. FBS is absorbed here as a structural decomposition, yet the situated-FBS framework's formulation and reformulation cycle (Gero & Kannengiesser, 2004) describes the movement that Design States already record as data: a scheme that is reformulated leaves a trail of states, and the schema keeps the trail without naming the process that produced it. Representing that process allows the graph to distinguish between a state reached through refinement and one achieved through reframing — a distinction discussed in the co-evolution literature. (Schön, 1992; Poon & Maher, 1997; Dorst & Cross, 2001; Dorst, 2011).`

- **new:** `The third concerns movement. The situated extension of FBS (Gero & Kannengiesser, 2004) treats designing as movement between state spaces, and section 3.3 has established what the schema holds at each moment: a Design State resolves Function, Behaviour and Structure. Typing the movement between two such states asks one further thing of the schema — the design space each state belongs to. States accumulate in partitions as much as in succession: one set may hold facade alternatives while another holds plan layouts of the same building, and a facade set may divide again by typology, a hexagonal glazed pattern in one partition and a timber structural system in another. A comparison between two states within one partition therefore carries a different meaning from a comparison across partitions. Reformulation in the framework's sense redefines a state space, and so appears as a change of partition; refinement is movement within a partition, leaving its Function intact. Recording partition membership on the state is the addition this direction asks for, and it is what would let the graph carry the distinction between reframing and refinement that the co-evolution literature treats as central (Schön, 1992; Poon & Maher, 1997; Dorst & Cross, 2001; Dorst, 2011).`

*Reason:* states the precondition instead of a derivation that a pairwise diff cannot support.
Uses the author's own two examples (facade vs plan; hexagonal glazed vs timber structural) so the
partition idea is concrete without importing T4's formal apparatus — no `DesignSpaceGraph`, no
`MetricSpec`, no `DesignSpacePoint`.

*Register:* no `rather than` added; `Reformulation … redefines a state space, and so appears as a
change of partition` replaces the contrast form. Negation-led framing avoided throughout — the
paragraph says what the addition *is*, not what the schema lacks.

*Two-boundaries sentence — correction:* an earlier draft of this plan said it was "retained" from
R14.3. It is **not in R14.3 at all** (verified: 0 matches); it exists only in R14.4. It is therefore
**added** by E3b, as the final clause of the new text above:

> `Two boundaries give such a relation its shape: it describes movement between the moments an architect chose to validate, at the granularity of those checkpoints, and it reaches the framework's external world in the authoring model and its expected world in the rules, while the designer's interpretation of either belongs to protocol study.`

Worth adding because it bounds the claim, and because E2 no longer carries the protocol-study limit
into § 2.2 — this becomes its only statement. `such a relation` anaphors to
`Typing the movement between two such states` earlier in the paragraph.

R14.3's existing final line `Each is a direction the schema admits rather than a commitment it
makes.` follows it and is untouched.

*Side effect:* fixes the stray full stop in `co-evolution literature. (Schön, 1992; …)`.

### Method and verification

As PART 1: backup, `docx_replace.py --from-json --dry-run`, apply to temp, `validate_docx.py`,
paragraph-diff, then move over `R14.3.docx`.

**Author decisions recorded for PART 3:**

| Decision | Choice |
|---|---|
| Handoff of the design-space formalisation | **No companion citation** — kept as an open direction in § 6.1. T1's single self-citation apparatus is left untouched. |
| Pre-existing `ordered series` linearity claim | **Fix** — E1b. |

**PART 3 EXECUTION STATUS — applied 2026-08-31 18:31. All five edits FIXED by agent** via
`docx_replace.py`, 5/5 matched as declared. Backup: `…\scratchpad\R14.3_BACKUP_before_PART3.docx`
(5 376 828 bytes). Verified: 31 parts · `w:ins` 142 · `w:del` 13 · comments 58 · commentRefs 58 —
all unchanged · paragraph diff `[56, 79, 147]` exactly · PART 1's FBS mapping intact · no T4
vocabulary and no forward reference introduced · `Gero & Kannengiesser, 2004` 2 → 3.
The two `validate_docx.py` table findings are pre-existing, byte-identical to backup.

**Note:** the co-evolution citation group appears **twice** document-wide (`[P47]` § 2.1 and
`[P147]`), unchanged from backup. The plan's "expect 1" was a miscalibrated expectation, not a
defect — `[P47]` is pre-existing and unrelated.

**Five edits: E1, E1b, E2, E3a, E3b.**

1. Dry run reports **1/1** for all five.
2. Paragraph diff returns **`[56, 79, 147]`** only.
3. Preservation vs backup: 31 parts, `w:ins` 141, `w:del` 14, comments 56, commentRefs 56.
4. `[P79]` contains neither `the route a scheme travelled` nor `an ordered series`; the three FBS
   role assignments from PART 1 survive intact.
5. `[P56]` contains no `is not represented`; no `  —`.
6. `[P147]` contains no `exclusions`, no `settled boundaries`, no `literature. (Schön`.
7. **No T4 vocabulary introduced** — `DesignSpaceGraph`, `MetricSpec`, `DesignSpacePoint` absent;
   and no forward reference added, per the recorded decision.
8. Cross-section read: §§ 2.2, 3.3, 6.1 make one claim — states are units; relating them needs
   partition membership; **no section asserts a single trajectory**.
9. `Gero & Kannengiesser, 2004` in-text count 2 → 3.

---

## Carried forward — not in this change

- **C46** *"What 3 exclusions?"* — **RESOLVED by the author** in `[P56]`, which now names the three:
  generated vocabulary, IFC alignment, movement between Design States. S3a completes it by aligning
  § 6.1's term.
- **The `AU-R143-C02` reply thread is absent from R14.3** (grep count 0; it exists only in R14.4).
  S1 + S3 make its claims true of R14.3, but the reply itself still does not travel with this
  document. Porting it was offered and **not** selected — so a reply must be written, or the thread
  copied, before R14.3 goes back to the reviewer.
- **S4 (Figure 5)** — not assessed in this session. R14.4's package included it; whether the figure
  needs to show the typed relation S3 now specifies is open.
- **Divergence** — R14.3 and R14.4 remain non-comparable branches. After S1 + S3, three of four
  package items are in R14.3 (S1, S2, S3); S4 remains.
- **`fulfill` / `Behavior` spelling** — see *Register notes*; still unaddressed.
- **Pre-existing, not introduced here:** table captions run 1, 2, 3, 5, 6, 7 — no Table 4;
  Table 6 captioned but never cited.

---

# PART 4 — C55: the repository reference

## Clause

### C55 — Evgenii Ermolenko [2] · 2026-08-23 · § 3 THE DESIGN GRAMMAR ONTOLOGY, `[P99]`

> Add reference to GitHub repository: https://github.com/Erarchitech/design-grammar-system

Anchored to the literal placeholder `reference` in the closing sentence of `[P99]`:
*"…is maintained as a version-controlled, open ontology project (reference)."*

**Kind:** convention (journal guidance decides the form) plus one checked fact (what the repository
is). **Resolution: Applied**, on a different target than the comment names — see *Author decisions*.

## Convention — what ITcon requires

From the ITcon authors' guide (itcon.org/for-authors), verbatim:

- *"The APA 7th edition referencing style must be used."*
- References *"listed in alphabetical order in the section titled 'References.'"*
- *"Include a DOI as a URL whenever available. If no DOI is available, provide a URL for online
  sources."*
- In-text: author–date in brackets.

**Observation, not acted on:** the bundled `Publications/ITcon_template2023.dotx` carries one
example entry — `Turk Z. (1991). Integration of Existing Programs Using Frames, …` — in a pre-APA-7
house style that the current author guide contradicts. The manuscript's 41 existing entries are
already APA 7; the template example is the stale artefact, not the paper.

## Author decisions taken during the round

1. **Sole authorship on the software entry** — `Ermolenko, E.` alone, matching the commit history.
   This keeps `(Ermolenko, 2026)` distinct from `(Ermolenko et al., 2026)`, so neither entry needs
   an `a`/`b` suffix. Had all three authors been credited, both this entry and the existing ptBIM
   entry would have required `2026a`/`2026b`, and every in-text citation of the ptBIM paper with
   them.
2. **A tagged version rather than a bare repository link** — the deposit is tagged `v1.0.1`.
3. **AVAILABILITY `[P333]` rewritten** to carry the citation instead of a bare URL — approved as a
   consequential change under this clause.
4. **Separate deposit repository** — see below. This is why the applied URL is not the one the
   comment names.

## Why the cited URL differs from the comment's

The comment names `Erarchitech/design-grammar-system`, the development repository. Checking what
that repository actually contains found 539 tracked files of the author's Obsidian knowledge vault
and 121 tracked files under `Publications/`, including this manuscript and, in `01_Comments/`,
review files named after their authors. No secrets are tracked. Two consequences were put to the
author:

- an open licence over that repository declares the vault and the drafts openly licensed;
- a reader following the citation lands on the manuscript under review and on another reviewer's
  comments.

The author selected a **separate citable deposit**, which is what the AVAILABILITY paragraph already
promises (*"deposited at an open, citable archive"*). Originals stay in the development repository;
the deposit is a copy.

**Deposit:** https://github.com/Erarchitech/design-grammar-ontology · tag `v1.0.1` · 329 files ·
Apache-2.0 for the services, code and migrations; CC BY 4.0 for `ontology/` and `spec/`, declared in
each ontology header as a `cc:license` triple. Contents follow AVAILABILITY's own enumeration: core
module and catalogue, three alignment extensions, SHACL shape set and disjointness overlay, the four
normative specifications, the rule-shape catalogue, four schema migrations, and the three runtime
services (sources only — build output, IDE caches and dependency trees excluded).

## Facts checked, not assumed

Checked against the deposit itself, after staging, not against the source tree or the draft's prose:

| Claim in the paper | Source of truth | Result |
|---|---|---|
| Table 3 totals 62 / 43 / 68 | unique `owl:Class` / `owl:ObjectProperty` / `owl:DatatypeProperty` IRIs in `ontology/DesignGrammar-V7.owl` | **62 / 43 / 68** — match |
| Table 3 per-layer 18 / 15 / 13 / 12 / 4 | same count split by namespace prefix (`&dg;` `&dgm;` `&dgc;` `&dgv;` `&dgs;`) | **18 / 15 / 13 / 12 / 4** — match |
| Annex C: 9 equivalent-class, 9 subclass, 16 subproperty axioms | `DesignGrammar-standards-extension-V7.owl` | **9 / 9 / 16** — match |
| Annex C: two disjointness axioms | `dg-disjointness.ttl` | **2** — match |
| Annex C: seventeen SHACL node shapes | `dg-shapes.ttl` | **17** — match |
| Repository is public | HTTP fetch of the deposit URL | public; description, licences and tag `v1.0.1` all visible |

**Finding that shaped the deposit:** `ontology/DesignGrammar.owl` — the unversioned file a reader
would take for "the core module" — yields **143 / 38 / 66** and does *not* reproduce Table 3. Only
the `-V7` bundle does. The deposit therefore ships `DesignGrammar-V7.owl`, and its README names that
file explicitly and gives the shell commands to recount both the totals and the layer split, so the
recountability sentence in AVAILABILITY is checkable rather than merely asserted.

## Edits

### E4 — `[P99]` § 3 — the placeholder

**Before:** `…is maintained as a version-controlled, open ontology project (reference).`

**After:** `…is maintained as a version-controlled, open ontology project (Ermolenko, 2026).`

The word *open* is now honest: before this round the repository carried no licence at all.

### E5 — `[P333]` AVAILABILITY — bare URL to citation

**Before:** `…are versioned in the same repository (https://github.com/Erarchitech/design-grammar-system) and will be released under the same licence.`

**After:** `…are versioned in the same deposit (Ermolenko, 2026) and will be released under the same licence.`

`repository` → `deposit` is required, not cosmetic: with the deposit separate, *"the same
repository"* is false.

### E6 — REFERENCES — new entry, between `Eastman…` and `Ermolenko, E., Figueiredo, B., & Azenha, M.`

> Ermolenko, E. (2026). *Design Grammar ontology* (Version 1.0.1) [Computer software]. GitHub.
> https://github.com/Erarchitech/design-grammar-ontology

Title italicised, `[Computer software]` roman and sentence case, `GitHub` as host. Placement follows
APA 9.47 — one-author entries precede multiple-author entries with the same surname. Inserted as a
`Reference`-styled `w:p` cloned from the neighbouring entries' markup, not via a style of its own.

## Verification

1. `docx_replace.py` dry run: **2/2** as declared; then applied 2/2.
2. Reference insertion: `document.xml` grew 367 chars; one paragraph added.
3. Every edited paragraph read back in full — `[P99]`, `[P333]`, and the reference list around the
   insertion point. Order reads Eastman → Ermolenko, E. → Ermolenko, E., Figueiredo, B., & Azenha,
   M. → Farghaly. Correct.
4. `validate_docx.py`: all structural checks pass. The one `[FAIL]` (table caption sequence
   1, 2, 3, 5, 6, 7) and one `[WARN]` (Table 6 uncited) are **byte-identical to the backup's** —
   pre-existing, nothing introduced.
5. Deposit secret scan before publication: no key-shaped strings, no hardcoded credentials.

Backup: `scratchpad/R14.3_BACKUP_before_C55.docx`.

## Carried forward from this part

- **DOI at acceptance.** ITcon asks for a DOI whenever one exists. The deposit is tagged but not yet
  archived. On acceptance, archive `v1.0.1` through Zenodo's GitHub integration and swap the entry's
  URL for the minted DOI. This must happen at proofs, or the reference ships less durable than the
  journal's guidance asks for.
- **Copyright holder.** `LICENSE` reads `Copyright 2026 Evgenii Ermolenko`. This is FCT-funded
  doctoral work at the University of Minho; if the institution holds or shares copyright, that line
  needs to name it. Author's call, unresolved.
- **The licence could be named in AVAILABILITY.** It now reads *"will be released under the same
  licence"*, written when the licence did not exist. Apache-2.0 and CC BY 4.0 are now facts. C55 did
  not ask for this, so the vaguer wording stands unless the author decides otherwise.
- **`structure_rules.json` was excluded** from the deposit deliberately: it carries `mappings`, not
  the rule shapes § 4 describes. `llm/cypher_catalog.json` is the artefact that sentence refers to.

## Out-of-scope observations — NOT acted on

- `ITcon_template2023.dotx` contradicts the current ITcon author guide on reference style.
- The development repository publicly tracks the Obsidian vault and `Publications/`. Route (A)
  removes the paper's dependence on it, but the exposure itself is untouched and predates this
  round.

---

# PART 4 — C75: the six cross-layer bridges merged into one list

## Clause

**C75** — Word comment id 75 · Evgenii Ermolenko [2] · 2026-08-31 · anchored in § 3.2 body `[109]`

> Merge this paragraph description of the other set of bridges with previous 3 bridges, so all
> brdiges are listed in one plase with same status (no implementations status need to be mentioned
> at all)

Three requests: merge the two descriptions (**C75a**), one place and one status (**C75b**), no
implementation status anywhere (**C75c**).

**Resolution: Applied.** Four tracked edits in `[107]`, `[109]` and `[111]`.

## What was checked before writing

| Fact | Source of truth | Result |
|---|---|---|
| Whether the six bridge names appear anywhere else | accepted-text dump of all 385 `w:p` | `ENCODED_AS`, `GROUNDED_IN`, `DERIVED_FROM` occur **only** in `[109]`. `REFERS_TO` also in the Cypher listing `[197]` and cell `[202]`; `ATTRIBUTE_OF` also in `[259]` and `[273]` — none carries status wording, none edited. |
| Whether Table 3 lists bridges | `[113]`–`[155]` | It does not — Layer / Role / Principal node types / Cls / ObjP / DataP. Untouched. |
| `[109]`'s claim *"every layer gains at least one typed bridge **of its own**"* | endpoints of the six bridges | True only under a *participates-in* reading. Origins are Metagraph ×2, ValidGraph ×2, SpecGraph ×2 — **Ontograph and ComputGraph originate none.** The wording was therefore not carried over; the replacement says *connected by*, which holds for all five. |
| The missing full stop before `Since` in `[107]` | XML | Confirmed: the 2026-08-24 round deleted the `.` (`w:del w:id="68"`) and never replaced it. The merge supplies it as a consequence, not as a separate fix. |
| Whether Figure 4 shows three bridges or six | `Publications/figures/R14.3/fig04_layers.png` (opened and read) | **All six, uniformly solid, no legend and no dashed distinction.** An earlier assumption drawn from the stale R14.2 masters — where `T1_ITcon_R14.2_figures.drawio` draws the three later bridges `dashed=1` — was wrong, and the author corrected it. The figure was already at same-status; the **caption** was the stale part. |

## Edits

### E1 — `[107]` the count — **STATUS: APPLIED (tracked del + ins)**

**Before:** `…carrying no hierarchy or precedence. Three typed cross-layer bridges make the layers mutually addressable:`

**After:** `…carrying no hierarchy or precedence. Six typed cross-layer bridges make the layers mutually addressable:`

The run is untracked, so the substitution was written as a `w:del`/`w:ins` pair rather than an
in-place rewrite — an untracked change here would have been invisible to the author in Word.

### E2 — `[107]` the list extended from three to six — **STATUS: APPLIED**

Written inside the existing `w:ins w:id="67"`, so the added text is already a tracked insertion.

**Before:**

> REFERS_TO grounds every Metagraph atom in Ontograph vocabulary; ATTRIBUTE_OF links a rule atom to
> the ComputGraph parameter it constrains; **and** VALIDATES connects a validation run to the Design
> State it was computed against, with the per-object verdicts it produced reaching the object
> instances themselves

**After:**

> REFERS_TO grounds every Metagraph atom in Ontograph vocabulary; ATTRIBUTE_OF links a rule atom to
> the ComputGraph parameter it constrains; VALIDATES connects a validation run to the Design State it
> was computed against, with the per-object verdicts it produced reaching the object instances
> themselves; ENCODED_AS runs from a SpecGraph note to the Metagraph rule that formalises it, so that
> a rule carries the specification it came from and a specification that has been formalised is
> distinguishable from one that has not; GROUNDED_IN runs from a SpecGraph note to the Ontograph
> terms it commits the project to, keeping a note and the vocabulary it introduced linked as the
> vocabulary grows; and DERIVED_FROM runs from a ValidGraph result to the ComputGraph parameter whose
> value produced it, closing the path between a verdict and the parametric quantity behind it. Each
> of the five layers is thereby connected by at least one typed bridge.

Consequential changes recorded under this clause: `and` moves from the VALIDATES clause to the
DERIVED_FROM clause; the sentence-final full stop missing before `Since` is supplied.

The three carried-over glosses are `[109]`'s own wording, unchanged except that each terminal `.`
becomes `;` to join the list. Nothing was rewritten for style.

### E3 — `[109]` struck out — **STATUS: APPLIED (tracked deletion)**

The whole paragraph is marked deleted: three plain runs and one run inside `w:ins w:id="76"`
converted to `w:delText` inside `w:del`, and the paragraph mark marked deleted in `w:pPr/w:rPr`.
`commentRangeStart`/`End` and both `commentReference` runs for comments **74** and **75** are left
outside the deletion wrappers, so both threads survive and the author sees the struck-through source
of the merge next to the comment that asked for it.

Removed with it, and this is what satisfies **C75c**:

- `The three bridges declared above leave the SpecGraph reachable only through the core band.`
- `Three further bridges follow from the same pattern and are set out here as proposals, shown in Figure 4. alongside the declared ones.`
- `…the Metagraph ceases to be the sole origin of cross-layer reference — a position that followed from the order in which the first three bridges were introduced.`

### E4 — `[111]` Figure 4 caption — **STATUS: APPLIED (tracked del + ins)**

**Before:** `…with the typed cross-layer bridges REFERS_TO, ATTRIBUTE_OF, and VALIDATES.`

**After:** `…with the typed cross-layer bridges REFERS_TO, ATTRIBUTE_OF, VALIDATES, ENCODED_AS, GROUNDED_IN, and DERIVED_FROM.`

Applied on the author's correction that Figure 4 already draws all six. The caption was the only
place left naming three of six, so leaving it would have re-created the split C75 asks to remove.

## Verification

| Check | Result |
|---|---|
| Every edit matched as declared | 4/4; the script fails loudly on a wrong or ambiguous match and wrote nothing until all four resolved |
| Paragraph diff, accepted view | `[107]`, `[109]`, `[111]` **only** |
| Package parts | 31 → 31 |
| Tracked changes | `w:ins` 140 → **142** (E1, E4); `w:del` 13 → **20** (E1, E4, plus E3's four run deletions and its paragraph mark) |
| Comments | 56 anchors / 56 references / 56 entries in `comments.xml` — unchanged |
| Structure | 385 `w:p`, 6 tables, 212 body paragraphs — unchanged; opens cleanly |
| `figure-cited` | still passes — dropping `shown in Figure 4` from `[109]` did not orphan the figure, since `[107]` already cites `(Figure 4, Table 3)` |
| `validate_docx.py` | output identical to the backup's apart from the filename and the body word count (9372 → 9222, the deleted `[109]` runs). The one `[FAIL] table-numbering` and one `[WARN] table-cited` are pre-existing. |
| Read back in full | `[106]`–`[112]` in the accepted-changes view. The merged sentence is grammatical, the list carries six items with a single `and`, and `Since each layer references the shared core band…` follows a complete sentence for the first time. |

Backup: `scratchpad/R14.3_BACKUP_before_C75.docx` (4 308 783 bytes).

## Carried forward from this part

- **No reply comment was written for C75.** As with C45, replies to author threads are authored
  separately, and the thread is still open in the file.
- **Comment 74's annotation is now stale.** It reads *"Three cross-layer bridges proposed — ENCODED_AS,
  GROUNDED_IN, DERIVED_FROM — shown in Figure 3 and described here. They are proposals; no ontology
  file was modified."* Both halves are now false: they are no longer presented as proposals, and the
  figure is 4, not 3. The annotation sits on the struck-through paragraph, so it disappears when the
  deletion is accepted — but if the author keeps it, it contradicts the body.
- **Comment 77 carries the same stale claim** on the Figure 4 caption (*"drawn dashed with a legend so
  they cannot be read as declared"*), and the figure does not do that.
- **Comment 80 is now partly answered by side effect.** It asks for a SpecGraph bridge to be
  *"proposed, included in the schema, shown in the figure, and described in the paper"* — ENCODED_AS
  and GROUNDED_IN now appear in the body list at declared status. Whether that closes C80 is the
  author's call; C79 (edges to Core concepts) is untouched.
- **The R14.2 drawio masters are behind the R14.3 figure.** `T1_ITcon_R14.2_figures.drawio` still
  draws the three later bridges dashed. `Publications/figures/R14.3/` holds `fig04_layers.png` but
  **no `.drawio` source for it** — the editable master for the current Figure 4 was not located.

## Out-of-scope observations — NOT acted on

- `[108]`'s third consequence (*"And it keeps the set open: because a layer refers to the shared core
  rather than to another layer's internals, a further layer — cost, or environmental performance —
  can be added against the same core without renegotiating the existing five."*) restates `[107]`'s
  closing sentence almost verbatim. `[107]` is now ~395 words with that duplication standing at both
  ends. Pre-existing; C75 did not ask.
- `[107]` opens a sentence with `Though the vocabularies inside them are deliberately standardised…`
  — a subordinate clause with no main clause. Pre-existing.

### Re-application after a Word overwrite — 2026-08-31, ~20:10

**What happened.** The C55 edits were written to the manuscript at 19:54 and read back from the live
file. Word then saved its own in-memory copy over the file at 20:10, reverting all three. This was
detected when the follow-up licence-naming replacement returned **0/1** and the raw XML still showed
`versioned in the same repository (https://github.com/Erarchitech/design-grammar-system)`.

**What the author changed in Word in the meantime** — outside C55, recorded here because it is the
reason the earlier working copy could not simply be restored:

- `[P107]` — the three *proposed* cross-layer bridges promoted into the declared set: *"Three typed
  cross-layer bridges"* → *"Six typed cross-layer bridges…"*, now naming `ENCODED_AS`,
  `GROUNDED_IN` and `DERIVED_FROM` alongside `REFERS_TO`, `ATTRIBUTE_OF` and `VALIDATES`, closing
  with *"Each of the five layers is thereby connected by at least one typed bridge."*
- `[P109]` — the paragraph that had set those three out as proposals **deleted**, its content having
  moved into `[P107]`.
- **Figure 4 caption** — now lists all six bridges.
- **Figure 5 caption** — rewritten to describe partition groupings: *"Design states accumulate in
  groupings (shown dashed) — alternatives within a facade typology, typologies within one design
  space, separate design spaces for one building. Partitioning determines which states are
  comparable for typing movement (section 6.1)."* This addresses **S4**, which the previous session
  carried forward as unassessed.

**Resolution.** The stale working copy was **not** restored — doing so would have destroyed those
four author edits. C55 was re-applied on top of the author's current text: E4 and E5 via
`docx_replace.py` (**2/2** as declared), E6 by paragraph insertion. Both author edits verified still
present in the result (`Six typed cross-layer bridges` ✓, `Design states accumulate in groupings` ✓).

**E5 extended.** With the author's approval, the sentence now names the licences rather than
deferring to *"the same licence"*, which was written before any licence existed:

**After:** `…are versioned in the same deposit (Ermolenko, 2026). The ontology modules, the shape set
and the specifications are released under the Creative Commons Attribution 4.0 International licence,
and the runtime services, the rule-shape catalogue and the migration scripts under the Apache
License 2.0.`

This matches the deposit exactly: CC BY 4.0 over `ontology/` and `spec/`, Apache-2.0 over
`services/`, `llm/` and `migrations/`.

**Backups.** `scratchpad/R14.3_BACKUP_before_C55.docx` (pre-C55, 19:54) and
`scratchpad/R14.3_BACKUP_before_C55_v2.docx` (the author's Word-saved state, 20:10). The re-applied
file is `scratchpad/R14.3_WORK2.docx`; `validate_docx.py` reports only the two pre-existing table
findings.

**Operational lesson.** A `~$` lock file next to the manuscript is not advisory. Editing while Word
holds the document does not fail — it succeeds, and is then silently reverted by Word's next save.
The manuscript must be closed in Word *and stay closed* until the swap is confirmed.

**Version correction.** The cited version is **`v1.0.1`**, not `v1.0.0`. After the deposit was first published, the author confirmed that the University of Minho is a joint copyright holder (FCT-funded doctoral work), so `LICENSE` now reads `Copyright 2026 Evgenii Ermolenko, University of Minho`, `ontology/LICENSE.md` carries the same holders for the CC BY portion, and the version strings were bumped. `v1.0.0` remains on the remote but is superseded; the manuscript cites `v1.0.1`. Re-tagging rather than re-pointing `v1.0.0` avoids rewriting a published tag, and cost nothing because the citation had not yet been written into the manuscript.

### Final application — 2026-08-31, 20:43 · **C55 is now in the manuscript**

Applied against the author's 20:42 save, after Word was closed and the `~$` lock confirmed gone.
The earlier working copies were discarded rather than restored; each was rebuilt from the current
file, because the author continued editing in Word between attempts.

**Paragraph indices shifted** by the author's deletion of the old `[P109]`. Current locations:

| Edit | § | was | **now** |
|---|---|---|---|
| E4 | 3 | `[P99]` | `[P99]` |
| E5 | AVAILABILITY | `[P333]` | **`[P331]`** |
| E6 | REFERENCES | after `[P345]` | **`[P344]`**, after Eastman at `[P343]` |

**Content diff against the base, with indices stripped: exactly three changes** — `[P99]`, the
AVAILABILITY paragraph, and the inserted reference. Nothing else in the document differs.

**Verified on the live file after the swap:**

1. `open ontology project (Ermolenko, 2026).` present.
2. `are versioned in the same deposit (Ermolenko, 2026). The ontology modules, the shape set and the
   specifications are released under the Creative Commons Attribution 4.0 International licence, and
   the runtime services, the rule-shape catalogue and the migration scripts under the Apache
   License 2.0.` present.
3. Reference list reads Eastman → **Ermolenko, E. (2026). *Design Grammar ontology* (Version 1.0.1)
   [Computer software]. GitHub. https://github.com/Erarchitech/design-grammar-ontology** →
   Ermolenko, E., Figueiredo, B., & Azenha, M. → Farghaly. Correct per APA 9.47.
4. The author's own Word edits survive intact — `Six typed cross-layer bridges` ✓,
   `Design states accumulate in groupings` ✓.
5. `validate_docx.py` findings **identical** to `scratchpad/R14.3_BACKUP_before_C55_final.docx` —
   the table-caption `[FAIL]` and the Table 6 `[WARN]` are pre-existing; nothing introduced.

**Backups, in order:** `R14.3_BACKUP_before_C55.docx` (19:54, pre-C55) ·
`R14.3_BACKUP_before_C55_v2.docx` (20:10, after Word's overwrite) ·
`R14.3_BACKUP_before_C55_final.docx` (20:42, the base actually edited).
