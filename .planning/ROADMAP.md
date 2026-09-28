# Roadmap: Design Grammar System v12.0 — Theory–Implementation Alignment

**Planned:** 2026-09-19  
**Status:** Active package (activated 2026-09-19 after v9.0 override closeout)  
**Phase numbering:** `1200–1205`, following the repository `vX.Y → X·100+Y·10` convention.  
**Depends on:** the v9.0 Phase 40 closeout ledger and the standalone GSD control-plane reconciliation; it does not absorb Phase 40's live UAT or v11.0's publication/manuscript work.

> **Activation contract:** v12.0 is now the active milestone package. `.planning/phases/` is empty and ready for the first active phase; `.planning/STATE.md`, `.planning/PROJECT.md`, and active `.planning/REQUIREMENTS.md` now point to v12.0. The standalone control-plane reconciliation must complete before Phase 1200 planning/execution.

## Purpose and sequencing decision

v12.0 closes theory–implementation gaps that are not owned by v9.0 Phase 40 or v11.0. It is not a second publication milestone and not a replacement for v11.0.

**Early prerequisite rule:** before v9.1 or v10.0 is activated, the shared contract foundation must be complete:

1. standalone reconciliation of `GSD-ALIGN-001..013` items classified `auto`;
2. v9.0 Phase 40's live UAT and narrow V8 preflight remain owned by Phase 40;
3. v12.0 Phases 1200–1203 complete: canonical evidence/status contract, parser/status semantics, replay/per-object verdict contract, and identity/`ATTRIBUTE_OF` decision;
4. v11.0 1105/1106 and the v9.1/v10.0 activation gates consume those decisions without duplicating ownership.

v12.0 Phase 1204 is required before v10.0 activation if v10.0's deterministic/LLM reproducibility claims depend on it. Phase 1205 is a release gate for external multi-user evaluation, not a blocker for the paper or local single-user feature work.

## Cross-milestone ownership

| Concern | Owner |
|---|---|
| v9.0 live Rhino/LLM/Speckle UAT and Phase 40 closeout | v9.0 Phase 40 |
| v9.0 control-plane drift (`GSD-ALIGN-001..013`) | Standalone reconciliation pass before v12 planning |
| Publication bundle, V8 contract, manuscript, dissemination | v11.0 Phases 1101–1109 |
| Theory–implementation contract gaps and security gate | v12.0 Phases 1200–1205 |
| DG chatbot product capability | v9.1 Phases 910–917, after the shared-contract gate |
| Script Intelligence capability | v10.0 Phases 41–49, after the semantic-boundary gate |
| Full RDF/OWL canonical migration | Not scheduled; reconsider only after DE-01/DE-02 |

## Phases

### Phase 1200: Contract, Status Vocabulary, Evidence Envelope, and Golden Fixture

**Goal:** Freeze the common evidence and outcome contract before downstream milestones consume it.

**Packages:** `ALIGN-P01`, `ALIGN-P02`, `ALIGN-P04`  
**Requires:** standalone auto-class GSD reconciliation; read-only Phase 40/v11 ownership records.  
**Blocks:** v9.1 activation; v10.0 activation; phases 1201–1205.

**Deliverables:**

- canonical statuses: `passed`, `failed`, `unknown`, `not_evaluated`, `no_population`, `unsupported`, `indeterminate`, `error`;
- evidence envelope with project/definition/dgId, source representation, input/output hashes, contract versions, service/version, provider/model where applicable, timestamps, warnings, and status;
- one frozen cross-service fixture containing all four atom types, two objects with mixed outcomes, a Design State, and geometry reference;
- DE-01 runner contract, with silent disagreement treated as failure and typed non-equivalence accepted for unsupported cases;
- v11.0 1105 handoff specification, without duplicating its schema-propagation work.

**Gate:** status and evidence semantics are accepted by the owner; fixture is committed in the future milestone package; no downstream gate treats legacy booleans as authoritative.

**Plans:** 9/9 plans executed — 3 gap-closure plans added after `1200-VERIFICATION.md` returned `gaps_found` (06/07/08), plus a 4th (09) after `1200-REVIEW.md` found WR-01

Plans:
**Wave 1**

- [x] 1200-01-PLAN.md — Publish `spec/EVIDENCE-CONTRACT.md` + JSON Schema annex; bounded propagation (wave 1)
- [x] 1200-02-PLAN.md — Frozen golden fixture, Neo4j seed, manifest, canonical golden vectors, fixture reachability (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 1200-03-PLAN.md — Python leg: canonical JSON, typed status + envelope models, additive sidecar persistence (wave 2)
- [x] 1200-04-PLAN.md — C# leg: `EvidenceStatus`, `CanonicalJsonWriter`, envelope DTO, cross-language hash parity (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 1200-05-PLAN.md — DE-01 runner across four legs, dual-format report, owner acceptance gate (wave 3)

**Wave 4** *(gap closure — blocked on Wave 3 completion; 06 and 07 are independent of each other)*

- [x] 1200-06-PLAN.md — GAP-1/CR-01: preserve decimal scale in `CanonicalJsonWriter`, add trailing-zero golden vector, state the rule in §6 (wave 4)
- [x] 1200-07-PLAN.md — GAP-2/CR-02: fire `compare_legs`' non-declarable guard on any non-empty set; replace the test that certified the defect (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 1200-08-PLAN.md — GAP-3: live four-leg DE-01 run (human, Docker required), REQUIREMENTS.md reconciliation, owner re-confirmation (wave 5)

**Wave 6** *(gap closure — blocked on Wave 4 completion; raised by `1200-REVIEW.md` WR-01)*

- [x] 1200-09-PLAN.md — WR-01/IN-01: preserve negative-zero sign in `CanonicalJsonWriter`, add negative-zero and ordinary-negative golden vectors (wave 6)

### Phase 1201: Rule Parser and Evaluator Conformance

**Goal:** Make the implemented C# rule subset explicit and safe.

**Package:** `ALIGN-P03`  
**Requires:** 1200.  
**Blocks:** v9.1 activation only where shared parser/status surfaces are consumed; v10.0 semantic-boundary gate.

**Deliverables:**

- typed parser fixtures for ObjectPropertyAtom, malformed arity, quoted commas, escaping, duplicate arrows, datatype/language literals, and unsupported syntax;
- explicit unsupported/indeterminate outcomes for unsupported built-ins and predicate forms;
- documented distinction between schema-level SWRL atom types and the bounded C# evaluator subset;
- no claim that the C# path is a general SWRL/OWL reasoner.

**Gate:** supported fixtures pass; unsupported fixtures return typed non-verdict outcomes; no unsupported construct becomes an ordinary failure.

**Plans:** 6/6 plans executed

Plans:

- [x] 1201-01-PLAN.md — Tracer slice: single rollup precedence extracted, D-15 builtin allow-list, additive `Status`, unsupported builtin returns `unsupported` instead of throwing (wave 1)
- [x] 1201-02-PLAN.md — Remaining evaluator collapse sites: `no_population`, `unknown`, ObjectPropertyAtom refusal, `not_evaluated` at the publish boundary (wave 2)
- [x] 1201-03-PLAN.md — Parser `TryParse` with resolver-driven atom typing, quoted commas/escaping/datatype/language literals, Neo4j predicate-kind resolver (wave 3)
- [x] 1201-04-PLAN.md — Parser conformance corpus, `spec/SWRL-SUBSET.md` with non-claims section, doc↔code drift guard, propagation (wave 4)
- [x] 1201-05-PLAN.md — dg-reasoner leg `run_id` fix, `not_evaluated` for what SHACL cannot express, non-null report hashes (wave 1, Python-side, parallel with 01)
- [x] 1201-06-PLAN.md — D-11 exit gate: live four-leg DE-01 re-run at `silent_disagreement_count = 0` (wave 5, **requires a live compose stack**, human checkpoint)

### Phase 1202: Design State Replay and Per-Object Verdict Closure

**Goal:** Establish one canonical replay contract for state and validation outcomes.

**Packages:** `ALIGN-P05`, `ALIGN-P06`  
**Requires:** 1200 and 1201.  
**Blocks:** v9.1 shared-surface gate; v10.0 activation gate; future state-dependent generation/editing.

**Deliverables:**

- explicit decision on content-equivalence versus capture-event identity;
- v2 serializer/readers aligned for geometry, ClassIri, lists, enums, and schema version, or an explicit exclusion contract;
- canonical per-object `ValidationEntity` replay path with mixed pass/fail fixture;
- canonical state hash and membership manifest;
- explicit separation of snapshot identity from mutable run/operational status.

**Gate:** publish → query → replay reproduces the canonical state hash and preserves mixed object verdicts, or every excluded member is formally documented.

**Plans:** 11/11 plans complete

Plans:
**Wave 1**

- [x] 1202-01-PLAN.md — Wave 0 test/fixture scaffolding: RED per-object verdict Facts, RED `ON CREATE SET` immutability regression, mixed pass/fail sibling fixture under `fixtures/golden/replay/` (wave 0)
- [x] 1202-02-PLAN.md — Identity semantics: canonical DesignState projection + `canonicalStateHash` in C# and Python with cross-language parity, additive capture-event StateId overload, two-layer identity declared (wave 1)
- [x] 1202-03-PLAN.md — Serializer/reader alignment: `ClassIri` as a normative optional DTO member, the missing version check, and a reader-parity proof that halted D-09's convergence on a real dual-wire-shape collision (wave 1; convergence deliberately not implemented — the exclusion contract is claimed in 1202-09)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 1202-04-PLAN.md — C# per-object verdict read path: additive `GetPerObjectVerdictsAsync`, first Cypher projection of `evidenceEnvelopeJson`, `Enumerable.Repeat` fabrication deleted (wave 2)
- [x] 1202-05-PLAN.md — Python side: `ON CREATE SET` snapshot/status separation, rollup reconciled to the shipped precedence, spec propagation with declared exclusions (wave 2)
- [x] 1202-06-PLAN.md — ObjState minting convergence with the Pitfall-1 signature resolution, GH Release rebuild, blocking human checkpoint on the identity behavior change (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 1202-07-PLAN.md — DE-01 exit evidence: canonical-state-hash comparison dimension plus the live four-leg run against a `--no-cache` rebuilt stack (wave 3, **requires a live compose stack**, human checkpoint)

**Gap closure** *(from `1202-VERIFICATION.md` `status: gaps_found` — both plans target ALGN12-09, the only requirement left partially satisfied; independent, parallel)*

- [x] 1202-08-PLAN.md — Gap 1: make the gate's canonical-state-hash half live-demonstrable — seed `DG-1202-REPLAY`, add `--replay-fixture`, give the C# leg a second independent hash source so `agree`/`disagree` is reachable instead of `not_applicable`, refresh the retained exit evidence, reconcile the ALGN12-11 checkbox (wave 1, **requires a live compose stack**, human checkpoint)
- [x] 1202-09-PLAN.md — Gap 2: claim ALGN12-09's "or an explicit exclusion contract" hatch — write the `parameters[]` dual-wire-shape divergence into `spec/DATABASE.md` and `spec/EVIDENCE-CONTRACT.md`, naming which reader is authoritative for which producer (wave 1, docs + comments only, no reader change)

**Gap closure, round 2** *(from the re-verified `1202-VERIFICATION.md` — the two Critical findings `1202-REVIEW.md` CR-01/CR-02, which were out of scope for 1202-08/09; independent, parallel, different subsystems)*

- [x] 1202-10-PLAN.md — Gap 1 (CR-01, ALGN12-10): `BuildPerObjectVerdicts` groups on the `(RuleId, ObjectId)` pair before the ObjectId rollup and surfaces a duplicate-identity collision as an additive, typed signal on `PerObjectVerdict`/`PerObjectVerdictResult` — `VerdictSource` stays at two members, `StatusRollup.Rollup` stays verbatim (D-12), and `spec/EVIDENCE-CONTRACT.md` §5.1 records the reader-side behavior (wave 1, C# + spec, no live stack needed)
- [x] 1202-11-PLAN.md — Gap 2 (CR-02, ALGN12-08): mirror the Label-vs-Geometry guard for Object-vs-Geometry in `ObjectStateComponent.SolveInstance` using a **dedicated** error template (the existing one hardcodes "Label"), with the guard predicate factored into `DG.Core` so it is unit-testable without the Rhino SDK (wave 1, C# only, optional non-blocking canvas human-check)

### Phase 1203: Identity Convergence and `ATTRIBUTE_OF` Decision

**Goal:** Resolve identity authority and the declared-but-unimplemented rule–parameter bridge.

**Packages:** `ALIGN-P07`, `ALIGN-P08`  
**Requires:** 1200 and 1202.  
**Blocks:** v9.1 activation if the chatbot exposes identity/provenance; v10.0 activation and Phase 47 rule ownership.

**Deliverables:**

- align Grasshopper ObjState minting with the core identity contract, with migration treatment for historical IDs;
- define platform authority/conflict/detach/provenance policy;
- CQ3 fixture covering forward and reverse rule–parameter trace;
- decision between implementing `ATTRIBUTE_OF` alongside `PARAM_LINK` or formally adopting `PARAM_LINK` and retiring/re-scoping the TBox commitment;
- full schema propagation if the bridge is implemented.

**Gate:** ontology, runtime, specification, and paper ownership agree; both query directions are evidenced or the narrowed contract is documented.

**Decision (D-01, locked in `1203-CONTEXT.md`):** Branch A — `ATTRIBUTE_OF` is implemented as a real `(:Atom)-[:ATTRIBUTE_OF]->(:Parameter)` relation alongside `PARAM_LINK`, derived from `inputBindings` at publish time. `PARAM_LINK` is `Parameter`→`Interface` and cannot express the rule–parameter claim in either direction.

**Plans:** 6/6 plans complete

Plans:
**Wave 1**

- [x] 1203-01-PLAN.md — Preflight: capture both suite baselines, inventory every pinned identity literal, relocate the WR-02 defect, and record the true SHACL shape count (wave 1, read-and-record only)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 1203-02-PLAN.md — D-08 + D-09 as ONE coordinated re-derivation: length-prefix hash encoding in both languages, `project` folded into DesignState hashes where legitimately reachable, every golden vector and pinned literal updated in lockstep (wave 2)
- [x] 1203-04-PLAN.md — `ATTRIBUTE_OF` derivation and project-scoped MERGE at publish time, forward and reverse query tests (wave 2, parallel with 1203-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 1203-03-PLAN.md — CR-01 label-aware `mint_identity` with a mint→bind→publish coincidence regression, WR-01 graph tagging, WR-03 dead-constant deletion, ALGN12-13 conflict/detach/provenance test coverage (wave 3, serialized after 1203-02 — both touch `dg_identity.py`)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 1203-05-PLAN.md — D-05 schema propagation sweep across every surface plus the SHACL shape, and D-06 consolidation of `spec/DG-ID.md` into the single identity authority (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 1203-06-PLAN.md — CQ3 fixture in a sibling path evidencing both query directions, with a live-stack human checkpoint (wave 5, **requires a running compose stack**)

### Phase 1204: Determinism and LLM Reproducibility Benchmark

**Goal:** Separate deterministic validator repeatability from LLM proposal repeatability.

**Package:** `ALIGN-P13`  
**Requires:** 1200–1203; fixed provider/model/prompt snapshots.  
**Blocks:** v10.0 activation if its consulting/generation claims depend on reproducibility.

**Deliverables:**

- repeated fixed-fixture validator runs with hashes and canonical statuses;
- separate LLM repeatability/abstention/invalid-output report;
- provider/model/prompt/config provenance;
- no universal determinism claim across live LLM or canvas state.

**Gate:** reports deterministic and model-dependent results separately, with confidence/limitations.

### Phase 1205: Security and Tenancy Release Gate

**Goal:** Establish server-side authorization and fail-closed project boundaries.

**Package:** `ALIGN-P14`  
**Requires:** 1200 evidence envelope; may run after 1203 but must precede external multi-user evaluation.  
**Blocks:** external multi-user release, not local single-user feature milestones.

**Deliverables:**

- server-side user/tenant authorization;
- direct Neo4j proxy exposure review and removal/restriction;
- secret/default-credential hardening and rotation procedure;
- unauthorized cross-project and direct-proxy tests;
- deployment boundary for connector heartbeat and privileged graph access.

**Gate:** unauthorized cross-project and direct-proxy access fail closed; secret handling is deployment-safe.

**Plans:** 19 plans

Plans:
**Wave 1**

- [ ] 1205-01-PLAN.md — Known-default secret policy, `.env.example`, owner-run env checker; owner creates `.env` before any enforcement (human checkpoint)
- [ ] 1205-02-PLAN.md — Server-side identity store: scrypt users, hashed sessions, memberships, invites, three principal resolvers, bootstrap admin, deployment profile
- [ ] 1205-03-PLAN.md — Grasshopper publish clients send the `dgc_` connector token; Token inputs; CONNECTOR multi-user no-bundle handling
- [ ] 1205-04-PLAN.md — Operator tooling: DE-01 connector-token path, LLM master-secret re-encryption script, live boundary checker
- [ ] 1205-05-PLAN.md — n8n workflows: relay-token guard, service token, hardcoded internal URLs, env credentials, atomic project-scoped ingest write
- [ ] 1205-06-PLAN.md — LLM-generated Cypher project-scope guard, foreign-literal and key-collision checks (dg_context)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 1205-07-PLAN.md — Tracer: login + deny-by-default dependency + one enforced project route end to end; startup profile, D-11 refusal, bootstrap, heartbeat bundle
- [ ] 1205-08-PLAN.md — Authorized test fixtures so every existing suite runs under a real principal
- [ ] 1205-09-PLAN.md — Compose: required `.env` secrets, 127.0.0.1 bindings, multi-user override, dockerignore

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 1205-10-PLAN.md — Global enforcement flip: 67-route classification, removals, resource-bound id routes, D-14 inventory and sweeps
- [ ] 1205-11-PLAN.md — UI data layer: apiFetch, named endpoints replace the nine Cypher sites, relay replaces n8n webhooks

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 1205-12-PLAN.md — Projects, memberships, invitations and the named graph endpoints (D-06)
- [ ] 1205-13-PLAN.md — UI login / accept-invite, membership-scoped Projects screen with owner members panel

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 1205-14-PLAN.md — Workflow relay with owner-bound polling; /mcp and generate-cypher project enforcement
- [ ] 1205-15-PLAN.md — nginx/vite proxy removal with 404 tombstones; secret-free config.js; bundle secret scan

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 1205-16-PLAN.md — `spec/SECURITY-BOUNDARY.md` with four machine-checked blocks and the rotation runbook; spec drift test; doc pointers
- [ ] 1205-17-PLAN.md — D-15 two-user/two-project cross-project matrix

**Wave 7** *(blocked on Wave 6 completion; requires a running compose stack)*

- [ ] 1205-18-PLAN.md — Live: owner rotates every committed secret, n8n publish, local-profile boundary checks (human checkpoint)

**Wave 8** *(blocked on Wave 7 completion; requires a running compose stack)*

- [ ] 1205-19-PLAN.md — Live GATE12-05 judgement in the multi-user profile with owner verdict (human checkpoint)

## Activation gates for downstream milestones

### v9.1 activation

Requires:

- Phase 40 owns and records the pending live UAT disposition;
- standalone GSD reconciliation is complete;
- v12.0 1200–1203 gates pass;
- v11.0 shared-surface gate is acknowledged, without requiring full v11.0 activation.

### v10.0 activation

Requires:

- v12.0 1200–1204 gates pass;
- v11.0 1105/1106 semantic-boundary and rule-ownership gate is accepted;
- Phase 47 retains its explicit partition prerequisite.

### v11.0 activation

Remains governed by its own future-milestone rules and activation sequence. v12.0 supplies evidence and resolved contract decisions; v11.0 remains owner of publication bundle and manuscript alignment.

## Deferred / not owned here

- `ALIGN-P09`, `ALIGN-P15`, `ALIGN-P16`: v11.0 1106/1107.
- `ALIGN-P10`, `ALIGN-P11`, `ALIGN-P12`: v9.0 Phase 40 and `GSD-ALIGN-005/007/009`.
- Alternative B/DE-02 and Alternative C/DE-03: reconsider only after the hybrid contract gates produce evidence.
- Graphify regeneration: separate evidence run, not a v12.0 prerequisite.
- v4.0 BOT bridge: future scope.

## Acceptance summary

v12.0 is successful when the shared contract is executable, unsupported semantics are typed, state replay and per-object verdicts are preserved, identity/`ATTRIBUTE_OF` ownership is resolved, deterministic and LLM repeatability are separated, and security fails closed before external multi-user evaluation.
