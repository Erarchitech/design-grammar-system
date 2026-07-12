---
phase: 815-dg-api-documentation
plan: "815-01"
subsystem: ui-v2
tags: [api-docs, documentation-viewer, content-architecture]
requires:
  - Phase 810 (ApiDocsScreen skeleton)
  - Phase 812 (Connector credential backend)
  - Phase 814 (Reasoner screen — same screen layer pattern)
provides:
  - Revit-API-style documentation browser for DG connector API
  - Extendable content module system (add file = add section)
affects:
  - ui-v2/src/screens/ApiDocsScreen.jsx (skeleton → full viewer)
  - ui-v2/src/screens/apidocs/content/ (8 new files)
tech-stack:
  added:
    - Vite import.meta.glob for content aggregation
    - Structured block types (text/code/endpoint/table/note)
  patterns:
    - Revit-API documentation information architecture
    - Content-driven pages with zero viewer-code changes
key-files:
  created:
    - ui-v2/src/screens/apidocs/content/index.js
    - ui-v2/src/screens/apidocs/content/01-getting-started.js
    - ui-v2/src/screens/apidocs/content/02-authentication.js
    - ui-v2/src/screens/apidocs/content/03-credentials-api.js
    - ui-v2/src/screens/apidocs/content/04-heartbeat-api.js
    - ui-v2/src/screens/apidocs/content/05-connectors-status-api.js
    - ui-v2/src/screens/apidocs/content/06-validation-publish-api.js
    - ui-v2/src/screens/apidocs/content/07-extending.js
  modified:
    - ui-v2/src/screens/ApiDocsScreen.jsx (skeleton → full viewer)
decisions:
  - Content modules discovered via import.meta.glob with ##- prefix sorting
  - Block types mirror Revit API reference sections (endpoint signature, params table, request/response)
  - No new shared primitives — CodeBlock and design tokens reused
metrics:
  duration: "~8 minutes"
  completed_date: "2026-07-11"
status: complete
---

# Phase 815 Plan 01: DG API Documentation — Summary

**One-liner:** Revit-API-style in-app documentation browser for the DG connector and validation API, with left tree navigation and right detail pane rendering typed blocks (text, code, endpoint, table, note), driven by content modules that auto-register via Vite's `import.meta.glob`.

## Completed Tasks

| Task | Name                | Type       | Commit | Key Files |
| ---- | ------------------- | ---------- | ------ | --------- |
| 1    | content architecture | auto (APID-03) | `311a5eb` | 8 content files in `apidocs/content/` |
| 2    | viewer              | auto (APID-01) | `774ef15` | `ApiDocsScreen.jsx` (313 lines) |
| 3    | content             | auto (APID-02) | `311a5eb` | Authored inline during Task 1 |
| 4    | verify              | auto         | `3326f1d` | Build + endpoint cross-check |

## Content Architecture

7 section modules in `ui-v2/src/screens/apidocs/content/`:

| Module | Pages | Documents |
| ------ | ----- | --------- |
| `01-getting-started.js` | Overview, Base URL and Proxying, API Conventions | Nginx proxy paths, `/data-service/` prefix stripping |
| `02-authentication.js` | Token Format, Creating Credentials, Token Lifecycle | `dgc_` prefix, SHA-256 hashing, create-once-return-once |
| `03-credentials-api.js` | Create Credential, Revoke Credential | `POST/DELETE /connectors/{id}/credentials` |
| `04-heartbeat-api.js` | Send Heartbeat, Status Semantics | `POST /connectors/heartbeat`, never_connected/active/stale |
| `05-connectors-status-api.js` | List All Connectors | `GET /connectors`, 14 connectors in 5 categories |
| `06-validation-publish-api.js` | Publish Validation, List Runs, Get View, Delete Run, Error Response Format | `POST /validation/publish`, `GET /validation/runs/{project}`, `GET/DELETE` view/run endpoints, 11 error codes |
| `07-extending.js` | Content Module Format | Self-documenting module schema, block type reference |

## Viewer Layout

- **Left tree pane** (260px): expandable sections (chevron toggle), page items with Signal Red active highlight (`--color-signal-ink` + `--color-signal-soft`)
- **Right detail pane**: breadcrumb (`Section / Page`), 26px page title, summary line with bottom border, then rendered block sequence
- **Block types**:
  - `text`: paragraph prose, max 700px readable width
  - `code`: `CodeBlock` component with optional label, `--font-mono` (Geist Mono)
  - `endpoint`: color-coded method badge (GET green, POST blue, DELETE Signal Red), path, description, parameter table, request/response `CodeBlock` examples
  - `table`: grid with uppercase header labels, first column bold
  - `note`: three variants — info (muted border), warning (Signal Red soft background), tip (green)
- **State**: local-only (`expandedSections`, `selectedSectionId`, `selectedPageId`)
- **No loading state**: content is eagerly loaded via `import.meta.glob({eager: true})`

## Content Accuracy

Every endpoint, parameter, response shape, error code, and status derivation documented in the content modules was cross-checked against the real source:
- `data-service/app.py` (40+ endpoint routes)
- `data-service/connectors.py` (credential lifecycle, token format, status derivation)
- `data-service/reasoner.py` (reasoner registry)
- `ui-v2/nginx.conf` (proxy path mappings)

Error response table documents all 11 error codes found in the codebase (CONNECTOR_NOT_FOUND, CREDENTIAL_NOT_FOUND, CONNECTOR_AUTH_FAILED, SPECKLE_CONFIG_MISSING, SPECKLE_TOKEN_MISSING, PUBLISH_VALIDATION_ERROR, PUBLISH_INTERNAL_ERROR, DELETE_VALIDATION_ERROR, DELETE_INTERNAL_ERROR, RUN_NOT_FOUND, REASONER_NOT_FOUND).

## Verification

```bash
npm --prefix ui-v2 run build
# ✓ 940 modules transformed, built in 6.14s, 0 errors
```

All documented routes verified against `app.py` decorators.

## Deviations from Plan

None — plan executed exactly as written. Task 3 content was authored inline during Task 1 since the content module files ARE the content.

## Stub Tracking

No stubs. All content modules carry accurate, complete documentation. The viewer renders every block type with real data.

## Threat Flags

None. The API docs screen is a read-only documentation browser with no network access, no auth surface, and no data mutation.

## Self-Check: PASSED

All files exist, all commits exist (311a5eb, 774ef15, 3326f1d), build passes.
