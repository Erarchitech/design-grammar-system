# DG Grasshopper Plugin

This folder contains the initial implementation of the **DG** Grasshopper add-in.

## Structure
- `src/DG.Core`: rule models, Neo4j access, SWRL parser, classifier, validator
- `src/DG.Grasshopper`: Grasshopper components (`CONNECTOR`, `METAGRAPH`, `RULE DECONSTRUCT`, `CLASSIFICATOR`, `VALIDATOR`)
- `tests/DG.Tests`: parser/evaluator/classifier unit tests

## Build Notes
`DG.Core` and `DG.Tests` build directly with .NET SDK.

`DG.Grasshopper` enables real Grasshopper components when Rhino 8 SDK DLLs are found:
- `C:\Program Files\Rhino 8\System\RhinoCommon.dll`
- `C:\Program Files\Rhino 8\Plug-ins\Grasshopper\Grasshopper.dll`

You can override Rhino location with MSBuild property:

```powershell
dotnet build DG\DG.sln -p:RhinoInstallDir="D:\Apps\Rhino 8"
```

When SDK DLLs are not found, `DG.Grasshopper` still compiles as a placeholder assembly (without GH runtime classes).

## Core Data Types
- `DG.Rule`
- `DG.Variable`
- `DG.ElementRef`
- `DG.Core.Models.BindingRow`
- `DG.Core.Models.RuleEvaluationResult`
- `DG.Core.Models.ConnectionInfo`

## Component Contracts
- `CONNECTOR`: Neo4j connection object output
- `METAGRAPH`: load rules from `Metagraph`
- `RULE DECONSTRUCT`: unique variables, SWRL, name/description
- `CLASSIFICATOR`: map variable list to value branches, with optional `ElementRefs` branches that attach DG entity ids and geometry to binding rows
- `VALIDATOR`: pass/no-pass + rule report + failing bindings, with optional validation publish to `data-service`

## Validation Publish Flow
- `BindingRow.ValuesByVar` remains the only source for semantic rule evaluation.
- `BindingRow.ElementRefsByVar` is a sidecar map used only for downstream visualization/export.
- `VALIDATOR` accepts:
  - `Rules`
  - `Variables`
  - `Run`
  - `SendRules`
  - `DataServiceUrl`
- `VALIDATOR` outputs:
  - `Pass`
  - `RuleName`
  - `RuleDescription`
  - `Report`
  - `FailingBindings`
  - `PublishStatus`
  - `ValidationRunId`
  - `ModelViewerUrl`

When `SendRules=True`, the component:
1. evaluates all rules locally,
2. derives the DG project from the rule payload,
3. builds a validation publish package from rule results and `ElementRefs`,
4. posts it to `data-service /validation/publish`.

The package deduplicates referenced entities per rule by `dgEntityId`, with `fail` overriding `pass` when the same element appears in both sets.
