# Roadmap: Design Grammar System

## Milestones

- ✅ **v8.2 Connector Integration & Reasoning Engine** — Phases 820-824 (shipped 2026-07-12; override closeout resolved 2026-07-13: 822 frontend UAT passed live + 823 retroactive VERIFICATION written — only 824's 3 in-Rhino checks remain deferred; wired Grasshopper CONNECTOR to platform-issued credentials and replaced Reasoner placeholders with real OWL 2 DL (HermiT) + SHACL validation via a new isolated `dg-reasoner` sidecar) → [requirements](milestones/v8.2-REQUIREMENTS.md) | [roadmap](milestones/v8.2-ROADMAP.md) | [phases](milestones/v8.2-phases/)
- ✅ **v8.1 Platform Setup Regions** — Phases 810-816 (shipped 2026-07-11; all 7 phases executed and verified; first milestone on the vX.Y → X·100+Y·10 phase-numbering convention; formal milestone record completed 2026-07-13 — MILESTONES.md entry + retroactive VERIFICATION.md for Phases 810–813) → [requirements](milestones/v8.1-REQUIREMENTS.md) | [roadmap](milestones/v8.1-ROADMAP.md) | [phases](milestones/v8.1-phases/)
- ✅ **v8.0 Design Grammars V2 UI** — Phases 21-27 (shipped 2026-07-07; Phase 27 Speckle 3D Embed added post-ship, completed 2026-07-08) → [requirements](milestones/v8.0-REQUIREMENTS.md) | [roadmap](milestones/v8.0-ROADMAP.md) | [phases](milestones/v8.0-phases/)
- 🔄 **v9.0 AI Workflow Intelligence** — Phases 28-40 (active — reactivated 2026-07-12; Phase 28 shipped 2026-07-06; restructured 2026-07-08: GH canvas → Computgraph serialization pipeline elaborated into Phases 32-37; Phase 29 next)
- 📋 **v10.0 Script Intelligence** — Phases 41-49 (planned 2026-07-08, isolated; activates after v9.0; renumbered from milestone-local 1-9) → [requirements](milestones/v10.0-REQUIREMENTS.md) | [roadmap](milestones/v10.0-ROADMAP.md)
- 📋 **v4.0 BOT Ontology Bridge** — Phases 1-4 (planned) → [requirements](milestones/v4.0-REQUIREMENTS.md) | [roadmap](milestones/v4.0-ROADMAP.md)
- ✅ **v7.0 Update of DG Addin for Grasshopper** — Phases 13-20 (shipped 2026-07-05) → [requirements](milestones/v7.0-REQUIREMENTS.md) | [roadmap](milestones/v7.0-ROADMAP.md) | [phases](milestones/v7.0-phases/)
- ⛔ **v3.0 Typed Variables and Composable Design State** — Superseded 2026-07-02 (Phase 7 shipped, carried into v7.0) → [archive](milestones/v3.0-ROADMAP.md)
- ✅ **v2.0 DG Plugin - Design State and Validation Runs** — Phases 1-6 (shipped 2026-05-10) → [archive](milestones/v2.0-ROADMAP.md)
- ✅ **v1.1 Project Knowledge Graph** — Phases 1-7 (shipped 2026-04-10) → [archive](milestones/v1.1-phases/)

---

*v8.1 Platform Setup Regions detail archived to `milestones/v8.1-ROADMAP.md` on 2026-07-11 (all 7 phases complete and verified; phase dirs 810-816 archived to `milestones/v8.1-phases/` on 2026-07-12).*
*v8.2 Connector Integration & Reasoning Engine detail archived to `milestones/v8.2-ROADMAP.md` on 2026-07-12 (5 phases, 19 plans; override closeout — Phases 822/823/824 verification deferred, see `MILESTONES.md` + `STATE.md` Deferred Items). Update 2026-07-13: 822 + 823 overrides closed (live UAT pass + retroactive verification); only 824's in-Rhino UAT remains.*

---

## v9.0 — AI Workflow Intelligence

**Planned:** 2026-07-03
**Restructured:** 2026-07-08 — Grasshopper canvas → Computgraph serialization elaborated: former Phase 5 (GH node recognition) expanded into Phases 32–37; former input-generation/auto-validation/E2E phases renumbered to 38/39/40. Script *generation/editing/consulting* deferred to v10.0 (`.planning/milestones/v10.0-ROADMAP.md`).
**Renumbered:** 2026-07-08 — global phase numbering adopted: milestone-local 1–13 → **28–40**, continuing from v8.0's Phase 27 (repo convention: phase numbers continue across milestones).
**Reactivated:** 2026-07-12 — resumed after v8.1/v8.2 shipped; phase directories moved from `milestones/v9.0-phases/` into `.planning/phases/` unchanged, requirements restored to `.planning/REQUIREMENTS.md`.
**Extended:** 2026-07-13 — Phase 32.1 (Cross-Platform Identity and Mapping — DG ID) inserted after Phase 32; DGID requirement family (6 requirements) added. Extracted Computgraph objects carry a durable platform-neutral DG ID binding counterpart representations across connectors (Grasshopper ↔ Revit/IFC/Speckle) within one Design State.
**Status:** Active (Phase 28 shipped 2026-07-06; Phase 29 next)
**Depends on:** v7.0 (VALIDATOR rework, composed DesignState, PARAMETER REINSTATE, graph schema v4 — shipped 2026-07-05). v8.0 shipped 2026-07-07 — all UI deliverables in this roadmap target **`ui-v2/`** (the legacy `graph-viewer/` SPA is archived; Phase 28's settings panel predates the cutover and is revisited in the Phase 40 docs pass).

### Overview

v9.0 upgrades the intelligence layer of the Design Grammar System along two axes:

1. **LLM infrastructure** — a provider-agnostic **cloud LLM connector** (Phase 28, ✅ built): the user enters an API key in the UI and controls which LLM (Anthropic Claude, OpenAI-compatible, or local Ollama fallback) manages Design Grammars. On top sits a **DG-aware context layer** (Phase 29) making every LLM call ontology-aware, and the rules ingest/edit pipeline is rebuilt on it (Phase 31), with an orchestration decision gate (Phase 30).

2. **Grasshopper canvas intelligence** — the ontology's **Computgraph layer** (`dgc:` in `ontology/DesignGrammar-V7.owl`) gets its first runtime consumer. The graph context of a Grasshopper script is serialized to Neo4j as `Object → Behavior → Algorithm → Procedure → Pattern → Parameter/Interface`, via a pipeline the architect controls end-to-end on the canvas:
   - **Serialization core** (Phase 32): GH_Document traversal + the DG Canvas Annotation Convention parser (`OBJECT - FRAME`, `1_ALGORITHM`, `11_Proc`, `11_Pat_*`, `11_Var_/Const_/Emg_/IntF_*` — the Frame worked example, already modeled as OWL named individuals).
   - **Cross-platform identity — DG ID** (Phase 32.1): every extracted design object carries a durable, platform-neutral `dgId`; native platform ids (GH instance GUID, Revit UniqueId, IFC GlobalId, Speckle applicationId) are *representations* bound to it in an identity registry, so counterpart objects (GH parametric wall ↔ generated Revit BIM wall) resolve to one identity within a Design State and share cross-platform properties (e.g. Ladybug-computed insulation readable from the Revit panel representation).
   - **DG Canvas Bridge** (Phase 33): a native adaptation of the [grasshopper-mcp](https://github.com/alfredatnycu/grasshopper-mcp) pattern — a TCP listener component in the DG plugin + a bridge client and `gh_*` MCP tools in data-service.
   - **Tagging components** (Phase 34): the architect marks known ontological entities on canvas (components + manual selection).
   - **LLM recognition + on-canvas preview** (Phase 35): AI guesses the untagged rest; the proposal appears as temporary groups/scribbles on the canvas for confirmation **before anything is published**.
   - **Persistence + display** (Phase 36): MERGE-idempotent Computgraph writes, project-isolated, with provenance; ui-v2 Computgraph layer view.
   - **Structure validation MVP** (Phase 37): Design Rules mapped to script structure — deterministic Cypher checks + an LLM consult endpoint. This is the seam v10.0 Script Intelligence (generate/edit/consult) builds on.

Plus **AI-generated script inputs** (Phase 38, rides Computgraph parameters), the **DesignState auto-validation investigation** (Phase 39), and **E2E + docs** (Phase 40).

**14 phases (28–40 + 32.1), estimated ~17–21 implementation sessions.**

### Phases

### Phase 28: Cloud LLM Connector and Provider Abstraction ✅

**Goal:** Every LLM call in the system goes through one provider-agnostic gateway; the user controls provider, model, and API key from the UI, and the system falls back to local Ollama when no key is configured.

**Requires:** No prior v9.0 phases (foundation for everything else).

**Requirements:** LLMC-01, LLMC-02, LLMC-03, LLMC-04, LLMC-05, LLMC-06

**Deliverables:** (built 2026-07-06)

- `data-service/llm_gateway.py` — provider adapters (Anthropic Claude, OpenAI-compatible, Ollama) behind one `POST /llm/generate` contract
- `data-service/app.py` — gateway endpoint + `GET/PUT/DELETE /llm/settings` + `POST /llm/settings/test` + `GET /llm/models`
- Encrypted-at-rest key storage (Fernet, `LLM_MASTER_SECRET` env; key never in Neo4j, localStorage, or logs)
- LLM settings panel (built in legacy `graph-viewer/index.html` pre-v8.0 cutover — ui-v2 port tracked in Phase 40)
- n8n workflows rewired to the gateway; pytest coverage

**Success Criteria:** met — see `.planning/phases/28-cloud-llm-connector/28-VERIFICATION.md`

**Plans:** 3 plans (complete)

- [x] 28-01-PLAN.md — Gateway Core
- [x] 28-02-PLAN.md — n8n Workflow Rewiring
- [x] 28-03-PLAN.md — UI Settings Panel

---

### Phase 29: DG-Aware Context Layer (SWRL + Ontology + Cypher Awareness)

**Goal:** LLM calls stop relying on a single static prompt — every ingest/query request is assembled from the V7 ontology catalog (now including Computgraph concepts), SWRL violation-pattern conventions, and a standard Cypher expression catalog, and every generated Cypher statement is schema-validated before it touches Neo4j.

**Requires:** Phase 28 (context layer assembles prompts behind the gateway).

**Requirements:** CTXA-01, CTXA-02, CTXA-03, CTXA-04, CTXA-05

**Deliverables:**

- `data-service/dg_context.py` — deterministic context assembler: selects relevant ontology V7 concepts per layer (Ontograph / Metagraph / Validgraph / **Computgraph**), SWRL atom patterns, and Cypher templates for the request type
- `llm/cypher_catalog.json` (new, versioned) — parameterized standard Cypher expressions for common rule shapes: max/min limit, range, ratio, boolean requirement, existence/count — each with a worked SWRL + Cypher example
- SWRL convention block in machine-readable form (violation-inverted body semantics, atom ordering, Var/Literal argument rules)
- Computgraph concept catalog block (dgc: classes, relations, enum values, the annotation-convention grammar) — consumed by Phase 35 recognition prompts
- `data-service` Cypher validator — checks generated Cypher against the current schema template (labels, relationship types, `kind` enums, property names, bracket nesting) and returns structured violations for the retry loop
- n8n prompt nodes reduced to thin callers of the context assembler

**Success Criteria:**

1. The ingest prompt for a "maximum height" rule demonstrably contains the max-limit Cypher template and the V7 concepts it references (inspectable via a debug endpoint)
2. Deliberately corrupting the LLM output (wrong label, wrong kind value) is caught by the validator before execution and returned as a structured violation list
3. Context selection is fully deterministic — same request, same context, no embeddings involved
4. A natural-language graph query about design states answers correctly using v4 `kind` values with the new context layer active

**Plans:** 8/8 plans complete
**Wave 1**

- [x] 29-01-PLAN.md — Cypher expression catalog (`llm/cypher_catalog.json`, 6 shapes) + `dg_context.py` defensive loader (CTXA-02)
- [x] 29-02-PLAN.md — `dg_knowledge.py`: machine-readable SWRL conventions + Computgraph concept catalog parsed from DesignGrammar-V7.owl (CTXA-03, CTXA-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 29-03-PLAN.md — deterministic context assembler + `/context/assemble` + `/context/debug`; rule_edit Rule_Id convention resolved (CTXA-01, CTXA-05)

**Wave 3** *(unblocked — Wave 2 complete)*

- [x] 29-04-PLAN.md — Cypher validator + bounded retry loop + `/context/generate-cypher` (CTXA-04)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 29-05-PLAN.md — n8n prompt nodes reduced to thin callers + `spec/DATABASE.md` catalog note (CTXA-01, CTXA-04)

**Wave 5** *(gap closure — UAT Success Criterion 4: "no design states were found" for ConfigurationC; root cause = assembler described aspirational :DesignState/:Run nodes, real shipped shape is :ValidationRun + statePayloadJson blob + HAS_ENTITY)*

- [x] 29-06-PLAN.md — converge `dg_context.py` VALIDGRAPH_CONCEPTS + `validate_cypher()` allow-lists to the real ValidationRun/statePayloadJson/HAS_ENTITY shape + live `fetch_existing_design_states()` helper (CTXA-01, CTXA-04)
- [x] 29-07-PLAN.md — forward `existing_design_states` into the n8n graph-query Cypher prompt + live re-sync (CTXA-01)
- [x] 29-08-PLAN.md — deploy + human-verify re-run of UAT Success Criterion 4 for ConfigurationC (CTXA-01, CTXA-04)

---

### Phase 30: Orchestration Evaluation — n8n vs OpenClaw

**Goal:** A grounded go/no-go decision on replacing n8n with OpenClaw as the orchestration layer, backed by a working spike — not opinion.

**Requires:** Phase 28. Can run parallel to Phase 29.

**Requirements:** ORCH-01, ORCH-02, ORCH-03, ORCH-04

**Deliverables:**

- Evaluation matrix: webhook parity, function-node equivalents, LLM provider support, self-host Docker footprint, state/retry handling, maintenance and community health, migration cost — n8n vs OpenClaw
- Spike: the `graph-query` workflow ported to OpenClaw against the live stack, exercising the same `/n8n/webhook/dg/graph-query` contract behind the Nginx proxy
- ADR in `DG_OBSIDIAN/knowledge/decisions/` recording the decision with explicit criteria
- If go: phased migration plan — one workflow at a time, n8n kept running in parallel until parity is verified

**Success Criteria:**

1. The spike answers with evidence: can OpenClaw serve the DG webhook workflows (request → LLM gateway → Neo4j → response) with equivalent latency and error handling?
2. The ADR states go/no-go, the criteria that decided it, and — on go — which milestone executes the migration
3. No production workflow is switched in this phase; n8n remains the active orchestrator throughout v9.0 unless the ADR explicitly schedules cut-over inside Phase 31

**Plans:** TBD

---

### Phase 31: Rules Ingestion and Editing Workflow Upgrade

**Goal:** The rules ingest and edit workflows exploit the cloud LLM and context layer: ambiguity triggers clarification instead of guessing, edits preview atom-level changes before committing, and failed generations self-correct through validator feedback.

**Requires:** Phases 28–29; Phase 30 ADR (determines whether the upgraded workflows are built in n8n or OpenClaw).

**Requirements:** RING-01, RING-02, RING-03, RING-04, RING-05

**Deliverables:**

- Upgraded ingest workflow: gateway + context assembler + validator-feedback retry loop (bounded attempts, then actionable error)
- Clarification loop: ambiguous rules return a clarification question to the UI instead of a guessed graph
- Edit flow with preview: proposed atom changes rendered as old→new diff in the ui-v2 Graph screen before the MATCH-DELETE + re-create commit
- Regression suite: reference rule set from `test/` fixtures run through both cloud and Ollama paths

**Success Criteria:**

1. The reference rule set ingests with a pass-rate ≥ the current Ollama baseline (measured, not assumed), and cloud-path results validate against the schema template with zero manual fixes
2. Submitting "the building must not be too tall" yields a clarification question (which limit?), not a fabricated rule
3. Editing a rule shows the atom diff; confirming applies it with old-atom cleanup intact; cancelling leaves the graph unchanged
4. Disabling the API key mid-session degrades gracefully to Ollama with a visible provider indicator — no broken workflow state

**Plans:** TBD

---

### Phase 32: Computgraph Serialization Core

**Goal:** The graph context of a live Grasshopper definition — components, parameters, wires, groups, scribbles — serializes into a versioned, ontology-shaped JSON document (`cgContextJson v1`), with the DG Canvas Annotation Convention parsed into typed Computgraph entities. Pure logic, no LLM, no network.

**Requires:** Nothing in v9.0 (LLM-free; can start immediately). v7.0 plugin architecture (milestone prerequisite).

**Requirements:** CGSR-01, CGSR-02, CGSR-03, CGSR-04

**Deliverables:**

- `DG/src/DG.Core/Models/Computgraph/` — GH-free object model mirroring the OWL: `CgObject`, `CgAlgorithm`, `CgProcedure`, `CgPattern` (nestable), `CgParameter` (kind: Variable/Constant/Emergent; dataType: Float/Integer/Text/Boolean/Geometry; slider domain where present), `CgInterface` (Input/Output), `CgNode` (raw canvas component), `CgWire`
- `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` — convention grammar: scribbles `OBJECT - <NAME>` / `<n>_ALGORITHM`; groups `<NN>_Proc - <Name>`, `<NN>_Pat_<k>[ <name>]`, `<NN>_Var_<Name>`, `<NN>_Const_<Name>`, `<NN>_Emg_<Name>`, `<NN>_IntF_<Name>`; non-conforming names classify as *untagged*, never guessed
- `DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs` — versioned `cgContextJson v1` envelope (System.Text.Json, camelCase — same conventions as `DesignStatePayloadV2Serializer`)
- `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` (`#if GRASSHOPPER_SDK`) — GH_Document traversal: `GH_Document.Objects`, `GH_Group.ObjectIDs` (incl. group nesting), `GH_Scribble`, wire topology via `IGH_Param.Sources`, slider domains, component GUIDs/names/nicknames/positions
- xUnit fixture in `DG/tests/DG.Tests/`: the Frame example (screenshot ↔ `dg:Object_Frame` / `dgc:Algorithm_1` / `dgc:Proc_11`+`Proc_12` OWL individuals) as a serialized document

**Success Criteria:**

1. Parsing the annotated Frame fixture yields exactly: 1 Object ("FRAME"), 1 Algorithm, 2 Procedures ("11_Proc - 2D Truss Configuration", "12_Proc - 2D Footer Configuration"), the patterns/parameters/interfaces named in the convention — matching the OWL named individuals
2. A group named outside the convention lands in the *untagged* set with its raw components intact — nothing is invented
3. The serializer round-trips: `cgContextJson v1` → model → JSON is stable (idempotent re-serialization)
4. All parser/serializer logic runs and passes tests without the Grasshopper SDK (DG.Core only)

**Plans:** 5/5 plans complete

**Wave 1**

- [x] 32-01-PLAN.md — GH-free Computgraph object model + CgContext root + RawCanvas input contract (CGSR-01)

**Wave 2** *(blocked on Wave 1)*

- [x] 32-02-PLAN.md — CanvasAnnotationParser: convention grammar → typed entities, untagged routing, Emr tolerance, nesting, dataType inference (CGSR-02)
- [x] 32-03-PLAN.md — ComputgraphContextSerializer: versioned cgContextJson v1 read/write, idempotent round-trip (CGSR-03)

**Wave 3** *(blocked on Wave 2)*

- [x] 32-04-PLAN.md — CanvasContextExtractor (#if GRASSHOPPER_SDK): GH_Document traversal → RawCanvas + SerializeContext seam (CGSR-03)
- [x] 32-05-PLAN.md — Frame RawCanvas fixture + xUnit integration test proving all 4 success criteria (CGSR-01..04)

---

### Phase 32.1: Cross-Platform Identity and Mapping (DG ID)

**Goal:** Every design object extracted into the Computgraph carries a durable, platform-neutral DG ID — the same conceptual object (a parametric wall in Grasshopper and the BIM wall generated from it in Revit) resolves to one identity within a Design State, and properties computed on one platform (e.g. Ladybug-derived insulation on a facade panel) attach to that identity and become readable from every other platform's bound representation.

**Requires:** Phase 32 (Computgraph object model + `cgContextJson` envelope carry the `dgId`). Parallel-safe with Phases 33–35. Feeds Phase 36 (published nodes carry `dgId`), Phase 38 (generated inputs), and future connector milestones (Revit connector; v4.0 BOT bridge).

**Requirements:** DGID-01, DGID-02, DGID-03, DGID-04, DGID-05, DGID-06

**Deliverables:**

- `spec/DG-ID.md` — the identity spec: `dgId` format + minting rules (deterministic re-mint for convention-tagged Computgraph entities; rename/stability semantics; collision policy), the cross-platform binding model, and shared-property semantics — written against the surveyed state of the art (Rhino.Inside.Revit element tracking/binding, Speckle `applicationId` vs hash `id`, IFC GlobalId, Revit UniqueId episode+ElementId, BHoM adapter ids)
- `DG/src/DG.Core/Models/Identity/` — `DgId` value type + deterministic minting service (GH-free); Computgraph model entities (`CgObject`, `CgProcedure`, `CgPattern`, `CgParameter`, `CgInterface`) and the `cgContextJson` envelope gain `dgId` fields (Phase 32's versioned-contract rule applies)
- Neo4j identity registry: `dgId` property on Computgraph nodes + a representation-binding shape (platform, native-id kind — GH instance GUID / Revit UniqueId / IFC GlobalId / Speckle applicationId — native-id value, connector, boundAt), project-isolated; DesignState/ObjState payloads reference member objects by `dgId`
- `data-service/dg_identity.py` + identity API endpoints: resolve (native id → dgId), bind (attach a platform representation), shared-property read/write keyed by `dgId` with platform/connector/timestamp provenance — parameterized Cypher only
- Cross-platform property-flow proof: an Emergent insulation parameter written from the GH side is readable via the identity API by a simulated Revit-side consumer (test fixture — the real Revit connector is a future milestone)
- ADR in `DG_OBSIDIAN/knowledge/decisions/` recording the chosen scheme and the surveyed alternatives

**Success Criteria:**

1. Re-extracting the same annotated definition yields identical `dgId`s for every tagged entity (deterministic stability); the documented rename rules state exactly when identity is preserved vs re-minted
2. Binding a simulated Revit representation (UniqueId) to the `dgId` of a GH-extracted wall lets either native id resolve to the same entity, and the containing DesignState references that `dgId`
3. An insulation value written from the GH side is readable through the identity API keyed by `dgId` — with platform provenance — without Rhino running
4. `spec/DG-ID.md` + the ADR document the scheme against Rhino.Inside.Revit element tracking, Speckle applicationId, IFC GlobalId, and Revit UniqueId approaches with explicit rationale for DG's connector architecture

**Plans:** 2/7 plans executed

**Wave 1**

- [x] 32.1-01-PLAN.md — DgId value type + deterministic minting service (SHA-256 over project|definitionId|cgId) + golden vector (DGID-01)
- [x] 32.1-02-PLAN.md — spec/DG-ID.md identity spec + ADR vs Rhino.Inside.Revit/Speckle/IFC/UniqueId/BHoM (DGID-01, DGID-06)
- [ ] 32.1-03-PLAN.md — dg_identity.py + /identity mint/resolve/bind API, Representation registry, anti-misbinding 409 (DGID-02, DGID-03, DGID-05)

**Wave 2** *(blocked on Wave 1; plan 05 also assumes Phase 32 artifacts exist)*

- [ ] 32.1-04-PLAN.md — SharedProperty read/write API + simulated-Revit Ladybug-insulation property-flow proof (DGID-04, DGID-05)
- [x] 32.1-05-PLAN.md — dgId on Computgraph entities + CgContextDgIdAssigner + cgContextJson additive round-trip (DGID-01, DGID-03)
- [ ] 32.1-06-PLAN.md — ObjState/statePayloadJson v2 additive dgId reference, v1/v2 backward-compat (DGID-03)

**Wave 3** *(blocked on Wave 2)*

- [ ] 32.1-07-PLAN.md — schema propagation: DATABASE.md, cypher_template, dataset_schema, CLAUDE.md tables, copilot-instructions, README, dg-shapes.ttl SHACL, dg_context.py allow-lists (DGID-01, DGID-02, DGID-04)

---

### Phase 33: DG Canvas Bridge (grasshopper-mcp adaptation)

**Goal:** data-service (and through it, any LLM/MCP client) can read the live Grasshopper canvas and drive on-canvas previews — via a native re-implementation of the grasshopper-mcp bridge pattern inside the DG plugin, no third-party plugin dependency.

**Requires:** Phase 32 (the listener serves `cgContextJson`).

**Requirements:** BRDG-01, BRDG-02, BRDG-03, BRDG-04

**Deliverables:**

- `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` — **DG CANVAS LISTENER**: `TcpListener` on a configurable port (default **8720**), grasshopper-mcp wire protocol (newline-terminated JSON `{"type": ..., "parameters": {...}}`, UTF-8); commands: `get_canvas_context` (Phase 32 serializer), `get_selection` (selected object ids), `preview_structure` / `clear_preview` / `get_preview_status` (Phase 35 consumers); canvas access marshalled via `RhinoApp.InvokeOnUiThread`; on/off boolean input; status output
- `data-service/gh_bridge.py` — TCP client (env `GH_BRIDGE_HOST` default `host.docker.internal`, `GH_BRIDGE_PORT` default `8720`), timeout + connection-refused mapped to actionable errors
- `data-service/app.py` — `POST /computgraph/context/pull` (project + definition scope → live `cgContextJson`); new tools on the existing `POST /mcp` JSON-RPC server: `gh_get_context`, `gh_get_selection`, `gh_preview_structure`, `gh_clear_preview`
- `docker-compose.yml` — `GH_BRIDGE_HOST/PORT` env + `extra_hosts: host.docker.internal:host-gateway` for data-service

**Success Criteria:**

1. With Rhino running and DG CANVAS LISTENER on, `POST /computgraph/context/pull` from inside the Docker network returns the live canvas as `cgContextJson v1`
2. An MCP client calling `gh_get_context` via `POST /mcp` gets the same document (tools/list shows the four `gh_*` tools)
3. Listener off / Rhino closed → data-service returns a What+Where+How-to-fix error, not a hang (bounded timeout)
4. The listener never touches the canvas off the UI thread; toggling it off closes the socket cleanly and repeated on/off cycles don't leak ports

**Plans:** 3/4 plans executed

Plans:
**Wave 1**

- [x] 33-01-PLAN.md — DG.Core bridge protocol + command dispatcher (wire contract, allow-list) [BRDG-01]
- [x] 33-03-PLAN.md — gh_bridge.py client + /computgraph/context/pull + 4 gh_* MCP tools + docker-compose [BRDG-02, BRDG-03, BRDG-04]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 33-02-PLAN.md — DG CANVAS LISTENER component: TcpListener + UI-thread marshalling + lifecycle [BRDG-01, BRDG-04]

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 33-04-PLAN.md — live in-Rhino end-to-end verification (human-verify) [BRDG-01..04]

---

### Phase 34: Ontology Tagging Components and Manual Selection

**Goal:** The architect marks the ontological entities they know directly on the canvas — object/algorithm identity via a marker component, and any manually selected set of components as a typed Computgraph entity — producing exactly the annotation convention the serializer parses.

**Requires:** Phase 32 (convention grammar + styles are the contract). Parallel-safe with Phase 33.

**Requirements:** TAGC-01, TAGC-02, TAGC-03

**Deliverables:**

- `DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs` — the color/style constants per entity kind (procedure container, pattern orange, nested pattern purple, parameter pink, interface white — from the Frame reference)
- `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs` — **DG OBJECT MARKER**: inputs Object name (+ optional `dg:Class` IRI from ONTOGRAPH), algorithm index; creates/updates the `OBJECT - <NAME>` and `<n>_ALGORITHM` scribbles; reads existing markers on re-run
- `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs` — **DG ENTITY TAG**: inputs kind (Proc/Pat/Var/Const/Emg/IntF via value list), name, optional procedure index; button-triggered: wraps the *current canvas selection* into a convention-named, convention-colored `GH_Group` (auto-increments indices, e.g. next free `11_Pat_k`); undoable via `GH_UndoRecord`
- Both components `#if GRASSHOPPER_SDK` guarded, DG category/subcategory, `DgIcons` entries, GUID registration

**Success Criteria:**

1. Selecting a slider and tagging it as Var with name "SpansCount" under procedure 11 produces a pink group named `11_Var_SpansCount` — and the Phase 32 serializer reads it back as a `CgParameter` (Variable)
2. DG OBJECT MARKER on an empty canvas creates the two scribbles; on an annotated canvas it reads and reports the existing Object/Algorithm without duplicating
3. Manual tags survive the round-trip: tag → serialize → the tagged entity appears as ground truth (`source: tagged`) in `cgContextJson`
4. Ctrl+Z removes a tag group cleanly (component uses undo records)

**Plans:** 3/3 plans complete
**Wave 1**

- [x] 34-01-PLAN.md — CanvasAnnotationGrammar token constants + CanvasAnnotationNameFactory (GH-free write path) + xUnit round-trip suite (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 34-02-PLAN.md — DG OBJECT MARKER component: scribble create/report + dg.objectClassIri ValueTable metadata (Wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 34-03-PLAN.md — CanvasAnnotationStyles palette + DG ENTITY TAG component: selection→group, undo, nesting, guard rails (Wave 3)

---

### Phase 35: LLM Recognition and On-Canvas Proposal Preview

**Goal:** AI classifies the untagged remainder of the canvas into Computgraph entities — using the architect's tags as ground-truth anchors — and the proposal appears **on the canvas** as clearly-styled temporary groups and scribbles that the architect confirms, edits, or rejects before anything leaves Rhino.

**Requires:** Phases 29 (Computgraph concept catalog in context assembler), 33 (bridge), 34 (tags as anchors).

**Requirements:** RCGN-01, RCGN-02, RCGN-03, RCGN-04

**Deliverables:**

- `data-service/cg_recognition.py` — recognition pipeline: `cgContextJson` (tagged anchors + untagged nodes/wires) + Computgraph concept catalog + Frame few-shot example → LLM gateway → **proposed-structure JSON** (strict schema: entity kind, name suggestion, member component ids, confidence, rationale); schema-validated with bounded retry; `POST /computgraph/recognize`
- Preview rendering: bridge command `preview_structure` draws the proposal as temporary `GH_Group`s + scribbles in a distinct preview style (dashed/desaturated + `[?]` name prefix), all inside one `GH_UndoRecord`
- Confirm/reject flow: `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` — **DG STRUCTURE CONFIRM**: lists pending proposals per procedure; accept converts preview groups to permanent convention groups (Phase 34 styles), reject removes them cleanly; partial accept supported; `clear_preview` wipes all pending
- Recognition report: entities it could not classify are listed as *unrecognized* with member ids — never invented, never silently dropped

**Success Criteria:**

1. On the Frame definition with only the Object marker + 2 procedure tags present, recognition proposes patterns/parameters/interfaces whose member sets match the reference annotation for ≥ the majority of blocks, each with confidence + rationale
2. The proposal is visible on the canvas as preview groups; Ctrl+Z or `clear_preview` removes every trace
3. Accepting proposal(s) yields permanent groups that the Phase 32 serializer parses identically to hand-made tags (`source: recognized` recorded)
4. Nothing is written to Neo4j in this phase's flow until explicit confirmation; unrecognized blocks appear in the report

**Plans:** TBD

---

### Phase 36: Computgraph Persistence and Graph Layer Display

**Goal:** A confirmed canvas structure persists to Neo4j as the Computgraph layer — project-isolated, MERGE-idempotent, provenance-carrying — and is browsable as a distinct layer in the ui-v2 graph viewer.

**Requires:** Phases 32 (serializer), 32.1 (`dgId` on every published entity), 35 (confirmed structures; direct tagged-only publish works without 35).

**Requirements:** CGPD-01, CGPD-02, CGPD-03, CGPD-04, CGPD-05

**Deliverables:**

- `data-service/app.py` — `POST /computgraph/publish`: confirmed `cgContextJson` → Cypher; node labels `Object`, `Behavior`, `Algorithm`, `Procedure`, `Pattern`, `Parameter` (`paramKind`: Variable/Constant/Emergent; `dataType`), `Interface` (`ifaceType`: Input/Output) — all with `graph:'Computgraph'` + `project`; relationships `HAS_BEHAVIOR`, `HAS_ALGORITHM`, `HAS_PROCEDURE`, `HAS_PATTERN`, `PATTERN_HOST_TO`, `HAS_PARAMETER`, `HAS_INTERFACE`, `PARAM_LINK`; optional `REFERS_TO` bridge Object→`Class` when a Class IRI was tagged
- MERGE keys: stable entity ids derived from definition id + convention name (re-publish updates, never duplicates); every published node also carries its Phase 32.1 `dgId` so cross-platform representation bindings survive re-publish
- Provenance properties per node: `source` (tagged | recognized), `provider`/`model` (when recognized), `definitionId`, `publishedAt`
- Publish path from the plugin: **DG COMPUTGRAPH PUBLISH** component (or a confirm-then-publish output on DG STRUCTURE CONFIRM) following the `ValidationPublishClient` HTTP pattern
- Schema propagation checklist: `cypher_template.txt`, `training/dataset_schema.json`, `spec/DATABASE.md`, `CLAUDE.md` schema tables, n8n/orchestrator prompts via the Phase 29 catalog
- `ui-v2/src/graph/` + `ui-v2/src/screens/` — Computgraph layer in the datascape: distinct styling for the new labels, per-project filter toggle

**Success Criteria:**

1. Publishing the confirmed Frame structure yields the expected subgraph (1 Object–Behavior–Algorithm chain, 2 Procedures, patterns/parameters/interfaces with correct kinds), project-scoped
2. Re-publishing the same definition changes zero node counts (MERGE idempotency verified by count query)
3. Every Computgraph node answers a provenance query: source, model (if recognized), definition, timestamp
4. The ui-v2 graph viewer shows the Computgraph layer distinctly and filters it per project

**Plans:** TBD

---

### Phase 37: Script Structure Validation MVP

**Goal:** Design Grammars validate the *structure of the Grasshopper script itself*: deterministic Cypher checks over the published Computgraph plus Design-Rule-mapped structural requirements, and an LLM consult endpoint that answers questions about a script's structure — the foundation v10.0 Script Intelligence (generation/editing/consulting) builds on.

**Requires:** Phase 36 (published Computgraph to validate).

**Requirements:** SVAL-01, SVAL-02, SVAL-03

**Deliverables:**

- `data-service/cg_structure_checks.py` + `POST /computgraph/validate` — deterministic checks with entity references: annotation-convention compliance, orphan Patterns (no Procedure), Procedures without Interfaces, Parameters without dataType, dangling `PARAM_LINK`s, unreachable nodes
- Rule-mapped structural checks: a mapping shape linking a `Rule` to structural requirements over the Computgraph (e.g. "a Frame algorithm must contain a Truss-configuration Procedure", "height must be a VariableParam") — evaluated via Cypher, reported pass/fail per rule with the offending/satisfying entities
- `POST /computgraph/consult` — NL question + published Computgraph context (via `dg_context.py`) → gateway → grounded answer citing entity names; explicitly read-only
- Report surface: validation report JSON consumable by ui-v2 (and printable from a GH panel via the bridge)

**Success Criteria:**

1. Deleting an Interface tag from the Frame structure and re-publishing makes `/computgraph/validate` flag the Procedure-without-Interface check with the exact procedure named
2. A rule mapped to "must contain Procedure matching *Footer*" passes on Frame and fails on a copy published without the 12_Proc group
3. "Which parameters drive the truss height?" via `/computgraph/consult` answers citing `11_Var_HTotal` (grounded in the graph, not hallucinated)
4. All structural checks are deterministic and LLM-free; only `/consult` calls the gateway

**Plans:** TBD

---

### Phase 38: AI-Generated Grasshopper Script Inputs

**Goal:** Given a rule and the published Computgraph Parameter structure, AI proposes concrete input parameter sets for the Grasshopper script — delivered as ParamState-compatible payloads the architect can review and apply via PARAMETER REINSTATE.

**Requires:** Phase 36 (`dgc:` Parameter structure with slider domains comes from serialization + persistence); v7.0 PARAMETER REINSTATE (milestone prerequisite).

**Requirements:** GHIN-01, GHIN-02, GHIN-03, GHIN-04

**Deliverables:**

- Input-generation endpoint: rule (or design intent text) + published `Parameter` set (VariableParams with serialized slider domains) → N candidate parameter assignments, typed Number/Integer/Boolean only (standing v2.0 decision)
- Candidates serialized as ParamState-compatible payloads (statePayloadJson v2) with provenance properties: source rule, provider/model, timestamp
- ui-v2 review surface: candidate list with per-parameter values, accept/reject; accepted candidates stored as ParamStates
- Application path: accepted ParamState applied on the canvas through the existing PARAMETER REINSTATE component — no new apply mechanism

**Success Criteria:**

1. For a max-height rule against the Frame definition, generated candidates keep every parameter inside its recognized slider domain and satisfy the rule's limit where determinable
2. An accepted candidate round-trips: stored as ParamState → visible in VALIDATION GRAPH reads → applied via PARAMETER REINSTATE with per-parameter ReStatus reporting
3. Nothing touches the canvas without explicit user acceptance — generation and application are strictly separated
4. Provenance is queryable: `MATCH` on generated ParamStates returns rule, model, and timestamp for each

**Plans:** TBD

---

### Phase 39: DesignState Auto-Validation Investigation

**Goal:** A prototyped, evidence-based answer to "can validation run automatically when a DesignState is captured?" — architecture chosen, guardrails defined, full implementation scoped for a follow-up milestone.

**Requires:** v7.0 VALIDATOR + composed DesignState shipped (milestone prerequisite). Independent of Phases 30–38; can run parallel.

**Requirements:** DSAV-01, DSAV-02, DSAV-03

**Deliverables:**

- Investigation note comparing trigger architectures: (a) capture-time hook in the DESIGN STATE / VALIDATOR components (GH-side), (b) data-service watcher on DesignState writes, (c) event-driven trigger on Neo4j ValidGraph writes — with latency, publish-flood, and Speckle-noise analysis for each
- Working prototype of at least one path: capturing a new DesignState produces a validation Run without a manual VALIDATOR trigger
- Guardrail design: debounce window, per-project rate limit, opt-in flag (auto-validation must be explicitly enabled per project)
- ADR in `DG_OBSIDIAN/knowledge/decisions/` scoping full implementation to a future milestone

**Success Criteria:**

1. The prototype demonstrably closes the loop on live Docker: DesignState captured → Run appears in ValidGraph and (if enabled) publishes to Speckle — hands-off
2. Rapid successive captures do not flood Speckle: the debounce/rate-limit design is validated in the prototype, not just described
3. The ADR records the chosen architecture, the rejected options with reasons, and the follow-up milestone scope

**Plans:** TBD

---

### Phase 40: E2E Validation and Docs

**Goal:** The full v9.0 intelligence chain runs end-to-end on live Docker under a cloud provider, provider switching is friction-free, and every new service, component, setting, and workflow is documented.

**Requires:** Phases 28–39.

**Requirements:** INTG-01, INTG-02, INTG-03, INTG-04

**Deliverables:**

- E2E run: NL rule → cloud-LLM ingest (context layer + validation) → graph → GH validation → Speckle publish, on live Docker
- E2E GH intelligence chain: object marked + entities tagged → LLM recognition → on-canvas preview → confirm → Computgraph publish → structure validation → generated inputs accepted → applied via PARAMETER REINSTATE → validation run (auto or manual per Phase 39 outcome)
- Provider-switch drill: Claude ↔ OpenAI-compatible ↔ Ollama via settings only, mid-session, no restarts; LLM settings panel available in ui-v2 (port from legacy panel if not done earlier)
- Docs: CLAUDE.md service map + schema tables + gotchas, `spec/DATABASE.md` Computgraph section, DG_OBSIDIAN notes (decisions from Phases 30 and 39 filed; DG Canvas Annotation Convention note), `docs/` component reference for the 4–5 new GH components, graphify refresh

**Success Criteria:**

1. Both E2E chains complete without errors in one session on live Docker
2. Provider switching requires only the settings panel — verified for all three providers
3. All 54 v9.0 requirements are checked off in v9.0-REQUIREMENTS.md with traceability complete
4. `grep -ri "ollama" CLAUDE.md spec/` presents Ollama as the fallback provider, not the sole LLM path

**Plans:** TBD

---

### Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 28. Cloud LLM Connector and Provider Abstraction | 3/3 | Complete | 2026-07-06 |
| 29. DG-Aware Context Layer | 8/8 | Complete   | 2026-07-19 |
| 30. Orchestration Evaluation — n8n vs OpenClaw | 0/? | Not started | — |
| 31. Rules Ingestion and Editing Workflow Upgrade | 0/? | Not started | — |
| 32. Computgraph Serialization Core | 5/5 | Complete    | 2026-07-18 |
| 32.1 Cross-Platform Identity and Mapping (DG ID) | 3/7 | In Progress| 2026-07-18 |
| 33. DG Canvas Bridge (grasshopper-mcp adaptation) | 3/4 | In Progress|  |
| 34. Ontology Tagging Components and Manual Selection | 3/3 | Complete   | 2026-07-18 |
| 35. LLM Recognition and On-Canvas Proposal Preview | 0/? | Not started | — |
| 36. Computgraph Persistence and Graph Layer Display | 0/? | Not started | — |
| 37. Script Structure Validation MVP | 0/? | Not started | — |
| 38. AI-Generated Grasshopper Script Inputs | 0/? | Not started | — |
| 39. DesignState Auto-Validation Investigation | 0/? | Not started | — |
| 40. E2E Validation and Docs | 0/? | Not started | — |

Dependency shape: `28 → 29 → 31` (31 also gated by 30's ADR); `28 → 30` (parallel to 29); `32 → 32.1` (parallel-safe with 33–35); `32 → 33 → 35`; `32 → 34 → 35` (33 ‖ 34); `29 → 35`; `{32.1,35} → 36 → 37`; `36 → 38`; `39` parallel to 30–38; all → `40`. **Phase 32 has no v9.0 dependencies and can start immediately.**

### Files Modified Summary (projected)

| File | Phase | Change |
|------|-------|--------|
| `data-service/llm_gateway.py` | 28 ✅ | Provider adapters (Claude / OpenAI-compatible / Ollama) |
| `data-service/dg_context.py` | 29, 35, 37 | **New** — deterministic ontology/SWRL/Cypher/Computgraph context assembler |
| `llm/cypher_catalog.json` | 29 | **New** — versioned standard Cypher expression catalog |
| `data-service/gh_bridge.py` | 33 | **New** — TCP client to DG CANVAS LISTENER (host.docker.internal:8720) |
| `data-service/cg_recognition.py` | 35 | **New** — LLM recognition pipeline + proposed-structure schema |
| `data-service/cg_structure_checks.py` | 37 | **New** — deterministic structural checks + rule-mapped checks |
| `data-service/app.py` | 29, 33, 35, 36, 37, 38 | Context debug endpoint; `/computgraph/context/pull`, `gh_*` MCP tools; `/computgraph/recognize`; `/computgraph/publish`; `/computgraph/validate` + `/consult`; input generation |
| `docker-compose.yml` | 30, 33 | OpenClaw spike container; `GH_BRIDGE_*` env + `extra_hosts` |
| `DG/src/DG.Core/Models/Computgraph/*` | 32, 32.1 | **New** — GH-free Computgraph object model (+ `dgId` fields in 32.1) |
| `spec/DG-ID.md` | 32.1 | **New** — cross-platform identity spec (dgId format, minting, binding model, shared properties) |
| `DG/src/DG.Core/Models/Identity/*` | 32.1 | **New** — DgId value type + deterministic minting service |
| `data-service/dg_identity.py` | 32.1 | **New** — identity registry API (resolve/bind + shared-property read/write) |
| `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` | 32 | **New** — annotation-convention grammar |
| `DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs` | 32 | **New** — cgContextJson v1 |
| `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` | 32 | **New** — GH_Document traversal |
| `DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs` | 34 | **New** — per-kind group colors/styles |
| `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` | 33 | **New** — DG CANVAS LISTENER (TCP bridge) |
| `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs` | 34 | **New** — DG OBJECT MARKER |
| `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs` | 34 | **New** — DG ENTITY TAG |
| `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` | 35 | **New** — DG STRUCTURE CONFIRM (+ publish trigger, Phase 36) |
| `DG/tests/DG.Tests/` | 32, 34, 35 | Frame fixture; parser/serializer/proposal-schema tests |
| `ui-v2/src/graph/`, `ui-v2/src/screens/` | 31, 36, 38 | Edit-preview UI; Computgraph layer styling/filter; input candidate review |
| `n8n/workflows/*.json` | 29, 31 | Thin context-assembler callers; upgraded ingest/edit flow (or OpenClaw successor per Phase 30 ADR) |
| `cypher_template.txt`, `training/dataset_schema.json`, `spec/DATABASE.md` | 36 | Computgraph labels/relations (standard propagation checklist) |

*v9.0 roadmap inlined 2026-07-12 on reactivation (previously isolated at `milestones/v9.0-ROADMAP.md` since 2026-07-03; restructured 2026-07-08 — Computgraph serialization pipeline (Phases 32–37) elaborated from the Frame worked example; script generation/editing/consulting planned as v10.0; renumbered 2026-07-08: milestone-local 1–13 → global 28–40).*
