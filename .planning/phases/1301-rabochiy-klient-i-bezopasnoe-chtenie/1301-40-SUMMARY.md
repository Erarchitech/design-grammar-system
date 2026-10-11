---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 40
subsystem: connectors-access
status: complete
completed: 2026-10-11
requires: [1301-36]
provides:
  - per-connector access requests (viewer requests, owner/admin approves, approved viewer mints the token) (D-46)
  - DeGram-hosted Connectors page as a table of all connectors with access and Вкл/Выкл status (D-45)
affects: [1301-41]
tech-stack:
  patterns:
    - single JSON store with two row lists written in one atomic replace
    - route policy lowered to the member floor with a handler-side gate (role >= editor OR approved access)
    - render-prop for the one-time token panel to avoid a screen/table import cycle
key-files:
  created:
    - data-service/connector_access.py
    - data-service/tests/test_connector_access.py
    - ui-v2/src/screens/HostedConnectorsTable.jsx
    - ui-v2/tests/connector-access-api.test.mjs
  modified:
    - data-service/app.py
    - data-service/route_policy.py
    - data-service/tests/test_connectors.py
    - data-service/tests/test_route_inventory.py
    - data-service/tests/test_cross_project_matrix.py
    - spec/SECURITY-BOUNDARY.md
    - spec/API.md
    - ui-v2/src/lib/connectorsApi.js
    - ui-v2/src/screens/ConnectorsScreen.jsx
    - ui-v2/src/styles/tokens/colors.css
    - ui-v2/tests/degram-grants.test.mjs
    - ui-v2/tests/degram-grants.browser.jsx
requirements-completed: [DGCL-05, DGCL-06]
---

# Phase 1301 Plan 40: per-connector access requests and the DeGram connectors table

**A viewer can request access to Grasshopper, Revit and the other registry connectors, the owner or admin approves it under the connector's «Pending requests» in the Web UI, and the approved viewer then mints that connector's token; DeGram «Коннекторы» is now one table of every connector with an access cell and a Вкл/Выкл dot.**

## What was built

### Data service (D-46)
- `connector_access.py`: store `connector-access.json` (`grants` + `requests`, one atomic replace). `create_request` (note at most 200, one pending row per user/project/connector, 409 `ACCESS_EXISTS` for owner/editor or an active access, 404 `CONNECTOR_NOT_FOUND` for unknown ids and `degram`), `issue_access` (member required, replaces an earlier active row, closes the pending request), `revoke_access`, `can_create`, `access_state` (`available` / `pending` / `requestable`), lists (project, mine) with no token or hash, cascades `revoke_for_user` and `revoke_for_user_project` (membership removal also closes the user's pending requests, so a re-added member does not regain access).
- Routes (5): `POST /connector-access-requests`, `GET /connector-access/mine`, `GET|POST /projects/{project}/connector-access`, `DELETE /projects/{project}/connector-access/{access_id}`.
- `POST /connectors/{connector_id}/credentials`: policy row `role="viewer"`; handler requires effective role >= editor (admin counts as owner) OR `can_create`, else 403 `CONNECTOR_ACCESS_REQUIRED`. Credential DELETE stays editor-only.
- `GET /connectors?project=P` adds `access` to each registry connector for a member of P (admin included); no project or a non-member leaves the payload unchanged. The DeGram card has no `access` field.
- Member removal (`DELETE /projects/{project}/members/{username}`) cascades connector access next to the DeGram cascade.

### Spec
- `spec/SECURITY-BOUNDARY.md`: five rows added to the §4.2 route-policy block in sorted position, credential POST row now `viewer`, storage note (`connector-access.json`), §3.2 section «Who may mint a connector token», §10 row.
- `spec/API.md`: the five routes and `GET /connectors?project=` documented.

### ui-v2 (D-45)
- `connectorsApi.js`: `listConnectors(project)` and `requestConnectorAccess`, `listMyConnectorAccess`, `listProjectConnectorAccess`, `issueConnectorAccess`, `revokeConnectorAccess`.
- `HostedConnectorsTable.jsx`: `<table>` with `border: none` cells, name in the first column; access cell «Доступен» + «Создать токен» / «Запросить доступ» (optional note) / «Запрос отправлен»; status cell right-aligned «Вкл» with `--status-on` dot when `status === "active"`, «Выкл» with `--status-fail` otherwise; RU/EN via `hostLang()`. The DeGram row is one row of the same table: access comes from `GET /degram/grants/mine` (active grant -> «Доступен», no token action; pending request -> «Запрос отправлен»; else «Запросить доступ» via `requestGrant`).
- `colors.css`: `--status-on` (light `#2e9e5b`, dark `#4cc77f`). The Web UI `StatusDot` is unchanged.
- `ConnectorsScreen.jsx`: hosted mode loads `listConnectors(project)` + `listMyGrants()` and renders the table, reusing the existing one-time `TokenRevealPanel` through a render prop. Web UI owner/admin cards gain «Pending requests» (Grant) and «Approved access» (Revoke access) from `listProjectConnectorAccess`; loads are guarded by a sequence counter against stale project switches.

## Verification (real output)
- `python -m pytest` on `test_connector_access.py`, `test_degram_grants.py`, `test_degram_pairing.py`, `test_delegated_token.py`, `test_route_inventory.py`, `test_connectors.py`, `test_cross_project_matrix.py`, `test_security_boundary_spec.py`: **2395 passed** (host run; no env failures in this set). `test_auth_tracer.py`, `test_dsav_live_loop.py`, `test_dsav_publish_leg.py`, `test_project_routes.py`, `test_review_fix_1205.py`: 182 passed, 1 skipped, 7 deselected.
- `node --test ui-v2/tests/*.test.mjs`: 231/231 (includes the five plan files: 25/25).
- `node ui-v2/tests/run-grants.mjs host`: 9/9 PASS; `node ui-v2/tests/run-grants.mjs`: 7/7 PASS. A mutation check (breaking the active dot colour) made `GRANTS-host-connector-table` FAIL, so the browser assertions are not vacuous.
- `npm --prefix ui-v2 run build`: exit 0 (chunk-size warning only).
- Acceptance greps: `CONNECTOR_ACCESS_REQUIRED` in `connector_access.py` and `app.py` (docstring + raise via `connector_access.access_required()`); `status-on` in `colors.css` and `HostedConnectorsTable.jsx`; `connector-access` appears 9 times in `SECURITY-BOUNDARY.md`.

## Deviations from Plan

### Auto-fixed Issues
None needing a code fix after the fact.

### Judgement calls
- **TDD order.** The Python test file and the node API test were written before the implementation, but the Python suite was not run red separately (the module did not exist, so the import failed by construction); the UI browser/regex tests were updated alongside the implementation, not before. The mutation check above stands in for the missing red run on the dot colours.
- **DeGram row copy.** The plan names «Запросить новый токен» for the DeGram row; D-45 says «Запросить доступ». The table uses «Запросить доступ» (EN «Request access») for a member with no grant, and the previous trimmed panel («Запросить новый токен») remains in `DegramGrantsPanel` (still used for the owner card and its tests) but is no longer rendered by the hosted screen.
- **Single commit.** The plan says «Do not commit yet» for Tasks 1-3 and one commit in Task 4, so all three tasks are in one commit.
- `DegramGrantsPanel.jsx` (listed in the plan) did not need a change.
- **Requirements not marked.** The plan frontmatter lists DGCL-05 and DGCL-06 (logout/revoke lifecycle and long-request cancellation), which this plan advances only partly. `requirements.mark-complete` ran and flipped both, but the change to `.planning/REQUIREMENTS.md` was reverted (`git checkout -- .planning/REQUIREMENTS.md`, file had no other edits) so the traceability table does not claim completion before the phase verifier decides. Likewise `state.advance-plan` bumped `current_plan` from 2 to 3 against a 41-plan phase (its counter is out of step with the plan numbering); that field was restored to 2.
- Web UI `load()` also fetches `GET /projects/{project}/connector-access` for owners/admins, so the access lists are present when a card expands.

## Known Stubs
None.

## Threat Flags
None beyond the register: T-1301-40-01 (handler gate tested: 403 `CONNECTOR_ACCESS_REQUIRED` for a viewer without access, per connector and per project), -02 (non-owner and viewer 403 on issue/revoke/list, tested), -03 (no `token`/`token_hash` in any list payload, tested), -04 (matrix sweep of the new member rows plus dedicated P1/P2 cases, `PROJECT_MISMATCH` tested), -05 (`issued_by`, `revoked_by` stored).

## Limits
- Not live-tested: nothing was rebuilt or restarted (plan 41, owner consent). The flow and table are covered by the TestClient suite and the headless-Chrome harness, not the running stack.
- RU copy is covered by a source regex in `degram-grants.test.mjs`, not rendered in the browser harness (the runner only sets `host=degram`).
- The framework tree still carries other sessions' uncommitted edits (`data-service/cypher_allowlist.py`, `dg_context.py`, `spec/DATABASE.md`, `ui-v2/src/lib/auth.js`, `ProjectsScreen.jsx`, `ui-v2/tests/evidence/degram-verified.json`, and others). None of them is in this plan's files; only the 16 plan files were staged by explicit path. `ui-v2` build and node tests were run on the working tree, which includes those edits.
- Nothing pushed, the `apps/degram` gitlink was not bumped.

## Commits
- framework `c9665ed` feat(1301-40): per-connector access requests and the DeGram connectors table (D-45, D-46)

## Self-Check: PASSED
