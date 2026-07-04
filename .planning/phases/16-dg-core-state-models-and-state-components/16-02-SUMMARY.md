---
phase: 16-dg-core-state-models-and-state-components
plan: 02
subsystem: core-services
tags: [id-generator, sha256, content-addressed, dg-core, csharp, xunit]

requires:
  - plan: 16-01
    provides: [ObjState, ParamState, PropState, DesignState models]

provides:
  - ComputeParamStateId (renamed from ComputeDefStateId, same DS_ prefix, same logic)
  - ComputePropStateId (PS_ prefix, SHA-256 hash over ruleIri|dataPropertyIri|propValueLex)
  - ComputeDesignStateId (DS_ prefix, SHA-256 hash over sorted member StateIds)
  - ComputeObjectStateId preserved unchanged (OS_ prefix)
  - ComputeObjectInstanceId removed (OI_ prefix constant removed)
  - IdRefPrefix constant preserved unchanged
  - 10 unit tests: 2 ComputeParamStateId, 3 ComputeObjectStateId, 3 ComputePropStateId, 2+1 ComputeDesignStateId

affects: [16-05-state-components, 16-06-designstate-component, future Phase 18 validator]

tech-stack:
  added: []
  patterns:
    - SHA-256 content-addressed IDs with 16-char hex prefixes
    - Deterministic sorting for order-independent hashing
    - Type-specific value formatting (Number "R" round-trip, Integer/Boolean invariant)
  modified:
    - DesignStateIdGenerator.cs

key-files:
  modified:
    - DG/src/DG.Core/Services/DesignStateIdGenerator.cs
    - DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs

deviation-log: []

## What was built

Updated DesignStateIdGenerator to support Phase 16 state models:

- **ComputeParamStateId** (renamed): Same deterministic hash over sorted parameter ID+value pairs, DS_ prefix unchanged
- **ComputePropStateId** (new): PS_ prefix, hash input = ruleIri|dataPropertyIri|propValueLex where lex is type-formatted value string
- **ComputeDesignStateId** (new): DS_ prefix, hash input = concatenated sorted member StateIds
- **ComputeObjectInstanceId** removed: OI_ prefix constant and method deleted
- **Prefix constants**: DefStatePrefix → ParamStatePrefix (value DS_), PropStatePrefix (PS_), DesignStatePrefix (DS_) added, ObjectStatePrefix (OS_) and IdRefPrefix (IDR_) preserved

## Self-Check: PASSED

- Build: passes (net9.0, Release configuration)
- Tests: 10/10 tests pass
- Determinism: order-independent hashing verified for both ComputeParamStateId and ComputeDesignStateId
- Backward compat: ComputeObjectStateId unchanged, existing tests preserved
