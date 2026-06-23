---
phase: 07-schema-foundation
reviewed: 2026-06-23T12:30:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - DG/src/DG.Core/DG.Core.csproj
  - DG/src/DG.Core/Data/Neo4jRuleRepository.cs
  - DG/src/DG.Core/Models/DefState.cs
  - DG/src/DG.Core/Models/ObjectInstance.cs
  - DG/src/DG.Core/Models/ObjectState.cs
  - DG/src/DG.Core/Models/Variable.cs
  - DG/src/DG.Core/Models/VariableKind.cs
  - DG/src/DG.Core/Parsing/VariableTypeInferrer.cs
  - DG/src/DG.Core/Services/DesignStateIdGenerator.cs
  - DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs
  - DG/tests/DG.Tests/Neo4jRuleRepositoryVariableKindTests.cs
  - DG/tests/DG.Tests/VariableTypeInferrerTests.cs
  - data-service/app.py
  - graph-viewer/config.template.js
  - migrations/2026-06-23_var_project_merge_key.cypher
  - n8n/workflows/rules-to-metagraph.json
  - training/dataset_schema.json
  - training/updated_cypher_reference_examples_v3.cypher
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-06-23T12:30:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

This is a re-review of Phase 7 after a prior review/fix cycle (`07-REVIEW.md` iteration 1, `07-REVIEW-FIX.md`). The previously-identified Critical (cross-project `Var` leak via unconstrained `ARG` target in `AtomsQuery`) and three of four Warnings (argLabels exclusivity, dead `DefState`/`ObjectState`/`ObjectInstance` scaffolding documentation, `InferredDatatype` gap documentation) were verified fixed in the current code — `AtomsQuery` now includes `WHERE av IS NULL OR av.project IS NULL OR av.project = $project` (Neo4jRuleRepository.cs:41), `isVariable == isLiteral` is now guarded (line 161-165), and the scaffolding classes carry explicit doc comments. WR-04 (n8n prompt drift risk) remains explicitly deferred/skipped, as documented in `07-REVIEW-FIX.md`.

This re-review surfaces one new Critical issue that the prior pass missed: `Variable.Kind` — this phase's headline feature (Object/Property inference) — is computed correctly in `Neo4jRuleRepository.PopulateVariables` but is silently dropped when rules cross into the Grasshopper plugin layer (`MetagraphComponent.ToPublicRule` and `RuleDeconstructComponent`'s equivalent mapping), because both call sites construct `new global::DG.Variable { Name = ..., InferredDatatype = ... }` without copying `Kind`. The prior review's WR-03 caught the analogous gap for `InferredDatatype` (never populated by this phase) but did not notice that `Kind` — which IS populated by this phase — has the mirror-image bug: populated upstream, dropped downstream. End-to-end, no Grasshopper canvas output (`MetagraphComponent`, `RuleDeconstructComponent`, `GhCastingHelpers`) ever exposes `Kind`, making the entire `VariableTypeInferrer` inference pipeline currently inert for any real user-facing consumer. Three Warnings and two Info items round out the rest.

## Critical Issues

### CR-01: `Variable.Kind` computed by `PopulateVariables` is never copied to the Grasshopper-facing `DG.Variable` — Phase 7's headline feature has zero live consumers

**File:** `DG/src/DG.Grasshopper/Components/MetagraphComponent.cs:200-207`, `DG/src/DG.Grasshopper/Components/RuleDeconstructComponent.cs:142-148`
**Issue:** `Neo4jRuleRepository.PopulateVariables` (DG.Core, this phase) sets `Variable.Kind` via `VariableTypeInferrer.Infer(rule, variableName)` (Neo4jRuleRepository.cs:267) — this is the entire point of the phase per `VariableKind.cs`, `VariableTypeInferrer.cs`, and their dedicated test suites. However, the only two places that translate a `DG.Core.Models.Rule`'s `Variables` collection into the Grasshopper-facing `global::DG.Variable` type both omit `Kind`:
```csharp
// MetagraphComponent.cs:202-206
publicRule.Variables.Add(new global::DG.Variable
{
    Name = variable.Name,
    InferredDatatype = variable.InferredDatatype,
});
// Kind is never set — defaults to null
```
```csharp
// RuleDeconstructComponent.cs:144-148 (same pattern, twice in this file:
// once for the SWRL-only fallback path at line 94-98, once for the main
// rule.Variables loop at line 144-148)
publicRule.Variables.Add(new global::DG.Variable
{
    Name = variable.Name,
    InferredDatatype = variable.InferredDatatype,
});
```
`global::DG.Variable : DG.Core.Models.Variable` (PublicTypes.cs:7-9) does inherit the `Kind` property, so this is purely a missing assignment, not a missing field. `GhCastingHelpers.cs:67` (the third Grasshopper consumer, casting back from public to core types) also only round-trips `InferredDatatype`, never `Kind`. The result: every `VariableKind` value computed by this phase's new inference logic is discarded before it reaches any Grasshopper component output, canvas display, or downstream consumer — the feature is unit-tested and functionally correct in isolation, but dead on arrival in the actual product. `Variable.cs`'s doc comment ("Downstream Grasshopper consumers ... read this field but nothing currently writes it") describes the opposite gap (`InferredDatatype` unpopulated upstream) and does not mention this one, so a future reader would not discover this gap from the existing documentation.
**Fix:** Add `Kind = variable.Kind` to all three object initializers:
```csharp
publicRule.Variables.Add(new global::DG.Variable
{
    Name = variable.Name,
    InferredDatatype = variable.InferredDatatype,
    Kind = variable.Kind,
});
```
Apply in `MetagraphComponent.cs:202-206`, both occurrences in `RuleDeconstructComponent.cs` (lines 94-98 and 144-148), and add the corresponding round-trip in `GhCastingHelpers.cs:67`. If `DG.Grasshopper` is intentionally out of this phase's scope (conditional `#if GRASSHOPPER_SDK` compilation, no GH SDK reference in `DG.Core`), at minimum document this as a known follow-up gap in `Variable.cs`'s doc comment so it isn't silently lost, since it directly contradicts the phase's stated purpose.

## Warnings

### WR-01: `VariableTypeInferrer.Infer` has no handling for `ObjectPropertyAtom`, a documented atom type, leaving object-relating variables permanently classified as indeterminate

**File:** `DG/src/DG.Core/Parsing/VariableTypeInferrer.cs:33-51`
**Issue:** The schema (`training/dataset_schema.json`, `cypher_template.txt`, and the n8n LLM prompt's "Atom types: ClassAtom, DataPropertyAtom, ObjectPropertyAtom, BuiltinAtom") explicitly lists `ObjectPropertyAtom` as a valid, LLM-producible atom type (e.g. for relations between two individuals like `adjacentTo(?b1, ?b2)`). `VariableTypeInferrer.Infer`'s second loop (lines 33-51) only checks `atom.Type != "DataPropertyAtom"` for Property classification — `ObjectPropertyAtom` args are never matched by either the Object-priority loop (which requires `atom.Type == "ClassAtom"`) or the Property-priority loop, so any variable that appears only inside an `ObjectPropertyAtom` (and not also as a `ClassAtom` subject elsewhere) falls through to `null` (indeterminate), even though semantically both args of an ObjectProperty relate two named individuals and arguably warrant `VariableKind.Object`. There is no test coverage for this atom type in either `VariableTypeInferrerTests.cs` or `Neo4jRuleRepositoryVariableKindTests.cs`, so this gap is currently silent and unverified either way.
**Fix:** Decide and implement the intended classification for `ObjectPropertyAtom` args (likely `VariableKind.Object` for both positions, since ObjectProperty relates individuals, not literal values), then add explicit test coverage:
```csharp
foreach (var atom in atoms)
{
    if (atom.Type != "ObjectPropertyAtom")
        continue;
    foreach (var arg in atom.Args)
    {
        if (arg.Kind == ArgKind.Variable && string.Equals(arg.Value, variableName, StringComparison.Ordinal))
            return VariableKind.Object;
    }
}
```

### WR-02: `PopulateVariables` calls `SwrlRuleParser.Parse(rule.Swrl)` with no exception handling — a single malformed SWRL string aborts the entire `GetRulesAsync` call for every rule in the project

**File:** `DG/src/DG.Core/Data/Neo4jRuleRepository.cs:240-263`
**Issue:** `SwrlRuleParser.Parse` throws `ArgumentException` for empty/whitespace input, `FormatException` when the expression lacks exactly one `->`, and `FormatException` again for any atom that doesn't match `AtomRegex` (Parsing/SwrlRuleParser.cs:17,23,55). `PopulateVariables` (line 226-270) iterates every rule and calls `Parse` unconditionally whenever `rule.Swrl` is non-blank, with no try/catch. Under the documented v3 ingestion pipeline, `r.text`/`r.swrl` is always written as a valid SWRL expression by the LLM template, making a throw unlikely in the common case — but the n8n cleanup step (`rules-to-metagraph.json`'s "Prepare Graph Payload" function, with its `fixOutsideQuotes`/`hasValidNesting` repair logic) exists specifically because malformed LLM Cypher/text output is a known, recurring real-world risk in this pipeline, and legacy/manually-edited/partially-migrated rules in the graph are plausible too. If even one rule among many in a project has malformed `text`, this uncaught exception propagates out of `GetRulesAsync`, failing the rule list load for the *entire project*, not just the offending rule.
**Fix:** Wrap the `SwrlRuleParser.Parse` call per-rule so one bad rule doesn't take down the whole batch:
```csharp
if (!string.IsNullOrWhiteSpace(rule.Swrl))
{
    try
    {
        var parsed = SwrlRuleParser.Parse(rule.Swrl);
        // ... existing logic
    }
    catch (Exception ex) when (ex is ArgumentException or FormatException)
    {
        // log and continue with whatever atoms/variables were already loaded from the graph
    }
}
```

### WR-03: `VariableTypeInferrer.Infer`'s priority-2 "Property" check accepts `arg.Pos >= 2` on `DataPropertyAtom` with no upper bound or arity validation

**File:** `DG/src/DG.Core/Parsing/VariableTypeInferrer.cs:40-51`
**Issue:** The check `arg.Pos >= 2` (line 44) classifies a variable as `VariableKind.Property` whenever it appears at position 2 *or higher* of any `DataPropertyAtom`. Per the schema, a well-formed `DataPropertyAtom` always has exactly 2 args (subject at pos 1, value at pos 2 — see `cypher_template.txt`: "DataPropertyAtom: ARG {pos:1} -> Var (subject), ARG {pos:2} -> Var (value)"), so `pos >= 3` should never occur for this atom type in valid data. If malformed/legacy graph data (or a future schema change) produces a `DataPropertyAtom` with 3+ args, this code silently accepts any of them as `Property` without flagging the data as unexpected. Not a live bug under current schema invariants, but the unbounded `>= 2` check provides no defense if that invariant is violated.
**Fix:** Low priority given current schema guarantees; if defensive validation is desired, tighten to `arg.Pos == 2` to match the documented 2-arg `DataPropertyAtom` shape exactly, or add a comment noting the invariant being relied upon.

## Info

### IN-01: `Variable.cs`'s doc comment describes the `InferredDatatype` gap but not the (now-identified) `Kind` propagation gap, making it incomplete/misleading about what is and isn't wired end-to-end

**File:** `DG/src/DG.Core/Models/Variable.cs:7-13`
**Issue:** The existing doc comment (added per the prior review's WR-03 fix) states `InferredDatatype` is "[a]lways null for variables produced by that path as of Phase 7" and lists the three Grasshopper consumers that read it. It does not mention that `Kind` — the field this phase actually populates — has a symmetric problem one layer further downstream (see CR-01 above: dropped during `Rule`→`global::DG.Rule` translation, not within `DG.Core` itself). A reader of this file alone would reasonably conclude `Kind` is fully wired since the doc comment is silent about it.
**Fix:** Once CR-01 is fixed, this is moot. If CR-01 is deferred, update this doc comment to also flag the `Kind` propagation gap at the Grasshopper boundary so the two gaps are documented together.

### IN-02: `VariableTypeInferrer.Infer` re-scans `rule.BodyAtoms.Concat(rule.HeadAtoms)` independently in two loops and is invoked once per distinct variable name from `PopulateVariables`, with no memoization

**File:** `DG/src/DG.Core/Parsing/VariableTypeInferrer.cs:9,33`
**Issue:** Carried over from the prior review's IN-01 (not yet addressed, and out of v1 performance scope per review instructions) — flagging again only because it remains present in the current code and is the kind of thing that will compound if `ObjectPropertyAtom` support (WR-01) adds a third scan loop.
**Fix:** No action needed at current scale; consider a single-pass `Dictionary<string, VariableKind?>` build if rule/atom counts grow significantly.

---

_Reviewed: 2026-06-23T12:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
