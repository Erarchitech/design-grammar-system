---
tags: [decision, validgraph, serialization, reinstate, v12]
date: 2026-10-05
status: accepted
---

# ValidGraph inline reader reads both parameter shapes (D-09 exclusion lifted)

## Context

Phase 1202-09 (D-09) declared that the v2 `statePayloadJson` `parameters[]` member has two wire shapes, each with its own reader, and deliberately did not converge them:

- the **flat** shape (`numberValue`/`integerValue`/`booleanValue`) is written by the accept-candidate writer and read by `Neo4jValidGraphRepository.TryParseDesignState`;
- the **condensed** shape `{type, value}` is written by `DesignStatePayloadV2Serializer`, which every VALIDATOR publish uses, and read by the serializer.

The spec noted that the inline reader *silently* returns null values on the condensed shape. It also listed "a consumer reading both producers through one code path" as a trigger that would force convergence, assuming that did not happen.

The facade test showed that it does happen. VALIDATION GRAPH reads every canvas-published run through `TryParseDesignState`, so PARAMETER REINSTATE received null parameter values and wrote zeros into the sliders (findings F24/F25).

## Decision

The owner decided on 2026-10-05 that `TryParseDesignState` dispatches **per entry**:

- a `parameters[]` entry or a `propStates[].propValue` with a `value` key goes to `DesignStatePayloadV2Serializer.ParameterFromConciseJson`;
- anything else keeps the flat CLR-name binding.

`DesignStatePayloadV2Serializer.Deserialize` is unchanged and still throws on the flat shape. Nothing converges onto the throwing reader, so D-09's concern about dropping stored flat rows does not apply. At reinstate time, a missing typed value now blocks the reinstate (`ReinstatementStatus.MissingValue`).

## Consequences

- VALIDATION GRAPH → DESIGN STATE DECONSTRUCT → PARAMETER REINSTATE works for canvas-published states.
- The pinned "divergence" Fact for the condensed shape was replaced by `TryParseDesignState_ReadsTheSerializerOwnConciseParameterShape` and `TryParseDesignState_ConciseShape_ReadsEveryValueType`. The flat-shape Fact is unchanged.
- `spec/DATABASE.md` carries an amendment block at the top of the D-09 subsection. Its items 3–6 now describe the pre-amendment state.
- A third `parameters[]` producer would still need a new reader branch. The dispatch key is the presence of `value`.

## Related

- [[knowledge/debugging/Reinstate from ValidGraph read null parameters and wrote zeros into sliders]]
- [[sessions/2026-10-05 v12 hexagonal facade test steps 2-8 and five DG fixes]]
