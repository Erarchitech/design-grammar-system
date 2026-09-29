# Deployment

## Docker Compose

All services start with:
```bash
docker compose up -d
```

Dependency ordering via `depends_on`.

## Port Map

| Port | Service | Binding |
|------|---------|---------|
| 8080 | Design Grammars UI (nginx) | all interfaces |
| 7474 | Neo4j Browser | 127.0.0.1 (not published in `multi-user`) |
| 7687 | Neo4j Bolt | 127.0.0.1 (not published in `multi-user`) |
| 5678 | n8n | 127.0.0.1 (not published in `multi-user`) |
| 8000 | data-service | 127.0.0.1 |
| 8001 | dg-reasoner | 127.0.0.1 |
| 11435 | Ollama | 127.0.0.1 |
| 8090 | Speckle ingress | all interfaces |
| 9000/9001 | MinIO (Speckle storage) | 127.0.0.1 |

## Docker Volumes

`neo4j_data`, `n8n_data`, `ollama`, `speckle_postgres_data`, `speckle_redis_data`, `speckle_minio_data`

## UI Rebuild

After changes to `index.html`:
```bash
docker compose build --no-cache design-grammars && docker compose up -d design-grammars
```
`--no-cache` is **required** — Docker layer caching can serve stale `index.html`. After rebuild, hard-refresh (Ctrl+Shift+R) or use incognito.

## Deployment profiles and secrets (Phase 1205)

The normative contract is `spec/SECURITY-BOUNDARY.md`.

- **Secrets come from `.env`.** Copy `.env.example` to `.env` (gitignored) and replace every `change-me-...` placeholder with a locally generated value. Compose requires each secret (`${VAR:?...}`), so a missing one stops the stack from starting. Check completeness with `python tools/security/check_env_file.py`.
- **Local profile (default).** `docker compose up -d`. data-service warns, and still starts, if a secret is a known default. Authentication is always enforced.
- **Multi-user profile.** `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml up -d`. Sets `DG_DEPLOYMENT=multi-user`: data-service refuses to start with a known-default or too-short secret, the heartbeat omits the Neo4j bundle, FastAPI docs are off, and Neo4j (7474/7687) and n8n (5678) are not published. Direct-Bolt Grasshopper components are unsupported in this profile.
- **Bindings.** Every internal service publishes to `127.0.0.1` only; only the UI (8080) and the Speckle ingress (8090) are routable. The exact list per profile is the `published-ports` block in the spec and is checked by `data-service/tests/test_security_boundary_spec.py`.
- **Live check.** After rebuilding with `--no-cache`, run `python tools/security/check_live_boundary.py --profile multi-user`.
- **Rotation.** Committed secrets are treated as compromised. The ordered rotation runbook (Neo4j, Speckle Postgres, MinIO, `LLM_MASTER_SECRET` with re-encryption of the stored LLM key, n8n, service token, bootstrap admin, connector tokens) is section 9 of the spec. Git history is not rewritten.
- **TLS.** Not terminated by this stack; set `DG_COOKIE_SECURE=true` behind a TLS front end before any external deployment.

## Environment Variable Injection

`ui-v2/entrypoint.sh` regenerates the browser `config.js` at container startup. Since Phase 1205 it carries only `dataServiceUrl` and `speckleBaseUrl`; no credential is ever injected into the browser (see `spec/SECURITY-BOUNDARY.md`).

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
