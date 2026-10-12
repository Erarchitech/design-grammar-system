---
phase: 1308-dg-web-ui
plan: "10"
subsystem: ui-v2-projects-screen
tags: [react, members, roles, export-policy, i18n, node-test, browser-harness]
requires:
  - phase: 1308-01
    provides: "settled ProjectsScreen.jsx / auth.js working tree"
  - phase: 1308-02
    provides: "PUT /projects/{project}/members/{username} with LAST_OWNER protection"
  - phase: 1308-05
    provides: "i18n layer (t, tp, tc, describeError, roleLabel, raw-text guard)"
provides:
  - "lib/memberApi.changeMemberRole(project, username, role)"
  - "lib/memberRoles.isSoleOwner, needsSelfDemotionConfirm"
  - "lib/projectSettingsApi getDegramPolicy, setDegramPolicy, policyPatch, shouldShowProjectSettings"
  - "ProjectsScreen: MemberRow/MemberRoleSelect role Select and admin-only ProjectSettingsPanel"
  - "dict/projects.js RU dictionary and tests/i18n-swept/projects.json manifest"
affects: [1308-24]
tech-stack:
  added: []
  patterns:
    - "inline error state keeps the error object and renders describeError at render time, so the text follows a live language switch"
    - "browser harness (run-panel.mjs) is the real-React proof for panel behaviour; node tests cover API modules and pure helpers"
key-files:
  created:
    - ui-v2/src/lib/memberApi.js
    - ui-v2/src/lib/memberRoles.js
    - ui-v2/src/lib/projectSettingsApi.js
    - ui-v2/tests/member-roles-api.test.mjs
    - ui-v2/tests/project-settings-api.test.mjs
    - ui-v2/tests/i18n-swept/projects.json
  modified:
    - ui-v2/src/screens/ProjectsScreen.jsx
    - ui-v2/src/i18n/dict/projects.js
    - ui-v2/tests/projects-panel.browser.jsx
key-decisions:
  - "Members and Project settings panels share one wrapper div so the 24px marginTop is the only gap between them (the screen column already has a 28px gap)"
  - "Checkbox primitive has no input element, so each policy row wraps it in role=checkbox with tabIndex, aria-checked/disabled/labelledby/describedby and Space/Enter handling; no new primitive"
  - "The confirm button for whole-definition export uses tc('confirm', ...) because the UI-SPEC gives it a different RU text than the toggle label"
  - "A malformed policy GET body fails closed to the load-error state; no flag is guessed"
requirements-completed: [WEBUI-03, WEBUI-04]
duration: ~75 min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 10: Role Select, admin Project settings and Projects screen i18n Summary

**Owners and admins change member roles from a per-row Select (optimistic, rollback, mapped errors, sole-owner guard, self-demotion confirm); DG admins alone get a Project settings panel for the export policy with a confirm before whole-definition export; the whole Projects screen runs through t()/tp() with an RU dictionary and a raw-text-guard manifest.**

## What was built

- **Task 1 (406abef):** `changeMemberRole` (PUT, cookie + `X-DG-CSRF`, both path segments encoded) and the pure helpers `isSoleOwner` / `needsSelfDemotionConfirm` (matches `user.username ?? email ?? name`; admin and other-member changes never confirm). `MemberRow` owns the per-row state: the Select shows the new value at once and is disabled (opacity 0.45) in flight; on success the member list is patched locally and refreshed behind the `panelScope` guard, and «Role updated for {username}» goes to a hidden `aria-live="polite"` node; on failure the value rolls back and `describeError` text appears under the row. The sole owner's Select is disabled with the tooltip and a hidden `aria-describedby` node. A non-admin owner demoting themselves sees the inline confirm («Change role» / «Keep my role», Escape keeps). The static `Badge` is gone; the row button reads «Remove member».
- **Task 2 (e90adf8):** `projectSettingsApi.js` and `ProjectSettingsPanel` below Members, rendered only through `shouldShowProjectSettings(user, project)` (DG admin and a project). Loading text, load error with «Retry loading settings», two toggles (12px helper, 4px label gap, 16px between rows), only the changed flag is sent (`policyPatch`), optimistic update with rollback, hidden saved region, `ADMIN_REQUIRED` shows the mapped text and reloads. Enabling `wholeDefinitionAllowed` shows the inline confirm (text with the project, «Allow whole-definition export» / «Keep export off», Escape keeps off); the checkbox stays off until confirmed.
- **Task 3 (5a0180f):** every remaining literal in `ProjectsScreen.jsx` through `t()`/`tp()` (back, title, create form, tile descriptions with plural «{n} node in graph», footer plural, invite form, notes, errors); roles via `roleLabel`; load/create/members/invite errors store the error object and render `describeError`. `tests/i18n-swept/projects.json` lists the screen and the three lib modules with an empty allow list.

## Verification (real runs)

- `node --test ui-v2/tests/*.test.mjs`: 274 pass, 0 fail (includes the raw-text guard for `projects.json`, key coverage in both directions and placeholder parity). `npm --prefix ui-v2 test`: 274 pass.
- `npm --prefix ui-v2 run build`: succeeds after each task.
- `python -m pytest data-service/tests/test_degram_policy.py -q`: 18 passed (host python, route unchanged).
- Panel harness `node ui-v2/tests/run-panel.mjs t1308-10` (real React 18 + ReactDOM in headless Chrome, fake fetch, CSP connect-src none): 30/30 PASS (15 existing, updated where needed; 15 new: role Select 6, Project settings 8, Russian render 1). Evidence files from these runs were deleted (`.planning/audit-evidence/` is untracked owner WIP).
- Mutation checks run by hand and reverted: disabling the whole-definition confirm branch failed the harness (exit 1); replacing `{t("Back")}` by raw text failed the raw-text guard on `projects.json`.
- Acceptance greps: `changeMemberRole`, `MemberRoleSelect`, `shouldShowProjectSettings(`, `setDegramPolicy` found in the screen; RU strings «Роль пользователя {username}», «Исключить участника», «Наблюдатель» (core), «Разрешить экспорт определения целиком», «Видно только администраторам DG» found in the dictionaries; `ui-v2/tests/run-panel.mjs` is tracked and passes.
- Not verified: rendering in a real browser against the live stack (no rebuild of `design-grammars` in this plan; live check belongs to 1308-24), visual spacing/typography by eye, and the live DeGram `#degram-lang` path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Panel harness updated although not in files_modified**
- **Found during:** Task 1 and Task 3
- **Issue:** `ui-v2/tests/projects-panel.browser.jsx` (tracked, run by `run-panel.mjs`, which Task 3 tells to run) asserted the old English labels («Remove», «Invite», «Copy», «Dismiss»), the server text «Cannot remove last owner» (D-09 now maps `LAST_OWNER` by code), the lowercase role in the invite note, and, for an admin, the old request order.
- **Fix:** assertions updated to the renamed labels and mapped texts; for a DG admin the policy GET is now the first request (child effect runs before the screen's); new cases added for role Select, Project settings and a Russian render. 
- **Files modified:** `ui-v2/tests/projects-panel.browser.jsx`
- **Commits:** 406abef, e90adf8, 5a0180f

**2. [Process] Tests-first was partial**
- Task 1 and 2 API/helper tests were written and run RED (missing modules; missing screen wiring) before implementation. The browser-harness cases were written after the component code, compensated by the two mutation checks above. No separate `test(...)` commits exist (TDD gate warning).

No other deviations. Panel rendering choices that go beyond the plan text are listed under key-decisions.

## Known Stubs

None. No empty or placeholder data flows to the UI.

## Threat Flags

None. T-1308-10-01 (server routes are the control, unchanged), -02 (all calls via `apiFetch`, asserted in the API tests and the harness teardown for every request), -03 (`encodeURIComponent` on every segment, tested with `'A/B ?#'`) and -04 (`shouldShowProjectSettings` unit test, source assertion that the panel renders in one place, harness case that an owner who is not an admin sees no panel and issues no policy request) are covered. The prohibition «no export-policy control, values or placeholder for a non-admin» is enforced in the UI by that guard and remains unresolved at the server only in the sense the plan flagged: the routes stay admin-only (`test_degram_policy.py`).

## Self-Check: PASSED

- Files exist: `ui-v2/src/lib/memberApi.js`, `memberRoles.js`, `projectSettingsApi.js`, `ui-v2/tests/member-roles-api.test.mjs`, `project-settings-api.test.mjs`, `i18n-swept/projects.json`.
- Commits exist: 406abef, e90adf8, 5a0180f.
