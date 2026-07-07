# Milestones

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

## v9.0 AI Workflow Intelligence (Future)

**Status:** Paused — Phase 01 (cloud-llm-connector) executed 2026-07-06 and parked in [v9.0-phases/](v9.0-phases/); resume after v8.0 Design Grammars V2 UI
**Defined:** 2026-07-03

Two axes: (1) LLM infrastructure — provider-agnostic cloud LLM connector (user-supplied API key, Claude/OpenAI-compatible/Ollama-fallback, provider control from the UI) plus a DG-aware context layer injecting ontology V7 concepts, SWRL conventions, and a standard Cypher expression catalog with pre-execution validation; (2) AI implementation workflows — upgraded rules ingest/edit (clarification loops, atom-diff previews, validation-feedback retries), AI recognition of Grasshopper node blocks as Object Behaviour persisted to the Computgraph layer, AI-generated Grasshopper script inputs as ParamState payloads, and a DesignState auto-validation investigation. Includes an n8n→OpenClaw orchestration decision gate (spike + ADR, no committed migration).

**Phases planned:** 8 (36 requirements)
→ [Requirements](v9.0-REQUIREMENTS.md) | [Roadmap](v9.0-ROADMAP.md)

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
