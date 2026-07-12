# Phase 823: SHACL Validation Layer - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning
**Mode:** Autonomous smart discuss — recommended decisions taken (user pre-authorized)

<domain>
## Phase Boundary

Phase 823 turns the Phase 821 pySHACL placeholder into a real SHACL validation layer that runs on **every validation run**: when the Grasshopper VALIDATOR publishes a run through `POST /validation/publish`, data-service also asks the `dg-reasoner` sidecar to validate that run's DesignState/Rule instance data (translated to RDF as a ValidGraph ABox per `spec/LPG-OWL-MAPPING.md`) against real, version-controlled SHACL shapes. SHACL runs **alongside — never replacing —** the SWRL-based VALIDATOR, under a documented rule-partition/precedence policy. Violations surface as What+Where+How-to-fix messages (via DG's existing `ErrorMessageTemplates` on the Grasshopper side) with info/warning/violation severity rendered Solibri-style (red/orange/yellow) in the V2 UI's Model screen.

**Not in this phase:** re-encoding any architect-authored business/design-compliance rule as SHACL (partition policy forbids it); OWL consistency UX (Phase 822); LLM-ingestion axiom emission (deferred out of v8.2 per ADR-820-1); async job pattern; SHACL shape authoring UI; persisting SHACL history beyond the per-run report.

</domain>

<decisions>
## Implementation Decisions

### SHACL Trigger & Data Flow
- **D-01:** SHACL runs **server-side on each validation run**: `POST /validation/publish` (data-service, app.py ~L1241) calls the sidecar's `POST /shacl/validate` **synchronously after `store_validation_run`**, with an explicit short httpx timeout (mirror the existing `/reasoner/consistency` proxy pattern, app.py ~L1173). No queue, no background jobs — repo-wide sync-HTTP Key Decision.
- **D-02:** **SHACL is non-fatal to publish.** If the sidecar is unreachable, times out, or errors, the publish response and stored run carry `shacl: {status: "unavailable"|"timeout", ...}` and the publish still returns 200 with its normal payload. A SHACL failure must never block or fail the Speckle-publish hot path.
- **D-03:** `POST /shacl/validate` request gains an optional `run_id` alongside `project`: `{project, run_id?}`. With `run_id`, the sidecar validates that run's ValidGraph ABox (see D-04) unioned with the project's existing OntoGraph/Metagraph export (Rule instance data). Without `run_id`, it validates the project-level export as today (backward compatible with the 821 contract).
- **D-04:** Phase 823 builds the **ValidGraph→RDF ABox export** in dg-reasoner per the informative sketch in `spec/LPG-OWL-MAPPING.md` §"ValidGraph to RDF Sketch": DesignState kinds → `dgv:ObjState/ParamState/PropState` individuals, Run → `dgv:Run` with `ValidStatus`/`SendStatus`, `HAS_STATE` composition → `dgv:hasState`. **Primary data source is the `statePayloadJson` v2 envelope stored on the `ValidationRun` node** (data-service's live write path stores the state as JSON on the run, not as separate DesignState nodes) — the exporter parses the envelope and mints individuals; if live `DesignState` nodes exist for the project (label-scoped read, per the export-scoping mandate), include them too. Promote the sketch's normative details as needed and update the spec's status note.
- **D-05:** The ABox export **implements `owl:AllDifferent` (UNA)** over all minted named individuals in the export batch — the obligation Phase 821 explicitly deferred to this phase (821 decision log + LPG-OWL-MAPPING UNA section).
- **D-06:** SHACL report is **stored as `shaclReportJson` on the `ValidationRun` node** (same pattern as `rulesJson`/`statePayloadJson`) and **returned in the publish response** so the Grasshopper VALIDATOR can surface it immediately.

### Shapes Authoring & Severity
- **D-07:** Shapes live in **`ontology/dg-shapes.ttl`**, version-controlled, loaded by the sidecar from the existing read-only `./ontology` volume mount (exact 821 D-04/D-07 overlay pattern — edit + restart, no image rebuild). The 821 "empty placeholder shapes graph" in `run_shacl()` is replaced by loading this file.
- **D-08:** Shape scope for 823 = **data-integrity shapes for v4 instance data**, e.g.: DesignState `kind` ∈ {ObjState, ParamState, PropState}; PropState composition completeness (Rule + DataProperty + PropValue); Run has `ValidStatus` boolean list + `SendStatus`; Rule structural integrity (Rule_Id present/format, has SWRL, body atom order contiguous); Atom `REFERS_TO` target resolvable; Var `name` non-empty. Exact shape list is planner/researcher discretion — but **no architect-authored business rule may be re-encoded as a shape** (partition policy).
- **D-09:** Severity uses the standard SHACL vocabulary mapped once: `sh:Violation` → `violation` (red), `sh:Warning` → `warning` (orange), `sh:Info` → `info` (yellow) — Solibri-style. Severity is set per shape by design intent: integrity breaks = violation; suspicious-but-tolerable = warning; advisory = info. Every shape carries a human-authored `sh:message`.
- **D-10:** **Raw-RDF hygiene:** the sidecar maps each pySHACL result to a structured entry `{severity, what, where, howToFix, focusLabel, shapeId}` — focus-node IRIs resolved to human labels with local-name fallback (reuse Phase 822's `unsatisfiable_classes` {iri,label} enrichment pattern in `reasoning.py`). `sh:focusNode`, `sh:sourceShape`, raw IRIs, and any `sh:*` vocabulary never appear in fields shown to architects.

### Rule Partition & Precedence Policy
- **D-11:** The policy is a **new `spec/RULE-PARTITION-POLICY.md`**, cross-referenced from `spec/LPG-OWL-MAPPING.md` and CLAUDE.md's schema-change-propagation checklist.
- **D-12:** **Partition line:** the SWRL VALIDATOR owns architect-authored design-compliance rules (quantitative geometry/parameter constraints from NL ingestion — the metagraph Rule corpus). SHACL owns structural data-integrity of instance data (schema conformance of DesignState/Run/Rule structure). The policy includes a "what belongs where" decision table for future rule categories.
- **D-13:** **Precedence:** single-authoring principle — no business rule exists in both systems, so verdict disagreement can only mean mis-categorization; the policy prescribes re-homing the rule (moving it to its correct system), never merging or overriding verdicts. For design compliance, SWRL is authoritative; for data integrity, SHACL is authoritative.
- **D-14:** Enforcement is documentation + review discipline in this phase; an automated shape-vs-rule overlap linter is explicitly deferred.

### Surfacing (Grasshopper + UI)
- **D-15:** **Grasshopper:** the publish response's SHACL block is formatted through a new `ErrorMessageTemplates.ShaclViolation(...)` (What+Where+How-to-fix, matching the class's established tone) in DG.Core, surfaced by the VALIDATOR component in its Report output and as runtime messages. Severity→GH runtime level mapping is Claude's discretion with one constraint: a SHACL data violation must **not** render the component as failed/errored (publish success stays visually distinct from data findings).
- **D-16:** **UI:** the Model screen (`ui-v2/src/screens/ModelScreen.jsx`) gains a SHACL results section in the selected run's detail — runs already live there. The Reasoner screen stays consistency-only (822 scope).
- **D-17:** UI data path: extend the existing run-fetch surface (`/validation/runs/{project}` list or the view endpoints) to include the parsed `shaclReport`; `modelApi.js` picks it up. Pre-823 runs (no `shaclReportJson`) display a quiet "not checked" state — never an error.
- **D-18:** UI severity treatment: red/orange/yellow chips + a count summary (e.g. "2 violations · 1 warning · 3 info") built from existing design tokens (`--color-signal` red; amber/yellow analogs per 822's verdict-state precedent). Empty report renders a positive "conforms" state.

### Claude's Discretion
- Exact shape list/count in `dg-shapes.ttl` (D-08 boundary: data-integrity only, each with sh:message + severity).
- `shacl` response envelope field names; timeout values (bounded by the 821 sidecar timeout pattern); GH runtime-message level mapping (D-15 constraint).
- Whether run-scoped ABox validation unions the static TBox for vocabulary resolution (pySHACL `ont_graph` vs plain union) — pick what pySHACL handles cleanly.
- Copy/wording of all user-facing messages and the "not checked"/"conforms" states.
- Whether `/validation/view/*` endpoints or the runs list carries the report to the UI (whichever the Model screen consumes most naturally).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Normative mapping & upstream contracts
- `spec/LPG-OWL-MAPPING.md` — §"ValidGraph to RDF Sketch (Informative)" (~L321) is the ABox blueprint this phase makes real (DesignState/Run individuals, `dgv:hasState`, UNA interaction); §UNA (`owl:AllDifferent`, ~L300) is now mandatory for the ABox export; §"SWRL Builtin Exclusion" does NOT apply to pySHACL input (only HermiT).
- `.planning/phases/821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation/821-CONTEXT.md` — D-11 (placeholder shapes → 823 swaps real ones), D-04/D-07 (ontology overlay volume-mount pattern D-07 reuses), D-09 (timeout pattern), D-15 (pytest layout).
- `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/820-DECISION.md` — ADR-820-1/2 context; label-scoped export mandate (graph-property drift makes graph-scoping lossy).
- `.planning/REQUIREMENTS.md` — SHCL-01, SHCL-02 (the two requirements this phase closes).

### Existing code to modify
- `dg-reasoner/reasoning.py` — `run_shacl()` (~L316), `_shacl_worker` (~L267), `_run_shacl_with_timeout` (~L284): replace placeholder shapes, add run-scoped ABox path, severity/result mapping with label enrichment (822's {iri,label} pattern lives here too).
- `dg-reasoner/ontology_export.py` — `build_graph(session, project)`: the existing OntoGraph/Metagraph export the ABox unions with; new ValidGraph ABox export lands beside it.
- `data-service/app.py` — `publish_validation` (~L1241) + `store_validation_run` (~L435): the SHACL call + `shaclReportJson` persistence; `post_reasoner_consistency` (~L1173) is the proxy/timeout template; `list_validation_runs`/`/validation/view/*` (~L1339-1434) for the UI data path.
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — gains `ShaclViolation(...)` (What+Where+How-to-fix house style).
- `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` — consumes the publish response's SHACL block into Report/runtime messages.
- `ui-v2/src/screens/ModelScreen.jsx` + `ui-v2/src/lib/modelApi.js` — run detail SHACL section + fetch surface.

### Schema
- `training/dataset_schema.json` + `cypher_template.txt` + `spec/DATABASE.md` — v4 single source of truth. NOTE the live write-path reality: data-service persists `ValidationRun` (graph:'ValidGraph', key `runId`) with `statePayloadJson`/`rulesJson`/`ValidStatus` properties plus `ValidationEntity` rows — the schema's `Run`/`DesignState` labels describe the GH-side conceptual model; the ABox exporter must read what is actually stored (D-04).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dg-reasoner` SHACL plumbing is already real: `run_shacl()` builds the live export and invokes `pyshacl.validate()` in a timeout-bounded spawn+killpg subprocess — 823 only swaps shapes in, adds the ABox, and maps results.
- `data-service/app.py` `post_reasoner_consistency` — the exact httpx proxy/timeout/error-envelope template for the new SHACL call (`DG_REASONER_URL` env already wired).
- Phase 822's label-enrichment (`unsatisfiable_classes` → `{iri, label}` with local-name fallback) — the same pattern D-10 needs for `focusLabel`.
- `ontology/` volume mount into dg-reasoner (821 D-07) — `dg-shapes.ttl` rides the same mount.
- `ErrorMessageTemplates` What+Where+How-to-fix house style + `_structured_error_response` on the Python side.
- ui-v2 `Badge`/`Button` primitives + `--color-signal` and verdict-state color precedents from 822's Reasoner card work.

### Established Patterns
- Synchronous HTTP + explicit timeouts, no message queue (repo-wide Key Decision) — D-01/D-02 honor it.
- Label-scoped Cypher extraction (never scope by the `graph` property) — mandatory for the ABox export too.
- Project isolation via `project` property — ABox IRIs are project-scoped per the mapping spec's IRI-minting rules.
- pytest per-service `tests/` with `@pytest.mark.integration` for live-Neo4j tests (821 D-15).
- Screen-local React state in ui-v2; existing error-line pattern for transport errors.

### Integration Points
- `POST /validation/publish` → (after store) → sidecar `POST /shacl/validate {project, run_id}` → report stored on `ValidationRun` + returned to VALIDATOR.
- VALIDATOR (GH) ← publish response → `ErrorMessageTemplates.ShaclViolation` → Report output + runtime messages.
- Model screen ← runs/view endpoints ← `shaclReportJson`.
- `ontology/dg-shapes.ttl` ← read-only volume → dg-reasoner shape load.

</code_context>

<specifics>
## Specific Ideas

- The 821 placeholder was deliberately labelled "empty placeholder shapes graph — Phase 823 swaps this for real SHACL shapes" — that comment must disappear in this phase; leaving it would signal the swap never happened.
- Solibri Model Checker's severity presentation (red/orange/yellow with counts) is the explicit visual reference for criterion 4 — counts summary first, expandable detail per finding.
- The "no raw RDF vocabulary" bar from 822 (never show full IRIs) applies verbatim: architects see labels and plain-language messages only.
- UNA (`owl:AllDifferent`) is a Phase-821-deferred obligation landing here — the ABox export without it would let a reasoner/validator silently merge distinct states.

</specifics>

<deferred>
## Deferred Ideas

- Automated shape-vs-SWRL-rule overlap linter (D-14) — policy is documentation-first this phase.
- SHACL shape authoring/browsing UI — shapes are version-controlled artifacts for now.
- Durable SHACL history/trends beyond the per-run stored report.
- Async submit/poll for very long SHACL runs — inherited deferral from 821/822.
- Re-running SHACL on historical runs (backfill) — pre-823 runs simply show "not checked".

</deferred>

---

*Phase: 823-SHACL Validation Layer*
*Context gathered: 2026-07-12*
