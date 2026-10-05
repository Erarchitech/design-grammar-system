---
tags: [session, test, v12, facade, grasshopper, validator, reinstate, fix]
date: 2026-10-05
status: paused-step-8-awaiting-dg-install
---

# Session: 2026-10-04 → 2026-10-05 — v12 hexagonal facade test: steps 2–7 passed, step 8 blocked, five DG defects fixed

## Goal

Continue the guided full-cycle test `v12-hexagonal-facade-01` from step 2: connector token, rule metrics and calibration in Grasshopper, ingest of the rules, wiring DG on the canvas, publishing variants V1–V4, Model Viewer, and switching Design States back with PARAMETER REINSTATE.

## What Was Done

- **Step 2.** A Grasshopper connector token was minted for the project. CONNECTOR showed "Connected · Auth OK".
- **Step 3a — metrics script.** Wrote `test/v12-hexagonal-facade-01/gh-measure-rules.cs`, a Rhino 8 C# Script with tree access (one object per branch). It computes all rule quantities in metres, with quantiles, violator previews and a `THRESHOLDS` block, and every version was compile-checked against the Rhino 8 DLLs. Seven V1 runs are recorded in `3a-V1-summary.txt`.
- **Rule set changes, all owner decisions.**
  - Ground-floor modules are pentagons and form their own class `GroundFloorUnit`. All modules must have closed outlines: R9/R10 cover gap count, R11/R12 cover vertex count (5 and 6).
  - R4 (symmetry) was dropped entirely. On V1, all 32 corner-folded units are asymmetric by construction.
  - R3 became the control rule and R6 (planarity) became the V4 driver.
  - The final set has 11 rules over 5 classes.
- **Step 3b — calibration.**
  - Thresholds are anchored on V1 with about 8% margin (owner decision): R1 ≥ 1.3, R2 ≤ 6.0, R7 ≥ 4.5 m, R8 ≤ 120 m. Thresholds are never tuned to make variants fail.
  - Variants were chosen by sweeping sliders through **RhinoCode** in the live Rhino (no Rhino MCP exists, see memory `rhinocode-drives-live-rhino`):
    - V2 is `Module Width F1` 4400 → fails R2 (12) and R7 (57);
    - V3 is F1 10000 → fails R1 (4);
    - V4 is `Наклон нечет сот` 0 → fails R6 (14).
  - Violators were localised by panel normal azimuth: F1 is the facade at about 321°.
  - Details are in `3b-variants.md`.
- **Step 3c — ingest.**
  - All 11 rules were ingested one at a time, each checked in Neo4j (`3c-ingest.md`).
  - R8–R12 were entered without class or property hints. Recognition mostly worked: R10 falsely matched `HexagonalUnit`.
  - A delete sent in Ingest mode made the LLM invent a rule from a bare ID, and `MERGE` blended it into the existing rule. The rule was cleaned with the UI delete.
- **Step 5 — wiring.**
  - RhinoCode built 50 objects in the group "DG v12 test wiring": GD, METAGRAPH, 5 OBJECT STATE, 11 RULE DECONSTRUCT and PROPERTY STATE, PARAMETER STATE, DESIGN STATE and VALIDATOR (`5-wiring.md`).
  - It exposed F15/F16, which were fixed in DG (TDD) and deployed.
  - Afterwards, V1 gave 11/11 PASS, and each rule's ValidStatus landed on its own class's slots.
- **Step 6 — publish.** V1–V4 were published through RhinoCode. **All 44 runs matched the matrix exactly**, and ValidGraph holds 44 `completed` runs and 3865 entities (`6-publish-runs.md`).
- **Step 7 — Model Viewer.** The owner confirmed the colouring visually. The UI remarks are recorded as F18–F22.
- **Step 8 — reinstate.**
  - VALIDATION GRAPH, DS DECONSTRUCT, List Item and PARAMETER REINSTATE were added to the canvas.
  - Reinstating V2 reported "Applied 3" but wrote F1 = 1000 and the tilts 0 / 0. The values had already been lost when reading from ValidGraph (F24), and REINSTATE substituted zeros (F25).
  - The canvas was restored to V1. F23, F24 and F25 were fixed in DG (TDD), but the new build is **not yet installed**.
- **DG code changes** (commit `fix(dg)`):
  - `DesignStateGuard`, `ValidStatusMapper` and `BindingRow.SourceObjStateIndex` (F15/F16);
  - dual-shape `TryParseDesignState` with a `ParameterFromConciseJson` helper (F24);
  - `ReinstatementStatus.MissingValue` with `IsBlocking()` (F25);
  - `ToPublicDesignState` now copies `Label` (F23);
  - the `spec/DATABASE.md` D-09 amendment.
  - DG.Tests: 731 pass, 4 E2E fail (baseline). Release build has 0 errors and 0 warnings.

## Decisions Made

- [[knowledge/decisions/ValidGraph inline reader reads both parameter shapes, D-09 exclusion lifted]]. The owner reversed Phase 1202 D-09 for the inline reader.
- Test-level owner decisions: `GroundFloorUnit` class, closed-outline rules, R4 removed, R3 control / R6 active, V1-anchored thresholds, variants built on F1 only, and the canvas assembled by RhinoCode. All are recorded in `test/v12-hexagonal-facade-01/README.md`.

## Issues Encountered

- [[knowledge/debugging/DESIGN STATE and VALIDATOR assumed one class per Design State]] — F15/F16, fixed.
- [[knowledge/debugging/Reinstate from ValidGraph read null parameters and wrote zeros into sliders]] — F23/F24/F25, fixed, install pending.
- [[knowledge/debugging/CONNECTOR caches an unreachable heartbeat until the token or Go changes]] — F14, open.
- [[knowledge/debugging/Rule ingest blends a rule invented from a bare Rule_Id into the existing rule]] — F13, together with F6/F9/F11/F12, open.
- [[knowledge/debugging/Grasshopper Panels can neither be captured as parameters nor safely carry tokens]] — F7/F17, open.
- [[knowledge/debugging/Model Viewer shows a foreign base model and a hard-coded tile property catalogue]] — F18–F22, open.
- VALIDATOR publishing is slow: about 18 s per run, about 195 s for 11 rules.

## Next Steps

1. **Install the new DG** (DG.gha `a9f96e93…`, DG.Core.dll `4ab3952b…`): save the `.gh`, close Rhino, then copy `DG.gha`, `DG.Grasshopper.dll/.pdb` and `DG.Core.dll/.pdb` from `DG/src/DG.Grasshopper/bin/Release/net7.0-windows` to `%APPDATA%\Grasshopper\Libraries\DG`, with a backup, and check the hashes. Reopen Rhino, paste the token into CONNECTOR and VALIDATOR, and toggle `Go`.
2. **Repeat step 8** with the existing canvas components (`reinstate_state.py` pattern):
   - reinstate V2 → expect F1 = 4400, tilts −1 / +1, and only R2 and R7 failing;
   - reinstate V4 → expect only R6 failing;
   - reinstate V1.
   - Labels V1–V4 should now be visible.
3. **Step 9:** control rule A1 → expect `unsupported`.
4. Close the test: summary of findings F1–F25 and a decision on which open findings become phases.

## Related Notes

- [[sessions/2026-10-04 v12 hexagonal facade full-cycle test setup]]
- [[knowledge/debugging/OBJECT STATE index ObjectRefs collide across classes for computed geometry]]
- [[knowledge/decisions/Architect rules are reshaped to the v12 evaluator boundary before ingest]]
