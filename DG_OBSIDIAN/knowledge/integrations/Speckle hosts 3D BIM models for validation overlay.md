---
tags: [integration, speckle, 3d, bim, validation]
date: 2026-04-05
---

# Speckle Hosts 3D BIM Models for Validation Overlay

## Self-Hosted Stack (7 containers)

| Container                    | Role                           |
| ---------------------------- | ------------------------------ |
| `speckle-server`             | Core API server                |
| `speckle-frontend-2`         | Web UI (Nuxt)                  |
| `speckle-postgres`           | PostgreSQL 16 (metadata)       |
| `speckle-redis`              | Valkey/Redis (queues)          |
| `speckle-minio`              | Object storage (S3-compatible) |
| `speckle-preview-service`    | 3D preview generation          |
| `speckle-ingress`            | Nginx ingress at port 8090     |
| `speckle-webhook-service`    | Webhook delivery               |
| `speckle-fileimport-service` | File import processing         |

## Integration Points

### Per-Project Configuration

Stored as `IntegrationConfig` nodes in Neo4j (graph=`ValidationGraph`):
- `speckleProjectId` — Speckle project to link
- `baseModelId` — source BIM model
- `validationModelId` — auto-created `dg-validation` model for overlay

### Validation Publish Flow

```
Grasshopper VALIDATOR → POST /data-service/validation/publish
  → data-service builds Speckle Base object
    → Rules: [{ruleId, ruleName, passed}]
    → Entities: [{dgEntityId, geometry (Mesh/Point/Line/Polyline), ruleIds, status}]
  → ServerTransport.send() → creates Version in validation model
  → Returns modelViewerUrl for 3D visualization
```

### Token Management

- `SPECKLE_WRITE_TOKEN` — for publishing validation versions
- `SPECKLE_READ_TOKEN` — for loading models in viewer
- Fallback chain: env vars → `/app/data/speckle-settings.json` → empty

### Python Library

`specklepy` — handles client auth, model CRUD, version creation, object transport.

## Related

- [[Validation results publish to Speckle as overlay versions]]
- [[Model Viewer is a Vite-built Speckle 3D viewer]]
- [[Data-service is a FastAPI MCP bridge to Neo4j and Speckle]]
