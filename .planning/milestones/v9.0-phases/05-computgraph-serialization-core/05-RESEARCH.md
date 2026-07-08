# Research: Canvas → Computgraph Serialization (Phases 5–10 shared reference)

**Date:** 2026-07-08. Sources: `ontology/DesignGrammar-V7.owl`, user's annotated Frame screenshot, https://github.com/alfredatnycu/grasshopper-mcp (protocol reference), repo exploration.

---

## 1. grasshopper-mcp bridge — protocol reference (adapted, not vendored)

Architecture of the reference project:
- **C# side:** `GH_MCP` Grasshopper component hosts a **TCP server** inside Rhino (default localhost:8080 in the original; DG uses **8720** to avoid clashing with the DG UI on :8080).
- **Python side:** an MCP bridge server forwards MCP tool calls to the TCP socket.
- **Wire format:** newline-terminated JSON per command: `{"type": "<command>", "parameters": {...}}` → JSON response (UTF-8, BOM-tolerant decode).
- **Original tool set (14):** add_component, connect_components, clear/save/load_document, get_document_info, get_component_info, get_all_components, get_connections, search_components, get_component_parameters, validate_connection, create_pattern, get_available_patterns. Plus a component knowledge base (parameter/connection rules) and pattern-based intent recognition.

**DG adaptation decisions:**
- Re-implement natively in `DG.Grasshopper` (no second plugin, no fork); data-service acts as the "bridge server", reusing its existing `POST /mcp` JSON-RPC server.
- v9.0 command set is **read + preview only**: `get_canvas_context`, `get_selection`, `preview_structure`, `clear_preview`, `get_preview_status`. Write commands (`add_component`, `connect_components`, …) are **deferred to v10** (Script Intelligence seed).
- Keep the wire format identical (`{type, parameters}`, newline-terminated) so v10 can extend the same listener with the reference implementation as a guide.
- Canvas access must be marshalled: `RhinoApp.InvokeOnUiThread` (the TCP accept loop runs on a worker thread).

## 2. Ontology map — Computgraph layer (`DesignGrammar-V7.owl`)

Prefixes: `dg = http://example.org/design-grammar#`, `dgc = .../design-grammar/comp#`.

| OWL entity | Line ≈ | Meaning / GH mapping |
|---|---|---|
| `dg:Object` / `dg:Function` / `dg:Behavior` / `dg:Structure` | 2277–2298 | FBS band; Behavior IS the parametric definition |
| `dgc:Algorithm` | 2307 | whole GH definition ("1_Algorithm") |
| `dgc:Procedure` | 2314 | GH Group/Cluster ("11_Proc - 2D Truss Configuration") |
| `dgc:Pattern` | 2321 | GH component / small node block; nestable |
| `dgc:Parameter` → `VariableParam` / `ConstantParam` / `EmergentParam` | 2332–2362 | slider/toggle · fixed preset · computed output |
| `dgc:Interface` → `Input` / `Output` (disjointUnionOf) | 2369–2391 | inter-procedure connectors |
| `dgc:ParamDataTypeValue` individuals | 2414–2453 | Float, Integer, Text, Boolean, Geometry |
| `dgc:ListStructureValue` individuals | 2457–2490 | Flatten, Graft, Simplify, Reverse |

Relations: `dg:hasBehavior` (Object→Behavior, 2509) · `dgc:hasAlgorithm` (Behavior→Algorithm, functional, 2530) · `dgc:hasProcedure` (2540) · `dgc:hasPattern` (2549) · `dgc:patternHostTo` (Pattern→Pattern nesting, 2558) · `dgc:hasInterface` ({Alg/Proc/Pat}→Interface, 2567) · `dgc:hasParameter` (Pattern→Parameter, 2583) · `dgc:paramLink` (Parameter→Interface, 2592) · `dgc:attributeOf` (cross-layer Atom→Parameter bridge, 2621). Datatype props: `dg:objectName`, `dgc:algorithmName/procedureName/patternName/parameterName/interfaceName` (2640+, functional).

**Neo4j label mapping (Phase 9):** strip prefixes — labels `Object|Behavior|Algorithm|Procedure|Pattern|Parameter|Interface` + `graph:'Computgraph'` + `project`; enum values become properties (`paramKind`, `dataType`, `ifaceType`, `listStructure`); relations upper-snake (`HAS_BEHAVIOR`, `HAS_ALGORITHM`, `HAS_PROCEDURE`, `HAS_PATTERN`, `PATTERN_HOST_TO`, `HAS_PARAMETER`, `HAS_INTERFACE`, `PARAM_LINK`).

## 3. Frame worked example — screenshot ↔ OWL individuals

The OWL already models the screenshot (individuals from line ~2720):

| Canvas annotation (screenshot) | OWL individual |
|---|---|
| Scribble `OBJECT - FRAME` | `dg:Object_Frame` (→ `dg:Behavior_Frame`, `dg:Structure_Frame`) |
| Scribble `1_ALGORITHM` | `dgc:Algorithm_1` |
| Group `11_Proc - 2D Truss Configuration` | `dgc:Proc_11` |
| Group `12_Proc - 2D Footer Configuration` | `dgc:Proc_12` |
| Purple nested groups `11_Pat_DivideLine`, `11_Pat_TopChord`, … | `dgc:Pat_11_DivideLine`, `dgc:Pat_11_TopChord` |
| `12_Pat_1 Create footer bottom lines` | `dgc:Pat_12_FooterBottomLines` |
| White `11_IntF_ParSplitAt` / `11_IntF_TrussConfig` / `11_IntF_MergeRes` / `12_...FooterFrame` | `dgc:IntF_11_ParSplitAt` / `IntF_11_TrussConfig` / `IntF_11_MergeRes` / `IntF_12_FooterFrame` |
| Pink `11_Var_SpansCount`, `11_Var_LenTotal`, `11_Var_Mode`, `11_Var_HTotal`, `12_Var_HFooter`, `12_Var_FooterCount` | VariableParams |
| Pink `11_Const_ptZero`, `11_Const_vecY`, `11_Const_SplitPar`, `11_Const_TrussConfig`, `11_Const_Divider`, `12_Const_IndList_1/2`, `12_Const_TrussConfig` | ConstantParams |
| Pink `11_Emg_DivPoints`, `11_Emg_ParamAt`, `11_Emg_LineSDL`, `11_Emr_UpperChord` (typo: Emr), `11_Emg_TopFrame`, `11_Emg_VertPost`, `12_Emg_BottomLn/TopLn/FooterUnit/FooterFrame` | EmergentParams |

Observed color convention: Procedure container = white/light panel; Pattern = orange group; nested Pattern = purple; Parameter (all kinds) = pink; Interface = white; yellow scribble-like labels = pattern name callouts.

## 4. Annotation-convention grammar (draft for CanvasAnnotationParser)

```
object     := "OBJECT - " NAME                     (scribble)
algorithm  := DIGIT "_ALGORITHM"                   (scribble)
procedure  := NN "_Proc - " NAME                   (group)
pattern    := NN "_Pat_" IDX (" " NAME)?           (group; nesting via group containment)
variable   := NN "_Var_" NAME                      (group, pink)
constant   := NN "_Const_" NAME                    (group, pink)
emergent   := NN ("_Emg_"|"_Emr_") NAME            (group, pink; Emr = tolerated variant)
interface  := NN "_IntF_" NAME                     (group, white)
NN         := algorithm-digit procedure-ordinal    (e.g. "11", "12")
```
Non-matching group/scribble names → untagged set + warning. Names may contain spaces/underscores after the prefix.

## 5. cgContextJson v1 — draft envelope

```jsonc
{
  "schemaVersion": "cg-context-1",
  "project": "my-project",
  "definition": { "documentId": "GUID", "fileName": "frame.gh", "capturedAt": "ISO8601" },
  "object": { "name": "FRAME", "classIri": null, "source": "tagged" },
  "algorithms": [{ "index": 1, "name": "1_ALGORITHM",
    "procedures": [{
      "id": "cg:1:proc:11", "index": 11, "name": "2D Truss Configuration", "source": "tagged",
      "memberIds": ["<instanceGuid>", "..."],
      "patterns": [{ "id": "cg:1:pat:11_1", "label": "11_Pat_1", "name": null,
                     "hostPatternId": null, "memberIds": ["..."], "source": "tagged" }],
      "parameters": [{ "id": "cg:1:par:11_Var_SpansCount", "kind": "Variable",
                       "name": "SpansCount", "dataType": "Integer",
                       "domain": { "min": 1, "max": 20, "step": 1 },
                       "memberIds": ["..."], "source": "tagged" }],
      "interfaces": [{ "id": "cg:1:intf:11_ParSplitAt", "name": "ParSplitAt",
                       "ifaceType": "Output", "memberIds": ["..."], "source": "tagged" }]
    }]
  }],
  "untagged": { "nodeIds": ["..."], "groups": [{ "nickname": "raw name", "memberIds": ["..."] }] },
  "nodes": [{ "instanceId": "GUID", "componentGuid": "GUID", "name": "Divide Curve",
              "nickname": "Divide", "position": [x, y] }],
  "wires": [{ "fromNode": "GUID", "fromParam": "GUID", "toNode": "GUID", "toParam": "GUID" }],
  "warnings": ["'11_Emr_UpperChord' normalized to Emergent (Emr→Emg)"]
}
```
`source` per entity: `tagged` (manual convention group) | `recognized` (Phase 8, after confirmation). Ids are deterministic (`cg:<alg>:<kind>:<conventionName>`) — these become the Phase 9 MERGE keys together with `definition.documentId`.

## 6. Proposed-structure JSON (Phase 8 contract, draft)

Recognition returns the same entity shapes as §5 but wrapped as proposals:
```jsonc
{ "proposals": [{ "kind": "Pattern", "suggestedName": "11_Pat_VecList_Arch",
                  "procedureIndex": 11, "memberIds": ["..."],
                  "confidence": 0.82, "rationale": "..." }],
  "unrecognized": [{ "memberIds": ["..."], "reason": "..." }] }
```
Schema-validated in data-service before any preview command is sent to the canvas (bounded retry through the gateway, mirroring the CTXA-04 validator pattern).

## 7. Existing code to reuse

| Need | Reuse |
|---|---|
| HTTP publish from plugin | `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` pattern (static HttpClient, camelCase JSON, `{dataServiceUrl}` input) |
| JSON serializer conventions | `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` |
| Neo4j repository pattern | `DG/src/DG.Core/Data/Neo4jOntoGraphRepository.cs` |
| LLM calls | `data-service/llm_gateway.py` (`POST /llm/generate`, Phase 1 ✅) |
| MCP server | `data-service/app.py` `POST /mcp` (JSON-RPC; extend `tools/list` + `tools/call`) |
| Component scaffolding | any `#if GRASSHOPPER_SDK` component in `DG/src/DG.Grasshopper/Components/` + `DgComponentCategory` + `DgIcons` |
