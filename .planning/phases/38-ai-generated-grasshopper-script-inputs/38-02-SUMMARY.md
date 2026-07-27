---
phase: 38-ai-generated-grasshopper-script-inputs
plan: 02
subsystem: computgraph
tags: [computgraph, canvas-extraction, publish, reinstate, join-a, dg-core, dg-grasshopper, data-service]

# Dependency graph
requires: [38-01]
provides:
  - "CgNode.InputParams (additive, optional) -- component input-param instance GUID + NickName + Name + Index, closing the gap that CgWire.ToParam was a bare GUID and CgNode.Nickname is the owning component's own nickname"
  - "ComputgraphContextSerializer round-trips InputParams via a nullable DTO array with [JsonIgnore(WhenWritingNull)], keeping schemaVersion at cg-context-1 and pre-Phase-38 payloads byte-identical"
  - "CanvasContextExtractor.ReadInputParams populates InputParams for every live-captured component"
  - "computgraph_publish.derive_reinstate_parameter_ids(cg_context) -> dict[cgId, reinstateParameterId], persisted as Parameter.reinstateParameterId at publish -- refuses (omits) rather than guesses on zero-match or ambiguous multi-match"
affects: [38-04, 38-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive-optional envelope field with [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] on the DTO property, not just a nullable-projection guard -- needed because System.Text.Json otherwise still emits \"key\":null for a null property, which would fail the byte-identical/no-token backward-compat contract"
    - "Refuse-don't-guess join derivation: zero matches or >1 distinct resolved value both omit the map entry; ambiguity logs one redacted warning (cgId + candidate count, never the raw competing NickName strings)"

key-files:
  created:
    - DG/src/DG.Core/Models/Computgraph/CgNodeInputParam.cs
  modified:
    - DG/src/DG.Core/Models/Computgraph/CgNode.cs
    - DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs
    - DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs
    - DG/tests/DG.Tests/ComputgraphContextSerializerTests.cs
    - data-service/computgraph_publish.py
    - data-service/tests/cg_fixtures.py
    - data-service/tests/test_computgraph_publish.py

key-decisions:
  - "CgNodeDto.InputParams needed an explicit [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] attribute (Rule 1 fix, found by the new backward-compat test) -- the global JsonSerializerOptions has no DefaultIgnoreCondition, so a plain nullable projection still emitted \"inputParams\":null, violating the plan's explicit 'no inputParams token' acceptance criterion"
  - "Used cg_context[\"nodes\"] / cg_context[\"wires\"] directly (top-level envelope keys), not cg_context[\"raw\"][\"wires\"] -- the plan flagged this key path as unconfirmed ('use the actual key path present in the parsed envelope'); the envelope has no raw wrapper, confirmed against cg_fixtures.py and test_computgraph_publish.py's existing fixture shape"
  - "PARAMETER_STATE_COMPONENT_GUID is a lowercase-hyphenated GUID literal (a2e8c4f1-6b3d-4a9c-8e5f-2d7b0c1a3f6e), matched case-insensitively against the node's componentGuid -- mirrors the default casing of C#'s Guid.ToString() that CanvasContextExtractor emits"
  - "Ambiguity warning is deliberately redacted to cgId + candidate count, never the raw competing NickName strings -- avoids echoing user-controlled canvas text into logs while still being diagnosable"
  - "cg_fixtures.py's Frame fixture gained a new PARAMETER STATE node + wire (not a mutation of the existing SpansCount->Interface wire) so the pre-existing PARAM_LINK-derivation test coverage stays untouched while JOIN A gets its own dedicated divergent-NickName exercise"

requirements-completed: [GHIN-02]

coverage:
  - id: D-02-truth
    description: "CanvasContextExtractor additively captures each component's input params as (instance GUID + NickName) pairs"
    requirement: GHIN-02
    verification:
      - kind: automated
        ref: "dotnet build ./DG/DG.sln -c Release (0 errors); grep -c 'Params.Input' CanvasContextExtractor.cs >= 1; ReadInputParams wrapped in try/catch"
        status: pass
    human_judgment: false
  - id: D-03-truth
    description: "Envelope stays schemaVersion cg-context-1; the new field is optional/additive; a v1 payload omitting it still deserializes"
    requirement: GHIN-02
    verification:
      - kind: automated
        ref: "dotnet test --filter FullyQualifiedName~ComputgraphContextSerializer -> 17/17 pass, including the new round-trip, omitted-key, and no-token tests"
        status: pass
    human_judgment: false
  - id: D-01-truth
    description: "computgraph_publish.py derives reinstateParameterId at publish time and persists it on the :Parameter node"
    requirement: GHIN-02
    verification:
      - kind: automated
        ref: "grep -c 'reinstateParameterId' computgraph_publish.py == 4; _publish_parameters Cypher SET contains p.reinstateParameterId = row.reinstateParameterId; python -m pytest test_computgraph_publish.py -q -> 12/12 pass"
        status: pass
    human_judgment: false
  - id: D-02-derivation-truth
    description: "Derivation walks slider component -> outgoing wire -> PARAMETER STATE component's input param, taking that input param's NickName (or param_{i} fallback) as reinstateParameterId"
    requirement: GHIN-02
    verification:
      - kind: automated
        ref: "test_derive_reinstate_ids_happy_path_with_divergent_names + test_derive_reinstate_ids_blank_nickname_falls_back_to_param_index, both passing"
        status: pass
    human_judgment: false
  - id: D-04-truth
    description: "A parameter whose reinstateParameterId cannot be resolved is published with the property absent, never guessed"
    requirement: GHIN-02
    verification:
      - kind: automated
        ref: "test_derive_reinstate_ids_no_wire_is_omitted, test_derive_reinstate_ids_wire_to_non_paramstate_component_is_omitted, test_derive_reinstate_ids_ambiguous_multi_match_is_omitted_with_one_warning, test_derive_reinstate_ids_malformed_context_returns_empty_dict_no_raise -- all passing"
        status: pass
    human_judgment: false
  - id: D-05-truth
    description: "Publish writes reinstateParameterId for every parameter it can resolve regardless of paramKind (no paramKind filtering at publish)"
    requirement: GHIN-02
    verification:
      - kind: other
        ref: "Source inspection: derive_reinstate_parameter_ids and _build_publish_params apply no paramKind filter; the row assignment is unconditional. Read-boundary filtering to Variable is explicitly out of scope for this plan per the plan's own D-05 note (enforced downstream at generation, not here)."
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 02: Close JOIN A -- Input-Param Capture and reinstateParameterId Derivation Summary

**Additive `CgNode.InputParams` capture on the canvas plus a refuse-don't-guess `derive_reinstate_parameter_ids` walk at publish time, closing the single biggest unscoped risk named in 38-RESEARCH.md 3.1: a Computgraph Parameter's convention name silently diverging from the NickName PARAMETER REINSTATE actually matches on.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 5
- **Files modified:** 7 (1 created)

## Accomplishments

- `CgNodeInputParam` (new file) carries `InstanceId`/`Nickname`/`Name`/`Index` per component input; `CgNode.InputParams` is an additive-optional `List<>` defaulted empty, documented as empty for pre-Phase-38 canvases.
- `ComputgraphContextSerializer` projects `InputParams` through a nullable `CgNodeInputParamDto[]?` with `[JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]` -- an empty list produces no `inputParams` key at all (not `"inputParams":null`), so an unchanged canvas serializes byte-identically to pre-Phase-38 output. `schemaVersion` stays `cg-context-1` throughout; a v1 payload lacking the key deserializes cleanly to an empty, non-null list.
- `CanvasContextExtractor.ReadInputParams` reads `Params.Input[i].InstanceGuid/NickName/Name` for every `IGH_Component`, wrapped in the file's existing guard-and-continue idiom at both the per-param and whole-scan level; floating params/sliders (no `Params.Input`) return an empty list. Wired into `TryAddNode`'s `CgNode` initializer.
- Three new xUnit tests pin the additive-field contract: round-trip preserves all four `InputParams` fields and ordering; a v1 payload with no `inputParams` key still deserializes to an empty list on every node; an empty `InputParams` list serializes with no `inputParams` token in the output JSON. All 17 tests in the file pass (14 pre-existing + 3 new).
- `computgraph_publish.derive_reinstate_parameter_ids(cg_context)` walks each Parameter's `memberIds` -> outgoing wires -> the destination node's `inputParams`, accepting a match only when the destination node's `componentGuid` equals the new module constant `PARAMETER_STATE_COMPONENT_GUID` (sourced from `ParameterStateComponent.ComponentGuid`). The resolved value is the input param's trimmed `nickname`, or `param_{index}` when blank -- mirroring `ParameterStateComponent.cs:68-71` exactly. Zero matches or an ambiguous multi-match both omit the parameter from the returned dict; ambiguity logs one redacted warning (cgId + candidate count, never the raw competing strings). The function never raises.
- `_build_publish_params` calls the derivation once and sets `row["reinstateParameterId"]` (value or `None`) on every parameter row; `_publish_parameters`' Cypher `SET` list persists `p.reinstateParameterId = row.reinstateParameterId` immediately after `p.dgId` -- a `null` value removes the property from the node, giving the intended "absent means unresolved" semantics with zero branching.
- `cg_fixtures.py`'s Frame fixture gained a new `PARAMETER STATE` node (`componentGuid = PARAMETER_STATE_COMPONENT_GUID`) with one input param whose `nickname` (`"Spans"`) deliberately diverges from the `SpansCount` parameter's convention-derived name, plus a wire from the SpansCount slider member into that input -- exercising JOIN A's actual failure mode rather than the trivially-equal case. `HTotal` deliberately has no such wire, exercising the "no wire -> omitted" refusal path.
- Seven new tests in `test_computgraph_publish.py` pin the derivation and every refusal case: happy path with divergent names, blank-nickname fallback to `param_{index}`, no-wire omission, wire-to-non-PARAMETER-STATE omission, ambiguous multi-match omission with exactly one warning, malformed-context (`{}` and `algorithms: None`) returning `{}` without raising, and the assembled `parameterRows` carrying `reinstateParameterId` present-with-`None` (not absent) for an unresolved parameter. 12/12 tests pass in the file (5 pre-existing + 7 new).

## Task Commits

Each task was committed atomically:

1. **Task 1: Additive input-param capture on CgNode** - `b440565` (feat)
2. **Task 2: Populate InputParams in the canvas extractor** - `7d4f0da` (feat)
3. **Task 3: Round-trip and backward-compatibility tests for the additive field** - `65860c3` (test)
4. **Task 4: Derive and persist reinstateParameterId at publish** - `7185a07` (feat)
5. **Task 5: Tests for the derivation and its refusal cases** - `a82d163` (test)

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `DG/src/DG.Core/Models/Computgraph/CgNodeInputParam.cs` - new model: InstanceId/Nickname/Name/Index
- `DG/src/DG.Core/Models/Computgraph/CgNode.cs` - added `InputParams` (additive, optional)
- `DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs` - `CgNodeInputParamDto`, `CgNodeDto.InputParams` (JsonIgnore-on-null), ToDto/FromDto projections
- `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` - `ReadInputParams` helper, wired into `TryAddNode`
- `DG/tests/DG.Tests/ComputgraphContextSerializerTests.cs` - 3 new tests (round-trip, backward-compat, no-token)
- `data-service/computgraph_publish.py` - `derive_reinstate_parameter_ids`, `PARAMETER_STATE_COMPONENT_GUID`, row/Cypher wiring
- `data-service/tests/cg_fixtures.py` - Frame fixture extended with `inputParams` + divergent-nickname wire
- `data-service/tests/test_computgraph_publish.py` - 7 new tests + a missing `sys.path.insert` fix for standalone runs

## Decisions Made

- `CgNodeDto.InputParams` required an explicit `[JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]` attribute, not just a nullable projection -- discovered as a test failure during Task 3 (the global serializer options have no `DefaultIgnoreCondition`, so `"inputParams":null` was still emitted, violating the plan's literal "no `inputParams` token" acceptance criterion). Fixed inline (Rule 1) before commit.
- Used the envelope's actual top-level `nodes`/`wires` keys (not a `raw` wrapper) for the publish-side walk -- the plan explicitly flagged this key path as unconfirmed; confirmed against the real serialized shape in `cg_fixtures.py` and the existing `_frame_cg_context()` fixture.
- `PARAMETER_STATE_COMPONENT_GUID` is matched case-insensitively (`.lower()` on both sides) against the node's `componentGuid`, since the C# extractor emits `Guid.ToString()`'s default lowercase-hyphenated form.
- Ambiguity warnings are deliberately redacted (cgId + count only) to avoid echoing user-controlled NickName text into logs while remaining diagnosable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `CgNodeDto.InputParams` emitted `"inputParams":null` instead of omitting the key**
- **Found during:** Task 3, writing the backward-compat/no-token tests
- **Issue:** A plain nullable projection (`Count == 0 ? null : ...`) still causes System.Text.Json to serialize the property as `"inputParams":null` under the module's `JsonSerializerOptions` (no `DefaultIgnoreCondition` set globally), which fails the plan's explicit acceptance criterion that no `inputParams` token appear for an unchanged canvas.
- **Fix:** Added `[JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]` to `CgNodeDto.InputParams` specifically (other nullable DTO properties like `Domain`/`DataType` intentionally keep emitting explicit `null` per existing test coverage, so a global option change was not appropriate).
- **Files modified:** `DG/src/DG.Core/Serialization/ComputgraphContextSerializer.cs`
- **Commit:** `65860c3`

**2. [Rule 3 - Blocking issue] `test_computgraph_publish.py` couldn't import `cg_fixtures` when run standalone**
- **Found during:** Task 5, first test run of the acceptance-criteria command in isolation
- **Issue:** The file only had `sys.path.insert(0, "..")` (the `data-service` dir); its sibling `test_cg_structure_checks.py` additionally inserts `os.path.dirname(__file__)` (the `tests` dir itself) so `from cg_fixtures import ...` resolves. Without the second insert, `python -m pytest data-service/tests/test_computgraph_publish.py -q` failed at collection with `ModuleNotFoundError: No module named 'cg_fixtures'` even though the combined multi-file run (which pytest's import-mode side effects had already primed) worked.
- **Fix:** Added the missing `sys.path.insert(0, os.path.dirname(__file__))` line, matching the established sibling-file precedent exactly.
- **Files modified:** `data-service/tests/test_computgraph_publish.py`
- **Commit:** `a82d163`

## Issues Encountered

None beyond the two auto-fixed items above.

## User Setup Required

None -- no external service configuration required. All verification ran locally: `dotnet build`/`dotnet test` for the C# side, `python -m pytest` for the Python side. The Neo4j-dependent integration suites in the same `data-service/tests/` directory (`test_cg_structure_checks.py`, `test_computgraph_consult.py`) still fail from the host with `ServiceUnavailable` -- confirmed pre-existing and unrelated to this plan's changes (the `neo4j` hostname only resolves inside the compose network; same baseline documented in STATE.md/CLAUDE.md).

## Next Phase Readiness

- Plan 38-04 (candidate generation / `boundParameters[]`) can now read `Parameter.reinstateParameterId` directly off the published `:Parameter` node instead of inferring a convention-name match -- the string is exactly what `ParameterReinstateComponent.cs:423-425`'s ordinal string equality matches on.
- Plan 38-07 (SC1 measurement) inherits a real divergent-name fixture (the Frame fixture's `SpansCount`/`"Spans"` pair) rather than only the trivially-equal case, so a future measurement pass exercising this path has genuine JOIN A coverage to draw on.
- No blockers. `spec/DATABASE.md`'s nullable `reinstateParameterId` contract (written in 38-01) is now backed by real code that actually populates it.

## Self-Check: PASSED

Verified all 8 modified/created files exist on disk and all 5 task commit hashes (b440565, 7d4f0da, 65860c3, 7185a07, a82d163) are present in `git log --oneline`.

---
*Phase: 38-ai-generated-grasshopper-script-inputs*
*Completed: 2026-07-27*
