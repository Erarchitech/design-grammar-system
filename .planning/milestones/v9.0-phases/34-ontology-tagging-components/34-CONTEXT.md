# Phase 34 Context: Ontology Tagging Components and Manual Selection

**Milestone:** v9.0 AI Workflow Intelligence (restructured 2026-07-08)
**Requirements:** TAGC-01..03
**Depends on:** Phase 32 (convention grammar is the contract). Parallel-safe with Phase 33.

## What this phase is

The architect's half of the tag→recognize→preview→confirm pipeline: DG components that turn *manual canvas selection* into convention-conformant annotations (groups + scribbles) that the Phase 32 parser reads back as ground truth. What the user tags is authoritative; the LLM (Phase 35) only fills the gaps.

## Decided

1. **`Canvas/CanvasAnnotationStyles.cs`** (DG.Grasshopper): single source for group colors per entity kind, matched to the Frame reference screenshot — Procedure = white/light container; Pattern = orange; nested Pattern = purple; Parameter (Var/Const/Emg) = pink; Interface = white. Also the preview style used by Phase 35 (distinct, desaturated/dashed) lives here so confirm = restyle.
2. **DG OBJECT MARKER** (`Components/ObjectMarkerComponent.cs`):
   - Inputs: `ObjectName` (text), optional `Class` (OntologyClass from ONTOGRAPH deconstruct — binds `dg:Object` to a `dg:Class` IRI), `AlgorithmIndex` (int, default 1)
   - Behavior: creates or updates the `OBJECT - <NAME>` and `<n>_ALGORITHM` scribbles (top-left placement, large font per screenshot); on an already-annotated canvas it *reads* and reports existing markers — never duplicates
   - Outputs: `ObjectName`, `AlgorithmIndex`, `Status`
3. **DG ENTITY TAG** (`Components/EntityTagComponent.cs`):
   - Inputs: `Kind` (value-list: Proc | Pat | Var | Const | Emg | IntF), `Name` (text), `ProcIndex` (int; for Proc kind this is the new procedure ordinal), `Tag` (button)
   - On button press: takes the **current canvas selection** (`OnPingDocument()` selected objects), wraps it in a `GH_Group` named per the convention (`<NN>_<Kind>_<Name>` / `<NN>_Proc - <Name>`), colored from `CanvasAnnotationStyles`, auto-incrementing the pattern index (`next free 11_Pat_k`) when Name is empty for Pat kind
   - Wrapped in a `GH_UndoRecord` — Ctrl+Z removes the tag cleanly
   - Outputs: `GroupName`, `MemberCount`, `Status`
   - Guard rails: empty selection → warning, no group; selection spanning two existing Proc groups for a non-Proc tag → warning listing the conflict
4. Both components: sealed `GH_Component`, `#if GRASSHOPPER_SDK` + stub, DG category/subcategory (`DgComponentCategory`), icons in `DgIcons`, new stable GUIDs (document them — the v2.0 GUID-drift gotcha).

## Constraints

- Components **emit** the convention; they must never introduce a name the Phase 32 parser can't read (share the grammar via DG.Core — e.g. a `CanvasAnnotationNameFactory` next to the parser, so write and read use one definition).
- Tagging never writes to Neo4j and never calls data-service — canvas-only.
- Nested patterns: tagging a selection inside an existing Pat group creates the purple nested style automatically (host = enclosing group).
- Re-tagging (same name) updates group membership instead of erroring.

## Open for planning

- UX for retag/rename/delete: dedicated small component vs relying on native GH group editing (leaning native: groups stay ordinary GH groups on purpose).
- Whether DG OBJECT MARKER should also emit a hidden metadata object (e.g. a `GH_Panel` or document user-data) carrying the `dg:Class` IRI, since scribbles carry only text. Preferred: document `UserData`/`ValueTable` keyed `dg.objectClassIri` — survives file save, invisible on canvas.
- Auto-suggest `ProcIndex` from marker's AlgorithmIndex + existing Proc groups.

## Verification sketch

Tag a slider selection as Var "SpansCount" under proc 11 → pink group `11_Var_SpansCount` appears; run the Phase 32 extractor → entity appears as `CgParameter{kind:Variable, source:tagged}`; Ctrl+Z removes the group; DG OBJECT MARKER re-run reports the existing scribbles without creating duplicates.
