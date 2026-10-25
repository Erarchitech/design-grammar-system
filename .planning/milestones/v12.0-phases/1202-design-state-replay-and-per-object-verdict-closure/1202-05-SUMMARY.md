---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 05
subsystem: database
tags: [cypher, neo4j, python, evidence-envelope, immutability, rollup-precedence, spec-docs]

requires:
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 01)
    provides: RED pytest regression (test_validation_run_immutability.py) proving the publish path lacked an ON CREATE SET immutability split; IMMUTABLE_PROPERTIES/MUTABLE_PROPERTIES contract constants
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 02)
    provides: canonical DesignState projection definition and shared hash constant, referenced in the spec/DATABASE.md canonicalStateHash bullet
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 04)
    provides: IValidGraphRepository.GetPerObjectVerdictsAsync, the C# read surface spec/DATABASE.md now points at as canonical
provides:
  - ON CREATE SET / SET split in data-service/app.py's publish Cypher (D-15) -- re-publishing an existing runId no longer overwrites rulesJson/statePayloadJson/createdAt
  - evidence_contract.ROLLUP_PRECEDENCE public alias, imported by get_validation_entity_sets to replace the failed-wins dedup with the shipped error-first precedence (D-12)
  - spec/DATABASE.md immutable/mutable property declaration, formally-retired ValidStatus note, D-11 legacy-run declared exclusion, canonicalStateHash property bullet, two-layer identity MERGE amendment, D-06 geometry declared exclusion
  - spec/EVIDENCE-CONTRACT.md SS5.1 per-object verdict source subsection
affects: [1202-06, 1202-07]

tech-stack:
  added: []
  patterns:
    - "Cypher MERGE ... ON CREATE SET ... SET ... split for write-once snapshot identity vs. mutable operational/output state on one node, keyed by the same MERGE key"
    - "Precedence-driven rollup via a front-to-back walk of an imported ordered tuple (never max/min over enum ordinal, never boolean arithmetic) -- the same idiom evidence_contract.py's own _rollup_status already used"

key-files:
  created:
    - data-service/tests/test_validation_entity_rollup.py
  modified:
    - data-service/app.py
    - data-service/evidence_contract.py
    - data-service/tests/test_designstate_capture.py
    - spec/DATABASE.md
    - spec/EVIDENCE-CONTRACT.md

key-decisions:
  - "Task 1's classification matched plan 01's RED test assumptions exactly with zero test changes needed, including for the 8 Speckle publish-output properties (which the test only asserts must stay in the plain SET, which they already did) -- no assertion needed weakening."
  - "Re-pinned test_designstate_capture.py's STORE_VALIDATION_RUN_SHA256 source-hash guard in the same commit as Task 1's edit, per that test's own docstring instruction ('a deliberate, approved change -- re-pin the hash in the very same commit'). This file is outside the plan's declared files_modified list but the test exists specifically to force a conscious re-pin on any deliberate change to store_validation_run -- leaving it broken would be a self-inflicted regression, not an out-of-scope touch."
  - "Added evidence_contract.ROLLUP_PRECEDENCE as a public alias of the existing _ROLLUP_PRECEDENCE tuple (same object, not a copy) since only the underscore-prefixed name existed on disk -- per the plan's explicit instruction to add a public accessor rather than reach through the underscore from app.py."
  - "Task 2's new tests live in a new sibling file (data-service/tests/test_validation_entity_rollup.py) rather than being appended to test_validation_run_immutability.py -- that file's own docstring and Task 1's RED-test scope is the D-15 publish-path Cypher-shape/immutability regression, a distinct concern from D-12's rollup-precedence behavior change. Plan explicitly permits this naming choice."
  - "Unrecognized ValidationEntity.status strings map to CanonicalStatus.UNKNOWN (a real frozen-vocabulary member) and are logged via logging.getLogger(__name__).warning(...) inline, matching the file's existing no-module-level-logger convention (checked: app.py has zero module-level `logger =` assignments, only inline getLogger calls at 3 existing sites)."

patterns-established:
  - "Public alias for an underscore-prefixed shipped constant, added at its definition site rather than reached through from a consumer module -- keeps the single-source-of-truth property while giving cross-module consumers a name that isn't nominally private."

requirements-completed: [ALGN12-10, ALGN12-11]

coverage:
  - id: D1
    description: "The publish path writes rulesJson/statePayloadJson/createdAt under ON CREATE SET and status/ValidStatus/SendStatus (plus the 8 Speckle publish-output properties) under an unconditional SET, so re-publishing an existing runId no longer overwrites the immutable snapshot"
    requirement: "ALGN12-11"
    verification:
      - kind: unit
        ref: "data-service/tests/test_validation_run_immutability.py -q (4 passed, was 2 failed/2 passed before this plan)"
        status: pass
      - kind: unit
        ref: "data-service/tests -q (819 passed, 4 pre-existing host-env failures, 25 pre-existing Neo4j-integration errors -- documented baseline, no regression)"
        status: pass
    human_judgment: false
  - id: D2
    description: "get_validation_entity_sets rolls up ValidationEntity rows via the shipped evidence_contract.ROLLUP_PRECEDENCE walk, so error outranks failed (the real behavior change from the old failed-wins dedup); unrecognized statuses map to UNKNOWN and are logged rather than discarded; build_view_payload's {failed, passed} shape is unchanged"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "data-service/tests/test_validation_entity_rollup.py -q (8 passed, incl. test_error_outranks_failed_for_the_same_object and test_build_view_payload_shape_is_unchanged)"
        status: pass
      - kind: other
        ref: "grep -c seen_failed app.py == 0; grep -c ROLLUP_PRECEDENCE app.py == 2 (>=1); grep -v comment-lines | grep -c 'CanonicalStatus.ERROR,' == 0 (no second ordered literal)"
        status: pass
    human_judgment: false
  - id: D3
    description: "spec/DATABASE.md declares the :Run immutable/mutable property split with MERGE-key and D-15 no-node-split rationale, marks the ValidStatus index-matched contract formally retired in favor of GetPerObjectVerdictsAsync, states the D-11 not_evaluated declared exclusion for legacy runs, adds the canonicalStateHash property bullet, amends the DesignState MERGE note for D-01's two-layer identity, and states the D-06 geometry declared exclusion contrasted with ClassIri's normative inclusion -- all via scoped edits, not a rewrite"
    requirement: "ALGN12-11"
    verification:
      - kind: other
        ref: "grep -q 'ON CREATE SET' && grep -q canonicalStateHash && grep -q GetPerObjectVerdictsAsync && grep -qi not_evaluated spec/DATABASE.md => OK; git diff --numstat spec/DATABASE.md == 94 insertions / 1 deletion on a 674-line file"
        status: pass
    human_judgment: false
  - id: D4
    description: "spec/EVIDENCE-CONTRACT.md gains a scoped SS5.1 subsection naming the envelope rows as the canonical per-object verdict source and demoting Run.ValidStatus/:ValidationEntity to legacy, without touching the frozen status vocabulary, envelope field table, or canonicalization rules"
    requirement: "ALGN12-10"
    verification:
      - kind: other
        ref: "git diff spec/EVIDENCE-CONTRACT.md | grep '^-' | grep -c 'no_population|indeterminate|unsupported' == 0; git diff --numstat == 14 insertions / 0 deletions"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-09-22
status: complete
---

# Phase 1202 Plan 05: Snapshot/Run-Status Separation and Rollup Precedence Reconciliation Summary

**Split the ValidationRun publish MERGE into ON CREATE SET (immutable snapshot) / SET (mutable status and publish-output) so re-publishing a runId no longer overwrites the original snapshot, reconciled the Python per-object rollup to the shipped error-first precedence, and propagated both declarations plus the D-06/D-08/D-10/D-11 exclusions into spec/DATABASE.md and spec/EVIDENCE-CONTRACT.md.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-22 (session start, first Read)
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completed
- **Files modified:** 6 (5 modified, 1 created)

## Accomplishments

- Split `data-service/app.py`'s publish Cypher (`store_validation_run`) into a `MERGE` carrying an `ON CREATE SET` clause (`rulesJson`, `statePayloadJson`, `createdAt` — the write-once snapshot identity) and an unconditional `SET` clause (`status`, `ValidStatus`, `SendStatus`, plus the 8 Speckle publish-output properties, which legitimately change on every re-publish). Turned plan 01's RED regression (`test_validation_run_immutability.py`) fully GREEN (4/4 passing, up from 2 failed/2 passed) with **zero test assertion changes** — the classification matched the RED test's own encoded assumptions exactly, including for the Speckle properties.
- Re-pinned `test_designstate_capture.py`'s `STORE_VALIDATION_RUN_SHA256` source-hash guard in the same commit, exactly as that test's own docstring instructs for a deliberate, approved change to `store_validation_run`.
- Replaced `get_validation_entity_sets`' failed-wins dedup (where `error` lost to `failed`) with a precedence-driven rollup that groups `ValidationEntity` rows by `dgEntityId` and walks the shipped `evidence_contract.ROLLUP_PRECEDENCE` front-to-back, taking the first status present — `error` now correctly outranks `failed`. Added `evidence_contract.ROLLUP_PRECEDENCE` as a public alias of the existing `_ROLLUP_PRECEDENCE` tuple (same object) since only the underscore-prefixed name existed on disk. Unrecognized status strings map to `CanonicalStatus.UNKNOWN` and are logged at warning level rather than discarded. The `{"failed": [...], "passed": [...]}` return shape is preserved via `evidence_contract.to_legacy_boolean`, the sole sanctioned canonical→boolean direction.
- Added 8 new tests in a new sibling module `data-service/tests/test_validation_entity_rollup.py`, covering error-outranks-failed (the real behavior change), passed-only rollup, unrecognized-status participation (both the legacy-pair-adjacent case and a truly-foreign string), `build_view_payload`'s shape preservation, and the pre-existing missing-`dgEntityId` skip behavior.
- `spec/DATABASE.md` `:Run` section gained: an **Immutable vs mutable properties** subsection with the exact 3-way classification, MERGE key, and D-15 no-physical-split rationale; a **ValidStatus index-matched contract — formally retired** subsection naming `GetPerObjectVerdictsAsync` as the identity-addressed canonical read path; a **declared exclusion for legacy runs** (D-11) stating the `not_evaluated`-with-no-fallback rule and its accepted cost.
- `spec/DATABASE.md` `:DesignState` section gained: a new `canonicalStateHash` property bullet (64-char uppercase hex, queryable-not-identity-bearing, sibling `canonicalizationVersion`, no backfill); an amendment to the MERGE note recording D-01's two-layer identity (capture-event node key + content-hash property) and its consequence for recapture dedup; a **declared exclusion: geometry** (D-06) subsection contrasted with `ClassIri`'s normative inclusion (D-05).
- `spec/EVIDENCE-CONTRACT.md` gained a new SS5.1 **Canonical per-object verdict source** subsection (pure addition, 14 lines, 0 deletions) naming the envelope's rows canonical and `Run.ValidStatus`/`:ValidationEntity` legacy/non-authoritative, cross-referencing `spec/DATABASE.md` for storage placement — the frozen status vocabulary, envelope field table, and canonicalization rules are untouched (verified via `git diff` grep for removed vocabulary tokens: 0 hits).
- Walked `CLAUDE.md` § Schema Change Propagation (see dedicated section below) and confirmed every expected non-touch by direct inspection rather than by assumption — including a direct read of `ontology/dg-shapes.ttl`'s `RunStatusShape` (confirmed it only checks `sendStatus`/`validStatus` presence via `minCount`, with no immutability or hash-related constraint that this plan's changes would need to update).

## Task Commits

Each task was committed atomically:

1. **Task 1: Split the publish MERGE into ON CREATE SET (immutable) and SET (mutable) (D-15)** - `d32cc7d` (fix)
2. **Task 2: Reconcile the Python per-object rollup to the shipped precedence (D-12)** - `ac3115a` (fix)
3. **Task 3: Propagate the declarations into spec/DATABASE.md and spec/EVIDENCE-CONTRACT.md** - `03ecd9f` (docs)

_No plan-metadata commit created by this executor — orchestrator owns STATE.md/ROADMAP.md updates centrally for this wave per the sequential-mode contract._

## Files Created/Modified

- `data-service/app.py` - `store_validation_run`'s publish Cypher split into `ON CREATE SET`/`SET`; `get_validation_entity_sets` rewritten to a precedence-driven rollup importing `evidence_contract.ROLLUP_PRECEDENCE`.
- `data-service/evidence_contract.py` - Added `ROLLUP_PRECEDENCE` as a public alias of `_ROLLUP_PRECEDENCE`.
- `data-service/tests/test_designstate_capture.py` - Re-pinned `STORE_VALIDATION_RUN_SHA256` for the deliberate D-15 change, per the test's own re-pin instruction.
- `data-service/tests/test_validation_entity_rollup.py` - New: 8 tests for the D-12 rollup reconciliation.
- `spec/DATABASE.md` - New `:Run` immutable/mutable subsection, formally-retired `ValidStatus` note, D-11 declared exclusion; new `:DesignState` `canonicalStateHash` bullet, two-layer identity MERGE amendment, D-06 geometry declared exclusion.
- `spec/EVIDENCE-CONTRACT.md` - New SS5.1 canonical per-object verdict source subsection.

## Decisions Made

- Task 1's classification required zero changes to plan 01's RED test — the test's `IMMUTABLE_PROPERTIES`/`MUTABLE_PROPERTIES` constants and the plan's own classification agreed exactly on all 6 named properties, and the 8 Speckle properties (not asserted individually by the RED test, only implicitly via "the plain SET clause exists and carries the mutable set") landed correctly in the plain `SET` per the plan's explicit rationale.
- `test_designstate_capture.py`'s `STORE_VALIDATION_RUN_SHA256` re-pin: this file is not in the plan's declared `files_modified` list, but its own docstring explicitly names "a deliberate, approved change — re-pin the hash in the very same commit" as the correct response, and Task 1's edit is exactly that case. Treated as a Rule 3 (blocking) auto-fix: leaving the guard red would be a self-inflicted, avoidable regression in the exact style the guard test was written to catch and immediately resolve.
- `evidence_contract.ROLLUP_PRECEDENCE` added as a **public alias** (same tuple object) rather than renaming `_ROLLUP_PRECEDENCE` outright, to avoid touching any of that module's existing internal call sites (`_rollup_status`) that reference the underscore name — purely additive.
- Task 2's new tests placed in a new sibling file rather than appended to `test_validation_run_immutability.py`, per the plan's explicit "or a sibling module if that file's scope no longer fits — name the choice in the SUMMARY" allowance. `test_validation_run_immutability.py`'s own module docstring scopes it to the D-15 Cypher-shape/immutability regression; the D-12 rollup-precedence behavior change is a distinct concern.
- Unrecognized-status logging uses an inline `logging.getLogger(__name__).warning(...)` call rather than a module-level `logger` variable, matching the file's existing convention (checked: `app.py` has zero module-level `logger =` assignments; all 3 pre-existing logging call sites use inline `logging.getLogger(__name__)`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Re-pinned test_designstate_capture.py's STORE_VALIDATION_RUN_SHA256 guard**
- **Found during:** Task 1, immediately after editing the publish Cypher and running the full data-service baseline
- **Issue:** A pre-existing pinned-source-hash regression test (`test_store_validation_run_source_hash_is_pinned`) failed because `store_validation_run`'s source changed. The test's own docstring states this is expected for "a deliberate, approved change" and instructs re-pinning the hash in the same commit.
- **Fix:** Computed the new SHA-256 over `inspect.getsource(app.store_validation_run)` and updated the `STORE_VALIDATION_RUN_SHA256` constant, with a comment explaining the D-15 change that triggered the re-pin.
- **Files modified:** `data-service/tests/test_designstate_capture.py`
- **Verification:** `python -m pytest data-service/tests/test_designstate_capture.py -q` — 22/22 passed.
- **Committed in:** `d32cc7d` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking, self-resolving per the test's own instructions)
**Impact on plan:** No scope creep — the re-pin is the exact response the pre-existing guard test's docstring prescribes for this plan's own Task 1 change, not an unrelated fix.

## CLAUDE.md SS Schema Change Propagation walk

Walked every surface named in `CLAUDE.md`'s "Schema Change Propagation" section against this plan's actual changes (a sidecar scalar property `canonicalStateHash`, a Cypher clause split, a Python rollup fix, and additive spec prose — no new node label, relationship type, or LLM-visible schema member):

| Surface | Touched? | Reason |
|---|---|---|
| `cypher_template.txt` | No | No new node label, relationship, or LLM-prompt-visible schema member is introduced. `canonicalStateHash` is a sidecar scalar on an existing `:DesignState` node, following the exact precedent of `shaclReportJson`/`evidenceEnvelopeJson` before it — neither of which required a `cypher_template.txt` change either. |
| `training/dataset_schema.json` | No | Same reasoning — no schema-visible-to-the-LLM-training-pipeline member added. |
| n8n workflow prompts (`rules-to-metagraph.json`, `graph-query-mcp.json`) | No | Neither workflow's prompt vocabulary references `:Run` property names or `:DesignState` sidecar properties; this plan adds none that would need prompt-level exposure. |
| `config.template.js` | No | No new UI-configurable schema surface. |
| `data-service/app.py` Cypher | **Yes** | This is the plan's own direct target (Task 1/2) — already the primary change, not a propagation follow-on. |
| `.github/copilot-instructions.md` | No | No structural schema change of the kind this file documents (it mirrors `CLAUDE.md`'s architecture summary, not per-property detail). |
| `README.md` | No | Same reasoning. |
| `spec/DATABASE.md` | **Yes** | This plan's own Task 3 target. |
| `ontology/dg-shapes.ttl` | No — verified by direct inspection, not assumption | Read `RunStatusShape`/`RunStatusShape_send`/`RunStatusShape_valid` directly: they only assert `sh:minCount 1` (and `sh:datatype xsd:boolean` for `sendStatus`) on the existing `sendStatus`/`validStatus` predicates. Immutability is enforced by Cypher `ON CREATE SET`, not a SHACL constraint, and `canonicalStateHash` is optional/queryable-not-identity-bearing, so no `minCount`/cardinality shape is appropriate for it. No structural or data-integrity constraint in this file needs updating. |
| `llm/structure_rules.json` | No | Carries Computgraph `inputBindings`/`mappings`, unrelated to `:Run`/`:DesignState` — this plan touches neither Computgraph entity shape. |
| `spec/EVIDENCE-CONTRACT.md` | **Yes** | This plan's own Task 3 target — a scoped addition (SS5.1), not a redefinition of the frozen vocabulary/envelope/canonicalization rules Phase 1200 owns. |
| `spec/SWRL-SUBSET.md` | No | No parser, builtin, or evaluator-subset change — this plan touches persistence and a Python rollup, not SWRL parsing/evaluation. |

All expected non-touches were confirmed correct on inspection; none required an edit.

## Issues Encountered

None beyond the self-resolving source-hash re-pin documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ALGN12-11 is satisfied: mutable operational/publish-output status is separated from immutable snapshot identity via `ON CREATE SET`, with the classification declared in `spec/DATABASE.md`. No physical `:StateSnapshot`/`:Run` node split, no migration — the split remains available to a later phase per D-15.
- ALGN12-10's Python half is reconciled to the shipped `ROLLUP_PRECEDENCE`; combined with plan 04's C# `GetPerObjectVerdictsAsync`, both languages now agree on precedence (error outranks failed) even though the C# envelope read remains the canonical source per D-10.
- Every declared exclusion this plan states (geometry D-06, legacy-run `not_evaluated` D-11, no physical node split, no backfill) is now written into `spec/DATABASE.md`/`spec/EVIDENCE-CONTRACT.md` rather than left implicit — satisfying the phase's "or every excluded member is formally documented" gate language for this plan's scope.
- Plan 06 can proceed to live-container verification (the `--no-cache` rebuild this plan's own `<verification>` section explicitly deferred) — `data-service` must be rebuilt (not merely restarted) before any live confirmation, since it has no source volume mount and would otherwise validate pre-change code.
- No blocker for sibling wave-1 plan 1202-06 (touches `DesignStateIdGenerator.cs` additively, `ObjectStateComponent.cs`, `ObjStateModelTests.cs` — zero file overlap confirmed against this plan's actual touched-file list).

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Completed: 2026-09-22*

## Self-Check: PASSED

All created/modified files verified present on disk:
- FOUND: data-service/app.py (modified)
- FOUND: data-service/evidence_contract.py (modified)
- FOUND: data-service/tests/test_designstate_capture.py (modified)
- FOUND: data-service/tests/test_validation_entity_rollup.py (created)
- FOUND: spec/DATABASE.md (modified)
- FOUND: spec/EVIDENCE-CONTRACT.md (modified)

All 3 commit hashes verified in git log: d32cc7d, ac3115a, 03ecd9f.
