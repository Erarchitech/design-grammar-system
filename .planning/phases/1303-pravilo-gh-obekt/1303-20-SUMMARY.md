---
phase: 1303-pravilo-gh-obekt
plan: "20"
subsystem: data-service-ingest-context
tags: [d-61, g5, dgopn-06, swrl-conventions, participants, schema-propagation, russian-keywords]
requires:
  - phase: 1303-pravilo-gh-obekt
    provides: "1303-17 (computable vocabulary merge in dg_context/dg_knowledge); 1303-19 (context participants in the C# validator)"
provides:
  - "SWRL_CONVENTIONS['computable_form'] with participants, relations, the not-a-class list and a participants_example (Task 1)"
  - "Russian shape keywords in _SHAPE_KEYWORD_PATTERNS; the slab-opening rule selects min_limit"
  - "_EXISTING_ENTITIES_QUERY returns domain for ObjectProperty rows"
  - "cypher_template.txt PARTICIPANTS AND RELATIONS section (after QUALITY CHECKS), schema documents carry ObjectProperty domain/range"
affects: [1303-21, 1303-22, 1303-23]
tech-stack:
  added: []
  patterns:
    - "participant instruction rides swrl_conventions (already serialized by n8n): no workflow change, no new pick-list key"
    - "docs-only template sections go after QUALITY CHECKS so _template_block() stays unchanged"
key-files:
  created: []
  modified:
    - data-service/dg_knowledge.py
    - data-service/tests/test_dg_knowledge.py
    - data-service/dg_context.py
    - data-service/tests/test_dg_context.py
    - data-service/tests/test_cypher_allowlist.py
    - cypher_template.txt
    - training/dataset_schema.json
    - spec/DATABASE.md
    - spec/LPG-OWL-MAPPING.md
    - .github/copilot-instructions.md
    - README.md
key-decisions:
  - "ObjectProperty domain/range are annotations only; spec/LPG-OWL-MAPPING.md states they are NOT exported as rdfs:domain/rdfs:range (RDFS would infer class membership from a rule's wording); the flat-vocabulary rule is kept."
  - "ontology/dg-shapes.ttl is unchanged: it holds no ObjectProperty shape (0 matches) and domain/range are optional annotations, so no SHACL shape is added or changed."
  - "spec/REPRODUCIBILITY.md unchanged: no LLM call site added; n8n workflow files untouched."
requirements-completed: []
requirements_partial: [DGOPN-06]
duration: ~1h (this session: Tasks 2-3 and close-out; Task 1 earlier)
completed: 2026-10-22
status: complete
---

# Phase 1303 Plan 20: Participants in the ingest prompt, Russian shape keywords Summary

The ingest prompt now tells the LLM to write every other object class a rule names as a participant (ClassAtom plus ObjectPropertyAtom) while keeping one numeric subject property, Russian rules such as the slab-opening rule select the `min_limit` shape, and ObjectProperty `domain`/`range` flow through the context and every schema document as annotations, never as OWL axioms.

## Performance

- Tasks: 3 of 3. Commits: `24be756` (wip, Task 1 implementation), `913b5b0` (Task 1 pins), `7b19c5f` (Task 2 RED), `689ab0d` (Task 2 GREEN), `bbaf667` (Task 3).
- Task 2 RED to GREEN: `TestRussianShapeKeywordsAndObjectPropertyDomain` added with 23 tests; RED = 20 failed, 3 passed (the 3 are the English, six-shape and domain pass-through pins that hold before and after). GREEN = all 23 pass; `tests/test_dg_context.py` 93 passed, 4 failed (the 4 baseline endpoint tests only).
- Full data-service suite after Task 3: 6407 passed, 35 skipped, 6 failed, 25 errors (see Baseline comparison). `tools/de01/tests`: 173 passed, 1 failed (golden-fixture runner, environmental baseline).

## Accomplishments

- Task 1 (done earlier, `24be756` + `913b5b0`): `computable_form` keeps one subject, one numeric DataPropertyAtom, one swrlb comparison and adds participants, ObjectPropertyAtom relations, the not-a-class list (outline, projection, clearance, edge, distance) and `participants_example`, whose Cypher passes the write allowlist and the full ingest validator.
- Task 2: each of the six shapes gained Russian stems matched as lowercase substrings (`не ближе`, `не менее`, `не меньше`, `минимум` -> min_limit; `не более`, `не больше`, `не превыш`, `максимум`, `не дальше` -> max_limit; `между` -> range; `доля`, `процент`, `отношение` -> ratio; `должен иметь`, `обязательн` -> boolean_requirement; `количество`, `число` -> existence_count). The catalog keeps exactly six shapes. `n.domain AS domain` added to `_EXISTING_ENTITIES_QUERY`; rows are passed through as `dict(record)`, so no other code changed. Determinism is covered by a non-endpoint test (`assemble_context` twice, byte-identical JSON, slab-opening rule selects `["min_limit"]`).
- Task 3: `cypher_template.txt` ObjectProperty props are `label, domain, range`; new "PARTICIPANTS AND RELATIONS" section with a "PARTICIPANT MERGE EXAMPLE" placed after QUALITY CHECKS (so `_template_block()` is unchanged); `test_cypher_template_participants_section_passes_the_write_profile` instantiates it and passes the write profile. `training/dataset_schema.json` gained an ObjectProperty node entry (valid JSON checked); `spec/DATABASE.md` shows `hostedBy` with domain/range plus a participants paragraph (links `spec/SWRL-SUBSET.md` section 2); `spec/LPG-OWL-MAPPING.md` has a new row stating domain/range are NOT exported as `rdfs:domain`/`rdfs:range` and the two stale "no ObjectProperty nodes exist" sentences are updated; `.github/copilot-instructions.md` and `README.md` carry one-line updates.
- `ontology/dg-shapes.ttl`: checked, no ObjectProperty shape exists; unchanged. `spec/SWRL-SUBSET.md` machine-checked blocks untouched (no atom-type or builtin boundary change in this plan).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's keyword list did not select a shape for the plan's own acceptance rule**
- **Found during:** Task 2 GREEN
- **Issue:** The slab-opening rule says `не может быть ближе 500мм`, not the bare `не ближе` the plan lists, so `_match_shape_ids` returned `[]` where the behavior block requires `["min_limit"]`.
- **Fix:** Added the verbal forms `не может/должен/должна/должно быть ближе` to min_limit and the mirror `... быть дальше` to max_limit (same meaning, same matching style). Documented in the comment above `_SHAPE_KEYWORD_PATTERNS`.
- **Files modified:** data-service/dg_context.py
- **Commit:** 689ab0d

**2. [Test fixture] RED test phrase adjusted**
- `Нагрузка не должна превышать` does not contain the plan's stem `не превыш`; the RED test phrase was changed to `Нагрузка не превышает` before the RED commit. The stem list is unchanged.

None of the above changes scope: still six shapes, no n8n or LLM call-site change.

## Baseline comparison

Failures after this plan, all outside plan-20 files and identical to the baseline classification in 1303-VALIDATION.md or logged in `deferred-items.md`:
- `test_dg_context.py::TestContextEndpoints::test_post_assemble_returns_200_for_valid_type`, `::test_get_debug_matches_post_assemble_body`, `TestDeterminism::test_repeated_assemble_calls_are_byte_identical`, `::test_get_debug_and_post_assemble_are_equal_for_graph_query` (endpoint 500, baseline).
- `test_static_proxy_boundary.py::test_nginx_proxies_only_to_data_service`, `::test_nginx_config_is_fully_clean` (logged in deferred-items.md since 1303-16: `/data-service/scripts/` nginx location from plan 1303-15 missing in the test allow-list; not touched here).
- 25 errors, all in `test_cg_structure_checks.py` and `test_computgraph_consult.py` integration classes, fail with `Failed to DNS resolve address neo4j:7687` (baseline).
- `tools/de01/tests/test_de01_runner.py::test_de01_runner_against_golden_fixture_has_zero_silent_disagreements` (baseline, environmental).
No new failure from plan-20 changes. The 4 `test_dg_context` endpoint tests are covered by the non-endpoint determinism test above.

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path or file access; `n.domain` is read-only inside an existing bound-parameter query.

## Open items

- The participants prompt is verified only against the cassettes and the allowlist; real LLM behavior (does it add participants to one-class rules?) needs the live pass in plan 1303-23.
- Plans 1303-19 and 1303-20 must ship together (1303-23).

## Self-Check: PASSED

Commits 24be756, 913b5b0, 7b19c5f, 689ab0d, bbaf667 exist; all files_modified paths present.
