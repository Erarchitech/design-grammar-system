---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
plan: 01
subsystem: spec
tags: [json-schema, evidence-contract, status-vocabulary, canonicalization, alignment]

# Dependency graph
requires: []
provides:
  - spec/EVIDENCE-CONTRACT.md — normative 8-status vocabulary, evidence envelope field table, canonicalization rules, golden fixture policy, DE-01 acceptance rule, v11.0 Phase 1105 handoff
  - spec/evidence-contract.schema.json — draft 2020-12 machine-readable annex, $defs.CanonicalStatus/EvidenceEnvelope/EvidenceRow
  - spec/DATABASE.md evidenceEnvelopeJson sidecar documentation on :Run
  - CLAUDE.md Schema Change Propagation cross-reference to spec/EVIDENCE-CONTRACT.md
affects: [1200-02, 1200-03, 1200-04, 1200-05, 1201, 1202, 1203, 1204, 1205, v11.0-1105]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Prose contract (semantics authority) + JSON Schema annex (shape authority) split, per RULE-PARTITION-POLICY.md's structural precedent (D-01)"
    - "Canonical-JSON hashing: pipe-joined scalar-tuple hashing for flat fields, 6-rule nested-payload canonicalization for structured fields, both versioned by canonicalizationVersion"

key-files:
  created:
    - spec/EVIDENCE-CONTRACT.md
    - spec/evidence-contract.schema.json
  modified:
    - spec/DATABASE.md
    - CLAUDE.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Followed plan's locked decisions D-01..D-16 verbatim (no re-opening); schema uses draft 2020-12 per planner's discretion, single file with 3 $defs"
  - "Bounded propagation per D-16: only spec/DATABASE.md, CLAUDE.md, .planning/REQUIREMENTS.md touched — no v11.0 Phase 1105-owned file modified"

patterns-established:
  - "$defs.CanonicalStatus.enum in spec/evidence-contract.schema.json is the single mechanical authority for the 8-status vocabulary; no second hardcoded list is permitted anywhere else in the repo"

requirements-completed: [ALGN12-01, ALGN12-02]

coverage:
  - id: D1
    description: "spec/EVIDENCE-CONTRACT.md defines exactly 8 canonical statuses, named verbatim, each with a normative meaning sentence, plus the D-05 situation table, D-04 one-directional legacy-boolean mapping, D-07 canonicalization rules, D-09/10/11 fixture freeze policy, D-12/13/14 DE-01 acceptance rule, and the D-15 v11.0 Phase 1105 handoff section"
    requirement: "ALGN12-01"
    verification:
      - kind: other
        ref: "plan 1200-01-PLAN.md Task 1 <verify> automated check (grep for all 8 statuses, 12 ## headings, Phase 1105 mention, canonicalizationVersion mention) — ran directly, all passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "spec/evidence-contract.schema.json validates as draft 2020-12 JSON Schema; $defs.CanonicalStatus.enum is exactly the 8 names; EvidenceEnvelope/EvidenceRow both required-field-complete and additionalProperties:false; root $ref resolves EvidenceEnvelope"
    requirement: "ALGN12-02"
    verification:
      - kind: other
        ref: "python -c jsonschema.Draft202012Validator.check_schema(s) plus a sample envelope jsonschema.validate() — ran directly, both passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "Bounded schema propagation (D-16): spec/DATABASE.md, CLAUDE.md, .planning/REQUIREMENTS.md carry the three additive edits this phase's own changes require; no v11.0 Phase 1105-owned file (cypher_template.txt, dataset_schema.json, n8n workflows, ui-v2 config, copilot-instructions.md, README.md, dg-shapes.ttl, structure_rules.json) is touched"
    requirement: "ALGN12-01"
    verification:
      - kind: other
        ref: "plan 1200-01-PLAN.md Task 3 <verify> automated grep check — ran directly, passed; confirmed via git diff --name-only that only the 3 intended files changed"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-09-20
status: complete
---

# Phase 1200 Plan 01: Contract, Status Vocabulary, Evidence Envelope Definition Summary

**Frozen 8-status evidence contract (`spec/EVIDENCE-CONTRACT.md` + `spec/evidence-contract.schema.json`) with a one-directional canonical-to-legacy-boolean mapping, 6-rule canonical-JSON hashing spec, and the v11.0 Phase 1105 propagation handoff.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-20T07:29:02Z
- **Completed:** 2026-09-20T07:34:13Z
- **Tasks:** 3
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- Published `spec/EVIDENCE-CONTRACT.md`: the normative prose contract with all 11 required sections — status vocabulary (8 names, D-05 situation table, per-status meaning sentences), current non-conforming behavior table (RuleEvaluator.cs/ValidationPublishPackageBuilder.cs defects), evidence envelope field table, row ordering/identity rules, legacy boolean compatibility (D-03/D-04 one-directional mapping), canonical JSON hashing spec (D-07, 6 rules), golden fixture freeze policy (D-09/10/11), DE-01 acceptance rule (D-12/13/14), an honest enforcement section, and the v11.0 Phase 1105 handoff (D-15)
- Published `spec/evidence-contract.schema.json`: single-file draft 2020-12 JSON Schema with `$defs.CanonicalStatus` (8-member enum, sole mechanical authority), `$defs.EvidenceEnvelope`, and `$defs.EvidenceRow`, both entity defs `additionalProperties: false`, root `$ref`s `EvidenceEnvelope` directly
- Performed the D-16-bounded propagation: `spec/DATABASE.md` gained the `evidenceEnvelopeJson` sidecar documentation on `:Run`; `CLAUDE.md` § Schema Change Propagation gained a cross-reference to `spec/EVIDENCE-CONTRACT.md`; `.planning/REQUIREMENTS.md` gained the D-15 ownership-split cross-reference — no v11.0 Phase 1105-owned file touched

## Task Commits

Each task was committed atomically:

1. **Task 1: Write spec/EVIDENCE-CONTRACT.md** - `29c7e33` (feat)
2. **Task 2: Write spec/evidence-contract.schema.json** - `e67088c` (feat)
3. **Task 3: Propagate 1200's own additive changes (D-16 bounded)** - `f2bcb44` (docs)

## Files Created/Modified
- `spec/EVIDENCE-CONTRACT.md` - normative prose contract (status vocabulary, envelope, hashing, fixture policy, DE-01 acceptance, 1105 handoff)
- `spec/evidence-contract.schema.json` - draft 2020-12 machine-readable annex
- `spec/DATABASE.md` - documented `evidenceEnvelopeJson` sidecar property on `:Run`
- `CLAUDE.md` - added `spec/EVIDENCE-CONTRACT.md` to § Schema Change Propagation
- `.planning/REQUIREMENTS.md` - added D-15 ownership-split cross-reference under "Contract and evidence (Phase 1200)"

## Decisions Made
- Followed the plan's locked decisions (D-01 through D-16) verbatim, with no re-opening, as instructed by the `<assumption_delta_decision>` block.
- Schema dialect: draft 2020-12, single file with three `$defs` (planner's discretion per RESEARCH.md), matching the plan's explicit direction.
- Kept the propagation edit narrowly bounded to exactly the three files D-16 requires; verified via `git diff --name-only` that no file from the deferred v11.0 Phase 1105 propagation list was touched.

## Deviations from Plan

None in the produced artifacts — Tasks 1, 2, and 3 were executed exactly as specified, and all automated verify/acceptance criteria in the plan passed on first attempt.

**One incidental note, not a deviation from this plan's own work:** `spec/DATABASE.md` already carried substantial pre-existing **uncommitted** changes in the working tree before this plan began executing (Phase 39/40 auto-validation `Run` properties, the `IntegrationConfig` node section, and the `SUPERSEDED_BY` relationship row — all unrelated prior work, not part of this plan or introduced by it). Task 3's single intended addition (the `evidenceEnvelopeJson` bullet) landed adjacent to that pre-existing content inside the same edit region, and splitting them into two commits would have required manual hunk surgery with meaningful risk of corrupting either change under the destructive-git-prohibition constraints. The Task 3 commit (`f2bcb44`) therefore includes both the intended `evidenceEnvelopeJson` documentation and the pre-existing unrelated `spec/DATABASE.md` content; this is disclosed in the commit message itself. No content was discarded, and the plan's own acceptance criteria (verified via targeted `grep`) all pass.

## Issues Encountered
None.

## Next Phase Readiness
- `spec/EVIDENCE-CONTRACT.md` and `spec/evidence-contract.schema.json` are committed and ready to be consumed by plans 1200-02 (golden fixture), 1200-03 (envelope wiring/persistence), 1200-04 (DG.Core Contracts DTOs + canonicalization helper), and 1200-05 (DE-01 runner).
- `$defs.CanonicalStatus.enum` is the single mechanical authority downstream plans must assert against — no second hardcoded status list should be introduced.
- No blockers for Wave 1 continuation (1200-02).

---
*Phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt*
*Completed: 2026-09-20*

## Self-Check: PASSED

All created files and task commit hashes verified present on disk and in git log:
- FOUND: spec/EVIDENCE-CONTRACT.md
- FOUND: spec/evidence-contract.schema.json
- FOUND: .planning/phases/1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt/1200-01-SUMMARY.md
- FOUND: 29c7e33 (Task 1 commit)
- FOUND: e67088c (Task 2 commit)
- FOUND: f2bcb44 (Task 3 commit)
