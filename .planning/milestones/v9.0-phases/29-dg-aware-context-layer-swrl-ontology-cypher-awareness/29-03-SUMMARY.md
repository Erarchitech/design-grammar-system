---
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
plan: 03
subsystem: api
tags: [fastapi, data-service, neo4j, ontology, cypher, context-assembly]

# Dependency graph
requires:
  - phase: 29-01
    provides: "load_cypher_catalog()/cypher_shape_ids() defensive loader in dg_context.py this plan's assembler unions"
  - phase: 29-02
    provides: "dg_knowledge.swrl_conventions() + load_computgraph_catalog() this plan's assembler unions"
provides:
  - "data-service/dg_context.py — ContextAssembleRequest + assemble_context() deterministic assembler (CTXA-01, CTXA-05)"
  - "data-service/dg_context.py — fetch_existing_entities() live per-project OntoGraph union with injectable session (D-17)"
  - "data-service/dg_context.py — _RULE_EDIT_GUIDANCE resolving Pitfall 3 (Rule_Id regenerate + MATCH-DELETE + iri/SWRL_label preserve), human-approved"
  - "data-service/app.py — POST /context/assemble + GET /context/debug sharing one code path (D-04)"
  - "data-service/tests/test_dg_context.py — TestContextAssemble + TestDeterminism suites"
affects: [29-04, 29-05, 31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "assemble_context() dispatches on a module-level CONTEXT_REQUEST_TYPES set (not a Pydantic Literal) so unknown types raise ValueError and surface through app.py as a CONTEXT_TYPE_INVALID 422 structured error, not FastAPI's generic validation body"
    - "Deterministic keyword matching uses a fixed-order tuple (_SHAPE_ID_ORDER) iterated against a fixed keyword-pattern dict, never the CYPHER_SHAPE_IDS set, so shape selection order is stable across process runs (CTXA-05)"
    - "fetch_existing_entities(project, session=None) duck-types neo4j.Session.run() — unit tests pass a FixtureSession, production lazily opens dg_context's own module-level driver (avoids circular import with app.py)"
    - "GET /context/debug takes the same params as POST /context/assemble and calls the identical assemble_context() — zero parallel assembly logic in the route"

key-files:
  created: []
  modified:
    - data-service/dg_context.py
    - data-service/app.py
    - data-service/tests/test_dg_context.py

key-decisions:
  - "ContextAssembleRequest.type kept as plain str (not Pydantic Literal) so assemble_context()'s own ValueError dispatch drives app.py's CONTEXT_TYPE_INVALID 422 structured-error shape, matching connectors.py's create_credential() validate-against-id-set precedent"
  - "fetch_existing_entities' Cypher adds an explicit AND n.project = $project bound parameter absent from the original n8n 'Fetch Existing Entities' node — per-project isolation is a standing CLAUDE.md invariant; parameter is bound, never string-interpolated (T-29-03a)"
  - "Task 3 checkpoint:human-verify — user responded 'approved': the documented rule_edit convention (Rule_Id regenerates on numeric-limit change via the R_<DOMAIN>_<PROPERTY>_<LIMIT>_V format; old Rule + old atoms removed via MATCH-DELETE; ontology iri/SWRL_label preserved and reused, never regenerated) is confirmed as-is. No code changes requested. This convention is now locked for Phase 31 RING-02's atom-level diff-preview design to build on."

patterns-established:
  - "Assembled context dict has a stable key order (type, project, ontograph, metagraph, validgraph, computgraph, swrl_conventions, selected_cypher_shapes, existing_entities, [edit_guidance for rule_edit]) — every value is a fixed constant, a fixed-order keyword match, or an ORDER BY'd live query result, never a raw unordered set/dict-insertion-order artifact"

requirements-completed: [CTXA-01, CTXA-05]

coverage:
  - id: D1
    description: "assemble_context() returns per-layer keys (Ontograph/Metagraph/Validgraph/Computgraph) plus swrl_conventions and selected_cypher_shapes for all three request types (rule_ingest, rule_edit, graph_query)"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestContextAssemble (6 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "rule_ingest with 'maximum'+'height' text selects the max_limit Cypher shape and its referenced V7 concepts"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestContextAssemble::test_rule_ingest_maximum_height_selects_max_limit_shape"
        status: pass
    human_judgment: false
  - id: D3
    description: "graph_query about design states surfaces the v4 DesignState kind enum {ObjState, ParamState, PropState}"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestContextAssemble::test_graph_query_design_states_surfaces_kind_enum"
        status: pass
    human_judgment: false
  - id: D4
    description: "rule_edit context documents Rule_Id-regenerate-on-numeric-change + old-atom MATCH-DELETE cleanup + ontology iri/SWRL_label preservation (Pitfall 3 resolution)"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestContextAssemble::test_rule_edit_contains_edit_convention_guidance"
        status: pass
    human_judgment: false
  - id: D5
    description: "Unknown request type raises ValueError; live-entity union runs against an injectable FixtureSession with zero live Neo4j in unit tests"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestContextAssemble::test_unknown_type_raises_value_error"
        status: pass
    human_judgment: false
  - id: D6
    description: "POST /context/assemble and GET /context/debug are live, delegate exclusively to assemble_context(), and two identical POST calls return byte-identical JSON bodies (CTXA-05 determinism); debug and assemble bodies are equal for the same params"
    requirement: "CTXA-05"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestDeterminism (2 tests)"
        status: pass
      - kind: integration
        ref: "docker compose exec -T data-service pytest tests/test_dg_context.py -x (18/18 passed)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Task 3 checkpoint: human confirms the rule_edit Rule_Id-regenerate + MATCH-DELETE + iri/SWRL_label-preserve convention before it propagates to Phase 31 RING-02's diff-preview design"
    verification: []
    human_judgment: true
    rationale: "Architectural convention with downstream design impact (Phase 31 RING-02) — requires explicit human sign-off, not automatable. User responded 'approved' with no requested changes."

duration: ~35min (across the pre-checkpoint session + this continuation)
completed: 2026-07-12
status: complete
---

# Phase 29 Plan 03: DG-Aware Context Assembler + /context/assemble + /context/debug Summary

**Deterministic `assemble_context()` unions per-layer V7 concepts, SWRL conventions, matched Cypher catalog shapes, and a live per-project Neo4j entity query into one dict served identically by `POST /context/assemble` and `GET /context/debug`; the rule_edit Rule_Id-regenerate/MATCH-DELETE/iri-preserve convention is now human-approved**

## Performance

- **Duration:** ~35 min total (Tasks 1-2 in the initial session, Task 3 checkpoint resolved in this continuation)
- **Completed:** 2026-07-12
- **Tasks:** 3 (all complete — 2 auto + 1 checkpoint:human-verify, approved)
- **Files modified:** 3 (data-service/dg_context.py, data-service/app.py, data-service/tests/test_dg_context.py)

## Accomplishments

- `data-service/dg_context.py`: `ContextAssembleRequest` (type/project/rules_text/question) + `assemble_context(req, session=None)` deterministically assembling Ontograph/Metagraph/Validgraph/Computgraph concept subsets, `dg_knowledge.swrl_conventions()`, keyword-matched Cypher catalog shapes (`_match_shape_ids` against a fixed `_SHAPE_ID_ORDER` tuple), and the live per-project OntoGraph entity union (`fetch_existing_entities`) — all three request types (`rule_ingest`, `rule_edit`, `graph_query`) covered; unknown types raise `ValueError`
- `data-service/dg_context.py`: `fetch_existing_entities(project, session=None)` ports n8n's "Fetch Existing Entities" Cypher verbatim (rules-to-metagraph.json ~294-312) with one addition — a bound `$project` parameter (the original had none; per-project isolation is a standing CLAUDE.md invariant). Duck-types `neo4j.Session.run()`; a `FixtureSession` satisfies unit tests with zero live Neo4j, production lazily opens `dg_context`'s own module-level driver
- `data-service/dg_context.py`: `_RULE_EDIT_GUIDANCE` documents the resolved Pitfall 3 convention as four addressable keys (`rule_id_regenerates_on_numeric_change`, `old_atom_cleanup`, `ontology_entities_preserved`, `scope_note`) — surfaced under the `edit_guidance` key for `rule_edit` requests
- `data-service/app.py`: `import dg_context` alongside the existing `reasoner`/`connectors` sibling imports; `# Context assembler endpoints (Phase 29: CTXA-01..05)` banner; `POST /context/assemble` (thin route, `ValueError` → `_structured_error_response(..., "CONTEXT_TYPE_INVALID", 422)`); `GET /context/debug` (same query-param contract, builds the same `ContextAssembleRequest`, calls the identical `dg_context.assemble_context()` — zero parallel logic)
- `data-service/tests/test_dg_context.py`: `TestContextAssemble` (6 tests) — per-layer keys present, max_limit shape selection for "maximum height" text, DesignState kind enum {ObjState, ParamState, PropState} for graph_query, all four edit-guidance facts present for rule_edit, unknown-type ValueError, FixtureSession-only live-entity union. `TestDeterminism` (2 tests) — two identical `POST /context/assemble` calls return byte-identical JSON; `GET /context/debug` body equals `POST /context/assemble` body for the same params
- **Task 3 (checkpoint:human-verify) — approved.** Presented the assembled `rule_edit` context via `GET /context/debug?type=rule_edit&...`; user confirmed the Rule_Id-regenerate-on-numeric-change + old-atom MATCH-DELETE cleanup + ontology iri/SWRL_label-preservation convention exactly as documented. No code changes requested. This closes the Pitfall 3 resolution and locks the convention for Phase 31 RING-02's diff-preview design.
- Final verification re-run in this continuation session: `tests/test_dg_context.py` 18/18 green (`TestCypherCatalog` + `TestContextAssemble` + `TestDeterminism`); full `data-service` suite 145 passed / 1 pre-existing unrelated failure (`tests/test_error_responses.py::test_publish_validation_missing_config`, already logged in `deferred-items.md` from Plan 29-01, confirmed unrelated to this plan's files — no regression)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement assemble_context() with deterministic selection + live-entity union** - `1a44945` (feat)
2. **Task 2: Wire /context/assemble and /context/debug into app.py + determinism test** - `b6cfc30` (feat)
3. **Task 3: Confirm the rule_edit Rule_Id convention (human-verify checkpoint)** - no code changes; user responded "approved" — convention locked as documented in `_RULE_EDIT_GUIDANCE`

**Plan metadata:** `commit_docs` is `false` in `.planning/config.json` for this project (same as Plans 29-01/29-02) — the final metadata commit (this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md) is expected to skip via the SDK's `skipped_commit_docs_false` path; see the Self-Check section below for confirmation this was handled correctly rather than force-committed.

## Files Created/Modified

- `data-service/dg_context.py` - `ContextAssembleRequest`, `assemble_context()`, `fetch_existing_entities()`, `_RULE_EDIT_GUIDANCE`, `_match_shape_ids()`, per-layer concept dicts (`ONTOGRAPH_CONCEPTS`/`METAGRAPH_CONCEPTS`/`VALIDGRAPH_CONCEPTS`)
- `data-service/app.py` - `import dg_context`; `POST /context/assemble`; `GET /context/debug`
- `data-service/tests/test_dg_context.py` - `TestContextAssemble` (6 tests), `TestDeterminism` (2 tests)

## Decisions Made

- `ContextAssembleRequest.type` is a plain `str`, not a Pydantic `Literal` — `assemble_context()` validates it against the module-level `CONTEXT_REQUEST_TYPES` set and raises `ValueError`, which app.py translates to this project's own `{error, hint, code}` structured-error shape (`CONTEXT_TYPE_INVALID`) instead of FastAPI's generic validation-error body. Mirrors `connectors.py`'s `create_credential()` precedent.
- `fetch_existing_entities`'s ported Cypher adds a bound `$project` parameter that the original n8n node lacked, enforcing this system's standing per-project isolation invariant (CLAUDE.md) without ever string-interpolating untrusted text into the query (T-29-03a mitigation).
- **Checkpoint resolution:** the user approved the rule_edit convention exactly as documented — Rule_Id regenerates on a numeric-limit change (the limit is embedded in the `R_<DOMAIN>_<PROPERTY>_<LIMIT>_V` format), old Rule + old Atom subgraph cleaned up via MATCH-DELETE, ontology `iri`/`SWRL_label` matched and reused (never regenerated). This resolves Pitfall 3 and is now the frozen convention Phase 31 RING-02 builds its atom-level diff-preview design on.

## Deviations from Plan

None - plan executed exactly as written across all three tasks. The checkpoint required no code changes; the user's "approved" response confirmed the documented convention as-is.

## Issues Encountered

None new. The one pre-existing, unrelated test failure (`tests/test_error_responses.py::test_publish_validation_missing_config`) reappeared in the full-suite sanity run in this continuation session — same failure already logged in Plan 29-01's `deferred-items.md` (Speckle `/validation/publish` config handling; not a file this plan touches). Not re-logged as a new deviation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `assemble_context()` + `/context/assemble` + `/context/debug` are live and ready for Plan 29-04's Cypher validator + bounded retry loop (`/context/generate-cypher`) to build on top of, and for Plan 29-05's n8n prompt-node thinning to call instead of inline Function-node prompt construction
- The rule_edit convention (`_RULE_EDIT_GUIDANCE`) is now human-approved and frozen — Phase 31 RING-02's atom-level diff-preview design can proceed against it without re-litigating Pitfall 3
- No blockers

---
*Phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: data-service/dg_context.py
- FOUND: data-service/app.py
- FOUND: data-service/tests/test_dg_context.py
- FOUND: 1a44945 (Task 1 commit)
- FOUND: b6cfc30 (Task 2 commit)
- CONFIRMED: tests/test_dg_context.py 18/18 passed (re-run in this continuation)
- CONFIRMED: full data-service suite 145 passed / 1 pre-existing unrelated failure (no regression)
