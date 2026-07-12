# Requirements: Design Grammar System — Milestone v8.2 Connector Integration & Reasoning Engine

**Defined:** 2026-07-11
**Core Value:** Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required.
**Milestone goal:** Wire the Grasshopper CONNECTOR component to the platform's credential mechanism, and replace the Reasoner screen's HermiT/Pellet placeholders with real OWL 2 DL + SHACL validation.

Archived v8.1 requirements: `.planning/milestones/v8.1-REQUIREMENTS.md`.

## v8.2 Requirements

Requirements for milestone v8.2. Each maps to roadmap phases 820–829.

### Reasoner Integration (REAS)

Continues the REAS category opened in v8.1 (REAS-01..03: placeholder selector). REAS-04..06 close out the deferred `REAS-F01` future requirement from v8.1 — real reasoning now replaces the placeholder.

- [x] **REAS-04**: The OntoGraph axiom-scoping approach is decided and documented (extend LLM ingestion to emit real `subClassOf`/`domain`/`range`/`disjointWith` axioms vs. scope reasoning to structural/referential checks vs. a hybrid), together with an LPG→OWL mapping spec covering edge-property reification (`Atom.ARG.pos`, `Rule.HAS_BODY/HAS_HEAD.order`)
- [x] **REAS-05**: A `dg-reasoner` sidecar service runs in docker-compose and exposes OWL 2 DL consistency-check and SHACL-validation endpoints, isolated from `data-service`'s Speckle-publish/validation-run hot path
- [x] **REAS-06**: User runs an OWL 2 DL consistency check from the Reasoner screen (HermiT default engine) and sees a pass/fail summary with unsatisfiable-class count, replacing the v8.1 "integration pending" placeholder label

### SHACL Validation (SHCL)

- [x] **SHCL-01**: DesignState/Rule instance data is translated to RDF and validated via SHACL on each validation run, running alongside (not replacing) the existing SWRL-based VALIDATOR, with a documented rule-partition/precedence policy between the two
- [x] **SHCL-02**: SHACL violations surface through DG's existing ErrorMessageTemplates (What+Where+How-to-fix) with severity (info/warning/violation) mapped to a Solibri-style red/orange/yellow treatment — never raw RDF/SHACL vocabulary shown to the architect

### Connector Grasshopper Integration (CONNG)

- [ ] **CONNG-01**: The Grasshopper CONNECTOR component accepts a platform-issued credential/token (minted from the v8.1 Connectors screen, "Grasshopper" connector type) as a new additive input — existing Neo4jURI/User/Password/Database inputs and the component's GUID are preserved unchanged
- [ ] **CONNG-02**: CONNECTOR shows in-canvas error feedback (GH runtime message, existing `AddRuntimeMessage`/ErrorMessageTemplates pattern) when the platform credential is invalid, revoked, or expired

## Future Requirements

Deferred. Tracked but not in the v8.2 roadmap.

### Reasoner Integration

- **REAS-F02**: Explanation/justification UX for OWL reasoning failures — translate axiom-unsatisfiability justifications into plain language (Protégé-style "Explain inference"), deferred until the pass/fail summary has been used in practice
- **REAS-F03**: TBox→SHACL shape auto-derivation — single source of truth generating both OWL constraints and SHACL shapes automatically; real open-world/closed-world design tension needs its own design pass

### Connectors

- **CONN-F01**: Actual connector plugins for target software beyond Grasshopper (Revit add-in, Dynamo package, etc.) — carried forward from v8.1
- **CONN-F02**: Per-credential usage analytics / request logs beyond last-connection date — carried forward from v8.1
- **CONN-F03**: Pre-emptive credential status display on CONNECTOR (live active/stale/revoked shown before a validation run, via the existing heartbeat endpoint)
- **CONN-F04**: Per-connector-type scoping surfaced explicitly in the Grasshopper UX (today implicit in the backend registry)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Replacing the SWRL VALIDATOR with SHACL | SHACL ships as a complementary, additive validation layer this milestone per the explicit milestone framing; SWRL already encodes DG's rule semantics (violation-inverted body atoms) and a wholesale swap is a separate future-milestone decision |
| Running OWL DL consistency reasoning on every validation run (same cadence as SHACL) | TBox reasoning is open-world/schema-level and answers a different question than per-design instance validation; conflating the two cadences into one status misleads architects and wastes cycles — OWL checks run only on-demand from the Reasoner screen or on ontology-export change |
| Exposing raw SHACL/RDF validation report JSON in the UI | Architects have no semantic-web background; raw `sh:focusNode`/`sh:sourceShape` output is meaningless without translation through ErrorMessageTemplates |
| Full Protégé-style ontology editor in the Reasoner screen | Massively out of scope — v8.2 reasons against the existing `DesignGrammar-V7.owl` export, it does not author it |
| Storing the raw CONNECTOR credential/token inside the `.gh` file | `.gh` files are shared/versioned across a team; baking a `dgc_` secret into canvas state is a credential-leak vector and contradicts the v8.1 "shown once" token pattern |
| Actual connector plugins for non-Grasshopper software (Revit, Dynamo, etc.) | v8.2 only wires the Grasshopper CONNECTOR component; other target-software plugins are separate future deliverables (tracked as CONN-F01) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REAS-04 | Phase 820 | Complete |
| REAS-05 | Phase 821 | Complete |
| REAS-06 | Phase 822 | Complete |
| SHCL-01 | Phase 823 | Complete |
| SHCL-02 | Phase 823 | Complete |
| CONNG-01 | Phase 824 | Pending |
| CONNG-02 | Phase 824 | Pending |

**Coverage:**

- v8.2 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-07-11*
*Roadmap created: 2026-07-11 — 5 phases (820–824), 100% coverage*
