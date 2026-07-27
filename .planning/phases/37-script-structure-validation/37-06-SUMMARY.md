---
phase: 37-script-structure-validation
plan: 06
subsystem: api
tags: [fastapi, neo4j, llm-gateway, cypher, computgraph, grounding, consult]

# Dependency graph
requires:
  - phase: 37-01
    provides: ConsultCassetteAdapter, DEFAULT_CONSULT_ANSWER, cg_fixtures.py parser-faithful Frame envelope builders
  - phase: 37-05
    provides: POST /computgraph/validate thin-route and structured-error precedent this plan's route follows
provides:
  - "fetch_computgraph_subgraph() -- the first live read of the published Computgraph, dual-mode session, deterministic, scoped by both project and definitionId"
  - "build_consult_prompt() -- deterministic prompt assembly with an untrusted-input delimiter around the question"
  - "check_consult_grounding() -- pure post-check partitioning cited vs. ungrounded convention-shaped mentions, flag-don't-block"
  - "consult_computgraph() -- the SVAL-03 pipeline, single in-process provider resolution, no execute path"
  - "POST /computgraph/consult route in app.py"
affects: [v10-script-intelligence, computgraph-consult-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dedicated context-fetch function outside CONTEXT_REQUEST_TYPES for a single-definition read, instead of a fourth request type"
    - "Cypher UNION ALL (not independent OPTIONAL MATCH branches off one node) to avoid a cross-join when fetching three sibling child collections"
    - "Extending an existing regex's .pattern text (cg_recognition.GRAMMAR_CITATION_NAME_RE) rather than redefining it, for a stricter downstream extractor"
    - "Truncation applied to the actual nested response structure that feeds the prompt, not only to the reported entityNames vocabulary"

key-files:
  created:
    - data-service/tests/test_computgraph_consult.py
  modified:
    - data-service/dg_context.py
    - data-service/app.py
    - .planning/phases/37-script-structure-validation/37-VALIDATION.md

key-decisions:
  - "fetch_computgraph_subgraph() is a standalone function, not a fourth CONTEXT_REQUEST_TYPES value -- assemble_context()'s project-wide static concept bundling is irrelevant to a single-definition structural question"
  - "The children query (Pattern/Parameter/Interface per Procedure) is one Cypher literal built from three UNION ALL branches with one trailing ORDER BY, not three independent OPTIONAL MATCHes off the same Procedure node -- the latter would cross-join the three child collections"
  - "_CONSULT_MENTION_RE extends cg_recognition.GRAMMAR_CITATION_NAME_RE.pattern with a trailing \\w+ instead of redefining the convention-prefix vocabulary, so the two extractors can never drift apart"
  - "consult_computgraph() always calls resolve_active_provider() to obtain provider/model for the GenerateRequest, even when an adapter is injected for tests -- only get_adapter() is skipped on injection, keeping the resolved model/provider meaningful in test assertions"
  - "Truncation (CONSULT_MAX_ENTITIES) is applied to the actual nested algorithms/object structure that build_consult_prompt() renders, not only to entityNames -- otherwise the cap would not actually bound prompt size"
  - "Integration tests publish under their own project string (p37-structure-consult), not by importing test_cg_structure_checks.py's published_frame fixture -- this codebase's tests/ package layout (both __init__.py and per-file sys.path.insert) makes true cross-module fixture object identity unreliable, so importing the fixture risks a second independent publish/teardown instance racing the original"

requirements-completed: [SVAL-03]

coverage:
  - id: D1
    description: "fetch_computgraph_subgraph() reads the published Object/Behavior/Algorithm/Procedure/Pattern/Parameter/Interface spine for one project+definitionId, deterministically, with convention tokens and truncation signalling"
    requirement: "SVAL-03"
    verification:
      - kind: unit
        ref: "data-service/dg_context.py signature/query-tag one-liner (Task 1 <verify>)"
        status: pass
      - kind: integration
        ref: "data-service/tests/test_computgraph_consult.py::TestConsultIntegration::test_consult_subgraph_entity_count_matches_publish_counts_and_not_truncated"
        status: pass
    human_judgment: false
  - id: D2
    description: "build_consult_prompt()/check_consult_grounding() produce a deterministic, injection-contained prompt and a flag-don't-block grounding verdict"
    requirement: "SVAL-03"
    verification:
      - kind: unit
        ref: "data-service/tests/test_computgraph_consult.py::test_prompt_builder_deterministic_same_input_same_output"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_consult.py::test_prompt_injection_question_stays_inside_untrusted_block_only"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_consult.py::test_grounding_default_cassette_answer_cites_total_height_and_flags_ghost_token"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /computgraph/consult route -- 200/422/502 shape, single provider resolution per request"
    requirement: "SVAL-03"
    verification:
      - kind: unit
        ref: "data-service/tests/test_computgraph_consult.py::test_route_well_formed_request_returns_200_with_documented_keys"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_consult.py::test_route_pipeline_exception_returns_502_with_documented_code"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_consult.py::test_pipeline_resolves_provider_once_per_call"
        status: pass
    human_judgment: false
  - id: D4
    description: "SC3: consulting the full Frame definition cites the total-height convention token end to end through the real route and live Neo4j"
    requirement: "SVAL-03"
    verification:
      - kind: integration
        ref: "data-service/tests/test_computgraph_consult.py::TestConsultIntegration::test_consult_full_frame_route_returns_200_with_grounded_total_height_citation"
        status: pass
    human_judgment: false
  - id: D5
    description: "37-VALIDATION.md signed off: Per-Task Verification Map populated, nyquist_compliant: true, SC1's live-Rhino half explicitly deferred to /gsd-verify-work 37"
    verification: []
    human_judgment: true
    rationale: "SC1 is an explicitly deferred live-Rhino-canvas human-verify checkpoint (Phase 33/34-02/34-03 precedent) -- the sign-off document itself is not machine-checkable beyond the automated grep/frontmatter assertions already run"

duration: 55min
completed: 2026-07-27
status: complete
---

# Phase 37 Plan 06: Consult Endpoint Summary

**Added `POST /computgraph/consult` -- a read-only, grounded natural-language consult over one published Computgraph subgraph, resolving the LLM gateway provider exactly once in-process and citing entity mentions against a live-fetched, deterministic subgraph.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-07-27
- **Completed:** 2026-07-27
- **Tasks:** 3
- **Files modified:** 4 (2 created)

## Accomplishments
- `fetch_computgraph_subgraph()` -- the first function in this codebase that reads the Computgraph back (Phase 36 only ever wrote it) -- a dual-mode-session, deterministically-ordered, project+definitionId-scoped read of the Object/Behavior/Algorithm/Procedure/Pattern/Parameter/Interface spine, with a `CONSULT_MAX_ENTITIES` cap that bounds what actually reaches the prompt (not only the reported vocabulary) and a `truncated` signal instead of silent dropping
- `build_consult_prompt()`/`check_consult_grounding()`/`consult_computgraph()` -- the full SVAL-03 pipeline: deterministic prompt assembly with the question rendered inside a delimited untrusted block, a pure grounding post-check that extends `cg_recognition`'s existing citation regex rather than redefining it, and a pipeline that resolves the provider once through the exact `generate_validated_cypher()` in-process sequence, accepting an injected adapter for tests
- `POST /computgraph/consult` route in `app.py`, following the validate route's thin-route + structured-error precedent (`COMPUTGRAPH_CONSULT_REQUEST_INVALID` 422, `COMPUTGRAPH_CONSULT_FAILED` 502)
- 17-test cassette-driven suite (`test_computgraph_consult.py`): prompt determinism, injection containment, grounding in both directions, single provider resolution, the 11-key documented response contract, route shape/error mapping, and an integration tier proving SC3's exact citation through the real HTTP route with only the adapter faked (no paid call), cross-project isolation asserted by entity name (not just count), definition isolation, and an independent entity-count cross-check
- `37-VALIDATION.md` signed off: Per-Task Verification Map populated with real plan-task ids, `nyquist_compliant: true`, `status: approved`, SC1's live-Rhino half explicitly named as deferred to `/gsd-verify-work 37`

## Task Commits

Each task was committed atomically:

1. **Task 1: fetch_computgraph_subgraph - the first live read of the Computgraph** - `6bf9649` (feat)
2. **Task 2: Prompt assembly, grounding post-check, and the consult route** - `43b5222` (feat)
3. **Task 3: Cassette-driven consult tests and the phase gate** - `e79b8d4` (test)

**Plan metadata:** _pending final docs commit_

## Files Created/Modified
- `data-service/dg_context.py` - `CONSULT_MAX_ENTITIES`, `_COMPUTGRAPH_SUBGRAPH_QUERY`, `_COMPUTGRAPH_SUBGRAPH_CHILDREN_QUERY`, `fetch_computgraph_subgraph()`, `CONSULT_SYSTEM_GUIDANCE`, `build_consult_prompt()`, `_CONSULT_MENTION_RE`, `check_consult_grounding()`, `consult_computgraph()`
- `data-service/app.py` - `ComputgraphConsultRequest`, `post_computgraph_consult()` serving `POST /computgraph/consult`
- `data-service/tests/test_computgraph_consult.py` - new two-tier cassette-driven test suite (17 tests)
- `.planning/phases/37-script-structure-validation/37-VALIDATION.md` - Per-Task Verification Map, Manual-Only Verifications resume point, Validation Sign-Off, frontmatter (`nyquist_compliant: true`, `status: approved`)

## Decisions Made
- `fetch_computgraph_subgraph()` stays outside `CONTEXT_REQUEST_TYPES` (still exactly 3 members) -- a dedicated function mirrors `fetch_existing_entities()`'s dual-mode session pattern instead of overloading the general context assembler
- The children query unions three branches (Pattern/Parameter/Interface) rather than three `OPTIONAL MATCH`es off the same `Procedure` node, avoiding a cross-join that would inflate row counts
- `_CONSULT_MENTION_RE` extends the imported `cg_recognition.GRAMMAR_CITATION_NAME_RE.pattern` with a trailing `\w+` rather than redefining the convention-prefix vocabulary in a second place
- `consult_computgraph()` always resolves the provider (for the `GenerateRequest`'s `model`/`provider` fields) even with an injected adapter -- only `get_adapter()` itself is skipped, so a test's assertions about the requested model/provider stay meaningful
- Truncation bounds the actual `algorithms`/`object` structure that feeds the prompt, not only `entityNames`, so `CONSULT_MAX_ENTITIES` genuinely caps prompt size (T-37-04)
- Integration tests publish under their own project string (`p37-structure-consult`) instead of importing `test_cg_structure_checks.py`'s `published_frame` fixture -- this repo's `tests/` package layout (an `__init__.py` present alongside every file's own `sys.path.insert(0, dirname(__file__))`) makes a bare cross-module `from test_cg_structure_checks import published_frame` resolve to a second, independently-executed module instance rather than the one pytest's own collector uses, which would race two independent publish/teardown cycles against the identical `FIXTURE_PROJECT` string -- the codebase's own isolation rule ("no other suite uses this project string") is honored by choosing a fresh string instead

## Deviations from Plan

None - plan executed exactly as written. All three tasks' `<verify>`/`<acceptance_criteria>` blocks pass as specified.

## Issues Encountered
- The Task 3 cross-project-isolation test initially asserted `"HTotal" not in prompt` against the *whole* prompt, which false-failed because `CONSULT_SYSTEM_GUIDANCE`'s own instruction text uses `11_Var_HTotal` as a generic format example ("prefer the convention token... e.g. 11_Var_HTotal"). Fixed by asserting only against the structural rendering section (after the guidance block, before the question delimiter) -- the guidance's illustrative example is not a fixture-data leak.
- Two host-tier tests initially asserted `citedEntities == ["11_Var_HTotal"]` against the cassette's `DEFAULT_CONSULT_ANSWER`, which also names the procedure by its exact display name ("2D Truss Configuration procedure") -- a second, legitimate literal-entity-name citation. Fixed the assertions to `"11_Var_HTotal" in citedEntities` (the SC3-relevant assertion) rather than requiring exact-list equality.
- A route-shape test's `_canned_consult_response()` helper was initially invoked *inside* the very lambda that monkeypatched `dg_context.consult_computgraph`, causing infinite recursion (observed as a 502 from `RecursionError`). Fixed by computing the canned response before applying the monkeypatch.
- The suite's own module docstring originally said "not gated behind `pytest.mark.live`" as prose, which the phase gate's `grep -v '^\s*#' ... grep -c 'pytest.mark.live'` literal-substring check (correctly) flagged as non-zero. Reworded to "the paid-call test marker" to keep the same meaning without the literal marker string appearing anywhere in the file.

None of the above are deviations from the plan's *scope* -- all are test-authoring fixes discovered and corrected during Task 3's own verification loop, before any commit.

## User Setup Required
None - no external service configuration required. The route calls the already-configured LLM gateway (`/llm/settings`); no new environment variables or dashboard steps.

## Next Phase Readiness
- `POST /computgraph/consult` is live and documented (`spec/API.md`), confirmed present in the running container's route table
- This is the seed the v10 Script Intelligence milestone builds on -- deliberately small (read-only, no Cypher generated or executed)
- SC1's live-Rhino half (deleting an Interface tag on canvas, re-publishing, confirming `/computgraph/validate` flags it) remains deferred to `/gsd-verify-work 37`, per the phase's Manual-Only Verifications table -- this is the one remaining human-verify item for the whole phase
- `spec/RULE-PARTITION-POLICY.md`'s Computgraph third-system row (added by an earlier plan in this phase) already documents where this consult path sits relative to SWRL/SHACL

---
*Phase: 37-script-structure-validation*
*Completed: 2026-07-27*

## Self-Check: PASSED

All created/modified files verified present on disk; all three task commit hashes (`6bf9649`, `43b5222`, `e79b8d4`) verified present in git log.
