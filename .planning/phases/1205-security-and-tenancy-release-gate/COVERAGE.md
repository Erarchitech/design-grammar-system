# Phase 1205 — API Coverage Matrix

Produced by the plan-phase API coverage checkpoint (`api-coverage.cjs` detected API/SDK/webhook/MCP surfaces in the plan scope). Default decision is INTEGRATE; every OPT-OUT carries a one-line reason.

| Capability | Decision | Plan(s) | Reason |
|---|---|---|---|
| data-service REST API (all 82 routes) | INTEGRATE | 1205-07, 1205-10, 1205-12, 1205-14 | Every route runs the deny-by-default principal dependency and is classified in ROUTE_POLICIES and spec/SECURITY-BOUNDARY.md (D-03, D-14). |
| Browser session auth (`/auth/*`) | INTEGRATE | 1205-07, 1205-12, 1205-13 | Server-side scrypt users, HttpOnly SameSite=Strict session cookie, CSRF header, invitation-only onboarding (D-01, D-05). |
| n8n webhooks (rules-ingest, graph-query, knowledge-*) | INTEGRATE | 1205-05, 1205-14, 1205-18 | Reached only through the data-service relay with the internal service token; workflows verify it at entry (D-04, D-08). |
| `/mcp` JSON-RPC tool surface | INTEGRATE | 1205-06, 1205-10, 1205-14 | Service-token only; `neo4j_query` requires a bound project and passes the static scope guard plus result withholding (D-04). |
| Grasshopper SDK components (VALIDATOR, COMPUTGRAPH PUBLISH, CONNECTOR) | INTEGRATE | 1205-03 | Trailing non-persistent Token input; Bearer dgc_ token on every publish; no-bundle handling in multi-user (D-04, D-07, D-19). |
| Connector token API (`/connectors/*`, heartbeat) | INTEGRATE | 1205-07, 1205-10 | Heartbeat keeps its own token check; multi-user omits the Neo4j bundle; credential routes resource-bound (D-04, D-07). |
| Speckle read token delivery (`/validation/view/*`) | INTEGRATE | 1205-10, 1205-15 | Already server-side; now project-authorised; removed from config.js (D-12). |
| LLM provider APIs via the gateway | INTEGRATE | 1205-04, 1205-10 | Unchanged call path; `/llm/generate` service-only; stored key re-encrypted on master-secret rotation (D-13). |
| DE-01 host runner → data-service | INTEGRATE | 1205-04, 1205-18 | Connector token from env or gitignored file; never serialised into reports (D-20). |
| Neo4j HTTP API from the browser (`/neo4j/…/tx/commit`) | OPT-OUT | 1205-11, 1205-15 | Removed by D-06: no generic Cypher passthrough for the browser; nginx tombstones return 404. |
| n8n webhooks called directly by the browser (`/n8n/…`) | OPT-OUT | 1205-11, 1205-15 | Removed by D-08: the UI calls the authorised data-service relay instead. |
| Neo4j Bolt for Grasshopper in the multi-user profile | OPT-OUT | 1205-03, 1205-09 | D-07 withholds the bundle and the Bolt publish in multi-user; migrating the C# repositories to HTTP is a Deferred Idea. |
| n8n REST/editor API for publishing workflows | OPT-OUT | 1205-18 | Live publish uses the n8n CLI inside the container; no API key or REST integration is introduced. |
| External IdP / OAuth / OIDC | OPT-OUT | — | Deferred Idea in CONTEXT.md; D-05 locks a self-contained user store with no external IdP. |
| Neo4j Enterprise RBAC / per-tenant databases | OPT-OUT | — | Deferred Idea; Neo4j 5 Community has no RBAC (Correction 4). |
