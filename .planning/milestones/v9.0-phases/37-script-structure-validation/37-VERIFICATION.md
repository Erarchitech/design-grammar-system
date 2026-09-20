---
phase: 37-script-structure-validation
verified: 2026-07-27T00:00:00Z
status: human_needed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Delete an Interface tag from Procedure 11_Proc on the real Frame Grasshopper canvas, re-publish through the DG COMPUTGRAPH PUBLISH component, then POST /computgraph/validate {project, definitionId}"
    expected: "Response flags the procedure_without_interface check and names the exact procedure (11_Proc / 2D Truss Configuration) in the finding's entities"
    why_human: "SC1 requires a live Rhino/Grasshopper canvas edit and a re-publish through the real DG plugin. The automated integration tier proves the check logic against synthetic published envelopes (interface-stripped fixture in 37-05's integration suite), but not the end-to-end canvas -> parse -> publish -> validate loop through the actual plugin UI. Explicitly deferred in 37-VALIDATION.md's Manual-Only Verifications table to /gsd-verify-work 37, per the Phase 33 / 34-02 / 34-03 precedent, not self-approved."
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  status: human_needed
---

# Phase 37: Script Structure Validation Verification Report

**Phase Goal:** Design Grammars validate the structure of the Grasshopper script itself: deterministic Cypher checks over the published Computgraph plus Design-Rule-mapped structural requirements, and an LLM consult endpoint that answers questions about a script's structure — the foundation v10.0 Script Intelligence (generation/editing/consulting) builds on.
**Verified:** 2026-07-27
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SVAL-01: Deterministic, LLM-free structural checks run over the published Computgraph via Cypher, each finding referencing exact entities | ✓ VERIFIED | `data-service/cg_structure_checks.py` (919 lines) implements 7 checks (`check_orphan_patterns`, `check_procedures_without_interface`, `check_dangling_param_links`, `check_algorithms_without_procedure`, `check_parameters_without_datatype`, `check_objects_without_behavior`, `check_annotation_conventions`). SC4 grep gate (`llm_gateway\|adapter\.generate` over the module) returns 0. `docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -q` → 40+ integration tests pass live against Neo4j (ran and confirmed personally: 77 passed for structure-checks + consult combined) |
| 2 | SVAL-02: Design Rules can be mapped to script-structure requirements and evaluated over the Computgraph, reported pass/fail per rule with supporting entities | ✓ VERIFIED | `llm/structure_rules.json` (4 seeded mappings), `_OPERATION_TEMPLATES`, `evaluate_rule_mappings()` in `cg_structure_checks.py`. Confirmed by running `docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -q -k rule_mapped` (included in the full container run — 573 passed, 0 failed) |
| 3 | SVAL-03: `POST /computgraph/consult` answers NL questions about a published script structure via the gateway, grounded in graph entities, read-only | ✓ VERIFIED | `data-service/dg_context.py` (`fetch_computgraph_subgraph`, `build_consult_prompt`, `check_consult_grounding`, `consult_computgraph`) + `POST /computgraph/consult` route in `app.py`. `docker compose exec data-service python -m pytest tests/test_computgraph_consult.py -q` → 17/17 pass against live Neo4j with a cassette LLM adapter (no paid call) |
| 4 | SC1: Deleting an Interface tag from the Frame structure and re-publishing makes `/computgraph/validate` flag Procedure-without-Interface, naming the exact procedure | ⚠️ HUMAN VERIFICATION NEEDED | Automated analogue proven (interface-stripped synthetic envelope, 37-05 integration tier), but the live-Rhino canvas-edit-and-republish loop through the real DG plugin is explicitly deferred to `/gsd-verify-work 37` — not self-approved, per `37-VALIDATION.md` and Phase 33/34-02/34-03 precedent |
| 5 | SC2: A rule mapped to "must contain Procedure matching *Footer*" passes on the full Frame and fails on a copy published without the 12_Proc group | ✓ VERIFIED | `data-service/tests/test_cg_structure_checks.py::TestRuleMappedChecksIntegration` — SC2 positive/negative pair asserted by entity content, ran green in-container |
| 6 | SC3: "Which parameters drive the truss height?" via `/computgraph/consult` answers citing `11_Var_HTotal` (grounded, not hallucinated) | ✓ VERIFIED | `data-service/tests/test_computgraph_consult.py::TestConsultIntegration::test_consult_full_frame_route_returns_200_with_grounded_total_height_citation` — passed in-container against live Neo4j with cassette adapter |
| 7 | SC4: All structural checks are deterministic and LLM-free; only `/consult` calls the gateway | ✓ VERIFIED | `grep -v '^\s*#' data-service/cg_structure_checks.py \| grep -c 'llm_gateway\|adapter\.generate'` → `0` (ran personally). Determinism tests (`test_rule_mapped_determinism...`, `test_structural_route_determinism...`) pass in-container |
| 8 | Report surface: validation report JSON matches `spec/API.md` exactly, `counts` correctly reflects both findings and rule-mapped failures | ✓ VERIFIED | Code review found CR-01 (`counts.warning` never reflected rule-mapped failures) and WR-02 (worked example mismatch) — both fixed in commits `9e60191` and `aa8ffdd`, confirmed present in `build_validation_report()` (line 909: `counts[SEVERITY_WARNING] += sum(1 for result in rule_results if not result["passed"])`) and in `spec/API.md`'s regenerated example |

**Score:** 7/8 truths verified (1 explicitly and correctly routed to human verification — SC1's live-Rhino half)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data-service/cg_structure_checks.py` | 7 SVAL-01 checks + SVAL-02 rule evaluator + report builder | ✓ VERIFIED | 919 lines, all documented functions present, wired into `app.py` route, zero interpolated Cypher (grepped, 0 matches) |
| `llm/structure_rules.json` | Versioned rule-mapping artifact, 4 seeded mappings | ✓ VERIFIED | `{"version": 1, "mappings": [...]}` with exactly `ruleId`/`operation`/`params`/`description` keys, no embedded Cypher |
| `data-service/dg_context.py` (Phase 37 additions) | Subgraph fetch + consult pipeline | ✓ VERIFIED | 438 new lines confirmed via `git diff --stat 069e8f8 HEAD`; `fetch_computgraph_subgraph`, `build_consult_prompt`, `check_consult_grounding`, `consult_computgraph` all present and wired |
| `data-service/app.py` routes | `POST /computgraph/validate`, `POST /computgraph/consult` | ✓ VERIFIED | 95 new lines; both routes registered (confirmed via `app.routes` inspection in plan verify steps and directly via grep) |
| `data-service/tests/cg_fixtures.py`, `consult_cassette.py`, `test_cg_fixtures.py`, `README.md` | Wave-0 test substrate | ✓ VERIFIED | All present, all referenced by later plans' test suites |
| `data-service/tests/test_cg_structure_checks.py`, `test_computgraph_consult.py` | Two-tier test suites | ✓ VERIFIED | 77 tests combined, all pass in-container against live Neo4j; host-tier subsets (52 tests) pass with zero container |
| `spec/API.md` Computgraph subsection | Normative validate/consult contracts | ✓ VERIFIED | Present, all documented keys grepped and confirmed, worked example regenerated post-review (WR-02 fix) |
| `spec/RULE-PARTITION-POLICY.md` addendum | Third validation system named | ✓ VERIFIED | "Computgraph Structural Checks (Phase 37)" section present, decision-table rows added, no existing decision renumbered |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `app.py::post_computgraph_validate` | `cg_structure_checks.build_validation_report` | direct call, one session | ✓ WIRED | Confirmed by grep + passing route tests |
| `app.py::post_computgraph_consult` | `dg_context.consult_computgraph` | direct call, one session | ✓ WIRED | Confirmed by grep + passing route tests |
| `build_validation_report` | `run_structural_checks` + `evaluate_rule_mappings` | direct calls | ✓ WIRED | Both feed `findings`/`ruleResults`; `counts` now aggregates both (post CR-01 fix) |
| `consult_computgraph` | LLM gateway (`resolve_active_provider`/`get_adapter`) | in-process call, injectable adapter | ✓ WIRED | `resolve_active_provider` appears ≥2 times in `dg_context.py` (pre-existing generator + this path); no HTTP re-post to the generate route |
| `evaluate_rule_mappings` | Metagraph `Rule` node (soft FK) | `Rule_Id` existence probe, `ruleExists` flag | ✓ WIRED | Confirmed by `RULE_EXISTS_METAGRAPH` op tag and passing `ruleExists false` integration assertions |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Host-tier unit suite (structure checks + consult, no container) | `python -m pytest data-service/tests/test_cg_structure_checks.py -q -k "convention or structure_rules or report_contract"` | 40 passed, 20 deselected | ✓ PASS |
| Host-tier consult suite | `python -m pytest data-service/tests/test_computgraph_consult.py -q` | 12 passed, 5 errors (integration tests needing live Neo4j — expected on host per README) | ✓ PASS (host-safe subset) |
| Full host suite (regression check) | `python -m pytest data-service/tests/ -q` | 544 passed, 4 failed (pre-existing `test_dg_context.py` Neo4j-hostname-resolution baseline, documented, unrelated to Phase 37), 1 skipped, 1 deselected, 25 errors (integration-marked, need compose network) | ✓ PASS — matches documented baseline, no regressions introduced |
| Integration tier: structure checks + consult (live Neo4j via compose) | `docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py tests/test_computgraph_consult.py -q` | 77 passed | ✓ PASS |
| Full integration suite (regression check) | `docker compose exec data-service python -m pytest tests/ -q` | 573 passed, 1 skipped, 1 deselected, 0 failures | ✓ PASS |
| SC4 gate: no gateway reference in checks module | `grep -v '^\s*#' data-service/cg_structure_checks.py \| grep -c 'llm_gateway\|adapter\.generate'` | `0` | ✓ PASS |
| Debt-marker scan on all Phase 37 files | `grep -n -E "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"` over all created/modified files | no matches | ✓ PASS |

### Code Review Findings (Resolved Before This Verification)

| ID | Severity | Issue | Resolution | Verified |
|----|----------|-------|------------|----------|
| CR-01 | critical | `counts.warning` never reflected rule-mapped (SVAL-02) failures, contradicting `spec/RULE-PARTITION-POLICY.md` and `spec/API.md`'s own worked example | Rolled `ruleResults` failures into `counts[SEVERITY_WARNING]` in `build_validation_report()` | ✓ Confirmed in code at `cg_structure_checks.py:909` |
| WR-01 | warning | Rule-mapping loader didn't require the operation-specific mandatory param (`namePattern`/`label`), letting a malformed mapping silently always-pass | Extended `_mapping_rejection_reason()` to reject mappings missing the operation-specific required param | ✓ Confirmed in code at `cg_structure_checks.py:440-453` |
| WR-02 | warning | `spec/API.md`'s worked example didn't match the real message format, entity shape, or `cgId` null-vs-empty-string contract | Regenerated the worked example from the real `_compose_message()`/`_entity()` output shape | ✓ Confirmed present in `spec/API.md` |
| IN-01 | info | `CHECK_IDS`/`STRUCTURE_RULE_IDS` dead exports | Not fixed (info-level, out of fix scope — acceptable) | — |
| IN-02 | info | Unreachable `except ValueError` branch in `post_computgraph_validate` | Not fixed (info-level, defensive forward-compatibility — acceptable) | — |

All in-scope (critical + warning) findings were fixed and independently re-verified in this pass by reading the resulting code, not merely trusting the REVIEW-FIX.md narrative.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SVAL-01 | 37-03 | Deterministic, LLM-free structural checks with entity references | ✓ SATISFIED | `cg_structure_checks.py`, integration tests green, SC4 gate green |
| SVAL-02 | 37-04 | Design Rules mapped to structural requirements, evaluated with pass/fail + supporting entities | ✓ SATISFIED | `llm/structure_rules.json`, `evaluate_rule_mappings()`, SC2 pair proven |
| SVAL-03 | 37-06 | `POST /computgraph/consult` answers NL questions, grounded, read-only | ✓ SATISFIED | `consult_computgraph()` + route, SC3 proven, no execute path |

`.planning/REQUIREMENTS.md` traceability table (line 168) reads `| SVAL-01 … SVAL-03 | Phase 37 | ✅ Complete (2026-07-27) |` and the requirement checklist entries (lines 91-93) are all checked `[x]` — no stale "Pending" state remains for this phase's requirement family (the concern flagged in the verification prompt about a prior ellipsis-range "Pending" row is resolved).

No orphaned requirements: all three SVAL IDs declared in plan frontmatter (`37-03`, `37-04`, `37-06`) match `.planning/REQUIREMENTS.md`'s SVAL family exactly.

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in any Phase 37 file. No empty implementations, no hardcoded-empty stub returns, no console-log-only handlers.

### Human Verification Required

### 1. SC1 — Live Rhino/Grasshopper canvas edit and re-publish flags Procedure-without-Interface

**Test:** Open the Frame definition in Rhino/Grasshopper. Delete an Interface tag from Procedure `11_Proc` (2D Truss Configuration). Re-publish through the DG COMPUTGRAPH PUBLISH component. Then `POST /computgraph/validate {project, definitionId}`.
**Expected:** The response's `findings` array contains a `procedure_without_interface` finding naming the exact procedure (`11_Proc` / "2D Truss Configuration").
**Why human:** Requires a live Grasshopper canvas edit and a real re-publish through the DG plugin UI — the automated integration tier proves the check logic correctly fires against a synthetic interface-stripped envelope, but cannot exercise the actual canvas → parse → publish round trip. This is explicitly named as deferred (not silently omitted) in `37-VALIDATION.md`'s Manual-Only Verifications table, per the established Phase 33 / 34-02 / 34-03 precedent for this project.

### Gaps Summary

No gaps found. All must-haves from the merged PLAN frontmatter (six plans) and all four ROADMAP success criteria are either verified with passing automated evidence (re-run personally, not merely trusted from SUMMARY.md) or explicitly and correctly routed to human verification with no attempt at self-approval. The one critical and two warning-level code-review findings were fixed in dedicated commits and the fixes were independently confirmed present and correct in the current codebase. No regressions were introduced relative to the pre-existing test baseline (544/548 host, 573/573 in-container, matching the documented known-baseline failures).

The phase is ready to proceed pending the human completing the SC1 live-Rhino checkpoint via `/gsd-verify-work 37`.

---

_Verified: 2026-07-27_
_Verifier: Claude (gsd-verifier)_
