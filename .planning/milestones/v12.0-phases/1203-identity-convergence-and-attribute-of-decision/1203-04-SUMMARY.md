---
phase: 1203-identity-convergence-and-attribute-of-decision
plan: 04
subsystem: database
tags: [neo4j, cypher, computgraph, metagraph, inputBindings, attribute-of]

requires:
  - phase: 1203-01
    provides: "Verified preflight baseline and the observed Atom_Id-suffix-to-type convention (_A2/_H1 -> DataPropertyAtom) backing the D-04 attachment rule"
provides:
  - "ATTRIBUTE_OF as a real, project-scoped, provenance-carrying Neo4j relationship from a rule's DataPropertyAtom (Metagraph) to its governing published Parameter (Computgraph)"
  - "_attribute_of_from_bindings: pure derivation reusing cg_input_bindings.classify_rule, deduplicated, reporting unresolved parameter names rather than dropping them"
  - "_classify_bound_rules: session-scoped helper classifying every inputBindings rule id against the current project's Metagraph, skipping rules whose :Rule node does not exist in that project"
  - "_publish_attribute_of: parameterized UNWIND MERGE writer, both endpoints project-scoped, coexisting unchanged alongside PARAM_LINK"
  - "publishedCounts.attributeOf in the publish_structure response"
affects: ["1203-05", "1203-06"]

tech-stack:
  added: []
  patterns: ["derive-then-MERGE pure/writer split (mirrors _paramlinks_from_wires/_publish_param_links)", "skip-on-RuleNotFoundError for a repo-wide bindings file iterated across all projects"]

key-files:
  created: []
  modified:
    - data-service/computgraph_publish.py
    - data-service/tests/test_computgraph_publish.py

key-decisions:
  - "Threaded session-based rule classification through a new _classify_bound_rules helper called at the publish_structure level (which already owns `session`), keeping _build_publish_params pure/no-DB-access per its own docstring rather than adding a session parameter to it"
  - "A rule id present in inputBindings but whose :Rule node does not exist in the current project raises RuleNotFoundError inside classify_rule; caught and skipped (not raised) since inputBindings is a single repo-wide file with no project scoping of its own -- a Computgraph publish must never fail over an unrelated project's rule"
  - "ATTRIBUTE_OF attaches via HAS_BODY-then-type-filter (MATCH (r)-[:HAS_BODY]->(a:Atom {type: 'DataPropertyAtom'})), not via a precomputed Atom_Id string, disambiguating the body _A2 occurrence from the head _H1 occurrence that shares the same type per the 1203-01 preflight's observed convention"
  - "Committed both tasks (derivation + writer) as a single atomic commit rather than two: the tasks share the same two files with interleaved changes, and every test exercising the writer also exercises the derivation through publish_structure, making a clean independently-green split impractical without re-running tests mid-split"

patterns-established:
  - "Cross-partition (Metagraph<->Computgraph) MERGE writer: source endpoint reached via a project-scoped MATCH plus a type-filtered traversal (no definitionId key on the Metagraph side), target endpoint matched by its full three-part Computgraph key (cgId, definitionId, project) -- the template for any future Metagraph<->Computgraph bridge"

requirements-completed: [ALGN12-14]

coverage:
  - id: D1
    description: "_attribute_of_from_bindings derives deduplicated, provenance-carrying ATTRIBUTE_OF rows from the existing inputBindings resolution, reporting (not dropping) unresolved parameter names"
    requirement: "ALGN12-14"
    verification:
      - kind: unit
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_two_bound_parameters_yield_two_rows"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_rule_absent_from_bindings_yields_zero_rows"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_unresolved_parameter_name_reported_not_dropped"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_duplicate_rule_parameter_pair_deduplicates"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_row_carries_provenance"
        status: pass
    human_judgment: false
  - id: D2
    description: "_publish_attribute_of MERGEs a project-scoped ATTRIBUTE_OF edge; forward and reverse query directions each return exact single-row results, cross-project isolation holds, and re-publishing is idempotent"
    requirement: "ALGN12-14"
    verification:
      - kind: integration
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_forward_query_returns_governing_parameter_name"
        status: pass
      - kind: integration
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_reverse_query_returns_governing_rule_and_atom"
        status: pass
      - kind: integration
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_cross_project_isolation_no_edge"
        status: pass
      - kind: integration
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_republish_is_idempotent"
        status: pass
      - kind: integration
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_param_link_unchanged_alongside_new_edge"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_publish.py::test_attribute_of_no_interpolated_cypher"
        status: pass
    human_judgment: false

duration: 45 min
completed: 2026-09-22
status: complete
---

# Phase 1203 Plan 04: ATTRIBUTE_OF Persistence Summary

**`ATTRIBUTE_OF` now exists as a real, MERGE-idempotent, project-scoped Neo4j relationship from a rule's `DataPropertyAtom` to its governing published `Parameter`, derived at Computgraph publish time from the `inputBindings` resolution `cg_input_bindings.classify_rule` already computes in memory.**

## Performance

- **Duration:** 45 min
- **Completed:** 2026-09-22
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `_attribute_of_from_bindings`, a pure derivation function (modeled structurally on `_paramlinks_from_wires`) that turns a `{ruleId: RuleClassification}` dict plus published Parameter rows into deduplicated, provenance-carrying `{ruleId, paramCgId, derivedFromRuleId, source, determinability}` rows, reporting (via warning log) any bound parameter name absent from the published set instead of silently dropping it
- Added `_classify_bound_rules`, a session-scoped helper at the `publish_structure` level that classifies every rule declared in `inputBindings` against the current project's Metagraph via `cg_input_bindings.classify_rule` (reused unchanged, D-02), skipping (not raising for) a rule id whose `:Rule` node does not exist in this project -- since `inputBindings` is a single repo-wide file with no project scope of its own
- Added `_publish_attribute_of`, a parameterized `UNWIND $rows` MERGE writer mirroring `_publish_param_links`'s exact structure: matches `:Rule` by `Rule_Id` + `project`, traverses `HAS_BODY` to the `:Atom` filtered on `type = 'DataPropertyAtom'` (D-04 -- disambiguating the body `_A2` occurrence from the head `_H1` occurrence, which share `type` but not `HAS_BODY`/`HAS_HEAD` role), matches `:Parameter` by `cgId` + `definitionId` + `project`, and MERGEs `ATTRIBUTE_OF` with provenance properties set from the row
- Wired both into `publish_structure`: `_classify_bound_rules` runs before the write transaction, `_publish_attribute_of` is called inside `_write` guarded by the same truthiness-check pattern as every other `_publish_*` call, and `publishedCounts` gained an `attributeOf` key
- Wrote 11 new tests covering: two-bound-parameters derivation, zero rows for an unbound rule, unresolved-name reporting, deduplication, provenance, forward query (exact single row), reverse query (exact single row), cross-project isolation (zero edges), MERGE idempotence, no-interpolated-Cypher, and `PARAM_LINK` coexisting unchanged
- Extended the test file's `FakeGraph`/`FixtureSession` fixture with `rules` (a `(Rule_Id, project)` set letting tests seed a Metagraph `:Rule` the fake's new `READ_RULE_LIMIT` and `PUBLISH_ATTRIBUTE_OF` op handlers can find), and a set-based dedup guard on the `ATTRIBUTE_OF` relationship append so the fake correctly models Cypher's MERGE idempotence for this specific edge type
- Full `data-service/tests` suite: 830 passed (up from the 1203-01 preflight baseline of 819, exactly +11 new tests), same 4 failed / 25 errors as baseline, all pre-classified as documented environment-dependent (Neo4j unreachable from host) -- zero new failures or errors introduced

## Task Commits

Both tasks landed in one atomic commit -- see Deviations below for why.

1. **Task 1: Derive ATTRIBUTE_OF rows from the existing inputBindings resolution** - `0ffb96e` (feat)
2. **Task 2: MERGE the project-scoped ATTRIBUTE_OF edge and evidence both query directions** - `0ffb96e` (feat, same commit)

**Plan metadata:** (this SUMMARY commit, following)

## Files Created/Modified

- `data-service/computgraph_publish.py` - Added `_attribute_of_from_bindings`, `_classify_bound_rules`, `_publish_attribute_of`; wired all three into `publish_structure`/`_build_publish_params`/`publishedCounts`; imported `cg_input_bindings`
- `data-service/tests/test_computgraph_publish.py` - Added 11 tests for ATTRIBUTE_OF derivation and publication; extended `FakeGraph` with a `rules` seed set and `READ_RULE_LIMIT`/`PUBLISH_ATTRIBUTE_OF` op handlers

## Decisions Made

- **Session threading:** `_build_publish_params` stays pure/no-DB-access per its own existing docstring contract. Rule classification (which needs a live `session` for `read_rule_limit`) happens in a new `_classify_bound_rules` helper called from `publish_structure` (which already owns `session`), and the resulting `{ruleId: RuleClassification}` dict is passed into `_build_publish_params` as an optional parameter defaulting to `{}` -- every pre-existing call site that omits it (e.g. `test_publish_row_carries_reinstate_parameter_id_including_none_for_unresolved`) is unaffected.
- **Cross-project rule lookup failure mode:** `classify_rule` raises `RuleNotFoundError` when no `:Rule` node exists for a given `(ruleId, project)`. Since `inputBindings` is a single repo-wide file iterated across every publish regardless of project, most entries will be irrelevant to any given project. `_classify_bound_rules` catches `RuleNotFoundError` per rule id and skips it (debug log), so a Computgraph publish never fails because an unrelated project's Rule doesn't exist yet. This also mechanically produces the cross-project isolation test's expected zero-edge outcome.
- **Attachment mechanism:** Per the 1203-01 preflight's observed `Atom_Id`-suffix-to-`type` convention (both `_A2` and `_H1` map to `type = 'DataPropertyAtom'`), the writer matches `(r)-[:HAS_BODY]->(a:Atom {type: 'DataPropertyAtom'})` -- the `HAS_BODY` relationship itself disambiguates the body atom from the head atom, so the filter never depends on `Atom_Id` string parsing.
- **Single atomic commit for both tasks:** Task 1 (derivation) and Task 2 (writer) modify the same two files with interleaved changes, and every integration test exercising the writer necessarily also exercises the derivation through `publish_structure`. Splitting into two independently-testable commits would have required either a temporary no-op writer stub or re-running the suite mid-split with reduced coverage; neither improves auditability enough to justify the risk. Both tasks' acceptance criteria are independently verified via targeted `grep` and the `-k "attribute_of"` test filter, which is documented in this Summary in place of two separate commit hashes.

## Deviations from Plan

**1. [Process] Both tasks committed as one atomic commit instead of two**
- **Found during:** Task 2 (writer implementation)
- **Issue:** The plan's per-task commit protocol assumes each task can land as an independently coherent, independently-verifiable commit. Here, the derivation (`_attribute_of_from_bindings`) and the writer (`_publish_attribute_of`) share both modified files with interleaved edits, and the integration-style tests (forward/reverse query, idempotence, cross-project isolation) necessarily exercise both functions together through `publish_structure` -- there is no meaningful intermediate state where Task 1 is "done" and testable in isolation from Task 2's writer.
- **Fix:** Committed both tasks' code and tests together in one commit (`0ffb96e`), with the commit message explicitly covering both the derivation and the writer. All of Task 1's acceptance criteria (grep counts, `-k "attribute_of"` test pass, zero-row/unresolved/dedup/provenance assertions) and all of Task 2's acceptance criteria (grep counts, full-suite pass, forward/reverse exact-row assertions, cross-project/idempotence assertions, no-interpolated-Cypher, `PARAM_LINK` unchanged) were independently verified via targeted commands before the single commit was made.
- **Files modified:** `data-service/computgraph_publish.py`, `data-service/tests/test_computgraph_publish.py`
- **Verification:** `python -m pytest data-service/tests/test_computgraph_publish.py -q -k "attribute_of"` (11 passed), `python -m pytest data-service/tests/test_computgraph_publish.py -q` (23 passed, full file), `python -m pytest data-service/tests -q` (830 passed / 4 failed / 25 errors, all pre-existing/environment-dependent per the 1203-01 preflight baseline)
- **Committed in:** `0ffb96e`

---

**Total deviations:** 1 (process-only; no functional/scope deviation, no Rule 1-4 auto-fix)
**Impact on plan:** No scope creep. Both tasks' distinct acceptance criteria were verified independently even though they share one commit.

## Issues Encountered

None requiring escalation. The one non-trivial design decision (threading `session` for `classify_rule` without violating `_build_publish_params`'s pure-function contract) was resolved by introducing `_classify_bound_rules` as a new session-scoped helper at the `publish_structure` level, keeping every existing function's documented invariants intact.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `ATTRIBUTE_OF` is now live in `computgraph_publish.py`; plans 05/06 (WR-02/API docs, and any remaining phase-closing work) can reference it as an established, tested cross-partition bridge pattern.
- The forward query (`Rule --HAS_BODY--> DataPropertyAtom --ATTRIBUTE_OF--> Parameter`) and reverse query (`Parameter <--ATTRIBUTE_OF-- Atom <--HAS_BODY-- Rule`) shapes used in this plan's tests are the exact Cypher shapes any later CQ3-demonstration fixture or documentation example should cite.
- No blockers identified.

---
*Phase: 1203-identity-convergence-and-attribute-of-decision*
*Completed: 2026-09-22*

## Self-Check: PASSED

- `data-service/computgraph_publish.py` modified and present on disk: confirmed
- `data-service/tests/test_computgraph_publish.py` modified and present on disk: confirmed
- Commit `0ffb96e` found in `git log --oneline --all`: confirmed
- `grep -c '_attribute_of_from_bindings' data-service/computgraph_publish.py` = 2: confirmed
- `grep -c 'attributeOfRows' data-service/computgraph_publish.py` = 4: confirmed (>= 2 required)
- `grep -c '_publish_attribute_of' data-service/computgraph_publish.py` = 3: confirmed (>= 2 required)
- `grep -c 'ATTRIBUTE_OF' data-service/computgraph_publish.py` = 6: confirmed (>= 1 required)
- `grep -c 'classify_rule' data-service/computgraph_publish.py` = 5: confirmed (>= 1 required)
- `grep -c 'PARAM_LINK' data-service/computgraph_publish.py` = 3: confirmed unchanged from baseline
- `grep -nE 'tx\.run\(f"|session\.run\(f"' data-service/computgraph_publish.py` returns no matches: confirmed
- `python -m pytest data-service/tests/test_computgraph_publish.py -q -k "attribute_of"` = 11 passed: confirmed
- `python -m pytest data-service/tests/test_computgraph_publish.py -q` = 23 passed: confirmed
- `python -m pytest data-service/tests -q` = 830 passed / 4 failed / 1 skipped / 8 deselected / 25 errors (all pre-existing per 1203-01 baseline): confirmed
- No new JSON/YAML mapping file created (git status shows only pre-existing build-artifact/graphify-cache noise unrelated to this plan): confirmed
