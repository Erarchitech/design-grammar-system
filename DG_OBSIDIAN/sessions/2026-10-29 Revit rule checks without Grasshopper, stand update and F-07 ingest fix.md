---
tags: [session, v13.0, phase-1303, quick, revit, stand, ingest, degram]
date: 2026-10-29
---

# Session: 2026-10-29 — Revit rule checks without Grasshopper, stand update and F-07 ingest fix

## Goal

1. Plan and fix the findings of the multi-user demo test on `docs/demo/dg-demo-ru.html` (`/gsd-audit-fix`,
   quick 261029-dmt). The test stopped at step 03: the check failed with `GH_BRIDGE_UNREACHABLE` on
   `host.docker.internal:8720`.
2. Update the Contabo stand so that the tester's second PC can run the check.
3. Find out why three of the five rules give no verdict, and clear the project's rules on request.

## What Was Done

- **F-01: checks run in Revit, no Rhino.Inside or Grasshopper** (owner decisions D-73..D-75). Commits `705b7bf`,
  `fa0e6d2`, `74f49e7`.
  - data-service queues a job for the caller's own DG Revit connector (pull queue, `/connector/jobs/*`).
  - The connector runs the generated pyRevit program (shared `model_context.py.tmpl`). The program is compatible with
    IronPython 2.7/3.4 and CPython.
  - The new `dg-evaluator` (.NET 9 on DG.Core) judges the values. Every rule is published in parallel.
  - The connector paints the verdict with black lines and writes `DG_Violation`.
- **Other findings fixed:**
  - F-02/F-03 (`a5434cb`): subject-to-class links for every rule; plain-language rules.
  - F-04 (`79938ee`): colour overrides keep the lines black.
  - F-05 (`f3588cc`): new demo instruction without codes, with invitation and connector steps.
  - F-06 (mapping view in the Model Viewer) is stage 2 (D-78).
- **DeGram:** `aac8353c` and `38e0e1ee` were pushed to the fork, the gitlink was bumped and 0.1.16 was built.
- **Localhost:** `dg-f01-data-service:4bcb756` and `dg-evaluator:4bcb756`; the evaluator was checked on the real
  rules.
- **Retest on PC-2 still failed.** DeGram pointed at the stand (`activeDgTarget=demo`), and the stand still ran the
  old data-service (`/connector/jobs/next` → 404).
- **Stand update** (after the owner's snapshot `degram-0.1.15-before-f01`):
  - The stand's files were diffed against the commit first. The UI held uncommitted Dev/Demo toggle and panel work,
    committed now as `f9f1feb` at the owner's request.
  - Each service got a thin image layer over its running image: data-service and UI, the UI with nginx only.
  - `dg-evaluator` was added. Rollback tags: `rollback-f01`, `rollback-f07`.
- **F-07** (`efa6621`, `b30d2ea`, deployed): R2–R4 of `isolation-check-a` gave `no_population` because their ingest
  reused R1/R2 Atom_Ids. See [[knowledge/debugging/Ingest output reused other rules' Atom_Ids, so rules shared atoms and gave no verdict (F-07)|debugging]].
  - The atom admission check F27 had lived only as a container hotfix. It is now committed, extended by an
    atom-ownership rule and deployed.
- **Rule cleanup:** the owner could not delete the rules in the interface.
  - Cause: `delete_rule` silently kept a rule whose arguments were all shared. Fixed in `993b709`, not yet deployed;
    see [[knowledge/debugging/Rule delete kept a rule whose arguments were all shared and still answered deleted|debugging]].
  - All five rules were deleted on the stand after a JSON backup.

## Decisions Made

- D-73..D-78 (owner): job queue via connector pull; Revit-native calculators (pyRevit); C# evaluation service on the
  server; only the Revit connector in the instruction; mapping view as stage 2. See
  [[knowledge/decisions/Revit rule checks run as connector jobs and are judged by dg-evaluator, no Grasshopper (D-73 to D-78)|decision]].
- Owner: commit F27 together with F-07 and deploy both; the tester re-enters the rules.
- Owner: commit the Dev/Demo toggle and the resizable Model Viewer panels (`f9f1feb`).

## Issues Encountered

- I committed foreign uncommitted work by mistake (F27 inside `cypher_allowlist.py`). The commit was undone before
  anything was pushed and split into a F27 commit and a F-07 commit with the owner's consent. See
  [[container-hotfixes-vanish-on-recreate]] (auto-memory).
- Stand files are CRLF and the working tree is partly LF, so diff with `--strip-trailing-cr`.
- On Windows, `/tmp` differs between Python and Git Bash; use explicit paths.
- Deploying `993b709` to the stand was refused by the permission layer: it needs the owner's explicit authorization.

## Next Steps

1. Owner: authorize deploying `993b709` (rule delete fix) to the stand data-service.
2. Tester on PC-2:
   1. Enter the five rules of `isolation-check-a` again (step 8).
   2. In Revit, click «Вход» and choose the stand address.
   3. Send «Проверь модель Revit на соответствие всем правилам.».
   4. Expected: one run per rule in the Model Viewer, colours in Revit with black lines, no Rhino.
3. Localhost: rebuild data-service from the current commit, which now includes F27/F-07 and the delete fix.
4. Stage 2: the mapping view in the Model Viewer (F-06, D-78).

## Related Notes

- `.planning/quick/261029-dmt-multi-user-demo-test-fixes/261029-dmt-SUMMARY.md`
- `.planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md` (D-73..D-78)
- [[sessions/2026-10-27 DG connectors install from the DeGram Connectors tab]]
