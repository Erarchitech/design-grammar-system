# Deployment

## Docker Compose

All services start with:
```bash
docker compose up -d
```

Dependency ordering via `depends_on`.

## Port Map

| Port | Service |
|------|---------|
| 8080 | Design Grammars UI (nginx) |
| 7474 | Neo4j Browser |
| 7687 | Neo4j Bolt |
| 5678 | n8n |
| 8000 | data-service |
| 11435 | Ollama |
| 8090 | Speckle ingress |
| 9000/9001 | MinIO (Speckle storage) |

## Docker Volumes

`neo4j_data`, `n8n_data`, `ollama`, `speckle_postgres_data`, `speckle_redis_data`, `speckle_minio_data`

## UI Rebuild

After changes to `index.html`:
```bash
docker compose build --no-cache design-grammars && docker compose up -d design-grammars
```
`--no-cache` is **required** — Docker layer caching can serve stale `index.html`. After rebuild, hard-refresh (Ctrl+Shift+R) or use incognito.

## Environment Variable Injection

`graph-viewer/entrypoint.sh` uses `sed` to replace placeholders in `config.template.js` → `config.js` at container startup. Variables include Neo4j credentials, n8n webhook URLs, and NeoVis display configuration.

## Grasshopper Plugin Build

```powershell
dotnet build .\DG\DG.sln -c Release
```

Override Rhino path if non-standard:
```powershell
dotnet build .\DG\DG.sln -c Release -p:RhinoInstallDir="D:\Apps\Rhino 8"
```

## Model Viewer Build

The Model Viewer is built during the Docker multi-stage build (Vite production build in stage 1, copied to nginx in stage 2).

For local development:
```bash
cd graph-viewer/model-viewer
npm install
npm run dev
```
