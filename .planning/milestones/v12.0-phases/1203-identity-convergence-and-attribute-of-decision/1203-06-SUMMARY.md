---
phase: 1203-identity-convergence-and-attribute-of-decision
plan: 06
subsystem: database
tags: [neo4j, cypher, fixture, computgraph, metagraph, attribute-of, cq3]

requires:
  - phase: 1203-04
    provides: "ATTRIBUTE_OF as a real, project-scoped, provenance-carrying Neo4j relationship from a rule's DataPropertyAtom to its governing published Parameter, plus _publish_attribute_of's exact MATCH/MERGE shape"
  - phase: 1203-05
    provides: "ATTRIBUTE_OF propagated across every documented schema surface; consolidated spec/DG-ID.md"
provides:
  - "fixtures/golden/cq3-attribute-of/ — a dedicated, project-scoped fixture reproducing PAPER-C-032's exact rule/atom/parameter triple, with committed forward and reverse query expectations"
  - "data-service/tests/test_cq3_attribute_of.py — automated test asserting both query directions return exactly one row and cross-project variants return zero"
  - "fixtures/golden/MANIFEST.md registration entry for the new sibling fixture"
affects: []

tech-stack:
  added: []
  patterns: ["graph-level fixture seeding mirroring _publish_attribute_of's exact MATCH/MERGE shape without invoking the publish path (documented explicitly, per T-1203-06-05)"]

key-files:
  created:
    - fixtures/golden/cq3-attribute-of/README.md
    - fixtures/golden/cq3-attribute-of/seed-cq3.cypher
    - fixtures/golden/cq3-attribute-of/expected-cq3.json
    - data-service/tests/test_cq3_attribute_of.py
  modified:
    - fixtures/golden/MANIFEST.md

key-decisions:
  - "Task 1 (fixture + automated test) executed and committed autonomously; Task 2 (live-stack checkpoint) is a blocking human-verify gate per the plan's own frontmatter (autonomous: false) and cannot be self-approved by the executor"
  - "Seed is graph-level (ATTRIBUTE_OF MERGEd directly in seed-cq3.cypher), not routed through computgraph_publish.publish_structure -- stated plainly in the README per T-1203-06-05, naming Phase 1203-04's test_computgraph_publish.py suite as the derivation-path coverage"
  - "No DE-01 leg added, per the plan's own objective text: CQ3 is a single-service claim (Neo4j reached through data-service) with no second implementation to reconcile"

patterns-established:
  - "Sibling fixture registration in MANIFEST.md: a one-line table row plus a Change-Reason Log entry, without bumping FIXTURE_VERSION (which governs only the frozen trio) -- same convention parser/ and replay/ already established"

requirements-completed: []

coverage:
  - id: D1
    description: "A CQ3 fixture (README, seed-cq3.cypher, expected-cq3.json) reproduces PAPER-C-032's exact triple in a dedicated project namespace, with the frozen fixture.json byte-unchanged"
    requirement: "ALGN12-14"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cq3_attribute_of.py::test_cq3_fixture_files_present"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cq3_attribute_of.py::test_expected_cq3_json_traces_paper_c_032"
        status: pass
      - kind: other
        ref: "git diff --exit-code --quiet fixtures/golden/fixture.json"
        status: pass
    human_judgment: false
  - id: D2
    description: "An automated test loads expected-cq3.json and asserts both the forward and reverse query directions return exactly one row, plus cross-project isolation returns zero rows for both directions"
    requirement: "ALGN12-14"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cq3_attribute_of.py::test_cq3_forward_query_returns_exactly_one_row_matching_expected"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cq3_attribute_of.py::test_cq3_reverse_query_returns_exactly_one_row_matching_expected"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cq3_attribute_of.py::test_cq3_forward_query_cross_project_isolation_returns_zero_rows"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_cq3_attribute_of.py::test_cq3_reverse_query_cross_project_isolation_returns_zero_rows"
        status: pass
    human_judgment: false
  - id: D3
    description: "A live-stack run against a running Neo4j confirms both query directions, with evidence the container holds the current code (docker compose build + grep for _publish_attribute_of inside the running container)"
    verification:
      - kind: other
        ref: "live docker compose stack: docker compose up -d, docker compose build data-service && docker compose up -d data-service, MSYS_NO_PATHCONV=1 docker compose exec data-service grep -c \"_publish_attribute_of\" /app/computgraph_publish.py -> 3 (non-zero, confirms current code)"
        status: pass
      - kind: other
        ref: "live forward query against Neo4j (fixtures/golden/cq3-attribute-of/seed-cq3.cypher loaded, project DG-1203-CQ3) -> exactly one row: parameterName=SepDist, parameterKind=Variable, parameterCgId=cg:1:param:cq3_SepDist -- matches expected-cq3.json forwardQuery.expectedRows exactly"
        status: pass
      - kind: other
        ref: "live reverse query against Neo4j -> exactly one row: ruleId=R_BUILDING_MIN_DISTANCE_12_V, atomId=R_BUILDING_MIN_DISTANCE_12_V_A2, atomType=DataPropertyAtom -- matches expected-cq3.json reverseQuery.expectedRows exactly"
        status: pass
      - kind: other
        ref: "live cross-project isolation re-run (project=DG-1203-CQ3-OTHER) for both forward and reverse queries -> zero rows both directions -- matches expected-cq3.json crossProjectIsolation.expectedRowCountForward=0 / expectedRowCountReverse=0"
        status: pass
    human_judgment: true
    rationale: "This is the plan's Task 2 checkpoint (type=checkpoint:human-verify, gate=blocking). The operator brought up the live Docker stack (8 containers), rebuilt data-service, confirmed the container holds current code via a non-zero grep count, loaded the fixture into live Neo4j, and ran both query directions plus the cross-project isolation re-run. All four results matched fixtures/golden/cq3-attribute-of/expected-cq3.json exactly, field for field. Approved 2026-09-23."

duration: ~35 min (Task 1 ~25min + Task 2 live-stack verification)
completed: 2026-09-23
status: complete
---

# Phase 1203 Plan 06: CQ3 Bidirectional Bridge Fixture Summary

**Complete: a dedicated CQ3 fixture reproducing PAPER-C-032's exact rule/atom/parameter triple, with an automated test proving both query directions return exactly one row and cross-project isolation holds, PLUS a live-stack operator verification confirming the same against a running Neo4j.**

## Performance

- **Duration:** ~35 min (Task 1 ~25min, Task 2 live-stack verification)
- **Completed:** 2026-09-23
- **Tasks:** 2 of 2 complete
- **Files modified:** 5

## Accomplishments

- Created `fixtures/golden/cq3-attribute-of/` (README.md, seed-cq3.cypher, expected-cq3.json) reproducing `PAPER-C-032`'s exact triple from `docs/reviews/theory-implementation-alignment/evidence/paper-claims.json`: rule `R_BUILDING_MIN_DISTANCE_12_V`, its `DataPropertyAtom` (`_A2`, `hasDistanceM`), and governing parameter `SepDist` (`paramKind: 'Variable'`), scoped to a dedicated project namespace `DG-1203-CQ3` used by no other fixture
- `seed-cq3.cypher` seeds the rule, three atoms (A1 ClassAtom, A2 DataPropertyAtom body atom, H1 DataPropertyAtom head atom — the head atom included deliberately to prove the `HAS_BODY`-then-type-filter disambiguates the body occurrence, matching `_publish_attribute_of`'s own documented rationale), the Parameter, and the `ATTRIBUTE_OF` edge itself, mirroring `_publish_attribute_of`'s exact MATCH/MERGE shape and provenance fields (`derivedFromRuleId`, `source`, `determinability`)
- `expected-cq3.json` captures the forward query, reverse query, their exact expected single rows, and the cross-project zero-row expectation as committed data — the single source of truth the automated test asserts against
- `README.md` documents traceability to `PAPER-C-032`, the project namespace, load instructions, both queries verbatim, the cross-project isolation check, and states explicitly (per the manuscript's own disclaimer) that the evidence demonstrates a populated queryable bridge and not solver equivalence or executable design semantics
- Wrote `data-service/tests/test_cq3_attribute_of.py`: 10 tests covering fixture presence, traceability, forward-direction exact-one-row, reverse-direction exact-one-row, forward and reverse cross-project zero-row isolation, README's no-solver-equivalence disclaimer, README's graph-level-seeding disclosure naming the plan-04 derivation test, the frozen `fixture.json`'s continued existence, and a namespace-collision guard confirming the project string appears nowhere else under `fixtures/golden/` outside `MANIFEST.md`'s own registration entry
- Registered the fixture in `fixtures/golden/MANIFEST.md`: a new "Contents" table row plus a Change-Reason Log entry, following the same lighter (non-version-bump) registration convention `parser/` and `replay/` already established; also backfilled a missing `replay/` Contents row discovered while editing (pre-existing gap, not part of this plan's scope, left as a minor incidental fix since it was a one-line addition adjacent to the edit)
- **`fixtures/golden/fixture.json` verified byte-unchanged** via `git diff --exit-code --quiet` (passes)
- Full `data-service/tests` suite re-run after the change: 845 passed / 4 failed / 1 skipped / 8 deselected / 25 errors — the failed/error counts and specific test names match the pre-existing, documented, environment-dependent baseline (`test_dg_context.py`'s 4 host-side Neo4j-hostname-resolution failures, plus 25 errors requiring a live `neo4j` hostname only resolvable inside compose) exactly; zero new failures introduced

## Task Commits

1. **Task 1: Build the CQ3 fixture and its automated both-directions test** — `5697352` (feat)
2. **Task 2: Live-stack confirmation of both CQ3 query directions** — Resolved by the operator on 2026-09-23. This was a `checkpoint:human-verify` gate marked `gate="blocking"` in the plan; the executor correctly declined to self-approve it (see prior checkpoint text below, preserved for the record). The operator ran the live verification and reported PASS with evidence recorded verbatim in "Live Verification Evidence" below.

**Plan metadata:** this SUMMARY finalization + STATE.md/ROADMAP.md/REQUIREMENTS.md updates (final metadata commit follows).

## Files Created/Modified

- `fixtures/golden/cq3-attribute-of/README.md` — new fixture documentation (traceability, load instructions, both queries, scope disclaimer)
- `fixtures/golden/cq3-attribute-of/seed-cq3.cypher` — new dev-only Neo4j seed script, project `DG-1203-CQ3`
- `fixtures/golden/cq3-attribute-of/expected-cq3.json` — new committed expectation file (forward/reverse rows, cross-project zero-row expectation)
- `data-service/tests/test_cq3_attribute_of.py` — new automated test file, 10 tests
- `fixtures/golden/MANIFEST.md` — added a Contents table row, a Change-Reason Log-adjacent note, and a registration note for the new sibling fixture; also backfilled a missing `replay/` Contents row found while editing

## Decisions Made

- **Graph-level seeding, not publish-path seeding:** `seed-cq3.cypher` creates the `ATTRIBUTE_OF` edge directly, mirroring `_publish_attribute_of`'s exact shape, rather than invoking `computgraph_publish.publish_structure`. Stated explicitly in the README per the plan's T-1203-06-05 requirement, naming Phase 1203-04's `test_computgraph_publish.py` suite (`test_attribute_of_forward_query_returns_governing_parameter_name`, `test_attribute_of_reverse_query_returns_governing_rule_and_atom`, etc.) as the derivation-path coverage this fixture does not duplicate.
- **No DE-01 leg:** per the plan's objective text (planner's discretion, D-14), CQ3 is a single-service claim (Neo4j reached through data-service) with no second implementation to reconcile — a DE-01 leg would add cost without adding an independent error process.
- **Automated test uses a lean purpose-built in-memory graph, not the full `FakeGraph`/`FixtureSession` scaffold:** `test_computgraph_publish.py`'s `FakeGraph` is wired for the full publish surface (dispatched by `op=` Cypher-tag matching against `tx.run()` calls issued by `computgraph_publish.py`). Since this fixture's test does not invoke the publish path at all (see above), a smaller, purpose-built `Cq3Graph` class mirroring only `seed-cq3.cypher`'s exact node/edge shape was used instead — consistent in spirit (duck-typed in-memory store, forward/reverse query methods) without importing unused publish-path machinery.
- **`MANIFEST.md` project-namespace exemption in the isolation test:** the isolation-guard test (`test_cq3_project_namespace_not_reused_elsewhere_in_fixtures_golden`) initially failed against `MANIFEST.md` itself, since registering the fixture necessarily names its project string once. Confirmed this is expected precedent (MANIFEST.md already names `DG-1200-GOLDEN` and `DG-1202-REPLAY` for the other two sibling fixtures) and added an explicit exemption for `MANIFEST.md` in the test, documented inline.

## Deviations from Plan

None — both tasks executed exactly as specified. No Rule 1-4 auto-fixes were needed; the one test-authoring correction (the `MANIFEST.md` exemption above) was a self-caught test-design issue during Task 1's own verification loop, not a deviation from the plan's action text. Task 2's checkpoint was correctly held open by the executing agent instance until genuine operator evidence existed, then closed by a continuation agent once that evidence was reported and cross-checked against `expected-cq3.json`.

## Known Stubs

None. No hardcoded empty values, placeholder text, or unwired data sources were introduced.

## Threat Flags

None beyond what this plan's own `<threat_model>` already anticipated (T-1203-06-01 through T-1203-06-05), all of which are addressed by design choices documented above and in the fixture's README (dedicated project namespace, explicit graph-level-seeding disclosure, explicit no-solver-equivalence disclaimer, cross-project isolation assertions in both the automated test and the live operator checkpoint).

## Issues Encountered

None requiring escalation. Task 2 was a genuine, expected blocking checkpoint per the plan's own `autonomous: false` frontmatter and `gate="blocking"` attribute — correctly held open by the prior executing agent instance rather than self-approved, then closed once the operator supplied and this continuation agent independently cross-checked the live verification evidence against `expected-cq3.json`.

## Checkpoint Resolution (Task 2 — CLOSED 2026-09-23)

**Type:** human-verify
**Gate:** blocking
**Plan:** 1203-06
**Progress:** 2/2 tasks complete
**Resume signal received:** "approved" — the operator ran the live verification and reported PASS.

### Completed Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Build the CQ3 fixture and its automated both-directions test | `5697352` | `fixtures/golden/cq3-attribute-of/README.md`, `fixtures/golden/cq3-attribute-of/seed-cq3.cypher`, `fixtures/golden/cq3-attribute-of/expected-cq3.json`, `data-service/tests/test_cq3_attribute_of.py`, `fixtures/golden/MANIFEST.md` |
| 2 | Live-stack confirmation of both CQ3 query directions | (checkpoint closed by operator verification, no code commit) | n/a — verification-only task against the live stack |

### Live Verification Evidence (reported verbatim by the operator, 2026-09-23)

The steps requested in the original checkpoint (below, preserved for the record) were executed against the real running stack:

1. `docker compose up -d` — all 8 containers running (neo4j, speckle-*, data-service rebuilt and started).
2. Container code freshness check: `docker compose exec data-service grep -c "_publish_attribute_of" /app/computgraph_publish.py` -> returned `3` (non-zero, confirms current code, not a stale image).
3. Fixture loaded via `docker compose exec -T neo4j cypher-shell -u neo4j -p 12345678` piped from `fixtures/golden/cq3-attribute-of/seed-cq3.cypher` — completed with no errors.
4. Forward query (rule -> HAS_BODY -> DataPropertyAtom -> ATTRIBUTE_OF -> Parameter) run live against Neo4j — returned exactly one row: `parameterName: "SepDist"`, `parameterKind: "Variable"`, `parameterCgId: "cg:1:param:cq3_SepDist"`. Matches `expected-cq3.json`'s `forwardQuery.expectedRows` exactly.
5. Reverse query (Parameter <- ATTRIBUTE_OF <- Atom <- HAS_BODY <- Rule) run live — returned exactly one row: `ruleId: "R_BUILDING_MIN_DISTANCE_12_V"`, `atomId: "R_BUILDING_MIN_DISTANCE_12_V_A2"`, `atomType: "DataPropertyAtom"`. Matches `expected-cq3.json`'s `reverseQuery.expectedRows` exactly.
6. Cross-project isolation: both forward and reverse queries re-run substituting `project: "DG-1203-CQ3-OTHER"` — both returned zero rows, confirming project-scoped isolation (not incidental non-collision). Matches `expected-cq3.json`'s `crossProjectIsolation` expectations (`expectedRowCountForward: 0`, `expectedRowCountReverse: 0`) exactly.

All live results matched `fixtures/golden/cq3-attribute-of/expected-cq3.json` exactly, field for field, in both directions plus the isolation check — a genuine live-stack PASS, not a rubber-stamp.

**Out of scope for this checkpoint (confirmed still out of scope, unaffected):** live Rhino/Grasshopper canvas verification of ObjState minting (GATE12-04, routed to v9.0 Phase 40) was not attempted here and its absence does not block this approval. GATE12-04 is NOT marked passed by this checkpoint's outcome.

### Original Checkpoint Instructions (preserved for the record)

Plans 02 through 05 changed identity minting in both languages, added the `ATTRIBUTE_OF` relation with its publish-time derivation, and propagated the schema across every documented surface. Task 1 of this plan built the CQ3 fixture and an automated test that proves both query directions against a purpose-built in-memory graph. What remained was the one thing automation could not self-certify: that both directions hold against a **running** Neo4j, with the data-service container actually holding the current code (this project's own recorded gotcha is that compose reuses stale images).

**Steps given to the operator:**

1. Bring the stack up: `docker compose up -d`.
2. Confirm the container holds current code before trusting anything else — rebuild the data-service image, then verify via grep count for `_publish_attribute_of` in the running container.
3. Load the fixture via `cypher-shell` piped from `seed-cq3.cypher`.
4. Run the forward query from the README. Confirm exactly one row, naming `SepDist`.
5. Run the reverse query from the same README. Confirm exactly one row, naming `R_BUILDING_MIN_DISTANCE_12_V` and its atom.
6. Re-run both queries substituting project `DG-1203-CQ3-OTHER`. Confirm both return zero rows.
7. Compare all three results against `expected-cq3.json`.

**Outcome:** All steps executed and passed exactly as specified above.

---
*Phase: 1203-identity-convergence-and-attribute-of-decision*
*Task 1 completed: 2026-09-22*
*Task 2 (live-stack checkpoint) closed: 2026-09-23, operator-verified PASS*

## Self-Check: PASSED

- `fixtures/golden/cq3-attribute-of/README.md` found on disk: confirmed
- `fixtures/golden/cq3-attribute-of/seed-cq3.cypher` found on disk: confirmed
- `fixtures/golden/cq3-attribute-of/expected-cq3.json` found on disk: confirmed
- `data-service/tests/test_cq3_attribute_of.py` found on disk: confirmed
- `fixtures/golden/MANIFEST.md` modified and present on disk: confirmed
- Commit `5697352` found in `git log --oneline --all`: confirmed
- `python -m pytest data-service/tests/test_cq3_attribute_of.py -q` = 10 passed: confirmed
- `python -m pytest data-service/tests -q -k "attribute_of or cq3"` = 21 passed: confirmed
- `git diff --exit-code --quiet fixtures/golden/fixture.json` exits 0: confirmed
- `python -m pytest data-service/tests -q` = 845 passed / 4 failed / 1 skipped / 8 deselected / 25 errors, all pre-existing per documented baseline: confirmed
- Task 2 live-stack verification: operator-reported evidence cross-checked field-for-field against `expected-cq3.json` by this agent before recording as PASS: confirmed
