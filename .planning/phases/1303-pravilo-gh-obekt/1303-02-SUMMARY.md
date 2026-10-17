---
phase: 1303-pravilo-gh-obekt
plan: "02"
status: complete
completed: 2026-10-17
requirements: [DGMAP-01, DGMAP-02, DGMAP-03, DGMAP-04]
executor: controller (inline; DSH hub unreachable and subagents stopped on rate limits)
---

# 1303-02 Summary — mapping routes and persistence

## What was built

- `data-service/mapping_store.py` — project-graph reads (classes = project classes ∪ classes referenced by the project's rule atoms; rule-atom rows from the unfiltered `_RULE_CONFLICT_QUERY` join, superseded rules excluded; class → rule ids), persistence of `MappingSession` (summary JSON, context JSON, zlib+base64 descriptors and result), `MappingDecision` (`HAS_DECISION`), `MappingProfile` (`CREATED_PROFILE`, `ASSIGNS_ROLE` → `Class` by iri), and orchestration (`create_session`, `get_session`, `list_sessions`, `post_decision` → `engine.decide` + store + recompute, `apply_session` → `engine.partition`, `list_profiles`, `create_authored_profile`). Every statement binds `$project` and carries `// op=mapping_*`; the module reuses `dg_context`'s lazy driver (no second copy of the Neo4j settings).
- `data-service/app.py` — seven routes on the guarded router before the final `include_router`: `POST|GET /mapping/sessions`, `GET /mapping/sessions/{session_id}`, `POST /mapping/sessions/{session_id}/decisions`, `POST /mapping/sessions/{session_id}/apply`, `GET|POST /mapping/profiles`; structured `MAPPING_*` errors, `_internal_failure` (`MAPPING_FAILED`, 502) otherwise; actor = principal username; `MappingSession`, `MappingDecision`, `MappingProfile` added to `LOCKED_NODE_LABELS`.
- `data-service/route_policy.py` — seven rows; sessions/reads/apply `member + connector` (body or query project), decisions and authored profiles member-only (`editor`); `tests/test_route_inventory.py` count 113 → 120.
- Docs: `spec/SECURITY-BOUNDARY.md` (seven route-policy rows in sorted position, connector-scope prose), `spec/DATABASE.md` (Graph Separation, "Mapping learning state" section, three relationship rows, Phase 1303 migration note), `spec/LPG-OWL-MAPPING.md` (experimental rows, provenance-only, not exported), `spec/API.md` (Mapping section).
- `data-service/tests/test_mapping_routes.py` — 10 route tests through a real admin session with an in-memory store and a stub driver.

## Verification

- `python -m pytest data-service/tests/test_mapping_engine.py data-service/tests/test_mapping_routes.py -q` → **26 passed**.
- `python -m pytest data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py data-service/tests/test_cross_project_matrix.py data-service/tests/test_graph_routes.py -q` → **2392 passed** (the generated denial sweeps include the new rows).
- `python -m pytest tools/de01/tests/test_reproducibility_scope_drift.py -q` → passed (no LLM call site).
- Full suite on the host: **5757 passed, 35 skipped, 4 failed, 25 errors**. All failures/errors are the known Neo4j-unreachable host baseline: `test_dg_context.py` ×4 (`neo4j` hostname resolves only inside compose) and the `*Integration` classes of `test_cg_structure_checks.py` and `test_computgraph_consult.py` ×25 (live Neo4j; Docker stopped). No mapping-related failure. A pre-change baseline run was not recorded; the failing ids match the documented environmental baseline classes.

## Deviations

- Orchestration lives in `mapping_store` (not in app.py) so the routes stay thin and tests can replace the low-level persistence functions.
- nginx is unchanged (see 1303-05 summary): the Web UI import is bounded by the generic 1 MB request limit; the Revit reader keeps uploads small.

## Open issues

- Live Neo4j round trip not yet exercised (plan 06 after the container rebuild); in-container pytest of the mapping tests is part of plan 06.
