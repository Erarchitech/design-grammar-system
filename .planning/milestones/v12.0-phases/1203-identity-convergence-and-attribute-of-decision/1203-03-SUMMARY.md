---
phase: 1203-identity-convergence-and-attribute-of-decision
plan: 03
subsystem: api
tags: [identity, dgId, cypher, neo4j, fastapi, pydantic, cr-01, wr-01, wr-03]

# Dependency graph
requires:
  - phase: 1203-01
    provides: preflight test baseline + identity-literal inventory
  - phase: 1203-02
    provides: length-prefix hash-input encoding (_encode_hash_input) that compute_dg_id builds on
provides:
  - label-aware, graph-tagging mint_identity that coincides with the publish writers' anchor MERGE
  - ENTITY_KINDS allowlist (Object/Procedure/Pattern/Parameter/Interface) as the single source of truth for mintable Computgraph labels
  - MintRequest.entity_kind validated field threaded through /identity/mint
  - mint-then-bind-then-publish regression test proving CR-01 is closed
  - ALLOWED_PROPERTIES dead code removed from dg_context.py (WR-03)
affects: [1203-05 (spec/API.md and spec/DATABASE.md route documentation for /identity/mint's new entity_kind field), any future Computgraph publish-path work]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Label-then-parameterize: a Cypher label that must vary is validated against a module-level allowlist immediately before f-string interpolation into the query text, with every other value staying a bound parameter (Neo4j has no label parameter syntax)."
    - "Node-identity-keyed test fixture: FakeGraph gained an entities_by_key store keyed by (label, cgId, definitionId, project) so a regression test can prove 'one node' vs 'two nodes' structurally, not just infer coincidence from a shared dgId string."

key-files:
  created: []
  modified:
    - data-service/dg_identity.py
    - data-service/app.py
    - data-service/dg_context.py
    - data-service/tests/test_dg_identity.py

key-decisions:
  - "Took the explicit entity_kind argument route (per CONTEXT.md's Claude's-Discretion grant) rather than having mint_identity infer a label from cgId's string shape — resolution-by-guessing would reintroduce the implicit coupling this milestone exists to remove."
  - "ENTITY_KINDS = (Object, Procedure, Pattern, Parameter, Interface), confirmed directly against computgraph_publish.py's five publish writers (_publish_object/_publish_procedures/_publish_patterns/_publish_parameters/_publish_interfaces), each of which MERGEs on the identical labelled three-part key."
  - "mint_identity keeps its own entity_kind re-validation (raising DgIdentityError(DGID_INVALID_ENTITY_KIND)) in addition to MintRequest's pydantic field_validator, so direct callers of the function (not just the HTTP route) are protected."
  - "Left validate_cypher() untouched — its docstring already described only bracket-balance/label/relationship/kind-enum/key-naming/verb-policy checks, never claiming property-level validation, so no docstring correction was needed alongside the ALLOWED_PROPERTIES deletion."

patterns-established:
  - "Allowlist-then-interpolate for Cypher labels: guard immediately adjacent to the interpolation site, with an inline comment marking it as allowlist-constrained so a later reader doesn't mistake it for unvalidated interpolation."

requirements-completed: [ALGN12-13]

coverage:
  - id: D1
    description: "mint_identity's anchor MERGE is label-aware and coincides with the publish writers' anchor (CR-01 closed)"
    requirement: "ALGN12-13"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_identity.py#test_mint_then_publish_merge_coincides_on_one_node"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_dg_identity.py#test_mint_then_bind_then_publish_preserves_binding"
        status: pass
    human_judgment: false
  - id: D2
    description: "mint_identity tags minted nodes graph = 'Computgraph' (WR-01 closed)"
    requirement: "ALGN12-13"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_identity.py#test_mint_identity_tags_graph_computgraph"
        status: pass
    human_judgment: false
  - id: D3
    description: "Minting with an unrecognized entity_kind is rejected"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_identity.py#test_mint_identity_rejects_unknown_entity_kind"
        status: pass
    human_judgment: false
  - id: D4
    description: "Existing anti-misbinding guard (ambiguous-binding 409) is unaffected by the mint change"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_identity.py#test_ambiguous_bind_rejected"
        status: pass
    human_judgment: false
  - id: D5
    description: "ALLOWED_PROPERTIES dead constant removed with zero remaining references (WR-03 closed)"
    verification:
      - kind: other
        ref: "grep -rn 'ALLOWED_PROPERTIES' --include=*.py . (excluding .kilo/obj/bin) returns zero matches"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-22
status: complete
---

# Phase 1203 Plan 03: Label-Aware Mint + Dead-Code Removal Summary

**mint_identity now MERGEs on the same labelled (cgId, definitionId, project) key the publish writers use and tags Computgraph, closing CR-01/WR-01; ALLOWED_PROPERTIES deleted (WR-03).**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Closed CR-01: `mint_identity`'s anchor MERGE was label-less (`MERGE (e {cgId, definitionId, project})`) while every publish writer in `computgraph_publish.py` MERGEs on a labelled key. A pre-publish mint therefore created an orphan node distinct from the one the publish path later wrote, silently losing any bound representation. `mint_identity` now takes a validated `entity_kind` and MERGEs `(:<entity_kind> {cgId, definitionId, project})`, coinciding with the publish anchor.
- Closed WR-01: minted nodes now carry `graph = 'Computgraph'` in the same `SET` clause, matching every other Computgraph writer.
- Added `ENTITY_KINDS` (`Object`, `Procedure`, `Pattern`, `Parameter`, `Interface`) as a module-level allowlist in `dg_identity.py`, confirmed directly against `computgraph_publish.py`'s five publish writers before being fixed.
- `MintRequest.entity_kind` is a new pydantic-validated field (same `field_validator` pattern as `BindRepresentationRequest.platform`/`native_id_kind`), threaded through the single production caller (`/identity/mint` in `app.py`).
- Wrote the CR-01 regression proof: `test_mint_then_bind_then_publish_preserves_binding` mints, binds a native-id representation, runs a publish-shaped MERGE (same label/key as the real publish writers), and asserts the binding is still reachable. Verified by hand that this test fails against the pre-fix label-less `mint_identity` (two disjoint nodes, empty `reps` on the published node) — the fix makes them coincide on one node.
- Extended the test file's `FakeGraph` with a full node-identity store (`entities_by_key`, keyed by `(label, cgId, definitionId, project)`) so the regression can prove "one node" structurally rather than inferring it from a shared dgId string alone.
- Closed WR-03: deleted the dead `ALLOWED_PROPERTIES` constant from `dg_context.py` after confirming zero references anywhere in the repo (it was never consulted by `validate_cypher` or any other module).

## Task Commits

1. **Task 1: Make mint_identity label-aware and graph-tagging, with a mint-bind-publish coincidence regression** - `9b4fa04` (fix)
2. **Task 2: Delete the dead ALLOWED_PROPERTIES constant** - `e5727b4` (chore)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `data-service/dg_identity.py` - `ENTITY_KINDS` allowlist added; `MintRequest.entity_kind` validated field; `mint_identity` signature/anchor/docstring updated for label-awareness + graph tagging
- `data-service/app.py` - `/identity/mint` route threads `payload.entity_kind` into `mint_identity`
- `data-service/tests/test_dg_identity.py` - all 12 existing `mint_identity` call sites updated to pass `"Object"`; `FakeGraph` extended with a node-identity store; 4 new tests plus a `_publish_shaped_merge` test helper mirroring the real publish writers' Cypher
- `data-service/dg_context.py` - `ALLOWED_PROPERTIES` constant and its comment block deleted

## Decisions Made

- Took the explicit `entity_kind` argument route per CONTEXT.md's discretion grant, not label inference from `cgId` shape — inference would reintroduce implicit coupling this milestone removes.
- `ENTITY_KINDS` set confirmed against the five actual publish writers rather than assumed from schema docs alone.
- Kept `mint_identity`'s own entity-kind guard (raising `DgIdentityError(DGID_INVALID_ENTITY_KIND)`) as defense-in-depth alongside the pydantic validator, since the plan's behavior spec requires rejection at the function level, not only the HTTP boundary.
- No `validate_cypher` docstring change was needed — it never overstated property-level validation in the first place.

## Deviations from Plan

None - plan executed exactly as written. The `entity_kind` guard inside `mint_identity` (in addition to the pydantic-level validator) was explicitly called for by the plan's own behavior block ("Minting with an unrecognized entity kind must be rejected") and acceptance criteria (`ENTITY_KINDS` referenced at least 3 times: definition, validator, guard-before-interpolation), so this is plan-specified work, not a deviation.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `/identity/mint` now requires `entity_kind` in its request body — any external caller (e.g. a future Grasshopper connector or n8n workflow) issuing a pre-publish mint must supply one of `Object`/`Procedure`/`Pattern`/`Parameter`/`Interface`. Plan 05 (per the preflight's route-doc gap) should document this field on `spec/API.md`'s first-write for `/identity/*` routes.
- Full Python suite run: 835 passed, 4 failed, 1 skipped, 8 deselected, 25 errors — the 4 failures and 25 errors are byte-identical to the `1203-PREFLIGHT.md` documented environment-dependent set (`test_dg_context.py` Neo4j-hostname-from-host, `test_cg_structure_checks.py`/`test_computgraph_consult.py` Neo4j DNS at setup). No new failures. The passed-count delta above the 819 preflight baseline reflects tests added by sibling plans (1203-02, 1203-04) landed earlier in this session, plus this plan's own 4 new tests — not a regression.

## Self-Check: PASSED

- `data-service/dg_identity.py` — FOUND
- `data-service/app.py` — FOUND
- `data-service/dg_context.py` — FOUND
- `data-service/tests/test_dg_identity.py` — FOUND
- commit `9b4fa04` — FOUND
- commit `e5727b4` — FOUND

---
*Phase: 1203-identity-convergence-and-attribute-of-decision*
*Completed: 2026-09-22*
