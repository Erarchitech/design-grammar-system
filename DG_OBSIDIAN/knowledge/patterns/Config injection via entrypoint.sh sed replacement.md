---
tags: [pattern, docker, config, deployment]
date: 2026-04-05
---

# Config Injection via entrypoint.sh Sed Replacement

## Pattern

The `design-grammars` Docker container injects runtime configuration by replacing placeholders in `config.template.js` using `sed` at container startup.

## How It Works

`graph-viewer/entrypoint.sh`:
1. Reads environment variables (NEO4J_URI, N8N_WEBHOOK, etc.) with fallback defaults
2. Uses `sed` to replace placeholder values in `config.template.js`
3. Writes result to `config.js`
4. Execs `nginx` as PID 1

## Config Variables

| Env Var | Config Property | Default |
|---------|----------------|---------|
| `NEO4J_URI` | `neo4jUri` | `bolt://localhost:7687` |
| `NEO4J_HTTP` | `neo4jHttp` | `/neo4j` |
| `NEO4J_USER` | `neo4jUser` | `neo4j` |
| `NEO4J_PASSWORD` | `neo4jPassword` | `12345678` |
| `N8N_WEBHOOK` | `n8nWebhook` | `/n8n/webhook/dg/rules-ingest` |
| `N8N_QUERY_WEBHOOK` | `n8nQueryWebhook` | `/n8n/webhook/dg/graph-query` |
| `DATA_SERVICE_URL` | `dataServiceUrl` | `/data-service` |
| `SPECKLE_BASE_URL` | `speckleBaseUrl` | `http://localhost:8090` |
| `N8N_USER` | `n8nUser` | — |
| `N8N_PASSWORD` | `n8nPassword` | — |

## Why This Pattern

- No build-time config baking — same image works in different environments
- `config.template.js` is the source; `config.js` is generated at runtime
- Works with Docker Compose `environment:` section

## Related

- [[Deployment uses Docker Compose with nginx reverse proxy]]
- [[Single-file React SPA avoids build tooling for main UI]]
