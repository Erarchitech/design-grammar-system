# Phase 34: Ontology Tagging Components and Manual Selection - Research

**Researched:** 2026-07-18
**Domain:** Grasshopper (GH1/Rhino 8) SDK canvas mutation — GH_Group/GH_Scribble creation, undo records, value-list/button-style inputs — feeding the Phase 32 `CanvasAnnotationParser` grammar
**Confidence:** MEDIUM-HIGH (grammar/model contract and in-repo patterns are HIGH/VERIFIED; GH SDK write-path mechanics upgraded to HIGH-CITED via the Perplexity Verification Addendum — scribble creation, undo-record composition, and `GH_Document.ValueTable` metadata all confirmed against official API docs/McNeel forum working code; live-Rhino empirical confirmation still deferred to `checkpoint:human-verify`)

## Summary

Phase 34 is the "write" counterpart to Phase 32's "read" (`CanvasAnnotationParser`). The parser already fully defines the grammar these two components must emit — it was read directly from `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` and is authoritative (not inferred). The single highest-risk item is CONTEXT.md's own constraint: the components must never emit a name the parser can't read back identically. The parser currently builds its regexes from inline literal strings (not shared constants), so a new `CanvasAnnotationNameFactory` (DG.Core) cannot safely "just duplicate the string shapes" without risking silent drift — the recommended fix is a small preparatory refactor extracting the grammar's literal tokens (`"OBJECT - "`, `"_ALGORITHM"`, `"_Proc - "`, `"_Pat_"`, `"_Var_"`, `"_Const_"`, `"_Emg_"`, `"_IntF_"`) into shared internal constants that both `CanvasAnnotationParser`'s regex construction and the new factory's string-building reference.

The GH SDK mechanics themselves (creating a `GH_Group`, wrapping it in a `GH_UndoRecord`, reading current selection, deferring document mutation safely) have **no in-repo precedent** — this is new territory for the codebase. Two closely related precedents do exist and should be reused: (1) `CanvasListenerComponent`'s `ReadSelectedGuids()` for reading canvas selection via `obj.Attributes.Selected`, and (2) `ParameterReinstateComponent`'s rising-edge boolean trigger pattern plus its `doc.ScheduleSolution(...)`-deferred mutation, which web research confirms is not just a project convention but a **hard GH SDK constraint**: objects cannot be added to or removed from a `GH_Document` while a solution is in progress — mutations must be scheduled. Both new components should reuse `CanvasContextExtractor.ExtractRaw` + `CanvasAnnotationParser.Parse` to read the *current* canvas state (existing markers, existing Proc/Pat groups) rather than re-implementing scribble/group scanning by hand — this guarantees read/write symmetry by construction.

Two items are genuinely open and should go to the planner as explicit decisions rather than assumptions: (1) whether `EntityTagComponent`'s `ProcIndex` input is the full NN token (e.g. `"11"`) for every Kind including Proc, or an ordinal-only value for Proc that then needs an implicit algorithm digit from somewhere; (2) the exact hex colors for `CanvasAnnotationStyles` — CONTEXT.md and the Frame reference only name colors ("orange", "purple", "pink"), no screenshot or hex values are checked into the repo, so any hex chosen here is `[ASSUMED]` and needs human confirmation against the actual reference image before being locked.

**Primary recommendation:** Extract the grammar's literal tokens into shared DG.Core constants first (small, low-risk refactor of the existing 32-01/02 code), build `CanvasAnnotationNameFactory` and `CanvasAnnotationStyles` against those constants, then implement both components by composing already-proven in-repo patterns (rising-edge boolean trigger, `ScheduleSolution`-deferred mutation, `CanvasContextExtractor`/`CanvasAnnotationParser` for read-back) rather than inventing new idioms — the only genuinely novel SDK surface is `GH_Group`/`GH_Scribble` creation and `GH_UndoRecord`, which should get dedicated `checkpoint:human-verify` gates in the plan since this environment cannot run live Grasshopper to confirm behavior.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Convention name construction (`CanvasAnnotationNameFactory`) | DG.Core (GH-free) | — | Must be usable/testable without the GH SDK, symmetric with `CanvasAnnotationParser` (same tier it lives in) |
| Style/color constants (`CanvasAnnotationStyles`) | DG.Grasshopper (`Canvas/`) | — | Consumes `System.Drawing.Color`/GH types; not meaningfully GH-free, and Phase 35 preview styling also lives here |
| DG OBJECT MARKER / DG ENTITY TAG components | DG.Grasshopper (`Components/`, `#if GRASSHOPPER_SDK`) | — | Live `GH_Component` subclasses; canvas mutation, selection reading, undo |
| Canvas read-back (existing markers/groups) | DG.Grasshopper (`Canvas/CanvasContextExtractor` + DG.Core `CanvasAnnotationParser`) | — | Reuse Phase 32/33 pipeline verbatim — don't re-implement scanning |
| Neo4j / data-service | N/A this phase | — | Explicit constraint: tagging is canvas-only, never touches Neo4j or data-service |

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

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

### Constraints

- Components **emit** the convention; they must never introduce a name the Phase 32 parser can't read (share the grammar via DG.Core — e.g. a `CanvasAnnotationNameFactory` next to the parser, so write and read use one definition).
- Tagging never writes to Neo4j and never calls data-service — canvas-only.
- Nested patterns: tagging a selection inside an existing Pat group creates the purple nested style automatically (host = enclosing group).
- Re-tagging (same name) updates group membership instead of erroring.

### Claude's Discretion (Open for planning)

- UX for retag/rename/delete: dedicated small component vs relying on native GH group editing (leaning native: groups stay ordinary GH groups on purpose).
- Whether DG OBJECT MARKER should also emit a hidden metadata object (e.g. a `GH_Panel` or document user-data) carrying the `dg:Class` IRI, since scribbles carry only text. Preferred: document `UserData`/`ValueTable` keyed `dg.objectClassIri` — survives file save, invisible on canvas.
- Auto-suggest `ProcIndex` from marker's AlgorithmIndex + existing Proc groups.

### Deferred Ideas (OUT OF SCOPE)

None explicitly listed in CONTEXT.md beyond the milestone-level Out of Scope table (REQUIREMENTS.md): AI generation/editing of GH scripts, bridge write-commands (`add_component`, `connect_components`), GH Cluster introspection — none of these are touched by TAGC.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TAGC-01 | DG OBJECT MARKER creates/updates `OBJECT - <NAME>` and `<n>_ALGORITHM` scribbles (optionally bound to `dg:Class` IRI) and reads existing markers without duplicating | §"Annotation-convention grammar" (verbatim from `CanvasAnnotationParser.cs`); §"Read-before-write via the existing extractor/parser pipeline"; §"GH_Scribble creation" |
| TAGC-02 | DG ENTITY TAG wraps current manual canvas selection into a convention-named, convention-colored group for a chosen entity kind with automatic index assignment, undoable via undo records | §"Annotation-convention grammar"; §"GH_Group creation and coloring"; §"GH_UndoRecord / GH_Document.UndoUtil"; §"Reading canvas selection" |
| TAGC-03 | Manual tags round-trip as ground truth: tagged entities appear in `cgContextJson` with `source: tagged` and are parsed identically by the serializer on every re-run | §"Source=tagged is already the default everywhere" — verified in the DG.Core models; no new code needed beyond emitting conforming names |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Schema Change Propagation checklist does **not** apply to this phase (no graph schema/label/relationship change — canvas-only, no Neo4j writes).
- New GUIDs must be documented per the "v2.0 GUID-drift gotcha" (CLAUDE.md Known Gotchas) — confirmed unique via repo-wide grep before locking (Phase 33 precedent: `grep -rn "ComponentGuid =>"`).
- `#if GRASSHOPPER_SDK` conditional-compilation convention (CLAUDE.md Tech Stack / Known Gotchas) applies to both new components, matching every existing `DG.Grasshopper/Components/*.cs` file.
- DG category conventions (`DgComponentCategory.Category = "DG"`, subcategories) must be followed — no ad hoc category strings.

## Standard Stack

### Core

No new external packages. This phase is pure C#/.NET using APIs already referenced by the project:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| RhinoCommon / Grasshopper / GH_IO | Rhino 8 SDK (already referenced via `RhinoInstallDir` in `DG.Grasshopper.csproj`) | `GH_Component`, `GH_Group`, `GH_Scribble`, `GH_UndoRecord`, `GH_Document` | Already the project's only GH SDK dependency; `[VERIFIED: DG/src/DG.Grasshopper/DG.Grasshopper.csproj]` — confirmed present on this machine (`C:\Program Files\Rhino 8\System\RhinoCommon.dll` and `...\Plug-ins\Grasshopper\Grasshopper.dll` both exist, `GRASSHOPPER_SDK` will be defined) |
| .NET SDK | net7.0-windows (DG.Grasshopper), net9.0 (DG.Core/DG.Tests) | Existing multi-target split | `[VERIFIED: dotnet --version → 10.0.301 installed, supports both TFMs]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| xUnit | already referenced by DG.Tests | Unit-test `CanvasAnnotationNameFactory` (name construction, next-free-index logic) | Every new DG.Core class gets a matching `*Tests.cs`, per existing `CanvasAnnotationParserTests.cs` style |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native `GH_Group` nesting (a group's own InstanceGuid listed as a member of an outer group) for nested-Pattern detection | A custom "parent group id" property on a bespoke wrapper type | Native nesting is exactly what `CanvasContextExtractor.TryAddGroup` already reads (`other.InstanceGuid` inside `group.ObjectIDs` → `NestedGroupIds`) — a custom wrapper would require re-plumbing the already-shipped Phase 32/33 extractor. Use native nesting. |
| Rising-edge boolean `Tag` input (matches CONTEXT.md's own wording: "Use a Button or Boolean Toggle") | A true `GH_ButtonObject` special-object input | CONTEXT.md explicitly names this the same as `ParameterReinstateComponent`'s `Reinstate` input; `GH_ButtonObject` is a different SDK object (used for the on-canvas Button *component* itself, not a plain boolean param) and has no in-repo precedent. Reuse the proven rising-edge pattern instead of introducing a second UI idiom. |
| Auto-created `GH_ValueList` wired to `Kind` on first placement | A plain text/int input the user must self-validate | A pre-wired value list is standard GH plugin UX (confirmed via multiple community sources, `[CITED: james-ramsden.com, mcneel forum]`) and prevents typos in the 6-way enum; no in-repo precedent exists, so this is new SDK surface — flag for `checkpoint:human-verify`. |

**Installation:** No installation required — RhinoCommon/Grasshopper/GH_IO are referenced via `HintPath` against the local Rhino 8 install (already configured in `DG.Grasshopper.csproj`); no NuGet packages to add.

## Package Legitimacy Audit

**Not applicable this phase** — no new external packages (NuGet, npm, or otherwise) are introduced. All APIs used are already-referenced Rhino/Grasshopper SDK assemblies or existing project code.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │              Live GH_Document                │
                    │  (components, sliders, existing groups,      │
                    │   existing scribbles — architect's canvas)   │
                    └───────────────┬───────────────────────────────┘
                                    │
     ┌──────────────────────────────┼──────────────────────────────┐
     │  READ (before deciding create-vs-update)                    │
     │  CanvasContextExtractor.ExtractRaw(doc, project)            │
     │        → RawCanvas  →  CanvasAnnotationParser.Parse(raw)     │
     │        → CgContext (existing Object/Algorithms/Procedures)   │
     └──────────────────────────────┬──────────────────────────────┘
                                    │ inspect CgContext for existing
                                    │ markers / groups under target NN
                                    ▼
     ┌───────────────────────────────────────────────────────────────┐
     │  DG OBJECT MARKER (SolveInstance)                              │
     │  ObjectName, Class(IRI), AlgorithmIndex ──►                    │
     │    if existing "OBJECT - X" / "<n>_ALGORITHM" found → REPORT   │
     │    else → build scribble text via CanvasAnnotationNameFactory  │
     │           → doc.ScheduleSolution(1, _ => doc.AddObject(...))   │
     └───────────────────────────────────────────────────────────────┘

     ┌───────────────────────────────────────────────────────────────┐
     │  DG ENTITY TAG (SolveInstance, rising-edge Tag trigger)        │
     │  Kind, Name, ProcIndex, Tag(bool) ──►                          │
     │    on rising edge:                                            │
     │      1. selection = doc.Objects.Where(o=>o.Attributes.Selected)│
     │      2. empty? → Warning, no group                            │
     │      3. build NickName via CanvasAnnotationNameFactory         │
     │         (auto-increment Pat index if Name empty)               │
     │      4. existing group with same NickName? → update ObjectIDs  │
     │         else → new GH_Group, Colour from CanvasAnnotationStyles│
     │      5. detect host (selection ⊆ existing Pat group?) →        │
     │         nest (purple) by adding new group's guid to host group │
     │      6. GH_UndoRecord wraps steps 3-5                          │
     │      7. doc.ScheduleSolution(1, _ => { mutate; ExpireSolution})│
     └───────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
     Next canvas read (DG CANVAS LISTENER get_canvas_context, or the
     next DG OBJECT MARKER / DG ENTITY TAG run) sees the new group/
     scribble and CanvasAnnotationParser classifies it as `source:
     tagged` — no code change needed there; it already defaults to
     "tagged" on every Cg* model.
```

### Recommended Project Structure

```
DG/src/DG.Core/Parsing/
├── CanvasAnnotationParser.cs         # EXISTING (Phase 32) — read path
├── CanvasAnnotationGrammar.cs        # NEW — shared literal tokens (prefixes/infixes),
│                                     #   referenced by BOTH the parser's regex construction
│                                     #   and the new factory's string building
└── CanvasAnnotationNameFactory.cs    # NEW — write path: builds convention-conformant
                                      #   names + computes next-free indices; GH-free,
                                      #   pure string logic, fully unit-testable

DG/src/DG.Grasshopper/Canvas/
├── CanvasContextExtractor.cs         # EXISTING (Phase 32/33) — reused for read-before-write
└── CanvasAnnotationStyles.cs         # NEW — Color constants per entity kind + preview variant

DG/src/DG.Grasshopper/Components/
├── ObjectMarkerComponent.cs          # NEW — DG OBJECT MARKER
└── EntityTagComponent.cs             # NEW — DG ENTITY TAG

DG/tests/DG.Tests/
└── CanvasAnnotationNameFactoryTests.cs  # NEW — xUnit, mirrors CanvasAnnotationParserTests.cs style
```

### Pattern 1: Shared grammar tokens between read (parser) and write (factory)

**What:** `CanvasAnnotationParser`'s regexes currently embed the grammar's literal tokens directly inline (e.g. `"^OBJECT - (?<name>.+)$"`, `@"^(?<nn>\d+)_Pat_(?<idx>[^ ]+)( (?<name>.+))?$"`). CONTEXT.md's constraint #1 requires write and read to "use one definition." The lowest-risk way to guarantee this without destabilizing the already-shipped, tested parser is to extract just the literal tokens into named constants and have the *existing* regex pattern strings interpolate those constants — the regex shapes themselves don't change, so `CanvasAnnotationParserTests.cs` (11 passing tests) keeps passing unmodified.

**When to use:** Required preparatory refactor before writing `CanvasAnnotationNameFactory`.

**Example:**
```csharp
// Source: composed from DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs (existing code, this repo)
// NEW file: DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs
internal static class CanvasAnnotationGrammar
{
    public const string ObjectPrefix = "OBJECT - ";
    public const string AlgorithmSuffix = "_ALGORITHM";
    public const string ProcedureInfix = "_Proc - ";
    public const string PatternInfix = "_Pat_";
    public const string VariableInfix = "_Var_";
    public const string ConstantInfix = "_Const_";
    public const string EmergentInfix = "_Emg_";      // canonical
    public const string EmergentTolerated = "_Emr_";  // read-only tolerated variant
    public const string InterfaceInfix = "_IntF_";
}

// CanvasAnnotationParser.cs regex fields become (shape unchanged, tokens interpolated):
private static readonly Regex ObjectRegex = new(
    $"^{Regex.Escape(CanvasAnnotationGrammar.ObjectPrefix)}(?<name>.+)$",
    RegexOptions.Compiled | RegexOptions.CultureInvariant);
// ...same treatment for the other 7 regexes.
```
Then `CanvasAnnotationNameFactory` builds strings from the *same* constants — e.g. `CanvasAnnotationGrammar.ObjectPrefix + name.Trim()`, `nn + CanvasAnnotationGrammar.PatternInfix + idx + (name is null ? "" : " " + name)`, etc. Drift between read and write becomes structurally impossible for the token boundaries (spacing/casing/prefix text) — the main remaining risk is in the NN construction logic (see Pitfall 2 below), which is arithmetic, not textual.

### Pattern 2: Read-before-write via the existing extractor/parser pipeline

**What:** Both new components need to know "does this marker/group already exist" before deciding create vs. update. Rather than re-scanning `doc.Objects` by hand (duplicating `CanvasContextExtractor`'s traversal), call the exact same one-call seam `CanvasListenerComponent` already uses for reads: `CanvasContextExtractor.ExtractRaw(doc, project)` → `CanvasAnnotationParser.Parse(raw)` → inspect the resulting `CgContext.Object`, `.Algorithms`, and their nested `Procedures`/`Patterns`/`Parameters`/`Interfaces` for an entity matching the requested Kind/Name/NN.

**When to use:** `ObjectMarkerComponent.SolveInstance` (detect existing Object/Algorithm scribbles); `EntityTagComponent.SolveInstance` (detect existing group with the same NickName for re-tag semantics, and detect the next-free Pat index under a given NN).

**Example:**
```csharp
// Source: composed from DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs
// + DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs (existing code, this repo)
var raw = CanvasContextExtractor.ExtractRaw(OnPingDocument(), project: "");
var context = CanvasAnnotationParser.Parse(raw);

// ObjectMarkerComponent: does an OBJECT scribble already exist?
if (context.Object is not null)
{
    // report existing values, do not create a duplicate scribble
}

// EntityTagComponent: what's the next free Pat index under NN "11"?
var existingIndices = context.Algorithms
    .SelectMany(a => a.Procedures)
    .Where(p => p.Index == targetProcIndex)
    .SelectMany(p => p.Patterns)
    .Select(p => /* parse trailing numeric idx from p.Label via CanvasAnnotationGrammar */ 0)
    .ToList();
var nextFreeIdx = existingIndices.Count == 0 ? 1 : existingIndices.Max() + 1;
```
This guarantees the write path can never disagree with what the read path would report on the very next `get_canvas_context` call.

### Pattern 3: Rising-edge boolean trigger (reused verbatim from `ParameterReinstateComponent`)

**What:** `EntityTagComponent`'s `Tag` input is a plain `bool` `GH_ParamAccess.item` input, defaulting `false`, with a `_lastTagInput` field initialized to `true` (prevents auto-fire on first solve/file-open when the input happens to already be `true`). Fire only on `false → true` transition.

**When to use:** `EntityTagComponent.SolveInstance`, exactly mirroring `ParameterReinstateComponent`'s `_lastApplyInput`/`isRisingEdge` shape (see that file, lines 22, 120-135).

**Example:** `[VERIFIED: DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs:22,120-135]` — reuse this exact shape; do not introduce a `GH_ButtonObject`.

### Pattern 4: Deferred document mutation via `ScheduleSolution`

**What:** GH's own SDK constraint (not just a project convention): objects cannot be added to or removed from a `GH_Document` while a solution is in progress — the mutation must be scheduled to run before or after a solve, via `GH_Document.ScheduleSolution(int delayMs, Action<GH_Document> callback)`. This is already the established in-repo idiom for deferred mutation: `ParameterReinstateComponent.ScheduleWriteValues` (writing slider values) and `CanvasListenerComponent.ScheduleRefresh` (`doc.ScheduleSolution(1, _ => ExpireSolution(false))`).

**When to use:** Every `doc.AddObject(...)` call for a new `GH_Group`/`GH_Scribble`, and every membership mutation on an existing group, triggered from inside `SolveInstance`.

**Example:**
```csharp
// Source: pattern from DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs
// (ScheduleWriteValues) and CanvasListenerComponent.cs (ScheduleRefresh) — existing code,
// this repo — plus [CITED: mcneel forum "Deleting a component from the canvas": "You cannot
// delete objects from the document during a solution... schedule a solution and provide a
// callback method"] confirming this is an SDK requirement, not just a style choice.
var doc = OnPingDocument();
doc?.ScheduleSolution(1, currentDoc =>
{
    var record = new GH_UndoRecord("Tag Entity");
    // ... build actions, then mutate ...
    currentDoc.UndoUtil.RecordEvent(record); // or RecordAddObjectEvent, see Pattern 5
    ExpireSolution(false);
});
```

### Pattern 5: `GH_Group` creation, coloring, and undo

**What:** `[CITED: web search — james-ramsden.com, mcneel forum; no in-repo precedent]` The standard shape for creating a canvas group:
```csharp
var group = new Grasshopper.Kernel.Special.GH_Group();
group.NickName = conventionName;             // e.g. "11_Var_SpansCount"
group.Colour = CanvasAnnotationStyles.ForKind(kind); // System.Drawing.Color
doc.AddObject(group, false);
foreach (var guid in selectedGuids) group.AddObject(guid); // per-member GUID
```
Reading members back is already `[VERIFIED: DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs:171]` — `group.ObjectIDs` (a `List<Guid>`) is the property the extractor already reads, confirming `ObjectIDs` is real and populated by `AddObject`. Nesting is native: if the new (inner) group's own `InstanceGuid` is added as a member of an existing (outer) `GH_Group`'s `ObjectIDs` — i.e. `hostGroup.AddObject(newGroup.InstanceGuid)` — the extractor's existing nesting detection (`other.InstanceGuid` inside `group.ObjectIDs` → `NestedGroupIds`) picks it up automatically with zero extractor changes.

For undo: `[CITED: mcneel forum "Ins and Outs of Undo"]` — either the granular pattern (`new GH_UndoRecord(name)`, populate with `GH_AddObjectAction`/etc. *before* mutating, then `doc.UndoUtil.RecordEvent(record)`), or the simpler one-call helper `GH_Document.GH_UndoUtil.RecordAddObjectEvent(string name, IEnumerable<IGH_DocumentObject> objects)` for the common "I just added N objects" case. Given this phase only adds one `GH_Group` (and possibly registers it as a nested member of another), the simpler `RecordAddObjectEvent` helper is likely sufficient — confirm behavior with a `checkpoint:human-verify` task before relying on it for the Ctrl+Z acceptance criterion.

**When to use:** `EntityTagComponent`'s tag-creation step; `ObjectMarkerComponent`'s scribble-creation step (analogous, via `GH_AddObjectAction`/`RecordAddObjectEvent` for the scribble instead of a group).

### Pattern 6: Reading current canvas selection

**What:** Already proven in-repo. `[VERIFIED: DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:158-177]` `ReadSelectedGuids()` iterates `doc.Objects` and checks `obj.Attributes is { Selected: true }`. Reuse this exact shape (return the objects, not just GUIDs, so `EntityTagComponent` can pass them straight to `group.AddObject(obj.InstanceGuid)`).

**When to use:** `EntityTagComponent.SolveInstance`, on the rising edge of `Tag`.

### Anti-Patterns to Avoid

- **Re-implementing scribble/group scanning inside the new components** instead of reusing `CanvasContextExtractor.ExtractRaw` + `CanvasAnnotationParser.Parse` — this is exactly the kind of drift CONTEXT.md's constraint #1 warns about; two independent scanners will diverge over time.
- **Mutating `doc.Objects` directly inside `SolveInstance`** (adding/removing a `GH_Group`/`GH_Scribble` synchronously) — per Pattern 4, this is an SDK-level hazard, not just a style nit; always defer via `ScheduleSolution`.
- **Introducing a second "how do I get a user-triggered action" idiom** (`GH_ButtonObject`, a custom timer, etc.) when the rising-edge boolean pattern is already proven and explicitly endorsed by CONTEXT.md's own wording ("Use a Button or Boolean Toggle").
- **Constructing NN by arithmetic** (`algorithmIndex * 10 + procOrdinal`) — see Pitfall 2 below; the parser's `SplitNn` uses string-substring splitting (`nn.Substring(0,1)` / `nn.Substring(1)`), so NN must be built the same way (string concatenation) or multi-digit ordinals silently corrupt.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting whether a selection is already inside an existing Pattern group (nesting) | A custom "find enclosing group" tree walk with its own containment rules | Native GH group nesting — add the new group's own `InstanceGuid` as a member of the host group's `ObjectIDs`; `CanvasContextExtractor` already detects this via `NestedGroupIds` with zero changes needed | The read side already exists and is tested; a parallel containment concept in the write path would only need to agree with it, so use the same mechanism |
| User-triggered action (button) | `GH_ButtonObject` special object, custom debounce timer | Rising-edge boolean input, exactly like `ParameterReinstateComponent.Reinstate` | Proven in-repo pattern; CONTEXT.md explicitly names it |
| Deferred canvas mutation | Manual `Task.Delay` + retry loop, or direct mutation with try/catch around SDK exceptions | `GH_Document.ScheduleSolution(delayMs, callback)`, exactly like `ParameterReinstateComponent.ScheduleWriteValues` / `CanvasListenerComponent.ScheduleRefresh` | It's the documented SDK-correct way to mutate a document outside an active solve; ad hoc retry/catch around the constraint is fragile and unnecessary |
| Reading canvas selection | Custom canvas-widget hit-testing | `doc.Objects.Where(o => o.Attributes.Selected)`, exactly like `CanvasListenerComponent.ReadSelectedGuids` | Already proven, already the exact API GH itself uses for "Selected" state |

**Key insight:** This phase's actual net-new SDK surface is small (`GH_Group`/`GH_Scribble` creation + `GH_UndoRecord`) — everything else (trigger pattern, deferred mutation, selection reading, canvas read-back) already has a working, tested precedent two phases old in this exact codebase. Concentrate implementation risk and review attention on the group/scribble/undo mechanics, and gate them behind `checkpoint:human-verify` since no live Rhino session is available in this research/planning environment to confirm behavior empirically.

## Runtime State Inventory

Not applicable — this phase is not a rename/refactor/migration phase. It is greenfield (two new components, two new DG.Core/DG.Grasshopper files).

## Common Pitfalls

### Pitfall 1: Mutating the document synchronously inside `SolveInstance`
**What goes wrong:** `doc.AddObject(group, false)` (or removing/updating one) called directly inside `SolveInstance` either silently fails, corrupts iterator state over `doc.Objects`, or throws, because a solution is actively in progress.
**Why it happens:** It's the path of least resistance — `SolveInstance` already has `doc` in scope via `OnPingDocument()`.
**How to avoid:** Always wrap the actual `AddObject`/membership mutation in `doc.ScheduleSolution(1, currentDoc => { ... })`, matching `ParameterReinstateComponent.ScheduleWriteValues` exactly (see Pattern 4).
**Warning signs:** Group appears intermittently, or only after a second unrelated solve; `InvalidOperationException` on collection modification during enumeration.

### Pitfall 2: Constructing the NN token by arithmetic instead of string concatenation
**What goes wrong:** `CanvasAnnotationParser.SplitNn` parses NN as `nn.Substring(0,1)` (algorithm digit, always 1 char) + `nn.Substring(1)` (procedure ordinal, any remaining length) — e.g. `"110"` splits to algorithm `1`, ordinal `10`. If a component builds NN via `(algorithmIndex * 10 + procOrdinal).ToString()` instead of `algorithmIndex.ToString() + procOrdinal.ToString()`, ordinals ≥ 10 silently produce the wrong NN (e.g. alg=1, ordinal=10 → arithmetic gives `"20"` = alg 2, ordinal 0 — wrong; concatenation gives `"110"` = alg 1, ordinal 10 — correct).
**Why it happens:** `11`, `12` in the Frame example look like base-10 arithmetic (`alg*10 + ordinal`) when they're actually string concatenation that happens to coincide for single-digit ordinals.
**How to avoid:** Always build NN as `algorithmIndex.ToString(CultureInfo.InvariantCulture) + procOrdinal.ToString(CultureInfo.InvariantCulture)` (matching `SplitNn`'s inverse exactly), never via multiplication.
**Warning signs:** A tagged Procedure/Pattern/Parameter under ordinal ≥ 10 gets silently reassigned to the wrong algorithm/ordinal on the next parse.

### Pitfall 3: Hand-rolling the grammar's literal tokens in the new factory
**What goes wrong:** `CanvasAnnotationNameFactory` reimplements `"_Proc - "`, `"_Pat_"`, etc. as its own literals instead of sharing constants with `CanvasAnnotationParser`'s regexes — a future edit to one (e.g. a spacing fix) silently desyncs from the other.
**Why it happens:** The parser's regexes are currently `private` and inline — there's no shared constant to reuse without first doing the extraction (Pattern 1).
**How to avoid:** Do the `CanvasAnnotationGrammar` extraction refactor (Pattern 1) before writing the factory; both files reference the same constants.
**Warning signs:** `CanvasAnnotationParserTests.cs` still passes but a new round-trip test (factory output → parser input) fails, or passes only for the tested cases.

### Pitfall 4: Assuming `GH_Scribble` uses a simple `Attributes.Pivot` point like other components
**What goes wrong:** `GH_Scribble` is a resizable rectangular note (draggable corner-to-corner), not a point-anchored component — setting only a `Pivot` (as `CanvasContextExtractor.TryAddScribble` *reads*, for extraction purposes only) does not correctly *place/size* a newly created scribble for display; the actual bounds/corners and font-size API were not confirmed by primary documentation in this research session (community-plugin precedent only — MetaHopper's "Set Scribble Properties" component is the closest reference found).
**Why it happens:** `GH_Scribble.Attributes.Pivot` exists and is readable (confirmed via the existing extractor code), which invites the (wrong) assumption that scribble geometry is a single point like a normal component.
**How to avoid:** Treat scribble placement/sizing as a `checkpoint:human-verify` item — implement against the closest available reference (MetaHopper source, if inspectable) and confirm visually in live Rhino that the "top-left placement, large font" requirement (CONTEXT.md) renders correctly before considering the task done.
**Warning signs:** Scribble appears with default/tiny size, wrong position, or throws on construction.

### Pitfall 5: Exact colors don't match the Frame reference
**What goes wrong:** `CanvasAnnotationStyles` ships with plausible-but-wrong hex values because no screenshot or hex palette is checked into the repo — only color *names* ("orange", "purple", "pink", "white") are documented in `32-RESEARCH.md` §3 and `34-CONTEXT.md` decision #1.
**Why it happens:** The Frame reference is an external screenshot (referenced in prose, not committed as an image file in this repo — confirmed via repo-wide search for "frame"-named files, which only found the unrelated JSON/test fixture `frame-cg-context.json`).
**How to avoid:** Treat the specific hex values in this research (see Code Examples below) as placeholders `[ASSUMED]`; add a `checkpoint:human-verify` task comparing rendered groups against the actual Frame screenshot the user has, before locking the palette.
**Warning signs:** Colors are directionally right (orange is orange) but don't match the reference on close visual comparison.

## Code Examples

### `CanvasAnnotationStyles.cs` — placeholder palette (needs human verification against the Frame screenshot)

```csharp
// NEW file — DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs
// Colors are [ASSUMED] placeholders — CONTEXT.md/32-RESEARCH.md name colors ("orange",
// "purple", "pink", "white") but no hex palette or screenshot is checked into this repo.
// checkpoint:human-verify — compare against the actual Frame reference before locking.
#if GRASSHOPPER_SDK
using System.Drawing;

namespace DG.Grasshopper.Canvas;

internal static class CanvasAnnotationStyles
{
    public static readonly Color Procedure = Color.FromArgb(255, 245, 245, 245); // white/light
    public static readonly Color Pattern = Color.FromArgb(255, 243, 156, 18);     // orange
    public static readonly Color NestedPattern = Color.FromArgb(255, 155, 89, 182); // purple
    public static readonly Color Parameter = Color.FromArgb(255, 255, 182, 208);  // pink (Var/Const/Emg)
    public static readonly Color Interface = Color.FromArgb(255, 250, 250, 250);  // white

    // Phase 35 preview variant (this phase only needs to define the constant scaffold;
    // Phase 35 wires it into actual preview rendering). Desaturated + lower alpha is the
    // achievable technique via the public GH_Group.Colour API; true "dashed border" may
    // not be achievable without a custom IGH_Attributes override (Phase 35's problem).
    public static Color Preview(Color baseColor) =>
        Color.FromArgb(140, baseColor.R, baseColor.G, baseColor.B);
}
#endif
```

### `EntityTagComponent` — rising-edge trigger + deferred group creation (composed sketch)

```csharp
// Composed from proven in-repo patterns:
// - rising-edge trigger: DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs:22,120-135
// - selection reading: DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:158-177
// - deferred mutation: DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs
//   (ScheduleWriteValues) + CanvasListenerComponent.cs (ScheduleRefresh)
// - GH_Group API: [CITED: james-ramsden.com, mcneel forum] — no in-repo precedent
private bool _lastTagInput = true;

protected override void SolveInstance(IGH_DataAccess da)
{
    // ... read Kind, Name, ProcIndex ...
    bool tagInput = false;
    da.GetData(3, ref tagInput);
    var isRisingEdge = tagInput && !_lastTagInput;
    _lastTagInput = tagInput;
    if (!isRisingEdge) { /* report last status, return */ return; }

    var doc = OnPingDocument();
    if (doc is null) return;

    var selected = doc.Objects.Where(o => o.Attributes is { Selected: true }).ToList();
    if (selected.Count == 0)
    {
        AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "No objects selected — nothing tagged.");
        return;
    }

    doc.ScheduleSolution(1, currentDoc =>
    {
        var group = new Grasshopper.Kernel.Special.GH_Group
        {
            NickName = conventionName, // via CanvasAnnotationNameFactory
            Colour = CanvasAnnotationStyles.ForKind(kind, isNested),
        };
        currentDoc.UndoUtil.RecordAddObjectEvent("Tag Entity", new IGH_DocumentObject[] { group });
        currentDoc.AddObject(group, false);
        foreach (var obj in selected) group.AddObject(obj.InstanceGuid);
        if (hostGroup is not null) hostGroup.AddObject(group.InstanceGuid); // native nesting
        ExpireSolution(false);
    });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| N/A | N/A | — | This is a first-of-its-kind feature for the codebase (no prior "canvas tagging" component existed before Phase 34); no deprecated predecessor to migrate from. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `GH_Group.AddObject(Guid)`, `GH_Group.Colour` (System.Drawing.Color), `GH_Group.NickName`, and `doc.AddObject(group, false)` are the correct API shapes for creating/coloring a group | Pattern 5, Code Examples | Compile errors; plan should include a build-and-fix step, gated by `checkpoint:human-verify` in live Rhino |
| A2 | **RESOLVED (Perplexity, 2026-07-18):** Use the explicit composition — `new GH_UndoRecord("Tag Entity")` + `record.AddAction(new GH_AddObjectAction(obj))` per added object + `doc.UndoServer.PushUndoRecord(record)` (namespaces `Grasshopper.Kernel.Undo` / `.Actions`). No `RecordAddObjectEvent` exists on `GH_Document` in official API docs — do NOT plan against it. For ENTITY TAG only the group itself is a new document object (members already exist), so one `GH_AddObjectAction(group)` in the record undoes the whole tag. | Pattern 5, Addendum | Residual risk low; live-Rhino Ctrl+Z check stays as `checkpoint:human-verify` |
| A3 | **RESOLVED (Perplexity, 2026-07-18):** `Grasshopper.Kernel.Special.GH_Scribble` — construct, call `CreateAttributes()`, set `Text` and `Font` (`System.Drawing.Font`, size = large per screenshot), set `Attributes.Pivot` (`PointF`), then `doc.AddObject(scrib, false)` inside `ScheduleSolution`, finish with `Grasshopper.Instances.InvalidateCanvas()`. There is no writable `Bounds` — the scribble auto-sizes from Text+Font; placement is Pivot-only. | Pitfall 4, Addendum | Residual risk: exact rendered size needs live-Rhino confirmation only |
| A4 | **RESOLVED (Perplexity, 2026-07-18):** `GH_Document.ValueTable` (type `Grasshopper.Kernel.GH_SettingsServer`) is the official per-document key-value store — `doc.ValueTable.SetValue("dg.objectClassIri", iri)` / `GetValue(key, fallback)`; serialized into the .gh/.ghx file and reloads with it. Use a `dg.`-prefixed key namespace. No Rhino-document User Text needed. | Claude's Discretion item #2 in CONTEXT.md, Addendum | Residual risk minimal — official documented API |
| A5 | Exact hex colors for Procedure/Pattern/NestedPattern/Parameter/Interface | Code Examples, Pitfall 5 | Visual mismatch with the Frame reference screenshot; low functional risk (colors are directionally correct) but should be confirmed before considering the deliverable "done" |
| A6 | `ProcIndex` semantics: whether it is always the full NN token (recommended) or ordinal-only for Proc kind with an implicit algorithm digit from elsewhere | Open Questions | Ambiguous UX; if unresolved, the "auto-increment next free Pat index" logic and the Proc-tagging flow could disagree on what a given integer means |

**If this table is empty:** N/A — see entries above; every claim not directly read from this repo's own source files is listed here.

## Open Questions

1. **`ProcIndex` semantics for `EntityTagComponent`**
   - What we know: CONTEXT.md says `ProcIndex (int; for Proc kind this is the new procedure ordinal)`, and the phase's own Verification sketch says "Tag a slider selection as Var 'SpansCount' under procedure 11" — implying, for non-Proc kinds, the user supplies the full NN token (`"11"`), not just an ordinal.
   - What's unclear: For Proc kind specifically, is `ProcIndex` the ordinal only (needing an implicit algorithm digit sourced from, e.g., the current DG OBJECT MARKER's `AlgorithmIndex`), or is it also the full NN (user manually types `"11"` to create Procedure ordinal 1 under algorithm 1)?
   - Recommendation: Treat `ProcIndex` as the full NN token uniformly across all Kinds (including Proc) — simplest, most consistent UX, matches the Verification sketch's wording, and avoids needing cross-component state (marker → tag) at all. Confirm with the user/planner before locking; this is exactly the kind of decision `/gsd-discuss-phase` follow-up or the plan's own assumptions section should surface explicitly.

2. **~~Exact undo granularity needed for TAGC-02's Ctrl+Z acceptance criterion~~ — RESOLVED (see Perplexity Verification Addendum)**
   - Resolution: use the explicit `GH_UndoRecord` + `GH_AddObjectAction` + `doc.UndoServer.PushUndoRecord(record)` composition. `RecordAddObjectEvent` does not exist on `GH_Document` in official docs. Since the tag group is the only *new* document object (members already exist on canvas), a single `GH_AddObjectAction(group)` in the record cleanly undoes the tag. Keep the `checkpoint:human-verify` live-Rhino Ctrl+Z confirmation as the final gate.

3. **~~`GH_Scribble` placement/sizing API~~ — RESOLVED (see Perplexity Verification Addendum)**
   - Resolution: `GH_Scribble` → `CreateAttributes()` → set `Text` + `Font` (`System.Drawing.Font`; font size controls rendered size — there is no writable `Bounds`, the scribble auto-sizes from Text+Font) → set `Attributes.Pivot = new PointF(x, y)` for top-left placement → `doc.AddObject(scrib, false)` inside `ScheduleSolution` → `Grasshopper.Instances.InvalidateCanvas()`.

## Perplexity Verification Addendum (2026-07-18, main-session web search)

Post-research verification of the three lowest-confidence SDK areas via Perplexity (sources: McNeel Discourse, official grasshopper-api-docs / developer.rhino3d.com API pages). These upgrade A2/A3/A4 from LOW/MEDIUM to HIGH-CITED and supersede Open Questions 2–3.

### 1. Scribble creation (DG OBJECT MARKER)

```csharp
// inside doc.ScheduleSolution(1, d => { ... })
var scrib = new Grasshopper.Kernel.Special.GH_Scribble();
scrib.CreateAttributes();                                  // BEFORE touching Attributes
scrib.Text = "OBJECT - BRIDGE";
scrib.Font = new System.Drawing.Font("Microsoft Sans Serif", 30f, FontStyle.Regular); // size drives rendered size
scrib.Attributes.Pivot = new System.Drawing.PointF(x, y);  // top-left canvas placement
doc.AddObject(scrib, false);
Grasshopper.Instances.InvalidateCanvas();
```

- No writable `Bounds` — the scribble auto-sizes from Text+Font. Placement is Pivot-only.
- Source: discourse.mcneel.com "ghPython: create Scribble on the canvas and set its position" (working code); Sonderwoods/GrasshopperScribbles repo.

### 2. Undoable tagging (DG ENTITY TAG)

```csharp
using Grasshopper.Kernel.Undo;          // GH_UndoRecord
using Grasshopper.Kernel.Undo.Actions;  // GH_AddObjectAction

var record = new GH_UndoRecord("DG Tag Entity");
var group = new GH_Group { NickName = conventionName, Colour = CanvasAnnotationStyles.For(kind) };
foreach (var id in selectedGuids) group.AddObject(id);     // members already on canvas — NOT new objects
record.AddAction(new GH_AddObjectAction(group));           // only the group is added
doc.AddObject(group, false);
doc.UndoServer.PushUndoRecord(record);
```

- `GH_Document` has **no** `RecordAddObjectEvent` in official API docs — the explicit record composition above is the verified path. (`GH_DocumentObject.RecordUndoEvent(...)` overloads exist for mutating *existing* objects, e.g. re-tag membership updates → use `GH_GenericObjectAction`.)
- Sources: official API pages `GH_Document.UndoServer`, `GH_UndoServer.PushUndoRecord`, `Grasshopper.Kernel.Undo.Actions` namespace (lists `GH_AddObjectAction`, `GH_RemoveObjectAction`, `GH_GenericObjectAction`, `GH_NickNameAction`, `GH_PivotAction`); grasshopper3d.com "Ins and Outs of Undo".

### 3. Per-document metadata for `dg.objectClassIri`

```csharp
var doc = OnPingDocument();
doc.ValueTable.SetValue("dg.objectClassIri", classIri);            // persists into the .gh file
var iri = doc.ValueTable.GetValue("dg.objectClassIri", "");
```

- `GH_Document.ValueTable` is of type `GH_SettingsServer` with typed `SetValue`/`GetValue` overloads (string/int/bool); it is serialized with the .gh/.ghx and reloads with the file. This is the official realization of CONTEXT.md's preferred "document UserData/ValueTable" carrier — invisible on canvas, survives save.
- Do NOT use `new GH_SettingsServer("name")` directly (that path writes to %AppData% plugin settings, not the document).
- Sources: official API pages `GH_Document.ValueTable`, `GH_SettingsServer`; discourse.mcneel.com "Assign user data to grasshopper component".

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rhino 8 SDK (RhinoCommon.dll, Grasshopper.dll, GH_IO.dll) | `GRASSHOPPER_SDK` conditional compilation for both new components | ✓ | Rhino 8 (install dir confirmed) | — |
| .NET SDK | Building DG.Core (net9.0) / DG.Grasshopper (net7.0-windows) | ✓ | 10.0.301 | — |
| Interactive Rhino/Grasshopper session | Manual UAT of canvas mutation, undo, scribble placement | ✗ (not available in this research/planning environment) | — | All GH-SDK-specific behaviors (Patterns 5, Pitfalls 1/4, Assumptions A1-A3) must be gated behind `checkpoint:human-verify` tasks in the plan and verified by the user in live Rhino |

**Missing dependencies with no fallback:** None — the interactive Rhino session gap has a documented fallback (checkpoint:human-verify gating).

**Missing dependencies with fallback:**
- Interactive Rhino/Grasshopper session — fallback is deferring empirical confirmation to human-verify checkpoints during/after execution, consistent with Phase 33's precedent (in-Rhino UAT deferred to a `*-UAT.md` file).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | xUnit (existing, `DG/tests/DG.Tests/DG.Tests.csproj`) |
| Config file | none — standard xUnit project, no custom config |
| Quick run command | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanvasAnnotationNameFactory"` |
| Full suite command | `dotnet test DG/tests/DG.Tests/` |

**Important constraint confirmed this session:** `DG.Tests` targets `net9.0` and **cannot** `ProjectReference` `DG.Grasshopper` (`net7.0-windows7.0`) — this is the same NU1201 TFM-incompatibility already documented in STATE.md (Phase 823 Plan 05). Confirmed by direct evidence: `DG.Tests` currently has zero tests for `CanvasListenerComponent` (the only existing live `GH_Component` introduced since this constraint was documented), only for the GH-free `CanvasAnnotationParser`/`CanvasBridgeDispatcher` it depends on. **The same will be true for `ObjectMarkerComponent`/`EntityTagComponent` — they are not unit-testable from DG.Tests.** Only the new GH-free `CanvasAnnotationNameFactory`/`CanvasAnnotationGrammar` (DG.Core) can get automated xUnit coverage; the components themselves require live-Rhino manual UAT.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TAGC-01 | Marker scribble text construction matches parser grammar exactly | unit | `dotnet test --filter "FullyQualifiedName~CanvasAnnotationNameFactoryTests.BuildObjectScribble"` | ❌ Wave 0 |
| TAGC-01 | Marker on live canvas creates/detects scribbles without duplicating | manual-only (live Rhino) | — (checkpoint:human-verify) | N/A |
| TAGC-02 | Group nickname construction (Proc/Pat/Var/Const/Emg/IntF, incl. next-free-Pat-index) matches parser grammar exactly | unit | `dotnet test --filter "FullyQualifiedName~CanvasAnnotationNameFactoryTests"` | ❌ Wave 0 |
| TAGC-02 | Selection wrapped into group, undo removes it cleanly, nested style applied | manual-only (live Rhino) | — (checkpoint:human-verify) | N/A |
| TAGC-03 | A factory-built group nickname round-trips through `CanvasAnnotationParser.Parse` to the expected typed entity with `source: "tagged"` | unit (round-trip, GH-free) | `dotnet test --filter "FullyQualifiedName~CanvasAnnotationNameFactoryTests.RoundTrip"` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanvasAnnotation"`
- **Per wave merge:** `dotnet test DG/tests/DG.Tests/` (full suite — currently 250+ tests per STATE.md history; confirm exact count at execution time)
- **Phase gate:** Full suite green (dotnet test) + `dotnet build DG/DG.sln -c Release` clean, before the live-Rhino `checkpoint:human-verify` UAT items are exercised, before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs` — covers TAGC-01/02/03's factory logic (name construction, next-free-index, round-trip through the existing parser)
- [ ] `DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs` — shared token constants (prerequisite refactor, Pattern 1); existing `CanvasAnnotationParserTests.cs` must still pass unmodified after this refactor (regression gate)
- [ ] No new test-framework install needed — xUnit already configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Local desktop plugin, no auth surface introduced |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — canvas-only, single local user, no project/permission boundary crossed |
| V5 Input Validation | Yes (light) | `Name`/`ProcIndex` inputs should be validated so that a user-supplied `Name` cannot itself contain grammar-breaking substrings (e.g. embedded `"_Proc - "`, newlines, or leading/trailing whitespace that changes `Trim()`-sensitive matching) before being interpolated into a convention name via `CanvasAnnotationNameFactory` |
| V6 Cryptography | No | N/A — no secrets, no crypto |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A crafted/malformed `.gh` file contains group nicknames that accidentally or deliberately collide with the convention grammar (spoofing a "tagged" entity that wasn't actually placed by the architect) | Spoofing | Low severity for a local single-user desktop tool — `CanvasAnnotationParser` already treats all matching text as `source: "tagged"` by design (manual tags are ground truth per the milestone's core decision); no additional mitigation needed in this phase, but worth noting the trust boundary explicitly: **anyone who can edit the .gh file can spoof a tag** — acceptable given the tool's threat model (single architect, local file) |
| User-supplied `Name` containing the grammar's own infix tokens (e.g. `Name = "Foo_Var_Bar"` for a Constant tag) produces an ambiguous nickname that could re-parse as a different Kind | Tampering (of the tool's own data model, not malicious) | `CanvasAnnotationNameFactory` should reject/sanitize names containing the reserved infix tokens (`_Proc - `, `_Pat_`, `_Var_`, `_Const_`, `_Emg_`/`_Emr_`, `_IntF_`) with a clear `AddRuntimeMessage(Warning, ...)`, per the project's What+Where+How-to-fix convention (`ErrorMessageTemplates`) |

## Sources

### Primary (HIGH confidence)
- `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` (this repo) — the authoritative grammar; read directly, not inferred
- `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` (this repo) — extraction/nesting-detection precedent
- `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` (this repo) — selection reading, `ScheduleSolution`/UI-thread precedent
- `DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs` (this repo) — rising-edge trigger, deferred-mutation precedent
- `DG/src/DG.Core/Models/Computgraph/*.cs` (this repo) — confirms `Source = "tagged"` is already the default on every Cg* model (TAGC-03 needs no new code beyond correct naming)
- `.planning/milestones/v9.0-phases/32-computgraph-serialization-core/32-RESEARCH.md` §3-4 (this repo) — Frame worked example + grammar draft, cross-checked against the shipped parser
- `.planning/milestones/v9.0-phases/33-dg-canvas-bridge/33-RESEARCH.md` (this repo) — `ScheduleSolution`/UI-thread pitfalls, directly applicable
- Direct machine check: `Test-Path` confirms Rhino 8 SDK assemblies present; `dotnet --version` → 10.0.301

### Secondary (MEDIUM confidence)
- [WebSearch, mcneel forum — "Deleting a component from the canvas"] — confirms document mutation must be scheduled, not synchronous, during a solution
- [WebSearch, james-ramsden.com — "Instantiate a Value List Grasshopper component with C#" / "automatically create a value list in C#"] — `GH_ValueList`/`GH_ValueListItem` construction pattern
- [WebSearch, mcneel forum — "Ins and Outs of Undo"] — `GH_UndoRecord`/`GH_Document.UndoUtil` pattern
- [WebSearch, various — GH_Group.AddObject/Colour/NickName code snippets] — group creation/coloring pattern, no single authoritative doc page found

### Tertiary (LOW confidence)
- Document User Text (`dg.objectClassIri` storage) — inferred from Human/Elefront plugin ecosystem convention, not confirmed against primary Rhino/Grasshopper SDK docs in this session — see Assumption A4
- `GH_Scribble` bounds/font API — no primary documentation found; MetaHopper community-plugin precedent only — see Assumption A3
- Exact hex colors — no screenshot/palette in repo, values in this document are placeholders — see Assumption A5

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; existing Rhino 8 SDK reference confirmed present on this machine
- Architecture (grammar/read-write symmetry): HIGH — grammar read directly from shipped, tested source; refactor recommendation is conservative (constants extraction only, no regex-shape change)
- Architecture (GH_Group/Scribble/Undo mechanics): MEDIUM — no in-repo precedent, web-search-sourced patterns not verified against an interactive Rhino session
- Pitfalls: MEDIUM-HIGH — Pitfalls 1-3 are HIGH (grounded in verified in-repo constraints); Pitfalls 4-5 are MEDIUM (flagged explicitly as needing human verification)

**Research date:** 2026-07-18
**Valid until:** 30 days (stable domain — GH1 SDK and this repo's own grammar/parser are not fast-moving; re-verify sooner only if Phase 32's grammar changes before Phase 34 executes)
