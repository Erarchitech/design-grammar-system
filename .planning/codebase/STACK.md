# Technology Stack

## Languages

| Language | Version | Usage |
|---|---|---|
| **C#** | .NET 7 / .NET 9 (multi-target) | `DG.Core` library + `DG.Grasshopper` Rhino plugin |
| **Python** | 3.11 | `data-service/` FastAPI backend |
| **JavaScript / JSX** | ES2020+ (no transpile for main SPA) | `graph-viewer/index.html` single-file React SPA |
| **JavaScript (JSX, Vite)** | ES2022 | `graph-viewer/model-viewer/` Speckle 3D viewer (React + Vite) |

## Runtimes & Platforms

- **Docker** — all services orchestrated via `docker-compose.yml`
- **Nginx (Alpine)** — serves the Design Grammars SPA + reverse proxy to Neo4j, n8n, data-service
- **Node 20 Alpine** — build stage only (model-viewer Vite build in `graph-viewer/Dockerfile`)
- **Rhino 8 / Grasshopper** — host for the `DG.Grasshopper` plugin (Windows desktop, .NET 7)

## Frameworks & Libraries

### C# (.NET)
- **Neo4j.Driver 5.28.2** — Bolt driver for Neo4j graph queries (`DG.Core.csproj`)
- **Grasshopper SDK** — conditional reference to `RhinoCommon.dll`, `Grasshopper.dll`, `GH_IO.dll` from Rhino 8 install path (`DG.Grasshopper.csproj`)
- **xUnit 2.9.2** + **coverlet 6.0.2** — unit testing (`DG.Tests.csproj`, targets net9.0)

### Python
- **FastAPI** — REST API and MCP endpoint (`data-service/app.py`)
- **Uvicorn** — ASGI server
- **neo4j** (Python driver) — Bolt connector to Neo4j
- **specklepy 3.2.4** — Speckle server SDK for publishing validation geometry

### JavaScript (main SPA — `graph-viewer/index.html`)
- **React 18** (CDN, no JSX — uses `React.createElement` throughout)
- **NeoVis.js** — Neo4j graph visualization on `<canvas>`
- **Google Fonts** — Inter (body), Space Grotesk (headings/branding)
- No build step; raw JS inlined in a single 2425-line HTML file

### JavaScript (model-viewer — `graph-viewer/model-viewer/`)
- **React 18.3** + **@vitejs/plugin-react 4.4.1**
- **@speckle/viewer 2.28** — 3D model viewer with filtering/selection extensions
- **Vite 5.4** — bundler (builds to `dist/`, served at `/model-viewer/`)

## Infrastructure Services (Docker)

| Service | Image | Port | Purpose |
|---|---|---|---|
| `neo4j` | `neo4j:5` | 7474 / 7687 | Graph database (single DB, project isolation via `project` property) |
| `n8n` | `n8nio/n8n` | 5678 | Workflow automation — 2 workflows: rule ingest + graph query |
| `ollama` | `ollama/ollama:latest` | 11435→11434 | Local LLM inference (GPU-enabled, default model `llama3.1:latest`) |
| `data-service` | Custom (Python 3.11) | 8000 | FastAPI: MCP endpoint, validation publish, execution tracking |
| `design-grammars` | Custom (Nginx Alpine) | 8080 | Static SPA + reverse-proxy |
| `speckle-server` | `speckle/speckle-server:latest` | — | Speckle AEC data platform |
| `speckle-postgres` | `postgres:16.4-alpine` | — | Speckle backing store |
| `speckle-redis` | `valkey/valkey:8.1-alpine` | — | Speckle cache |
| `speckle-minio` | `minio/minio` | 9000 / 9001 | Speckle object storage |

## Configuration

- **Environment variables** — Docker Compose injects Neo4j creds, n8n auth, Ollama model, Speckle tokens
- **`graph-viewer/config.template.js`** — runtime config template; `entrypoint.sh` performs `sed` substitution at container start to produce `config.js`
- **`data-service/data/speckle-settings.json`** — persisted Speckle connection settings (base URL, tokens)
- **Neo4j auth** — hardcoded default `neo4j/12345678` across all services
- **n8n auth** — basic auth with credentials in `docker-compose.yml` env vars

## Build & Deploy

- `docker compose build --no-cache design-grammars && docker compose up -d design-grammars` — rebuild UI
- `DG.Grasshopper` outputs `DG.gha` via MSBuild post-build copy target
- Model viewer built at Docker image build time via `npm ci && npm run build` (multi-stage Dockerfile)
