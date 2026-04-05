# Directory Structure

## Top-Level Layout

```
design-grammar-system/
├── .github/
│   ├── copilot-instructions.md          # Copilot context: v3 schema, architecture, conventions
│   └── agents/
│       └── DesignGrammarAgent.agent.md  # Pencil design agent definition
├── cypher_template.txt                  # v3 Cypher template — source of truth for LLM prompts
├── docker-compose.yml                   # All services: Neo4j, n8n, Ollama, data-service, SPA, Speckle
├── data-service/                        # FastAPI backend (Python)
├── DG/                                  # .NET solution: Core library + Grasshopper plugin + Tests
├── graph-viewer/                        # Web SPA + model viewer + Pencil design files
├── n8n/                                 # n8n workflow JSON definitions
├── training/                            # Dataset schema + Cypher reference examples
├── test/                                # Ad-hoc test data + scripts (JS, Python)
├── speckle/                             # Speckle bootstrap SQL
├── pencil_doc/                          # Pencil document data
└── docs/                                # Documentation
```

## Key Directories in Detail

### `data-service/` — Python FastAPI Backend
```
data-service/
├── app.py                          # Main FastAPI app (~870 lines)
│                                     # - MCP endpoint (POST /mcp)
│                                     # - Validation publish/list/delete/view
│                                     # - Execution result tracking
│                                     # - Speckle integration config CRUD
├── speckle_validation.py           # Speckle SDK integration
│                                     # - build_client(), publish_validation_version()
│                                     # - Model/version management helpers
├── Dockerfile                      # Python 3.11-slim, uvicorn entrypoint
├── requirements.txt                # fastapi, uvicorn, neo4j, specklepy
└── data/
    └── speckle-settings.json       # Persisted Speckle connection settings
```

### `DG/` — .NET Solution (Grasshopper Plugin)
```
DG/
├── DG.sln                         # VS 2022 solution, 3 projects
├── src/
│   ├── DG.Core/                   # Core library (net7.0 + net9.0)
│   │   ├── Models/                # Domain models
│   │   │   ├── Rule.cs            # Rule with Id, Name, Swrl, BodyAtoms, HeadAtoms, Variables
│   │   │   ├── Atom.cs            # Atom with Id, Type, PredicateIri, Side, Args
│   │   │   ├── AtomArg.cs         # Argument: kind (Variable/Literal/Constant), value, position
│   │   │   ├── Variable.cs        # Named variable (?b, ?h)
│   │   │   ├── BindingRow.cs      # Variable→value map + optional ElementRef map
│   │   │   ├── ConnectionInfo.cs  # Neo4j connection parameters
│   │   │   ├── RuleEvaluationResult.cs  # Pass/fail + failing bindings
│   │   │   ├── ValidationPublish*.cs    # Validation payload models
│   │   │   └── ElementRef.cs      # Entity reference with geometry
│   │   ├── Data/                  # Data access layer
│   │   │   ├── INeo4jConnectorService.cs  # Interface: connection testing
│   │   │   ├── Neo4jConnectorService.cs   # Implementation: TryConnectAsync with timeout
│   │   │   ├── IRuleRepository.cs         # Interface: rule fetching
│   │   │   └── Neo4jRuleRepository.cs     # Implementation: Cypher queries for rules + atoms
│   │   ├── Parsing/               # SWRL parser
│   │   │   ├── SwrlRuleParser.cs  # Static Parse(): string → ParsedSwrlRule
│   │   │   └── ParsedSwrlRule.cs  # Parsed result: BodyAtoms, HeadAtoms, Variables
│   │   ├── Validation/            # Rule evaluation engine
│   │   │   ├── RuleEvaluator.cs   # Evaluates SWRL rules against binding rows
│   │   │   ├── FailingBindingFormatter.cs  # Formats failing bindings for display
│   │   │   ├── ValidationPublishPackageBuilder.cs  # Builds Speckle publish payloads
│   │   │   └── ValidationReportFormatter.cs        # Text report generation
│   │   └── Classification/        # Variable binding
│   │       ├── VariableBinder.cs  # BuildBindings(): zips variables × values → BindingRows
│   │       └── ClassificationResult.cs  # Result: BoundVariables + MissingVariables
│   └── DG.Grasshopper/            # Grasshopper plugin (net7.0-windows)
│       ├── Components/            # 5 Grasshopper components
│       │   ├── ConnectorComponent.cs     # CONNECTOR — Neo4j connection
│       │   ├── MetagraphComponent.cs     # METAGRAPH — Load rules from Neo4j
│       │   ├── ClassificatorComponent.cs # CLASSIFICATOR — Map GH values to variables
│       │   ├── ValidatorComponent.cs     # VALIDATOR — Evaluate rules + publish
│       │   └── RuleDeconstructComponent.cs  # Deconstruct Rule objects
│       ├── Validation/            # Publish helpers
│       │   ├── ValidationPublishClient.cs    # HTTP client for data-service
│       │   ├── ValidationPublishContract.cs  # JSON contract DTOs
│       │   └── ValidationGeometryPayloadSerializer.cs  # Geometry serialization
│       ├── DgComponentCategory.cs # Component category constants
│       ├── DgIcons.cs             # Embedded icon loader
│       ├── PluginInfo.cs          # GH_AssemblyInfo metadata
│       └── PublicTypes.cs         # Public type wrappers for cross-component data
└── tests/
    └── DG.Tests/                  # xUnit tests (net9.0)
        ├── SwrlRuleParserTests.cs              # Parser correctness
        ├── RuleEvaluatorTests.cs               # Evaluation logic
        ├── VariableBinderTests.cs              # Variable binding
        ├── FailingBindingFormatterTests.cs     # Formatter output
        └── ValidationPublishPackageBuilderTests.cs  # Publish payload building
```

### `graph-viewer/` — Web UI + Model Viewer
```
graph-viewer/
├── index.html                     # Main SPA (~2425 lines, single-file React 18)
│                                    # Components: AppRouter, RegisterPage, HomePage,
│                                    # ProjectPage, GraphViewerPage
├── config.template.js             # Runtime config template (NeoVis labels, colors, endpoints)
├── entrypoint.sh                  # Docker entrypoint: sed-substitutes config.template.js → config.js
├── Dockerfile                     # Multi-stage: build model-viewer + serve with nginx
├── nginx.conf                     # Reverse proxy: /neo4j → neo4j:7474, /n8n → n8n:5678, /data-service → data-service:8000
├── interface/                     # Pencil (.pen) design files
│   ├── design-grammars-RegisterForm.pen
│   ├── design-grammars-home.pen
│   ├── design-grammars-Project.pen
│   ├── design-grammars-GraphViewer.pen
│   ├── design-grammars-ModelViewer.pen
│   ├── design-grammars-MetagraphOntology.pen
│   ├── design-grammars-MetagraphOntology.drawio
│   └── SKILL.md
└── model-viewer/                  # Speckle 3D viewer (separate React app)
    ├── package.json               # react, @speckle/viewer, vite
    ├── vite.config.js             # base: /model-viewer/
    └── src/
        ├── main.jsx
        ├── App.jsx                # Speckle viewer with validation overlay
        └── styles.css
```

### `n8n/workflows/` — Workflow Definitions
```
n8n/workflows/
├── rules-to-metagraph.json       # (~505 lines) NL rule → LLM prompt → Cypher → Neo4j
└── graph-query-mcp.json          # (~475 lines) NL question → Cypher → answer
```

### `training/` — LLM Reference Data
```
training/
├── dataset_schema.json            # v3 schema definition (node types, keys, properties, connections)
├── updated_cypher_reference_examples_v3.cypher  # Complete Cypher examples for reference
└── output/merged_hf/              # HuggingFace merged output (training artifacts)
```

## Naming Conventions

- **Docker service:** `design-grammars` (build context: `./graph-viewer`)
- **Grasshopper components:** ALL-CAPS names: `CONNECTOR`, `METAGRAPH`, `CLASSIFICATOR`, `VALIDATOR`
- **C# namespaces:** `DG.Core.Models`, `DG.Core.Data`, `DG.Core.Parsing`, `DG.Core.Validation`, `DG.Core.Classification`
- **Neo4j node labels:** PascalCase: `Rule`, `Atom`, `Class`, `DatatypeProperty`, `ObjectProperty`, `Builtin`, `Var`, `Literal`
- **Config keys:** camelCase in JS (`neo4jUri`, `n8nWebhook`), SCREAMING_SNAKE in env vars
- **localStorage keys:** `dg_users`, `dg_current_user`
