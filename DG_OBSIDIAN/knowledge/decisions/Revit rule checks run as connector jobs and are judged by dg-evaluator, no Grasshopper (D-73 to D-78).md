---
tags: [decision, phase-1303, revit, connector, evaluator, stand]
date: 2026-10-29
status: implemented (F-01), deployed on localhost and the stand
---

# Revit rule checks run as connector jobs and are judged by dg-evaluator, no Grasshopper (D-73 to D-78)

## Context

The multi-user demo test failed at the check with `GH_BRIDGE_UNREACHABLE`:
- data-service runs on the server, where `host.docker.internal` is the server itself;
- DG CANVAS LISTENER binds only to the PC's loopback.

The tester was also asked to start Grasshopper and set up CONNECTOR/LISTENER by hand.

## Decisions (owner, 2026-10-29)

- **D-73: job queue over connector pull.** data-service queues a job for the caller's own DG Revit connector, keyed
  by project, user and connector. The connector polls `GET /connector/jobs/next` over HTTPS. The server never
  connects to the PC.
- **D-74: Revit-native calculators.**
  - The same catalogue calculators are generated as a pyRevit program, which the connector runs in Revit through an
    ExternalEvent. Rhino.Inside and Grasshopper are not used.
  - The program works under IronPython 2.7/3.4 and CPython (pythonnet).
- **D-75: C# evaluation service on the server.**
  - `dg-evaluator` (.NET 9, DG.Core) builds the DesignState as OBJECT/PROPERTY/DESIGN STATE do and evaluates like
    VALIDATOR. "Only C# evaluates" still holds.
  - Internal service, no published port.
- **D-76:** the demo instruction installs only the Revit connector.
- **D-77:** colour overrides paint fills only; lines stay black (Revit and later the Model Viewer).
- **D-78:** the mapping view in the Model Viewer is stage 2.

## Consequences

- A `multi-user` deployment always takes the Revit path; a missing connector answers 409 `REVIT_NOT_CONNECTED`.
  Localhost falls back to Grasshopper only when no connector polls.
- nginx needs `location /data-service/connector/` with `client_max_body_size 64m` for meshes.
- The verdict depends on clean Metagraph atoms; see
  [[knowledge/debugging/Ingest output reused other rules' Atom_Ids, so rules shared atoms and gave no verdict (F-07)]].
