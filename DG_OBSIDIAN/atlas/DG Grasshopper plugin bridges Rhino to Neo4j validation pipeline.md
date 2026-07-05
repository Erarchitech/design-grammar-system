---
tags: [atlas, grasshopper, csharp, rhino, plugin]
date: 2026-04-05
graphify_communities: ["Community 214", "Community 237", "Community 31", "Community 36", "Community 44", "Community 78", "Community 86", "DG.Grasshopper.csproj", "Graph Schema v3 is the Canonical Data Model", "Neo4jConnectorService", "Neo4jConnectorService.cs", "Ontology v5 DCM ComputationGraph", "Product Bridges Natural Language Rules to Graph-Based Val...", "RuleDeconstructComponent", "State Projection for Validation Runs", "Validation Results Publish to Speckle as Overlay Versions", "ValidationGeometryPayload", "Validator Failing Bindings Output Data", "Zone A Maximum Height (75m)", "n8n Workflow Orchestrator for LLM Rule Ingestion and Queries"]
---

# DG Grasshopper Plugin Bridges Rhino to Neo4j Validation Pipeline

The `DG/` folder contains a C# solution (`DG.sln`) with a Grasshopper add-in for Rhino 8 that connects to the Neo4j graph, loads rules, binds Rhino geometry to SWRL variables, evaluates rules, and optionally publishes results to Speckle.

## Solution Structure

```
DG/
├── src/DG.Core/          — Pure logic layer (no Grasshopper deps)
│   ├── Data/             — Neo4j connectivity + rule repository
│   ├── Models/           — Domain objects (Rule, Atom, Variable, BindingRow, ElementRef)
│   ├── Parsing/          — SWRL regex parser
│   ├── Classification/   — Variable binder (zips values into binding rows)
│   └── Validation/       — Rule evaluator, report formatters, publish builder
├── src/DG.Grasshopper/   — GH components (conditional on Rhino SDK)
│   └── Components/       — 5 Grasshopper components
└── tests/DG.Tests/       — xUnit tests
```

## Grasshopper Components

| Component | Purpose | Key I/O |
|-----------|---------|---------|
| `CONNECTOR` | Create Neo4j connection | → `ConnectionInfo` |
| `METAGRAPH` | Load rules from graph | ConnectionInfo → Rules list |
| `RULE DECONSTRUCT` | Extract rule details | Rule → Variables, SWRL, Name |
| `CLASSIFICATOR` | Bind GH values to variables | Variables + DataTree → BindingRows |
| `VALIDATOR` | Evaluate rules + optional publish | Rules + Bindings → Pass/Fail + Report |

## Validation Pipeline

```
CONNECTOR → METAGRAPH → RULE DECONSTRUCT → CLASSIFICATOR → VALIDATOR
                                                             ↓ (optional)
                                                        data-service HTTP → Speckle
```

## Key Patterns

- **Conditional compilation** — `#if GRASSHOPPER_SDK` guards all GH-dependent code. Without Rhino SDK, `DG.Grasshopper` compiles as a placeholder.
- **Async polling** — Components use `ScheduleSolution()` + task caching instead of blocking. See [[Grasshopper async component with ScheduleSolution polling]].
- **Multi-target** — DG.Core targets net7.0 + net9.0 for broad compatibility.

## Build Command

```powershell
dotnet build .\DG\DG.sln -c Release
```

Override Rhino path: `-p:RhinoInstallDir="D:\Apps\Rhino 8"`

## Related

- [[Technology stack spans C-Sharp Grasshopper and Python FastAPI and React SPA]]
- [[Validation results publish to Speckle as overlay versions]]
- [[SWRL parsing is bespoke regex not vendor OWL library]]

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Community 214|Community 214]]
- [[graphify/communities/Community 237|Community 237]]
- [[graphify/communities/Community 31|Community 31]]
- [[graphify/communities/Community 36|Community 36]]
- [[graphify/communities/Community 44|Community 44]]
- [[graphify/communities/Community 78|Community 78]]
- [[graphify/communities/Community 86|Community 86]]
- [[graphify/communities/DG.Grasshopper.csproj|DG.Grasshopper.csproj]]
- [[graphify/communities/Graph Schema v3 is the Canonical Data Model|Graph Schema v3 is the Canonical Data Model]]
- [[graphify/communities/Neo4jConnectorService|Neo4jConnectorService]]
- [[graphify/communities/Neo4jConnectorService.cs|Neo4jConnectorService.cs]]
- [[graphify/communities/Ontology v5 DCM ComputationGraph (261)|Ontology v5 DCM ComputationGraph]]
- [[graphify/communities/Product Bridges Natural Language Rules to Graph-Based Val...|Product Bridges Natural Language Rules to Graph-Based Val...]]
- [[graphify/communities/RuleDeconstructComponent|RuleDeconstructComponent]]
- [[graphify/communities/State Projection for Validation Runs|State Projection for Validation Runs]]
- [[graphify/communities/Validation Results Publish to Speckle as Overlay Versions|Validation Results Publish to Speckle as Overlay Versions]]
- [[graphify/communities/ValidationGeometryPayload (79)|ValidationGeometryPayload]]
- [[graphify/communities/Validator Failing Bindings Output Data|Validator Failing Bindings Output Data]]
- [[graphify/communities/Zone A Maximum Height (75m)|Zone A Maximum Height (75m)]]
- [[graphify/communities/n8n Workflow Orchestrator for LLM Rule Ingestion and Queries|n8n Workflow Orchestrator for LLM Rule Ingestion and Queries]]
<!-- graphify:connections:end -->
