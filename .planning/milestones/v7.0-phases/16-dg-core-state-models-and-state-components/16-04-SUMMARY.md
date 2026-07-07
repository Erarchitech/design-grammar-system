---
phase: 16
plan: 04
status: complete
started: 2026-07-04
completed: 2026-07-04
tasks_total: 2
tasks_completed: 2
commits:
  - feat(16-04): create DesignStatePayloadV2Serializer with v2 versioned envelope
  - test(16-04): add v2 serializer round-trip and rejection tests
key-files:
  created:
    - DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs
    - DG/tests/DG.Tests/DesignStatePayloadV2SerializerTests.cs
---

## What was built

DesignStatePayloadV2Serializer — a static class in `DG.Core.Serialization` that serializes/deserializes `DesignState` aggregates to/from a versioned JSON envelope.

### Envelope structure
```json
{
  "version": "2",
  "stateId": "DS_abc123def4567890",
  "capturedAtUtc": "2026-07-04T10:00:00.0000000Z",
  "objStates": [{ "stateId": "...", "objectRef": "...", "label": "...", "capturedAtUtc": "..." }],
  "paramStates": [{ "stateId": "...", "capturedAtUtc": "...", "parameters": [...] }],
  "propStates": [{ "stateId": "...", "ruleIri": "...", "dataPropertyIri": "...", "propValue": {...} }]
}
```

### Key design decisions
- **Clean break from v1** (D-06/D-07): new class, no reference to `DesignStateJsonSerializer`. Private DTOs are duplicated (not shared) — acceptable per plan.
- **Geometry excluded** from ObjState DTO per PROJECT.md.
- **Deterministic output**: sub-arrays sorted by StateId; parameters sorted by ParameterId.
- **Version validation**: rejects missing version, version "1", or any non-"2" value with `InvalidOperationException`.
- **TDD**: Task 1 (serializer) implemented, Task 2 (tests) written — 9 tests covering round-trip, parameter preservation, version rejection, empty/malformed JSON, and timestamp validation.

### Test results
- **9/9** new tests pass
- **118/119** total tests pass (1 pre-existing E2E test fails — requires running Docker services)

## Deviations
None.

## Self-Check: PASSED
