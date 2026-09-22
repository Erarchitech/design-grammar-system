---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 10
subsystem: validation
tags: [csharp, evidence-envelope, verdict-rollup, code-review-gap-closure, dg-core]

# Dependency graph
requires:
  - phase: 1202 (plans 01, 05, 13)
    provides: PerObjectVerdict/PerObjectVerdictResult/VerdictSource types, BuildPerObjectVerdicts rollup, spec/EVIDENCE-CONTRACT.md §5.1
provides:
  - Additive duplicate-identity signal on the canonical C# per-object verdict read path (HasDuplicateRuleObjectRows, CollidingRuleObjectPairs)
  - (RuleId, ObjectId)-first collision detection inside BuildPerObjectVerdicts, feeding the unchanged D-12 rollup
  - spec/EVIDENCE-CONTRACT.md §5.1 subsection reconciling §4's row-identity rule with the C# reader's behavior
affects: [1202-11, any future consumer of GetPerObjectVerdictsAsync on the Grasshopper canvas]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive result-type extension over enum-member growth (VerdictSource stays 2 members; new signal lives on PerObjectVerdict/PerObjectVerdictResult) for orthogonal provenance-vs-integrity axes"
    - "Single materialized row sequence feeding both a detection pass and the unchanged StatusRollup.Rollup call, so flag and status can never describe different row sets"

key-files:
  created: []
  modified:
    - DG/src/DG.Core/Data/IValidGraphRepository.cs
    - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
    - DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs
    - spec/EVIDENCE-CONTRACT.md

key-decisions:
  - "CR-01 fix option (a) detect-and-surface, via an additive property (HasDuplicateRuleObjectRows / CollidingRuleObjectPairs) rather than a third VerdictSource enum member — duplicate-row identity is a data-quality fact about a present envelope, not a change in provenance"
  - "Property names: PerObjectVerdict.HasDuplicateRuleObjectRows (bool, default false), PerObjectVerdictResult.CollidingRuleObjectPairs (IReadOnlyList<RuleObjectPair>, default empty), new sealed record RuleObjectPair(string RuleId, string ObjectId) in IValidGraphRepository.cs"
  - "BuildPerObjectVerdicts materializes envelope.Rows once, groups by composite (RuleId, ObjectId) via an explicit ordinal PairOrdinalComparer before the existing ObjectId-level StatusRollup.Rollup grouping — same row sequence feeds both passes so the flag and the status can never diverge"
  - "No spec/DATABASE.md change: the stored evidenceEnvelopeJson shape is unchanged (reader-side-only behavior); spec/DATABASE.md:158 already delegates that property's content authority to spec/EVIDENCE-CONTRACT.md, which received the scoped §5.1 addition instead"

requirements-completed: [ALGN12-10]

coverage:
  - id: D1
    description: "PerObjectVerdict/PerObjectVerdictResult gain an additive, defaulted duplicate-identity signal (HasDuplicateRuleObjectRows, CollidingRuleObjectPairs); VerdictSource unchanged at 2 members"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "dotnet build DG/src/DG.Core/DG.Core.csproj -c Release"
        status: pass
      - kind: unit
        ref: "grep -c 'EvidenceEnvelope,' DG/src/DG.Core/Data/IValidGraphRepository.cs (returns 1)"
        status: pass
    human_judgment: false
  - id: D2
    description: "BuildPerObjectVerdicts groups by (RuleId, ObjectId) before the ObjectId rollup, detects collisions, and still calls StatusRollup.Rollup exactly once over every row including duplicates"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release"
        status: pass
      - kind: unit
        ref: "grep -vn '^\\s*//' DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs | grep -c 'StatusRollup.Rollup' (returns 1)"
        status: pass
      - kind: unit
        ref: "DG.Tests#BuildPerObjectVerdicts_WithDuplicateRuleObjectPairRows_FlagsTheCollisionAndStillRollsUp"
        status: pass
      - kind: unit
        ref: "DG.Tests#BuildPerObjectVerdicts_WithDuplicateRuleObjectPairRows_DoesNotThrowOrDegrade"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-12 cross-rule rollup provably unchanged: existing Facts extended in place with negative collision assertions, not duplicated"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "DG.Tests#BuildPerObjectVerdicts_WithMixedRows_KeepsObjectVerdictsDistinct"
        status: pass
      - kind: unit
        ref: "DG.Tests#BuildPerObjectVerdicts_WithMultipleRowsPerObject_RollsUpByStatusRollupPrecedence"
        status: pass
    human_judgment: false
  - id: D4
    description: "Absence (null/malformed envelope) never implies a collision"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "DG.Tests#BuildPerObjectVerdicts_WithNullEnvelope_ReportsNotEvaluatedAndEnvelopeAbsent"
        status: pass
      - kind: unit
        ref: "DG.Tests#BuildPerObjectVerdicts_WithMalformedJson_DegradesToEnvelopeAbsent"
        status: pass
    human_judgment: false
  - id: D5
    description: "spec/EVIDENCE-CONTRACT.md §4 and §5.1 no longer read as contradictory: §5.1 records the C# reader's detection behavior; §4 gets a one-sentence forward pointer; frozen sections (§1/§3/§6) untouched"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "grep -c 'ruleId, objectId' spec/EVIDENCE-CONTRACT.md (2 -> 4, increased)"
        status: pass
      - kind: unit
        ref: "git diff --numstat spec/EVIDENCE-CONTRACT.md (24 insertions, 1 deletion)"
        status: pass
    human_judgment: false

# Metrics
duration: ~25min
completed: 2026-09-22
status: complete
---

# Phase 1202 Plan 10: (RuleId, ObjectId) Duplicate-Row Detection for Per-Object Verdicts Summary

**BuildPerObjectVerdicts now detects and reports evidence rows that collide on the `(ruleId, objectId)` identity pair, closing REVIEW CR-01 (gap 1) via an additive flag rather than a new VerdictSource enum member.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments

- `PerObjectVerdict` gained a defaulted-`false` `HasDuplicateRuleObjectRows` property and `PerObjectVerdictResult` gained a defaulted-empty `CollidingRuleObjectPairs` collection (new `RuleObjectPair` record), both doc-commented against CR-01 and `spec/EVIDENCE-CONTRACT.md` §4. `VerdictSource` confirmed unchanged at exactly 2 members.
- `BuildPerObjectVerdicts` restructured to group `envelope.Rows` by the composite `(RuleId, ObjectId)` identity (ordinal, via an explicit `PairOrdinalComparer`) before the existing ObjectId-level rollup. Collisions are detected and reported; `StatusRollup.Rollup` is still called exactly once, over every row including duplicates — the D-12 rollup output is byte-for-byte unchanged. A duplicate-pair envelope still returns `EnvelopePresent = true` with a complete, usable verdict list — no degrade, no throw.
- `spec/EVIDENCE-CONTRACT.md` §5.1 gained a subsection stating the C# reader's detection behavior in five parts (cross-rule case unchanged, duplicate detection named by property, flag-not-degrade, Python-leg parity, closes CR-01/gap 1); §4 gained a one-sentence forward pointer. `spec/DATABASE.md` deliberately left untouched (see Decisions).
- Two existing `BuildPerObjectVerdicts` Facts extended in place with negative duplicate-collision assertions (regression guard for D-12); both degrade Facts extended to assert `CollidingRuleObjectPairs` stays empty; two new Facts added for the review's concrete duplicate-pair example, one asserting the flag/rollup/pair contents and one asserting no-throw-no-degrade.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the additive duplicate-identity signal to the verdict contract types** - `5e3a045` (feat)
2. **Task 2: Group by (RuleId, ObjectId) first in BuildPerObjectVerdicts, detect collisions, rewrite doc-comment** - `681727b` (feat)
3. **Task 3: Propagate the detection behavior into spec/EVIDENCE-CONTRACT.md §5.1** - `2400318` (docs)
4. **Task 4: Extend the existing BuildPerObjectVerdicts Facts with the regression guard and the duplicate-pair Fact** - `7427d31` (test)

_Note: no TDD RED/GREEN split was applicable here — the plan's `tdd="true"` tasks extended already-passing production code with additive members and an in-place test extension, not a fresh RED-first feature; each task's own build/test verification substitutes for a separate RED commit._

## Files Created/Modified

- `DG/src/DG.Core/Data/IValidGraphRepository.cs` - New `RuleObjectPair` record; `PerObjectVerdict.HasDuplicateRuleObjectRows`; `PerObjectVerdictResult.CollidingRuleObjectPairs`; extended `VerdictSource` and `GetPerObjectVerdictsAsync` doc-comments
- `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` - `BuildPerObjectVerdicts` restructured to detect `(RuleId, ObjectId)` collisions before the unchanged ObjectId rollup; new private `PairOrdinalComparer`; doc-comment rewritten to cover both the cross-rule and duplicate-identity cases
- `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs` - Four existing Facts extended in place; two new Facts (`BuildPerObjectVerdicts_WithDuplicateRuleObjectPairRows_FlagsTheCollisionAndStillRollsUp`, `BuildPerObjectVerdicts_WithDuplicateRuleObjectPairRows_DoesNotThrowOrDegrade`)
- `spec/EVIDENCE-CONTRACT.md` - §5.1 gained a new subsection recording the C# reader's duplicate-detection behavior; §4 gained a one-sentence forward pointer to it

## Decisions Made

- **Additive flag over new `VerdictSource` member (the plan's own load-bearing call, restated here for traceability):** a duplicate-pair row set is still sourced from the evidence envelope, so provenance is unchanged; modeling the collision as a third enum member would break the `Source == EvidenceEnvelope` ⟺ "envelope was readable" invariant every existing caller can rely on today, and would conflate two orthogonal axes (provenance × row integrity) into one enum.
- **`spec/DATABASE.md` needs no change.** The stored `evidenceEnvelopeJson` shape is byte-for-byte unchanged by this plan — only the C# reader's interpretation of already-stored rows changed. `spec/DATABASE.md:158` already delegates that property's content authority to `spec/EVIDENCE-CONTRACT.md`, which received the scoped §5.1 addition. This satisfies the CLAUDE.md Schema Change Propagation duty by confirming no propagation to `spec/DATABASE.md` is required, rather than silently skipping the check.
- **Explicit `PairOrdinalComparer` over the default tuple `EqualityComparer`.** The default `(string, string)` tuple comparer already uses ordinal string equality via each component's own `Equals`, but an explicit comparer makes the ordinal intent visible and auditable at the call site rather than relying on an implicit default — matches the plan's action text ("if the executor prefers an explicit comparer, it must be ordinal on both components").

## Deviations from Plan

None — plan executed exactly as written. Property names (`HasDuplicateRuleObjectRows`, `CollidingRuleObjectPairs`, `RuleObjectPair`) were chosen at the executor's discretion per the plan's explicit delegation ("the executor picks the final spelling") and used consistently across Task 1's types, Task 2's producer, and Task 4's Facts.

## Issues Encountered

None. `dotnet build DG/DG.sln -c Release` succeeded with 0 warnings / 0 errors after Task 2. The filtered `BuildPerObjectVerdicts` test run (6 Facts) and the full `DG.Tests` run were both fully green on the first attempt.

## Test Results

- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~BuildPerObjectVerdicts"`: **6/6 passing** (0 failed, 0 skipped).
- `dotnet test DG/tests/DG.Tests/`: **545/545 passing** (0 failed, 0 skipped). The `DesignStateValidationFlowTests` environment-dependent baseline (documented as "4 failures when Neo4j is down") was also run in isolation and showed **4/4 passing** — the local Docker/Neo4j compose stack was reachable during this session, so the known-baseline failures did not manifest. No failure names to report; there were no failures of any kind.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-01 (REVIEW gap 1) is closed: the canonical C# per-object read path now detects and reports `(ruleId, objectId)` duplicate rows rather than silently absorbing them, matching the Python leg's `compare_legs` posture.
- No canvas component currently consumes `GetPerObjectVerdictsAsync` (confirmed in the plan's own blast-radius analysis), so this additive signal costs nothing downstream today and is available the moment one is wired.
- Independent of sibling gap-closure plan 1202-11 (no file overlap); no blockers for that plan or for phase-level re-verification.

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Completed: 2026-09-22*
