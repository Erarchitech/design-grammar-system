---
phase: 1308-dg-web-ui
plan: "15"
subsystem: ui
tags: [connectors, react, i18n, connector-session, access-grants, api-docs]
requires:
  - phase: 1308-dg-web-ui
    provides: "Plan 24 supplies session-derived registry status and per-connector access responses"
provides:
  - "Web UI connector cards show session status, sign-in counts and account sign-in guidance instead of token controls"
  - "Owners and admins can grant or revoke per-connector access; eligible editors and viewers can request it"
  - "DeGram-hosted connector table uses shared EN/RU translations and has no token action"
  - "Six API-docs pages explain DG-account connector sign-in and session lifecycle"
affects: [1308-17, 1308-18, 1308-19, 1308-20, connector-uat]
tech-stack:
  added: []
  patterns:
    - "Scope registry and access reads to the selected project; hide stale cards and fail closed when member/access reads fail"
    - "Use shared t/tp, formatDate and describeError for connector copy, counts, dates and inline errors"
key-files:
  created:
    - ui-v2/tests/i18n-swept/connectors.json
  modified:
    - ui-v2/src/screens/ConnectorsScreen.jsx
    - ui-v2/src/screens/HostedConnectorsTable.jsx
    - ui-v2/src/screens/DegramGrantsPanel.jsx
    - ui-v2/src/lib/connectorsApi.js
    - ui-v2/src/lib/memberApi.js
    - ui-v2/src/i18n/dict/connectors.js
    - ui-v2/src/i18n/dict/screens.js
    - ui-v2/src/screens/apidocs/content/01-getting-started.js
    - ui-v2/src/screens/apidocs/content/02-authentication.js
    - ui-v2/src/screens/apidocs/content/03-credentials-api.js
    - ui-v2/src/screens/apidocs/content/04-heartbeat-api.js
    - ui-v2/src/screens/apidocs/content/05-connectors-status-api.js
    - ui-v2/src/screens/apidocs/content/07-extending.js
    - ui-v2/tests/connector-access-api.test.mjs
    - ui-v2/tests/api-security.test.mjs
    - ui-v2/tests/degram-grants.browser.jsx
    - ui-v2/tests/degram-grants.test.mjs
key-decisions:
  - "Keep the DeGram grant panel's separate authorization flow; rename its member request action so it does not imply issuing a token."
  - "Do not render project-scoped cards or owner controls until all required reads for that project succeed."
patterns-established:
  - "Disable the grant action during a POST and use an action sequence/project guard before applying a late result."
requirements-completed: [WEBUI-09, WEBUI-02, WEBUI-07]
coverage:
  - id: D1
    description: "Token-free Web UI cards show session status, live sign-in counts, access state and role-appropriate grant/request controls in EN/RU."
    requirement: WEBUI-09
    verification:
      - kind: automated_ui
        ref: "node ui-v2/tests/run-grants.mjs (11/11 offline harness cases)"
        status: pass
    human_judgment: true
    rationale: "Offline DOM harness verifies the flows, but visual layout, accessibility and real account/project behavior have not been accepted live."
  - id: D2
    description: "Hosted connector rows keep colored status dots, plain available access, member requests and a DG-account sign-in caption."
    requirement: WEBUI-09
    verification:
      - kind: automated_ui
        ref: "node ui-v2/tests/run-grants.mjs host (10/10 offline harness cases)"
        status: pass
    human_judgment: true
    rationale: "Host-mode rendering is tested offline; no running DeGram-hosted UI or add-in sign-in was inspected."
  - id: D3
    description: "Connector translations, EN/RU count plurals, cookie/CSRF API wrappers and six account-sign-in documentation pages build and pass source guards."
    requirement: WEBUI-02
    verification:
      - kind: unit
        ref: "node --test ui-v2/tests/*.test.mjs (278/278 passed)"
        status: pass
      - kind: other
        ref: "npm --prefix ui-v2 run build and plan 15 source searches"
        status: pass
    human_judgment: false
  - id: D4
    description: "The UI consumes session-derived registry status provided by plan 24, including active_sessions."
    requirement: WEBUI-07
    verification:
      - kind: automated_ui
        ref: "degram-grants.browser.jsx#GRANTS-normal-screen-project-change-hides-stale-access"
        status: pass
    human_judgment: true
    rationale: "Server contract was tested in plan 24, but end-to-end sign-in/status with a deployed service was not run in this plan."
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 15: Connector Session UI Summary

**Connector UI and developer docs now guide DG-account sign-in and per-connector access, without offering legacy credential creation or reveal.**

## Accomplishments

- Replaced the token panels in the normal Connectors screen with session-derived status, last sign-in, translated live sign-in counts, access lines and instructions. An owner/admin can select an eligible editor/viewer and grant access; members without access can request it. Grant, revoke and request errors appear inline through `describeError`. Project switches hide old cards and failed member/access reads cannot masquerade as an empty grant list.
- Removed token controls from the DeGram-hosted table, preserved its green/red dots and separate DeGram grant flow, and added the sign-in caption. The normal Web UI keeps monochrome ink/gray dots. Shared translations replaced the hosted table's private language map; the DeGram panel's member action now says “Request access.”
- Removed credential create/revoke client calls; added `listProjectMembers` through `apiFetch`. Rewrote the six planned API-docs content modules around account login, scoped eight-hour `dgk_` sessions, sign-out, heartbeat and the retired creation route's 410 response. Navigation IDs remain intact.

## Task Commits

- `0386a7f` — Web and hosted UI, API wrappers, translations and offline tests (Tasks 1–2 combined).
- `3011bc8` — six API-documentation pages (Task 3).

## Verification

- `node --test ui-v2/tests/*.test.mjs`: **278 passed, 0 failed, 0 skipped**.
- `node ui-v2/tests/run-grants.mjs`: **11/11 PASS**. `node ui-v2/tests/run-grants.mjs host`: **10/10 PASS**. Coverage includes duplicate-grant 409 EN/RU feedback, in-flight disabled grant action, project switching, failed owner member-list read, hosted requests and absence of token buttons.
- `npm --prefix ui-v2 run build`: **passed** (existing warning for a minified chunk larger than 500 kB).
- Source acceptance: no `createCredential`, `revokeCredential`, legacy connector-token prefix, or token-creation labels under `ui-v2/src`; no removed token components or local date formatter in the normal screen. `GrantToMemberForm`, `active_sessions` and `issueConnectorAccess` are present. Authentication and connector-session reference pages name `/auth/connector-session`; heartbeat and extending pages also reference it. Scoped `git diff --check` passed.
- `python tools/degram/workspace.py verify`: gitlink matches component HEAD, context installed. `graphify update .` rebuilt the graph earlier in execution with a missing optional SQL parser warning; generated graph files are not in either task commit.

## Deviations from Plan

- **[Rule 1 - Correctness] Prevent previous-project access from appearing on a new project.** Found during Task 2. Registry cards are hidden until the selected project's read completes; late action results are guarded by project and load sequence. The normal browser harness checks A→B and EN/RU plural output. Committed in `0386a7f`.
- **[Rule 1 - Correctness] Fail closed on owner member/access read errors.** Found during Task 2. Reads must succeed before owner controls or the empty eligible-member message appear; the browser harness tests a failed member read. Committed in `0386a7f`.
- **TDD history:** Tasks 1–2 were implemented and verified during the interrupted execution before these commits, so separate RED test commits were not recorded. The final history groups the passing test changes with their production code; no pre-implementation failing-test claim is made.

**Total deviations:** 2 correctness fixes. **Impact:** both preserve project/authorization clarity without changing the planned API.

## Deferred Verification

No live deployment, browser/DeGram visual acceptance, account sign-in from an add-in, or live connector-status round trip was performed. Plan 24's live DSAV cases were collected only, not executed; plans 1308-19/20 own the live retirement and rollout checkpoints. `requirements-completed` lists the plan's target IDs, not phase-wide live acceptance.

The browser harness modified `ui-v2/tests/evidence/degram-verified.json` and produced local evidence/preflight files. Those generated or pre-existing files, unrelated planning changes and graph output were excluded from the task commits.

## Next Phase Readiness

Offline UI and documentation gates are green. Continue only with the next dependency-eligible Phase 1308 plan; preserve unrelated working-tree edits and keep live acceptance open.

## Self-Check: PASSED (offline scope)

Both task commits exist, all planned offline verification commands and source gates passed, and this summary distinguishes offline proof from live acceptance.
