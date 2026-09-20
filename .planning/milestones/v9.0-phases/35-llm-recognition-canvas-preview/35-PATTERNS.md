# Phase 35: LLM Recognition and On-Canvas Proposal Preview - Pattern Map

**Mapped:** 2026-07-19
**Files analyzed:** 10
**Analogs found:** 9 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `data-service/cg_recognition.py` | service | request-response (LLM call + bounded retry) | `data-service/dg_context.py` (`generate_validated_cypher`, `validate_cypher`, `append_corrective_feedback`) | exact |
| `data-service/app.py` (`POST /computgraph/recognize`) | route/controller | request-response | `data-service/app.py` (`post_context_generate_cypher`, lines 1335-1348) | exact |
| `data-service/gh_bridge.py` (replace preview stubs) | service (TCP client) | request-response over raw socket | `data-service/gh_bridge.py` itself — `_call()` + existing `preview_structure`/`clear_preview`/`get_preview_status` stub functions (lines 108-131) | exact (already present, needs no structural change — only downstream `app.py` route + expectations change) |
| `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` (`BuildDispatcher`, `HandlePreviewStructure`, `HandleClearPreview`, `HandleGetPreviewStatus`) | controller (command dispatcher) | event-driven (async TCP accept loop) | itself — `HandleGetCanvasContext`/`HandleGetSelection` + `InvokeOnCanvas` (lines 129-194); write variant modeled on `EntityTagComponent.cs` `ScheduleSolution`/undo pattern (lines 83-90, 308-426) | role-match (read handlers exact; write handlers need a new `InvokeOnCanvasWrite` composed from both analogs) |
| `DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs` (new) | store (shared static registry) | CRUD (in-memory) | `DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs` (internal static class idiom, whole file, 61 lines) | role-match (structural idiom only; no CRUD analog exists — closest is a static lookup, not a mutable dictionary) |
| `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` (new) | component (GH_Component, confirm UX) | event-driven (SolveInstance on Accept/Reject/Apply) | `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs` (whole file — undo/group mutation) + `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs` (ValueTable read/write, lines 39-45, 119-132, 174-179) | exact (undo/group idiom) + exact (ValueTable idiom) |
| `CanvasAnnotationStyles.cs` (additive `[?]` prefix constant) | utility/config | transform | itself — `Preview(Color baseColor)` already added (lines 53-59) | exact (already-scaffolded; only a name-prefix constant is new) |
| `CanvasContextExtractor.cs` / `CanvasAnnotationParser.cs` (additive `Recognized`/`Source` read) | transform (raw canvas → parsed context) | transform | itself — existing `TryAddGroup`/`Parse` methods (not yet read in this pass; RESEARCH.md gives exact line-level guidance, see Pattern 4) | role-match (additive-only; must not touch classification regex per Phase 34-01 lock) |
| `data-service/tests/test_cg_recognition.py` (new) | test | request-response | `data-service/tests/test_dg_context.py` — `TestValidator` (L408), `TestRetryLoop` (L578), `_FakeAdapterForRetry` (L559) | exact |
| `DG/tests/DG.Tests/PreviewRegistryTests.cs` (new, if splittable) | test | CRUD | No direct analog — `DG.Tests` cannot reference `DG.Grasshopper` (TFM incompatibility); precedent is "most GH-dependent logic is manual UAT only" (EntityTagComponent has no unit test) | **no analog** |

## Pattern Assignments

### `data-service/cg_recognition.py` (service, request-response)

**Analog:** `data-service/dg_context.py`

**Module docstring / path-resolution convention** (lines 1-33): follow the same header style — explain what this module composes from siblings (`dg_knowledge.load_computgraph_catalog()`, `llm_gateway`), and state explicitly that this mirrors `generate_validated_cypher()`'s structure, not a new idiom.

**Core bounded-retry pattern to mirror verbatim** (`dg_context.py` lines 880-922):
```python
def generate_validated_cypher(
    prompt: str, request_type: str, max_retries: int = 2
) -> dict[str, Any]:
    if request_type not in CONTEXT_REQUEST_TYPES:
        raise ValueError(f"Unknown request type: {request_type}")

    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()
    provider, model, api_key = resolve_active_provider(settings, master_secret)
    adapter = get_adapter(provider, settings.get("baseUrl"))

    current_prompt = prompt
    violations: list[dict[str, Any]] = []
    for attempt in range(max_retries + 1):
        req = GenerateRequest(prompt=current_prompt, model=model, provider=provider)
        response = adapter.generate(req, api_key)
        result = validate_cypher(response.text, request_type)
        if result["valid"]:
            return {"valid": True, "cypher": response.text, "attempts": attempt + 1}
        violations = result["violations"]
        current_prompt = append_corrective_feedback(prompt, violations)

    return {"valid": False, "violations": violations, "attempts": max_retries + 1}
```
For `recognize_structure()`: same shape, swap `validate_cypher` for a new `validate_proposed_structure(parsed, cg_context)`, and insert a `_extract_json(response.text)` step before validation (new — no precedent, see Pitfall 1 in RESEARCH.md). **Critical inherited constraint: NEVER re-POST to `/llm/generate` on retry** — call `adapter.generate()` in-process each attempt, exactly as above.

**Corrective feedback pattern to mirror** (lines 860-877):
```python
def append_corrective_feedback(prompt: str, violations: list[dict[str, Any]]) -> str:
    lines = [prompt, "", "--- CORRECTIVE FEEDBACK: the previous Cypher failed validation ---"]
    for violation in violations:
        where = f" (at: {violation['path']})" if violation.get("path") else ""
        lines.append(f"- [{violation['code']}] {violation['message']}{where}")
    lines.append(
        "Regenerate the Cypher, fixing every violation listed above. Output "
        "Cypher only -- no JSON, no markdown fences, no commentary."
    )
    return "\n".join(lines)
```
Recognition variant needs the opposite output-discipline instruction ("Output ONLY a single JSON object, no markdown fences, no commentary" — RESEARCH.md Pitfall 1) but the same violation-list-to-text shape.

**Validator pattern to mirror** — `validate_cypher()` return shape `{"valid": bool, "violations": [{"code","message","path"}]}` is reused unchanged; RESEARCH.md's `validate_proposed_structure()` code example (lines 422-452 of 35-RESEARCH.md) is the concrete template — copy directly, including the `_collect_known_member_ids`/`_collect_tagged_member_ids` helper split and the two mandatory checks (`unknown_member_id`, `tagged_overlap`).

**Error handling pattern**: `map_provider_error(exc)` + `_structured_error_response(...)` (used at `app.py` lines 1346-1348) is the What+Where+How-to-fix error convention to reuse for any adapter-level failure in `cg_recognition.py`.

---

### `data-service/app.py` — `POST /computgraph/recognize` (route, request-response)

**Analog:** `post_context_generate_cypher` (`app.py` lines 1335-1348)

```python
@app.post("/context/generate-cypher")
def post_context_generate_cypher(payload: dg_context.GenerateCypherRequest):
    try:
        return dg_context.generate_validated_cypher(payload.prompt, payload.type)
    except ValueError as exc:
        raise _context_type_invalid_error(exc)
    except Exception as exc:
        error_msg, hint, code = map_provider_error(exc)
        raise _structured_error_response(error_msg, hint, code, 502)
```
New route: thin delegation to `cg_recognition.recognize_structure(cg_context, procedure_index)`, same `try/except ValueError` + `except Exception -> map_provider_error` shape. Keep it **synchronous request/response** (CLAUDE.md: no message queue) — do not add a background job.

---

### `data-service/gh_bridge.py` (service, TCP client — replace stub behavior of callers, not `_call` itself)

**Analog:** itself, lines 108-131 (existing `_call` envelope handling + the 3 stub function bodies)

```python
def preview_structure(structure: dict) -> dict:
    """Preview stub — returns `{"supported": False, ...}` until Phase 35."""
    return _call("preview_structure", structure)
```
No change needed to `_call()`'s envelope/error handling (already bounded: connect timeout, read timeout, malformed-response guards — lines 36-105). The three functions' **docstrings** need updating (no longer "stub"), but the body (`_call("preview_structure", structure)`) is already correct and forwards to whatever the C# dispatcher now returns. `test_gh_bridge.py`'s two stub tests (`test_preview_structure_stub_returns_without_raising`, `test_clear_preview_stub_returns_without_raising`) must be replaced, not merely extended (RESEARCH.md "State of the Art" table).

---

### `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` (controller, event-driven)

**Analog:** itself (read handlers) + `EntityTagComponent.cs` (write/undo pattern)

**Dispatcher registration to replace** (lines 129-141):
```csharp
private CanvasCommandDispatcher BuildDispatcher()
{
    var handlers = new Dictionary<string, Func<CanvasCommandRequest, object?>>
    {
        [CanvasBridgeCommands.GetCanvasContext] = HandleGetCanvasContext,
        [CanvasBridgeCommands.GetSelection] = HandleGetSelection,
        [CanvasBridgeCommands.PreviewStructure] = _ => CanvasCommandDispatcher.StubResult(CanvasBridgeCommands.PreviewStructure),
        [CanvasBridgeCommands.ClearPreview] = _ => CanvasCommandDispatcher.StubResult(CanvasBridgeCommands.ClearPreview),
        [CanvasBridgeCommands.GetPreviewStatus] = _ => CanvasCommandDispatcher.StubResult(CanvasBridgeCommands.GetPreviewStatus),
    };
    return new CanvasCommandDispatcher(handlers);
}
```
Replace the three `StubResult(...)` lambdas with `HandlePreviewStructure`, `HandleClearPreview`, `HandleGetPreviewStatus`. `HandleGetPreviewStatus` is a pure read — copy `HandleGetSelection`'s exact shape (line 153-156: `InvokeOnCanvas(() => (object?)new { ... })`), reading `PreviewRegistry.Pending` instead of selection GUIDs.

**Read-handler + UI-thread marshalling pattern to copy verbatim** (lines 143-156, 184-194):
```csharp
private object? HandleGetCanvasContext(CanvasCommandRequest request)
{
    return InvokeOnCanvas(() =>
    {
        var project = request.TryGetString("project");
        var contextJson = CanvasContextExtractor.SerializeContext(OnPingDocument(), project);
        return (object?)System.Text.Json.Nodes.JsonNode.Parse(contextJson);
    });
}

private static object? InvokeOnCanvas(Func<object?> work)
{
    var tcs = new TaskCompletionSource<object?>(TaskCreationOptions.RunContinuationsAsynchronously);
    RhinoApp.InvokeOnUiThread(new Action(() =>
    {
        try { tcs.SetResult(work()); }
        catch (Exception ex) { /* tcs.SetException(ex) — see full file for the catch branch */ }
    }));
    return tcs.Task.GetAwaiter().GetResult();
}
```
**New territory (write variant, RESEARCH.md Pattern 2/Pitfall 3):** `preview_structure`/`clear_preview` must *write*. `InvokeOnCanvas` only marshals reads. Build `InvokeOnCanvasWrite` with the same `TaskCompletionSource` shape, but inside the UI-thread callback perform the mutation directly (no `ScheduleSolution` needed — RESEARCH.md's explicit recommendation, since the bridge command doesn't run inside another component's `SolveInstance`), then call `Grasshopper.Instances.InvalidateCanvas()` (already used by `ObjectMarkerComponent.cs` line 179) to force the redraw, and only resolve the `TaskCompletionSource` after the mutation + invalidate have run.

**Undo/group mutation pattern to copy from `EntityTagComponent.cs`** (lines 308-426):
```csharp
// lines 308-310 (deferred-mutation framing — read but do NOT copy ScheduleSolution
// itself for the bridge write path; the *undo record + group creation* shape below is
// what to copy):
// doc.ScheduleSolution(1, currentDoc => { ... });

// lines 411-426 (undo record + group creation + push — copy this shape):
var record = new GH_UndoRecord("DG Tag Entity");
// ... build GH_Group, set NickName/Colour, AddObject(id) per member ...
record.AddAction(new GH_AddObjectAction(group));
currentDoc.UndoServer.PushUndoRecord(record);
```
For `HandlePreviewStructure`, wrap ALL created groups + the legend scribble under **one** `GH_UndoRecord("DG structure proposal")` per CONTEXT.md decision 2 (single Ctrl+Z wipes everything) — this differs from `EntityTagComponent`'s per-call single-group record; iterate proposals inside one record before `PushUndoRecord`.

---

### `DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs` (new store)

**Analog:** `DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs` (internal static class idiom, whole 61-line file)

```csharp
#if GRASSHOPPER_SDK
using System.Drawing;
using DG.Core.Parsing;

namespace DG.Grasshopper.Canvas;

internal static class CanvasAnnotationStyles
{
    public static Color Preview(Color baseColor) =>
        Color.FromArgb(140, baseColor.R, baseColor.G, baseColor.B);
}
#endif
```
`Preview(Color baseColor)` (lines 53-59) already exists — reuse directly, do not reimplement desaturation. `PreviewRegistry` should follow the same `#if GRASSHOPPER_SDK` + `internal static class` wrapper, but add a `ConcurrentDictionary<string, PreviewEntry>` for mutable shared state (RESEARCH.md gives the exact target shape, lines 456-475 of RESEARCH.md — reproduced below as the concrete code to write, not merely an analog):
```csharp
internal static class PreviewRegistry
{
    private static readonly ConcurrentDictionary<string, PreviewEntry> _entries = new();
    public static void RegisterAll(IEnumerable<(string proposalId, Guid groupGuid)> created, IEnumerable<ProposalDto> proposals) { /* ... */ }
    public static IReadOnlyCollection<PreviewEntry> Pending => _entries.Values.ToList();
    public static bool TryGet(string proposalId, out PreviewEntry entry) => _entries.TryGetValue(proposalId, out entry!);
    public static void Remove(string proposalId) => _entries.TryRemove(proposalId, out _);
    public static void Clear() => _entries.Clear();
}
internal sealed record PreviewEntry(string ProposalId, Guid GroupGuid, EntityTagKind Kind, string SuggestedName, double Confidence, string Rationale);
```

---

### `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs` (new)

**Analogs:** `EntityTagComponent.cs` (undo/group mutation) + `ObjectMarkerComponent.cs` (ValueTable persistence)

**`#if GRASSHOPPER_SDK` guard + `GH_Component` shape**: copy `EntityTagComponent.cs`'s class skeleton (`RegisterInputParams`/`RegisterOutputParams`/`SolveInstance`/`AddedToDocument`) — every existing GH component in this repo follows this, per CLAUDE.md's explicit rule.

**ValueTable read/write pattern to copy** (`ObjectMarkerComponent.cs` lines 39-45, 119-132, 174-179):
```csharp
pManager.AddGenericParameter("Class", "Class", "Optional OntologyClass from ONTOGRAPH deconstruct -- binds dg:Object to a dg:Class IRI (stored in document ValueTable)", GH_ParamAccess.item);
pManager[1].Optional = true;

// read-before-write check:
var storedIri = doc?.ValueTable.GetValue("dg.objectClassIri", string.Empty);
if (!string.IsNullOrWhiteSpace(classIri) && !string.Equals(storedIri, classIri, StringComparison.Ordinal))
{
    doc?.ScheduleSolution(1, currentDoc =>
    {
        try { currentDoc.ValueTable.SetValue("dg.objectClassIri", classIri); }
        catch (Exception ex) { /* ... */ }
    });
}
// ... later, direct write + redraw:
if (!string.IsNullOrWhiteSpace(classIri))
{
    currentDoc.ValueTable.SetValue("dg.objectClassIri", classIri);
}
global::Grasshopper.Instances.InvalidateCanvas();
```
For Accept: `doc.ValueTable.SetValue($"dg.recognized.{group.InstanceGuid}", "true")` on the restyled/renamed permanent group (RESEARCH.md Pattern 4, lines 344-362) — same idiom, new key namespace (`dg.recognized.<guid>` instead of `dg.objectClassIri`). Consider also stashing `dg.recognized.{guid}.provider`/`.timestamp` at zero extra cost (RESEARCH.md's forward-compat note for CGPD-03).

**Reject**: remove the preview `GH_Group` + its scribble cleanly — mirror the undo-record + `doc.RemoveObject(...)` pattern (not directly excerpted above; consult `EntityTagComponent.cs`'s `DetachFromStaleHosts` at line 455 for the closest existing "remove from group" precedent before writing new removal logic).

---

### `CanvasAnnotationStyles.cs` (additive)

**Analog:** itself — `Preview()` already exists (lines 53-59, full text above). Add only a `"[?] "` prefix constant (e.g. `public const string PreviewPrefix = "[?] ";`) next to it; do not touch `ForKind`/the five `Color` constants.

---

### `CanvasContextExtractor.cs` / `CanvasAnnotationParser.cs` (additive `Source` propagation)

**Not yet read in this pass** — RESEARCH.md's Pattern 4 (lines 344-364) gives the exact target shape:
```csharp
// In CanvasContextExtractor.TryAddGroup:
var isRecognized = doc.ValueTable.GetValue($"dg.recognized.{group.InstanceGuid}", "false") == "true";
// -> set RawGroup.Recognized = isRecognized

// In CanvasAnnotationParser.Parse (DG.Core, GH-free):
// read RawGroup.Recognized, set typed entity's Source = recognized ? "recognized" : "tagged"
```
**Hard constraint (Phase 34-01 lock):** this is the one place Phase 35 touches previously-frozen Phase 32/34 code — must be a single additive optional-field read, never a change to the nickname-classification regex. `CanvasAnnotationParserTests.cs`/`CanvasAnnotationNameFactoryTests.cs`/`FrameFixtureTests.cs` must pass unmodified as a regression gate.

---

### `data-service/tests/test_cg_recognition.py` (new)

**Analog:** `data-service/tests/test_dg_context.py` — `TestValidator` (L408), `TestRetryLoop` (L578), `_FakeAdapterForRetry` (L559)

Mirror the class-per-concern shape: a `TestValidator`-equivalent class exercising `validate_proposed_structure()` directly (bad-shape, missing-field, unknown-member-id, tagged-overlap cases), and a `TestRetryLoop`-equivalent class using a fake adapter (mirroring `_FakeAdapterForRetry`) to assert the bounded-retry count and that corrective feedback is appended to the *original* prompt each attempt (not accumulated). Add a `TestExtractJson`-style class (no existing analog — new territory per Pitfall 1) covering: bare JSON, markdown-fenced JSON, JSON with leading/trailing prose, and malformed JSON producing a `bad_json` violation.

---

## Shared Patterns

### LLM provider-agnostic call + bounded retry
**Source:** `data-service/dg_context.py` lines 880-922 (`generate_validated_cypher`) + lines 860-877 (`append_corrective_feedback`)
**Apply to:** `cg_recognition.py`'s `recognize_structure()`
Key invariant: never re-POST to `/llm/generate` on retry; call `adapter.generate()` in-process each attempt using the same `resolve_active_provider()`/`get_adapter()` resolved once before the loop.

### Structured error response (What+Where+How-to-fix)
**Source:** `data-service/app.py` `map_provider_error(exc)` + `_structured_error_response(...)` (used at lines 1346-1348); C# side: `ErrorMessageTemplates` (referenced in RESEARCH.md, not yet read — locate via `graphify explain "ErrorMessageTemplates"` before use in planning if exact excerpt needed)
**Apply to:** all new error paths in `cg_recognition.py`, the new `POST /computgraph/recognize` route, and any new C# handler failure branches.

### GH document undo record + group mutation
**Source:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs` lines 411-426 (`GH_UndoRecord` + `GH_AddObjectAction` + `UndoServer.PushUndoRecord`)
**Apply to:** `HandlePreviewStructure` (one record wrapping all proposal groups + legend scribble) and `StructureConfirmComponent`'s Accept/Reject mutations.

### `GH_Document.ValueTable` per-document persisted key/value
**Source:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs` lines 122-129, 174-179 (`ValueTable.GetValue`/`SetValue` + `Grasshopper.Instances.InvalidateCanvas()`)
**Apply to:** `source: recognized` marker write (`StructureConfirmComponent` on Accept) and read (`CanvasContextExtractor.TryAddGroup`).

### `#if GRASSHOPPER_SDK` conditional compilation
**Source:** every file in `DG/src/DG.Grasshopper/Components/` and `Canvas/` (e.g. `CanvasAnnotationStyles.cs` line 1 / line 61 `#endif`)
**Apply to:** `StructureConfirmComponent.cs`, `PreviewRegistry.cs`, and all additions to `CanvasListenerComponent.cs`.

### Internal static class idiom for shared canvas-scoped state/constants
**Source:** `DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs` (whole file)
**Apply to:** `PreviewRegistry.cs`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `DG/tests/DG.Tests/PreviewRegistryTests.cs` | test | CRUD | `DG.Tests` (net9.0) cannot reference `DG.Grasshopper` (net7.0-windows, NU1201 TFM incompatibility) — no existing unit test covers any `DG.Grasshopper`-tier GH_Component/registry; existing precedent is that this class of logic is validated via manual live-Rhino UAT only (`EntityTagComponent` itself has zero unit tests). If `PreviewRegistry`'s pure data-shape logic (proposal dedup, status transitions) can be extracted into a DG.Core-referenceable type, a DG.Core-side test becomes possible — otherwise scope this as UAT-only, consistent with Phase 33/34. |
| JSON-extraction-from-LLM-text logic (`_extract_json` helper inside `cg_recognition.py`) | utility | transform | No existing precedent anywhere in the codebase — every prior LLM call site (n8n `rules-to-metagraph.json`, `dg_context.generate_validated_cypher`) explicitly instructs plain-text (Cypher) output, never JSON. This is new code with no analog; RESEARCH.md's own inline sketch (Pitfall 1) is the template to use instead of a codebase analog. |

## Metadata

**Analog search scope:** `data-service/` (dg_context.py, app.py, gh_bridge.py, llm_gateway.py, tests/test_dg_context.py, tests/test_gh_bridge.py), `DG/src/DG.Grasshopper/Components/` (EntityTagComponent.cs, CanvasListenerComponent.cs, ObjectMarkerComponent.cs), `DG/src/DG.Grasshopper/Canvas/` (CanvasAnnotationStyles.cs)
**Files scanned:** 8 read directly (2 read partially with offset/limit) + 2 graphify queries for orientation
**Pattern extraction date:** 2026-07-19
