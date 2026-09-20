---
phase: 38-ai-generated-grasshopper-script-inputs
plan: 03
subsystem: data-service
tags: [computgraph, metagraph, swrl, determinability, join-b, input-generation, data-service]

# Dependency graph
requires: [38-01]
provides:
  - "data-service/cg_input_bindings.py: load_input_bindings/binding_for_rule (inputBindings loader with the value-threshold fence), read_rule_limit (SWRL threshold extraction with violation-inversion decoding), classify_rule (determinability classifier, under-claims by construction), select_parameters (parameter selection + exclusion-reason reporting)"
  - "llm/structure_rules.json: inputBindings populated as a sibling top-level key with one direct-parameter and one monotone-bound seed binding"
  - "data-service/tests/cg_fixtures.py: additive rule/binding/parameter fixtures for the three determinability classes, reusable by plan 38-07"
affects: [38-04, 38-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Under-claim-by-construction: classify_rule() forces limit=None whenever determinability is geometry-required, regardless of what read_rule_limit found on the graph -- the guarantee lives in the classifier's own control flow, not in a downstream prompt instruction"
    - "Refuse-rather-than-guess on SWRL ambiguity: read_rule_limit demotes to None (with a warning) on zero, multiple, or malformed comparison BuiltinAtoms instead of picking one arbitrarily"
    - "Shared-constant path resolution: cg_input_bindings.py imports cg_structure_checks.STRUCTURE_RULES_FILE directly rather than recomputing it, making the two loaders' file paths structurally unable to diverge"

key-files:
  created:
    - data-service/cg_input_bindings.py
    - data-service/tests/test_cg_input_bindings.py
  modified:
    - llm/structure_rules.json
    - data-service/tests/cg_fixtures.py

key-decisions:
  - "inputBindings seeded against two real ruleIds rather than synthetic ones: R_STRUCT_FRAME_HEIGHT_VAR_V (already requires HTotal to be a Variable Float Parameter per Phase 37's own mapping, making it a natural direct-parameter binding) and R_URB_HEIGHT_MAX_75_V (the exact Rule_Id example CLAUDE.md's own format documentation uses, as a plausible monotone-bound rule over HTotal+SpansCount). The other two Phase 37 structural rules stay deliberately unmapped, exercising the geometry-required default against real data rather than only a unit-test double."
  - "read_rule_limit issues one Cypher call with two OPTIONAL MATCH hops (HAS_BODY -> BuiltinAtom, then ARG pos 1/2 -> Var/Literal) rather than three separate queries -- keeps the 'one parameterized read query' plan constraint literal while still returning one row per body-atom candidate for the multi-atom-ambiguity check to fan out over."
  - "select_parameters's Boolean-domain carve-out is an explicit `data_type != \"Boolean\"` guard in the missing-domain check, not a reordering of the four exclusion checks -- keeps the check order stable (kind, datatype, domain, reinstate-id) while still passing a null-domain Boolean straight to `bound`."
  - "cg_input_bindings.py's Tier 0 tests use a canned-row _FakeSession (mirrors test_cg_structure_checks.py's _CannedAlgorithmSession) rather than a write-oriented FakeGraph -- this module issues exactly one read call per function under test, so a plain list-of-dicts double is honest and sufficient."

requirements-completed: [GHIN-01]

coverage:
  - id: D-07
    description: "inputBindings is a new sibling top-level key in llm/structure_rules.json; Phase 37's load_structure_rules() needs zero changes -- proven by loading the edited file through the shipped loader and asserting the four existing mappings still parse"
    requirement: GHIN-01
    verification:
      - kind: automated
        ref: "test_load_structure_rules_unaffected_by_input_bindings_addition asserts the exact four original ruleId set against cg_structure_checks.load_structure_rules() on the real edited file; python -m pytest data-service/tests/test_cg_structure_checks.py -k convention -q -> 14/14 pass"
        status: pass
      human_judgment: false
  - id: D-08
    description: "Every binding declares determinability explicitly; a rule with no binding entry resolves to geometry-required"
    requirement: GHIN-01
    verification:
      - kind: automated
        ref: "test_unmapped_rule_classifies_geometry_required_with_limit_none; load_input_bindings raises InputBindingError for an unrecognized determinability value (test_unknown_determinability_raises)"
        status: pass
      human_judgment: false
  - id: D-10
    description: "The numeric limit is read from the Rule's SWRL atoms at call time and never read from or written to llm/structure_rules.json"
    requirement: GHIN-01
    verification:
      - kind: automated
        ref: "_FORBIDDEN_BINDING_KEYS fence pinned by 6 parametrized tests (one per key: min/max/threshold/value/limit/operator), each asserting the key name and ruleId appear in the raised InputBindingError's message"
        status: pass
      human_judgment: false
  - id: violation-inversion
    description: "swrlb:greaterThan(?v,X) decodes to constraint v<=X, swrlb:lessThan(?v,X) to v>=X, swrlb:notEqual(?v,X) to v==X (plus the two inclusive forms)"
    requirement: GHIN-01
    verification:
      - kind: automated
        ref: "test_greater_than_body_yields_inverted_le_operator, test_less_than_body_yields_inverted_ge_operator; BODY_BUILTIN_TO_CONSTRAINT asserted directly via the plan's own acceptance-criteria one-liner"
        status: pass
      human_judgment: false
  - id: D-09
    description: "classify_rule() returns geometry-required for anything it cannot prove, and the returned limit is None in that case -- can only ever under-claim"
    requirement: GHIN-01
    verification:
      - kind: automated
        ref: "test_unmapped_rule_classifies_geometry_required_with_limit_none uses a fixture rule with a real, readable swrlb:greaterThan atom and still asserts limit is None -- the structural guarantee, not a coincidence of missing data"
        status: pass
      human_judgment: false
  - id: forbidden-key-fence
    description: "A binding entry carrying a numeric limit, comparison operator or threshold key is rejected at load with an actionable error"
    requirement: GHIN-01
    verification:
      - kind: automated
        ref: "6 parametrized tests over min/max/threshold/value/limit/operator, each asserting the key name and ruleId in the message; _find_forbidden_key scans any nesting level"
        status: pass
      human_judgment: false
  - id: D-06
    description: "An architect-supplied parameterOverrides list replaces the declarative binding's parameter selection for that call, and the override path is exercised by test"
    requirement: GHIN-01
    verification:
      - kind: automated
        ref: "test_override_replaces_parameters_preserves_determinability asserts source=='override', parameterNames replaced, determinability unchanged"
        status: pass
      human_judgment: false

duration: ~40min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 03: Close JOIN B -- Determinability Classifier and SWRL Threshold Reader Summary

**A loadable `inputBindings` artifact plus `cg_input_bindings.py`'s determinability classifier and SWRL threshold reader, closing which Computgraph parameters a Metagraph rule constrains and whether its limit is checkable from parameters alone -- with the D-09 overclaiming guarantee enforced structurally rather than by prompt discipline.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 4
- **Files modified:** 4 (2 created)

## Accomplishments

- `data-service/cg_input_bindings.py` (new, ~420 lines) exposes the full JOIN B surface: `load_input_bindings`/`binding_for_rule` (the `inputBindings` loader, degrading to `{}` on any absence but raising `InputBindingError` for a present-but-malformed entry, including a value-threshold key at any nesting level -- the same fence `cg_structure_checks._FORBIDDEN_PARAM_KEYS` established, re-applied via `_FORBIDDEN_BINDING_KEYS`); `read_rule_limit` (one parameterized Cypher call recovering the Rule's numeric limit from its SWRL body atoms, decoding the violation-inverted semantics explicitly and demoting to `None` on any ambiguity -- unknown rule, zero comparison atoms, a `Var` where a `Literal` is expected, a non-numeric `lex`, or more than one competing comparison atom, each logged once rather than silently guessed); `classify_rule` (the determinability classifier: an unmapped rule defaults to `geometry-required` with `limit=None` and `source="default"`; a binding's class and parameters carry through with `source="binding"`; `parameter_overrides` replaces only *which* parameters are in scope, never the determinability class, with `source="override"`; `limit` is forced to `None` whenever `determinability == "geometry-required"`, regardless of what `read_rule_limit` found -- the single line making D-09 structural); `select_parameters` (partitions published `:Parameter` rows into `(bound, excluded)`, emitting all four documented exclusion reasons -- `non-variable-kind`, `unsupported-datatype`, `missing-domain`, `unresolved-reinstate-id` -- with an explicit Boolean-domain carve-out, both lists sorted by `parameterName`).
- `llm/structure_rules.json` gained the `inputBindings` sibling key with one `direct-parameter` binding (`R_STRUCT_FRAME_HEIGHT_VAR_V` -> `HTotal`) and one `monotone-bound` binding (`R_URB_HEIGHT_MAX_75_V` -> `HTotal`+`SpansCount`, `metricExpression="HTotal + 0.1 * SpansCount"`, `monotoneIn=["HTotal"]`); the pre-existing four `mappings[]` entries are byte-identical (confirmed via `git diff` showing additions only).
- `data-service/tests/cg_fixtures.py` gained additive fixtures for all three determinability classes -- `RULE_DIRECT_PARAM_ID`/`RULE_MONOTONE_ID`/`RULE_GEOMETRY_ID` plus their canned Neo4j row builders (`direct_param_limit_rows`, `geometry_rule_limit_rows`, `no_builtin_limit_rows`), the two binding-entry builders, and `published_parameter_rows()` -- eight rows exercising every `select_parameters` exclusion reason, the full `Float`/`Integer`/`Boolean`/`Text`/`Geometry` type table, and the Boolean-null-domain non-exclusion case -- reusable as-is by plan 38-07.
- `data-service/tests/test_cg_input_bindings.py` (new, 38 tests, all Tier 0 -- no Neo4j, no LLM) pins every documented behavior: the loader/fence (missing file, malformed JSON, all six forbidden keys, monotone-bound field requirements, duplicate `ruleId`, unknown `determinability`), the Phase 37 non-regression proof (`load_structure_rules()` against the real edited file, asserting the exact four original `ruleId`s), SWRL limit extraction (both inversion directions, unknown-rule raise, zero/multiple/malformed comparison atoms all resolving to `None`), classification (the D-09 guarantee against a rule with a *readable* limit, the override path, `RuleNotFoundError` surfacing before any binding lookup), and selection (parametrized type-mapping table, all four exclusion reasons, the Boolean carve-out, sort-order, and named-parameter restriction).

## Task Commits

Each task was committed atomically:

1. **Task 1: inputBindings loader with the value-threshold fence** - `811cd01` (feat)
2. **Task 2: SWRL limit extraction from the Rule's atoms** - `491f2c8` (feat)
3. **Task 3: Determinability classifier and parameter selection** - `4cbff64` (feat)
4. **Task 4: Tier 0 tests including the Phase 37 non-regression proof** - `c6fbb53` (test)

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `data-service/cg_input_bindings.py` (new) - loader/fence, SWRL limit extraction, classifier, parameter selection
- `llm/structure_rules.json` - `inputBindings` sibling key added (mappings unchanged)
- `data-service/tests/cg_fixtures.py` - additive rule/binding/parameter fixtures for all three determinability classes
- `data-service/tests/test_cg_input_bindings.py` (new) - 38 Tier 0 tests

## Decisions Made

- Seeded `inputBindings` against two real, plausible `Rule_Id`s (`R_STRUCT_FRAME_HEIGHT_VAR_V` for `direct-parameter`, `R_URB_HEIGHT_MAX_75_V` -- CLAUDE.md's own format-documentation example -- for `monotone-bound`) rather than inventing placeholder ids, leaving the other two Phase 37 structural rules deliberately unmapped so the `geometry-required` default is exercised against a real artifact shape.
- `read_rule_limit` fans a single Cypher call's `OPTIONAL MATCH` chain (`HAS_BODY` -> `BuiltinAtom`, then `ARG` pos 1/2 -> `Var`/`Literal`) out to one row per candidate comparison atom, so the "exactly one parameterized query" constraint and the "detect >1 competing atom" requirement are both satisfied by the same call rather than needing a second query.
- The Boolean-domain carve-out in `select_parameters` is an explicit `data_type != "Boolean"` guard inside the `missing-domain` check, not a reordering of the four checks -- keeps the documented check order (kind, datatype, domain, reinstate-id) stable while still routing a null-domain Boolean straight to `bound`.
- Tier 0 tests use a plain canned-row `_FakeSession` (mirroring `test_cg_structure_checks.py`'s `_CannedAlgorithmSession`) since every function under test issues exactly one read call -- no write-oriented `FakeGraph` needed.

## Deviations from Plan

None -- plan executed exactly as written. Tasks were committed in four passes as specified; Task 1's commit includes `llm/structure_rules.json` alongside the loader module since the plan's `files_modified` list scopes both to Task 1.

## Issues Encountered

One self-caught test bug during Task 4 verification: an early draft of `test_greater_than_body_yields_inverted_le_operator` passed a bare dict to `_FakeSession(...)` instead of a one-element list, which `list(dict)` silently turned into a list of dict *keys* rather than raising -- surfaced immediately as an `AttributeError: 'str' object has no attribute 'get'` on the first `pytest` run, fixed inline before commit (not a deviation from scope, an in-task test-authoring fix caught by the plan's own automated verify command).

## User Setup Required

None -- no external service configuration required. All verification ran locally via `python -m pytest`; the Neo4j-dependent integration tier of the sibling `test_cg_structure_checks.py` suite still fails from the host with the pre-existing `getaddrinfo failed` baseline (`neo4j` hostname only resolves inside the compose network, documented in STATE.md/CLAUDE.md) -- confirmed unrelated to this plan's changes and untouched by it.

## Next Phase Readiness

- Plan 38-04 (candidate generation) can call `classify_rule` + `select_parameters` directly to populate `determinabilityClass`, `ruleLimit`, `boundParameters[]`, and `excludedParameters[]` in the `POST /computgraph/generate-inputs` response, per `spec/API.md`'s contract.
- Plan 38-07 (SC1 measurement) inherits real fixtures for all three determinability classes plus a parameter-row set exercising every exclusion reason, rather than needing to build its own.
- No blockers.

## Self-Check: PASSED

Verified both created files exist on disk (`data-service/cg_input_bindings.py`, `data-service/tests/test_cg_input_bindings.py`) and all 4 task commit hashes (811cd01, 491f2c8, 4cbff64, c6fbb53) are present in `git log --oneline`.

---
*Phase: 38-ai-generated-grasshopper-script-inputs*
*Completed: 2026-07-27*
