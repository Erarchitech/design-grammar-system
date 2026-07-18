# Requirements: Design Grammar System v9.0 — AI Workflow Intelligence

**Defined:** 2026-07-03
**Restructured:** 2026-07-08 — GHRC family (5 requirements) replaced by CGSR/BRDG/TAGC/RCGN/CGPD/SVAL families (23 requirements) elaborating the Grasshopper canvas → Computgraph serialization pipeline. Script generation/editing/consulting deferred to the v10 seed.
**Extended:** 2026-07-13 — DGID family (6 requirements) added for inserted Phase 32.1 (Cross-Platform Identity and Mapping — DG ID)
**Status:** Paused (Phase 28 complete 2026-07-06)
**Core Value:** The architect controls which LLM runs the Design Grammar System — entering an API key to use a frontier cloud model or staying fully local — and that LLM understands the DG ontology, SWRL conventions, and standard Cypher shapes natively, extending AI assistance onto the Grasshopper canvas itself: the graph context of a script serializes into the ontology's Computgraph layer through architect tagging + LLM recognition + on-canvas confirmation, becomes browsable and structurally validatable against Design Rules, and drives generated script inputs.

---

## v9.0 Requirements

### Cloud LLM Connector (LLMC) — Phase 28 ✅

- [x] **LLMC-01**: A provider-agnostic LLM gateway in data-service exposes one generate contract with adapters for Anthropic Claude, OpenAI-compatible APIs, and local Ollama — all LLM traffic in the system routes through it
- [x] **LLMC-02**: The user can enter, update, test, and remove an API key and select provider + model from the UI settings panel; saving a key triggers a live validation call with clear success/failure feedback
- [x] **LLMC-03**: API keys are stored encrypted at rest (master secret via environment variable), never written to Neo4j, browser localStorage, or logs; the UI shows only a masked key indicator
- [x] **LLMC-04**: All existing LLM call sites (rules ingest workflow, graph-query workflow) are rewired to the gateway — no direct Ollama HTTP calls remain in orchestrator workflows
- [x] **LLMC-05**: With no API key configured, the system falls back to local Ollama with behavior identical to pre-v9.0 — full offline capability is preserved
- [x] **LLMC-06**: Provider errors (invalid key, quota exhausted, timeout, model unavailable) surface in the UI as actionable messages following the What+Where+How-to-fix pattern

### DG-Aware Context Layer (CTXA) — Phase 29

- [x] **CTXA-01**: Prompt assembly injects the relevant subset of the DG ontology V7 concept catalog (per graph layer: Ontograph, Metagraph, Validgraph, Computgraph) into every ingest and query request
- [x] **CTXA-02**: A versioned standard Cypher expression catalog covers the common rule shapes (max/min limit, range, ratio, boolean requirement, existence/count) with worked SWRL + Cypher examples, injected as few-shot context per request type
- [x] **CTXA-03**: SWRL conventions (violation-inverted body semantics, atom ordering, Var/Literal argument rules) exist in machine-readable form and are part of the assembled context
- [x] **CTXA-04**: Generated Cypher is validated against the current schema template (labels, relationship types, kind enums, property names, bracket nesting) before execution; violations return as structured feedback driving a bounded automatic retry loop
- [x] **CTXA-05**: Context selection is deterministic — schema and catalog lookup only, no embeddings (consistent with the standing no-RAG decision; revisit only if the deterministic layer proves insufficient)

### Orchestration Evaluation (ORCH) — Phase 30

- [ ] **ORCH-01**: A documented evaluation matrix compares n8n and OpenClaw on webhook parity, function-node equivalents, LLM provider support, self-host Docker footprint, state/retry handling, maintenance burden, and migration cost
- [ ] **ORCH-02**: A working spike ports the graph-query workflow to OpenClaw against the live stack behind the existing Nginx proxy contract
- [ ] **ORCH-03**: An ADR records the go/no-go decision with explicit criteria; a no-go leaves n8n untouched and closes the question for this milestone
- [ ] **ORCH-04**: On a go decision, the migration plan moves one workflow at a time with n8n running in parallel as fallback until end-to-end parity is verified — no big-bang cut-over

### Rules Ingestion and Editing (RING) — Phase 31

- [ ] **RING-01**: The upgraded ingest workflow (gateway + context layer + validation retry) achieves a pass-rate on the reference rule set ≥ the measured Ollama baseline
- [ ] **RING-02**: Editing a rule shows an atom-level old→new diff preview before commit; confirming applies with old-atom MATCH-DELETE cleanup intact; cancelling leaves the graph unchanged
- [ ] **RING-03**: Ambiguous rules (missing limit, unknown concept, ambiguous unit) trigger a clarification question to the user instead of a guessed graph
- [ ] **RING-04**: Failed Cypher validation auto-retries with validator feedback up to a bounded attempt count, then surfaces an actionable error — never executes invalid Cypher
- [ ] **RING-05**: The full ingest/edit flow still works on the local Ollama fallback path (regression-verified)

### Computgraph Serialization Core (CGSR) — Phase 32

- [x] **CGSR-01**: A GH-free object model in DG.Core mirrors the ontology's Computgraph layer — Algorithm, Procedure, Pattern (nestable), Parameter (Variable/Constant/Emergent kinds, dataType, slider domain), Interface (Input/Output), plus raw canvas nodes and wires — unit-tested without the Grasshopper SDK
- [x] **CGSR-02**: The DG Canvas Annotation Convention (scribbles `OBJECT - <NAME>` / `<n>_ALGORITHM`; groups `<NN>_Proc - <Name>`, `<NN>_Pat_<k>`, `<NN>_Var_<Name>`, `<NN>_Const_<Name>`, `<NN>_Emg_<Name>`, `<NN>_IntF_<Name>`) parses into typed Computgraph entities; non-conforming names classify as untagged — never guessed
- [x] **CGSR-03**: A canvas extractor serializes the live GH_Document — components, parameters (with slider domains), group membership including nesting, scribbles, and wire topology — into a versioned `cgContextJson v1` envelope
- [x] **CGSR-04**: The annotated Frame reference definition serializes to a structure matching its OWL named individuals (`dg:Object_Frame` → `dgc:Algorithm_1` → `dgc:Proc_11`/`Proc_12` with their patterns, parameters, interfaces), verified by an xUnit fixture

### Cross-Platform Identity and Mapping (DGID) — Phase 32.1

- [x] **DGID-01**: Every design object extracted into the Computgraph (Object, Procedure, Pattern, Parameter, Interface) carries a platform-neutral `dgId` that is deterministic across re-extractions of the same definition, unique within a project, and documented in a versioned identity spec (`spec/DG-ID.md`: format, minting, rename/stability rules, collision policy)
- [ ] **DGID-02**: A Neo4j identity registry binds each `dgId` to its per-platform representations (Grasshopper instance GUID, Revit UniqueId/ElementId, IFC GlobalId, Speckle applicationId) with connector provenance; representations attach and detach without changing the `dgId`
- [ ] **DGID-03**: Counterpart objects across platforms resolve to one identity within a Design State — a Revit BIM wall generated from a Grasshopper parametric wall binds to the wall's existing `dgId`, and DesignState/ObjState payloads reference member objects by `dgId`
- [ ] **DGID-04**: Properties computed on one platform attach to the shared identity and are readable from any bound representation — e.g. a Ladybug-derived insulation value written from Grasshopper is readable for the Revit panel representation — with every shared-property write carrying platform/connector/timestamp provenance
- [ ] **DGID-05**: data-service exposes an identity API (mint/resolve/bind + shared-property read/write) over parameterized, project-isolated Cypher; unresolvable or ambiguously bound native ids return structured What+Where+How-to-fix errors, never a silent misbinding
- [x] **DGID-06**: The identity scheme is recorded in an ADR against the surveyed state of the art (Rhino.Inside.Revit element tracking/binding, Speckle applicationId vs hash id, IFC GlobalId, Revit UniqueId episode+ElementId, BHoM adapter ids) with explicit rationale for the DG connector architecture

### DG Canvas Bridge (BRDG) — Phase 33

- [x] **BRDG-01**: A DG CANVAS LISTENER component hosts a TCP listener (configurable port, default 8720) speaking the grasshopper-mcp wire protocol (newline-terminated JSON `{type, parameters}`) with commands `get_canvas_context`, `get_selection`, `preview_structure`, `clear_preview`, `get_preview_status`
- [x] **BRDG-02**: data-service pulls the live canvas context from Rhino through a bridge client (`GH_BRIDGE_HOST`/`GH_BRIDGE_PORT` env, `host.docker.internal` from Docker) via `POST /computgraph/context/pull`
- [x] **BRDG-03**: The existing `POST /mcp` JSON-RPC server exposes `gh_get_context`, `gh_get_selection`, `gh_preview_structure`, `gh_clear_preview` tools so any MCP client (including the connected LLM) can read and preview against the canvas
- [x] **BRDG-04**: The bridge is safe and diagnosable: canvas access marshalled to the UI thread, bounded timeouts, clean socket shutdown on toggle-off, and listener-unreachable errors surfaced with the What+Where+How-to-fix pattern

### Ontology Tagging Components (TAGC) — Phase 34

- [x] **TAGC-01**: A DG OBJECT MARKER component creates/updates the `OBJECT - <NAME>` and `<n>_ALGORITHM` scribbles (optionally bound to a `dg:Class` IRI) and reads existing markers without duplicating
- [x] **TAGC-02**: A DG ENTITY TAG component wraps the current manual canvas selection into a convention-named, convention-colored group for a chosen entity kind (Proc/Pat/Var/Const/Emg/IntF) with automatic index assignment, undoable via undo records
- [x] **TAGC-03**: Manual tags round-trip as ground truth: tagged entities appear in `cgContextJson` with `source: tagged` and are parsed identically by the serializer on every re-run

### LLM Recognition and Proposal Preview (RCGN) — Phase 35

- [ ] **RCGN-01**: A recognition pipeline classifies untagged canvas entities into Computgraph proposals via the LLM gateway, using the architect's tags as ground-truth anchors plus the Computgraph concept catalog and the Frame few-shot example; output is schema-validated (kind, name, member ids, confidence, rationale) with a bounded retry loop
- [ ] **RCGN-02**: Proposals render on the Grasshopper canvas as temporary preview groups and scribbles in a visually distinct style, created inside an undo record — fully removable via undo or `clear_preview`
- [ ] **RCGN-03**: The architect confirms, partially accepts, or rejects proposals on the canvas (DG STRUCTURE CONFIRM); accepted proposals convert to permanent convention groups indistinguishable from manual tags (with `source: recognized` provenance); rejected ones are removed cleanly
- [ ] **RCGN-04**: Nothing is published to Neo4j without explicit on-canvas confirmation; blocks the LLM cannot classify are reported as unrecognized with member ids — never invented, never silently dropped

### Computgraph Persistence and Display (CGPD) — Phase 36

- [ ] **CGPD-01**: `POST /computgraph/publish` persists a confirmed structure to Neo4j as the Computgraph layer — labels `Object|Behavior|Algorithm|Procedure|Pattern|Parameter|Interface` with `graph:'Computgraph'` and project isolation; relationships `HAS_BEHAVIOR`, `HAS_ALGORITHM`, `HAS_PROCEDURE`, `HAS_PATTERN`, `PATTERN_HOST_TO`, `HAS_PARAMETER`, `HAS_INTERFACE`, `PARAM_LINK`
- [ ] **CGPD-02**: Publishing is MERGE-idempotent on stable entity ids (definition id + convention name): re-publishing the same definition creates zero duplicate nodes (verified by count query)
- [ ] **CGPD-03**: Every published node carries provenance — `source` (tagged | recognized), provider/model when recognized, definition id, timestamp — queryable via Cypher
- [ ] **CGPD-04**: The ui-v2 graph viewer renders the Computgraph layer with distinct styling, filterable per project; the schema propagation checklist (`cypher_template.txt`, `dataset_schema.json`, `spec/DATABASE.md`, CLAUDE.md, orchestrator prompts) is completed for the new labels
- [ ] **CGPD-05**: A publish path exists from the plugin (DG COMPUTGRAPH PUBLISH trigger following the ValidationPublishClient HTTP pattern) so the confirm→publish flow completes without leaving Grasshopper

### Script Structure Validation (SVAL) — Phase 37

- [ ] **SVAL-01**: Deterministic, LLM-free structural checks run over the published Computgraph via Cypher — convention compliance, orphan Patterns, Procedures without Interfaces, untyped Parameters, dangling links — each finding referencing the exact entities
- [ ] **SVAL-02**: Design Rules can be mapped to script-structure requirements (e.g. required Procedure/Parameter presence) and evaluated over the Computgraph, reported pass/fail per rule with supporting entities
- [ ] **SVAL-03**: `POST /computgraph/consult` answers natural-language questions about a published script structure using Computgraph context through the gateway — answers grounded in graph entities, read-only

### Grasshopper Input Generation (GHIN) — Phase 38

- [ ] **GHIN-01**: Given a rule (or design-intent text) plus the published Computgraph Parameter structure, AI proposes candidate input parameter sets for the Grasshopper script, respecting serialized slider domains
- [ ] **GHIN-02**: Candidates are ParamState-compatible payloads (Number/Integer/Boolean only, per the standing v2.0 typed-state decision) applicable through the existing PARAMETER REINSTATE component
- [ ] **GHIN-03**: Every generated candidate carries provenance: source rule, provider/model, timestamp — queryable in the graph
- [ ] **GHIN-04**: Generation and application are strictly separated — nothing reaches the canvas without explicit user acceptance of a candidate

### DesignState Auto-Validation Investigation (DSAV) — Phase 39

- [ ] **DSAV-01**: An investigation note compares trigger architectures (GH capture-time hook, data-service watcher, Neo4j write event) with latency, publish-flood, and Speckle-noise analysis
- [ ] **DSAV-02**: A prototype demonstrates at least one path end-to-end: capturing a new DesignState produces a validation Run without a manual VALIDATOR trigger
- [ ] **DSAV-03**: An ADR records the chosen architecture and guardrails (debounce window, per-project rate limit, per-project opt-in flag) and scopes full implementation to a follow-up milestone

### Integration (INTG) — Phase 40

- [ ] **INTG-01**: E2E on live Docker with a cloud provider: NL rule → context-assembled ingest → validated Cypher → graph → Grasshopper validation → Speckle publish
- [ ] **INTG-02**: Switching provider (Claude ↔ OpenAI-compatible ↔ Ollama) requires only the settings panel — no container restarts, no workflow edits
- [ ] **INTG-03**: E2E GH intelligence chain: object marked + entities tagged → LLM recognition → on-canvas preview → confirmed → published to Computgraph → structure-validated → accepted generated inputs applied via PARAMETER REINSTATE → validation run recorded
- [ ] **INTG-04**: CLAUDE.md, spec/, and DG_OBSIDIAN document the gateway, settings, bridge, annotation convention, Computgraph layer, new GH components, and the Phase 30/39 ADRs; graphify refreshed

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| AI *generation* of Grasshopper script parts, on-canvas editing, consulting assistant | **v10 Script Intelligence seed** (`.planning/milestones/v10.0-SEED.md`) — v9.0 delivers the bridge, Computgraph, and validation foundations it builds on; bridge write-commands (`add_component`, `connect_components`) are explicitly deferred |
| Fine-tuning cloud LLMs | Prompt + context-layer approach continues (standing decision); `training/` LoRA assets remain local-Ollama-only |
| Embedding-based RAG for context retrieval | Deterministic schema/catalog lookup first — consistent with the v1.1 no-RAG decision; revisit only with evidence it's insufficient |
| Multi-user API key management / billing / quotas | Single key per deployment; the system is single-team self-hosted |
| Token-streaming UI | Async polling pattern already in place; streaming adds complexity without workflow value |
| Committed n8n→OpenClaw migration | Phase 30 is a decision gate; migration executes only on an explicit go, and full cut-over may land in a later milestone |
| DesignState auto-validation full implementation | Investigation + prototype + ADR only (DSAV); production implementation is scoped by the ADR into a follow-up milestone |
| Non-parametric input generation (geometry, text, trees) | ParamState payloads stay Number/Integer/Boolean per the v2.0 deterministic-reinstatement decision |
| GH Cluster introspection (patterns inside clusters) | Convention maps Procedures to Groups; cluster internals are opaque in v9.0 — revisit with v10 |
| Vendoring the third-party GH_MCP plugin | Native bridge decision (below); grasshopper-mcp is the protocol reference, not a dependency |
| Revit connector implementation | Phase 32.1 defines the DG ID contract, registry, and identity API and proves them with a simulated second-platform consumer; the real Revit-side connector lands in a future milestone (dedicated connector milestone / v4.0 BOT bridge) |

---

## Key Decisions (v9.0)

| Decision | Rationale |
|----------|-----------|
| Single LLM gateway in data-service, not per-workflow provider nodes | One place for adapters, retries, key handling, and usage accounting; orchestrator stays thin |
| Ollama retained as zero-config fallback | Preserves offline capability and the current default behavior; cloud is opt-in via key |
| Keys encrypted server-side, never client-persisted | API keys are credentials, not preferences — localStorage and Neo4j are the wrong trust boundary |
| OpenClaw evaluated behind a decision gate, not adopted upfront | n8n works today; replacement must prove webhook/workflow parity in a spike before any migration |
| **Native canvas bridge** — grasshopper-mcp *pattern* (TCP listener + JSON commands) re-implemented inside the DG plugin, adapted to DG needs | No second plugin on the canvas, no divergent fork to maintain; full control over the DG-specific serialization format; data-service reuses its existing `/mcp` server and Phase-01 gateway (confirmed 2026-07-08) |
| **DG Canvas Annotation Convention is the contract** between architect, serializer, and LLM | Groups/scribbles named `OBJECT/ALGORITHM/NN_Proc/NN_Pat/Var/Const/Emg/IntF` map 1:1 to `dgc:` classes; the Frame example exists as OWL named individuals, giving fixture, convention, and ontology a single source of truth (confirmed 2026-07-08) |
| **Tag → recognize → preview → confirm → publish**, in that order | The architect's manual tags are ground truth; the LLM only fills gaps; nothing reaches Neo4j without on-canvas confirmation — mirrors the RING clarification-over-guessing principle |
| GH recognition writes to the Computgraph layer (`dgc:`) | The ontology reserved this layer for exactly this ("translation of design grammars into/from parametric definitions"); v9.0 is its first runtime consumer |
| **Durable DG IDs are the cross-platform identity spine** — native platform ids (GH instance GUID, Revit UniqueId/ElementId, IFC GlobalId, Speckle applicationId) are representations *bound to* a dgId, never the identity itself | A GH parametric wall and the Revit wall generated from it are one design object in DG; no single-platform id survives the platform boundary, and cross-platform state (e.g. Ladybug-computed insulation surfacing on the Revit panel) needs an id that does (confirmed 2026-07-13) |
| Generated inputs ride the existing ParamState → PARAMETER REINSTATE path | No parallel apply mechanism; reuse of the v7.0 state pipeline keeps provenance and status reporting |
| Auto-validation is investigation-first | Trigger architecture and publish-flood guardrails must be prototyped before committing component changes |
| Structure validation MVP is deterministic-first | Cypher checks + rule mapping are reproducible; the LLM only serves the read-only `/consult` endpoint — v10 expands from this seam |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LLMC-01 … LLMC-06 | Phase 28 | ✅ Complete (2026-07-06) |
| CTXA-01 … CTXA-05 | Phase 29 | Pending |
| ORCH-01 … ORCH-04 | Phase 30 | Pending |
| RING-01 … RING-05 | Phase 31 | Pending |
| CGSR-01 … CGSR-04 | Phase 32 | ✅ Complete (2026-07-18) |
| DGID-01 … DGID-06 | Phase 32.1 | Pending |
| BRDG-01 … BRDG-04 | Phase 33 | Pending |
| TAGC-01 … TAGC-03 | Phase 34 | Pending |
| RCGN-01 … RCGN-04 | Phase 35 | Pending |
| CGPD-01 … CGPD-05 | Phase 36 | Pending |
| SVAL-01 … SVAL-03 | Phase 37 | Pending |
| GHIN-01 … GHIN-04 | Phase 38 | Pending |
| DSAV-01 … DSAV-03 | Phase 39 | Pending |
| INTG-01 … INTG-04 | Phase 40 | Pending |

**Coverage:**

- v9.0 requirements: 60 total (6 complete, 54 pending)
- Mapped to phases: 60
- Unmapped: 0

---

*Requirements defined: 2026-07-03; restructured 2026-07-08 — GHRC replaced by CGSR/BRDG/TAGC/RCGN/CGPD/SVAL (Computgraph serialization pipeline)*
