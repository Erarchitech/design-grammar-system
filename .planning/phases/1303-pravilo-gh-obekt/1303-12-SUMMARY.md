---
phase: 1303-pravilo-gh-obekt
plan: "12"
status: complete
completed: 2026-10-18
requirements: [DGMAP-01, DGMAP-04]
executor: "controller (Claude) for the implementation, docs and deployment; a DSH flash worker wrote the tests and was cancelled after its shell stalled for 11 minutes (it was about to widen its sandbox access)"
commits: [268958e, 71ff4a0]
---

# 1303-12 Summary — server side of the Revit slice

## What was built

- **Population per applied group** (`mapping_engine.populations_of`). The result is `{class: [group sizes]}`: one size per GH stream, else per group. `ev_population` gives evidence only when exactly one class has a group of that size. On the live session `ms-56907a90d11f`, 125 (GlassPanel and BottomTriangularPanel) and 1 (Basement contour and bbox F) now give no evidence, 25 → GroundFloorUnit, 100 → HexagonalUnit. Before, a group of 125 triangles got «GlassPanel». The old `{class: n}` shape stored in older session contexts is still read.
- **Default populations for Revit** (`mapping_store.create_session`). A Revit session without `populationsFromSessionId` uses the latest applied Grasshopper session of the project and records its id in the context. An explicit id wins. With no applied GH session, a Revit session has no population evidence and no error.
- **`document_of`** fills `document` for Revit sessions (label before « · »), so DeGram can match them to the open Revit model.
- **Docs:**
  - `spec/SECURITY-BOUNDARY.md` §3.8: the DG Revit connector zone and the owner decision lifting Revit restrictions. Route policy and machine-checked blocks are unchanged.
  - `spec/API.md`: Revit note.
  - `1303-API-CONTRACT.md` §8: the Revit descriptor, session, connector routes and tools, writes, DeGram.

## Verification

- Mapping tests: 60 passed (50 before + 10 new).
- Boundary and inventory tests: 1045 passed.
- Full data-service suite from the host: 5820 passed, 35 skipped; 4 failed (`test_dg_context`) and 25 errors (Neo4j integration, `neo4j` DNS from the host). This is the known environment baseline.
- **Deployment.**
  - The image was built from `git archive` of `778b228` into a new scratch folder with `docker build --no-cache`.
  - Image `29f8eccf78e2…`; rollback tag `design-grammar-system-data-service:pre-1303-11` = `8c8c04a8f79d`.
  - The container was recreated with `up -d --no-build --no-deps data-service` (compose sections of the main checkout and the branch are identical).
- **Served code** checked in the container:
  - `latest_applied_session_id` and the new evidence text are present;
  - `GET /` answers 200; `/mapping/sessions` without a credential answers 401;
  - a read-only recompute of `ms-56907a90d11f` with the retired profiles still gives 6 questions, so the demo cold start is unchanged;
  - the latest applied GH session is `ms-9dd7fb28e111`; session rows carry `document`.

## Notes

- The worker left empty sandbox directories with a restrictive ACL in `data-service/sandbox_probe/`. They are untracked, git ignores them, and they are to be removed once the DSH hub releases them.

## Addendum 2026-10-19 — Revit groups without evidence get one question (`85cf1b6`)

- **Found in the offline transfer probe.** Synthetic Revit families on the live project rules (100×6, 25×5, 125×4, 125×3 adaptive points) were mapped with the cold start in place. The 4-point family had no candidate: GlassPanel has no vertex-count signature rule, and the population 125 is ambiguous. It stayed `unmapped` with no question, so D-52 «≤ 1 question per family group» and full recall were impossible on a cold Revit read.
- **Change.** For Revit only, a group with no candidate and no matched profile or «none» answer gets one `assign` question (`unmatched: true`). It offers every project class and «None of these», with the title «… : which class?». Grasshopper keeps its LLM proposal, and the demo cold start is unchanged: the recompute of `ms-56907a90d11f` with the new engine still gives 6.
- **Probe results:**
  - cold Revit read: 2 questions (one batch for the three suggested families + one for the glass family);
  - the same descriptors with the 18.10 profiles active in memory: 0 questions, 375/375 auto. This is the GH → Revit transfer through `geometry.vertexCount`.
- **Tests:** mapping 63 passed.
- **Deployment.** Image `82378ca11829…` from `git archive` of `85cf1b6`; rollback tag `pre-1303-11` (`8c8c04a8f79d`) unchanged. Probes: `GET /` 200, mapping without a credential 401, GH recompute 6.
- **Note for the protocol script.** The engine's profile dicts do not carry `retiredReason`, so `dgmap_revit_transfer.py` selects the cold-start profiles by a direct graph query.
