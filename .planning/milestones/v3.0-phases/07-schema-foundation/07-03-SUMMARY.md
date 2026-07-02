---
phase: 07-schema-foundation
plan: 03
subsystem: api
tags: [csharp, dotnet, cypher, neo4j, migration, dg-core]

# Dependency graph
requires:
  - phase: 07-01
    provides: VariableKind enum, Variable.Kind nullable property, VariableTypeInferrer.Infer(Rule, string) static classifier
provides:
  - cypher_template.txt with fixed Var MERGE key (name+project) and SCHEMA VERSION v3.1 stamp
  - DesignState {StateId, project, kind} MERGE block in cypher_template.txt
  - migrations/2026-06-23_var_project_merge_key.cypher one-time backfill script
  - Neo4jRuleRepository.PopulateVariables wired to VariableTypeInferrer.Infer (Variable.Kind populated on every loaded rule)
affects: [07-04 (n8n workflow JSON schema propagation must mirror SCHEMA VERSION v3.1), Phase 8 (OBJECT STATE component consumes Variable.Kind), Phase 9 (DesignState node shape), Phase 10 (CLASSIFICATOR consumes Variable.Kind)]

# Tech tracking
tech-stack:
  added: []
  patterns: [InternalsVisibleTo test seam for private static repository logic, idempotent coalesce()-based Cypher migration script]

key-files:
  created:
    - migrations/2026-06-23_var_project_merge_key.cypher
    - DG/tests/DG.Tests/Neo4jRuleRepositoryVariableKindTests.cs
  modified:
    - cypher_template.txt
    - DG/src/DG.Core/Data/Neo4jRuleRepository.cs
    - DG/src/DG.Core/DG.Core.csproj

key-decisions:
  - "Var MERGE key fix scoped strictly to Var node type per CONTEXT.md - Class/Atom/DatatypeProperty/ObjectProperty/Builtin/Literal MERGE blocks left untouched even though they share the same name-only-key pattern"
  - "New DesignState block includes project in the MERGE key from the start (StateId + project together) - does not repeat the Var bug on the new node type"
  - "Migration script only tags currently-untagged orphan Var nodes via coalesce() - does not attempt to split already cross-contaminated nodes (no audit trail exists to reconstruct correct ownership); documented as accepted scope limit per threat_model T-07-07"
  - "PopulateVariables made testable via an internal PopulateVariablesForTesting wrapper + InternalsVisibleTo DG.Tests, rather than changing GetRulesAsync's public surface or requiring a live Neo4j connection for unit tests"
  - "AtomsQuery/RulesQuery left unchanged - both already filter by project:$project at the Rule/Atom match level; the Var bug is a storage-layer MERGE-key issue, not a query-layer filtering issue"

patterns-established:
  - "Repository-internal logic that needs direct unit-test coverage without a live DB dependency is exposed via an internal *ForTesting wrapper + InternalsVisibleTo, not by changing its access modifier to public"

requirements-completed: [SCHM-01, SCHM-02]

# Metrics
duration: 18min
completed: 2026-06-23
status: complete
---

# Phase 7 Plan 03: Var Merge-Key Fix, DesignState Block, Migration Script, and Variable.Kind Wiring Summary

**Fixed the latent cross-project Var MERGE-key collision bug (SCHM-02), added the DesignState{kind} MERGE block (SCHM-01), shipped a one-time backfill migration script, and wired Neo4jRuleRepository.PopulateVariables to VariableTypeInferrer so Variable.Kind is populated on every rule read from Neo4j**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-06-23T00:58:17Z
- **Tasks:** 2 completed
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- `cypher_template.txt`'s `vEntity`/`vValue` Var MERGE patterns now include `project` inside the MERGE braces alongside `name` — eliminates the cross-project Var node collision described in PITFALLS.md Pitfall 4
- New `:DesignState {StateId, project}` MERGE block added (structurally parallel to the existing `Rule.kind` pattern), with `project` in the MERGE key from the start — Phase 9-11 components now have an exact node shape to target
- `GRAPH SCHEMA` documentation section updated: `Var` key now documented as `name + project`; new `DesignState` entry added
- `SCHEMA VERSION: v3.1` stamp added as the anchor 07-04 will mirror into the n8n workflow JSON (Pitfall 9 prevention)
- `migrations/2026-06-23_var_project_merge_key.cypher` created — first migration script in the repo; backfills missing `project` via `coalesce()`, documents the audit query for already-cross-contaminated nodes (not auto-resolved, by design), and embeds the verification query
- `Neo4jRuleRepository.PopulateVariables` now calls `VariableTypeInferrer.Infer(rule, variableName)` for every variable on every loaded rule and assigns the result to `Variable.Kind`, with `null` correctly propagated (not coalesced) for Builtin-only variables
- 3 new unit tests cover all 3 plan behavior cases: Object-kind via ClassAtom subject, Property-kind via DataPropertyAtom value-only, and null propagation for Builtin-only variables

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Var merge key and add DesignState block, write migration script** - `603f47d` (fix)
2. **Task 2: Wire PopulateVariables to VariableTypeInferrer** - `d8bebbf` (test, RED) + `9584e1c` (feat, GREEN)

**Plan metadata:** (this commit)

_Note: Task 2 used the TDD test→feat commit split per the plan's `tdd="true"` marker. RED was confirmed via a genuine compile failure (CS0117 — `PopulateVariablesForTesting` did not exist), not a logic-only failure._

## Files Created/Modified
- `cypher_template.txt` - fixed Var MERGE key (name+project), new DesignState MERGE block, SCHEMA VERSION v3.1 stamp, updated GRAPH SCHEMA doc section
- `migrations/2026-06-23_var_project_merge_key.cypher` - one-time backfill script (new `migrations/` directory, first precedent in repo)
- `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` - `PopulateVariables` final loop now calls `VariableTypeInferrer.Infer`; added `internal static PopulateVariablesForTesting` test seam
- `DG/src/DG.Core/DG.Core.csproj` - added `InternalsVisibleTo` for `DG.Tests`
- `DG/tests/DG.Tests/Neo4jRuleRepositoryVariableKindTests.cs` - 3 xUnit tests covering the plan's behavior cases

## Decisions Made
- Used an `internal static PopulateVariablesForTesting` wrapper around the existing `private static PopulateVariables` plus `InternalsVisibleTo` rather than making `PopulateVariables` public or requiring a live Neo4j connection in tests — keeps `IRuleRepository`'s public contract unchanged while making the extraction/inference logic directly unit-testable, consistent with the plan's instruction not to touch `AtomsQuery`/`RulesQuery`
- Migration script written as a standalone `.cypher` file (not a data-service endpoint or inline `cypher-shell` one-liner) per CONTEXT.md's discretion note — no migration-script precedent existed yet in the repo, so this establishes the convention: header comment with purpose/execution method/scope-limitation warning, the idempotent `coalesce()` backfill statement, a documented (not auto-executed) audit query, and a documented verification query

## Deviations from Plan

None - plan executed exactly as written. No Rule 1-4 deviations triggered.

## Issues Encountered

None. The .NET SDK (10.0.109) was available in this environment, so all build/test verification used real `dotnet build`/`dotnet test` commands.

Full test suite run after Task 2: 76 passed, 4 failed — the 4 failures are the pre-existing `DG.Tests.E2E.DesignStateValidationFlowTests` cases requiring a live Neo4j at `bolt://localhost:7687` (Docker stack not running in this environment), consistent with the environment note and the same failures documented in 07-02-SUMMARY.md. No regressions introduced by this plan's changes.

The plan's manual verification step (running the migration script against a live Neo4j instance and confirming `MATCH (v:Var) WHERE NOT EXISTS(v.project) RETURN count(v)` returns 0) was explicitly deferred to live-environment/phase verification per the plan's `<verification>` section — not executable in this environment since the Docker Neo4j stack is not running. The migration script's content and logic were verified via inspection and the grep-based done-criteria, consistent with the environment note's guidance.

## User Setup Required

To complete the Var merge-key migration in a live environment:
1. Ensure the Docker Neo4j stack is running (`docker compose up -d neo4j`)
2. Run `migrations/2026-06-23_var_project_merge_key.cypher` via `cypher-shell` or Neo4j Browser
3. Verify with `MATCH (v:Var) WHERE NOT EXISTS(v.project) RETURN count(v)` — expect 0
4. Optionally run the audit query embedded in the script's comments to identify any already-cross-contaminated Var nodes requiring manual remediation (not auto-resolved by this script)

## Next Phase Readiness

- `cypher_template.txt` is ready for 07-04's n8n workflow JSON schema propagation — the `SCHEMA VERSION: v3.1` stamp is the anchor to mirror
- `Neo4jRuleRepository.PopulateVariables` now populates `Variable.Kind` on every rule read from Neo4j, ready for Phase 8 (OBJECT STATE component) and Phase 10 (CLASSIFICATOR) to consume
- The `:DesignState {kind}` MERGE block in `cypher_template.txt` establishes the exact node shape Phase 9-11 components will MERGE into Neo4j
- The migration script is ready to run against a live Neo4j instance whenever the Docker stack is available; this is tracked as a deferred manual verification step, not a blocker for subsequent phase planning

---
*Phase: 07-schema-foundation*
*Completed: 2026-06-23*

## Self-Check: PASSED

All 4 created/modified key files verified present on disk; all 3 commit hashes (603f47d, d8bebbf, 9584e1c) verified present in git log.
