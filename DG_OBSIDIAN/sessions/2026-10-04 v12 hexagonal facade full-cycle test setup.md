---
tags: [session, test, v12, facade, grasshopper, validator]
date: 2026-10-04
status: paused-step-2
---

# Session: 2026-10-01 → 2026-10-04 — v12 hexagonal facade full-cycle test: setup and rule approval

## Goal

Run a guided manual end-to-end test of the deployed DG v12 on a parametric hexagonal facade, with Claude acting as instructor: new project → new rules → GH model linked to DG → several facade variants → validation → Design States and results in Model Viewer → switching Design States back in Grasshopper.

## What Was Done

- **Verified the live stack instead of the docs.** All 15 containers were up, the LLM gateway was set to provider `openai`, and Speckle write/read tokens were saved, with the default project and base model in the env (auto-config on first publish). The old setup guide turned out to be stale ([[knowledge/debugging/V2 UI has no Speckle project link form and the setup guide predates v7]]).
- **Step 0:** found a stale `DG.gha` (2026-07-26, CONNECTOR without the `Platform Token` input). The user rebuilt Release and redeployed it, and the SHA256 of the deployed file matches the build output.
- **Step 1:** project `v12-hexagonal-facade-01` was created with the user as a member and 0 rules. No connector token yet.
- **Rule analysis against the evaluator** (`spec/SWRL-SUBSET.md`, `DesignStateBindingService`, `RuleEvaluator`, `VariableTypeInferrer`). The user's A1/A2/B1/B2/C1/D1 were classified and reshaped ([[knowledge/decisions/Architect rules are reshaped to the v12 evaluator boundary before ingest]]).
- **Approved set of 8 rules over 4 classes** (`GlassPanel`, `HexagonalUnit`, `BottomTriangularPanel`, `Facade`). D1 was split into `R_FAC_ASPECT_MIN_2_V` + `R_FAC_ASPECT_MAX_4_V` at the user's request (lower bound 2, upper 4). Added: planarity ≤ 5 mm, panel width ≥ 0.9 m, facade height ≤ 50 m. A1 is kept as an `unsupported` control.
- **Model inventory without Rhino.** The `.gh` (raw deflate GH_IO) was parsed, giving 27 sliders with names, values and ranges. The model is in mm, and 19 sliders are unnamed. There is no slider for storeys or module count, so variants will be driven by cell width, cell tilt (even/odd) and panel projection.
- **Test order changed:** compute the metrics on V1 first (3a), then calibrate thresholds (3b), then ingest (3c).
- **Artifacts** in `test/v12-hexagonal-facade-01/`: `README.md` (step tracker, expected-result matrix, journal, findings F1–F3), `RULES.md`, `rules-approved.json`, `model-inventory.md`. The user's `.gh` lives there too.

## Decisions Made

- Rules are reshaped to the evaluator boundary before ingest, and a range becomes two violation rules (see the decision note).
- All artifacts of this test are stored in `test/v12-hexagonal-facade-01/`. Tokens are never written there.

## Issues Encountered

- F1/F2: stale setup guide, and no Speckle link form in the V2 UI. See [[knowledge/debugging/V2 UI has no Speckle project link form and the setup guide predates v7]].
- F3: index-based `ObjectRef`s collide across classes for computed geometry. See [[knowledge/debugging/OBJECT STATE index ObjectRefs collide across classes for computed geometry]].
- Docker Desktop was down after a reboot on 2026-10-03 and was restarted by the user. The Neo4j password is rotated (Phase 1205): use `${NEO4J_AUTH#neo4j/}` inside the container, not `12345678`.

## Next Steps

1. **Step 2:** mint the Grasshopper connector token (Connectors → Grasshopper, project `v12-hexagonal-facade-01`).
2. **Step 3a:** build a "DG METRICS" group in GH with 7 lists (aspect, width_m, planarity_m, levelOffset_m, symmetry_m, vertexCount, height_m), send min/max and counts, then calibrate thresholds (3b) and ingest the rules one by one with a Neo4j SWRL check after each (3c).
3. Name the variant-driving sliders before the first Design State capture (PARAMETER REINSTATE matches by ParameterId).
4. Steps 5–9 as listed in `test/v12-hexagonal-facade-01/README.md`.

## Related Notes

- [[knowledge/decisions/Architect rules are reshaped to the v12 evaluator boundary before ingest]]
- [[knowledge/debugging/OBJECT STATE index ObjectRefs collide across classes for computed geometry]]
- [[knowledge/debugging/V2 UI has no Speckle project link form and the setup guide predates v7]]
