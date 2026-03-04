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
- `DG.Core.Models.BindingRow`
- `DG.Core.Models.RuleEvaluationResult`
- `DG.Core.Models.ConnectionInfo`

## Component Contracts
- `CONNECTOR`: Neo4j connection object output
- `METAGRAPH`: load rules from `Metagraph`
- `RULE DECONSTRUCT`: unique variables, SWRL, name/description
- `CLASSIFICATOR`: map variable list to value branches
- `VALIDATOR`: pass/no-pass + rule report + failing bindings
