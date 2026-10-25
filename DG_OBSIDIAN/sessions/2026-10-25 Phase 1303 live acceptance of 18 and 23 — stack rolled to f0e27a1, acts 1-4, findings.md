---
tags: [session, phase-1303, dgopn-05, dgopn-06, acceptance]
date: 2026-10-25
---

# Session: 2026-10-25 — Phase 1303 live acceptance of plans 1303-18 and 1303-23

Model: claude-sonnet-5-5. Branch `feature/mapping-mvp`, worktree `dg-mapping`. Nothing pushed.

## Goal

`/gsd-execute-phase 1303 --wave 11` (plan 1303-23). The wave guard stopped it (1303-06/07/14/18 incomplete); the owner chose "variant A": run 1303-18 first, leave 06/07/14 aside, then do the agent part of 1303-23 and test live together.

## What Was Done

- **1303-18 Tasks 1–2** were already done in the previous pass (commits ab41fcf, e38b2b3, 2a61d07, 0a03ad5); verified on disk, no new commits. Task 3 (live V13) is partly done by the owner, see below.
- **1303-23 Tasks 1–2** by a gsd-executor: gate on the committed sha (data-service 4 failed + 25 DNS errors, de01 1 failed, all in the 1303-18 baseline; DG.Tests 5 environment failures: worktree `.git` file, Neo4j test password; ui-v2 370/370), images built `--no-cache` from `git archive f0e27a1`, override `D:\dgb\mapping-release-f0e27a1\compose.mapping-images.yml`, rollback file beside it, `DG.gha` built (sha256 `02788a22…`) and installed by the owner (hash verified equal). Evidence: `test/str-openings-01/evidence/stack-rollout-1303-23.json`, commit `fe4ca03`.
- **Company** `UAT-A` assigned to `str-openings-01` by the owner through `PUT /projects/str-openings-01/company` from the browser console (no UI for it; admin only). Reassigning revokes connector tokens.
- **Revit bridge**: Routes had taken port 48885 (48884 busy at Revit start); after a full Revit restart it listens on 48884 and `dg_revit` is healthy.
- **Act 1 (ingest)**: rule `R_STR_OPENING_CLEARANCE_MIN_500_V` written with subject Opening, ClassAtoms Slab/Column/Wall, ObjectPropertyAtoms `hostedBy`, `projectsOnto`×2. Old traces of `R_OpeningSlabEdgeClearance500` were audited read-only (rule/atoms gone; DataProperty, calculator and one ingest session intentionally kept, owner chose "leave as is"). Remark: the Graph Viewer shows `REFERS_TO` only at an ObjectProperty; domain/range are node properties, so no class-to-class edge is drawn (see decision note).
- **Act 2 (conflict)**: second rule (columns only, 300 mm) opened the conflict dialog, Cancel → delete preview → `POST /rules/bulk-delete`; Neo4j read afterwards: five rules, no orphan atoms/vars/ontology.
- **Act 3 (VALIDATOR)**: per-box verdicts of the live canvas equal the last recorded runs (2026-10-22 13:27–13:29) for all five rules over 313 boxes, 0 differing boxes (R1 beam 1, R2 columns 4, R3 above 1, R4 0, new rule 313). The new rule evaluates and its message lists the asserted participants.
- **Act 4 (calculator)**: `hasMinProjectionClearanceMm` READS_CLASS to Slab (Floors, hostedBy Opening), Wall, Column; the old generated script read `OST_StructuralFraming` (Beam) instead of Floors. Owner allowed regeneration. The calculator had been confirmed to the UAT-A catalogue (09:12), so Reject/"Ask DG" were not shown (D-60); the owner retired it (09:21), then one Neo4j write (approved: `regenerateRequested = true` on the project copy) and "Generate check" gave exactly one LLM call (09:38). New source sha `8e2133c5e0` reads Columns/StructuralColumns/Walls and is active/pending. **Values are still `min=0.0 max=0.0` on all 313 boxes**: the script ends `if min_clear is None: return 0.0`, so "nothing related found" reads as a violation.
- Plan 18 V13 steps done by the owner: confirm into the catalogue, retire with reason (log `POST /retire` 200, copy and entry `retired`, nodes kept). Not done: second-project reuse (G2), isolation, `promotion-live.json`, PROTOCOL «Акт 5», UAT test 13.

## Decisions Made

- Findings accepted for a new plan **1303-24** (owner, 2026-10-25): calculator returns "no data" instead of 0.0; listener timeout for `run_property_check` and no blind retry after BUSY; UI regenerate for a retired calculator; Graph Viewer draws derived class-to-class edges. See [[Graph Viewer draws class-to-class edges derived from ObjectProperty domain and range (Phase 1303)]].
- Regeneration of a confirmed calculator went through a targeted Neo4j write because D-60 offers only Retire in the UI.

## Issues Encountered

- [[Run check answers BUSY because the solution blocks the Rhino UI thread longer than 10 s, and SendValid left True loops publishing (Phase 1303)]]
- [[Generated property calculators return 0.0 when no related element is found (Phase 1303)]]
- The open Revit document was the `…_отсоединено_maggenda` local copy and the Grasshopper document `C:\Users\Admin\Downloads\phase1303-test-revit.gh`; the chain lives in a group "DG · Проверка свойств (str-openings-01)" and its script has type "Python 3 Script" with nickname `DG PROPERTY CALCULATOR`, so palette search never finds it.
- **Incident, stopped at 10:09:21 UTC:** the owner set `SendValid` True and Grasshopper stayed frozen for over half an hour; `ValidationRun` nodes created on 2026-10-25: **50** (09:15–10:09, sets of five every ~3 min). A `run_property_check send=false` that I queued (it answered BUSY after 10 s, the delegate stayed queued) switched `SendValid` off when the UI thread got a gap; afterwards the listener answered again and `toggles` showed `SendValid` False. Duplicate runs (and their Speckle versions) need a cleanup decision from the owner; nothing was deleted.

## Next Steps

1. Confirm the publish loop has stopped (Esc in Grasshopper, `SendValid` False), count the extra `ValidationRun` nodes and Speckle versions of 2026-10-25 and ask the owner before any cleanup.
2. Plan and execute 1303-24 (4 items above) with TDD; then reinstall `DG.gha`.
3. Finish 1303-18 Task 3 (second project, isolation, evidence files) and write 1303-18 / 1303-23 SUMMARY, UAT, STATE, ROADMAP.
4. 1303-06, 1303-07, 1303-14 remain unexecuted.

## Related Notes

- [[sessions/2026-10-22 Phase 1303 wave 10 — plans 21 and 22 executed|wave 10 session]]
- [[Multi-participant rules keep one subject and assert the other classes as context (Phase 1303, D-61 to D-65)]]
- [[Property calculators read elements by their DG mapping, not only by Revit category (Phase 1303-15)]]
