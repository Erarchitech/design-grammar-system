# Requirements: Design Grammar System v12.0 — Theory–Implementation Alignment

**Defined:** 2026-09-19  
**Status:** Active milestone package — ready to plan (activated 2026-09-19)  
**Core value:** Make the implementation's semantic, replay, identity, determinism, and security contracts explicit before v9.1/v10.0 consume them.

> v9.0 was closed by override closeout with accepted debt. Phase 40 retains historical live-UAT ownership and evidence; v11.0 retains publication/manuscript ownership. v12.0 Phase 1200 is not yet executed.

## Contract and evidence (Phase 1200)

- [x] **ALGN12-01**: Canonical statuses distinguish `passed`, `failed`, `unknown`, `not_evaluated`, `no_population`, `unsupported`, `indeterminate`, and `error`.
- [x] **ALGN12-02**: A common evidence envelope records project, definition, dgId/source representation, input/output hashes, schema/ontology/rule/shape versions, service/version, provider/model where applicable, timestamps, warnings, and status.
- [x] **ALGN12-03**: A frozen cross-service fixture contains all four atom types, two objects with mixed outcomes, a Design State, and a geometry reference.
- [ ] **ALGN12-04**: DE-01 compares Python, dg-reasoner, C#, and persisted replay against the same fixture; supported cases agree canonically and unsupported cases are typed rather than silently divergent.

> **Phase 1200 verification note (gap-closure, 2026-09-20):** ALGN12-02 and ALGN12-04 were reverted from `[x]` to `[ ]` by `1200-VERIFICATION.md` after code review found two blocking defects: `CanonicalJsonWriter.cs` dropped a decimal's stored scale where `canonical_json.py` preserved it (CR-01), and `report.py`'s `compare_legs` misclassified a single non-declarable status as declared rather than silent (CR-02). Plan **1200-06** fixed CR-01 — the C# leg now derives scale from `decimal.GetBits` and matches Python's `format(Decimal, "f")`, pinned by a recomputed golden vector with a genuine trailing-zero digest; both suites pass. **ALGN12-02 is re-closed on that evidence.** Plan **1200-07** fixed CR-02 — the guard now fires on any non-empty set of non-declarable statuses, with a named regression test and the previously-wrong test replaced; a second live instance of the same defect shape was found and fixed in the existing suite during this plan. Plan **1200-08** then executed DE-01's first genuine four-leg run (data-service, dg-reasoner, csharp, replay all `available: true`, against the corrected code, after rebuilding a stale `data-service` image that predated this phase's own changes). That run reported `silent_disagreement_count = 3`: dg-reasoner returned `no_population` (pySHACL `conforms=true` with zero findings — an empty target set, not a real evaluation) on all three golden objects, disagreeing with data-service/csharp/replay's real `passed`/`failed` verdicts on two of them. This is a genuine cross-leg disagreement the corrected classifier now correctly reports as `silent_disagreement` rather than absorbing it as declared — proving CR-02's fix works as intended — but it also means **ALGN12-04's own acceptance condition ("supported cases agree canonically") is not yet met**, so ALGN12-04 stays open. Additionally, `inputHash`/`outputHash` were `null` on every leg for every row in that run, so CR-01's fix could not be observed at the live service boundary (only at the unit-test level) — a second reason ALGN12-04 is not yet fully evidenced. **Finding routed to Phase 1201:** dg-reasoner's SHACL shapes are not targeting the seeded `DG-1200-GOLDEN` objects (`OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`) — this is separate from the pre-declared, by-design `ObjectPropertyAtom`/`SwrlRuleParser.ResolveAtomType` non-result (ALGN12-05), which behaved as expected in the same run. ALGN12-01 and ALGN12-03 remain genuinely satisfied; ALGN12-03's `fixture.json` contents were confirmed unchanged by plans 1200-06 and 1200-09 (only `canonical-vectors.json`, a sibling file, gained vectors under the freeze policy). **Plan 1200-09** then closed a further finding from the phase's own code review (`1200-REVIEW.md` WR-01): the CR-01 fix still lost the sign of a *negative-zero* decimal, because `decimal.ToString("F{scale}")` normalizes `-0.00m` to `"0.00"` while Python's `format(Decimal("-0.00"), "f")` yields `"-0.00"` — the same parity bug class as CR-01, for an input none of the then-existing golden vectors exercised. The C# leg now re-attaches the sign from `decimal.GetBits`' sign bit, guarded so ordinary negatives (which `ToString` already signs correctly) are not double-signed; two new golden vectors cover negative zero and an ordinary negative value (also closing review finding IN-01, that no vector exercised any negative value), `FIXTURE_VERSION` is bumped to 1.2.0, and the fix was proven to be detected by its own tests via a negative-control run. ALGN12-02's re-closure therefore now rests on decimal parity verified across non-negative, negative, and negative-zero inputs.

**Ownership split (D-15):** Phase 1200 owns the evidence envelope and status vocabulary *definition*, at `spec/EVIDENCE-CONTRACT.md`. v11.0 Phase 1105 owns *propagation* of that definition across the `CLAUDE.md` § Schema Change Propagation list (`cypher_template.txt`, `training/dataset_schema.json`, n8n workflow prompts, `ui-v2` config, `.github/copilot-instructions.md`, `README.md`, `ontology/dg-shapes.ttl`, `llm/structure_rules.json`). Coordinate, do not duplicate.

## Parser and evaluator conformance (Phase 1201)

- [x] **ALGN12-05**: ObjectPropertyAtom and malformed/unsupported syntax have explicit parser outcomes and regression fixtures.
- [x] **ALGN12-06**: Unsupported built-ins and predicate forms never collapse into ordinary failed verdicts.
- [x] **ALGN12-07**: Documentation and tests distinguish the schema-level SWRL subset from the bounded C# evaluator; no full-reasoner claim is made.

## Design State and verdict replay (Phase 1202)

- [x] **ALGN12-08**: Design State identity is explicitly classified as content-equivalence or capture-event identity.
- [ ] **ALGN12-09**: Publish → query → replay preserves the canonical state hash, membership manifest, schema version, and all normative members, or records explicit exclusions.
- [ ] **ALGN12-10**: Mixed per-object outcomes remain distinct through persistence and C# retrieval; no run-level aggregate is replicated across objects.
- [ ] **ALGN12-11**: Mutable operational/run status is separated from immutable snapshot identity and payload.

## Identity and rule–parameter bridge (Phase 1203)

- [ ] **ALGN12-12**: Grasshopper ObjState and core identity minting use one documented authority and migration policy.
- [ ] **ALGN12-13**: Platform identity conflict, detach, representation provenance, and shared-property authority are specified and tested.
- [ ] **ALGN12-14**: The `ATTRIBUTE_OF` versus `PARAM_LINK` decision is recorded; ontology, runtime, specifications, and manuscript ownership agree.

## Determinism and reproducibility (Phase 1204)

- [ ] **ALGN12-15**: Deterministic validator repeatability is measured separately from LLM proposal repeatability, abstention, and invalid-output behavior.
- [ ] **ALGN12-16**: Provider/model/prompt/configuration snapshots are sufficient to reproduce the declared AI experiment or explain why it is not reproducible.

## Security and tenancy (Phase 1205)

- [ ] **ALGN12-17**: Ordinary API and graph access enforce server-side user/tenant authorization rather than relying on client-side auth and project predicates.
- [ ] **ALGN12-18**: Direct Neo4j proxy exposure is removed or restricted behind an authorized server boundary.
- [ ] **ALGN12-19**: Compose/default credentials and secrets are hardened, rotated, and excluded from browser-readable runtime configuration.
- [ ] **ALGN12-20**: Unauthorized cross-project and direct-proxy access tests fail closed.

## Activation gates

- [ ] **GATE12-01**: Standalone GSD control-plane reconciliation (`GSD-ALIGN-001..013`) is complete before v12.0 planning/execution.
- [ ] **GATE12-02**: v12.0 Phases 1200–1203 are complete before v9.1 activation.
- [ ] **GATE12-03**: v12.0 Phases 1200–1204 plus v11.0 semantic-boundary/rule-ownership gate are complete before v10.0 activation.
- [ ] **GATE12-04**: Phase 40 retains ownership of live Rhino/LLM/Speckle UAT; v12.0 cannot mark those items passed.
- [ ] **GATE12-05**: Phase 1205 is release-blocking for external multi-user evaluation, but does not block local single-user feature development or the paper's bounded claims.

## Out of scope

- Manuscript edits and DOCX changes: v11.0 Phase 1107.
- V8 publication bundle synchronization: v11.0 Phases 1101–1109.
- Live Rhino/LLM/Speckle UAT: v9.0 Phase 40.
- Full RDF/OWL canonical migration: reconsider after DE-01/DE-02 evidence.
- Graphify regeneration and v4.0 BOT bridge.

## Traceability

| Requirement family | Phase | Count |
|---|---:|---:|
| ALGN12 contract/evidence | 1200 | 4 |
| ALGN12 parser/evaluator | 1201 | 3 |
| ALGN12 state/verdict replay | 1202 | 4 |
| ALGN12 identity/bridge | 1203 | 3 |
| ALGN12 determinism | 1204 | 2 |
| ALGN12 security/tenancy | 1205 | 4 |
| Gates | Cross-phase | 5 |
| **Total** | | **25** |
