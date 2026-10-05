---
tags: [debugging, reinstate, validgraph, serialization, grasshopper, fixed]
date: 2026-10-05
status: fixed-2026-10-05-install-pending
---

# Reinstate from ValidGraph read null parameters and wrote zeros into sliders (F23, F24, F25)

## Symptom (test v12-hexagonal-facade-01, step 8)

The canvas chain was VALIDATION GRAPH (44 runs, 4 Design States) → DESIGN STATE DECONSTRUCT → List Item → PARAMETER REINSTATE (Target = PARAMETER STATE).

Reinstating V2 (`DS_6FA0FBE79CCE3A22`) reported **"Applied 3 parameters"**, but the sliders became `Module Width F1` = 1000 (the slider minimum) with both tilts at 0. The expected values were 4400 / −1 / +1. The canvas silently turned into a variant that never existed: 1038 objects and 4 failing rules. On top of that, all Design State labels came out empty.

## Causes

1. **F24.** `statePayloadJson` held `"value":4400` (the condensed `{type, value}` shape written by `DesignStatePayloadV2Serializer`). VALIDATION GRAPH parses it with `Neo4jValidGraphRepository.TryParseDesignState`, whose `JsonSerializer.Deserialize<DesignStateParameter>` has no `Value` member, so every `NumberValue` came out null. The same applied to `PropValue`. This was the documented "silent direction" of the Phase 1202 D-09 declared exclusion.
2. **F25.** `ParameterReinstateComponent.WriteToSource` writes `parameter.NumberValue ?? 0.0` (and `?? false` for booleans). `DesignStateReinstatementService.Validate` skips the domain check when the value is null and returns `Applied`.
3. **F23.** `ValidationGraphComponent.ToPublicDesignState` copied `StateId`, `CapturedAtUtc` and the states but not `Label`.

## Fix (TDD)

- The inline reader dispatches per entry on the `value` key (see [[knowledge/decisions/ValidGraph inline reader reads both parameter shapes, D-09 exclusion lifted]]).
- New status `ReinstatementStatus.MissingValue`. `ReinstatementStatusExtensions.IsBlocking()` replaces three hand-copied blocker lists (service, `ReinstatementResult.BlockedCount`, component). A parameter without its typed value aborts the reinstate, and the canvas stays untouched.
- `ToPublicDesignState` now sets `Label`.
- Tests: `Neo4jValidGraphRepositoryTests` (+4), `ReinstatementMissingValueTests` (4), and the enum contract went from 7 to 8. DG.Tests: 731 pass, 4 baseline E2E failures.

## Status

The code is fixed and committed. The new DG.gha is **not yet installed** in Rhino, and step 8 has to be repeated on the already-published V1–V4. The stored data is intact, so there is no need to republish.

## Related

- [[sessions/2026-10-05 v12 hexagonal facade test steps 2-8 and five DG fixes]]
