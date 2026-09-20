---
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
plan: 01
subsystem: api
tags: [cypher, swrl, neo4j, fastapi, json-catalog, data-service]

# Dependency graph
requires: []
provides:
  - "llm/cypher_catalog.json — versioned {version, shapes:[...]} catalog with all 6 standard rule shapes"
  - "data-service/dg_context.py — defensive load_cypher_catalog() + CYPHER_SHAPE_IDS index, module skeleton for the rest of Phase 29"
  - "data-service/tests/test_dg_context.py — TestCypherCatalog suite, pattern precedent for later Phase 29 test classes"
affects: [29-02, 29-03, 29-04, 29-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dg_context.py mirrors reasoner.py/connectors.py: module constant path + defensive load_*() helper that never raises"
    - "Cypher catalog resolved via DG_KNOWLEDGE_REPO_ROOT (Docker /mnt/repo mount) — no Dockerfile COPY change needed for repo-root llm/ artifact"

key-files:
  created:
    - llm/cypher_catalog.json
    - data-service/dg_context.py
    - data-service/tests/test_dg_context.py
    - .planning/milestones/v9.0-phases/29-dg-aware-context-layer-swrl-ontology-cypher-awareness/deferred-items.md
  modified: []

key-decisions:
  - "Catalog resolves via DG_KNOWLEDGE_REPO_ROOT env var against the existing .:/mnt/repo:ro mount — confirmed inside the running container, resolves to /mnt/repo/llm/cypher_catalog.json"
  - "CYPHER_SHAPE_IDS computed once at import time (mirrors REASONER_IDS/CONNECTOR_IDS pattern); load_cypher_catalog()/cypher_shape_ids() remain callable directly for dynamic re-reads in tests"
  - "existence_count models D-12's 'builtin atom pair' as swrlb:greaterThanOrEqual (existence check on the count value) + swrlb:lessThan (count-threshold violation), both against the same project-keyed ?count Var"

patterns-established:
  - "Catalog shape object: {id, name, description, swrl_pattern, cypher_template, worked_example} — array form, iterate in Python and (later) n8n JS"
  - "range shape stays a single catalog entry whose worked_example documents a min-rule + max-rule PAIR (two Rule nodes), per the existing cypher_template.txt two-rule convention — no new schema shape"

requirements-completed: [CTXA-02]

coverage:
  - id: D1
    description: "llm/cypher_catalog.json exists at repo root with integer version=1 and all 6 shapes (max_limit, min_limit, range, ratio, boolean_requirement, existence_count), each with a worked SWRL + Cypher example"
    requirement: "CTXA-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestCypherCatalog::test_real_catalog_exposes_expected_shape_ids"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestCypherCatalog::test_every_shape_has_required_keys"
        status: pass
    human_judgment: false
  - id: D2
    description: "existence_count shape's Var MERGE keys on both name and project (Pitfall 1 cross-project collision guard)"
    requirement: "CTXA-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestCypherCatalog::test_existence_count_var_merge_keys_on_project"
        status: pass
    human_judgment: false
  - id: D3
    description: "load_cypher_catalog() never raises — degrades to {version:0, shapes:[]} on missing, malformed, or wrong-shape catalog file"
    requirement: "CTXA-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestCypherCatalog::test_missing_catalog_file_degrades_to_empty_catalog"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestCypherCatalog::test_malformed_catalog_file_degrades_to_empty_catalog"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestCypherCatalog::test_catalog_file_with_wrong_shape_degrades_to_empty_catalog"
        status: pass
    human_judgment: false
  - id: D4
    description: "dg_context.py resolves the catalog path via DG_KNOWLEDGE_REPO_ROOT inside the data-service container without a Dockerfile change"
    requirement: "CTXA-02"
    verification:
      - kind: integration
        ref: "docker compose exec -T data-service python -c \"import dg_context; ...\" — confirmed CYPHER_CATALOG_FILE == /mnt/repo/llm/cypher_catalog.json, exists=True"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-12
status: complete
---

# Phase 29 Plan 01: Cypher Catalog Foundation Summary

**Versioned llm/cypher_catalog.json (6 rule shapes) plus a never-raising dg_context.py loader resolved via the existing DG_KNOWLEDGE_REPO_ROOT /mnt/repo Docker mount**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-12T15:58:59Z
- **Tasks:** 2 (both complete)
- **Files modified:** 3 created (1 JSON catalog, 1 Python module, 1 test file) + 1 deferred-items log

## Accomplishments
- `llm/cypher_catalog.json` at repo root: `{version: 1, shapes: [...]}` with all six shapes (`max_limit`, `min_limit`, `range`, `ratio`, `boolean_requirement`, `existence_count`), each carrying `id`/`name`/`description`/`swrl_pattern`/`cypher_template`/`worked_example` and using only MERGE/SET Cypher (no DELETE/DETACH/REMOVE/DROP/CREATE anywhere in the catalog)
- `range` shape preserves the cypher_template.txt two-separate-violation-rules convention: one `worked_example` documents a min-rule (`R_URB_HEIGHT_MIN_10_V`) + max-rule (`R_URB_HEIGHT_MAX_75_V`) pair, sharing the same `ex:Building`/`ex:height` OntoGraph nodes via MERGE reuse
- `existence_count` (new territory, D-12) models "at least N related things exist" as a `swrlb:greaterThanOrEqual` (existence check) + `swrlb:lessThan` (count-threshold violation) Builtin atom pair against a `Literal` threshold, reusing only the documented node labels/relationships; its `Var` MERGE keys on both `name` and `project` (Pitfall 1 regression guard)
- `data-service/dg_context.py`: module docstring explaining the `llm/`-vs-`dg_knowledge.py` split (D-16), `CYPHER_CATALOG_FILE` path constant resolved via `DG_KNOWLEDGE_REPO_ROOT`, `EXPECTED_SHAPE_IDS` constant, defensive `load_cypher_catalog()` (mirrors `reasoner.load_settings()`'s never-raise shape), `cypher_shape_ids()` function + `CYPHER_SHAPE_IDS` module-level derived index
- `data-service/tests/test_dg_context.py`: `TestCypherCatalog` with 7 tests covering the real catalog's shape-id/key completeness, the existence_count Pitfall-1 guard, the `CYPHER_SHAPE_IDS` constant, and three missing/malformed/wrong-shape degradation cases via a `catalog_path` monkeypatch fixture
- Rebuilt and restarted the `data-service` Docker image (no live-reload volume mount for source — confirmed via `Dockerfile`'s `COPY . .`) so the new files are testable in-container; confirmed `CYPHER_CATALOG_FILE` resolves to `/mnt/repo/llm/cypher_catalog.json` inside the container and 7/7 `TestCypherCatalog` tests pass there

## Task Commits

Each task was committed atomically:

1. **Task 1: Author llm/cypher_catalog.json with all six rule shapes** - `a3d2a09` (feat)
2. **Task 2: Create dg_context.py module skeleton + catalog loader, and test_dg_context.py with TestCypherCatalog** - `24a9bd2` (feat)

_Note: `commit_docs` is `false` for this project — the final metadata commit (SUMMARY/STATE/ROADMAP) is expected to be skipped per config; see `<final_commit>` handling below._

## Files Created/Modified
- `llm/cypher_catalog.json` - versioned Cypher expression catalog, 6 shapes with worked SWRL+Cypher examples
- `data-service/dg_context.py` - catalog path resolution + defensive loader + derived shape-id index
- `data-service/tests/test_dg_context.py` - `TestCypherCatalog` pytest suite
- `.planning/milestones/v9.0-phases/29-dg-aware-context-layer-swrl-ontology-cypher-awareness/deferred-items.md` - logged one unrelated pre-existing test failure (out of scope)

## Decisions Made
- Catalog lives at repo-root `llm/cypher_catalog.json` (not `data-service/llm/`), resolved via `DG_KNOWLEDGE_REPO_ROOT=/mnt/repo` against the already-existing `.:/mnt/repo:ro` volume mount — this resolves RESEARCH.md's Open Question 2 exactly as the plan's `<objective>` specified, with zero `Dockerfile`/build-context changes
- `CYPHER_SHAPE_IDS` is a module-level constant computed once at import time (matches the `REASONER_IDS`/`CONNECTOR_IDS` precedent) rather than a per-call function-only accessor; `cypher_shape_ids()` remains available as a plain function for tests/callers that need a fresh read after the catalog file changes
- `existence_count`'s "Builtin atom pair" (D-12) is `swrlb:greaterThanOrEqual` (asserts the count value is a valid non-negative existence check) followed by `swrlb:lessThan` (the actual count-threshold violation check) — both atoms share the same project-keyed `?count` Var, satisfying "reuses ONLY the documented node labels/relationships, no new schema surface"

## Deviations from Plan

None - plan executed exactly as written. One pre-existing, unrelated test failure (`tests/test_error_responses.py::test_publish_validation_missing_config`) was discovered while running the full `data-service` suite as a sanity check beyond the plan's required `TestCypherCatalog` scope; it concerns Speckle `/validation/publish` config handling, not any file this plan touches, and was logged to `deferred-items.md` per the executor's scope-boundary rule rather than fixed here.

## Issues Encountered
- The `data-service` container has no live-reload volume mount for source code (`Dockerfile` does `COPY . .` at build time, and `docker-compose.yml`'s only `data-service` volumes are `./data-service/data:/app/data` and `.:/mnt/repo:ro`) — the new `dg_context.py`/`test_dg_context.py` files were invisible to `docker compose exec` until `docker compose build data-service && docker compose up -d data-service` was run. This is expected/known Docker layer-caching behavior (per `CLAUDE.md`'s Known Gotchas), not a plan defect; resolved by rebuilding before running the plan's verify command.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `llm/cypher_catalog.json` and `dg_context.py`'s catalog-loading half are ready for Plan 29-02 to add the sibling `dg_knowledge.py` (SWRL convention block + Computgraph catalog) alongside the same module
- `dg_context.py`'s defensive-load pattern and `data-service/tests/test_dg_context.py`'s boilerplate/fixture structure are the established precedent for the remaining `TestContextAssemble`/`TestSwrlConventions`/`TestValidator`/`TestRetryLoop`/`TestDeterminism` classes RESEARCH.md's Phase Requirements → Test Map calls for in later plans
- No blockers. One deferred, out-of-scope item logged (see `deferred-items.md`) for a future phase touching Speckle validation-publish config.

---
*Phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: llm/cypher_catalog.json
- FOUND: data-service/dg_context.py
- FOUND: data-service/tests/test_dg_context.py
- FOUND: a3d2a09 (Task 1 commit)
- FOUND: 24a9bd2 (Task 2 commit)
