---
phase: 823-shacl-validation-layer
plan: 04
subsystem: docs
tags: [shacl, owl, rdf, swrl, documentation, spec, rule-partition, validation]

# Dependency graph
requires:
  - phase: 823-01
    provides: dg-reasoner/valid_graph_export.py (build_valid_graph + add_all_different, ValidGraph ABox export, owl:AllDifferent UNA)
provides:
  - spec/RULE-PARTITION-POLICY.md — normative rule-partition/precedence policy between the SWRL VALIDATOR and the SHACL validation layer
  - Cross-references from spec/LPG-OWL-MAPPING.md and CLAUDE.md to the new policy
  - shaclReportJson (ValidationRun/Run property) documented in spec/DATABASE.md, CLAUDE.md, README.md, .github/copilot-instructions.md
  - spec/LPG-OWL-MAPPING.md ValidGraph sketch + UNA sections marked Phase-823-implemented (no longer forward-looking)
affects: [823-02-shacl-shapes-authoring, 823-03-shacl-runtime-integration, rule-authoring-review, future-shacl-shape-additions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-authoring precedence: no business rule exists in both SWRL and SHACL — disagreement means mis-categorization, remedy is re-homing not verdict-merging"
    - "Schema-change-propagation checklist extended to cover SHACL shapes artifact (ontology/dg-shapes.ttl) and the new policy document"

key-files:
  created:
    - spec/RULE-PARTITION-POLICY.md
  modified:
    - spec/LPG-OWL-MAPPING.md
    - spec/DATABASE.md
    - CLAUDE.md
    - README.md
    - .github/copilot-instructions.md

key-decisions:
  - "Partition line (D-12): SWRL VALIDATOR owns architect-authored design-compliance rules (quantitative geometry/parameter constraints from NL ingestion); SHACL owns structural data-integrity of instance data (schema conformance of DesignState/Run/Rule structure)"
  - "Precedence (D-13): single-authoring principle — verdict disagreement can only mean mis-categorization; remedy is re-homing the rule, never merging or overriding verdicts; SWRL authoritative for design compliance, SHACL authoritative for data integrity"
  - "Enforcement (D-14): documentation + review discipline this phase; automated shape-vs-rule overlap linter explicitly deferred (named future item, not a promise)"

patterns-established:
  - "Decision-table test for new rule categories: BIM-geometry/parameter/architect-intent dependent -> SWRL; pure graph-shape/schema-conformance with zero business content -> SHACL"

requirements-completed: [SHCL-01]

coverage:
  - id: D1
    description: "spec/RULE-PARTITION-POLICY.md exists with partition line, decision table (SWRL vs SHACL examples with rationale), single-authoring precedence, and deferred-linter enforcement note"
    requirement: "SHCL-01"
    verification:
      - kind: other
        ref: "grep -qi 'SWRL' spec/RULE-PARTITION-POLICY.md && grep -qi 'SHACL' spec/RULE-PARTITION-POLICY.md && grep -Eqi 're-hom|rehom' spec/RULE-PARTITION-POLICY.md (PARTITION_OK)"
        status: pass
    human_judgment: false
  - id: D2
    description: "spec/LPG-OWL-MAPPING.md, spec/DATABASE.md, CLAUDE.md, README.md, .github/copilot-instructions.md all cross-reference the policy and/or document shaclReportJson; ValidGraph ABox + UNA marked implemented"
    requirement: "SHCL-01"
    verification:
      - kind: other
        ref: "grep -qi 'RULE-PARTITION-POLICY' spec/LPG-OWL-MAPPING.md CLAUDE.md && grep -qi 'shaclReportJson' spec/DATABASE.md CLAUDE.md README.md .github/copilot-instructions.md (PROPAGATION_OK)"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-12
status: complete
---

# Phase 823 Plan 04: Rule Partition Policy & Documentation Propagation Summary

**Authored spec/RULE-PARTITION-POLICY.md (D-11..D-14: partition line, decision table, single-authoring precedence, deferred-linter enforcement) and propagated shaclReportJson + ABox/UNA-implemented status across five cross-referencing spec/config surfaces**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-12T09:28:16Z (approx, per STATE.md session continuity)
- **Completed:** 2026-07-12
- **Tasks:** 2
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments
- New `spec/RULE-PARTITION-POLICY.md`: states the partition line (SWRL owns architect-authored design-compliance rules, SHACL owns structural data-integrity), an 8-row "what belongs where" decision table, single-authoring precedence (re-homing not verdict-merging), and the deferred-overlap-linter enforcement note
- `spec/LPG-OWL-MAPPING.md`: ValidGraph-to-RDF Sketch and UNA sections both flipped from "forward-looking"/"future" to "implemented in Phase 823 by `dg-reasoner/valid_graph_export.py`", with a cross-reference to the new policy
- `spec/DATABASE.md`: documented `shaclReportJson` as a new JSON-string property on the ValidationRun/Run node, sibling to `rulesJson`/`statePayloadJson`, explicitly noting it is absent on pre-823 runs
- `CLAUDE.md`: Schema Change Propagation checklist now names `ontology/dg-shapes.ttl` and cross-references `spec/RULE-PARTITION-POLICY.md`; `shaclReportJson` called out as its own propagation surface
- `README.md` and `.github/copilot-instructions.md`: extended their existing `statePayloadJson` documentation lines with a `shaclReportJson` mention

## Task Commits

Each task was committed atomically:

1. **Task 1: Author spec/RULE-PARTITION-POLICY.md** - `a906869` (docs)
2. **Task 2: Cross-reference the policy + document shaclReportJson and the implemented ABox/UNA** - `e32e8a0` (docs)

**Plan metadata:** (this commit, follows)

_Note: pure documentation plan — no test/feat/refactor split, both tasks are `docs` commits._

## Files Created/Modified
- `spec/RULE-PARTITION-POLICY.md` - New normative policy: partition line, decision table, precedence, enforcement, severity/message-house-style pointer
- `spec/LPG-OWL-MAPPING.md` - ValidGraph sketch + UNA sections marked Phase-823-implemented; cross-ref to RULE-PARTITION-POLICY.md added
- `spec/DATABASE.md` - `shaclReportJson` documented on the Run node
- `CLAUDE.md` - Schema Change Propagation checklist extended (dg-shapes.ttl, shaclReportJson, RULE-PARTITION-POLICY.md cross-ref)
- `README.md` - `shaclReportJson` added to Run's key-properties line
- `.github/copilot-instructions.md` - `shaclReportJson` added to Run's canonical-properties line

## Decisions Made
- Partition line, decision table, precedence, and enforcement scope match D-11 through D-14 in `823-CONTEXT.md` verbatim — no deviation from the pre-authored decision log.
- The DATABASE.md/CLAUDE.md/README.md/copilot-instructions.md `shaclReportJson` documentation describes the property as it will be written by the (not-yet-implemented-in-this-plan) publish path — this plan is documentation-only and does not itself write the property; runtime wiring is Phase 823's later waves.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' automated verification gates (`PARTITION_OK`, `PROPAGATION_OK`) passed on first attempt.

## Issues Encountered

None.

## Known Stubs

None. This is a documentation-only plan; no code stubs are introduced.

## Threat Flags

None. Per the plan's `<threat_model>`, this is a documentation-only change with no new runtime trust boundary — the policy document itself is the mitigation for the one identified threat (undocumented partition leading to double-authored rules), and no code/package surface was touched.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The rule-partition policy is now a stable, version-controlled reference for the remaining Phase 823 waves (shapes authoring at `ontology/dg-shapes.ttl`, `dg-reasoner` SHACL-runtime wiring, Grasshopper/UI surfacing) — shape authors can consult `spec/RULE-PARTITION-POLICY.md`'s decision table before adding new shapes.
- `shaclReportJson` is now documented ahead of the plan(s) that will actually write it (`data-service/app.py` publish path per D-06) — downstream plans have a stable schema contract to implement against.
- No blockers. This plan has zero code dependency (pure documentation, Wave 1) and ran in parallel with the ABox exporter (823-01, already complete).

---
*Phase: 823-shacl-validation-layer*
*Completed: 2026-07-12*

## Self-Check: PASSED

All 6 created/modified files and both task commit hashes (a906869, e32e8a0) verified present.
