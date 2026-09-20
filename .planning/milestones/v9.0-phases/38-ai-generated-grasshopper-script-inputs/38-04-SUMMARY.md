---
phase: 38-ai-generated-grasshopper-script-inputs
plan: 04
subsystem: api
tags: [computgraph, llm-gateway, generation, pydantic, ast-eval, data-service]

# Dependency graph
requires:
  - phase: 38-02
    provides: "Parameter.reinstateParameterId, resolvable from a published :Parameter node"
  - phase: 38-03
    provides: "cg_input_bindings.classify_rule/select_parameters, RuleLimit/RuleClassification, inputBindings artifact"
provides:
  - "cg_input_sampler.py: deterministic Tier 0 sampler (sample_tier0, sample_candidate_set) and the dynamic domain validator (validate_candidate) with no clamp helper anywhere in the module"
  - "cg_schemas.py: GeneratedParameterValue/GeneratedCandidate/GeneratedCandidateSet, a shape-only wire contract (D-17)"
  - "cg_input_generation.py: generate_inputs() two-tier orchestrator -- deterministic floor always ships, bounded-retry LLM refinement never trusted for satisfaction claims"
  - "POST /computgraph/generate-inputs route with all seven documented error codes mapped from real exception paths"
  - "prompts/input_generation_system.md versioned system prompt"
affects: [38-05, 38-06, 38-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Restricted ast.parse()-based arithmetic evaluator for a monotone-bound rule's metricExpression -- never Python eval(), degrades to undeterminable on any parse/evaluation failure rather than raising"
    - "Qualified module-attribute access (llm_gateway.resolve_active_provider) instead of a bare-name import, specifically to keep a single-call-site grep invariant literal and inspectable"
    - "candidate.parameters[].parameterId is the bound parameter's reinstateParameterId, never its parameterName -- the exact string ParameterReinstateComponent.cs matches on; displayName carries the human-readable parameterName"

key-files:
  created:
    - data-service/cg_input_sampler.py
    - data-service/cg_input_generation.py
    - data-service/prompts/input_generation_system.md
    - data-service/tests/test_cg_input_sampler.py
    - data-service/tests/test_cg_input_generation.py
    - data-service/tests/test_cg_input_boundary.py
  modified:
    - data-service/cg_schemas.py
    - data-service/app.py

key-decisions:
  - "Tier 0's sample_tier0(bound_params, limit, strategy) applies the rule limit's direction as a UNIFORM best-effort bias across every numeric bound parameter rather than evaluating metricExpression -- exact for a direct-parameter rule's single parameter, an honest heuristic (not a guarantee) for a monotone-bound rule's several. Tier 0's only hard guarantee is domain validity (validate_candidate returns []); whether a Tier-0 candidate satisfies the rule is computed authoritatively afterward, same as a Tier-1 candidate."
  - "ruleSatisfaction is computed via a hand-written ast-based restricted expression evaluator against a monotone-bound rule's metricExpression, never Python eval() and never asked of the model (GeneratedCandidate carries no confidence/satisfaction field at all) -- D-09/T-38-16 enforced structurally, not by prompt discipline."
  - "candidate.parameters[].parameterId is set to the bound row's reinstateParameterId, not parameterName -- exercised directly by test against the Frame fixture's deliberately divergent HTotal/Spans pair (plan 38-02's JOIN A fixture), since that field is what ParameterReinstateComponent.cs's ordinal string match actually reads."
  - "resolve_active_provider is called via the qualified `llm_gateway.resolve_active_provider(...)` (module import, not a bare-name import) specifically so the acceptance criterion 'this name appears exactly once in the file' is literally true and grep-verifiable, matching D-16's single-call-site requirement."
  - "The diversity gate (D-13) is a retry-triggering violation over the WHOLE candidate set (near-duplicate feedback fed back for regeneration), not a silent drop-some-candidates step -- 'the set is diverse enough' is treated as a pass/fail gate on the full response, consistent with the plan's no-partial-result guarantee."
  - "test_cg_input_sampler.py was authored during Task 1 (ahead of its nominal Task 5 file ownership) because Task 1's own <verify> command runs pytest against it -- Task 5 then added only the two remaining test files. Documented as a sequencing deviation, not a scope change."

requirements-completed: [GHIN-01, GHIN-02, GHIN-03, GHIN-04]

coverage:
  - id: D1
    description: "Deterministic Tier 0 sampler (sample_tier0/sample_candidate_set) that alone produces at least one valid candidate per call, and a per-request dynamic domain validator (validate_candidate) with no clamp/coerce/repair helper anywhere in the module"
    requirement: GHIN-03
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_input_sampler.py (29 tests: every strategy validates clean with/without a limit, determinism, all five violation codes producible, near-limit clamping both directions, degenerate-domain no-raise, diversity threshold, immutability)"
        status: pass
    human_judgment: false
  - id: D2
    description: "GeneratedParameterValue/GeneratedCandidate/GeneratedCandidateSet Pydantic v2 models pass through to_strict_json_schema() unchanged in shape, carry no numeric Field bound (D-17)"
    requirement: GHIN-03
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_schemas.py -q (25/25 pass, includes the new models); grep -c 'ge=|le=|gt=|lt=' unchanged from pre-edit baseline"
        status: pass
    human_judgment: false
  - id: D3
    description: "generate_inputs() two-tier orchestrator: Tier 0 floor always computed first and held; Tier 1 bounded retry (max 2 retries) validates every candidate's domain and set-wide diversity before acceptance; falls back to the Tier 0 floor (never empty, never raises) on exhaustion or truncation; ruleSatisfaction and provenance computed after the model returns"
    requirement: GHIN-03
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_input_generation.py (15 tests: Tier 1 success + JOIN A parameterId honored, out-of-domain retry, exhaustion falls back with llm_candidates_rejected flag, truncation falls back with output_truncated flag and no retry, diversity-violation retry, provider-resolved-once, provenance completeness, geometry-required always undeterminable, Float/Integer/Boolean type mapping with Text/Geometry excluded, statePayload DS_-prefixed id + ISO-8601 timestamp, monotone-bound metricExpression evaluation, all four error paths)"
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /computgraph/generate-inputs route exposes the orchestrator with all seven documented error codes mapped from real exception paths; performs zero writes"
    requirement: GHIN-03
    verification:
      - kind: other
        ref: "grep-based acceptance criteria on data-service/app.py: 1 route decorator, all 7 COMPUTGRAPH_GENERATE_INPUTS_* codes present; manual TestClient-free import smoke test confirming route registration; python -m pytest data-service/tests/test_error_responses.py -q (3/3 pass, no regression to the shipped structured-error contract)"
        status: pass
    human_judgment: false
  - id: D5
    description: "GHIN-04/D-22: the generation path (cg_input_generation, cg_input_sampler, cg_input_bindings) never imports gh_bridge or the not-yet-created cg_paramstate_store, and contains no write-Cypher token, asserted transitively via an ast-based import-closure walk"
    requirement: GHIN-04
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_input_boundary.py (4/4 pass): ast-based transitive closure excludes gh_bridge; cg_input_generation does not import cg_paramstate_store; none of the three modules' source contains MERGE/CREATE (/SET tokens"
        status: pass
    human_judgment: false

duration: ~2h
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 04: Generation Core -- Tier 0 Sampler, Tier 1 Orchestrator, and the generate-inputs Route Summary

**A deterministic Tier 0 sampler with a per-request dynamic domain validator, a Tier 1 LLM orchestrator that selects and explains within those bounds, and `POST /computgraph/generate-inputs` -- with a useless model degrading the result to the guaranteed floor rather than emptying it, and rule-satisfaction claims computed after the fact via a restricted ast-based evaluator rather than trusted from the model.**

## Performance

- **Duration:** ~2h
- **Tasks:** 5
- **Files modified:** 8 (6 created, 2 modified)

## Accomplishments

- `cg_input_sampler.py` (new, ~370 lines): pure Tier 0 -- `STRATEGIES`, `DEFAULT_CANDIDATE_COUNT=4`, `MAX_CANDIDATE_COUNT=8`, `NEAR_DUPLICATE_THRESHOLD=0.10`, `step_align` (tolerance-based step-index rounding), `validate_candidate` (the five violation codes: `unknown-parameter`, `missing-parameter`, `type-mismatch`, `out-of-domain`, `step-misaligned` -- with a docstring naming exactly why it never mutates a value), `sample_tier0` (per-strategy deterministic assignment, conservative/near-limit direction-aware via a duck-typed `.operator`/`.value` limit object), `sample_candidate_set` (cycles strategies, perturbs past the fourth candidate so a fifth is never a duplicate of the first), `normalized_distance`/`is_near_duplicate` (domain-scaled L1 distance, zero-safe on a degenerate domain).
- `cg_schemas.py` gained `GeneratedParameterValue`/`GeneratedCandidate`/`GeneratedCandidateSet` -- a shape-only wire contract per D-17, with a module comment naming `cg_input_sampler.validate_candidate` as the actual enforcement point and warning against adding a numeric `Field` bound that `to_strict_json_schema()` would silently strip.
- `cg_input_generation.py` (new, ~700 lines): `generate_inputs()` resolves the definition, classifies the rule (`RuleNotFoundError` propagates before any parameter read), reads and selects bound parameters (raising `NoEligibleParametersError` with the exclusion reasons when nothing is eligible), samples the Tier 0 floor and holds it, resolves the LLM provider/adapter exactly once via the qualified `llm_gateway.resolve_active_provider(...)`, then runs a bounded (2-retry) Tier 1 loop that validates every candidate's domain AND the full set's pairwise diversity before accepting it -- feeding structured violations back on any failure. On exhaustion or truncation it falls back to the Tier 0 floor with an explicit flag (`llm_candidates_rejected` / `output_truncated`) rather than failing. Every candidate, whichever tier produced it, is post-processed identically: `ruleSatisfaction` is computed from the candidate's actual values via a restricted `ast`-based arithmetic evaluator against a monotone-bound rule's `metricExpression` (never Python `eval()`, never asked of the model), forced `undeterminable` for `geometry-required` rules regardless of what was readable; `provenance` carries all ten documented keys; `statePayload` is a `DS_`-prefixed, ISO-8601-timestamped ParamState-compatible envelope.
- `prompts/input_generation_system.md` (new): versioned system prompt (mirrors `recognition_system.md`'s front-matter convention) instructing the model to select values within stated domains, produce exactly one candidate per requested strategy, use only the exact `parameterId` values supplied, and never claim rule satisfaction.
- `POST /computgraph/generate-inputs` added to `app.py`: a thin route opening one session and returning the delegate's result directly, mapping `DefinitionResolutionError`, `RuleNotFoundError`, `NoEligibleParametersError`, `InputBindingError`, a bare `ValueError` (out-of-range `candidateCount`), `DomainViolationExhaustedError`, and a bare `Exception` onto all seven documented error codes.
- Three new test modules (`test_cg_input_sampler.py` 29 tests, `test_cg_input_generation.py` 15 tests, `test_cg_input_boundary.py` 4 tests) -- 48 tests total, all passing, plus no regression in `test_cg_schemas.py`, `test_error_responses.py`, `test_cg_recognition.py`, `test_cg_input_bindings.py`, or `test_cg_topology.py` (181 combined tests green).

## Task Commits

Each task was committed atomically:

1. **Task 1: Deterministic sampler and dynamic domain validator** - `7713984` (feat) -- includes `test_cg_input_sampler.py`, written early to satisfy this task's own `<verify>` step (see Deviations)
2. **Task 2: Pydantic contract for the model's candidate set** - `6679704` (feat)
3. **Task 3: Tier 1 orchestrator with bounded retry and provenance** - `539d4f5` (feat)
4. **Task 4: The generate-inputs route** - `ba3aad8` (feat)
5. **Task 5: Tier 0 test suite and the GHIN-04 import-boundary assertion** - `0df2f18` (test) -- `test_cg_input_sampler.py` already existed from Task 1; this commit added the two remaining test files

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `data-service/cg_input_sampler.py` - Tier 0 deterministic sampler + dynamic domain validator
- `data-service/cg_schemas.py` - `GeneratedParameterValue`/`GeneratedCandidate`/`GeneratedCandidateSet`
- `data-service/cg_input_generation.py` - Tier 1 orchestrator, `generate_inputs()`
- `data-service/prompts/input_generation_system.md` - versioned system prompt
- `data-service/app.py` - `ComputgraphGenerateInputsRequest` + `POST /computgraph/generate-inputs` route
- `data-service/tests/test_cg_input_sampler.py` - 29 Tier 0 tests
- `data-service/tests/test_cg_input_generation.py` - 15 Tier 1 orchestrator tests
- `data-service/tests/test_cg_input_boundary.py` - 4 GHIN-04 import-boundary tests

## Decisions Made

- Tier 0's `limit` direction bias is applied uniformly across every numeric bound parameter rather than evaluating `metricExpression` (which Tier 0 has no visibility into) -- documented in the module docstring as an honest heuristic for `monotone-bound` rules and an exact behavior for `direct-parameter` rules, with the actual satisfaction guarantee living entirely in the post-processing step, not in the sampler.
- `candidate.parameters[].parameterId` is the bound row's `reinstateParameterId`, never `parameterName` -- verified directly against the Frame fixture's deliberately divergent `HTotal`/`Spans` pair (plan 38-02's JOIN A fixture), since that is the exact string `ParameterReinstateComponent.cs` matches on; `displayName` carries the human-readable `parameterName`.
- `resolve_active_provider` is accessed via `llm_gateway.resolve_active_provider(...)` (a qualified module reference) rather than a bare-name import, so the literal name appears exactly once in the file's source -- satisfying the "single call site, never inside the retry loop" acceptance criterion literally, not just in spirit.
- The diversity gate treats "not diverse enough" as a retry-triggering violation over the whole Tier-1 candidate set (fed back via `append_domain_feedback`), not a silent drop of individual candidates -- consistent with the plan's "no partial result" guarantee for a single attempt's output.
- `ruleSatisfaction` for a `monotone-bound` rule is computed by a hand-written `ast.parse()`-based restricted arithmetic evaluator (`+`, `-`, `*`, `/`, parens, literals, bare variable names only) against `metricExpression`, deliberately never Python `eval()` -- degrades any malformed expression to `undeterminable` rather than raising or executing arbitrary code.
- Two docstring/comment rewrites were needed after the fact to keep this plan's own literal grep-based acceptance criteria true: a mention of "`Field(ge=..., le=...)`" in `cg_schemas.py`'s D-17 comment and "`sys.modules`" in `test_cg_input_boundary.py`'s docstring both accidentally matched the forbidden-pattern greps they were describing; both were reworded to convey the same meaning without the literal banned substring.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `test_cg_input_sampler.py` written during Task 1, not deferred to Task 5**
- **Found during:** Task 1, attempting to run its own `<verify>` command
- **Issue:** Task 1's `<verify>` step is `python -m pytest data-service/tests/test_cg_input_sampler.py -q`, but that file is listed under Task 5's `<files>`, not Task 1's -- the command as written cannot pass until a later task exists.
- **Fix:** Wrote a full 29-test `test_cg_input_sampler.py` as part of Task 1's own commit, so the task's verify step is genuinely satisfied when it runs. Task 5 then only needed to add the two remaining test files (`test_cg_input_generation.py`, `test_cg_input_boundary.py`); it did not need to re-touch the sampler test file.
- **Files modified:** `data-service/tests/test_cg_input_sampler.py`
- **Commit:** `7713984` (Task 1)

**2. [Rule 1 - Bug] `cg_schemas.py`'s new nullable `Field` defaults triggered a false-positive grep match on the plan's own "no new `ge=`/`le=`/`gt=`/`lt=` constraint" acceptance criterion**
- **Found during:** Task 2, running the acceptance-criteria grep before committing
- **Issue:** `Field(default=None, ...)` contains the literal substring `lt=` (from `defau**lt=**None`), which the plan's grep check `'ge=\|le=\|gt=\|lt='` matches -- inflating the line count from the pre-edit baseline of 1 even though no actual numeric bound was added. A second false positive came from the D-17 warning comment itself literally spelling `Field(ge=..., le=...)` as an example of what NOT to add.
- **Fix:** Switched the three new nullable fields to positional `Field(None, description=...)` (no `default=` keyword), and reworded the warning comment to describe "a numeric-bound Field constraint" instead of spelling out the literal forbidden pattern.
- **Files modified:** `data-service/cg_schemas.py`
- **Commit:** `6679704` (Task 2)

**3. [Rule 1 - Bug] Two more self-referential literal-token false positives, caught before their respective commits**
- **Found during:** Task 3 (`resolve_active_provider` grep) and Task 5 (`sys.modules` grep)
- **Issue:** `cg_input_generation.py`'s bare-name import of `resolve_active_provider` plus its single call site produced 2 matching lines against a "`grep -c` returns 1" acceptance criterion; a docstring mention of "`/llm/generate`" in the same file matched a "returns 0" criterion. Separately, `test_cg_input_boundary.py`'s own docstring, explaining that it deliberately does NOT inspect the interpreter's loaded-module registry, spelled out the literal string `sys.modules` twice -- matching the file's own "`grep -c 'sys.modules'` returns 0" criterion.
- **Fix:** Switched to `import llm_gateway` + qualified `llm_gateway.resolve_active_provider(...)` (single occurrence); reworded the `/llm/generate` docstring mention to avoid the literal path string; reworded both `sys.modules` docstring mentions to describe the same idea ("the interpreter's already-loaded module registry") without the literal banned substring.
- **Files modified:** `data-service/cg_input_generation.py`, `data-service/tests/test_cg_input_boundary.py`
- **Commit:** `539d4f5` (Task 3), `0df2f18` (Task 5)

---

**Total deviations:** 4 auto-fixed (1 blocking-sequencing, 3 self-referential documentation bugs caught by this plan's own acceptance-criteria greps before commit)
**Impact on plan:** All four were caught and fixed before their respective task commits landed -- no scope creep, no behavior change beyond what each task already specified. The sequencing deviation (writing the sampler test early) only moved WHEN a planned file was written, not WHAT was built.

## Issues Encountered

None beyond the auto-fixed items above -- every fix was caught by the plan's own automated verify commands before commit, exactly as the deviation protocol intends.

## User Setup Required

None -- no external service configuration required. All verification ran locally via `python -m pytest` against fake Neo4j sessions and a fake LLM adapter; no live Neo4j or live LLM call was made anywhere in this plan's tests.

## Next Phase Readiness

- Plan 38-05 (the standalone `:DesignState` writer / `POST /computgraph/candidates/accept`) can now consume `generate_inputs()`'s exact candidate shape -- `candidateId`, `strategy`, `parameters[]`, `excludedParameters[]`, `ruleSatisfaction`, `provenance` (all ten keys), `statePayload` -- as its input contract. `test_cg_input_boundary.py` already asserts `cg_input_generation` does not import the persistence module that plan creates, so wiring them together incorrectly will fail loudly on the very first run after 38-05 lands.
- Plan 38-06 (rendering) inherits `boundParameters[]`/`excludedParameters[]`/`candidates[]` in the exact shape `spec/API.md` documents, with `parameterId` already resolved to the reinstate-time identity rather than the display name.
- Plan 38-07 (SC1 measurement) has real functions to measure against: `cg_input_sampler.sample_candidate_set`/`normalized_distance` for SC1-a/d, `generate_inputs()`'s `llm_candidates_rejected` flag for SC1-c, and `_rule_satisfaction()`'s `geometry-required` -> `undeterminable` forcing for SC1-e. The `direct-parameter`/`monotone-bound` SC1-b threshold (>=75% satisfying the rule limit) is not yet measured against a live LLM in this plan -- that measurement is explicitly plan 38-07's job, not this one's.
- No blockers.

## Self-Check: PASSED

All 8 created/modified files verified present on disk (`test -f`) and all 5 task commit hashes (7713984, 6679704, 539d4f5, ba3aad8, 0df2f18) verified present via `git log --oneline --all`.

---
*Phase: 38-ai-generated-grasshopper-script-inputs*
*Completed: 2026-07-27*
