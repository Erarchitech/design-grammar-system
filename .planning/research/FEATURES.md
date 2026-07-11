# Feature Landscape: v8.2 Connector Integration & Reasoning Engine

**Domain:** OWL 2 DL ontology-consistency reasoning + SHACL instance validation + credential-gated visual-programming (Grasshopper) connector, layered onto the existing DG platform
**Researched:** 2026-07-11
**Confidence:** MEDIUM (cross-checked web sources — vendor docs, W3C spec, community/GitHub issue threads — no HIGH-confidence primary-doc lookups available this pass; see Sources)

**Milestone context:** v8.2 adds three things to an already-shipped platform: (1) a Grasshopper CONNECTOR component wired to the v8.1 Connectors-screen credential system (today it connects to Neo4j directly with no credential relationship), (2) real OWL 2 DL reasoning replacing the v8.1 Reasoner screen's HermiT/Pellet placeholder selector, (3) a SHACL validation layer alongside the existing bespoke-regex SWRL VALIDATOR. This file treats those three as one interlocking feature set, not three independent products.

---

## Critical Framing: Two Different Kinds of "Reasoning," Two Different Cadences

This distinction drives every table-stakes/differentiator call below and must survive into the roadmap as two separate phases, not one:

| | **OWL 2 DL Consistency Reasoning** | **SHACL Instance Validation** |
|---|---|---|
| **Operates on** | TBox (ontology schema: classes, properties, disjointness, domain/range) | ABox (instance data: a specific DesignState/Rule/graph snapshot) |
| **World assumption** | Open-world — reasoner infers what *could* be true from what's asserted | Closed-world — checker rejects data that fails an explicit shape |
| **When it runs** | Ontology-authoring time: when `DesignGrammar-V7.owl` (or its Neo4j encoding) itself changes — rarely, on schema edits | Every validation run: every time a captured DesignState is checked against a Rule, same cadence as today's SWRL VALIDATOR |
| **What a failure means** | The ontology itself is broken (a class is unsatisfiable, contradicts another class) — a modeling bug | This specific design/building instance violates a rule or is malformed — an architect-facing result |
| **Who acts on the result** | Ontology maintainer / whoever edited the schema | The architect running validation on their model |
| **DG v8.2 trigger point** | Reasoner screen "Run consistency check" action, or CI-style check when the ontology export changes | VALIDATOR component's Cypher-Compute flow, run alongside (or eventually replacing parts of) the SWRL evaluation |

Sources converge on this split (general RDF/OWL practice, not BIM-specific): OWL reasoning is infrequent and schema-scoped; SHACL is the mechanism for "does this data conform" at write/validate time — mirroring the existing DG architecture almost exactly (TBox ≈ ontology export, ABox ≈ per-project Neo4j graph). Any roadmap phase that conflates the two into a single "add reasoning" phase will produce the wrong cadence and the wrong UI location for at least one of them.

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Reasoner screen "Run check" action that actually reasons (replacing the v8.1 placeholder selector) | v8.1 already shipped a HermiT/Pellet picker with an explicit "integration pending" label — users who saw that screen expect the next release to remove the label, not add a third placeholder | MEDIUM | HermiT is the more practically usable default (bundled with Protégé 5.6.1, actively used); Pellet/Openllet show low recent maintenance activity — pick HermiT as the shipped path, keep Pellet selectable but flag lower confidence |
| Consistency-check pass/fail summary at ontology level ("N unsatisfiable classes found" / "Ontology is consistent") | This is the minimum output any OWL reasoner UI provides (Protégé shows red-highlighted unsatisfiable classes in the class hierarchy) | LOW | Binary status + count is enough for v1; does not require explanation/justification UI yet |
| SHACL violation → itemized list mapped back to the offending Rule/DesignState/atom, not raw RDF | Universal SHACL-tooling convention: sh:resultMessage is author-written specifically to be end-user-readable, sh:focusNode identifies the offending instance; no production tool shows raw triples to end users | MEDIUM | Directly reuses DG's existing ErrorMessageTemplates "What+Where+How-to-fix" pattern already used elsewhere in DG.Core — this is a natural extension point, not a new UX language |
| Severity levels on validation results (info/warning/violation or similar) | SHACL natively defines sh:Info/sh:Warning/sh:Violation; the AEC industry standard (Solibri) uses a 3-tier critical/moderate/low traffic-light system that architects already recognize from BIM tooling | LOW–MEDIUM | Map SHACL's 3 native severities directly to a red/orange/yellow treatment consistent with Solibri-trained user expectations — do not invent a new taxonomy |
| CONNECTOR component accepts a pasted credential/token string as one input, replacing manual Neo4jURI/User/Password inputs | Both Speckle (developer-access-token node) and n8n (credential reference) already establish "paste an opaque token, not raw connection secrets" as the AEC/workflow-tool norm; DG's existing 6-input manual-entry CONNECTOR is the outlier, not the target state | MEDIUM | v8.1 already mints `dgc_`-prefixed tokens shown once — the natural v8.2 move is a single Credential/Token input replacing Neo4jUser+Neo4jPassword (URI/Database/Project/Connect trigger can remain) |
| In-canvas error feedback when the credential is invalid/revoked (GH runtime error, not silent failure) | Grasshopper's native `AddRuntimeMessage` affordance (which DG.Grasshopper already uses via ErrorMessageTemplates) is the expected surface — n8n's canvas equivalent is a red "failed" badge + click-through error text; doing nothing / silent no-op would be a regression versus DG's own established error-message quality bar | LOW | This is mostly wiring existing DG.Core error-template patterns to a new failure mode (401/403 from the credential check), not new UX invention |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Combined OWL-consistency + SHACL pipeline where SHACL shapes are (eventually) derived from the same ontology TBox that HermiT reasons over | Most BIM tools pick one lane — either Solibri-style rule checking (no formal ontology) or academic OWL tooling (no architect-friendly UX). DG doing both, tied to the same DesignGrammar-V7.owl source of truth, is a genuine differentiator versus IDS/Solibri (which have no OWL layer) and versus raw semantic-web tooling (which has no architect UX) | HIGH | Defer full shape-auto-derivation to a later milestone; v8.2 can ship both engines independently against the existing ontology without full TBox→SHACL codegen |
| Explanation/justification UX for *why* a class is unsatisfiable (not just that it is) | Protégé's "Explain inference" (axiom-set justification) is the gold-standard OWL UX feature but is aimed at ontology engineers, not architects — DG could differentiate by translating the axiom justification into a plain-language sentence the way it already does for SWRL/validation errors | HIGH | This is a stretch feature; table-stakes v1 only needs pass/fail + count, not full justification chains |
| Credential status visible pre-emptively inside Grasshopper (not just on first failed run) | n8n's own credential UX is reactive-only — no advance warning before a node fails; DG could differentiate by having the CONNECTOR component's "Connect" output reflect live status (active/stale/revoked) sourced from the v8.1 heartbeat/status endpoint already built in Phase 812, surfacing it before the user hits a validation failure | MEDIUM | Directly reuses the CONNB-01..04 status endpoint already shipped — low marginal backend cost, mostly a GH-component UI decision |
| Per-connector credential scoping (CONNECTOR token scoped to "Grasshopper" connector type specifically, distinct from other 13 connector types) | Speckle's scoped-token model (profile:read, stream:read, etc.) and the v8.1 credential backend's per-connector-type registry both support this; a Grasshopper-specific credential type reduces blast radius if a token leaks | LOW–MEDIUM | v8.1's Connector Credential Backend (812) already models 14 connector types — Grasshopper is just one of them, so this is largely already available, not new work |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Running full OWL DL consistency reasoning on every validation run (same cadence as SHACL/SWRL) | Seems more "thorough" — "why not check everything every time?" | TBox reasoning is open-world and can be computationally expensive at scale; it answers "is the schema broken," which does not change between validation runs unless the ontology itself was edited. Running it per-validation-run wastes cycles and conflates two unrelated failure classes in one error surface | Trigger OWL consistency checks only on Reasoner-screen "Run check" action or on ontology-export change; keep SHACL/SWRL as the per-validation-run mechanism |
| Exposing raw SHACL/RDF validation report JSON (sh:focusNode, sh:sourceShape IRIs, etc.) directly in the Model Viewer UI | Fastest to implement — "just show the reasoner's own output" | Architects have no semantic-web background (explicit milestone constraint); raw SHACL vocabulary is meaningless to them and would be a UX regression versus DG's existing ErrorMessageTemplates pattern | Translate sh:resultMessage + sh:focusNode into the same What+Where+How-to-fix template already used for SWRL/validation errors elsewhere in DG |
| Replacing the existing SWRL VALIDATOR outright with SHACL in v8.2 | SHACL is the "more standard" W3C mechanism, tempting to consolidate | The milestone brief explicitly frames SHACL as investigated "alongside" the existing SWRL-based VALIDATOR, not a replacement; SWRL already encodes DG's rule semantics (violation-inverted body atoms) and a wholesale swap is a much bigger, riskier scope than v8.2's phase budget (820–829) supports | Ship SHACL as an additional/complementary validation layer this milestone; treat SWRL→SHACL consolidation (if ever) as a separate future milestone decision |
| Storing the raw Grasshopper CONNECTOR credential/token in the .gh file or bake it into component state | Simplest for the user — "just remember my token" | .gh files are shared/versioned across a team; baking a `dgc_` secret into a canvas file is a credential-leak vector, and directly contradicts the v8.1 "shown once, never displayed again" pattern already established for these tokens | Store only a token reference/last-4 + status in the component's persistent data; require re-paste (or a secure OS-level credential store) if the token is lost, matching how the Connectors screen already treats tokens as show-once secrets |
| Full Protégé-style ontology editor bundled into the Reasoner screen | "Since we have a reasoner, let users edit the ontology too" | Massively out of scope — the milestone is about *reasoning against* the existing `DesignGrammar-V7.owl` export, not authoring it; an in-app OWL editor is a different, much larger product | Keep the Reasoner screen to selection + "run check" + result summary; ontology edits stay in the existing Protégé/file-based workflow that produced DesignGrammar-V7.owl |

---

## Feature Dependencies

```
v8.1 Connector Credential Backend (Phase 812: mint/list/revoke, heartbeat/status)
    └──requires (already shipped)──> CONNECTOR component: credential input
                                          └──requires──> CONNECTOR component: in-canvas status/error feedback
                                                             └──enhances──> Differentiator: pre-emptive status display

v8.1 Reasoner Screen (Phase 814: HermiT/Pellet placeholder selector, persisted choice)
    └──requires (already shipped)──> Reasoner-stack architecture decision (Jena/HermiT/OWL API integration path)
                                          └──requires──> OWL 2 DL consistency reasoning ("Run check" action + pass/fail summary)
                                                             └──enhances──> Explanation/justification UX (differentiator, deferred)

Existing SWRL VALIDATOR (bespoke regex, Neo4j Cypher evaluation)
    └──unaffected by──> SHACL validation layer (additive, not a replacement — explicit milestone constraint)
                              └──requires──> Reasoning-stack architecture decision (shared with OWL path: Jena/pySHACL/TopBraid choice)
                              └──requires──> Severity-mapped, ErrorMessageTemplates-consistent result surfacing

Reasoning-stack architecture decision (RDF/OWL-native stack vs Neo4j property-graph ontology encoding)
    └──BLOCKS both──> OWL 2 DL reasoning integration
    └──BLOCKS both──> SHACL validation layer
```

### Dependency Notes

- **CONNECTOR credential input requires the v8.1 Connector Credential Backend (Phase 812):** the mint/list/revoke/heartbeat API already exists — v8.2's CONNECTOR work is a *consumer* of that API, not a new backend. This is the lowest-risk, most self-contained piece of v8.2.
- **OWL reasoning integration requires the Reasoner-stack architecture decision first:** picking HermiT-via-OWL-API-via-JPype/Py4j (Java-in-Python-service) vs. Owlready2 (Python-native, embeds HermiT/Pellet) vs. a standalone Jena Fuseki service is a prerequisite that gates all reasoner UI work — this decision should be its own early phase, not bundled into "build the reasoner feature."
- **SHACL validation layer shares the same architecture-decision gate:** pySHACL (Python-native, fits the existing FastAPI data-service) vs. TopBraid SHACL API (Java, more mature but adds a JVM dependency) is the analogous choice, and ideally resolved in the *same* architecture-decision phase as the OWL choice, since both may converge on "avoid introducing a JVM dependency into data-service" or diverge deliberately.
- **SHACL validation does NOT block or get blocked by the SWRL VALIDATOR:** explicit milestone framing is "investigated alongside," so these can be parallel workstreams once the architecture decision lands.
- **Explanation/justification UX (differentiator) enhances but does not gate the table-stakes pass/fail summary:** ship the summary first; justification chains are a valid v8.3+ follow-up.

---

## MVP Definition

### Launch With (v1 — v8.2 scope)

- [ ] CONNECTOR component: single credential/token input replaces manual Neo4jUser+Neo4jPassword, validated against the v8.1 credential backend on Connect — table stakes, closes the explicit "no relationship" gap called out in the milestone brief
- [ ] CONNECTOR component: in-canvas error feedback (GH runtime message) on invalid/revoked/expired credential, using existing ErrorMessageTemplates pattern — table stakes, avoids silent-failure regression
- [ ] Reasoning-stack architecture decision documented and committed (Jena/OWL-API/Owlready2/pySHACL/TopBraid choice) — blocks everything else, must land first
- [ ] OWL 2 DL consistency check ("Run check" action on Reasoner screen, HermiT default): binary pass/fail + unsatisfiable-class count, replacing the placeholder label — table stakes, closes the explicit "integration pending" gap
- [ ] SHACL validation layer: runs instance-level checks on DesignState/Rule data, surfaces results through the existing ErrorMessageTemplates What+Where+How-to-fix pattern with severity mapped to Solibri-style red/orange/yellow — table stakes, delivers the "data-level design-rule/instance validation" requirement

### Add After Validation (v1.x)

- [ ] Pre-emptive credential status display on the CONNECTOR component (live active/stale/revoked from the heartbeat endpoint, shown before a validation run is attempted) — differentiator, low marginal cost once v1 lands
- [ ] Per-connector-type token scoping surfaced explicitly in the Grasshopper UX (today it's implicit in the backend registry) — differentiator, mostly UI-copy work

### Future Consideration (v2+)

- [ ] Explanation/justification UX for unsatisfiable-class reasoning failures (translate OWL axiom justifications into plain language) — defer until the pass/fail summary has been used in practice and users ask "why"
- [ ] TBox→SHACL shape auto-derivation (single source of truth generating both the OWL constraints and SHACL shapes) — defer; significant scope, and current SHACL-vs-OWL literature notes soundness/completeness tension between open-world OWL and closed-world SHACL that needs careful design, not a v1 rush
- [ ] SWRL→SHACL consolidation (retiring the bespoke-regex VALIDATOR) — explicitly out of scope per milestone framing; revisit only as its own future milestone

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| CONNECTOR credential input (replace manual Neo4j creds) | HIGH | MEDIUM | P1 |
| CONNECTOR in-canvas credential error feedback | HIGH | LOW | P1 |
| Reasoning-stack architecture decision | HIGH (blocks all else) | MEDIUM | P1 |
| OWL 2 DL consistency check + pass/fail summary | HIGH | MEDIUM–HIGH | P1 |
| SHACL instance validation layer + ErrorMessageTemplates surfacing | HIGH | MEDIUM–HIGH | P1 |
| Pre-emptive credential status display | MEDIUM | LOW | P2 |
| Per-connector-type scoping surfaced in GH UX | LOW–MEDIUM | LOW | P3 |
| Explanation/justification UX for reasoning failures | MEDIUM | HIGH | P3 |
| TBox→SHACL auto-derivation | LOW (for v8.2) | HIGH | P3 |

**Priority key:**
- P1: Must have for v8.2 launch
- P2: Should have, add when possible within v8.2 or immediate follow-up
- P3: Nice to have, defer to a future milestone

---

## Competitor / Comparable-Tool Feature Analysis

| Feature | Solibri (BIM rule checking) | n8n (workflow canvas credentials) | Speckle (Grasshopper/Dynamo connector) | DG v8.2 Approach |
|---------|------------------------------|-------------------------------------|------------------------------------------|-------------------|
| Rule/violation severity | 3-tier critical/moderate/low, auto-assigned, red/orange/yellow triangle icons, filterable | N/A (not a rule-checking tool) | N/A | Map SHACL's native Info/Warning/Violation to the same red/orange/yellow convention architects already recognize from Solibri |
| Credential wiring into canvas | N/A | Named credential referenced by node, not pasted inline; central Credentials panel | Managed account (separate desktop app) for interactive use; explicit developer-token node for automation, scoped (profile:read, stream:read, etc.) | Single credential/token input on CONNECTOR, validated against v8.1 backend on Connect — closer to Speckle's token-node pattern since DG's CONNECTOR is itself already a "headless/automation" style component |
| Token expiry/revocation feedback | N/A | Reactive only: red "failed" badge on the node after a run hits the auth error; no proactive warning; recovery via "Reconnect Account" | Not directly documented for revocation UX; token minted externally in the web app | v1: reactive GH runtime error on Connect (matches n8n's reactive baseline). v1.x differentiator: proactive status via the already-built heartbeat endpoint (exceeds both comparables) |
| Ontology/schema-level consistency checking | Not present — Solibri has no OWL/formal-ontology layer | N/A | N/A | Genuine gap DG can fill: no comparable BIM tool combines rule-checking UX with real OWL DL reasoning |
| Non-expert error surfacing | Itemized list + severity icon + report export, IFC-element-linked | Raw provider error text shown on click-through (not friendly) | N/A (account errors, not data-validation errors) | Follow Solibri's model (itemized, severity-coded, entity-linked), not n8n's raw-error-text model — consistent with DG's existing ErrorMessageTemplates philosophy |

---

## Sources

- Solibri Help Center — "Understanding Checking," "Understanding the Severity Levels of Checking Results," "244 IDS Validation" (`help.solibri.com`) — MEDIUM confidence (vendor docs, cross-checked)
- buildingSMART IDS documentation and Plannerly/BIM Corner explainers on IDS validation reporting — MEDIUM confidence
- W3C SHACL specification vocabulary (sh:focusNode, sh:resultMessage, sh:resultSeverity) and SHACL 1.2 User Interfaces draft (`w3.org/TR/shacl12-ui/`) — MEDIUM confidence (spec-level, cross-checked against tooling blogs)
- Protégé documentation and GitHub issues on unsatisfiable-class highlighting and "Explain inference" UX (`protegeproject/protege`) — MEDIUM confidence
- n8n Community forum and GitHub issues on OAuth2 credential expiry/revocation UX (`community.n8n.io`, `github.com/n8n-io/n8n`) — MEDIUM confidence
- Speckle documentation on Grasshopper/Dynamo connector authentication (Account Select, Server Token node, scoped developer tokens) (`docs.speckle.systems`, `speckle.guide`) — MEDIUM confidence
- General web survey of HermiT/Pellet/Openllet/ELK maintenance status (GitHub repos, "OWL Reasoners still useable in 2023" analysis) — MEDIUM confidence, dated 2023 baseline extrapolated forward; recommend re-verifying exact library versions at implementation time via the reasoning-stack architecture-decision phase
- DG existing codebase: `DG.Core/Services/ErrorMessageTemplates`, `DG.Grasshopper/Components/ValidationGraphComponent.cs`, `data-service/reasoner.py` (Phase 814), Connector Credential Backend (Phase 812) — HIGH confidence, direct code/graph inspection via graphify

---
*Feature research for: OWL 2 DL reasoning, SHACL instance validation, credential-gated Grasshopper connector*
*Researched: 2026-07-11*
