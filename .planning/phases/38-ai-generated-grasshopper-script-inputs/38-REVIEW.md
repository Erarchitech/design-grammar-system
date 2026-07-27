---
phase: 38-ai-generated-grasshopper-script-inputs
reviewed: 2026-07-27T00:00:00Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
  - DG/src/DG.Core/Models/Computgraph/CgNode.cs
  - DG/src/DG.Core/Models/Computgraph/CgNodeInputParam.cs
  - DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs
  - DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs
  - DG/tests/DG.Tests/ComputgraphContextSerializerTests.cs
  - DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs
  - data-service/app.py
  - data-service/cg_input_bindings.py
  - data-service/cg_input_generation.py
  - data-service/cg_input_sampler.py
  - data-service/cg_paramstate_store.py
  - data-service/cg_schemas.py
  - data-service/computgraph_publish.py
  - data-service/prompts/input_generation_system.md
  - data-service/tests/cg_fixtures.py
  - data-service/tests/input_gen_eval/__init__.py
  - data-service/tests/input_gen_eval/cassettes/README.md
  - data-service/tests/input_gen_eval/cassettes/direct_parameter.json
  - data-service/tests/input_gen_eval/cassettes/monotone_bound.json
  - data-service/tests/input_gen_eval/scoring.py
  - data-service/tests/test_cg_input_bindings.py
  - data-service/tests/test_cg_input_boundary.py
  - data-service/tests/test_cg_input_generation.py
  - data-service/tests/test_cg_input_sampler.py
  - data-service/tests/test_cg_paramstate_store.py
  - data-service/tests/test_computgraph_publish.py
  - data-service/tests/test_input_gen_eval.py
  - llm/structure_rules.json
  - spec/API.md
  - spec/DATABASE.md
  - spec/RULE-PARTITION-POLICY.md
  - ui-v2/src/components/display/CandidateTable.jsx
  - ui-v2/src/components/index.js
  - ui-v2/src/lib/inputGenApi.js
  - ui-v2/src/screens/ModelScreen.jsx
findings:
  critical: 2
  warning: 3
  info: 2
  total: 7
status: issues_found
---

# Phase 38: Code Review Report

**Reviewed:** 2026-07-27T00:00:00Z
**Depth:** standard
**Files Reviewed:** 34
**Status:** issues_found

## Summary

Phase 38 (AI-generated Grasshopper script inputs) is well-architected and unusually well-documented: the Tier0/Tier1 split, the generation/acceptance write-boundary (enforced by an `ast`-based import-closure test), the never-clamp domain validator, and the D-09 "never overclaim on geometry-required" guarantee are all real, tested, structural properties, not just docstring claims. However, two genuine functional defects were found that undermine documented guarantees: (1) the `POST /computgraph/candidates/accept` route cannot honor the `parameterOverrides` feature that `generate-inputs` supports, so any candidate generated with an override is unconditionally rejected at accept time; and (2) the new `AI input candidates` panel in `ModelScreen.jsx` reuses non-globally-unique `candidateId` values (`c0`..`cN-1`) as a persistent "already accepted" key without ever resetting it across regenerations, causing unrelated future candidates to render as falsely already-accepted and blocking their real acceptance. Three further robustness/spec-compliance gaps in `cg_input_generation.py` and `cg_input_bindings.py` are reported as warnings.

## Critical Issues

### CR-01: `POST /computgraph/candidates/accept` cannot honor a candidate generated with `parameterOverrides`

**File:** `data-service/cg_paramstate_store.py:261-296`, `data-service/app.py:1615-1647`
**Issue:** `generate_inputs()` accepts a `parameter_overrides` list (spec/API.md's documented D-06 architect override) and threads it into `cg_input_bindings.classify_rule(session, rule_id, project, bindings, parameter_overrides)`, which replaces the bound-parameter scope for that call. `accept_candidate()`, however, calls `classify_rule(session, rule_id, project, bindings)` with **no** `parameter_overrides` argument at all, and `ComputgraphAcceptCandidateRequest` (app.py) has no `parameterOverrides` field to even carry one through. The override information is also never persisted anywhere in `provenance` (`_PROVENANCE_KEYS`/`_REQUIRED_PROVENANCE_KEYS` in `cg_paramstate_store.py` carry no such key), so it cannot be reconstructed from the round-tripped candidate either.

Concretely: a rule whose default `inputBindings` entry scopes to `["HTotal"]`, generated instead with `parameterOverrides=["SpansCount"]`, produces a candidate whose `parameters[]` carry SpansCount's `reinstateParameterId`. At accept time, `classify_rule()` (no override) resolves back to the default `["HTotal"]` scope, `select_parameters()` builds a `bound` list containing only the HTotal row, and `cg_input_sampler.validate_candidate()` then reports `unknown-parameter` (SpansCount's id isn't in `bound`) and `missing-parameter` (HTotal was never supplied) — `accept_candidate` raises `CandidateDomainViolation` and refuses to write. Any candidate generated via `parameterOverrides` is therefore unconditionally un-acceptable, silently breaking a documented feature end to end. No test in `test_cg_paramstate_store.py` or `test_cg_input_generation.py` exercises override+accept together, so this was never caught.
**Fix:** Add `parameterOverrides` to `ComputgraphAcceptCandidateRequest` and thread it through to `accept_candidate(..., parameter_overrides=payload.parameterOverrides)` → `classify_rule(session, rule_id, project, bindings, parameter_overrides)`, mirroring `generate_inputs()`'s call shape. If threading the raw list through the request is undesirable, persist the resolved parameter scope (or the override list itself) in `provenance` at generation time so accept-time re-classification can reconstruct it without a fresh caller-supplied argument.

### CR-02: `acceptedStateIds` never resets across regenerations, causing false "Accepted" state on unrelated future candidates

**File:** `ui-v2/src/screens/ModelScreen.jsx:394-398, 1132, 1134-1159`
**Issue:** `cg_input_generation._postprocess_candidates` assigns `candidateId: f"c{index}"` — an index-based id, unique only *within one response*, reused verbatim (`c0`, `c1`, ...) by every subsequent `generate-inputs` call for the same or a different rule. `ModelScreen.jsx` tracks acceptance with `acceptedStates` (`[{candidateId, stateId}]`), appended to on every successful `acceptCandidate()` call (line ~1147) but **never cleared**: the effect that resets `candidates`/`genErr` on rule change (lines 394-398) does not reset `acceptedStates`, and the "Generate" click handler (line ~1094) does not reset it either. `CandidateTable` is then handed `acceptedStateIds={acceptedStates.map((a) => a.candidateId)}` (line 1132) and renders any candidate whose `candidateId` matches — by position, not by identity — as already `Accepted` (hiding its Accept/Reject buttons, see `CandidateTable.jsx:138-163`).
Concretely: accept candidate `c1` for rule A, then either switch to rule B or simply click "Generate" again for the same rule — the new response's `c1` (a completely different, never-accepted candidate) renders with the "Accepted" badge and no Accept button, permanently blocking the architect from accepting that row through the UI.
**Fix:** Reset `acceptedStates` alongside `setCandidates(null)` in the rule-change effect (line 396) and again at the start of the Generate click handler, before `generateInputs()` is awaited. Longer-term, key acceptance by the response's own generation identity (e.g. pair `candidateId` with the response's own `stateId`/a monotonically-increasing generation counter) rather than the bare per-response index.

## Warnings

### WR-01: Tier-1 candidate set is never checked for the requested count or for valid/non-duplicate `strategy` values

**File:** `data-service/cg_input_generation.py:783-821`
**Issue:** The system prompt and `build_generation_prompt` instruct the model to "Produce exactly {candidate_count} candidates, one per strategy... never fewer, never more, never a duplicate strategy," and `cg_schemas.GeneratedCandidate.strategy` is deliberately typed `str` (not a `Literal`) on the stated premise that "validity is checked" elsewhere. In the retry loop, only `cg_input_sampler.validate_candidate()` (per-parameter domain/step/type) and `_diversity_violations()` (pairwise distance) are run against the parsed `candidate_assignments` — there is no check that `len(candidate_assignments) == count`, and no check that every `candidate["strategy"]` is one of `cg_input_sampler.STRATEGIES` or that no two candidates share a strategy. A model that returns fewer candidates than requested, or reuses a strategy string, passes straight through as a Tier-1 success (`tier1_candidates = candidate_assignments`), with no retry and no diagnostic flag, silently violating the documented contract and (for a short count) the SC1-d diversity denominator.
**Fix:** Add a `count_violations`/`strategy_violations` check alongside the existing domain/diversity checks in the retry loop: reject (and re-append feedback) when `len(candidate_assignments) != count`, when any `strategy` is outside `cg_input_sampler.STRATEGIES`, or when strategies repeat.

### WR-02: `select_parameters()` silently drops an overridden/bound parameter name absent from the published set

**File:** `data-service/cg_input_bindings.py:465-508`
**Issue:** When `classification.parameterNames` is non-empty, `considered = [p for p in published_parameters if p.get("parameterName") in name_filter]` filters `published_parameters` down to matching rows only. If a name in `parameterNames` (from either the `inputBindings` entry or an architect-supplied `parameterOverrides` list) does not correspond to any published `:Parameter`, it produces no row in `considered` at all — so it never reaches `_exclusion_reason()` and never appears in either `bound` or `excluded`. This directly contradicts the module's own stated "never guess"/"never silently drop" discipline (documented for `derive_reinstate_parameter_ids` in `computgraph_publish.py`, and implied for `excludedParameters[]` by spec/API.md D-04) — an architect who typos a parameter name in `parameterOverrides`, or a binding whose `parameters[]` entry drifts from the published Computgraph, gets no `excludedParameters[]` entry and no error explaining why fewer parameters than expected were bound.
**Fix:** After filtering, diff `classification.parameterNames` against the set of `parameterName` values actually found in `considered`/`published_parameters`, and emit an explicit excluded entry (new reason, e.g. `not-published`) for each name with no matching row.

### WR-03: `Neo4jValidGraphRepository.TryParseDesignState`'s v1 fallback is not covered by its own "never crash" exception filter

**File:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:157-242`
**Issue:** The method's docstring and the `catch` clause's comment ("Malformed payload — return null rather than crash") imply the whole method degrades gracefully on any parse failure. The `try` block, however, wraps both the v2 branch and the v1 fallback (`DesignStateJsonSerializer.Deserialize(statePayloadJson)`), while the `catch` filter is narrowed to `ex is JsonException or InvalidOperationException`. If the v1 deserializer throws any other exception type for a malformed-but-non-JSON-invalid v1 payload, it propagates out of `TryParseDesignState` into `GetRunsAsync`'s `ForEachAsync` callback, which has no surrounding try/catch of its own — a single malformed legacy v1 `DesignState` would then fail the entire `GetRunsAsync` call (every run in the response), not just the one bad payload, contradicting the "never crash" framing this phase's changes rely on when parsing the newly-introduced v2 envelope alongside legacy v1 data.
**Fix:** Either broaden the catch filter to `catch (Exception)` (matching the "never crash" contract already implied) or verify and document the exact closed set of exception types `DesignStateJsonSerializer.Deserialize` can throw and confirm they are all covered.

## Info

### IN-01: `spec/API.md`'s `candidates/accept` example `stateId` is lowercase hex, but the implementation emits uppercase

**File:** `spec/API.md:284`, `data-service/cg_paramstate_store.py:73-95`
**Issue:** `compute_param_state_id()` builds `f"DS_{digest}"` from `hashlib.sha256(...).hexdigest()[:16].upper()`, always uppercase (matching `dg:`-style ids elsewhere in the codebase and `Neo4jValidGraphRepositoryTests.cs`'s own `DS_A1B2C3D4E5F6A7B8`-style fixtures). The example response in `spec/API.md` shows `"stateId": "DS_a1b2c3d4e5f6a7b8"` (lowercase), which is not a value the shipped code could ever produce.
**Fix:** Uppercase the example `stateId` in spec/API.md to match the real output shape.

### IN-02: `PARAMETER_STATE_COMPONENT_GUID` is duplicated as a bare string literal in three places

**File:** `data-service/computgraph_publish.py:68`, `data-service/tests/cg_fixtures.py:52-54`
**Issue:** The GUID is correctly pinned to `DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs`'s real `ComponentGuid` today, but it is hand-copied as a literal in two Python files (plus the C# source of truth), with only a comment — no test — asserting the cross-language identity. A future GUID change on the C# side (component GUIDs are supposed to be immutable, but the risk is real given `CLAUDE.md`'s own "Old component GUIDs" gotcha) would silently desync JOIN A without any test failing to flag it.
**Fix:** Add a small cross-language parity test (mirroring `test_computgraph_publish.py`'s existing `GOLDEN_DG_ID` parity anchor pattern) that fails loudly if the literal ever drifts from the C# source, or centralize the constant in one place both languages read from at build/test time.

---

_Reviewed: 2026-07-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
