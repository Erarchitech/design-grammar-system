---
phase: 1303-pravilo-gh-obekt
plan: "21"
subsystem: rule-conflict-check
tags: [d-64, d-65, dgopn-06, conflict-check, route-policy, graph-viewer]
requires:
  - phase: 1303-pravilo-gh-obekt
    provides: "1303-19 (RuleVariableRoles context-only definition); 1303-20 (participants written by ingest)"
provides:
  - "data-service/rule_conflicts.structural_conflicts: LLM-free conflict read on the written rule's atoms"
  - "GET /rules/{project}/{rule_id}/conflicts (member/path/viewer, 404 RULE_NOT_FOUND)"
  - "Graph Viewer: ingest first, conflict dialog after the write, Cancel opens the confirmed delete dialog"
affects: [1303-22, 1303-23]
tech-stack:
  added: []
  patterns:
    - "key = (subject class, DatatypeProperty, comparator); overlap over context participants, subject excluded, empty set overlaps everything with the same key"
    - "pure decision mapping (planConflictDecision) extracted from React so it is testable"
key-files:
  created:
    - data-service/rule_conflicts.py
    - data-service/tests/test_rule_conflicts.py
    - ui-v2/tests/rule-conflict-after-ingest.test.mjs
  modified:
    - data-service/app.py
    - data-service/route_policy.py
    - data-service/tests/test_route_inventory.py
    - data-service/tests/test_graph_routes.py
    - spec/SECURITY-BOUNDARY.md
    - spec/RULE-PARTITION-POLICY.md
    - ui-v2/src/lib/graphApi.js
    - ui-v2/src/screens/GraphScreen.jsx
    - ui-v2/src/i18n/dict/graph.js
key-decisions:
  - "Subject-in-set question resolved by the 2026-10-21 D-64 refinement: overlap is over context participants only (subject excluded); an empty set on either side overlaps."
  - "A rule may carry several keys (e.g. a range written as two builtins); a conflict needs one shared key."
  - "sharedClasses are class display names (label, else the IRI without its prefix), sorted; intersection is computed on IRIs."
  - "Only the exact decision 'cancel' leads to the delete dialog; an unknown or missing decision does nothing, so nothing is deleted without confirmation."
  - "With several cancelled rules from one ingest, the single shared delete dialog opens for the first; the others stay written and are named in a turn warning."
requirements-completed: []
requirements_partial: [DGOPN-06]
duration: ~2h
completed: 2026-10-22
status: complete
---

# Phase 1303 Plan 21: Conflict check on the written rule Summary

A rule is now compared with the project's active rules from its stored atoms (subject class, DatatypeProperty, comparator, context participant classes) after ingest, so Russian and English rules are checked the same way, every participant class counts, and Cancel removes the new rule only through the existing confirmed delete dialog.

## Performance

- Tasks: 3 of 3. Commits: `73a1a2d` (Task 1), `1225070` (Task 2), `38d5f53` (Task 3).
- Task 1: 15 tests in `tests/test_rule_conflicts.py`, all pass. The three D-64 examples are pinned: `{Slab, Column, Wall}` vs `{Slab, Column}` -> conflict with `sharedClasses [Column, Slab]`; `{Column}` vs `{Beam}` -> no conflict; one-class vs `{Slab, Column, Wall}` -> conflict with `sharedClasses []`. Also covered: different property, comparator or subject; the new rule never matches itself; no head -> `conflict=false`, reason `no-subject`; no subject ClassAtom -> reason `no-subject-class`; Russian labels; participant variable that also feeds a DataPropertyAtom is not context.
- Task 2: `tests/test_route_inventory.py` + `test_graph_routes.py` + `test_rule_conflicts.py` + `test_security_boundary_spec.py`: 1279 passed. Route pin 133 -> 134, SECURITY-BOUNDARY table row added in the same commit.
- Task 3: `npm --prefix ui-v2 test` 370/370 pass (7 new in `rule-conflict-after-ingest.test.mjs`; the source-shape test was RED before the GraphScreen change); `npm --prefix ui-v2 run build` succeeds.
- Full data-service suite: 6451 passed, 35 skipped, 8 deselected, 4 failed, 25 errors (see Baseline comparison).

## Accomplishments

- `rule_conflicts.py`: two read queries (new rule atoms; corpus atoms of active rules measuring one of the new rule's properties), both bound to `$project`, corpus excludes any rule with an outgoing `SUPERSEDED_BY`. Context-only variable logic mirrors `DG/src/DG.Core/Parsing/RuleVariableRoles.cs`. `currentValue` is the Literal lex of the comparator's position-2 argument.
- `GET /rules/{project}/{rule_id}/conflicts` answers `{ruleId, conflict, matches:[{ruleId, swrl, description, currentValue, sharedClasses}]}` (+ `reason` when the rule's key is unreadable); unknown rule -> 404 `RULE_NOT_FOUND`; route-policy row member/path/viewer; a non-member is refused before any read (tested).
- `RULE-PARTITION-POLICY.md` gained an "Update 1303-21" paragraph in the corpus-level conflict addendum; `POST /rules/check-conflict` and `dg_context.check_rule_conflict` are unchanged.
- Graph Viewer: `runIngestWithConflictCheck` runs `runTurn(0, ...)` first, then `fetchRuleConflicts` for each created Rule; the dialog shows the new Rule_Id, the matches and their shared classes; Replace/Update -> `supersedeRule(matches[0])`, Keep both -> `acceptRuleOverlap`, Cancel -> `openDeleteDialog(newRuleId)`. A failed conflict read adds a `checkFailed` turn warning and leaves the rule. The refused/failed provenance warnings are kept. RU strings added; the stale pre-write strings were replaced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The route-count pin lives in `test_route_inventory.py`, not `test_route_policy.py`**
- **Found during:** Task 2
- **Issue:** the plan names `data-service/tests/test_route_policy.py`, which does not exist; the pin (`len(ROUTE_POLICIES) == 133`) is in `tests/test_route_inventory.py`.
- **Fix:** updated the pin there (134) with the history comment. Added route tests to `tests/test_graph_routes.py` (named in the plan's verify command) instead.
- **Commit:** 1225070

**2. [Process] Task 1 tests were written after the implementation**
- The TDD RED commit for Task 1 was not made: `rule_conflicts.py` was written before its tests, then both were committed together (`73a1a2d`). The tests pass and pin the behavior; no separate RED run exists for Task 1. Tasks 2 and 3: the UI source-shape test was run RED before the GraphScreen edit; the route tests were added with the route.

None of the above changes scope.

## Baseline comparison

Failures after this plan, all outside plan-21 files and identical to the baseline recorded in 1303-20-SUMMARY / 1303-VALIDATION.md:
- `test_dg_context.py::TestContextEndpoints::test_post_assemble_returns_200_for_valid_type`, `::test_get_debug_matches_post_assemble_body`, `TestDeterminism::test_repeated_assemble_calls_are_byte_identical`, `::test_get_debug_and_post_assemble_are_equal_for_graph_query` (endpoint 500, baseline).
- 25 errors in `test_cg_structure_checks.py` and `test_computgraph_consult.py` integration classes: `Failed to DNS resolve address neo4j:7687` (baseline).
- The two `test_static_proxy_boundary.py` failures listed in 1303-20 no longer occur (plan 1303-18 allowed the `/data-service/scripts/` location in commit 2a61d07).
No new failure from plan-21 changes.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model: the new route is read-only, project-bound in both queries and goes through the single policy point; supersede keeps its `RULE_NOT_PUBLISHABLE` precondition; deletion only through the confirmed delete dialog.

## Open items

- Neither read query has run against a live Neo4j in this plan (fake-session tests only, as the plan specifies); the real-graph behavior (atom tagging, `collect` of arg maps) is for the live pass in plan 1303-23.
- `dg_context.check_rule_conflict` is now unused by the Graph Viewer; it stays for other callers.

## Self-Check: PASSED

Commits 73a1a2d, 1225070, 38d5f53 exist; all created files present.
