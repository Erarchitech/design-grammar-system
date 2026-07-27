---
phase: 38-ai-generated-grasshopper-script-inputs
verified: 2026-07-27T00:00:00Z
status: human_needed
score: 3/4 must-haves verified
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "SC2 full round-trip: an accepted ParamState, once wired into PARAMETER REINSTATE on a live Grasshopper canvas, moves every slider to its accepted value and reports a per-parameter success ReStatus"
    test: "Publish the Frame definition; generate candidates for the direct-parameter fixture rule; accept one; wire the resulting DesignState into PARAMETER REINSTATE and trigger it"
    expected: "Every parameter in the accepted candidate reports a success ReStatus and its slider shows the accepted value"
    why_human: "Requires a live Rhino/Grasshopper session with a real canvas and slider components — no headless harness can exercise SetSliderValue or read ReStatus outputs. The storage (cg_paramstate_store) and VALIDATION GRAPH read (Neo4jValidGraphRepository.StandaloneStatesQuery) halves are unit-tested and pass; only the apply-side state transition is unverified."
human_verification:
  - test: "PARAMETER REINSTATE round-trip (38-UAT.md item 1, GHIN-02/SC2): publish Frame, generate for a direct-parameter rule, accept a candidate, read it via VALIDATION GRAPH, wire into PARAMETER REINSTATE, trigger"
    expected: "Every parameter in the accepted candidate reports a success ReStatus and its slider shows the accepted value"
    why_human: "Requires Rhino/Grasshopper; no headless harness for slider mutation or ReStatus"
  - test: "JOIN A on a real definition (38-UAT.md item 2, D-01/D-02): set a PARAMETER STATE input NickName different from its parameter's convention name, publish, inspect the resulting :Parameter node"
    expected: "The divergent parameter's reinstateParameterId equals the NickName, not the convention-derived name; any unresolvable parameter is absent from the node and reported in excludedParameters with reason unresolved-reinstate-id"
    why_human: "Requires a live canvas with a real, divergently-named wiring — the derivation logic is unit-tested against synthetic fixtures but this proves it against a genuine Rhino-authored definition"
  - test: "SC3 — nothing reaches the canvas before acceptance (38-UAT.md item 3, GHIN-04): generate candidates, reject all of them, observe canvas and network tab"
    expected: "No slider value changes at any point between generation and an explicit Accept click, and the browser network tab shows zero POSTs to /computgraph/candidates/accept"
    why_human: "Observing the absence of a side effect in a live GUI/network session cannot be automated from this repository's test suites"
---

# Phase 38: AI-generated Grasshopper Script Inputs — Verification Report

**Phase Goal:** Given a rule and the published Computgraph Parameter structure, AI proposes concrete input parameter sets for the Grasshopper script — delivered as ParamState-compatible payloads the architect can review and apply via PARAMETER REINSTATE.
**Verified:** 2026-07-27
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
|---|---|---|---|
| 1 | For a max-height rule against the Frame definition, generated candidates keep every parameter inside its recognized slider domain and satisfy the rule's limit where determinable | ✓ VERIFIED | `cg_input_sampler.validate_candidate` is the single, non-reimplemented enforcement point (`data-service/cg_input_sampler.py`), reused by both the sampler, the generation retry loop, the accept-side re-validation, and the eval harness. `python -m pytest data-service/tests/test_input_gen_eval.py -q -s` measures SC1-a=100%, SC1-b=100% (>= 75% required), SC1-c=4 valid candidates from a useless-model fixture, SC1-d=0.217 (>= 0.10 required), SC1-e=0 overclaims — all five thresholds pass, recorded in `38-VALIDATION.md`. 148/148 phase-owned pytest tests pass; `dotnet build`/`dotnet test` for the C# side are green (35/35). Caveat: the two committed cassettes backing SC1-a/b are synthetic-authored, not recorded from a live provider — this is disclosed in `38-VALIDATION.md` and does not affect the mechanical validator's correctness, which is independently proven by `test_cg_input_sampler.py`'s property-style sweep. |
| 2 | An accepted candidate round-trips: stored as ParamState → visible in VALIDATION GRAPH reads → applied via PARAMETER REINSTATE with per-parameter ReStatus reporting | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Storage half verified: `cg_paramstate_store.accept_candidate` writes a `DS_`-prefixed, MERGE-idempotent `:DesignState{kind:'ParamState'}` with all 11 provenance properties (`test_cg_paramstate_store.py`, 7+ tests green — zero writes on domain/provenance violation, confirmed by test). Read half verified: `Neo4jValidGraphRepository.StandaloneStatesQuery` is an additive second read wrapped in try/catch-degrade, dedup-safe, parameterized on `$project` (`Neo4jValidGraphRepositoryTests.cs`, 18/18 green, including a literal cross-language `statePayloadJson` parse test). The apply-side state transition (slider mutation + per-parameter ReStatus inside a live Grasshopper canvas) has no automated test path — it is a state-transition truth that only a live Rhino session can exercise. Routed to human verification (38-UAT.md item 1). |
| 3 | Nothing touches the canvas without explicit user acceptance — generation and application are strictly separated | ✓ VERIFIED | Structural guarantee is machine-checked, not merely claimed: `test_cg_input_boundary.py` walks the transitive AST import closure of `cg_input_generation`/`cg_input_sampler`/`cg_input_bindings` and asserts `gh_bridge` and `cg_paramstate_store` are absent (4/4 tests green). UI: `acceptCandidate(` appears exactly once in `ModelScreen.jsx`, inside the `CandidateTable`'s `onAccept` click handler; `generateInputs(` appears once, inside the `Generate` button's `onClick`; grep across every `React.useEffect` block in the file confirms neither function name appears inside any effect body. `Reject` (`onReject`) issues no request — confirmed by reading `CandidateTable.jsx`, which imports no API module. Live-browser network-tab confirmation (38-UAT.md item 3) remains pending as a corroborating human check but the structural separation is independently provable and proven. |
| 4 | Provenance is queryable: MATCH on generated ParamStates returns rule, model, and timestamp for each | ✓ VERIFIED | `cg_paramstate_store.fetch_generated_param_states` is a parameterized `MATCH (ds:DesignState {project, kind:'ParamState'}) WHERE ds.source='ai-generated'` read, filterable by `sourceRuleId`; `test_fetch_generated_param_states_returns_rule_model_and_timestamp` (data-service/tests/test_cg_paramstate_store.py:242) asserts `stateId`, `sourceRuleId`, `provider`, `model`, `generatedAt` are all present per row and that `rule_id` filtering works — this is the GHIN-03/SC4 assertion, and it passes. |

**Score:** 3/4 truths verified (1 present + wired, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `spec/API.md` | Normative contract for both new routes, SC1 thresholds | ✓ VERIFIED | Both route headings present, all 10 error codes, SC1-a..e table with literal thresholds, zero-write and never-overclaim guarantees documented |
| `spec/DATABASE.md` | ValidGraph/Computgraph schema amendments, false invariants removed | ✓ VERIFIED | `reinstateParameterId` documented as nullable on `:Parameter`; DesignState block has 4th `ai-generated` example line; "no orphan DesignStates" and "written only by VALIDATOR" invariants both removed (0 matches); two-writer statement and "Reading standalone ParamStates" note present naming `Neo4jValidGraphRepository` and 38-05 |
| `spec/RULE-PARTITION-POLICY.md` | `inputBindings` schema, single-authoring note, no new D-number | ✓ VERIFIED | "Input Generation Bindings (Phase 38)" section present (2 occurrences: heading + anchor), `inputBindings` schema fields present, `_FORBIDDEN_PARAM_KEYS` cross-referenced |
| `data-service/cg_input_bindings.py` | JOIN B: binding load, determinability, SWRL limit read | ✓ VERIFIED | Exists; `load_input_bindings`, `classify_rule`, `select_parameters`, `read_rule_limit` all present; 0 write statements; WR-02 fix (`not-published` reason) present at line 520 |
| `data-service/cg_input_sampler.py` | Tier 0 sampler + dynamic domain validator, never clamps | ✓ VERIFIED | `validate_candidate`, `sample_tier0`, `sample_candidate_set`, `normalized_distance` all present; no clamp/repair helper found by grep; property-sweep tests green |
| `data-service/cg_input_generation.py` | Tier 1 orchestrator, bounded retry, provenance, import boundary | ✓ VERIFIED | `generate_inputs` present; provider resolved once (grep confirms 1 occurrence of `resolve_active_provider`); WR-01 fix (`_count_and_strategy_violations`) present and wired into retry loop; no `gh_bridge`/write import |
| `data-service/cg_paramstate_store.py` | Accept-side persistence, server-side re-validation | ✓ VERIFIED | `accept_candidate`, `compute_param_state_id`, `fetch_generated_param_states` present; CR-01 fix (`parameter_overrides` threaded to `classify_rule`) present |
| `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` | Additive standalone-DesignState read | ✓ VERIFIED | `StandaloneStatesQuery`/`GetStandaloneStatesQueryForTesting` present; WR-03 fix (`catch (Exception)` broadened) present at both v1/v2 parse sites; 18/18 tests green |
| `ui-v2/src/lib/inputGenApi.js` | API client for the two routes | ✓ VERIFIED | `generateInputs`, `acceptCandidate`, `fetchAcceptedCandidates` exported; targets both documented routes |
| `ui-v2/src/components/display/CandidateTable.jsx` | Row-per-candidate table, D-09 honesty, D-04 visibility | ✓ VERIFIED | No API import; renders `satisfied`/`violated`/`undeterminable` distinctly (undeterminable styled neutral, D-09 comment present); excluded parameters render with reason, never a blank cell |
| `data-service/tests/input_gen_eval/scoring.py` | SC1 scoring functions | ✓ VERIFIED | All 5 functions present, reuse `validate_candidate`/`normalized_distance` rather than reimplementing |
| `.planning/phases/38.../38-UAT.md` | Tier 2 in-Rhino human verifications | ✓ VERIFIED | 3 items, single-line `expected:`/`result:` pairs (audit-uat parseable), `result: [pending]` — appropriately unresolved, not a gap |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `computgraph_publish.py` (`reinstateParameterId` write) | `cg_input_bindings.select_parameters` (read) | Graph property `Parameter.reinstateParameterId` | ✓ WIRED | Same string written at publish, read at generation; unresolved case excluded with reason, never guessed (tested) |
| `cg_input_generation.generate_inputs` | `cg_paramstate_store.accept_candidate` | Candidate object shape (`spec/API.md` `candidates[]`) | ✓ WIRED | `accept_candidate` re-reads live domains and re-runs `validate_candidate` rather than trusting the round-tripped client object; CR-01 fix makes `parameterOverrides` symmetric between generate and accept |
| `cg_paramstate_store.accept_candidate` (write) | `Neo4jValidGraphRepository.GetRunsAsync` (read) | `:DesignState{kind:'ParamState', graph:'ValidGraph'}` node | ✓ WIRED | Additive second read appended before dedup block; cross-language payload-shape test (`test_9`, Neo4jValidGraphRepositoryTests.cs) proves the Python-written envelope parses on the C# side |
| `ui-v2 ModelScreen.jsx` (Generate button) | `inputGenApi.generateInputs` → `app.py` route | HTTP POST | ✓ WIRED | Called only from `onClick`, never from `useEffect` (grep-verified across every effect block) |
| `ui-v2 CandidateTable` (Accept button) | `inputGenApi.acceptCandidate` → `app.py` route | HTTP POST | ✓ WIRED | Single call site in `ModelScreen.jsx`, inside `onAccept`'s click handler; CR-02 fix resets `acceptedStates` on rule-change and on new Generate click |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| SC1 five thresholds computed and asserted | `python -m pytest data-service/tests/test_input_gen_eval.py -q -s` | 15 passed; measured domainCompliance=1.0, ruleSatisfaction=1.0, diversity=0.217, overclaimCount=0 | ✓ PASS |
| Phase-owned Python test suite | `python -m pytest data-service/tests/test_cg_input_bindings.py test_cg_input_sampler.py test_cg_input_generation.py test_cg_input_boundary.py test_cg_paramstate_store.py test_computgraph_publish.py test_input_gen_eval.py test_error_responses.py test_cg_schemas.py -q` | 148 passed, 0 failed | ✓ PASS |
| .NET build | `dotnet build ./DG/DG.sln -c Release` | 0 warnings, 0 errors | ✓ PASS |
| .NET phase-owned tests | `dotnet test --filter "FullyQualifiedName~ComputgraphContextSerializer\|FullyQualifiedName~Neo4jValidGraphRepository"` | 35 passed, 0 failed | ✓ PASS |
| UI build | `npm --prefix ui-v2 run build` | exits 0 | ✓ PASS |
| GHIN-04 import-boundary assertion | `python -m pytest data-service/tests/test_cg_input_boundary.py -q` | 4 passed | ✓ PASS |
| `test_cg_structure_checks.py` (Phase 37 non-regression) | `python -m pytest data-service/tests/test_cg_structure_checks.py -q` | 20 errors, all `neo4j:7687` DNS-resolution failures (host cannot resolve the compose-internal hostname) | ? SKIP — pre-existing, documented environment limitation (see `38-VALIDATION.md` Sampling Rate and project MEMORY.md), not a Phase 38 regression |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| GHIN-01 | 38-01, 38-03, 38-04, 38-06 | AI proposes candidates from a rule + published Parameter structure, respecting slider domains | ✓ SATISFIED | `cg_input_bindings` + `cg_input_sampler`/`cg_input_generation` + `/computgraph/generate-inputs` route + UI panel, all tested |
| GHIN-02 | 38-02, 38-05 | ParamState-compatible payloads (Number/Integer/Boolean), applicable via PARAMETER REINSTATE | ✓ SATISFIED (mechanism) / pending human confirmation of live apply | `statePayload` v2 envelope built per candidate; `reinstateParameterId` JOIN A closed with refusal-not-guess semantics; live apply is UAT item 1 |
| GHIN-03 | 38-01, 38-04, 38-05 | Provenance (source rule, provider/model, timestamp) queryable in the graph | ✓ SATISFIED | All 10 provenance keys on every candidate object and all 11 persisted properties on the node; `fetch_generated_param_states` test asserts the MATCH read directly |
| GHIN-04 | 38-04, 38-05, 38-06 | Generation and application strictly separated; nothing reaches canvas without explicit acceptance | ✓ SATISFIED (structural) / pending human confirmation of no canvas mutation | `ast`-based import-boundary test; single accept call site in a click handler; no write import in the generation module |

No orphaned requirements: all four GHIN-01..04 IDs are claimed across the seven plans and REQUIREMENTS.md maps all four to Phase 38 exclusively.

### Anti-Patterns Found

None. Grep for `TODO|FIXME|XXX|TBD|HACK|PLACEHOLDER` across all phase-modified core files (`cg_input_bindings.py`, `cg_input_sampler.py`, `cg_input_generation.py`, `cg_paramstate_store.py`, `computgraph_publish.py`, `CandidateTable.jsx`, `inputGenApi.js`, `ModelScreen.jsx`, `Neo4jValidGraphRepository.cs`, `CgNodeInputParam.cs`, `CanvasContextExtractor.cs`) returns zero matches.

### Code Review Fix Verification (38-REVIEW.md → 38-REVIEW-FIX.md)

The review found 2 Critical + 3 Warning issues after all 7 plans executed. All 5 were independently re-verified present in the current codebase (not merely claimed in 38-REVIEW-FIX.md):

| Finding | Fix Verified In Code |
|---|---|
| CR-01 (accept can't honor `parameterOverrides`) | `cg_paramstate_store.py:267` (`parameter_overrides` param), `app.py:1531,1627` (`parameterOverrides` field on both request models, threaded through) |
| CR-02 (`acceptedStateIds` never resets) | `ModelScreen.jsx:402,1106` (`setAcceptedStates([])` in rule-change effect and Generate click handler) |
| WR-01 (no count/strategy check on Tier-1 output) | `cg_input_generation.py:633` (`_count_and_strategy_violations`), wired into retry loop at line 865-871 |
| WR-02 (`select_parameters` silently drops unmatched names) | `cg_input_bindings.py:520` (`"not-published"` reason entry) |
| WR-03 (narrow catch filter on v1 DesignState fallback) | `Neo4jValidGraphRepository.cs:127,237` (`catch (Exception)`, broadened from the narrower filter) |

All fixes confirmed by direct file inspection, and the phase's full test suite (148 pytest + 35 xUnit) still passes with the fixes in place.

### Human Verification Required

Three items, all previously captured in `.planning/phases/38-ai-generated-grasshopper-script-inputs/38-UAT.md` (Tier 2, requires a live Rhino/Grasshopper session), harvested here rather than duplicated:

1. **PARAMETER REINSTATE round-trip (GHIN-02, SC2)**
   **Test:** Publish the Frame definition; generate candidates for the `direct-parameter` fixture rule; accept one; add a VALIDATION GRAPH component and confirm the accepted ParamState appears; wire into PARAMETER REINSTATE and trigger.
   **Expected:** Every parameter in the accepted candidate reports a success ReStatus and its slider shows the accepted value.
   **Why human:** Requires a live Rhino canvas — no headless harness for slider mutation or ReStatus.

2. **JOIN A on a real definition (D-01/D-02)**
   **Test:** Set a PARAMETER STATE input NickName to differ from its parameter's convention name; publish; inspect the resulting `:Parameter` node.
   **Expected:** The divergent parameter's `reinstateParameterId` equals the NickName; unresolvable parameters are absent from the node and reported in `excludedParameters` with reason `unresolved-reinstate-id`.
   **Why human:** Requires a genuinely divergent, Rhino-authored canvas wiring, not a synthetic fixture.

3. **SC3 — nothing reaches the canvas before acceptance (GHIN-04)**
   **Test:** Generate candidates, reject all of them, observe the canvas and the browser network tab.
   **Expected:** No slider value changes at any point; zero POSTs to `/computgraph/candidates/accept`.
   **Why human:** Observing the absence of a side effect in a live GUI/network session cannot be automated from this repository's test suites.

### Gaps Summary

No blocking gaps found. All artifacts exist, are substantive, are wired, and pass their own test suites (148 pytest + 35 xUnit + clean `dotnet build`/`npm run build`). The 2 Critical + 3 Warning code-review findings were independently confirmed fixed in the current code, not merely claimed. The only unresolved items are the three Tier 2 in-Rhino verifications that no automated tool in this environment can exercise — these are appropriately captured in `38-UAT.md` with `result: [pending]` rather than glossed over, and are surfaced here as human-verification items per the Escalation Gate pattern. One truth (SC2's full round-trip) is downgraded from VERIFIED to PRESENT_BEHAVIOR_UNVERIFIED because its apply-side state transition (slider mutation + ReStatus) has no test coverage — the storage and read halves are fully tested, but "applied via PARAMETER REINSTATE with per-parameter ReStatus reporting" as a complete chain has not been observed running.

---

_Verified: 2026-07-27_
_Verifier: Claude (gsd-verifier)_
