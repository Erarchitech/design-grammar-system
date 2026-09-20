---
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
plan: 02
subsystem: api
tags: [swrl, ontology, owl, xml, fastapi, data-service, computgraph]

# Dependency graph
requires:
  - phase: 29-01
    provides: "dg_context.py catalog-loading module skeleton this plan's sibling module sits alongside"
provides:
  - "data-service/dg_knowledge.py — SWRL_CONVENTIONS machine-readable block + swrl_conventions() accessor (CTXA-03)"
  - "data-service/dg_knowledge.py — load_computgraph_catalog() parsing the Computgraph portion of DesignGrammar-V7.owl, cached, DOCTYPE-safe (Computgraph portion of CTXA-01, forward-prep D-14/D-15)"
  - "data-service/tests/test_dg_knowledge.py — TestSwrlConventions + TestComputgraphCatalog suites"
affects: [29-03, 29-04, 29-05, 32, 34, 35]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dg_knowledge.py mirrors reasoner.py's module-constant layout for SWRL_CONVENTIONS; Computgraph catalog is parse-once + module-level cache, matching llm_gateway's expensive-discovery caching"
    - "OWL parsing reuses ontology/export_to_markdown_v7.py's existing helpers (localname/get_text/parse_domain_or_range/parse_one_of/get_about) via importlib.util.spec_from_file_location, the exact dynamic-load pattern ontology/make_docs_v7.py already uses — no new OWL walker written"

key-files:
  created:
    - data-service/dg_knowledge.py
    - data-service/tests/test_dg_knowledge.py
  modified: []

key-decisions:
  - "SWRL_CONVENTIONS structured as four independently-addressable top-level keys (violation_inversion, atom_ordering, argument_rules, naming_quirks) rather than a single prose blob, per the plan's machine-readable requirement"
  - "Computgraph catalog reuses export_to_markdown_v7.py's OWL-walking helper functions dynamically (importlib.util.spec_from_file_location) instead of writing a second parser — RESEARCH.md Assumption A1 confirmed true: the exporter script's helpers are plain module-level functions, fully importable"
  - "RESEARCH.md Pitfall 4 (DOCTYPE entity-block breaking naive ElementTree.parse) verified NOT to apply to this file — Python's stdlib xml.etree.ElementTree.parse() resolves DesignGrammar-V7.owl's small internal-entity table (<!ENTITY dgc \"...\">) natively; export_to_markdown_v7.py already calls plain ET.parse() with zero custom entity handling and has done so successfully. No pre-processing/entity-substitution/xml.sax workaround was needed."
  - "DG Canvas Annotation Convention grammar is derived directly from the OWL file's own Frame worked-example individual labels (Algorithm_1, Proc_11, Pat_11_DivideLine, Var_11_SpansCount, Const_11_ptZero, Emg_11_LineSDL/Emr typo, IntF_11_ParSplitAt) rather than invented — satisfies D-14's 'catalogs what's already defined' constraint"

patterns-established:
  - "Computgraph catalog shape: {source_iri, source_file, hub, entity_classes, relations, attributes, enum_values, annotation_convention} — entity_classes keyed by class name (Algorithm/Procedure/Pattern/Parameter/Interface) for O(1) lookup"

requirements-completed: [CTXA-03, CTXA-01]

coverage:
  - id: D1
    description: "SWRL_CONVENTIONS is a machine-readable dict encoding violation-inverted body semantics, HAS_BODY/HAS_HEAD atom ordering (order), ARG argument rules (pos), Var merge on name+project, and Rule_Id/Atom_Id/SWRL_label naming quirks — each independently addressable, not a single prose blob"
    requirement: "CTXA-03"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_knowledge.py::TestSwrlConventions (8 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "load_computgraph_catalog() parses the real DesignGrammar-V7.owl (DOCTYPE-safe) and returns the dgc:Computgraph hub plus the five entity classes Algorithm/Procedure/Pattern/Parameter/Interface"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_knowledge.py::TestComputgraphCatalog::test_returns_hub_class"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_dg_knowledge.py::TestComputgraphCatalog::test_returns_all_five_entity_classes"
        status: pass
    human_judgment: false
  - id: D3
    description: "No unresolved '&dgc;' entity literal survives into the parsed catalog output (Pitfall 4 guard)"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_knowledge.py::TestComputgraphCatalog::test_no_unresolved_dgc_entity_literal_survives"
        status: pass
    human_judgment: false
  - id: D4
    description: "Computgraph catalog parses once and caches — a second load_computgraph_catalog() call does not re-parse the OWL file"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_knowledge.py::TestComputgraphCatalog::test_second_call_does_not_reparse"
        status: pass
    human_judgment: false
  - id: D5
    description: "Catalog includes the DG Canvas Annotation Convention grammar (scribble/group naming patterns) as addressable data"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_knowledge.py::TestComputgraphCatalog::test_includes_annotation_convention_grammar"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-12
status: complete
---

# Phase 29 Plan 02: SWRL Conventions + Computgraph Catalog Summary

**Machine-readable SWRL convention dict plus a cached, DOCTYPE-safe Computgraph concept catalog parsed from the real DesignGrammar-V7.owl, reusing the existing export_to_markdown_v7.py OWL-walking helpers instead of a second parser**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-12T19:35:00Z
- **Tasks:** 2 (both complete)
- **Files modified:** 2 created (1 Python module, 1 test file)

## Accomplishments
- `data-service/dg_knowledge.py`: `SWRL_CONVENTIONS` module-level dict with four independently-addressable keys — `violation_inversion` (flag + statement), `atom_ordering` (HAS_BODY/HAS_HEAD + `order`), `argument_rules` (ARG + `pos`, Var merge on `name`+`project`, Literal merge on `lex`+`datatype`, Builtin merge on `iri`), and `naming_quirks` (Rule_Id/Atom_Id/SWRL_label/SWRL, reserved relationship properties) — plus a `swrl_conventions()` typed accessor
- `data-service/dg_knowledge.py`: `load_computgraph_catalog()` parses the Computgraph portion of the real `ontology/DesignGrammar-V7.owl` exactly once per process (module-level `_COMPUTGRAPH_CACHE`), returning the `dgc:Computgraph` hub, all five entity classes (Algorithm/Procedure/Pattern/Parameter/Interface) by resolved IRI + label + comment, `dgc:` relations (ObjectProperty) and attributes (DatatypeProperty) with domain/range, closed `owl:oneOf` enum values (ParamDataType, ListStructure), and the DG Canvas Annotation Convention grammar (7 naming patterns: Algorithm/Procedure/Pattern/VariableParam/ConstantParam/EmergentParam/Interface, including the OWL file's own `Emg`/`Emr` typo variant) derived from the file's Frame worked example
- Confirmed `ontology/export_to_markdown_v7.py`'s helper functions (`NS`, `localname`, `get_text`, `get_resource`, `get_about`, `parse_domain_or_range`, `parse_one_of`) are plain importable module-level functions (RESEARCH.md Assumption A1 verified true) — reused dynamically via `importlib.util.spec_from_file_location`, the exact pattern `ontology/make_docs_v7.py` already uses to invoke that same module, instead of writing a second OWL walker
- Verified directly against the live file that `xml.etree.ElementTree.parse()` resolves `DesignGrammar-V7.owl`'s DOCTYPE internal-entity block (`<!ENTITY dgc "http://example.org/design-grammar/comp#">` etc.) with zero custom handling — RESEARCH.md's Pitfall 4 concern (raised as `[ASSUMED — verify at implementation time]`) turned out not to apply to this file; `export_to_markdown_v7.py` already calls plain `ET.parse()` successfully, confirming the same for `dg_knowledge.py`
- `data-service/tests/test_dg_knowledge.py`: `TestSwrlConventions` (8 tests) covers every SWRL convention key; `TestComputgraphCatalog` (9 tests) covers hub + all five entity classes, zero unresolved `&dgc;` literals across the whole returned structure (recursive string-leaf scan), relations/enum-values presence, annotation-convention-grammar presence, source provenance, and a cache-hit test (monkeypatched `ET.parse` call-counter asserts exactly 1 parse across two `load_computgraph_catalog()` calls)
- Rebuilt and restarted the `data-service` Docker image after each task (no live-reload volume mount for source, per the known Docker layer-caching gotcha already documented in 29-01's SUMMARY) — confirmed `COMPUTGRAPH_OWL_FILE` resolves to `/mnt/repo/ontology/DesignGrammar-V7.owl` inside the container and all 17/17 `test_dg_knowledge.py` tests pass there; full `data-service` suite run afterward shows 134 passed / 1 pre-existing unrelated failure (no new regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Author the machine-readable SWRL convention block** - `1d1a991` (feat)
2. **Task 2: Parse the Computgraph concept catalog from DesignGrammar-V7.owl (DOCTYPE-safe, cached)** - `770b021` (feat)

_Note: `commit_docs` was `false` for the prior plan (29-01) in this project — the final metadata commit (SUMMARY/STATE/ROADMAP) is expected to skip per the same config; see `<final_commit>` handling below._

## Files Created/Modified
- `data-service/dg_knowledge.py` - SWRL_CONVENTIONS machine-readable block + swrl_conventions() accessor; COMPUTGRAPH_OWL_FILE path constant; load_computgraph_catalog() parse-once-and-cache function reusing export_to_markdown_v7.py's OWL helpers
- `data-service/tests/test_dg_knowledge.py` - TestSwrlConventions (8 tests) + TestComputgraphCatalog (9 tests)

## Decisions Made
- SWRL_CONVENTIONS uses four top-level dict keys (`violation_inversion`, `atom_ordering`, `argument_rules`, `naming_quirks`) instead of a single prose string, so the plan's "addressable, not opaque blob" acceptance criterion is met structurally, not just by convention
- Computgraph catalog dynamically loads `ontology/export_to_markdown_v7.py` via `importlib.util.spec_from_file_location` rather than reimplementing an OWL walker in `dg_knowledge.py` — mirrors `ontology/make_docs_v7.py`'s own driver pattern for invoking that module, confirmed at implementation time (RESEARCH.md A1) that the exporter's helper functions are freely importable (not locked inside `main()`)
- No entity pre-processing / `xml.sax` custom resolver was implemented — plain `ET.parse()` handles the file's small internal DTD entity table correctly out of the box, verified both standalone (`python -c "ET.parse(...)"` outside Docker) and inside the rebuilt `data-service` container
- Annotation Convention grammar is captured as 7 explicit `{kind, annotation, grammar, example}` pattern rows plus a `numbering` rule string, sourced entirely from the OWL file's Frame worked-example individual `rdfs:label` values already present in `DesignGrammar-V7.owl` (~2719-2930) — the OWL file's own data is the sole source, per D-14, not the future Phase 32 grammar spec

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<verify>` commands pass exactly as specified in 29-02-PLAN.md.

## Issues Encountered
- Same pre-existing Docker layer-caching gotcha as 29-01: `data-service`'s container has no live-reload source mount, so `dg_knowledge.py`/`test_dg_knowledge.py` were invisible to `docker compose exec` until `docker compose build data-service && docker compose up -d data-service` ran (twice, once per task, to keep verification honest per-task). Not a plan defect — expected, documented in CLAUDE.md's Known Gotchas.
- One unrelated, pre-existing test failure (`tests/test_error_responses.py::test_publish_validation_missing_config`) reappeared in the full-suite sanity run — this is the exact same failure already logged in 29-01's `deferred-items.md` (Speckle `/validation/publish` config handling, no file this plan touches). Not re-logged as a new deviation; still out of scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `dg_knowledge.py`'s `SWRL_CONVENTIONS`/`swrl_conventions()` and `load_computgraph_catalog()` are ready for plan 29-03's context assembler (`dg_context.py`'s `assemble_context()`) to import and union with `dg_context.py`'s existing `load_cypher_catalog()` half
- Per D-15, `load_computgraph_catalog()` is deliberately NOT imported or called from `app.py` or any endpoint yet — it is pure forward-prep, unit-tested in isolation, awaiting Phase 35's RCGN wiring
- The dynamic-`importlib` OWL-parsing approach (reusing `export_to_markdown_v7.py`) is now a proven, tested precedent — Phase 32 (CGSR, Computgraph object-model construction) and Phase 34 (ontology tagging components) can consult `dg_knowledge.load_computgraph_catalog()`'s output shape as a reference for what's already static-file-derivable versus what those phases still need to build fresh (parser-generated Computgraph instances from live GH canvases, not the static example)
- No blockers.

---
*Phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: data-service/dg_knowledge.py
- FOUND: data-service/tests/test_dg_knowledge.py
- FOUND: 1d1a991 (Task 1 commit)
- FOUND: 770b021 (Task 2 commit)
