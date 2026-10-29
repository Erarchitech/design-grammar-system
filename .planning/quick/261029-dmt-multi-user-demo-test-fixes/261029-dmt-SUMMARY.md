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

## Not done yet (needs the owner)

1. **Live end-to-end on localhost** (Docker was not running in this session): `docker compose build dg-evaluator
   data-service design-grammars` (`--no-cache` for the UI), Revit with `DG-DemoProject-2-openings`, sign in, map,
   ingest the five plain-language rules, "Проверь модель Revit на соответствие всем правилам.". Check the
   `SUBJECT_LINK_QUERY` Cypher against a live Neo4j as part of it.
2. **DeGram build with the new connector payload:** `python tools/degram/workspace.py verify` fails today because the
   child HEAD `aac8353c` (quick 261029-cxc) is ahead of the gitlink `500f1cad` and not yet on the fork. After the owner
   authorizes the push and the gitlink bump: stage the payloads (`tools/degram/stage_connector_payloads.py`), update
   the `degram_property_check` tool description (it still says the check is placed on the Grasshopper canvas) and
   build 0.1.16.
3. **Stand update** (owner authorization, Contabo snapshot first): pack from a clean commit, `deploy.sh`, then rerun
   step 11 of the instruction as the engineer.
4. **Stage 2:** the mapping view in the Model Viewer (F-06).
