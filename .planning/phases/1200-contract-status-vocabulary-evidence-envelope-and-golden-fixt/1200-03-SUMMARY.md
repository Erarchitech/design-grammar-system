---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
plan: 03
subsystem: api
tags: [python, pydantic, jsonschema, canonical-json, sha-256, evidence-envelope, fastapi, neo4j]

# Dependency graph
requires:
  - phase: 1200-01
    provides: spec/EVIDENCE-CONTRACT.md (8-status vocabulary, D-06/D-07 canonicalization rules), spec/evidence-contract.schema.json ($defs.CanonicalStatus/EvidenceEnvelope/EvidenceRow)
  - phase: 1200-02
    provides: fixtures/golden/fixture.json (ALGN12-03 content), fixtures/golden/canonical-vectors.json (5 golden hash vectors), jsonschema>=4.20,<5 pinned in data-service/requirements.txt
provides:
  - data-service/canonical_json.py — hash_scalar_tuple (dgId-parity scalar hashing), canonicalize/hash_canonical (6-rule nested-payload canonicalization), CANONICALIZATION_VERSION
  - data-service/evidence_contract.py — CanonicalStatus (schema-pinned 8-member StrEnum), EvidenceRow/EvidenceEnvelope Pydantic models, load_contract_schema, build_envelope, validate_envelope, to_legacy_boolean
  - data-service/app.py additive evidenceEnvelopeJson sidecar — persist_evidence_envelope, parse_evidence_envelope, _build_publish_evidence_envelope, wired into POST /validation/publish and the view-assembly payload
  - Three new test modules asserting golden-vector parity, schema/vocabulary agreement, ALGN12-03 fixture shape, and the additive sidecar's degradation behavior
affects: [1200-04, 1200-05, 1201, 1202, 1203, 1204, 1205]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Explicit recursive-walk JSON canonicalization (no json.dumps delegation) so escaping/number rules stay exactly mirror-able in the C# leg (plan 1200-04)"
    - "Envelope roll-up status derived by explicit precedence tuple (error > failed > indeterminate > unsupported > unknown > not_evaluated > no_population > passed), never boolean arithmetic"
    - "Additive Neo4j sidecar write/read pair mirroring the shipped _persist_shacl_report/_parse_shacl_report shape exactly (parameterized MERGE/SET, degrade-to-None-never-raise reader)"

key-files:
  created:
    - data-service/canonical_json.py
    - data-service/evidence_contract.py
    - data-service/tests/test_canonical_json.py
    - data-service/tests/test_evidence_contract.py
    - data-service/tests/test_golden_fixture_shape.py
  modified:
    - data-service/app.py

key-decisions:
  - "canonicalize() rejects native float unconditionally (rule 2); the golden-vector test loads canonical-vectors.json with json.load(..., parse_float=Decimal) rather than accepting float, since JSON itself has no decimal type — this is the correct real-producer discipline, not a workaround"
  - "Envelope validation dumps with exclude_none=True: the schema's optional scalar fields are typed as bare 'string' (no null alternative), so Pydantic's default null-for-None dump was a real schema mismatch, fixed under Rule 1"
  - "_build_publish_evidence_envelope treats a rule id present in failedRuleIds/passedRuleIds as a genuine evaluated outcome (failed/passed respectively) since those lists already discriminate pass vs fail per rule; a rule id with no signal in either list emits UNKNOWN with an explanatory warning, per D-04's prohibition on inferring canonical status from an absent/collapsed boolean"

patterns-established:
  - "spec/evidence-contract.schema.json $defs.CanonicalStatus.enum remains the sole vocabulary authority — evidence_contract.CanonicalStatus is asserted equal to it by test, never a second hardcoded list"

requirements-completed: [ALGN12-01, ALGN12-02, ALGN12-03]

coverage:
  - id: D1
    description: "canonical_json.py implements all six D-07 canonicalization rules via explicit recursive walk (no json.dumps delegation) and hash_scalar_tuple reproduces the shipped dgId golden vector; test_canonical_json.py reproduces every fixtures/golden/canonical-vectors.json vector byte-exactly and digest-exactly"
    requirement: "ALGN12-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_canonical_json.py — 17 tests, ran directly via pytest, all pass"
      - kind: other
        ref: "grep -c 'json.dumps' data-service/canonical_json.py == 0 — ran directly, confirmed"
        status: pass
    human_judgment: false
  - id: D2
    description: "evidence_contract.py's CanonicalStatus StrEnum (8 members) is mechanically pinned to spec/evidence-contract.schema.json $defs.CanonicalStatus.enum; EvidenceEnvelope/EvidenceRow mirror the schema annex with additionalProperties:false; build_envelope sorts rows by (objectId, ruleId) and derives roll-up status by explicit precedence; validate_envelope enforces the schema via jsonschema.validate; to_legacy_boolean is the only canonical<->boolean direction (no boolean-to-canonical inference exists)"
    requirement: "ALGN12-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_evidence_contract.py — 22 tests, ran directly via pytest, all pass"
      - kind: other
        ref: "grep -c 'def .*bool.*-> CanonicalStatus\\|from_legacy\\|from_boolean' data-service/evidence_contract.py == 0 — ran directly, confirmed"
        status: pass
    human_judgment: false
  - id: D3
    description: "The golden fixture's ALGN12-03 content (four atom types, mixed-outcome objects, three-kind Design State, geometry reference, no_population row, ordering, and the ObjectPropertyAtom/Phase 1201 manifest disclosure) is asserted by an automated test, not just review"
    requirement: "ALGN12-03"
    verification:
      - kind: unit
        ref: "data-service/tests/test_golden_fixture_shape.py — 8 tests, ran directly via pytest, all pass"
    human_judgment: false
  - id: D4
    description: "app.py gains an additive evidenceEnvelopeJson sidecar write (persist_evidence_envelope) and never-raising read (parse_evidence_envelope) mirroring _persist_shacl_report/_parse_shacl_report exactly; the publish path builds and persists an envelope after store_validation_run without altering any existing ValidStatus/SendStatus/statePayloadJson/shaclReportJson write, and a build/validate/persist failure degrades quietly rather than breaking publish"
    verification:
      - kind: unit
        ref: "data-service/tests/test_evidence_contract.py TestPersistEvidenceEnvelope/TestParseEvidenceEnvelope/TestBuildPublishEvidenceEnvelope — 8 tests, ran directly via pytest, all pass"
      - kind: other
        ref: "full data-service suite: 789 passed / 4 failed (pre-existing, Neo4j-host-resolution-dependent) / 1 skipped / 8 deselected / 25 errors (pre-existing, same class) — ran directly, no regression vs the 760-passed baseline measured with only Task 1's files present"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-09-20
status: complete
---

# Phase 1200 Plan 03: Contract Python Implementation — Canonical JSON, Evidence Envelope, Additive Sidecar Summary

**Two new data-service modules (`canonical_json.py`, `evidence_contract.py`) implementing the frozen 8-status vocabulary, the 6-rule canonical-JSON hasher pinned to the shared golden vectors, and an additive `evidenceEnvelopeJson` Neo4j sidecar wired into the validation-publish path exactly like the shipped SHACL sidecar.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-20T07:43:00Z
- **Completed:** 2026-09-20T08:02:19Z
- **Tasks:** 3
- **Files modified:** 6 (5 created, 1 modified)

## Accomplishments
- `data-service/canonical_json.py`: `hash_scalar_tuple` reproduces the shipped `compute_dg_id`/`DgIdMintingService` dgId golden vector byte-for-byte; `canonicalize`/`hash_canonical` implement all six D-07 rules (Unicode code-point key ordering, `Decimal`-only fixed-point numbers with `float` rejected, minimal whitespace, NFC normalization, minimal escaping with non-ASCII left unescaped, and a hard NaN/Infinity prohibition) via an explicit recursive walk with zero `json.dumps` delegation
- `data-service/evidence_contract.py`: `CanonicalStatus` (8-member `StrEnum`) is mechanically pinned to `spec/evidence-contract.schema.json`'s enum by a set-equality test; `EvidenceEnvelope`/`EvidenceRow` Pydantic models mirror the schema annex field-for-field with `additionalProperties:false`; `build_envelope` sorts rows by `(objectId, ruleId)` and derives the envelope-level roll-up status by an explicit worst-case precedence tuple; `validate_envelope` runs `jsonschema.validate` against the schema annex; `to_legacy_boolean` is the sole canonical→boolean direction, with no boolean→canonical inference function anywhere in the module
- `data-service/tests/test_golden_fixture_shape.py`: mechanically asserts ALGN12-03 — exactly four atom types, mixed pass/fail outcomes, a three-kind Design State, a geometry reference, a `no_population` row, ascending `expectedOutcomes` ordering, and the `MANIFEST.md` disclosure of the by-design `ObjectPropertyAtom`/Phase 1201 non-result
- `data-service/app.py`: added `persist_evidence_envelope`/`parse_evidence_envelope`, copying `_persist_shacl_report`/`_parse_shacl_report`'s exact parameterized-MERGE / never-raise shapes; wired `evidenceEnvelope` into `build_view_payload` alongside `shaclReport`; the `/validation/publish` path now builds an envelope from `entity_dicts`' `failedRuleIds`/`passedRuleIds` (genuine `failed`/`passed` per rule id; `unknown` with an explanatory warning where neither list has a signal), validates it, and persists it in a try/except that degrades quietly on any failure — the existing `store_validation_run` write, `ValidStatus`, `SendStatus`, and `shaclReportJson` writes are all untouched

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement canonical_json.py and pin it to the shared golden vectors** - `5fc5920` (feat)
2. **Task 2: Implement evidence_contract.py — typed status, envelope models, schema validation** - `5394954` (feat)
3. **Task 3: Add the additive evidenceEnvelopeJson sidecar write and read to app.py** - `44cd61f` (feat), corrected by `b94afe8` (fix) — see Deviations

## Files Created/Modified
- `data-service/canonical_json.py` - canonicalization + scalar-tuple hashing helpers
- `data-service/evidence_contract.py` - typed status vocabulary, envelope models, schema validation
- `data-service/tests/test_canonical_json.py` - golden-vector parity tests
- `data-service/tests/test_evidence_contract.py` - vocabulary/envelope/sidecar tests
- `data-service/tests/test_golden_fixture_shape.py` - ALGN12-03 fixture-shape assertions
- `data-service/app.py` - additive `evidenceEnvelopeJson` sidecar write/read, publish-path wiring

## Decisions Made
- `canonicalize()` rejects native `float` unconditionally per the plan's explicit instruction; the golden-vector test loads `canonical-vectors.json` with `json.load(..., parse_float=Decimal)` since JSON's own number type has no decimal/float distinction — this is the discipline a real producer must follow, not a test-only workaround.
- `validate_envelope` dumps the envelope with `exclude_none=True`: the schema types optional scalar fields (`shapeVersion`, `dgId`, etc.) as bare `"string"` with no `null` alternative, so Pydantic's default null-for-`None` dump was a genuine schema mismatch (Rule 1 auto-fix), not a planned behavior.
- `_build_publish_evidence_envelope` treats `failedRuleIds`/`passedRuleIds` membership as a genuine evaluated outcome (these lists already discriminate pass vs. fail per rule id, unlike a single collapsed boolean); only a rule id present in neither list falls back to `UNKNOWN` with a warning, matching D-04's prohibition on inferring canonical status from an absent/collapsed boolean signal.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `validate_envelope` failed schema validation on its own optional-field default (`None`)**
- **Found during:** Task 2, writing `test_build_envelope_returns_valid_shape`
- **Issue:** `EvidenceEnvelope.model_dump(mode="json")` serializes unset optional fields (e.g. `shapeVersion`) as JSON `null`, but the schema types them as bare `"string"` with no `null` alternative — every envelope with any unset optional field failed `jsonschema.validate`.
- **Fix:** `validate_envelope` now dumps with `exclude_none=True`, dropping unset optional keys entirely (matching "absent," which the schema does allow) rather than emitting an explicit `null`.
- **Files modified:** `data-service/evidence_contract.py`
- **Verification:** `test_build_envelope_returns_valid_shape` and both schema-conflict tests pass.
- **Committed in:** `5394954` (Task 2 commit)

**2. [Rule 1 - Bug, self-caused] Task 3 commit accidentally included an unrelated pre-existing feature**
- **Found during:** Post-commit self-check after Task 3's `44cd61f`
- **Issue:** The working tree carried ~334 lines of a pre-existing, unrelated, uncommitted feature (a rule-ingest conflict check / supersession endpoint from a separate 2026-09-19 debug session — flagged in this plan's own `<wave_context>` as out-of-scope content to leave alone). I staged only my 7 intended hunks via `git apply --cached`, but then ran `git commit -m "..." -- data-service/app.py ...`; supplying a pathspec to `git commit` re-stages the *working-tree* version of that path before committing, silently discarding my careful partial-index staging and pulling in the full unrelated diff.
- **Fix:** Built a standalone patch of exactly the unwanted hunk (`git diff`, isolated by hunk header), reverse-applied it to remove it from the committed tree via a new commit (`b94afe8`, per the no-amend protocol), then forward-applied the same patch back onto the *working tree only* (not the index) to restore the unrelated feature to its original pre-existing, uncommitted state — matching how it was found before this plan started.
- **Files modified:** `data-service/app.py` (commit `b94afe8` removes the out-of-scope hunk from history; the working tree afterward carries it again, unstaged, unchanged from its original content)
- **Verification:** `git show HEAD:data-service/app.py | grep -c 'check_rule_conflict\|RuleConflictCheckPayload\|SUPERSEDED_BY'` returns `0` (absent from committed history); `grep -c` on the working-tree file returns `11` (present, uncommitted, matching its pre-plan state); `git status --short data-service/app.py` shows a single unstaged `M` for exactly that content; full data-service test suite re-run afterward shows 789 passed with no regression.
- **Committed in:** `b94afe8` (correction commit, immediately after `44cd61f`)

---

**Total deviations:** 2 auto-fixed (1 bug in the envelope validation dump, 1 self-caused commit-scope bug corrected immediately with a follow-up commit).
**Impact on plan:** The first fix was necessary for `validate_envelope` to work at all against the real schema. The second was a process error introduced and corrected within this same plan's execution, with no effect on any other phase's work — the unrelated feature's own uncommitted state is now byte-identical to what it was before this plan began, and this plan's own three task commits (`5fc5920`, `5394954`, `44cd61f`/`b94afe8`) contain only `1200-03`'s intended `files_modified` scope.

## Issues Encountered
- Docker Desktop's engine is unreachable in this execution environment (same environment gate disclosed in plan 1200-02's SUMMARY — `docker compose exec` cannot be used). All verification in this plan was run directly against host Python 3.14 (`pytest`, `jsonschema` 4.26, `pydantic` 2.12), which imports `data-service/app.py` cleanly and produces results consistent with the in-container baseline described in the plan (accounting for the pre-existing Neo4j-host-resolution-dependent failures/errors, unaffected by this plan's changes). A human with a running Docker Desktop should confirm the in-container `docker compose exec -T data-service pytest` invocations the plan's `<verify>` blocks specify, matching the same disclosed gap from 1200-02.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `data-service/canonical_json.py` and `data-service/evidence_contract.py` are committed and ready for plan 1200-04's C# mirror (`DG.Core.Contracts`) to cross-check against the same golden vectors.
- `data-service/app.py`'s additive `evidenceEnvelopeJson` sidecar is committed, wired into `/validation/publish`, and ready for plan 1200-05's DE-01 runner to read as the Python leg's evidence artifact.
- No blockers for continuing to 1200-04. A human with a running Docker Desktop should confirm the in-container `pytest` invocations before 1200-05's DE-01 runner is exercised live against the containerized `data-service` leg (same disclosed gap as 1200-02).

---
*Phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt*
*Completed: 2026-09-20*
