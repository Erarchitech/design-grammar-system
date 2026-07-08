---
tags: [session]
date: 2026-07-08
---

# 2026-07-08 Per-object property binding and Speckle auto-config

## Context

v7.0 VALIDATOR component publish was failing with `SPECKLE_CONFIG_MISSING` (404).
Fix escalated into a full per-object property binding feature when the root cause
turned out to be: (a) Speckle IntegrationConfig required manual UI setup, (b) silent
DesignState serialization failures, (c) PROPERTY STATE couldn't resolve DataProperty
IRI from RULE DECONSTRUCT variables, and (d) the binding model was rule-scoped
(one property value broadcast to all objects) — couldn't produce per-object pass/fail.

## Commits (5)

| Commit | Description |
|--------|-------------|
| `c602f57` | Auto-configure Speckle IntegrationConfig from env vars (`SPECKLE_PROJECT_ID` + `SPECKLE_BASE_MODEL_ID`) on first publish |
| `abfb0b8` | Surface DesignState serialization errors via SendStatus; remove null-ClassIri skip in binder |
| `a2a063c` | Resolve DataProperty IRI from Rule+Variable in PROPERTY STATE (fixes `h(<missing>)`) |
| `f56eea5` | Per-object property binding: PropState.ObjectRef, binder per-object linking, id-generator collision fix, serializer round-trip, OBJECT STATE class broadcast + per-instance ObjectRef, PROPERTY STATE ObjState input |
| `dc4e2ce` | Broadcast single Rule/DataProperty across all PropValues (fixes "only first item True") |

## Key design decision

**Per-object property binding (Option C):** PropState gains optional `ObjectRef` linking
a property value to one object instance. When set, the binder applies the value only to the
matching object's row. When null, legacy broadcast-to-all behavior preserved (backward compat).
PROPERTY STATE's new ObjState input pairs positionally with PropValue.

See also: [[knowledge/decisions/Per-object property binding via PropState.ObjectRef]]

## Files changed (14)

- `data-service/app.py` — `_auto_configure_integration()`, fallback in `publish_validation()`
- `docker-compose.yml` — `SPECKLE_PROJECT_ID`, `SPECKLE_BASE_MODEL_ID` env vars
- `.env` — created with all Speckle env vars (NOT committed — contains tokens)
- `DG/src/DG.Core/Models/PropState.cs` — `ObjectRef` field
- `DG/src/DG.Core/Services/DesignStateBindingService.cs` — `ResolveDataPropertyIri()`, per-object `ApplyPropertyValues()`
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — `ComputePropStateId` with `objectRef`
- `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` — `objectRef` round-trip
- `DG/src/DG.Grasshopper/Components/GhCastingHelpers.cs` — `TryPropState` copies ObjectRef
- `DG/src/DG.Grasshopper/Components/PropertyStateComponent.cs` — ObjState input, IRI resolution, broadcast
- `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` — class broadcast, per-instance ObjectRef
- `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` — surface serialization errors
- `DG/tests/DG.Tests/DesignStateBindingServiceTests.cs` — +2 per-object tests
- `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` — +2 collision/compat tests
- `DG/tests/DG.Tests/DesignStatePayloadV2SerializerTests.cs` — +1 ObjectRef round-trip test

## Test results

- 215/215 C# non-E2E tests pass
- 58/58 Python data-service tests pass
- Full solution builds clean (0 warnings, 0 errors)

## Remaining issues (for next session)

1. **DesignStateLabel missing** in Model Viewer tile header — DESIGN STATE's
   `DesignStateLabel` input (4th pin) needs a text string wired from OBJECT STATE's
   Label output (or a manual Panel). The label flows through V2 serializer → data-service
   → `_project_state_summary` → ModelScreen.jsx reads `g.state?.label`.
2. **Abstract boxes in Model Viewer viewport** — the V2 Model Viewer renders synthetic
   isometric SVG boxes from entity IDs (by design in ModelScreen.jsx:26-57). Real 3D
   Speckle geometry is viewable via the `modelViewerUrl` link in the legacy model-viewer.
   This is a V2 architectural choice, not a rendering bug.
