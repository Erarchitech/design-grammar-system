---
phase: 38-ai-generated-grasshopper-script-inputs
plan: 01
subsystem: api
tags: [spec, contract-first, neo4j, computgraph, validgraph, rule-partition-policy]

# Dependency graph
requires: []
provides:
  - "POST /computgraph/generate-inputs and POST /computgraph/candidates/accept normative contracts in spec/API.md — every JSON key, all ten error codes, four enumerated vocabularies, and the five SC1 numeric thresholds"
  - "spec/DATABASE.md amended: Parameter.reinstateParameterId (nullable) documented; DesignState's single-writer and always-linked-Run invariants replaced with a two-writer / Run-less-until-composed statement; a fourth ai-generated example DesignState node; a 'Reading standalone ParamStates' note recording finding F1"
  - "spec/RULE-PARTITION-POLICY.md 'Input Generation Bindings (Phase 38)' addendum: the inputBindings schema, the geometry-required default, and the single-authoring/scope-fence extension"
  - "CLAUDE.md: DesignState provenance properties, structure_rules.json added to Schema Change Propagation, two new Known Gotchas bullets"
affects: [38-02, 38-03, 38-04, 38-05, 38-06, 38-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Contract-first documentation: write the API/DB/policy contracts before any implementation code exists, so later plans implement against fixed strings rather than inferred ones"

key-files:
  created: []
  modified:
    - spec/API.md
    - spec/DATABASE.md
    - spec/RULE-PARTITION-POLICY.md
    - CLAUDE.md

key-decisions:
  - "SC1 thresholds fixed as five hard numbers (100% / >=75% / >=1 / >=0.10 / exactly 0) in spec/API.md rather than prose, so plan 38-07 has literal assertions rather than a re-derivation exercise"
  - "spec/DATABASE.md's DesignState invariants amended as a two-writer statement (VALIDATOR publish path + POST /computgraph/candidates/accept) rather than deleted outright, preserving the dedup-by-MERGE guarantee for both writers"
  - "A standalone accepted ParamState with no linked Run is documented as the intended interim lifecycle state ('not yet validated'), not an orphan defect — reframes finding F2 as a spec amendment rather than a spec violation"
  - "inputBindings lives as a new sibling top-level key in llm/structure_rules.json (not new mappings[] entries) because a binding is a selector, not a Cypher check — keeps load_structure_rules() and Phase 37's validator untouched"
  - "No new D- number assigned in RULE-PARTITION-POLICY.md's Phase 38 addendum, following the Phase 37 addendum's precedent exactly (no Phase 38 CONTEXT decision letter maps to a partition-policy decision)"

requirements-completed: [GHIN-01, GHIN-02, GHIN-03, GHIN-04]

coverage:
  - id: D1
    description: "spec/API.md documents both new routes with every JSON key, all ten error codes, four vocabularies, and the five SC1 thresholds"
    requirement: GHIN-01
    verification:
      - kind: other
        ref: "grep-based acceptance criteria in 38-01-PLAN.md Task 1 (all passed: route headings, token presence, 10 unique error codes, 4 strategies, 3 claims, 5 SC1 rows, clamping negation, zero-writes prose)"
        status: pass
    human_judgment: false
  - id: D2
    description: "spec/DATABASE.md amended: reinstateParameterId documented, DesignState two-writer statement replaces the false single-writer/no-orphan invariants, fourth example node, Reading standalone ParamStates note"
    requirement: GHIN-03
    verification:
      - kind: other
        ref: "grep-based acceptance criteria in 38-01-PLAN.md Task 2 (all passed: no orphan-designstates phrase, no written-only-by-VALIDATOR phrase, 3 DesignState kinds preserved, Phase 38 changelog entry, Neo4jValidGraphRepository + 38-05 named)"
        status: pass
    human_judgment: false
  - id: D3
    description: "spec/RULE-PARTITION-POLICY.md Input Generation Bindings addendum with the full inputBindings schema and no new D- number"
    requirement: GHIN-02
    verification:
      - kind: other
        ref: "grep-based acceptance criteria in 38-01-PLAN.md Task 3 (all passed: heading count >=2, inputBindings count >=3, monotone-bound count >=2, _FORBIDDEN_PARAM_KEYS present, D- number set unchanged, Phase 37 addendum has zero deletions)"
        status: pass
    human_judgment: false
  - id: D4
    description: "CLAUDE.md names the two new schema surfaces and two gotchas a future session would otherwise rediscover"
    requirement: GHIN-04
    verification:
      - kind: other
        ref: "grep-based acceptance criteria in 38-01-PLAN.md Task 4 (all passed: reinstateParameterId, structure_rules.json in propagation paragraph, sourceRuleId on DesignState row, zero deletions in Known Gotchas)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 01: Contracts and Spec Amendments Summary

**Normative API contract for `/computgraph/generate-inputs` and `/computgraph/candidates/accept`, plus the ValidGraph two-writer schema amendment and `inputBindings` policy addendum that make Phase 38's code legal to write.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments
- `spec/API.md` gained full request/response contracts for both new routes: every JSON key from `artifacts_this_phase_produces`, the `determinabilityClass`/`strategy`/`ruleSatisfaction.claim`/`excludedParameters[].reason` vocabularies, all ten error codes, and the five-row SC1 acceptance-threshold table (100% mechanical validity, >=75% rule satisfaction, >=1 Tier-0 floor, >=0.10 diversity, exactly 0 overclaiming) as literal numbers, not prose.
- `spec/DATABASE.md` amended in place: `Parameter.reinstateParameterId` documented as nullable; the DesignState block's two now-false invariants ("written only by VALIDATOR", "no orphan DesignStates") replaced with a two-writer statement and an explicit "Run-less until composed and validated is the intended lifecycle" clarification; a fourth `ai-generated` example DesignState node added; a "Reading standalone ParamStates" note records finding F1 (`Neo4jValidGraphRepository.RunsQuery` reads `:ValidationRun` only) and the pre-existing `:ValidationRun`/`:Run` label drift without widening it; a Phase 38 change-log entry added.
- `spec/RULE-PARTITION-POLICY.md` gained an "Input Generation Bindings (Phase 38)" addendum (same voice/precedent as the Phase 37 addendum, no new `D-` number): input generation is a fourth rule-corpus consumer that reads and never authors a threshold; the `inputBindings` sibling-key schema (`ruleId`, `determinability`, `parameters`, `metricExpression`, `monotoneIn`, `description`); the `geometry-required` default for unmapped rules; and the scope fence extending `_FORBIDDEN_PARAM_KEYS`'s value-threshold ban to input bindings.
- `CLAUDE.md` got three additive edits: the `DesignState` ValidGraph-Labels row now notes the optional AI-generated provenance properties; the Schema Change Propagation list now sweeps `llm/structure_rules.json`; two new Known Gotchas bullets cover the VALIDATION GRAPH read gap and `reinstateParameterId` nullability.

## Task Commits

Each task was committed atomically:

1. **Task 1: generate-inputs and candidates/accept contracts in spec/API.md** - `b5808ed` (docs)
2. **Task 2: ValidGraph and Computgraph schema amendments in spec/DATABASE.md** - `04c4117` (docs)
3. **Task 3: inputBindings specification and single-authoring note** - `39f77e1` (docs)
4. **Task 4: CLAUDE.md schema propagation and gotcha entries** - `e006105` (docs)

**Plan metadata:** pending (this commit)

## Files Created/Modified
- `spec/API.md` - Two new route contracts (`generate-inputs`, `candidates/accept`), SC1 thresholds table, all ten error codes
- `spec/DATABASE.md` - `Parameter.reinstateParameterId`, DesignState two-writer amendment + fourth example node + standalone-read note, Phase 38 changelog
- `spec/RULE-PARTITION-POLICY.md` - Input Generation Bindings (Phase 38) addendum, Normative-scope anchor, Consistency & Propagation extension
- `CLAUDE.md` - ValidGraph Labels row, Schema Change Propagation list, two Known Gotchas bullets

## Decisions Made
- SC1 thresholds are five fixed numbers in the spec, not a "measure and see" placeholder — closes the Phase 35 "shipped plumbing, never measured quality" failure mode by construction before plan 38-04 writes any generation code.
- The DesignState invariant amendment is worded as "two writers" plus an explicit lifecycle clarification (Run-less is intended, not orphaned) rather than simply deleting the old text, so a future reader understands *why* the invariant changed, not just that it did.
- `inputBindings` is a new sibling top-level key in `llm/structure_rules.json`, not new `mappings[]` entries — a binding is a selector (which parameters, what determinability), not a Cypher check, and this keeps Phase 37's `load_structure_rules()` and validator untouched (zero code changes required for the new key to be legal).
- No new `D-` number in the RULE-PARTITION-POLICY.md addendum, matching the Phase 37 addendum precedent exactly — verified via `grep -o 'D-[0-9][0-9]'` before/after showing the identical set (D-07, D-08, D-10 through D-14).

## Deviations from Plan

None — plan executed exactly as written. Two self-corrections were made during Task 2's acceptance-criteria verification: the initial DATABASE.md changelog line and two-writer bullet each contained the literal phrases the acceptance criteria required to be *absent* ("no orphan DesignStates", "written only by VALIDATOR", used descriptively rather than as the banned invariant text). Both were reworded in place before commit so the banned phrases genuinely have zero occurrences while the amendment's meaning is unchanged — not a deviation from scope, just an in-task wording fix caught by the plan's own automated verify command before the commit was made.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. This plan is documentation-only; no code, no dependencies, no infrastructure changes.

## Next Phase Readiness
- Plans 38-02 through 38-07 can now be executed against written, grep-verifiable contracts rather than inferred ones — every JSON key, error code, and enumerated value referenced by those plans' contract tests is pinned in `spec/API.md`.
- Plan 38-05 (the standalone `:DesignState` writer and the additive VALIDATION GRAPH second read) has its target invariant amendment already in place in `spec/DATABASE.md` — no spec work remains blocking that plan.
- Plan 38-07 (SC1 measurement) has five literal numeric thresholds to assert against, closing the ambiguity that caused Phase 35's quality-measurement gap.
- No blockers.

## Self-Check: PASSED

All 4 modified files and all 5 commit hashes (b5808ed, 04c4117, 39f77e1, e006105, 846fd25) verified present.

---
*Phase: 38-ai-generated-grasshopper-script-inputs*
*Completed: 2026-07-27*
