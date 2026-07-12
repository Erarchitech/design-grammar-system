---
phase: 812-connector-credential-backend
plan: "812-01"
subsystem: data-service
tags: [connectors, credentials, fastapi, security]
requires: []
provides:
  - GET /connectors (registry + status + credential summaries)
  - POST /connectors/{connector_id}/credentials (mint dgc_ token, shown once)
  - DELETE /connectors/{connector_id}/credentials/{credential_id} (revoke)
  - POST /connectors/heartbeat (Bearer dgc_ auth, stamps last_connection)
affects: [813-connectors-screen, 815-dg-api-documentation]
tech-stack:
  added: []
  patterns:
    - SHA-256 token hashing (plaintext never persisted)
    - JSON persistence under DATA_DIR mirroring llm_gateway settings style
key-files:
  created:
    - data-service/connectors.py
    - data-service/tests/test_connectors.py
  modified:
    - data-service/app.py
    - .gitignore
decisions:
  - "Registry ships 14 connectors, not 13 — enumerated contract in REQUIREMENTS CONN-01 and PLAN 812-01 lists 14 slugs; the '13' in prose is a counting typo"
  - "Tokens hashed (SHA-256) rather than encrypted — plaintext never needed back"
  - "connector last_connection = max over all its credentials incl. revoked (past connections still happened)"
metrics:
  duration: ~15 min
  completed: 2026-07-11
status: complete
---

# Phase 812 Plan 01: Connector Credential Backend Summary

**One-liner:** Connector credential CRUD + token-authenticated heartbeat in data-service — dgc_ tokens minted server-side, returned once, persisted only as SHA-256 hashes, with never_connected/active/stale status derivation per connector.

## Objective

data-service can mint, list, and revoke connector credentials and track per-connector connection status via a token-authenticated heartbeat endpoint (CONNB-01..04). Platform side of the connector ecosystem; UI in Phase 813, docs in 815.

## Endpoints Added

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/connectors` | Registry (14 connectors / 5 categories) joined with per-connector `status`, `last_connection`, and credential summaries (`credential_id`, `label`, `created_at`, `revoked` — never token/hash). Also returns ordered `categories` list. |
| POST | `/connectors/{connector_id}/credentials` | Body `{label?}`. 201 with `{credential_id, token}` — only time the token is visible. 404 `CONNECTOR_NOT_FOUND` for unknown ids. |
| DELETE | `/connectors/{connector_id}/credentials/{credential_id}` | 204; revoked tokens stop authenticating. 404 `CONNECTOR_NOT_FOUND` / `CREDENTIAL_NOT_FOUND`. |
| POST | `/connectors/heartbeat` | `Authorization: Bearer dgc_...`; matches SHA-256 hash against non-revoked credentials; stamps that connector's `last_connection`; returns `{connector_id, status}`. 401 `CONNECTOR_AUTH_FAILED` on unknown/revoked/malformed token. |

Errors use the existing `_structured_error_response` convention (`{error, hint, code}` detail body).

## Implementation Notes

- `data-service/connectors.py` mirrors `llm_gateway.py` persistence: module-level `DATA_DIR` (from `DG_DATA_DIR`) + `CREDENTIALS_FILE` (`data/connector-credentials.json`), tolerant `load_credentials`/`save_credentials` helpers.
- Tokens: `dgc_` + `secrets.token_urlsafe(32)`; only `hashlib.sha256` hex digest persisted (hashing beats encryption — plaintext never needed back).
- Status derivation: `never_connected` (no heartbeat ever), `active` (≤ 7 days), `stale` (older). `derive_status(last_connection, now=None)` takes an injectable `now` for deterministic tests.
- `.gitignore` now excludes `data-service/data/*` (keeps tracked `.gitkeep`) so `connector-credentials.json`, `llm-settings.json`, `speckle-settings.json` runtime state stays out of git.

## Test Results

`python -m pytest data-service/tests/ -q` → **82 passed** (19 new in `test_connectors.py`, 63 pre-existing, **no pre-existing failures**).

New coverage: registry shape (14 slugs / 5 categories); create returns token once and persists only the hash; token never appears in GET /connectors output; heartbeat with valid token → `active` + `last_connection` stamped; unknown/malformed/revoked token → 401; status derivation for never_connected/active/stale (injected `now`); stale surfaces end-to-end via endpoint; revoke lifecycle incl. history preservation.

## Deviations from Plan

**1. [Rule 1 - Plan inconsistency] Registry has 14 connectors, not 13**
- **Found during:** Task 1
- **Issue:** Plan (and ROADMAP/REQUIREMENTS prose) says "13 connectors / 5 categories", but the enumerated slug list in the plan's fixed contract and REQUIREMENTS CONN-01 both list **14** names (BIM Authoring has 6: Revit, Blender, Tekla, Archicad, Civil3D, Infraworks).
- **Fix:** Implemented the enumerated 14-slug contract (Phase 813 UI depends on exact slugs); tests assert 14. The "13" is a counting typo in prose.
- **Files:** data-service/connectors.py, data-service/tests/test_connectors.py

**2. [Rule 2 - Missing critical functionality] .gitignore hardening for runtime credential store**
- **Found during:** Task 1 (per orchestrator constraint)
- **Issue:** `data-service/data/*.json` runtime state (incl. the new credential store with token hashes) was not gitignored.
- **Fix:** Added `data-service/data/*` + `!data-service/data/.gitkeep` to `.gitignore`.

No other deviations — plan executed as written.

## Self-Check: PASSED

- FOUND: data-service/connectors.py
- FOUND: data-service/tests/test_connectors.py
- FOUND: commit 6cde93c
