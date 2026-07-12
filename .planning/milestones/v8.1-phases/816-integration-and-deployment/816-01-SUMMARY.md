---
phase: 816-integration-and-deployment
plan: "816-01"
status: complete
started: "2026-07-11T12:12:00Z"
completed: "2026-07-11T12:37:00Z"
duration: ~25min
files_modified:
  - ui-v2/nginx.conf (added /reasoner/ location block)
  - ui-v2/vite.config.js (added /reasoner/ dev proxy)
---

# Summary 816-01: Integration & Deployment

## What was built

The full connector lifecycle was verified end-to-end through the deployed stack. The rebuilt `design-grammars` container ships all v8.1 regions with no v8.0 regressions.

## Task Results

### Task 1: proxy & compose audit — ✓ PASS

**nginx gap found & fixed:** `reasonerApi.js` calls `/reasoner/settings` directly, but nginx.conf had no `/reasoner/` location block — only `/llm/`, `/data-service/`, `/neo4j/`, and `/n8n/`. Same gap in vite.config.js dev proxy. Added the missing route matching the `/llm/` pattern (no prefix strip — data-service expects `/reasoner/*`).

**docker-compose audit:** `./data-service/data:/app/data` mount exists — connector credentials (`connector-credentials.json`) and reasoner settings (`reasoner-settings.json`) persist across restarts. `DG_DATA_DIR: /app/data` points correctly. No changes needed.

### Task 2: E2E connector lifecycle (INTG-01) — ✓ PASS

Tested against the running stack (`docker compose up -d`, data-service rebuilt, design-grammars rebuilt):

1. **Create credential** — `POST /data-service/connectors/grasshopper/credentials` → 201, returned `credential_id` + `token`
2. **Heartbeat** — `POST /data-service/connectors/heartbeat` with `Authorization: Bearer dgc_...` → `{"connector_id":"grasshopper","status":"active"}`
3. **Status verified** — `GET /data-service/connectors` reports grasshopper as `active` with fresh `last_connection` timestamp
4. **Revoke** — `DELETE /data-service/connectors/grasshopper/credentials/{id}` → 204
5. **Post-revoke auth** — Heartbeat with revoked token → 401 ✓

Test credential was revoked during the test (Step 4).

### Task 3: deployment cutover (INTG-02) — ✓ PASS

- `docker compose build --no-cache design-grammars` — ✓
- `docker compose up -d design-grammars` — ✓
- Smoke checks on :8080:
  - Landing page: 200 ✓
  - Connectors API: 14 connectors across 5 categories ✓
  - **Reasoner API: 2 reasoners via new `/reasoner/` nginx route** ✓
  - LLM settings: 200 ✓
  - SPA shell (Graph/Model/Projects): 200 ✓
  - Neo4j proxy: 200 ✓
- `python -m pytest data-service/tests/ -q` — **90 passed**, 2 warnings ✓
- `npm --prefix ui-v2 run build` — **✓ built in 4.77s** ✓

### Task 4: docs touch-up — ✓ No changes

CLAUDE.md service-map and architecture lines don't need updating — connector/reasoner endpoints live inside data-service on the existing port 8000, covered by the existing nginx proxy pattern.

## Key files created/modified

| File | Action |
|------|--------|
| `ui-v2/nginx.conf` | Added `/reasoner/` location block |
| `ui-v2/vite.config.js` | Added `/reasoner` dev proxy |

## Issues encountered

- **Stale worktree isolation:** Two executor dispatch attempts hit base-mismatch errors because Claude Code's `isolation="worktree"` reused worktrees from a prior session whose HEAD was at `18afabb` (diverged from expected `63ab758`). Switched to sequential inline execution on master per user direction.
- **data-service rebuild needed:** The running data-service container predated Phase 812/814 connector/reasoner endpoints. Rebuilding `data-service` resolved all 404s.

## Self-Check: PASSED

- [x] All 4 tasks executed
- [x] nginx/vite routing gap fixed and committed
- [x] E2E connector lifecycle verified (create → heartbeat → active → revoke → 401)
- [x] Deployment cutover with smoke checks, pytest (90/90), vite build (4.77s)
- [x] CLAUDE.md reviewed — no changes needed
