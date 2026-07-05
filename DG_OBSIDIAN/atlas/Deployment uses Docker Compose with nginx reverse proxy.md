---
tags: [atlas, deployment, docker, nginx]
date: 2026-04-05
graphify_communities: ["Community 213", "Community 226", "Docker Compose Orchestration", "Graph Schema v3 is the Canonical Data Model", "Match Step (Neo4j Full-Text Search, No LLM)", "Remove all test notes from Neo4j.", "Validation Endpoints (publish/runs/view)"]
---

# Deployment Uses Docker Compose with Nginx Reverse Proxy

## Service Startup

```bash
docker compose up -d
```

All 12+ containers start with dependency ordering via `depends_on`.

## UI Rebuild (After index.html Changes)

```bash
docker compose build --no-cache design-grammars && docker compose up -d design-grammars
```

`--no-cache` is required to avoid [[Docker layer caching can serve stale index.html]]. After rebuild, do a hard-refresh (Ctrl+Shift+R) or use incognito.

## Nginx Reverse Proxy Routes

| URL Path | Upstream Target | Purpose |
|----------|----------------|---------|
| `/` | Static files | Main SPA (`index.html`) |
| `/model-viewer/` | Static files | Vite-built 3D viewer |
| `/neo4j/*` | `http://neo4j:7474` | Direct Neo4j HTTP API |
| `/data-service/*` | `http://data-service:8000` | FastAPI data-service |
| `/n8n/*` | `http://n8n:5678` | n8n webhooks + REST |

Config file: `graph-viewer/nginx.conf`. Uses DNS resolver `127.0.0.11` (Docker internal).

## Environment Variable Injection

`graph-viewer/entrypoint.sh` uses `sed` to replace placeholders in `config.template.js` → `config.js`. See [[Config injection via entrypoint.sh sed replacement]].

## Port Map

| Port | Service |
|------|---------|
| 8080 | Design Grammars UI |
| 7474/7687 | Neo4j browser/bolt |
| 5678 | n8n |
| 8000 | data-service |
| 11435 | Ollama |
| 8090 | Speckle ingress |
| 9000/9001 | MinIO (Speckle storage) |

## Docker Volumes

`neo4j_data`, `n8n_data`, `ollama`, `speckle_postgres_data`, `speckle_redis_data`, `speckle_minio_data`

## Related

- [[Architecture is a microservices Docker pipeline]]
- [[Config injection via entrypoint.sh sed replacement]]
- [[Docker layer caching can serve stale index.html]]

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Community 213|Community 213]]
- [[graphify/communities/Community 226|Community 226]]
- [[graphify/communities/Docker Compose Orchestration|Docker Compose Orchestration]]
- [[graphify/communities/Graph Schema v3 is the Canonical Data Model|Graph Schema v3 is the Canonical Data Model]]
- [[graphify/communities/Match Step (Neo4j Full-Text Search, No LLM)|Match Step (Neo4j Full-Text Search, No LLM)]]
- [[graphify/communities/Remove all test notes from Neo4j.|Remove all test notes from Neo4j.]]
- [[graphify/communities/Validation Endpoints (publishrunsview) (259)|Validation Endpoints (publish/runs/view)]]
<!-- graphify:connections:end -->
