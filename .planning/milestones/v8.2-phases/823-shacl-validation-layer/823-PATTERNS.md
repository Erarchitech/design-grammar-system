# Phase 823: SHACL Validation Layer - Pattern Map

**Mapped:** 2026-07-12
**Files analyzed:** 13
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `dg-reasoner/reasoning.py` (`run_shacl`, `_shacl_worker`, `_run_shacl_with_timeout`) | service | transform (RDF validate) | `dg-reasoner/reasoning.py::run_consistency`/`_reason_worker`/`_reason_with_timeout` (same file, sibling pipeline) | exact |
| `dg-reasoner/valid_graph_export.py` (NEW) | service | transform (Cypher→RDF) | `dg-reasoner/ontology_export.py::build_graph` | exact |
| `ontology/dg-shapes.ttl` (NEW) | config | file-I/O | `ontology/dg-disjointness.ttl` (821 overlay pattern) | exact |
| `dg-reasoner/app.py` (`ShaclRequest`, `shacl_validate`) | route | request-response | same file's `ConsistencyRequest`/`reason_consistency` route | exact |
| `data-service/app.py` (`publish_validation` SHACL call) | controller | request-response (non-fatal proxy) | same file's `post_reasoner_consistency` (~L1174) | exact |
| `data-service/app.py` (`store_validation_run` `shaclReportJson` param) | model/CRUD | CRUD (Cypher MERGE/SET) | same function's existing `rulesJson`/`statePayloadJson` params | exact |
| `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` (`ShaclViolation`) | utility | transform (string formatting) | same file's `PublishFailed`/`ReinstatementBlocked` | exact |
| `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs` (`Shacl` DTO) | model | request-response (DTO) | same file's `ValidationPublishResponse` | exact |
| `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` | component (GH) | event-driven (SolveInstance) | same file, existing publish-response handling block (lines ~110-137) | exact |
| `ui-v2/src/screens/ModelScreen.jsx` (SHACL section) | component | request-response (render from fetched state) | same file's `<Panel title="Validation run">` block (~L885-894) | exact |
| `ui-v2/src/lib/modelApi.js` | service (API client) | request-response | same file's `fetchValidationRuns`/`fetchValidationView` | exact |
| `ui-v2/src/styles/tokens/colors.css` (new warning/info tokens) | config | — | same file's `--color-signal` block | exact |
| `ui-v2/src/components/display/Badge.jsx`, `ui-v2/src/components/surfaces/Collapsible.jsx` (severity variants) | component | — | same files' existing `variant`/`signal` prop patterns | exact |
| `spec/RULE-PARTITION-POLICY.md` (NEW) | docs | — | `spec/LPG-OWL-MAPPING.md` (structure/tone) | role-match |

## Pattern Assignments

### `dg-reasoner/reasoning.py` — extend `run_shacl`/`_shacl_worker`/`_run_shacl_with_timeout` (service, transform)

**Analog:** same file's `run_consistency`/`_reason_with_timeout`/`_reason_worker` (lines 178-264) — the sibling pipeline this phase's SHACL path must mirror in shape.

**Current placeholder to replace** (lines 316-345):
```python
def run_shacl(project: str, session=None) -> dict:
    """Run the real pySHACL pipeline against an empty/placeholder shapes graph (D-11)."""
    owns_session = session is None
    if owns_session:
        session = _get_driver().session()
    try:
        data_graph = ontology_export.build_graph(session, project)
    finally:
        if owns_session:
            session.close()

    # Deliberately empty placeholder shapes graph -- Phase 823 swaps this for
    # real SHACL shapes. Clearly labelled so it's unmistakable in review.
    shapes_graph = Graph()

    result = _run_shacl_with_timeout(data_graph, shapes_graph, DG_REASONER_TIMEOUT_SECONDS)
    if result.get("timeout"):
        return {"conforms": None, "error": "timeout", "timeout_seconds": DG_REASONER_TIMEOUT_SECONDS}

    return {"conforms": result["conforms"], "results": []}
```
Remove the "Deliberately empty placeholder" comment entirely per CONTEXT.md's explicit callout — leaving it signals the swap never happened.

**Worker to extend** (lines 267-282) — currently discards everything but the bool:
```python
def _shacl_worker(data_nt: str, shapes_nt: str, queue: "multiprocessing.Queue") -> None:
    os.setsid()
    try:
        from pyshacl import validate as pyshacl_validate

        conforms, _results_graph, _results_text = pyshacl_validate(
            data_nt,
            shacl_graph=shapes_nt,
            inference="none",
            advanced=False,
        )
        queue.put({"conforms": bool(conforms)})
    except Exception as exc:
        queue.put({"error": f"{type(exc).__name__}: {exc}"})
```
New version must pass `allow_infos=True, allow_warnings=True` (RESEARCH.md Pattern 1 gotcha) and put JSON-serializable structured results, not raw rdflib objects — follow the `_reason_worker` label-enrichment convention below.

**Label-enrichment pattern to reuse verbatim** (lines 127-140, 160-172 — Phase 822's `{iri,label}` local-name-fallback, cited by D-10):
```python
def _local_name(iri: str) -> str:
    if "#" in iri:
        candidate = iri.rsplit("#", 1)[-1]
    elif "/" in iri:
        candidate = iri.rsplit("/", 1)[-1]
    else:
        candidate = iri
    return candidate or iri

# ... in _reason_worker:
owl_nothing = "http://www.w3.org/2002/07/owl#Nothing"
unsatisfiable_by_iri = {}
for cls in inconsistent:
    iri = getattr(cls, "iri", str(cls))
    if iri == owl_nothing:
        continue
    labels = list(getattr(cls, "label", []) or [])
    label = str(labels[0]) if labels and str(labels[0]).strip() else _local_name(iri)
    unsatisfiable_by_iri[iri] = {"iri": iri, "label": label}
```
For SHACL, apply the same `{iri, label}` shape to `focusNode` → `focusLabel`, looking up `rdfs.label` on the focus node in the *data graph* (not results graph) before falling back to `_local_name()`.

**Timeout-bounded subprocess pattern to preserve exactly** (lines 284-313, `_run_shacl_with_timeout`) — spawn context, `os.setsid()`/`os.killpg()`, temp `.nt` file cleanup in `finally`. Do not bypass this wrapper for convenience (Security Domain DoS mitigation in RESEARCH.md).

**New result-walking helper** (per RESEARCH.md Pattern 1, add near `_local_name`):
```python
from rdflib.namespace import SH

def _walk_shacl_results(results_graph) -> list[dict]:
    structured_results = []
    for report in results_graph.subjects(predicate=None, object=SH.ValidationReport):
        for result in results_graph.objects(report, SH.result):
            severity_uri = results_graph.value(result, SH.resultSeverity)
            structured_results.append({
                "severity": {SH.Violation: "violation", SH.Warning: "warning", SH.Info: "info"}
                    .get(severity_uri, "violation"),
                "message": str(results_graph.value(result, SH.resultMessage) or ""),
                "focusNode": str(results_graph.value(result, SH.focusNode) or ""),
                "path": str(results_graph.value(result, SH.resultPath) or ""),
                "sourceShape": str(results_graph.value(result, SH.sourceShape) or ""),
            })
    return structured_results
```

---

### `dg-reasoner/valid_graph_export.py` (NEW, service, transform) — sibling to `ontology_export.py`

**Analog:** `dg-reasoner/ontology_export.py::build_graph` (line 219) and its helpers `mint()`, `make_argument_list()`, `expand_iri()`, `bind_prefixes()`.

**`mint()` pattern to reuse verbatim** (lines 131-133):
```python
def mint(project: str, kind: str, key: str) -> URIRef:
    """Mint a project-scoped IRI: `{BASE}/project/{project}/{kind}/{key}`."""
    return URIRef(f"{BASE}/project/{quote(project, safe='')}/{kind}/{quote(key, safe='')}")
```
New exporter calls `mint(project, "state", state_id)` and `mint(project, "run", run_id)` — zero new logic needed, per RESEARCH.md's Don't-Hand-Roll table.

**`make_argument_list()` pattern to reuse for `Run.ValidStatus` and `owl:AllDifferent`'s `owl:distinctMembers`** (lines 155-171):
```python
def make_argument_list(graph: Graph, terms_in_order: list) -> URIRef | BNode:
    """Build a plain `rdf:List` for a BuiltinAtom's `swrl:arguments`.

    Unlike `swrl:AtomList` cells, argument-list cells carry no extra type --
    this is a bare RDF collection encoding `ARG.pos` order for variable-arity
    builtins (spec #BuiltinAtom and swrl:arguments).
    """
    if not terms_in_order:
        return RDF.nil
    first_cell = BNode()
    cell = first_cell
    for index, term in enumerate(terms_in_order):
        graph.add((cell, RDF.first, term))
        next_cell = BNode() if index < len(terms_in_order) - 1 else RDF.nil
        graph.add((cell, RDF.rest, next_cell))
        cell = next_cell
    return first_cell
```

**Duck-typed session contract to honor** (docstring convention from `reasoning.py` line 26-28): "Every public function accepts an injectable Neo4j-session-shaped `session` argument... so tests can supply a fixture-backed shim." `build_valid_graph(session, project, run_id)` must follow this exact signature shape.

**Label-scoped Cypher to mirror** (RESEARCH.md's suggested query, matching `ontology_export.py`'s `ONTOGRAPH_QUERY`/`METAGRAPH_QUERY` style — label-scoped, never `{graph: 'X'}`-scoped):
```cypher
MATCH (run:ValidationRun)
WHERE run.project = $project AND run.runId = $runId
RETURN run.statePayloadJson AS statePayloadJson,
       run.ValidStatus AS validStatus,
       run.SendStatus AS sendStatus
```

**`owl:AllDifferent` (UNA) construction** (RESEARCH.md Pattern 3, net-new — no existing `OWL.AllDifferent` reference in the codebase):
```python
from rdflib import BNode
from rdflib.namespace import OWL, RDF

def add_all_different(graph: Graph, individuals: list[URIRef]) -> None:
    if not individuals:
        return
    all_diff = BNode()
    graph.add((all_diff, RDF.type, OWL.AllDifferent))
    graph.add((all_diff, OWL.distinctMembers, make_argument_list(graph, individuals)))
```

---

### `ontology/dg-shapes.ttl` (NEW, config, file-I/O)

**Analog:** `ontology/dg-disjointness.ttl` (loaded in `reasoning.py::_hybrid_union` line 98: `union.parse(DG_DISJOINTNESS_PATH, format="turtle")`). Follow the exact same read-only `:ro` volume-mount + module-level `os.getenv(..., "/app/ontology/...")` path pattern (lines 66-67):
```python
DG_OWL_PATH = os.getenv("DG_OWL_PATH", "/app/ontology/DesignGrammar-V7.owl")
DG_DISJOINTNESS_PATH = os.getenv("DG_DISJOINTNESS_PATH", "/app/ontology/dg-disjointness.ttl")
```
Add `DG_SHAPES_PATH = os.getenv("DG_SHAPES_PATH", "/app/ontology/dg-shapes.ttl")` alongside these and `union.parse(DG_SHAPES_PATH, format="turtle")` (or a dedicated `Graph().parse(...)` for the shapes graph, since shapes are NOT unioned into the data/TBox — they are the `shacl_graph=` argument to `pyshacl.validate()`).

---

### `data-service/app.py` — SHACL non-fatal proxy call in `publish_validation` (controller, request-response)

**Analog:** `post_reasoner_consistency` (lines 1168-1210) — the EXACT proxy/timeout template cited by D-01.

```python
class ReasonerConsistencyRequest(BaseModel):
    project: str
    engine: str = "hermit"


@app.post("/reasoner/consistency")
def post_reasoner_consistency(payload: ReasonerConsistencyRequest):
    """Thin proxy to the dg-reasoner sidecar's `POST /reason/consistency` (D-06)."""
    try:
        response = httpx.post(
            f"{DG_REASONER_URL}/reason/consistency",
            json={"project": payload.project, "engine": payload.engine},
            timeout=httpx.Timeout(connect=2.0, read=95.0, write=2.0, pool=2.0),
        )
    except httpx.TimeoutException:
        raise _structured_error_response(
            "Reasoner sidecar request timed out.",
            "The dg-reasoner sidecar is slow or unreachable. Try again later.",
            "REASONER_TIMEOUT",
            504,
        )
    except httpx.ConnectError:
        raise _structured_error_response(
            "Could not connect to the reasoner sidecar.",
            "Verify the dg-reasoner service is running.",
            "REASONER_UNAVAILABLE",
            502,
        )

    try:
        body = response.json()
    except ValueError:
        body = {"detail": response.text}

    return JSONResponse(status_code=response.status_code, content=body)
```

**Critical divergence (D-02 non-fatal):** unlike `post_reasoner_consistency` (which raises `_structured_error_response` — a 502/504 HTTPException — on failure), the new SHACL call inside `publish_validation` must NEVER raise. It must be wrapped so failures degrade to a status dict embedded in the publish response. RESEARCH.md's recommended non-fatal version:
```python
def _call_shacl_validate(project: str, run_id: str) -> dict:
    try:
        response = httpx.post(
            f"{DG_REASONER_URL}/shacl/validate",
            json={"project": project, "run_id": run_id},
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
        return {"status": "unavailable"}
```
Call this from inside `publish_validation` (starts at line 1241) AFTER `store_validation_run` completes (D-01), then persist the result via a second/combined call and include it in the response body.

**`DG_REASONER_URL` already wired** (line 71): `DG_REASONER_URL = os.getenv("DG_REASONER_URL", "http://dg-reasoner:8000")` — reuse as-is, no new env var needed for the base URL (only a new timeout env var, e.g. `DG_SHACL_HTTP_TIMEOUT_SECONDS`).

---

### `data-service/app.py` — `store_validation_run` gains `shaclReportJson` (model, CRUD)

**Analog:** same function's existing `statePayloadJson`/`rulesJson` parameter+Cypher pattern (lines 435-489):
```python
def store_validation_run(
    project: str,
    run_id: str,
    config: SpeckleProjectConfigPayload,
    publish_result: dict[str, str],
    rules_summary: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    state_payload_json: str | None = None,
    valid_status_param: list[bool] | None = None,
) -> None:
    ...
    write_query(
        """
        MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})
        SET
            ...
            run.rulesJson = $rulesJson,
            run.statePayloadJson = $statePayloadJson,
            run.status = 'completed',
            run.ValidStatus = $validStatus,
            run.SendStatus = true,
            run.createdAt = $createdAt
        """,
        {
            "graph": VALIDATION_GRAPH,
            "project": project,
            "runId": run_id,
            ...
            "rulesJson": json.dumps(rules_summary),
            "statePayloadJson": state_payload_json,
            ...
        },
    )
```
Add `shacl_report_json: str | None = None` parameter and `run.shaclReportJson = $shaclReportJson` / `"shaclReportJson": shacl_report_json` — identical shape, same `MERGE`/`SET` Cypher block. Since SHACL runs AFTER `store_validation_run` per D-01, this will need either a second `write_query` `SET` call keyed by `{project, runId}` after the SHACL proxy call returns, or restructuring to call `store_validation_run` after the SHACL call completes — confirm ordering during planning (D-01 says "synchronously after `store_validation_run`", implying a second write).

---

### `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — new `ShaclViolation` (utility, transform)

**Analog:** same file's `PublishFailed`/`ReinstatementBlocked` (lines 24-46) — house style is `{Context}: {what happened}. {how to fix}.`:
```csharp
public static string ReinstatementBlocked(string parameterId, ReinstatementStatus status, string detail)
{
    var fix = status switch
    {
        ReinstatementStatus.MissingTarget => "Reconnect the original slider or toggle.",
        ReinstatementStatus.TypeMismatch => "Reconnect a matching slider or recapture state.",
        ReinstatementStatus.AmbiguousTarget => "Ensure only one slider has this NickName.",
        ReinstatementStatus.OutOfRange => "Adjust slider domain to include the saved value.",
        _ => "Check the parameter connection.",
    };

    return $"Reinstatement blocked: parameter '{parameterId}' {detail}. {fix}";
}

public static string PublishFailed(string project, string errorDetail)
{
    return $"Validation publish failed for project '{project}': {errorDetail}. Check data-service connection and Speckle configuration.";
}
```
New method (from RESEARCH.md's Code Examples section, matches this exact style):
```csharp
public static string ShaclViolation(string severity, string what, string where, string howToFix)
{
    return $"SHACL {severity}: {what} at {where}. {howToFix}";
}
```
**Test convention to follow** (`DG/tests/DG.Tests/ErrorMessageTemplateTests.cs`, existing) — asserts `Contains(paramOrContext)`, `Contains(": ")`, and `EndsWith(".")` for every template. New `[Theory]`/`[InlineData]` test cases for `ShaclViolation` must follow this identical structure.

---

### `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs` — new `Shacl` DTO (model, request-response)

**Analog:** same file's existing `ValidationPublishResponse` (lines 84-97):
```csharp
internal sealed class ValidationPublishResponse
{
    public string Status { get; init; } = string.Empty;
    public string RunId { get; init; } = string.Empty;
    public string ValidationModelId { get; init; } = string.Empty;
    public string ValidationVersionId { get; init; } = string.Empty;
    public string BaseVersionId { get; init; } = string.Empty;
    public string ModelViewerUrl { get; init; } = string.Empty;
}
```
Add a nested `Shacl` property (`ShaclReportPayload? Shacl { get; init; }`) and a new class following the same `{ get; init; } = default` idiom, e.g.:
```csharp
internal sealed class ShaclReportPayload
{
    public string Status { get; init; } = string.Empty;
    public bool? Conforms { get; init; }
    public List<ShaclFindingPayload> Findings { get; } = new();
}

internal sealed class ShaclFindingPayload
{
    public string Severity { get; init; } = string.Empty;
    public string What { get; init; } = string.Empty;
    public string Where { get; init; } = string.Empty;
    public string HowToFix { get; init; } = string.Empty;
    public string FocusLabel { get; init; } = string.Empty;
    public string ShapeId { get; init; } = string.Empty;
}
```
**Deserialization pitfall (RESEARCH.md Pitfall 4):** field names must exactly camelCase-match across dg-reasoner Python dict keys → data-service JSON pass-through → these C# properties (`System.Text.Json` with `JsonNamingPolicy.CamelCase` silently nulls on mismatch, never throws). Pick names once and use identically everywhere: `severity`, `what`, `where`, `howToFix`, `focusLabel`, `shapeId`, `status`, `conforms`, `findings`.

---

### `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` — consume `response.Shacl` (component, event-driven)

**Analog:** same file's existing publish-response handling in `SolveInstance` (lines 110-137):
```csharp
if (sendValid)
{
    try
    {
        var response = ValidationPublishClient.Publish(
            new[] { rule },
            new[] { result },
            bindings,
            dataServiceUrl,
            designState,
            validStatus);
        sendStatus = string.IsNullOrWhiteSpace(response.Status) ? "published" : response.Status;
        validationRunId = response.RunId;
        modelViewerUrl = response.ModelViewerUrl;
    }
    catch (Exception ex)
    {
        sendStatus = $"Publish failed: {ex.Message}";
        AddRuntimeMessage(GH_RuntimeMessageLevel.Error, $"Publish failed: {ex.Message}");
    }
}
```
Extend this block: after `response` is obtained, iterate `response.Shacl?.Findings`, format each via `ErrorMessageTemplates.ShaclViolation(...)`, append to the `Report` output list (currently built at line 104 as `da.SetDataList(3, new[] { ValidationReportFormatter.ToReportLine(result) })`), and call `AddRuntimeMessage` — **capped at `GH_RuntimeMessageLevel.Warning`, never `.Error`** (D-15 hard constraint — publish success must stay visually distinct from data findings; `.Error` is reserved for true component failures like the existing `catch (Exception ex)` block above).

---

### `ui-v2/src/screens/ModelScreen.jsx` — new "SHACL Data Integrity" Panel (component, request-response render)

**Analog:** same file's existing `<Panel title="Validation run">` block (lines 885-894) and the `Collapsible`/`CollapsibleItem` failing/passing-items pattern (lines 895-904):
```jsx
<Panel title="Validation run">
  <KVRow label="Run Id" value={view.runId} />
  <KVRow label="Date Created" value={view.createdAt ? String(view.createdAt).slice(0, 19).replace("T", " ") : "—"} />
  <KVRow label="Base Model" value={view.baseModelId || "—"} />
  <KVRow label="Validation Model" value={view.validationModelId || "—"} />
  <div style={{ display: "flex", gap: 28, marginTop: 10 }}>
    <StatBlock label="Failing" value={String(failItems.length)} signal={failItems.length > 0} />
    <StatBlock label="Passing" value={String(passItems.length)} />
  </div>
</Panel>
<Collapsible label="Failing items" count={failItems.length} signal={failItems.length > 0} open={failOpen} onToggle={() => setFailOpen((v) => !v)}>
  {failItems.map((it) => (
    <CollapsibleItem key={it.id} primary={it.primary} secondary={it.secondary} selected={picked === it.id} onClick={() => pick(it.id)} />
  ))}
</Collapsible>
```
**Insertion point (per 823-UI-SPEC.md, binding UI contract):** new `<Panel title="SHACL Data Integrity">` directly after the "Validation run" Panel's `StatBlock` row, before the "Failing items" `Collapsible`. Four states keyed on `findings.length` (never on a `conforms` boolean — see UI-SPEC's "hard rule"): not-checked (`shaclReport` undefined), unavailable/timeout (`shaclReport.status`), conforms (`findings.length === 0`), findings-present (severity chip summary + per-severity `Collapsible` groups, each finding a 4-line card: `focusLabel` / `what` / `Where: {where}` / `Fix: {howToFix}` — `shapeId` present in data but never rendered).

**`Chip` component to extend for severity chips** (`ui-v2/src/components/display/Chip.jsx`, full file, 32 lines):
```jsx
export default function Chip({ selected = false, onRemove, children, style }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6, height: 26,
      boxSizing: "border-box", borderRadius: "var(--radius-full)", padding: "0 12px",
      font: "500 13px/1 var(--font-sans)",
      background: selected ? "var(--accent-selection-bg)" : "var(--color-paper)",
      color: selected ? "var(--color-signal-ink)" : "var(--color-ink)",
      border: selected ? "1px solid var(--color-signal)" : "1px solid var(--color-hairline)",
      ...style
    }}>
      {children}
    </span>
  );
}
```
UI-SPEC prefers extending `Badge.jsx` (not shown here, referenced in UI-SPEC lines 118-126) with `violation`/`warning`/`info` variants using the new color tokens — follow that spec exactly, it is the binding UI contract for this phase.

---

### `ui-v2/src/lib/modelApi.js` — extend fetch surface (service/API client, request-response)

**Analog:** same file's `fetchValidationRuns`/`fetchValidationView` (lines 25-35):
```js
export function fetchValidationRuns(project) {
  return getJson(`${base()}/validation/runs/${encodeURIComponent(project || "default-project")}`);
}

export function fetchValidationView(project, runId, ruleId) {
  const p = encodeURIComponent(project || "default-project");
  const tail = ruleId ? `/${encodeURIComponent(runId)}/${encodeURIComponent(ruleId)}` : `/${encodeURIComponent(runId)}`;
  return getJson(`${base()}/validation/view/${p}${tail}`);
}
```
Per D-17, `shaclReport` most naturally rides the existing `fetchValidationRuns`/`fetchValidationView` response payloads (data-service embeds `shaclReportJson` parsed into the response body) — likely **zero new exported function needed** in `modelApi.js`, only a data-service response-shape change consumed by `ModelScreen.jsx`'s existing `view` state. Confirm during planning which endpoint (`/validation/runs/{project}` list vs `/validation/view/*`) the Model screen consumes for the selected-run detail (it currently uses `fetchValidationView` for `view` — see `ModelScreen.jsx` line 883 `propMode === "run" && view`).

---

### `ui-v2/src/styles/tokens/colors.css` — new severity tokens (config)

**Analog:** existing `--color-signal` family (lines 23-28, `:root`; lines 75-78, dark mode):
```css
/* The one chromatic hue — Signal Red. Spent only on selection,
   failure, and destructive affordances (DSYS-01). */
--color-signal: #e7000b;
--color-signal-ink: #b8000e;              /* selected text/labels on light surfaces */
--color-signal-soft: rgba(231, 0, 11, 0.08);  /* selection wash */
--color-signal-mid: rgba(231, 0, 11, 0.32);   /* selection ring, node halos */
```
Dark-mode override:
```css
--color-signal: #ff3b44;
--color-signal-ink: #ff7079;
--color-signal-soft: rgba(255, 59, 68, 0.14);
--color-signal-mid: rgba(255, 59, 68, 0.4);
```
**Exact new tokens to add** (per 823-UI-SPEC.md, binding — do not deviate from these hex values without design review):
```css
/* :root block, immediately after the Signal Red block */
--color-warning: #d97706;
--color-warning-ink: #b45309;
--color-warning-soft: rgba(217, 119, 6, 0.10);

--color-info: #ca8a04;
--color-info-ink: #854d0e;
--color-info-soft: rgba(202, 138, 4, 0.10);

/* :root[data-theme="dark"] block */
--color-warning: #fb923c;
--color-warning-ink: #fdba74;
--color-warning-soft: rgba(251, 146, 60, 0.16);

--color-info: #facc15;
--color-info-ink: #fde047;
--color-info-soft: rgba(250, 204, 21, 0.16);
```

## Shared Patterns

### Non-fatal sidecar proxy with explicit short timeout
**Source:** `data-service/app.py::post_reasoner_consistency` (lines 1168-1210)
**Apply to:** the new SHACL proxy call in `publish_validation` — same `httpx.post(DG_REASONER_URL + ..., json=..., timeout=httpx.Timeout(...))` shape, but MUST catch-all and return a status dict instead of raising (D-02 non-fatal constraint; contrast with the reasoner-consistency route which does raise `_structured_error_response`).

### Timeout-bounded subprocess isolation (spawn + killpg)
**Source:** `dg-reasoner/reasoning.py::_reason_with_timeout`/`_run_shacl_with_timeout` (lines 178-313, already implemented for SHACL, just needs richer data returned)
**Apply to:** no change to the isolation mechanism itself — only the payload shape `_shacl_worker` puts on the queue changes from `{"conforms": bool}` to the full structured-findings dict.

### `{iri, label}` local-name-fallback enrichment
**Source:** `dg-reasoner/reasoning.py::_local_name` (lines 127-140) + its use in `_reason_worker` (lines 160-172), explicitly cited by D-10 as the pattern to reuse for `focusLabel`.
**Apply to:** `_walk_shacl_results`'s `focusNode` → `focusLabel` resolution.

### What+Where+How-to-fix error message house style
**Source:** `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` (all existing methods, e.g. lines 24-46)
**Apply to:** `ErrorMessageTemplates.ShaclViolation` and its GH surfacing in `ValidatorComponent.cs`.

### Project-scoped IRI minting
**Source:** `dg-reasoner/ontology_export.py::mint` (lines 131-133)
**Apply to:** `valid_graph_export.py`'s `dgv:ObjState`/`ParamState`/`PropState`/`Run` individual IRIs — reuse verbatim with new `kind` values `"state"`/`"run"`.

### Bare `rdf:List` construction
**Source:** `dg-reasoner/ontology_export.py::make_argument_list` (lines 155-171)
**Apply to:** `Run.ValidStatus` boolean list encoding and `owl:AllDifferent`'s `owl:distinctMembers` list.

### Existing sidebar Panel/Collapsible/Chip visual language
**Source:** `ui-v2/src/screens/ModelScreen.jsx` (lines 875-969), `ui-v2/src/components/display/Chip.jsx`
**Apply to:** the new "SHACL Data Integrity" Panel — reuses `Panel`, `Collapsible`, `CollapsibleItem`, `Badge` (extended with new variants), and the new color tokens; zero new spacing/typography values needed per 823-UI-SPEC.md.

## No Analog Found

None — all 13 files/areas have a strong same-file or same-service analog (mostly exact matches, since Phase 821/822 already established every mechanical pattern this phase needs to extend).

## Metadata

**Analog search scope:** `dg-reasoner/`, `data-service/app.py`, `DG/src/DG.Core/Services/`, `DG/src/DG.Grasshopper/Components/` + `Validation/`, `ui-v2/src/screens/`, `ui-v2/src/lib/`, `ui-v2/src/styles/tokens/`, `ui-v2/src/components/display/`
**Files scanned:** `dg-reasoner/reasoning.py`, `dg-reasoner/ontology_export.py`, `dg-reasoner/app.py`, `data-service/app.py`, `DG/src/DG.Core/Services/ErrorMessageTemplates.cs`, `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs`, `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs`, `ui-v2/src/screens/ModelScreen.jsx`, `ui-v2/src/lib/modelApi.js`, `ui-v2/src/styles/tokens/colors.css`, `ui-v2/src/components/display/Chip.jsx`, `.planning/phases/823-shacl-validation-layer/823-UI-SPEC.md` (binding UI contract, read in full)
**Pattern extraction date:** 2026-07-12
