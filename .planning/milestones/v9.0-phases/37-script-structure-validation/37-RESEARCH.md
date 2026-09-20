# Phase 37: Script Structure Validation MVP - Research

**Researched:** 2026-07-27
**Domain:** Declarative structural validation over a Neo4j property graph (Computgraph) + a grounded read-only LLM consult endpoint
**Confidence:** HIGH (internal codebase contract) / MEDIUM (partition-policy extension, grounding-check design)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Decided

1. **`data-service/cg_structure_checks.py`** + `POST /computgraph/validate` `{project, definitionId?}`:
   Deterministic, LLM-free checks, each returning `{checkId, severity, message, entities[]}`:
   - convention compliance (names parse; normalized variants like `Emr` flagged info-level)
   - orphan `Pattern` (no `HAS_PATTERN` from any Procedure)
   - `Procedure` without any `Interface`
   - `Parameter` without `dataType`
   - dangling `PARAM_LINK` (link to an Interface outside the parameter's procedure chain)
   - `Algorithm` without `Procedure`; `Object` without `HAS_BEHAVIOR` chain
2. **Rule-mapped structural checks:** a declarative mapping shape (JSON, versioned alongside `llm/cypher_catalog.json`) linking a Metagraph `Rule` (by `Rule_Id`) to structural requirements over the Computgraph, e.g.:
   - `requiresProcedure`: name pattern must exist under the Object's Algorithm ("a Frame algorithm must contain a *Truss* procedure")
   - `requiresParameter`: a parameter with given kind/dataType must exist ("height must be a VariableParam")
   - `forbidsOrphan`, `requiresInterface` variants
   Evaluated via parameterized Cypher; report pass/fail per rule with the satisfying/offending entities. This is intentionally a small vocabulary — v10 grows it; the mapping file format is the extension point.
3. **`POST /computgraph/consult`** `{project, definitionId, question}`: assembles the published Computgraph subgraph (via `dg_context.py`) + the question → LLM gateway → answer that cites entity names present in the graph. Strictly read-only; no Cypher execution from LLM output in this phase. This endpoint is the consulting-assistant seed.
4. **Report surface:** validation report JSON consumable by ui-v2 (Graph screen panel) and printable to a GH panel via the bridge (`get_preview_status`-style command or plain HTTP from a small component — decide in planning; lowest-cost option wins, this is MVP).

### Constraints

- SVAL-01/02 checks are deterministic and reproducible — no LLM in the validate path; only `/consult` calls the gateway.
- Checks operate on the *published* Computgraph (Neo4j), not the live canvas — canvas freshness is the architect's responsibility (re-publish first); the report carries `publishedAt` so staleness is visible.
- Rule mapping must not require ontology changes — it references existing `Rule` nodes by id and Computgraph entities by label/property.
- Consult answers must be grounded: prompt instructs citation of entity names; response post-check verifies cited names exist in the subgraph (flag, don't block, on miss).

### Open for planning (Claude's Discretion)

- Rule-mapping file location and shape (`llm/structure_rules.json` vs per-project Neo4j nodes — leaning file-first for MVP, graph-native in v10). **Resolved below: `llm/structure_rules.json`, file-first.**
- Severity taxonomy alignment with the existing validation report conventions (ValidGraph runs). **Resolved below: reuse the SHACL `{violation, warning, info}` mapping.**
- Whether structure validation results are persisted (as a lightweight `Run`-like record) or ephemeral (leaning ephemeral for MVP; persistence when v10 workflows need history). **Resolved below: ephemeral for MVP.**

### Deferred Ideas (OUT OF SCOPE)

- AI *generation* of Grasshopper script parts, on-canvas editing, full consulting assistant — v10 Script Intelligence seed (`.planning/milestones/v10.0-SEED.md`); `/computgraph/consult` here is deliberately a small read-only seed, not the full assistant.
- Bridge write-commands (`add_component`, `connect_components`) — explicitly deferred per REQUIREMENTS.md Out-of-Scope.
- ui-v2 UI-SPEC work for the report surface — out of scope per the operator's scope decision for this phase; researched as a JSON contract only.
- AI-SPEC.md generation — out of scope per the operator's scope decision; `/consult`'s contract and grounding rule are already fixed in CONTEXT.md.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SVAL-01 | Deterministic, LLM-free structural checks run over the published Computgraph via Cypher — convention compliance, orphan Patterns, Procedures without Interfaces, untyped Parameters, dangling links — each finding referencing the exact entities | See "Phase 36 Output Contract" (verified node/relationship map + per-check Cypher shape) and Pitfall 1 (convention-compliance must read `Algorithm.contextJson.warnings`, not a graph pattern) and Pitfall 2 (test substrate must use live Neo4j, not FakeGraph, for pattern-match checks) |
| SVAL-02 | Design Rules can be mapped to script-structure requirements (e.g. required Procedure/Parameter presence) and evaluated over the Computgraph, reported pass/fail per rule with supporting entities | See "Open-for-Planning Item 1" (rule-mapping file shape, mirrors `llm/cypher_catalog.json`), Pattern 2 (declarative-operation-to-Cypher-template compiler), and Pitfall 3 (keep the vocabulary structural-only, never value-threshold, to avoid re-encoding SWRL scope) |
| SVAL-03 | `POST /computgraph/consult` answers natural-language questions about a published script structure using Computgraph context through the gateway — answers grounded in graph entities, read-only | See "`/computgraph/consult` Context Assembly" (new `fetch_computgraph_subgraph()` function, in-process gateway call pattern reused from `generate_validated_cypher()`) and the Validation Architecture SC3 test row (cassette-based grounding test) |
</phase_requirements>

## Summary

Phase 37 adds a third validation surface to a project that already partitions validation between SWRL (architect-authored design compliance) and SHACL (RDF-side structural data-integrity). Its two deterministic pieces — `cg_structure_checks.py` and the rule-mapping vocabulary — operate entirely on the **Computgraph**, a Neo4j Labeled-Property-Graph (LPG) partition that Phase 36 established and that has no RDF/OWL projection today (SHACL/OWL operate on the OntoGraph/Metagraph RDF translation from Phase 821, not on Computgraph). This asymmetry — LPG-native data validated by LPG-native Cypher, versus RDF-native data validated by SHACL — is the principled resolution to the partition question the user flagged, but `spec/RULE-PARTITION-POLICY.md` currently only names two systems and does not mention Computgraph at all. This is a real, concrete gap: the plan should add a short row to the policy's decision table (or a new section) naming Computgraph structural checks as a third system with its own scope, not silently let a reviewer wonder why a third Cypher-validation path exists uncovered by the policy that CLAUDE.md says governs "which validation system owns a given rule category."

The single highest-value finding from source inspection: Phase 36's `computgraph_publish.py` writes a specific, verified node/relationship/property contract (7 labels, 9 relationship types, provenance fields) that must be the literal target of every SVAL-01 check — and one check in CONTEXT.md's list (Emg/Emr annotation-convention normalization) **cannot be detected from the published graph as literally worded**, because the raw annotation string is stripped before publish (only the parsed `ParamKind` survives on `Parameter.paramKind`). The normalization event is recoverable only via the envelope's top-level `warnings: string[]` array, which happens to survive into `Algorithm.contextJson` (a JSON string property) because the publish path strips only `untagged`, not `warnings`. The convention-compliance check must therefore be implemented as "parse `Algorithm.contextJson`, extract `warnings`" — not a pure Cypher pattern match — and the plan must say so explicitly rather than let a task silently fail against a graph that has nothing to match.

For `/computgraph/consult`, `dg_context.py`'s `assemble_context()` has no context type for definitionId-scoped Computgraph subgraphs today (only project-wide static concepts + a project-wide live OntoGraph entity fetch + project-wide ValidGraph design-state fetch). The correct move is a **new, dedicated function** (e.g. `fetch_computgraph_subgraph(project, definition_id, session)`) that mirrors the existing `fetch_existing_entities`/`fetch_existing_design_states` live-query pattern, called directly by a new route handler — not shoehorned into `CONTEXT_REQUEST_TYPES` (rule_ingest/rule_edit/graph_query), whose static per-layer concept bundling is irrelevant to a single-definition structural question. The in-process gateway call pattern is already proven by `dg_context.generate_validated_cypher()`: `resolve_active_provider() -> get_adapter() -> adapter.generate(req, api_key)`, never a re-POST to `/llm/generate`.

**Primary recommendation:** Build `cg_structure_checks.py` as pure, session-injected Cypher-plus-light-Python functions mirroring `computgraph_publish.py`'s dependency-injection style; add one new row (or subsection) to `spec/RULE-PARTITION-POLICY.md` naming Computgraph/LPG structural checks as a third, Cypher-native system explicitly out of SHACL's RDF-side scope; keep `structure_rules.json` as a first-class declarative artifact (never inline ad hoc Cypher strings) versioned alongside `llm/cypher_catalog.json`; and give `/consult` its own dedicated context-fetch function rather than extending `assemble_context()`'s three existing request types.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Deterministic structural checks (SVAL-01) | API/Backend (data-service) | Database (Neo4j Cypher) | Checks are pure Cypher pattern-matches over Computgraph plus a thin Python response-shaping layer; no browser/SSR involvement |
| Rule-mapped structural checks (SVAL-02) | API/Backend (data-service) | Database (Neo4j Cypher) | Same tier as SVAL-01; the mapping file is a backend-owned declarative artifact, not client config |
| `/computgraph/consult` (SVAL-03) | API/Backend (data-service) | — (gateway is same-tier, in-process) | Context assembly + LLM call both happen inside data-service; no new client tier introduced |
| Report surface (JSON) | API/Backend (data-service) | GH plugin (bridge print) | ui-v2 explicitly out of scope this phase; the only other consumer is the GH canvas via the existing bridge dispatcher |
| GH-panel print of report | Client (Grasshopper plugin via bridge) | API/Backend (data-service, source of the JSON) | Bridge command is a thin HTTP-or-socket forwarder, not new business logic |

**Note:** every capability in this phase is backend/database tier. There is no browser-tier or SSR-tier work; the "Claude's Discretion" GH-panel print in CONTEXT.md is a thin client consumer of an already-backend-owned report, which is consistent with the scope decision that ui-v2 is out of the UI-SPEC path.

## Partition Question (highest priority)

### 1. What does `spec/RULE-PARTITION-POLICY.md` say, and where does SVAL fall?

The policy (read in full, `spec/RULE-PARTITION-POLICY.md`) draws **one** partition line, between:
- **SWRL VALIDATOR** — architect-authored design-compliance rules (quantitative geometry/parameter constraints against BIM data), evaluated by the Grasshopper plugin against the Metagraph `Rule` corpus.
- **SHACL** — structural data-integrity of **ValidGraph/Metagraph instance data**, evaluated server-side by the `dg-reasoner` sidecar on every publish, against `ontology/dg-shapes.ttl`.

Its "test for new rule categories" (line 48) is: *"if the constraint could only be evaluated by inspecting BIM geometry, project parameters, or an architect's stated intent, it belongs to SWRL. If the constraint holds purely by inspecting the shape of the graph data... it belongs to SHACL."* [VERIFIED: spec/RULE-PARTITION-POLICY.md]

Applying that test literally to SVAL-01/02 gives an ambiguous answer: structural checks like "orphan Pattern" or "Procedure without Interface" are pure graph-shape checks (SHACL-shaped by the test), yet SVAL-02's rule-mapped checks ("a Frame algorithm must contain a Truss procedure") are explicitly **project-specific, Rule-referencing, architect-intent-adjacent** (SWRL-shaped by the test). **Neither answer is right, because the test's hidden premise is that all instance data lives in one RDF-projected graph** (ValidGraph/Metagraph). The Computgraph is a different partition entirely: a Neo4j-native LPG layer (Object/Behavior/Algorithm/Procedure/Pattern/Parameter/Interface, established Phase 36) that Phase 821/823's RDF translation and SHACL shapes **do not cover** — `ontology/dg-shapes.ttl`'s Computgraph shapes (added Phase 36-04, per `36-04-SUMMARY.md`) constrain the *shape of the published node properties themselves* (enum membership, dgId format), not script-structure semantics like "has an Interface" or "matches a Rule's structural requirement." [VERIFIED: .planning/milestones/v9.0-phases/36-computgraph-persistence-display/36-04-SUMMARY.md]

**Conclusion: Phase 37's structural-check category falls in an undefined gap.** The policy's decision table has zero rows naming Computgraph, and its "What Belongs Where" framing assumes exactly two systems. This is not a violation of the existing partition (SVAL doesn't duplicate any SWRL or SHACL rule) — it is a documentation gap: a third validation system now exists with no entry in the document that CLAUDE.md's Schema Change Propagation checklist names as authoritative for "which validation system owns a given rule category."

### 2. Cypher (per CONTEXT.md) vs. the existing SHACL layer — does this create a conflict?

No conflict with the *existing* partition, for a structural reason the external research corroborates: SHACL (via `dg-reasoner`, Owlready2/HermiT-adjacent tooling) validates the **RDF ABox** produced by Phase 821's OntoGraph/Metagraph translation — it has no path to the Computgraph LPG data at all today. Building SVAL's checks in SHACL would require first RDF-projecting the Computgraph (a new translation layer, unplanned, and contrary to `ontology/dg-shapes.ttl`'s Computgraph shapes already being scoped to node-property shape only, not cross-entity structural checks like "has at least one Interface"). Per the prefetched trade-off research: Cypher-native checks are preferable exactly when "the primary store is Neo4j/OpenCypher... constraints are pattern-heavy with arbitrary path/neighborhood conditions" [CITED: external research — Cypher-vs-SHACL trade-off]; SHACL is preferable for RDF-native, cross-tool-portable, formally-reasoned constraints. Computgraph is Neo4j-native and never touches RDF, so CONTEXT.md's Cypher decision is architecturally correct, not merely convenient.

The one discipline this research recommends borrowing from the trade-off literature: keep `structure_rules.json` (SVAL-02's rule-mapping vocabulary) a **first-class declarative artifact**, with Cypher only as its compilation target inside `cg_structure_checks.py` — mirroring the DTGraph pattern (rules compile to OpenCypher, rules are not hand-written Cypher strings scattered through the codebase) [CITED: external research — DTGraph]. This is exactly the shape CONTEXT.md already proposes (`requiresProcedure`/`requiresParameter`/`forbidsOrphan`/`requiresInterface` as declarative operation names, not raw Cypher) — the plan should preserve this discipline and resist the temptation to let a Rule's mapping entry embed a raw Cypher fragment.

### 3. Does the partition policy need an update commit? What exact wording?

**Yes.** Recommend adding a new **fourth row-class** to the existing decision table (not a new document — the existing document's structure, cross-references, and enforcement model already fit) with this exact framing:

> **New table row** (append to "What Belongs Where (Decision Table)"):
>
> | Rule Category | Example | System | Rationale |
> |---|---|---|---|
> | Script/Computgraph structural shape (LPG-native, no RDF projection) | "Every `Procedure` has at least one `Interface`"; "no orphan `Pattern`" | **Cypher (`cg_structure_checks.py`)** | Computgraph is a Neo4j LPG partition with no RDF/OWL translation (unlike ValidGraph/Metagraph); SHACL has no path to this data. Structural checks are Cypher pattern-matches over the published graph, LLM-free, analogous in spirit to SHACL's data-integrity role but scoped to a layer SHACL cannot reach. |
> | Rule-mapped script-structure requirement | "A Frame `Algorithm` must contain a *Truss* `Procedure`" | **Cypher, referencing a Metagraph `Rule` by id (`llm/structure_rules.json`)** | Architect-authored intent (like SWRL) but evaluated against Computgraph shape, not BIM geometry/parameters — SWRL's violation-inverted-body-atom machinery has no Computgraph equivalent; this is a new, narrow evaluation path that reuses `Rule_Id` as a foreign key only, never SWRL semantics |

> **New prose, appended after "Partition Line (D-12)" or as a new "§ Computgraph Structural Checks (Phase 37)" subsection:**
>
> "A third validation surface, introduced in Phase 37, evaluates the Computgraph — a Neo4j LPG partition (Object/Behavior/Algorithm/Procedure/Pattern/Parameter/Interface, Phase 36) with no RDF/OWL projection. Neither SWRL (which evaluates BIM/parameter data against the Metagraph Rule corpus) nor SHACL (which evaluates the OntoGraph/Metagraph RDF ABox, `ontology/dg-shapes.ttl`) has a path to this data. Structural and rule-mapped script-structure checks are therefore evaluated by deterministic, parameterized Cypher in `data-service/cg_structure_checks.py`, reported through their own severity taxonomy (aligned to the SHACL severity mapping below). This is not a fourth reconciliation problem: Computgraph structural checks never re-encode a SWRL or SHACL rule, and no rule exists in two of the three systems simultaneously — the same single-authoring principle (D-13) extends to this third system by construction, since its subject graph is disjoint from the other two."

**Consequence for the plan:** add a Wave-0-adjacent documentation task updating `spec/RULE-PARTITION-POLICY.md` with the above (or equivalent) wording as part of Phase 37's own schema-propagation-style deliverables — this is cheap (one doc edit) and closes a real gap a future reviewer or planner would otherwise hit blind.

## Phase 36 Output Contract (verified, from `computgraph_publish.py` + `36-01-SUMMARY.md`)

Every SVAL-01/02 check must be expressible against exactly this contract — nothing more, nothing less. [VERIFIED: data-service/computgraph_publish.py]

| Node Label | MERGE Key | Key Properties | Has `dgId`? | Provenance |
|---|---|---|---|---|
| `Object` | `cgId` ("obj:"+name), `definitionId`, `project` | `objectName`, `classIri` | Yes | `source`, `provider`/`model`/`confidence` if recognized |
| `Behavior` | `definitionId`, `project` (synthesized, no cgId) | — | No | `definitionId`, `publishedAt` only |
| `Algorithm` | `algIndex`, `definitionId`, `project` | `algorithmName`, **`contextJson`** (full confirmed envelope minus `untagged`, JSON string) | No | `definitionId`, `publishedAt` |
| `Procedure` | `cgId`, `definitionId`, `project` | `procedureName`, `procIndex` | Yes | `source`, `provider`/`model`/`confidence` |
| `Pattern` | `cgId`, `definitionId`, `project` | `patternName` | Yes | `source`, `provider`/`model`/`confidence` |
| `Parameter` | `cgId`, `definitionId`, `project` | `parameterName`, `paramKind` (Variable\|Constant\|Emergent), `dataType` (Float\|Integer\|Text\|Boolean\|Geometry), `domainMin`/`domainMax`/`domainStep` | Yes | `source`, `provider`/`model`/`confidence` |
| `Interface` | `cgId`, `definitionId`, `project` | `interfaceName`, `ifaceType` (Input\|Output) | Yes | `source`, `provider`/`model`/`confidence` |

| Relationship | From -> To | Always present? |
|---|---|---|
| `HAS_BEHAVIOR` | Object -> Behavior | always |
| `HAS_ALGORITHM` | Behavior -> Algorithm | always |
| `HAS_PROCEDURE` | Algorithm -> Procedure | always |
| `HAS_PATTERN` | Procedure -> Pattern | always |
| `PATTERN_HOST_TO` | Pattern -> Pattern | only when `hostPatternId` present |
| `HAS_PARAMETER` | Procedure -> Parameter | always |
| `HAS_INTERFACE` | Procedure -> Interface | always |
| `PARAM_LINK` | Parameter -> Interface | only when a wire connects the parameter's and interface's memberIds |
| `REFERS_TO` | Object -> Class | only when `object.classIri` is present |

Every node also carries `graph:'Computgraph'`, `project`, `definitionId`, `publishedAt` (ISO 8601 UTC). `publishedAt` is the field CONTEXT.md's staleness note refers to ("the report carries `publishedAt` so staleness is visible").

**Every check in SVAL-01, mapped to this contract:**

| SVAL-01 check (from CONTEXT.md) | Cypher shape against the verified contract |
|---|---|
| Annotation-convention compliance | **Cannot be a pure graph-pattern match** — see finding below. Must read `Algorithm.contextJson`, JSON-parse in Python, inspect the envelope's top-level `warnings: string[]` array (present per `CgContext.Warnings`, DG.Core) for Emg/Emr-normalization or other parser-emitted warning strings. |
| Orphan `Pattern` (no `HAS_PATTERN` from any Procedure) | `MATCH (pn:Pattern {project:$p, definitionId:$d}) WHERE NOT ()-[:HAS_PATTERN]->(pn) RETURN pn` |
| `Procedure` without any `Interface` | `MATCH (pr:Procedure {project:$p, definitionId:$d}) WHERE NOT (pr)-[:HAS_INTERFACE]->() RETURN pr` |
| `Parameter` without `dataType` | Currently **cannot occur** post-publish: `_build_publish_params` raises `ValueError` (422) if `dataType` is missing/unrecognized before any write happens (see `_VALID_PARAM_DATA_TYPES` check). This check is therefore effectively unreachable against data that passed publish — flag as a defensive/dead check, or repurpose to catch a null-valued property from data published before this validation existed. |
| Dangling `PARAM_LINK` (link to Interface outside the parameter's procedure chain) | `MATCH (p:Parameter)-[:PARAM_LINK]->(i:Interface) MATCH (prP:Procedure)-[:HAS_PARAMETER]->(p) MATCH (prI:Procedure)-[:HAS_INTERFACE]->(i) WHERE prP <> prI RETURN p, i` |
| `Algorithm` without `Procedure`; `Object` without `HAS_BEHAVIOR` chain | `MATCH (a:Algorithm) WHERE NOT (a)-[:HAS_PROCEDURE]->() RETURN a` / `MATCH (o:Object) WHERE NOT (o)-[:HAS_BEHAVIOR]->() RETURN o` — the latter is also effectively unreachable (`_publish_behavior` always runs whenever `object` is non-null), but is cheap defensive insurance against future refactors. |

**This is the single highest-value finding for the planner:** do not let a task silently implement "convention compliance... normalized variants like `Emr` flagged" as a naive Cypher `WHERE name CONTAINS 'Emr'` match — it will never fire, because the raw `Emr` string never reaches the published graph (only the parsed `paramKind` enum survives; the tolerated-variant normalization already happened in `CanvasAnnotationParser.cs` at parse time, before the envelope is even confirmed). [VERIFIED: DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs L46, L247-249; data-service/computgraph_publish.py L150 (`_storage_ctx` strips only `untagged`, not `warnings`); DG/src/DG.Core/Models/Computgraph/CgContext.cs L64 (`Warnings` field)]

## `/computgraph/consult` Context Assembly (SVAL-03)

`dg_context.py`'s `assemble_context()` (the one function `/context/assemble` and `/context/debug` both call, D-04 "no parallel code path") dispatches on `req.type in {"rule_ingest", "rule_edit", "graph_query"}` and raises `ValueError` on anything else, which `app.py` maps to a `CONTEXT_TYPE_INVALID` 422. [VERIFIED: data-service/dg_context.py L108, L455-470] Its assembled context bundles project-wide static concept dictionaries (Ontograph/Metagraph/Validgraph/**Computgraph catalog** — the static schema catalog from `dg_knowledge.load_computgraph_catalog()`, not live instance data) plus a live, project-wide OntoGraph entity fetch (`fetch_existing_entities`) and, for `graph_query` only, a live ValidGraph design-state fetch (`fetch_existing_design_states`). **There is no existing function that fetches a live, definitionId-scoped Computgraph subgraph** — Phase 36 only ever *writes* to Computgraph; nothing in the codebase today *reads* it back for LLM context.

**Recommendation:** do not add a fourth value to `CONTEXT_REQUEST_TYPES`. The static concept-bundling `assemble_context()` does is irrelevant to a single-definition structural question (the LLM doesn't need Ontograph/Metagraph concepts or the Cypher-shape catalog to answer "which parameters drive the truss height"). Instead:

1. Add a new function to `dg_context.py` (or a new sibling module, e.g. `cg_structure_checks.py` itself, if the planner prefers colocating with the checks) — `fetch_computgraph_subgraph(project: str, definition_id: str, session: Any = None) -> dict` — that runs one read-only Cypher query returning every Object/Behavior/Algorithm/Procedure/Pattern/Parameter/Interface node plus their relationships for that `(project, definitionId)` pair, shaped as a compact entity list (name + label + key relationships) rather than raw Neo4j records. This mirrors `fetch_existing_entities`'s "live Neo4j query with an explicit ORDER BY" determinism discipline (CTXA-05's "no embeddings, no timestamps, no set-derived collections" applies equally well here for reproducible consult answers).
2. `POST /computgraph/consult`'s route handler assembles `{subgraph, question}` into a prompt and calls the gateway **in-process**, exactly like `generate_validated_cypher()`: `resolve_active_provider(settings, master_secret) -> get_adapter(provider, base_url) -> adapter.generate(GenerateRequest(prompt=..., model=model, provider=provider), api_key)`. [VERIFIED: data-service/dg_context.py L906-915] Never re-POST to `/llm/generate`.
3. The response post-check (grounding verification) is a plain Python string-containment check: extract entity names present in the assembled subgraph, scan the LLM's answer text for each, and flag (not block) if the answer mentions no subgraph entity name at all, or if it's empty — this satisfies CONTEXT.md's "flag, don't block" constraint without building the fuller claim/evidence pipeline the external research describes (GraphEval/HalluGraph triple-decomposition) as a stricter, non-MVP guardrail. Recommended MVP response shape, adapting the external research's suggestion to this project's existing envelope conventions (`GenerateResponse`-like flat shape, not a nested claims array, matching this codebase's preference for flat, directly-serializable dicts):

```json
{
  "question": "Which parameters drive the truss height?",
  "answer": "The truss height is driven by 11_Var_HTotal (Variable, Float)...",
  "citedEntities": ["11_Var_HTotal"],
  "groundedCount": 1,
  "ungroundedMentions": [],
  "subgraphEntityCount": 42,
  "definitionId": "frame.gh",
  "publishedAt": "2026-07-08T00:00:00Z"
}
```

## Open-for-Planning Items — Concrete Recommendations

### 1. Rule-mapping file location and shape

**Recommendation: `llm/structure_rules.json`, file-first, matching `llm/cypher_catalog.json`'s exact conventions.** `cypher_catalog.json` is `{"version": <int>, "shapes": [{"id", "name", "description", ...}]}`, loaded defensively by `dg_context.load_cypher_catalog()` — never raises on a missing/malformed file, falls back to an empty catalog, and exposes a derived module-level id-index (`CYPHER_SHAPE_IDS`) computed once at import time. [VERIFIED: data-service/dg_context.py L57-103] Mirror this exactly for `structure_rules.json`: `{"version": 1, "mappings": [{"ruleId": "R_...", "operation": "requiresProcedure"|"requiresParameter"|"forbidsOrphan"|"requiresInterface", "params": {...}}]}`, a defensive `load_structure_rules()` in `cg_structure_checks.py` (or a new small module) that never raises, and a `Path` resolution using the same `DG_KNOWLEDGE_REPO_ROOT`/`/mnt/repo` Docker-mount pattern `CYPHER_CATALOG_FILE` already uses. This keeps the rule-mapping artifact discoverable exactly where an architect or future contributor would already look (next to `cypher_catalog.json`), and reuses a battle-tested defensive-load pattern rather than inventing a new one.

### 2. Severity taxonomy alignment

**Recommendation: reuse the SHACL severity mapping verbatim: `{violation, warning, info}` (Solibri-style), documented in `spec/RULE-PARTITION-POLICY.md`'s "How SHACL Findings Surface" section.** [VERIFIED: spec/RULE-PARTITION-POLICY.md L83-89] That table maps `sh:Violation -> violation (red)`, `sh:Warning -> warning (orange)`, `sh:Info -> info (yellow)`. CONTEXT.md's own check list already uses this vocabulary informally ("normalized variants... flagged info-level"), so this is not a new decision so much as making an implicit choice explicit. Concretely:

| SVAL Severity | When used |
|---|---|
| `violation` | Orphan Pattern, Procedure without Interface, dangling PARAM_LINK, Algorithm without Procedure — structural breakage that would make the script uninterpretable by v10 tooling |
| `warning` | Rule-mapped structural requirement fails (SVAL-02) — a design intent isn't met, but the graph itself is well-formed |
| `info` | Annotation-convention normalization (Emg/Emr, or any other tolerated-variant warning surfaced from `Algorithm.contextJson.warnings`) — cosmetic/informational, not a structural defect |

Also reuse the same message discipline this project applies everywhere else: `ErrorMessageTemplates.cs`'s What+Where+How-to-fix pattern (already the house style for `dg_context.py`'s `validate_cypher()` violations, e.g. `"Label 'X' is not one of the allowed schema labels (...). Where: node label 'X'. How to fix: ..."` [VERIFIED: data-service/dg_context.py L692-700]). Each SVAL finding's `message` field should follow the identical three-part structure, not a bare string.

### 3. Persist vs. ephemeral structure-validation results

**Recommendation: ephemeral for MVP, confirming CONTEXT.md's lean.** The existing `ValidationRun`/`Run` persistence machinery (`store_validation_run`, `shaclReportJson` on the same node) is purpose-built for the SWRL/geometry validation pipeline keyed on Speckle model/version ids — retrofitting it to also carry Computgraph structural-check results would conflate two different subjects (a BIM design-state run vs. a script-structure snapshot) on one node type, exactly the kind of dual-authoring the partition policy's single-authoring principle warns against by analogy. Since checks are deterministic and re-run on demand (CONTEXT.md's own determinism verification sketch depends on this), persistence adds no correctness value at MVP scope — it only matters once v10 workflows need history/trend data, which CONTEXT.md already defers. If a lightweight persisted record becomes necessary later, model it as its own node type (e.g. `StructureValidationRun`, its own `graph:'Computgraph'`-adjacent label) rather than overloading `Run`.

## Report Surface (JSON contract + GH-panel print)

Per the scope decision, this is researched as a JSON contract, not a ui-v2 component. Recommended shape for `POST /computgraph/validate`:

```json
{
  "project": "p1",
  "definitionId": "frame.gh",
  "publishedAt": "2026-07-08T00:00:00Z",
  "checkedAt": "2026-07-27T12:00:00Z",
  "findings": [
    {
      "checkId": "procedure_without_interface",
      "severity": "violation",
      "message": "Procedure '11_Proc' has no Interface. Where: Procedure cgId=cg:1:proc:11_Proc. How to fix: tag at least one IntF_ group under this Procedure and re-publish.",
      "entities": [{"label": "Procedure", "cgId": "cg:1:proc:11_Proc", "name": "11_Proc"}]
    }
  ],
  "ruleResults": [
    {"ruleId": "R_STRUCT_FRAME_TRUSS", "passed": false, "satisfyingEntities": [], "offendingEntities": [{"label": "Algorithm", "algIndex": 1}]}
  ]
}
```

This is directly consumable by ui-v2 in a future phase (not this one) and by a GH-panel print via the bridge. For the bridge: `gh_bridge.py`'s existing command set (`get_canvas_context`, `get_selection`, `preview_structure`, `clear_preview`, `get_preview_status`) is dispatched through `CanvasCommandDispatcher`'s injected handler dictionary — **no reflection, a deliberate code change is required to add a new command** (Phase 33 decision). [VERIFIED: data-service/gh_bridge.py; .planning/STATE.md L266] The lowest-cost MVP option is a new bridge command (e.g. `get_structure_validation_report`) that the GH-side dispatcher forwards as a plain synchronous HTTP GET to data-service's `/computgraph/validate` and renders in a passive panel — matching CONTEXT.md's "lowest-cost option wins" instruction. This is a small, additive dispatcher entry, not a new subsystem.

## Standard Stack

### Core

No new external packages are required. [VERIFIED: data-service/requirements.txt — cryptography, fastapi, httpx, neo4j, pydantic>=2.7,<3, pytest, specklepy==3.2.4, uvicorn already present and sufficient for Cypher execution, FastAPI routing, Pydantic request/response models, and the existing in-process LLM gateway call]

| Library | Version | Purpose | Why Standard |
|---|---|---|---|
| `neo4j` (Python driver) | already pinned | Cypher execution for `cg_structure_checks.py` | Same driver every other data-service module uses; no new dependency |
| `fastapi` / `pydantic` | already pinned | `POST /computgraph/validate` and `POST /computgraph/consult` route + request models | Established pattern (`ComputgraphPublishRequest`, `ContextAssembleRequest`) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| Cypher-native checks | SHACL shapes over an RDF-projected Computgraph | Requires building a new Computgraph->RDF translation layer (unplanned, no Phase covers it); loses direct access to Neo4j's own indexes/optimizer for path-heavy structural checks; rejected per the partition-question analysis above |
| Hand-rolled entity-grounding NLP library | GraphEval/HalluGraph-style triple decomposition | Overkill for a "flag, don't block" MVP; a plain entity-name string-containment check against the assembled subgraph is sufficient and matches CONTEXT.md's explicit MVP framing |

**Installation:** none — no new packages.

## Package Legitimacy Audit

Not applicable — Phase 37 introduces zero new external packages. All required functionality (Cypher execution, FastAPI routing, in-process LLM gateway calls) is served by dependencies already present in `data-service/requirements.txt`.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Architect (GH canvas, re-published)                  ui-v2 / GH panel (future consumer)
        |                                                      ^
        v                                                      |
POST /computgraph/publish (Phase 36, unchanged)                |
        |                                                      |
        v                                                      |
   Neo4j Computgraph                                            |
   (Object/Behavior/Algorithm/Procedure/Pattern/Parameter/Interface)
        |                                                      |
        |-- read-only Cypher --------------------------------->|
        v                                                      |
cg_structure_checks.py                                          |
   - deterministic checks (SVAL-01)  ---> findings[] -----------|
   - rule-mapped checks (SVAL-02, reads llm/structure_rules.json,
     joins Metagraph Rule by Rule_Id) ---> ruleResults[] --------|
        |
        v
POST /computgraph/validate  (thin FastAPI route, assembles report JSON)


Architect / GH panel question
        |
        v
POST /computgraph/consult
        |
        v
fetch_computgraph_subgraph(project, definitionId)  [NEW function, dg_context.py-adjacent]
        |
        v
resolve_active_provider() -> get_adapter() -> adapter.generate()   [llm_gateway.py, in-process, existing pattern]
        |
        v
grounding post-check (entity-name string match against subgraph)  [flag, don't block]
        |
        v
{answer, citedEntities, ungroundedMentions, ...}
```

### Recommended Project Structure

```
data-service/
├── cg_structure_checks.py     # NEW: deterministic checks (SVAL-01) + rule-mapped checks (SVAL-02)
├── dg_context.py              # MODIFIED: add fetch_computgraph_subgraph() (SVAL-03 context assembly)
├── app.py                     # MODIFIED: POST /computgraph/validate, POST /computgraph/consult routes
├── tests/
│   └── test_cg_structure_checks.py   # NEW: mirrors test_computgraph_publish.py's FixtureSession
llm/
└── structure_rules.json       # NEW: rule-mapping vocabulary, versioned alongside cypher_catalog.json
spec/
└── RULE-PARTITION-POLICY.md   # MODIFIED: new decision-table rows + Computgraph subsection
```

### Pattern 1: Session-injected, pure Cypher check functions

**What:** Every check function accepts `session: Any` and `project`/`definition_id` params (no lazy-connect default), matching `computgraph_publish.py`'s "caller owns the session" discipline and Phase 821's `reasoning.py` "functions accept an injectable session param... tests bypass live Neo4j entirely" precedent.
**When to use:** Every function in `cg_structure_checks.py`.
**Example:**
```python
# Pattern mirrors computgraph_publish.py (Phase 36) and reasoning.py (Phase 821)
def check_orphan_patterns(session: Any, project: str, definition_id: str) -> list[dict]:
    result = session.run(
        """
        MATCH (pn:Pattern {project: $project, definitionId: $definitionId})
        WHERE NOT ()-[:HAS_PATTERN]->(pn)
        RETURN pn.cgId AS cgId, pn.patternName AS name
        // op=CHECK_ORPHAN_PATTERN
        """,
        {"project": project, "definitionId": definition_id},
    )
    return [
        {
            "checkId": "orphan_pattern",
            "severity": "violation",
            "message": (
                f"Pattern '{row['name']}' has no owning Procedure. "
                f"Where: Pattern cgId={row['cgId']}. "
                "How to fix: re-tag this Pattern under a Procedure group and re-publish."
            ),
            "entities": [{"label": "Pattern", "cgId": row["cgId"], "name": row["name"]}],
        }
        for row in result
    ]
```

### Pattern 2: Declarative rule-mapping compiled to parameterized Cypher

**What:** `structure_rules.json` entries name an `operation` (`requiresProcedure`, `requiresParameter`, `forbidsOrphan`, `requiresInterface`); `cg_structure_checks.py` owns one Cypher template per operation, parameterized by the mapping entry's `params`.
**When to use:** SVAL-02 rule evaluation only — never let a mapping entry embed raw Cypher (defeats the declarative-artifact discipline the DTGraph precedent recommends).
**Example:**
```python
# structure_rules.json entry:
# {"ruleId": "R_STRUCT_FRAME_TRUSS", "operation": "requiresProcedure", "params": {"namePattern": "*Truss*"}}

_OPERATION_TEMPLATES = {
    "requiresProcedure": """
        MATCH (a:Algorithm {project: $project, definitionId: $definitionId})
        OPTIONAL MATCH (a)-[:HAS_PROCEDURE]->(pr:Procedure)
          WHERE pr.procedureName CONTAINS $namePattern
        RETURN a.algIndex AS algIndex, collect(pr.cgId) AS matchingProcedureCgIds
        // op=RULE_REQUIRES_PROCEDURE
    """,
    # ... requiresParameter, forbidsOrphan, requiresInterface
}
```

### Anti-Patterns to Avoid

- **Detecting Emg/Emr normalization via a live Cypher string match on `Parameter.parameterName` or `paramKind`:** the raw tag string never reaches the published graph — this check will silently never fire. Read `Algorithm.contextJson.warnings` instead (see Phase 36 Output Contract section).
- **Adding a fourth value to `CONTEXT_REQUEST_TYPES` for consult:** conflates a definitionId-scoped instance-data question with `assemble_context()`'s project-wide static-concept bundling; write a dedicated function instead.
- **Embedding raw Cypher inside `structure_rules.json` mapping entries:** defeats the declarative-artifact-as-compilation-source discipline; keep operations as named, parameterized templates in Python.
- **Persisting structure-validation results onto the existing `ValidationRun`/`Run` node:** conflates two different validation subjects on one node type; stay ephemeral per CONTEXT.md's lean, or use a distinct node type later.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Bracket/verb/label validation for any Cypher this phase emits dynamically (rule-mapped templates are static per-operation, but if a future extension lets `structure_rules.json` params influence raw Cypher text) | A second ad hoc Cypher sanity-checker | `dg_context.has_valid_nesting()` / the `validate_cypher()` allow-list pattern | Already battle-tested against live LLM output noise (per its own docstring); reuse rather than re-derive |
| Provider resolution / adapter dispatch for `/consult` | A new provider-selection helper | `llm_gateway.resolve_active_provider()` + `get_adapter()` | Single source of truth for provider/model/key resolution across the whole gateway; duplicating it risks drift from settings changes |
| Entity-grounding verification for `/consult` | A full claim/triple-decomposition pipeline (GraphEval/HalluGraph-style) | A flat entity-name string-containment check against the assembled subgraph | CONTEXT.md's MVP scope is "flag, don't block" on a citation miss; the stricter literature pattern is explicitly a v10+ option, not an MVP requirement |

**Key insight:** every non-trivial validation/parsing primitive this phase needs (Cypher safety, LLM provider dispatch, structured-error shaping) already exists in this codebase from Phases 29/35/36 — the only genuinely new code is the check logic itself and the rule-mapping compiler.

## Runtime State Inventory

Not applicable — Phase 37 is a greenfield addition (new endpoints, new module, new JSON artifact). It does not rename, refactor, or migrate any existing entity, key, or identifier. No stored data, live service config, OS-registered state, secrets, or build artifacts need auditing.

## Common Pitfalls

### Pitfall 1: Treating "convention compliance" as detectable purely via live Cypher

**What goes wrong:** A check is written expecting to find raw `Emr`/`Emg` tag strings on published `Parameter` nodes; it never fires against any real data.
**Why it happens:** The annotation grammar and its Emg/Emr tolerance live in `CanvasAnnotationParser.cs` (C#, pre-publish); normalization is already resolved into `ParamKind` before the envelope is even confirmed on-canvas. Only the top-level `warnings` array (preserved inside `Algorithm.contextJson`) records that a normalization happened.
**How to avoid:** Implement this one check as "fetch `Algorithm.contextJson` via Cypher, JSON-parse in Python, scan `warnings`" rather than a graph pattern match.
**Warning signs:** A pytest fixture that publishes a Frame envelope with an `Emr`-tagged parameter and asserts the check fires — if it fires on a naive Cypher-only implementation, the fixture itself is wrong (it's probably injecting the raw tag into a field that wouldn't survive real publish).

### Pitfall 2: FakeGraph duck-typing can't validate arbitrary Cypher pattern-matches

**What goes wrong:** `test_computgraph_publish.py`'s `FakeGraph`/`FixtureSession` harness dispatches on a fixed `// op=PUBLISH_*` tag per Cypher literal and executes a hand-written Python method per op — it is not a real Cypher engine. SVAL-01/02 checks are read-heavy pattern-matches (`WHERE NOT (...)->()`, multi-hop joins) whose correctness cannot be proven by a duck-typed dict store without reimplementing a mini Cypher interpreter (which would itself need testing, and would diverge from real Neo4j semantics over time).
**Why it happens:** The existing precedent (`FakeGraph`) was built for MERGE-based writes, where a fixed op-tag-to-python-function mapping is a faithful simulation. Checks are fundamentally different: arbitrary read-side graph traversal.
**How to avoid:** Run `cg_structure_checks.py`'s integration tests against real Neo4j inside the docker-compose network (the same constraint `test_dg_context.py`'s 4 Neo4j-dependent tests already document: `neo4j` as a hostname only resolves inside compose, not from the host). Reserve FakeGraph-style doubles only for route-shape/response-shape tests (does the endpoint return the right JSON structure given a canned check-function result), not for proving the Cypher itself is correct.
**Warning signs:** A Wave 0 test suite that "passes" using only FakeGraph but has never been run once against a live Neo4j instance with the Frame fixture actually published.

### Pitfall 3: Rule-mapped checks quietly duplicating SWRL semantics

**What goes wrong:** A future `structure_rules.json` entry starts encoding numeric comparisons (e.g. "height parameter must exceed 10") that really belong to SWRL's violation-inverted business-rule domain, not a structural-shape check.
**Why it happens:** SVAL-02's `requiresParameter` operation checks *existence and kind/dataType*, which is legitimately structural; it's an easy slide from there to also checking *values*, which crosses back into SWRL's domain (per the partition policy's own test: "does this constraint express a real-world design requirement... or a structural precondition").
**How to avoid:** Keep `structure_rules.json`'s vocabulary strictly to presence/kind/type/relationship checks (existence, dataType match, orphan/interface presence) — never a value-threshold comparison. If a future need arises for value-threshold checks over Computgraph data, that is new SWRL scope (evaluated by the Grasshopper plugin against BIM/parameter values), not an SVAL structural check.
**Warning signs:** A mapping entry's `params` includes a numeric `min`/`max`/comparison operator rather than a name pattern or kind/type enum.

### Pitfall 4: `/consult` context assembly silently omitting stale-data warning

**What goes wrong:** A consult answer is generated from a Computgraph subgraph that is stale relative to the live canvas (architect made changes, hasn't re-published), and the response gives no signal of this.
**Why it happens:** CONTEXT.md explicitly delegates canvas freshness to the architect ("canvas freshness is the architect's responsibility... the report carries `publishedAt` so staleness is visible") — but this only works if `/consult`'s response actually surfaces `publishedAt` prominently, the same as `/computgraph/validate`'s report.
**How to avoid:** Include `publishedAt` (from the Computgraph nodes just fetched) in every `/consult` response, not only in `/validate`'s report.
**Warning signs:** A UAT/manual test where the architect edits the canvas, doesn't re-publish, asks a question, and gets an answer with no visible timestamp to contradict it.

## Code Examples

### In-process gateway call (existing precedent, reused verbatim in shape)

```python
# Source: data-service/dg_context.py generate_validated_cypher() (L880-922), the established
# in-process call sequence -- never re-POST to /llm/generate.
master_secret = os.getenv("LLM_MASTER_SECRET", "")
settings = load_persisted_llm_settings()
provider, model, api_key = resolve_active_provider(settings, master_secret)
adapter = get_adapter(provider, settings.get("baseUrl"))

req = GenerateRequest(prompt=consult_prompt, model=model, provider=provider)
response = adapter.generate(req, api_key)
```

### Defensive catalog loader (pattern to replicate for `structure_rules.json`)

```python
# Source: data-service/dg_context.py load_cypher_catalog() (L75-91) -- exact pattern to mirror
def load_structure_rules() -> dict[str, Any]:
    if not STRUCTURE_RULES_FILE.exists():
        return {"version": 0, "mappings": []}
    try:
        payload = json.loads(STRUCTURE_RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 0, "mappings": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("mappings"), list):
        return {"version": 0, "mappings": []}
    return payload
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Two validation systems (SWRL, SHACL), one partition line | Three validation systems (+ Computgraph structural Cypher checks) | Phase 37 (this phase) | `spec/RULE-PARTITION-POLICY.md` needs an explicit update, not a silent third system |
| No live read-path for Computgraph | First live Computgraph read (`fetch_computgraph_subgraph`, new this phase) | Phase 37 | Phase 36 was write-only; Phase 37 is the first consumer that reads Computgraph back for LLM/consult purposes |

**Deprecated/outdated:** none — this phase introduces new surfaces, it does not replace anything.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | The recommended severity taxonomy (`violation`/`warning`/`info` mapped per check type) is the right assignment per check — this is a design recommendation, not something verified against a spec that dictates it | Severity taxonomy alignment | If the user prefers a different mapping (e.g. all SVAL-01 structural breaks as `warning` not `violation`), the plan's severity constants need a one-line change; low risk, easily corrected in review |
| A2 | The suggested `structure_rules.json` file shape (`{"version", "mappings": [{"ruleId","operation","params"}]}`) is a recommendation extrapolated from `cypher_catalog.json`'s conventions, not a pre-existing schema found in the codebase | Rule-mapping file location and shape | Low risk — this is explicitly CONTEXT.md's "Open for planning" item; the plan is free to adjust field names as long as it stays declarative and file-based per the locked decision |
| A3 | The recommended `/consult` response shape (`answer`, `citedEntities`, `ungroundedMentions`, etc.) is adapted from the prefetched external research, not a pattern already present in this codebase | `/computgraph/consult` Context Assembly | Low risk — CONTEXT.md only fixes the grounding rule (flag, don't block) and the general contract (question+context->gateway->answer), not the exact JSON field names |

## Open Questions

1. **Exact wording/placement of the `spec/RULE-PARTITION-POLICY.md` update**
   - What we know: the policy needs a new decision-table row (or rows) plus a short Computgraph-scoped subsection; a draft is provided above.
   - What's unclear: whether the user wants this as a full-fledged new "§ Partition Line (D-XX)" subsection with its own decision letter (matching the document's `D-11/D-12/D-13/D-14` numbering convention tied to Phase 823's CONTEXT.md decisions) or a lighter addendum note, since Phase 37 has no equivalent numbered-decision CONTEXT.md entry for this specific point.
   - Recommendation: treat as a Wave-0/early-task documentation deliverable in the plan, phrased as an addendum (no new `D-` numbering, since no Phase 37 CONTEXT.md decision letter maps to it) — cheaper and avoids implying a formal governance decision was made that wasn't.

2. **Whether `Parameter without dataType` and `Object without HAS_BEHAVIOR` checks are worth keeping given they're currently unreachable**
   - What we know: both conditions are pre-empted by `_build_publish_params`'s `ValueError` validation (422 on publish) — a Parameter without a recognized dataType, or an Object whose Behavior synthesis is skipped, cannot exist in the published graph today.
   - What's unclear: whether the plan should implement these two checks anyway (defensive, catches a future refactor regression or a graph mutated outside the publish path) or drop them from SVAL-01's initial scope and note the gap.
   - Recommendation: implement them as cheap defensive checks (a few lines of Cypher each) — the cost is trivial and the CONTEXT.md verification sketch doesn't test them directly, so they carry no test-writing burden beyond a basic "returns empty on well-formed Frame" assertion.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Neo4j | Cypher structural checks, live Computgraph reads | Confirmed running per docker-compose (`neo4j:7474/7687`) | Neo4j 5 (project standard) | — |
| data-service container | New routes, module | Existing service, rebuild required after code changes | — | `docker compose build --no-cache data-service && docker compose up -d data-service` |
| LLM provider (Anthropic/OpenAI/Ollama) | `/computgraph/consult` | Depends on operator's configured `LLMSettings` at runtime | — | Ollama is the zero-config fallback per existing gateway design; `/consult` degrades the same way `/llm/generate` already does if no provider configured |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** LLM provider for `/consult` — falls back to whatever the gateway's existing resolution order already provides (Ollama default).

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (already the project standard for data-service) |
| Config file | none dedicated — data-service tests run via `python -m pytest data-service/tests/ -q` per existing precedent (`36-01-SUMMARY.md`) |
| Quick run command | `python -m pytest data-service/tests/test_cg_structure_checks.py -q` |
| Full suite command | `python -m pytest data-service/tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| SVAL-01 | Orphan Pattern / Procedure-without-Interface / dangling PARAM_LINK / Algorithm-without-Procedure detected with exact entity references | integration (live Neo4j, docker-compose network) | `docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -k structural -q` | ❌ Wave 0 |
| SVAL-01 | Convention-compliance (Emg/Emr normalization) surfaced from `Algorithm.contextJson.warnings` | unit (pure Python, no Neo4j — pass a synthetic contextJson string) | `python -m pytest data-service/tests/test_cg_structure_checks.py -k convention -q` | ❌ Wave 0 |
| SVAL-02 | Rule-mapped check passes on full Frame, fails on a copy missing `12_Proc` | integration (live Neo4j; requires publishing two Frame variants) | `docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -k rule_mapped -q` | ❌ Wave 0 |
| SVAL-03 | `/consult` answer cites `11_Var_HTotal`, grounded (not hallucinated) | integration with a mocked/cassette LLM adapter (mirrors `_FakeAdapterForRetry`/cassette.py precedent) — deterministic response fixture, not a live LLM call in CI | `python -m pytest data-service/tests/test_dg_context.py -k consult -q` (or a new `test_computgraph_consult.py`) | ❌ Wave 0 |
| SVAL-01/02 determinism | Identical repeated `/computgraph/validate` calls produce byte-identical findings | unit/integration, run twice, assert equality | included in the structural-check integration test | ❌ Wave 0 |
| SC1 (Interface removal -> flagged) | Manual/live-Rhino re-publish step | **human-verify** (requires an actual GH canvas edit + re-publish through the plugin) | checkpoint:human-verify | — |
| SC2 (rule mapped to *Footer* passes/fails on two published copies) | Automatable via two synthetic `_frame_cg_context()`-style envelopes (one with `12_Proc`, one without), both published into the same test Neo4j, then rule-evaluated | automated | included in rule_mapped integration test | ❌ Wave 0 |
| SC3 (`/consult` cites `11_Var_HTotal`) | Automatable with a cassette/fixture LLM response (mirrors `data-service/tests/recognition_eval/cassette.py`) | automated | included in consult integration test | ❌ Wave 0 |
| SC4 (validate-path is LLM-free, `/consult` is the only gateway caller) | Static/code-review check: grep `cg_structure_checks.py` for any `llm_gateway`/`adapter.generate` import | automated (grep-based gate, mirrors `36-01-SUMMARY.md`'s `grep -c` gate-check style) | `grep -c "llm_gateway\|adapter.generate" data-service/cg_structure_checks.py` (expect 0) | — |

### Sampling Rate

- **Per task commit:** the quick unit-level command (convention-compliance test, no Neo4j needed)
- **Per wave merge:** the full integration suite inside the compose network (`docker compose exec data-service python -m pytest tests/ -q`)
- **Phase gate:** full suite green + the SC1 human-verify checkpoint explicitly logged (cannot be automated — requires a live Grasshopper canvas edit and re-publish through the real plugin) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `data-service/tests/test_cg_structure_checks.py` — covers SVAL-01/SVAL-02, needs both a FakeGraph-style route-shape test tier AND a live-Neo4j integration tier (see Pitfall 2 — FakeGraph cannot substitute for real Cypher pattern-match correctness)
- [ ] A second published Frame variant fixture (Interface removed from `11_Proc`, or `12_Proc` group entirely absent) for SC1/SC2 — can reuse `test_computgraph_publish.py`'s `_frame_cg_context()` builder function as a base, with the relevant entity stripped/mutated before calling `publish_structure()`
- [ ] A cassette/fixture LLM response for `/consult` testing (mirrors `data-service/tests/recognition_eval/cassette.py`'s record/replay pattern) so SC3 is testable without a live LLM call in CI
- [ ] Confirm whether `data-service/tests/` currently run inside the compose network in CI/local dev, or only ad hoc via `docker compose exec` — if there is no standing CI job that runs data-service tests against live Neo4j, this phase's integration tests may need a documented manual/local run step, same as the existing `test_dg_context.py`'s 4 Neo4j-dependent tests today

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | No | Single-team self-hosted deployment; no new auth surface introduced (matches existing project-wide decision) |
| V3 Session Management | No | Stateless HTTP endpoints, no session state introduced |
| V4 Access Control | No | Project isolation via the `project` property (existing pattern), not a new access-control model |
| V5 Input Validation | Yes | Pydantic request models for `/computgraph/validate` (`{project, definitionId?}`) and `/computgraph/consult` (`{project, definitionId, question}`), matching `ComputgraphPublishRequest`'s existing precedent |
| V6 Cryptography | No | No new secrets/crypto surface; reuses the existing encrypted-at-rest LLM API key handling unchanged |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Cypher injection via `project`/`definitionId`/`question` params | Tampering | Parameterized `tx.run()`/`session.run()` calls only — never f-string/`.format()`/`%` interpolation into Cypher text, exactly as `computgraph_publish.py` already enforces (T-36-01 precedent) |
| Prompt injection via `question` attempting to make the LLM assert facts not in the subgraph, or attempting to leak system-prompt content | Spoofing/Tampering | The read-only grounding post-check (entity-name match against the assembled subgraph) is the primary mitigation; `/consult` never executes any Cypher derived from the LLM's output (unlike `generate_validated_cypher()`'s path, this endpoint has no write/generate-then-execute step at all — it is strictly read subgraph -> prompt -> text answer) |
| Cross-project data leakage (a `/consult` question for project A accidentally answered using project B's Computgraph) | Information Disclosure | `fetch_computgraph_subgraph` must scope every Cypher `MATCH` by both `project` AND `definitionId` in the `WHERE`/pattern-property clause, mirroring every existing Computgraph query's `{project: $project, definitionId: $definitionId}` property-match discipline |

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `data-service/computgraph_publish.py` — full Phase 36 write contract (node labels, MERGE keys, relationships, provenance)
- `data-service/dg_context.py` — `assemble_context()`, `CONTEXT_REQUEST_TYPES`, `validate_cypher()`, `generate_validated_cypher()`, cypher-catalog loader pattern
- `data-service/llm_gateway.py` — `GenerationOptions`, adapter dispatch, `resolve_active_provider()`/`get_adapter()`
- `data-service/gh_bridge.py` — bridge command set and dispatcher precedent
- `data-service/tests/test_computgraph_publish.py` — `FakeGraph`/`FixtureSession` harness, `_frame_cg_context()` fixture builder
- `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs`, `DG/src/DG.Core/Models/Computgraph/CgContext.cs`, `CgParameter.cs`, `CgNode.cs` — annotation-convention normalization boundary
- `spec/RULE-PARTITION-POLICY.md` — full partition contract read in entirety
- `.planning/REQUIREMENTS.md`, `.planning/milestones/v9.0-phases/37-script-structure-validation/37-CONTEXT.md`, `.planning/milestones/v9.0-phases/36-computgraph-persistence-display/36-01-SUMMARY.md`, `36-04-SUMMARY.md`
- `llm/cypher_catalog.json` — versioned-artifact convention to mirror for `structure_rules.json`

### Secondary (MEDIUM confidence — prefetched external research, cited by the orchestrator)
- ProGS (Property Graph Shapes Language) — https://eprints.soton.ac.uk/450455/1/crc_Query_Validation_ISWC_2021_submission_5_.pdf
- DTGraph (declarative rules compiling to OpenCypher) — https://github.com/yannramusat/DTGraph
- Neo4j Cypher-DSL — https://neo4j.github.io/cypher-dsl/
- W3C SHACL spec — https://www.w3.org/TR/shacl/
- GraphEval — https://arxiv.org/abs/2407.10793
- HalluGraph — https://vcnoel.github.io/hallugraph-demo/
- Detecting Hallucinations in Graph RAG — https://arxiv.org/html/2512.09148v1

### Tertiary (LOW confidence)
- None used as authoritative — all recommendations above are either grounded in direct codebase inspection or the orchestrator-provided external research digest.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, fully verified against `requirements.txt` and existing module imports
- Architecture: HIGH — every pattern recommendation is a direct mirror of an already-shipped Phase 29/35/36/821 precedent, verified by reading the actual source
- Partition-policy resolution: MEDIUM — the *analysis* (Computgraph is LPG-native, SHACL/OWL has no path to it) is directly verified from the policy document and `computgraph_publish.py`; the *exact wording* of the recommended policy update is this research's own drafting, not a pre-existing verified text
- Pitfalls: HIGH — the two highest-value pitfalls (Emg/Emr non-detectability, FakeGraph's read-query limitation) are both traced to specific verified line numbers in the C#/Python source, not inferred

**Research date:** 2026-07-27
**Valid until:** 30 days (stable internal codebase contract; re-verify if Phase 36 code changes before Phase 37 planning executes)
