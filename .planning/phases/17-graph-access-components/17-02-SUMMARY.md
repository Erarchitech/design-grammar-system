---
phase: 17-graph-access-components
plan: 02
subsystem: DG Grasshopper Plugin
tags:
  - graph-access-components
  - METAGRAPH
  - Objects
  - Cypher
  - repository
requires:
  - 17-01 (CONNECTOR + GRAPH DECONSTRUCT handle types)
provides:
  - IRuleRepository.GetObjectsAsync (interface)
  - GetObjectsAsync implementation (Neo4jRuleRepository)
  - MetagraphComponent Objects + ObjectName outputs
  - OntologyClass public wrapper
affects:
  - DG/src/DG.Core/Data/IRuleRepository.cs
  - DG/src/DG.Core/Data/Neo4jRuleRepository.cs
  - DG/src/DG.Core/Models/OntologyClass.cs
  - DG/src/DG.Grasshopper/PublicTypes.cs
  - DG/src/DG.Grasshopper/Components/MetagraphComponent.cs
  - DG/tests/DG.Tests/ObjectsQueryTests.cs
tech-stack:
  added:
    - Cypher REFERS_TO->Class query with DISTINCT dedup
  patterns:
    - Parallel async query pattern (WhenAll on Rules + Objects)
    - Repository single-async-method pattern
    - Public wrapper inheritance for GH output types
key-files:
  created:
    - DG/tests/DG.Tests/ObjectsQueryTests.cs
  modified:
    - DG/src/DG.Core/Data/IRuleRepository.cs
    - DG/src/DG.Core/Data/Neo4jRuleRepository.cs
    - DG/src/DG.Core/Models/OntologyClass.cs
    - DG/src/DG.Grasshopper/PublicTypes.cs
    - DG/src/DG.Grasshopper/Components/MetagraphComponent.cs
decisions:
  - OntologyClass unsealed in Core to permit public wrapper inheritance (matches existing pattern for Rule, Variable, etc.)
  - _objectsLoadTask typed explicitly as DG.Core.Models.OntologyClass to resolve namespace ambiguity with DG.OntologyClass public wrapper
  - GetObjectsAsync creates its own driver+session per existing GetRulesAsync pattern (no session sharing across parallel calls)
duration: 6m
completed_date: 2026-07-04
status: complete
---

# Phase 17 Plan 02: METAGRAPH Objects Output — Summary

Extend the METAGRAPH component and its backing repository to output Objects (Class nodes referenced by rules via REFERS_TO edges) alongside the existing Rules output. Objects are deduplicated by Class IRI (Cypher DISTINCT) and ordered by label. Both queries run as parallel async tasks sharing one CancellationTokenSource.

## Tasks Executed

### Task 1: Extend IRuleRepository and Neo4jRuleRepository with GetObjectsAsync

**Status:** Complete

**Changes:**
- Added `GetObjectsAsync(ConnectionInfo, CancellationToken)` to `IRuleRepository` interface
- Added `ObjectsQuery` private const with REFERS_TO->Class Cypher traversal (D-02)
- Query uses `DISTINCT` to deduplicate Classes referenced by multiple rules
- Query is parameterized with `$project` and ordered by `c.label`
- Unsealed `OntologyClass` in Core (was `sealed`, needed for public wrapper inheritance)
- Added `OntologyClass` public wrapper to `PublicTypes.cs`

**Commit:** 9fa1bc1

### Task 2: Extend MetagraphComponent with Objects output

**Status:** Complete

**Changes:**
- Added `_latestObjects` and `_objectsLoadTask` fields
- Added 2 new output ports: Objects (index 3) and ObjectName (index 4)
- Changed input unwrap from `ConnectionInfo` to `MetagraphHandle` (with `HandleTypeUnwrapped` error message)
- Both Rules and Objects queries start as parallel async tasks via `Task.WhenAll`
- Status message now shows both rule count and object count
- Added `ToPublicOntologyClass` helper for Core-to-public wrapper conversion

**Key design note:** Rules sort by `Rule_Id`, Objects sort by `c.label` — these are independent sort keys. Cross-list positional pairing is NOT guaranteed (same Class referenced by multiple rules appears once due to DISTINCT). Downstream consumers join by IRI reference, not list position.

**Commit:** 853292b

### Task 3: Create unit tests for Objects query

**Status:** Complete

**Tests (7 total, all passing):**
- `ObjectsQuery_ShouldContainDedupKeyword` — validates DISTINCT in query string
- `ObjectsQuery_ShouldTargetMetagraphLayer` — validates graph:'Metagraph' and $project
- `ObjectsQuery_ShouldReturnIriAndLabel` — validates RETURN clause columns
- `ObjectsQuery_ShouldOrderByLabel` — validates ORDER BY clause
- `ObjectsQuery_ShouldTraverseReferstoClass` — validates REFERS_TO->(c:Class) pattern
- `OntologyClassModel_FromGetObjectsAsync_ShouldPreserveFields` — validates IRI and Label mapping
- `OntologyClassModel_ShouldHaveEmptyStringDefaults` — validates default values

**Commit:** b93bb06

## Deviations from Plan

### [Rule 2 - Missing critical functionality] OntologyClass was sealed, preventing public wrapper

**Found during:** Task 1 — build failed when adding `OntologyClass : DG.Core.Models.OntologyClass` public wrapper
**Issue:** `DG.Core.Models.OntologyClass` was declared `sealed`, which prevented the public wrapper inheritance pattern (used by all other GH output types: Rule, Variable, ParamState, ObjState, PropState, etc.)
**Fix:** Unsealed `OntologyClass` by removing `sealed` keyword
**Files modified:** `DG/src/DG.Core/Models/OntologyClass.cs`
**Commit:** 9fa1bc1

### [Rule 2 - Missing critical functionality] Namespace ambiguity between Core and DG OntologyClass

**Found during:** Task 2 — build error CS0029 (type mismatch) and CS0411 (type inference failure)
**Issue:** `OntologyClass` unqualified name resolves to `DG.OntologyClass` (public wrapper) instead of `DG.Core.Models.OntologyClass` (Core type) in the MetagraphComponent namespace context, because `DG.Grasshopper.Components` is a child of the `DG` namespace
**Fix:** Explicitly qualified `_objectsLoadTask` field type and `ToPublicOntologyClass` parameter as `DG.Core.Models.OntologyClass`
**Files modified:** `DG/src/DG.Grasshopper/Components/MetagraphComponent.cs`
**Commit:** 853292b

## Threat Surface

No new threat surface introduced beyond what the plan documented. All queries use parameterized `$project` (T-17-03 mitigated). QueryTimeout caps execution at 20s (T-17-04 accepted). Objects are ontology Classes, same sensitivity level as existing Rules output (T-17-05 accepted).

## Self-Check: PASSED

- [x] `dotnet build DG/DG.sln` — Build succeeded
- [x] `IRuleRepository` has `GetObjectsAsync` — 1 occurrence
- [x] `Neo4jRuleRepository` has `ObjectsQuery` — 2 occurrences (declaration + call)
- [x] `Neo4jRuleRepository.ObjectsQuery` contains `REFERS_TO` — verified
- [x] `Neo4jRuleRepository.ObjectsQuery` contains `DISTINCT` — verified
- [x] `MetagraphComponent` accepts `MetagraphHandle` — 2 occurrences
- [x] `MetagraphComponent` has 5 outputs (Rules, Objects, RuleName, ObjectName, Count)
- [x] ObjectsQuery unit tests pass — 7/7 passed
- [x] All 3 commits exist: 9fa1bc1, 853292b, b93bb06
