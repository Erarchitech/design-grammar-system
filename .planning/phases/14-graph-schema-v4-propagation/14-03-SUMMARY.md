---
phase: 14-graph-schema-v4-propagation
plan: 03
subsystem: database
tags: [coalesce, backward-compat, smoke-test, wave-0, designstate-seed]

requires:
  - phase: 13-ontology-v7-and-contract-investigation
    provides: Rule-property rename decisions (D-04/D-05/D-06), kind rename (D-09/D-10)
provides:
  - Extended coalesce chains on Neo4jRuleRepository.cs for v4 Rule-property backward-compat (D-06)
  - smoke_rules_ingest.sh — SCHM-09 live-ingest Wave 0 harness
  - smoke_graph_query.sh — SCHM-10 graph-query Wave 0 harness
  - seed_designstates.cypher — SCHM-13 migration precondition (v3-kind DesignState nodes)
affects:
  - 14-04 (live-smoke verify wave, consumes both smoke scripts)
  - 14-06 (kind-migration demo, consumes seed data)

tech-stack:
  added: []
  patterns: [coalesce new-before-old backward-compat, n8n re-import gotcha documentation]

key-files:
  created:
    - test/smoke_rules_ingest.sh
    - test/smoke_graph_query.sh
    - test/seed_designstates.cypher
  modified:
    - DG/src/DG.Core/Data/Neo4jRuleRepository.cs

key-decisions:
  - "Description coalesce also extended to RuleDescription (RESEARCH recommendation — completes backward-compat contract alongside n8n RuleDescription backfill)"

patterns-established:
  - "New Property First in coalesce: every backward-compat coalesce chains the new PascalCase property before the old lowercase one (new-before-old), preventing stale-data reads during the transition window"
  - "Wave 0 harness pattern: each live-verify plan that needs a running Docker stack gets a standalone bash smoke script that can be run independently without orchestration"

requirements-completed: [SCHM-09, SCHM-10, SCHM-13]

coverage:
  - id: D-06
    description: "Neo4jRuleRepository coalesce chains extended for renamed Rule props (SWRL/RuleName/RuleDescription, new-before-old)"
    requirement: SCHM-09
    verification:
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ --filter FullyQualifiedName~Neo4jRuleRepositoryVariableKindTests"
        status: pass
    human_judgment: false
  - id: SCHM-09-W0
    description: "smoke_rules_ingest.sh — Wave 0 harness for live-ingest verification"
    verification:
      - kind: other
        ref: "grep -q .SWRL test/smoke_rules_ingest.sh && test -x test/smoke_rules_ingest.sh"
        status: pass
    human_judgment: true
    rationale: "Smoke script requires live Docker stack with re-imported n8n workflow — not run automatically. File presence and structure verified."
  - id: SCHM-10-W0
    description: "smoke_graph_query.sh — Wave 0 harness for graph-query verification"
    verification:
      - kind: other
        ref: "grep -q r.SWRL test/smoke_graph_query.sh && test -x test/smoke_graph_query.sh"
        status: pass
    human_judgment: true
    rationale: "Smoke script requires live Docker stack with re-imported n8n workflow — not run automatically. File presence and structure verified."
  - id: SCHM-13-W0
    description: "seed_designstates.cypher — Wave 0 precondition for kind-migration demo"
    verification:
      - kind: other
        ref: "grep -q 'DefState' test/seed_designstates.cypher && grep -q 'VALIDATES' test/seed_designstates.cypher"
        status: pass
    human_judgment: true
    rationale: "Seed script requires manual execution against dev Neo4j. File presence and structural correctness verified."

duration: 12min
completed: 2026-07-03
status: complete
---

# Phase 14 Plan 03: Read-Side Backward-Compact Patch and Wave 0 Harness

**Extended Neo4jRuleRepository coalesce for v4 Rule-property names (SWRL/RuleName/RuleDescription, new-before-old), three Wave 0 test/seed scripts for downstream plans**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-03T10:30:00Z
- **Completed:** 2026-07-03T10:42:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Extended three coalesce chains in `Neo4jRuleRepository.cs` to list new PascalCase properties first (D-06): `r.RuleName` before `r.title`/`r.name`/`r.Rule_Id`, `r.RuleDescription` before `r.description`, `r.SWRL` before `r.swrl`/`r.text`
- Created `test/smoke_rules_ingest.sh` — live-ingest smoke test that posts a rule to the n8n webhook and asserts the written Rule node carries `.SWRL`
- Created `test/smoke_graph_query.sh` — graph-query smoke test that posts an NL query and asserts the generated Cypher references `r.SWRL`
- Created `test/seed_designstates.cypher` — inserts 6 pre-v4 DesignState nodes (3 DefState + 2 ObjectState Run-linked, 1 orphaned DefState) at graph='Metagraph' so the 14-06 kind-migration exercises rename/layer-move/orphan-delete on real data
- All three scripts carry the n8n re-import gotcha header documenting the `import:workflow` + `id`-field workaround

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Neo4jRuleRepository coalesce for renamed Rule props (D-06)** - `5eab257` (feat)
2. **Task 2: Create the two live-smoke scripts (Wave 0 harness for SCHM-09 / SCHM-10)** - `58fdb95` (feat)
3. **Task 3: Create the DesignState seeding script (Wave 0 precondition for SCHM-13)** - `ad702da` (feat)

## Files Created/Modified

- `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` — Modified: three coalesce chains extended for backward-compat with new PascalCase Rule property names
- `test/smoke_rules_ingest.sh` — Created: live-ingest smoke test for SCHM-09 verification
- `test/smoke_graph_query.sh` — Created: graph-query smoke test for SCHM-10 verification
- `test/seed_designstates.cypher` — Created: DesignState seeding script for SCHM-13 migration precondition

## Decisions Made

- **Description coalesce also extended to RuleDescription** — The plan's D-06 mandated the name and swrl lines; RESEARCH recommended the description line as an additive third change, which is consistent with the same backward-compat contract and directly enabled by the n8n `Annotate Graph Props` RuleDescription backfill. Implemented here.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 harness complete: Plans 14-04 (live-smoke verify) can consume `smoke_rules_ingest.sh` and `smoke_graph_query.sh` immediately.
- Plan 14-06 (kind-migration demo) can consume `seed_designstates.cypher` immediately.
- All downstream plans must run `chmod +x test/*.sh` if the executable bit was lost during checkout.

---
*Phase: 14-graph-schema-v4-propagation*
*Completed: 2026-07-03*
