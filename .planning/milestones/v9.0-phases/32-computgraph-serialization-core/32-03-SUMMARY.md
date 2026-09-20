---
phase: 32-computgraph-serialization-core
plan: 03
subsystem: infra
tags: [csharp, dotnet, json, serialization, computgraph, system.text.json]

# Dependency graph
requires:
  - phase: 32-computgraph-serialization-core plan 01
    provides: "GH-free Computgraph object model (CgContext, Cg* entities, ParamKind/ParamDataType/IfaceType enums)"
provides:
  - "ComputgraphContextSerializer.Serialize(CgContext) : string — camelCase cgContextJson v1 writer via private DTO tree"
  - "ComputgraphContextSerializer.Deserialize(string) : CgContext — version-guarded, InvalidOperationException-wrapped reader"
  - "Deterministic collection ordering across the whole envelope (algorithms/procedures by index; patterns/parameters/interfaces/nodes/memberIds/nodeIds/warnings by StringComparer.Ordinal; wires by 4-key tuple; untagged groups by nickname)"
affects: [33-computgraph-bridge, 35-computgraph-recognition, 36-computgraph-persistence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Serializer owns a private nested DTO tree (13 DTO classes) mirroring cgContextJson v1 1:1; domain models carry zero serialization attributes"
    - "Enum-as-string mapping via switch expressions in dedicated ToDto/FromDto helper pairs (ParamKindToDto/FromDto, ParamDataTypeToDto/FromDto, IfaceTypeToDto/FromDto) — unknown string on read throws InvalidOperationException naming the bad value"
    - "Version-check-first deserialize: SchemaVersion checked immediately after JSON parse, before any FromDto mapping runs"
    - "Shared static JsonSerializerOptions (CamelCase, WriteIndented=false) mirrored verbatim from DesignStatePayloadV2Serializer"

key-files:
  created:
    - DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs
    - DG/tests/DG.Tests/ComputgraphContextSerializerTests.cs
  modified: []

key-decisions:
  - "Parameter DTO field named Kind (not ParamKind) so PropertyNamingPolicy.CamelCase emits \"kind\", matching cgContextJson v1's documented envelope (RESEARCH.md §5) rather than the behavior line's alternate \"paramKind\" wording"
  - "Enum string values kept as exact PascalCase member names (\"Variable\", \"Float\", \"Output\") for 1:1 match with the OWL-derived vocabulary, per plan's explicit discretion note"
  - "Warnings list is sorted StringComparer.Ordinal like every other collection (plan's explicit 'NodeIds/Warnings/MemberIds sorted Ordinal' instruction) even though warning order could carry sequential meaning — determinism/idempotency takes precedence per plan"
  - "Null DataType/Domain serialize as explicit JSON null (not omitted) — satisfies the behavior line's 'omits or nulls... without error' without adding JsonIgnoreCondition config"

requirements-completed: [CGSR-03]

coverage:
  - id: D1
    description: "Serialize(CgContext) emits camelCase JSON carrying schemaVersion 'cg-context-1' with object, algorithms, untagged, nodes, wires, and warnings via a private DTO tree, with deterministic ordering on every collection and enum values as PascalCase strings"
    requirement: "CGSR-03"
    verification:
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#Serialize_ShouldEmitSchemaVersionAndCamelCaseKeys"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#Serialize_ShouldEmitEnumValuesAsStrings"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#Serialize_WithMembersInReversedOrder_ShouldProduceByteIdenticalJson"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#Serialize_WithNullDataTypeAndDomain_ShouldNotThrowAndShouldNullTheKeys"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#Serialize_WhenContextIsNull_ShouldThrowArgumentNullException"
        status: pass
    human_judgment: false
  - id: D2
    description: "Deserialize(json) reverses the DTO tree with a version-check-first guard (rejects non-'cg-context-1' schemaVersion before any FromDto mapping), wraps all failures in InvalidOperationException, and Serialize(Deserialize(json)) is proven byte-idempotent — Phase 32 Success Criterion 3"
    requirement: "CGSR-03"
    verification:
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#Deserialize_RoundTrip_ShouldPreserveEntities"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#SerializeDeserialize_RoundTrip_ShouldBeIdempotent"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#Deserialize_WhenSchemaVersionIsNotCgContext1_ShouldThrow"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#Deserialize_WhenPayloadIsEmpty_ShouldThrow"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphContextSerializerTests.cs#Deserialize_WhenJsonIsMalformed_ShouldThrowInvalidOperationExceptionNotJsonException"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-18
status: complete
---

# Phase 32 Plan 03: Computgraph Context Serializer Summary

**`ComputgraphContextSerializer` — a camelCase, versioned (`cg-context-1`), idempotent JSON reader/writer for `CgContext` built on a private 13-class DTO tree, mirroring `DesignStatePayloadV2Serializer`'s conventions exactly.**

## Performance

- **Duration:** 25 min
- **Tasks:** 2
- **Files modified:** 2 (1 new source file, 1 new test file)

## Accomplishments
- `ComputgraphContextSerializer.Serialize(CgContext)` maps the full `Cg*` model tree to a private DTO tree and emits camelCase `cgContextJson v1` JSON — `schemaVersion`, `project`, `definition`, `object`, `algorithms` (with nested `procedures`/`patterns`/`parameters`/`interfaces`), `untagged`, `nodes`, `wires`, `warnings`
- Every collection in the envelope serializes in deterministic order (`OrderBy(..., StringComparer.Ordinal)` for id/GUID-keyed collections, `OrderBy(Index)` for algorithms/procedures, a 4-key tuple sort for wires) — two `CgContext`s built with members in reversed order produce byte-identical JSON
- Enum fields (`ParamKind`, `ParamDataType?`, `IfaceType`) map to/from PascalCase JSON strings via dedicated switch-expression helpers; unrecognized strings on deserialize throw `InvalidOperationException` naming the offending value
- `ComputgraphContextSerializer.Deserialize(string)` reverses the DTO tree with a version-check-first guard (`SchemaVersion != "cg-context-1"` throws before any `FromDto` mapping runs), empty/whitespace and malformed-JSON guards, both wrapped in `InvalidOperationException` — never a raw `JsonException`
- Idempotency proven: `Serialize(Deserialize(json)) == json` for the same `CgContext` — Phase 32 Success Criterion 3
- 10 passing xUnit facts in `ComputgraphContextSerializerTests`; models remain free of `[JsonPropertyName]` (confirmed via grep gate: 0 matches)

## Task Commits

Each task was committed atomically:

1. **Task 1: DTO tree + Serialize (model → DTO → camelCase JSON, deterministic ordering)** - `f84bc37` (feat)
2. **Task 2: Deserialize (JSON → DTO → model) with version guard + idempotent round-trip** - `f63f566` (feat)

**Plan metadata:** (pending — final commit below)

## Files Created/Modified
- `DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs` - Static serializer: `Serialize`/`Deserialize` public entry points, `ValidateContext`/`ValidateDeserialized` guard methods, `ToDto`/`FromDto` mapping pairs for all 13 entity shapes, private nested DTO classes
- `DG/tests/DG.Tests/ComputgraphContextSerializerTests.cs` - 10 facts: camelCase/schemaVersion presence, enum-as-string, deterministic-ordering (reversed member order), null DataType/Domain handling, null-arg guard, round-trip entity preservation, idempotency, bad-version guard, empty-payload guard, malformed-JSON guard

## Decisions Made
- `CgParameterDto.Kind` (not `ParamKind`) as the DTO property name so `PropertyNamingPolicy.CamelCase` emits `"kind"` — matches the `cgContextJson v1` envelope documented in RESEARCH.md §5 verbatim, rather than the plan behavior line's alternate `"paramKind"` phrasing
- Enum string values kept as exact PascalCase member names (`"Variable"`, `"Float"`, `"Output"`) for 1:1 alignment with the OWL-derived vocabulary — matches plan's "Claude's discretion" note
- `Warnings` sorted `StringComparer.Ordinal` alongside every other collection, per the plan's explicit "NodeIds/Warnings/MemberIds sorted Ordinal" instruction, even though warning message order could carry sequential meaning — determinism/idempotency wins per plan
- Null `DataType`/`Domain` serialize as explicit JSON `null` (not omitted via `JsonIgnoreCondition`) — satisfies "omits or nulls... without error" with the simpler of the two options

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Full `DG.Tests` suite run (267 tests) shows only 4 pre-existing failures, all `DesignStateValidationFlowTests` E2E tests requiring a live Neo4j connection on `bolt://localhost:7687` — unrelated to this plan's scope, out of scope per the deviation-rules scope boundary.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `ComputgraphContextSerializer` is ready to be consumed by Phase 33 (bridge, serves `cgContextJson v1` over HTTP), Phase 35 (recognition round-trips it), and Phase 36 (persistence reads it) — the versioned envelope contract is locked
- `dotnet build ./DG/DG.sln -c Release` succeeds cleanly (DG.Core, DG.Tests, DG.Grasshopper — 0 warnings, 0 errors)
- No blockers or concerns

---
*Phase: 32-computgraph-serialization-core*
*Completed: 2026-07-18*

## Self-Check: PASSED

Both created files (ComputgraphContextSerializer.cs, ComputgraphContextSerializerTests.cs) found on disk; both commit hashes (f84bc37, f63f566) found in git log.
