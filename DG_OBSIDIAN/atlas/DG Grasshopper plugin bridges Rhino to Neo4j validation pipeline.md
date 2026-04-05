---
tags: [atlas, grasshopper, csharp, rhino, plugin]
date: 2026-04-05
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
