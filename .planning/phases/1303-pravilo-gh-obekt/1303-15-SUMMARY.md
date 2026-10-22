---
phase: 1303-pravilo-gh-obekt
plan: "15"
status: partial
completed: 2026-10-21
requirements: [DGOPN-01, DGOPN-02, DGOPN-03, DGOPN-04]
requirements_accepted: []
commits: "43 commits matching 1303-15, 85b6705 (plan) .. b7bcbf0 (last code); session note 01e19c1"
committing_repository: framework (worktree dg-mapping, branch feature/mapping-mvp)
executor: "Controller (Claude) inline; reconstructed afterwards from commits and the 2026-10-21 session note"
---

# 1303-15 Summary — MEP opening boxes checked in Revit through Rhino.Inside and VALIDATOR

> **Status: implemented and run live, acceptance evidence NOT recorded.** This SUMMARY was written after the fact from the commit history (43 commits, 75 files under `data-service/`, `DG/`, `ui-v2/`) and `DG_OBSIDIAN/sessions/2026-10-21 Phase 1303-15 ...md`. It closes the missing-SUMMARY gap that blocked wave routing; it does **not** claim that DGOPN-01..04 are accepted. The plan's own done criteria (gold, precision/recall, protocol, guide, UAT) are listed under *Not delivered*.

## Delivered

- **Rules R1–R4** (beam, column, openings-above, clearance < 300 mm) enter project `str-openings-01` through the normal NL → SWRL → Neo4j path. Ingest was hardened along the way: atom types are repaired from `REFERS_TO`, bare variables get `?`, every class a rule names is created at ingest, rule deletion also removes orphaned ontology nodes / ingest sessions, and a duplicate-class check asks the operator during ingest.
- **Property-script generator** (`data-service/property_scripts.py`, route `POST /scripts/property-calculator`, `…/place`, `/scripts/property-check/run`). Catalogue of three vetted Revit calculators (category intersection count, openings below count, min opening clearance in mm). Binding order: stored binding → alias → vocabulary near-match → LLM-written calculator under a fixed contract with AST validation. Generated calculators persist in Neo4j (`COMPUTED_BY`, `READS_CLASS`, experimental). Per amendments A-1..A-3 the scripts are **Rhino 8 Python 3**, not C#.
- **Placement on the canvas.** The placement plan is computed by data-service (`property_scripts.placement_plan`), validated by DG.Core `PropertyScriptPlacement`, executed by the CANVAS LISTENER under one undo record. The chain is re-placed only when its plan changed. Spike result: `Python3Component` supports `SetSource(string)` and `IGH_VariableParameterComponent.CreateParameter` (Rhino 8.25), so the RhinoCode fallback was not needed.
- **DG.gha inside Rhino.Inside.Revit 2024:** multi-targeted `net7.0-windows;net48`, `NetFrameworkAssemblyResolver` first, `await using` replaced (see debugging note on `IAsyncDisposable`).
- **Check started from DeGram** (`degram_property_check`: generate / run / clear / status, bound project only). One-shot SendValid/Paint toggles set only between solutions, highlighter writes Revit only when the verdict changes, published runs are read back from the graph, nginx `/data-service/scripts/` timeout 240 s.
- **Model Viewer:** true box geometry; per rule only the classes that rule reads; context colour + α control; a picked element shows source model, platform and its Revit id.
- **Mapping outranks category:** calculators read elements by their DG mapping (pylon 4711685, a wall mapped Column, is now seen by the column rule).

## Live evidence (owner-reported / session note, not independently re-run here)

Model copy `D:\dgb\revit-models\Likino_KR_GP_R24_CH10-dg-openings.rvt`. Last run 2026-10-21 12:54–12:55 UTC: **313 boxes, 4 runs**.

| Rule | Violations | Boxes |
|------|-----------:|-------|
| R2 column | 4 | 4861053, 4861769, 4861787, 4747124 |
| R1 beam | 1 | 4747406 |
| R3 above openings | 1 | 4747397 |
| R4 clearance | 0 | closest 730 mm |

Boxes 4747124 and 4747406 are **new findings the owner has not yet confirmed in Revit**. The context was added to those four runs by hand after a 502, so that run is not a clean end-to-end proof of the fixed 502 path.

Deployed: data-service/UI `b7bcbf0` (override `D:\dgb\mapping-release-b7bcbf0\compose.mapping-images.yml`), dg-reasoner `e600716`, installed DG.gha from `9023b6e`.

## Not delivered (plan done criteria still open)

- Task 1: no `evidence/inventory.json`, no owner-confirmed `evidence/gold.json`; the geometry definitions for R3/R4 were never recorded as confirmed.
- Task 5/6: no `evidence/run1.json`, **no precision/recall against a gold**, no `test/str-openings-01/PROTOCOL.md` («Акт 4»), no demo step in `1303-TEST-GUIDE.md`, no `1303-UAT.md` test 13. `test/str-openings-01/evidence/` is empty.
- A clean rerun from DeGram after the 502 fix (expected: no 502, context added automatically, boxes painted with `DG_Violation`) has not been observed.
- Open Revit dialog that held the highlighter transaction for about 10 minutes: its text is unknown and nothing suppresses it. The listener's one-shot SolutionEnd reset after such a dialog is unconfirmed on a clean run.
- Not run/recorded in this reconstruction: `pytest` / `dotnet test` counts for the final state. Do not read any green claim into this file.
- Revit write (highlighter) was applied only to the local copy (D-52); a before/after hash of the original (T-15-02) was not recorded here.

## Next

1. Owner reruns the check from DeGram, confirms 4747124 / 4747406 in Revit, records any dialog text.
2. Then, in one short pass: gold + inventory + run1 + PROTOCOL + guide step + UAT 13, and only then mark DGOPN-01..04 accepted.
3. Plans 1303-16/19 (wave 7) do not depend on that evidence; D-54 (generated calculators join the catalogue after confirmation) is the follow-up in 16–18.
