# Phase 32 Context: Computgraph Serialization Core

**Milestone:** v9.0 AI Workflow Intelligence (restructured 2026-07-08)
**Requirements:** CGSR-01..04
**Depends on:** nothing in v9.0 (LLM-free, network-free) — can start immediately.

## What this phase is

The pure-logic foundation of the canvas→Computgraph pipeline: an object model, an annotation-convention parser, a JSON serializer, and a GH_Document extractor. Everything downstream (bridge, tagging, recognition, persistence) speaks the `cgContextJson v1` document defined here.

## Decided

1. **Object model lives in DG.Core** (`DG/src/DG.Core/Models/Computgraph/`), zero Grasshopper dependencies, mirroring `ontology/DesignGrammar-V7.owl` lines ~2247–2670:
   - `CgObject` (name, optional classIri) → implicit `CgBehavior` → `CgAlgorithm` (index, name)
   - `CgProcedure` (index `NN`, name) → `CgPattern` (nestable via host reference ⇒ `dgc:patternHostTo`)
   - `CgParameter` — `ParamKind` enum {Variable, Constant, Emergent} (⇒ `dgc:VariableParam/ConstantParam/EmergentParam`); `ParamDataType` enum {Float, Integer, Text, Boolean, Geometry} (⇒ `dgc:ParamDataType_*` individuals); slider domain (min/max/step) when the underlying component is a slider
   - `CgInterface` — `IfaceType` enum {Input, Output} (⇒ `dgc:Input/Output`)
   - `CgNode` (raw canvas component: instance GUID, component GUID, name, nickname, position) and `CgWire` (source node/param → target node/param) — the untyped substrate every entity references by member ids
2. **Parser in DG.Core**: `Parsing/CanvasAnnotationParser.cs`. Grammar (case-sensitive prefixes, regex-based; full grammar in `32-RESEARCH.md`):
   - Scribble `OBJECT - <NAME>` → CgObject; scribble `<n>_ALGORITHM` → CgAlgorithm
   - Group `<NN>_Proc - <Name>` → Procedure; `<NN>_Pat_<k>[ <name>]` → Pattern; `<NN>_Var_<Name>` / `<NN>_Const_<Name>` / `<NN>_Emg_<Name>` → Parameter kinds; `<NN>_IntF_<Name>` → Interface
   - `NN`'s first digit = algorithm index, rest = procedure ordinal (e.g. `11` = algorithm 1, procedure 1)
   - Tolerate the screenshot's observed typo class (`11_Emr_UpperChord`): accept `Emg|Emr` for Emergent but emit a normalization warning
   - **Anything non-conforming → untagged set.** The parser never guesses; guessing is Phase 35's job (LLM) with human confirmation.
3. **Serializer in DG.Core**: `Serialization/ComputgraphContextSerializer.cs`, `System.Text.Json` camelCase — same conventions as `DesignStatePayloadV2Serializer`. Envelope carries `schemaVersion: "cg-context-1"`, project, definition id (document GUID + file name), capture timestamp, entities (with `source: tagged` per-entity), untagged nodes, wires, warnings.
4. **Extractor in DG.Grasshopper** (`Canvas/CanvasContextExtractor.cs`, `#if GRASSHOPPER_SDK`): traverses `GH_Document.Objects`; groups via `GH_Group.ObjectIDs` (nesting = a group id inside another group's ObjectIDs); scribbles via `GH_Scribble.Text`; wires via `IGH_Param.Sources` on every component input and floating param; slider domain via `GH_NumberSlider.Slider.Minimum/Maximum` etc. Extractor produces raw structures; classification happens in DG.Core (keeps GH surface minimal and logic testable).
5. **Fixture:** the Frame example. Build it as a checked-in JSON document (extractor output shape) under `DG/tests/DG.Tests/Fixtures/frame-cg-context.json`, asserting the parse matches the OWL named individuals (`dg:Object_Frame`, `dgc:Algorithm_1`, `dgc:Proc_11`, `dgc:Proc_12`, `Pat_11_DivideLine`, `Pat_11_TopChord`, `IntF_11_ParSplitAt`, `IntF_11_TrussConfig`, `IntF_11_MergeRes`, `Pat_12_FooterBottomLines`, `IntF_12_FooterFrame`, plus Var/Const/Emg parameters per the screenshot). A real annotated `.gh` file is kept in `test/` for manual E2E but is not a unit-test dependency.

## Constraints

- No LLM, no HTTP, no Neo4j in this phase.
- Follow the repo conditional-compilation rule: all GH-SDK code behind `#if GRASSHOPPER_SDK` with empty stub in `#else`.
- `cgContextJson v1` is a **versioned contract** — Phases 6/8/9 consume it; breaking changes require a version bump.
- Group membership is by component instance GUID; entities carry member ids, not copies of node data.
- Sliders/panels/value lists inside a `Var_/Const_` group define the parameter's dataType; multi-component parameter groups take the "primary" input component (slider > value list > panel) — record ambiguity as a warning, don't fail.

## Open for planning (`/gsd-plan-phase`)

- Exact regex set + unit-test matrix for the convention grammar (include Cyrillic/space/edge-case names).
- How pattern nesting maps when a purple group sits inside an orange group inside the Proc group (host chain depth > 1).
- Whether `CgWire` endpoints reference param indices or param instance GUIDs (GUIDs preferred — stable under param renames).

## Pointers

- Research: [32-RESEARCH.md](32-RESEARCH.md) — protocol/ontology/fixture reference, cgContextJson v1 draft schema
- Ontology: `ontology/DesignGrammar-V7.owl` (Computgraph block ~2247–2670; Frame individuals ~2720+)
- Serializer precedent: `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs`
- Component precedent: `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` (structure, guards, category)
