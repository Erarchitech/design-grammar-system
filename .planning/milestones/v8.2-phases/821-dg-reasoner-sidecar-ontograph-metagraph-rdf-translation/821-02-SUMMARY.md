---
phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
plan: 02
subsystem: dg-reasoner
tags: [rdflib, swrl, owl, cypher-to-rdf, pytest, python]

# Dependency graph
requires:
  - phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
    plan: 01
    provides: dg-reasoner sidecar package (Dockerfile, requirements.txt, app.py, tests/) with rdflib/neo4j pinned deps
provides:
  - dg-reasoner/ontology_export.py — build_graph(session, project) -> rdflib.Graph, the clean production Cypher->RDF translator (label-scoped Metagraph+OntoGraph export, ARG.pos/HAS_BODY/HAS_HEAD.order reification, SkippedAtom/SkippedRule capture)
  - strip_hermit_unsupported(graph) -> int helper for Plan 03's reasoning pipeline
  - committed offline-testable fixture + structural fidelity test suite proving translation correctness without docker/neo4j/JRE
affects: [821-03-reasoning-routes, 821-04-data-service-proxy, 822-owl-2-dl-reasoning-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [session-duck-typed build_graph (works with real neo4j.Session or a fixture-backed test shim, no neo4j import at module scope), fixture-driven structural (not golden-byte) RDF fidelity testing]

key-files:
  created:
    - dg-reasoner/ontology_export.py
    - dg-reasoner/tests/fixtures/metagraph_fixture.json
    - dg-reasoner/tests/test_ontology_export.py

key-decisions:
  - "build_graph(session, project) takes any object exposing neo4j.Session's .run(query, **params) contract (iterable of mapping-like records + .single() on the result), never importing neo4j at module scope — main()'s CLI path lazy-imports the real driver. This makes the module unit-testable via a duck-typed FixtureSession without installing or mocking the neo4j package at all."
  - "Fixture models the real R_BUILDING_MAX_STOREY_9_V worked example from spec/LPG-OWL-MAPPING.md directly (ClassAtom+DataPropertyAtom+BuiltinAtom body, DataPropertyAtom head) plus one deliberately-incomplete BuiltinAtom modeled on the spec's own R_COLUMN_CONTINUITY_V_A3 example (REFERS_TO present, zero ARG edges) to exercise the SkippedAtom path without inventing a second rule."
  - "Rule.kind/RuleName/RuleDescription are emitted as dg:-namespace annotation properties on the swrl:Imp individual per the spec's Node Mapping Table (no SWRL equivalent exists for these) — not covered by the 5 mandated fidelity assertions but implemented for full mapping-table compliance."
  - "owl:AllDifferent (UNA) was intentionally NOT implemented in this plan — spec/LPG-OWL-MAPPING.md explicitly scopes it forward to Phase 823's ValidGraph ABox export ('Phase 820's spike and current TBox-only reasoning do not need this — no individuals are minted')."

requirements-completed: []

coverage:
  - id: D1
    description: "ontology_export.py is a clean implementation of spec/LPG-OWL-MAPPING.md (custom Cypher + RDFLib), not a port of the spike; n10s/neosemantics is never imported"
    requirement: "REAS-05"
    verification:
      - kind: other
        ref: "grep -in 'n10s|neosemantics' dg-reasoner/ontology_export.py — only appears in a docstring comment explaining its absence, zero import statements"
        status: pass
    human_judgment: false
  - id: D2
    description: "Label-scoped Cypher (METAGRAPH_QUERY/ONTOGRAPH_QUERY) scopes by node label per spec #Export Scoping, never by the graph property"
    requirement: "REAS-05"
    verification:
      - kind: other
        ref: "grep -q 'n:Rule OR n:Atom' dg-reasoner/ontology_export.py — matches the plan's automated verify command"
        status: pass
    human_judgment: false
  - id: D3
    description: "ARG.pos and HAS_BODY/HAS_HEAD.order survive translation — structurally asserted via parsed-Turtle round-trip (D-14), not golden-file byte diffs"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_ontology_export.py::test_rule_is_swrl_imp_with_body_order_matching_has_body_order, ::test_rule_head_order_matches_has_head_order, ::test_binary_atom_argument_positions_match_arg_pos, ::test_head_atom_argument2_is_typed_literal_matching_arg_pos"
        status: pass
    human_judgment: false
  - id: D4
    description: "BuiltinAtom uses swrl:arguments (rdf:List) universally, never argument1/2"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_ontology_export.py::test_builtin_atom_uses_swrl_arguments_not_argument1_2"
        status: pass
    human_judgment: false
  - id: D5
    description: "SWRL-incomplete atoms (no ARG edges) are captured as annotated SkippedAtom, excluded from the swrl:Imp mapping"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_ontology_export.py::test_incomplete_atom_becomes_skipped_atom_and_is_excluded_from_swrl_imp"
        status: pass
    human_judgment: false
  - id: D6
    description: "Pitfall-1 atom-count guard: exported atom count equals independent label-based count"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_ontology_export.py::test_atom_count_guard_holds_for_fixture (build_graph itself raises AssertionError on mismatch — reaching any subsequent assertion proves the guard passed)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full test suite (unit + fidelity) runs green with zero docker/neo4j/JRE dependency"
    requirement: "REAS-05"
    verification:
      - kind: unit
        ref: "python -m pytest dg-reasoner/tests/ -q -> 9 passed, 2 skipped (pre-existing integration tests requiring live neo4j)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-12
status: complete
---

# Phase 821 Plan 02: dg-reasoner OntoGraph/Metagraph RDF Translator Summary

**Clean `dg-reasoner/ontology_export.py` Cypher->RDF translator built directly against `spec/LPG-OWL-MAPPING.md` (not ported from the Phase 820 spike), with a committed fixture and 8 structural fidelity tests proving `ARG.pos` and `HAS_BODY`/`HAS_HEAD.order` survive translation into ordered `swrl:AtomList`s and `swrl:argument1`/`argument2`/`arguments`.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2
- **Files modified:** 3 (all created)

## Accomplishments

- `dg-reasoner/ontology_export.py`: `build_graph(session, project) -> rdflib.Graph` implements every row of the spec's Metagraph->SWRL-RDF and OntoGraph->OWL Node Mapping Tables, label-scoped Cypher (`ONTOGRAPH_QUERY`, `METAGRAPH_QUERY`, `BODY_HEAD_QUERY`, `REFERS_QUERY`, `ARG_QUERY`, `ATOM_COUNT_QUERY`), IRI minting per the spec's `{base}/project/{project}/{kind}/{key}` scheme, edge-property reification (`ARG.pos` -> `argument1`/`argument2` for binary atoms or `swrl:arguments` rdf:List for `BuiltinAtom`; `HAS_BODY`/`HAS_HEAD.order` -> ordered `swrl:AtomList`), the Pitfall-1 atom-count guard, and `SkippedAtom`/`SkippedRule` capture for SWRL-incomplete data.
- `strip_hermit_unsupported(graph) -> int` exposed for Plan 03's reasoner-input filtering (removes `swrl:Imp` rules transitively referencing a `BuiltinAtom`, prunes orphaned `Variable`/`Builtin` declarations).
- `dg-reasoner/tests/fixtures/metagraph_fixture.json`: a graph-shaped fixture modeling the real `R_BUILDING_MAX_STOREY_9_V` worked example from the spec (multi-atom body, single-atom head, both ARG positions) plus a deliberately-incomplete `BuiltinAtom` modeled on the spec's own `R_COLUMN_CONTINUITY_V_A3` example.
- `dg-reasoner/tests/test_ontology_export.py`: 8 pytest tests via a `FixtureSession` that duck-types `neo4j.Session.run()` over the fixture — zero docker/neo4j/JRE dependency. Each test parses the produced Turtle back with rdflib and asserts structurally (D-14, no golden-byte diffs).
- Full `dg-reasoner/tests/` suite verified green: 9 passed, 2 skipped (pre-existing integration tests that correctly skip without a live Neo4j).

## Task Commits

Each task was committed atomically:

1. **Task 1: Clean Cypher->RDF translator per spec/LPG-OWL-MAPPING.md** - `d8d76df` (feat)
2. **Task 2: Committed fixture + structural fidelity tests** - `db869cb` (test)

_No TDD tasks in this plan; both were `type="auto"` per the plan._

## Files Created/Modified

- `dg-reasoner/ontology_export.py` - `build_graph`, `strip_hermit_unsupported`, `mint`, `expand_iri`, `xsd_datatype`, `make_atom_list`, `make_argument_list`, `bind_prefixes`, label-scoped Cypher constants, `ATOM_TYPE_MAP`, `main()` CLI (lazy neo4j import)
- `dg-reasoner/tests/fixtures/metagraph_fixture.json` - committed graph-shaped fixture (nodes + edges) for `fixture-proj`
- `dg-reasoner/tests/test_ontology_export.py` - `FixtureSession` shim + 8 structural fidelity tests

## Decisions Made

- **Session duck-typing over neo4j import:** `build_graph(session, project)` accepts any object exposing `.run(query, **params)` returning iterable mapping-like records with `.single()` on the result — matching `neo4j.Session` exactly but never importing `neo4j` at module scope. `main()`'s CLI path imports the real driver lazily. This makes the module trivially unit-testable (no mocking library needed, no `neo4j` package required at all for the test suite to pass) while keeping the production CLI path fully functional.
- **Fixture models the spec's own worked examples:** rather than inventing arbitrary test data, the fixture directly mirrors `R_BUILDING_MAX_STOREY_9_V` (the spec's complete-rule Turtle example) for the happy path, and `R_COLUMN_CONTINUITY_V_A3` (the spec's own cited incomplete-atom example) for the `SkippedAtom` path — keeping the tests traceable to the normative contract they verify.
- **Rule annotation properties (`dg:kind`/`dg:ruleName`/`dg:ruleDescription`) implemented but not fidelity-tested:** the Node Mapping Table specifies these as required (no SWRL equivalent), so they're emitted on every exported `swrl:Imp`, but the plan's 5 mandated fidelity assertions don't cover them — included for full mapping-table compliance rather than narrowly satisfying only the tested surface.
- **`owl:AllDifferent` (UNA) deliberately deferred:** the spec explicitly scopes this to Phase 823's future ValidGraph ABox export ("Phase 820's spike and current TBox-only reasoning do not need this — no individuals are minted"). Metagraph exports mint IRIs for Rule/Atom/Var but this plan does not add `owl:AllDifferent`, matching the spec's own stated scope boundary — not a gap, an explicit non-requirement for this plan.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' automated verify commands passed on first attempt with no rework needed.

## Issues Encountered

None. Local Python 3.14 environment has `rdflib==7.6.0` (exact match to the pinned dg-reasoner requirement) and `pytest==9.0.2` already available, so both tasks' verification commands ran natively without needing the Docker image.

## User Setup Required

None — no external service configuration required. The translator's live CLI path (`python ontology_export.py <project> [out.ttl]`) reuses the same `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` env-var contract already wired in `dg-reasoner/app.py` (Plan 01).

## Next Phase Readiness

- `dg-reasoner/ontology_export.py`'s `build_graph(session, project)` is ready for Plan 03's `/reason/consistency` and `/shacl/validate` routes to call directly with a live `driver.session()`.
- `strip_hermit_unsupported(graph)` is ready for Plan 03's HermiT invocation path (strip builtin-atom rules before passing the graph to Owlready2/HermiT).
- No blockers. One note for Plan 03: `build_graph`'s `AssertionError` on the Pitfall-1 atom-count guard is currently unhandled at the call-site level — Plan 03's route handlers should decide how to surface this as an HTTP error (e.g. 500 with a diagnostic message) rather than letting it propagate as an unhandled exception.

---
*Phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation*
*Completed: 2026-07-12*

## Self-Check: PASSED

All 3 created files verified present on disk (dg-reasoner/ontology_export.py, dg-reasoner/tests/fixtures/metagraph_fixture.json, dg-reasoner/tests/test_ontology_export.py). Both task commits (`d8d76df`, `db869cb`) verified present in git log. Full test suite re-verified green (9 passed, 2 skipped) after writing this summary.
