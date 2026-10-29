---
quick_id: 261029-dmt
title: Multi-user demo test findings — urgent fixes (audit-fix)
date: 2026-10-29
status: code-complete, live verification pending
decisions: [D-73, D-74, D-75, D-76, D-77, D-78]
---

# 261029-dmt: multi-user demo test findings

Source: the tester's report on `docs/demo/dg-demo-ru.html` (the test stopped at step 03 with
`GH_BRIDGE_UNREACHABLE` on `host.docker.internal:8720`). Plan: `C:\Users\Admin\.claude\plans\bright-snuggling-wilkinson.md`.
Owner decisions D-73..D-78 are in `.planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md`.

## Findings and outcome

| # | Finding | Class | Status | Commit |
|---|---|---|---|---|
| F-01 | The check fails with GH_BRIDGE_UNREACHABLE; the tester has to start Grasshopper and set up CONNECTOR/LISTENER | manual-only (architecture) | code done, live check pending | 705b7bf, fa0e6d2, 74f49e7 |
| F-02 | R1 shows no OpeningBox–Beam link in the Graph Viewer (R2 does) | auto-fixable | fixed | a5434cb |
| F-03 | Rules must be plain language without class or property names | manual-only (vocabulary + prompt) | fixed | a5434cb |
| F-04 | Colour overrides in Revit paint the lines too (one patch) | auto-fixable | fixed | 79938ee |
| F-05 | Demo instruction: invitation sign-in, connector install, new model, short steps, no S1/M1 codes | auto-fixable | fixed | f3588cc |
| F-06 | Mapping view in the Model Viewer (two colour modes, black edges, Validation Runs tile, Design State) | manual-only | stage 2 (D-78) | — |
| F-07 | Stand retest: R2–R4 of `isolation-check-a` give no verdict (`no_population`) | auto-fixable (ingest) + data | fixed for new ingests; tester re-enters the rules | efa6621, b30d2ea |

## Root causes

- **F-01:** data-service is the only caller of the Grasshopper bridge and runs on the server; on the stand
  `host.docker.internal` is the server, and DG CANVAS LISTENER binds to the PC's loopback only. DeGram's
  "Grasshopper — ready" is a separate local probe, so it hid the failure.
- **F-02:** the ingest prompt's beam example used the one-class form its own statement forbids; the LLM copied it, so no
  Beam class and no ObjectProperty were written, and the Graph Viewer draws class links only from ObjectProperty
  domain/range (D-69).

## What changed

- Revit checks run without Rhino.Inside or Grasshopper: data-service queues a job for the caller's own DG Revit
  connector, the connector runs the generated pyRevit program (same catalogue calculators, shared
  `model_context.py.tmpl`), `dg-evaluator` (DG.Core) judges the values, every rule is published in parallel and the
  connector paints the verdict (lines black) and writes `DG_Violation`.
- Program and connector code run under every pyRevit engine (IronPython 2.7/3.4, CPython 3): no coding line,
  IronPython-safe syntax, `eid()` instead of `IntegerValue` (removed in Revit 2026), engine-neutral MeshTriangle access,
  `__namespace__` on the ExternalEvent handler.
- Ingest: participant-form beam example, a deterministic subject-to-class ObjectProperty after ingest and on the next
  check, a class vocabulary with Russian words and Russian meanings of the computable properties.

## Verification

- pytest data-service: 6705 passed; failures only environmental (no `neo4j` host from the dev PC: dg_context,
  cg_structure_checks, computgraph_consult) and `recognition_eval/test_repeat_sweep.py`, which another session has
  uncommitted changes in.
- pytest Revit connector: 438 passed. dotnet: 878 passed, 4 failed (known live-Neo4j E2E baseline). ui-v2 api-security:
  163 passed.
- The generated pyRevit program is executed against a fake Revit 2026 API (boxes from the mapping, values, meshes,
  both MeshTriangle accessor styles).

## Live on localhost (2026-10-29, after the owner started Docker and authorized the push)

- `dg-evaluator:4bcb756` and `dg-f01-data-service:4bcb756` (built from `git archive HEAD`) run next to the unchanged
  rest of the stack (override `C:/Users/Admin/dgb-f01/compose.f01.yml`); only the data-service container was replaced.
- dg-evaluator reads the live rules of `str-openings-01`: all five (including the LLM-generated R5 calculator) evaluate
  with synthetic values as expected (failed / passed / unknown). The Revit program generated from the live rules is
  IronPython-safe.
- Dry run of `POST /scripts/property-check/run` (send=false) with a simulated connector: finished, summary ok,
  violations, and a paint job with per-box verdicts. The F-02 Cypher ran live: `ex:intersectsBeam`, `intersectsColumn`,
  `isAboveDoor/Window` and `hostedByWall` now relate Opening to the structure classes, so the Graph Viewer shows R1's link.
- DeGram: child `aac8353c` and the tool-description fix `38e0e1ee` were pushed to the fork. The gitlink was bumped
  (37c394f, 92b705a) and `workspace.py verify` passes. The connector payloads were staged from the clean `92b705a`.
  `DeGram-Setup-0.1.16.exe` was built in `D:/dgb/src/apps/desktop/release` and carries `check_jobs.py` and the new tool text.

## Stand rollout (2026-10-29, after the owner's Contabo snapshot `degram-0.1.15-before-f01`)

- The retest from the tester's second PC still failed with `GH_BRIDGE_UNREACHABLE`. Cause: the stand still ran the old
  data-service. `/data-service/connector/jobs/next` answered 404 there.
- Before the update, the stand's files were compared with the commit:
  - data-service had no stand-only changes; it lacked `c9d917b` and F-01.
  - The compose files and nginx differed only by the F-01 additions.
  - The UI sources were the uncommitted Dev/Demo toggle and resizable Model Viewer panels. They were committed as
    `f9f1feb`, so the UI was not rebuilt; its image got only the new nginx config.
- Update from `f9f1feb` in `/root/dg-f01-f9f1feb`:
  - data-service: the running image plus 17 changed files;
  - design-grammars: the running image with the new `default.conf` (nginx -t ok);
  - dg-evaluator: new, on `dg_default`, no published port.
  - Rollback tags: `dg-data-service:rollback-f01` and `dg-design-grammars:rollback-f01`.
  - Only these three containers changed; `.env`, volumes and n8n were not touched.
- Checks after the update:
  - The connector route answers 401.
  - `DG_DEPLOYMENT=multi-user`.
  - The evaluator health check passes from data-service.
  - The container files equal the commit.
  - Dry run on the five rules of `isolation-check-a`: the Revit program is generated, the evaluator answers 200,
    and R1/R5 give verdicts.
- **F-07:** R2–R4 gave `no_population` because their atoms were corrupted at ingest.
  - The output for R3/R4 MERGEd the Atom_Ids `R1_A1`/`R2_A1`, so the rules share atoms. R2's OpeningBox atom has two
    ARGs, and R3/R4 have three OpeningBox atoms with five to seven ARGs.
  - The Grasshopper path gives the same result, because it uses the same DG.Core.
  - The fix has two commits:
    - `efa6621` commits F27, the atom admission check from the v12 facade test. Until then it was an uncommitted
      container hotfix, lost on localhost when data-service was recreated.
    - `b30d2ea` rejects an atom linked by more than one rule and an Atom_Id that is not `<Rule_Id>_A<n>`/`_H<n>`.
  - Both were deployed to the stand in `/root/dg-f07-b30d2ea` (rollback tag `dg-data-service:rollback-f07`). Checked in
    the running container: foreign atom rejected, F27 shape rejected, valid A1 accepted.
- **Data:** deleting one of R2–R4 would also remove the R1/R2 atoms they share. Owner decision: the tester deletes all
  five rules of the project in the interface and enters them again (step 8), then repeats the check.

## Not done yet (needs the owner)

1. **Revit run on localhost** (owner at the PC):
   - Install DeGram 0.1.16.
   - In DeGram → Коннекторы, click «Установить» for Revit.
   - Open `DG-DemoProject-2-openings` in Revit, click «Вход» and run the mapping.
   - Send «Проверь модель Revit на соответствие всем правилам.».
   - Expected: runs in the Model Viewer, colours in Revit with black lines, no Rhino.
2. (done) DeGram build 0.1.16 with the new connector payload.
3. (done) Stand update. Remaining: on the stand, the tester deletes all five rules of `isolation-check-a`, enters them
   again and repeats the check. The Revit «Вход» must use the stand address.
5. **Localhost:** the F27/F-07 checks reach the local data-service only after it is rebuilt from `b30d2ea` (Docker is
   off on the dev PC now).
4. **Stage 2:** the mapping view in the Model Viewer (F-06).
