# Phase 1303: Pattern Map (covers plan 1303-16 ONLY, decisions D-54..D-58)

**Mapped:** 2026-10-20
**Files analyzed:** 17 (3 new, 14 modified)
**Analogs found:** 17 / 17 (all in worktree `C:\Users\Admin\source\repos\dg-mapping`)

Paths below are relative to the worktree root. Line numbers are from the worktree files as read.

## File Classification

| File | Role | Data Flow | Closest Analog | Match |
|------|------|-----------|----------------|-------|
| `data-service/property_calculator_store.py` (+ `load_catalogue`, `vocabulary_rows`, confirm/reject/retire, review fields) | store | CRUD (Neo4j) | same file `LOAD_QUERY`/`SAVE_QUERY`/`load_active`/`save` (16-31, 91-114); `mapping_store.py:938-1026` for tx lock + idempotent commit | exact |
| `data-service/property_calculator_review.py` (NEW, pure) | utility | transform | `design_state_projection.py:176-195` + `app.py:983-1000` (propStates shapes) | role-match |
| `data-service/property_scripts.py` (`resolve(... shared)`, `_from_shared`) | service | transform | same file `resolve` 211-262, `_from_stored` 194-208 | exact |
| `data-service/property_calculator_llm.py` (`validate_function(source, name=)`) | utility | transform | same file `validate_function` 71 | exact |
| `data-service/dg_context.py` (`assemble_context` vocab merge) | service | request-response | same file `assemble_context` 458-482 | exact |
| `data-service/app.py` (4 routes, `LOCKED_NODE_LABELS`, `CLAIM_UNTAGGED_SHARED_GRAPHS`) | controller | request-response | `app.py:2113-2205` property-calculator routes; 5629-5675 constants | exact |
| `data-service/route_policy.py` (4 rows) | config | request-response | `route_policy.py:231-239` | exact |
| `spec/SECURITY-BOUNDARY.md` (4 rows in fenced route table) | config/doc | n/a | lines 310-312 | exact |
| `spec/DATABASE.md`, `spec/LPG-OWL-MAPPING.md` | doc | n/a | DATABASE.md 612-617, 647-648; LPG-OWL-MAPPING.md 376-378 | exact |
| `spec/REPRODUCIBILITY.md` | doc | n/a | fenced block 163-176 (see Shared Patterns: likely NO new row) | n/a |
| `ui-v2/src/lib/mappingApi.js` (4 helpers) | utility | request-response | `placePropertyCheck`/`runPropertyCheck` 48-58 | exact |
| `ui-v2/src/screens/MappingPanel.jsx` (candidate review card) | component | request-response | `PropertyCheckCard` 943-975 (rendered at 1466) | exact |
| `ui-v2/src/i18n/dict/screens.js` | config | n/a | lines 195-202 | exact |
| `ui-v2/tests/mapping-api.test.mjs` | test | request-response | existing file (same helper tests) | exact |
| `data-service/tests/test_property_calculator_review.py` (NEW) | test | transform | `tests/test_property_scripts.py` `_Session` 151-165 | role-match |
| `data-service/tests/test_property_scripts.py`, `test_dg_context.py`, `test_route_inventory.py`, `test_security_boundary_spec.py` | test | mixed | existing files | exact |

## Pattern Assignments

### `property_calculator_store.py` (store, CRUD)

**Analog:** itself. Add a parallel set of queries for the GLOBAL node. Copy the style: module-level Cypher string constants, `session.run(Q, **params).data()`, `dict(row)` normalisation, `.consume()` on writes.

Load/save style (16-31, 91-114):
```python
LOAD_QUERY = ("MATCH (pc:PropertyCalculator {project:$project}) WHERE coalesce(pc.status, 'active') = 'active' "
    "RETURN pc.dataPropertyIri AS dataPropertyIri, ... ORDER BY dataPropertyIri")
def load_active(session, project):
    out = {}
    for row in session.run(LOAD_QUERY, project=project).data():
        row = dict(row); row["params"] = json.loads(row.pop("paramsJson") or "{}")
        out[row["dataPropertyIri"]] = row
    return out
```
Plan 16 adds: `load_catalogue(session, company)` returning dict keyed by lower-cased `propertyKey` from `(:CatalogueCalculator {graph:'CalculatorCatalogue', company:$company, status:'active'})` (no `project` property, D-56; carries `sourceProject`); `vocabulary_rows(session, company)` wrapped in try/except returning `[]`, keeping only rows that have `propertyKey`, `ORDER BY propertyKey, sha256` (RESEARCH Pitfall 6); add `reviewStatus`/`catalogueId` fields to LOAD/SAVE (SAVE currently hard-sets `pc.status = 'active'` at line 28; reject/retire must not be undone by a later `save`, Pitfall 3).

Confirm tx: copy lock + conflict pattern from `mapping_store.py:938-943` (lock) and `:979-1026` (idempotent commit, conflict codes); sketch in RESEARCH "Confirm, one transaction". Use `session.execute_write(fn)`, MERGE on `sha256`, 409 on taken (company, propertyKey).

### `property_scripts.py` (service, transform)

**Analog:** `resolve` 211-262. New order: file catalogue -> shared -> project-stored -> generator. Insert after the catalogue step at line ~243, before `if binding is None and dp["iri"] in stored` (245):
```python
binding = fresh.get(dp["iri"])
if binding is None:
    binding = resolve_property(dp, catalogue, chooser)   # file catalogue
    ...
if binding is None and dp["iri"] in stored:
    binding = _from_stored(stored[dp["iri"]], catalogue)
if binding is None and generator is not None:
    answer = generator(dp, rules_by_dp[dp["iri"]], box_label)
```
Add `shared: dict | None = None` (and rejected set) param; `_from_shared(entry)` mirrors `_from_stored` (194-208), re-checks `sha256(source)==entry.sha256` and `validate_function`, returns `None` + warning on mismatch. Return binding in the existing generated shape (`{"calculator": f"generated:{digest[:10]}", "origin":"generated","function","source","sha256","resolvedBy":"shared","new":...}`, see 252-256) so `assemble` needs no change. Callers load shared next to `stored = property_calculator_store.load_active(...)` at lines 414 and 453. Must still write a project `PropertyCalculator` (store `save_context_classes` MATCHes it).

### `dg_context.py` (service, request-response)

**Analog:** `assemble_context` 458-482 (deterministic, ORDER BY, no timestamps). Merge per RESEARCH Pattern 2: `copy.deepcopy(dg_knowledge.swrl_conventions())` then `+= property_calculator_store.vocabulary_rows(session, company)`; never mutate the module constant; company via `company.company_for_project(project)` (`company.py:53`, returns None when unassigned: then no shared rows).

### `app.py` routes (controller)

**Analog:** `app.py:2199-2205` (GET with `Query`) and 2113-2130 (POST with Pydantic body + `_mapping_actor(request)`):
```python
@router.get("/scripts/property-calculators")
def get_property_calculators(project: str = Query(...)):
    with driver.session() as session:
        stored = property_calculator_store.load_active(session, project)
    return {"project": project, "calculators": list(stored.values())}
```
New: `GET /scripts/property-calculators/candidates?project&runId`, `POST .../confirm`, `.../reject`, `.../retire`. Body models follow `PropertyCheckRunRequest` (2128-ish) with `project: str`. Error mapping: raise structured codes `CALCULATOR_CHANGED`/`CALCULATOR_INTEGRITY` as 409 (RESEARCH).

**Constants (5629-5675):** add `"CatalogueCalculator"` to `LOCKED_NODE_LABELS` (list at 5629; the mapping entries at 5636-5638 are the precedent with a Phase comment) so editors cannot rewrite stored source via the generic graph route (Pitfall 7). Add the catalogue graph name `"CalculatorCatalogue"` to `CLAIM_UNTAGGED_SHARED_GRAPHS = ["SpecGraph"]` (5675, WR-02 comment) so `CLAIM_UNTAGGED_QUERY` (`WHERE n.project IS NULL AND NOT coalesce(n.graph,'') IN $sharedGraphs`) never claims it (Pitfall 1). The list is exposed at app.py:5779 and 5820 and asserted in `tests/test_graph_routes.py:222`.

### `route_policy.py` (config)

**Analog:** 231-239:
```python
("GET", "/scripts/property-calculators"): _p(_MEM, _DEL, source="query", role="viewer"),
("POST", "/scripts/property-calculator/place"): _p(_MEM, _DEL, source="body", role="editor"),
```
New rows (D-57: DeGram never confirms, so confirm/reject/retire use `_p(_MEM, ...)` WITHOUT `_DEL` if member-only is wanted; the `_DEL` delegated principal marker is what lets the DeGram agent call; candidates GET may keep `_MEM, _DEL`, viewer). Retire = owner role per planner default (check how `role="owner"` is spelled elsewhere in the file). Keep a comment block like line 231-232.

### `spec/SECURITY-BOUNDARY.md` (doc, machine-checked)

**Analog:** lines 310-312, format `METHOD|path|principals|source|role`:
```
GET|/scripts/property-calculators|delegated+member|query|viewer
```
Add 4 matching lines; `tests/test_security_boundary_spec.py` and `tests/test_route_inventory.py` go red together if either side drifts (Pitfall 11), so change route + policy + spec in the same task.

### Spec docs

- `spec/DATABASE.md`: add `CatalogueCalculator` node entry after the PropertyCalculator block (612-617; same property-list-in-parens style, "Merge key", "written only by ..."); add `reviewStatus`, `catalogueId`, `reviewLock` fields; relationship row analog 647-648 if a link edge is added.
- `spec/LPG-OWL-MAPPING.md`: add a row beside 376-378 (`| node | — | note. Not exported. |`).
- `spec/REPRODUCIBILITY.md`: the fenced block (163-176) lists only LLM call sites (`file|function|scope-class`, "exactly nine lines"). Plan 16 adds no new LLM call (promotion removes one); do NOT add a row. Add only prose (as for `mapping_llm.py` 178-182) saying a promoted calculator is reused without the LLM, if desired. Note RESEARCH Pitfall 2: the drift test is already red; fix is separate.

### `ui-v2/src/lib/mappingApi.js` (utility)

**Analog:** 48-58:
```js
export function placePropertyCheck(project) {
  return apiFetch(`${dataServiceBase()}/scripts/property-calculator/place`, { method: "POST", body: { project } });
}
export function runPropertyCheck(project, { clear = false } = {}) {
  return apiFetch(`${dataServiceBase()}/scripts/property-check/run`, { method: "POST", body: { project, clear } });
}
```
New: `listCalculatorCandidates(project, runId)` (GET with query string), `confirmCalculator(project, {dataPropertyIri, sha256, runId, runTime...})`, `rejectCalculator`, `retireCalculator`. Preceded by a `// Phase 1303-16 (DGOPN-05, D-54..D-58)` comment like line 48.

### `MappingPanel.jsx` (component)

**Analog:** `PropertyCheckCard({ project, t })` 943-975: local `useState` for `busy/result/error`, async handler with try/catch/finally, `t(...)` for strings. Render the review card next to it (rendered at line 1466 `<PropertyCheckCard project={project} t={t} />`). Show source, sample values, verdicts, Confirm/Reject buttons (human click only, D-57).

### `i18n/dict/screens.js`

**Analog:** 195-202: English-key to Russian map entries, parameters as `{property}`:
```js
"No calculator for {property} ({rule})": "Нет калькулятора для {property} ({rule})",
```
Add every new UI string here (EN key -> RU value).

### `property_calculator_review.py` (NEW, pure) and its test

Pure functions over the run payload (RESEARCH "Candidate samples from a run"): parse `statePayloadJson`, filter `propStates` by `dataPropertyIri`, sort by `objectRef`, first N + n/min/max. Test analog `tests/test_property_scripts.py:151-165`:
```python
class _Session:
    def __init__(self, rows, stored=()): ...
    def run(self, query, **params):
        self.calls.append((query, params))
        if "READS_CLASS" in query: ...
```
Dispatch on query substrings and return `[]`-style results for unmatched queries; for `dg_context` tests use `FixtureSession` (`tests/test_dg_context.py:107-119`), which returns the same rows for ANY query (so `vocabulary_rows` must drop rows lacking `propertyKey`, Pitfall 6).

## Shared Patterns

- **Company scoping (D-56):** `company.company_for_project(project)` (`company.py:53`) is the only company read; global node carries `company` + `sourceProject`, never `project`.
- **Project isolation:** project nodes keyed `{project:$project}`; the catalogue is the only deliberate project-less node, hence the `LOCKED_NODE_LABELS` + `CLAIM_UNTAGGED_SHARED_GRAPHS` pair.
- **AST contract:** re-run `property_calculator_llm.validate_function` (line 71) on every confirm and on every shared load; stored name is `calc_gen_<hex>` so it needs a `name=` parameter (RESEARCH layout).
- **Actor:** `_mapping_actor(request)` (app.py ~2130) for `confirmedBy`.
- **Neo4j HTTP/driver:** never infer write success from status; one statement per entry (memory note on tx/commit).

## No Analog Found

None for structure. Behavioural sketches without a code twin (use RESEARCH): per-box sample extraction (Pitfall 9) and run-time binding (D-58).

## Metadata

**Analog search scope:** `data-service/*.py`, `data-service/tests`, `spec/`, `ui-v2/src/{lib,screens,i18n}`
**Pattern extraction date:** 2026-10-20
