---
phase: 1205-security-and-tenancy-release-gate
plan: "15"
subsystem: ui-v2 nginx / runtime config
tags: [nginx, tombstone, config-js, secret-scan, d-06, d-08, d-12, d-16, static-boundary]

requires:
  - phase: 1205-09
    provides: "UI container environment reduced to DATA_SERVICE_URL and SPECKLE_BASE_URL"
  - phase: 1205-11
    provides: "UI source reads only dataServiceUrl / speckleBaseUrl; Speckle read token comes from /validation/view"
  - phase: 1205-13
    provides: "membership-scoped Projects UI; no remaining consumer of /neo4j or /n8n"
provides:
  - "ui-v2/nginx.conf without neo4j/n8n proxies; ^~ /neo4j and ^~ /n8n return 404 ahead of the SPA fallback"
  - "ui-v2/gen-config.sh: two-variable, two-key config.js generator (output path as $1)"
  - "data-service/tests/test_static_proxy_boundary.py (D-16 static half, 11 tests incl. induced-regression proofs)"
  - "data-service/tests/test_config_js_no_secrets.py (D-12 generator + dist bundle scan, 10 tests, fails closed without dist)"
affects: [1205-16, 1205-17, 1205-18, 1205-19]

tech-stack:
  added: []
  patterns:
    - "Brace-aware nginx location parser in a pytest file, no nginx binary needed"
    - "Bundle scan hashes every quoted string literal against KNOWN_DEFAULT_SHA256 so the digest-only default is detectable without being spelled out"

key-files:
  created:
    - ui-v2/gen-config.sh
    - data-service/tests/test_static_proxy_boundary.py
    - data-service/tests/test_config_js_no_secrets.py
  modified:
    - ui-v2/nginx.conf
    - ui-v2/entrypoint.sh
    - ui-v2/Dockerfile
    - ui-v2/vite.config.js

key-decisions:
  - "gen-config.sh JS-escapes backslash/double-quote and strips CR/LF from the two URL values so a hostile env value cannot inject a config key"
  - "Neo4j default literal is checked as an exact string literal in the bundle (not a raw substring) to avoid false positives on numeric constants; the change-me prefix and key names are raw substring checks"
  - "Legacy cfg.neo4jUri display fallback in GraphScreen is left untouched: it is a non-secret label and is not on the forbidden key list"

requirements-completed: []

duration: ~25min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 15: nginx tombstones and secret-free runtime config Summary

The UI container no longer proxies to Neo4j or n8n (both paths are explicit 404 tombstones) and its generated config.js carries exactly `dataServiceUrl` and `speckleBaseUrl`, with both facts machine-checked by two new test files.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | nginx tombstones, dev-proxy removal, static proxy boundary test | d32e20c |
| 2 | Secret-free config.js generator and config/bundle secret scan | 1d705e5 |

## Verification

- `python -m pytest data-service/tests/test_static_proxy_boundary.py` : 11 passed (host).
- `python -m pytest data-service/tests/test_config_js_no_secrets.py` : 10 passed (host), including the dist scan against the freshly built bundle.
- Combined with `test_compose_boundary.py`: 40 passed (host).
- In-container (`data-service`, test files copied in via `docker cp` rather than a data-service rebuild, then removed; `ui-v2/` reached through the `/mnt/repo` mount): 21 passed.
- `npm --prefix ui-v2 run build`: green.
- `grep -c "neo4j:7474\|n8n:5678" ui-v2/nginx.conf` = 0; `grep -c "return 404" ui-v2/nginx.conf` = 2.
- `docker compose build --no-cache design-grammars` succeeded (gen-config.sh copied and executable) and `docker compose up -d design-grammars` recreated the live container.
- Live config.js key names (names only): `dataServiceUrl`, `speckleBaseUrl`.
- Live status codes: `/neo4j/` 404, `/neo4j/db/neo4j/tx/commit` 404, `/n8n/` 404, `/n8n/webhook/dg/rules-ingest` 404, `/` 200, `/data-service/projects` 401 (proxy to data-service intact).
- `tools/security/check_live_boundary.py` (local profile) status lines, `passed: True`:
  - proxy_removed: `/neo4j/` 404 pass; `/neo4j/db/neo4j/tx/commit` 404 pass; `/n8n/webhook/dg/graph-query` 404 pass
  - unauthenticated: 4 routes 401 pass; `/data-service/` 200 pass
  - config_js: no credential key name (pass); no known-default literal (pass)
  - ports 7687 / 7474 / 5678: info only (trusted-local, not enforced in local profile)

## Deviations from Plan

None to code. Two process notes:

- The auto-mode classifier blocked reading `ui-v2/public/config.js` directly (credential-materialization guard), so its content was never inspected. It is covered indirectly: the dist scan (which includes the copy of public/config.js in dist) found no credential key name, tx/commit path, default literal or digest.
- The in-container run used `docker cp` of the two new test files instead of a data-service image rebuild (the live data-service image predates them); the data-service image itself was not modified.

## Known Stubs

None.

## Threat Flags

None. All five register entries (T-1205-15-01..05) are mitigated as planned.

## Requirements

ALGN12-18 and ALGN12-19 are not marked complete here: the live half of D-16 and the SECURITY-BOUNDARY drift test land in 1205-16/18/19.

## Self-Check: PASSED

Files present: ui-v2/gen-config.sh, both test files, modified nginx.conf/entrypoint.sh/Dockerfile/vite.config.js. Commits d32e20c and 1d705e5 exist.
