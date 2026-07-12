# Phase 823: SHACL Validation Layer - Research

**Researched:** 2026-07-12
**Domain:** pySHACL result-graph extraction, Neo4j LPG→RDF ABox translation, cross-language (Python/C#/JSX) error-surfacing pipeline
**Confidence:** HIGH (all code-path claims verified by direct source read; pySHACL/rdflib behavior verified against the actually-installed package source, not training-data recall)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**SHACL Trigger & Data Flow**
- D-01: SHACL runs server-side on each validation run: `POST /validation/publish` (data-service, app.py ~L1241) calls the sidecar's `POST /shacl/validate` synchronously after `store_validation_run`, with an explicit short httpx timeout (mirror the existing `/reasoner/consistency` proxy pattern, app.py ~L1173). No queue, no background jobs.
- D-02: SHACL is non-fatal to publish. If the sidecar is unreachable, times out, or errors, the publish response and stored run carry `shacl: {status: "unavailable"|"timeout", ...}` and the publish still returns 200 with its normal payload. A SHACL failure must never block or fail the Speckle-publish hot path.
- D-03: `POST /shacl/validate` request gains an optional `run_id` alongside `project`: `{project, run_id?}`. With `run_id`, the sidecar validates that run's ValidGraph ABox (D-04) unioned with the project's existing OntoGraph/Metagraph export. Without `run_id`, validates the project-level export as today (backward compatible with the 821 contract).
- D-04: Phase 823 builds the ValidGraph→RDF ABox export in dg-reasoner per `spec/LPG-OWL-MAPPING.md` §"ValidGraph to RDF Sketch": DesignState kinds → `dgv:ObjState/ParamState/PropState` individuals, Run → `dgv:Run` with `ValidStatus`/`SendStatus`, `HAS_STATE` composition → `dgv:hasState`. Primary data source is the `statePayloadJson` v2 envelope stored on the `ValidationRun` node — the exporter parses the envelope and mints individuals; if live `DesignState` nodes exist for the project (label-scoped read), include them too. Promote the sketch's normative details as needed and update the spec's status note.
- D-05: The ABox export implements `owl:AllDifferent` (UNA) over all minted named individuals in the export batch — the obligation Phase 821 explicitly deferred to this phase.
- D-06: SHACL report is stored as `shaclReportJson` on the `ValidationRun` node (same pattern as `rulesJson`/`statePayloadJson`) and returned in the publish response so the Grasshopper VALIDATOR can surface it immediately.

**Shapes Authoring & Severity**
- D-07: Shapes live in `ontology/dg-shapes.ttl`, version-controlled, loaded by the sidecar from the existing read-only `./ontology` volume mount (821 D-04/D-07 overlay pattern — edit + restart, no image rebuild). The 821 "empty placeholder shapes graph" in `run_shacl()` is replaced by loading this file.
- D-08: Shape scope for 823 = data-integrity shapes for v4 instance data (DesignState `kind` enum; PropState composition completeness; Run `ValidStatus`/`SendStatus`; Rule structural integrity; Atom `REFERS_TO` target resolvable; Var `name` non-empty). Exact shape list is planner/researcher discretion — but no architect-authored business rule may be re-encoded as a shape (partition policy).
- D-09: Severity uses standard SHACL vocabulary mapped once: `sh:Violation` → `violation` (red), `sh:Warning` → `warning` (orange), `sh:Info` → `info` (yellow) — Solibri-style. Severity is set per shape by design intent. Every shape carries a human-authored `sh:message`.
- D-10: Raw-RDF hygiene: the sidecar maps each pySHACL result to a structured entry `{severity, what, where, howToFix, focusLabel, shapeId}` — focus-node IRIs resolved to human labels with local-name fallback (reuse Phase 822's `unsatisfiable_classes` {iri,label} enrichment pattern in `reasoning.py`). `sh:focusNode`, `sh:sourceShape`, raw IRIs, and any `sh:*` vocabulary never appear in fields shown to architects.

**Rule Partition & Precedence Policy**
- D-11: The policy is a new `spec/RULE-PARTITION-POLICY.md`, cross-referenced from `spec/LPG-OWL-MAPPING.md` and CLAUDE.md's schema-change-propagation checklist.
- D-12: Partition line: SWRL VALIDATOR owns architect-authored design-compliance rules (quantitative geometry/parameter constraints from NL ingestion). SHACL owns structural data-integrity of instance data. The policy includes a "what belongs where" decision table for future rule categories.
- D-13: Precedence: single-authoring principle — no business rule exists in both systems, so verdict disagreement can only mean mis-categorization; the policy prescribes re-homing the rule, never merging or overriding verdicts. For design compliance, SWRL is authoritative; for data integrity, SHACL is authoritative.
- D-14: Enforcement is documentation + review discipline in this phase; an automated shape-vs-rule overlap linter is explicitly deferred.

**Surfacing (Grasshopper + UI)**
- D-15: Grasshopper: the publish response's SHACL block is formatted through a new `ErrorMessageTemplates.ShaclViolation(...)` (What+Where+How-to-fix, matching the class's established tone) in DG.Core, surfaced by the VALIDATOR component in its Report output and as runtime messages. Severity→GH runtime level mapping is Claude's discretion with one constraint: a SHACL data violation must not render the component as failed/errored (publish success stays visually distinct from data findings).
- D-16: UI: the Model screen (`ui-v2/src/screens/ModelScreen.jsx`) gains a SHACL results section in the selected run's detail — runs already live there. The Reasoner screen stays consistency-only (822 scope).
- D-17: UI data path: extend the existing run-fetch surface (`/validation/runs/{project}` list or the view endpoints) to include the parsed `shaclReport`; `modelApi.js` picks it up. Pre-823 runs (no `shaclReportJson`) display a quiet "not checked" state — never an error.
- D-18: UI severity treatment: red/orange/yellow chips + a count summary (e.g. "2 violations · 1 warning · 3 info") built from existing design tokens (`--color-signal` red; amber/yellow analogs per 822's verdict-state precedent). Empty report renders a positive "conforms" state.

### Claude's Discretion
- Exact shape list/count in `dg-shapes.ttl` (D-08 boundary: data-integrity only, each with sh:message + severity).
- `shacl` response envelope field names; timeout values (bounded by the 821 sidecar timeout pattern); GH runtime-message level mapping (D-15 constraint).
- Whether run-scoped ABox validation unions the static TBox for vocabulary resolution (pySHACL `ont_graph` vs plain union) — pick what pySHACL handles cleanly.
- Copy/wording of all user-facing messages and the "not checked"/"conforms" states.
- Whether `/validation/view/*` endpoints or the runs list carries the report to the UI (whichever the Model screen consumes most naturally).

### Deferred Ideas (OUT OF SCOPE)
- Automated shape-vs-SWRL-rule overlap linter (D-14) — policy is documentation-first this phase.
- SHACL shape authoring/browsing UI — shapes are version-controlled artifacts for now.
- Durable SHACL history/trends beyond the per-run stored report.
- Async submit/poll for very long SHACL runs — inherited deferral from 821/822.
- Re-running SHACL on historical runs (backfill) — pre-823 runs simply show "not checked".
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHCL-01 | DesignState/Rule instance data translated to RDF and validated via SHACL on each validation run, alongside SWRL VALIDATOR, with a documented rule-partition/precedence policy | ValidGraph ABox export design (below), `_shacl_worker`/`run_shacl` upgrade plan, `spec/RULE-PARTITION-POLICY.md` structure guidance |
| SHCL-02 | SHACL violations surface through ErrorMessageTemplates (What+Where+How-to-fix) with info/warning/violation → red/orange/yellow, never raw RDF/SHACL vocabulary | pySHACL result-graph extraction pattern, `ErrorMessageTemplates.ShaclViolation` design, ModelScreen severity-chip gap analysis |

</phase_requirements>

**Note on the UI-SPEC file:** `.planning/phases/823-shacl-validation-layer/823-UI-SPEC.md` referenced in the task inputs does not exist on disk — only `823-CONTEXT.md` is present in that directory (confirmed via directory listing). STATE.md's `stopped_at: "Phase 823 UI-SPEC approved"` and the Session Continuity `Resume file` pointer to it appear to be stale/aspirational bookkeeping, not a written artifact. The planner should treat CONTEXT.md's D-16/D-17/D-18 (and this research's ModelScreen findings) as the UI contract for this phase, or invoke `/gsd-ui-phase` first if a formal UI-SPEC is wanted before planning.

## Summary

Phase 821 already proved the pySHACL plumbing end-to-end (`dg-reasoner/reasoning.py::run_shacl`/`_shacl_worker`/`_run_shacl_with_timeout`) but validates the live OntoGraph/Metagraph export against a deliberately empty shapes graph — it always conforms and returns only `{conforms, results: []}`, discarding pySHACL's actual per-result data. Phase 823's real work is threefold: (1) extract structured per-result data (severity, message, focus node, path) from pySHACL's `results_graph` instead of just the `conforms` bool, and — critically — pass `allow_warnings=True, allow_infos=True` to `pyshacl.validate()` so the `conforms` flag isn't spuriously flipped false by every Info-severity shape (verified against the installed pySHACL 0.40.0 source: `shape.py` L728-737 shows `conforms` factors in ALL severities unless explicitly allowed); (2) build a new ValidGraph→RDF ABox exporter that reads the `statePayloadJson` v2 envelope directly off the `ValidationRun` Neo4j node (confirmed empirically: `cypher_template.txt` documents DesignState/Run as "document-only — NOT emitted by LLM ingest", and `store_validation_run` in app.py never creates DesignState/Run graph nodes — only `ValidationRun`+`ValidationEntity` — so the "live DesignState nodes" branch in D-04 will be a no-op in current data, but should still be implemented defensively per the label-scoping mandate); (3) wire the result through five layers unmodified in shape but new in content: dg-reasoner → data-service (non-fatal proxy + persistence) → `ValidationPublishResponse` (C# DTO needs a new field) → `ErrorMessageTemplates.ShaclViolation` → ModelScreen.jsx (a UI section that has nowhere to slot color severity yet — no orange/yellow design tokens exist in the codebase today).

**Primary recommendation:** Extend `reasoning.py`'s existing subprocess/timeout skeleton in place (don't rewrite it) — swap the empty `Graph()` shapes graph for a loaded `ontology/dg-shapes.ttl`, add a `_walk_shacl_results(results_graph)` helper using `rdflib.namespace.SH` constants, and add a new `valid_graph_export.py` sibling to `ontology_export.py` for the ABox translation (mirrors 821 D-08's per-service file layout). On the UI side, budget explicit design-token work: the "amber/yellow analogs per 822's verdict-state precedent" referenced in CONTEXT.md does not exist in the current codebase (Phase 822 has a plan but has not executed — `ReasonerScreen.jsx` today only has generic `Badge variant="solid"/"outline"`, no severity color system) — this phase must add the warning/info color tokens itself, not "reuse" a pattern that isn't there yet.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| RDF ABox translation (DesignState/Run → dgv: individuals) | API/Backend (dg-reasoner sidecar) | — | Pure Cypher→RDFLib transform, same tier as the existing OntoGraph/Metagraph exporter it's unioned with |
| SHACL shape evaluation (pySHACL) | API/Backend (dg-reasoner sidecar) | — | CPU-bound, JVM-adjacent-free (pure Python), isolated from data-service's hot path per the sidecar architecture (REAS-05) |
| SHACL result → structured envelope mapping (severity/label enrichment) | API/Backend (dg-reasoner) | — | Same process as the pySHACL call; label enrichment needs the same Neo4j session the export used |
| Non-fatal SHACL proxy call + `shaclReportJson` persistence | API/Backend (data-service) | — | Mirrors `post_reasoner_consistency`'s existing proxy-with-timeout pattern; data-service already owns `ValidationRun` persistence |
| ErrorMessageTemplates.ShaclViolation formatting | Grasshopper Plugin (DG.Core) | — | DG.Core has zero GH SDK dependency; existing house style (What+Where+How-to-fix) lives here for all other error surfaces |
| SHACL block consumption + runtime messages | Grasshopper Plugin (DG.Grasshopper, ValidatorComponent) | — | ValidatorComponent already owns the publish-response→Report/runtime-message pipeline |
| SHACL results section + severity chips | Frontend (ui-v2 ModelScreen.jsx) | — | Same screen already owns the "Validation run" detail panel; no new screen needed |
| Rule-partition policy documentation | Docs/Spec (spec/) | — | Pure documentation artifact, no runtime tier |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pySHACL | 0.40.0 | SHACL Core validation of the ABox | Already pinned in `dg-reasoner/requirements.txt` since Phase 821; pure Python, no new JVM surface `[VERIFIED: dg-reasoner/requirements.txt, local package inspection]` |
| RDFLib | 7.6.0 | RDF graph construction/serialization shared with pySHACL and Owlready2 | Already pinned; `rdflib.namespace.SH` (a `DefinedNamespace`) ships inside this version and exposes `SH.Violation`/`SH.Warning`/`SH.Info`/`SH.resultSeverity`/`SH.focusNode`/`SH.resultMessage`/`SH.resultPath`/`SH.sourceShape`/`SH.result`/`SH.conforms`/`SH.ValidationReport` — confirmed by reading the installed `rdflib/namespace/_SH.py` directly `[VERIFIED: local rdflib 7.6.0 install, C:\Users\Admin\AppData\Roaming\Python\Python314\site-packages\rdflib\namespace\_SH.py]` |
| owlrl | 7.6.2 | pySHACL's own transitive dependency (OWL 2 RL forward-chaining, used only if `inference=` is set) | Already pinned; not directly imported by dg-reasoner code, kept for pySHACL's declared range `[VERIFIED: dg-reasoner/requirements.txt]` |

**No new packages are introduced by this phase** — pySHACL/RDFLib/owlrl were all installed in Phase 821 for exactly this purpose. See Package Legitimacy Audit below (all `N/A — already vetted`).

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyshacl.consts` (internal module) | bundled | Alternative source of `SH_*` constant names (`SH_focusNode`, `SH_resultSeverity`, etc.) | Prefer `rdflib.namespace.SH` instead (public rdflib API, not an internal pyshacl module) — use `pyshacl.consts` only if a name is missing from rdflib's `SH` `DefinedNamespace` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `rdflib.namespace.SH` constants | `pyshacl.consts.SH_*` constants | Both resolve to the identical `http://www.w3.org/ns/shacl#` IRIs (verified: pyshacl's own `validator_conformance.py` imports from `pyshacl.consts`, which are just `SH.foo` aliases) — `rdflib.namespace.SH` is preferred because it's stable public rdflib API, not tied to pySHACL's internal module layout across future upgrades |

**Installation:** None required — no new `pip install` lines for this phase.

**Version verification:** `pip show pyshacl` on this machine confirms `Version: 0.40.0` matching the repo's pin; `dg-reasoner/requirements.txt` pins `pyshacl==0.40.0`, `rdflib==7.6.0`, `owlrl==7.6.2` unchanged since Phase 821 — no version bump needed for this phase's work.

## Package Legitimacy Audit

No new external packages are introduced by this phase. All three RDF/SHACL libraries used (`pyshacl`, `rdflib`, `owlrl`) were installed and vetted in Phase 821's STACK.md research and remain unchanged.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| pyshacl | PyPI | Phase 821 research: actively maintained, RDFLib org | Phase 821 research: sufficient | github.com/RDFLib/pySHACL | OK (carried from Phase 821) | Already approved — no re-audit needed |
| rdflib | PyPI | Phase 821 research | — | github.com/RDFLib/rdflib | OK (carried from Phase 821) | Already approved |
| owlrl | PyPI | Phase 821 research | — | — | OK (carried from Phase 821, transitive pySHACL dependency) | Already approved |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Grasshopper VALIDATOR component
  │  SendValid=true
  ▼
ValidationPublishClient.Publish()  (DG.Grasshopper, HTTP POST)
  │
  ▼
data-service  POST /validation/publish  (app.py:1241 publish_validation)
  │
  ├─► Speckle publish (existing, unchanged)
  ├─► store_validation_run()  — writes ValidationRun + ValidationEntity nodes (existing, unchanged)
  │
  └─► NEW: httpx.post(DG_REASONER_URL + "/shacl/validate", {project, run_id})
           │  short timeout, non-fatal (D-01/D-02)
           ▼
      dg-reasoner  POST /shacl/validate  (app.py:85 shacl_validate)
           │
           ▼
      reasoning.run_shacl(project, run_id, session)
           │
           ├─► ontology_export.build_graph(session, project)          — existing Metagraph/OntoGraph export
           ├─► NEW: valid_graph_export.build_valid_graph(session, project, run_id)
           │         reads ValidationRun.statePayloadJson (v2 envelope) → dgv:ObjState/ParamState/PropState/Run individuals
           ├─► NEW: add owl:AllDifferent over ALL minted individuals (UNA, D-05)
           ├─► load ontology/dg-shapes.ttl  (replaces empty placeholder Graph())
           │
           ▼
      pyshacl.validate(data_graph, shacl_graph=shapes, allow_warnings=True, allow_infos=True)
           │  returns (conforms, results_graph, results_text)
           ▼
      NEW: _walk_shacl_results(results_graph) → [{severity, message, focusNode, path, sourceShape}, ...]
           │  + label enrichment (focusNode IRI → human label, reuse 822's {iri,label} pattern)
           ▼
      structured JSON result, put on multiprocessing.Queue (must be JSON-serializable — no rdflib objects)
           │
           ◄─── back through data-service ───
           │
           ├─► shaclReportJson persisted on ValidationRun node (D-06)
           └─► included in /validation/publish response body
           │
           ▼
ValidationPublishResponse (C# DTO, DG.Grasshopper) — gains new Shacl field
           │
           ▼
ValidatorComponent.SolveInstance() → ErrorMessageTemplates.ShaclViolation(what, where, howToFix)
           │
           ├─► Report output (text list)
           └─► AddRuntimeMessage (level capped at Warning — never Error, per D-15)

Independently, on screen load:
ui-v2 ModelScreen.jsx ──fetchValidationRuns/fetchValidationView──► GET /validation/runs/{project} or /validation/view/*
           │
           ▼
      shaclReport parsed from stored shaclReportJson → severity chips (red/orange/yellow) + count summary
      in the existing "Validation run" Panel, right sidebar (ui-v2/src/screens/ModelScreen.jsx ~L885)
```

### Recommended Project Structure

```
dg-reasoner/
├── reasoning.py            # MODIFY: run_shacl() gains run_id param, loads dg-shapes.ttl, calls new result-walker
├── valid_graph_export.py   # NEW: build_valid_graph(session, project, run_id) — ValidGraph→RDF ABox translator
├── ontology_export.py      # MODIFY (maybe): shared add_all_different() helper if not placed in valid_graph_export.py
└── tests/
    ├── test_valid_graph_export.py   # NEW: unit fixture tests (mirrors test_ontology_export.py's _walk_list/turtle_graph pattern)
    └── test_reasoning.py            # NEW or extend: _walk_shacl_results() unit tests against a hand-built results_graph fixture

ontology/
└── dg-shapes.ttl           # NEW: version-controlled SHACL shapes, volume-mounted read-only (821 D-07 pattern)

data-service/
├── app.py                  # MODIFY: publish_validation() gains SHACL proxy call; store_validation_run() gains shaclReportJson param
└── tests/
    └── test_shacl_proxy.py # NEW: mirrors test_reasoner.py's TestClient pattern for the new proxy call

DG/src/DG.Core/Services/
└── ErrorMessageTemplates.cs   # MODIFY: add ShaclViolation(...)

DG/src/DG.Grasshopper/Validation/
├── ValidationPublishContract.cs  # MODIFY: ValidationPublishResponse gains a Shacl field (new nested DTO)
└── ValidatorComponent.cs         # MODIFY: consume response.Shacl, format via ErrorMessageTemplates, add to Report + runtime messages

ui-v2/src/
├── screens/ModelScreen.jsx      # MODIFY: add SHACL section to "Validation run" Panel
├── lib/modelApi.js              # MODIFY (maybe): none if shaclReport rides existing fetchValidationRuns/fetchValidationView payloads
└── styles/tokens/colors.css     # MODIFY: add --color-warning/--color-info (orange/yellow) — DO NOT EXIST TODAY

spec/
└── RULE-PARTITION-POLICY.md     # NEW
```

### Pattern 1: pySHACL result-graph walking (the core new technical pattern)

**What:** `pyshacl.validate()` returns `(conforms, results_graph, results_text)`. `results_graph` is a plain `rdflib.Graph` containing one `sh:ValidationReport` node with `sh:result` edges to individual result nodes. Each result node carries `sh:resultSeverity`, `sh:focusNode`, `sh:resultMessage`, `sh:resultPath` (optional), `sh:sourceShape`, `sh:value` (optional).

**When to use:** Replaces the current `_shacl_worker`'s `queue.put({"conforms": bool(conforms)})` — that line discards everything except the boolean.

**Critical gotcha (verified against installed pySHACL 0.40.0 source, `pyshacl/shape.py` lines 728-737):** By default (`allow_infos=False, allow_warnings=False`), **any** `sh:Warning` or `sh:Info` severity result causes pySHACL's own `conforms` to be `False` — identical treatment to a `sh:Violation`. This directly conflicts with D-18's "empty report renders a positive conforms state" intent (an Info-only report should still read as "conforms" to the architect, distinguishable from a real Violation). The fix is to call `pyshacl.validate(..., allow_infos=True, allow_warnings=True)` — this makes pySHACL's `conforms` reflect **violations only** while still including all Info/Warning results in `results_graph` for display. Do NOT rely on the raw `conforms` return value without these two kwargs.

**Example (Python, new code for `reasoning.py` or a new `shacl_results.py` helper):**
```python
# Source: verified against installed pySHACL 0.40.0 (pyshacl/entrypoints.py, pyshacl/shape.py)
# and rdflib 7.6.0's bundled SH DefinedNamespace (rdflib/namespace/_SH.py)
from rdflib.namespace import SH
from pyshacl import validate as pyshacl_validate

conforms, results_graph, _results_text = pyshacl_validate(
    data_graph,
    shacl_graph=shapes_graph,
    inference="none",
    advanced=False,
    allow_infos=True,      # sh:Info no longer flips `conforms` to False
    allow_warnings=True,   # sh:Warning no longer flips `conforms` to False
)

structured_results = []
for report in results_graph.subjects(predicate=None, object=SH.ValidationReport):
    for result in results_graph.objects(report, SH.result):
        severity_uri = results_graph.value(result, SH.resultSeverity)
        structured_results.append({
            "severity": {SH.Violation: "violation", SH.Warning: "warning", SH.Info: "info"}
                .get(severity_uri, "violation"),  # default per SHACL spec: sh:Violation
            "message": str(results_graph.value(result, SH.resultMessage) or ""),
            "focusNode": str(results_graph.value(result, SH.focusNode) or ""),
            "path": str(results_graph.value(result, SH.resultPath) or ""),
            "sourceShape": str(results_graph.value(result, SH.sourceShape) or ""),
        })
# structured_results is plain dict/str -- JSON-serializable, safe to queue.put() across
# the multiprocessing boundary (unlike raw URIRef/Literal/BNode rdflib objects).
```

**Focus-node label enrichment:** reuse the exact `_local_name()` helper and `{iri, label}` shape already in `reasoning.py` (used for `unsatisfiable_classes` in `_reason_worker`). The ABox export mints IRIs with `rdfs:label` for Rule/state individuals — look up `rdfs.label` on the focus node in the data graph (not the results graph) before falling back to `_local_name(focusNode)`.

### Pattern 2: ValidGraph ABox export — reading the real v2 envelope

**What:** The `statePayloadJson` stored on `ValidationRun` nodes is produced by `DG.Core.Serialization.DesignStatePayloadV2Serializer.Serialize()`. Its exact JSON shape (verified by reading the C# serializer directly, camelCase via `JsonNamingPolicy.CamelCase`):

```json
{
  "version": "2",
  "stateId": "DS_...",
  "label": "optional string or null",
  "capturedAtUtc": "2026-07-12T10:00:00.0000000Z",
  "objStates": [
    {"stateId": "OS_...", "objectRef": "string (required)", "label": "string or null", "capturedAtUtc": "..." }
  ],
  "paramStates": [
    {"stateId": "DS_...", "capturedAtUtc": "...",
     "parameters": [{"parameterId": "p1", "displayName": "Height", "type": "number|integer|boolean", "value": 75.0}]}
  ],
  "propStates": [
    {"stateId": "PS_...", "ruleIri": "ex:...", "dataPropertyIri": "ex:...", "objectRef": "string or null",
     "propValue": {"parameterId": "...", "displayName": "...", "type": "number|integer|boolean", "value": 12} }
  ]
}
```

**When to use:** This is the exporter's ONLY reliable data source per D-04 — `Neo4j` does not store separate `DesignState`/`Run` graph nodes for the current write path (verified: `cypher_template.txt` L50 documents these as "document-only — NOT emitted by LLM ingest"; `store_validation_run()` in `app.py` only `MERGE`s `ValidationRun`/`ValidationEntity` nodes, never `DesignState`). The "if live DesignState nodes exist" branch in D-04 should still be implemented (label-scoped, per the export-scoping mandate) but expect it to be a no-op against current live data — do not let its absence silently degrade to zero-individuals; log/report the count either way.

**Fetching the envelope for a specific run (new Cypher, mirrors ontology_export.py's label-scoped style):**
```cypher
-- Source: pattern consistent with ontology_export.py's ONTOGRAPH_QUERY/METAGRAPH_QUERY
MATCH (run:ValidationRun)
WHERE run.project = $project AND run.runId = $runId
RETURN run.statePayloadJson AS statePayloadJson,
       run.ValidStatus AS validStatus,
       run.SendStatus AS sendStatus
```

**IRI minting for state individuals (per LPG-OWL-MAPPING.md §ValidGraph to RDF Sketch, already normative-adjacent):**
- `dgv:ObjState`/`ParamState`/`PropState`: `{base}/project/{project}/state/{stateId}` — reuse `mint(project, "state", state_id)` following `ontology_export.py`'s existing `mint()` helper pattern exactly.
- `dgv:Run`: `{base}/project/{project}/run/{run_id}`.
- `HAS_STATE` (parent DesignState → its ObjState/ParamState/PropState children) → `dgv:hasState` object property, one triple per child.
- `Run.ValidStatus` (bool list) → `rdf:List` of `xsd:boolean` literals (reuse `make_argument_list`-style helper, already in `ontology_export.py`), attached via a new `dgv:validStatus` property.
- `Run.SendStatus` (single bool) → `dgv:sendStatus` `xsd:boolean` datatype property.

### Pattern 3: owl:AllDifferent (UNA) construction

**What:** rdflib construction of an anonymous `owl:AllDifferent` individual with `owl:distinctMembers` as an `rdf:List`.

**When to use:** Required once per export batch, over the UNION of Metagraph individuals (Rule/Atom/Var — already minted by `ontology_export.build_graph`) and the new ValidGraph individuals (ObjState/ParamState/PropState/Run) minted by the new exporter. Not yet implemented anywhere in the codebase (confirmed: no `OWL.AllDifferent` reference exists in `ontology_export.py` today).

```python
# Source: pattern reuses ontology_export.py's existing make_atom_list()-style
# list-construction helper (BNode chain via rdf:first/rdf:rest), applied to
# owl:distinctMembers instead of swrl:AtomList/rdf:List semantics.
from rdflib import BNode
from rdflib.namespace import OWL, RDF

def add_all_different(graph: Graph, individuals: list[URIRef]) -> None:
    if not individuals:
        return
    all_diff = BNode()
    graph.add((all_diff, RDF.type, OWL.AllDifferent))
    graph.add((all_diff, OWL.distinctMembers, make_argument_list(graph, individuals)))
    # make_argument_list already exists in ontology_export.py -- reuse it verbatim,
    # it builds a bare rdf:List with no extra typing, exactly what owl:distinctMembers needs.
```

Collect `individuals` by tracking every `URIRef` minted during both `build_graph()` and `build_valid_graph()` (both already build internal `atom_iri`/similar dicts keyed by entity id — extend to return the mint list, or walk `graph.subjects()` filtered by `RDF.type` in (`SWRL.Variable`, `SWRL.Imp`, ..., `DGV.ObjState`, `DGV.Run`, ...) after both exports are merged).

### Anti-Patterns to Avoid

- **Don't put raw pySHACL results (URIRef/BNode/Literal objects) on the multiprocessing Queue.** `_shacl_worker` runs in a `spawn`-context subprocess and communicates via `multiprocessing.Queue`, which pickles its payload. rdflib term objects are picklable in principle, but the existing worker pattern (and `_reason_worker`'s `unsatisfiable_classes` handling) already establishes the convention of converting everything to plain `str`/`bool`/`dict` before `queue.put()` — follow that convention for consistency and to guarantee the FastAPI JSON response layer can serialize it without a custom encoder.
- **Don't call `pyshacl.validate()` without `allow_infos=True, allow_warnings=True`** — see Pattern 1's gotcha. Silently shipping the default would make every project with even one Info-severity shape report `conforms: false`, contradicting D-18's "empty [violations] report renders a positive conforms state".
- **Don't scope the new Cypher queries by the `graph` property.** `spec/LPG-OWL-MAPPING.md`'s Export Scoping mandate applies to the ValidGraph exporter too — scope by label (`n:DesignState OR n:Run`) or by the `ValidationRun` node's own key properties (`project`, `runId`), never by `{graph: 'ValidGraph'}` (known tagging drift precedent: `phase14-smoke` project has `DesignState`/`Run` nodes mistagged `graph:'Metagraph'` per the spec's own documented audit).
- **Don't use `GH_RuntimeMessageLevel.Error` for SHACL violations in `ValidatorComponent`.** D-15 explicitly requires that a SHACL data finding never renders the component as failed/errored. Grasshopper only has three native runtime levels (Remark=blue/informational, Warning=orange, Error=red+component-visually-fails). Cap the severity mapping at `Warning` even for `sh:Violation`-severity SHACL results; reserve `Error` exclusively for true component failures (missing required inputs, publish exceptions) as the component already does today.
- **Don't assume Phase 822's "verdict-state color precedent" exists in code yet.** See Common Pitfalls below — this is a hard blocker for D-18 if not addressed directly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SHACL constraint evaluation | Custom Cypher-based shape checker | pySHACL (already pinned) | Already proven in Phase 821's plumbing; hand-rolling SHACL semantics (targets, path traversal, severity defaults) duplicates a W3C-spec-compliant library for no benefit |
| SH vocabulary IRIs | Hard-coded string IRIs (`"http://www.w3.org/ns/shacl#Violation"`) | `rdflib.namespace.SH.Violation` etc. | Avoids typos in long IRI strings scattered across the codebase; `SH` is a `DefinedNamespace` so `SH.Foo` raises at attribute-access time if the term doesn't exist, catching typos early |
| RDF list construction for `owl:distinctMembers` | New bespoke list-builder | `ontology_export.py`'s existing `make_argument_list()` | Already handles the exact rdf:List/BNode-chain construction needed; UNA's `owl:distinctMembers` has the same "bare list, no extra typing" shape as `swrl:arguments` |
| IRI minting for new entity kinds (state/run) | New ad-hoc string-formatting function | `ontology_export.py`'s existing `mint(project, kind, key)` | Already implements the exact `{base}/project/{project}/{kind}/{key}` scheme the mapping spec requires; adding `"state"`/`"run"` as new `kind` values requires zero new logic |

**Key insight:** Every piece of RDF-construction machinery this phase needs (list-building, IRI minting, prefix binding, label enrichment, timeout/subprocess isolation) already exists in `dg-reasoner/reasoning.py` and `dg-reasoner/ontology_export.py` from Phase 821/822. This phase is almost entirely *extension* of existing helpers with new inputs (a shapes file, a new data source), not new infrastructure.

## Common Pitfalls

### Pitfall 1: pySHACL's default `conforms` semantics contradict D-18's intent
**What goes wrong:** Any project whose SHACL report contains only Info or Warning findings (no true Violations) would report `conforms: false` from pySHACL's raw return value, making the UI show a false "not conforming" state for what should read as "conforms, with advisory notes."
**Why it happens:** pySHACL's default (`allow_infos=False, allow_warnings=False`) treats every non-default severity as conformance-breaking unless explicitly told otherwise (verified in `pyshacl/shape.py` L728-737).
**How to avoid:** Always pass `allow_infos=True, allow_warnings=True` to `pyshacl.validate()`; derive the UI's "conforms" boolean from `not any(r["severity"] == "violation" for r in structured_results)`, not from pySHACL's raw `conforms` bool directly (or use the raw bool AFTER confirming the two kwargs are set, which makes it equivalent).
**Warning signs:** A test project with zero Violation-severity shapes but one Info-severity shape shows `shaclReport.conforms === false` in the API response.

### Pitfall 2: The "822 verdict-state color precedent" referenced in CONTEXT.md D-18 does not exist yet
**What goes wrong:** The planner writes a task like "reuse 822's amber/yellow color tokens for warning/info chips" and the task silently fails or produces an incorrect result because there is nothing to reuse.
**Why it happens:** Per `.planning/STATE.md`, Phase 822 has a plan (`c428ed1 docs(822): create phase plan`) but has NOT executed — `ReasonerScreen.jsx` (read directly for this research) still shows only the pre-822 placeholder UI (`Badge variant="solid"`/`"outline"`, no severity colors at all). `ui-v2/src/styles/tokens/colors.css` (read directly) defines only `--color-signal` (red, both light/dark variants) plus `--status-fail`/`--status-pass`/`--status-base` — **no amber, orange, warning, or info color token exists anywhere in the token files today.** STATE.md itself documents "Phase 823 (SHACL) depends on Phase 821 only, not Phase 822" — meaning 823 could genuinely execute before 822 lands its verdict-state UI.
**How to avoid:** Treat the color-token work as net-new for this phase. Add `--color-warning`/`--color-warning-ink`/`--color-warning-soft` (orange, e.g. `#e88a00` family) and `--color-info`/`--color-info-ink`/`--color-info-soft` (yellow, e.g. `#c9a000` family) to `colors.css` in both the `:root` (light) and dark-mode override blocks, following the exact structure already used for `--color-signal`/`--color-signal-ink`/`--color-signal-soft`/`--color-signal-mid`. Do not block this phase's UI work on Phase 822 landing first — if 822 lands its own tokens later with different names, that's a follow-up rename, not a blocker now.
**Warning signs:** Design review finds SHACL warning/info chips rendered in plain red (falling back to `--color-signal`) or unstyled black text because no orange/yellow token resolved.

### Pitfall 3: `run_shacl()`'s current signature and the sidecar's `ShaclRequest` model both need a breaking-compatible extension
**What goes wrong:** Forgetting that THREE places share the `{project, run_id?}` contract: `dg-reasoner/app.py`'s `ShaclRequest` Pydantic model (currently `project: str` only), `reasoning.run_shacl(project, session=None)`'s Python signature, and `data-service/app.py`'s new proxy call payload. Missing one breaks either the 821 backward-compat guarantee (D-03) or the new run-scoped path.
**Why it happens:** The three layers are edited independently in different files/languages.
**How to avoid:** Add `run_id: str | None = None` to all three simultaneously; keep `test_shacl_validate_returns_empty_shapes_contract` (existing test in `dg-reasoner/tests/test_routes.py`) passing unmodified as the backward-compat check — it calls `POST /shacl/validate` with only `{"project": "x"}` and expects the pre-823 contract shape to still work when `run_id` is omitted.
**Warning signs:** Existing `test_routes.py` tests fail after the change, or the new run-scoped path silently ignores `run_id` because the Pydantic model dropped the field on request parsing.

### Pitfall 4: The publish-response SHACL block must survive TWO independent JSON deserialization boundaries
**What goes wrong:** `ValidationPublishResponse` (C#, `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs`) is deserialized via `System.Text.Json` with `PropertyNamingPolicy = JsonNamingPolicy.CamelCase` from the raw HTTP response body data-service returns. If the new `Shacl` field's nested C# DTO property names don't exactly camelCase-match the Python dict keys data-service forwards (which themselves must match what dg-reasoner's structured result uses), the GH-side object will silently deserialize with nulls (System.Text.Json doesn't throw on unknown/missing properties by default) rather than erroring loudly.
**Why it happens:** Three independent naming choices (dg-reasoner Python dict keys → data-service JSON pass-through → C# DTO property names) with no compile-time or schema check between them.
**How to avoid:** Pick the field names once (e.g. `severity`, `what`, `where`, `howToFix`, `focusLabel`, `shapeId`, `status`, `conforms`) and use identical camelCase spelling in all three layers; add a DG.Tests round-trip test that deserializes a hand-built JSON string through `ValidationPublishResponse` and asserts every `Shacl` field populated (mirrors the existing `DesignStatePayloadV2SerializerTests.cs` round-trip pattern).
**Warning signs:** GH component's Report output shows a SHACL section but every field renders empty/blank despite the raw HTTP response (visible via browser devtools or a manual curl) containing real data.

## Code Examples

### Non-fatal proxy call pattern (data-service, mirrors existing `post_reasoner_consistency`)
```python
# Source: adapted from the existing post_reasoner_consistency (data-service/app.py ~L1174),
# which is the explicit template cited by CONTEXT.md D-01. This version differs in that it
# must be NON-FATAL (D-02) -- it never raises, it returns a status dict for embedding.
def _call_shacl_validate(project: str, run_id: str) -> dict:
    try:
        response = httpx.post(
            f"{DG_REASONER_URL}/shacl/validate",
            json={"project": project, "run_id": run_id},
            # Shorter than post_reasoner_consistency's 95s read timeout -- SHACL runs
            # inline in the publish hot path (D-01) and must not hold the Speckle-publish
            # response open as long as an on-demand OWL consistency check can. Recommend
            # a distinct env var (e.g. DG_SHACL_HTTP_TIMEOUT_SECONDS, default ~15s) rather
            # than reusing DG_REASONER_TIMEOUT_SECONDS (90s) for this proxy's own client-side wait.
            timeout=httpx.Timeout(connect=2.0, read=15.0, write=2.0, pool=2.0),
        )
        body = response.json()
        if response.status_code == 504 or body.get("error") == "timeout":
            return {"status": "timeout"}
        return {"status": "ok", **body}
    except httpx.TimeoutException:
        return {"status": "timeout"}
    except httpx.ConnectError:
        return {"status": "unavailable"}
    except Exception:
        # Catch-all: SHACL must NEVER raise into publish_validation's success path (D-02).
        return {"status": "unavailable"}
```

### Existing `ErrorMessageTemplates` house style to match (verified from `DG/src/DG.Core/Services/ErrorMessageTemplates.cs`)
```csharp
// Source: DG/src/DG.Core/Services/ErrorMessageTemplates.cs (existing, read directly)
// Every template: {Component/Context}: {what happened}. {how to fix}.
// New method should follow this exact shape -- e.g.:
public static string ShaclViolation(string severity, string what, string where, string howToFix)
{
    return $"SHACL {severity}: {what} at {where}. {howToFix}";
}
```
The existing test convention (`DG/tests/DG.Tests/ErrorMessageTemplateTests.cs`, read directly) asserts `Contains(paramOrContext)`, `Contains(": ")`, and `EndsWith(".")` for every template — the new `ShaclViolation` test should follow the identical `[Theory]`/`[InlineData]` structure already used for `SerializationFailed`/`ReinstatementBlocked`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `run_shacl()` validates against an empty placeholder `Graph()`, returns only `{conforms: true, results: []}` | `run_shacl()` loads `ontology/dg-shapes.ttl`, returns structured per-result findings with severity | This phase (823) | The entire point of the phase — 821 explicitly deferred this |
| `ontology_export.build_graph()` mints Metagraph/OntoGraph individuals with no `owl:AllDifferent` | Every SHACL-validated export batch (including the Metagraph individuals already minted) gains a UNA declaration | This phase (823), per spec's explicit forward-looking normative requirement | Prevents a reasoner/validator from silently merging distinct Neo4j nodes exported as OWL individuals |
| `ValidationPublishResponse` (C#) has no field for non-SWRL findings | Gains a `Shacl` nested DTO | This phase (823) | First non-SWRL validation channel surfaced through the VALIDATOR component |

**Deprecated/outdated:**
- The 821 code comment "Deliberately empty placeholder shapes graph — Phase 823 swaps this for real SHACL shapes" (in `run_shacl()`) must be removed this phase per CONTEXT.md's explicit callout — leaving it would falsely signal the swap never happened.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommended orange (`#e88a00`-family) and yellow (`#c9a000`-family) hex values for the new `--color-warning`/`--color-info` tokens | Pitfall 2 / Recommended Project Structure | Low — these are starting-point suggestions only; exact values are explicitly Claude's/planner's discretion per CONTEXT.md, and any WCAG-AA-passing warm-orange/yellow pair on the existing paper/ink surfaces satisfies the requirement |
| A2 | `DG_SHACL_HTTP_TIMEOUT_SECONDS` ~15s as the data-service-side httpx read timeout for the new proxy call | Code Examples | Low-Medium — if real `dg-shapes.ttl` shapes + a large ABox genuinely need more than 15s to validate, this timeout would trigger false "unavailable" states on real (not slow-network) work; the planner should treat this as a starting default, verify against actual `run_shacl()` wall-clock time on a representative project during implementation, and adjust if needed (CONTEXT.md explicitly leaves exact timeout values to Claude's discretion) |

## Open Questions (RESOLVED)

> All three questions were resolved at plan time (2026-07-12); each recommendation was adopted as a binding decision in the Phase 823 plan set.

1. **RESOLVED: single shared session** (Plan 823-02 passes the one session owned by `run_shacl()` into both `build_graph()` and `build_valid_graph()`). **Does the sidecar's Neo4j session (already opened for `build_graph`) need a second round-trip for the run-scoped `ValidationRun.statePayloadJson` fetch, or can both queries share one session?**
   - What we know: `run_shacl(project, session=None)` already opens/owns a session when none is injected (`owns_session` pattern in `reasoning.py`). Both `build_graph()` and the new `build_valid_graph()` accept the same duck-typed session contract.
   - What's unclear: Whether to fetch the `ValidationRun` node in the same session as the Metagraph/OntoGraph export or open a second short-lived one.
   - Recommendation: Reuse the single session already opened by `run_shacl()` for both calls — no reason to open two bolt sessions for one request; pass the same `session` object into both `build_graph()` and `build_valid_graph()`.

2. **RESOLVED: plain data-graph union, no `ont_graph=`** (adopted in Plan 823-02 — D-08's SHACL Core constraints need no OWL subsumption). **Should `pyshacl.validate()`'s `ont_graph=` parameter be used to union the static TBox for vocabulary resolution during SHACL validation, or should the TBox simply be merged into the data graph before calling validate (plain union)?**
   - What we know: `pyshacl.entrypoints.validate()` accepts an `ont_graph` kwarg specifically for this purpose (confirmed in the installed source); CONTEXT.md explicitly leaves this to Claude's discretion, noting "pick what pySHACL handles cleanly."
   - What's unclear: Whether DG's shapes (D-08 scope: data-integrity only, e.g. `kind` enum membership, required-property presence) actually need any TBox-level class hierarchy resolution at all — SHACL Core constraints like `sh:in`, `sh:minCount`, `sh:datatype` operate directly on RDF term values and don't require OWL subsumption reasoning.
   - Recommendation: Start with a plain data-graph union (Metagraph/OntoGraph export ∪ ValidGraph ABox, no TBox), since D-08's shape list doesn't appear to need class-hierarchy-aware targeting (`sh:targetClass dgv:Run` matches on `rdf:type dgv:Run` directly, no subsumption needed). Only reach for `ont_graph=` if a specific shape genuinely requires TBox-derived class membership.

3. **RESOLVED: the recommended envelope below was adopted verbatim as the canonical contract pinned in Plan 823-02** (`{status, conforms, results[], counts}`, `results` as the array key). **What is the exact `shaclReportJson` envelope shape stored on `ValidationRun` and returned in the publish response?**
   - What we know: D-06 says "same pattern as `rulesJson`/`statePayloadJson`" (a JSON string column); D-10 specifies the per-result shape `{severity, what, where, howToFix, focusLabel, shapeId}`; D-17 requires a distinguishable "not checked" state for pre-823 runs (absent/null `shaclReportJson`) vs. a "conforms" positive state for an empty-violations report.
   - What's unclear: The exact top-level envelope key names (`status`, `conforms`, `results`/`findings`, `countsBySeverity` — all explicitly left to Claude's discretion per CONTEXT.md).
   - Recommendation: `{"status": "ok"|"unavailable"|"timeout", "conforms": bool|null, "results": [{"severity","what","where","howToFix","focusLabel","shapeId"}], "counts": {"violation": n, "warning": n, "info": n}}`. Absent/null `shaclReportJson` on a run → UI shows "not checked" (D-17); `status !== "ok"` → UI shows unavailable/timeout state distinctly from both "not checked" and "conforms"; `status === "ok" && counts.violation === 0 && counts.warning === 0 && counts.info === 0` → positive "conforms" state (D-18).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pySHACL | SHACL validation in dg-reasoner | ✓ | 0.40.0 (installed on this machine, matches repo pin) | — |
| rdflib | RDF graph construction/SH namespace | ✓ | 7.6.0 (implied by pySHACL's declared range; not directly probed as a standalone package on this machine but same pin as Phase 821) | — |
| Docker / docker-compose | Running dg-reasoner + data-service + neo4j to test end-to-end | Not probed this session (research is read-only; STATE.md confirms images were rebuilt during Phase 821 execution) | — | Unit-tier tests (`test_routes.py`-style monkeypatched tests) require no Docker; only the live integration round-trip does |
| Live Neo4j with `v8-ui-smoke`/similar validation-run data | Testing the run-scoped ABox export against real `statePayloadJson` | Not probed this session | — | Fixture-backed unit tests (per 821 D-13's two-tier strategy) cover the no-live-DB case |

No missing dependencies block planning; all required Python packages are already pinned and installed from Phase 821.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (dg-reasoner, data-service) | pytest (already configured; `dg-reasoner/requirements.txt` pins `pytest`; `data-service/requirements.txt` pins `pytest`) |
| Framework (DG.Core/DG.Grasshopper) | xUnit (`DG/tests/DG.Tests`, existing) |
| Framework (ui-v2) | None configured — no test script in `ui-v2/package.json` (confirmed via grep); UI verification for this phase is manual/UAT per the existing project convention |
| Config file | `dg-reasoner/tests/conftest.py` (registers `integration` marker + `neo4j_available()` skip helper); `data-service/tests/conftest.py` (not read this session, presumed analogous) |
| Quick run command | `cd dg-reasoner && pytest tests/ -m "not integration"` / `cd data-service && pytest tests/` / `dotnet test .\DG\tests\DG.Tests\` (needs `DOTNET_ROLL_FORWARD=LatestMajor` per STATE.md blockers) |
| Full suite command | `cd dg-reasoner && pytest tests/` (includes `@pytest.mark.integration`, requires live docker Neo4j) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHCL-01 | ValidGraph ABox export mints correct dgv: individuals from a v2 envelope fixture | unit | `pytest dg-reasoner/tests/test_valid_graph_export.py -x` | ❌ Wave 0 |
| SHCL-01 | `run_shacl` with `run_id` unions ABox + Metagraph/OntoGraph, includes owl:AllDifferent | unit | `pytest dg-reasoner/tests/test_reasoning.py -k shacl -x` | ❌ Wave 0 (extend or create) |
| SHCL-01 | Backward-compat: `run_shacl` without `run_id` still returns 821 contract shape | unit | `pytest dg-reasoner/tests/test_routes.py -k shacl -x` | ✅ (existing `test_shacl_validate_returns_empty_shapes_contract` — must still pass with the new code path when `run_id` omitted; extend for the new-contract case) |
| SHCL-01 | Non-fatal SHACL proxy call in `publish_validation` never raises when sidecar unreachable/timeout | unit | `pytest data-service/tests/test_shacl_proxy.py -x` | ❌ Wave 0 |
| SHCL-02 | `pyshacl.validate(..., allow_infos=True, allow_warnings=True)` prevents Info/Warning from flipping `conforms` | unit | `pytest dg-reasoner/tests/test_reasoning.py -k allow_warnings -x` | ❌ Wave 0 |
| SHCL-02 | `ErrorMessageTemplates.ShaclViolation` produces What+Where+How-to-fix formatted string | unit | `dotnet test DG/tests/DG.Tests --filter ShaclViolation` | ❌ Wave 0 |
| SHCL-02 | `ValidationPublishResponse` round-trip-deserializes a `Shacl` block from JSON | unit | `dotnet test DG/tests/DG.Tests --filter ValidationPublishResponse` | ❌ Wave 0 |
| SHCL-02 | Severity → GH runtime message level never uses `Error` for SHACL findings | unit/manual | `dotnet test DG/tests/DG.Tests --filter ValidatorComponent` (if a GH-SDK-gated test harness exists) or manual GH canvas check | ❌ Wave 0 / manual-only fallback (ValidatorComponent.cs is `#if GRASSHOPPER_SDK`-gated, may not be unit-testable outside a live GH host) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -m "not integration"` in the touched service directory; `dotnet test` for C# changes.
- **Per wave merge:** Full pytest suite (including `@pytest.mark.integration` where live Neo4j is available) + full `dotnet test`.
- **Phase gate:** Full suite green before `/gsd-verify-work`; UI section requires manual UAT per ui-v2's existing no-test-framework convention.

### Wave 0 Gaps
- [ ] `dg-reasoner/tests/test_valid_graph_export.py` — covers SHCL-01 ABox translation from a fixture v2 envelope
- [ ] `dg-reasoner/tests/fixtures/valid_graph_fixture.json` — a small hand-built `ValidationRun`-shaped fixture (mirrors existing `metagraph_fixture.json`) with at least one ObjState, one ParamState, one PropState
- [ ] `data-service/tests/test_shacl_proxy.py` — covers the non-fatal proxy call's three failure modes (unreachable/timeout/success)
- [ ] `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` extension — `ShaclViolation` test cases, following the existing `[Theory]` pattern
- [ ] `ontology/dg-shapes.ttl` — the shapes file itself is also a test fixture in the sense that `test_reasoning.py`'s unit tests need a small in-memory shapes graph (not necessarily the full production file) to exercise severity mapping without a live Neo4j/Docker dependency

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase adds no new auth surface — SHACL validation is an internal sidecar-to-sidecar call on the existing docker network, same trust boundary as the existing `/reasoner/consistency` proxy |
| V3 Session Management | No | Not applicable |
| V4 Access Control | No | No new access-control surface; `/shacl/validate` remains internal-only (821 D-12, no nginx route, no host port) |
| V5 Input Validation | Yes | `run_id` is a new optional request field on `POST /shacl/validate` — validate it's a non-empty string when present (Pydantic's `str \| None` type already rejects non-string JSON values); the Cypher fetch for `ValidationRun` by `{project, runId}` uses parameterized Cypher (`$project`, `$runId`) exactly like all existing queries in this codebase — never string-interpolate `run_id` into Cypher |
| V6 Cryptography | No | No new cryptographic surface |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via `run_id` | Tampering | Parameterized Cypher queries (`$runId`), already the established pattern throughout `app.py`/`ontology_export.py` — never string-format `run_id` into a query string |
| SHACL shapes file tampering (someone edits `ontology/dg-shapes.ttl` to weaken data-integrity checks) | Tampering | Version-controlled, code-reviewed file (D-07); the read-only `:ro` volume mount prevents the running container from writing back, but does not prevent a compromised host from editing the source file — out of scope for this phase (matches 821's existing trust model for `dg-disjointness.ttl`) |
| Information disclosure: raw SHACL/RDF vocabulary or focus-node IRIs (which embed `project` names and internal entity IDs) leaking to the UI | Information Disclosure | D-10's structured mapping (`{severity, what, where, howToFix, focusLabel, shapeId}`) is itself the mitigation — never pass the raw `results_graph` or raw IRIs through to any HTTP response consumed by the frontend; this is already an explicit out-of-scope item in `.planning/REQUIREMENTS.md`'s "Out of Scope" table ("Exposing raw SHACL/RDF validation report JSON in the UI") |
| Denial of service via a pathological/adversarial SHACL shapes file or ABox causing pySHACL to hang | Denial of Service | Already mitigated by the existing `_run_shacl_with_timeout`'s spawn+killpg subprocess isolation pattern (821); this phase must preserve that wrapper around the real-shapes call, not bypass it for convenience |

## Sources

### Primary (HIGH confidence)
- `dg-reasoner/reasoning.py`, `dg-reasoner/ontology_export.py`, `dg-reasoner/app.py`, `dg-reasoner/tests/test_routes.py`, `dg-reasoner/tests/conftest.py` — read directly, current state of the Phase 821 plumbing this phase extends
- Installed pySHACL 0.40.0 source (`pyshacl/entrypoints.py`, `pyshacl/shape.py`, `pyshacl/validator_conformance.py`, `pyshacl/consts.py`) at `C:\Users\Admin\AppData\Roaming\Python\Python314\site-packages\pyshacl\` — read directly, confirms `validate()` signature, `(conforms, results_graph, results_text)` return shape, and the `allow_infos`/`allow_warnings` severity-to-conforms logic
- Installed rdflib 7.6.0's `SH` DefinedNamespace (`rdflib/namespace/_SH.py`) — read directly, confirms all needed SHACL vocabulary term names are available as public rdflib API
- `data-service/app.py` (relevant sections: `ValidationPublishRequest`, `store_validation_run`, `get_validation_run`, `_project_state_summary`, `list_validation_runs`, `build_view_payload`, `publish_validation`, `post_reasoner_consistency`) — read directly
- `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` — read directly, the authoritative v2 envelope shape
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs`, `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` — read directly, house style + test convention
- `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs`, `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs`, `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs` — read directly
- `ui-v2/src/screens/ModelScreen.jsx`, `ui-v2/src/lib/modelApi.js`, `ui-v2/src/screens/ReasonerScreen.jsx`, `ui-v2/src/styles/tokens/colors.css`, `ui-v2/src/components/display/Chip.jsx` — read directly, confirms no severity color tokens exist yet
- `spec/LPG-OWL-MAPPING.md` (full document) — read directly, the normative mapping contract
- `.planning/phases/821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation/821-CONTEXT.md` — read directly
- `cypher_template.txt` (DesignState/Run section, L50-67) — read directly, confirms document-only status
- `.planning/research/STACK.md` — read directly, confirms pinned versions and rationale from Phase 821's own research

### Secondary (MEDIUM confidence)
- None — all technical claims in this document were verified directly against installed package source or repository code, not web search.

### Tertiary (LOW confidence)
- A2 (SHACL proxy timeout default of ~15s) is a reasoned estimate, not empirically measured against this specific ABox/shapes combination — flagged in Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, versions confirmed against the actually-installed pySHACL 0.40.0/rdflib 7.6.0 on this machine
- Architecture: HIGH — every integration point (data-service proxy, C# DTO, ModelScreen slot) verified by direct source read, not inferred
- Pitfalls: HIGH — the `allow_infos`/`allow_warnings` gotcha and the missing color-token gap were both discovered by direct source inspection, not training-data assumption; these are the two findings most likely to be missed by a planner working from CONTEXT.md alone

**Research date:** 2026-07-12
**Valid until:** 30 days (stable internal codebase; pySHACL/rdflib pins unchanged since Phase 821, no fast-moving external dependency in this phase's scope)
