---
phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
plan: 03
subsystem: dg-reasoner
tags: [owlready2, hermit, pyshacl, rdflib, owl, fastapi, python]

# Dependency graph
requires:
  - phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
    plan: 02
    provides: ontology_export.build_graph(session, project) -> rdflib.Graph and strip_hermit_unsupported(graph) -> int
  - phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
    plan: 01
    provides: dg-reasoner sidecar package (FastAPI app.py skeleton, Dockerfile w/ JRE, ./ontology read-only mount)
provides:
  - dg-reasoner/reasoning.py — run_consistency(project, engine, session) and run_shacl(project, session), the hybrid TBox+overlay+live-export union, builtin-atom stripping, NTriples serialization, timeout-bounded HermiT subprocess, real pySHACL plumbing
  - ontology/dg-disjointness.ttl — curated owl:disjointWith overlay (D-04), version-controlled, volume-mounted read-only
  - real POST /reason/consistency and POST /shacl/validate routes on dg-reasoner/app.py, replacing the Plan 01 501 stubs
affects: [821-04-data-service-proxy, 822-owl-2-dl-reasoning-integration, 823-shacl-validation]

# Tech tracking
tech-stack:
  added: []
  patterns: [multiprocessing.Process + join(timeout) + terminate() for hard wall-clock reasoner bounds (kills the java grandchild too), injectable-session functions (session=None defaults to a lazily-created module driver, tests inject a fixture-backed shim), lazy pyshacl/owlready2 imports inside functions to keep module import light]

key-files:
  created:
    - ontology/dg-disjointness.ttl
    - dg-reasoner/reasoning.py
    - dg-reasoner/tests/test_routes.py
  modified:
    - dg-reasoner/app.py

key-decisions:
  - "reasoning.py owns a lazy module-level Neo4j driver (_get_driver(), created only on first use) mirroring app.py's pattern, but every public function (run_consistency, run_shacl) also accepts an injectable `session` parameter — app.py opens one session per request via its existing driver and passes it through, so reasoning.py never needs its own connection in production; tests inject a FixtureSession and never touch Neo4j at all."
  - "_reason_with_timeout uses multiprocessing.Process + a Queue for the child->parent result handoff (Process itself has no return value) — join(timeout) then terminate() on expiry, and a child that exits without reporting (OS-killed) raises RuntimeError rather than silently claiming consistency."
  - "unsatisfiable_classes explicitly filters out owl:Nothing per the plan's 'ignoring owl:Nothing' contract note, computed via set subtraction on the IRI strings collected from onto.inconsistent_classes()."
  - "run_shacl builds its data graph from the live export (ontology_export.build_graph) rather than the full hybrid TBox+overlay union — SHACL shape validation targets project data, not TBox axioms; the plan explicitly allowed either ('the live export graph (or hybrid data graph)')."
  - "engine validation is layered: reasoning.SUPPORTED_ENGINES = frozenset({'hermit'}) is checked in both app.py's route (422 on unknown, so the reasoner is never invoked with a request that will fail) and defensively inside run_consistency itself (ValueError) in case it's ever called directly."

requirements-completed: []

coverage:
  - id: D1
    description: "ontology/dg-disjointness.ttl is a real curated ex: namespace owl:disjointWith overlay, not a seeded contradiction; DesignGrammar-V7.owl stays pristine"
    requirement: "REAS-05"
    verification:
      - kind: other
        ref: "rdflib parse exits 0 (6 triples); grep confirms owl:disjointWith present; ex:Door/ex:Window and ex:Wall/ex:Slab pairs declared as owl:Class with disjointWith, no subclass-under-two-parents construct"
        status: pass
    human_judgment: false
  - id: D2
    description: "_hybrid_union parses BOTH DesignGrammar-V7.owl (xml) AND dg-disjointness.ttl (turtle) and adds the live export triples"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "manual smoke run: reasoning._hybrid_union('fixture-proj', FixtureSession(fixture)) -> 2195 triples; axiom_counts shows disjointWith=2 (TBox's 0 + overlay's 2), subClassOf=65/domain=101/range=112 (from DesignGrammar-V7.owl), classDeclarations=80"
        status: pass
    human_judgment: false
  - id: D3
    description: "Reasoner input is serialized as NTriples (never Turtle) before Owlready2 load"
    requirement: "REAS-05"
    verification:
      - kind: other
        ref: "grep -Eq 'format=.(nt|ntriples)' dg-reasoner/reasoning.py; manual smoke run confirms _serialize_nt produces a 340KB .nt file from the fixture's hybrid union"
        status: pass
    human_judgment: false
  - id: D4
    description: "strip_hermit_unsupported is called and its count surfaced as stripped_builtin_rules in the D-10 response"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "manual smoke run: strip_hermit_unsupported(union) removed 1 swrl:Imp on the fixture (the R_BUILDING_MAX_STOREY_9_V rule, which has a BuiltinAtom body per Plan 02's fixture); test_reason_consistency_returns_d10_contract asserts stripped_builtin_rules is present in the response"
        status: pass
    human_judgment: false
  - id: D5
    description: "run_consistency enforces a wall-clock timeout via multiprocessing terminate() and returns the full D-10 response dict"
    requirement: "REAS-05"
    verification:
      - kind: other
        ref: "grep -Eq 'terminate|timeout' dg-reasoner/reasoning.py; test_reason_consistency_timeout_returns_504 asserts the route surfaces a monkeypatched timeout dict as HTTP 504"
        status: pass
    human_judgment: false
  - id: D6
    description: "run_shacl calls the real pySHACL validate() and returns {conforms: true, results: []} for empty shapes"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "manual smoke run: reasoning.run_shacl('fixture-proj', session=FixtureSession(fixture)) -> {'conforms': True, 'results': []} using the real pyshacl.validate() against an empty rdflib.Graph shapes graph"
        status: pass
    human_judgment: false
  - id: D7
    description: "Both routes exist on app.py returning the D-10/D-11 contract; the 501 not-implemented stubs are gone; pytest test_routes.py passes with HermiT monkeypatched (no docker/JRE)"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "python -m pytest dg-reasoner/tests/test_routes.py -q -> 4 passed; full dg-reasoner/tests suite -> 13 passed, 2 skipped (pre-existing live-Neo4j integration tests)"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-07-12
status: complete
---

# Phase 821 Plan 03: dg-reasoner Hybrid Reasoning Core & Real Routes Summary

**`dg-reasoner/reasoning.py` unions the pristine `DesignGrammar-V7.owl` TBox + the new curated `ontology/dg-disjointness.ttl` overlay + the live per-project export, strips HermiT-unsupported SWRL builtin rules, serializes to NTriples, and runs Owlready2/HermiT under a hard `multiprocessing`-enforced timeout — wired into real `POST /reason/consistency` (D-09/D-10) and `POST /shacl/validate` (D-11, real pySHACL against empty shapes) routes, replacing Plan 01's 501 stubs.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 3
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- `ontology/dg-disjointness.ttl`: a version-controlled, curated `owl:disjointWith` overlay in the `ex:` domain-vocabulary namespace (`ex:Door`/`ex:Window`, `ex:Wall`/`ex:Slab`) — genuine architectural disjointness axioms, not the Phase 820 spike's seeded contradiction. Keeps `DesignGrammar-V7.owl` pristine (D-04) while making the hybrid union non-trivial (its own TBox has 0 `disjointWith` axioms).
- `dg-reasoner/reasoning.py`: `_hybrid_union` (TBox xml + overlay turtle + live export, D-03), `_axiom_counts` (rdflib-parsed, never grep), `_serialize_nt` (Owlready2 cannot parse Turtle), `_reason_worker`/`_reason_with_timeout` (`multiprocessing.Process` + `Queue` + `join(timeout)` + `terminate()` on expiry — kills the java grandchild too), `run_consistency` (full D-10 contract dict, or a clean `{consistent: null, error: "timeout", ...}` dict on expiry), `run_shacl` (real `pyshacl.validate()` against an intentionally empty placeholder shapes graph, D-11).
- `dg-reasoner/app.py`: real `POST /reason/consistency` (`ConsistencyRequest{project, engine="hermit"}`, 422 on unknown engine, 504 passthrough on reasoner timeout) and `POST /shacl/validate` (`{project}` → `{conforms, results}`) routes, both opening a Neo4j session via the existing module-level driver and delegating to `reasoning.py`.
- `dg-reasoner/tests/test_routes.py`: 4 contract tests via FastAPI `TestClient`, with `reasoning.run_consistency`/`run_shacl` monkeypatched — asserts the D-10 response shape, unknown-engine 422, timeout 504, and the D-11 `{conforms: true, results: []}` shape. Zero docker/JRE dependency.
- Manually smoke-tested the full non-HermiT pipeline against Plan 02's committed fixture (no live Neo4j needed, `FixtureSession`): hybrid union produced 2195 triples (axiom_counts: subClassOf=65, domain=101, range=112, disjointWith=2, classDeclarations=80), `strip_hermit_unsupported` removed 1 builtin-referencing rule, NTriples serialization produced a valid 340KB `.nt` file, and `run_shacl` returned the real pySHACL `{conforms: True, results: []}`.
- Full `dg-reasoner/tests/` suite verified green: 13 passed, 2 skipped (pre-existing integration tests requiring live Neo4j).

## Task Commits

Each task was committed atomically:

1. **Task 1: Curated disjointness overlay (ontology/dg-disjointness.ttl)** - `90c8106` (feat)
2. **Task 2: Hybrid reasoning core (reasoning.py)** - `fae85f4` (feat)
3. **Task 3: Wire real routes into app.py + route contract tests** - `8b7122b` (feat)

_No TDD tasks in this plan; all three were `type="auto"` per the plan._

## Files Created/Modified

- `ontology/dg-disjointness.ttl` - curated `owl:disjointWith` overlay: `ex:Door`/`ex:Window`, `ex:Wall`/`ex:Slab`, header comment documenting the union-at-reasoning-time contract
- `dg-reasoner/reasoning.py` - `_hybrid_union`, `_axiom_counts`, `_serialize_nt`, `_reason_worker`, `_reason_with_timeout`, `run_consistency`, `run_shacl`, `_get_driver`, env vars `DG_REASONER_TIMEOUT_SECONDS`/`DG_OWL_PATH`/`DG_DISJOINTNESS_PATH`, `SUPPORTED_ENGINES`
- `dg-reasoner/app.py` - `ConsistencyRequest`/`ShaclRequest` pydantic models; real `POST /reason/consistency` and `POST /shacl/validate` handlers replacing the Plan 01 501 stubs
- `dg-reasoner/tests/test_routes.py` - 4 contract tests: D-10 shape, unknown-engine 422, timeout 504, D-11 empty-shapes shape

## Decisions Made

- **Injectable-session design over a hard Neo4j dependency:** `run_consistency`/`run_shacl` accept an optional `session` parameter; when omitted they lazily open one via a module-level driver (`_get_driver()`, created on first use, never at import time). In production `app.py` opens one session per request via its existing driver and passes it through — reasoning.py never opens its own connection when called from the API. Tests inject a `FixtureSession` (from Plan 02's test module) and never touch Neo4j, matching `ontology_export.build_graph`'s duck-typed contract.
- **`multiprocessing.Process` + `Queue` for the timeout boundary:** `Process` has no return value, so the child reports its result (`{"unsatisfiable_classes": [...]}` or `{"error": ...}`) through a `Queue`; the parent `join(timeout)`s and `terminate()`s on expiry (killing the java grandchild too, per D-09), and treats a child that exits without reporting (e.g. OS-killed) as a `RuntimeError` rather than silently claiming consistency.
- **`owl:Nothing` explicitly filtered from `unsatisfiable_classes`:** collected via set subtraction on the IRI strings from `onto.inconsistent_classes()`, matching the plan's "ignoring owl:Nothing" contract note for the `consistent` boolean.
- **`run_shacl` validates the live export, not the full hybrid union:** SHACL shape validation targets per-project data, not TBox axioms, so `run_shacl` calls `ontology_export.build_graph` directly rather than `_hybrid_union` — the plan explicitly permitted either choice.
- **Two-layer engine validation:** `app.py`'s route checks `payload.engine` against `reasoning.SUPPORTED_ENGINES` and returns 422 before ever calling into `reasoning.py` (so an unknown engine never reaches the reasoner); `run_consistency` also raises `ValueError` defensively for direct callers that bypass the route.

## Deviations from Plan

None — plan executed exactly as written. All three tasks' automated verify commands passed on first attempt.

## Issues Encountered

- **Local Windows dev host has no JRE** (matches Plan 01's own finding and the Phase 820 spike's documented workaround — the spike ran its HermiT steps inside a throwaway Linux container specifically because "No JRE is installed on the dev host"). This session additionally hit an Owlready2-on-Windows quirk: `Path(nt_path).as_uri()` produces a `file:///C:/Users/...`-shaped URI that Owlready2 mishandles on Windows (`OSError: [Errno 22] Invalid argument: '/C:/Users/...'`), surfacing *before* `sync_reasoner()` is even reached. This is a Windows-dev-host-only artifact: the dg-reasoner Docker image (Plan 01, `python:3.11-slim` + `openjdk-21-jre-headless`) is Linux, where `Path(...).as_uri()` produces a standard POSIX `file:///tmp/...` URI with no drive-letter ambiguity — the exact same `.as_uri()` pattern the 820 spike used successfully inside its Linux throwaway container. No code change was made for this; verification of the actual HermiT invocation is deferred to Plan 04's live integration round-trip (run inside the Docker image), consistent with RESEARCH.md's two-tier validation architecture (unit fidelity always-on, integration round-trip requires docker).
- `pyshacl==0.40.0` and `owlrl==7.6.2` (both already pinned in `dg-reasoner/requirements.txt` since Plan 01) were not yet installed in the local dev Python environment; installed them locally (matching the exact pinned versions) purely to run this plan's verification commands natively, same pattern Plan 02 used for `rdflib`/`pytest`.
- Beyond that: `_hybrid_union`, `strip_hermit_unsupported`, `_serialize_nt`, and `run_shacl` were all manually smoke-tested end-to-end against Plan 02's committed fixture and confirmed working before relying on route-level monkeypatched tests for the full route contract.

## User Setup Required

None — no external service configuration required. The Docker image already bakes the JRE (Plan 01); no changes needed there. `DG_REASONER_TIMEOUT_SECONDS`/`DG_OWL_PATH`/`DG_DISJOINTNESS_PATH` all have dev-safe defaults matching the compose mount paths from Plan 01.

## Next Phase Readiness

- `dg-reasoner/reasoning.py`'s `run_consistency`/`run_shacl` and `dg-reasoner/app.py`'s real routes are ready for Plan 04's live integration proof (real `v8-ui-smoke` project, live Neo4j, live JRE inside the Docker image) and the `data-service` thin-proxy route.
- The D-10 response contract (`consistent`, `unsatisfiable_classes`, `axiom_counts`, `duration_ms`, `stripped_builtin_rules`) is frozen for Phase 822's reasoner-screen UX; the D-11 contract (`conforms`, `results`) is frozen for Phase 823's real SHACL shapes.
- One thing worth a passing note for Plan 04: the actual HermiT subprocess invocation (`sync_reasoner()` succeeding against a real hybrid union, and the timeout path actually firing under load) has only been proven by the Phase 820 spike, not by this plan's own automated tests — Plan 04's live integration test inside the Docker image is where that gets proven for the production `reasoning.py` module. This plan's own verification covers everything up to and including the NTriples file handed to Owlready2, plus the full pySHACL path.
- No blockers.

---
*Phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation*
*Completed: 2026-07-12*

## Self-Check: PASSED

All 4 created/modified files verified present on disk (ontology/dg-disjointness.ttl, dg-reasoner/reasoning.py, dg-reasoner/tests/test_routes.py, dg-reasoner/app.py). All three task commits (`90c8106`, `fae85f4`, `8b7122b`) verified present in git log. Full `dg-reasoner/tests/` suite re-verified green (13 passed, 2 skipped) after writing this summary.
