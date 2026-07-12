# DG Grasshopper Plugin

This folder contains the initial implementation of the **DG** Grasshopper add-in.

Close Rhino and Grasshopper first, then run this from the repo root. It builds the updated plugin and mirrors the release output into %AppData%\Grasshopper\Libraries\DG:

$src = (Resolve-Path ".\DG\src\DG.Grasshopper\bin\Release\net7.0-windows").Path
$dst = Join-Path $env:APPDATA "Grasshopper\Libraries\DG"

dotnet build .\DG\DG.sln -c Release
New-Item -ItemType Directory -Force -Path $dst | Out-Null
robocopy $src $dst /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit code $LASTEXITCODE" }

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
- `CONNECTOR`: Neo4j connection object output. Inputs `Neo4jURI`, `Neo4jUser`, `Neo4jPassword`, `Database`, `PROJECT NAME`, `Connect` are unchanged, plus two additive optional inputs (Phase 824):
  - `DataServiceUrl` — DG data-service base URL (default `http://localhost:8000`) used for platform-token auth.
  - `Platform Token` (nickname `Token`) — optional `dgc_` credential minted from the Connectors screen's Grasshopper connector. Wire it from a Panel (never internalised); it authenticates a `data-service` heartbeat on `Connect` and is never persisted to the `.gh` file, an output, the status label, or a log. An invalid/revoked/expired token surfaces an in-canvas error (data-service unreachable is a warning) but does **not** block the bolt connection. The component GUID `24E78A17-4533-44E7-8931-1224A70A1B36` and the existing inputs/outputs are unchanged, so saved canvases keep working without rewiring.
- `METAGRAPH`: load rules from `Metagraph`
- `RULE DECONSTRUCT`: unique variables, SWRL, name/description
- `CLASSIFICATOR`: map variable list to value branches, with optional `ElementRefs` branches that attach DG entity ids and geometry to binding rows
- `VALIDATOR`: pass/no-pass + rule report + failing bindings, with optional validation publish to `data-service`

## Validation Publish Flow
- `BindingRow.ValuesByVar` remains the only source for semantic rule evaluation.
- `BindingRow.ElementRefsByVar` is a sidecar map used only for downstream visualization/export.
- `ElementRefs` accepts either explicit `DG.ElementRef` objects or plain geometry items. When plain geometry is provided, DG derives the `dgEntityId` from the paired variable value in the same branch/row when possible.
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
