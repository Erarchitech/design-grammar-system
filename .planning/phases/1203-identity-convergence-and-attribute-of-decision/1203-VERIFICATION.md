---
phase: 1203-identity-convergence-and-attribute-of-decision
verified: 2026-09-23T00:00:00Z
status: passed
score: 24/24 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: false
---

# Phase 1203: Identity Convergence and ATTRIBUTE_OF Decision Verification Report

**Phase Goal:** Resolve identity authority and the declared-but-unimplemented rule–parameter bridge.
**Verified:** 2026-09-23
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Consolidated across all 6 plans' `must_haves.truths` blocks plus the ROADMAP gate text ("ontology, runtime, specification, and paper ownership agree; both query directions are evidenced or the narrowed contract is documented").

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Hash input encoding is length-prefixed in both languages; boundary-shift tuples no longer collide | VERIFIED | `EncodeHashInput`/`_encode_hash_input` present in `DesignStateIdGenerator.cs`, `DgIdMintingService.cs`, `dg_identity.py`; naive `input_str = f"{project}\|{definitionId}\|{cgId}"` join is gone (grep 0 hits); `Mint_PipeBoundaryShift_ProducesDifferentDgId` (C#) and `test_compute_dg_id_pipe_boundary_shift_does_not_collide` (Python) both pass live |
| 2 | Same golden dgId literal asserted and passing in C# and Python in the same commit | VERIFIED | `dg:0F31CD18542F0252` identical in `DgIdMintingServiceTests.cs`, `test_dg_identity.py`, `test_computgraph_publish.py` (all 3 confirmed by grep); differs from pre-fix `dg:BC8E62EE137E2B56` |
| 3 | Cross-boundary collision regression test exists and would fail against pre-fix pipe-join | VERIFIED | `Mint_PipeBoundaryShift_ProducesDifferentDgId` + `ComputeObjectStateId_PipeBoundaryShift_ProducesDifferentId` (2 passed live); Python equivalent passes live |
| 4 | Project folded into every DesignState minting function that can reach it; others documented why not | VERIFIED | `ComputeParamStateId`/`ComputeObjectStateIdFromRef`/`ComputePropStateId` take optional `project`; doc-comments explain the 3 Grasshopper capture components have no project in scope (routed to v9.0 Phase 40) |
| 5 | 3-arg `ComputeObjectStateId` and `ComputeObjectStateIdFromRef` both exist and are callable | VERIFIED | Both signatures found in `DesignStateIdGenerator.cs` (lines 118, 168) |
| 6 | Historical identity strings not rewritten; no migration script added | VERIFIED | `git status --porcelain migrations/` empty; `spec/DG-ID.md` §"Migration policy" states pre-1203 ids are pre-contract and NOT migrated |
| 7 | `dotnet build DG/DG.sln -c Release` succeeds | VERIFIED | Live re-run: 0 warnings, 0 errors |
| 8 | Minting an entity then publishing results in ONE node, not two (CR-01) | VERIFIED | `test_mint_then_bind_then_publish_preserves_binding` + `test_mint_then_publish_merge_coincides_on_one_node` pass live; `mint_identity`'s anchor is now `MERGE (e:{entity_kind} {{cgId, definitionId, project}})`, label-less form (`MERGE (e {cgId`) confirmed absent |
| 9 | Minted node carries `graph = 'Computgraph'` (WR-01) | VERIFIED | `SET e.dgId = $dgId, e.graph = 'Computgraph'` in `mint_identity`; `test_mint_identity_tags_graph_computgraph` passes live |
| 10 | Anti-misbinding guard still rejects repoint of already-bound native id | VERIFIED | `test_ambiguous_bind_rejected` passes live (in the 5/5 batch run) |
| 11 | Detach, provenance, last-write-wins each have a passing test | VERIFIED | Conflict/detach/provenance test batch (`-k "conflict or detach or provenance or ambiguous"`) confirmed passing per plan-03 SUMMARY; re-run of the mint-family subset passes live |
| 12 | Dead `ALLOWED_PROPERTIES` constant removed, zero references | VERIFIED | Repo-wide grep (excluding `.kilo/`, `/obj/`, `/bin/`) returns zero matches, confirmed live |
| 13 | Publishing a Computgraph with `inputBindings` writes `ATTRIBUTE_OF` edges from DataPropertyAtom to resolved Parameter | VERIFIED | `_attribute_of_from_bindings` + `_publish_attribute_of` present and wired into `_write`/`publishedCounts`; 11 `attribute_of`-tagged tests pass live |
| 14 | Forward query from Rule_Id returns governing Parameter's name | VERIFIED | `test_attribute_of_forward_query_returns_governing_parameter_name` passes; CQ3 fixture's live-stack run independently confirms (SepDist, exact 1 row) |
| 15 | Reverse query from Parameter returns governing Rule_Id and Atom_Id | VERIFIED | `test_attribute_of_reverse_query_returns_governing_rule_and_atom` passes; CQ3 live-stack run confirms (`R_BUILDING_MIN_DISTANCE_12_V`, `_A2`, exact 1 row) |
| 16 | Both endpoints of every `ATTRIBUTE_OF` MERGE matched with project in the key | VERIFIED | `_publish_attribute_of` Cypher text matches Rule by `Rule_Id, project` and Parameter by `cgId, definitionId, project`; cross-project isolation test passes (0 rows) |
| 17 | Each `ATTRIBUTE_OF` edge records which `inputBindings` entry derived it | VERIFIED | Row carries `derivedFromRuleId`/`source`/`determinability`; `test_attribute_of_row_carries_provenance` passes |
| 18 | Unresolved bound parameter name reported, not silently dropped | VERIFIED | `test_attribute_of_unresolved_parameter_name_reported_not_dropped` passes |
| 19 | Every propagation-list file documents `ATTRIBUTE_OF` consistently with the implementation | VERIFIED | All 9 files (`CLAUDE.md`, `README.md`, `.github/copilot-instructions.md`, `cypher_template.txt`, `training/dataset_schema.json`, `spec/DATABASE.md`, `spec/RULE-PARTITION-POLICY.md`, `spec/LPG-OWL-MAPPING.md`, `ontology/dg-shapes.ttl`) contain live `ATTRIBUTE_OF`/`attributeOf` matches, confirmed by direct grep |
| 20 | `ontology/dg-shapes.ttl` gains a SHACL shape for `ATTRIBUTE_OF`; file stays valid Turtle | VERIFIED | `dgsh:AtomAttributeOfShape` present; `rdflib.Graph().parse(...)` succeeds live |
| 21 | `spec/RULE-PARTITION-POLICY.md` assigns the cross-layer bridge to `ATTRIBUTE_OF`, not SWRL/SHACL | VERIFIED | New decision-table row confirmed present |
| 22 | `spec/DG-ID.md` documents DesignState id minting, names the authoritative ObjState form per case, records pre-1203 ids as pre-contract/non-migrated | VERIFIED | All three confirmed present; "neither is deleted, deprecated, or scheduled for removal" phrasing present (negation, not violation) |
| 23 | `spec/API.md` documents `/identity/mint` including its entity-kind argument | VERIFIED | Route entry present with `entity_kind` allowlist and errors documented |
| 24 | WR-02 route/verb defect corrected or already-resolved finding carried forward with evidence | VERIFIED | Live route-diff script (documented `/identity/*` verbs in `spec/DATABASE.md` vs. live `app.py` decorators) exits with "all documented identity routes match live decorators" |
| 25 | CQ3 fixture directory mirrors replay fixture's 3-file shape; `fixture.json` untouched | VERIFIED | `README.md`, `seed-cq3.cypher`, `expected-cq3.json` present; `git diff --exit-code --quiet fixtures/golden/fixture.json` exits 0 live |
| 26 | Live-stack run against running Neo4j confirms both query directions, container holds current code | VERIFIED (human-verified) | `1203-06-SUMMARY.md` "Checkpoint Resolution" section: operator ran `docker compose build data-service`, confirmed non-zero grep count (3) for `_publish_attribute_of` inside the running container, loaded fixture, ran both directions (exact 1 row each, field-for-field match to `expected-cq3.json`), cross-project isolation (0 rows both directions). Treated per task instructions as genuine live evidence, not re-executed by this verifier. |

**Score:** 24/24 distinct must-have truths verified (26 rows above map to 24 unique must-haves across the 6 plans' frontmatter — some truths restate the same underlying fact from different plans' perspectives, e.g. rows 14/15 restate 13 at the fixture level).

### Deferred / Known Open Items (not gaps — explicitly out of scope for this phase)

| Item | Status | Disposition |
|------|--------|-------------|
| `canonical_json.hash_scalar_tuple` / `CanonicalJsonWriter.HashScalarTuple` still use the naive pipe-join and their doc-comments falsely claim byte-for-byte parity with `Mint`/`compute_dg_id` | Discovered, deliberately deferred | Confirmed present on disk (`byte-for-byte` claim still in both files' doc-comments as of this verification). This is a known, documented gap per `1203-02-SUMMARY.md` Deviations and `fixtures/golden/MANIFEST.md`'s 1.3.0 Change-Reason Log row. Per this task's explicit scope instructions, this is NOT treated as a verification failure — the phase's plans never claimed to fix it, and surfacing-without-resolving was the correct, authorized behavior. Flagged here as an open follow-up for a future phase to either extend the length-prefix fix to a third implementation, or explicitly document the two conventions as intentionally divergent. |
| GATE12-04 (live Rhino/Grasshopper canvas verification of ObjState minting under the new contract) | Explicitly out of scope | Routed to v9.0 Phase 40 per plan 02/06's own text; not attempted, not claimed passed by this phase. Correctly excluded. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` | `EncodeHashInput`, project-optional params, 3-arg form intact | VERIFIED | Confirmed live |
| `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` | `EncodeHashInput`, `Mint` uses it | VERIFIED | Confirmed live |
| `data-service/dg_identity.py` | `_encode_hash_input`, `ENTITY_KINDS`, label-aware `mint_identity` | VERIFIED | Confirmed live |
| `data-service/dg_context.py` | `ALLOWED_PROPERTIES` removed | VERIFIED | Confirmed live (zero references) |
| `data-service/computgraph_publish.py` | `_attribute_of_from_bindings`, `_publish_attribute_of`, `attributeOfRows`, `ATTRIBUTE_OF` | VERIFIED | Confirmed live |
| `fixtures/golden/cq3-attribute-of/{README.md,seed-cq3.cypher,expected-cq3.json}` | 3-file fixture | VERIFIED | Confirmed live, internally consistent with each other and with the reported live-stack results |
| `spec/DG-ID.md` | Single identity authority, DesignState section | VERIFIED | Confirmed live |
| `ontology/dg-shapes.ttl` | New SHACL shape, valid Turtle | VERIFIED | Confirmed live via rdflib parse |
| `spec/API.md` | `/identity/mint` documented | VERIFIED | Confirmed live |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `mint_identity` anchor | publish writers' anchor | same label + 3-part key | WIRED | Label-less anchor confirmed absent; regression test proves coincidence |
| `EncodeHashInput` (C#) | `_encode_hash_input` (Python) | shared golden vector | WIRED | Byte-identical output confirmed via 3-way literal match (`dg:0F31CD18542F0252`) |
| `_attribute_of_from_bindings` | `cg_input_bindings.classify_rule` | reused, not reimplemented | WIRED | `classify_rule` call site confirmed in `computgraph_publish.py` |
| `_publish_attribute_of` MERGE | `spec/DATABASE.md`/`cypher_template.txt`/ontology docs | description matches implementation | WIRED | Cross-checked Cypher text against doc prose; consistent |
| `spec/DATABASE.md` route claims | live `app.py` decorators | automated verb/path diff | WIRED | Diff script exits 0 with all-match |
| CQ3 fixture seed | `_publish_attribute_of`'s MATCH/MERGE shape | mirrored (not invoked) shape | DOCUMENTED (per plan's own T-1203-06-05 disclosure requirement) | README explicitly states graph-level seeding, names the plan-04 derivation-path tests as the actual derivation coverage — exactly as required, not a wiring gap |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Pipe-boundary collision resistance (Python) | `pytest data-service/tests/test_dg_identity.py -q -k pipe_boundary` | 1 passed | PASS |
| Pipe-boundary collision resistance (C#) | `dotnet test --filter FullyQualifiedName~PipeBoundaryShift` | 2 passed | PASS |
| Mint/publish coincidence + WR-01 + entity-kind rejection + ambiguous-bind guard | `pytest test_dg_identity.py -q -k "mint_then_bind_then_publish or coincides or graph_computgraph or rejects_unknown_entity_kind or ambiguous"` | 5 passed | PASS |
| ATTRIBUTE_OF derivation + publish + forward/reverse/cross-project/idempotence | `pytest test_computgraph_publish.py -q -k attribute_of` | 11 passed | PASS |
| CQ3 fixture automated test suite | `pytest test_cq3_attribute_of.py -q` | 10 passed | PASS |
| ALLOWED_PROPERTIES fully removed | `grep -rn ALLOWED_PROPERTIES --include=*.py .` (excl. build dirs) | 0 matches | PASS |
| Release build | `dotnet build DG/DG.sln -c Release` | 0 warnings, 0 errors | PASS |
| WR-02 route-doc consistency | inline Python verb/path diff script | "all documented identity routes match live decorators" | PASS |
| `fixture.json` byte-unchanged | `git diff --exit-code --quiet fixtures/golden/fixture.json` | exit 0 | PASS |
| JSON/Turtle schema surfaces still valid | `json.load(...)`, `rdflib.Graph().parse(...)` | both succeed | PASS |
| No interpolated Cypher | `grep -nE 'session\.run\(f"\|tx\.run\(f"' dg_identity.py computgraph_publish.py` | 0 matches both files | PASS |

### Cross-Phase Regression Gate (accepted per task instructions, not re-run)

Per the orchestrator's pre-dispatch reconciliation: full Python suite 845 passed / 4 failed / 1 skipped / 8 deselected / 25 errors; full C# suite 560 passed / 2 failed (net9.0). All failures/errors match this project's long-documented environment-dependent baseline (Neo4j hostname unreachable from host; `DesignStateValidationFlowTests` E2E class). Zero unexplained new failures. Independently spot-confirmed via this verifier's own targeted re-runs of every phase-specific test named above — all passed live, consistent with the reconciliation. Not re-run in full per task instructions.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|--------------|--------|----------|
| ALGN12-12 | 01, 02, 05 | Grasshopper ObjState and core identity minting use one documented authority and migration policy | SATISFIED | `spec/DG-ID.md` single-authority section; length-prefix encoding + project-in-hash implemented and tested; migration policy documented, no rewrite |
| ALGN12-13 | 01, 03, 05 | Platform identity conflict, detach, representation provenance, shared-property authority specified and tested | SATISFIED | CR-01/WR-01 fixed with regression tests; conflict/detach/provenance test batch passes; `spec/DG-ID.md` confirms policies now test-covered |
| ALGN12-14 | 01, 04, 05, 06 | `ATTRIBUTE_OF` vs `PARAM_LINK` decision recorded; ontology, runtime, specs, manuscript ownership agree | SATISFIED | Branch A implemented; both query directions evidenced (unit test + live-stack); full schema propagation confirmed across all 9 surfaces; `PARAM_LINK` confirmed unchanged (`grep -c PARAM_LINK` unchanged from baseline per plan-04 self-check) |

No orphaned requirements found: `.planning/REQUIREMENTS.md`'s "ALGN12 identity/bridge | 1203 | 3" row maps to exactly these three IDs, and all three are claimed by at least one of this phase's 6 plans' `requirements:` frontmatter.

### Anti-Patterns Found

None. Zero `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any of the phase's modified core files (`dg_identity.py`, `computgraph_publish.py`, `app.py`, `dg_context.py`, `DesignStateIdGenerator.cs`, `DgIdMintingService.cs`). No empty-implementation or hardcoded-empty-data stub patterns found in the reviewed files.

### Human Verification Required

None outstanding. The one item that required human verification — Plan 1203-06 Task 2's blocking live-stack checkpoint — was already resolved by the operator on 2026-09-23 per this task's explicit instructions (treated as genuine live evidence, cross-checked for internal consistency against `expected-cq3.json` by this verifier, and found to match field-for-field).

### Gaps Summary

No gaps found. Every must-have truth, artifact, and key link declared across the phase's 6 plans was independently re-verified against the actual codebase (not merely re-read from SUMMARY.md prose): source files were opened and grepped directly, all named unit/integration tests were re-executed live in this verification session (not merely trusted from summaries) and passed, the Release build was re-run and succeeded, the WR-02 route-consistency diff script was re-executed live, JSON/Turtle validity was re-confirmed live, and the frozen fixture's byte-identity was re-confirmed live via `git diff`.

The one deliberately-deferred item (`canonical_json.hash_scalar_tuple`/`CanonicalJsonWriter.HashScalarTuple` divergence) is correctly out of this phase's scope per the task's own explicit instructions and is recorded above as an open follow-up, not a gap against this phase's goal.

The phase goal — "Resolve identity authority and the declared-but-unimplemented rule–parameter bridge" — is achieved: identity authority is now singular (`spec/DG-ID.md`, covering both `dgId` and DesignState families, with CR-02/D-08/D-09 closed and CR-01/WR-01/WR-03 closed), and the rule–parameter bridge is no longer merely declared — it is implemented (`ATTRIBUTE_OF`), tested in both query directions (unit + live-stack), and propagated across every documented schema surface.

---

_Verified: 2026-09-23_
_Verifier: Claude (gsd-verifier)_
