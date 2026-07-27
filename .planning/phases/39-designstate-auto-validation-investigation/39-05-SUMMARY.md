---
phase: 39-designstate-auto-validation-investigation
plan: 05
subsystem: docs
tags: [adr, investigation, obsidian, evidence, shacl, dsav]

requires:
  - "39-01 (dsav_watcher.py — the state machine and guardrails the documents describe)"
  - "39-02 (POST /designstate/capture + lifespan — the security posture the ADR records)"
  - "39-03 (39-EVIDENCE.json — the measured SC1/SC2 artifact both documents transcribe)"
  - "39-04 (measurements.speckle_publish — the measured Speckle-noise data point and the row_lifecycle caveat)"
provides:
  - "39-INVESTIGATION-NOTE.md — the DSAV-01 three-architecture comparison: path (b) measured, paths (a)/(c) analytic with inline provenance markers"
  - "The DSAV-03 ADR in DG_OBSIDIAN/knowledge/decisions/ — the durable record Phase 40's INTG-03 reads to know whether validation runs auto or manual"
  - "F-39-01 promoted from a measurement to an explicitly open, unresolved design question rather than an inherited silence"
  - "A corrected precedent reference: the degrade-never-raise policy is Phase 823 D-823-02, not D-823-03"
affects: ["40 (INTG-03 defers to 'the Phase 39 outcome' — this ADR is that outcome)"]

tech-stack:
  added: []
  patterns:
    - "Bracketed inline provenance markers on every analytic cell, naming either the measured figure it derives from or the specific empirical blocker it rests on — a cell without a marker is a defect"
    - "Artifact-arithmetic over summary prose: where a prior SUMMARY's derived figure cannot be reconciled with the evidence artifact, the note uses the artifact and labels the summary figure as summary-sourced rather than laundering it"
    - "Scoped vault-index edit — a single-line insertion into the Decisions list, never a whole-file rewrite of a 231-line MOC"

key-files:
  created:
    - .planning/phases/39-designstate-auto-validation-investigation/39-INVESTIGATION-NOTE.md
    - "DG_OBSIDIAN/knowledge/decisions/Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails.md"
  modified:
    - DG_OBSIDIAN/00-home/index.md

key-decisions:
  - "The ~1.5 s dg-reasoner round-trip figure in 39-03-SUMMARY.md is not reproduced as fact: 2.0 s debounce + 1.5 s already exceeds the artifact's recorded 2.679 s total, so the note derives path (a)'s latency floor from artifact arithmetic (2.679 − 2.0 = 0.679 s upper bound) and labels the summary figure as summary-sourced"
  - "The ADR cites Phase 823 D-823-02 as the degrade-never-raise precedent, not D-823-03 as the plan instructed — D-823-03 is UI state gating on results.length; D-823-02 is the non-fatal SHACL proxy in the publish path"
  - "F-39-01 is written as an open question with an explicit warning sentence telling the reader not to interpret the phase's success criteria as meaning auto-validation produces meaningful pass/fail verdicts today"
  - "The row_lifecycle caveat is given its own call-out block in the note rather than a footnote, because a reader who misses it would believe a queryable Neo4j row exists behind the Speckle measurement"

requirements-completed: [DSAV-01, DSAV-03]

coverage:
  - id: D1
    description: "An investigation note compares all three trigger architectures on latency, publish-flood and Speckle-noise, with path (b) measured and paths (a)/(c) analytic (DSAV-01)"
    requirement: "DSAV-01"
    verification:
      - kind: cli
        ref: "39-05-PLAN.md Task 1 <automated> transcription check — 'note ok'"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every path-(b) figure in the note matches 39-EVIDENCE.json exactly; the collapse ratio and configured rate limit are mechanically re-checked against the artifact"
    requirement: "DSAV-01"
    verification:
      - kind: cli
        ref: "39-05-PLAN.md Task 1 <automated> — asserts sc2_collapse.captures_in and sc2_runs_per_minute.configured_rate_limit_per_minute appear in the note"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every analytic cell for paths (a) and (c) carries an inline bracketed provenance marker naming a measured path-(b) figure or a specific empirical blocker (P-18)"
    verification: []
    human_judgment: true
    rationale: "Editorial — 39-VALIDATION.md § Manual-Only Verifications assigns this to a human reviewer. All 12 analytic cells carry markers; a reviewer must judge whether each anchor is the right one."
  - id: D4
    description: "The ADR exists in DG_OBSIDIAN/knowledge/decisions/ with the required sections and is linked from the vault index (DSAV-03, SC3)"
    requirement: "DSAV-03"
    verification:
      - kind: cli
        ref: "39-05-PLAN.md Task 2 <automated> front-matter/section/blocker/index check — 'adr ok'"
        status: pass
    human_judgment: false
  - id: D5
    description: "The vault index received a scoped edit, not a rewrite (T-39-13)"
    requirement: "DSAV-03"
    verification:
      - kind: cli
        ref: "git diff --stat -- DG_OBSIDIAN/00-home/index.md → 1 insertion, 0 deletions"
        status: pass
    human_judgment: false
  - id: D6
    description: "ADR completeness and correctness — whether the reasoning is sound, not merely whether the sections are present"
    verification: []
    human_judgment: true
    rationale: "39-VALIDATION.md § Manual-Only Verifications: an ADR can be checked automatically for section presence but not for soundness. Reviewer should confirm each rejected option's blocker is the empirical one, and that the F-39-01 treatment reads as genuinely unresolved rather than hedged."

metrics:
  duration: ~40min
  completed: 2026-07-28
  tasks: 2
  files: 3

status: complete
---

# Phase 39 Plan 05: Investigation Note and DSAV-03 ADR Summary

**The phase's two documentary deliverables are written and filed: a three-architecture comparison whose path-(b) column is transcribed figure-by-figure from `39-EVIDENCE.json` and whose path-(a)/(c) columns carry inline provenance markers, and an ADR in the vault that records the choice, seven empirically-blocked rejections, the identity-model debt, a corrected precedent reference, and nine ordered follow-up items — with F-39-01 presented as an open question rather than a solved one.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-28
- **Tasks:** 2 completed
- **Files modified:** 3 (2 new, 1 modified)

## Accomplishments

**`39-INVESTIGATION-NOTE.md` (DSAV-01).** Opens on the question, the answer, and the two blocking findings that reshaped the roadmap's premise — no `:DesignState` write exists to watch, and no server-side SWRL evaluator exists — stating plainly that those two facts, not a preference between architectures, determined the prototype's shape. Then a six-column comparison table (latency, publish-flood, Speckle noise, dependency footprint, testability without Rhino, verdict) with one row per architecture. Path (b)'s cells are marked **measured** and quote the artifact; all twelve path-(a) and path-(c) cells are marked **analytic** and end with a bracketed marker naming either the measured figure they derive from or the specific blocker they rest on. Followed by a full measured breakdown of path (b), the coverage-gap section, the guardrails-as-measured section, a six-item consequences section, and a provenance statement.

**The DSAV-03 ADR**, filed to `DG_OBSIDIAN/knowledge/decisions/` in the planner's chosen P-08 style — Style C front matter (`name` / `description` / `metadata` with `type`, `phase`, `decision_date`, `requirements`, `status`) over a Style B prose body. Eleven sections: Context, Decision, Rejected options, the headline coverage-gap finding, Guardrails as built, the `add-alongside` identity decision with its three accepted debts and three promote triggers, the precedent departure, Consequences and accepted limitations, nine ordered follow-up items, Security posture, and References. It cross-links the investigation note per D-16 and deliberately does not duplicate its tables.

**Vault index registered** with a single-line insertion into § Decisions, placed with the other phase decision entries, in that section's existing `[[decisions/<file>|<label>]]` format.

## The two integrity decisions that shaped the writing

**1. A prior summary's figure was not laundered into the note.** `39-03-SUMMARY.md` decomposes the SC1 latency as "2.0 s debounce + up to one 2.0 s poll interval + a ~1.5 s dg-reasoner SHACL round-trip", and reports a three-run spread of 3.427 / 2.801 / 2.679 s. Neither the ~1.5 s round-trip nor the other two run times exists in `39-EVIDENCE.json`, and **the ~1.5 s figure cannot be reconciled with the recorded total**: 2.0 + 1.5 = 3.5 s already exceeds the artifact's `latency_seconds` of 2.679. Reproducing it would have put a plausible-looking number with no artifact key behind it into the phase's headline document — precisely the T-39-12 failure mode.

Instead the note derives path (a)'s latency floor from artifact arithmetic alone: 2.679 − 2.0 = **0.679 s**, which must contain *both* the poll phase offset *and* the SHACL round-trip, so 0.679 s is an upper bound on path (a)'s floor. The summary's spread is quoted once, in a call-out explicitly labelled *summary-sourced, not artifact-sourced*, and is used in no comparison cell.

**2. F-39-01 is written as unresolved, with a warning sentence.** The temptation in an ADR is to present a measured verdict pipeline as working. It is not working in the sense a reader would assume. The note and the ADR both carry an explicit sentence — *"This ADR must not be read as saying auto-validation currently produces meaningful pass/fail verdicts. It does not yet."* — followed by the measurement (`conforms: false`, one violation, shape `RunStatusShape_valid`, `ValidStatus: [false, false]` for two ObjStates), the mechanism (SHACL runs before `ValidStatus` is written; the finding's `focusLabel` is the `runId`, which matches no objState, so the conservative fallback flips every index), and the two candidate fixes with a statement that choosing between them was out of budget and belongs with follow-up item 1.

## The row_lifecycle caveat is discoverable, not buried

`measurements.speckle_publish.row_lifecycle` records that the published Neo4j run row was destroyed by a later routine suite run and deliberately not recreated. The note gives this its own block-quoted call-out inside the Speckle-noise section, not a footnote, because a reader who missed it would reasonably believe a queryable row sits behind the measurement. The call-out states: the before/after counts (`send_status_true_rows` 1 → 0), the deleting fixture by file, the mechanism (`integration`-marked but not `live`-marked, so a bare in-container run collected it), the explicit non-repair with its reason (D-11 permits exactly one publish-enabled run; re-running would mint a second Speckle version), and the durable independent Speckle-side proof with its 0.97 s-after-`completedAt` timestamp and the human confirmation. It also appears as consequence 7 in the ADR.

## Task Commits

1. **Task 1: the DSAV-01 investigation note** — `179c127` (docs)
2. **Task 2: the DSAV-03 ADR + scoped vault-index link** — `02ceb53` (docs)
3. **Task 1 addendum: the requirements-traceability range-row no-op** — `00ebc7c` (docs)

_Plan metadata commit follows below._

## Files Created/Modified

- `.planning/phases/39-designstate-auto-validation-investigation/39-INVESTIGATION-NOTE.md` — **new**, 237 lines. The DSAV-01 comparison, the measured path-(b) breakdown, the coverage gap, the guardrails, six consequences, and the provenance statement.
- `DG_OBSIDIAN/knowledge/decisions/Phase 39 DesignState auto-validation — data-service watcher, SHACL verdict, guardrails.md` — **new**, 170 lines. The DSAV-03 ADR.
- `DG_OBSIDIAN/00-home/index.md` — **1 insertion, 0 deletions.**

## Decisions Made

- **Style C front matter over a Style B body**, per P-08, with `status: accepted` inside the `metadata` block rather than at the top level, so the whole machine-readable payload sits in one place.
- **`spec/RULE-PARTITION-POLICY.md` and Phase 823's D-823-04 are cited together** in the coverage-gap sections. The gap is not "a shape nobody got round to writing" — it is a recorded partition decision that SHACL carries data-integrity shapes only. Framing it as an omission would misrepresent it as easy to close.
- **The ADR names the security residual explicitly** rather than listing the mitigations and stopping. The in-memory rate limiter is restart-resettable; that sentence exists so a follow-up milestone inherits an honest starting point.
- **Seven rejected options, not two.** The plan named path (a), path (c), the canvas bridge, a Python SWRL port, a compliance shape, Speckle-row config fields, and an optional `publish_result`. All seven are recorded with their blockers, because "why not the obvious cheaper thing" is exactly what a reader of a rejected-options section is looking for.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan cited the wrong Phase 823 decision id for the degrade-never-raise precedent**

- **Found during:** Task 2, reading `Phase 823 SHACL validation layer design decisions.md` as the plan's `read_first` instructed
- **Issue:** The plan says to reference *"specifically D-823-03's degrade-never-raise policy, which D-08 departs from"*. **D-823-03 is not that decision** — it is "UI state gating на `results.length`, не на `conforms`", about how the SHACL panel picks between four display states. The degrade-never-raise policy is **D-823-02**, "Non-fatal SHACL sidecar proxy в publish path": `_call_shacl_validate` wrapped so that HTTP 504 / timeout / unavailable never drops the publish response. Writing the plan's id verbatim would have pointed the ADR's most load-bearing cross-reference at an unrelated UI decision, and the two records would not in fact point at each other as D-08 requires.
- **Fix:** the ADR cites **D-823-02** by its actual title and content, and additionally inherits **D-823-07**'s timeout-budget lesson with a note on why it matters *more* on the auto path (a false timeout burns an attempt from a bounded counter and can drive a healthy run to `failed`, where on the manual path it merely costs a findings panel). D-823-04 is cited separately in the coverage-gap section.
- **Files modified:** the ADR
- **Verification:** the Task 2 verify command passes; the cited title matches the heading at line 28 of the Phase 823 note.
- **Committed in:** `02ceb53`

---

**2. [Rule 2 - Missing Critical] A prior summary's unreconcilable figure needed an explicit provenance caveat, not silent omission**

- **Found during:** Task 1, deriving path (a)'s latency floor
- **Issue:** P-17 requires every number to be transcribed from the artifact, and P-18 requires each analytic cell to cite a measured anchor. Path (a)'s floor is naturally expressed as "the SHACL round-trip alone" — and the only round-trip figure in the phase's prose is `39-03-SUMMARY.md`'s ~1.5 s, which has no artifact key and contradicts the artifact's own total. Quietly dropping it would leave a future reader to rediscover the contradiction; quoting it would fabricate a measured-looking anchor.
- **Fix:** the note derives the floor from artifact arithmetic (2.679 − 2.0 = 0.679 s as an upper bound), and adds a labelled provenance caveat naming the summary figure, stating that it cannot be reconciled with the recorded total, and stating that the note therefore uses artifact arithmetic instead. The three-run spread is reported in the same caveat, explicitly marked summary-sourced.
- **Files modified:** the investigation note
- **Verification:** every numeral in the comparison table traces to an artifact key; the two derived values (0.679 s, 4.299 s) are labelled as derived arithmetic over artifact values.
- **Committed in:** `179c127`

---

**3. [Scope addendum] The requirements-traceability range-row no-op recorded in the note**

- **Found during:** Task 2 wrap-up
- **Issue:** `REQUIREMENTS.md` carries DSAV-01/02/03 as individual checkboxes but records traceability as one **phase-level range row** (`DSAV-01 … DSAV-03 | Phase 39 | Pending`). `requirements mark-complete` cannot split a range row per-ID, so Wave 3's `DSAV-02` marking flipped the checkbox but left the range row reading `Pending` — and the same applies to this plan's two requirements until all three are done.
- **Fix:** a short subsection under the note's Provenance heading recording the mechanism and stating which artifact is authoritative (the checkboxes) and which is not (the range row), so a later reader does not mistake a stale `Pending` for unfinished work.
- **Files modified:** the investigation note
- **Committed in:** `00ebc7c`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical) + 1 scope addendum
**Impact on plan:** file scope is exactly the three files the plan names. Both auto-fixes protect the plan's own stated integrity constraint — one from citing the wrong precedent, one from laundering an unverifiable number into the phase's headline document.

## Issues Encountered

- **The plan's `<read_first>` list is trustworthy about *which* files to read but not always about *what is in them*.** Deviation 1 is the concrete instance: the decision id was wrong, and it was only caught because the plan also instructed reading the file. Reading the cited source rather than trusting the citation was load-bearing here.
- **`39-PRE-DECISIONS.md` remains untracked** in the phase directory. It predates this plan and is not in its file scope; left alone, as Wave 4 also did.
- **No `git stash`, `git clean`, `git checkout` or `git restore` was used at any point.** The repository's many pre-existing uncommitted `DG/**/bin/` and `DG/**/obj/` build artifacts were left untouched, and all 8 pre-existing stashes are intact.

## Verification Evidence

| Check | Result |
|---|---|
| Task 1 `<automated>` transcription check | **`note ok`** |
| Task 2 `<automated>` front-matter / section / blocker / index check | **`adr ok`** |
| `grep -c "p39-autoval"` on the note | **4** (≥ 1 required) |
| ADR cross-links `39-INVESTIGATION-NOTE.md` (D-16) | present |
| `git diff --stat -- DG_OBSIDIAN/00-home/index.md` | **1 file changed, 1 insertion(+)** — scoped, no deletions (T-39-13) |
| `python -m pytest data-service/tests/ -q` (host) | **699 passed, 4 failed, 1 skipped, 8 deselected, 25 errors** — byte-identical to the documented baseline; this plan is documentation-only |
| Blockers named in the ADR | `community`, `apoc`, `read-only`, `swrl` all present |
| Unresolved placeholder text in either document | none |
| Credential-shaped literals in either document | none — only Speckle project/model/version identifiers |

## User Setup Required

None. This plan touched no code and no running service.

## Next Phase Readiness

- **DSAV-01 and DSAV-03 are satisfied**, closing the phase's requirement set (DSAV-02 landed in Wave 3). SC3 is satisfied; SC1 and SC2 were satisfied by Waves 3 and 4.
- **Phase 40's INTG-03 deliverable can now resolve "auto or manual per Phase 39 outcome"** — the ADR is filed in the vault and linked from its index, and its answer is: *the mechanism is auto, but the verdict it delivers today is a non-discriminating well-formedness check, so INTG-03 should treat validation as manual until follow-up item 1 lands.*
- **The single most important open item for whoever picks this up** is F-39-01. It is measured, explained, and unresolved by design. Two candidate fixes are named; neither has been evaluated for consequences.
- No blockers.

---
*Phase: 39-designstate-auto-validation-investigation*
*Completed: 2026-07-28*

## Self-Check: PASSED

All three claimed files exist on disk (`39-INVESTIGATION-NOTE.md`, the ADR in `DG_OBSIDIAN/knowledge/decisions/`, `39-05-SUMMARY.md`) and all three task commits (`179c127`, `02ceb53`, `00ebc7c`) are present in git history.
