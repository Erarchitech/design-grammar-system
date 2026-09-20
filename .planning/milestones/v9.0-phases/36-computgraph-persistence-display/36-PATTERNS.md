# Phase 36: Computgraph Persistence and Graph Layer Display - Pattern Map

**Mapped:** 2026-07-19
**Files analyzed:** 8 new/modified
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `data-service/app.py` (+`POST /computgraph/publish` route) | route (thin controller) | request-response | `app.py` `pull_computgraph_context`/`post_computgraph_recognize` (lines 1276-1330) | exact |
| `data-service/computgraph_publish.py` (NEW) | service (domain module) | CRUD (write, MERGE-idempotent) | `data-service/dg_identity.py` (module split + `compute_dg_id`/`mint_identity` shape) | exact |
| `data-service/tests/test_computgraph_publish.py` (NEW) | test | request-response (duck-typed) | `data-service/tests/test_dg_identity.py` (`FakeGraph`/`FakeResult` fixture) | exact |
| `DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs` (NEW) | component (GH_Component) | event-driven (rising-edge trigger) | `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` | role-match (trigger shape); NOT role-match for network (see Shared Patterns) |
| `DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs` (NEW) | service (HTTP client) | request-response (outbound POST) | `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` | exact |
| `DG/src/DG.Grasshopper/Validation/ComputgraphPublishContract.cs` (NEW) | model (DTO) | request-response | `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs` | exact |
| `ui-v2/src/graph/buildRings.js` (EDIT) | utility (pure transform) | transform | itself (existing `LAYER_ORDER`/`ORBITS`/`CAPTIONS` tables) | exact — edit in place |
| `ui-v2/src/screens/GraphScreen.jsx` (EDIT — `rowsOf`) | component (React screen) | transform (display truncation) | itself (existing `rowsOf` at line 690) | exact — edit in place |
| Schema-propagation docs (`cypher_template.txt`, `dataset_schema.json`, `spec/DATABASE.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `README.md`, `config.template.js`, `ontology/dg-shapes.ttl`) | config/docs | batch | `.planning/milestones/v9.0-phases/32.1-cross-platform-identity-and-mapping-dg-id/32.1-07-SUMMARY.md` (file-by-file precedent) | role-match |

## Pattern Assignments

### `data-service/app.py` — `POST /computgraph/publish` (route, request-response)

**Analog:** `data-service/app.py` lines 1272-1330 (`pull_computgraph_context`, `post_computgraph_recognize`)

**Thin-route delegation pattern** (verified, lines 1296-1330):
```python
class RecognizeRequest(BaseModel):
    cg_context: dict
    procedure_index: int | None = None
    project: str | None = None


@app.post("/computgraph/recognize")
def post_computgraph_recognize(payload: RecognizeRequest):
    try:
        return cg_recognition.recognize_structure(payload.cg_context, payload.procedure_index)
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check the submitted cg_context shape (cgContextJson v1 envelope).",
            "RECOGNIZE_REQUEST_INVALID",
            422,
        )
    except Exception as exc:
        error_msg, hint, code = map_provider_error(exc)
        raise _structured_error_response(error_msg, hint, code, 502)
```

**Apply directly to the new route:**
```python
class ComputgraphPublishRequest(BaseModel):
    project: str
    cg_context: dict


@app.post("/computgraph/publish")
def post_computgraph_publish(payload: ComputgraphPublishRequest):
    try:
        with driver.session() as session:
            return computgraph_publish.publish_structure(session, payload.project, payload.cg_context)
    except ValueError as exc:
        raise _structured_error_response(
            str(exc),
            "Check the submitted cg_context shape (cgContextJson v1 envelope).",
            "COMPUTGRAPH_PUBLISH_REQUEST_INVALID",
            422,
        )
```

**Error factory to reuse verbatim** (`app.py` lines 588-593):
```python
def _structured_error_response(error: str, hint: str, code: str, status_code: int = 500) -> HTTPException:
    """Return an HTTPException with a structured JSON detail body (error, hint, code)."""
    return HTTPException(
        status_code=status_code,
        detail={"error": error, "hint": hint, "code": code},
    )
```
Do not redefine — import/use the module-level `app.py` function.

**Session pattern** (`write_query`/`read_single` helpers, lines 300-314) — for the NEW module use raw `session.run(...)` directly (not `write_query`, which opens its own `with driver.session()` — the route must own the session so the whole publish is one transaction):
```python
def write_query(query: str, parameters: dict[str, Any] | None = None) -> None:
    with driver.session() as session:
        session.run(query, parameters or {}).consume()
```
Route opens `with driver.session() as session:` itself (as `pull_computgraph_context`/`identity/mint` already do) and passes `session` into `computgraph_publish.publish_structure(session, ...)` — this is the one place `write_query`'s convenience wrapper must NOT be used, because it would open a second/separate transaction (see Pitfall 3 in RESEARCH.md, `store_validation_run`'s 2-call anti-pattern).

---

### `data-service/computgraph_publish.py` (NEW — service/domain module, CRUD)

**Analog:** `data-service/dg_identity.py` (module docstring shape, `compute_dg_id`, MERGE-key discipline, `DgIdentityError`)

**Module split + docstring convention** (lines 1-37 of `dg_identity.py`):
```python
"""Cross-platform identity registry — dgId minting, native-id <-> dgId resolution, binding.
...
Security: every ``session.run`` receives parameters as a dict — identity strings
(``native_id`` / ``dg_id`` / ``project`` / ``platform``) are NEVER f-string / ``%`` /
``.format`` interpolated into query text (T-32.1-03a: Cypher injection).
"""
from __future__ import annotations
import hashlib
from typing import Any
from pydantic import BaseModel, field_validator
```
`computgraph_publish.py` should open with the same docstring shape (module purpose, security note on parameterized queries) and the same `Any`-typed duck-typed `session` first-arg convention used throughout `dg_identity.py`'s helpers (`def mint_identity(session: Any, project: str, ...)`).

**dgId computation — call the PURE function only, never `mint_identity`** (lines 52-63):
```python
def compute_dg_id(project: str, definition_id: str, cg_id: str) -> str:
    """Mint a deterministic dgId from the pipe-joined triple ``project|definitionId|cgId``.
    ...
    """
    input_str = f"{project}|{definition_id}|{cg_id}"
    digest = hashlib.sha256(input_str.encode("utf-8")).hexdigest().upper()
    return DGID_PREFIX + digest[:16]
```
Import `from dg_identity import compute_dg_id` and call it inline per entity — do NOT call `mint_identity()` (its `MERGE (e {cgId, definitionId, project})` is label-less and will duplicate against a labeled `MERGE (n:Pattern {...})`; see RESEARCH.md Pitfall 1). Set the returned string as a plain `dgId` property inside the SAME labeled `MERGE`.

**MERGE-idempotent write shape to mirror** (`upsert_integration_config`, lines 428-450, and `bind_representation`'s MERGE+SET split, lines 254-273):
```python
def upsert_integration_config(project: str, payload: SpeckleProjectConfigPayload) -> SpeckleProjectConfigPayload:
    payload = normalize_speckle_project_config_payload(payload)
    write_query(
        """
        MERGE (cfg:IntegrationConfig {graph:$graph, provider:'Speckle', project:$project})
        SET
            cfg.speckleProjectId = $speckleProjectId,
            ...
            cfg.updatedAt = $updatedAt
        """,
        {...},
    )
```
Apply the same `MERGE (n:Label {key1:$k1, key2:$k2, project:$project}) SET n.prop = $val, ...` shape per entity type, chained via `WITH`/`UNWIND` into ONE statement (per CONTEXT.md's transactional constraint — do not split into multiple `session.run()` calls the way `store_validation_run` does).

**Behavior-node synthesis (no cgId/dgId, single MERGE key):**
```python
MERGE (b:Behavior {definitionId:$definitionId, project:$project})
SET b.graph = 'Computgraph', b.project = $project, b.publishedAt = $publishedAt
MERGE (o)-[:HAS_BEHAVIOR]->(b)
```

**Error type to mirror** (`DgIdentityError`, lines 75-87):
```python
class DgIdentityError(Exception):
    def __init__(self, message: str, code: str = "DGID_ERROR", existing_dg_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.existing_dg_id = existing_dg_id
```
If `computgraph_publish.py` needs a domain exception (e.g. malformed envelope), raise plain `ValueError` instead (matches `cg_recognition.recognize_structure`'s contract, which the new route's `except ValueError` branch already expects) rather than inventing a second `*Error` class — no code in this phase needs a `code` attribute beyond the one FastAPI-level 422.

---

### `data-service/tests/test_computgraph_publish.py` (NEW — test, request-response)

**Analog:** `data-service/tests/test_dg_identity.py` lines 44-67 (`FakeResult`/`FakeGraph`)

```python
class FakeResult:
    """Duck-types the slice of neo4j.Result the helpers use: .single() + iteration."""
    def __init__(self, rows: list[dict]):
        self._rows = list(rows)
    def single(self):
        return self._rows[0] if self._rows else None
    def __iter__(self):
        return iter(self._rows)


class FakeGraph:
    """Stateful in-memory registry keyed by the `op=` tag on each Cypher statement.
    Records every (op, query, params) call so tests can assert bound-parameter
    and no-untagged-write contracts.
    """
    def __init__(self):
        self.entity_by_dgid: dict[tuple[str, str], bool] = {}
        self.reps: list[dict] = []
```
Extend with a Computgraph-shaped in-memory store (nodes keyed by `(label, cgId|definitionId, project)`) driven by the same `op=` comment convention already used in `dg_identity.py`'s Cypher strings (`// op=MINT`, `// op=BIND`) — add `// op=PUBLISH` tags to the new module's Cypher so the fixture can dispatch on them. Reuse the golden vector `(p1, frame.gh, cg:1:proc:11_Proc) -> dg:BC8E62EE137E2B56` from `test_dg_identity.py` for the dgId-parity unit test.

---

### `DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs` (NEW — service, request-response)

**Analog:** `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` (full file, 146 lines)

**Static HttpClient + camelCase JSON + error-throwing shape** (lines 15-64, 132-138):
```csharp
internal static class ValidationPublishClient
{
    private static readonly HttpClient HttpClient = new();
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    public static ValidationPublishResponse Publish(... string dataServiceUrl, ...)
    {
        var request = BuildRequest(...);
        var endpoint = $"{NormalizeUrl(dataServiceUrl)}/validation/publish";
        using var response = HttpClient.PostAsJsonAsync(endpoint, request, JsonOptions).GetAwaiter().GetResult();
        var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException($"Validation publish failed ({(int)response.StatusCode}): {body}");
        }
        var parsed = JsonSerializer.Deserialize<ValidationPublishResponse>(body, JsonOptions);
        if (parsed is null)
        {
            throw new InvalidOperationException("Validation publish failed: backend returned an empty response.");
        }
        return parsed;
    }

    private static string NormalizeUrl(string dataServiceUrl)
    {
        var normalized = string.IsNullOrWhiteSpace(dataServiceUrl)
            ? "http://localhost:8000"
            : dataServiceUrl.Trim();
        return normalized.TrimEnd('/');
    }
}
```

**Conditional-compilation wrapper (mandatory — every GH-dependent file in this repo has this):**
```csharp
#if GRASSHOPPER_SDK
... real implementation ...
#else
namespace DG.Grasshopper.Validation;
internal static class ComputgraphPublishClient
{
}
#endif
```

**Apply for `ComputgraphPublishClient.Publish(string cgContextJson, string project, string dataServiceUrl)`:** mirror the `Publish(...)` method exactly, POST to `{NormalizeUrl(dataServiceUrl)}/computgraph/publish`, same try/status-check/deserialize/throw shape. `RESEARCH.md`'s own Code Examples section already has this drafted verbatim — copy that shape.

---

### `DG/src/DG.Grasshopper/Validation/ComputgraphPublishContract.cs` (NEW — model/DTO)

**Analog:** `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs` (full file, 113 lines)

**DTO shape convention** (lines 1-27, 86-106):
```csharp
#if GRASSHOPPER_SDK
using DG.Core.Validation;

namespace DG.Grasshopper.Validation;

internal sealed class ValidationPublishRequest
{
    public string Project { get; init; } = "default-project";
    public string? StatePayloadJson { get; init; }
    public List<bool>? ValidStatus { get; set; }
    public List<ValidationPublishRulePayload> Rules { get; } = new();
    ...
}

internal sealed class ValidationPublishResponse
{
    public string Status { get; init; } = string.Empty;
    public string RunId { get; init; } = string.Empty;
    ...
}
#else
namespace DG.Grasshopper.Validation;
internal sealed class ValidationPublishRequest
{
}
#endif
```
`ComputgraphPublishContract.cs` needs only two DTOs: `ComputgraphPublishRequest { string Project; JsonElement CgContext }` and `ComputgraphPublishResponse { string Status; List<string> StaleEntityIds; ... }` — far smaller than the validation contract (no geometry/rules nesting), but same `internal sealed class` + `#if GRASSHOPPER_SDK`/`#else` stub convention.

---

### `DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs` (NEW — component, event-driven)

**Analog (trigger/rising-edge shape only):** `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` lines 1-80

**Rising-edge trigger pattern** (lines 24, 57-80):
```csharp
private bool _lastApply = true; // true prevents first-solve auto-fire (ParameterReinstate precedent)
private string _status = "Idle";

protected override void SolveInstance(IGH_DataAccess da)
{
    var applyInput = false;
    da.GetData(2, ref applyInput);

    // Rising-edge detection: _lastApply starts true so first solve with Apply=true does
    // NOT auto-fire (mirrors ParameterReinstateComponent's _lastApplyInput).
    var isRisingEdge = applyInput && !_lastApply;
    _lastApply = applyInput;

    if (isRisingEdge)
    {
        ApplySelection(acceptIds, rejectIds);
    }

    da.SetDataList(0, DescribePending());
    da.SetData(1, _status);
}
```
Apply the identical `_lastApply`/rising-edge idiom to a `Publish` boolean input on the new component. Component header conventions to copy: fresh-GUID comment (`// Fresh GUID -- verified unused via repo-wide grep across Components/.`), `DgComponentCategory.Category`/`ActionsSubcategory`, `protected override Bitmap Icon => DgIcons.<Name>24;`.

**Do NOT copy the network-free invariant from `StructureConfirmComponent`** — that component has a grep-enforced zero-HttpClient/zero-Neo4j test (`grep -cE 'HttpClient|data-service|neo4j|Neo4j' StructureConfirmComponent.cs == 0`). `ComputgraphPublishComponent` is the one place a network call belongs; wire canvas re-extraction (`CanvasContextExtractor.ExtractRaw()` → `CanvasAnnotationParser.Parse()` → `CgContextDgIdAssigner.AssignDgIds()` → `ComputgraphContextSerializer.Serialize()`) then call `ComputgraphPublishClient.Publish(...)` inside `SolveInstance` on the rising edge, following `ValidationPublishClient`'s call-site shape from wherever `ValidatorComponent`/similar currently invokes `ValidationPublishClient.Publish(...)`.

---

### `ui-v2/src/graph/buildRings.js` (EDIT — utility, transform)

**Analog:** itself — existing `LAYER_ORDER`/`ORBITS`/`CAPTIONS` tables (lines 8, 12-19, 22-45)

**Current (buggy) state, verified by direct read:**
```javascript
const LAYER_ORDER = ["OntoGraph", "Metagraph", "KnowledgeGraph", "SpecGraph", "ComputGraph", "ValidGraph"];
...
const ORBITS = {
  ...
  ComputGraph: { Pattern: 0, Parameter: 1, Interface: 2 },
  ValidGraph: { ... }
};
const CAPTIONS = { ... }; // no Object/Algorithm/Procedure/Pattern/Parameter/Interface entries currently present under those exact names
```
**Required edit (locked by UI-SPEC.md, verbatim from CONTEXT.md/RESEARCH.md):**
```javascript
const LAYER_ORDER = ["OntoGraph", "Metagraph", "KnowledgeGraph", "SpecGraph", "Computgraph", "ValidGraph"];
...
ORBITS.Computgraph = {
  Object: 0, Behavior: 0, Algorithm: 0,
  Procedure: 1, Pattern: 1,
  Parameter: 2, Interface: 2
};
CAPTIONS.Object = ["objectName"];
CAPTIONS.Algorithm = ["algorithmName"];
CAPTIONS.Procedure = ["procedureName"];
CAPTIONS.Pattern = ["patternName"];
CAPTIONS.Parameter = ["parameterName"];
CAPTIONS.Interface = ["interfaceName"];
// Behavior: no entry — intentional fallthrough to captionOf()'s generic fallback
```
Fix the casing exactly in place (`"ComputGraph"` → `"Computgraph"`, same list position between `SpecGraph` and `ValidGraph`), remove the stale placeholder `ComputGraph: {...}` orbit entry, add the 7-label orbit map and 6 caption entries as object-literal keys (matching the existing style where `ORBITS.Computgraph = {...}` / `CAPTIONS.X = [...]` are set as top-level keys, not necessarily re-declaring the whole `const` object — follow whichever style keeps the diff minimal against the existing `const ORBITS = {...}` / `const CAPTIONS = {...}` block literals).

`primaryLabel`/`captionOf`/`buildRings()` (lines 49-147) need NO changes — they already generically consume whatever `ORBITS`/`CAPTIONS` tables contain and fall back correctly (`captionOf` line 53-58 already implements the "no caption entry → generic fallback" behavior Behavior needs).

---

### `ui-v2/src/screens/GraphScreen.jsx` (EDIT — component, transform)

**Analog:** itself — existing `rowsOf` at line 690 (single shared function, not two as RESEARCH.md speculated — verified by direct read)

**Current implementation (verified):**
```javascript
const rowsOf = (n, max) => (n ? n.props.slice(0, max).map((p) => ({ key: p[0], value: String(p[1]) })) : []);
```
Called at two sites: `rowsOf(hv, 6)` (hover, line 876) and `rowsOf(se, 24)` (selected/detail panel, line 897) — both go through this ONE function, so the truncation guard is a single-point edit, not two:
```javascript
const rowsOf = (n, max) =>
  (n ? n.props.slice(0, max).map((p) => ({ key: p[0], value: String(p[1]).slice(0, 200) + (String(p[1]).length > 200 ? "…" : "") })) : []);
```
This guards `contextJson` on `Algorithm` nodes (potentially multi-KB) from both the 6-row hover and 24-row detail panel in one change, per UI-SPEC.md's binding contract.

---

## Shared Patterns

### Structured error response (data-service)
**Source:** `data-service/app.py` lines 588-593
**Apply to:** `POST /computgraph/publish` route's `ValueError` branch — code `COMPUTGRAPH_PUBLISH_REQUEST_INVALID`, status 422.
```python
def _structured_error_response(error: str, hint: str, code: str, status_code: int = 500) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": error, "hint": hint, "code": code})
```

### Deterministic dgId, computed inline never minted
**Source:** `data-service/dg_identity.py` lines 52-63 (`compute_dg_id`)
**Apply to:** `computgraph_publish.py` — every entity carrying a `cgId` (Object/Procedure/Pattern/Parameter/Interface). Never call `mint_identity()` from the publish path (label-less MERGE anchor mismatch — see Pitfall 1 in RESEARCH.md).

### Static HttpClient + camelCase JSON GH→data-service publish
**Source:** `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` (whole file)
**Apply to:** `ComputgraphPublishClient.cs` — identical `HttpClient`/`JsonSerializerOptions`/`NormalizeUrl`/status-check/throw shape.

### Rising-edge trigger boolean input
**Source:** `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` lines 24, 68-71 (`_lastApply` idiom)
**Apply to:** `ComputgraphPublishComponent.cs`'s `Publish` input.

### `#if GRASSHOPPER_SDK` / `#else` stub convention
**Source:** every file in `DG/src/DG.Grasshopper/Validation/` and `Components/`
**Apply to:** all 3 new C# files (`ComputgraphPublishComponent.cs`, `ComputgraphPublishClient.cs`, `ComputgraphPublishContract.cs`) — real implementation guarded, empty stub in `#else` so non-Grasshopper builds (net9.0 `DG.Tests`) still compile.

### Schema-propagation checklist file-by-file execution
**Source:** `.planning/milestones/v9.0-phases/32.1-cross-platform-identity-and-mapping-dg-id/32.1-07-SUMMARY.md`
**Apply to:** the Wave/plan covering `cypher_template.txt`, `dataset_schema.json`, `spec/DATABASE.md`, CLAUDE.md schema tables, `.github/copilot-instructions.md`, `README.md`, `config.template.js`, `ontology/dg-shapes.ttl` — follow the same "document-only-comment-block" pattern used for Representation/SharedProperty in that prior phase; also correct the stale `dgId`-on-`:Algorithm` claim at `spec/DATABASE.md` line 113 (RESEARCH.md Pitfall 5).

## No Analog Found

None — every file in this phase's scope has a direct or role-match analog already in the repo (confirmed by RESEARCH.md's "100% composition, no net-new architecture" framing and this session's direct verification of all cited source files).

## Metadata

**Analog search scope:** `data-service/` (app.py, dg_identity.py, tests/test_dg_identity.py), `DG/src/DG.Grasshopper/Components/` and `Validation/`, `ui-v2/src/graph/`, `ui-v2/src/screens/`
**Files scanned (direct read this session):** `data-service/app.py` (lines 300-500, 1260-1440), `data-service/dg_identity.py` (full, 476 lines), `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` (full), `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs` (full), `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` (lines 1-80), `ui-v2/src/graph/buildRings.js` (full, 147 lines), `ui-v2/src/screens/GraphScreen.jsx` (lines 680-700), `data-service/tests/test_dg_identity.py` (lines 44-67)
**Pattern extraction date:** 2026-07-19
