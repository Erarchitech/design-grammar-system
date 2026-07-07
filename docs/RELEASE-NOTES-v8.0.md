# Release Notes — v8.0 "Design Grammars V2 UI"

**Shipped:** 2026-07-07

v8.0 replaces the dark legacy web SPA with the **Design Grammars V2** light
clinical-blueprint interface — a Vite + React app at `ui-v2/` served by the
`design-grammars` container at :8080, wired to the same live backends
(Neo4j proxy, n8n webhooks, data-service, Speckle).

## What's new

- **Landing** — particle-ring hero with the materialising "DESIGN GRAMMARS."
  title; region callouts fly (520ms scale+opacity) into the three screens;
  inline login/register on a rising frost card. Auth is **byte-compatible
  with the legacy store** (`dg_users` salted SHA-256 + `dg_current_user`) —
  existing accounts keep working.
- **Graph Viewer** — the live project metagraph as an orbital datascape: one
  ring layer per `graph` value (OntoGraph / Metagraph / … / ValidGraph), three
  label orbits per layer, ink-arc edges, idle drift, divergence field. Node
  selection shows the red halo + divergence callout + properties panel; the
  prompt bar drives rules-ingest / graph-query n8n workflows with an extended
  session panel; search popover + property-scoped filter bar.
- **Model Viewer** — validation runs from data-service grouped by design
  state; failing/passing collapsible groups; per-instance inspection with
  per-rule breakdown; stylised isometric map (Signal Red failing, ink passing)
  with wheel zoom + minimap; SWRL rule panel verbatim from the metagraph.
- **Projects** — live tile grid from Neo4j; opening a project scopes both
  viewers; New Project creates a fresh scope.
- **Design system** — `ui-v2/src/styles/tokens/` (6-file split) + 23 JSX
  primitives ported from `design/v2/_ds/`; self-hosted Geist / Geist Mono /
  Oswald (no CDN); dev-only specimen page at `/#specimen`.

## Retired

- **Legacy dark SPA** (`graph-viewer/index.html`) — archived in place; the
  container no longer serves it. `docker-compose.yml` builds `./ui-v2`.
- **Legacy Model Viewer** (`graph-viewer/model-viewer/`, `/model-viewer/`
  route) — replaced by the V2 Model Viewer screen. Run metadata
  `modelViewerUrl` links pointing at `/model-viewer/` are dead after cutover.
- Graphics-settings toolbar extras (per-run screenshots, colour swatches) —
  deferred, see REQUIREMENTS "Future".

## Backend fixes shipped alongside

- `n8n/workflows/graph-query-mcp.json` — fatal quote-syntax error in the
  "Build Cypher Prompt" Code node (every graph query hung). **Re-import the
  workflow into n8n** if your instance still has the broken version.
- Both DG workflows — `project_name` now falls back to the webhook `body.*`
  payload (before: everything ingested landed in `default-project`).
- The V2 client also re-implements the legacy post-ingest project claim
  (`tagProjectNodes`), so scoping works with either workflow version.

## Known issues / actions needed

1. **Pending migration (needs approval):**
   `migrations/2026-07-07_validationgraph_to_validgraph.cypher` — all
   v2.0-era validation runs carry `graph:'ValidationGraph'`; schema v4 and
   data-service expect `'ValidGraph'`. Until it runs, those runs are invisible
   in the Model Viewer (V2 and legacy alike).
2. **Live n8n workflows drift** — the running n8n instance carries newer
   workflow versions than `n8n/workflows/*.json` (edited in the n8n editor).
   Re-import from the repo (or export the live ones back to the repo) to
   reconcile; the client-side tagging keeps project scoping working either way.
3. Cyrillic text falls back from Geist to system fonts (Geist has no Cyrillic
   glyphs; the design's UI strings are English).

## Upgrade

```bash
docker compose build --no-cache design-grammars && docker compose up -d design-grammars
```

Hard-refresh (Ctrl+Shift+R) after cutover — the legacy SPA may be cached.
