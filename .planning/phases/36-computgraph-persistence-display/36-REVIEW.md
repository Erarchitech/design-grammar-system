---
phase: 36-computgraph-persistence-display
reviewed: 2026-07-19T15:33:17Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - data-service/computgraph_publish.py
  - data-service/app.py
  - DG/src/DG.Grasshopper/Validation/ComputgraphPublishContract.cs
  - DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs
  - DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs
  - DG/src/DG.Grasshopper/DgIcons.cs
  - ui-v2/src/graph/buildRings.js
  - ui-v2/src/screens/GraphScreen.jsx
  - training/dataset_schema.json
  - spec/DATABASE.md
  - ontology/dg-shapes.ttl
  - .github/copilot-instructions.md
findings:
  critical: 2
  warning: 9
  info: 4
  total: 15
status: issues_found
---

# Phase 36: Code Review Report

**Reviewed:** 2026-07-19T15:33:17Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 36 delivers the Computgraph publish pipeline (data-service module + route, GH component + HTTP client) and the Computgraph graph-layer display (buildRings orbits/captions, properties-panel truncation), plus four schema documentation surfaces. The core publish module is well-built: parameterized Cypher throughout (no injection surface found), single-transaction atomicity, untagged-section exclusion honored (T-36-02), and dgId computed via the pure function to avoid the label-less-anchor MERGE trap.

However, the end-to-end flow is broken at the wire contract: the C# client camelCases the request body while the FastAPI model expects snake_case, so **every publish from the new GH component will fail with HTTP 422**. Tests exercise `publish_structure()` directly and never cross the HTTP boundary, which is why this was not caught. Separately, the property-truncation "fix" (ee907c9) introduced a data-corruption path: editing any long property in the Graph Viewer now writes the truncated 200-char value back to Neo4j. Schema-doc drift also remains: fix commit 4e441d3 corrected the Algorithm merge key in `cypher_template.txt` and `spec/DATABASE.md` but missed the node-entry key in `training/dataset_schema.json` and the node list in `.github/copilot-instructions.md`.

## Critical Issues

### CR-01: GH → data-service publish request always rejected with 422 (camelCase vs snake_case field name)

**File:** `data-service/app.py:1339-1348`, `DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs:11-25`, `DG/src/DG.Grasshopper/Validation/ComputgraphPublishContract.cs:14`
**Issue:** `ComputgraphPublishClient` serializes with `JsonNamingPolicy.CamelCase`, so the POST body is `{"project": ..., "cgContext": {...}}`. The pydantic model declares `cg_context: dict` with no alias and no `populate_by_name` config, so FastAPI rejects every request from the component with `422 — Field required: cg_context`. Every other GH-client-facing model in `app.py` uses camelCase Python field names for exactly this reason (`ValidationPublishRequest.statePayloadJson`, `ruleResults`, etc. at app.py:214-226). Server-side tests (`test_computgraph_publish.py`) call `publish_structure()` directly, so the HTTP contract is never exercised. The entire 36-02 deliverable (DG COMPUTGRAPH PUBLISH) is non-functional against the 36-01 route.
**Fix:**
```python
class ComputgraphPublishRequest(BaseModel):
    project: str
    cgContext: dict   # match the GH client's camelCase wire format (ValidationPublishRequest convention)

@app.post("/computgraph/publish")
def post_computgraph_publish(payload: ComputgraphPublishRequest):
    ...
    return computgraph_publish.publish_structure(session, payload.project, payload.cgContext)
```
(or keep `cg_context` and add `Field(alias="cgContext")` + `model_config = ConfigDict(populate_by_name=True)`). Add one route-level test that POSTs the exact JSON shape the C# client emits.

### CR-02: Property truncation feeds the inline editor — editing any long property silently corrupts it in Neo4j

**File:** `ui-v2/src/screens/GraphScreen.jsx:690` (with `ui-v2/src/components/display/PropertiesTable.jsx:11-23`)
**Issue:** The Phase-36 change `value: String(p[1]).length > 200 ? String(p[1]).slice(0, 200) + "…" : String(p[1])` truncates the *same* `value` field that `PropertiesTable.begin()` uses to seed the edit draft (`setDraft(String(r.value ?? ""))`). The selection panel is editable (`onEdit={editNodeProp}`, GraphScreen.jsx:897). Clicking ✎ then Enter on any property longer than 200 chars — e.g. `Algorithm.contextJson`, the exact property this truncation was added for — writes the truncated `…`-suffixed string back to Neo4j via `updateNodeProp`, destroying the reconstruction attachment with no warning. Before this change the draft round-tripped the full value, so this is a regression introduced by the truncation fix.
**Fix:** Keep the full value separate from the display value so the editor drafts from the untruncated source:
```jsx
const rowsOf = (n, max) => (n ? n.props.slice(0, max).map((p) => {
  const full = String(p[1]);
  return { key: p[0], value: full.length > 200 ? full.slice(0, 200) + "…" : full, rawValue: full };
}) : []);
```
and in `PropertiesTable.begin()`: `setDraft(String(r.rawValue ?? r.value ?? ""))` (or make >200-char values non-editable).

## Warnings

### WR-01: dataset_schema.json still documents Algorithm merge key as `cgId` — contradicts code and the corrected docs

**File:** `training/dataset_schema.json:228-242`
**Issue:** The Algorithm node entry's `key` block lists `cgId` + `definitionId` + `project`, but the code MERGEs Algorithm on `{algIndex, definitionId, project}` (computgraph_publish.py:407) and never sets a `cgId` on Algorithm at all. Fix commit 4e441d3 corrected this key in `cypher_template.txt` and `spec/DATABASE.md` and fixed this file's relationships block, but missed this node entry. `dataset_schema.json` is declared the single source of truth for schema v4 — an LLM prompt built from it will emit MERGE keys that duplicate Algorithm nodes.
**Fix:** Replace the `key` block with `{"algIndex": "integer", "definitionId": "string", "project": "default-project"}` and drop the `cgId` placeholder from Algorithm.

### WR-02: copilot-instructions.md Algorithm key line not fixed by 4e441d3

**File:** `.github/copilot-instructions.md:35`
**Issue:** `- \`Algorithm\`: key \`cgId\`+\`definitionId\`+\`project\`` — same stale merge key as WR-01; the fix commit corrected only the relationship lines (54-55) in this file. Note the same stale key also survives in `CLAUDE.md`'s node table (`Algorithm | Computgraph | cgId+definitionId+project`) — both are listed schema-propagation surfaces.
**Fix:** Change to `key \`algIndex\`+\`definitionId\`+\`project\`` in both files.

### WR-03: DATABASE.md carries contradictory PARAM_LINK semantics within the same document

**File:** `spec/DATABASE.md:279`
**Issue:** The Parameter node section says "`PARAM_LINK` links parameters across procedures" (the pre-fix Parameter→Parameter semantics), while the relationships table at line 401 (corrected by 4e441d3) says `PARAM_LINK | Parameter | Interface | Parameter → interface, wire-derived`. Code implements Parameter→Interface (computgraph_publish.py:582). A reader of the Parameter section gets the wrong model.
**Fix:** Reword line 279 to "- `PARAM_LINK` connects this parameter to the Interface nodes its wires feed (wire-derived)".

### WR-04: Publish accepts null/empty merge-key inputs — null `algIndex` aborts with an opaque Neo4j error; empty entity ids silently collapse distinct entities

**File:** `data-service/computgraph_publish.py:154, 164, 181, 200, 235`
**Issue:** `_build_publish_params` validates `paramKind`/`dataType`/`ifaceType` but not the merge-key fields. (a) `alg_index = algorithm.get("index")` may be `None`; `MERGE (a:Algorithm {algIndex: row.index, ...})` with a null map value raises Neo4j's "Cannot merge node using null property value" — a `ClientError`, not `ValueError`, so the route returns an unstructured 500 instead of the intended 422. (b) `procedure.get("id") or ""` (same for patterns/parameters/interfaces at 181/200/235) turns a missing id into `cgId: ""` — two id-less entities MERGE into the *same* node, silently collapsing distinct entities and corrupting the published subgraph.
**Fix:** Validate up front, matching the module's documented ValueError contract:
```python
if alg_index is None:
    raise ValueError("algorithm.index is required on every algorithm.")
proc_cg_id = procedure.get("id")
if not proc_cg_id:
    raise ValueError(f"procedure.id is required (algorithm {alg_index}).")
```

### WR-05: Publish route surfaces Neo4j/driver failures as raw 500s — sibling routes map them to structured errors

**File:** `data-service/app.py:1360-1371`
**Issue:** `post_computgraph_publish` catches only `ValueError`. Any Neo4j failure (`ServiceUnavailable`, auth error, the null-merge-key `ClientError` from WR-04) propagates as an unstructured FastAPI 500. The adjacent `/computgraph/recognize` route (app.py:1329-1331) catches generic `Exception` and returns the project's structured error envelope; the GH component's error message quality depends on that envelope.
**Fix:** Add a broad handler mirroring the recognize route:
```python
except ValueError as exc:
    ...
except Exception as exc:
    raise _structured_error_response(
        str(exc), "Check Neo4j availability and the publish payload.",
        "COMPUTGRAPH_PUBLISH_FAILED", 502)
```

### WR-06: Provenance trio (provider/model/confidence) is unreachable dead code for GH-originated publishes

**File:** `data-service/computgraph_publish.py:174-176, 190-192, 227-229, 251-253, 296-298` (root cause in `DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs:580-679`)
**Issue:** The publish module reads `provider`/`model`/`confidence` for `source == "recognized"` entities, and `spec/DATABASE.md`/`dataset_schema.json` document these as populated for recognized entities. But none of the wire DTOs (`CgObjectDto`, `CgProcedureDto`, `CgPatternDto`, `CgParameterDto`, `CgInterfaceDto`) carry these fields — only `Source`/`DgId`. Every envelope produced by `ComputgraphContextSerializer.Serialize` (the only path DG COMPUTGRAPH PUBLISH uses) omits them, so published `recognized` entities always get `provider/model/confidence = null`, contradicting the phase's "provenance-carrying" goal (CGPD provenance) and the schema docs.
**Fix:** Either add `Provider`/`Model`/`Confidence` to the Cg* DTOs and models and populate them in the Phase-35 accept path, or amend DATABASE.md/dataset_schema.json to state provenance is not yet transported from GH (deferring the wire change explicitly).

### WR-07: SHACL shapes demand properties the publish path treats as optional — valid publishes will fail data-integrity validation

**File:** `ontology/dg-shapes.ttl:385-391, 419-425, 488-495` vs `data-service/computgraph_publish.py:171, 209-213`
**Issue:** `AlgorithmShape_algIndex`, `ProcedureShape_procIndex`, and `ParameterShape_dataType` all declare `sh:minCount 1` / `sh:severity sh:Violation`. But the publish code allows `dataType` to be `None` (line 209 explicitly permits it) and writes `procIndex` from `procedure.get("index")` which may be null (Cypher `SET p.x = null` removes the property). A Parameter with no dataType — legal per the publish validation — becomes a SHACL Violation. The two validation systems disagree on optionality, which `spec/RULE-PARTITION-POLICY.md` calls out as mis-categorization to avoid.
**Fix:** Either drop `sh:minCount 1` from `ParameterShape_dataType` (and `ProcedureShape_procIndex`), or make `dataType` required in `_build_publish_params` — then update DATABASE.md's "optional" markers to match whichever side wins.

### WR-08: buildRings has no caption for `Behavior` — every Behavior node renders the literal string "Behavior"

**File:** `ui-v2/src/graph/buildRings.js:17, 22-51`
**Issue:** `ORBITS.Computgraph` places `Behavior` in orbit 0, but `CAPTIONS` has no `Behavior` entry. `captionOf` then falls back to `props.label || props.name || props.id || label` — a Behavior node carries only `definitionId`/`graph`/`project`/`publishedAt` (computgraph_publish.py:384-388), so every Behavior displays as "Behavior". The schema table (CLAUDE.md / DATABASE.md) defines `definitionId` as Behavior's display property. Since caption is also the search/sort key (`arr.sort((a,b) => a.label.localeCompare(b.label))` and `computeMatches`), all Behaviors are indistinguishable in the layer.
**Fix:** Add `Behavior: ["definitionId"]` to `CAPTIONS`.

### WR-09: No timeout on the publish HttpClient — a hung data-service freezes the Grasshopper solve for up to 100 s

**File:** `DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs:10, 25-26`
**Issue:** `Publish` runs synchronously on the GH solver thread (`.GetAwaiter().GetResult()`) with a shared `HttpClient` that keeps the default 100-second timeout. If the data-service accepts the TCP connection but stalls (container restarting, Neo4j blocked mid-transaction), Rhino's UI is unresponsive for the full default timeout with no way to cancel. `ValidationPublishClient` shares this flaw, but this new client copies it into a path that can carry much larger payloads (full canvas envelope).
**Fix:** Set an explicit bounded timeout on the client:
```csharp
private static readonly HttpClient HttpClient = new() { Timeout = TimeSpan.FromSeconds(15) };
```
and surface `TaskCanceledException` as a "data-service did not respond within 15s" status message.

## Info

### IN-01: Representation / SharedProperty have no orbit or caption mapping in the Computgraph layer

**File:** `ui-v2/src/graph/buildRings.js:17, 22-51`
**Issue:** The identity-registry labels (`Representation`, `SharedProperty`) carry `graph: 'Computgraph'` (dataset_schema.json:158, 176) so they render in this layer, but they are absent from `ORBITS.Computgraph` (fall to outer orbit 2, mixed with Parameter/Interface) and from `CAPTIONS` (render as "Representation"/"SharedProperty" instead of `nativeId`/`propertyName` per the schema display columns).
**Fix:** Add `Representation: ["nativeId"], SharedProperty: ["propertyName"]` to `CAPTIONS` and place both labels in `ORBITS.Computgraph` deliberately.

### IN-02: `publishedAt` stored as an ISO string while DATABASE.md documents `datetime()`

**File:** `data-service/computgraph_publish.py:79`; `spec/DATABASE.md:125, 142`
**Issue:** Code writes `datetime.now(timezone.utc).isoformat()` (a string property); the DATABASE.md examples show `publishedAt: datetime()` and the property table types it `datetime`. Cypher `datetime()` comparisons/`duration` math against these nodes will fail on the string type.
**Fix:** Either write a Cypher `datetime($publishedAt)` in the SET clauses, or change the doc type to `string (ISO-8601)`.

### IN-03: Dangling `hostPatternId` and object-less envelopes are silently dropped rather than reported

**File:** `data-service/computgraph_publish.py:83-100, 491-505`
**Issue:** (a) `_publish_pattern_hosts` is MATCH-based — a `hostPatternId` referencing a pattern absent from the payload silently creates no edge, with no entry in the response. (b) When `object` is null but `algorithms` exist, Algorithm nodes are still MERGEd but the trailing `MATCH (b:Behavior ...)` finds nothing, so they persist as orphans with no `HAS_ALGORITHM` parent edge and the response gives no indication the hierarchy is disconnected.
**Fix:** Count unmatched host rows / detect the object-less-with-algorithms case and include a `warnings` array in the publish response.

### IN-04: Component architecture table not updated for the new component

**File:** `.github/copilot-instructions.md:71-89`
**Issue:** The "Component Architecture (14 components)" table (mirrored in CLAUDE.md's "Rhino 8 SDK (14 components)") does not include DG COMPUTGRAPH PUBLISH (nor the Phase 33-35 components CANVAS LISTENER / OBJECT MARKER / ENTITY TAG / STRUCTURE CONFIRM). Anyone using the table to reason about the plugin's surface gets a stale picture.
**Fix:** Add the Phase 33-36 components and update the count.

---

_Reviewed: 2026-07-19T15:33:17Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
