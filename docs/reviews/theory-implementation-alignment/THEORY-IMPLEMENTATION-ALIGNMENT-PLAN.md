# Theory–Implementation Alignment Plan

**Review target:** `Publications/T1_ITcon_DG_Draft_R15.7.docx`  
**Paper extraction:** `docs/reviews/theory-implementation-alignment/evidence/paper-full-text.md`  
**Repository:** `C:/Users/Admin/source/repos/design-grammar-system`  
**Repository baseline:** `HEAD 5a5ca6ca69509b4f61c18ebb4716905b18fa6b40`, branch `master`  
**Review date:** 2026-09-19  
**Scope:** theory–implementation alignment, claim calibration, target architecture, validation and GSD planning. This report is read-only with respect to source, manuscript, planning, and vault files. It creates no code fixes and no commits.

## 1. Executive Assessment

### 1.1 Decision

**Conditional GO for a bounded theory–implementation alignment revision.** The repository supports a credible implementation-grounded paper if the manuscript distinguishes schema-level, artefact-level, implemented-runtime, test-verified, live-verified, prototype, planned, and unsupported claims. The strongest defensible system description is:

> A deterministic, violation-pattern, comparison-based Grasshopper validation and design-state pipeline, backed by a project-scoped graph service, SHACL/OWL sidecar validation, ComputGraph structural extraction, human-confirmed AI assistance, and a Neo4j/Speckle persistence path.

**NO-GO for unqualified claims** that the current runtime is a full SWRL/OWL reasoner, a complete cross-platform BIM connector, a lossless geometry/state replay engine, a production CDE governance system, or a universally deterministic LLM-enabled pipeline. Those claims are contradicted or materially weakened by the inspected implementation and must either be narrowed, marked proposed, or supported by new experiments before publication.

### 1.2 What is already aligned

* The paper's violation-first rule representation has a concrete implementation path: natural-language rule ingestion, validated graph persistence, typed rule/atom structures, bounded comparison evaluation, and validation publication. The backend inventory describes this as P1 and the C# audit describes the corresponding parser/binding/evaluation path [audit: evidence/backend-inventory.json:13-38; audit: parts/csharp.md:139-155].
* Design State capture, validation publication, per-entity persistence, automatic-validation experimentation, and model-view retrieval exist as distinct runtime paths. They are not yet one uniform immutable lifecycle, but the pieces are identifiable [audit: evidence/backend-inventory.json:158-185].
* ComputGraph structural extraction is implemented as a canvas-to-context-to-recognition-to-confirmed-publish path. The implementation preserves topology, tags, parameters, interfaces, provenance, and warnings; it does not execute the Grasshopper solver [audit: evidence/backend-inventory.json:101-113; audit: parts/csharp.md:123-129].
* Project-local `dgId` minting, representation binding endpoints, shared properties, and identity lookup form a real identity registry in the Python service, while the C# side proves deterministic GH-side minting only [audit: evidence/backend-inventory.json:143-155; audit: parts/csharp.md:131-137].
* OWL/SHACL/RDF/JSON-LD and buildingSMART alignment artefacts are present in the evidence set, and the paper explicitly defines these as a core-plus-extension standards strategy rather than imports into the DG core [audit: evidence/literature-ledger.json:119-180; audit: evidence/ontology-dg-shapes-ttl.json:1-7; audit: evidence/ontology-dg-disjointness-ttl.json:1-7; paper P100-P101].

### 1.3 Publication blockers

1. **Claim granularity:** Replace universal runtime language with claim-specific status. The paper itself says runtime-demonstrated claims are limited and excludes user-level interoperability, cross-organisation governance, identity-conflict resolution, and LLM reliability from established evidence (P081).
2. **Reasoner wording:** Call the C# path a violation-pattern evaluator over pre-bound rows, not a general SWRL engine. The parser is a bespoke lexical subset and the evaluator does not evaluate class, data-property, or object-property predicate semantics [audit: parts/csharp.md:21-45].
3. **Design State immutability:** Reconcile the paper's immutable three-part snapshot language (P102-P105) with manual publish payloads, auto-validation status mutation, standalone accepted `ParamState` nodes, and lossy v2 replay [audit: evidence/backend-inventory.json:171-185; audit: parts/csharp.md:99-113].
4. **CQ2/per-object verdicts:** Preserve the backend's per-entity records as the canonical evidence. Do not describe the C# query component as replaying per-object verdicts; its inspected repository path repeats a run-level aggregate across objects [audit: parts/csharp.md:107-113].
5. **CQ3/`ATTRIBUTE_OF`:** The paper presents a bidirectional rule-to-parameter bridge (P163-P169), but the audited Python publish path uses `HAS_PARAMETER`/`PARAM_LINK` and input-binding resolution; no `ATTRIBUTE_OF` writer/query was found [audit: evidence/backend-inventory.json:130-141].
6. **Operational security and tenancy:** Project predicates and connector tokens are not equivalent to server-side user/tenant authorization. The audit records client-side browser auth, exposed direct Neo4j proxying, and route-level authorization gaps [audit: evidence/backend-inventory.json:188-197].
7. **Live evidence:** The repository contains pending and blocked UAT items for Rhino bridge, recognition, tag persistence, validation, and parameter reinstatement; these must remain pending until independently executed [audit: evidence/gsd-audit-uat.json:1-139].

### 1.4 Recommended paper posture

Use the paper's schema and demonstration results as the principal contribution. Present the repository as a co-developed implementation that demonstrates selected paths and exposes the next empirical agenda. Move cross-platform interoperability, full CDE governance, complete rule expressiveness, and LLM performance from asserted capability to **planned/proposed** architecture. This posture is consistent with the manuscript's own limitations and future-work language (P179-P185) and with the implementation audit.

## 2. Evidence and Method

### 2.1 Evidence hierarchy

The review uses the following evidence classes:

| Class | Meaning used in this report | Evidence anchor |
|---|---|---|
| **Implemented** | Source/declarative artefact inspected and the path exists. Existence does not prove deployment or successful execution. | [audit: evidence/backend-inventory.json:7-11] |
| **Test-verified** | A named repository test or documented test manifest asserts the behaviour; this review did not rerun every delegated child test. | [audit: evidence/backend-inventory.json:7-11] |
| **Live-verified** | Existing repository evidence records a live/container/Rhino/Speckle execution; the review did not repeat it. | [audit: evidence/backend-inventory.json:7-11] |
| **Partial** | A path exists but does not cover the full paper claim, or has a known seam, security boundary, or compatibility gap. | This report's matrix |
| **Prototype** | An executable investigation path exists but semantics, reliability, or lifecycle policy remains unsettled. | [audit: evidence/backend-inventory.json:171-185] |
| **Planned** | Paper/specification architecture or future work, without inspected runtime proof. | paper P133, P143, P181, P185 |
| **Unsupported** | No inspected implementation or evidence was found for the claim. | Child-audit absence statements below |
| **Contradicted** | Inspected runtime behaviour conflicts with the claim as worded. | Contradictions C1-C6 in [audit: evidence/backend-inventory.json:209-239] |
| **Unknown** | The available artefacts do not establish the status. | Pending/blocked UAT and unresolved evidence gaps |

### 2.2 Inputs inspected

* Full extracted paper text, including paragraph IDs P001-P187, with paper metadata confirming 240 body paragraphs, six tables, 49 parts, and three insertions [audit: evidence/paper-metadata.json:1-9].
* Parent evidence inventories: repository file inventory, module inventory, backend inventory, FastAPI routes, n8n inventory, compose inventory, ontology shape/disjointness summaries, git baseline, GSD inventory, and GSD audit-UAT output.
* The delegated child audits: backend/frontend/workflows/security/operations [audit: parts/backend.md:1-176], C# and Grasshopper [audit: parts/csharp.md:1-185], paper decomposition [audit: parts/paper.md:1-66], GSD reconciliation [audit: gsd.md:1-67], literature and standards [audit: parts/literature.md:1-93], and Obsidian/Graphify [audit: audit parts/knowledge-graph.md:1-68].
* Citation ledger `C:/Users/Admin/AppData/Local/hermes/cache/citations/ledger.json`, restricted to registered IDs 1-19.

### 2.3 Child-artifact coverage

The delegated evidence artifacts are available under the audit root: `parts/backend.md`, `parts/csharp.md`, `parts/paper.md`, `gsd.md`, `parts/literature.md`, and `audit parts/knowledge-graph.md`. Their machine-readable companions are recorded in `evidence/integrated-index.json`, which reports 62 indexed artifacts, 22 required artifacts present, and none missing. The report also retains the parent inventories and the full 50-record register in `evidence/paper-claims.json`; the tables below present the 22 major claim families while the JSON register is the exhaustive claim-level record.

### 2.4 Scope and non-actions

The Graphify artefact is stale: the latest inspected snapshot records 15,605 nodes and 23,659 links at commit `77abe053`, one commit behind repository `HEAD` `5a5ca6c`. An older parent capture also records 5,412 nodes and 6,907 links at `67f1db3`; these are separate historical snapshots, not contradictory counts. Graphify was not regenerated. No source, manuscript, planning, vault, database, live connector, Rhino, Revit, IFC, or external service was modified.

## 3. Current System Baseline and Pipeline Inventory

### 3.1 Repository and runtime baseline

The inspected repository is a multi-service system comprising `data-service` (112 files), `dg-reasoner` (21), `DG/src/DG.Core` (87), `DG/src/DG.Grasshopper` (57), `ui-v2/src` (72), `n8n/workflows` (5), `ontology` (54), and `spec` (12) [audit: evidence/module-inventory.json:1-86]. The FastAPI surface includes rule, graph, reasoner, ComputGraph, identity, Design State, validation, execution-result, knowledge, and rule-edit routes [audit: evidence/fastapi-routes.json:1-385]. The compose inventory records 21 services/resources, including Neo4j, reasoner, data service, n8n, Ollama, UI, and Speckle-related services; it also records literal secrets in the compose artefact [audit: evidence/compose-inventory.json:1-26].

Parent runtime evidence reports: `data-service` pytest 772 passed, 1 skipped, 8 deselected; `dg-reasoner` pytest 39 passed; DG .NET tests 412 passed; .NET Release build 0 warnings/0 errors; UI Vite build passed with a chunk-size warning; `docker compose config` passed; and live containers were up. These are parent-provided baseline results, not rerun in this report. The GSD audit-UAT evidence remains open for 10 items: nine pending and one blocked across phases 33, 34, 35, 37, and 38 [audit: evidence/gsd-audit-uat.json:1-139].

### 3.2 Pipeline inventory

| ID | Pipeline | Evidence status | Current implementation | Alignment boundary |
|---|---|---|---|---|
| P1 | Natural-language rule ingest to Metagraph | Implemented; test coverage present; live status not independently reverified | n8n acknowledgement, context assembly, bounded LLM generation, Cypher validation, Neo4j transaction, execution-result persistence [audit: evidence/backend-inventory.json:13-38] | LLM interpretation and workflow activation are not universal deterministic execution; n8n source artefacts for rules/query are `active:false` [audit: evidence/n8n-inventory.json:1-35]. |
| P2 | Natural-language graph query | Implemented; test coverage present; live status not independently reverified | Project-scoped context, read-only Cypher generation/validation, Neo4j query, answer generation [audit: evidence/backend-inventory.json:41-55] | Answer generation is provider/model dependent; direct Neo4j proxy exposure is an operational/security boundary. |
| P3 | Rule edit/rewrite | Partial implemented | Rule-ID detection, cleanup, replacement ingest, session refresh [audit: evidence/backend-inventory.json:58-69] | Revision semantics are not a typed immutable revision chain; workflow activation drift is recorded. |
| P4 | Rule delete and orphan-safe cleanup | Implemented; named tests; prior live evidence exists | Preview, semantic selection, hallucinated-ID quarantine, fixed parameterized delete, shared/orphan accounting [audit: evidence/backend-inventory.json:72-83] | Confirmation is explicit, but route-level authentication/authorization is not established. |
| P5 | SpecGraph knowledge ingest/query/update | Implemented/partial | Path-confined ingest, note CRUD, full-text query, proposed/confirmed optimistic-concurrency updates [audit: evidence/backend-inventory.json:86-98] | CDE governance, steward approval, impact analysis, and release workflow are not end-to-end implemented. |
| P6 | Grasshopper canvas pull, recognition, preview, confirmed ComputGraph publish | Implemented; live Rhino status deferred | Bounded bridge, deterministic topology, LLM residual recognition, relational safety validation, human confirmation, atomic publish [audit: evidence/backend-inventory.json:101-113] | Structural capture is not solver execution; live bridge/recognition UAT remains pending or blocked. |
| P7 | ComputGraph structural validation and grounded consult | Implemented; test verified; live compose integration required | Seven deterministic structural checks, rule mapping, bounded consult and grounding [audit: evidence/backend-inventory.json:116-127] | Read-only validation is separate from a unified OWL/SWRL reasoner; UI consult client is not evident. |
| P8 | AI rule-to-parameter candidate generation | Implemented; tests/evaluation present | Tier-0 deterministic candidates, bounded provider retries, provenance, accept-time domain revalidation, accepted ParamState persistence [audit: evidence/backend-inventory.json:130-141] | Confidence constants are provisional; the trace uses input bindings/`PARAM_LINK`, not demonstrated `ATTRIBUTE_OF`. |
| P9 | Project-local identity and shared properties | Implemented; cross-platform live conflict run not reverified | Deterministic `dgId`, identity registry, resolve/bind/detach, shared property read/write [audit: evidence/backend-inventory.json:143-155] | Proves a project-local spine, not independent-platform synchronization or conflict resolution. |
| P10 | Manual validation publish, SHACL sidecar, Speckle overlay, run/view/delete | Implemented; one live Speckle leg recorded | Speckle version, ValidGraph run/entities, optional SHACL report, model view and delete [audit: evidence/backend-inventory.json:158-169] | Per-entity persistence exists, but immutable three-part Design State semantics are not guaranteed for every input. |
| P11 | Automatic Design State validation watcher | Prototype; extensive historical test/live evidence, not rerun | Capture, debounce/coalesce, rate limit, SHACL, ValidStatus derivation, retry, optional Speckle [audit: evidence/backend-inventory.json:171-185] | Repository records a known all-false verdict issue before ValidStatus writing; do not present as settled production semantics. |
| P12 | Browser auth, project isolation, connector auth | Partial | Client-side session, project predicates, connector token creation/hash/revocation/heartbeat [audit: evidence/backend-inventory.json:188-197] | Browser auth is not server-side tenancy; direct graph exposure and default/fallback secret risks remain. |
| P13 | C# rule parse/bind/evaluate/publish/read/replay | Partial implemented | Bespoke parser, state binding, numeric comparison evaluator, validation package, HTTP publish, Neo4j read and state replay [audit: parts/csharp.md:139-155] | Not full SWRL; unsupported built-ins can look like failure; v2 replay omits geometry/class and query paths disagree on versions [audit: parts/csharp.md:21-69,99-113]. |
| P14 | C# ComputGraph extraction and canvas preview | Partial implemented | GH document extraction, `cg-context-1` serialization, deterministic IDs, process-local preview registry [audit: parts/csharp.md:123-129,115-121] | Structural representation is implemented; preview bridge commands are explicit stubs and registry state is non-persistent. |
| P15 | C# connector and identity | Partial implemented | GH token heartbeat to data service, Neo4j Bolt probe, deterministic GH-side `dgId` minting [audit: parts/csharp.md:79-87,131-137] | No inspected Revit API, IFC reader/exporter, Speckle representation binding, or Rhino.Inside synchronization path. |

### 3.3 Baseline interpretation

The baseline is not one reasoning engine. It is a partitioned system: LLM-assisted authoring/query; deterministic graph validation; SHACL structural validation; OWL consistency through a sidecar; C# Grasshopper authoring/validation; ComputGraph structural capture; and graph/Speckle persistence. This partition is a strength when documented explicitly, but it contradicts a reading in which all paper semantics are executed by a single unified runtime [audit: evidence/backend-inventory.json:209-239].

## 4. Complete Paper Claim Map

The complete 50-record claim register is maintained in `evidence/paper-claims.json` with stable `PAPER-C-001` through `PAPER-C-050` IDs and all requested fields. The table below is the compact decision-facing map of 22 major claim families; the JSON register is the exhaustive claim-by-claim deliverable.

The following claim map assigns stable `PAPER-C` IDs to the paper's substantive claim families. Each row cites the paper paragraphs that define the claim and gives the evidence status that should appear in the revised manuscript.

| ID | Paper claim and anchor | Required implementation interpretation | Status |
|---|---|---|---|
| PAPER-C01 | Automated compliance checking decomposes into interpretation, model preparation, execution, and reporting; semantic-web approaches use IFC/OWL/SPARQL/SWRL (P005-P006). | Background and positioning claim; it does not assert that DG implements every referenced standard. | **Implemented as literature framing**; cite registered literature/standards [3], [10]-[12]. |
| PAPER-C02 | Design grammars are generative, inspectable rule formalisms and DG provides a direct BIM-data encoding (P007-P013). | DG ontology and Metagraph encode design-grammar intent and rules as graph artefacts. | **Schema-level implemented; runtime breadth partial.** |
| PAPER-C03 | Design-lifecycle operability consists of timestamped Design States, platform-neutral identity, and human-in-the-loop AI rule authoring (P014). | These are three separable capabilities; do not imply equal maturity. | **Mixed:** state/identity/AI paths implemented or prototype; cross-platform operation planned. |
| PAPER-C04 | Four competency questions are machine-checked on a demonstration graph (P015, P149-P176). | Report exact demonstration results as demonstration-level evidence, separate from repository production/runtime claims. | **Paper demonstration established by manuscript; repository replication status unknown unless named artefacts are supplied.** |
| PAPER-C05 | The runtime context supports mainstream BIM, Rhino, Grasshopper, Dynamo and iterative grounded implementation (P079-P081). | Runtime context and intended environments are broader than demonstrated connectors. | **Partial/planned; P081 itself limits user-level interoperability.** |
| PAPER-C06 | Five coplanar graph layers are held in one LPG: Ontograph, Metagraph, ComputGraph, ValidGraph, SpecGraph (P094-P101). | Backend contains values/paths for these graph concerns, but no general bidirectional projection service was found. | **Partial; strongest contradiction C1** [audit: evidence/backend-inventory.json:209-215]. |
| PAPER-C07 | Six typed bridges connect layers: `REFERS_TO`, `ATTRIBUTE_OF`, `VALIDATES`, `ENCODED_AS`, `GROUNDED_IN`, `DERIVED_FROM` (P096-P097). | Treat these as normative schema/design claims; verify each bridge separately in runtime mappings. | **Mixed:** `REFERS_TO`/validation-like paths are evidenced; `ATTRIBUTE_OF` and governance bridges are not evidenced end-to-end. |
| PAPER-C08 | Ontograph governance includes proposal, steward approval, versioning, provenance, impact analysis, and regression checks (P097, P134-P143). | Knowledge CRUD and sessions are not the same as governed vocabulary release. | **Planned/partial; CDE governance is not implemented end-to-end** [audit: evidence/backend-inventory.json:236-239]. |
| PAPER-C09 | Design State is an immutable, timestamped triple of ObjState, ParamState and PropState, consumed by runs and retained for longitudinal comparison (P102-P105). | Require an immutable snapshot contract, canonical state hash, complete membership, and replay tests before asserting universal runtime compliance. | **Contradicted/partial:** manual and auto paths differ; v2 replay loses geometry/class and readers disagree [audit: evidence/backend-inventory.json:221-224; audit: parts/csharp.md:99-105]. |
| PAPER-C10 | Violation-first SWRL rules use typed ClassAtom, DataPropertyAtom, ObjectPropertyAtom and BuiltinAtom with ordered arguments; passing rules return nothing and findings represent violations (P106-P122). | Separate the formal schema's four atom types from the C# lexical parser/evaluator subset. | **Schema-level implemented; C# execution partial.** The C# parser lacks an ObjectPropertyAtom branch and semantic predicate evaluation [audit: parts/csharp.md:21-37]. |
| PAPER-C11 | Quantitative threshold, equality, cardinality and related constraints are assigned to a deterministic SWRL validator; OWL handles terminological consistency; SHACL handles structural/data integrity (P123-P130, P170-P175). | Preserve the explicit service partition and identify which service produced each result. | **Partial but credible:** threshold subset and SHACL/OWL sidecar paths exist; not universal SWRL expressiveness. |
| PAPER-C12 | ComputGraph captures Algorithm–Procedure–Pattern–Parameter–Interface structure and supports parametric traceability (P140-P143). | Current runtime captures structure, tags, parameters, interfaces and provenance; it does not execute component algorithms or solver semantics. | **Structural implementation; executable FBS behaviour planned** [audit: parts/csharp.md:123-129]. |
| PAPER-C13 | Identity is object-centred and platform-neutral; GH GUID, Revit `UniqueId`, IFC `GlobalId`, viewer `applicationId` can bind to one DG identity (P137-P139, P184). | Distinguish deterministic minting and registry APIs from actual independent-platform identity reconciliation. | **Project-local implementation; cross-platform binding planned/unknown** [audit: evidence/backend-inventory.json:143-155; audit: parts/csharp.md:79-87]. |
| PAPER-C14 | The conceptual information-update flow includes extraction, identity resolution, Ontograph grounding, BOT/IFC/bSDD candidates, Topologic analysis, operator review, and validation (P143-P147). | Treat the flow as target architecture unless each connector and approval leg is evidenced. | **Planned architecture; selected legs implemented.** |
| PAPER-C15 | Authoring follows tag → recognise → preview → confirm → publish (P147). | ComputGraph path implements this as a bounded human-confirmed workflow; live Rhino UAT remains open. | **Implemented path, unknown live readiness** [audit: evidence/backend-inventory.json:101-113; audit: evidence/gsd-audit-uat.json:1-73]. |
| PAPER-C16 | CQ1 proves inspectable rule decomposition and shared-vocabulary grounding (P150-P154). | Use the deposited demonstration query/result as paper evidence; backend rule ingest supports related graph persistence. | **Demonstration established; runtime parity not independently reproduced in this review.** |
| PAPER-C17 | CQ2 proves 57 per-object rows, including 32 violations, with traceability to the Design State (P155-P162). | Preserve the reported demonstration result, but do not generalize to every C# retrieval path. | **Demonstration established; C# replay path partial and potentially contradicted** [audit: parts/csharp.md:107-113]. |
| PAPER-C18 | CQ3 proves bidirectional `ATTRIBUTE_OF` trace between rule atom and parameter (P163-P169). | Require a live graph fixture containing the exact bridge and both forward/reverse queries. | **Unknown/contradicted in inspected runtime:** no `ATTRIBUTE_OF` writer/query found; current path uses `PARAM_LINK` [audit: evidence/backend-inventory.json:216-219]. |
| PAPER-C19 | CQ4 proves OWL consistency, SHACL conformance, and OOPS!-style catalogue quality (P170-P175). | Keep as schema/demonstration evidence and identify the exact module, overlay, shape set, reasoner, and run. | **Paper evidence; runtime artefacts present, independent reproduction status unknown** [audit: evidence/ontology-dg-shapes-ttl.json:1-7; audit: evidence/ontology-dg-disjointness-ttl.json:1-7]. |
| PAPER-C20 | The expressiveness boundary is a subset of OWL+SWRL; no disjunction, complex class expressions, or temporal constraints; open-world absence requires complete population plus SHACL closure (P179-P180). | This is aligned with the audit and should become the central limitation statement. | **Aligned, with additional runtime detail needed:** empty bindings and unsupported built-ins currently collapse into failure/unknown states [audit: parts/csharp.md:47-69]. |
| PAPER-C21 | Future work includes independent authoring environments, identity-conflict resolution, IFC exchange, BOT/Topologic correspondence, LLM accuracy/abstention/workload, governance scalability, larger graphs, disjunction/temporal rules, and requirement-driven exchange (P181, P185). | Preserve as the revised empirical roadmap; map each item to a GSD-ALIGN work package below. | **Planned.** |
| PAPER-C22 | The conclusion claims durable, queryable, auditable, versioned, re-executable rules and a vendor-neutral open-standard ecosystem (P183-P187). | Narrow “re-executable” to deterministic paths with complete inputs and immutable artefact snapshots; qualify vendor-neutral interoperability as architectural intent. | **Partial/conditional; not a blanket runtime claim.** |

## 5. Theory–Implementation Alignment Matrix

Status vocabulary is defined in §2.1. “Target evidence” is the minimum evidence required before strengthening the paper claim.

| Alignment topic | Paper reference | Repository/audit evidence | Status | Gap or contradiction | Target evidence / decision |
|---|---|---|---|---|---|
| Rule as durable inspectable graph artefact | PAPER-C02, PAPER-C10, PAPER-C16; P078, P151-P154 | Rule/Atom/Var/Literal ingestion and graph persistence [audit: evidence/backend-inventory.json:13-38] | Implemented/partial | Active workflow drift and no complete revision model | Freeze a rule envelope containing source text, normalized atoms, model/provider, prompt hash, provenance, and revision parent. |
| Four typed SWRL atom classes | PAPER-C10; P078, P122 | C# parser classifies built-ins/classes/data properties but has no ObjectPropertyAtom branch [audit: parts/csharp.md:21-29] | Partial | Two-argument object predicates can be misclassified | Add parser conformance fixtures or narrow manuscript language to schema-level atom typing. |
| Violation-first semantics | PAPER-C10, PAPER-C20; P107-P121, P179 | C# evaluator and backend rule validation implement bounded violation patterns [audit: parts/csharp.md:31-45; audit: evidence/backend-inventory.json:116-127] | Implemented subset | Empty population and unsupported built-ins are semantically ambiguous | Introduce explicit `not_evaluated`, `no_population`, `unsupported`, `indeterminate`, `passed`, `failed`. |
| OWL/SWRL/SHACL service partition | PAPER-C11; P123-P130, P170-P175 | `dg-reasoner` sidecar and SHACL/OWL artefacts; backend explicitly partitions deterministic checks [audit: evidence/backend-inventory.json:116-127] | Implemented/partial | No unified provenance envelope across services | Record service, version, input graph hash, shape/ontology/rule version, and result hash per run. |
| Five-layer LPG | PAPER-C06; P094-P101 | Ontograph/Metagraph/ValidGraph/SpecGraph context and ComputGraph paths exist [audit: evidence/backend-inventory.json:41-55,101-127] | Partial | General bidirectional projection service not found; ComputGraph is separate | Decide whether five layers are logical partitions or a normative runtime contract; publish schema-to-route coverage. |
| Six typed bridges | PAPER-C07; P096-P097 | `REFERS_TO` and validation paths exist; `ATTRIBUTE_OF` not found; governance bridges are not end-to-end [audit: evidence/backend-inventory.json:209-239] | Partial/contradicted for some bridges | Paper can overstate bridge completeness | Build a bridge inventory fixture and query each direction. |
| Immutable Design State | PAPER-C09; P102-P105 | Manual and automatic capture paths; auto status mutation; standalone ParamState; C# v2 serialization excludes geometry/class [audit: evidence/backend-inventory.json:171-185; audit: parts/csharp.md:99-105] | Partial/contradicted as universal | State snapshot, run status, and payload versions are not one contract | Adopt immutable `statePayloadHash`, complete membership manifest, versioned schema, and read/write parity tests. |
| Per-object verdict persistence | PAPER-C17; P155-P162 | Python validation stores `ValidationEntity`; C# query repeats overall status across ObjStates [audit: evidence/backend-inventory.json:158-169; audit: parts/csharp.md:107-113] | Partial | Retrieval consumer may lose per-object distinctions | Make `ValidationEntity` canonical and test mixed pass/fail replay end to end. |
| ComputGraph structural capture | PAPER-C12, PAPER-C15; P140-P147 | Canvas pull, topology, recognition, preview, confirmed publish [audit: evidence/backend-inventory.json:101-113] | Implemented/unknown live | Solver semantics not captured; Rhino UAT pending | Keep “structural ComputGraph” wording; complete phases 33-35 UAT. |
| FBS/behaviour semantics | PAPER-C12; P140, P161 | C# and backend capture nodes/wires/tags, not algorithms or solver execution [audit: parts/csharp.md:123-129] | Unsupported/planned | Structural graph cannot prove Behaviour semantics | Either define a traceability-only ComputGraph or specify an executable intermediate representation experiment. |
| Platform-neutral identity | PAPER-C13; P137-P139, P184 | Python identity registry and C# deterministic minting [audit: evidence/backend-inventory.json:143-155; audit: parts/csharp.md:89-97] | Partial | No live Revit/IFC/Speckle conflict resolution; GH ObjState ID diverges from core helper | Define authority, conflict, merge, detach, and provenance policy; run independent-platform fixtures. |
| IFC/bSDD/IDS exchange | PAPER-C14, PAPER-C21; P101, P180-P185 | Standards references and procedural correspondence design; no inspected end-to-end IFC exchange | Planned/unknown | Class-level correspondence is not instance exchange | Create one requirement-driven IDS/IFC/bSDD fixture and record rejected/accepted mappings [1]-[6]. |
| BOT/topology alignment | PAPER-C14, PAPER-C19; P101, P133, P180, P184 | Local ontology/source artefacts and literature ledger; no child literature artifact | Planned/unknown | Topologic evidence and BOT semantics not empirically cross-checked | Define relation precision/recall fixture and provenance rule [7], [10]-[14]. |
| AI authoring and abstention | PAPER-C03, PAPER-C21; P141-P147, P181 | Bounded generation, recognition, candidate generation, human acceptance [audit: evidence/backend-inventory.json:13-38,101-141] | Prototype/partial | Confidence constants provisional; pending recognition UAT; no measured workload | Benchmark accuracy, abstention, review time, and invalid-output rate by model/provider. |
| Deterministic re-execution | PAPER-C22; P051, P081, P127, P183 | Deterministic structural/SHACL/SWRL subsets; LLM paths are provider/model/time dependent [audit: evidence/backend-inventory.json:231-234] | Partial/contradicted if universal | No immutable prompt/model snapshot for all LLM writes | Split deterministic validator reproducibility from AI proposal reproducibility. |
| CDE governance | PAPER-C08, PAPER-C21; P097, P133, P181 | Note CRUD, sessions, update confirmation; no steward state machine/impact analysis [audit: evidence/backend-inventory.json:236-239] | Planned/partial | Operational governance claim exceeds code | Specify governance states, actor authorization, impact graph, release, rollback, and audit trail. |
| Security and tenancy | PAPER-C05, PAPER-C08; P094, P129, P133 | Project predicates and connector tokens; browser localStorage auth and direct graph proxy [audit: evidence/backend-inventory.json:188-197] | Partial/contradicted | Project scoping is not tenant authorization | Treat security as a release gate before external multi-user evaluation. |

## 6. Literature and Standards

### 6.1 Standards boundary

The registered citation ledger supports a standards stack that is useful for the target architecture but should not be read as proof of implementation:

* **IDS and bSDD:** Use IDS for requirement-driven information delivery and bSDD references for controlled classification/term identity. The ledger registers buildingSMART IDS, bSDD API, and bSDD references in IDS/IFC [1]-[3]. The immediate alignment requirement is procedural: a DG rule or requirement should retain the external identifier, source release, mapping type, approval state, and rejection rationale.
* **IFC:** IFC is the exchange/classification context, not evidence that the current repository imports or exports IFC instances. The ledger registers the IFC schema specification [4]. The paper's P180-P185 wording should preserve this boundary.
* **OWL:** OWL is appropriate for terminological consistency and class/property axioms. The current paper's OWL 2 DL claims should point to the exact core, disjointness overlay, and export used in the reported run; the C# evaluator should not be called an OWL/SWRL reasoner [7].
* **SHACL:** SHACL is the closed-world structural/data-integrity layer. The repository has a shape artefact with 20 node shapes [audit: evidence/ontology-dg-shapes-ttl.json:1-7]. The paper's open-world mitigation in P179 is conceptually aligned, but the runtime must distinguish a missing population from a passed validation.
* **JSON-LD/RDF:** JSON-LD and RDF are suitable interchange/projection forms for provenance and sidecar validation, but the report found no evidence that every LPG layer has a reversible, lossless JSON-LD/RDF projection [9].
* **IDS/IFC/bSDD governance:** Standards references should be treated as external identifier and requirements contracts. They do not automatically establish semantic equivalence, object identity, or exchange completeness.

### 6.2 Literature implications

The registered literature set contains the paper's main AEC compliance, ontology, BIM, semantic-web, AI, and design-grammar references, including the DOI entries recorded in `evidence/literature-ledger.json` [audit: evidence/literature-ledger.json:1-233]. The report uses these sources only to frame decisions already present in the paper and repository; it does not infer unverified findings from titles that are absent from the ledger. The most important literature-to-implementation implications are:

1. Rule interpretation, model preparation, execution, and reporting should remain separate stages; the current multi-service architecture follows this separation [10]-[12].
2. Property graphs reduce transformation burden, but graph convenience does not remove the need to specify open-world/closed-world semantics, projection loss, and provenance [7]-[9], [13]-[16].
3. Design-grammar claims require inspectable, revisable rule objects, not only natural-language prompts; the Metagraph path is the strongest implementation correspondence [10], [16]-[19].
4. AI-assisted authoring must be evaluated by accuracy, abstention, invalid proposal rate, and operator workload, not by successful generation alone. This is explicitly future work in P181 and P185 and is not established by the current pending UAT [audit: evidence/gsd-audit-uat.json:53-73].
5. Interoperability claims require independent authoring environments and conflict fixtures; registry endpoints and deterministic hashes are necessary but insufficient [1]-[6], [17]-[19].

## 7. Target Architecture, Alternatives, and Decision Experiments

### 7.1 Recommended target architecture

Adopt a **contract-first, partitioned reasoning architecture** with one canonical evidence envelope:

```text
Authoring / BIM / CDE inputs
        |
        v
[1] Ingest + identity resolution + provenance
        |
        +--> Ontograph vocabulary / external candidates
        +--> Metagraph rules / typed atoms / revisions
        +--> ComputGraph structural context
        +--> Immutable Design State snapshot
        |
        v
[2] Explicit rule-owner router
        |
        +--> deterministic violation evaluator (bounded SWRL subset)
        +--> OWL consistency sidecar
        +--> SHACL structural/data validation
        +--> geometry/topology evidence service
        |
        v
[3] Canonical ValidationRun + ValidationEntity evidence
        |
        +--> Speckle/viewer overlay
        +--> Grasshopper retrieval/replay
        +--> queryable provenance and audit
```

Every stage should emit: `project`, `definition`, `dgId`, source representation, input hash, schema/ontology/rule/shape version, execution service/version, model/provider metadata where applicable, start/end time, status, warnings, and output hash. The canonical status vocabulary should include at least `passed`, `failed`, `unknown`, `not_evaluated`, `no_population`, `unsupported`, `indeterminate`, and `error`.

### 7.2 Alternative A — Keep the current hybrid stack and narrow claims

**Description:** Retain Python data service, n8n, Neo4j, dg-reasoner, C# Grasshopper path, and Speckle. Repair contracts and evidence without replacing the runtime.

**Advantages:** Lowest migration cost; preserves working tests and parent-verified builds; matches the paper's explicit service partition.  
**Disadvantages:** More compatibility seams; n8n activation/drift and mixed v1/v2 readers remain; graph-layer bridge coverage must be documented rather than assumed.  
**Recommendation:** **Preferred near-term option.**

**Decision experiment DE-01:** Run the same fixture through backend validator, dg-reasoner, C# evaluator, and persisted replay. Compare rule IDs, object IDs, statuses, warnings, input hashes, and output hashes. Acceptance: identical canonical statuses for supported cases and explicit non-equivalence for unsupported cases.

### 7.3 Alternative B — Make the RDF/OWL/SHACL sidecar canonical

**Description:** Convert project graph data to RDF/JSON-LD, use OWL/SHACL services as the normative semantic layer, and retain Neo4j as a projection/query store.

**Advantages:** Clear standards semantics; stronger alignment to OWL/SHACL claims; easier external standards exchange.  
**Disadvantages:** Projection cost; possible loss of LPG ergonomics; existing C# and n8n paths would require adapters; performance and identity round-trip need measurement.

**Decision experiment DE-02:** Export one representative Metagraph, Design State, ComputGraph, and ValidGraph fixture to RDF/JSON-LD; re-import it; run SHACL and selected queries; measure lossless round-trip for IDs, order, provenance, geometry references, and per-object results. Acceptance: zero loss for normative fields or an explicit loss register.

### 7.4 Alternative C — Make a typed domain service canonical and use graph stores as projections

**Description:** Introduce typed APIs/events for rules, states, identity, validation, and provenance; retain Neo4j/Speckle as materialized views.

**Advantages:** Strong contracts, authorization, versioning, and testability; easier immutable Design State semantics.  
**Disadvantages:** Largest refactor; risks disconnect from existing ontology artefacts and query workflows.

**Decision experiment DE-03:** Define JSON schemas and event fixtures for `RuleRevision`, `DesignStateSnapshot`, `IdentityBinding`, and `ValidationRun`; replay them into Neo4j and the C# client. Acceptance: deterministic reconstruction and schema evolution tests across one version upgrade.

### 7.5 Alternatives decision

Choose **Alternative A for the next alignment milestone**, while borrowing the evidence-envelope and canonical-status requirements from B/C. Reconsider B or C only after DE-01 and DE-02 quantify projection loss, or if security/tenancy requirements make the current route unacceptable.

## 8. Revised GSD Plan

The plan below incorporates the dedicated GSD audit at `gsd.md` and its machine-readable proposals at `evidence/gsd-proposed-updates.json`, while adding theory–implementation alignment work not already owned by the active roadmap. IDs are intentionally new and stable: `GSD-ALIGN-01` through `GSD-ALIGN-16`.

> **Renamed 2026-09-19 — use `ALIGN-P01..P16`.** These sixteen IDs collided with the
> control-plane register `GSD-ALIGN-001..013` in `gsd.md`. The rows below keep their original
> numbering for provenance; §8.2 maps each to its `ALIGN-Pnn` identifier and its owning
> milestone/phase. Cite `ALIGN-Pnn` in all new artifacts.

| ID | Work package | Deliverable | Depends on | Verification gate | Status |
|---|---|---|---|---|---|
| GSD-ALIGN-01 | Freeze claim/status vocabulary | `implemented/partial/planned/prototype/unsupported/contradicted/unknown` glossary and manuscript claim register | None | Every PAPER-C row has one status and evidence anchor | Planned |
| GSD-ALIGN-02 | Canonical evidence envelope | JSON schema for input/output hashes, service version, provenance, model metadata, warnings, and status | 01 | Fixture validates across Python, C#, reasoner, and persisted run | Planned |
| GSD-ALIGN-03 | Rule parser conformance | Typed parser fixtures including ObjectPropertyAtom, malformed arity, literals with commas, and unsupported syntax | 02 | Parser either succeeds correctly or returns typed unsupported result | Planned |
| GSD-ALIGN-04 | Validation status semantics | Explicit `no_population`, `not_evaluated`, `unsupported`, `indeterminate`, and `error` states | 02, 03 | Empty/missing/unsupported/mixed fixtures preserve distinct statuses | Planned |
| GSD-ALIGN-05 | State v2 replay closure | Serialize/deserialize geometry reference, ClassIri, lists, enums, and schema version | 02, 04 | Publish → query → replay reproduces canonical state hash | Planned |
| GSD-ALIGN-06 | Per-object verdict preservation | Make `ValidationEntity` canonical for replay and test mixed object outcomes | 02, 05 | One failing and one passing object remain distinct after C# retrieval | Planned |
| GSD-ALIGN-07 | Identity contract convergence | Align `ObjectStateComponent` minting with `DesignStateIdGenerator`; define project/definition/object/representation authority | 02 | Golden vectors and conflict fixtures pass | Planned |
| GSD-ALIGN-08 | `ATTRIBUTE_OF` decision | Either implement exact bridge or revise paper/spec to `PARAM_LINK` and document semantics | 01, 02 | Forward and reverse trace query fixture; decision recorded | Decision required |
| GSD-ALIGN-09 | Standards exchange spike | IDS requirement → bSDD/IFC candidate → operator decision → DG provenance record | 02, 07 | Accepted/rejected mapping fixture and round-trip report | Planned |
| GSD-ALIGN-10 | ComputGraph live UAT | Complete phases 33-35 bridge, recognition, preview, and publish tests | Runtime access to Rhino/LLM | Pending UAT items resolved; blocked recognition either unblocked or documented | Unknown/pending |
| GSD-ALIGN-11 | Parameter generation UAT | Complete phase 38 reinstatement, accept gate, and no-preaccept mutation tests | 02, 05 | Three pending tests pass with evidence | Pending |
| GSD-ALIGN-12 | Auto-validation semantics | Reproduce and correct the all-false ValidStatus issue; define capture/run lifecycle | 02, 04 | Known regression fixture passes and failure statuses are typed | Prototype |
| GSD-ALIGN-13 | Determinism benchmark | Separate deterministic validator repeatability from LLM proposal repeatability | 02 | Same fixture repeated; hashes and status comparison report | Planned |
| GSD-ALIGN-14 | Security/tenancy gate | Server-side user/tenant authorization, direct Neo4j exposure review, secret/config hardening | 02 | Unauthorized cross-project and direct-proxy tests fail closed | Partial/high risk |
| GSD-ALIGN-15 | Bridge and governance inventory | Machine-readable coverage of six paper bridges, CDE approval states, impact analysis, and release provenance | 01, 08, 09 | No bridge is labelled implemented without a writer, reader, and fixture | Planned |
| GSD-ALIGN-16 | Manuscript alignment pass | Update R15.7 claims, limitations, availability, and evidence table using PAPER-C IDs | 01-15 | Every strong claim has source/evidence; every unsupported claim is narrowed or marked future work | Planned |

### 8.1 GSD sequencing

1. **Contract gate:** GSD-ALIGN-01, 02, 03, 04.
2. **Replay/identity gate:** GSD-ALIGN-05, 06, 07, 08.
3. **Empirical gate:** GSD-ALIGN-09, 10, 11, 12, 13.
4. **Release gate:** GSD-ALIGN-14, 15, 16.

Do not regenerate the stale Graphify database as part of this plan. If graph context is needed later, rebuild it against the current commit in a separately recorded evidence run.

### 8.2 Mapping to updated GSD plans

Added 2026-09-19 after the cross-milestone GSD discussion. Source of decisions:
`.planning/milestones/v12.0-CONTEXT.md`; discussion record:
`.planning/milestones/v12.0-DISCUSSION-LOG.md`.

**Identifier change.** This section's work packages were renamed from `GSD-ALIGN-01..16` to
**`ALIGN-P01..P16`**. The `GSD-ALIGN-` prefix is retained by the control-plane reconciliation
register in `gsd.md` / `evidence/gsd-proposed-updates.json` (`GSD-ALIGN-001..013`), which is
already machine-readable and consumed by tooling. The two registers previously collided.
`ALIGN-Pnn` in this table corresponds one-to-one, in order, with the `GSD-ALIGN-01..16` rows
of the table in §8.

**Routing decision.** The sixteen packages were triaged against existing milestone ownership.
The unowned residue forms a new isolated milestone **v12.0 — Theory–Implementation Alignment**,
phases **1200–1205** (per the repository's `vX.Y → X·100 + Y·10` numbering convention with a
ten-phase cap; v11.0 occupies 1101–1109 in the 1100 block). v12.0 is **not activated** —
v9.0 Phase 40 remains the frontier, and `.planning/phases/`, `STATE.md`, and the active
`REQUIREMENTS.md` are untouched.

| Package | Work package | Owner | Phase / item |
|---|---|---|---|
| ALIGN-P01 | Freeze claim/status vocabulary | v12.0 **+** v11.0 | 1200 (vocabulary) + 1105 (spec propagation) |
| ALIGN-P02 | Canonical evidence envelope | v12.0 **+** v11.0 | 1200 (envelope) + 1105 (provenance metadata) |
| ALIGN-P03 | Rule parser conformance | **v12.0** | 1201 |
| ALIGN-P04 | Validation status semantics | **v12.0** | 1200 |
| ALIGN-P05 | State v2 replay closure | **v12.0** | 1202 |
| ALIGN-P06 | Per-object verdict preservation | **v12.0** | 1202 |
| ALIGN-P07 | Identity contract convergence | **v12.0** | 1203 |
| ALIGN-P08 | `ATTRIBUTE_OF` decision | **v12.0** | 1203 — both branches costed, decision open |
| ALIGN-P09 | Standards exchange spike | v11.0 | 1106 |
| ALIGN-P10 | ComputGraph live UAT | v9.0 | Phase 40 + `gsd.md` GSD-ALIGN-005/007 |
| ALIGN-P11 | Parameter generation UAT | v9.0 | Phase 40 + `gsd.md` GSD-ALIGN-007 |
| ALIGN-P12 | Auto-validation semantics | v9.0 | Phase 40 + `gsd.md` GSD-ALIGN-009 |
| ALIGN-P13 | Determinism benchmark | **v12.0** | 1204 |
| ALIGN-P14 | Security/tenancy gate | **v12.0** | 1205 — own phase, release-blocking |
| ALIGN-P15 | Bridge and governance inventory | v11.0 | 1106 |
| ALIGN-P16 | Manuscript alignment pass | v11.0 | 1107 |

**v12.0 phase structure.** Six phases, mapping onto §8.1's four gates:

| Phase | Scope | Gate |
|---|---|---|
| 1200 | Contract + canonical status vocabulary + cross-service golden fixture + **DE-01** | Contract |
| 1201 | Rule parser conformance (C# `DG.Core` typed atoms) | Contract |
| 1202 | Design State v2 replay closure + per-object verdict preservation | Replay/identity |
| 1203 | Identity contract convergence + `ATTRIBUTE_OF` decision | Replay/identity |
| 1204 | Determinism benchmark | Empirical |
| 1205 | Security and tenancy release gate | Release |

The golden fixture of §11 item 3 is **Phase 1200's deliverable**, not a prerequisite spike.
DE-01 (§7.2) runs against it, and phases 1201–1205 verify against that single artifact.

**Sequencing prerequisite.** The control-plane reconciliation (`gsd.md` `GSD-ALIGN-001..013`,
`auto` class) executes **before** v12.0 is planned, so the milestone is scoped against true
phase status rather than the recorded drift. Highest-value items: 001 (one status vocabulary
across STATE/ROADMAP/PROJECT/REQUIREMENTS), 003 (record Phase 35 SC1 as a measured FAIL —
M1 = 0.03125 against a 0.60 gate — not as blocked), 002 (UAT coverage register from raw
per-file scans), 009 (Phase 39 validation frontmatter vs. passed verification).

**Correction to §4 PAPER-C18 and §5.** Verified against the working tree on 2026-09-19:
`dgc:attributeOf` / `ATTRIBUTE_OF` **is declared in the ontology TBox** —
`ontology/DesignGrammar-V7.md:707`, with the Parameter bridge note at line 414 and
corresponding entries in the `.owl` serializations — but has **zero runtime writers and zero
readers** (no occurrence in `data-service/*.py` or `DG/src`). `PARAM_LINK` is the implemented
relation (`computgraph_publish.py`, `cg_structure_checks.py`, `dg_context.py`, and specified in
`spec/DATABASE.md` and `spec/RULE-PARTITION-POLICY.md`). The finding stands, but the bridge is
**declared-but-unimplemented** rather than absent: implementing it requires no TBox change,
while revising the paper to `PARAM_LINK` leaves the TBox committed to a property nothing uses
and so needs an explicit note or retraction. This shifts the relative cost of the two branches
in §12.2 clarification 1, which remains the author's decision.

**Out of scope for v12.0**, recorded with named owners: Alternatives B and C with DE-02/DE-03
(revisit only after DE-01 and DE-02 quantify projection loss, per §7.5); Graphify regeneration
(§8, risk R-15); v4.0 BOT Ontology Bridge (`gsd.md` GSD-ALIGN-011, future scope).

## 9. Research and Validation Plan

### 9.1 Research questions

| RQ | Question | Measure | Minimum result |
|---|---|---|---|
| RQ1 | Does the bounded validator produce the same verdict from source rule, graph row, C# binding, and persisted replay? | Status/hash agreement on a fixture suite | 100% agreement for supported cases; typed disagreement for unsupported cases |
| RQ2 | Does the system preserve per-object verdict identity through publish and retrieval? | Mixed pass/fail object fixture | No aggregate-to-object replication error |
| RQ3 | Does Design State remain immutable and replayable across manual and automatic paths? | Snapshot hash, membership, schema/version, replay | Same canonical state hash after round-trip; explicit status transitions outside snapshot |
| RQ4 | Does the identity registry resolve GH/Revit/IFC/Speckle representations without unsafe ambiguity? | Independent-platform conflict matrix | Deterministic accept/reject/merge decision with provenance |
| RQ5 | Does AI assistance improve authoring without unacceptable review burden? | Precision, recall, abstention, invalid proposal rate, review time | Report confidence intervals and human workload; no single accuracy number alone |
| RQ6 | Does standards alignment support requirement-driven exchange? | IDS/bSDD/IFC mapping acceptance and round-trip | Accepted/rejected mappings are reproducible and versioned |
| RQ7 | Does ontology/SHACL projection preserve normative semantics? | RDF/JSON-LD round-trip and shape/reasoner results | No silent loss of IDs, order, provenance, or verdict granularity |

### 9.2 Validation layers

* **Static:** source/route/schema inventories; paper claim register; bridge and status vocabulary checks.
* **Unit:** parser edge cases, status semantics, ID golden vectors, serializer round-trips, geometry warnings.
* **Service integration:** data-service ↔ Neo4j ↔ reasoner ↔ n8n; fixture-based execution with explicit hashes.
* **Host integration:** C# Grasshopper components, Rhino bridge, preview persistence, geometry payloads.
* **Cross-platform:** GH/Revit/IFC/Speckle representation binding and conflict policy.
* **Human/UAT:** tag–recognise–preview–confirm–publish, AI abstention and review effort, governance approval.
* **Release:** security/tenancy, compose reproducibility, CI, documentation and exact source/artefact hashes.

### 9.3 Current validation gaps

The available UAT artefact contains 10 items: nine pending and one blocked. Pending coverage includes live canvas pull and MCP parity, marker persistence, publishability gating, deterministic structural validation, parameter reinstatement, and no-preaccept mutation. Recognition quality is blocked on the live LLM/Rhino path [audit: evidence/gsd-audit-uat.json:1-139]. These results are **unknown**, not failures and not passes.

## 10. Risk Register

| ID | Risk | Evidence | Likelihood | Impact | Mitigation/owner decision | Class |
|---|---|---|---|---|---|---|
| R-01 | Paper overstates C# as full SWRL execution | Bespoke parser/evaluator subset [audit: parts/csharp.md:21-45] | High | High | Narrow claim; implement conformance only if needed | Manual-only |
| R-02 | Empty population is interpreted as compliance/failure incorrectly | Empty bindings collapse diagnostic meaning [audit: parts/csharp.md:47-61] | High | High | Adopt typed status policy and fixtures | Manual-only then code |
| R-03 | Unsupported built-ins appear as ordinary failures | Exception converted to `Passed=false` [audit: parts/csharp.md:39-45] | High | High | Add `unsupported` status and publication policy | Manual-only policy |
| R-04 | Design State replay is lossy | v2 omits geometry/ClassIri; readers mix v1/v2 [audit: parts/csharp.md:99-105] | High | High | GSD-ALIGN-05 | Auto-fixable after contract decision |
| R-05 | Per-object results are replaced by run-level status | C# query repeats aggregate [audit: parts/csharp.md:107-113] | High | High | Canonical `ValidationEntity` replay fixture | Auto-fixable after contract decision |
| R-06 | GH ObjState identity diverges from core identity | Different ID formulas [audit: parts/csharp.md:89-97] | Medium | High | GSD-ALIGN-07 golden vectors | Auto-fixable after authority decision |
| R-07 | Geometry is silently omitted or lossy | Tessellation/curve approximation/no warning [audit: parts/csharp.md:71-77] | Medium | Medium | Add geometry warning/status and host tests | Auto-fixable |
| R-08 | Cross-platform identity is assumed from hashing | No Revit/IFC/Speckle connector in C# [audit: parts/csharp.md:79-87] | High | High | Independent-platform experiment | Manual-only/unknown |
| R-09 | `ATTRIBUTE_OF` is claimed but not emitted | Backend uses `PARAM_LINK` [audit: evidence/backend-inventory.json:216-219] | High | High | Decide implementation vs claim revision | Manual-only |
| R-10 | CDE governance is confused with note CRUD | Missing steward/impact/release workflow [audit: evidence/backend-inventory.json:236-239] | High | High | Define governance state machine | Manual-only |
| R-11 | Browser/project security is not tenancy security | Client-side auth and direct Neo4j proxy [audit: evidence/backend-inventory.json:188-197] | High | Critical | Release-blocking security phase | Manual-only then code |
| R-12 | LLM paths are presented as deterministic | Provider/model/time dependence [audit: evidence/backend-inventory.json:231-234] | High | High | Snapshot model/prompt and separate reproducibility measures | Manual-only |
| R-13 | Auto-validation all-false issue invalidates claims | Historical F-39-01 record [audit: evidence/backend-inventory.json:171-185] | Medium | High | Reproduce/correct/regression-test | Auto-fixable after semantic decision |
| R-14 | Pending/blocked UAT is silently treated as complete | 9 pending, 1 blocked [audit: evidence/gsd-audit-uat.json:125-139] | High | High | Keep status unknown; complete host tests | Skip until environment available |
| R-15 | Stale graphify context misleads planning | Parent handoff: graph at old commit | Medium | Medium | Do not regenerate in this report; rebuild in controlled task | Skip for current report |
| R-16 | Compose/default secret exposure persists | Compose inventory records secrets literal [audit: evidence/compose-inventory.json:24-26] | High | Critical | Security gate and secret rotation | Manual-only/release blocker |

## 11. Immediate Actions: 10–20 Items

The following 16 actions are ordered by decision value and risk reduction. They are actions, not completed fixes.

1. **Freeze the PAPER-C register** and update the manuscript review copy so every substantive claim has a status and paragraph anchor.
2. **Adopt the canonical validation status vocabulary** before changing evaluator behaviour; specifically decide empty bindings, missing population, unsupported built-ins, and SHACL timeout semantics.
3. **Create one cross-service golden fixture** containing a rule, four atom types, two objects, one passing object, one failing object, a Design State, and a geometry reference.
4. **Run DE-01** across Python, dg-reasoner, C#, and persisted replay; record hashes and non-equivalences.
5. **Resolve `ATTRIBUTE_OF`**: implement a typed bridge with forward/reverse queries, or revise PAPER-C18 and the corresponding conclusion language to describe `PARAM_LINK`.
6. **Close the v1/v2 serializer seam** and prove publish → query → replay with geometry/class membership preserved or explicitly excluded from the normative state contract.
7. **Fix per-object replay semantics** so a mixed run cannot return one aggregate status for every object.
8. **Align ObjState identity minting** between Grasshopper and core services, then regenerate golden vectors without altering historical IDs unless migration is approved.
9. **Add parser edge-case fixtures** for ObjectPropertyAtom, quoted commas, escaping, malformed arity, duplicate arrows, datatype/language literals, and unsupported syntax.
10. **Add geometry observability**: unsupported geometry and approximation must emit warnings or typed status, not disappear silently.
11. **Complete pending phases 33–35 host UAT** for bridge, marker persistence, recognition, preview, and publish; preserve blocked status if Rhino/LLM access is unavailable.
12. **Complete phase 38 parameter UAT** for reinstatement, unresolved IDs, and no mutation before acceptance.
13. **Reproduce the auto-validation all-false issue** and decide whether capture, SHACL, ValidStatus, or run completion owns each transition.
14. **Run DE-02** on one representative graph export to RDF/JSON-LD and back, measuring order, IDs, provenance, geometry references, and verdicts.
15. **Build one IDS/bSDD/IFC exchange fixture** with accepted and rejected mappings and explicit operator provenance [1]-[6].
16. **Treat security/tenancy as a release gate**: remove direct browser graph privilege, add server-side authorization, and rotate/default-secret handling before external multi-user evaluation.

## 12. Missing Inputs and Required Clarifications

### 12.1 Missing inputs

* No material child artifact is missing from the indexed audit bundle; `evidence/integrated-index.json` records 22/22 required artifacts present. The full machine-readable claim, GSD, literature, backend, and knowledge-graph registers remain the authoritative detailed records.
* No independent artifact was supplied that reproduces the paper's CQ1-CQ4 graph queries against the current `HEAD`.
* No live Revit, IFC, Speckle conflict-resolution, or Rhino.Inside evidence was found in the inspected C# audit.
* No end-to-end standards exchange fixture was supplied for IDS/bSDD/IFC.
* No measured LLM accuracy, abstention, reviewer workload, or provider/model comparison dataset was supplied.
* No complete bridge inventory proves writers, readers, and fixtures for all six paper bridges.
* No current Graphify rebuild was supplied; the latest available snapshot is one commit behind `HEAD`, and the older 5,412-node capture is retained as historical context.

### 12.2 Required clarifications

1. Is `ATTRIBUTE_OF` normative for the next paper version, or is `PARAM_LINK` the accepted implementation contract?
2. Does a missing binding mean `unknown`, `not_evaluated`, `no_population`, or fail-closed `failed`? The choice changes both runtime semantics and the paper's P179 explanation.
3. Is a Design State a content-equivalence identity or a capture-event/version identity? Current IDs exclude label and capture time [audit: parts/csharp.md:89-105].
4. Are geometry and `ClassIri` normative members of a replayable v2 Design State, or intentionally outside the persistence contract?
5. Which service owns canonical per-object verdicts: C# evaluator, data service, ValidGraph, or a versioned evidence envelope?
6. Is ComputGraph intended only as a structural trace, or must it encode executable Behaviour/FBS semantics?
7. Which platform is identity authority when GH, Revit, IFC, Speckle, and viewer identifiers conflict?
8. Is the five-layer model a logical organizational partition or a mandatory runtime/projection contract?
9. What is the authorization model for project isolation and CDE governance? Project predicates alone are not sufficient tenancy policy.
10. Which LLM provider/model/prompt snapshot is required for a claim of reproducibility?
11. Which pending UAT environment can be made available: Rhino, Grasshopper, LLM gateway, Neo4j compose, Speckle, and browser UI?
12. Should the manuscript report parent-provided test counts as current evidence, or should all counts be regenerated under a clean commit and captured in a new evidence bundle?

## 13. Audit-Fix Classification

The user invoked `gsd-audit-fix`, but this investigation produces **no code fixes**. Classification is therefore a planning/reporting outcome only.

| Finding family | Classification | Rationale | Action in this investigation |
|---|---|---|---|
| Claim wording that overstates reasoner scope, interoperability, governance, or determinism | **Manual-only** | Requires authorial/theoretical decisions, not a safe mechanical patch | Reported as PAPER-C and alignment decisions; no manuscript edit made |
| Empty-binding, unsupported-builtin, state-identity, bridge, and verdict-granularity policies | **Manual-only** | Semantics and authority must be chosen before code changes | Raised as clarifications and GSD gates |
| Serializer reader mismatch, per-object aggregate replication, ObjState ID mismatch, parser fixtures, geometry warnings | **Auto-fixable after decision** | Likely localized implementation/test changes, but unsafe before contract decisions | Classified only; no source edits made |
| Pending Rhino/LLM/Speckle/IFC UAT | **Skip** | Requires unavailable or separately provisioned live environments | Kept `pending`, `blocked`, or `unknown`; no fabricated result |
| Stale graphify database | **Skip** | User explicitly required no regeneration and it is outside this file's ownership | Recorded as a context limitation |
| Security/tenancy and compose secret exposure | **Manual-only/release blocker** | Requires threat-model, deployment, credential, and authorization decisions | Raised as a release gate; no operational changes made |
| Missing child artifacts | **Skip** | No findings may be invented from absent files | No required child artifact is missing from the indexed audit bundle; unresolved empirical evidence remains listed in §12 |

This classification satisfies the audit-fix requirement while preserving the instruction that this investigation makes no code fixes.

## Sources

The following block is mechanically rendered from `C:/Users/Admin/AppData/Local/hermes/cache/citations/ledger.json`; only registered IDs 1-19 are used in inline citations.

1. https://technical.buildingsmart.org/projects/information-delivery-specification-ids
2. https://technical.buildingsmart.org/services/bsdd/using-the-bsdd-api
3. https://technical.buildingsmart.org/services/bsdd/referencing-bsdd-in-ids-and-ifc
4. https://technical.buildingsmart.org/standards/ifc/ifc-schema-specifications
5. https://github.com/buildingSMART/IDS
6. https://github.com/buildingSMART/IDS/blob/development/Documentation/UserManual/README.md
7. https://www.w3.org/TR/owl11-syntax
8. https://www.w3.org/TR/shacl
9. https://www.w3.org/TR/json-ld
10. https://doi.org/10.1016/j.autcon.2009.07.002
11. https://doi.org/10.1016/j.autcon.2015.12.003
12. https://doi.org/10.1016/j.autcon.2016.10.003
13. https://doi.org/10.1016/j.autcon.2023.105106
14. https://doi.org/10.1016/j.jii.2023.100519
15. https://doi.org/10.1016/j.engappai.2022.104755
16. https://doi.org/10.4018/ijswis.2014040102
17. https://doi.org/10.36680/j.itcon.2025.049
18. https://doi.org/10.1016/j.autcon.2022.104688
19. https://doi.org/10.1016/j.aei.2024.102770
