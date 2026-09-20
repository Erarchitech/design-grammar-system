---
phase: 37-script-structure-validation
plan: 02
subsystem: docs
tags: [rule-partition-policy, api-contract, computgraph, spec-first, wave-1-contracts]

requires: [37-01]
provides:
  - "spec/RULE-PARTITION-POLICY.md: Computgraph structural checks named as a third validation system (two decision-table rows + addendum section, no new D- number)"
  - "spec/API.md: normative POST /computgraph/validate and POST /computgraph/consult contracts (every JSON key, all 7 checkId values, all 4 operation values, all 6 error codes)"
affects: [37-03, 37-04, 37-05, 37-06]

tech-stack:
  added: []
  patterns:
    - "Addendum-not-decision pattern: a partition-policy update can be a named section with no D-NN number when no CONTEXT.md decision letter maps to it -- avoids implying a formal governance decision that wasn't made"
    - "Contract-before-code: JSON response shapes and error-code vocabularies written into spec/API.md before any route handler exists, so later contract tests pin real committed text rather than a guess"

key-files:
  created: []
  modified:
    - spec/RULE-PARTITION-POLICY.md
    - spec/API.md

key-decisions:
  - "Computgraph Structural Checks section placed after Precedence & Single-Authoring (D-13) and before Enforcement (D-14), framed explicitly as an addendum with no D- number -- no Phase 37 CONTEXT.md decision letter maps to this point, so a numbered decision would misrepresent it as formal governance"
  - "Severity taxonomy is the existing SHACL violation/warning/info mapping, cross-referenced not restated -- the addendum links to 'How SHACL Findings Surface' rather than duplicating the table, keeping one source of truth for the taxonomy"
  - "POST /computgraph/publish (shipped Phase 36) gets only a one-line table entry in spec/API.md -- this plan closes the doc gap for it, it does not respecify it"
  - "definitionId-omitted resolution rule (0/1/many published definitions -> NO_DEFINITION/use-it/AMBIGUOUS_DEFINITION) documented as normative prose ahead of any implementation, keeping the report single-shaped instead of branching into per-definition vs. aggregate forms"

requirements-completed: [SVAL-01, SVAL-02, SVAL-03]

coverage:
  - id: D1
    description: "spec/RULE-PARTITION-POLICY.md names Computgraph structural checks as a third validation system with its own decision-table rows, severity cross-reference, single-authoring rationale, and value-threshold exclusion -- no existing decision renumbered, no new D- letter invented"
    requirement: "SVAL-01"
    verification:
      - kind: other
        ref: "grep -c 'cg_structure_checks.py' spec/RULE-PARTITION-POLICY.md == 2; grep -c 'Computgraph Structural Checks (Phase 37)' == 3; grep -o 'D-[0-9][0-9]' | sort -u == D-11..D-14 unchanged; git diff shows only additive rows/sentences in the SWRL/SHACL sections"
        status: pass
    human_judgment: false
  - id: D2
    description: "spec/API.md documents POST /computgraph/validate with every response key (project, definitionId, publishedAt, checkedAt, findings[], ruleResults[], counts), the definitionId resolution rule, all 7 checkId values, all 4 operation values, the determinism + LLM-free invariants, and 4 error codes"
    requirement: "SVAL-01, SVAL-02"
    verification:
      - kind: other
        ref: "grep -c for every required token (checkedAt, publishedAt, conventionName, ruleExists, satisfyingEntities, offendingEntities) all >=1; all 7 checkId strings and all 4 operation strings present; all 4 validate error codes present"
        status: pass
    human_judgment: false
  - id: D3
    description: "spec/API.md documents POST /computgraph/consult with every response key (question, answer, grounded, groundedCount, citedEntities, ungroundedMentions, subgraphEntityCount, truncated), the read-only/flag-don't-block/staleness-visible guarantees in prose, and 2 error codes"
    requirement: "SVAL-03"
    verification:
      - kind: other
        ref: "grep -c 'read-only' and 'never executes' both present; groundedCount/subgraphEntityCount/truncated/ungroundedMentions all present; both consult error codes present"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-27
status: complete
---

# Phase 37 Plan 02: Partition-Policy Addendum and Computgraph API Contracts Summary

**Extended `spec/RULE-PARTITION-POLICY.md` with a third-system addendum for Computgraph structural checks, and wrote the normative `spec/API.md` request/response contracts for `POST /computgraph/validate` and `POST /computgraph/consult` before any implementation code exists.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified:** 2 (both existing spec files, no new files)

## Accomplishments

- `spec/RULE-PARTITION-POLICY.md`: appended two rows to the "What Belongs Where" decision table (Script/Computgraph structural shape -> `cg_structure_checks.py`; Rule-mapped script-structure requirement -> `structure_rules.json`-referenced Cypher), added a new "Computgraph Structural Checks (Phase 37)" addendum section (placed between Precedence & Single-Authoring D-13 and Enforcement D-14, no `D-` number assigned), extended the top "Normative scope" anchor list, and extended the closing "Consistency & Propagation" paragraph to also flag future Computgraph schema changes for policy review. No existing decision text was altered or renumbered.
- `spec/API.md`: added a `### Computgraph` subsection under the data-service heading with a one-line summary of the already-shipped `POST /computgraph/publish`, and full contracts for the two new routes -- every response JSON key, the `definitionId` zero/one/many resolution rule (`COMPUTGRAPH_VALIDATE_NO_DEFINITION` / `COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION`), all 7 `checkId` values, all 4 rule-mapped `operation` values, the determinism and LLM-free invariants for `/validate`, and the read-only / flag-don't-block / staleness-visible guarantees for `/consult`, plus all 6 error codes and a closing "Report surface" note naming the GH-panel print as a deferred item.

## Task Commits

Each task was committed atomically:

1. **Task 1: Partition-policy addendum for Computgraph structural checks** - `d6ec924` (docs)
2. **Task 2: Computgraph route contracts in spec/API.md** - `77ab18a` (docs)

**Plan metadata:** (pending — final commit below)

## Files Created/Modified
- `spec/RULE-PARTITION-POLICY.md` - two decision-table rows + "Computgraph Structural Checks (Phase 37)" addendum section + anchor/propagation updates
- `spec/API.md` - `### Computgraph` subsection: `/computgraph/publish` one-liner + full `/computgraph/validate` and `/computgraph/consult` contracts

## Decisions Made

All nine "Open for planning" / open-question resolutions listed in the plan's `planning_decisions_recorded_here` block are now traceable to committed text:

1. Rule-mapping file location/shape (`llm/structure_rules.json`, file-first) — referenced in the new decision-table row and the addendum's value-threshold-exclusion sentence.
2. Severity taxonomy (`violation`/`warning`/`info`, reused verbatim) — stated explicitly in the addendum's "Severity assignment" bullets, cross-referencing "How SHACL Findings Surface" rather than restating it.
3. Persist vs. ephemeral (ephemeral) — stated in the addendum's closing sentence and in `spec/API.md`'s implicit lack of a run-id/persistence field in the validate response.
4. Partition-policy placement (lighter addendum, no `D-` number) — the new section's opening sentence states this explicitly.
5. The two unreachable defensive checks (`parameter_without_datatype`, `object_without_behavior`) kept in SVAL-01 scope — both appear in the `checkId` vocabulary enumerated in `spec/API.md`.
6. Report surface scope (JSON contract in `spec/API.md`, GH-panel print deferred and named) — closing "Report surface" note in `spec/API.md`.
7. `definitionId` optionality on validate (0/1/many resolution rule) — documented as normative prose in `spec/API.md` ahead of the response-key table.
8. Determinism and `checkedAt` (byte-identical `findings`/`ruleResults`, `checkedAt` the sole varying field) — stated as an explicit invariant in `spec/API.md`.
9. `namePattern` semantics (case-sensitive substring, bound parameter, never glob/regex) — not directly quoted in either spec file; this is an implementation-detail decision for `structure_rules.json`'s `requiresProcedure`/`requiresParameter` template compiler (plans 37-03/37-04), not a claim `spec/API.md`'s route contract or the partition-policy addendum needed to assert. Flagged here for traceability rather than silently omitted.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' automated verification and acceptance-criteria greps passed on the first attempt with no auto-fixes required.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. This plan is documentation-only; zero packages installed, zero services touched (confirmed by the plan's own threat model: T-37-SC "npm/pip/cargo installs" disposition is `accept`, zero packages).

## Next Phase Readiness

- The two normative contracts this plan produced are the literal target for plans 37-03 (`cg_structure_checks.py` SVAL-01), 37-04 (SVAL-02 rule-mapped checks + `llm/structure_rules.json`), 37-05 (`POST /computgraph/validate` route + report contract test pinning `spec/API.md`'s exact keys), and 37-06 (`POST /computgraph/consult` route + grounding contract test).
- `spec/RULE-PARTITION-POLICY.md` no longer has an uncovered third validation path — a reviewer proposing a new Computgraph check now has a decision-table test and an addendum section to consult, matching `CLAUDE.md`'s Schema Change Propagation checklist.
- No blockers for Wave 1 continuation.

---
*Phase: 37-script-structure-validation*
*Completed: 2026-07-27*

## Self-Check: PASSED

All modified files confirmed present on disk (`spec/RULE-PARTITION-POLICY.md`, `spec/API.md`, `37-02-SUMMARY.md`); both task commit hashes (`d6ec924`, `77ab18a`) confirmed present in `git log --oneline --all`.
