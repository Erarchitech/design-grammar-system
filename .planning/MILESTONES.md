# Milestones

## v8.2 Connector Integration & Reasoning Engine (Shipped: 2026-07-12)

**Phases completed:** 5 phases, 19 plans, 44 tasks
**Closeout:** override closeout — **Known verification overrides: 3** (Phases 822 & 824 in-app/in-Rhino UAT deferred; Phase 823 closed via user-approved checkpoint with no formal VERIFICATION.md — see STATE.md `## Deferred Items`)
**Override status update (2026-07-13 gap-closure session):** 2 of 3 closed — Phase 822's three frontend UAT scenarios executed live and **passed** (822-UAT.md; 822-VERIFICATION.md now `passed`); Phase 823 received a formal retroactive **823-VERIFICATION.md** (`passed`, 4/4 — fresh in-container suites: dg-reasoner 39/39, data-service 168/168, DG 234/234). Phase 824's 3 in-Rhino checks remain the only open item (needs live Rhino/Grasshopper — 824-UAT.md).

**Key accomplishments:**

- **Phase 820** — Resolved the OntoGraph axiom-scoping question as a *hybrid* approach and authored the normative `spec/LPG-OWL-MAPPING.md` (Metagraph SWRL vocabulary, OntoGraph OWL terms, edge-property reification for `ARG.pos` + `HAS_BODY/HAS_HEAD.order`, IRI minting, UNA handling); both decisions recorded as ADRs with spike evidence.
- **Phase 821** — New isolated `dg-reasoner` sidecar (Python 3.11 + headless JRE, internal-only in docker-compose, n10s-equipped neo4j) with a clean `ontology_export.py` Cypher→RDF translator and 8 fidelity tests proving `ARG.pos` and `HAS_BODY/HAS_HEAD.order` survive translation; a short-timeout httpx proxy wires data-service to the sidecar.
- **Phase 822** — Real OWL 2 DL consistency check (HermiT default engine) wired end-to-end into the Reasoner screen, replacing the v8.1 "integration pending" placeholder; `unsatisfiable_classes` enriched to `{iri,label}`; HermiT flipped to `integrated`. Backend gate green (dg-reasoner 19/19, data-service 13/13); manual frontend UAT deferred.
- **Phase 823** — SHACL Validation Layer: 8 version-controlled data-integrity NodeShapes over the run-scoped ValidGraph ABox (with `owl:AllDifferent` UNA), `shaclReportJson` propagated across five spec/config surfaces + `spec/RULE-PARTITION-POLICY.md`; findings surface on the VALIDATOR component (capped Warning/Remark) and a Solibri-style SHACL Data Integrity panel in the ui-v2 Model screen.
- **Phase 824** — CONNECTOR gains an additive platform-token heartbeat with in-canvas Error/Warning feedback and full token secrecy (hashed dedup key, persistent-data scrub, token-free outputs); component GUID and existing ports untouched; whole solution builds green against the Rhino 8 SDK.

---

## v8.1 Platform Setup Regions (Shipped: 2026-07-11)

**Phases completed:** 7 phases, 7 plans (810–816; first milestone on the vX.Y → X·100+Y·10 phase-numbering convention)
**Closeout:** all 7 phases executed and verified 2026-07-11; phase dirs archived to `milestones/v8.1-phases/` 2026-07-12. *(This entry was written 2026-07-13 during the gap-closure session — the formal `/gsd-complete-milestone` pass was skipped at ship time; retroactive VERIFICATION.md docs for Phases 810–813 and the 813 plan summary were added the same session.)*

**Key accomplishments:**

- **Phase 810** — Landing ring extended from 3 to 7 region callouts (AI Engine, Connectors, Reasoner, DG API Docs) with four new navigable screen layers on the standard 520ms fly grammar and back navigation; zero regression to the existing three regions.
- **Phase 811** — AI Engine screen: provider/model/API-key setup over the Phase-28 LLM gateway (`/llm/settings`), key stored encrypted-at-rest and surfaced only as set/not-set, with a connection test.
- **Phase 812** — Connector credential backend in data-service: 14-connector / 5-category registry, server-side `dgc_` tokens returned once and persisted hash-only, token-authenticated heartbeat, never-connected/active/stale status derivation; 18 lifecycle pytest tests.
- **Phase 813** — Connectors screen: category-grouped connector cards with credential creation, copy-once token panel, activation status + last-connection dates, and two-step revoke.
- **Phase 814** — Reasoner screen with HermiT/Pellet selection persisting server-side; placeholders explicitly labeled "integration pending" (replaced for HermiT by real reasoning in v8.2 Phase 822).
- **Phase 815** — DG API Documentation region: Revit-API-style tree + detail browser over structured content modules (`import.meta.glob` auto-registration — new pages need zero viewer-code changes), covering credential auth, heartbeat/status, and validation publish end-to-end.
- **Phase 816** — Integration & deployment: `/reasoner/` nginx + vite proxy routes added, full connector lifecycle proven E2E, container ships all seven regions with v8.0 screens intact (6/6 verification).

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
