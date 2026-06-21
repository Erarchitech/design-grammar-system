---
tags: [atlas, stack, technology]
date: 2026-04-05
graphify_communities: ["Architecture is a Microservices Docker Pipeline", "STACK.md - Technology Stack Research", "Validation Viewer API", "n8n Workflow Orchestrator"]
---

# Technology Stack Spans C-Sharp Grasshopper and Python FastAPI and React SPA

## Languages & Runtimes

| Layer | Language | Runtime | Key Libraries |
|-------|----------|---------|---------------|
| **Grasshopper Plugin** | C# | .NET 7/9 (Windows) | Neo4j.Driver 5.28.2, Grasshopper SDK (Rhino 8) |
| **Data Service** | Python 3 | FastAPI/Uvicorn | neo4j, specklepy, pydantic |
| **Workflow Engine** | JavaScript (n8n) | Node.js | Built-in n8n nodes (HTTP, Function, Webhook) |
| **Main UI** | JavaScript | React 18 (CDN, no JSX) | NeoVis.js, neo4j-driver |
| **Model Viewer** | JSX | React + Vite | @speckle/viewer, three.js |
| **LLM** | — | Ollama | llama3.1:latest (default) |
| **Database** | Cypher | Neo4j 5 | — |
| **Proxy** | — | Nginx | — |

## Fonts & Design

- Body: **Inter** (400, 500, 600)
- Headings/branding: **Space Grotesk** (500, 600)
- Dark theme UI with CSS custom properties (`--bg`, `--accent`, `--panel`, etc.)

## Build Targets

- `DG.Core` → net7.0 + net9.0 (multi-target)
- `DG.Grasshopper` → net7.0-windows (Rhino SDK conditional via `#if GRASSHOPPER_SDK`)
- `model-viewer` → Vite production build (stage 1 of Docker multi-stage)
- `design-grammars` container → Nginx serving static files

## Related

- [[Architecture is a microservices Docker pipeline]]
- [[DG Grasshopper plugin bridges Rhino to Neo4j validation pipeline]]
- [[UI is a single-file React 18 SPA with no build step]]

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Architecture is a Microservices Docker Pipeline|Architecture is a Microservices Docker Pipeline]]
- [[graphify/communities/STACK.md - Technology Stack Research|STACK.md - Technology Stack Research]]
- [[graphify/communities/Validation Viewer API|Validation Viewer API]]
- [[graphify/communities/n8n Workflow Orchestrator|n8n Workflow Orchestrator]]
<!-- graphify:connections:end -->
