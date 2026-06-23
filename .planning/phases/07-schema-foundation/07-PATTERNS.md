# Phase 7: Schema Foundation - Pattern Map

**Mapped:** 2026-06-23
**Files analyzed:** 9 (new/modified)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `DG/src/DG.Core/Models/VariableKind.cs` (new enum) | model | transform | `DG/src/DG.Core/Models/ArgKind.cs` | exact |
| `DG/src/DG.Core/Parsing/VariableTypeInferrer.cs` (new) | utility | transform | `DG/src/DG.Core/Parsing/SwrlRuleParser.cs` (static parse utility) / `DG/src/DG.Core/Classification/VariableBinder.cs` (static classification utility) | exact |
| `DG/src/DG.Core/Models/DefState.cs` (new) | model | CRUD | `DG/src/DG.Core/Models/DesignStateSnapshot.cs` | exact (extends shape) |
| `DG/src/DG.Core/Models/ObjectState.cs` (new) | model | CRUD | `DG/src/DG.Core/Models/DesignStateSnapshot.cs` + `DesignStateParameter.cs` | role-match |
| `DG/src/DG.Core/Models/ObjectInstance.cs` (new, OI_ prefix, identity anchor) | model | CRUD | `DG/src/DG.Core/Models/DesignStateSnapshot.cs` (StateId pattern) + `DG/src/DG.Grasshopper/Components/DesignStateComponent.cs` (ID hash logic) | partial (new concept, no direct C# analog yet) |
| ID generation logic for `DS_`/`OS_` prefixes (lands in a Models helper or repository, exact placement at Claude's discretion) | utility | transform | `DG/src/DG.Grasshopper/Components/DesignStateComponent.cs` → `ComputeStateId()` (SHA256 pattern) | exact |
| `cypher_template.txt` (Var MERGE key fix + DS_/OS_ shapes + schema version stamp) | config | CRUD | same file, existing `Var` MERGE block (lines 109-115) and `Rule.kind` pattern (lines 102-106) | exact (self-modify) |
| `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` (`PopulateVariables()` consumes `VariableTypeInferrer`; Var MERGE-key-aware queries) | service | CRUD | same file, `AtomsQuery` (lines 37-55) + `PopulateVariables()` (lines 212-256) | exact (self-modify) |
| `training/dataset_schema.json` (new node types + VariableKind field) | config | transform | same file, `metagraph.nodes[]` entries — `Var` node block (lines 86-95) and `Rule` `kind` prop pattern (lines 29-35) | exact (self-modify) |
| `n8n/workflows/rules-to-metagraph.json` (LLM system prompt ALLOWED node labels / GRAPH SCHEMA section) | config | event-driven | same file, existing node-type vocabulary in the system-prompt `parameters` block (~lines 73-122) | exact (self-modify) |
| `graph-viewer/config.template.js` (DesignState kind-based NeoVis labels/visGroups) | config | request-response | same file, `labels`/`visGroups` for `Rule` (kind-discriminated already at the data level) and `Var` (lines 17-31, 41-55) | role-match |
| `data-service/app.py` (statePayloadJson extension point — vocabulary only, no behavior change this phase) | service | CRUD | same file, `statePayloadJson` field + `_project_state_summary()` (lines 161, 415, 432, 518-578, 864) | exact (self-modify, additive only) |

## Pattern Assignments

### `DG/src/DG.Core/Models/VariableKind.cs` (model, transform)

**Analog:** `DG/src/DG.Core/Models/ArgKind.cs`

**Full file** (8 lines) — the exact convention to mirror:
```csharp
namespace DG.Core.Models;

public enum ArgKind
{
    Variable = 0,
    Literal = 1,
}
```

Apply directly: `public enum VariableKind { Object = 0, Property = 1 }` (or include a non-canvas-exposed value per the priority-chain rule in CONTEXT.md — builtin-only variables are "not exposed to canvas", so this may be a tri-state enum or a nullable `VariableKind?` return from the inferrer rather than a third enum member; CONTEXT.md leaves this to Claude's discretion only insofar as method signature, not the two canvas-facing values).

---

### `DG/src/DG.Core/Parsing/VariableTypeInferrer.cs` (utility, transform)

**Analog (structure/static-utility convention):** `DG/src/DG.Core/Classification/VariableBinder.cs`
**Analog (parsing/atom-walking convention):** `DG/src/DG.Core/Parsing/SwrlRuleParser.cs`

**Static utility class shape** (`VariableBinder.cs` lines 1-16):
```csharp
using DG.Core.Models;

namespace DG.Core.Classification;

public static class VariableBinder
{
    public static ClassificationResult BuildBindings(
        IReadOnlyList<Variable> variables,
        IReadOnlyDictionary<string, IReadOnlyList<object?>> valuesByVariable,
        IReadOnlyDictionary<string, IReadOnlyList<ElementRef?>>? elementRefsByVariable = null)
    {
        var result = new ClassificationResult();
        ...
```
No instance state, single static entry method taking immutable inputs, returns a populated result object — this is the convention `VariableTypeInferrer` should follow (live in `DG.Core.Parsing` per CONTEXT.md, e.g. `public static class VariableTypeInferrer { public static VariableKind? Infer(...) }` or similar, called per-variable from `Neo4jRuleRepository.PopulateVariables()`).

**Atom-arg-walking pattern to reuse for the priority chain** (`SwrlRuleParser.cs` lines 30-41, and duplicated in `Neo4jRuleRepository.PopulateVariables()` lines 217-224):
```csharp
var variables = parsed.BodyAtoms
    .Concat(parsed.HeadAtoms)
    .SelectMany(atom => atom.Args)
    .Where(arg => arg.Kind == ArgKind.Variable)
    .Select(arg => arg.Value)
    .Distinct(StringComparer.Ordinal)
    .OrderBy(name => name, StringComparer.Ordinal);
```
`VariableTypeInferrer` should walk `rule.BodyAtoms.Concat(rule.HeadAtoms)`, filter `atom.Type == "ClassAtom"` for `pos == 1` args (Object — priority 1), then `atom.Type == "DataPropertyAtom"` for `pos >= 2` args (Property — priority 2), matching the existing `Atom.Type` string values already produced by `SwrlRuleParser.ResolveAtomType()` (`"ClassAtom"`, `"DataPropertyAtom"`, `"BuiltinAtom"` — see `SwrlRuleParser.cs` lines 82-94). Use `Atom.Args` (`AtomArg.Pos`, `AtomArg.Kind`) and `Atom.PredicateIri` for the head-only-variable IRI-based fallback (priority 4).

**Consumption point** (`Neo4jRuleRepository.cs` lines 212-256, `PopulateVariables`):
```csharp
private static void PopulateVariables(IEnumerable<Rule> rules)
{
    foreach (var rule in rules)
    {
        var names = new HashSet<string>(StringComparer.Ordinal);
        foreach (var name in rule.BodyAtoms
                     .Concat(rule.HeadAtoms)
                     .SelectMany(atom => atom.Args)
                     .Where(arg => arg.Kind == ArgKind.Variable)
                     .Select(arg => arg.Value))
        {
            names.Add(name);
        }
        ...
        foreach (var variableName in names.OrderBy(name => name, StringComparer.Ordinal))
        {
            rule.Variables.Add(new Variable { Name = variableName });
        }
    }
}
```
Modify the final loop to call `VariableTypeInferrer.Infer(rule, variableName)` and set the new `Variable.Kind` property (add `VariableKind? Kind` to `Variable.cs`, mirroring `Rule.Kind`'s `init`-only string property convention but typed as the new enum).

---

### `DG/src/DG.Core/Models/DefState.cs` (model, CRUD)

**Analog:** `DG/src/DG.Core/Models/DesignStateSnapshot.cs` + `DesignStateParameter.cs`

**Full existing snapshot model** (`DesignStateSnapshot.cs`, 13 lines):
```csharp
using System.Collections.ObjectModel;

namespace DG.Core.Models;

public class DesignStateSnapshot
{
    public string StateId { get; init; } = string.Empty;

    public DateTimeOffset CapturedAtUtc { get; init; }

    public Collection<DesignStateParameter> Parameters { get; } = new();
}
```
`init`-only scalar properties, `Collection<T>` for list properties (no public setter — append-only via the getter), no constructor logic. `DefState` should extend this exact shape (rename `StateId`→ keep as `DS_`-prefixed `StateId`, add a `Kind` discriminator if the single-label `:DesignState{kind}` pattern needs to surface client-side — SCHM-01 decision says this lives at the Neo4j level via `kind` property, so the C# class itself need not carry a `Kind` field unless both `DefState`/`ObjectState` share one base — CONTEXT.md says "No concrete parent `DesignState` node," implying these can remain two independent C# classes without inheritance, consistent with `Rule`/`Atom`'s flat non-hierarchical model style elsewhere in `DG.Core.Models`).

**Companion parameter-type enum + class** (`DesignStateParameter.cs`, full file, 24 lines) — reuse this enum/class as-is or compose it directly into `DefState.Parameters`:
```csharp
namespace DG.Core.Models;

public enum DesignStateParameterType
{
    Number,
    Integer,
    Boolean,
}

public class DesignStateParameter
{
    public string ParameterId { get; init; } = string.Empty;
    public string DisplayName { get; init; } = string.Empty;
    public DesignStateParameterType Type { get; init; }
    public double? NumberValue { get; init; }
    public long? IntegerValue { get; init; }
    public bool? BooleanValue { get; init; }
}
```
This is the existing v2.0 `DesignStateParameterTypeValue` analog referenced in CONTEXT.md/SCHM-06 — the ontology enum-discriminator pattern to mirror for `VariableKindValue`, `VariableScopeValue`, `DesignStateKindValue`, `ValidationStatusValue` mirrors this C# enum's *intent* (closed value set) even though SCHM-06 targets the OWL/ontology layer, not C#.

---

### `DG/src/DG.Core/Models/ObjectState.cs` / `ObjectInstance.cs` (model, CRUD)

**Analog:** `DesignStateSnapshot.cs` shape (StateId + timestamp + collection) for `ObjectState`; no direct analog exists for `ObjectInstance` (new cross-rule identity concept) — use the same `init`-only property convention.

**ID generation to extend (SHA256 pattern)** — `DG/src/DG.Grasshopper/Components/DesignStateComponent.cs` lines 248-275:
```csharp
private static string ComputeStateId(IEnumerable<DesignStateParameter> parameters)
{
    var sb = new StringBuilder();
    foreach (var p in parameters.OrderBy(x => x.ParameterId, StringComparer.Ordinal))
    {
        sb.Append(p.ParameterId);
        sb.Append('=');
        sb.Append(p.Type switch
        {
            DesignStateParameterType.Boolean => p.BooleanValue?.ToString(System.Globalization.CultureInfo.InvariantCulture) ?? "null",
            DesignStateParameterType.Integer => p.IntegerValue?.ToString(System.Globalization.CultureInfo.InvariantCulture) ?? "null",
            DesignStateParameterType.Number  => p.NumberValue?.ToString("R", System.Globalization.CultureInfo.InvariantCulture) ?? "null",
            _ => "null",
        });
        sb.Append(';');
    }
    var hash = SHA256.HashData(Encoding.UTF8.GetBytes(sb.ToString()));
    return Convert.ToHexString(hash)[..16];
}
```
This `System.Security.Cryptography.SHA256.HashData` + `Convert.ToHexString(...)[..16]` pattern is the exact code to copy for the new `OS_<SHA256(projectId + objectInstanceId + variableName)>` ID format (CMPST-07): build a deterministic input string (e.g. `$"{projectId}|{objectInstanceId}|{variableName}"`), hash it, hex-encode, prefix with `OS_`. Keep the existing `DS_` prefix logic (currently the 16-char hex hash alone, undecorated — confirm whether `DesignStateComponent` currently prepends `DS_`; it does not in the excerpt above, so the `DS_` prefix application must be added at the call site or inside `ComputeStateId`, consistent with CONTEXT.md's note that `DefState.StateId` is "existing SHA256-based `DS_<hash>` format (unchanged from v2.0)" — verify exact current prefix handling before reusing).

Note: this SHA256 logic currently lives inside a Grasshopper component (`#if GRASSHOPPER_SDK` guarded). Since `ObjectInstance`/`ObjectState` ID generation is a pure-logic concern, consider relocating/duplicating this hashing helper into `DG.Core` (no GH dependency) so it's testable via `DG.Tests` and reusable from `Neo4jRuleRepository` or wherever `OS_`/`OI_` IDs get minted — this mirrors the project's stated principle that `DG.Core` holds "pure logic (no GH deps)."

---

### `cypher_template.txt` (config, CRUD) — Var merge-key fix

**Analog:** same file, existing `Var` MERGE block, lines 108-115:
```
// 3. Metagraph — variables, literals
MERGE (vEntity:Var {name: '?<ENTITY_VAR>'})
SET vEntity.project = '<PROJECT>',
    vEntity.graph = 'Metagraph'

MERGE (vValue:Var {name: '?<VALUE_VAR>'})
SET vValue.project = '<PROJECT>',
    vValue.graph = 'Metagraph'
```
**Fix required (SCHM-02):** move `project` into the MERGE key itself, not the subsequent `SET`:
```
MERGE (vEntity:Var {name: '?<ENTITY_VAR>', project: '<PROJECT>'})
SET vEntity.graph = 'Metagraph'

MERGE (vValue:Var {name: '?<VALUE_VAR>', project: '<PROJECT>'})
SET vValue.graph = 'Metagraph'
```
This is the precise bug: `MERGE` currently only matches/creates on `name`, so `SET vEntity.project = ...` runs on a node that could already exist under a different project — fixing this means moving `project` into the `{...}` MERGE pattern, matching how `Class`/`DatatypeProperty`/`Atom`/`Builtin` nodes elsewhere in the same template already use multi-property MERGE keys is NOT the existing pattern (they currently MERGE on `iri`/`Atom_Id` alone too, with `project` set afterward — lines 85-153) — **Var is being fixed first per SCHM-02 scope; do not extend this fix to other node types in this phase** (out of scope per CONTEXT.md "Phase 7 stays scoped strictly to REQUIREMENTS.md VTYP/SCHM items").

**Reference for `kind`-discriminated single-label pattern (SCHM-01)** — `Rule` node block, lines 101-106:
```
MERGE (r:Rule {Rule_Id: '<RULE_ID>'})
SET r.text = '<SWRL_EXPRESSION>',
    r.kind = 'violation',
    r.project = '<PROJECT>',
    r.graph = 'Metagraph'
```
The new `:DesignState {kind: 'DefState' | 'ObjectState'}` nodes should follow this exact MERGE-then-SET-with-kind-property shape, with `project` added to the MERGE key from the start (don't repeat the Var bug on new node types).

---

### `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` (service, CRUD) — query updates

**Analog:** same file, `AtomsQuery` (lines 37-55) for Cypher query string conventions, and `PopulateVariables()` (lines 212-256) as the inference plug-in point (see VariableTypeInferrer section above).

**Cypher query string convention** (raw string literal with `coalesce()` defaulting, `graph`/`project` filters on every MATCH):
```csharp
private const string AtomsQuery = """
    MATCH (r:Rule {graph:'Metagraph', project:$project})-[rel:HAS_BODY|HAS_HEAD]->(a:Atom {graph:'Metagraph', project:$project})
    OPTIONAL MATCH (a)-[:REFERS_TO]->(p)
    OPTIONAL MATCH (a)-[arg:ARG]->(av)
    RETURN
        ...
    ORDER BY ruleId, relationType, atomOrder, argPos
    """;
```
Any new query touching `Var` nodes (e.g. a verification/count query for the migration sweep) should follow this same `graph`/`project`-scoped MATCH + `coalesce()` + `ORDER BY` convention, and be declared as a `private const string ... = """ ... """;` raw string literal alongside `RulesQuery`/`AtomsQuery`.

---

### `training/dataset_schema.json` (config, transform)

**Analog:** same file, `Var` node block (lines 86-95) and `Rule.kind` prop pattern (lines 24-35).

**Existing Var node schema entry:**
```json
{
  "label": "Var",
  "key": {
    "name": "?<varName>"
  },
  "props": {
    "project": "default-project",
    "graph": "Metagraph"
  }
}
```
Fix the `"key"` block to include `"project": "default-project"` (mirroring the MERGE-key fix in `cypher_template.txt`) — currently only `name` is documented as the key, which is itself evidence of the same latent bug propagated into the schema doc.

**Existing `kind`-as-prop pattern to copy for new DesignState nodes:**
```json
"rule_node": {
  "label": "Rule",
  "key": { "Rule_Id": "same_as_dataset_id" },
  "props": {
    "text": "SWRL expression string",
    "kind": "violation | compliance",
    ...
  }
}
```
Add a new `metagraph.nodes[]` (or top-level) entry for `DesignState` using this same `"key"` + `"props"` shape, with `"kind": "DefState | ObjectState"` and `StateId` (`DS_`/`OS_` prefixed) as the key.

---

### `n8n/workflows/rules-to-metagraph.json` (config, event-driven)

**Analog:** same file's embedded LLM system-prompt parameters block (~lines 73-122) which encodes the same node-type vocabulary as `dataset_schema.json` and `cypher_template.txt`.

This file embeds the schema as prompt text inside an n8n Function/Set node's `parameters` JSON (matched lines 73-122 above contain `"label": "Var"`, `"type": "Var"` references). Any update must keep this prompt-embedded copy of the schema textually consistent with `dataset_schema.json` and `cypher_template.txt` — read the full matched node content before editing (large file; use targeted `Grep`+`Read` with line-range offsets, not a full-file read, since this is an n8n workflow JSON export likely several hundred KB).

---

### `graph-viewer/config.template.js` (config, request-response)

**Analog:** same file, `labels`/`visGroups` blocks, lines 17-31 and 41-55.

**Existing label/color entry pattern:**
```javascript
labels: {
  ...
  Var: { label: "name" },
  ...
},
visGroups: {
  ...
  Var: { color: { background: "#c6b5ff", border: "#9278d9" } },
  ...
}
```
Add a `DesignState: { label: "StateId" }` entry to `labels`, and since NeoVis `visGroups` key off node label (not property value), kind-based coloring for `DefState` vs `ObjectState` within the single `:DesignState` label requires either (a) a NeoVis community-detection/groupBy-on-property config if supported, or (b) accept a single color for `:DesignState` and treat per-kind visual distinction as Claude's discretion per CONTEXT.md ("any visually distinct pair is acceptable, no convention to match") — verify NeoVis's config schema supports property-based (not just label-based) `visGroups` before committing to an approach; if not supported, a single `DesignState` color is acceptable for this phase, deferring kind-based visual distinction to a later UI phase.

---

### `data-service/app.py` (service, CRUD) — vocabulary-only touch

**Analog:** same file, `statePayloadJson` field definition (line 161) and `_project_state_summary()` (lines 518, 578).

```python
statePayloadJson: str | None = None
...
run.statePayloadJson = $statePayloadJson,
...
"statePayloadJson": state_payload_json,
...
"state": _project_state_summary(row.get("statePayloadJson")),
...
state_payload_json=payload.statePayloadJson,
```
CONTEXT.md/Integration Points confirms: "full extension lands in Phase 11, but the node/prefix vocabulary must agree starting here." This phase should NOT change `_project_state_summary()` behavior — only ensure any new constants/comments referencing node-type vocabulary (`DS_`/`OS_`/`OI_`/`IDR_` prefixes) are consistent if mentioned in docstrings/comments near this code. Read lines 500-590 directly before editing to confirm no behavior change is needed, only vocabulary alignment (e.g. comments documenting the JSON shape).

## Shared Patterns

### Static utility class convention (DG.Core)
**Source:** `DG/src/DG.Core/Classification/VariableBinder.cs`, `DG/src/DG.Core/Parsing/SwrlRuleParser.cs`
**Apply to:** `VariableTypeInferrer.cs`
```csharp
public static class VariableBinder
{
    public static ClassificationResult BuildBindings(/* immutable inputs */) { ... }
}
```
No instance state, static entry method(s), pure functions over immutable `IReadOnlyList`/`IReadOnlyDictionary` inputs, returns a populated result object.

### Model property convention (DG.Core.Models)
**Source:** `DG/src/DG.Core/Models/DesignStateSnapshot.cs`, `Rule.cs`, `Variable.cs`
**Apply to:** `DefState.cs`, `ObjectState.cs`, `ObjectInstance.cs`, `VariableKind.cs`
```csharp
public class Rule
{
    public string Id { get; init; } = string.Empty;
    ...
    public Collection<Atom> BodyAtoms { get; } = new();
}
```
`init`-only scalar properties with non-null default (`= string.Empty`), `Collection<T>` getter-only properties for lists, flat classes (no inheritance hierarchy observed elsewhere in `DG.Core.Models`).

### Single-label + `kind` discriminator (Neo4j)
**Source:** `cypher_template.txt` lines 101-106 (`Rule.kind`), `dataset_schema.json` lines 24-35
**Apply to:** `:DesignState {kind: 'DefState' | 'ObjectState'}` node creation in `cypher_template.txt`, `Neo4jRuleRepository.cs` queries, and `dataset_schema.json`
```
MERGE (r:Rule {Rule_Id: '<RULE_ID>'})
SET r.text = '<SWRL_EXPRESSION>',
    r.kind = 'violation',
    r.project = '<PROJECT>',
    r.graph = 'Metagraph'
```

### MERGE-key correctness (project-scoped node identity)
**Source:** `cypher_template.txt` `Class`/`Atom` blocks (multi-property-key-eligible, though currently only Var is being fixed) — and the bug itself in the `Var` block (lines 109-115)
**Apply to:** the Var MERGE fix; do not propagate this fix to other node types in this phase (explicitly scoped to SCHM-02 / Var only)

### SHA256 deterministic ID generation
**Source:** `DG/src/DG.Grasshopper/Components/DesignStateComponent.cs` lines 248-275 (`ComputeStateId`)
**Apply to:** new `OS_`/`OI_` ID generation logic (wherever it lands — `DG.Core` preferred for testability, per CONTEXT.md's discretion note)
```csharp
var hash = SHA256.HashData(Encoding.UTF8.GetBytes(sb.ToString()));
return Convert.ToHexString(hash)[..16];
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `DG/src/DG.Core/Models/ObjectInstance.cs` | model | CRUD | New cross-rule identity concept (CMPST-06) — no prior C# class represents a stable cross-rule anchor distinct from a state snapshot; build from the `DesignStateSnapshot.cs` property-convention template, not a structural analog |
| Migration sweep script (orphaned-Var cleanup, `coalesce(v.project, 'default-project')`) | migration | batch | "No migration-script precedent exists yet in the repo, this is the first one" (CONTEXT.md, Claude's Discretion) — write as a standalone `.cypher` file or `cypher-shell` command using the `coalesce()` + `MATCH...SET` idiom already used throughout `cypher_template.txt` (e.g. lines 27, 32-33, 47-48 for `coalesce()` usage patterns), since no dedicated migration-runner file/pattern exists in this repo |

## Metadata

**Analog search scope:** `DG/src/DG.Core/Models/`, `DG/src/DG.Core/Parsing/`, `DG/src/DG.Core/Classification/`, `DG/src/DG.Core/Data/`, `DG/src/DG.Grasshopper/Components/`, `cypher_template.txt`, `training/dataset_schema.json`, `n8n/workflows/`, `graph-viewer/config.template.js`, `data-service/app.py`
**Files scanned:** ~20 (full reads) + 4 targeted greps
**Pattern extraction date:** 2026-06-23
