---
phase: 17-graph-access-components
plan: 03
subsystem: DG Grasshopper Plugin
tags:
  - ontology
  - graph-access
  - repository
  - component
  - async-load
  - v7-names
requires:
  - 17-01 (OntographHandle, PublicTypes base, DgIcons)
  - ontology/GH_DesignGrammars.pdf (ONTOGRAPH port spec)
provides:
  - OntoGraph read access for downstream PROPERTY STATE and VALIDATOR
affects:
  - DG/src/DG.Core/Data/
  - DG/src/DG.Grasshopper/Components/
  - DG/tests/DG.Tests/
tech-stack:
  added:
    - IOntoGraphRepository interface (3 query methods)
    - Neo4jOntoGraphRepository (3 Cypher queries targeting graph='OntoGraph')
    - OntoGraphComponent (async GH component with 3 outputs)
    - OntoGraph repository tests (9 xunit tests)
  patterns:
    - repository: single-method-per-query, ConnectionInfo + CancellationToken, IReadOnlyList<T> return
    - component: async-load with ContinueWith + ScheduleSolution (MetagraphComponent pattern)
    - tests: reflection-based query string validation
key-files:
  created:
    - DG/src/DG.Core/Data/IOntoGraphRepository.cs
    - DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs
    - DG/src/DG.Grasshopper/Components/OntoGraphComponent.cs
    - DG/tests/DG.Tests/Neo4jOntoGraphRepositoryTests.cs
  modified:
    - DG/src/DG.Core/Models/OntologyProperty.cs (unsealed for public wrapper inheritance)
    - DG/src/DG.Grasshopper/PublicTypes.cs (added OntologyProperty public wrapper)
decisions:
  - OntologyProperty unsealed in Core (matching OntologyClass pattern) to allow DG.Grasshopper public wrapper inheritance
  - GUID F8C6A4B2-1E3D-4F5A-8C7B-9D0E1F2A3B4C assigned to OntoGraphComponent (no conflict with existing components)
metrics:
  duration: "4m 27s"
  completed_date: "2026-07-04"
  tasks: 3
  files_created: 4
  files_modified: 2
  tests_added: 9
status: complete
---

# Phase 17 Plan 03: ONTOGRAPH Component and Repository

## One-liner

Created the ONTOGRAPH component and its backing repository (IOntoGraphRepository + Neo4jOntoGraphRepository) with 3 Cypher queries against `graph='OntoGraph'`, enabling architects to browse the OntoGraph layer's Class, ObjProperty, and DataProperty nodes directly from the Grasshopper canvas, with 9 unit tests validating query structure.

## Tasks Executed

### Task 1: Create IOntoGraphRepository interface and Neo4jOntoGraphRepository implementation
- **Commit:** e5b5147
- **Files:**
  - `DG/src/DG.Core/Data/IOntoGraphRepository.cs` — interface with 3 methods (GetClassesAsync, GetObjPropertiesAsync, GetDataPropertiesAsync)
  - `DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs` — sealed implementation with 3 parameterized Cypher queries
- **Key details:**
  - Each query targets `graph='OntoGraph'` with `$project` parameterized isolation
  - `ObjPropertiesQuery` uses V7 label name `ObjProperty` (not `ObjectProperty`)
  - `DataPropertiesQuery` uses V7 label name `DataProperty` (not `DatatypeProperty`)
  - All queries ORDER BY label for deterministic output
  - QueryTimeout of 20s from the established pattern (Neo4jRuleRepository)

### Task 2: Create OntoGraphComponent (async GH component, 3 outputs)
- **Commit:** 54f268c
- **Files:**
  - `DG/src/DG.Grasshopper/Components/OntoGraphComponent.cs` — full async-load component
  - `DG/src/DG.Core/Models/OntologyProperty.cs` — unsealed (was sealed, blocked public wrapper inheritance)
  - `DG/src/DG.Grasshopper/PublicTypes.cs` — added `OntologyProperty : DG.Core.Models.OntologyProperty`
- **Key details:**
  - Inputs: OntographHandle (from GRAPH DECONSTRUCT), Refresh (Boolean trigger)
  - Outputs: Class, ObjProperties, DataProperties (all generic lists)
  - Follows MetagraphComponent async pattern: parallel task execution, ContinueWith + ScheduleSolution
  - Graceful handling: disconnected handle, refresh=false, errors, cancellation

### Task 3: Create unit tests for ONTOGRAPH repository queries
- **Commit:** b84294b
- **Files:**
  - `DG/tests/DG.Tests/Neo4jOntoGraphRepositoryTests.cs` — 9 test methods
- **Key details:**
  - 9 facts: ClassesQuery targeting, V7 label names, ORDER BY, parameterized $project, interface implementation, model field preservation, default values
  - Uses reflection-based private constant access (same pattern as ObjectsQueryTests)
  - All 9 pass

## Success Criteria Check

| Criterion | Status |
|-----------|--------|
| GHGA-04: ONTOGRAPH outputs Class / ObjProperties / DataProperties | Done |
| All 3 queries target `graph='OntoGraph'` with correct V7 label names | Verified |
| Component follows async-load pattern (ContinueWith + ScheduleSolution) | Verified |
| Empty OntoGraph layer returns empty lists (not errors) | Implemented via empty list handling |
| All 3 queries `ORDER BY c.label` | Verified |
| `DOTNET ROLL_FORWARD=LatestMajor` | n/a (net9.0 project, SDK 10.0, tests pass) |

## Verification

- `dotnet build DG/DG.sln` — passes (0 warnings, 0 errors)
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~OntoGraphRepository"` — 9/9 passed

## Deviations

### Plan Execution Additions

1. **Unsealed OntologyProperty in Core** — `OntologyProperty` was sealed in `DG.Core.Models`, preventing the DG.Grasshopper public wrapper from inheriting it. Unsealed to match the `OntologyClass` pattern (which was already unseated). Found during Task 2 build validation.

2. **Added OntologyProperty public wrapper to PublicTypes.cs** — The plan's Task 2 note anticipated this: "If OntologyProperty and OntologyClass don't have public wrappers... add them." The `OntologyClass` wrapper existed (from Plan 01) but `OntologyProperty` was missing. Added `public class OntologyProperty : DG.Core.Models.OntologyProperty`.

These are not bugs — they follow the same pattern established in Plan 01 for `OntologyClass` and complete the missing public wrapper.

## Threat Surface

No new threat surface beyond the planned STRIDE register:

| Threat ID | Category | Disposition | Status |
|-----------|----------|-------------|--------|
| T-17-06 | Tampering | mitigate (parameterized $project) | All queries use $project |
| T-17-07 | Information Disclosure | accept — ontology metadata | Component outputs Class/ObjProperties/DataProperties |
| T-17-08 | Denial of Service | accept — QueryTimeout 20s | Implemented on all 3 queries |

## Artifacts

| Symbol | Kind | File |
|--------|------|------|
| `IOntoGraphRepository` | interface (NEW) | DG/src/DG.Core/Data/IOntoGraphRepository.cs |
| `IOntoGraphRepository.GetClassesAsync` | method (NEW) | DG/src/DG.Core/Data/IOntoGraphRepository.cs |
| `IOntoGraphRepository.GetObjPropertiesAsync` | method (NEW) | DG/src/DG.Core/Data/IOntoGraphRepository.cs |
| `IOntoGraphRepository.GetDataPropertiesAsync` | method (NEW) | DG/src/DG.Core/Data/IOntoGraphRepository.cs |
| `Neo4jOntoGraphRepository` | sealed class (NEW) | DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs |
| `Neo4jOntoGraphRepository.ClassesQuery` | private const string (NEW Cypher) | DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs |
| `Neo4jOntoGraphRepository.ObjPropertiesQuery` | private const string (NEW Cypher) | DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs |
| `Neo4jOntoGraphRepository.DataPropertiesQuery` | private const string (NEW Cypher) | DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs |
| `DG.Grasshopper.Components.OntoGraphComponent` | class (NEW GH component) | DG/src/DG.Grasshopper/Components/OntoGraphComponent.cs |

## Self-Check

- [x] All task commits verified in git log
- [x] Build succeeded (0 errors, 0 warnings)
- [x] Tests passed (9/9)
- [x] All created files exist on disk
- [x] No unexpected file deletions
