---
phase: 823-shacl-validation-layer
plan: 01
subsystem: api
tags: [rdflib, owl, shacl-prep, neo4j, python, dg-reasoner]

# Dependency graph
requires:
  - phase: 821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation
    provides: ontology_export.py's mint()/make_argument_list()/bind_prefixes() helpers and duck-typed session contract this plan reuses verbatim
provides:
  - "dg-reasoner/valid_graph_export.py: build_valid_graph(session, project, run_id) -> (Graph, list[URIRef]) translating a ValidationRun's statePayloadJson v2 envelope to dgv:ObjState/ParamState/PropState/Run named individuals"
  - "add_all_different(graph, individuals): owl:AllDifferent (UNA) declaration over minted individuals, closing Phase 821's deferred D-05 obligation"
  - "DGV = Namespace(BASE + '/valid#') pinned namespace for Plan 823-02's SHACL shapes to target via sh:targetClass"
affects: [823-02, 823-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ValidGraph ABox export mirrors ontology_export.py's module structure exactly: label/key-scoped parameterized Cypher, duck-typed session, mint()-based IRI minting, no module-scope neo4j import"
    - "Defensive label-scoped branch for live DesignState/Run nodes: implemented per export-scoping mandate even though current write path never creates those labels (document-only per cypher_template.txt)"

key-files:
  created:
    - dg-reasoner/valid_graph_export.py
    - dg-reasoner/tests/test_validgraph_export.py
    - dg-reasoner/tests/fixtures/valid_graph_fixture.json
  modified: []

key-decisions:
  - "build_valid_graph returns (graph, minted_individuals) rather than emitting a single fixed UNA internally-only -- callers unioning multiple export batches (Plan 823-02's run_shacl) can re-derive owl:AllDifferent over the full combined individual list"
  - "Missing run row (no ValidationRun found) yields a fully empty graph (zero individuals, no exception); a found run row with null/absent statePayloadJson still mints the dgv:Run individual (sendStatus/validStatus) but zero state individuals -- these are two distinct degrade paths per D-04's behavior contract"

patterns-established:
  - "Pattern: ValidGraph ABox exporter as a sibling module to ontology_export.py, reusing its mint()/make_argument_list()/bind_prefixes() helpers verbatim rather than duplicating IRI-minting or rdf:List construction logic"

requirements-completed: [SHCL-01]

coverage:
  - id: D1
    description: "build_valid_graph mints one dgv:ObjState/ParamState/PropState individual per state and one dgv:Run individual from a ValidationRun's v2 statePayloadJson envelope, linked via dgv:hasState"
    requirement: "SHCL-01"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_validgraph_export.py#test_exactly_one_of_each_state_kind_and_run"
        status: pass
      - kind: unit
        ref: "dg-reasoner/tests/test_validgraph_export.py#test_state_individual_iris_match_mint_and_carry_labels"
        status: pass
      - kind: unit
        ref: "dg-reasoner/tests/test_validgraph_export.py#test_has_state_links_parent_designstate_to_each_child"
        status: pass
      - kind: unit
        ref: "dg-reasoner/tests/test_validgraph_export.py#test_run_individual_carries_send_and_valid_status"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every export batch with named individuals emits exactly one owl:AllDifferent (UNA) enumerating all minted individuals via owl:distinctMembers"
    requirement: "SHCL-01"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_validgraph_export.py#test_all_different_covers_every_minted_individual"
        status: pass
      - kind: unit
        ref: "dg-reasoner/tests/test_validgraph_export.py#test_add_all_different_is_noop_on_empty_list"
        status: pass
      - kind: unit
        ref: "dg-reasoner/tests/test_validgraph_export.py#test_add_all_different_emits_distinct_members_list"
        status: pass
    human_judgment: false
  - id: D3
    description: "Exporter reads run data with parameterized, label-scoped Cypher ($project, $runId) -- never scoped by the graph property"
    requirement: "SHCL-01"
    verification:
      - kind: unit
        ref: "grep -n 'graph:' dg-reasoner/valid_graph_export.py (source assertion: no {graph: property filter present)"
        status: pass
    human_judgment: false
  - id: D4
    description: "build_valid_graph never raises on a missing run row or a run with null/absent statePayloadJson"
    requirement: "SHCL-01"
    verification:
      - kind: unit
        ref: "dg-reasoner/tests/test_validgraph_export.py#test_missing_state_payload_json_does_not_raise_and_yields_zero_state_individuals"
        status: pass
      - kind: unit
        ref: "dg-reasoner/tests/test_validgraph_export.py#test_missing_run_row_does_not_raise_and_yields_zero_state_individuals"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-12
status: complete
---

# Phase 823 Plan 01: ValidGraph RDF ABox Exporter Summary

**New `dg-reasoner/valid_graph_export.py` translates a ValidationRun's `statePayloadJson` v2 envelope into `dgv:ObjState/ParamState/PropState/Run` named individuals plus the `owl:AllDifferent` UNA declaration Phase 821 deferred, all proven by fixture-backed unit tests.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-12T12:02:00+03:00
- **Completed:** 2026-07-12T12:26:15+03:00
- **Tasks:** 2 (TDD: RED then GREEN)
- **Files modified:** 3 (2 new test/fixture files, 1 new implementation file)

## Accomplishments
- Built `build_valid_graph(session, project, run_id) -> (Graph, list[URIRef])`, the ValidGraph→RDF ABox exporter Plan 823-02's SHACL layer will validate against
- Implemented `add_all_different(graph, individuals)` — the `owl:AllDifferent` (UNA) obligation Phase 821 explicitly deferred to this phase
- Pinned the `dgv:` namespace (`http://example.org/design-grammar/valid#`) that Plan 823-02's SHACL shapes will target via `sh:targetClass`
- Proved the exporter degrades gracefully (zero individuals, no exception) on both a missing run row and a run with null `statePayloadJson`

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1: Failing unit tests + v2-envelope fixture for build_valid_graph** - `20eb92a` (test)
2. **Task 2: Implement valid_graph_export.py (build_valid_graph + add_all_different / UNA)** - `d51558f` (feat)

## TDD Gate Compliance

- RED gate: `20eb92a` (`test(823-01): add failing unit tests...`) — confirmed collection failure with `ModuleNotFoundError: No module named 'valid_graph_export'` before implementation existed
- GREEN gate: `d51558f` (`feat(823-01): implement ValidGraph->RDF ABox exporter...`) — all 10 tests in `test_validgraph_export.py` pass
- No REFACTOR commit needed — implementation was clean on first GREEN pass

## Files Created/Modified
- `dg-reasoner/valid_graph_export.py` - `build_valid_graph()`/`add_all_different()`, `DGV` namespace, `RUN_QUERY`/`DESIGNSTATE_QUERY` Cypher constants
- `dg-reasoner/tests/test_validgraph_export.py` - fixture-session shim + 10 unit tests covering typing, IRI minting, labels, `dgv:hasState`, `dgv:sendStatus`/`dgv:validStatus`, UNA coverage, and the two no-exception degrade paths
- `dg-reasoner/tests/fixtures/valid_graph_fixture.json` - single `ValidationRun`-shaped fixture with a v2 envelope (1 objState/paramState/propState) matching `DesignStatePayloadV2Serializer`'s camelCase shape

## Decisions Made
- `build_valid_graph` returns `(graph, minted_individuals)` instead of only a `Graph` — lets Plan 823-02's `run_shacl` union this exporter's individuals with `ontology_export.build_graph`'s Metagraph/OntoGraph individuals and re-derive a single batch-wide `owl:AllDifferent`, rather than trusting two independently-emitted UNA declarations to compose correctly
- Two distinct empty-data degrade paths, per D-04's contract: a missing `ValidationRun` row yields a fully empty graph (no individuals at all, since nothing is confirmed to exist); a found row with null/absent `statePayloadJson` still mints the `dgv:Run` individual (its `sendStatus`/`validStatus` properties are independently confirmed by the row) but zero state individuals
- Defensive `DESIGNSTATE_QUERY` (label-scoped `n:DesignState OR n:Run`) implemented per the export-scoping mandate even though it is a confirmed no-op against current write-path data (`cypher_template.txt` documents these as document-only) — the plan explicitly required it not be silently omitted

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria were met without needing Rule 1-4 deviations.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. This is a pure Python module addition to the existing `dg-reasoner` sidecar, exercised entirely by fixture-backed unit tests with no live Neo4j/Docker dependency.

## Next Phase Readiness
- `dg-reasoner/valid_graph_export.py` and its `DGV` namespace are ready for Plan 823-02 to wire into `reasoning.py`'s `run_shacl()` (union with `ontology_export.build_graph`, load real `ontology/dg-shapes.ttl` shapes, map pySHACL results)
- The `(graph, minted_individuals)` return contract is the integration point Plan 823-02 needs for its own batch-wide UNA re-derivation
- No blockers identified for Plan 823-02

---
*Phase: 823-shacl-validation-layer*
*Completed: 2026-07-12*
