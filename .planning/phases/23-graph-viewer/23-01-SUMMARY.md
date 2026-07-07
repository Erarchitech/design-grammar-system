---
phase: 23-graph-viewer
plan: "23-01"
status: complete
completed: 2026-07-07
commits:
  - 85ef35a feat(23-01) API client + datascape engine
  - e8ec276 feat(23-01) Graph Viewer screen
  - 0eb65d4 fix(23-01) n8n workflow repairs
  - 2ba9e92 fix(23-01) project_name key + post-ingest tagging
duration: ~2.5h (incl. live-stack debugging)
---

# Summary 23-01: Graph Viewer

## What shipped

Live orbital datascape (GVIEW-01), selection + divergence callout + details panel (GVIEW-02), prompt bar → rules-ingest webhook with session panel (GVIEW-03), query mode → graph-query webhook (GVIEW-04), search popover with jump-to-result + property-scoped filter bar (GVIEW-05). Files per PLAN.

## Live-stack findings & fixes (significant)

1. **`graph-query-mcp.json` was dead** — the `Build Cypher Prompt` Code node had unescaped `''` inside single-quoted JS strings ("Unexpected string" in n8n logs; every query execution hung forever). Introduced by the parked v9.0 phase-01 rewiring. Fixed (double-quoted), re-imported, verified: UI query answered in 4.7s.
2. **Project scoping was silently broken backend-side** — the workflows' `Set Input Defaults` reads `$json.project_name || $json.project` but webhook payloads arrive under `$json.body.*`; only `rules_text` had a body fallback. Everything ingested landed in `default-project`. Repo JSONs patched with body fallbacks; **and** the V2 client now performs the legacy SPA's post-ingest `tagProjectNodes` claim (`project IS NULL OR 'default-project' → active project`) — the documented "Neo4j node tagging" gotcha is the system's actual scoping mechanism, so the V2 client reproduces it for parity.
3. **Live n8n workflows have drifted ahead of the repo JSONs** (versionCounter 22, extra "Fetch Existing Entities"/smart-edit nodes; user-edited in the n8n editor). CLI re-import did not reliably replace the active version on n8n 2.4.8 — flagged for the user; client-side tagging makes scoping robust regardless.
4. **Legacy data mismatch**: all v2.0-era validation nodes carry `graph:'ValidationGraph'` but schema v4 + data-service use `'ValidGraph'` → those runs are invisible to data-service (also in the legacy UI). Bulk migration was denied by the auto-mode policy (agent-inferred mass mutation) — written up as `migrations/2026-07-07_validationgraph_to_validgraph.cypher` **pending user approval**.

## Decisions

- Ring layers map 1:1 to live `graph` property values (incl. pre-v7 KnowledgeGraph as its own layer); labels bucket into 3 orbits per layer with outer-orbit fallback for unknown labels.
- Session turns live in memory (mockup behaviour); step progress animates client-side capped until the poll completes.
- Prompt modes limited to Ingest/Query (mockup's Edit mode is out of scope per REQUIREMENTS).

## Verification results

All five GVIEW criteria verified against the live Docker stack (see PLAN verification section). Zero console errors; `npm run build` clean.
