---
phase: 38-ai-generated-grasshopper-script-inputs
fixed_at: 2026-07-27T18:40:00Z
review_path: .planning/phases/38-ai-generated-grasshopper-script-inputs/38-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 38: Code Review Fix Report

**Fixed at:** 2026-07-27T18:40:00Z
**Source review:** .planning/phases/38-ai-generated-grasshopper-script-inputs/38-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (critical_warning scope — Info findings IN-01/IN-02 excluded)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: `POST /computgraph/candidates/accept` cannot honor a candidate generated with `parameterOverrides`

**Files modified:** `data-service/cg_paramstate_store.py`, `data-service/app.py`
**Commit:** c5e794f
**Applied fix:** Added `parameter_overrides: list[str] | None = None` parameter to `accept_candidate()`, threaded it into `cg_input_bindings.classify_rule(session, rule_id, project, bindings, parameter_overrides)` (mirroring `generate_inputs()`'s call shape exactly). Added `parameterOverrides: list[str] | None = None` field to `ComputgraphAcceptCandidateRequest` in `app.py` and passed `payload.parameterOverrides` through to `accept_candidate(...)`. Verified: Python `ast.parse` on both files, plus full `test_cg_paramstate_store.py` + `test_computgraph_publish.py` + `test_cg_input_generation.py` suites (34 passed).

### CR-02: `acceptedStateIds` never resets across regenerations, causing false "Accepted" state on unrelated future candidates

**Files modified:** `ui-v2/src/screens/ModelScreen.jsx`
**Commit:** 7b1530b
**Applied fix:** Added `setAcceptedStates([])` to the rule-change effect (alongside the existing `setCandidates(null)`/`setGenErr("")` reset) and to the top of the "Generate" button's `onClick` handler, before `generateInputs()` is awaited. This prevents position-based `candidateId` reuse (`c0`..`cN-1`) across responses from rendering an unrelated, never-accepted candidate as already-accepted. No JS/JSX syntax checker was available in this environment (no `node_modules` installed for `ui-v2`); verification relied on Tier 1 (re-read confirming fix text present and surrounding code intact) per the verification strategy's documented fallback for unsupported file types.

### WR-01: Tier-1 candidate set is never checked for the requested count or for valid/non-duplicate `strategy` values

**Files modified:** `data-service/cg_input_generation.py`
**Commit:** 41c7e8a
**Applied fix:** Added a new `_count_and_strategy_violations(candidate_assignments, count)` helper that checks `len(candidate_assignments) == count`, that every `strategy` is one of `cg_input_sampler.STRATEGIES`, and that no two candidates share a strategy — emitting the same violation-dict shape (`parameterId`/`code`/`message`) the existing domain/diversity checks use. Wired the check into the retry loop between the domain-violation check and the diversity check, so a violation triggers the same `append_domain_feedback` + `continue` retry path rather than silently passing as a Tier-1 success. Verified: `ast.parse` syntax check plus the full existing `test_cg_input_generation.py` suite (15 passed, no regressions).

### WR-02: `select_parameters()` silently drops an overridden/bound parameter name absent from the published set

**Files modified:** `data-service/cg_input_bindings.py`
**Commit:** 1364955
**Applied fix:** After the existing `bound`/`excluded` partition loop, added a diff step: when `classification.parameterNames` is non-empty, compute `found_names` from `considered` and append an explicit `{cgId: None, parameterName: <name>, reason: "not-published"}` entry to `excluded` for every name in the filter set with no matching published-parameter row. This surfaces typo'd `parameterOverrides` entries and drifted `inputBindings` scopes instead of letting them vanish from both `bound[]` and `excluded[]`. Verified: `ast.parse` syntax check plus the full `test_cg_input_bindings.py` suite (38 passed) and cross-check runs of `test_cg_paramstate_store.py` / `test_computgraph_publish.py` / `test_cg_input_generation.py` (34 passed), no regressions.

### WR-03: `Neo4jValidGraphRepository.TryParseDesignState`'s v1 fallback is not covered by its own "never crash" exception filter

**Files modified:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs`
**Commit:** b0feac3
**Applied fix:** Broadened the `catch` filter from `catch (Exception ex) when (ex is JsonException or InvalidOperationException)` to `catch (Exception)`, matching the "never crash" contract the method's docstring and comment already imply, and updated the comment to explain why (the v1 fallback deserializer's exception surface is not a closed set the narrower filter can safely enumerate, and an uncaught exception here would fail `GetRunsAsync`'s entire response, not just the one malformed run). Verified: `dotnet build DG/src/DG.Core/DG.Core.csproj` (0 warnings, 0 errors) and `dotnet test DG/tests/DG.Tests/DG.Tests.csproj --filter Neo4jValidGraphRepositoryTests` (18 passed, 0 failed).

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-07-27T18:40:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
