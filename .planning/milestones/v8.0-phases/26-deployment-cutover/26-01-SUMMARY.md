---
phase: 26-deployment-cutover
plan: "26-01"
status: complete
completed: 2026-07-07
commits:
  - 3befb6e feat(26-01) container cutover
  - 4722d2d docs(26-01) CLAUDE.md V2 architecture
  - 2934748 docs(26-01) v8.0 release notes
duration: ~40min
---

# Summary 26-01: Deployment Cutover and E2E Parity

## What shipped

- **DEPL-01**: `docker compose up` serves the V2 UI at :8080 — `design-grammars` now builds `ui-v2/` (node build stage → nginx), same proxy routes, `config.js` regenerated from env at container start. Rebuilt `--no-cache` and verified live.
- **DEPL-02**: 7-point E2E parity checklist passed against live Docker services (see PLAN) — serving, config injection, graph browse, validation browsing, graph query, rule ingest, project scoping.
- **Legacy retirement**: `graph-viewer/` (dark SPA + old model-viewer) archived in place; documented in `docs/RELEASE-NOTES-v8.0.md`; CLAUDE.md updated (service map, key decisions, repo structure, commands, tech stack, gotchas, priorities).

## Decisions / notes

- The old `/model-viewer/` route is not carried into the V2 nginx config — the legacy Speckle viewer retires with the dark SPA; stored `modelViewerUrl` links on old runs go dead (release-noted).
- `entrypoint.sh` pinned to LF via `ui-v2/.gitattributes` (CRLF would break the alpine shebang).
- `docs/` is gitignored; release notes force-added, matching the v7.0 precedent.
- n8n credentials are no longer baked into the served config (the V2 client doesn't need n8n basic auth for webhook calls through the proxy).

## Milestone status

v8.0 complete — all 25 requirements delivered. Outstanding user actions listed in the release notes: approve the ValidGraph tag migration; reconcile live n8n workflow versions with the repo JSONs.
