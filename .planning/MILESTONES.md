# Milestones

## v8.2 Connector Integration & Reasoning Engine (Shipped: 2026-07-12)

**Phases completed:** 5 phases, 19 plans, 44 tasks
**Closeout:** override closeout — **Known verification overrides: 3** (Phases 822 & 824 in-app/in-Rhino UAT deferred; Phase 823 closed via user-approved checkpoint with no formal VERIFICATION.md — see STATE.md `## Deferred Items`)

**Key accomplishments:**

- **Phase 820** — Resolved the OntoGraph axiom-scoping question as a *hybrid* approach and authored the normative `spec/LPG-OWL-MAPPING.md` (Metagraph SWRL vocabulary, OntoGraph OWL terms, edge-property reification for `ARG.pos` + `HAS_BODY/HAS_HEAD.order`, IRI minting, UNA handling); both decisions recorded as ADRs with spike evidence.
- **Phase 821** — New isolated `dg-reasoner` sidecar (Python 3.11 + headless JRE, internal-only in docker-compose, n10s-equipped neo4j) with a clean `ontology_export.py` Cypher→RDF translator and 8 fidelity tests proving `ARG.pos` and `HAS_BODY/HAS_HEAD.order` survive translation; a short-timeout httpx proxy wires data-service to the sidecar.
- **Phase 822** — Real OWL 2 DL consistency check (HermiT default engine) wired end-to-end into the Reasoner screen, replacing the v8.1 "integration pending" placeholder; `unsatisfiable_classes` enriched to `{iri,label}`; HermiT flipped to `integrated`. Backend gate green (dg-reasoner 19/19, data-service 13/13); manual frontend UAT deferred.
- **Phase 823** — SHACL Validation Layer: 8 version-controlled data-integrity NodeShapes over the run-scoped ValidGraph ABox (with `owl:AllDifferent` UNA), `shaclReportJson` propagated across five spec/config surfaces + `spec/RULE-PARTITION-POLICY.md`; findings surface on the VALIDATOR component (capped Warning/Remark) and a Solibri-style SHACL Data Integrity panel in the ui-v2 Model screen.
- **Phase 824** — CONNECTOR gains an additive platform-token heartbeat with in-canvas Error/Warning feedback and full token secrecy (hashed dedup key, persistent-data scrub, token-free outputs); component GUID and existing ports untouched; whole solution builds green against the Rhino 8 SDK.

---

## v7.0 Update of DG Addin for Grasshopper (Shipped: 2026-07-05)

**Status:** Shipped — 8 phases, 37 plans complete; archived 2026-07-07
**Timeline:** 2026-07-02 → 2026-07-05

Rebuilt the DG Grasshopper addin around the ontology-aligned 14-component schema (`ontology/GH_DesignGrammars.pdf`): Ontology V6→V7 rename with recovery mapping, state trio (ObjState/ParamState/PropState) + DesignState composition, graph access chain (CONNECTOR, GRAPH DECONSTRUCT, METAGRAPH, ONTOGRAPH, VALIDATION GRAPH), VALIDATOR rework with DesignState-driven binding, CLASSIFICATOR elimination, PARAMETER REINSTATE, KnowledgeGraph→SpecGraph runtime rename, graph schema v4 propagation, release notes for canvas breakage.

→ [Requirements](v7.0-REQUIREMENTS.md) | [Roadmap](v7.0-ROADMAP.md) | [Phases archive](v7.0-phases/)

---

## v3.0 Typed Variables and Composable Design State (Superseded: 2026-07-02)

**Status:** Superseded by v7.0 — Update of DG Addin for Grasshopper
**Timeline:** 2026-05-11 → 2026-07-02

Phase 7 (Schema Foundation) **shipped** and carries forward into v7.0: `VariableKind` enum + `VariableTypeInferrer` priority-chain classifier, `DesignStateIdGenerator` (DS_/OS_/OI_ prefixes), Var merge-key cross-project fix, DefState/ObjectState model scaffolding, schema propagation v3.1.

Phases 8–12 (METAGRAPH expansion, OBJECT STATE + DESIGN STATE rework, CLASSIFICATOR rework, RUN DECONSTRUCT, E2E) **dropped** — the component plan was replaced wholesale by the `ontology/GH_DesignGrammars.pdf` schema (CLASSIFICATOR eliminated; state capture decomposed into OBJECT/PARAMETER/PROPERTY STATE; graph access decomposed into GRAPH DECONSTRUCT + ONTOGRAPH + VALIDATION GRAPH).

→ [Requirements](v3.0-REQUIREMENTS.md) | [Roadmap](v3.0-ROADMAP.md) | [Phase 7 archive](v3.0-phases/)

---

## v4.0 BOT Ontology Bridge (Planned)

**Status:** Planned — pending v3.0 completion
**Defined:** 2026-05-25

Automatic alignment of DG Ontograph entities to the W3C Building Topology Ontology (BOT). When users submit rules containing spatial concepts (building, storey, space, site, zone, element), the pipeline creates BOT anchor nodes on-demand and links them to `ex:` OntoGraph nodes via `ALIGNED_TO` edges. Custom concepts with no BOT match are unaffected.

**Phases planned:** 4
→ [Requirements](v4.0-REQUIREMENTS.md) | [Roadmap](v4.0-ROADMAP.md)

---

## v8.0 Design Grammars V2 UI (Shipped: 2026-07-07)

**Status:** Shipped — Phases 21–27, 28 requirements complete (Phase 27 Speckle 3D Embed added post-ship, completed 2026-07-08)
**Timeline:** 2026-07-07 → 2026-07-08

Replaced the dark legacy web SPA with the "Design Grammars V2" light clinical-blueprint interface as the real product UI (`ui-v2/`, Vite + React): design-system foundation (tokens, Geist/Oswald, frost/blueprint primitives), particle-ring landing with inline auth, canvas datascape Graph Viewer wired to live Neo4j + n8n webhooks, Model Viewer over data-service validation runs, project scoping, deployment cutover at :8080 with E2E parity. Post-ship Phase 27 replaced the synthetic SVG map with an embedded Speckle 3D viewer (validation colour overlay, SVG fallback toggle).

→ [Requirements](v8.0-REQUIREMENTS.md) | [Phases archive](v8.0-phases/)

---

## v9.0 AI Workflow Intelligence (Active)

**Status:** Active — reactivated 2026-07-12 (phase directories + requirements moved from `milestones/v9.0-phases/`+`v9.0-REQUIREMENTS.md` into `.planning/phases/`+`.planning/REQUIREMENTS.md`; roadmap detail inlined in `.planning/ROADMAP.md`). Phase 28 (cloud-llm-connector) shipped 2026-07-06; Phase 29 next. Restructured + renumbered 2026-07-08 (milestone-local 1–13 → global 28–40).
**Defined:** 2026-07-03

Two axes: (1) LLM infrastructure — provider-agnostic cloud LLM connector (user-supplied API key, Claude/OpenAI-compatible/Ollama-fallback, provider control from the UI) plus a DG-aware context layer injecting ontology V7 concepts, SWRL conventions, and a standard Cypher expression catalog with pre-execution validation; (2) Grasshopper canvas intelligence — the script's graph context serialized to the ontology's Computgraph layer via annotation-convention parsing (Frame worked example), a native grasshopper-mcp-style canvas bridge, tagging components + manual selection, LLM recognition with on-canvas proposal preview/confirm, MERGE-idempotent persistence with ui-v2 layer display, and a script structure-validation MVP; plus upgraded rules ingest/edit, AI-generated script inputs as ParamState payloads, and a DesignState auto-validation investigation. Includes an n8n→OpenClaw orchestration decision gate (spike + ADR, no committed migration).

**Phases planned:** 13 (Phases 28–40, 54 requirements)
→ [Requirements](../REQUIREMENTS.md) | [Roadmap](../ROADMAP.md) | [Phases](../phases/)

---

## v10.0 Script Intelligence (Future)

**Status:** Planned (isolated) — activates via `/gsd-new-milestone` after v9.0 ships
**Defined:** 2026-07-08

The connected LLM becomes an active partner on the Grasshopper canvas: granular wire substrate persistence with topology queries and snapshot diffing, a DG-native component knowledge base, bridge write commands (off by default, KB-validated, undo-batched), cluster introspection, script part generation into tagged slots with on-canvas preview/confirm, script part editing as old→new canvas diffs, graph-native structure-rule grammar, and a multi-turn rule-aware consulting assistant that proposes but never executes.

**Phases planned:** 9 (Phases 41–49, 31 requirements)
→ [Requirements](v10.0-REQUIREMENTS.md) | [Roadmap](v10.0-ROADMAP.md)

---

## v2.0 DG Plugin - Design State and Validation Runs (Shipped: 2026-05-10)

**Phases completed:** 6 phases, 10 plans
**Timeline:** 2026-04-30 → 2026-05-10 (11 days)

**Key accomplishments:**

- Typed design-state capture (Number/Integer/Boolean) with deterministic JSON serialization
- Full persistence chain: DESIGN STATE → Classificator → Validator → Neo4j with state payloads
- VALIDATION RUNS component with rule/state filtering and deterministic output schema
- Trigger-based REINSTATE component with 7-value per-parameter status reporting (Applied, MissingTarget, TypeMismatch, etc.)
- Model Viewer grouping strip with Rule/Design-State switch, collapsible groups, resize handle, localStorage persistence
- E2E hardening: What+Where+How-to-fix error pattern across C# (ErrorMessageTemplates), Python (structured JSON errors), JS (hint extraction)
- 18/18 requirements validated via human UAT

---
