---
phase: 823-shacl-validation-layer
plan: 02
subsystem: reasoning
tags: [shacl, pyshacl, rdflib, fastapi, owl, python]

# Dependency graph
requires:
  - phase: 823-01
    provides: build_valid_graph(session, project, run_id) + add_all_different(graph, individuals) ValidGraph ABox exporter
  - phase: 821
    provides: run_shacl scaffolding, _run_shacl_with_timeout spawn+killpg subprocess isolation, _local_name label-fallback helper
provides:
  - "ontology/dg-shapes.ttl — 8 version-controlled data-integrity SHACL NodeShapes spanning violation/warning/info severities"
  - "reasoning.py: DG_SHAPES_PATH env const, _walk_shacl_results(), _enrich_shacl_result(), upgraded run_shacl(project, run_id=None, session=None) with run-scoped ValidGraph ABox union + batch-wide owl:AllDifferent"
  - "Canonical shaclReport envelope {conforms, results:[{severity,what,where,howToFix,focusLabel,shapeId}], counts:{violation,warning,info}} — zero raw sh:*/RDF-IRI leakage"
  - "app.py ShaclRequest.run_id: str | None = None, forwarded to run_shacl; stale placeholder docstring corrected"
affects: [823-03, 823-05, 823-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_walk_shacl_results/_enrich_shacl_result two-stage mapping: raw pySHACL results_graph -> raw dicts -> enriched canonical findings, keeping rdflib.namespace.SH constants (never hard-coded shacl# IRI strings) out of the returned payload"
    - "allow_infos=True, allow_warnings=True passed to pyshacl.validate(); conforms is independently re-derived as not any(severity == 'violation') rather than trusted from pySHACL's raw bool"
    - "Sidecar {project, run_id?} contract extension pattern: add the field to the Pydantic model + the Python function signature + the route call simultaneously to avoid breaking the 821 backward-compat test"

key-files:
  created:
    - ontology/dg-shapes.ttl
    - dg-reasoner/tests/test_shacl_report.py
  modified:
    - dg-reasoner/reasoning.py
    - dg-reasoner/app.py
    - dg-reasoner/tests/test_routes.py

key-decisions:
  - "Tasks 1-2 (shapes authoring + run_shacl upgrade) were completed and committed in a concurrent session (844ccca, e59e507, e1ea738) before this executor was resumed; this run independently re-verified both via the full test_shacl_report.py suite and all Task 2 acceptance-criteria greps before touching Task 3"
  - "run_shacl's unchanged fake_run_shacl signature in test_routes.py backward-compat test was extended to fake_run_shacl(project, run_id=None, session=None) to match the new call site (reasoning.run_shacl(payload.project, run_id=payload.run_id)) — required so the existing test still exercises the real route wiring rather than mocking around it"
  - "app.py's shacl_validate docstring rewritten from the stale 821 placeholder note ('real shapes land in Phase 823') to describe the actual run_id-aware dual-path behavior now that Phase 823 has landed"

patterns-established:
  - "Sidecar request-model extension checklist: Pydantic field + function signature + route forward + backward-compat test signature update, all in one commit"

requirements-completed: [SHCL-01, SHCL-02]

coverage:
  - id: D1
    description: "ontology/dg-shapes.ttl authored with 8 data-integrity SHACL NodeShapes (violation/warning/info severities), each carrying sh:message + dgsh:howToFix"
    requirement: "SHCL-01"
    verification:
      - kind: unit
        ref: "rdflib parse + NodeShape count assertion (Task 1 automated verify, re-run this session)"
        status: pass
    human_judgment: false
  - id: D2
    description: "run_shacl loads real shapes, unions the run-scoped ValidGraph ABox with the Metagraph/OntoGraph export under owl:AllDifferent, and returns the canonical {conforms, results, counts} envelope with zero raw sh:*/RDF-IRI leakage"
    requirement: "SHCL-01"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_shacl_report.py (9 tests, re-run this session)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sidecar ShaclRequest accepts optional run_id, forwarded to run_shacl; 821 backward-compat contract holds when run_id is omitted; run-scoped path returns the canonical envelope"
    requirement: "SHCL-02"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_routes.py#test_shacl_validate_returns_empty_shapes_contract, #test_shacl_validate_with_run_id_returns_canonical_envelope"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-12
status: complete
---

# Phase 823 Plan 02: Real SHACL Shapes + Run-Scoped ABox Validation Summary

**Replaced the Phase 821 empty-placeholder SHACL shapes graph with 8 version-controlled data-integrity NodeShapes, upgraded `run_shacl` to union the run-scoped ValidGraph ABox under a batch-wide `owl:AllDifferent` and emit a raw-RDF-free `{conforms, results, counts}` envelope, and extended the sidecar's `ShaclRequest` with an optional `run_id` that forwards through the route.**

## Performance

- **Duration:** ~15 min (this session — Task 3 only; Tasks 1-2 landed in a prior concurrent session)
- **Tasks:** 3/3 complete (1 executed this session, 2 verified as already-complete)
- **Files modified this session:** 2 (`dg-reasoner/app.py`, `dg-reasoner/tests/test_routes.py`)

## Accomplishments
- `ontology/dg-shapes.ttl` authored with 8 data-integrity SHACL NodeShapes (DesignState-kind membership, PropState completeness, Run status, ObjState objectRef, Var name, Rule structural, Rule SWRL advisory, ParamState zero-parameter advisory) spanning all three severities, each with a plain-language `sh:message` and a `dgsh:howToFix` remediation string
- `run_shacl(project, run_id=None, session=None)` upgraded: loads real shapes from `DG_SHAPES_PATH`, unions in the run-scoped `ValidGraph` ABox (via Plan 823-01's `build_valid_graph`) when `run_id` is given, re-derives a single batch-wide `owl:AllDifferent` over both exports' minted individuals, calls `pyshacl.validate(..., allow_infos=True, allow_warnings=True)`, and maps every result through `_walk_shacl_results`/`_enrich_shacl_result` into the canonical six-key finding shape
- `app.ShaclRequest` gained `run_id: str | None = None`, forwarded to `reasoning.run_shacl(payload.project, run_id=payload.run_id)`; the stale "real shapes land in Phase 823" docstring was corrected to describe the actual dual-path (project-only vs. run-scoped) behavior
- Full `dg-reasoner` non-integration test suite (35 tests across `test_shacl_report.py`, `test_routes.py`, `test_validgraph_export.py`, and the pre-existing HermiT/consistency suites) passes green with zero regressions

## Task Commits

Tasks 1-2 were completed and committed during a concurrent prior session (this executor picked up mid-plan with those already verified):

1. **Task 1: Author ontology/dg-shapes.ttl + DG_SHAPES_PATH env const** — `844ccca` (feat), refined in `e59e507` (fix: named property shapes so sh:severity/message take effect)
2. **Task 2: Upgrade run_shacl — real shapes, run-scoped ABox union, allow_infos/warnings, structured result mapping** — `e1ea738` (wip: recover in-progress SHACL result-enrichment work + phase docs)
3. **Task 3: Add optional run_id to the sidecar ShaclRequest + backward-compat route tests** — `221a473` (feat, this session)

**Plan metadata:** committed together with this SUMMARY (see final commit below)

## Files Created/Modified
- `ontology/dg-shapes.ttl` - 8 data-integrity SHACL NodeShapes (Tasks 1)
- `dg-reasoner/reasoning.py` - `DG_SHAPES_PATH`, `_walk_shacl_results`, `_enrich_shacl_result`, upgraded `run_shacl` (Tasks 1-2)
- `dg-reasoner/tests/test_shacl_report.py` - new TDD test file for the result-walking/enrichment pipeline (Task 2)
- `dg-reasoner/app.py` - `ShaclRequest.run_id`, route forwarding, corrected docstring (Task 3, this session)
- `dg-reasoner/tests/test_routes.py` - `fake_run_shacl` signature extended to `(project, run_id=None, session=None)`; new `test_shacl_validate_with_run_id_returns_canonical_envelope` test (Task 3, this session)

## Decisions Made
- Tasks 1-2 verified as already-complete via independent re-run of `test_shacl_report.py` (9/9 pass) and all Task 2 acceptance-criteria greps (`allow_infos=True` x2, `allow_warnings=True` x2, zero "Deliberately empty placeholder" occurrences, uses `rdflib.namespace.SH` constants) before proceeding to Task 3 — no re-implementation performed
- Extended the existing backward-compat `fake_run_shacl` monkeypatch in `test_routes.py` to accept `run_id=None` rather than leaving it `(project, session=None)`, since the real route now always passes `run_id=payload.run_id` as a keyword argument; this keeps the test exercising the actual route wiring instead of silently breaking on signature mismatch
- Corrected the `shacl_validate` route docstring, which still described the 821-era "placeholder/empty shapes graph ... real shapes land in Phase 823" state even though Tasks 1-2 had already landed real shapes — stale documentation left over from the plan's TDD ordering (docstring predates shapes authoring)

## Deviations from Plan

None beyond the docstring correction called out above, which was explicitly requested in the resume briefing (not a Rule 1-4 deviation, but an instructed documentation fix alongside Task 3).

## Issues Encountered
None. Full `dg-reasoner/tests/` suite (35 passed, 4 integration tests deselected) confirmed no regression across all three tasks' combined changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The canonical `shaclReport` envelope (`{conforms, results, counts}` with six-key findings) is now real end-to-end in `dg-reasoner`, ready for Plan 823-03 (data-service proxy wrapping with top-level `status: "ok"`), Plan 823-05 (Grasshopper `ValidationPublishResponse` DTO), and Plan 823-06 (UI rendering)
- No blockers identified for downstream plans

---
*Phase: 823-shacl-validation-layer*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: ontology/dg-shapes.ttl
- FOUND: dg-reasoner/tests/test_shacl_report.py
- FOUND: .planning/phases/823-shacl-validation-layer/823-02-SUMMARY.md
- FOUND commit: 844ccca (Task 1)
- FOUND commit: e59e507 (Task 1 fix)
- FOUND commit: e1ea738 (Task 2)
- FOUND commit: 221a473 (Task 3, this session)
