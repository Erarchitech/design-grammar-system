---
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
plan: 04
subsystem: api
tags: [fastapi, data-service, cypher-validation, security, retry-loop]

# Dependency graph
requires:
  - phase: 29-03
    provides: "assemble_context() + /context/assemble + /context/debug (dg_context.py surface, CONTEXT_REQUEST_TYPES) this plan's validator and retry loop build on top of"
provides:
  - "data-service/dg_context.py — validate_cypher() schema + request-type-aware verb-policy validator (CTXA-04, PRIMARY security control)"
  - "data-service/dg_context.py — generate_validated_cypher() bounded (2-retry/3-attempt) in-process retry orchestrator (D-06/D-07)"
  - "data-service/app.py — POST /context/generate-cypher, the single n8n-facing prompt-in -> validated-cypher-out call"
  - "data-service/tests/test_dg_context.py — TestValidator (14 tests) + TestRetryLoop (5 tests) + TestGenerateCypherEndpoint (3 tests)"
affects: [29-05, 31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "validate_cypher() never raises on malformed Cypher -- every schema/verb problem becomes a {code, message, path?} violation dict; ValueError is reserved for an unrecognized request_type only"
    - "Label extraction walks every :Label in a multi-label chain (n:LabelA:LabelB) via a nested regex pass, correcting an edge case the original n8n JS regex (single greedy capture) did not fully handle"
    - "generate_validated_cypher() validates request_type upfront (before touching the adapter) so an unknown type fails fast without a live LLM call, then calls resolve_active_provider -> get_adapter -> adapter.generate directly in-process per retry attempt -- never re-POSTs to /llm/generate"
    - "Retry-loop tests monkeypatch dg_context.get_adapter (not llm_gateway.get_adapter) since dg_context imports the name directly -- mirrors TestReasonerConsistencyProxy's monkeypatch.setattr technique, retargeted from httpx.post to the adapter object"

key-files:
  created: []
  modified:
    - data-service/dg_context.py
    - data-service/app.py
    - data-service/tests/test_dg_context.py

key-decisions:
  - "GenerateCypherRequest.type kept as plain str (not Pydantic Literal), matching ContextAssembleRequest's 29-03 precedent -- generate_validated_cypher() raises ValueError for an unknown type and app.py maps it to the same CONTEXT_TYPE_INVALID 422 shape, rather than following the plan text's literal 'Literal[...]' phrasing"
  - "Label allow-list extraction was implemented as a corrected multi-label walker (nested regex over every :Label segment) rather than a literal line-for-line port of the n8n labelRegex, because the original JS regex's greedy [^\\)]* prefix only ever captures the LAST label in a multi-label chain (n:LabelA:LabelB) -- the plan explicitly asked for multi-label handling, so this is a Rule 1 fix over the buggy precedent, not a deviation from intent"
  - "ALLOWED_RELATIONSHIPS includes VALIDATES (Run->DesignState, documented in cypher_template.txt) alongside the four Metagraph relationship types and HAS_STATE, so the validator doesn't false-positive on ValidGraph-side Cypher even though LLM ingest never emits it"
  - "generate_validated_cypher() validates request_type before resolving any adapter/provider (fail-fast) -- this is slightly ahead of the plan's literal call sequence but avoids requiring a live LLM adapter just to prove the CONTEXT_TYPE_INVALID error path in tests"

patterns-established:
  - "Cypher validator violation vocabulary: unbalanced_brackets, unknown_label, unknown_relationship, bad_kind_enum, bad_key_name, missing_project_key, disallowed_verb -- each violation is {code, message, path?} in What+Where+How-to-fix tone, mirroring the C#-side ErrorMessageTemplates discipline"

requirements-completed: [CTXA-04]

coverage:
  - id: D1
    description: "validate_cypher(clean_ingest_cypher, 'rule_ingest') returns {valid: True, violations: []} against a real, fully-instantiated catalog worked_example (max_limit)"
    requirement: "CTXA-04"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestValidator::test_clean_ingest_cypher_from_real_catalog_validates_true"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every violation code (unbalanced_brackets, unknown_label, unknown_relationship, bad_kind_enum, bad_key_name x3, missing_project_key) is independently triggered and asserted"
    requirement: "CTXA-04"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestValidator (14 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "T-29-02 verb policy: rule_ingest/rule_edit reject DETACH/DELETE (disallowed_verb); graph_query rejects any write verb (MERGE/SET/DELETE), reusing is_write_query() precedent; a genuinely read-only graph_query Cypher produces zero disallowed_verb violations"
    requirement: "CTXA-04"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestValidator (ingest/edit/graph_query verb-policy tests, 4 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "generate_validated_cypher() bounded retry loop: first-attempt success (attempts=1), 2-failures-then-success (attempts=3, corrective feedback verified in the 3rd prompt), all-3-fail (bounded at 3, violations surfaced), never re-POSTs to /llm/generate, fails fast on an unknown request_type without touching the adapter"
    requirement: "CTXA-04"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestRetryLoop (5 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "POST /context/generate-cypher is the single n8n-facing call: returns validated Cypher for a mocked-valid adapter, a 502 structured error on adapter failure, and a 422 CONTEXT_TYPE_INVALID on an unknown type; no separate /context/validate route exists"
    requirement: "CTXA-04"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestGenerateCypherEndpoint (3 tests)"
        status: pass
      - kind: integration
        ref: "docker compose exec -T data-service pytest tests/test_dg_context.py -x -q (40/40 passed); docker compose exec -T data-service pytest -q (167 passed, 1 pre-existing unrelated failure)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Manual verification (Success Criterion 2): a deliberately corrupted Cypher (unknown label + bad verbs) returns a structured violation list before any Neo4j execution"
    verification:
      - kind: manual
        ref: "docker compose exec data-service python -c 'validate_cypher(...)' -- returned unknown_label + 2x disallowed_verb violations, valid=false"
        status: pass
    human_judgment: true
    rationale: "Direct manual exercise of the validator against a corrupted statement, per the plan's <verification> section -- not itself a pytest assertion, run as a sanity check alongside the automated suite."

duration: ~50min
completed: 2026-07-12
status: complete
---

# Phase 29 Plan 04: Cypher Validator + Bounded Retry Loop + /context/generate-cypher Summary

**`validate_cypher()` is the phase's PRIMARY security control -- a request-type-aware schema + write-verb-policy gate (T-29-01/T-29-02 mitigation) that no LLM-generated Cypher bypasses before Neo4j `tx/commit`; `generate_validated_cypher()` wraps it in a bounded (2-retry/3-attempt) in-process adapter retry loop behind the single n8n-facing `POST /context/generate-cypher`**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-07-12
- **Tasks:** 2 (both auto, both complete)
- **Files modified:** 3 (data-service/dg_context.py, data-service/app.py, data-service/tests/test_dg_context.py)

## Accomplishments

- `data-service/dg_context.py`: `ALLOWED_LABELS` (12 labels including ValidGraph's IntegrationConfig/ValidationEntity), `ALLOWED_RELATIONSHIPS` (HAS_BODY/HAS_HEAD/REFERS_TO/ARG/HAS_STATE/VALIDATES), `DESIGNSTATE_KINDS`, `WRITE_VERBS` = {MERGE, SET}, `DISALLOWED_VERBS` = {DELETE, REMOVE, DETACH, DROP, CREATE} -- all sourced from `cypher_template.txt`'s GRAPH SCHEMA + OUTPUT RULES sections
- `data-service/dg_context.py`: `has_valid_nesting()` ported near-verbatim from n8n's `hasValidNesting()` (rules-to-metagraph.json "Parse LLM Output"). Label/relationship extraction ports `graph-query-mcp.json`'s "Parse Cypher" `labelRegex`/`relRegex`, with the label walker corrected to handle EVERY `:Label` in a multi-label chain (`n:LabelA:LabelB`) via a nested regex pass -- the original JS regex's greedy prefix only ever captured the last label in such a chain
- `data-service/dg_context.py`: `validate_cypher(cypher, request_type) -> dict` returns `{valid, violations: [{code, message, path?}]}`. Checks: `unbalanced_brackets`, `unknown_label`, `unknown_relationship`, `bad_kind_enum` (DesignState.kind outside {ObjState, ParamState, PropState}), `bad_key_name` (Rule keyed on `id` not `Rule_Id`; Atom keyed on non-`Atom_Id`; DatatypeProperty setting `.label` instead of `.SWRL_label`), `missing_project_key` (Var MERGE without `project`), and request-type-aware `disallowed_verb` -- rule_ingest/rule_edit permit only MERGE/SET; graph_query rejects ANY write verb by reusing app.py's `is_write_query()` precedent (duplicated regex, not imported, to avoid a circular import since app.py imports dg_context)
- `data-service/dg_context.py`: `append_corrective_feedback(prompt, violations)` appends structured violations to the original prompt in What+Where+How-to-fix tone. `generate_validated_cypher(prompt, request_type, max_retries=2)` fails fast with `ValueError` on an unknown `request_type` (before touching any adapter), then calls `resolve_active_provider -> get_adapter -> adapter.generate` directly in-process per attempt (mirrors `llm_generate()`'s exact sequence, `app.py:996-1027`) -- never re-POSTs to `/llm/generate`. Bounded at `max_retries=2` (3 attempts total per D-07); returns `{"valid": True, "cypher", "attempts"}` on success or `{"valid": False, "violations", "attempts": 3}` on exhaustion
- `data-service/dg_context.py`: `GenerateCypherRequest(BaseModel)` = `{prompt, type, project?, model?, provider?}` -- `type` kept as plain `str` (ValueError-dispatch convention from 29-03), not a Pydantic `Literal`
- `data-service/app.py`: `POST /context/generate-cypher` -- the single n8n-facing route wrapping `dg_context.generate_validated_cypher()`; `ValueError` -> `CONTEXT_TYPE_INVALID` 422 (reusing `_context_type_invalid_error` from 29-03); any adapter exception -> `map_provider_error()` -> 502 structured error (mirrors `llm_generate()`'s own error mapping)
- `data-service/tests/test_dg_context.py`: `TestValidator` (14 tests) covering every violation code plus a clean pass against a real, fully-instantiated catalog worked_example; `TestRetryLoop` (5 tests: first-attempt success, two-failures-then-success with corrective-feedback assertion on the exact retry prompt, all-three-attempts-fail bounded at 3, no HTTP re-entry to `/llm/generate`, fail-fast on an unrecognized type without resolving an adapter); `TestGenerateCypherEndpoint` (3 tests: success, adapter failure -> 502, unknown type -> 422)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement validate_cypher() with schema, bracket, and request-type-aware verb-policy checks** - `d4d7dc2` (feat)
2. **Task 2: Implement the bounded retry loop and POST /context/generate-cypher** - `09d36c1` (feat)

**Plan metadata:** `commit_docs` is `false` in `.planning/config.json` for this project (same as Plans 29-01/29-02/29-03) -- the final metadata commit (this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md) is expected to skip via the SDK's `skipped_commit_docs_false` path.

## Files Created/Modified

- `data-service/dg_context.py` - `ALLOWED_LABELS`, `ALLOWED_RELATIONSHIPS`, `DESIGNSTATE_KINDS`, `WRITE_VERBS`, `DISALLOWED_VERBS`, `has_valid_nesting()`, `validate_cypher()`, `append_corrective_feedback()`, `generate_validated_cypher()`, `GenerateCypherRequest`
- `data-service/app.py` - `POST /context/generate-cypher`
- `data-service/tests/test_dg_context.py` - `TestValidator` (14 tests), `TestRetryLoop` (5 tests), `TestGenerateCypherEndpoint` (3 tests)

## Decisions Made

- `GenerateCypherRequest.type` is a plain `str`, not a Pydantic `Literal` -- consistent with `ContextAssembleRequest`'s 29-03 precedent (ValueError-dispatch -> `CONTEXT_TYPE_INVALID`), even though the plan's task text literally said `Literal[...]`. This keeps the two request models symmetric and reuses the existing error-mapping path instead of introducing FastAPI's generic validation-error body for this endpoint only.
- Label allow-list extraction corrects a real bug in the n8n JS precedent it ports: the original `labelRegex`'s greedy `[^\)]*` prefix only ever captures the LAST label in a multi-label node (`n:LabelA:LabelB` yields only `LabelB`). Since the plan explicitly calls for multi-label handling, this was implemented as a nested-regex walk over every `:Label` segment in the chain rather than a literal line-for-line port of the buggy behavior (Rule 1 auto-fix: the port target's bug is not something to preserve).
- `ALLOWED_RELATIONSHIPS` includes `VALIDATES` (Run->DesignState) alongside the plan's explicitly-named four Metagraph types + `HAS_STATE`, since `cypher_template.txt` documents it as part of the schema (even though LLM ingest never emits it) -- avoids a false-positive `unknown_relationship` on any future ValidGraph-side Cypher the validator might see.
- `generate_validated_cypher()` validates `request_type` against `CONTEXT_REQUEST_TYPES` before resolving any provider/adapter, failing fast with `ValueError`. This is a minor sequencing improvement over the plan's literal call order (which implied the check happens inside the loop via `validate_cypher()`) -- it means an unknown type never requires a live/mocked LLM call to surface the error, which also made `TestRetryLoop::test_unknown_request_type_raises_value_error_without_touching_adapter` possible without any adapter mock at all.

## Deviations from Plan

None requiring a checkpoint -- both tasks executed within the auto-fix rules. Two implementation-detail decisions (documented above under Decisions Made / key-decisions) diverge from the plan's literal phrasing but stay within CONTEXT.md's Claude's Discretion scope ("Exact violation code vocabulary... derive from the validator's actual checks" and the general precedent of 29-03's `type: str` convention) and RESEARCH.md's Rule 1 (auto-fix bugs discovered in the port target).

## Issues Encountered

- **Docker image staleness (not a code bug):** `data-service`'s container filesystem (`/app`) is baked into the image at build time (`COPY . .` in the Dockerfile) -- it is NOT a live bind mount of `data-service/`. Only `data-service/data` (runtime data) and the whole repo root at `/mnt/repo` (read-only) are bind-mounted. Editing `dg_context.py`/`app.py` on the host had zero effect on `docker compose exec data-service pytest` until `docker compose build data-service && docker compose up -d data-service` was run. This is the same pattern CLAUDE.md documents for the `design-grammars` UI container ("Docker layer caching can serve stale index.html -- always use --no-cache") but was not previously documented for `data-service`; worth a CLAUDE.md/Known-Gotchas addition in a future docs pass, not done here as out-of-scope for this plan.
- One pre-existing, unrelated test failure (`tests/test_error_responses.py::test_publish_validation_missing_config`) reappeared in the full-suite run (167 passed / 1 failed) -- already logged in Plan 29-01's `deferred-items.md` (Speckle `/validation/publish` config handling; not a file this plan touches). Not re-logged as a new deviation.

## User Setup Required

None -- no external service configuration required. Zero new third-party packages (confirmed by RESEARCH.md's Package Legitimacy Audit: N/A for this phase).

## Next Phase Readiness

- `validate_cypher()` + `generate_validated_cypher()` + `POST /context/generate-cypher` are live and pytest-covered, ready for Plan 29-05's n8n prompt-node thinning to call instead of the inline "Parse LLM Output"/"Parse Cypher" JS validation those nodes currently do
- Both High-severity threats from the plan's threat model (T-29-01, T-29-02) are mitigated with passing tests -- satisfies ASVS L1 block-on-High per the plan's `<verification>` section
- No blockers

---
*Phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: data-service/dg_context.py
- FOUND: data-service/app.py
- FOUND: data-service/tests/test_dg_context.py
- FOUND: d4d7dc2 (Task 1 commit)
- FOUND: 09d36c1 (Task 2 commit)
- CONFIRMED: tests/test_dg_context.py 40/40 passed
- CONFIRMED: full data-service suite 167 passed / 1 pre-existing unrelated failure (no regression)
