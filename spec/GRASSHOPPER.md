# Grasshopper Plugin (DG)

## Solution Structure

```
DG/
├── DG.sln
├── src/
│   ├── DG.Core/                    ← Pure logic (no Grasshopper deps)
│   │   ├── Data/                   ← Neo4j connectivity
│   │   │   ├── INeo4jConnectorService.cs
│   │   │   ├── Neo4jConnectorService.cs
│   │   │   ├── IRuleRepository.cs
│   │   │   └── Neo4jRuleRepository.cs
│   │   ├── Models/                 ← Domain objects
│   │   │   ├── Rule.cs, Atom.cs, AtomArg.cs, Variable.cs
│   │   │   ├── BindingRow.cs, ConnectionInfo.cs, ElementRef.cs
│   │   │   └── ValidationPublish*.cs (Package, Rule, Entity, RuleResult)
│   │   ├── Parsing/                ← SWRL regex parser
│   │   │   ├── SwrlRuleParser.cs
│   │   │   └── ParsedSwrlRule.cs
│   │   ├── Classification/         ← Variable binder
│   │   │   ├── VariableBinder.cs
│   │   │   └── ClassificationResult.cs
│   │   └── Validation/             ← Rule evaluator + formatters
│   │       ├── RuleEvaluator.cs
│   │       ├── FailingBindingFormatter.cs
│   │       ├── ValidationReportFormatter.cs
│   │       └── ValidationPublishPackageBuilder.cs
│   └── DG.Grasshopper/             ← GH components (conditional)
│       ├── Components/
│       │   ├── ConnectorComponent.cs
│       │   ├── MetagraphComponent.cs
│       │   ├── RuleDeconstructComponent.cs
│       │   ├── ClassificatorComponent.cs
│       │   └── ValidatorComponent.cs
│       ├── Validation/
│       │   ├── ValidationPublishClient.cs
│       │   ├── ValidationPublishContract.cs
│       │   └── ValidationGeometryPayloadSerializer.cs
│       ├── DgComponentCategory.cs, DgIcons.cs, PluginInfo.cs
│       └── Properties/             ← Component icons (24×24 PNG)
└── tests/DG.Tests/
    ├── SwrlRuleParserTests.cs
    ├── RuleEvaluatorTests.cs
    ├── VariableBinderTests.cs
    ├── FailingBindingFormatterTests.cs
    └── ValidationPublishPackageBuilderTests.cs
```

## Grasshopper Components

| Component | Category | Purpose | Inputs | Outputs |
|-----------|----------|---------|--------|---------|
| `CONNECTOR` | DG | Create Neo4j connection | URI, User, Password | ConnectionInfo |
| `METAGRAPH` | DG | Load rules from graph | ConnectionInfo, Project | Rules list |
| `RULE DECONSTRUCT` | DG | Extract rule details | Rule | Variables, SWRL, Name, Text |
| `CLASSIFICATOR` | DG | Bind GH values to variables | Variables, DataTree | BindingRows |
| `VALIDATOR` | DG | Evaluate + optional publish | Rules, Bindings, PublishURL | Pass/Fail, Report |

## Validation Pipeline

```
CONNECTOR → METAGRAPH → RULE DECONSTRUCT → CLASSIFICATOR → VALIDATOR
                                                             ↓ (optional)
                                                        data-service HTTP → Speckle
```

## Build Targets

- `DG.Core` → `net7.0;net9.0` (multi-target)
- `DG.Grasshopper` → `net7.0-windows` (Rhino SDK conditional)
- Tests → `net9.0`

## Key Dependencies

- `Neo4j.Driver` 5.28.2
- Grasshopper SDK (Rhino 8)
- xUnit (tests)

## Build Command

```powershell
dotnet build .\DG\DG.sln -c Release
# Override Rhino path:
dotnet build .\DG\DG.sln -c Release -p:RhinoInstallDir="D:\Apps\Rhino 8"
```

## Key Patterns

- **Conditional compilation** — `#if GRASSHOPPER_SDK` guards all GH-dependent code. Without Rhino SDK installed, `DG.Grasshopper` compiles as a placeholder.
- **Async polling** — Components use `ScheduleSolution()` + task caching instead of blocking the GH UI thread.
- **SWRL parsing** — Bespoke regex parser, not a vendor OWL library. Handles `Class(?var)`, `Property(?var1, ?var2)`, and `Builtin(?var, literal)` patterns.

## Connector token on publish components (Phase 1205)

Every Grasshopper call to data-service is authenticated with a project-bound connector token (`dgc_...`); see `spec/SECURITY-BOUNDARY.md` (section 3.2).

- The **VALIDATOR** and **COMPUTGRAPH PUBLISH** components have a `Token` input. It takes the same `dgc_` token that the **CONNECTOR** component uses. The token is a runtime input and is not saved into the `.gh` file; re-supply it when the canvas is reopened.
- A token works only for its bound project and only on the connector-scoped routes: `POST /computgraph/publish`, `POST /validation/publish`, `GET /validation/view/...`, `POST /connectors/heartbeat` and `POST /designstate/capture`. Any other route answers 403.
- The direct-Bolt components (`Neo4j*Repository` based, connecting to `bolt://localhost:7687`) are a trusted-local boundary in the `local` profile and are **unsupported in `multi-user`**: Bolt is not published and the heartbeat withholds the Neo4j bundle. Use the data-service API instead.
