---
phase: 35-llm-recognition-canvas-preview
plan: 01
subsystem: api
tags: [llm, recognition, fastapi, pydantic, computgraph, cg_recognition]

# Dependency graph
requires:
  - phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
    provides: generate_validated_cypher()/validate_cypher() bounded-retry structural template, llm_gateway provider-agnostic call pattern
  - phase: 33-bridge-wire-protocol-canvas-listener-scaffold
    provides: gh_bridge.py TCP client + preview_structure/clear_preview/get_preview_status stub scaffolding
provides:
  - "data-service/cg_recognition.py: recognize_structure()/validate_proposed_structure()/_extract_json() recognition backend"
  - "POST /computgraph/recognize FastAPI route"
  - "data-service/fixtures/frame_recognition_fewshot.json Frame worked-example fixture"
  - "Bridge client docstrings + tests describing real forwarding (retiring the Phase-35-stub wording ahead of the C# handler implementation)"
affects: [35-02-canvas-preview-rendering, 35-03-structure-confirm-component, 36-computgraph-publish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Recognition pipeline mirrors dg_context.generate_validated_cypher()'s bounded-retry structure verbatim (same shape, different validator/prompt-assembler)"
    - "Hand-rolled JSON-from-LLM-text extraction (_extract_json) rather than a jsonschema dependency, for consistency with validate_cypher's existing hand-rolled idiom"

key-files:
  created:
    - data-service/cg_recognition.py
    - data-service/tests/test_cg_recognition.py
    - data-service/fixtures/frame_recognition_fewshot.json
  modified:
    - data-service/app.py
    - data-service/gh_bridge.py
    - data-service/tests/test_gh_bridge.py

key-decisions:
  - "validate_proposed_structure returns validate_cypher()'s exact {valid, violations:[{code,message,path}]} shape so append_recognition_feedback/the retry loop work unchanged"
  - "procedure_index scoping of untagged nodes uses one-hop wire adjacency to the procedure's tagged member ids -- the only per-procedure signal cgContextJson v1's untagged block carries, since untagged nodes have no procedure ownership field of their own"
  - "Frame few-shot fixture kept to one trimmed worked example (2 Interface proposals); measured assembled prompt size ~9.5KB for the test fixture context, locked under a 20KB test budget (A4 resolution) rather than falling back to a single procedure"
  - "RecognizeRequest.cg_context is a posted dict (caller pulls via /computgraph/context/pull first, then posts here) -- keeps the route synchronous/testable, no live bridge call inside recognize_structure itself"

patterns-established:
  - "cg_recognition.py is a sibling module to dg_context.py, not a new idiom -- same bounded-retry/validator/corrective-feedback structure, reused for a JSON contract instead of a Cypher contract"

requirements-completed: [RCGN-01, RCGN-04]

coverage:
  - id: D1
    description: "POST /computgraph/recognize classifies untagged Computgraph entities into a schema-valid {proposals[], unrecognized[]} payload via the LLM gateway, with a bounded (max_retries=2, 3 attempts total) corrective-feedback retry mirroring generate_validated_cypher()"
    requirement: "RCGN-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestRetryLoop#test_first_attempt_valid_returns_attempts_1_no_retry"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestRetryLoop#test_malformed_json_then_valid_retries_and_succeeds_at_attempt_2"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestRetryLoop#test_all_three_attempts_fail_returns_final_violations_bounded_at_3"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestRetryLoop#test_retry_loop_never_calls_llm_generate_http_endpoint"
        status: pass
    human_judgment: false
  - id: D2
    description: "validate_proposed_structure hard-rejects any proposal whose memberIds are absent from the submitted context (unknown_member_id) or overlap a tagged ground-truth entity (tagged_overlap), plus DoS-bound too_many_proposals/too_many_members"
    requirement: "RCGN-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestValidator#test_unknown_member_id_is_caught"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestValidator#test_tagged_overlap_is_caught"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestValidator#test_too_many_proposals_is_caught"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestValidator#test_too_many_members_per_proposal_is_caught"
        status: pass
    human_judgment: false
  - id: D3
    description: "_extract_json parses bare/fenced/prose-wrapped LLM JSON into a proposal object; malformed or non-object output becomes a bad_json violation fed into the same bounded retry, never an unhandled exception"
    requirement: "RCGN-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestExtractJson"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cg_recognition.py::TestRetryLoop#test_malformed_json_then_valid_retries_and_succeeds_at_attempt_2"
        status: pass
    human_judgment: false
  - id: D4
    description: "cg_recognition.py contains no Neo4j write path -- recognition never persists; unrecognized blocks are reported with member ids, never invented or silently dropped"
    requirement: "RCGN-04"
    verification:
      - kind: other
        ref: "grep -vE '^\\s*#' data-service/cg_recognition.py | grep -cE 'session\\.run|driver\\.session|tx\\.run' -> 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "gh_bridge.py preview_structure/clear_preview/get_preview_status docstrings describe real listener forwarding (retiring the Phase-35 stub wording); test_gh_bridge.py's two stub-shape tests rewritten to assert a forwarded payload, not {supported: False}"
    verification:
      - kind: unit
        ref: "data-service/tests/test_gh_bridge.py::TestCallSuccess#test_preview_structure_forwards_listener_result"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_gh_bridge.py::TestCallSuccess#test_clear_preview_forwards_listener_result"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-19
status: complete
---

# Phase 35 Plan 01: Recognition Backend Summary

**LLM-driven Computgraph structure recognition (`cg_recognition.py`) mirroring `dg_context.generate_validated_cypher()`'s bounded-retry structure, exposed as `POST /computgraph/recognize`, with hard-reject validation against hallucinated/tagged-overlap member ids and zero Neo4j write path.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-19T09:10:00Z (approx.)
- **Completed:** 2026-07-19T09:22:57Z
- **Tasks:** 3 (2 TDD, 1 auto)
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments

- `validate_proposed_structure()` + `_extract_json()` — the validation/JSON-extraction core, returning `validate_cypher()`'s exact `{valid, violations}` shape and never raising on malformed LLM output
- `recognize_structure()` — the bounded-retry recognition pipeline (mirrors `generate_validated_cypher()` verbatim: resolves provider/adapter once, calls `adapter.generate()` in-process each attempt, never re-POSTs to `/llm/generate`)
- `_build_recognition_prompt()` — deterministic prompt assembly (concept catalog + annotation-convention grammar + Frame few-shot + tagged anchors + procedure-scoped untagged nodes/wires/group hints + JSON-only output instruction)
- `POST /computgraph/recognize` — thin FastAPI route delegating to `cg_recognition.recognize_structure()`, same try/except ValueError + `map_provider_error` shape as `post_context_generate_cypher`
- Bridge client (`gh_bridge.py`) docstrings and the two preview stub tests updated to describe/assert real listener forwarding, ahead of the C# handler implementation in a later Phase 35 plan

## Task Commits

Each task was committed atomically (TDD RED/GREEN pairs for Tasks 1-2, single commit for Task 3):

1. **Task 1 RED: failing tests for validator + JSON extraction** - `fa9fb74` (test)
2. **Task 1 GREEN: validate_proposed_structure + _extract_json** - `f6c9bf7` (feat)
3. **Task 2 RED: failing tests for retry loop + prompt assembly** - `02f951d` (test)
4. **Task 2 GREEN: recognize_structure + prompt builder + Frame few-shot** - `5eb3db7` (feat)
5. **Task 3: POST /computgraph/recognize route + bridge docstrings/tests** - `e8cb8f9` (feat)

**Plan metadata:** (this commit) `docs: complete recognition-backend plan`

## Files Created/Modified

- `data-service/cg_recognition.py` - Recognition backend: `recognize_structure`, `validate_proposed_structure`, `_extract_json`, `_build_recognition_prompt`, `append_recognition_feedback`, `_collect_known_member_ids`/`_collect_tagged_member_ids`, `_load_frame_fewshot`; constants `MAX_PROPOSALS=200`/`MAX_MEMBERS_PER_PROPOSAL=1000`
- `data-service/tests/test_cg_recognition.py` - `TestValidator`, `TestExtractJson`, `TestRetryLoop`, `TestPrompt` (24 tests)
- `data-service/fixtures/frame_recognition_fewshot.json` - One trimmed Frame input->expected-proposals few-shot example
- `data-service/app.py` - `RecognizeRequest` model + `post_computgraph_recognize` route; `import cg_recognition` at module scope
- `data-service/gh_bridge.py` - Docstrings on `preview_structure`/`clear_preview`/`get_preview_status` updated to describe real forwarding (bodies unchanged -- `_call()` untouched)
- `data-service/tests/test_gh_bridge.py` - Two stub-shape tests renamed/rewritten to `test_preview_structure_forwards_listener_result`/`test_clear_preview_forwards_listener_result`

## Decisions Made

- `validate_proposed_structure` reuses `validate_cypher()`'s exact violation-list shape (`{valid, violations:[{code,message,path}]}`) so `append_recognition_feedback` and the retry loop needed zero new plumbing beyond a renamed feedback-appender
- `procedure_index`-scoped filtering of untagged nodes uses one-hop wire adjacency to the target procedure's tagged member ids, since cgContextJson v1's `untagged` block carries no procedure-ownership field of its own for untagged entities
- Frame few-shot kept to one trimmed worked example (measured prompt ~9.5KB for the test fixture context; locked under a 20KB test budget) rather than needing to fall back to a smaller single-procedure excerpt
- `RecognizeRequest.cg_context` is a posted dict rather than the route pulling live canvas data itself -- callers call `/computgraph/context/pull` first, keeping `/computgraph/recognize` synchronous and independently testable

## Deviations from Plan

None - plan executed exactly as written. All three tasks' `<action>` and `<behavior>` specifications were implemented as specified; all `<acceptance_criteria>` passed on first verification per task (no fix-attempt cycles needed).

## Issues Encountered

- `data-service` container was not running at the start of the session (only Neo4j/Speckle/n8n/Ollama/dg-reasoner were up) — started it via `docker compose up -d data-service`. The container has no live source-code volume mount (`docker-compose.yml` only mounts `./data-service/data:/app/data` and `.:/mnt/repo:ro`, not the `data-service` source tree itself), so each task's implementation required `docker compose build data-service && docker compose up -d data-service` before `pytest` picked up the new code — consistent with this project's documented environment note, not a deviation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The recognition backend (`cg_recognition.py`, `/computgraph/recognize`) is complete, tested (244/244 full data-service suite green), and ready for the canvas-preview-rendering plan (Phase 35's C# side) to call it via the existing `gh_bridge`/data-service HTTP boundary
- `gh_bridge.py`'s `preview_structure`/`clear_preview`/`get_preview_status` docstrings and tests now describe real forwarding, but the underlying `_call()` still talks to whatever the DG CANVAS LISTENER dispatcher returns -- the C# side's stub-to-real-handler swap (Phase 35's remaining plans) is what actually changes the runtime behavior; this plan only updated the Python-side description/test-shape ahead of that
- No blockers for the next plan in this phase

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-19*

## Self-Check: PASSED

All created files verified present on disk (`cg_recognition.py`, `test_cg_recognition.py`, `frame_recognition_fewshot.json`, this SUMMARY). All 5 task commits (`fa9fb74`, `f6c9bf7`, `02f951d`, `5eb3db7`, `e8cb8f9`) verified present in `git log`. Full data-service suite re-confirmed green (244/244) and the RCGN-04 Neo4j-write source assertion re-confirmed at 0 immediately before this SUMMARY was written.
