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

## Canvas bridge

The **DG CANVAS LISTENER** component hosts the canvas bridge: a raw TCP socket, UTF-8, one JSON object per line (newline-terminated, no BOM), bound to `127.0.0.1:8720` only (`IPAddress.Loopback`; the port is a component input). Wire format lives in `DG.Core.Bridge.CanvasBridgeProtocol`.

Request: `{"type":"<command>","parameters":{...}}`. Response, always single-line, always carrying `bridge:"dg"`, `version:1`:

- success: `{"bridge":"dg","version":1,"status":"ok","result":<payload>}`
- error: `{"bridge":"dg","version":1,"status":"error","error":{"message":"...","code":"..."}}`

### Commands

| Command | Kind | Result |
|---------|------|--------|
| `get_canvas_context` | read | DG serializer output of the served document (optional `project` parameter) |
| `get_selection` | read | `{selection: [<instanceGuid>, ...]}` |
| `get_preview_status` | read | pending preview proposals |
| `get_document_identity` | read | `{documentId, filePath, displayName, isModified, capturedAt}`; `filePath` is `null` for an unsaved document (Phase 1301 D-13) |
| `preview_structure` | **mutating** | draws proposal groups on the canvas in one undo record |
| `clear_preview` | **mutating** | removes the preview objects |

The read commands are listed in `CanvasBridgeCommands.ReadCommands`; they never modify the document. `get_document_identity` is strictly read-only: it reads `DocumentID`, `FilePath`, `DisplayName` and `IsModified` of the document the listener serves on the UI thread, nothing else. A client that wants to pin a document stores `documentId` (and `filePath`) and re-issues `get_document_identity` later to confirm it is the same document.

**DeGram sends read commands only** (D-15: no server routing; the DeGram GH adapter allowlists `ReadCommands`). Mutating commands exist for the DG UI/MCP preview flow and are out of scope for DeGram until the phase 1305 write path.

### Error codes

| Code | Meaning |
|------|---------|
| `BAD_REQUEST` | the line is not a parseable request (malformed, oversized over 5 MB, no `type`) |
| `UNKNOWN_COMMAND` | `type` is not in the dispatcher's explicit allow-list |
| `HANDLER_ERROR` | the handler threw (for example, no active document) |
| `BUSY` | the Rhino UI thread did not answer within `CanvasBridgeProtocol.CanvasUiTimeoutMs` (10000 ms) |

**BUSY (Phase 1301 D-18, DGCL-06).** Canvas work is marshalled to Rhino's UI thread. The wait is bounded; if it does not complete in 10 s (modal dialog, long solution), the client receives `status:"error"`, `code:"BUSY"` instead of the listener blocking indefinitely. BUSY is a diagnosable "try again later", not a failure of the document. The timed-out UI delegate is not cancelled and is never retried by the listener; for a read this is harmless, and a client that hit BUSY on a mutating command must re-read state before assuming the write did not happen.

### Trust boundary

No authentication: the socket is reachable by any local process of the same machine (loopback only, never a published port). One client is served at a time (serial accept loop), so a stuck request delays the next one by at most the BUSY timeout. The `filePath` returned by `get_document_identity` is visible to any local process, which is the same exposure as the existing canvas context. Residual risk: a local process can call the mutating preview commands; revisit together with the phase 1305 write path. See `spec/SECURITY-BOUNDARY.md` for the trust zones.
